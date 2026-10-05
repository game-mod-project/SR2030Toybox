"""게임을 띄워 창 내용을 캡처하고 입력을 보내는 검증용 드라이버.

    uv run python scripts/gamedrive.py start [게임 인자...]   # 기본 -window. 창을 화면 밖에 두고 포커스를 건드리지 않는다
    uv run python scripts/gamedrive.py status
    uv run python scripts/gamedrive.py shot out.png [배율]    # 게임 창의 클라이언트 영역만 캡처
    uv run python scripts/gamedrive.py click X Y              # 클라이언트 좌표(캡처 이미지의 원본 픽셀)
    uv run python scripts/gamedrive.py move X Y               # 누르지 않고 마우스만 올린다(툴팁 확인)
    uv run python scripts/gamedrive.py key VK [VK...]         # 가상 키 코드(16진/10진) 또는 이름(ESC, ENTER, SPACE)
    uv run python scripts/gamedrive.py show                  # 화면 밖에 둔 게임 창을 화면으로 가져온다(직접 볼 때)
    uv run python scripts/gamedrive.py stop

화면 전체가 아니라 게임 창만 PrintWindow 로 읽고, 입력도 게임 창에만 메시지로 보낸다
(실제 마우스·키보드와 다른 창은 건드리지 않는다). 그래서 게임 창이 보이지 않아도 된다 —
start 는 게임 창을 화면 밖 맨 뒤에 두고, 게임이 포커스를 가져가면 쓰던 창으로 돌려준다.
shot·click·key 도 창이 화면에 나와 있으면 다시 밖으로 보낸다(최소화하면 그려지지 않으므로 최소화는 하지 않는다).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from srkit import config  # noqa: E402

EXE = "SupremeRuler2030.exe"
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                            ctypes.c_void_p, wintypes.UINT]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.IsWindow.argtypes = [wintypes.HWND]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.MapViewOfFile.restype = ctypes.c_void_p
kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

FILE_MAP_ALL_ACCESS = 0xF001F


class SharedCursor(ctypes.Structure):
    """훅 DLL 과 나눠 쓰는 메모리 — native/srhook/srhook.c 의 SRCURSOR 와 같아야 한다."""
    _fields_ = [("on", ctypes.c_long), ("x", ctypes.c_long), ("y", ctypes.c_long), ("reads", ctypes.c_long),
                ("hwnd", ctypes.c_ulonglong)]

SW_SHOWNOACTIVATE, HWND_TOP, HWND_BOTTOM = 4, 0, 1
SWP_NOSIZE, SWP_NOACTIVATE = 0x0001, 0x0010
SM_XVIRTUALSCREEN, SM_CXVIRTUALSCREEN = 76, 78
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x200, 0x201, 0x202, 0x100, 0x101, 0x102
KEYS = {"ESC": 0x1B, "ENTER": 0x0D, "SPACE": 0x20, "TAB": 0x09, "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27}


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def game_pids() -> list[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if line.startswith(f'"{EXE}"')]


def game_window(pids: set[int] | None = None) -> tuple[int, str, tuple[int, int]] | None:
    """게임 프로세스의 보이는 최상위 창 중 가장 큰 것: (hwnd, 제목, 클라이언트 크기)."""
    pids = set(game_pids()) if pids is None else pids
    found: list[tuple[int, int, str, tuple[int, int]]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            found.append((rect.right * rect.bottom, hwnd, title.value, (rect.right, rect.bottom)))
        return True

    user32.EnumWindows(visit, 0)
    if not found:
        return None
    _, hwnd, title, size = max(found)
    return hwnd, title, size


def capture(hwnd: int, size: tuple[int, int]) -> Image.Image:
    w, h = size
    screen = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, w, h)
    old = gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    info = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(info), 0)
    gdi32.SelectObject(mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, screen)
    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")


def offscreen_x() -> int:
    """모든 모니터를 합친 화면의 오른쪽 끝보다 바깥인 x 좌표."""
    return user32.GetSystemMetrics(SM_XVIRTUALSCREEN) + user32.GetSystemMetrics(SM_CXVIRTUALSCREEN) + 64


def hide(hwnd: int, give_focus_to: int = 0) -> tuple[bool, bool]:
    """게임 창을 화면 밖 맨 뒤에 둔다. 게임이 포커스를 쥐고 있으면 give_focus_to 창으로 돌려준다.

    (창을 옮겼는지, 포커스를 돌려주려 했는지)를 돌려준다.
    """
    moved = refocused = False
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if rect.left < offscreen_x():
        user32.SetWindowPos(hwnd, HWND_BOTTOM, offscreen_x(), 0, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
        moved = True
    if give_focus_to and give_focus_to != hwnd and user32.GetForegroundWindow() == hwnd and user32.IsWindow(give_focus_to):
        # 포커스를 쥔 스레드에 입력을 붙여야 다른 프로세스가 포커스를 옮길 수 있다
        me, game = kernel32.GetCurrentThreadId(), user32.GetWindowThreadProcessId(hwnd, None)
        user32.AttachThreadInput(me, game, True)
        user32.SetForegroundWindow(give_focus_to)
        user32.AttachThreadInput(me, game, False)
        refocused = True
    return moved, refocused


def start_in_background(exe: Path, args: list[str], settle: float = 5.0, watch: float = 20.0,
                        timeout: float = 120.0) -> None:
    """게임을 띄우되 쓰던 화면을 건드리지 않는다: 활성화 없이 시작하고, 창이 생기는 대로 화면 밖으로 보낸다.

    게임은 시작하면서 창을 다시 만들거나 가운데로 옮기고 포커스를 가져가기도 하므로, 잠잠해질 때까지(settle 초) 지켜본다.
    지켜보는 시간은 창이 뜬 뒤 watch 초로 제한한다 — 그 뒤에 창이 화면에 나와 있다면 사용자가 일부러 꺼낸 것일 수 있다.
    """
    previous = user32.GetForegroundWindow()
    info = subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=SW_SHOWNOACTIVATE)
    proc = subprocess.Popen([str(exe), *args], cwd=exe.parent, startupinfo=info,
                            env={**os.environ, "SRHOOK_CURSOR": "1"})      # move/click 이 알려 주는 마우스 위치를 듣게 한다
    print(f"시작: pid {proc.pid}")
    seen: set[int] = set()
    moves = refocuses = 0
    began = last_fix = time.monotonic()
    first_seen: float | None = None
    while proc.poll() is None:
        now = time.monotonic()
        if first_seen is None and now - began > timeout:
            break
        if first_seen is not None and (now - first_seen > watch or now - last_fix > settle):
            break
        win = game_window({proc.pid})
        if win:
            first_seen = first_seen or now
            moved, refocused = hide(win[0], previous)
            moves, refocuses = moves + moved, refocuses + refocused
            if moved or refocused or win[0] not in seen:
                last_fix = time.monotonic()
            if win[0] not in seen:
                seen.add(win[0])
                print(f"창: {win[1]!r} 클라이언트 {win[2][0]}x{win[2][1]}")
        time.sleep(0.1)
    if proc.poll() is not None:
        print("게임이 이미 끝났습니다")
    elif not seen:
        print("창이 아직 없습니다")
    else:
        focus = "게임이 포커스를 쥐고 있음" if user32.GetForegroundWindow() in seen else "포커스는 다른 창에 있음"
        print(f"창을 화면 밖에 둠 (창 옮김 {moves}회, 포커스 돌려줌 {refocuses}회, 마지막 조치는 시작 {last_fix - began:.0f}초 뒤, {focus})")


@contextmanager
def shared_cursor(hwnd: int):
    """게임 안의 훅 DLL 이 만든 공유 메모리. start 로 띄우지 않은 게임(SRHOOK_CURSOR 없음)이면 None."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, f"Local\\srkit.cursor.{pid.value}")
    view = kernel32.MapViewOfFile(handle, FILE_MAP_ALL_ACCESS, 0, 0, ctypes.sizeof(SharedCursor)) if handle else None
    try:
        yield SharedCursor.from_address(view) if view else None
    finally:
        if view:
            kernel32.UnmapViewOfFile(view)
        if handle:
            kernel32.CloseHandle(handle)


def point_cursor(hwnd: int, x: int, y: int) -> None:
    """게임이 읽는 마우스 위치를 클라이언트 좌표 (x, y) 로 둔다. 실제 마우스는 움직이지 않는다.

    게임은 툴팁·버튼 강조·지도 가장자리 스크롤에 쓸 마우스 위치를 메시지가 아니라 GetCursorPos 로 읽으므로,
    훅 DLL 이 이 좌표를 대신 돌려주게 한다(start 가 SRHOOK_CURSOR=1 로 띄운 게임만 듣는다).
    """
    with shared_cursor(hwnd) as cursor:
        if cursor is not None:
            cursor.hwnd, cursor.x, cursor.y, cursor.on = hwnd, x, y, 1
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, (y << 16) | (x & 0xFFFF))


def need_window() -> tuple[int, str, tuple[int, int]]:
    win = game_window()
    if not win:
        raise SystemExit("게임 창이 없습니다" + ("" if game_pids() else " (프로세스도 없음)"))
    hide(win[0])        # 게임이 창을 화면으로 되돌려 놓았으면 다시 밖으로 (포커스는 건드리지 않는다)
    return win


def main(argv: list[str]) -> int:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    cmd, *args = argv or ["status"]
    cfg = config.load()
    if cmd == "start":
        if game_pids():
            raise SystemExit("이미 실행 중입니다")
        start_in_background(cfg.game_dir / EXE, args or ["-window"])
    elif cmd == "status":
        pids, win = game_pids(), game_window()
        print(f"프로세스: {pids or '없음'}")
        if win:
            rect = wintypes.RECT()
            user32.GetWindowRect(win[0], ctypes.byref(rect))
            where = "화면 밖" if rect.left >= offscreen_x() else f"화면 안 ({rect.left},{rect.top})"
            focus = ", 포커스를 쥐고 있음" if user32.GetForegroundWindow() == win[0] else ""
            print(f"창: {win[1]!r} 클라이언트 {win[2][0]}x{win[2][1]}, {where}{focus}")
            with shared_cursor(win[0]) as cursor:
                if cursor is None:
                    print("가상 마우스: 없음 (start 로 띄운 게임이 아님)")
                else:
                    where = f"({cursor.x},{cursor.y})" if cursor.on else "꺼짐(실제 마우스 위치 사용)"
                    print(f"가상 마우스: {where}, 게임이 위치를 물은 횟수 {cursor.reads}")
        else:
            print("창: 없음")
    elif cmd == "show":
        win = game_window()
        if not win:
            raise SystemExit("게임 창이 없습니다")
        user32.SetWindowPos(win[0], HWND_TOP, 80, 60, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
        print("게임 창을 화면으로 가져왔습니다 (다음 shot·click·key 때 다시 화면 밖으로 갑니다)")
    elif cmd == "shot":
        hwnd, title, size = need_window()
        img = capture(hwnd, size)
        scale = float(args[1]) if len(args) > 1 else 1.0
        if scale != 1.0:
            img = img.resize((round(size[0] * scale), round(size[1] * scale)), Image.LANCZOS)
        img.save(args[0])
        lo, hi = img.convert("L").getextrema()
        print(f"{title!r} {size[0]}x{size[1]} → {args[0]} (밝기 {lo}–{hi}{', 빈 화면일 수 있음' if hi - lo < 8 else ''})")
    elif cmd == "click":
        hwnd, _, _ = need_window()
        pos = (int(args[1]) << 16) | (int(args[0]) & 0xFFFF)
        point_cursor(hwnd, int(args[0]), int(args[1]))
        time.sleep(0.15)
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, pos)
        time.sleep(0.08)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, pos)
        print(f"클릭 {args[0]},{args[1]}")
    elif cmd == "move":
        hwnd, _, _ = need_window()
        point_cursor(hwnd, int(args[0]), int(args[1]))
        print(f"이동 {args[0]},{args[1]}")
    elif cmd == "key":
        hwnd, _, _ = need_window()
        for name in args:
            vk = KEYS.get(name.upper()) or int(name, 0)
            user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
            time.sleep(0.05)
            user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
            time.sleep(0.1)
        print(f"키 {' '.join(args)}")
    elif cmd == "type":
        # 게임 입력란은 바이트 단위로 글자를 받는다: 한글은 게임 파일과 같은 SR-UTF8 바이트로 보낸다
        from srkit import srutf8
        hwnd, _, _ = need_window()
        for b in srutf8.encode(" ".join(args)):
            user32.PostMessageW(hwnd, WM_CHAR, b, 1)
            time.sleep(0.03)
        print(f"입력 {' '.join(args)!r}")
    elif cmd == "stop":
        for pid in game_pids():
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        print("종료")
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
