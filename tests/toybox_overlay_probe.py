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

장치를 만들 수 없으면 "nodevice", 흉내를 만들 수 없으면 "skip <이유>".
tests/test_toybox.py 가 부른다(pytest 가 직접 모으는 테스트 파일이 아니다).
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from toybox_fake_game import OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)

SLOT_PRESENT, SLOT_RESIZE, SLOT_PRESENT1 = 8, 13, 22
LIMIT = 50      # 가짜 훅이 이만큼 불리면 맴도는 것이다. 여기서 끊어 프로세스가 죽지 않게 한다
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x100, 0x101, 0x102, 0x200, 0x201, 0x202
REAL_KEY = 0x00140001       # 실제 키보드의 메시지처럼 스캔 코드가 든 lParam (ToyBox 의 실행기가 보내는 것은 스캔 코드가 0 이다)
# 설정 창의 자리: 처음 뜨는 곳 40,60 · 크기 500x460 · 맑은 고딕 18px 기준 (build/verify/toybox/G1-open.png)
BUTTON = (90, 208)          # 돈 탭의 둘째 줄 "국고 +$10 B" (cheat georgew). 상태 줄이 생기기 전에는 (90, 186)
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

    def __init__(self, hook: str, buffer: tuple[int, int] | None = None):
        self.hook = hook
        self.swap, self.hwnd = make_swap_chain(buffer)
        self.got: list[tuple[str, int]] = []
        self.proc = WNDPROC(self.receive)
        self.table = None

    def receive(self, hwnd, message, wparam, lparam):
        name = {WM_KEYDOWN: "down", WM_KEYUP: "up", WM_CHAR: "char", WM_LBUTTONDOWN: "press", WM_LBUTTONUP: "release"}.get(message)
        if name:
            self.got.append((name, wparam))
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def start(self) -> bool:
        user32.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self.proc, ctypes.c_void_p))   # ToyBox 가 이 프로시저를 감싼다
        self.table = vtable(self.swap)
        if not load_toybox(self.hook, self.table):
            return False
        self.present(2)
        return True

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

    def click(self, point: tuple[int, int]) -> str:
        """그 자리를 누른다. 게임(가짜 창 프로시저)까지 간 것을 돌려준다: "press+release", 아무것도 안 갔으면 "none"."""
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


def start_game(hook: str, buffer: tuple[int, int] | None = None) -> Game | None:
    if not Path(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "malgun.ttf").is_file():
        print("skip 맑은 고딕이 없다(설정 창의 단추 자리가 달라진다)")
        return None
    game = Game(hook, buffer)
    if game.swap is None:
        print("nodevice")
        return None
    if not game.start():
        print("skip ToyBox 가 끼어들지 않았다")
        return None
    return game


def fake_game(hook: str, handler: int | None = None) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106)와 독일(176, 1499)이 있고 메뉴 상태다.

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    """
    toybox = ctypes.WinDLL(str(Path(hook).with_name("srtoybox.dll")))
    toybox.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    return fake


def run_gate(hook: str, mode: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    fake = fake_game(hook)
    if mode != "gate_menu":
        fake.play(176)
    game.hotkey()
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
    if mode != "direct_menu":
        fake.play(176)
    game.hotkey()
    game.got.clear()
    if mode == "direct_off":
        game.click(BUTTON)
        game.pump(lambda: game.has("up", 0x1B), 20)
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


def run_input(hook: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    out = {"hotkey": game.hotkey()}
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
