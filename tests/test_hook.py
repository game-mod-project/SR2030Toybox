"""빌드된 훅 DLL 을 직접 로드해 파이썬 구현(srutf8)과 같은 결과를 내는지 확인한다."""
import ctypes
import os
import random

import pytest

from srkit import hook, srutf8

CP_UTF8 = 65001


@pytest.fixture(scope="module")
def dll(cfg):
    path = hook.output(cfg)
    if not path.is_file():
        pytest.skip("훅 DLL 미빌드 (srkit hook-build)")
    os.environ["SRHOOK"] = "1"  # 레지스트리 언어 설정과 무관하게 켠다
    lib = ctypes.WinDLL(str(path))
    lib.srhook_mbtowc.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_void_p, ctypes.c_int]
    lib.srhook_mbtowc.restype = ctypes.c_int
    return lib


def _decode(lib, data: bytes, cp: int) -> str:
    """게임의 폭 측정 경로와 같은 방식(널 종료 문자열, 넉넉한 버퍼)으로 호출."""
    need = lib.srhook_mbtowc(cp, 0, data, -1, None, 0)
    buf = ctypes.create_unicode_buffer(need)
    assert lib.srhook_mbtowc(cp, 0, data, -1, buf, need) == need
    return buf.value


def test_matches_python_decoder(dll):
    rng = random.Random(2030)
    samples = [srutf8.encode(s) for s in ("정부 예산 %s¶북한 권력", "São Paulo café", "가", "A")]
    samples += ["Köln Düsseldorf don\x92t".encode("latin-1")]
    samples += [bytes(rng.randrange(1, 256) for _ in range(rng.randrange(1, 10))) for _ in range(3000)]
    for data in samples:
        assert _decode(dll, data, 1252) == srutf8.decode(data), data
        assert _decode(dll, data, CP_UTF8) == srutf8.decode(data, measure=True), data


def test_draw_path_buffer_contract(dll):
    """게임의 그리기 경로: 버퍼 크기 = strlen (널 자리 없음). ASCII 는 실패를 돌려주되 버퍼는 채워야 한다."""
    data = b"Hello"
    buf = ctypes.create_unicode_buffer(len(data) + 3)
    assert dll.srhook_mbtowc(1252, 0, data, -1, buf, len(data)) == 0
    assert buf[:5] == "Hello"
    data = srutf8.encode("한글 A")  # 멀티바이트가 있으면 널까지 들어간다
    buf = ctypes.create_unicode_buffer(len(data) + 3)
    assert dll.srhook_mbtowc(1252, 0, data, -1, buf, len(data)) == 5
    assert buf.value == "한글 A"


def test_other_codepages_pass_through(dll):
    data = "한글".encode("cp949")
    assert _decode(dll, data, 949) == "한글"


def test_virtual_cursor_position(dll):
    """검증용 마우스 위치: 공유 메모리에 창 안 좌표를 적어 두면 GetCursorPos 가 그 자리의 화면 좌표를 돌려준다."""
    from ctypes import wintypes

    class Shared(ctypes.Structure):     # native/srhook/srhook.c 의 SRCURSOR
        _fields_ = [("on", ctypes.c_long), ("x", ctypes.c_long), ("y", ctypes.c_long), ("reads", ctypes.c_long),
                    ("hwnd", ctypes.c_ulonglong)]

    user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    kernel32.OpenFileMappingW.restype = wintypes.HANDLE
    kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.MapViewOfFile.restype = ctypes.c_void_p
    kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    dll.srhook_get_cursor_pos.argtypes = [ctypes.POINTER(wintypes.POINT)]

    pt = wintypes.POINT()
    dll.srhook_get_cursor_pos(ctypes.byref(pt))     # 처음 부르면 공유 메모리가 생긴다. 꺼져 있으니 실제 위치
    handle = kernel32.OpenFileMappingW(0xF001F, False, f"Local\\srkit.cursor.{os.getpid()}")
    assert handle
    shared = Shared.from_address(kernel32.MapViewOfFile(handle, 0xF001F, 0, 0, ctypes.sizeof(Shared)))
    assert shared.on == 0 and shared.reads >= 1

    hwnd = user32.CreateWindowExW(0, "STATIC", "srkit-test", 0, 310, 220, 200, 200, None, None, None, None)
    assert hwnd
    try:
        shared.hwnd, shared.x, shared.y, shared.on = hwnd, 123, 45, 1
        want = wintypes.POINT(123, 45)
        user32.ClientToScreen(hwnd, ctypes.byref(want))
        assert dll.srhook_get_cursor_pos(ctypes.byref(pt)) and (pt.x, pt.y) == (want.x, want.y)
        assert (pt.x, pt.y) != (123, 45)    # 창 위치만큼 옮겨진 화면 좌표다
    finally:
        shared.on = 0
        user32.DestroyWindow(hwnd)


def test_wtsapi_exports_are_forwarded(dll):
    """프록시가 원래 WTSAPI32 함수를 시스템 DLL 로 넘기는지 확인."""
    real = ctypes.WinDLL(str(hook.system_dll()))
    for name in ("WTSRegisterSessionNotification", "WTSUnRegisterSessionNotification", "WTSFreeMemory"):
        proxy_fn = ctypes.cast(getattr(dll, name), ctypes.c_void_p).value
        assert proxy_fn == ctypes.cast(getattr(real, name), ctypes.c_void_p).value, name
