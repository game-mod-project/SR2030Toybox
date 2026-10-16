# ToyBox 연구 — "연구 가능으로" 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 연구 탭 · 부대 탭의 목록에서 고른 항목의 모자란 직접 선행 기술만 보유로 줘, 항목이 게임의 "가능한 연구"에 나오게 한다. 목록의 상태를 `보유` · `연구 중` · `연구 가능` · `선행 부족` · 열 수 없음의 까닭으로 나눈다.

**Architecture:** 순수 규칙 `research_plan` 에 `Research::Unlock` 을 더한다 — 열 수 있는 항목의 직접 선행을 모아 기존 `complete()` 에 넘긴다. 쓰기는 기존 연구 쓰기 경로(`game_write_research`)가 "켜기"로 한다.
스냅숏이 기술 · 설계의 지역 마스크, 설계의 특수 깃발, 플레이어 지역의 마스크를 더 읽는다(읽기만). 목록(`techs.cpp`)이 상태를 나누고, 창(`ui.cpp`)이 단추 둘을 더한다.

**Tech Stack:** C++(MSVC, `uv run srkit toybox-build`), Dear ImGui, pytest + ctypes.

**Spec:** [docs/superpowers/specs/2026-10-15-toybox-research-unlock-design.md](../specs/2026-10-15-toybox-research-unlock-design.md)

## Global Constraints

- 쓰는 곳 · 부르는 함수는 늘지 않는다: 플레이어의 보유 비트(묶음이 없으면 새 묶음), 대기열 노드의 "뺐다" 깃발, "지역의 효과를 다시 셈"(플레이어 인덱스) — 지금의 "완료"와 같다.
- 공용 표(지역 마스크 · 연구 대상 · 깃발 · 연구 기간)에는 쓰지 않는다. 항목 자체의 비트는 켜지 않는다.
- 읽기만 하는 칸(build 21347933): 기술 `+0x28`(qword 지역 마스크), 설계 `+0x18`(qword 지역 마스크), 설계 `+0xEC` 의 비트 `0x1`(특수), 플레이어 지역 객체 `+0x40`(qword).
- 열 수 없음의 글: `다른 지역 전용` · `연구 대상 아님` · `특수 설계`.
- 코드를 고치면 `uv run srkit toybox-build` → `uv run pytest`.

## 설계서와 다른 것 (계획에서 정했다)

- **새 서명을 더하지 않는다.** 설계서는 읽는 칸 넷을 연구 묶음의 서명에 넣자고 했다. 기술 · 설계의 칸은 이미 서명이 박은 레코드 크기 안의 자리이고, 잘못 읽어도 결과는 "열 수 없음"의 표시가 틀리는 것과
  그 항목의 선행을 주지 않는 것뿐이다(쓰는 곳은 플레이어의 선행 비트 그대로). 서명 추가(바이트를 게임에서 뽑아 `RESEARCH_PINS` 를 고치는 일)의 값에 비해 얻는 것이 작다. Task 3 에서 설계서를 고친다.
- **`선행` 열은 남긴다.** 상태 열이 나뉘어도 어느 선행이 모자란지(풍선말)를 보이는 데 쓴다.

## Review Focus

- 고른 것에 이미 보유 · 대기열인 항목과 열 수 없는 항목이 섞여 있다 — 열 수 있는 것만 열고 나머지는 세기만 한다(Task 1).
- 직접 선행 가운데 표에 없는 번호 · 0 이 있다 — 건너뛰고, 모자란 선행이 없으면 "이미 열림"으로 센다(Task 1).
- 설계의 `held`(깃발 A 또는 B)는 지금 "선행을 따라가지 않는다"로 쓰인다 — 특수(A)만 열 수 없음이고 B 는 연다(Task 1).
- 플레이어 지역 마스크가 0 이다(읽지 못했다) — 마스크가 있는 항목은 모두 `다른 지역 전용`으로 막힌다. 게임도 같은 셈이다(`test` 가 0)(Task 1).
- 선행이 이미 대기열에 있다 — `complete()` 처럼 그 노드도 대기열에서 뺀다(Task 1).

---

### Task 1: 규칙과 스냅숏 — `Research::Unlock`

**Files:**
- Modify: `native/srtoybox/research.h`, `native/srtoybox/research.cpp`
- Modify: `native/srtoybox/locate.h` (상수 넷), `native/srtoybox/game.cpp` (`shoot` 의 읽기, `game_write_research` 의 켜기)
- Modify: `native/srtoybox/exports.cpp` (`tables_from` · `srtoybox_research_plan` · action 매핑 셋), `native/srtoybox/keeper.cpp` (동사)
- Test: `tests/test_toybox_research.py`

**Interfaces:**
- Produces: `Research::Unlock`; `TechRow::mask` · `DesignRow::mask`(uint64_t) · `DesignRow::special`(bool); `ResearchTables::region_mask`(uint64_t);
  `const int BLOCK_NONE = 0, BLOCK_REGION = 1, BLOCK_CLOSED = 2, BLOCK_SPECIAL = 3, BLOCKS = 4;`
  `int tech_block(const TechRow &, uint64_t region_mask)`, `int design_block(const DesignRow &, uint64_t region_mask)`, `std::string block_label(int)`;
  `ResearchPlan::opened` · `already`(int) · `blocked[BLOCKS]`(int); 테스트 action 값 `2` = Unlock.

- [ ] **Step 1: 실패하는 시험** — `tests/test_toybox_research.py` 에 `UNLOCK = 2` 를 더하고(`COMPLETE, REVOKE = 0, 1` 줄 아래), `plan()` 이 `unlock` 줄을 읽게 고친다(돌려주는 dict 에 `"unlock": tuple(int(n) for n in lines.get("unlock", "").split())`). 시험:

```python
def test_unlock_completes_only_the_missing_direct_prerequisites(lib):
    """기술 3 의 선행 2 가 없고 2 의 선행 1 도 없다. 3 은 보유가 되지 않고 2 · 1 만 — 3 이 게임의 "가능한 연구"에 나온다."""
    got = plan(lib, [tech(1), tech(2, 1), tech(3, 2)], "items t3", action=UNLOCK)
    assert got["techs"] == [1, 2] and got["designs"] == [] and got["asked"] == (0, 0)
    assert got["unlock"] == (1, 0, 0, 0, 0)                                  # 연 것 · 이미 열림 · 다른 지역 · 연구 대상 아님 · 특수
    assert got["text"] == "연구 가능으로 — 항목 1개 열림 · 선행 기술 2개 완료"


def test_unlock_skips_held_queued_and_already_open_items(lib):
    rows = [tech(1, mine=True), tech(2, 1), tech(3, mine=True), tech(4, 9), node(1, 5), tech(5, 1)]
    got = plan(lib, rows, "items t2 t3 t5", action=UNLOCK)
    assert got["techs"] == [] and got["unlock"] == (0, 3, 0, 0, 0)          # 2: 선행 보유(이미 열림) · 3: 보유 · 5: 대기열
    assert got["text"] == "연구 가능으로 — 이미 열림 3개"


def test_unlock_of_a_design_brings_its_four_prerequisites(lib):
    got = plan(lib, [tech(1), tech(2, mine=True), tech(3), design(7, 1, 2, 3)], "items d7", action=UNLOCK)
    assert got["techs"] == [1, 3] and got["designs"] == [] and got["unlock"] == (1, 0, 0, 0, 0)


def test_unlock_refuses_what_the_game_would_still_hide(lib):
    """지역 마스크가 맞지 않는 기술 · 설계, 연구 대상이 아닌 설계, 특수 설계(+0xEC 의 비트 1)는 선행을 채워도 게임이 보이지 않는다 — 쓰지 않고 센다.
    깃발 B(held 이지만 특수가 아닌 것)는 연다."""
    rows = ["region 4", tech(1), tech(2, 1), "tmask 2 2", tech(3, 1), "tmask 3 6",
            design(7, 1), "dmask 7 8 0", design(8, 1, is_open=False), design(9, 1), "dmask 9 0 1", design(10, 1, held=True)]
    got = plan(lib, rows, "items t2 t3 d7 d8 d9 d10", action=UNLOCK)
    assert got["techs"] == [1] and got["unlock"] == (2, 0, 2, 1, 1)          # 열림: t3(마스크 6 & 4) · d10 / 다른 지역: t2 · d7
    assert got["text"] == "연구 가능으로 — 항목 2개 열림 · 선행 기술 1개 완료 · 열 수 없음 4개(다른 지역 전용 2 · 연구 대상 아님 1 · 특수 설계 1)"


def test_unlock_takes_a_queued_prerequisite_off_the_queue(lib):
    got = plan(lib, [tech(1), node(1, 1), tech(2, 1)], "items t2", action=UNLOCK)
    assert got["techs"] == [1] and got["nodes"] == [0]


def test_a_zero_region_mask_blocks_every_masked_item(lib):
    got = plan(lib, [tech(1), tech(2, 1), "tmask 2 1"], "items t2", action=UNLOCK)   # region 줄이 없다 = 0
    assert got["techs"] == [] and got["unlock"] == (0, 0, 1, 0, 0)
```

가짜 메모리 시험(같은 파일의 `Lab` 쪽 시험을 따라 — 이 파일에서 `srtoybox_research_write` 를 부르는 기존 시험 하나를 본떠): 기술 표에 기술 1 · 2(선행 1)를 두고 `action=2`, what `items t2` 로 쓴 뒤
기술 1 의 플레이어 비트만 켜졌고 기술 2 는 꺼진 채, 다른 나라(POLAND)의 비트와 기술 2 의 묶음 칸이 그대로인지 본다(이름: `test_unlock_writes_only_the_prerequisite_bit`).

- [ ] **Step 2: 실패를 본다** — `uv run pytest tests/test_toybox_research.py -k unlock -q` → `unlock` 줄이 없어 실패.

- [ ] **Step 3: 구현**

`locate.h` 의 `DESIGN_OWNERS` 줄 아래:

```cpp
const uint32_t TECH_MASK = 0x28;            // qword. 지역 마스크 — 0 이 아니면 플레이어 지역의 REGION_MASK 와 겹쳐야 연구할 수 있다(0x4e3a44). 읽기만
const uint32_t DESIGN_MASK = 0x18;          // qword. 〃 (0x7abcb1). 읽기만
const uint32_t DESIGN_SPECIAL_BIT = DESIGN_HOLD_A_BIT;   // DESIGN_HOLD_A 의 이 비트가 켜진 설계는 연구 목록에 나오지 않는다(0x7abc4e)
const uint32_t REGION_MASK = 0x40;          // qword. 지역 객체의 지역 마스크. 읽기만
```

`research.h`: `TechRow` 에 `uint64_t mask = 0;`, `DesignRow` 에 `uint64_t mask = 0; bool special = false;`(주석: 게임이 연구 목록에서 빼는 설계 — `+0xEC` 의 비트 1), `ResearchTables` 에 `uint64_t region_mask = 0;`.
`enum class Research { Complete, Revoke, Unlock };`. `ResearchPlan` 에 `int opened = 0, already = 0; int blocked[4] = {};`. 그리고:

```cpp
const int BLOCK_NONE = 0, BLOCK_REGION = 1, BLOCK_CLOSED = 2, BLOCK_SPECIAL = 3, BLOCKS = 4;
int tech_block(const TechRow &row, uint64_t region_mask);     // BLOCK_NONE · BLOCK_REGION
int design_block(const DesignRow &row, uint64_t region_mask); // 연구 대상 아님 → 특수 → 지역 의 순서로 첫째
std::string block_label(int block);                           // "다른 지역 전용" · "연구 대상 아님" · "특수 설계" · 빈 글
```

주석의 규칙 설명(`// 완료(Complete)` 위)에 Unlock 을 더한다: "연구 가능으로(Unlock) — Items 만. 항목마다 보유 · 대기열이면 이미 열림, 열 수 없으면(tech_block · design_block) 세기만, 아니면 직접 선행 가운데
표에 있고 보유하지 않은 것을 모은다(없으면 이미 열림). 모은 선행에 완료 규칙을 쓴다(asked 는 0). 항목 자체의 비트는 바꾸지 않는다."

`research.cpp` — 익명 이름공간 안에 `revoke` 다음:

```cpp
ResearchPlan unlock(const ResearchTables &t, const ResearchWhat &what, bool can_house)
{
    ResearchPlan counts;
    if (what.kind != ResearchWhat::Items)
        return counts;
    const std::vector<int> tech_at = index_of(t.techs, t.tech_slots), design_at = index_of(t.designs, t.design_slots);
    ResearchWhat needs;                         // 모은 직접 선행 — 완료 규칙에 넘긴다
    const auto take = [&](const int *ids, int count) {
        bool missing = false;
        for (int n = 0; n < count; n++) {
            const int i = find(tech_at, ids[n]);
            if (i >= 0 && !t.techs[static_cast<size_t>(i)].mine) {
                needs.techs.push_back(ids[n]);
                missing = true;
            }
        }
        (missing ? counts.opened : counts.already)++;
    };
    for (int id : what.techs) {
        const int i = find(tech_at, id);
        if (i < 0)
            continue;
        const TechRow &row = t.techs[static_cast<size_t>(i)];
        if (row.mine || row.queued)
            counts.already++;
        else if (const int block = tech_block(row, t.region_mask))
            counts.blocked[block]++;
        else
            take(row.needs, 2);
    }
    for (int id : what.designs) {
        const int i = find(design_at, id);
        if (i < 0)
            continue;
        const DesignRow &row = t.designs[static_cast<size_t>(i)];
        if (row.mine || row.queued)
            counts.already++;
        else if (const int block = design_block(row, t.region_mask))
            counts.blocked[block]++;
        else
            take(row.needs, 4);
    }
    ResearchPlan plan = complete(t, needs, can_house);
    plan.asked_techs = plan.asked_designs = 0;
    plan.opened = counts.opened;
    plan.already = counts.already;
    for (int b = 0; b < BLOCKS; b++)
        plan.blocked[b] = counts.blocked[b];
    return plan;
}
```

이름공간 밖:

```cpp
int tech_block(const TechRow &row, uint64_t region_mask)
{
    return row.mask != 0 && (row.mask & region_mask) == 0 ? BLOCK_REGION : BLOCK_NONE;
}

int design_block(const DesignRow &row, uint64_t region_mask)
{
    return !row.open ? BLOCK_CLOSED : row.special ? BLOCK_SPECIAL : row.mask != 0 && (row.mask & region_mask) == 0 ? BLOCK_REGION : BLOCK_NONE;
}

std::string block_label(int block)
{
    return block == BLOCK_REGION ? "다른 지역 전용" : block == BLOCK_CLOSED ? "연구 대상 아님" : block == BLOCK_SPECIAL ? "특수 설계" : "";
}
```

`research_plan` 의 첫 줄: `ResearchPlan plan = action == Research::Complete ? complete(tables, what, can_house) : action == Research::Unlock ? unlock(tables, what, can_house) : revoke(tables, what);`.
`research_summary` 맨 앞에 Unlock 갈래:

```cpp
    if (action == Research::Unlock) {
        std::string text;
        if (plan.opened > 0)
            add(&text, "항목 " + std::to_string(plan.opened) + "개 열림");
        if (!plan.techs.empty())
            add(&text, "선행 기술 " + std::to_string(plan.techs.size()) + "개 완료");
        if (plan.already > 0)
            add(&text, "이미 열림 " + std::to_string(plan.already) + "개");
        int blocked = 0;
        std::string why;
        for (int b = 1; b < BLOCKS; b++)
            if (plan.blocked[b] > 0) {
                blocked += plan.blocked[b];
                why += (why.empty() ? "" : " · ") + block_label(b) + " " + std::to_string(plan.blocked[b]);
            }
        if (blocked > 0)
            add(&text, "열 수 없음 " + std::to_string(blocked) + "개(" + why + ")");
        return text.empty() ? text : "연구 가능으로 — " + text;
    }
```

(`add` 가 " · " 로 잇는지 확인한다 — 기존 글 `기술 1개 · 부대 설계 1개` 의 꼴이다.)

`game.cpp` 의 `shoot`: 기술 줄에 `row.mask = field<uint64_t>(record, TECH_MASK);`, 설계 줄에 `row.mask = field<uint64_t>(record, DESIGN_MASK); row.special = (field<uint32_t>(record, DESIGN_HOLD_A) & DESIGN_SPECIAL_BIT) != 0;`,
표의 전역을 읽은 뒤 `peek(reinterpret_cast<const void *>(player + REGION_MASK), &t.region_mask, sizeof(t.region_mask));`(읽지 못하면 0 으로 둔다 — 마스크가 있는 항목이 모두 막힌다. 실패로 치지 않는다).
`game_write_research` 의 `poke_bits(item.owners + byte, mask, action == Research::Complete, 1)` → `action != Research::Revoke`.

`exports.cpp`: `tables_from` 에 줄 셋 — `region <마스크>` → `t.region_mask`, `tmask <번호> <마스크>` → 그 번호의 기술 행의 `mask`, `dmask <번호> <마스크> <특수>` → 그 설계 행의 `mask` · `special`
(행은 앞 줄에서 이미 넣었다 — 번호로 뒤에서부터 찾는다. 마스크는 10진수). action 매핑 셋(447 · 641 · 721행 근처)을 `action == 0 ? Complete : action == 2 ? Unlock : Revoke` 로.
`srtoybox_research_plan` 의 출력에 줄 하나: `"\nunlock " + opened + ' ' + already + ' ' + blocked[1] + ' ' + blocked[2] + ' ' + blocked[3]`(text 줄 앞에. 함수 주석의 "일곱 줄"을 "여덟 줄"로).
`keeper.cpp:332` 의 동사: `r.action == Research::Complete ? "완료" : r.action == Research::Unlock ? "연구 가능으로" : "미완료"`.

- [ ] **Step 4: 통과** — `uv run srkit toybox-build` → `uv run pytest tests/test_toybox_research.py -q` 전부 PASS.

- [ ] **Step 5: 커밋** — `feat: ToyBox 연구 — 연구 가능으로(선행만 채워 열기)의 규칙과 쓰기`

### Task 2: 목록의 상태와 단추

**Files:**
- Modify: `native/srtoybox/techs.h`, `native/srtoybox/techs.cpp`, `native/srtoybox/ui.cpp`, `native/srtoybox/exports.cpp` (`srtoybox_research_rows` 의 show 값)
- Test: `tests/test_toybox_research.py`(목록), `tests/test_toybox.py` · `tests/toybox_overlay_probe.py`(창)

**Interfaces:**
- Consumes: Task 1 의 `tech_block` · `design_block` · `block_label` · `Research::Unlock` · `ResearchTables::region_mask`.
- Produces: `STATE_OPEN = 3, STATE_LACKING = 4, STATE_BLOCKED = 5`; `ListRow::block`(int); `std::string state_label(const ListRow &row, bool units)`; `Show::Open` · `Show::Lacking`.

- [ ] **Step 1: 실패하는 시험** — `srtoybox_research_rows` 를 부르는 기존 목록 시험 하나(같은 파일)를 본떠 `test_rows_split_not_held_into_open_lacking_and_blocked`:
  기술 1(보유) · 2(선행 1 → 연구 가능) · 3(선행 4, 4 는 미보유 → 선행 부족) · 5(`tmask 5 2`, `region 4` → `다른 지역 전용`) · 6(대기열 → 연구 중)의 상태 글이 `보유` · `연구 가능` · `선행 부족` · `다른 지역 전용` · `연구 중` 인지,
  보기 `Open` 이 2 만, `Lacking` 이 3 만 내는지 본다(새 보기 값은 `exports.cpp` 의 show 정수 매핑 끝에 6 · 7 로 더한다).
  창: `tests/test_toybox.py:1042` 의 기대 dict 에 `"list:unlock": "고른 것 연구 가능으로", "list:all_unlock": "보이는 것 전부 연구 가능으로"` 를 더한다(부대 탭도 같은 글).

- [ ] **Step 2: 실패를 본다** — `uv run pytest tests/test_toybox_research.py -k rows_split -q` 와 그 창 시험.

- [ ] **Step 3: 구현**
  - `techs.h`: 상수 셋 · `ListRow::block` · `Show::Open, Show::Lacking`(enum 끝), `state_label(const ListRow &row, bool units)` — 보유는 `units ? "등록" : "보유"`, 연구 중 `연구 중`,
    연구 가능 `연구 가능`, 선행 부족 `선행 부족`, 막힘 `block_label(row.block)`. 옛 `state_label(int)` 은 지운다(부르는 곳: `ui.cpp:1130` — 새 함수로 바꾸고 `units` 삼항을 없앤다).
  - `techs.cpp`: `research_rows` 에서 줄의 선행을 센 뒤 `STATE_NONE` 인 줄을 나눈다 —
    ```cpp
    if (row.state == STATE_NONE) {
        row.block = designs ? design_block(design, tables.region_mask) : tech_block(tech, tables.region_mask);
        row.state = row.block != BLOCK_NONE ? STATE_BLOCKED : row.needs_mine == row.needs ? STATE_OPEN : STATE_LACKING;
    }
    ```
    (변수 이름은 그 함수의 것에 맞춘다.) 보기 `Open` · `Lacking` 은 그 상태만 지난다. `NotMine` 은 그대로 보유가 아닌 모두다.
  - `ui.cpp`: 보기 콤보에 `연구 가능` · `선행 부족` 을 더한다. 단추 줄(`list:all_undo` 의 `risky` 다음) 아래 새 줄:
    ```cpp
    const char *const LIST_UNLOCK_ALL = "list:all_unlock";   // (파일 머리의 LIST_UNDO_ALL 옆에)
    ...
    ImGui::BeginDisabled(off || chosen.empty());
    if (ImGui::Button("고른 것 연구 가능으로"))
        list_request(L, Research::Unlock, chosen, "고른 것");
    note("list:unlock", "고른 것 연구 가능으로");
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled))
        wrapped_tooltip("항목 자체는 보유가 되지 않는다 — 모자란 선행 기술만 보유로 준다. 연구는 게임에서 한다");
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::BeginDisabled(off || visible.empty());
    risky(LIST_UNLOCK_ALL, "보이는 것 전부 연구 가능으로", visible, "보이는 것", Research::Unlock);
    ImGui::EndDisabled();
    ```
    `risky` 는 `item_list` 안의 람다(965행)이고 `Research::Revoke` 를 박아 두었다 — 끝에 `Research action = Research::Revoke` 인자를 더해 `list_request(L, action, ids, what)` 로 하고,
    새 부름은 `risky(LIST_UNLOCK_ALL, "보이는 것 전부 연구 가능으로", visible, "보이는 것", Research::Unlock)` 로 한다. `wrapped_tooltip`(379행)은 이미 `item_list` 위에 있다.
  - 기존 시험에서 `미보유` · `미등록` 을 기대하던 곳은 위 규칙의 글로 고친다(선행을 모두 보유 → `연구 가능`, 아니면 `선행 부족`). 기대를 고친 시험마다 까닭을 한 줄 주석으로.

- [ ] **Step 4: 통과** — `uv run srkit toybox-build` → `uv run pytest -q` 전부 PASS.

- [ ] **Step 5: 커밋** — `feat: ToyBox 연구 목록 — 상태(연구 가능 · 선행 부족 · 열 수 없음)와 "연구 가능으로" 단추`

### Task 3: 문서와 게임 확인

- [ ] `docs/10-toybox.md` 의 연구 목록 설명(115행 근처의 "단추 넷")에 단추 둘 · 상태 다섯을 더하고, "다음 단계" 표에 줄 하나(코드 끝 · 게임 확인 전).
  설계서의 "쓰는 곳 · 부르는 것"의 서명 문장을 이 계획의 "설계서와 다른 것"대로 고친다. `CLAUDE.md` 는 쓰는 곳이 늘지 않으므로 고치지 않는다.
- [ ] 커밋 · 푸시 · `develop` PR(본문에 `uv run pytest` 결과).
- [ ] 게임 확인 U1 ~ U4(설계서의 표)는 DLL 설치(`srkit deploy toybox --apply` — 사용자가 한다) 뒤 백그라운드 에이전트로. 결과를 설계서 · `docs/10` 에 적는다.
