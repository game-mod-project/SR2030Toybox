# 연구 가능으로 — 다른 지역 전용도 연다 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Research::Unlock` 이 지역만이 막는 항목을 만나면 그 항목의 지역 코드 비트 하나를 플레이어 지역 객체 `+0x40` 에 더하고, 이어서 지금처럼 선행 · 앞 설계를 채운다.

**Architecture:** 규칙(`research.cpp` 의 `unlock`)이 더할 비트(`ResearchPlan::region_add`)를 정하고, 쓰기(`game.cpp` 의 `write_research`)가 다른 쓰기보다 먼저 그 칸을 CAS 로 쓴다. 창은 풍선말만 바뀐다.

**Tech Stack:** C++17(MSVC, ToyBox DLL), Python pytest + ctypes(가짜 게임).

**Spec:** `docs/superpowers/specs/2026-10-17-toybox-region-unlock-design.md`

## Global Constraints

- 쓰는 곳은 **플레이어 지역 객체의 `+0x40`(qword, `REGION_MASK` — 이미 `locate.h` 에 있다) 하나**가 는다. OR 만 한다(끄지 않는다). 다른 지역 · 공용 표(`+0x18` · `+0x28`)에는 쓰지 않는다. 부르는 게임 함수는 늘지 않는다.
- 이 칸을 **맨 먼저** 쓴다. 쓰기 직전 값이 스냅숏(`shot.tables.region_mask`)과 다르면 아무것도 쓰지 않고 `Wrote::NotInGame`. 이 칸을 쓸 수 없어도 아무것도 쓰지 않는다(`research_failed(done, "플레이어 지역의 지역 코드")`).
- 이 칸을 쓴 뒤의 실패는 지금처럼 멈춘다 — 이 칸은 되돌리지 않는다.
- 비트 = 글자 − 'A' + 1 번(독일 `GE` = `0xa0`, `K` = `0x800`). 규칙은 글자를 모른다 — 마스크의 비트만 다룬다.
- 바닥 글: `지역 N개 열림`(N = 새로 켠 비트 수)을 `항목 N개 열림` 바로 뒤에.
- 테스트: `uv run pytest`. DLL 빌드: `uv run srkit toybox-build`.

## Review Focus

1. "보이는 것 전부 연구 가능으로"(수천 항목) — 비트 셈이 항목마다 표 전체를 돌면 느리다. 셈은 마스크가 바뀔 때만 다시 한다(Task 1 의 `test_unlock_of_many_items_adds_each_bit_once`).
2. 플레이어 마스크를 읽지 못했다(0) — 마스크가 있는 항목마다 비트를 더하게 된다. 스냅숏이 0 이면 지역 단계를 하지 않고 지금처럼 `다른 지역 전용` 으로 센다(Task 1 의 `test_a_zero_region_mask_still_blocks_and_adds_nothing`).
3. 지역 + 단종 · 이미 개량됨이 함께 막는 설계 — 비트를 더하면 지역만 열리고 그 설계는 여전히 안 나온다. 그 까닭으로 세고 비트를 더하지 않는다(Task 1).
4. 비트가 이미 켜진 뒤의 같은 지역 항목 — 두 번째 항목은 이미 겹치므로 셈에 들어가지 않는다(Task 1).
5. 쓰기 직전에 칸을 쓸 수 없다 — 아무 비트도 켜지지 않아야 한다(Task 2 의 `test_nothing_is_written_when_the_region_cell_cannot_be_written`).

---

### Task 1: 규칙 — 더할 비트를 정한다

**Files:**
- Modify: `native/srtoybox/research.h`(ResearchPlan), `native/srtoybox/research.cpp`(`unlock`, `research_summary`), `native/srtoybox/exports.cpp`(`srtoybox_research_plan` 의 `unlock` 줄)
- Test: `tests/test_toybox_research.py`

**Interfaces:**
- Produces: `ResearchPlan::region_add`(`uint64_t`, 0 이면 없음 — 더할 비트들), `ResearchPlan::regions`(`int`, 그 비트 수). `srtoybox_research_plan` 의 `unlock` 줄 끝에 `<regions> <region_add 의 10진>` 두 수를 더한다(지금 일곱 → 아홉). 테스트의 `plan()` 은 그대로 tuple 로 읽는다.

규칙(`unlock` 안):
- `other = design_blocks(t′)` — `t′` 는 `t` 의 사본에 `region_mask = ~0ull`(지역을 뺀 까닭). 기술은 지역 말고 까닭이 없다.
- `cur = t.region_mask`. 항목마다(지금 차례 그대로, 보유 · 대기열은 지금처럼 `already`):
  - 다른 까닭이 있으면(`other[i] != BLOCK_NONE`) 그 까닭으로 센다(설계).
  - 아니고 `mask != 0 && (mask & cur) == 0` 이면: `cur == 0`(스냅숏이 0 — 읽지 못함)이면 `BLOCK_REGION` 으로 센다. 아니면 비트 하나를 골라 `cur |= bit`, `region_add |= bit` 하고 아래로.
  - 그 뒤는 지금처럼 `take(...)`. 다만 이 항목에서 지역을 열었으면(이 항목 때문에 비트를 더했거나, 앞 항목이 더한 비트로 비로소 겹치게 됐으면 — 즉 `mask & t.region_mask == 0` 이었으면) 선행이 다 있어도 `opened` 로 센다.
- 비트 고르기: 후보는 `mask` 의 비트들. 비트마다 "새로 열리는 항목 수" = 보유 · 대기열이 아니고, (기술이거나 `other == BLOCK_NONE` 인 설계이고), `mask != 0 && (mask & cur) == 0 && (mask & bit) != 0` 인 기술 · 설계의 수. 가장 작은 것, 같으면 낮은 비트.
  `cur` 가 바뀔 때만 64칸 셈 배열을 다시 채운다(한 번에 표를 한 번 돈다).
- `research_summary`(Unlock): `항목 N개 열림` 뒤에 `regions > 0` 이면 `지역 N개 열림`.
- 바꿀 것이 없음의 판정(`keeper.cpp` run_research 의 "techs 와 designs 가 모두 비면")에 `region_add == 0` 을 더한다 — 지역만 열고 선행은 이미 다 가진 항목도 쓴다.

- [ ] **Step 1: 실패하는 테스트**(모두 `action=UNLOCK`, `got = plan(...)`. `unlock` tuple 의 끝 둘이 `(regions, region_add)`)

```python
def test_unlock_adds_the_one_region_bit_a_region_only_design_needs(lib):
    # 독일 0xa0, K2A1 같은 설계 7(마스크 0x800, 선행 1 미보유) → 비트 0x800 하나, 선행 1 완료
    got = plan(lib, ["region 160", tech(1), design(7, 1), "dmask 7 2048 0"], "items d7", action=UNLOCK)
    assert got["techs"] == [1] and got["unlock"][-2:] == (1, 2048)
    assert got["text"] == "연구 가능으로 — 항목 1개 열림 · 지역 1개 열림 · 선행 기술 1개 완료"

def test_the_bit_that_opens_the_fewest_items_is_chosen(lib):
    # 설계 7 마스크 0x800|0x4000. 0x800 을 가진 막힌 설계가 둘 더(8, 9), 0x4000 은 7 뿐 → 0x4000
    rows = ["region 160", tech(1, mine=True), design(7, 1), "dmask 7 18432 0", design(8, 1), "dmask 8 2048 0", design(9, 1), "dmask 9 2048 0"]
    assert plan(lib, rows, "items d7", action=UNLOCK)["unlock"][-2:] == (1, 16384)

def test_on_a_tie_the_lower_bit_is_chosen(lib):
    rows = ["region 160", tech(1, mine=True), design(7, 1), "dmask 7 18432 0"]
    assert plan(lib, rows, "items d7", action=UNLOCK)["unlock"][-2:] == (1, 2048)

def test_unlock_of_many_items_adds_each_bit_once(lib):
    rows = ["region 160", tech(1, mine=True)] + [r for n in range(7, 40) for r in (design(n, 1), f"dmask {n} 2048 0")]
    got = plan(lib, rows, "items " + " ".join(f"d{n}" for n in range(7, 40)), action=UNLOCK)
    assert got["unlock"][0] == 33 and got["unlock"][-2:] == (1, 2048)

def test_a_design_also_blocked_for_another_reason_adds_no_bit(lib):
    # 단종(year 130 > retired 100) + 지역
    rows = ["region 160", "year 130", tech(1, mine=True), design(7, 1), "dmask 7 2048 0", "dold 7 100 0"]
    got = plan(lib, rows, "items d7", action=UNLOCK)
    assert got["unlock"][-2:] == (0, 0) and got["unlock"][6] == 1        # 단종 1

def test_a_design_that_already_overlaps_adds_no_bit(lib):
    rows = ["region 160", tech(1), design(7, 1), "dmask 7 128 0"]       # G(0x80)
    assert plan(lib, rows, "items d7", action=UNLOCK)["unlock"][-2:] == (0, 0)

def test_a_zero_region_mask_still_blocks_and_adds_nothing(lib):
    got = plan(lib, [tech(1), design(7, 1), "dmask 7 2048 0"], "items d7", action=UNLOCK)
    assert got["unlock"][2] == 1 and got["unlock"][-2:] == (0, 0)

def test_a_region_only_tech_opens_the_same_way(lib):
    got = plan(lib, ["region 160", tech(1), tech(2, 1), "tmask 2 2048"], "items t2", action=UNLOCK)
    assert got["techs"] == [1] and got["unlock"][-2:] == (1, 2048)
```

(`dold`/`year` 줄의 꼴은 `exports.cpp` 의 `tables_from` 을 보고 맞춘다 — 지금 테스트 `test_a_retired_design_is_blocked` 가 쓰는 꼴 그대로.)
`unlock` tuple 을 통째로 견주는 기존 테스트(예: `test_a_retired_design_is_blocked` 의 `(0, 3, 0, 0, 0, 0, 1)`)는 끝에 `0, 0` 을 더한다.
기존 테스트 `test_unlock_refuses_what_the_game_would_still_hide` 는 `region 4` 와 `dmask 7 8 0`(지역만) · `tmask 2 2`(지역만)을 쓴다 — 이제 그 둘은 열린다. 기대값을 새 규칙으로 고친다(지역 2개가 아니라 비트가 더해지고 연 항목이 는다). 바뀐 기대값을 커밋 메시지에 적는다.

- [ ] **Step 2:** `uv run srkit toybox-build && uv run pytest tests/test_toybox_research.py -q` — 새 테스트가 실패(`unlock` tuple 길이 7).
- [ ] **Step 3:** 위 규칙을 구현한다(`research.h` · `research.cpp` · `exports.cpp` · `keeper.cpp`).
- [ ] **Step 4:** 빌드 후 `uv run pytest tests/test_toybox_research.py -q` 통과.
- [ ] **Step 5:** 커밋 `feat(toybox): 연구 가능으로 — 지역만이 막으면 비트 하나를 더한다(규칙)`

### Task 2: 쓰기 — 플레이어 지역의 `+0x40`

**Files:**
- Modify: `native/srtoybox/game.cpp`(`write_research`), `native/srtoybox/game.h`(머리말의 연구 줄), `CLAUDE.md`(쓰는 곳의 연구 문단), `tests/toybox_fake_game.py`(`Lab.mask`)
- Test: `tests/test_toybox_research.py`

**Interfaces:**
- Consumes: `ResearchPlan::region_add`(Task 1).
- Produces: `Lab.mask(kind: int, number: int, mask: int) -> None` — 기술 `+0x28` · 설계 `+0x18` 에 qword. 테스트는 플레이어 지역의 칸을 `struct.unpack_from("<Q", fake.objects[GERMANY], 0x40)` 로 본다.

`write_research`: 계획이 정해진 뒤, "모든 칸이 쓰기 쪽인가" 검사에 `region_add != 0` 이면 `player + REGION_MASK`(8바이트)를 더하고(`done->cells++`), 묶음 · 비트 쓰기 **앞에** `InterlockedCompareExchange64(cell, old | region_add, old)`(`old = shot.tables.region_mask`, `__try` 안). 결과가 `old` 가 아니면 `release()` 후 `Wrote::NotInGame`. 성공하면 `done->written++`. Shot 에 플레이어 객체의 주소가 없으면 `uint64_t player` 를 더한다.

- [ ] **Step 1: 실패하는 테스트**

```python
def test_unlock_ors_one_region_bit_into_the_players_region_first(lib):
    fake, lab_ = lab()
    struct.pack_into("<Q", fake.objects[GERMANY], 0x40, 0xa0)
    struct.pack_into("<Q", fake.objects[POLAND], 0x40, 0x4)
    lab_.mask(DESIGN, 12, 0x800)                                   # 설계 12(선행 4 — 독일 보유)
    wrote, done = write(lib, fake, lab_, "items d12", action=UNLOCK)
    assert wrote == DONE and "지역 1개 열림" in done["text"]
    assert struct.unpack_from("<Q", fake.objects[GERMANY], 0x40)[0] == 0x8a0
    assert struct.unpack_from("<Q", fake.objects[POLAND], 0x40)[0] == 0x4
    assert lab_.owners(DESIGN, 12) == set()

def test_nothing_is_written_when_the_region_cell_cannot_be_written(lib):
    # 독일의 객체를 읽기만 되는 쪽(toybox_fake_game 의 보호된 쪽 만드는 도우미)으로 옮겨 +0x40 을 쓸 수 없게 한다
    ...
    assert wrote == FAILED and done["written"] == 0 and lab_.everything() == before
```

(둘째 테스트는 `toybox_fake_game.py` 의 보호된 쪽 도우미 — 위 `VirtualProtect` 를 쓰는 함수 — 로 독일 객체를 `PAGE_READONLY` 쪽에 복사해 `fake.where`/`POINTER`/지역 표를 그 주소로 돌린다. 선행이 모자란 설계(`items d11` 꼴)를 골라 비트 쓰기가 있었다면 바뀌었을 것을 `before` 로 견준다.)

- [ ] **Step 2:** 빌드 후 실패 확인.
- [ ] **Step 3:** 구현. `game.h` 머리말 "연구(3단계 3): …" 줄에 `, 그리고 "연구 가능으로"가 다른 지역 전용을 열 때 플레이어 지역 객체의 지역 코드 칸(+0x40, qword)에 비트 하나를 OR(2026-10-17)` 을 더한다. `CLAUDE.md` 의 같은 문단(**연구(3단계 3)**…)에 같은 뜻의 문장 한 줄과 설계서 링크.
- [ ] **Step 4:** `uv run pytest -q` 전체 통과.
- [ ] **Step 5:** 커밋 `feat(toybox): 연구 가능으로 — 플레이어 지역의 지역 코드 칸에 쓴다`

### Task 3: 창 · 문서

**Files:**
- Modify: `native/srtoybox/ui.cpp`(단추 둘의 풍선말), `docs/10-toybox.md`(118행 근처의 연구 가능으로 설명, 787행 표의 (다) 줄 뒤에 새 줄), `README.md`(연구 가능으로 줄에 "다른 지역 전용도" 반 문장)

- [ ] **Step 1:** 두 단추의 풍선말 끝에 설계서의 글 그대로: "다른 지역 전용이면 그 지역 코드 하나를 내 나라에 더한다 — 같은 코드의 다른 나라 설계도 함께 열리고, 되돌리지 않는다. 게임의 연구 장관이 그것을 연구할 수 있다".
- [ ] **Step 2:** 문서. 게임 안 확인 전이므로 "코드와 자동 테스트 끝 — 게임에서는 아직"으로 적는다.
- [ ] **Step 3:** 빌드 · `uv run pytest -q` 통과.
- [ ] **Step 4:** 커밋 `docs(toybox): 연구 가능으로가 다른 지역 전용도 연다`

### 그 뒤 (계획 밖, 컨트롤러)

게임 안 확인 R1 ~ R4(설계서의 표) — 백그라운드 에이전트, 임시 `SRTOYBOX_HOME`, 이 브랜치의 DLL 을 `srkit deploy toybox --apply` 해야 하므로 사용자의 확인을 받는다. 결과를 설계서에 적고 `develop` 으로 PR.
