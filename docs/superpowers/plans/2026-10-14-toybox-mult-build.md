# ToyBox 배율 — 건설 · 유닛 생산 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 배율 탭에 유닛 생산 속도 · 시설 건설 속도 배율(곱 보정 칸 15 · 16)과 "다음 자정에 완료" 단추를 더한다.

**Architecture:** 묶음 7 의 곱 보정 칸 유지(`keeper.cpp` 의 `mult_cells`)에 칸 둘을 더한다. 즉시 완료는 같은 고리 안의 "완료 대기" 상태로,
대기 동안 두 칸에 게임의 값 × 1000 을 쓰고, 날의 칸이 오른 뒤 게임이 칸을 다시 셈한 것을 보면 푼다. 게임의 함수는 부르지 않는다.

**Tech Stack:** C++(MSVC, `uv run srkit toybox-build`), Dear ImGui, pytest + ctypes(가짜 게임 메모리).

**Spec:** [docs/superpowers/specs/2026-10-14-toybox-mult-build-design.md](../specs/2026-10-14-toybox-mult-build-design.md)

## Global Constraints

- 쓰는 곳은 플레이어의 곱 보정 줄의 칸 15 · 16 만 는다. 다른 지역의 줄 · 항목 객체 · 대기열에는 쓰지 않는다. 게임의 함수를 부르지 않는다.
- 배율 범위 `MULT_CELL_MIN`(1) … `MULT_PERCENT_MAX`(1000). 설정 줄 `mult.unitbuild` · `mult.facbuild`(기본 100).
- 대기의 배수 `RUSH_TIMES = 1000.0f`, 대기 동안 두 칸의 쓰기 한도 `RUSH_VALUE_MAX = 100000.0f`. 다른 칸의 한도는 `MUL_VALUE_MAX`(1000) 그대로.
- "게임의 값"을 가려 읽는 검사(`cell_sane` — 1000 이상이면 건드리지 않는다)는 그대로다.
- 대기는 저장하지 않고 `배율 적용` 과 상관없이 듣는다. 판 · 플레이어가 바뀌면 버린다.
- 코드를 고치면 `uv run srkit toybox-build` 뒤 `uv run pytest` 를 돌린다.

## Review Focus

- 대기를 누른 채 날이 오르기 **전에** 게임이 칸을 다시 셈한다(연구가 끝나는 날 등) — 대기가 풀리지 않고 큰 값을 다시 써야 한다(Task 2 의 시험).
- 날의 칸만 오르고 칸이 아직 ToyBox 의 값이다(날의 셈 도중에 본 틱) — 대기를 풀지 않아야 한다(Task 2).
- `배율 적용` 이 꺼져 있고 지켜 둔 칸이 없을 때 대기를 누른다 — `mult_tick` 의 첫 조기 반환에 걸리지 않아야 한다(Task 2).
- 대기 중에 배율 설정을 바꾼다 — 대기 값(게임의 값 × 1000)이 그대로여야 하고, 풀린 뒤에 새 배율로 간다(Task 2).
- 칸 15 · 16 의 게임 값이 말이 안 된다(0 · NaN · 1000 이상) — 배율도 대기도 쓰지 않는다(Task 1 · 2).

---

### Task 1: 배율 둘 — 칸 15 · 16

**Files:**
- Modify: `native/srtoybox/locate.h:237` (칸 번호 상수)
- Modify: `native/srtoybox/keeper.h` (`Mult`), `native/srtoybox/keeper.cpp` (`cell_percent` · `operator==` · `mult_count`)
- Modify: `native/srtoybox/settings.h:26-32` · `native/srtoybox/settings.cpp` (`parse_mult` · 쓰기), `native/srtoybox/ui.cpp` (`mult_of`)
- Modify: `native/srtoybox/exports.cpp` (`srtoybox_keeper_mult` 의 키)
- Test: `tests/test_toybox_mult.py`

**Interfaces:**
- Produces: `MUL_UNIT_BUILD = 15`, `MUL_FAC_BUILD = 16`(locate.h), `Mult::unitbuild` · `Mult::facbuild`(int, 퍼센트), `Settings::mult_unitbuild` · `Settings::mult_facbuild`,
  테스트 키 `unitbuild=` · `facbuild=`.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_toybox_mult.py` 의 `test_the_cells_are_multiplied_only_in_the_players_row` 아래에:

```python
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
```

`test_the_settings_keep_the_multipliers` 의 끝에:

```python
    got = norm("mult.unitbuild=1000\nmult.facbuild=1\n")
    assert got["mult.unitbuild"] == "1000" and got["mult.facbuild"] == "1"
    bad = norm("mult.unitbuild=0\nmult.facbuild=1001\n")
    assert bad["mult.unitbuild"] == "100" and bad["mult.facbuild"] == "100"
```

- [ ] **Step 2: 실패를 본다** — `uv run pytest tests/test_toybox_mult.py -k "build_speeds or settings_keep" -v` → `srtoybox_keeper_mult` 가 -1(모르는 키), 설정 줄이 없다.

- [ ] **Step 3: 구현**

`locate.h:237` 아래:

```cpp
const int MUL_UNIT_BUILD = 15, MUL_FAC_BUILD = 16;   // 유닛 생산 속도 · 시설 건설 속도(기술 효과 15 · 16 — 날마다의 진행에 곱한다, 0x843567 · 0x77fb14)
```

`keeper.h` 의 `Mult` 에 `int research` 다음 줄:

```cpp
    int unitbuild = 100, facbuild = 100;       // 유닛 생산 · 시설 건설 속도 — 곱 보정 칸 15 · 16. MULT_CELL_MIN … MULT_PERCENT_MAX
```

`keeper.h` 의 머리 주석 `out · use · raw` 줄을 `out · use · raw · unitbuild · facbuild` 로 고친다.

`keeper.cpp` 의 `cell_percent` 맨 앞:

```cpp
    if (cell == MUL_UNIT_BUILD)
        return m.unitbuild;
    if (cell == MUL_FAC_BUILD)
        return m.facbuild;
```

`operator==` 의 첫 비교에 `|| a.unitbuild != b.unitbuild || a.facbuild != b.facbuild`, `mult_count` 의 첫 줄에 `+ (m.unitbuild != 100) + (m.facbuild != 100)`.

`settings.h` 의 `mult_research` 줄 다음: `int mult_unitbuild = 100, mult_facbuild = 100;` (주석 26행에 `"mult.unitbuild" · "mult.facbuild"` 를 더한다).

`settings.cpp` 의 `parse_mult` 에서 `research` 갈래 다음:

```cpp
    } else if (rest == "unitbuild") {
        if (in(SETTINGS_MULT_CELL_MIN))
            s.mult_unitbuild = static_cast<int>(n);
    } else if (rest == "facbuild") {
        if (in(SETTINGS_MULT_CELL_MIN))
            s.mult_facbuild = static_cast<int>(n);
```

쓰는 쪽(195 ~ 197행)의 `mult.research=` 줄 뒤에 `+ "mult.unitbuild=" + std::to_string(s.mult_unitbuild) + "\nmult.facbuild=" + std::to_string(s.mult_facbuild) + "\n"`.

`ui.cpp` 의 `mult_of` 에 `m.unitbuild = s.mult_unitbuild; m.facbuild = s.mult_facbuild;`.
`send_mult` 의 로그 줄의 "물자의 배율" 셈에서 `- (want.unitbuild != 100) - (want.facbuild != 100)` 을 더 빼고, 형식에 `건설 %d%% · 생산 %d%%` 를 더한다.

`exports.cpp` 의 `srtoybox_keeper_mult` 에서 `research` 갈래 다음: `else if (key == "unitbuild") m.unitbuild = n; else if (key == "facbuild") m.facbuild = n;` (주석의 키 목록에도).

- [ ] **Step 4: 통과를 본다** — `uv run srkit toybox-build` → `uv run pytest tests/test_toybox_mult.py -v` 전부 PASS.

- [ ] **Step 5: 커밋** — `git commit -m "feat: ToyBox 배율 — 유닛 생산 · 시설 건설 속도(곱 보정 칸 15 · 16)"`

### Task 2: 다음 자정에 완료(대기)

**Files:**
- Modify: `native/srtoybox/game.h:284-287` · `native/srtoybox/game.cpp:2674-2696` (`game_write_mult` 의 한도)
- Modify: `native/srtoybox/keeper.h` · `native/srtoybox/keeper.cpp` (`mult_cells` · `mult_tick` · 새 함수 둘 · reset)
- Modify: `native/srtoybox/exports.cpp` (`srtoybox_keeper_rush` · `srtoybox_rush_pending`)
- Test: `tests/test_toybox_mult.py`

**Interfaces:**
- Consumes: Task 1 의 `MUL_UNIT_BUILD` · `MUL_FAC_BUILD` · `Mult::unitbuild/facbuild`.
- Produces: `Wrote game_write_mult(int cell, float value, float max = MUL_VALUE_MAX)`, `const float RUSH_TIMES = 1000.0f, RUSH_VALUE_MAX = 100000.0f`(keeper.h),
  `std::string keeper_rush()`(시작. 못 하면 까닭, 되면 빈 글), `bool keeper_rush_pending()`. 내보내기 `int srtoybox_keeper_rush(char *out, int size)`(put 의 꼴 — 까닭의 글), `int srtoybox_rush_pending(void)`(0 / 1).

- [ ] **Step 1: 실패하는 시험을 쓴다** — `lib` 고정물에 `lib.srtoybox_keeper_rush.argtypes = [ctypes.c_char_p, ctypes.c_int]`, `Game` 에:

```python
    def rush(self) -> str:
        return text(self.lib.srtoybox_keeper_rush)

    def pending(self) -> bool:
        return self.lib.srtoybox_rush_pending() == 1

    def recompute(self) -> None:
        """게임이 날 끝에 하는 "효과를 다시 셈": 플레이어 줄을 처음 값으로."""
        for cell in range(200):
            self.set_cell(GERMANY, cell, 1.0 + cell / 100.0)
```

시험:

```python
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
```

(`FakeGame.menu()` 가 "진행 중이 아님"이다 — `test_nothing_happens_in_the_menu_or_in_multiplayer` 가 쓰는 것.)

- [ ] **Step 2: 실패를 본다** — `uv run pytest tests/test_toybox_mult.py -k rush -v` → `srtoybox_keeper_rush` 가 없다.

- [ ] **Step 3: 구현**

`game.h` 의 `game_write_mult` 를 `Wrote game_write_mult(int cell, float value, float max = MUL_VALUE_MAX);` 로(주석: "max 는 완료 대기의 두 칸만 RUSH_VALUE_MAX 로 넘긴다").
`game.cpp:2691` 의 `value < MUL_VALUE_MAX` 를 `value < max && max <= 100000.0f`.

`keeper.h` 의 `MultStats` 앞:

```cpp
// 다음 자정에 완료(설계서 2026-10-14). 누르면 그날의 셈 하루 동안 칸 15 · 16 에 게임의 값 × RUSH_TIMES 를 쓴다(배율 대신). 날의 칸이 오른 뒤
// 게임이 그 칸을 다시 셈한 것을 보면 푼다. 저장하지 않고 배율 적용과 상관없이 듣는다. 판 · 플레이어가 바뀌면 버린다.
const float RUSH_TIMES = 1000.0f, RUSH_VALUE_MAX = 100000.0f;
std::string keeper_rush();                      // 시작한다. 못 하면 까닭(게임 밖 · 값 쓰기 꺼짐 · 곱 보정 표나 날의 칸을 못 찾음), 되면 빈 글
bool keeper_rush_pending();
```

`keeper.cpp` 의 전역(`g_mult_told` 다음):

```cpp
bool g_rush;                        // 다음 자정에 완료 — 대기 중
uint32_t g_rush_day;                // 누른 때의 날의 칸
int g_rush_index;                   // 누른 때의 플레이어 지역 인덱스
```

`forget_cells()` 에 `g_rush = false;`(게임 밖 · 나라가 바뀜에서 부른다).

`mult_cells()` 의 고리를 이렇게 바꾼다(바뀌는 줄만):

```cpp
    const Daily today = g_rush ? game_daily() : Daily();   // 고리 앞에서 한 번
    const bool day_passed = g_rush && today.ok && today.day != g_rush_day;
    for (int cell = 1; cell < MUL_CELLS; cell++) {
        const int percent = cell_percent(g_mult, cell);
        if (percent == 0)
            continue;
        CellMemo &m = g_cells[cell];
        const float now = row[cell];
        const bool build = cell == MUL_UNIT_BUILD || cell == MUL_FAC_BUILD;
        if (g_rush && build && day_passed && !(m.have && now == m.wrote)) {
            g_rush = false;                     // 날이 오른 뒤 게임이 다시 셈했다 — 그날의 셈이 지났다
            log_line("배율: 다음 자정에 완료 — 풀었다");
        }
        const bool rush = g_rush && build;
        const bool scaled = rush || (g_mult.on && percent != 100);
        const float times = rush ? RUSH_TIMES : percent / 100.0f;
        float want = 0;
        if (m.have && now == m.wrote) {
            want = scaled ? m.base * times : m.base;
            ...(그대로)
        } else {
            m = CellMemo();
            if (!scaled || !cell_sane(now))
                continue;
            m.base = now;
            want = now * times;
        }
        const float max = rush ? RUSH_VALUE_MAX : MUL_VALUE_MAX;
        if (!(std::isfinite(want) && want > 0.0f && want < max)) {
            m = CellMemo();
            continue;
        }
        const Wrote wrote = game_write_mult(cell, want, max);
        ...(그대로)
```

`mult_tick()` 의 첫 조기 반환을 `if (!g_mult.on && g_cells_index == 0 && !g_rush)` 로, `if (!g_mult.on) { ... }` 안의 `g_cells_index = 0` 조건을 `g_mult_stats.held == 0 && !g_rush` 로.

새 함수(`keeper_mult` 다음):

```cpp
std::string keeper_rush()
{
    if (!game_writes())
        return "값 쓰기가 꺼져 있습니다.";
    const std::string cells = game_mult_off(MULT_PART_CELLS);
    if (!cells.empty())
        return cells;
    const Daily d = game_daily();
    if (!d.ok)
        return "게임을 진행 중일 때만 됩니다.";
    std::lock_guard<std::mutex> lock(g_lock);
    g_rush = true;
    g_rush_day = d.day;
    g_rush_index = d.index;
    g_mult_due = true;
    log_line("배율: 다음 자정에 완료 — 대기 (날 %u)", d.day);
    return "";
}

bool keeper_rush_pending()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_rush;
}
```

`mult_cells()` 에서 `index != g_cells_index` 로 기억을 버릴 때 `g_rush_index != index` 이면 대기도 버린다 — `forget_cells()` 가 이미 `g_rush = false` 를 하므로, **처음 틱**(g_cells_index 가 0 이다)에서 대기가 지워지지 않게 `if (index != g_cells_index)` 를
`if (index != g_cells_index) { const bool keep = g_rush && index == g_rush_index; forget_cells(); g_rush = keep; g_cells_index = index; }` 로 쓴다.
`keeper_reset_for_test()` 에 `g_rush = false;`.

`exports.cpp`(`srtoybox_mult_stats` 다음):

```cpp
// 테스트: 다음 자정에 완료를 누른다. 까닭의 글(되면 빈 글).
EXPORT int srtoybox_keeper_rush(char *out, int size)
{
    return put(keeper_rush(), out, size);
}

EXPORT int srtoybox_rush_pending(void)
{
    return keeper_rush_pending() ? 1 : 0;
}
```

- [ ] **Step 4: 통과를 본다** — `uv run srkit toybox-build` → `uv run pytest tests/test_toybox_mult.py -v` 전부 PASS.

- [ ] **Step 5: 커밋** — `git commit -m "feat: ToyBox 배율 — 다음 자정에 생산 · 건설 완료"`

### Task 3: 창 · 문서

**Files:**
- Modify: `native/srtoybox/ui.cpp` (`mult_tab` 의 `연구 속도` 줄 다음)
- Modify: `native/srtoybox/game.h:37-39` (머리말), `CLAUDE.md` (배율 문단), `docs/10-toybox.md` (기능 표의 배율 줄 · "다음 단계" 표), `README.md` (배율 문장)

- [ ] **Step 1: 창** — `mult_input("##research", …)` 의 `ImGui::EndDisabled();` 다음에:

```cpp
    ImGui::BeginDisabled(!cells.empty());
    ImGui::AlignTextToFramePadding();
    ImGui::TextUnformatted("유닛 생산 속도");
    ImGui::SameLine();
    mult_input("##unitbuild", "mult:unitbuild", &g_settings.mult_unitbuild, MULT_CELL_MIN);
    ImGui::SameLine();
    ImGui::TextUnformatted("시설 건설 속도");
    ImGui::SameLine();
    mult_input("##facbuild", "mult:facbuild", &g_settings.mult_facbuild, MULT_CELL_MIN);
    ImGui::SameLine();
    const bool pending = keeper_rush_pending();
    ImGui::BeginDisabled(pending);
    if (ImGui::Button(pending ? "다음 자정에 완료 — 대기 중" : "내 나라의 생산 · 건설을 다음 자정에 완료"))
        g_notice = keeper_rush();
    ImGui::EndDisabled();
    note("mult:rush", pending ? "1" : "0");
    help("help:rush", "다음 날의 셈 하루 동안 생산 · 건설 속도를 1000배로 한다 — 게임이 스스로 끝낸다. 남은 비용이 그날 한꺼번에 빠질 수 있다. 저장하지 않는다");
    ImGui::EndDisabled();
```

(`g_notice` 는 ui.cpp 의 전역 — 다른 탭의 단추와 같은 알림 줄이다.) `help("help:mult", …)` 의 글에 "생산 · 건설 속도는 게임의 보정 값에 곱한다" 를 더한다.

- [ ] **Step 2: 문서**
  - `game.h:37` 과 `CLAUDE.md` 의 "칸 서른셋(… 산출 72 … 82)" → "칸 서른다섯(… 산출 72 … 82 · 유닛 생산 속도 15 · 시설 건설 속도 16)". CLAUDE.md 에는 "'다음 자정에 완료'는 그날의 셈 하루 동안 15 · 16 에 게임의 값 × 1000 을 쓴다(2026-10-14)" 한 문장과 설계서 링크.
  - `docs/10-toybox.md` 기능 표의 배율 줄 아래에 두 줄(유닛 생산 · 시설 건설 속도 / 다음 자정에 완료 — "창에서" 는 `–`), "다음 단계" 표에 `7 (가)` 줄(상태: 코드 끝, 게임 확인 전).
  - `README.md` 의 배율 문장에 "유닛 생산 · 시설 건설 속도, 다음 자정에 완료(2026-10-14, 게임에서 보지 않았다)".

- [ ] **Step 3: 빌드 · 전체 시험** — `uv run srkit toybox-build` → `uv run pytest` 전부 PASS(게임 설치본이 있으면 `test_toybox_game.py` 의 서명 시험도).

- [ ] **Step 4: 커밋** — `git commit -m "feat: ToyBox 배율 탭 — 건설 · 생산 줄, 문서"`

### Task 4: 게임 안 확인 B1 ~ B4 (백그라운드 에이전트)

설계서의 "시험" 표 그대로. 임시 `SRTOYBOX_HOME`(새 이름의 폴더), `gamedrive.py start -window`, 2030 - 세계 · 독일의 버리는 판. 날은 한 판 3일 이내(7일마다 자동 저장).
칸 15 · 16 은 `gamedrive.py peek` 에 없다 — 메모리의 그 자리(세계 객체 `0x17a9020` + `0x5456a8` + 인덱스 × `0x320` + 4 × 칸)를 읽는 한 줄을 `peek` 에 더하거나(읽기만) 창의 `지금 N칸` 으로 본다.
본 것을 설계서의 "게임에서 본 것"과 `docs/10` 의 "창에서" 열에 적고, B3 에서 하루에 끝나지 않는 항목이 있으면 사용자에게 알린다(배수를 정하는 것은 사용자다).
끝나면 사용자의 `%APPDATA%\SR2030ToyBox\toybox.ini` 가 그대로인지(md5) 본다.
