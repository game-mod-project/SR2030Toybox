"""ToyBox: 연구의 규칙(native/srtoybox/research.cpp) — 완료 · 미완료가 어느 기술 · 부대 설계의 보유를 바꾸는가.

게임이 스스로 쓰는 규칙 그대로다(docs/11-game-internals.md): 기술을 주면 선행 기술도 주고, 빼면 그 기술에 기대는 기술 · 설계도 뺀다.
여기서는 표를 글로 지어 규칙만 본다 — 게임의 메모리에서 표를 읽고 쓰는 것은 tests/test_toybox_values.py 가 본다.
"""
import ctypes

import pytest

from srkit import toybox

COMPLETE, REVOKE = 0, 1
TECH, DESIGN = 1, 2          # 대기열 노드의 종류
GONE, ENDED = 0x80000000, 0x08000000


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_research_plan.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
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
