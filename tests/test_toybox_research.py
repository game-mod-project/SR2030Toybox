"""ToyBox 의 연구: 규칙(research) · 게임의 표 읽기와 쓰기(game). 게임은 띄우지 않는다.

규칙은 게임이 스스로 쓰는 것 그대로다(docs/11-game-internals.md): 기술을 주면 선행 기술도 주고, 빼면 그 기술에 기대는 기술 · 설계도 뺀다.
앞쪽은 표를 글로 지어 규칙만 보고, 뒤쪽은 가짜 게임 메모리(toybox_fake_game.Lab)에서 표를 읽고 비트를 쓰는 것을 본다.
"""
import ctypes
import struct

import pytest

import toybox_fake_exe
from toybox_fake_game import DESIGN, DESIGN_SIZE, ENDED, GONE, INDEX, MULTIPLAYER, OWNERS_BYTES, RESEARCH, TECH, TECH_SIZE, FakeGame, \
    Lab, kernel32, locked_page, standard_lab
from srkit import toybox

COMPLETE, REVOKE = 0, 1
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF, NO_TARGET, UNREADABLE, CRASHED = range(9)   # native/srtoybox/game.h 의 Wrote
GERMANY, POLAND, DENMARK = 176, 141, 150                                                         # 지역 인덱스
RECOMPUTE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)                                # "다시 셈" 자리에 두는 함수의 꼴


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    pointer = ctypes.POINTER
    lib.srtoybox_research_plan.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_research_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ResearchLayout), ctypes.c_int,
                                           ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_research_write.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ResearchLayout), ctypes.c_void_p,
                                            ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    return lib


def tech(number: int, *needs: int, mine: bool = False, level: int = 10, kind: int = 1, housed: bool = True) -> str:
    """기술 한 줄. housed: 보유 비트 묶음이 있다(누군가 보유한 적이 있다) — 내가 보유했으면 늘 있다."""
    first, second = (list(needs) + [0, 0])[:2]
    return f"t {number} {kind} {level} {first} {second} {int(mine)} {int(housed or mine)}"


def design(number: int, *needs: int, mine: bool = False, is_open: bool = True, held: bool = False, housed: bool = True) -> str:
    return f"d {number} {int(is_open)} {int(held)} {int(mine)} {int(housed or mine)} " + " ".join(
        str(n) for n in (list(needs) + [0] * 4)[:4])


def node(kind: int, number: int, first: int = 1, second: int = 0) -> str:
    return f"q {kind} {number} {first:x} {second:x}"


def plan(lib, rows: list[str], what: str, action: int = COMPLETE, slots: tuple[int, int] = (64, 64), can_house: bool = True) -> dict:
    """규칙을 돌린 결과: techs · designs(비트를 바꿀 번호), nodes(대기열에서 뺄 노드의 칸), asked(고른 기술 · 설계의 수),
    skipped(묶음이 없어 건너뛴 항목의 수), queued(표에서 대기열에 있는 것으로 읽힌 항목), text(알림의 글)."""
    out = ctypes.create_string_buffer(1 << 16)
    table = "\n".join([f"slots {slots[0]} {slots[1]}"] + rows)
    assert lib.srtoybox_research_plan(table.encode(), action, what.encode(), int(can_house), out, len(out)) >= 0
    lines = dict(line.split(" ", 1) if " " in line else (line, "") for line in out.value.decode("utf-8").split("\n"))
    return {"techs": [int(n) for n in lines["techs"].split()], "designs": [int(n) for n in lines["designs"].split()],
            "nodes": [int(n) for n in lines["nodes"].split()], "asked": tuple(int(n) for n in lines["asked"].split()),
            "skipped": int(lines["skipped"]), "queued": lines["queued"].split(), "text": lines["text"]}


def test_completing_a_tech_brings_its_prerequisites_up_the_chain(lib):
    """기술 3 은 2 를, 2 는 1 을 선행으로 갖는다. 3 을 완료로 하면 셋 다 — 게임의 "기술을 준다"와 같다."""
    got = plan(lib, [tech(1), tech(2, 1), tech(3, 2)], "items t3")
    assert got["techs"] == [1, 2, 3] and got["asked"] == (1, 0)
    assert got["text"] == "기술 3개(선행 2개 포함)"


def test_a_prerequisite_already_held_is_left_alone_and_so_is_what_lies_behind_it(lib):
    """2 를 이미 보유했다. 3 을 완료로 해도 2 는 넣지 않고, 2 의 선행(1 — 보유하지 않았다)도 보지 않는다(게임이 그렇게 한다)."""
    got = plan(lib, [tech(1), tech(2, 1, mine=True), tech(3, 2)], "items t3")
    assert got["techs"] == [3] and got["text"] == "기술 1개"


def test_both_prerequisites_are_followed(lib):
    got = plan(lib, [tech(1), tech(2), tech(3, 1, 2), tech(4)], "items t3")
    assert got["techs"] == [1, 2, 3]


def test_prerequisites_that_are_not_real_techs_are_skipped(lib):
    """선행의 번호가 0 이거나, 표의 자리 수 이상이거나, 빈 자리(쓰지 않는 번호)면 건너뛴다."""
    got = plan(lib, [tech(3, 0, 99), tech(4, 63, 7)], "items t3 t4")       # 자리 수는 64 다. 63 과 7 은 표에 없다
    assert got["techs"] == [3, 4] and got["asked"] == (2, 0)


def test_prerequisites_that_point_at_each_other_still_end(lib):
    got = plan(lib, [tech(1, 2), tech(2, 1)], "items t1")
    assert got["techs"] == [1, 2] and got["asked"] == (1, 0)


def test_what_is_already_held_is_not_in_the_plan(lib):
    got = plan(lib, [tech(1, mine=True), design(5, mine=True)], "items t1 d5")
    assert got == {"techs": [], "designs": [], "nodes": [], "asked": (0, 0), "skipped": 0, "queued": [], "text": ""}


def test_numbers_that_are_not_in_the_table_and_repeats_are_ignored(lib):
    got = plan(lib, [tech(1)], "items t1 t1 t9 t0 d9 t999")
    assert got["techs"] == [1] and got["asked"] == (1, 0) and got["designs"] == []


def test_something_asked_for_is_not_counted_as_a_prerequisite(lib):
    """고른 것 둘 가운데 하나가 다른 하나의 선행이어도 둘 다 "고른 것"이다 — 어느 것을 먼저 적었든."""
    for what in ("items t1 t2", "items t2 t1"):
        got = plan(lib, [tech(1), tech(2, 1)], what)
        assert got["techs"] == [1, 2] and got["asked"] == (2, 0) and got["text"] == "기술 2개"
    got = plan(lib, [tech(1), design(5, 1)], "items d5 t1")           # 설계의 선행을 따로 고르기도 했다
    assert got["techs"] == [1] and got["asked"] == (1, 1) and got["text"] == "기술 1개 · 부대 설계 1개"


def test_a_design_brings_the_techs_it_needs(lib):
    """부대 설계 5 는 기술 1 · 2 를 선행으로 갖고, 1 은 3 을 선행으로 갖는다. 2 는 이미 보유했다.
    설계를 완료로 하면 설계와 기술 1 · 3 — 게임이 설계 연구를 끝낸 뒤 "보유한 설계의 선행 기술을 준다"와 같다."""
    got = plan(lib, [tech(1, 3), tech(2, mine=True), tech(3), design(5, 1, 2)], "items d5")
    assert got["designs"] == [5] and got["techs"] == [1, 3] and got["asked"] == (0, 1)
    assert got["text"] == "기술 2개(선행 2개 포함) · 부대 설계 1개"


def test_all_four_prerequisites_of_a_design_are_followed(lib):
    got = plan(lib, [tech(1), tech(2), tech(3), tech(4), design(5, 1, 2, 3, 4)], "items d5")
    assert got["techs"] == [1, 2, 3, 4]


@pytest.mark.parametrize("flaw", [{"held": True}, {"is_open": False}], ids=["held", "not-open"])
def test_a_design_the_game_skips_gets_only_its_own_bit(lib, flaw):
    """깃발이 켜진 설계와 연구 대상이 아닌 설계는 게임이 선행 기술을 주는 데서 건너뛴다 — 설계의 비트만 바꾼다."""
    got = plan(lib, [tech(1), design(5, 1, **flaw)], "items d5")
    assert got["designs"] == [5] and got["techs"] == []


def test_level_takes_every_tech_at_or_below_it(lib):
    """"기술 수준 N 이하 전부 보유": 수준이 N 이하인 기술 모두. 선행은 수준이 더 높아도 딸려 온다."""
    rows = [tech(1, level=100), tech(2, level=120), tech(3, level=121), tech(4, 3, level=90), tech(5, level=50, mine=True)]
    got = plan(lib, rows, "level 120")
    assert got["techs"] == [1, 2, 3, 4] and got["asked"] == (3, 0)
    assert got["text"] == "기술 4개(선행 1개 포함)"
    assert plan(lib, rows, "level 49")["techs"] == []


def test_queue_takes_the_techs_and_designs_that_are_queued(lib):
    """"대기열의 연구 즉시 완료": 대기열에 있는 기술과 부대 설계 모두(내장 치트는 기술만 끝냈다), 그리고 그 노드를 대기열에서 뺀다."""
    rows = [tech(1), tech(2), tech(3), design(5, 2), design(6), node(DESIGN, 5), node(TECH, 1)]
    got = plan(lib, rows, "queue")
    assert got["queued"] == ["t1", "d5"]
    assert got["techs"] == [1, 2] and got["designs"] == [5] and got["nodes"] == [0, 1] and got["asked"] == (1, 1)
    assert got["text"] == "기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개"


def test_an_empty_queue_changes_nothing(lib):
    assert plan(lib, [tech(1), design(5)], "queue")["text"] == ""


@pytest.mark.parametrize("flags, live", [
    ((1, 0), True),                         # 막 걸었다
    ((1, 0x60000001), True),                # 연구 중
    ((GONE | 1, GONE | 0x60000001), False),  # 양쪽에서 뺐다(끝났다 · 취소했다)
    ((GONE | 1, 1), True),                  # 한쪽에만 남아 있다
    ((0, 0), False),
    ((1, ENDED | 1), True),                 # 내장 치트가 "끝냄"만 켜 둔 노드 — 대기열에 남아 있다
], ids=["queued", "running", "gone", "one-side", "blank", "ended-by-the-cheat"])
def test_which_nodes_count_as_queued(lib, flags, live):
    """게임의 기준: 깃발 둘 가운데 하나라도 아래 두 비트가 0 이 아니고 "뺐다"(0x80000000)가 꺼져 있다."""
    got = plan(lib, [tech(1), node(TECH, 1, *flags)], "queue")
    assert got["queued"] == (["t1"] if live else []) and got["nodes"] == ([0] if live else [])
    assert got["techs"] == ([1] if live else [])


def test_a_queued_item_that_is_already_held_is_only_taken_off_the_queue(lib):
    """내장 치트로 끝낸 기술은 보유가 됐는데도 대기열에 남는다. 새 단추는 그 노드를 정리한다 — 비트는 바꿀 것이 없다."""
    got = plan(lib, [tech(1, mine=True), design(5, mine=True), node(TECH, 1, 1, ENDED | 1), node(DESIGN, 5)], "queue")
    assert got["techs"] == [] and got["designs"] == [] and got["nodes"] == [0, 1]
    assert got["text"] == "대기열에서 2개"


def test_completing_from_the_list_takes_those_items_off_the_queue_and_leaves_the_rest(lib):
    """고른 것과 딸려 온 선행이 대기열에 있으면 뺀다. 이 요청과 상관없는 노드는 그대로 둔다."""
    rows = [tech(1), tech(2, 1), tech(3), design(5), node(TECH, 3), node(TECH, 1), node(DESIGN, 5), node(TECH, 2)]
    got = plan(lib, rows, "items t2")
    assert got["techs"] == [1, 2] and got["nodes"] == [1, 3]
    assert got["text"] == "기술 2개(선행 1개 포함) · 대기열에서 2개"


def test_items_nobody_holds_are_skipped_when_a_new_set_cannot_be_made(lib):
    """아무도 보유한 적이 없는 항목에는 보유 비트 묶음이 없다 — 완료로 바꾸려면 새 묶음을 걸어야 한다.
    그럴 수 없는 게임(can_house 가 거짓)에서는 그 항목만 건너뛴다: 그 선행은 따라가지 않고, 대기열에 있어도 빼지 않는다."""
    rows = [tech(1), tech(2, 1, housed=False), tech(3, 2), tech(4, housed=False), design(5, 4, housed=False), design(6, 1),
            node(TECH, 2), node(DESIGN, 5), node(TECH, 3)]
    got = plan(lib, rows, "items t3 t4 d5 d6")
    assert got["techs"] == [1, 2, 3, 4] and got["designs"] == [5, 6] and got["skipped"] == 0 and got["nodes"] == [0, 1, 2]
    got = plan(lib, rows, "items t3 t4 d5 d6", can_house=False)
    assert got["techs"] == [1, 3] and got["designs"] == [6]             # 2 · 4 · 5 는 묶음이 없다. 1 은 설계 6 의 선행으로 온다
    assert got["skipped"] == 3 and got["asked"] == (1, 1) and got["nodes"] == [2]
    assert got["text"] == "기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 1개"
    got = plan(lib, [tech(1), tech(2, 1, housed=False)], "items t2", can_house=False)
    assert got["techs"] == [] and got["skipped"] == 1                 # 건너뛴 기술의 선행(1)은 따라가지 않는다


def test_revoking_a_tech_takes_what_leans_on_it(lib):
    """기술 1 을 미완료로: 1 을 선행으로 갖는 보유 기술(2), 그것을 선행으로 갖는 보유 기술(3), 그 기술들을 선행으로 갖는 보유 설계(5).
    보유하지 않은 것(4 · 7), 게임이 건너뛰는 설계(6 — 깃발, 9 — 연구 대상이 아니다), 상관없는 것(8 · 10)은 그대로다 — 게임의 "기술을 뺀다"와 같다."""
    rows = [tech(1, mine=True), tech(2, 1, mine=True), tech(3, 2, mine=True), tech(4, 1), tech(10, mine=True),
            design(5, 2, mine=True), design(6, 3, mine=True, held=True), design(7, 1), design(8, 10, mine=True),
            design(9, 1, mine=True, is_open=False)]
    got = plan(lib, rows, "items t1", REVOKE)
    assert got["techs"] == [1, 2, 3] and got["designs"] == [5] and got["asked"] == (1, 0) and got["nodes"] == []
    assert got["text"] == "기술 3개(딸린 것 2개 포함) · 부대 설계 1개(딸린 것 1개 포함)"


def test_revoking_looks_at_all_four_prerequisites_of_a_design(lib):
    got = plan(lib, [tech(1, mine=True), design(5, 0, 0, 0, 1, mine=True)], "items t1", REVOKE)
    assert got["designs"] == [5]


def test_revoking_a_design_takes_only_that_design(lib):
    got = plan(lib, [tech(1, mine=True), design(5, 1, mine=True), design(6, 1, mine=True)], "items d5", REVOKE)
    assert got["techs"] == [] and got["designs"] == [5] and got["asked"] == (0, 1) and got["text"] == "부대 설계 1개"


def test_revoking_what_is_not_held_changes_nothing(lib):
    got = plan(lib, [tech(1), tech(2, 1, mine=True), design(5)], "items t1 d5", REVOKE)
    assert got["techs"] == [] and got["designs"] == [] and got["text"] == ""        # 1 을 보유하지 않았다 — 2 도 건드리지 않는다


def test_revoking_does_not_touch_the_queue(lib):
    got = plan(lib, [tech(1, mine=True), node(TECH, 1, 1, ENDED | 1)], "items t1", REVOKE)
    assert got["techs"] == [1] and got["nodes"] == []


@pytest.mark.parametrize("what", ["level 255", "queue"])
def test_revoking_is_only_for_chosen_items(lib, what):
    """"수준 N 이하"와 "대기열"은 완료에만 있다 — 미완료로는 아무것도 하지 않는다."""
    got = plan(lib, [tech(1, mine=True), node(TECH, 1)], what, REVOKE)
    assert got["techs"] == [] and got["text"] == ""


def test_a_large_table_is_planned_in_one_go(lib):
    """게임의 표는 기술 3000자리 · 부대 설계 22000자리다. 기술이 한 줄로 이어져 있어도 끝까지 간다."""
    rows = [tech(n, n - 1) for n in range(1, 3000)] + [design(n, 2999) for n in range(1, 22000, 7)]
    got = plan(lib, rows, "items d1", slots=(3000, 22000))
    assert len(got["techs"]) == 2999 and got["designs"] == [1] and got["text"] == "기술 2999개(선행 2999개 포함) · 부대 설계 1개"
    held = [tech(n, n - 1, mine=True) for n in range(1, 3000)] + [design(n, 2999, mine=True) for n in range(1, 22000, 7)]
    got = plan(lib, held, "items t1", REVOKE, slots=(3000, 22000))
    assert len(got["techs"]) == 2999 and len(got["designs"]) == len(range(1, 22000, 7))


# ---------------------------------------------------------------------------------------------------------------------
# 게임의 메모리에서: 표 읽기(read_research)와 쓰기(write_research)

def lab() -> tuple[FakeGame, Lab]:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임과 그 연구(toybox_fake_game.standard_lab — 기술 1 ~ 7, 부대 설계 10 ~ 14, 독일의 대기열).
    폴란드(141, 1106) · 덴마크(150, 1201)가 함께 있다."""
    fake = FakeGame()
    fake.region(POLAND, 1106, alive=3)
    fake.region(DENMARK, 1201, alive=3)
    fake.region(GERMANY, 1499)
    fake.play(GERMANY)
    return fake, standard_lab(fake, GERMANY, POLAND, DENMARK)


def read(lib, fake: FakeGame, lab: Lab, picked: int = 0):
    """표를 읽는다. 읽었으면 {slots, techs: {번호: 행}, designs: {번호: 행}, queue: [(종류, 번호, 깃발 0, 깃발 1)]}, 못 읽었으면 까닭의 글."""
    out = ctypes.create_string_buffer(1 << 16)
    ok = lib.srtoybox_research_read(fake.base, ctypes.byref(fake.at), ctypes.byref(lab.layout), picked, out, len(out))
    assert ok >= 0
    if ok == 0:
        return out.value.decode("utf-8")
    table = {"techs": {}, "designs": {}, "queue": []}
    for line in out.value.decode("utf-8").splitlines():
        word, *rest = line.split()
        if word == "slots":
            table["slots"] = tuple(int(n) for n in rest)
        elif word == "t":
            number, kind, level, first, second, mine, chosen, others, queued, housed = (int(n) for n in rest)
            table["techs"][number] = dict(kind=kind, level=level, needs=(first, second), mine=bool(mine), picked=bool(chosen),
                                          others=others, queued=bool(queued), housed=bool(housed))
        elif word == "d":
            number, cls, year, is_open, held, mine, chosen, others, queued, housed, *needs = (int(n) for n in rest)
            table["designs"][number] = dict(cls=cls, year=year, open=bool(is_open), held=bool(held), mine=bool(mine), picked=bool(chosen),
                                            others=others, queued=bool(queued), housed=bool(housed), needs=tuple(needs))
        else:
            table["queue"].append((int(rest[0]), int(rest[1]), int(rest[2], 16), int(rest[3], 16)))
    return table


def write(lib, fake: FakeGame, lab: Lab, what: str, action: int = COMPLETE, recompute=None) -> tuple[int, dict]:
    """연구를 바꾼다: (Wrote, 결과). 결과의 calls 는 "다시 셈" 자리의 함수가 불린 인자들 — [(세계 객체의 주소, 지역 인덱스)].
    recompute 를 주면 그 주소를 함수로 넘긴다(잘못된 주소로 예외를 낼 때)."""
    out = ctypes.create_string_buffer(1 << 16)
    calls: list[tuple[int, int]] = []
    hook = RECOMPUTE(lambda world, index: calls.append((world, index)))
    wrote = lib.srtoybox_research_write(fake.base, ctypes.byref(fake.at), ctypes.byref(lab.layout),
                                        recompute if recompute is not None else ctypes.cast(hook, ctypes.c_void_p), action,
                                        what.encode(), out, len(out))
    lines = dict(line.split(" ", 1) if " " in line else (line, "") for line in out.value.decode("utf-8").split("\n"))
    done = {name: [int(n) for n in lines[name].split()] for name in ("techs", "designs", "nodes")}
    done.update({name: int(lines[name]) for name in ("skipped", "housed", "cells", "written", "recomputed")})
    done.update(asked=tuple(int(n) for n in lines["asked"].split()), code=int(lines["code"], 16), why=lines["why"], text=lines["text"],
                calls=calls)
    return wrote, done


def differing(before: bytes, after: bytes) -> set[int]:
    return {i for i in range(len(before)) if before[i] != after[i]}


def test_the_tables_are_read_from_the_game(lib):
    fake, lab_ = lab()
    table = read(lib, fake, lab_)
    assert table["slots"] == (64, 64)
    assert sorted(table["techs"]) == [1, 2, 3, 4, 6, 7] and sorted(table["designs"]) == [10, 11, 12, 13, 14]     # 빈 자리는 없다
    assert table["techs"][1] == dict(kind=1, level=10, needs=(0, 0), mine=True, picked=False, others=1, queued=False, housed=True)
    assert table["techs"][2] == dict(kind=1, level=20, needs=(1, 0), mine=False, picked=False, others=1, queued=True, housed=True)
    assert table["techs"][3] == dict(kind=1, level=30, needs=(2, 0), mine=False, picked=False, others=0, queued=False, housed=False)
    assert table["designs"][11] == dict(cls=2, year=95, open=True, held=False, mine=False, picked=False, others=1, queued=True,
                                        housed=True, needs=(3, 0, 0, 0))
    assert table["designs"][12]["housed"] is False and table["designs"][14]["held"] is True and table["designs"][13]["others"] == 1
    assert table["queue"] == [(DESIGN, 11, 1, 0x60000001), (TECH, 2, 1, 0)]


def test_the_picked_country_is_marked(lib):
    """고른 나라의 보유를 행마다 적는다 — "타국의 연구"를 목록에 보이는 데 쓴다. 이번 판에 없는 번호와 플레이어 자신은 아무것도 고르지 않은 것과 같다."""
    fake, lab_ = lab()

    def picked(number: int) -> tuple[list[int], list[int]]:
        table = read(lib, fake, lab_, number)
        return ([n for n, row in table["techs"].items() if row["picked"]], [n for n, row in table["designs"].items() if row["picked"]])

    assert picked(1106) == ([1, 2], [11, 13])            # 폴란드
    assert picked(1201) == ([4, 7], [])                  # 덴마크
    assert picked(1499) == ([], []) and picked(9999) == ([], []) and picked(0) == ([], [])


def broken(flaw: str) -> tuple[FakeGame, Lab]:
    """lab() 에 흠 하나를 낸 것."""
    fake, lab_ = lab()
    tail = lab_.nodes[0]                                  # 먼저 건 노드가 목록의 끝이다
    if flaw == "menu":
        fake.menu()
    elif flaw == "multiplayer":
        fake.poke(MULTIPLAYER, "<B", 1)
    elif flaw == "wrong-index":
        fake.poke(INDEX, "<i", POLAND)                        # 전역의 인덱스가 플레이어의 객체가 아는 인덱스와 다르다
    elif flaw == "no-table":
        fake.poke(RESEARCH["tech_table"], "<Q", 0)
    elif flaw == "one-slot":
        fake.poke(RESEARCH["tech_count"], "<i", 1)
    elif flaw == "too-many":
        fake.poke(RESEARCH["design_count"], "<i", 70000)
    elif flaw == "techs-gone":
        fake.poke(RESEARCH["tech_table"], "<Q", 0x10)     # 읽을 수 없는 주소
    elif flaw == "designs-gone":
        fake.poke(RESEARCH["design_table"], "<Q", 0x10)
    elif flaw == "owners-gone":
        lab_.house(TECH, 3, block=0x10)
    elif flaw == "node-gone":
        ctypes.memmove(tail + 0x10, struct.pack("<Q", 0x10), 8)
    elif flaw == "loop":
        ctypes.memmove(tail + 0x10, struct.pack("<Q", lab_.nodes[1]), 8)     # 끝이 머리를 가리킨다
    return fake, lab_


@pytest.mark.parametrize("flaw, why, wrote", [
    ("menu", "게임이 진행 중이 아닙니다", NOT_IN_GAME),
    ("multiplayer", "멀티플레이에서는 연구를 읽지 않습니다", NOT_IN_GAME),
    ("wrong-index", "게임이 진행 중이 아닙니다", NOT_IN_GAME),
    ("no-table", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("one-slot", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("too-many", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("techs-gone", "기술 표를 읽을 수 없습니다", UNREADABLE),
    ("designs-gone", "부대 설계 표를 읽을 수 없습니다", UNREADABLE),
    ("owners-gone", "기술 3 의 보유 묶음을 읽을 수 없습니다", UNREADABLE),
    ("node-gone", "연구 목록의 노드를 읽을 수 없습니다", UNREADABLE),
    ("loop", "연구 목록이 끝나지 않습니다", UNREADABLE),
])
def test_a_game_that_does_not_add_up_is_neither_read_nor_written(lib, flaw, why, wrote):
    """표의 꼴이 다른 게임일 수 있다 — 읽지 않고, 한 칸도 쓰지 않고, 게임의 함수도 부르지 않는다."""
    fake, lab_ = broken(flaw)
    assert read(lib, fake, lab_) == why
    before = lab_.everything()
    result, done = write(lib, fake, lab_, "items t3 d11")
    assert result == wrote and done["written"] == 0 and done["calls"] == []
    assert lab_.everything() == before


def test_completing_a_tech_sets_the_players_bit_on_it_and_on_what_it_needs(lib):
    """기술 3 을 완료로: 3 과 그 선행 2 의 독일 비트가 켜진다(1 은 이미 보유했다). 3 에는 묶음이 없었다 — 게임처럼 프로세스 힙에서
    128바이트를 받아 건다. 대기열에 있던 2 는 대기열에서 빠진다. 끝에 독일의 효과를 한 번 다시 셈하게 한다."""
    fake, lab_ = lab()
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t3")
    assert wrote == DONE and done["techs"] == [2, 3] and done["designs"] == [] and done["asked"] == (1, 0)
    assert done["nodes"] == [1] and done["housed"] == 1 and done["skipped"] == 0
    assert done["cells"] == done["written"] == 5                                     # 비트 둘, 새 묶음의 포인터 하나, 노드의 깃발 둘
    assert done["recomputed"] == 1 and done["calls"] == [(lab_.world, GERMANY)]      # 플레이어 지역만. -1(모든 지역)이 아니다
    assert done["text"] == "기술 2개(선행 1개 포함) · 대기열에서 1개"
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY} and lab_.owners(TECH, 3) == {GERMANY} and lab_.owners(TECH, 1) == {GERMANY, POLAND}
    heap, block = kernel32.GetProcessHeap(), lab_.block(TECH, 3)
    assert kernel32.HeapValidate(heap, 0, block) and kernel32.HeapSize(heap, 0, block) == OWNERS_BYTES
    assert lab_.flags(lab_.nodes[0]) == (GONE | 1, GONE) and lab_.flags(lab_.nodes[1]) == (1, 0x60000001)   # 기술 2 의 노드만

    after = lab_.everything()
    assert set(after) - set(before) == {"t3"}                                         # 새 묶음 하나
    same = set(before) - {"techs", "t2", "n0"}
    assert all(after[name] == before[name] for name in same)                          # 전역 · 부대 설계 표 · 다른 묶음 · 다른 노드는 그대로다
    cell = 3 * TECH_SIZE + 0x50
    assert differing(before["techs"], after["techs"]) <= set(range(cell, cell + 8))   # 기술 표에서는 3 의 묶음 칸만(연구 기간은 그대로다)
    assert differing(before["t2"], after["t2"]) == {GERMANY // 8}
    assert differing(before["n0"], after["n0"]) == {0x23, 0x27}                       # 깃발 둘의 맨 위 비트


def test_only_the_players_bit_in_its_byte_changes(lib):
    """같은 바이트에 든 다른 나라 일곱의 비트는 읽은 그대로 쓴다."""
    fake, lab_ = lab()
    for index in (177, 183, 168, 175):                    # 176 과 같은 바이트(176 … 183), 그 앞 바이트
        lab_.own(TECH, 2, index)
    assert write(lib, fake, lab_, "items t2")[0] == DONE
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY, 177, 183, 168, 175}
    assert write(lib, fake, lab_, "items t2", REVOKE)[0] == DONE
    assert lab_.owners(TECH, 2) == {POLAND, 177, 183, 168, 175}


def test_completing_a_design_sets_its_bit_and_brings_the_techs_it_needs(lib):
    """부대 설계 11(선행 3 ← 2 ← 1)을 완료로: 설계의 비트와 기술 2 · 3. 내장 치트의 연구 단추들은 부대 설계를 건드리지 않았다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items d11")
    assert wrote == DONE and done["designs"] == [11] and done["techs"] == [2, 3] and done["asked"] == (0, 1) and done["nodes"] == [0, 1]
    assert done["text"] == "기술 2개(선행 2개 포함) · 부대 설계 1개 · 대기열에서 2개"
    assert lab_.owners(DESIGN, 11) == {POLAND, GERMANY} and lab_.owners(TECH, 3) == {GERMANY} and len(done["calls"]) == 1
    assert lab_.flags(lab_.nodes[1]) == (GONE | 1, GONE | 0x60000001)                 # 다른 비트는 그대로 두고 "뺐다"만 켠다


def test_a_design_alone_does_not_ask_the_game_to_recompute(lib):
    """부대 설계 12 는 선행(4)을 이미 보유했다 — 설계의 비트만 켠다. 효과의 표는 기술에서만 나온다: 다시 셈을 부르지 않는다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items d12")
    assert wrote == DONE and done["designs"] == [12] and done["techs"] == [] and done["housed"] == 1
    assert done["recomputed"] == 0 and done["calls"] == [] and lab_.owners(DESIGN, 12) == {GERMANY}


def test_the_queue_is_finished_without_touching_how_long_research_takes(lib):
    """"대기열의 연구 즉시 완료": 걸린 기술과 부대 설계를 모두 끝내고 대기열에서 뺀다. 내장 치트(e=mc2)는 부대 설계를 남겨 두었고,
    모든 기술의 연구 기간(+0x30)을 1일로 바꿨다 — 모든 나라가 함께 쓰는 표다. ToyBox 는 그 칸에 쓰지 않는다."""
    fake, lab_ = lab()
    days = [struct.unpack_from("<f", lab_.techs, n * TECH_SIZE + 0x30)[0] for n in range(64)]
    wrote, done = write(lib, fake, lab_, "queue")
    assert wrote == DONE and done["techs"] == [2, 3] and done["designs"] == [11] and done["asked"] == (1, 1) and done["nodes"] == [0, 1]
    assert all(flags[0] & GONE and flags[1] & GONE for flags in map(lab_.flags, lab_.nodes))
    assert [struct.unpack_from("<f", lab_.techs, n * TECH_SIZE + 0x30)[0] for n in range(64)] == days
    assert write(lib, fake, lab_, "queue")[1]["text"] == ""                           # 한 번 더 — 대기열이 비었다


def test_level_takes_the_techs_at_or_below_it(lib):
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "level 40")
    assert wrote == DONE and done["techs"] == [2, 3] and done["asked"] == (2, 0) and done["designs"] == []
    assert lab_.held(TECH, 64, GERMANY) == [1, 2, 3, 4, 6] and lab_.held(DESIGN, 64, GERMANY) == [10, 13, 14]


def test_revoking_a_tech_clears_the_players_bit_on_what_leaned_on_it(lib):
    """기술 4 를 미완료로: 4 와, 4 를 선행으로 갖는 6, 6 을 선행으로 갖는 설계 13. 14 는 게임이 건너뛰는 설계라 그대로다.
    다른 나라의 비트는 그대로이고 묶음도 그대로 둔다(풀지 않는다)."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items t4", REVOKE)
    assert wrote == DONE and done["techs"] == [4, 6] and done["designs"] == [13] and done["asked"] == (1, 0) and done["nodes"] == []
    assert done["text"] == "기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)"
    assert lab_.owners(TECH, 4) == {DENMARK} and lab_.owners(TECH, 6) == set() and lab_.block(TECH, 6) != 0
    assert lab_.owners(DESIGN, 13) == {POLAND} and lab_.owners(DESIGN, 14) == {GERMANY}
    assert done["housed"] == 0 and done["calls"] == [(lab_.world, GERMANY)]
    wrote, done = write(lib, fake, lab_, "items d10", REVOKE)
    assert wrote == DONE and done["designs"] == [10] and done["calls"] == [] and lab_.owners(DESIGN, 10) == set()


def rehouse(lab_: Lab, make) -> None:
    """모든 보유 묶음을 make() 가 주는 자리로 옮긴다(내용은 그대로)."""
    for kind, count in ((TECH, 64), (DESIGN, 64)):
        for number in range(1, count):
            old = lab_.block(kind, number)
            if old:
                new = make()
                ctypes.memmove(new, old, OWNERS_BYTES)
                lab_.house(kind, number, block=new)


@pytest.mark.parametrize("where", ["a-buffer", "a-bigger-block"])
def test_a_new_set_is_made_only_when_the_games_sets_are_heap_blocks_of_that_size(lib, where):
    """새 묶음은 게임이 나중에 풀 것이다 — 게임이 묶음을 받는 힙 · 크기와 같아야 한다. 이미 있는 묶음이 프로세스 힙의 128바이트 블록이
    아니면(다른 할당기를 쓰는 빌드, 지역이 늘어난 빌드) 만들지 않는다: 묶음이 없는 항목만 건너뛰고 나머지는 쓴다."""
    fake, lab_ = lab()
    pool = (ctypes.c_ubyte * 0x4000)()
    used = iter(range(0, 0x4000, 0x100))
    if where == "a-buffer":
        rehouse(lab_, lambda: ctypes.addressof(pool) + next(used))
    else:
        rehouse(lab_, lambda: kernel32.HeapAlloc(kernel32.GetProcessHeap(), 8, 2 * OWNERS_BYTES))
    wrote, done = write(lib, fake, lab_, "items t3 d12 d10 t7")
    assert wrote == DONE and done["techs"] == [7] and done["designs"] == [] and done["skipped"] == 2 and done["housed"] == 0
    assert lab_.block(TECH, 3) == 0 and lab_.block(DESIGN, 12) == 0 and lab_.owners(TECH, 7) == {DENMARK, GERMANY}
    assert lab_.owners(TECH, 2) == {POLAND}                                           # 건너뛴 3 의 선행은 따라가지 않았다


def test_nothing_is_written_when_one_of_the_sets_cannot_be_written(lib):
    """쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다. 하나라도 아니면 한 칸도 쓰지 않는다 — 받아 둔 새 묶음도 돌려준다."""
    fake, lab_ = lab()
    lab_.house(TECH, 2, block=locked_page())              # 기술 2 의 묶음이 읽기 전용 쪽에 있다
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t3")
    assert wrote == FAILED and done["why"] == "기술 2 의 보유 묶음" and done["written"] == 0 and done["cells"] == 5
    assert done["calls"] == [] and lab_.everything() == before and lab_.block(TECH, 3) == 0


def test_nothing_is_written_when_a_queue_node_cannot_be_written(lib):
    fake, lab_ = lab()
    page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
    lab_.queue(GERMANY, TECH, 7, at=page)
    assert kernel32.VirtualProtect(page, 0x1000, 0x02, ctypes.byref(ctypes.c_ulong()))
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t7")
    assert wrote == FAILED and done["why"] == "연구 목록의 노드" and done["written"] == 0
    assert done["calls"] == [] and lab_.everything() == before


def test_a_fault_in_the_games_function_is_caught(lib):
    """"다시 셈"에서 예외가 나면 죽지 않고 그 코드를 돌려준다(부른 쪽이 ToyBox 를 멈춘다). 비트는 이미 썼다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items t2", recompute=ctypes.c_void_p(8))    # 부를 수 없는 주소
    assert wrote == CRASHED and done["code"] == 0xC0000005 and done["recomputed"] == 0
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY}


def test_an_empty_request_writes_nothing_and_calls_nothing(lib):
    fake, lab_ = lab()
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t1 d10 t5 t63")      # 이미 보유한 것, 빈 자리, 표에 없는 번호
    assert wrote == DONE and done["text"] == "" and done["cells"] == 0 and done["calls"] == [] and lab_.everything() == before


# ---------------------------------------------------------------------------------------------------------------------
# 이 프로세스의 "게임"에서: 연구를 쓸 수 있는가, 게임이 뜰 때의 찾기와 로그

CAN_RESEARCH = 64                                         # srtoybox_game_flags 의 비트


def text(call, *args, size: int = 4096) -> str:
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return buf.raw[:max(n, 0)].decode("utf-8")


def test_research_is_off_until_its_place_is_known(lib):
    """연구는 제 묶음을 찾았을 때만 쓴다. 못 찾았으면 까닭을 그대로 보인다 — 내장 치트로 되돌아가지 않는다."""
    fake, lab_ = lab()
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    hook = RECOMPUTE(lambda world, index: None)
    try:
        lib.srtoybox_test_game(fake.base, ctypes.byref(fake.at), None)
        assert not lib.srtoybox_game_flags() & CAN_RESEARCH
        assert text(lib.srtoybox_research_off) == "이 게임 판에서는 쓸 수 없습니다 (연구의 자리를 주지 않았습니다)"
        lib.srtoybox_test_research(ctypes.byref(lab_.layout), ctypes.cast(hook, ctypes.c_void_p))
        assert lib.srtoybox_game_flags() & CAN_RESEARCH and text(lib.srtoybox_research_off) == ""
        lib.srtoybox_test_research(None, None)
        assert not lib.srtoybox_game_flags() & CAN_RESEARCH
    finally:
        lib.srtoybox_test_game(None, None, None)
    assert text(lib.srtoybox_research_off) == "게임 상태를 읽을 수 있을 때만 씁니다."


@pytest.fixture(scope="module")
def sigs(lib):
    """DLL 에 든 서명 표: (상태 21개, 값 12개, 연구 21개) — 저마다 [(찾을 것, 서명 글)]."""
    rows = lambda found: [(row.name, row.text) for row in found[2]]
    return rows(toybox.state_of(lib, b"")), rows(toybox.values_of(lib, b"")), rows(toybox.research_of(lib, b"", None))


def startup(lib, image: bytes, tmp_path, monkeypatch) -> tuple[int, str, list[str]]:
    """게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다: (아는 것의 비트, 연구를 쓸 수 없는 까닭, 로그의 줄들 — 때를 뗀 것)."""
    lib.srtoybox_test_init.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong]
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    try:
        lib.srtoybox_test_init(image, len(image))
        flags, off = lib.srtoybox_game_flags(), text(lib.srtoybox_research_off)
    finally:
        lib.srtoybox_test_game(None, None, None)              # 이미지를 놓기 전에 이 프로세스의 "게임"을 비운다
    log = tmp_path / "toybox.log"
    return flags, off, [line.split(" ", 2)[2] for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


FOUND = "연구를 씁니다 (기술 표 +0x5048 · 부대 설계 표 +0x5058 · 연구 목록 +0x2100 · 다시 셈 +0x1C00)"


def test_startup_finds_research_without_any_cheat(lib, sigs, tmp_path, monkeypatch):
    """치트 문자열이 하나도 없는 이미지에서도 연구의 자리와 다시 셈 함수를 찾는다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(state + values + research_)
    assert b"cheat" not in image
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    assert flags & CAN_RESEARCH and off == "" and FOUND in log
    assert not any("맞지 않은 서명" in line for line in log)


def test_startup_without_research_keeps_everything_else(lib, sigs, tmp_path, monkeypatch):
    """연구의 서명이 없는 게임: 연구만 꺼지고(까닭 한 줄) 상태 읽기와 돈 · 물자는 그대로다."""
    state, values, _ = sigs
    flags, off, log = startup(lib, toybox_fake_exe.sig_image(state + values), tmp_path, monkeypatch)
    assert flags & 5 == 5 and not flags & CAN_RESEARCH                                # 상태를 읽고 값(국고 · 재고)을 쓴다
    assert off == "이 게임 판에서는 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)"
    assert "연구를 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)" in log and not any(line.startswith("연구를 씁니다") for line in log)


def test_startup_drops_research_when_one_signature_is_missing(lib, sigs, tmp_path, monkeypatch):
    """연구는 서명 하나만 맞지 않아도 쓰지 않는다 — 표의 꼴이 서명마다 박혀 있다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(research_ + state + values, broken={17})        # 연구 목록의 셋째 서명
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    assert flags & 5 == 5 and not flags & CAN_RESEARCH and "연구를 쓸 수 없습니다 (연구 목록: 서명 3개 가운데 2개)" in log


def test_startup_drops_research_that_sits_on_the_world_pointer(lib, sigs, tmp_path, monkeypatch):
    """저마다 찾았어도 연구의 전역이 값 묶음의 세계 자료 포인터와 겹치면 연구는 쓰지 않는다. 돈 · 물자는 그대로다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(state + values + research_, targets={"tech_table": toybox_fake_exe.VALUE_LAYOUT["world_pointer"]})
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    clash = "기술 표: 찾은 주소가 세계 자료 포인터 의 자리와 겹칩니다"
    assert flags & 5 == 5 and not flags & CAN_RESEARCH and off == f"이 게임 판에서는 쓸 수 없습니다 ({clash})"
    assert f"연구를 쓸 수 없습니다 ({clash})" in log and any(line.startswith("값을 씁니다 (국고 ") for line in log)


def test_startup_without_the_state_does_not_look_for_research(lib, sigs, tmp_path, monkeypatch):
    _, _, research_ = sigs
    flags, off, log = startup(lib, toybox_fake_exe.sig_image(research_), tmp_path, monkeypatch)
    assert flags == 0 and off == "게임 상태를 읽을 수 있을 때만 씁니다." and not any("연구" in line for line in log)


# ---------------------------------------------------------------------------------------------------------------------
# 연구 요청의 줄(keeper): 창의 단추가 넣고, 게임 창의 타이머가 하나씩 쓴다

LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다."
FAULT = "효과를 다시 셈하는 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오."


class Playing:
    """이 프로세스의 "게임"이 lab() 인 동안. "다시 셈" 자리의 함수는 불린 인자를 calls 에 적고, inside 에 든 일을 그 안에서 한다."""

    def __init__(self, lib, home):
        self.lib, self.home = lib, home
        self.fake, self.lab = lab()
        self.calls: list[tuple[int, int]] = []
        self.inside: list = []
        self.hook = RECOMPUTE(self._recompute)

    def _recompute(self, world: int, index: int) -> None:
        self.calls.append((world, index))
        for act in self.inside:
            act()

    def ask(self, what: str, label: str, action: int = COMPLETE) -> int:
        return self.lib.srtoybox_keeper_research(action, what.encode(), label.encode())

    def tick(self) -> None:
        self.lib.srtoybox_keeper_tick()

    def told(self) -> tuple[str, str]:
        """(창 바닥의 "마지막으로 쓴 값", 알림)."""
        last, notice = text(self.lib.srtoybox_keeper_text).split("\t")
        return last, notice

    def runner(self) -> tuple[str, str, str]:
        """(오류 가드가 걸렸는가, 게임의 함수 안인가, 빨간 경고의 글)."""
        faulted, calling, notice = text(self.lib.srtoybox_runner_text).split("\t")
        return faulted, calling, notice

    def log(self) -> list[str]:
        path = self.home / "toybox.log"
        return [line.split(" ", 2)[2] for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

    def mine(self) -> tuple[list[int], list[int]]:
        """독일이 보유한 (기술, 부대 설계)."""
        return self.lab.held(TECH, 64, GERMANY), self.lab.held(DESIGN, 64, GERMANY)


@pytest.fixture
def playing(lib, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_keeper_research.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
    lib.srtoybox_keeper_text.argtypes = lib.srtoybox_runner_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
    game = Playing(lib, tmp_path)
    lib.srtoybox_test_game(game.fake.base, ctypes.byref(game.fake.at), None)
    lib.srtoybox_test_research(ctypes.byref(game.lab.layout), ctypes.cast(game.hook, ctypes.c_void_p))
    lib.srtoybox_keeper_reset()
    yield game
    lib.srtoybox_keeper_reset()                              # 오류 가드도 지운다 — 다음 테스트는 멈추지 않은 ToyBox 에서 시작한다
    lib.srtoybox_test_game(None, None, None)


MINE = ([1, 4, 6], [10, 13, 14])                             # lab() 에서 독일이 보유한 것


def test_research_requests_are_written_one_per_tick_in_order(playing):
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    assert playing.mine() == MINE and playing.calls == []     # 누른 것만으로는 쓰지 않는다 — 창 스레드의 틱에서 쓴다
    playing.tick()
    assert playing.mine() == ([1, 2, 3, 4, 6], [10, 11, 13, 14])
    assert playing.told() == ("기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열", "")
    assert playing.calls == [(playing.lab.world, GERMANY)]
    playing.tick()                                            # 다음 요청은 다음 틱에
    assert playing.mine() == ([1, 2, 3, 4, 6, 7], [10, 11, 13, 14])
    assert playing.told() == ("기술 1개를 완료로 — 기술 수준 70 이하", "")
    playing.tick()
    assert len(playing.calls) == 2 and playing.runner() == ("0", "0", "")
    assert playing.log() == ["연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개",
                             "연구 완료 (기술 수준 70 이하): 기술 1개"]
    assert playing.lab.owners(TECH, 7) == {DENMARK, GERMANY} and playing.lab.owners(DESIGN, 11) == {POLAND, GERMANY}   # 다른 나라는 그대로다


def test_a_request_that_changes_nothing_says_so(playing):
    """대기열이 비었을 때의 "대기열의 연구 즉시 완료": 한 칸도 쓰지 않고, 게임의 함수도 부르지 않고, 그렇다고 알린다."""
    assert playing.ask("items t1 d10", "고른 것") == 1
    before = playing.lab.everything()
    playing.tick()
    assert playing.told() == ("", "바꿀 것이 없습니다 — 고른 것") and playing.calls == [] and playing.lab.everything() == before
    assert playing.log() == ["연구 완료 (고른 것): 바꿀 것이 없습니다"]


def test_a_queued_item_that_is_already_held_is_only_cleared_from_the_queue(playing):
    """내장 치트로 "끝낸" 판에는 보유한 기술의 노드가 대기열에 남아 있다 — 그 노드만 뺀다. 비트를 바꾸지 않았으니 다시 셈도 없다."""
    head = RESEARCH["world"] + RESEARCH["lists"] + GERMANY * 24
    playing.lab.nodes.clear()
    playing.fake.poke(head, "<Q", 0)                          # 독일의 대기열을 비우고
    playing.fake.poke(head + 8, "<Q", 0)
    held = playing.lab.queue(GERMANY, TECH, 1, flags=(1, ENDED))
    assert playing.ask("queue", "대기열") == 1
    playing.tick()
    assert playing.told() == ("대기열에서 1개를 뺌 — 대기열", "") and playing.calls == [] and playing.mine() == MINE
    assert playing.lab.flags(held) == (GONE | 1, GONE | ENDED) and playing.log() == ["연구 완료 (대기열): 대기열에서 1개"]


def test_revoking_is_requested_the_same_way(playing):
    assert playing.ask("items t4", "고른 것", REVOKE) == 1
    playing.tick()
    assert playing.mine() == ([1], [10, 14])
    assert playing.told() == ("기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)를 미완료로 — 고른 것", "")
    assert playing.log() == ["연구 미완료 (고른 것): 기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)"]
    assert playing.lab.owners(TECH, 4) == {DENMARK} and playing.lab.owners(DESIGN, 13) == {POLAND}


def test_value_requests_of_the_tick_are_written_before_its_research_request(lib, playing):
    """틱마다 값 요청을 먼저 비우고, 그 뒤에 연구 요청을 하나 쓴다."""
    lib.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    lib.srtoybox_keeper_request.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
    lib.srtoybox_test_values(ctypes.byref(playing.fake.layout))
    seen: list[float] = []
    playing.inside.append(lambda: seen.append(playing.fake.treasury(GERMANY)))
    assert playing.ask("queue", "대기열") == 1 and lib.srtoybox_keeper_request(-1, 1, 100.0) == 1      # 국고를 100 으로
    playing.tick()
    assert seen == [100.0]                                    # 게임의 함수가 불렸을 때 국고는 이미 쓰여 있었다
    assert playing.log() == ["값 쓰기: 국고 0 -> 100", "연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개"]
    assert playing.told() == ("기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열", "")


def test_only_four_research_requests_wait(playing):
    assert [playing.ask("queue", "대기열") for _ in range(5)] == [1, 1, 1, 1, 0]
    playing.tick()
    assert playing.ask("queue", "대기열") == 1                 # 하나가 처리됐다
    assert playing.ask("bogus", "대기열", action=2) == -1


@pytest.mark.parametrize("leave", ["menu", "multiplayer"])
def test_research_requests_are_dropped_outside_a_game(playing, leave):
    """누른 뒤 쓰기 전에 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다."""
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    before = playing.lab.everything()
    if leave == "menu":
        playing.fake.menu()
    else:
        playing.fake.poke(MULTIPLAYER, "<B", 1)
    playing.tick()
    assert playing.told() == ("", LEFT_GAME) and playing.calls == []
    if leave == "menu":
        playing.fake.play(GERMANY)
    else:
        playing.fake.poke(MULTIPLAYER, "<B", 0)
    playing.tick()
    assert playing.lab.everything() == before and playing.calls == [] and playing.log() == []


def test_a_tick_that_comes_back_inside_the_games_function_does_nothing(playing):
    """게임의 함수가 일하는 동안 ToyBox 의 타이머가 다시 올 수 있다(게임이 메시지를 돌릴 때) — 그 안에서는 쓰지도 부르지도 않는다.
    그 안에서 누른 단추의 요청은 받아 두었다가 다음 틱에 쓴다."""
    seen: list = []

    def reenter() -> None:
        seen.append(playing.runner()[1])
        playing.tick()                                        # 그 안에서 다시 온 틱
        seen.append((playing.mine(), len(playing.calls)))
        seen.append(playing.ask("items d12", "고른 것"))

    playing.inside.append(reenter)
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    playing.tick()
    assert seen == ["1", (([1, 2, 3, 4, 6], [10, 11, 13, 14]), 1), 1]      # 수준 70 의 요청은 그 안에서 쓰이지 않았다
    assert playing.runner() == ("0", "0", "")
    playing.inside.clear()
    playing.tick()
    playing.tick()
    assert playing.mine() == ([1, 2, 3, 4, 6, 7], [10, 11, 12, 13, 14]) and len(playing.calls) == 2      # 설계 12 만으로는 부르지 않는다


def test_a_fault_in_the_games_function_stops_toybox(lib, playing):
    """"효과를 다시 셈"에서 예외가 나면 게임의 상태를 믿을 수 없다 — 직접 실행의 오류와 같이 ToyBox 를 멈춘다:
    빨간 경고를 띄우고, 그 뒤로는 아무것도 쓰지도 부르지도 않는다."""
    lib.srtoybox_test_research(ctypes.byref(playing.lab.layout), ctypes.c_void_p(8))      # 부를 수 없는 주소
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    playing.tick()
    assert playing.runner() == ("1", "0", FAULT)
    assert playing.log() == ["효과를 다시 셈하는 중 예외 0xC0000005 — ToyBox 를 멈춥니다"]
    after = playing.lab.everything()
    playing.tick()
    playing.ask("level 70", "기술 수준 70 이하")
    playing.tick()
    assert playing.lab.everything() == after and playing.told() == ("", "")
    assert playing.lab.held(TECH, 64, GERMANY) == [1, 2, 3, 4, 6]      # 비트는 예외가 나기 전에 썼다. 수준 70 의 요청은 버려졌다


def test_a_table_that_cannot_be_read_is_reported_and_nothing_is_written(playing):
    assert playing.ask("queue", "대기열") == 1
    playing.fake.poke(RESEARCH["tech_count"], "<i", 1)        # 표의 꼴이 다른 게임
    before = playing.lab.everything()
    playing.tick()
    why = "연구의 표를 읽을 수 없습니다 (표가 없거나 자리 수가 범위 밖입니다)"
    assert playing.told() == ("", why) and playing.log() == [why] and playing.calls == [] and playing.lab.everything() == before


def test_a_failed_write_turns_writing_off(lib, playing):
    """쓸 수 없는 칸을 만나면 한 칸도 쓰지 않고, 그 뒤로는 값 쓰기 전체를 끈다 — 까닭은 단추의 자리에 보인다."""
    playing.lab.house(TECH, 2, block=locked_page())           # 기술 2 의 묶음이 읽기 전용 쪽에 있다
    assert playing.ask("items t3", "고른 것") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    before = playing.lab.everything()
    playing.tick()
    playing.tick()
    assert playing.lab.everything() == before and playing.calls == [] and playing.told() == ("", "")
    assert playing.log() == ["연구 쓰기 실패 (기술 2 의 보유 묶음) — 값 쓰기를 끕니다"]
    assert not lib.srtoybox_game_flags() & CAN_RESEARCH and text(lib.srtoybox_research_off) != ""
    assert playing.ask("level 70", "기술 수준 70 이하") == 0     # 더 받지 않는다


def test_items_nobody_holds_are_skipped_and_counted_when_a_set_cannot_be_made(playing):
    pool = (ctypes.c_ubyte * 0x4000)()
    used = iter(range(0, 0x4000, 0x100))
    rehouse(playing.lab, lambda: ctypes.addressof(pool) + next(used))      # 게임의 묶음이 프로세스 힙의 것이 아니다
    skipped = "묶음을 만들 수 없는 게임 판입니다 — 보유한 나라가 없는 항목 {}개를 건너뜁니다"
    assert playing.ask("items t3 d12 t7", "고른 것") == 1 and playing.ask("items t3", "보이는 것") == 1
    playing.tick()
    assert playing.told() == ("기술 1개를 완료로 — 고른 것", skipped.format(2)) and playing.mine() == ([1, 4, 6, 7], MINE[1])
    playing.tick()
    assert playing.told() == ("기술 1개를 완료로 — 고른 것", skipped.format(1))
    assert playing.log() == [skipped.format(2), "연구 완료 (고른 것): 기술 1개", skipped.format(1)]
