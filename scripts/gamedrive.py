"""게임을 띄워 창 내용을 캡처하고 입력을 보내는 검증용 드라이버.

    uv run python scripts/gamedrive.py start [게임 인자...]   # 기본 -window. 창을 활성화하지 않고 다른 창 뒤에 띄운다
    uv run python scripts/gamedrive.py status
    uv run python scripts/gamedrive.py shot out.png [배율]    # 게임 창의 클라이언트 영역만 캡처
    uv run python scripts/gamedrive.py click X Y              # 클라이언트 좌표(캡처 이미지의 원본 픽셀)
    uv run python scripts/gamedrive.py key VK [VK...]         # 가상 키 코드(16진/10진) 또는 이름(ESC, ENTER, SPACE)
    uv run python scripts/gamedrive.py stop

화면 전체가 아니라 게임 창만 PrintWindow 로 읽고, 입력도 게임 창에만 메시지로 보낸다
(실제 마우스·키보드와 다른 창은 건드리지 않는다). 그래서 게임 창이 다른 창에 가려져 있어도 된다 —
start 는 쓰던 창의 포커스를 뺏지 않도록 게임 창을 맨 뒤로 보낸다(최소화하면 그려지지 않으므로 최소화는 하지 않는다).
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from srkit import config  # noqa: E402

EXE = "SupremeRuler2030.exe"
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
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

SW_SHOWNOACTIVATE, HWND_BOTTOM = 4, 1
SWP_KEEP = 0x0001 | 0x0002 | 0x0010  # NOSIZE | NOMOVE | NOACTIVATE
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


def game_window() -> tuple[int, str, tuple[int, int]] | None:
    """게임 프로세스의 보이는 최상위 창 중 가장 큰 것: (hwnd, 제목, 클라이언트 크기)."""
    pids = set(game_pids())
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


def start_in_background(exe: Path, args: list[str], settle: float = 8.0, timeout: float = 120.0) -> None:
    """게임을 띄우되 쓰던 창을 가리지 않게 한다: 활성화 없이 시작하고, 창이 생기는 대로 맨 뒤로 보낸다."""
    previous = user32.GetForegroundWindow()
    info = subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=SW_SHOWNOACTIVATE)
    proc = subprocess.Popen([str(exe), *args], cwd=exe.parent, startupinfo=info)
    print(f"시작: pid {proc.pid}")
    seen: set[int] = set()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and game_pids():
        win = game_window()
        if win and win[0] not in seen:      # 시작 화면 → 본 창처럼 창이 바뀌면 다시 보낸다
            seen.add(win[0])
            user32.SetWindowPos(win[0], HWND_BOTTOM, 0, 0, 0, 0, SWP_KEEP)
            if previous and user32.GetForegroundWindow() == win[0]:
                user32.SetForegroundWindow(previous)
            print(f"창: {win[1]!r} 클라이언트 {win[2][0]}x{win[2][1]} (다른 창 뒤에 둠)")
            deadline = min(deadline, time.monotonic() + settle)
        time.sleep(0.5)
    if not game_pids():
        print("게임이 이미 끝났습니다")
    elif not seen:
        print("창이 아직 없습니다")


def need_window() -> tuple[int, str, tuple[int, int]]:
    win = game_window()
    if not win:
        raise SystemExit("게임 창이 없습니다" + ("" if game_pids() else " (프로세스도 없음)"))
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
        print(f"창: {win[1]!r} 클라이언트 {win[2][0]}x{win[2][1]}" if win else "창: 없음")
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
        user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, pos)
        time.sleep(0.15)
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, pos)
        time.sleep(0.08)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, pos)
        print(f"클릭 {args[0]},{args[1]}")
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
