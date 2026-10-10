"""게임을 띄워 창 내용을 캡처하고 입력을 보내는 검증용 드라이버.

    uv run python scripts/gamedrive.py start [게임 인자...]   # 기본 -window. 창을 화면 밖에 두고, 게임이 포커스를 가져가지 못하게 한다
    uv run python scripts/gamedrive.py start --               # 인자 없이 띄운다(Steam 이 띄울 때처럼. 창 크기·모드는 저장된 설정)
    uv run python scripts/gamedrive.py steam                  # Steam 을 거쳐 띄운다(사용자가 켜는 방식). 창은 뜨는 대로 화면 밖으로
    uv run python scripts/gamedrive.py guard [초]             # 게임이 스스로 다시 시작할 때 새 창도 화면 밖에 두도록 지켜본다
    uv run python scripts/gamedrive.py status
    uv run python scripts/gamedrive.py shot out.png [배율]    # 게임 창의 클라이언트 영역만 캡처
    uv run python scripts/gamedrive.py click X Y              # 클라이언트 좌표(캡처 이미지의 원본 픽셀)
    uv run python scripts/gamedrive.py move X Y               # 누르지 않고 마우스만 올린다(툴팁 확인)
    uv run python scripts/gamedrive.py wheel N [X Y]          # 마우스 휠 N칸(음수 = 아래로). 지도 확대·축소
    uv run python scripts/gamedrive.py key VK [VK...]         # 가상 키 코드(16진/10진), 이름(ESC, ENTER, SPACE), 글자(S), 조합(CTRL+SHIFT+S)
    uv run python scripts/gamedrive.py show                  # 화면 밖에 둔 게임 창을 화면으로 가져온다(직접 볼 때)
    uv run python scripts/gamedrive.py peek [지역 번호]       # 이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다(읽기만, JSON).
                                                              # 번호를 주면 플레이어 대신 그 지역의 국고 · 재고 · 기술 수준 · 여론을 읽고,
                                                              # 플레이어와 그 지역 사이의 관계 여섯 칸도 읽는다
    uv run python scripts/gamedrive.py research [지역 번호] [--out 파일]   # 그 지역(없으면 플레이어)이 보유한 기술 · 부대 설계,
                                                              # 플레이어의 연구 대기열, 모든 기술의 연구 기간의 합(읽기만, JSON).
                                                              # 앞뒤 두 번을 견줘 ToyBox 가 무엇을 바꿨고 무엇이 그대로인지 본다
    uv run python scripts/gamedrive.py stop                   # 이 도구가 띄운 게임만 끝낸다 (--all: 전부)

이 도구는 **자기가 띄운 게임만** 다룬다(build/gamedrive-pids.json 에 기록). 사용자가 직접 켠 게임에는 캡처·입력·종료를 하지 않는다.

화면 전체가 아니라 게임 창만 PrintWindow 로 읽고, 입력도 게임 창에만 메시지로 보낸다
(실제 마우스·키보드와 다른 창은 건드리지 않는다). 그래서 게임 창이 보이지 않아도 된다 —
start 는 게임 창을 화면 밖 맨 뒤에 두고, 띄우는 동안 앞 창을 잠가 게임이 포커스를 가져가지 못하게 한다.
그래도 가져가면(사용자가 그사이 다른 창을 눌러 잠금이 풀렸다) 쓰던 창으로 돌려준다.
shot·click·key 도 창이 화면에 나와 있으면 다시 밖으로 보낸다(최소화하면 그려지지 않으므로 최소화는 하지 않는다).
"""
from __future__ import annotations

import ctypes
import json
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
user32.GetShellWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.LockSetForegroundWindow.argtypes = [wintypes.UINT]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.MapViewOfFile.restype = ctypes.c_void_p
kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

FILE_MAP_ALL_ACCESS = 0xF001F
OWNED_FILE = "gamedrive-pids.json"   # build/ 아래: 이 도구가 띄운 게임의 프로세스 ID 와 시작 시각


class SharedCursor(ctypes.Structure):
    """훅 DLL 과 나눠 쓰는 메모리 — native/srhook/srhook.c 의 SRCURSOR 와 같아야 한다."""
    _fields_ = [("on", ctypes.c_long), ("x", ctypes.c_long), ("y", ctypes.c_long), ("reads", ctypes.c_long),
                ("hwnd", ctypes.c_ulonglong)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    """SendInput 에 넘기는 키 입력 하나(마우스 입력의 크기만큼 자리를 둔다)."""
    class _Body(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("body",)
    _fields_ = [("type", wintypes.DWORD), ("body", _Body)]


SW_SHOWNOACTIVATE, HWND_TOP, HWND_BOTTOM = 4, 0, 1
LSFW_LOCK, LSFW_UNLOCK = 1, 2
INPUT_KEYBOARD, KEYEVENTF_KEYUP = 1, 0x0002
VK_UNASSIGNED = 0xE8        # 어떤 글쇠에도 배정되지 않은 가상 키 — 눌러도 아무 일도 하지 않는다
SWP_NOSIZE, SWP_NOACTIVATE = 0x0001, 0x0010
SM_XVIRTUALSCREEN, SM_CXVIRTUALSCREEN = 76, 78
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x200, 0x201, 0x202, 0x100, 0x101, 0x102
WM_MOUSEWHEEL = 0x020A
KEYS = {"ESC": 0x1B, "ENTER": 0x0D, "SPACE": 0x20, "TAB": 0x09, "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27}
MODS = {"CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12}


def parse_key(name: str) -> tuple[list[int], int]:
    """ "CTRL+SHIFT+S" → ([0x11, 0x10], 0x53). 마지막이 누를 키, 그 앞은 누른 채로 둘 수정키다."""
    *mods, last = name.upper().split("+")
    unknown = [m for m in mods if m not in MODS]
    if unknown:
        raise SystemExit(f"모르는 수정키: {', '.join(unknown)} (쓸 수 있는 것: {', '.join(MODS)})")
    if last in KEYS:
        vk = KEYS[last]
    elif len(last) == 1 and last.isalpha():
        vk = ord(last)
    else:
        vk = int(last, 0)
    return [MODS[m] for m in mods], vk


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


def hide(hwnd: int) -> bool:
    """게임 창을 화면 밖 맨 뒤에 둔다(포커스는 건드리지 않는다). 옮겼으면 True."""
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if rect.left >= offscreen_x():
        return False
    user32.SetWindowPos(hwnd, HWND_BOTTOM, offscreen_x(), 0, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
    return True


def window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def focus_holder(pids: set[int]) -> int:
    """앞 창이 그 프로세스들(게임)의 창이면 그 창, 아니면 0.

    게임은 창이 여럿이다(본 창과 인트로 영상 창). 가장 큰 창만 보면, 영상 창이 떠 있는 동안 본 창이 쥔 포커스를 놓친다.
    """
    hwnd = user32.GetForegroundWindow()
    return hwnd if hwnd and window_pid(hwnd) in pids else 0


def give_focus(target: int) -> None:
    """앞 창을 target 으로 옮겨 달라고 한다(됐는지는 부르는 쪽이 focus_holder 로 본다).

    다른 프로세스의 창이 앞 창일 때 Windows 는 "마지막 입력을 낸 프로세스"에게만 앞 창을 바꾸게 한다. 배정되지 않은 가상 키를
    눌렀다 떼어 그 자격을 얻는다 — 그 입력은 앞 창(게임)에 가고 아무 일도 하지 않는다. 앞 창의 스레드에 입력을 붙이는
    방법(AttachThreadInput)은 듣지 않았다 [확인: 실행, 2026-10-10 — docs/04 의 "포커스"].
    """
    tap = (INPUT * 2)(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_UNASSIGNED, 0, 0, 0, 0)),
                      INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_UNASSIGNED, 0, KEYEVENTF_KEYUP, 0, 0)))
    user32.SendInput(2, tap, ctypes.sizeof(INPUT))
    user32.SetForegroundWindow(target)


@contextmanager
def foreground_locked():
    """게임이 뜨면서 앞 창이 되는 것을 막는다(LockSetForegroundWindow). 걸었으면 True 를 내주고, 끝날 때 푼다.

    이 도구를 띄운 앱(예: Claude 데스크톱)이 앞 창일 때 띄운 게임은 앞 창이 될 자격을 물려받아, 뜨자마자(0.2초) 포커스를 가져간다.
    그 자격이 있을 때만 이 잠금이 걸리고, 자격이 없으면(다른 앱이 앞 창이다) 게임도 포커스를 가져가지 못한다
    [확인: 실행, 2026-10-10 — docs/04 의 "포커스"]. 사용자가 Alt 를 누르거나 다른 창을 누르면 Windows 가 잠금을 푼다 —
    그 뒤에 게임이 포커스를 가져가면 keep_hidden 이 돌려준다.
    """
    locked = bool(user32.LockSetForegroundWindow(LSFW_LOCK))
    try:
        yield locked
    finally:
        if locked:
            user32.LockSetForegroundWindow(LSFW_UNLOCK)


def keep_hidden(pids, previous: int, settle: float = 5.0, watch: float = 20.0, timeout: float = 120.0) -> None:
    """게임 창이 생기는 대로 화면 밖으로 보내고, 게임이 가져간 포커스를 previous 창에 돌려준다. pids() 는 게임 프로세스 ID 집합.

    게임은 시작하면서 창을 다시 만들거나 가운데로 옮기고 포커스를 가져가기도 하므로, 잠잠해질 때까지(settle 초) 지켜본다.
    지켜보는 시간은 창이 뜬 뒤 watch 초로 제한한다 — 그 뒤에 창이 화면에 나와 있다면 사용자가 일부러 꺼낸 것일 수 있다.
    창이 timeout 초 안에 생기지 않으면 그만둔다.
    """
    seen: set[int] = set()
    moves = returned = stuck = 0
    began = last_fix = time.monotonic()
    first_seen: float | None = None
    while True:
        now = time.monotonic()
        if first_seen is None and now - began > timeout:
            break
        if first_seen is not None and (now - first_seen > watch or now - last_fix > settle):
            break
        running = pids()
        if first_seen is not None and not running:
            break
        win = game_window(running) if running else None
        if win:
            first_seen = first_seen or now
            moved = hide(win[0])
            moves += moved
            holder = focus_holder(running)
            if holder:
                # 쓰던 창이 없었거나 그새 닫혔으면(예: Steam 의 실행 안내 창) 바탕 화면에라도 넘긴다 — 보이지 않는 게임이 키 입력을 받지 않게
                usable = previous and user32.IsWindow(previous) and window_pid(previous) not in running
                give_focus(previous if usable else user32.GetShellWindow())
                if focus_holder(running):
                    stuck += 1
                else:
                    returned += 1
            if moved or holder or win[0] not in seen:
                last_fix = time.monotonic()
            if win[0] not in seen:
                seen.add(win[0])
                print(f"창: {win[1]!r} 클라이언트 {win[2][0]}x{win[2][1]}")
        time.sleep(0.1)
    if not seen:
        print("게임 창이 나타나지 않았습니다")
    elif not pids():
        print("게임이 이미 끝났습니다")
    else:
        focus = "게임이 포커스를 쥐고 있음" if focus_holder(pids()) else "포커스는 다른 창에 있음"
        failed = f", 돌려주지 못함 {stuck}회" if stuck else ""
        print(f"창을 화면 밖에 둠 (창 옮김 {moves}회, 포커스 돌려줌 {returned}회{failed}, 마지막 조치는 시작 {last_fix - began:.0f}초 뒤, {focus})")


def start_in_background(cfg: config.Config, exe: Path, args: list[str]) -> None:
    """게임을 띄우되 쓰던 화면을 건드리지 않는다: 활성화 없이 시작하고, 창이 생기는 대로 화면 밖으로 보낸다."""
    previous = user32.GetForegroundWindow()
    info = subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=SW_SHOWNOACTIVATE)
    with foreground_locked() as locked:
        proc = subprocess.Popen([str(exe), *args], cwd=exe.parent, startupinfo=info,
                                env={**os.environ, "SRHOOK_CURSOR": "1"})  # move/click 이 알려 주는 마우스 위치를 듣게 한다
        record_owned(cfg, [proc.pid])
        print(f"시작: pid {proc.pid} (앞 창 잠금 {'걸림' if locked else '걸리지 않음 — 이 도구를 띄운 앱이 앞 창이 아니다'})")
        keep_hidden(lambda: {proc.pid} if proc.poll() is None else set(), previous)


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


def started_at(pid: int) -> int:
    """프로세스가 시작된 시각(FILETIME). 프로세스 ID 는 재사용되므로 '같은 프로세스'인지 가릴 때 함께 본다."""
    handle = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return 0
    times = [wintypes.FILETIME() for _ in range(4)]
    ok = kernel32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times))
    kernel32.CloseHandle(handle)
    return (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime) if ok else 0


def owned_pids(cfg: config.Config) -> set[int]:
    """이 도구가 띄운 게임 중 아직 살아 있는 것. 사용자가 직접 켠 게임은 여기에 없다."""
    try:
        recorded = json.loads((cfg.build_dir / OWNED_FILE).read_text())
    except (OSError, ValueError):
        return set()
    return {int(pid) for pid, began in recorded.items() if began and started_at(int(pid)) == began} & set(game_pids())


def record_owned(cfg: config.Config, pids) -> None:
    cfg.build_dir.mkdir(exist_ok=True)
    keep = {pid: started_at(pid) for pid in owned_pids(cfg) | set(pids)}
    (cfg.build_dir / OWNED_FILE).write_text(json.dumps({str(pid): began for pid, began in keep.items() if began}))


def not_ours() -> str:
    return "실행 중인 게임은 이 도구가 띄운 것이 아닙니다 — 사용자가 켠 게임일 수 있어 건드리지 않습니다"


def need_window(cfg: config.Config) -> tuple[int, str, tuple[int, int]]:
    """이 도구가 띄운 게임의 창. 사용자가 켠 게임은 캡처도 입력도 하지 않는다(창을 화면 밖으로 옮기게 되므로)."""
    mine = owned_pids(cfg)
    if not mine:
        raise SystemExit(not_ours() if game_pids() else "게임 창이 없습니다 (프로세스도 없음)")
    win = game_window(mine)
    if not win:
        raise SystemExit("게임 창이 없습니다")
    hide(win[0])        # 게임이 창을 화면으로 되돌려 놓았으면 다시 밖으로 (포커스는 건드리지 않는다)
    return win


def peek_more(read, more: dict[str, int], player: int, me: int, who: int) -> dict:
    """더 쓰는 값(기술 수준 · 세계 시장 여론 · 관계)을 읽는다(읽기만). 못 찾은 묶음(자리 0)의 것은 결과에 없다.

    read(주소, 형식) 은 값 하나를 읽는 함수, more 는 srkit.toybox.locate 가 찾은 자리. who 는 값을 읽을 지역 객체,
    player 는 플레이어의 지역 객체, me 는 플레이어의 인덱스다. who 가 플레이어가 아니면 둘 사이의 관계도 읽는다:
    mine 은 플레이어 객체의 표에서 그 지역의 칸, theirs 는 그 지역 객체의 표에서 플레이어의 칸 — 저마다 [관계 표 1, 관계 표 2, 전쟁 명분].
    """
    out: dict = {}
    if more["tech"]:
        out["tech"] = read(who + more["tech"], "<f")
    if more["opinion0"]:
        out["opinion"] = [read(who + more[name], "<f") for name in ("opinion0", "opinion1", "opinion2")]
    if more["relation0"] and who != player:
        them = read(who + 4, "<H")
        tables = ("relation0", "relation1", "casus")
        out["relations"] = {"mine": [read(player + more[name] + 4 * them, "<f") for name in tables],
                            "theirs": [read(who + more[name] + 4 * me, "<f") for name in tables]}
    return out


def peek_game(cfg: config.Config, number: int | None = None) -> dict:
    """이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 것을 읽는다(읽기만). 주소는 srkit locate 와 같은 방법(서명)으로 찾는다.

    ToyBox 의 창에 보이는 값이 아니라 게임의 메모리 그 자체다 — ToyBox 가 쓴 값과 치트 허용 비트를 따로 확인하는 데 쓴다.
    number 를 주면 국고 · 재고 · 기술 수준 · 여론을 플레이어 대신 그 번호의 지역 객체에서 읽고(지역 표에서 찾는다. 결과의 region 이
    그 번호다), 플레이어와 그 지역 사이의 관계(relations)도 읽는다 — 플레이하는 나라를 바꾼 뒤 앞 나라의 값이 그대로인지,
    관계의 단추가 양쪽 객체에 썼는지 볼 때 쓴다.
    """
    import struct

    from srkit import toybox

    mine = owned_pids(cfg)
    if not mine:
        raise SystemExit(not_ours() if game_pids() else "게임이 떠 있지 않습니다")
    found = toybox.locate(cfg)
    if found.state is None or found.values is None:
        raise SystemExit(f"주소를 찾지 못했습니다: {found.state_why or found.values_why}")
    state, values, legacy = found.state, found.values, found.legacy
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    process = kernel32.OpenProcess(0x0410, False, sorted(mine)[0])      # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if not process:
        raise SystemExit("게임 프로세스를 열 수 없습니다")
    try:
        module, needed = ctypes.c_void_p(), wintypes.DWORD()
        if not psapi.EnumProcessModules(process, ctypes.byref(module), ctypes.sizeof(module), ctypes.byref(needed)):
            raise SystemExit("게임의 모듈 목록을 읽을 수 없습니다")
        base = module.value                                             # 첫 모듈이 실행 파일이다

        def read(address: int, fmt: str):
            buf, got = ctypes.create_string_buffer(struct.calcsize(fmt)), ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(process, address, buf, len(buf), ctypes.byref(got))
            return struct.unpack(fmt, buf.raw)[0] if ok and got.value == len(buf) else None

        out = {"program": read(base + state["program_state"], "<i"), "mode": read(base + state["mode_state"], "<i"),
               "multiplayer": read(base + state["multiplayer"], "<B"), "player_index": read(base + state["player_index"], "<i")}
        if legacy is not None:
            out["cheats_allowed"] = int(bool((read(base + legacy["options"], "<I") or 0) & 0x40))
        player = read(base + state["player_pointer"], "<Q")
        out["in_game"] = bool(out["mode"] == 2 and out["program"] == 1 and player)
        if out["in_game"]:
            world = read(base + values["world_pointer"], "<Q")
            out["player"] = read(player + 8, "<H")
            who = player
            if number is not None:                                      # 지역 표(인덱스 1 … 지역 수)에서 그 번호의 객체를 찾는다
                count = min(read(base + state["region_count"], "<i") or 0, 1023)
                table = (read(base + state["region_table"] + 8 * index, "<Q") for index in range(1, count + 1))
                who = next((pointer for pointer in table if pointer and read(pointer + 8, "<H") == number), None)
                if who is None:
                    raise SystemExit(f"그 번호의 지역이 지역 표에 없습니다: {number}")
                out["region"] = number
            out["treasury"] = read(who + values["treasury"], "<d")
            out["stock"] = [read(who + values["stock_first"] + values["stock_step"] * i, "<f") for i in range(toybox.STOCK_SLOTS)]
            out["used"] = [bool((read(world + values["used_first"] + values["used_step"] * i, "<f") or 0) > 0)
                           for i in range(toybox.STOCK_SLOTS)] if world else None
            out.update(peek_more(read, found.more, player, out["player_index"], who))
        return out
    finally:
        kernel32.CloseHandle(process)


RESEARCH_BUILD = 0x695377B6     # 아래 보정 표의 자리를 본 빌드(21347933)의 PE TimeDateStamp
# 그 빌드에서만 아는 자리: 게임의 "효과를 다시 셈"이 지역마다 쌓는 보정 표 — (세계 객체 안의 자리, 지역마다의 간격, float 칸의 수).
# 검증에만 쓰는 상수다. ToyBox 는 이 자리를 모르고 건드리지 않는다(docs/11-game-internals.md)
EFFECT_TABLES = {"mul": (0x5456A8, 0x320, 200), "add": (0x60D6A8, 0x2C0, 176)}
EFFECT_CELL = 0x14D38           # 지역 객체 안의 한 칸(dword) — 같은 함수가 0 으로 되돌리고 다시 쌓는다
TECH_DAYS = 0x30                # 기술 레코드의 연구 기간(float). ToyBox 는 읽지도 쓰지도 않는다 — "그대로인가"만 본다
MAX_NODES = 1 << 20             # 연구 목록의 노드의 상한(ToyBox 의 스냅숏과 같다). 게임은 노드를 지우지 않는다 — 오래 한 판의 목록은 길다


def peek_research(read, research: dict[str, int], shape: dict[str, int], base: int, index: int, me: int,
                  region: int | None = None) -> dict:
    """연구의 표와 목록을 읽는다(읽기만). ToyBox 의 창이 아니라 게임의 메모리 그 자체다.

    read(주소, 바이트 수) 는 그만큼을 읽어 주는 함수(못 읽으면 None), research 는 srkit.toybox.locate 가 찾은 자리,
    shape 는 표의 꼴(srkit.toybox.research_shape), base 는 실행 파일이 올라온 주소다. index 는 보유를 볼 지역의 인덱스, me 는 플레이어의 인덱스.
    region 은 그 지역의 객체의 주소 — 주면 그 지역의 보정 표(effects)도 읽는다(RESEARCH_BUILD 에서만 부른다).

    결과: techs · designs(그 지역이 보유한 번호들), used(쓰는 항목의 수), unhoused(보유 묶음이 없는 항목의 수 — 아무도 보유한 적이 없다),
    queue(플레이어의 연구 목록: [종류(1 기술, 2 부대 설계), 번호, 깃발 1, 깃발 2] — 깃발은 16진 글), days(모든 기술의 연구 기간의 합).
    """
    import struct

    def chunk(address: int, size: int) -> bytes:
        raw = read(address, size)
        if raw is None:
            raise SystemExit(f"게임의 메모리를 읽을 수 없습니다: {address:#x} 부터 {size}바이트")
        return raw

    def value(address: int, fmt: str):
        return struct.unpack(fmt, chunk(address, struct.calcsize(fmt)))[0]

    def owned(pointer: int) -> bool:
        return bool(pointer) and bool(value(pointer + index // 8, "<B") >> index % 8 & 1)

    out: dict = {"index": index, "techs": [], "designs": [], "used": {"techs": 0, "designs": 0},
                 "unhoused": {"techs": 0, "designs": 0}, "queue": [], "days": 0.0}
    tables = (("techs", "tech_table", "tech_count", shape["tech_size"], shape["tech_kind"], "<B", shape["tech_owners"]),
              ("designs", "design_table", "design_count", shape["design_size"], shape["design_name"], "<Q", shape["design_owners"]))
    for name, table, count, size, alive, alive_fmt, owners in tables:
        start, slots = value(base + research[table], "<Q"), value(base + research[count], "<i")
        if not start or not 2 <= slots <= 65536:
            raise SystemExit(f"연구의 표가 없거나 자리 수가 범위 밖입니다: {name} {slots}")
        records = chunk(start, slots * size)                # 표는 한 번에 읽는다(부대 설계는 22000 × 0x168)
        for number in range(1, slots):
            at = number * size
            if not struct.unpack_from(alive_fmt, records, at + alive)[0]:
                continue                                    # 빈 자리
            pointer = struct.unpack_from("<Q", records, at + owners)[0]
            out["used"][name] += 1
            out["unhoused"][name] += 0 if pointer else 1
            if owned(pointer):
                out[name].append(number)
            if name == "techs":
                out["days"] += struct.unpack_from("<f", records, at + TECH_DAYS)[0]
    node = value(base + research["world"] + research["lists"] + shape["list_step"] * me, "<Q")
    seen: set[int] = set()
    while node:
        if node in seen or len(seen) >= MAX_NODES:          # 같은 노드에 다시 왔다(순환)
            raise SystemExit("연구 목록이 끝나지 않습니다")
        seen.add(node)
        first, second = value(node + shape["node_flags"], "<I"), value(node + shape["node_flags"] + 4, "<I")
        out["queue"].append([value(node + shape["node_kind"], "<B"), value(node + shape["node_id"], "<i"), f"{first:08x}", f"{second:08x}"])
        node = value(node + shape["node_next"], "<Q")
    if region is not None:
        world = base + research["world"]
        out["effects"] = {name: list(struct.unpack(f"<{cells}f", chunk(world + start + step * index, 4 * cells)))
                          for name, (start, step, cells) in EFFECT_TABLES.items()}
        out["effects"]["cell"] = value(region + EFFECT_CELL, "<I")
    return out


def research_game(cfg: config.Config, number: int | None = None) -> dict:
    """이 도구가 띄운 게임의 메모리에서 연구를 읽는다(peek_research). number 를 주면 플레이어 대신 그 번호의 지역이 보유한 것을 읽는다."""
    import struct

    from srkit import toybox

    mine = owned_pids(cfg)
    if not mine:
        raise SystemExit(not_ours() if game_pids() else "게임이 떠 있지 않습니다")
    found = toybox.locate(cfg)
    if found.state is None or found.research is None:
        raise SystemExit(f"주소를 찾지 못했습니다: {found.state_why or found.research_why}")
    state, shape = found.state, toybox.research_shape(toybox.library(cfg))
    exe = (cfg.game_dir / EXE).read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    process = kernel32.OpenProcess(0x0410, False, sorted(mine)[0])      # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if not process:
        raise SystemExit("게임 프로세스를 열 수 없습니다")
    try:
        module, needed = ctypes.c_void_p(), wintypes.DWORD()
        if not psapi.EnumProcessModules(process, ctypes.byref(module), ctypes.sizeof(module), ctypes.byref(needed)):
            raise SystemExit("게임의 모듈 목록을 읽을 수 없습니다")
        base = module.value                                             # 첫 모듈이 실행 파일이다

        def read(address: int, size: int):
            buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(process, ctypes.c_void_p(address), buf, size, ctypes.byref(got))
            return buf.raw if ok and got.value == size else None

        def value(address: int, fmt: str):
            raw = read(address, struct.calcsize(fmt))
            return struct.unpack(fmt, raw)[0] if raw is not None else None

        player, me = value(base + state["player_pointer"], "<Q"), value(base + state["player_index"], "<i")
        if not (value(base + state["mode_state"], "<i") == 2 and value(base + state["program_state"], "<i") == 1 and player):
            raise SystemExit("게임이 진행 중이 아닙니다")
        who, index = player, me
        if number is not None:                                          # 지역 표(인덱스 1 … 지역 수)에서 그 번호의 객체를 찾는다
            count = min(value(base + state["region_count"], "<i") or 0, 1023)
            table = ((i, value(base + state["region_table"] + 8 * i, "<Q")) for i in range(1, count + 1))
            index, who = next(((i, pointer) for i, pointer in table if pointer and value(pointer + 8, "<H") == number), (0, None))
            if who is None:
                raise SystemExit(f"그 번호의 지역이 지역 표에 없습니다: {number}")
        out = {"player": value(player + 8, "<H"), "region": value(who + 8, "<H")}
        out.update(peek_research(read, found.research, shape, base, index, me, who if stamp == RESEARCH_BUILD else None))
        return out
    finally:
        kernel32.CloseHandle(process)


@contextmanager
def held(hwnd: int, mods: list[int]):
    """게임 스레드의 키 상태표에 수정키를 눌린 것으로 적어 둔다(GetKeyState 가 읽는 값). 실제 키보드는 건드리지 않는다.

    메시지만 보내면 게임이 Ctrl·Shift 를 눌린 것으로 읽지 않는다. 게임이 GetAsyncKeyState 로 읽는다면 이 방법도 안 된다.
    """
    if not mods:
        yield
        return
    me, target = kernel32.GetCurrentThreadId(), user32.GetWindowThreadProcessId(hwnd, None)
    if not user32.AttachThreadInput(me, target, True):
        # 붙지 못한 채 보내면 이 도구의 상태표만 바뀌고 게임에는 맨 키가 간다(CTRL+SHIFT+S 가 S = 보급 지도가 된다)
        raise SystemExit(f"게임의 입력 스레드에 붙지 못했습니다 (Windows 오류 {ctypes.get_last_error()}) — "
                         "수정키 없이 맨 키만 전달되므로 조합키를 보내지 않았습니다")
    try:
        state = (ctypes.c_ubyte * 256)()
        user32.GetKeyboardState(state)
        saved = bytes(state)
        try:
            for vk in mods:
                state[vk] |= 0x80
                user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
            user32.SetKeyboardState(state)
            yield
        finally:
            # 본문이 예외로 끝나도(Ctrl+C, 시간 초과) 화면 밖 게임에 수정키가 눌린 채 남지 않게 한다
            for vk in reversed(mods):
                user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
            try:
                time.sleep(0.2)     # 게임이 보낸 메시지를 다 읽을 때까지 눌린 상태를 둔다
            finally:
                user32.SetKeyboardState((ctypes.c_ubyte * 256).from_buffer_copy(saved))
    finally:
        user32.AttachThreadInput(me, target, False)


def main(argv: list[str]) -> int:
    # 파이프로 받으면 표준 출력이 CP949 가 되어 shot 의 "–" 에서 죽는다. srkit 명령처럼 UTF-8 로 고정한다
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    cmd, *args = argv or ["status"]
    cfg = config.load()
    if cmd in ("start", "steam") and game_pids():
        raise SystemExit("이미 실행 중입니다" + ("" if owned_pids(cfg) else f" — {not_ours()}"))
    if cmd == "start":
        # 인자가 없으면 -window. 정말 인자 없이(Steam 이 띄우는 것처럼) 띄우려면 "--" 하나만 준다
        start_in_background(cfg, cfg.game_dir / EXE, [] if args == ["--"] else args or ["-window"])
    elif cmd == "guard":
        # 이 도구가 띄운 게임이 스스로 다시 시작할 때(해상도 변경 뒤 Steam 을 거쳐 재실행) 새 창도 화면 밖에 두고 이어받는다.
        # 재시작을 일으킨 조작 바로 뒤에만 쓴다 — 이 명령이 도는 동안 뜬 게임은 이 도구의 것으로 친다
        seconds = float(args[0]) if args else 40.0
        with foreground_locked():
            keep_hidden(lambda: set(game_pids()), user32.GetForegroundWindow(), settle=seconds, watch=seconds)
        record_owned(cfg, game_pids())
    elif cmd == "steam":
        # 사용자가 켜는 방식 그대로(Steam 을 거쳐) 띄운다. 가상 마우스는 못 쓴다(Steam 이 띄운 프로세스라 환경 변수를 줄 수 없다)
        previous = user32.GetForegroundWindow()     # Steam 의 안내 창이 뜨기 전에, 쓰던 창을 기억해 둔다
        appid = (cfg.game_dir / "steam_appid.txt").read_text().strip()
        with foreground_locked():
            os.startfile(f"steam://rungameid/{appid}")
            print(f"Steam 으로 실행 요청: {appid}")
            keep_hidden(lambda: set(game_pids()), previous, timeout=float(args[0]) if args else 90.0)
        record_owned(cfg, game_pids())
    elif cmd == "status":
        pids, mine = game_pids(), owned_pids(cfg)
        win = game_window(set(pids))
        print("프로세스: " + (", ".join(f"{pid}{'' if pid in mine else ' (이 도구가 띄운 것 아님)'}" for pid in pids) or "없음"))
        if win:
            rect = wintypes.RECT()
            user32.GetWindowRect(win[0], ctypes.byref(rect))
            where = "화면 밖" if rect.left >= offscreen_x() else f"화면 안 ({rect.left},{rect.top})"
            focus = ", 포커스를 쥐고 있음" if focus_holder(set(pids)) else ""
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
        mine = owned_pids(cfg)
        win = game_window(mine) if mine else None
        if not win:
            raise SystemExit(not_ours() if game_pids() else "게임 창이 없습니다")
        user32.SetWindowPos(win[0], HWND_TOP, 80, 60, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
        print("게임 창을 화면으로 가져왔습니다 (다음 shot·click·key 때 다시 화면 밖으로 갑니다)")
    elif cmd == "shot":
        hwnd, title, size = need_window(cfg)
        img = capture(hwnd, size)
        scale = float(args[1]) if len(args) > 1 else 1.0
        if scale != 1.0:
            img = img.resize((round(size[0] * scale), round(size[1] * scale)), Image.LANCZOS)
        img.save(args[0])
        lo, hi = img.convert("L").getextrema()
        print(f"{title!r} {size[0]}x{size[1]} → {args[0]} (밝기 {lo}–{hi}{', 빈 화면일 수 있음' if hi - lo < 8 else ''})")
    elif cmd == "click":
        hwnd, _, _ = need_window(cfg)
        pos = (int(args[1]) << 16) | (int(args[0]) & 0xFFFF)
        point_cursor(hwnd, int(args[0]), int(args[1]))
        time.sleep(0.15)
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, pos)
        time.sleep(0.08)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, pos)
        print(f"클릭 {args[0]},{args[1]}")
    elif cmd == "move":
        hwnd, _, _ = need_window(cfg)
        point_cursor(hwnd, int(args[0]), int(args[1]))
        print(f"이동 {args[0]},{args[1]}")
    elif cmd == "wheel":
        # wheel N [X Y]: 마우스 휠 N칸(양수 = 위로 굴림). 지도 확대·축소 확인용
        hwnd, _, size = need_window(cfg)
        x, y = (int(args[1]), int(args[2])) if len(args) > 2 else (size[0] // 2, size[1] // 2)
        point_cursor(hwnd, x, y)
        screen = wintypes.POINT(x, y)
        user32.ClientToScreen(hwnd, ctypes.byref(screen))
        for _ in range(abs(int(args[0]))):
            delta = 120 if int(args[0]) > 0 else -120
            user32.PostMessageW(hwnd, WM_MOUSEWHEEL, (delta & 0xFFFF) << 16, ((screen.y & 0xFFFF) << 16) | (screen.x & 0xFFFF))
            time.sleep(0.15)
        print(f"휠 {args[0]} @ {x},{y}")
    elif cmd == "key":
        hwnd, _, _ = need_window(cfg)
        for name in args:
            mods, vk = parse_key(name)
            with held(hwnd, mods):
                user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
                time.sleep(0.05)
                user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
                time.sleep(0.1)
        print(f"키 {' '.join(args)}")
    elif cmd == "type":
        # 게임 입력란은 바이트 단위로 글자를 받는다: 한글은 게임 파일과 같은 SR-UTF8 바이트로 보낸다
        from srkit import srutf8
        hwnd, _, _ = need_window(cfg)
        for b in srutf8.encode(" ".join(args)):
            user32.PostMessageW(hwnd, WM_CHAR, b, 1)
            time.sleep(0.03)
        print(f"입력 {' '.join(args)!r}")
    elif cmd == "peek":
        print(json.dumps(peek_game(cfg, int(args[0]) if args else None), ensure_ascii=False))
    elif cmd == "research":
        # research [지역 번호] [--out 파일]: 보유한 부대 설계가 수천 줄이라, 파일을 주면 거기에 적고 화면에는 수만 보인다
        target = args[args.index("--out") + 1] if "--out" in args else None
        numbers = [a for a in args if a not in ("--out", target)]
        got = research_game(cfg, int(numbers[0]) if numbers else None)
        if target is None:
            print(json.dumps(got, ensure_ascii=False))
        else:
            Path(target).write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
            print(f"{target}: 지역 {got['region']} — 기술 {len(got['techs'])}개 · 부대 설계 {len(got['designs'])}개 보유, "
                  f"대기열 {len(got['queue'])}개, 연구 기간의 합 {got['days']:g}")
    elif cmd == "stop":
        # 이 도구가 띄운 게임만 끝낸다. 사용자가 켠 게임까지 끝내려면 --all 을 분명히 준다
        mine, everything = owned_pids(cfg), set(game_pids())
        for pid in (everything if args == ["--all"] else mine):
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        left = set() if args == ["--all"] else everything - mine
        print("종료" + (f" (이 도구가 띄우지 않은 게임 {sorted(left)} 은 그대로 둠)" if left else ""))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
