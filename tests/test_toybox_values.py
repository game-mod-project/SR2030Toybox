"""ToyBox 의 값 쓰기: 값 계산(values) · 게임의 값 읽기와 쓰기(game) · 요청의 대기열(keeper). 게임은 띄우지 않는다."""
import ctypes
import struct

import pytest

import toybox_fake_exe
from toybox_fake_game import LAYOUT, MULTIPLAYER, OPTIONS, POINTER, TABLE, WORLD_POINTER, FakeGame
from srkit import toybox

ADD, SET, FLOOR = 0, 1, 2                 # native/srtoybox/values.h 의 Change
WRITE, NOTHING, REFUSE = 0, 1, 2          # 〃 Verdict
NAN, INF = float("nan"), float("inf")
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF = range(6)      # native/srtoybox/game.h 의 Wrote
TREASURY = -1                                                       # 쓰기의 대상: 국고. 0 … 11 은 그 칸의 재고
READS, CALLS, WRITES = 1, 2, 4                                      # srtoybox_game_flags 의 비트
UNREAD = "게임 상태를 읽을 수 있을 때만 씁니다."
FAILED_OFF = "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다."


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_value.argtypes = [ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    lib.srtoybox_short_number.argtypes = [ctypes.c_double, ctypes.c_char_p, ctypes.c_int]
    pointer = ctypes.POINTER
    lib.srtoybox_values_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ValueLayout), ctypes.c_char_p,
                                         ctypes.c_int]
    lib.srtoybox_values_write.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ValueLayout), ctypes.c_int,
                                          ctypes.c_double]
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    lib.srtoybox_test_init.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong]
    lib.srtoybox_values_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
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


def germany() -> FakeGame:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 국고 $14.43 B. 물자 0 · 3 · 7 을 쓰고 재고가 1000 · 2500 · 0. 폴란드(141)의 국고는 $5 B."""
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.play(176)
    fake.set_treasury(176, 14.43e9)
    fake.set_treasury(141, 5e9)
    for slot, amount in ((0, 1000.0), (3, 2500.0), (7, 0.0)):
        fake.use(slot)
        fake.set_stock(176, slot, amount)
    return fake


def read(lib, fake: FakeGame) -> dict[str, str]:
    out = ctypes.create_string_buffer(1024)
    assert lib.srtoybox_values_read(fake.base, ctypes.byref(fake.at), ctypes.byref(fake.layout), out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def write(lib, fake: FakeGame, slot: int, amount: float) -> int:
    return lib.srtoybox_values_write(fake.base, ctypes.byref(fake.at), ctypes.byref(fake.layout), slot, amount)


def everything(fake: FakeGame) -> bytes:
    """가짜 게임의 메모리 전부(전역 · 세계 자료 · 지역 객체들) — 쓰기가 다른 곳을 건드리지 않았는지 볼 때 쓴다."""
    return bytes(fake.mem) + bytes(fake.world) + b"".join(fake.snapshot(index) for index in sorted(fake.objects))


def test_values_are_read_from_the_players_region(lib):
    assert read(lib, germany()) == {"ok": "1", "treasury": "14430000000", "used": "100100010000",
                                    "stock": "1000,0,0,2500,0,0,0,0,0,0,0,0"}


@pytest.mark.parametrize("flaw", ["menu", "no-world", "unreadable-world", "stock-nan"])
def test_values_are_not_read_when_the_game_does_not_add_up(lib, flaw):
    fake = germany()
    if flaw == "menu":
        fake.menu()
    elif flaw == "no-world":
        fake.poke(WORLD_POINTER, "<Q", 0)
    elif flaw == "unreadable-world":
        fake.poke(WORLD_POINTER, "<Q", 0x00007FFFFFFF0000)
    else:
        fake.set_stock(176, 9, float("nan"))                 # 쓰지 않는 물자의 칸이어도: 구조가 바뀐 것일 수 있다
    assert read(lib, fake)["ok"] == "0"


def test_a_write_changes_only_that_slot(lib):
    """쓰는 곳은 플레이어 지역 객체의 그 칸뿐이다. 둘레의 바이트 · 다른 지역 · 전역 · 치트 허용 비트는 그대로다."""
    fake = germany()
    before = everything(fake)
    assert write(lib, fake, TREASURY, 24.43e9) == DONE
    assert fake.treasury(176) == 24.43e9
    after = everything(fake)
    changed = [i for i in range(len(before)) if before[i] != after[i]]
    assert changed and set(changed) <= set(range(len(before) - 0x200 + LAYOUT["treasury"], len(before) - 0x200 + LAYOUT["treasury"] + 8))
    assert fake.treasury(141) == 5e9 and fake.peek(OPTIONS, "<I") == 0
    assert write(lib, fake, 3, 9999.0) == DONE
    assert fake.stock(176, 3) == 9999.0
    last = everything(fake)
    slot = len(before) - 0x200 + LAYOUT["stock_first"] + LAYOUT["stock_step"] * 3
    assert set(i for i in range(len(after)) if after[i] != last[i]) <= set(range(slot, slot + 4))
    assert write(lib, fake, TREASURY, -1e12) == DONE and fake.treasury(176) == -1e12      # 국고는 음수가 된다


@pytest.mark.parametrize("flaw", ["menu", "multiplayer", "inconsistent", "unreadable"])
def test_nothing_is_written_outside_a_game_it_can_trust(lib, flaw):
    fake = germany()
    if flaw == "menu":
        fake.menu()
    elif flaw == "multiplayer":
        fake.poke(MULTIPLAYER, "<B", 1)
    elif flaw == "inconsistent":
        struct.pack_into("<H", fake.objects[176], 4, 175)                 # 객체가 아는 자기 인덱스가 다르다
    else:
        fake.poke(POINTER, "<Q", 0x00007FFFFFFF0000)
        fake.poke(TABLE + 8 * 176, "<Q", 0x00007FFFFFFF0000)
    before = everything(fake)
    assert write(lib, fake, TREASURY, 1.0) == NOT_IN_GAME
    assert write(lib, fake, 3, 1.0) == NOT_IN_GAME
    assert everything(fake) == before


def test_a_value_or_a_slot_that_makes_no_sense_is_not_written(lib):
    fake = germany()
    before = everything(fake)
    for amount in (float("nan"), float("inf"), float("-inf")):
        assert write(lib, fake, TREASURY, amount) == BAD_VALUE
        assert write(lib, fake, 3, amount) == BAD_VALUE
    assert write(lib, fake, 3, -1.0) == BAD_VALUE                         # 재고는 음수가 되지 않는다
    assert write(lib, fake, 12, 1.0) == BAD_VALUE and write(lib, fake, -2, 1.0) == BAD_VALUE   # 없는 칸
    assert write(lib, fake, 5, 1.0) == NOT_USED                           # 이번 판에서 쓰지 않는 물자
    struct.pack_into("<f", fake.world, LAYOUT["used_first"] + LAYOUT["used_step"] * 3, float("nan"))
    assert write(lib, fake, 3, 1.0) == NOT_USED                           # "쓰는가"가 수가 아니다
    fake.poke(WORLD_POINTER, "<Q", 0)
    assert write(lib, fake, 0, 1.0) == NOT_USED                           # 세계 자료를 읽을 수 없다
    objects = len(fake.mem) + len(fake.world)
    assert everything(fake)[objects:] == before[objects:]                 # 지역 객체들은 그대로다(전역과 세계 자료는 방금 테스트가 고쳤다)


@pytest.mark.parametrize("protection", [0x02, 0x20], ids=["read-only", "execute-read"])
def test_a_slot_on_a_page_that_is_not_read_write_is_not_written(lib, protection):
    """낡은 포인터가 읽을 수는 있지만 쓰면 안 되는 곳을 가리킨다. WriteProcessMemory 는 실행 쪽이면 보호를 풀고 쓴다 —
    그 전에 가려야 한다. 죽지 않고 실패로 돌아온다."""
    fake = germany()
    fake.lock(176, protection)
    fake.play(176)
    assert read(lib, fake)["ok"] == "1"                                   # 읽기는 된다
    before = fake.snapshot(176)
    assert write(lib, fake, TREASURY, 1.0) == FAILED
    assert write(lib, fake, 3, 1.0) == FAILED
    assert fake.snapshot(176) == before


@pytest.fixture(scope="module")
def all_sigs(lib):
    """DLL 에 든 서명 표 둘: ([상태 묶음 21개], [값 묶음 12개]) — 저마다 (찾을 것, 서명 글)."""
    return ([(row.name, row.text) for row in toybox.state_of(lib, b"")[2]],
            [(row.name, row.text) for row in toybox.values_of(lib, b"")[2]])


def init(lib, image: bytes, tmp_path, monkeypatch) -> tuple[int, str, str]:
    """게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다: (아는 것의 비트, 값을 쓸 수 없는 까닭, 로그)."""
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    try:
        lib.srtoybox_test_init(image, len(image))
        flags, off = lib.srtoybox_game_flags(), text(lib.srtoybox_values_off)
    finally:
        lib.srtoybox_test_game(None, None, None)              # 이미지를 놓기 전에 이 프로세스의 "게임"을 비운다
    log = tmp_path / "toybox.log"
    return flags, off, log.read_text(encoding="utf-8") if log.is_file() else ""


def test_startup_finds_the_state_and_the_values_without_any_cheat(lib, all_sigs, tmp_path, monkeypatch):
    """치트가 없는 빌드: 상태를 읽고 값을 쓴다. 명령 처리 함수는 없다 — 그것으로 도는 기능만 글쇠 방식이다."""
    state, values = all_sigs
    flags, off, log = init(lib, toybox_fake_exe.sig_image(state + values), tmp_path, monkeypatch)
    assert flags == READS | WRITES and off == ""
    assert "게임 상태를 읽습니다 (서명 21개 가운데 21개" in log
    assert "값을 씁니다 (국고 +0x1230, 재고 +0x2000 간격 0x20 × 12)" in log
    assert "명령 처리 함수를 찾지 못했습니다" in log and "맞지 않은 서명" not in log


def test_startup_without_the_values_keeps_everything_else(lib, all_sigs, tmp_path, monkeypatch):
    """값 묶음만 못 찾으면 돈 탭만 꺼진다. 까닭이 로그와 창에 같은 글로 남는다."""
    state, _values = all_sigs
    flags, off, log = init(lib, toybox_fake_exe.build(state), tmp_path, monkeypatch)
    assert flags == READS | CALLS
    assert off == "이 게임 판에서는 쓸 수 없습니다 (세계 자료 포인터: 서명 3개 가운데 0개)"
    assert "값을 쓸 수 없습니다 (세계 자료 포인터: 서명 3개 가운데 0개)" in log
    assert "옛 방식(내장 치트)으로 도는 기능이" in log


def test_startup_names_the_signatures_that_did_not_match(lib, all_sigs, tmp_path, monkeypatch):
    """셋 가운데 둘로 찾았을 때도, 맞지 않은 서명이 무엇인지 로그에 남는다 — 다음 업데이트에서 깨질 것을 미리 안다."""
    state, values = all_sigs
    flags, _off, log = init(lib, toybox_fake_exe.sig_image(state + values, broken={0, 22}), tmp_path, monkeypatch)
    assert flags == READS | WRITES
    assert "게임 상태를 읽습니다 (서명 21개 가운데 20개" in log
    assert "맞지 않은 서명: multiplayer #1 (안 맞음)" in log and "맞지 않은 서명: world_pointer #2 (안 맞음)" in log


def test_startup_with_everything(lib, all_sigs, tmp_path, monkeypatch):
    state, values = all_sigs
    flags, off, _log = init(lib, toybox_fake_exe.build(state + values), tmp_path, monkeypatch)
    assert flags == READS | CALLS | WRITES and off == ""


@pytest.mark.parametrize("image", [b"", bytes(0x1000)], ids=["empty", "zeros"])
def test_startup_in_something_that_is_not_the_game(lib, image, tmp_path, monkeypatch):
    flags, off, log = init(lib, image, tmp_path, monkeypatch)
    assert flags == 0 and off == UNREAD
    assert "게임 상태를 읽을 수 없습니다" in log and "맞지 않은 서명" not in log     # 스물한 줄을 쏟아 내지 않는다
