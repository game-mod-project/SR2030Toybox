"""ToyBox 의 배율(묶음 7): 곱 보정 칸의 유지, 날마다의 일(세금 · 국방비 · 연구 속도), 설정의 줄, 주소 찾기.

가짜 게임(tests/toybox_fake_game.py)에 곱 보정 표 · 날의 칸 · 예산 칸을 붙여 본다. 설치된 게임에서는 서명이 찾아내는 자리만 본다.
"""
import ctypes
import struct

import pytest

from srkit import toybox
from toybox_fake_game import Lab, FakeGame, TECH

MUL_TABLE, MUL_STEP, DAY = 0x4000, 0x320, 0x70
CELLS = dict(tax_total=0x180, army_pay_level=0x188, army_upkeep_level=0x18C, army_pay=0x190, army_upkeep=0x194, unit_cost=0x198,
             research_step=0x19C, social_cost=0x1A0, social_level=0x1C0)
GERMANY, POLAND = 176, 141
ACTIVE, GONE = 0x40000000, 0x80000000
PART_CELLS, PART_MONEY, PART_SPEED, PART_SOCIAL = 0, 1, 2, 3
BUILD_MULT = {"mul_table": 0x1CEE6C8, "day": 0x18294D0, "tax_total": 0xA6B8, "army_pay_level": 0xA6DC, "army_upkeep_level": 0xA6E0,
              "army_pay": 0x14CE0, "army_upkeep": 0x14CE4, "unit_cost": 0x14BDC, "research_step": 0x15E5C, "social_cost": 0x14C04,
              "social_level": 0xA680}    # build 21347933


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    for name in ("srtoybox_test_values", "srtoybox_test_more", "srtoybox_test_mult"):
        getattr(lib, name).argtypes = [ctypes.c_void_p]
    lib.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_keeper_tick_at.argtypes = [ctypes.c_ulonglong]
    lib.srtoybox_keeper_mult.argtypes = [ctypes.c_char_p]
    lib.srtoybox_mult_off.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_mult_stats.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_keeper_rush.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_settings_normalize.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    return lib


def text(call, *args, size: int = 8192) -> str:
    out = ctypes.create_string_buffer(size)
    assert call(*args, out, size) >= 0
    return out.value.decode("utf-8")


class Game:
    """독일(176)로 진행 중인 가짜 게임 + 곱 보정 표 · 날의 칸 · 예산 칸 · 연구 목록. 폴란드(141)가 다른 나라다."""

    def __init__(self, lib):
        self.lib = lib
        self.fake = FakeGame(0x28000)
        self.fake.region(POLAND, 1106, alive=3)
        self.fake.region(GERMANY, 1499)
        self.fake.play(GERMANY)
        self.fake.set_treasury(GERMANY, 10e9)
        self.fake.set_treasury(POLAND, 5e9)
        for index in (GERMANY, POLAND):
            for cell in range(200):
                self.set_cell(index, cell, 1.0 + cell / 100.0)
            self.budget(index, tax=365e9, levels=(1.0, 0.5), army=(36.5e9, 73e9), units=10e6, step=0.5)
        self.lab = Lab(self.fake)
        self.mult = toybox.MultLayout(mul_table=MUL_TABLE, day=DAY, **CELLS)
        self.now = 1000
        lib.srtoybox_test_game(self.fake.base, ctypes.byref(self.fake.at))
        lib.srtoybox_test_values(ctypes.byref(self.fake.layout))
        lib.srtoybox_test_more(ctypes.byref(self.fake.more))
        lib.srtoybox_test_research(ctypes.byref(self.lab.layout), None)
        lib.srtoybox_test_mult(ctypes.byref(self.mult))
        lib.srtoybox_keeper_reset()

    def cell(self, index: int, cell: int) -> float:
        return self.fake.peek(MUL_TABLE + MUL_STEP * index + 4 * cell, "<f")

    def set_cell(self, index: int, cell: int, value: float) -> None:
        self.fake.poke(MUL_TABLE + MUL_STEP * index + 4 * cell, "<f", value)

    def budget(self, index: int, tax: float, levels: tuple[float, float], army: tuple[float, float], units: float, step: float) -> None:
        self.fake._write(index, CELLS["tax_total"], "<d", tax)
        for name, value in (("army_pay_level", levels[0]), ("army_upkeep_level", levels[1]), ("army_pay", army[0]),
                            ("army_upkeep", army[1]), ("unit_cost", units), ("research_step", step)):
            self.fake._write(index, CELLS[name], "<f", value)
        for i in range(8):                                      # 사회 지출: 비용 73e9 × (i + 1) / 년, 수준 0.5 — 하루 합 3.6e9
            self.fake._write(index, CELLS["social_cost"] + 4 * i, "<f", 73e9 * (i + 1))
            self.fake._write(index, CELLS["social_level"] + 4 * i, "<f", 0.5)

    def day(self, add: int = 1) -> None:
        self.fake.poke(DAY, "<I", (self.fake.peek(DAY, "<I") + add) & 0xFFFFFFFF)

    def set(self, spec: str) -> None:
        assert self.lib.srtoybox_keeper_mult(spec.encode()) == 0

    def tick(self) -> None:
        self.now += 500
        self.lib.srtoybox_keeper_tick_at(self.now)

    def stats(self) -> list[int]:
        return [int(n) for n in text(self.lib.srtoybox_mult_stats).split("\t")]

    def rush(self) -> str:
        return text(self.lib.srtoybox_keeper_rush)

    def pending(self) -> bool:
        return self.lib.srtoybox_rush_pending() == 1

    def recompute(self) -> None:
        """게임이 날 끝에 하는 "효과를 다시 셈": 플레이어 줄을 처음 값으로."""
        for cell in range(200):
            self.set_cell(GERMANY, cell, 1.0 + cell / 100.0)

    def node(self, number: int, flags: tuple[int, int], left: float) -> int:
        at = self.lab.queue(GERMANY, TECH, number, flags)
        ctypes.memmove(at + 0x28, struct.pack("<f", left), 4)
        return at

    @staticmethod
    def left(node: int) -> float:
        return struct.unpack("<f", ctypes.string_at(node + 0x28, 4))[0]


@pytest.fixture
def game(lib, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    g = Game(lib)
    yield g
    lib.srtoybox_keeper_reset()
    lib.srtoybox_test_game(None, None)


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def test_nothing_is_written_while_the_switch_is_off(game):
    game.set("tax=200 out.0=300 research=500")
    game.tick()
    game.day()
    before = bytes(game.fake.mem)
    game.tick()
    assert bytes(game.fake.mem) == before and game.fake.treasury(GERMANY) == 10e9
    assert game.stats() == [0, 0, 0, 3]


def test_the_cells_are_multiplied_only_in_the_players_row(game):
    """생산(72 + 칸) · 인구 소비(60 + 칸) · 산업 소비(24 + 칸). 다른 나라의 줄과 맡지 않는 칸(사회 지출 비용의 108 … 115 도)은 그대로다."""
    poland = [game.cell(POLAND, c) for c in range(200)]
    germany = [game.cell(GERMANY, c) for c in range(200)]
    game.set("on=1 out.0=200 use.8=50 raw.3=10 social=150")
    game.tick()
    want = {72: 2.0, 68: 0.5, 27: 0.1}
    for cell in range(200):
        assert game.cell(GERMANY, cell) == f32(germany[cell] * f32(want.get(cell, 1.0))), cell
    assert [game.cell(POLAND, c) for c in range(200)] == poland
    assert game.stats() == [0, 3, 3, 4]


def test_build_speeds_multiply_cells_15_and_16(game):
    """유닛 생산 속도(15) · 시설 건설 속도(16). 다른 나라의 줄은 그대로다."""
    poland = [game.cell(POLAND, c) for c in range(200)]
    game.set("on=1 unitbuild=500 facbuild=200")
    game.tick()
    assert game.cell(GERMANY, 15) == f32(f32(1.15) * 5) and game.cell(GERMANY, 16) == f32(f32(1.16) * 2)
    assert [game.cell(POLAND, c) for c in range(200)] == poland
    assert game.stats() == [0, 2, 2, 2]
    game.set("unitbuild=100")
    game.tick()
    assert game.cell(GERMANY, 15) == f32(1.15)


def test_rush_writes_a_thousand_times_until_the_game_recomputes_after_the_day(game):
    """스위치가 꺼져 있어도 듣는다. 날이 오르기만 해서는(그날의 셈 도중) 풀지 않는다."""
    assert game.rush() == "" and game.pending()
    game.tick()
    assert game.cell(GERMANY, 15) == f32(f32(1.15) * 1000) and game.cell(GERMANY, 16) == f32(f32(1.16) * 1000)
    assert game.cell(GERMANY, 72) == f32(1.72)                  # 다른 칸은 그대로
    game.day()
    game.tick()
    assert game.pending() and game.cell(GERMANY, 15) == f32(f32(1.15) * 1000)
    game.recompute()
    game.tick()
    assert not game.pending() and game.cell(GERMANY, 15) == f32(1.15) and game.cell(GERMANY, 16) == f32(1.16)


def test_a_recompute_before_midnight_is_written_over_again(game):
    game.rush()
    game.tick()
    game.recompute()                                            # 연구가 끝나 낮에 다시 셈했다
    game.tick()
    assert game.pending() and game.cell(GERMANY, 15) == f32(f32(1.15) * 1000)


def test_after_the_rush_the_multipliers_take_over(game):
    game.set("on=1 unitbuild=200")
    game.tick()
    game.rush()
    game.set("unitbuild=300")                                   # 대기 중의 변경은 대기 값을 바꾸지 않는다
    game.tick()
    assert game.cell(GERMANY, 15) == f32(f32(1.15) * 1000)
    game.day()
    game.recompute()
    game.tick()
    assert not game.pending() and game.cell(GERMANY, 15) == f32(f32(1.15) * 3)


@pytest.mark.parametrize("change", ["player", "menu"])
def test_the_rush_is_dropped_when_the_game_changes(game, change):
    game.rush()
    game.tick()
    if change == "player":
        game.fake.play(POLAND)
    else:
        game.fake.menu()
    game.tick()
    assert not game.pending()
    assert [game.cell(POLAND, c) for c in (15, 16)] == [f32(1.15), f32(1.16)]


@pytest.mark.parametrize("value", [0.0, -1.0, 1000.0])
def test_the_rush_leaves_a_cell_that_makes_no_sense(game, value):
    game.set_cell(GERMANY, 15, value)
    game.rush()
    game.tick()
    assert game.cell(GERMANY, 15) == f32(value)
    assert game.cell(GERMANY, 16) == f32(f32(1.16) * 1000)


def test_the_rush_needs_a_game(game):
    game.fake.menu()
    assert game.rush() != "" and not game.pending()


def test_the_cells_are_written_again_after_the_game_recomputes_them(game):
    game.set("on=1 out.0=200")
    game.tick()
    base = f32(1.72)
    assert game.cell(GERMANY, 72) == f32(base * 2)
    game.tick()
    assert game.stats()[1] == 1                                 # 그대로면 다시 쓰지 않는다
    game.set_cell(GERMANY, 72, 1.9)                             # 게임이 다시 셈했다(연구가 끝나 값도 달라졌다)
    game.tick()
    assert game.cell(GERMANY, 72) == f32(f32(1.9) * 2) and game.stats()[1] == 2


def test_a_changed_percent_is_applied_to_the_games_value_not_to_ours(game):
    game.set("on=1 out.0=200")
    game.tick()
    game.set("out.0=300")
    game.tick()
    assert game.cell(GERMANY, 72) == f32(f32(1.72) * 3)


@pytest.mark.parametrize("off", ["on=0", "out.0=100"])
def test_turning_it_off_puts_the_games_value_back(game, off):
    game.set("on=1 out.0=200")
    game.tick()
    game.set(off)
    game.tick()
    assert game.cell(GERMANY, 72) == f32(1.72) and game.stats()[2] == 0
    game.tick()
    assert game.stats()[1] == 2                                 # 되돌린 뒤에는 쉰다


def test_a_cell_the_game_recomputed_is_not_put_back_when_turned_off(game):
    """끌 때 그 칸이 이미 게임의 값이면(게임이 다시 셈했다) 건드리지 않는다."""
    game.set("on=1 out.0=200")
    game.tick()
    game.set_cell(GERMANY, 72, 1.9)
    game.set("on=0")
    game.tick()
    assert game.cell(GERMANY, 72) == f32(1.9) and game.stats()[1] == 1


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), 1000.0])
def test_a_cell_that_makes_no_sense_is_left_alone(game, value):
    game.set_cell(GERMANY, 72, value)
    before = bytes(game.fake.mem)
    game.set("on=1 out.0=200")
    game.tick()
    assert bytes(game.fake.mem) == before


def test_the_other_country_is_left_alone_after_the_player_changes(game):
    game.set("on=1 out.0=200")
    game.tick()
    germany = game.cell(GERMANY, 72)
    game.fake.play(POLAND)
    game.tick()
    assert game.cell(GERMANY, 72) == germany                    # 앞 나라의 칸은 게임이 그날 다시 셈한다 — ToyBox 는 손대지 않는다
    assert game.cell(POLAND, 72) == f32(f32(1.72) * 2)


def test_taxes_and_defense_move_the_treasury_once_a_day(game):
    """세수 365e9 / 년 = 하루 1e9. 국방 = (1.0 × 36.5e9 + 0.5 × 73e9) / 365 + 10e6 = 210e6."""
    game.set("on=1 tax=150 defense=0")
    game.tick()                                                 # 날의 칸을 처음 봤다 — 맞추기만 한다
    assert game.fake.treasury(GERMANY) == 10e9
    game.day()
    game.tick()
    assert game.fake.treasury(GERMANY) == pytest.approx(10e9 + 0.5e9 + 210e6, rel=1e-9)
    game.tick()                                                 # 같은 날에는 한 번만
    assert game.fake.treasury(GERMANY) == pytest.approx(10e9 + 0.5e9 + 210e6, rel=1e-9)
    assert game.fake.treasury(POLAND) == 5e9 and game.stats()[0] == 1


def test_social_spending_moves_the_treasury_once_a_day(game):
    """하루치 사회 지출 = Σ 73e9 × (i + 1) × 0.5 / 365 = 3.6e9. 50 % 면 그 절반을 국고에 돌려준다. 곱 보정 칸은 건드리지 않는다."""
    cells = bytes(game.fake.mem)[MUL_TABLE:]
    game.set("on=1 social=50")
    game.tick()
    game.day()
    game.tick()
    assert game.fake.treasury(GERMANY) == pytest.approx(10e9 + 1.8e9, rel=1e-6) and bytes(game.fake.mem)[MUL_TABLE:] == cells
    game.set("social=200 tax=200")                              # 세금과 함께: +1e9 − 3.6e9
    game.day()
    game.tick()
    assert game.fake.treasury(GERMANY) == pytest.approx(10e9 + 1.8e9 + 1e9 - 3.6e9, rel=1e-6)


def test_days_that_passed_between_two_looks_are_all_counted(game):
    game.set("on=1 tax=200")
    game.tick()
    game.day(3)
    game.tick()
    assert game.fake.treasury(GERMANY) == pytest.approx(13e9, rel=1e-9) and game.stats()[0] == 3


@pytest.mark.parametrize("jump", [4, 400, -1, -30])
def test_a_jump_of_the_day_is_a_new_game_not_days(game, jump):
    """불러오기 · 새 판: 날의 칸이 뒤로 가거나 멀리 뛴다. 그때는 다시 맞추기만 한다."""
    game.set("on=1 tax=200")
    game.day(100)
    game.tick()
    game.day(jump)
    game.tick()
    assert game.fake.treasury(GERMANY) == 10e9
    game.day()
    game.tick()
    assert game.fake.treasury(GERMANY) == pytest.approx(11e9, rel=1e-9)


def test_the_day_is_matched_again_when_the_player_changes(game):
    game.set("on=1 tax=200")
    game.tick()
    game.fake.play(POLAND)
    game.day()
    game.tick()
    assert game.fake.treasury(POLAND) == 5e9 and game.fake.treasury(GERMANY) == 10e9
    game.day()
    game.tick()
    assert game.fake.treasury(POLAND) == pytest.approx(6e9, rel=1e-9) and game.fake.treasury(GERMANY) == 10e9


def test_research_speed_takes_more_off_the_running_nodes(game):
    """하루치 0.5일 × (500 % − 1) = 2일을 더 뺀다. 진행 중이 아닌 노드 · 빠진 노드는 그대로, 0.001 아래로는 내리지 않는다."""
    running = game.node(10, (1, ACTIVE | 0x20000001), 10.0)
    waiting = game.node(11, (1, 0), 10.0)
    gone = game.node(12, (1, ACTIVE | GONE), 10.0)
    nearly = game.node(13, (1, ACTIVE), 1.5)
    game.set("on=1 research=500")
    game.tick()
    game.day()
    game.tick()
    assert [game.left(n) for n in (running, waiting, gone, nearly)] == [8.0, 10.0, 10.0, f32(0.001)]
    assert game.fake.treasury(GERMANY) == 10e9 and game.stats()[0] == 1


def test_research_can_be_slowed_too(game):
    running = game.node(10, (1, ACTIVE), 10.0)
    game.set("on=1 research=50")
    game.tick()
    game.day()
    game.tick()
    assert game.left(running) == 10.25


def test_nothing_happens_in_the_menu_or_in_multiplayer(game):
    game.set("on=1 tax=200 out.0=200")
    game.fake.menu()
    before = bytes(game.fake.mem)
    game.tick()
    game.day()
    game.tick()
    game.day(-1)
    assert bytes(game.fake.mem) == before
    game.fake.play(GERMANY)
    game.fake.poke(0x10, "<B", 1)                               # 멀티플레이
    before = bytes(game.fake.mem)
    game.tick()
    assert bytes(game.fake.mem) == before


def test_each_part_says_why_it_is_off(lib, game):
    off = lambda part: text(lib.srtoybox_mult_off, part)
    assert [off(p) for p in (PART_CELLS, PART_MONEY, PART_SPEED, PART_SOCIAL)] == ["", "", "", ""]
    lib.srtoybox_test_mult(ctypes.byref(toybox.MultLayout(**{**dict(mul_table=MUL_TABLE, day=DAY, **CELLS), "social_level": 0})))
    assert off(PART_SOCIAL) != "" and off(PART_MONEY) == ""     # 사회 지출의 칸만 못 찾으면 그것만 꺼진다
    lib.srtoybox_test_mult(ctypes.byref(toybox.MultLayout(mul_table=MUL_TABLE)))
    assert off(PART_CELLS) == "" and off(PART_MONEY) != "" and off(PART_SPEED) != ""
    lib.srtoybox_test_mult(ctypes.byref(toybox.MultLayout(day=DAY, **CELLS)))
    assert off(PART_CELLS) != "" and off(PART_MONEY) == "" and off(PART_SPEED) == ""
    game.set("on=1 tax=200 out.0=200")
    before = bytes(game.fake.mem)[MUL_TABLE:]
    game.tick()
    game.day()
    game.tick()
    assert bytes(game.fake.mem)[MUL_TABLE:] == before and game.fake.treasury(GERMANY) == pytest.approx(11e9, rel=1e-9)
    lib.srtoybox_test_research(None, None)                      # 연구 묶음이 없으면 연구 속도만 꺼진다
    assert off(PART_SPEED) != "" and off(PART_MONEY) == ""


def test_the_settings_keep_the_multipliers(lib):
    norm = lambda ini: dict(line.split("=") for line in text(lib.srtoybox_settings_normalize, ini.encode("utf-8")).split("\n") if line)
    got = norm("mult.on=1\nmult.tax=250\nmult.defense=0\nmult.social=0\nmult.research=10\nmult.out.0=1000\nmult.use.10=50\nmult.raw.3=1\n")
    assert [got[k] for k in ("mult.on", "mult.tax", "mult.defense", "mult.social", "mult.research", "mult.out.0", "mult.use.10",
                             "mult.raw.3")] == ["1", "250", "0", "0", "10", "1000", "50", "1"]
    # 범위 밖 · 없는 칸 · 모르는 줄은 버린다(100 이 남는다)
    bad = norm("mult.on=2\nmult.tax=1001\nmult.defense=-1\nmult.social=1001\nmult.research=9\nmult.out.0=0\nmult.out.11=200\nmult.xyz.1=5\n")
    assert bad["mult.on"] == "0" and all(bad[k] == "100" for k in ("mult.tax", "mult.defense", "mult.social", "mult.research", "mult.out.0"))
    assert "mult.out.11" not in bad and "mult.xyz.1" not in bad
    got = norm("mult.unitbuild=1000\nmult.facbuild=1\n")
    assert got["mult.unitbuild"] == "1000" and got["mult.facbuild"] == "1"
    bad = norm("mult.unitbuild=0\nmult.facbuild=1001\n")
    assert bad["mult.unitbuild"] == "100" and bad["mult.facbuild"] == "100"


def test_the_addresses_are_found_in_the_installed_game(lib, game_dir):
    """설치된 게임에서: 찾을 것 열하나가 모두, 서명 서른셋이 모두 정확히 한 번(build 21347933 의 값과 같다)."""
    image = toybox.image_of((game_dir / toybox.EXE_NAME).read_bytes())
    found, why, rows = toybox.mult_of(lib, image)
    assert why == [""] * len(toybox.MULT_FIELDS) and [row.count for row in rows] == [1] * 33
    if found != BUILD_MULT:
        pytest.skip(f"다른 빌드의 게임입니다: {found}")


def test_nothing_is_found_in_something_that_is_not_the_game(lib):
    found, why, _rows = toybox.mult_of(lib, bytes(0x1000))
    assert not any(found.values()) and all(why)
