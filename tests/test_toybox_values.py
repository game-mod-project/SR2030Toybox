"""ToyBox 의 값 쓰기: 값 계산(values) · 게임의 값 읽기와 쓰기(game) · 요청의 대기열(keeper). 게임은 띄우지 않는다."""
import ctypes

import pytest

from srkit import toybox

ADD, SET, FLOOR = 0, 1, 2                 # native/srtoybox/values.h 의 Change
WRITE, NOTHING, REFUSE = 0, 1, 2          # 〃 Verdict
NAN, INF = float("nan"), float("inf")


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_value.argtypes = [ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    lib.srtoybox_short_number.argtypes = [ctypes.c_double, ctypes.c_char_p, ctypes.c_int]
    return lib


def text(call, *args, size: int = 4096) -> str | None:
    """글을 돌려주는 내보내기 함수를 부른다. 함수가 -1 을 주면 None."""
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return None if n < 0 else buf.raw[:n].decode("utf-8")


def value(lib, stock: bool, now: float, change: int, amount: float) -> tuple[int, float | None]:
    """(판정, 쓸 값). 쓰지 않으면 쓸 값은 None."""
    out = ctypes.c_double(-1.0)
    verdict = lib.srtoybox_value(int(stock), now, change, amount, ctypes.byref(out))
    return verdict, (out.value if verdict == WRITE else None)


def test_treasury_values(lib):
    assert value(lib, False, 14.43e9, ADD, 10e9) == (WRITE, 24.43e9)
    assert value(lib, False, 14.43e9, ADD, -100e9) == (WRITE, 14.43e9 - 100e9)    # 국고는 음수가 될 수 있다
    assert value(lib, False, 14.43e9, SET, 0.0) == (WRITE, 0.0)
    assert value(lib, False, 5.0, SET, 5.0) == (NOTHING, None)                    # 이미 그 값이다
    assert value(lib, False, 1e9, FLOOR, 5e9) == (WRITE, 5e9)
    assert value(lib, False, 9e9, FLOOR, 5e9) == (NOTHING, None)                  # 바닥 위다
    assert value(lib, False, 9.99e14, ADD, 1e14) == (WRITE, 1e15)                 # ±$1,000 T 안으로 자른다
    assert value(lib, False, -9.99e14, ADD, -1e14) == (WRITE, -1e15)
    assert value(lib, False, 5e15, FLOOR, 1e9) == (NOTHING, None)                 # 바닥은 값을 내리지 않는다 — 한도 밖의 값이어도


def test_stock_values(lib):
    assert value(lib, True, 1000.0, ADD, 1e6) == (WRITE, 1001000.0)
    assert value(lib, True, 1000.0, ADD, -1e8) == (WRITE, 0.0)                    # 0 아래로 내려가지 않는다
    assert value(lib, True, 0.0, ADD, -5.0) == (NOTHING, None)
    assert value(lib, True, 1000.0, SET, -3.0) == (WRITE, 0.0)
    assert value(lib, True, 9.99e8, ADD, 1e8) == (WRITE, 1e9)                     # 10억 이하로 자른다
    assert value(lib, True, 800.0, FLOOR, 1000.0) == (WRITE, 1000.0)
    assert value(lib, True, 1200.0, FLOOR, 1000.0) == (NOTHING, None)
    assert value(lib, True, 16777216.0, ADD, 1.0) == (NOTHING, None)              # float 의 눈금보다 작은 변화는 쓸 것이 없다


@pytest.mark.parametrize("now, amount", [(NAN, 1.0), (INF, 1.0), (-INF, 1.0), (1.0, NAN), (1.0, INF)],
                         ids=["now-nan", "now-inf", "now-minus-inf", "amount-nan", "amount-inf"])
def test_values_refuse_what_is_not_a_number(lib, now, amount):
    """지금 값이 수가 아니면 구조가 바뀐 것일 수 있다 — "이 값으로"조차 쓰지 않는다."""
    for stock in (False, True):
        for change in (ADD, SET, FLOOR):
            assert value(lib, stock, now, change, amount) == (REFUSE, None)


def test_short_numbers_look_like_the_games(lib):
    """게임의 재무 패널과 같은 줄임 표기($ 14.43 B, $50.00 K)."""
    short = lambda v: text(lib.srtoybox_short_number, v)
    assert [short(v) for v in (0, 7, 999.4, 1000, 50000, 14.43e9, 1.1e6, 999999, 1e12, -1e12, -24.5e9, 0.3, -0.3)] == \
        ["0", "7", "999", "1.00 K", "50.00 K", "14.43 B", "1.10 M", "1.00 M", "1.00 T", "-1.00 T", "-24.50 B", "0", "0"]
    assert short(NAN) == "?" and short(INF) == "?"
