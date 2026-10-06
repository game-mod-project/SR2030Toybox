"""ToyBox 의 화면 끼어들기가, 같은 자리(Present)에 끼어든 다른 훅과 함께 돌 때를 새 프로세스에서 흉내 낸다.

Steam 오버레이가 그런 훅이다: 자기가 불릴 때 가상 함수 표의 칸에 있는 것을 "원래 함수"로 알고 부른다.
ToyBox 가 그 훅을 원래 함수로 알고 부르면 둘이 서로를 부르며 맴돈다(실제로 게임이 죽었다 — docs/10 의 "확인한 것").

    python toybox_overlay_probe.py <훅 DLL 사본> <plain|before|rehook|inline>

before · rehook 은 가상 함수 표의 칸을 바꾸는 훅, inline 은 진짜 함수의 머리에 점프를 심는 훅이다(Steam 오버레이가 이쪽이다).

출력 한 줄: "calls=<가짜 훅이 불린 횟수> hr=<Present 의 반환값>". 장치를 만들 수 없으면 "nodevice".
tests/test_toybox.py 가 부른다(pytest 가 직접 모으는 테스트 파일이 아니다).
"""
import ctypes
import sys
import time
from ctypes import wintypes

SLOT_PRESENT = 8
LIMIT = 50      # 가짜 훅이 이만큼 불리면 맴도는 것이다. 여기서 끊어 프로세스가 죽지 않게 한다


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


PRESENT = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD] + [ctypes.c_int] * 4 \
    + [wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
kernel32.GetCurrentProcess.restype = wintypes.HANDLE


def make_swap_chain() -> ctypes.c_void_p | None:
    d3d11 = ctypes.WinDLL("d3d11")
    hwnd = user32.CreateWindowExW(0, "STATIC", "probe", 0, 0, 0, 64, 64, None, None, None, None)
    desc = SWAP_CHAIN_DESC()
    desc.BufferCount = 1
    desc.BufferDesc.Format = 28          # DXGI_FORMAT_R8G8B8A8_UNORM
    desc.BufferUsage = 0x20              # DXGI_USAGE_RENDER_TARGET_OUTPUT
    desc.OutputWindow = hwnd
    desc.SampleDesc.Count = 1
    desc.Windowed = True
    swap, device, context = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    for driver in (1, 5):                # 하드웨어, 안 되면 WARP
        hr = d3d11.D3D11CreateDeviceAndSwapChain(None, driver, None, 0, None, 0, 7, ctypes.byref(desc), ctypes.byref(swap),
                                                 ctypes.byref(device), None, ctypes.byref(context))
        if hr >= 0 and swap.value:
            return swap
    return None


def write_slot(table, index: int, value: int) -> None:
    address = ctypes.addressof(table.contents) + index * ctypes.sizeof(ctypes.c_void_p)
    old = wintypes.DWORD()
    kernel32.VirtualProtect(address, 8, 0x04, ctypes.byref(old))      # PAGE_READWRITE
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
    old = wintypes.DWORD()
    kernel32.VirtualProtect(function, 5, 0x40, ctypes.byref(old))
    ctypes.memmove(function, bytes([0xE9]) + (stub - (function + 5)).to_bytes(4, "little", signed=True), 5)
    kernel32.VirtualProtect(function, 5, old.value, ctypes.byref(old))
    kernel32.FlushInstructionCache(kernel32.GetCurrentProcess(), function, 5)


def main() -> int:
    hook, mode = sys.argv[1], sys.argv[2]
    swap = make_swap_chain()
    if swap is None:
        print("nodevice")
        return 0
    table = ctypes.cast(ctypes.cast(swap, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    state = {"calls": 0, "saved": table[SLOT_PRESENT]}       # saved: 가짜 훅이 아는 "원래 함수"

    @PRESENT
    def fake(this, sync, flags):
        """다른 프로그램의 훅 대역. 불릴 때 칸에 있는 것이 자기가 아니면 그것을 원래 함수로 안다."""
        state["calls"] += 1
        if state["calls"] > LIMIT:
            return 0
        now = table[SLOT_PRESENT]
        return PRESENT(now if now != fake_address else state["saved"])(this, sync, flags)

    fake_address = ctypes.cast(fake, ctypes.c_void_p).value
    if mode in ("before", "rehook"):
        write_slot(table, SLOT_PRESENT, fake_address)        # 다른 훅이 먼저 끼어들어 있다
    if mode == "inline":
        plant_jump(table[SLOT_PRESENT], fake_address)        # 다른 훅이 진짜 함수의 머리에 점프를 심어 두었다
    ctypes.WinDLL(hook)                                       # 훅이 ToyBox 를 불러오고, ToyBox 가 끼어든다
    start_value = table[SLOT_PRESENT]
    deadline = time.time() + 8
    while time.time() < deadline and table[SLOT_PRESENT] == start_value:
        time.sleep(0.05)
    if table[SLOT_PRESENT] == start_value:
        print("toybox did not hook")
        return 1
    if mode == "rehook":                                      # 다른 훅이 ToyBox 위에 다시 끼어든다
        state["saved"] = table[SLOT_PRESENT]
        write_slot(table, SLOT_PRESENT, fake_address)
    if mode == "inline":                                      # 그 훅이 표에서 ToyBox 의 함수를 보고 그것을 원래 함수로 안다
        state["saved"] = table[SLOT_PRESENT]
    hr = 0
    for _ in range(3):                                        # 게임이 화면을 세 번 내보낸다
        hr = PRESENT(table[SLOT_PRESENT])(swap, 0, 0)
    print(f"calls={state['calls']} hr={hr & 0xFFFFFFFF:#x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
