"""ToyBox 의 화면 · 입력 끼어들기를 게임 없이 새 프로세스에서 밟아 본다.

실제 Direct3D 장치와 swap chain, 가짜 "게임 창"을 만들고, 훅 DLL 사본을 불러 ToyBox 가 끼어들게 한 뒤 게임이 하듯
Present 를 부르고 창 메시지를 보낸다. Steam 오버레이 같은 다른 훅은 가짜로 흉내 낸다.

    python toybox_overlay_probe.py <훅 DLL 사본> <mode>

다른 훅과 함께 돌 때 (출력 "calls=<가짜 훅이 불린 횟수> hr=<마지막 반환값> plain=<아무 훅도 없을 때의 반환값>"):
    plain            다른 훅이 없다
    before           가상 함수 표의 칸에 다른 훅이 먼저 있다
    rehook           다른 훅이 표의 칸에 ToyBox 위로 다시 끼어든다
    inline           진짜 Present 의 머리에 점프가 심겨 있고, 그 훅이 ToyBox 의 함수를 원래 함수로 부른다
    steam            Steam 오버레이가 실제로 한 배치: 진짜 Present 와 ToyBox 함수 양쪽 머리에 점프, 원본은 ToyBox 함수의 트램펄린
    inline_resize    ResizeBuffers 의 머리에 점프
    inline_present1  Present1 의 머리에 점프
끼어들면 안 될 때 (출력 "hooked" 또는 "nohook"):
    longpatch        진짜 Present 의 머리가 16바이트 고쳐져 있다(깨끗한 진입로가 덮는 14바이트보다 길다)
    longpatch_resize 진짜 ResizeBuffers 의 머리만 그렇게 고쳐져 있다 — Present 에도 끼어들면 안 된다(그리기만 하고 뒷면을 못 놓는다)
    stale            올라와 있는 dxgi.dll 이 디스크의 파일과 다른 판이다
그리기와 입력 (출력은 "이름=값" 들):
    draw_resize      창을 켜고 그린 뒤 ResizeBuffers · Present1 을 부른다
    input            단축키, 창 위 · 밖의 누름, 치트를 넣는 동안의 실제 글쇠, 게임이 받은 글
    scale            그리는 크기가 창의 절반일 때 창 위 · 밖의 누름
게임 상태에 따른 단추 (출력 "button=<창 위 누름이 게임에 갔는가> text=<게임이 받은 글>"):
    gate_menu        ToyBox 가 게임을 읽을 수 있고 메뉴에 있다 — 단추가 꺼져 있다
    gate_leave       게임 안에서 단추를 누른 직후(실행되기 전) 메뉴로 나갔다 — 실행하지 않는다
    gate_typing      게임 안, 글쇠 방식(SRTOYBOX_DIRECT=0) — 1단계처럼 글쇠가 간다
직접 실행 (출력 "lines=<명령 처리 함수가 받은 줄들. 빈칸은 _, 줄 사이는 |> text=<게임이 받은 글>"):
    direct           게임 안에서 단추를 세 번 — 둘째 뒤에 치트 허용이 꺼진다(메뉴에 나갔다 온 것처럼)
    direct_fault     명령 처리 함수가 잘못된 주소에 쓴다 — ToyBox 가 잡고, 그 뒤로는 아무것도 실행하지 않는다
    direct_off       SRTOYBOX_DIRECT=0 — 명령 처리 함수를 부르지 않고 글쇠를 넣는다
    direct_menu      명령 처리 함수를 부를 수 있지만 게임 밖이다 — 부르지 않는다
    direct_read_off  같은 상황에서 SRTOYBOX_READ=0 — ToyBox 가 게임을 읽지 않는다: 단추가 켜져 있고 글쇠를 넣는다(1단계처럼)
명령 처리 함수가 일하는 도중에 ToyBox 로 되돌아올 때 (출력 "inside=<그 안에서 한 일의 결과> deepest=<명령 처리 함수가 겹쳐 불린 깊이> lines=… text=…"):
    reenter_timer    그 안에서 ToyBox 의 타이머가 다시 온다(게임이 메시지를 돌린다) — 대기열의 다음 명령을 그 안에서 시작하면 안 된다
    reenter_keyup    그 안에서 실제 키보드의 뗌이 온다
    reenter_present  그 안에서 화면을 한 번 내보낸다
ToyBox 가 부른 함수 안에서 난 예외를 위에서 잡을 때 (출력 "caught=<잡았는가> drawn=<그 뒤에 설정 창을 그렸는가>"):
    present_fault    진짜 Present 자리의 함수가 한 번 죽는다
돈 탭 — 내장 치트를 거치지 않고 국고를 고친다 (출력은 JSON 한 줄):
    money            게임 안에서 빠른 단추 다섯과 입력란(1234)의 더하기 · 빼기 · 이 값으로를 누른다
    money_menu       메뉴에 있다 — 단추가 꺼져 있다
    money_leave      단추를 누른 뒤 쓰기 전에 게임에서 나간다 — 쓰지 않고 버린다. 돌아오면 다시 된다
    money_write_off  SRTOYBOX_WRITE=0 — 까닭 한 줄만 보인다
    money_notfound   값의 자리를 찾지 못한 게임 — 〃
    money_unread     SRTOYBOX_READ=0 — 〃
    money_unreadable 게임 안인데 재고 칸 하나가 수가 아니다(보지 못한 구성의 판) — 〃
    money_fail       플레이어 지역 객체가 읽기 전용 쪽에 있다 — 쓰기가 실패하고 탭이 꺼진다
    money_reenter    옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 온다 — 그 안에서는 쓰지 않는다
설정 창에 보이는 글 (출력은 JSON 한 줄. 보이지 않는 글은 "-"):
    confirm          "외교·영토" 탭에서 폴란드를 고르고 스크롤을 내려 맨 아래의 "이 나라로 플레이"를 두 번 누른다
    confirm_fault    같은 탭에서 직접 실행이 죽는다 — 경고가 스크롤을 내려도 보인다
    hints            메뉴에 있을 때와 게임 안에 있을 때의 바닥 안내
    leave            직접 실행: 단추를 누른 뒤 실행되기 전에 게임에서 나간다 — 부르지 않고, 돌아오면 다시 된다
    multiplayer      직접 실행: 단추를 누른 뒤 실행되기 전에 멀티플레이 표시가 선다
    pick_gone        폴란드를 고른 뒤 폴란드가 이번 판에서 없어진다 — 고른 것이 풀린다
    pick_become      폴란드를 고른 뒤 플레이하는 나라가 폴란드가 된다 — 고른 것이 풀린다
    pick_again       폴란드에 대해 "한 번 더"를 기다리는 중에 덴마크를 고른다 — 처음부터 다시 묻는다
    ansi_search      게임 창이 ANSI 창일 때 검색란에 한글 한 글자(두 바이트)를 넣는다

장치를 만들 수 없으면 "nodevice", 흉내를 만들 수 없으면 "skip <이유>".
tests/test_toybox.py 가 부른다(pytest 가 직접 모으는 테스트 파일이 아니다).
"""
import ctypes
import json
import os
import struct
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from toybox_fake_game import MULTIPLAYER, OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)

SLOT_PRESENT, SLOT_RESIZE, SLOT_PRESENT1 = 8, 13, 22
LIMIT = 50      # 가짜 훅이 이만큼 불리면 맴도는 것이다. 여기서 끊어 프로세스가 죽지 않게 한다
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x100, 0x101, 0x102, 0x200, 0x201, 0x202
WM_TIMER, WM_MOUSEWHEEL = 0x113, 0x20A
TIMER_ID = 0x7B0C0001       # ToyBox 의 실행기가 게임 창에 건 타이머(native/srtoybox/input.cpp)
REAL_KEY = 0x00140001       # 실제 키보드의 메시지처럼 스캔 코드가 든 lParam (ToyBox 의 실행기가 보내는 것은 스캔 코드가 0 이다)
# 설정 창의 자리: 처음 뜨는 곳 40,60 · 크기 500x460 (build/verify/toybox/G1-open.png). 단추의 자리는 창에게 묻는다(Game.spot)
CHEAT_TAB = "tab:화면·진행"   # 아직 내장 치트로 도는 단추가 있는 탭(첫 탭 "돈"은 값 쓰기 전용 화면이다)
BUTTON = "run:fullmapshow"   # 그 탭의 첫 줄 "GUI 숨기기/보이기" (cheat fullmapshow) — 묶음 6 에서 옮길 때까지 남는다
TITLE = (300, 70)           # 제목 줄 — 눌러도 아무 일도 없다
NO_DIRTY_RECTS = (ctypes.c_byte * 40)()     # 0 으로 채운 DXGI_PRESENT_PARAMETERS (Present1 이 읽는 동안 살아 있어야 한다)


class RATIONAL(ctypes.Structure):
    _fields_ = [("Numerator", ctypes.c_uint), ("Denominator", ctypes.c_uint)]


class MODE_DESC(ctypes.Structure):
    _fields_ = [("Width", ctypes.c_uint), ("Height", ctypes.c_uint), ("RefreshRate", RATIONAL), ("Format", ctypes.c_uint),
                ("ScanlineOrdering", ctypes.c_uint), ("Scaling", ctypes.c_uint)]


class SAMPLE_DESC(ctypes.Structure):
    _fields_ = [("Count", ctypes.c_uint), ("Quality", ctypes.c_uint)]


class SWAP_CHAIN_DESC(ctypes.Structure):
    _fields_ = [("BufferDesc", MODE_DESC), ("SampleDesc", SAMPLE_DESC), ("BufferUsage", ctypes.c_uint),
                ("BufferCount", ctypes.c_uint), ("OutputWindow", wintypes.HWND), ("Windowed", wintypes.BOOL),
                ("SwapEffect", ctypes.c_uint), ("Flags", ctypes.c_uint)]


LRESULT = ctypes.c_ssize_t
PRESENT = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint)
PRESENT1 = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p)
RESIZE = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
HANDLER = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)    # 게임의 명령 처리 함수: void f(void *context, const char *line)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD] + [ctypes.c_int] * 4 \
    + [wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrA.restype = ctypes.c_void_p
user32.SetWindowLongPtrA.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SendMessageA.restype = LRESULT
user32.SendMessageA.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.IsWindowUnicode.argtypes = [wintypes.HWND]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


def make_swap_chain(buffer: tuple[int, int] | None = None):
    """가짜 게임 창(클라이언트 1024x768, 화면에 보이지 않는다)과 그 swap chain. buffer 를 주면 그리는 크기를 창과 다르게 한다."""
    d3d11 = ctypes.WinDLL("d3d11")
    hwnd = user32.CreateWindowExW(0, "STATIC", "probe", 0x80000000, 0, 0, 1024, 768, None, None, None, None)   # WS_POPUP: 테두리 없음
    desc = SWAP_CHAIN_DESC()
    desc.BufferCount = 1
    desc.BufferDesc.Format = 28          # DXGI_FORMAT_R8G8B8A8_UNORM
    if buffer:
        desc.BufferDesc.Width, desc.BufferDesc.Height = buffer
    desc.BufferUsage = 0x20              # DXGI_USAGE_RENDER_TARGET_OUTPUT
    desc.OutputWindow = hwnd
    desc.SampleDesc.Count = 1
    desc.Windowed = True
    swap, device, context = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    for driver in (1, 5):                # 하드웨어, 안 되면 WARP
        hr = d3d11.D3D11CreateDeviceAndSwapChain(None, driver, None, 0, None, 0, 7, ctypes.byref(desc), ctypes.byref(swap),
                                                 ctypes.byref(device), None, ctypes.byref(context))
        if hr >= 0 and swap.value:
            return swap, hwnd
    return None, hwnd


def vtable(swap):
    return ctypes.cast(ctypes.cast(swap, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))


def write_code(address: int, data: bytes) -> None:
    old = wintypes.DWORD()
    kernel32.VirtualProtect(address, len(data), 0x40, ctypes.byref(old))      # 실행 · 읽기 · 쓰기
    ctypes.memmove(address, data, len(data))
    kernel32.VirtualProtect(address, len(data), old.value, ctypes.byref(old))
    kernel32.FlushInstructionCache(kernel32.GetCurrentProcess(), address, len(data))


def write_slot(table, index: int, value: int) -> None:
    address = ctypes.addressof(table.contents) + index * ctypes.sizeof(ctypes.c_void_p)
    old = wintypes.DWORD()
    kernel32.VirtualProtect(address, 8, 0x04, ctypes.byref(old))              # 읽기 · 쓰기
    table[index] = value
    kernel32.VirtualProtect(address, 8, old.value, ctypes.byref(old))


def plant_jump(function: int, target: int) -> None:
    """함수의 머리 5바이트를 가까운 디딤돌로 가는 점프(E9)로 바꾼다. 디딤돌은 target 으로 가는 절대 점프다."""
    stub = None
    for step in range(1, 4000):                               # E9 가 닿는 2GB 안에서 빈 자리를 찾는다
        stub = kernel32.VirtualAlloc((function & ~0xFFFF) - step * 0x10000, 4096, 0x3000, 0x40)   # 예약+확정, 실행·읽기·쓰기
        if stub:
            break
    assert stub, "디딤돌을 둘 자리를 찾지 못했다"
    ctypes.memmove(stub, bytes([0xFF, 0x25, 0, 0, 0, 0]) + target.to_bytes(8, "little"), 14)
    write_code(function, bytes([0xE9]) + (stub - (function + 5)).to_bytes(4, "little", signed=True))


def prologue_decoder(hook: str):
    """ToyBox 의 명령 길이 세기를 빌려 쓴다. DLL 을 미리 올려 둘 뿐이다 — 끼어드는 것은 훅이 srtoybox_start 를 부를 때다."""
    toybox = ctypes.WinDLL(str(Path(hook).with_name("srtoybox.dll")))
    toybox.srtoybox_prologue_length.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    return toybox.srtoybox_prologue_length


def trampoline(length_of, function: int) -> int:
    """함수의 첫 명령들을 옮겨 놓고 그 다음 자리로 뛰는 코드(머리에 점프를 심는 훅이 '원래 함수'로 부르는 것). 옮길 수 없으면 0."""
    head = ctypes.string_at(function, 32)
    n = length_of(head, 32, 5)
    if n == 0:
        return 0
    code = kernel32.VirtualAlloc(None, 64, 0x3000, 0x40)
    ctypes.memmove(code, head[:n] + bytes([0xFF, 0x25, 0, 0, 0, 0]) + (function + n).to_bytes(8, "little"), n + 14)
    return code


def load_toybox(hook: str, table, slot: int = SLOT_PRESENT) -> bool:
    """훅을 불러 ToyBox 가 끼어들기를 마칠 때까지(로그에 결과가 적힐 때까지) 기다린다. 표의 그 칸이 바뀌었으면 True."""
    before = table[slot]
    ctypes.WinDLL(hook)                                       # 훅이 ToyBox 를 불러오고, ToyBox 가 다른 스레드에서 끼어든다
    home = os.environ.get("SRTOYBOX_HOME")
    log = Path(home, "toybox.log") if home else None
    deadline = time.time() + 10
    while time.time() < deadline:
        if log is None and table[slot] != before:             # 로그를 볼 수 없으면(손으로 돌릴 때) 칸이 바뀐 뒤 조금 더 기다린다
            time.sleep(0.5)
            break
        if log is not None and log.is_file() and "끼어들" in log.read_text(encoding="utf-8", errors="replace"):
            break
        time.sleep(0.05)
    return table[slot] != before


def set_mods(on: bool) -> None:
    """이 스레드의 키 상태표에 Ctrl · Shift 를 눌린 것(또는 뗀 것)으로 적는다. Alt 는 늘 뗀 것으로 적는다 —
    테스트가 도는 동안 사용자가 실제 키보드의 Alt 를 누르고 있으면 상태표에 그것이 남아, 단축키가 Ctrl+Shift+Alt+T 로 읽힌다."""
    state = (ctypes.c_ubyte * 256)()
    user32.GetKeyboardState(state)
    for vk in (0x11, 0x10):
        state[vk] = (state[vk] & 0x7F) | (0x80 if on else 0)
    state[0x12] &= 0x7F
    user32.SetKeyboardState(state)


def mods_down() -> bool:
    state = (ctypes.c_ubyte * 256)()
    user32.GetKeyboardState(state)
    return bool((state[0x11] | state[0x10]) & 0x80)


def press_hotkey(hwnd, lparam: int = 1) -> None:
    """Ctrl+Shift+T (ToyBox 의 기본 단축키)."""
    set_mods(True)
    user32.SendMessageW(hwnd, WM_KEYDOWN, 0x54, lparam)
    set_mods(False)


def u32(hr: int) -> str:
    return f"{hr & 0xFFFFFFFF:#x}"


def call(table, slot: int, swap, function: int | None = None) -> int:
    """게임이 하듯 표의 그 칸을(function 을 주면 그 함수를) 부른다."""
    target = function or table[slot]
    if slot == SLOT_PRESENT:
        return PRESENT(target)(swap, 0, 0)
    if slot == SLOT_RESIZE:
        return RESIZE(target)(swap, 0, 800, 600, 0, 0)
    return PRESENT1(target)(swap, 0, 0, ctypes.addressof(NO_DIRTY_RECTS))


def run_fake_hook(hook: str, mode: str, swap, table) -> int:
    slot = {"inline_resize": SLOT_RESIZE, "inline_present1": SLOT_PRESENT1}.get(mode, SLOT_PRESENT)
    proto = {SLOT_PRESENT: PRESENT, SLOT_RESIZE: RESIZE, SLOT_PRESENT1: PRESENT1}[slot]
    real = table[slot]
    plain = call(table, slot, swap)                           # 아무도 끼어들기 전의 반환값
    state = {"calls": 0, "saved": real}                       # saved: 가짜 훅이 아는 "원래 함수"

    def body(*args):
        """다른 프로그램의 훅 대역. 표의 칸에 끼어드는 훅은 그 칸에 있는 것이 자기가 아니면 그것을 원래 함수로 안다."""
        state["calls"] += 1
        if state["calls"] > LIMIT:
            return 0
        now = table[slot]
        return proto(now if mode in ("before", "rehook") and now != fake_address else state["saved"])(*args)

    fake = proto(body)
    fake_address = ctypes.cast(fake, ctypes.c_void_p).value
    length_of = None
    if mode == "steam":                                       # 오버레이가 먼저 진짜 함수에 끼어들었다: 원본은 진짜 함수의 트램펄린
        length_of = prologue_decoder(hook)
        state["saved"] = trampoline(length_of, real)
        if not state["saved"]:
            print("skip 진짜 함수의 머리를 옮길 수 없다")
            return 0
    if mode in ("before", "rehook"):
        write_slot(table, slot, fake_address)                 # 다른 훅이 표의 칸에 먼저 끼어들어 있다
    if mode in ("inline", "steam", "inline_resize", "inline_present1"):
        plant_jump(real, fake_address)                        # 다른 훅이 진짜 함수의 머리에 점프를 심어 두었다
    if not load_toybox(hook, table, slot):
        print("toybox did not hook")
        return 1
    ours = table[slot]
    if mode == "rehook":                                      # 다른 훅이 표의 칸에 ToyBox 위로 다시 끼어든다
        state["saved"] = ours
        write_slot(table, slot, fake_address)
    if mode in ("inline", "inline_resize", "inline_present1"):   # 그 훅이 표에서 본 ToyBox 의 함수를 원래 함수로 안다
        state["saved"] = ours
    if mode == "steam":                                       # 오버레이가 ToyBox 의 함수 머리에도 점프를 심고, 원본을 그 트램펄린으로 바꾼다
        state["saved"] = trampoline(length_of, ours)
        if not state["saved"]:
            print("skip ToyBox 함수의 머리를 옮길 수 없다(컴파일러가 낸 머리가 달라졌다)")
            return 0
        plant_jump(ours, fake_address)
    hr = 0
    for _ in range(3 if slot == SLOT_PRESENT else 1):         # 게임이 화면을 세 번 내보낸다(크기 바꾸기 · Present1 은 한 번)
        hr = call(table, slot, swap)
    print(f"calls={state['calls']} hr={u32(hr)} plain={u32(plain)}")
    return 0


def run_refusal(hook: str, mode: str, table) -> int:
    """ToyBox 의 깨끗한 진입로는 '함수의 첫 14바이트 뒤는 디스크의 파일과 같다'고 믿는다. 그 믿음이 깨진 자리에서는 끼어들면 안 된다."""
    if mode.startswith("longpatch"):   # 다른 훅이 머리를 16바이트 고쳐 놓았다(mov rax, imm64 / jmp rax / nop 4개). 실행하지는 않는다
        real = table[SLOT_RESIZE if mode == "longpatch_resize" else SLOT_PRESENT]
        write_code(real, bytes([0x48, 0xB8]) + bytes(8) + bytes([0xFF, 0xE0, 0x90, 0x90, 0x90, 0x90]))
    else:                         # 게임이 떠 있는 동안 Windows 업데이트가 dxgi.dll 을 바꿨다: 올라온 것의 머리말이 파일과 다르다
        base = kernel32.GetModuleHandleW("dxgi.dll")
        stamp = base + ctypes.c_int.from_address(base + 0x3C).value + 8      # IMAGE_NT_HEADERS.FileHeader.TimeDateStamp
        write_code(stamp, (ctypes.c_uint.from_address(stamp).value ^ 0x5A5A5A5A).to_bytes(4, "little"))
    print("hooked" if load_toybox(hook, table) else "nohook")
    return 0


def run_draw_resize(hook: str, swap, hwnd, table) -> int:
    real_resize = table[SLOT_RESIZE]
    plain_present1 = call(table, SLOT_PRESENT1, swap)
    if not load_toybox(hook, table):
        print("toybox did not hook")
        return 1
    out = {"resize_hooked": int(table[SLOT_RESIZE] != real_resize)}
    PRESENT(table[SLOT_PRESENT])(swap, 0, 0)                  # 첫 화면: ToyBox 가 준비하고 창 프로시저를 감싼다
    press_hotkey(hwnd)
    out["visible"] = u32(max(PRESENT(table[SLOT_PRESENT])(swap, 0, 0) & 0xFFFFFFFF for _ in range(3)))
    # 훅을 거치지 않고 진짜 ResizeBuffers 를 부르면 실패해야 한다 — ToyBox 가 뒷면을 쥐고 있다(= 실제로 그렸다)
    out["direct_resize"] = u32(call(table, SLOT_RESIZE, swap, real_resize))
    out["hooked_resize"] = u32(call(table, SLOT_RESIZE, swap))
    out["after"] = u32(max(PRESENT(table[SLOT_PRESENT])(swap, 0, 0) & 0xFFFFFFFF for _ in range(2)))
    out["present1"] = u32(call(table, SLOT_PRESENT1, swap))
    out["present1_plain"] = u32(plain_present1)
    print(" ".join(f"{k}={v}" for k, v in out.items()))
    return 0


class Game:
    """가짜 게임: 창 프로시저가 받은 글쇠 · 누름을 적고, 화면을 내보내며 메시지를 돌린다."""

    def __init__(self, hook: str, buffer: tuple[int, int] | None = None, ansi: bool = False):
        self.hook = hook
        self.ansi = ansi        # 창 프로시저를 ANSI 방식으로 건다 — 글자 메시지가 코드 페이지의 바이트로 온다
        self.swap, self.hwnd = make_swap_chain(buffer)
        self.got: list[tuple[str, int]] = []
        self.proc = WNDPROC(self.receive)
        self.table = None
        self.toybox = None

    def receive(self, hwnd, message, wparam, lparam):
        name = {WM_KEYDOWN: "down", WM_KEYUP: "up", WM_CHAR: "char", WM_LBUTTONDOWN: "press", WM_LBUTTONUP: "release"}.get(message)
        if name:
            self.got.append((name, wparam))
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def start(self) -> bool:
        subclass = user32.SetWindowLongPtrA if self.ansi else user32.SetWindowLongPtrW
        subclass(self.hwnd, -4, ctypes.cast(self.proc, ctypes.c_void_p))                   # ToyBox 가 이 프로시저를 감싼다
        self.table = vtable(self.swap)
        if not load_toybox(self.hook, self.table):
            return False
        self.toybox = ctypes.WinDLL(str(Path(self.hook).with_name("srtoybox.dll")))
        self.toybox.srtoybox_ui_report.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.present(2)
        return True

    def facts(self) -> dict[str, tuple[int, int, bool, str]]:
        """설정 창이 방금 그린 것들: 이름 → (가운데 x, 가운데 y, 보이는가, 글). 창이 닫혀 있으면 비어 있다."""
        buf = ctypes.create_string_buffer(1 << 16)
        self.toybox.srtoybox_ui_report(buf, len(buf))           # 처음 부를 때부터 모으기 시작한다
        self.present(2)
        assert self.toybox.srtoybox_ui_report(buf, len(buf)) >= 0
        out = {}
        for line in buf.value.decode("utf-8").splitlines():
            name, x, y, visible, text = line.split("\t", 4)
            out[name] = (int(x), int(y), visible == "1", text)
        return out

    def spot(self, name: str) -> tuple[int, int]:
        """그 항목의 가운데(누를 자리). 창에 보이고 있어야 한다."""
        x, y, visible, _ = self.facts()[name]
        assert visible, f"{name} 이 창에 보이지 않는다"
        return x, y

    def shown(self, name: str) -> str:
        """그 항목이 창에 보이면 그 글, 아니면(그리지 않았거나 스크롤 밖) "-"."""
        _, _, visible, text = self.facts().get(name, (0, 0, False, ""))
        return text if visible else "-"

    def present(self, frames: int = 1) -> None:
        for _ in range(frames):
            PRESENT(self.table[SLOT_PRESENT])(self.swap, 0, 0)

    def pump(self, until, limit: float) -> bool:
        """메시지를 돌리고 화면을 내보낸다 — until() 이 참이 되거나 limit 초가 지날 때까지."""
        message = wintypes.MSG()
        end = time.time() + limit
        while time.time() < end:
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            self.present()
            if until():
                return True
            time.sleep(0.005)
        return False

    def wait(self, seconds: float) -> None:
        end = time.time() + seconds
        self.pump(lambda: time.time() >= end, seconds + 1)

    def click(self, point: tuple[int, int] | str) -> str:
        """그 자리(또는 그 이름의 항목)를 누른다. 게임(가짜 창 프로시저)까지 간 것을 돌려준다: "press+release", 아무것도 안 갔으면 "none"."""
        if isinstance(point, str):
            point = self.spot(point)
        seen = len(self.got)
        for message, wparam in ((WM_MOUSEMOVE, 0), (WM_LBUTTONDOWN, 1), (WM_LBUTTONUP, 0)):
            user32.SendMessageW(self.hwnd, message, wparam, (point[1] << 16) | point[0])
            self.present(2)
        return "+".join(name for name, _ in self.got[seen:] if name in ("press", "release")) or "none"

    def hotkey(self, lparam: int = 1) -> str:
        """단축키를 누른다. 그 글쇠를 받은 쪽: "toybox"(삼켰다) 또는 "game"."""
        seen = len(self.got)
        press_hotkey(self.hwnd, lparam)
        self.present(3)
        return "game" if ("down", 0x54) in self.got[seen:] else "toybox"

    def open(self, lparam: int = 1) -> str:
        """단축키로 창을 열고 CHEAT_TAB 으로 간다. 단축키를 받은 쪽("toybox" / "game")을 돌려준다."""
        who = self.hotkey(lparam)
        self.click(CHEAT_TAB)
        return who

    def has(self, name: str, value: int) -> bool:
        return (name, value) in self.got

    def text(self) -> str:
        """게임이 받은 글쇠를 읽기 좋게: 글자는 그대로, 누름은 <이름>."""
        keys = {0x0D: "<Enter>", 0x1B: "<Esc>", 0x53: "<S>", 0x11: "<Ctrl>", 0x10: "<Shift>"}
        out = ""
        for name, value in self.got:
            if name == "char" and 32 <= value < 127:
                out += chr(value)
            elif name == "down":
                out += keys.get(value, f"<{value:#x}>")
        return out


def start_game(hook: str, buffer: tuple[int, int] | None = None, ansi: bool = False) -> Game | None:
    if not Path(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "malgun.ttf").is_file():
        print("skip 맑은 고딕이 없다(설정 창의 단추 자리가 달라진다)")
        return None
    game = Game(hook, buffer, ansi)
    if game.swap is None:
        print("nodevice")
        return None
    if not game.start():
        print("skip ToyBox 가 끼어들지 않았다")
        return None
    return game


def fake_game(hook: str, handler: int | None = None, values: bool = True) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106. 국고 $5 B)와 독일(176, 1499. 국고 $14.43 B)이 있고 메뉴 상태다.

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    values 가 False 면 값의 자리를 찾지 못한 게임이다(돈 탭이 꺼진다).
    """
    toybox = ctypes.WinDLL(str(Path(hook).with_name("srtoybox.dll")))
    toybox.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    toybox.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.set_treasury(141, 5e9)
    fake.set_treasury(176, 14.43e9)
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    if values:
        toybox.srtoybox_test_values(ctypes.byref(fake.layout))
    return fake


def run_gate(hook: str, mode: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    fake = fake_game(hook)
    if mode != "gate_menu":
        fake.play(176)
    game.open()
    button = game.click(BUTTON)
    if mode == "gate_leave":
        fake.menu()                                           # 눌린 명령이 실행되기 전에 게임에서 나갔다
    game.got.clear()
    game.pump(lambda: game.has("up", 0x1B), 20 if mode == "gate_typing" else 2)
    game.wait(0.4)
    print(f"button={button} text={game.text()}")
    return 0


def crash_stub() -> int:
    """부르면 0 번지에 쓰는 함수(mov dword ptr [0],1 / ret) — 게임의 함수 안에서 나는 접근 위반을 흉내 낸다."""
    code = kernel32.VirtualAlloc(None, 16, 0x3000, 0x40)
    ctypes.memmove(code, bytes([0xC7, 0x04, 0x25, 0, 0, 0, 0, 1, 0, 0, 0, 0xC3]), 12)
    return code


def run_direct(hook: str, mode: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":                      # 게임이 하듯 치트 허용 비트를 세운다
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)

    handler = HANDLER(body)
    fake = box["fake"] = fake_game(hook, crash_stub() if mode == "direct_fault" else ctypes.cast(handler, ctypes.c_void_p).value)
    if mode not in ("direct_menu", "direct_read_off"):
        fake.play(176)
    game.open()
    game.got.clear()
    if mode in ("direct_off", "direct_read_off"):
        game.click(BUTTON)
        game.pump(lambda: game.has("up", 0x1B), 20 if mode == "direct_off" or os.environ.get("SRTOYBOX_READ") == "0" else 2)
        game.wait(0.4)
    elif mode == "direct_menu":
        game.click(BUTTON)
        game.wait(1.0)
    else:
        for press in range(3):
            if press == 2:
                fake.poke(OPTIONS, "<I", 0)                   # 메뉴에 나갔다 온 것처럼 치트 허용이 꺼졌다
            game.click(BUTTON)
            game.wait(0.4)
    print("lines=" + "|".join(line.replace(" ", "_") for line in lines) + " text=" + game.text())
    return 0


DIPLOMACY = "tab:외교·영토"
LAST_BUTTON = "run:becomeregion"   # 그 탭의 맨 아래 단추 "이 나라로 플레이" — 되돌릴 수 없는 것이라 두 번 눌러야 한다


def recording_game(hook: str, crash: bool = False, ansi: bool = False):
    """가짜 게임(폴란드 · 덴마크 · 독일, 메뉴 상태)과 명령 처리 함수가 받은 줄들. crash 면 그 함수가 잘못된 주소에 쓴다."""
    game = start_game(hook, ansi=ansi)
    if game is None:
        return None
    lines: list[str] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)

    game.handler = HANDLER(body)                              # 게임이 살아 있는 동안 붙들어 둔다
    fake = box["fake"] = fake_game(hook, crash_stub() if crash else ctypes.cast(game.handler, ctypes.c_void_p).value)
    fake.region(150, 1201, alive=3)                           # 덴마크
    return game, fake, lines


def scroll_to(game: Game, name: str, up: bool = False) -> bool:
    """마우스를 설정 창 위에 두고, 그 항목이 보일 때까지 휠을 아래로(up 이면 위로) 굴린다."""
    for _ in range(12):
        if game.facts()[name][2]:
            return True
        user32.SendMessageW(game.hwnd, WM_MOUSEMOVE, 0, (400 << 16) | 400)
        user32.SendMessageW(game.hwnd, WM_MOUSEWHEEL, ((120 if up else -120) & 0xFFFF) << 16, 0)
        game.present(2)
    return game.facts()[name][2]


def run_window(hook: str, mode: str) -> int:
    """설정 창에 보이는 글과 그 전이. 출력은 JSON 한 줄."""
    if mode == "ansi_search" and kernel32.GetACP() != 949:
        print("skip 시스템 코드 페이지가 949(한국어)가 아니다")
        return 0
    made = recording_game(hook, crash=mode == "confirm_fault", ansi=mode == "ansi_search")
    if made is None:
        return 0
    game, fake, lines = made
    out: dict[str, object] = {}
    if mode in ("leave", "multiplayer"):
        fake.play(176)
        game.open()
        game.click(BUTTON)                                    # 눌렀다. 실행은 다음 타이머에서다(메시지를 돌릴 때 온다)
        if mode == "leave":
            fake.menu()                                       # 그 전에 게임에서 나갔다
        else:
            fake.poke(MULTIPLAYER, "<B", 1)                   # 그 전에 멀티플레이 표시가 섰다
        game.wait(0.5)
        out["dropped"] = list(lines)
        out["trouble"], out["status"] = game.shown("trouble"), game.shown("status")
        game.click(BUTTON)                                    # 단추가 꺼져 있다
        game.wait(0.4)
        out["while_off"] = list(lines)
        if mode == "leave":
            fake.play(176)
        else:
            fake.poke(MULTIPLAYER, "<B", 0)
        game.click(BUTTON)                                    # 돌아오면 다시 된다
        game.wait(0.4)
        out["lines"] = lines
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if mode == "hints":
        game.hotkey()
        out["menu"] = game.shown("hint")
        fake.play(176)
        out["game"] = game.shown("hint")
        print(json.dumps(out, ensure_ascii=False))
        return 0
    fake.play(176)
    game.hotkey()
    game.click(DIPLOMACY)
    game.wait(1.2)                                            # 나라 목록은 1초마다 읽는다
    game.click("row:1106")
    if mode == "confirm":
        out["hidden"] = game.shown(LAST_BUTTON)               # 맨 아래 단추는 처음에는 가려 있다
        out["scrolled"] = scroll_to(game, LAST_BUTTON)
        game.click(LAST_BUTTON)                               # 처음 누르면 묻기만 한다
        game.wait(0.3)
        out["after_first"] = list(lines)
        out["armed"] = game.shown(LAST_BUTTON)
        out["status"], out["picked"] = game.shown("status"), game.shown("picked")   # 스크롤을 내린 채로도 보이는가
        game.click(LAST_BUTTON)
        game.wait(0.4)
    elif mode == "confirm_fault":
        game.click("run:love")
        game.wait(0.4)
        out["at_top"] = game.shown("fault")
        out["scrolled"] = scroll_to(game, LAST_BUTTON)
        out["scrolled_down"] = game.shown("fault")
    elif mode in ("pick_gone", "pick_become"):
        game.click("run:love")
        game.wait(0.3)
        out["first"] = list(lines)
        if mode == "pick_gone":
            struct.pack_into("<I", fake.objects[141], 0, 5)   # 폴란드가 이번 판에 없는 지역이 됐다(다른 판을 불러온 것처럼)
            game.wait(1.5)                                    # 나라 목록은 1초마다 읽는다
        else:
            fake.play(141)                                    # 플레이하는 나라가 폴란드로 바뀌었다(cheat becomeregion)
            game.wait(0.3)
        out["status"], out["picked"], out["row"] = game.shown("status"), game.shown("picked"), game.shown("row:1106")
        game.click("run:love")                                # 고른 나라가 없다 — 단추가 꺼져 있다
        game.wait(0.3)
    elif mode == "pick_again":
        scroll_to(game, LAST_BUTTON)
        game.click(LAST_BUTTON)                               # 폴란드에 대해 묻는 중이다
        out["asked"] = game.shown(LAST_BUTTON)
        scroll_to(game, "search", up=True)                    # 목록은 탭 내용의 맨 위에 있다
        game.click("row:1201")                                # 그 사이에 덴마크로 바꿔 골랐다
        scroll_to(game, LAST_BUTTON)
        out["after_repick"] = game.shown(LAST_BUTTON)         # 묻던 것은 폴란드에 대한 것이었다 — 처음부터 다시
        game.click(LAST_BUTTON)
        game.wait(0.3)
        out["after_one_press"] = list(lines)
        out["asked_again"] = game.shown(LAST_BUTTON)
        game.click(LAST_BUTTON)
        game.wait(0.4)
    elif mode == "ansi_search":
        game.click("search")
        game.present(3)                                       # 검색란이 글을 받는다
        for byte in "폴".encode("cp949"):                      # ANSI 창에는 한글 한 글자가 WM_CHAR 두 번(앞 · 뒤 바이트)으로 온다
            user32.SendMessageA(game.hwnd, WM_CHAR, byte, 1)
            game.present()
        game.present(3)
        facts = game.facts()
        out["ansi"] = int(not user32.IsWindowUnicode(game.hwnd))
        out["search"] = game.shown("search")
        out["rows"] = sorted(name for name in facts if name.startswith("row:"))
    out["lines"] = lines
    print(json.dumps(out, ensure_ascii=False))
    return 0


def run_reenter(hook: str, mode: str) -> int:
    """게임의 명령 처리 함수가 일하는 도중에 ToyBox 로 되돌아온다(메시지를 돌리거나 화면을 내보내는 게임 코드가 그렇다)."""
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    inside: list[str] = []
    box = {"depth": 0, "deepest": 0, "done": False}

    def body(_context, line):
        lines.append(line.decode())
        box["depth"] += 1
        box["deepest"] = max(box["deepest"], box["depth"])
        try:
            if line == b"cheat allowcheats":
                box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)
            elif not box["done"]:
                box["done"] = True
                if mode == "reenter_timer":       # ToyBox 의 타이머가 그 안에서 다시 온다
                    user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)
                elif mode == "reenter_keyup":     # 실제 키보드의 뗌(스캔 코드가 있다)이 그 안에서 온다
                    user32.SendMessageW(game.hwnd, WM_KEYUP, 0x41, 0xC01E0001)
                else:                             # 그 안에서 화면을 한 번 내보낸다
                    PRESENT(game.table[SLOT_PRESENT])(game.swap, 0, 0)
                inside.append("ok")
        except OSError as error:
            inside.append(f"error:{(error.winerror or 0) & 0xFFFFFFFF:#x}")
        finally:
            box["depth"] -= 1

    handler = HANDLER(body)
    fake = box["fake"] = fake_game(hook, ctypes.cast(handler, ctypes.c_void_p).value)
    fake.play(176)
    game.open()
    game.got.clear()
    game.click(BUTTON)
    game.click(BUTTON)                                        # 둘째 명령이 대기열에 있는 채로 첫째가 실행된다
    game.wait(0.5)
    game.click(BUTTON)                                        # 그 뒤에도 ToyBox 가 살아 있어야 한다
    game.wait(0.4)
    print(f"inside={';'.join(inside) or '-'} deepest={box['deepest']} lines=" + "|".join(line.replace(" ", "_") for line in lines)
          + " text=" + game.text())
    return 0


MONEY = "tab:돈"


def run_money(hook: str, mode: str) -> int:
    """돈 탭: 내장 치트를 거치지 않고 국고를 고친다. 출력은 JSON 한 줄(보이지 않는 글은 "-")."""
    home = os.environ.get("SRTOYBOX_HOME")
    if mode == "money" and home:
        Path(home, "toybox.ini").write_text("money.amount=1234\n", encoding="utf-8")   # 입력란의 값(백만 달러). ToyBox 가 뜰 때 읽는다
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    inside: list[float] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)
        elif mode == "money_reenter":                         # 게임의 함수가 일하는 도중에 ToyBox 의 타이머가 다시 온다
            inside.append(box["fake"].treasury(176))
            user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)
            inside.append(box["fake"].treasury(176))

    game.handler = HANDLER(body)                              # 게임이 살아 있는 동안 붙들어 둔다
    fake = box["fake"] = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value, values=mode != "money_notfound")
    if mode == "money_fail":
        fake.lock(176)                                        # 플레이어 지역 객체가 읽기 전용 쪽에 있다(읽을 수는 있다)
    if mode == "money_unreadable":
        fake.set_stock(176, 9, float("nan"))                  # 값을 통째로 믿지 않는다(read_values)
    if mode != "money_menu":
        fake.play(176)
    game.hotkey()                                             # 창이 열리면 첫 탭이 "돈"이다
    game.got.clear()
    facts = game.facts()
    out: dict[str, object] = {"now": game.shown("money:now"), "off": game.shown("money:off")}
    out["cheat_buttons"] = sorted(name for name in facts if name.startswith("run:"))
    out["buttons"] = sorted(name for name in facts
                            if name.startswith("money:") and name not in ("money:now", "money:off", "money:amount"))

    def press(name: str) -> float:
        game.click(name)
        game.wait(0.2)                                        # 쓰는 것은 다음 타이머에서다
        return fake.treasury(176)

    if mode == "money":
        out["steps"] = [press(name) for name in ("money:+10b", "money:+100b", "money:-10b", "money:-100b", "money:zero",
                                                 "money:add", "money:add", "money:sub", "money:+10b", "money:set")]
        out["amount"], out["now_after"], out["wrote"] = game.shown("money:amount"), game.shown("money:now"), game.shown("wrote")
    elif mode == "money_menu":
        out["steps"] = [press("money:+10b")]
        out["status"] = game.shown("status")
    elif mode == "money_leave":
        game.click("money:+10b")                              # 눌렀다. 쓰는 것은 다음 타이머에서다(메시지를 돌릴 때 온다)
        fake.menu()                                           # 그 전에 게임에서 나갔다
        game.wait(0.3)
        out["dropped"], out["unwritten"] = fake.treasury(176), game.shown("unwritten")
        fake.play(176)
        out["steps"] = [press("money:+10b")]                  # 돌아오면 다시 된다
        out["unwritten_after"] = game.shown("unwritten")
    elif mode == "money_fail":
        out["steps"] = [press("money:+10b")]
        out["off_after"] = game.shown("money:off")
        out["buttons_after"] = sorted(name for name in game.facts() if name.startswith("money:") and name != "money:off")
    elif mode == "money_reenter":
        game.click(CHEAT_TAB)
        game.click(BUTTON)                                    # 옮기지 않은 기능 하나(직접 실행)가 대기열에 든다
        game.click(MONEY)
        game.click("money:+10b")                              # 국고 요청도 대기열에 든다
        game.wait(0.5)
        out["inside"], out["after"] = inside, fake.treasury(176)
    out["lines"], out["text"], out["options"], out["poland"] = lines, game.text(), fake.peek(OPTIONS, "<I"), fake.treasury(141)
    print(json.dumps(out, ensure_ascii=False))
    return 0


def crash_once_stub(flag: int, real: int) -> int:
    """깃발(flag 의 바이트)이 서 있으면 내리고 0 번지에 쓴다. 아니면 real 로 뛴다 — 한 번만 죽는 "진짜 Present"."""
    code = kernel32.VirtualAlloc(None, 64, 0x3000, 0x40)
    body = (bytes([0x48, 0xB8]) + flag.to_bytes(8, "little")                 # mov rax, flag
            + bytes([0x80, 0x38, 0x00, 0x74, 0x0E])                           # cmp byte ptr [rax], 0 / je +14
            + bytes([0xC6, 0x00, 0x00])                                       # mov byte ptr [rax], 0
            + bytes([0xC7, 0x04, 0x25, 0, 0, 0, 0, 1, 0, 0, 0])               # mov dword ptr [0], 1
            + bytes([0x48, 0xB8]) + real.to_bytes(8, "little") + bytes([0xFF, 0xE0]))   # mov rax, real / jmp rax
    ctypes.memmove(code, body, len(body))
    return code


def run_present_fault(hook: str) -> int:
    """ToyBox 가 부른 다음 함수(진짜 Present 나 다른 훅) 안에서 예외가 나고 그것을 위에서 누가 잡는다 — 그 뒤에도 ToyBox 는 그려야 한다."""
    if not Path(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "malgun.ttf").is_file():
        print("skip 맑은 고딕이 없다(설정 창의 단추 자리가 달라진다)")
        return 0
    game = Game(hook)
    if game.swap is None:
        print("nodevice")
        return 0
    table = vtable(game.swap)
    flag = ctypes.c_ubyte(0)
    write_slot(table, SLOT_PRESENT, crash_once_stub(ctypes.addressof(flag), table[SLOT_PRESENT]))   # ToyBox 가 끼어들 때 그 칸에 있던 것
    if not game.start():
        print("skip ToyBox 가 끼어들지 않았다")
        return 0
    flag.value = 1
    caught = 0
    try:
        game.present()
    except OSError:
        caught = 1
    game.hotkey()
    print(f"caught={caught} drawn={int('status' in game.facts())}")
    return 0


def run_input(hook: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    out = {"hotkey": game.open()}
    out["button"] = game.click(BUTTON)                        # 설정 창의 단추 — 게임에 가면 안 된다. 명령이 대기열에 든다
    out["outside"] = game.click((700, 100))                   # 설정 창 밖 — 게임이 받아야 한다
    game.got.clear()
    out["typing"] = int(game.pump(lambda: game.has("char", ord("c")), 10))   # 실행기가 치트를 적기 시작했다
    # 그동안 사용자가 실제 키보드로 9 를 치고(게임에 가면 치트를 받아 적는 줄에 섞인다) 단축키를 누른다(평소처럼 창이 닫혀야 한다)
    user32.PostMessageW(game.hwnd, WM_KEYDOWN, 0x39, 0x000A0001)
    user32.PostMessageW(game.hwnd, WM_CHAR, 0x39, 0x000A0001)
    user32.PostMessageW(game.hwnd, WM_KEYUP, 0x39, 0xC00A0001)
    game.wait(0.2)
    out["hotkey_busy"] = game.hotkey(REAL_KEY)
    out["done"] = int(game.pump(lambda: game.has("up", 0x1B), 20))            # 마지막 글쇠(ESC)까지 들어갔다
    game.wait(0.6)
    typed = game.text()
    out["mods_left"] = int(mods_down())
    out["title_after"] = game.click(TITLE)                    # 넣는 중에 누른 단축키로 창이 닫혔으면 게임이 받는다
    print(" ".join(f"{k}={v}" for k, v in out.items()) + " text=" + typed)
    return 0


def run_scale(hook: str) -> int:
    game = start_game(hook, buffer=(512, 384))                # 창은 1024x768 인데 그리는 크기는 그 절반 — 화면에는 두 배로 늘어나 보인다
    if game is None:
        return 0
    game.hotkey()
    # 설정 창은 그리는 좌표로 40..540 x 60..520 에 있고, 화면(창의 좌표)에는 80..1080 x 120..1040 으로 보인다
    title = game.click((TITLE[0] * 2, TITLE[1] * 2))          # 보이는 창의 제목 줄 — 게임에 가면 안 된다
    beside = game.click((60, 80))                             # 보이는 창의 왼쪽 위 바깥(그리는 좌표로 30,40) — 게임이 받아야 한다
    print(f"title={title} beside={beside}")
    return 0


def main() -> int:
    hook, mode = sys.argv[1], sys.argv[2]
    if mode == "input":
        return run_input(hook)
    if mode == "scale":
        return run_scale(hook)
    if mode.startswith("gate_"):
        return run_gate(hook, mode)
    if mode.startswith("direct"):
        return run_direct(hook, mode)
    if mode.startswith("reenter_"):
        return run_reenter(hook, mode)
    if mode.startswith("money"):
        return run_money(hook, mode)
    if mode in ("confirm", "confirm_fault", "hints", "leave", "multiplayer", "pick_gone", "pick_become", "pick_again", "ansi_search"):
        return run_window(hook, mode)
    if mode == "present_fault":
        return run_present_fault(hook)
    swap, hwnd = make_swap_chain()
    if swap is None:
        print("nodevice")
        return 0
    table = vtable(swap)
    if mode in ("longpatch", "longpatch_resize", "stale"):
        return run_refusal(hook, mode, table)
    if mode == "draw_resize":
        return run_draw_resize(hook, swap, hwnd, table)
    return run_fake_hook(hook, mode, swap, table)


if __name__ == "__main__":
    sys.exit(main())
