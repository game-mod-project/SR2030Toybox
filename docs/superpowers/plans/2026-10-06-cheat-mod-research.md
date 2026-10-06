# 치트·모드 조사와 제작 계획 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supreme Ruler 2030 의 게임 구조·데이터 파일·내장 치트·Workshop 모드를 조사해 `docs/05` ~ `docs/09` 로 남기고, 그 조사를 받치는 읽기 전용 도구 두 개(`srkit inventory`, `srkit probe`)를 만든다.

**Architecture:** 목록은 기계가 뽑고(`srkit inventory` → `build/inventory/*.csv`) 문서는 그 위에 사람이 쓴다. 게임에서 확인할 것은 화면 밖 게임(`scripts/gamedrive.py`)에서 백그라운드로 확인하고, 데이터 수정이 반영되는지는 값 한 곳만 바꾼 시험 모드(`srkit probe` → `srkit deploy`)로 본다. 실제 치트 모드 제작은 이 계획에 없다 — `docs/09` 가 제안까지만 한다.

**Tech Stack:** Python 3.11+ (`uv run`), pytest, 기존 `srkit` 패키지(`srtext`, `korean.decode_cp1252`, `deploy`), `scripts/gamedrive.py`, 내장 브라우저(위키·Workshop 열람), `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-10-06-cheat-mod-research-design.md`

## Global Constraints

- 대상 빌드: Steam appid `2093410`, build `21347933`. 문서 머리와 주소·수치 옆에 빌드 번호를 적는다.
- **게임 설치 폴더는 읽기 전용이다.** 바꾸는 경로는 `uv run srkit deploy <모드> --apply` / `undeploy <모드> --apply` 뿐이다. 이 계획에서 설치하는 것은 `probe-*` 와 `cache-orig` 뿐이고, 실험이 끝나면 되돌린다.
- 게임 폴더: `E:\SteamLibrary\steamapps\common\Supreme Ruler 2030` (`srkit.toml` 의 `game_dir`). Bash 예시의 `G` 는 `G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"` 이다.
- Python 은 `uv run` 으로만 실행한다. 코드를 고치면 `uv run pytest` 를 돌린다(시작 시점: 54 passed).
- 게임 텍스트는 CP1252 다. 읽을 때 `korean.decode_cp1252` 를 쓴다. UTF-8 로 열지 않는다.
- `build/` 는 커밋하지 않는다(`build/inventory/` `build/probe-*/` `build/verify/` `build/cache-orig/`).
- **공개 저장소다.** 문서에는 섹션·키·열 **이름**과 직접 쓴 설명만 넣는다. 게임 데이터 값은 예시 한두 개까지만. 위키 문장은 옮겨 적지 않고 우리말로 요약해 링크한다.
- 표기: **[확인]** 파일·실행 파일·게임 안에서 직접 확인 / **[추정]** 정황으로 판단 / **[위키]** 공식 위키에 있으나 이 빌드에서 미확인. 게임에서 확인하지 않은 동작을 "된다"고 쓰지 않는다.
- Git: `develop` 에서 분기 → `develop` 으로 PR → merge commit. `main` · `develop` 에 직접 커밋·푸시하지 않는다. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- 게임 실행: `uv run python scripts/gamedrive.py start` 를 백그라운드로. 메인 메뉴는 20초쯤 뒤에 그려진다. **사용자가 직접 켠 게임이 떠 있으면**(`status` 가 "이 도구가 띄운 것 아님") 건드리지 않고 기다린다. 게임을 저장하지 않는다.
- 게임 안 검증을 백그라운드 에이전트에 맡긴 동안에는 작업 브랜치를 바꾸지 않는다.
- **`cheat resettutorial` 은 어떤 경우에도 입력하지 않는다**(Steam 업적을 지운다 [위키]).
- 서브에이전트에 맡길 때는 지시문에 다음을 그대로 넣는다: "이 작업(Task N)만 수행하라." / "끝나면 보고하고 정지하라. 다른 Task로 진행하지 말라." / "명세에 없는 코드를 추측·즉흥(improvise) 구현하지 말라. 명세가 부족하면 멈추고 `NEEDS_CONTEXT`로 보고하라." / "모든 git/파일 명령에 절대경로 또는 `-C E:/SR2030ToyBox` 를 사용하라. `cd` 후 상대경로로 후속 명령을 내지 말 것." 결과는 그대로 믿지 않고 컨트롤러가 직접 확인한다.

## Review Focus

명세가 암시하지만 놓치기 쉬운 입력·상황이다. 각 줄은 담당 Task 의 테스트나 확인 단계로 못박혀 있다.

1. **게임 패치로 섹션의 줄 모양이 섞이거나 바뀐다** → 키 섹션 판정이 틀려도 조용히 넘어가면 안 된다. 절반만 이름으로 시작하는 섹션은 표로 남아 열이 나오고, 판정은 `sections.csv` 의 `kind` 에 드러난다 — Task 2 `test_mostly_lowercase_names_still_make_a_keyed_section`.
2. **따옴표가 안 맞는 줄, 행이 없는 섹션, 끝에 NUL 이 붙은 텍스트 파일** → 죽지 않고 읽는다(실제로 `*.OOF` 끝에 NUL, `BUILDSEQUENCE` 는 행 0개) — Task 1 `test_fields_split_on_commas_outside_strings`, Task 2 `test_empty_section_is_listed_with_zero_rows` `test_scan_walks_game_folders_and_skips_binary_files`.
3. **시험 모드를 만들 때 기준 블록에 그 값이 없다** → 다음 블록의 같은 값을 바꾸면 엉뚱한 지역으로 실험하게 된다. 거부하고 파일을 만들지 않는다 — Task 9 `test_anchor_must_be_unique_and_close`.
4. **캐시를 다시 만들면 게임이 `Cache\*.SAV` 를 고쳐 쓴다** → `undeploy` 로는 돌아오지 않는다. 실험 전 해시를 적고 실험 뒤 비교해, 달라졌으면 `cache-orig` 로 되돌린다 — Task 13 Step 2 · Step 9.
5. **시험 모드가 한글화 모드와 같은 파일을 건드린다 / 게임이 떠 있는 채로 설치한다** → 설치 미리보기의 줄 수로 확인하고(한 줄이어야 한다), 실행 중 설치는 `deploy` 가 거부한다 — Task 13 · 14 · 15 의 미리보기 단계.

---

## 파일 구조

| 파일 | 하는 일 | Task |
|---|---|---|
| `src/srkit/srtext.py` (수정) | `section_name()` 을 `parse()` 에서 꺼내 공개 | 1 |
| `src/srkit/inventory.py` (신규) | 줄 읽기 → 스캔 → 실행 파일 대조 → CSV 쓰기 | 1 ~ 4 |
| `src/srkit/probe.py` (신규) | 값 한 곳만 바꾼 시험 모드 만들기 | 9 |
| `src/srkit/cli.py` (수정) | `inventory` `probe` 명령 등록 | 4, 9 |
| `tests/test_srtext.py` (수정) · `tests/test_inventory.py` · `tests/test_probe.py` (신규) | 자동 테스트 | 1 ~ 4, 9 |
| `scripts/gamedrive.py` · `tests/test_gamedrive.py` (조건부 수정) | `key` 의 조합키 | 11 |
| `docs/05-game-systems.md` | ① 12개 영역 | 6 |
| `docs/06-data-reference.md` | ③ 섹션·키·열 참조 | 5, 16 |
| `docs/07-cheats.md` | 내장 치트표 | 7, 16 |
| `docs/08-workshop-survey.md` | ⑤ Workshop 전수 조사 | 8 |
| `docs/09-cheat-mod-plan.md` | ② ④ 분류표와 제작 계획 | 17 |
| `docs/01-game-structure.md` · `README.md` (수정) | 확인된 [추정] 갱신, 구조 목록 | 4, 9, 16, 17 |

브랜치와 Task: `docs/cheat-mod-spec`(0) → `feat/inventory`(1 ~ 4) → `docs/cheat-mod-research`(5 ~ 8) → `feat/probe`(9) → (조건부) `feat/gamedrive-combo-keys`(11) → `docs/cheat-mod-verify`(16 ~ 17). Task 10 · 12 ~ 15 는 게임 안 작업이라 코드 변경이 없다(산출물은 `build/verify/`).

---

### Task 0: 설계 문서와 이 계획을 `develop` 에 올린다

**Files:**
- 이미 커밋됨: `docs/superpowers/specs/2026-10-06-cheat-mod-research-design.md`, `docs/superpowers/plans/2026-10-06-cheat-mod-research.md` (브랜치 `docs/cheat-mod-spec`)

- [ ] **Step 1: 테스트 통과 확인**

Run: `uv run pytest -q`
Expected: `54 passed`

- [ ] **Step 2: 푸시하고 PR 을 연다**

```bash
git -C E:/SR2030ToyBox push -u origin docs/cheat-mod-spec
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/cheat-mod-spec \
  --title "docs: 치트·모드 조사 설계와 구현 계획" \
  --body "$(cat <<'EOF'
치트·모드 조사(게임 구조, 데이터 파일, 내장 치트, Workshop)의 설계 문서와 구현 계획.
문서만 바뀐다. 코드 변경 없음.

- `uv run pytest`: 54 passed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: 머지하고 `develop` 을 맞춘다**

```bash
gh pr merge --repo game-mod-project/SR2030Toybox docs/cheat-mod-spec --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

---

## Phase 1 — `srkit inventory` (브랜치 `feat/inventory`)

시작: `git -C E:/SR2030ToyBox switch -c feat/inventory develop`

### Task 1: 줄 읽기 함수

**Files:**
- Modify: `src/srkit/srtext.py:79-88` (`parse` 의 섹션 머리 판별을 함수로 꺼낸다)
- Create: `src/srkit/inventory.py`
- Test: `tests/test_srtext.py`, `tests/test_inventory.py` (신규)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `srtext.section_name(head: str) -> str | None` — `&&이름` 줄이면 대문자 이름(`&&END` 는 `"END"`), 아니면 `None`
  - `inventory.strip_comment(line: str) -> str`
  - `inventory.fields_of(line: str) -> list[str]`
  - `inventory.key_value(line: str) -> tuple[str, str] | None`
  - `inventory.header_names(comments: list[str]) -> list[str]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_srtext.py` 의 `test_roundtrip_is_lossless` 바로 위에 추가:

```python
def test_section_name_reads_every_head_shape():
    assert srtext.section_name("&&CVP 599") == "CVP"
    assert srtext.section_name("&&GROUPING\t\t0") == "GROUPING"
    assert srtext.section_name("&&WMDATA, 0") == "WMDATA"
    assert srtext.section_name("&&HOTKEYS,,,,,,//,&&HOTKEYSTEXT,,,") == "HOTKEYS"
    assert srtext.section_name("&&cvp 1") == "CVP"
    assert srtext.section_name("&&END") == "END"
    assert srtext.section_name("// &&CVP 1") is None
    assert srtext.section_name("502,") is None
```

`tests/test_inventory.py` 를 새로 만든다:

```python
from srkit import inventory


def test_strip_comment_keeps_slashes_inside_strings():
    assert inventory.strip_comment('1, "see http://x//y" // tail') == '1, "see http://x//y" '
    assert inventory.strip_comment('1,0,"//Grid","x"') == '1,0,"//Grid","x"'
    assert inventory.strip_comment("0, 1.000 //Resource, Minister") == "0, 1.000 "


def test_fields_split_on_commas_outside_strings():
    assert inventory.fields_of('21535, "City, capital", 21, , 586,') == ["21535", "City, capital", "21", "", "586", ""]
    assert inventory.fields_of("0, 1.000 //Resource, Minister") == ["0", "1.000"]
    assert inventory.fields_of("502,") == ["502", ""]
    assert inventory.fields_of('1, "unterminated, 2') == ["1", "unterminated, 2"]     # 따옴표가 안 맞아도 죽지 않는다


def test_key_value_accepts_space_colon_and_comma():
    assert inventory.key_value('regionname\t"Great Britain"') == ("regionname", '"Great Britain"')
    assert inventory.key_value("influence 1,2,3,6") == ("influence", "1,2,3,6")
    assert inventory.key_value("startymd:       2023, 8, 7") == ("startymd", "2023, 8, 7")
    assert inventory.key_value("scenarioid:     ") == ("scenarioid", "")
    assert inventory.key_value("aiforcesize, 2, 4, 8") == ("aiforcesize", "2, 4, 8")
    assert inventory.key_value("techlevel 70   // note") == ("techlevel", "70")
    assert inventory.key_value('21535, "City", 21') is None
    assert inventory.key_value("0x0D,0,0,1950") is None
    assert inventory.key_value(', , "text"') is None


def test_header_is_the_comment_with_the_most_names():
    comments = ["// Equipment data", "// Created by the Asset Manager on 12/18/2025 08:05:47",
                "// SR5ID, ModelCode+EquipName, ClassNum, // Notes"]
    assert inventory.header_names(comments) == ["SR5ID", "ModelCode+EquipName", "ClassNum", "Notes"]
    assert inventory.header_names(["// OUTPUT - 7", "// 660 Rows"]) == []
    assert inventory.header_names(["// Training Items Export,,,,", "// These are Espionage missions,,,,"]) == []
    assert inventory.header_names([]) == []
```

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_srtext.py tests/test_inventory.py -q`
Expected: `test_inventory.py` 는 수집 단계에서 `ImportError: cannot import name 'inventory' from 'srkit'`, `test_section_name_reads_every_head_shape` 는 `AttributeError: module 'srkit.srtext' has no attribute 'section_name'`

- [ ] **Step 3: 구현한다**

`src/srkit/srtext.py` — `def parse` 위에 함수를 더하고 `parse` 의 앞부분을 바꾼다:

```python
def section_name(head: str) -> str | None:
    """``&&이름`` 으로 시작하는 줄이면 섹션 이름(대문자)을, 아니면 None 을 돌려준다. 종료 표시는 "END" 다."""
    if not head.startswith("&&"):
        return None
    return re.split(r"[,\s]", head[2:], maxsplit=1)[0].upper()


def parse(text: str) -> Document:
    doc = Document()
    section: str | None = None
    for raw in text.split("\n"):
        parts = raw.split('"')
        head = parts[0].strip()
        line = Line(parts)
        name = section_name(head)
        if name is not None:
            section = None if name == "END" else name
        elif section and not head.startswith(("//", "#")) and len(parts) >= 3 and len(parts) % 2 == 1:
```

(`elif` 줄부터 아래는 그대로 둔다.)

`src/srkit/inventory.py` 를 새로 만든다:

```python
"""게임 텍스트 데이터의 섹션·키·열 목록을 뽑는다(읽기 전용). 산출물은 build/inventory/ 의 CSV 다.

데이터 줄은 두 가지로 읽는다: 이름으로 시작하는 줄(``키 값`` · ``키: 값`` · ``키, 값, …``)과 쉼표 행.
섹션이 "키 섹션"인지 "표"인지는 데이터로 정한다 — 행의 90% 이상이 소문자로 시작하는 이름으로 시작하면 키 섹션이다
(빌드 21347933 에서 CVP · GMC · MAP · SAV · WMDATA · WMPRODDATA · UISETTINGS · AIPARAMS).
"""
from __future__ import annotations

import re

KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::|,|\s|$)")


def strip_comment(line: str) -> str:
    """큰따옴표 밖의 ``//`` 부터 줄 끝까지를 버린다."""
    parts = line.split('"')
    for i in range(0, len(parts), 2):
        cut = parts[i].find("//")
        if cut >= 0:
            return '"'.join(parts[:i] + [parts[i][:cut]])
    return line


def fields_of(line: str) -> list[str]:
    """쉼표로 나눈 필드(앞뒤 공백 제거). 큰따옴표 안의 쉼표는 나누지 않고, 따옴표 밖의 주석은 버린다."""
    out, cur = [], ""
    for i, part in enumerate(strip_comment(line).split('"')):
        if i % 2:
            cur += part
            continue
        pieces = part.split(",")
        cur += pieces[0]
        for piece in pieces[1:]:
            out.append(cur.strip())
            cur = piece
    out.append(cur.strip())
    return out


def key_value(line: str) -> tuple[str, str] | None:
    """이름으로 시작하는 줄이면 (키, 값)을 돌려준다. 구분은 공백 · ``:`` · ``,`` 어느 것이든 된다."""
    body = strip_comment(line).strip()
    m = KEY_RE.match(body)
    if not m:
        return None
    return m.group(1), body[m.end(1):].lstrip(":, \t").strip()


def header_names(comments: list[str]) -> list[str]:
    """섹션 머리 바로 위 주석들 가운데 열 이름 줄을 고른다: 쉼표로 나눈 이름이 가장 많은 줄(둘 이상일 때만)."""
    best: list[str] = []
    for comment in comments:
        names = [n.strip().lstrip("/").strip() for n in comment.lstrip("/").split(",")]
        if sum(map(bool, names)) > sum(map(bool, best)):
            best = names
    return best if sum(map(bool, best)) >= 2 else []
```

- [ ] **Step 4: 통과를 확인한다**

Run: `uv run pytest -q`
Expected: `59 passed` (기존 54 + 새 5). `test_game_files_roundtrip` 이 그대로 통과해야 한다 — `parse` 의 동작이 바뀌지 않았다는 증거다.

- [ ] **Step 5: 커밋**

```bash
git -C E:/SR2030ToyBox add src/srkit/srtext.py src/srkit/inventory.py tests/test_srtext.py tests/test_inventory.py
git -C E:/SR2030ToyBox commit -m "feat: 게임 데이터 줄 읽기 — 섹션 머리, 키-값, 쉼표 행, 열 이름 주석

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: 스캔 — 키 섹션과 표

**Files:**
- Modify: `src/srkit/inventory.py`
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: `srtext.section_name`, `inventory.fields_of`, `inventory.key_value`, `inventory.header_names` (Task 1), `korean.decode_cp1252(data: bytes) -> str`
- Produces:
  - `inventory.Table` — `names: list[str]`, `filled: Counter` (열 번호 → 값이 있는 행 수), `example: dict[int, str]`, `width: int`
  - `inventory.Section` — `blocks: Counter` · `rows: Counter` (파일 → 수), `lower_first: int`, `keys: Counter`, `key_files: dict[str, set[str]]`, `key_example: dict[str, str]`, `tables: dict[str, Table]`, 속성 `keyed: bool`
  - `inventory.Inventory` — `sections: dict[str, Section]`, `skipped: list[tuple[str, str]]`
  - `inventory.scan_text(rel: str, text: str, sections: dict[str, Section]) -> None`
  - `inventory.is_binary(data: bytes) -> bool`
  - `inventory.scan(game_dir: Path) -> Inventory`
  - 상수 `SCAN_DIRS`, `KEYED_SHARE = 0.9`, `EXAMPLE_MAX = 60`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_inventory.py` — `from srkit import inventory` 아래에 자료를 넣고, 파일 끝에 테스트를 더한다:

```python
# 지역 블록(키 값), 시나리오 설정(키: 값), 이름 붙은 행(키, 값, …) — 셋 다 키 섹션이다
KEYED = (
    "// CVP data\n"
    "&&CVP 599\n"
    'regionname\t"Palestine"\n'
    "gdpc 3660\n"
    "influence 1,2,3,6\n"
    "techlevel 70   // note\n"
    "\n"
    "&&GROUPING 599\n"
    "502,\n"
    "504,\n"
    "\n"
    "&&CVP 1499\n"
    'regionname "Germany"\n'
    "gdpc 51203\n"
    "treasury 100\n"
    "techlevel 110\n"
    "&&GMC\n"
    "startymd:       2023, 8, 7\n"
    "scenarioid:     \n"
    "initialfunds:   2\n"
    "&&END\n"
    "&&WMDATA, 0\n"
    "aiplayrich, 75000000.000\n"
    "socadj, 1.000, 2.000\n"
)

TABLES = (
    "// Equipment data\n"
    "// Created by the Asset Manager on 12/18/2025 08:05:47\n"
    "// SR5ID, ModelCode+EquipName, ClassNum, DaysToBuild, Cost, // Notes\n"
    "&&UNITS\n"
    '21535, "City, capital", 21, , 586, // not a column\n'
    '10091, "Mk V Tempest", 10, 4.5, 2.3,\n'
    "&&END\n"
    "// OUTPUT - 7\n"
    "// 660 Rows\n"
    "&&CABPRIORITIES, 0\n"
    "0, 1.000, 1.000 //Resource Minister, Military Materials\n"
    "&&NAMESET 0\n"
    "Malisheve\n"
    "Zubin Potok\n"
    "al-Hasakah\n"
    "&&BUILDSEQUENCE\n"
)
```

```python
def scan(text: str, rel: str = "Maps/X.CVP") -> dict[str, inventory.Section]:
    sections: dict[str, inventory.Section] = {}
    inventory.scan_text(rel, text, sections)
    return sections


def test_keyed_sections_yield_keys():
    s = scan(KEYED)
    assert s["CVP"].keyed and s["GMC"].keyed and s["WMDATA"].keyed
    assert not s["GROUPING"].keyed
    assert list(s["CVP"].keys) == ["regionname", "gdpc", "influence", "techlevel", "treasury"]
    assert s["CVP"].keys["gdpc"] == 2 and s["CVP"].keys["treasury"] == 1
    assert s["CVP"].key_example["regionname"] == '"Palestine"'      # 처음 나온 값이 예시
    assert s["CVP"].blocks["Maps/X.CVP"] == 2 and s["CVP"].rows["Maps/X.CVP"] == 8
    assert list(s["GMC"].keys) == ["startymd", "scenarioid", "initialfunds"]
    assert "scenarioid" not in s["GMC"].key_example                # 값이 빈 키는 예시가 없다
    assert s["WMDATA"].key_example["socadj"] == "1.000, 2.000"


def test_mostly_lowercase_names_still_make_a_keyed_section():
    text = "&&CVP 1\n" + "".join(f"key{i} {i}\n" for i in range(9)) + "RacePrimary 4\n"
    assert scan(text)["CVP"].keyed                                  # 9/10: 대문자로 시작하는 키가 섞여도 된다
    assert "RacePrimary" in scan(text)["CVP"].keys
    half = "&&MIX\n" + "alpha 1\n" * 5 + "1, 2, 3\n" * 5
    assert not scan(half)["MIX"].keyed                              # 절반만 이름이면 표로 남아 열이 나온다
    assert scan(half)["MIX"].tables["Maps/X.CVP"].width == 3


def test_tables_yield_columns_with_names_from_the_header_comment():
    s = scan(TABLES, "Maps/DATA/DEFAULT.UNIT")
    units = s["UNITS"].tables["Maps/DATA/DEFAULT.UNIT"]
    assert not s["UNITS"].keyed
    assert units.names == ["SR5ID", "ModelCode+EquipName", "ClassNum", "DaysToBuild", "Cost", "Notes"]
    assert units.width == 6
    assert units.filled == {0: 2, 1: 2, 2: 2, 3: 1, 4: 2}           # 빈 칸은 세지 않는다
    assert units.example[1] == "City, capital" and units.example[3] == "4.5"
    cab = s["CABPRIORITIES"].tables["Maps/DATA/DEFAULT.UNIT"]
    assert cab.names == [] and cab.width == 3                       # 열 이름 주석이 없으면 번호만


def test_place_names_do_not_become_keys():
    s = scan(TABLES)
    assert not s["NAMESET"].keyed
    assert s["NAMESET"].rows["Maps/X.CVP"] == 3


def test_empty_section_is_listed_with_zero_rows():
    s = scan(TABLES)
    assert s["BUILDSEQUENCE"].blocks["Maps/X.CVP"] == 1
    assert s["BUILDSEQUENCE"].rows["Maps/X.CVP"] == 0 and not s["BUILDSEQUENCE"].keyed


def test_directives_and_lines_outside_sections_are_not_rows():
    text = ('#ifset 0x02\n#include "DEFAULT.UNIT", "MAPS\\DATA\\"\n#endifset\nstray, 1\n'
            '&&MAP\n#include "x.csv", "MAPS\\"\nmapfile "World2030"\n&&END\nafter, end\n')
    s = scan(text, "Sandbox/W.scenario")
    assert list(s) == ["MAP"]
    assert s["MAP"].rows["Sandbox/W.scenario"] == 1 and list(s["MAP"].keys) == ["mapfile"]


def test_each_file_keeps_its_own_column_names():
    sections: dict[str, inventory.Section] = {}
    inventory.scan_text("a.UNIT", "// Id, Name\n&&UNITS\n1, x\n", sections)
    inventory.scan_text("b.UNIT", "// Id, Name, Extra\n&&UNITS\n1, x, y\n", sections)
    assert sections["UNITS"].tables["a.UNIT"].names == ["Id", "Name"]
    assert sections["UNITS"].tables["b.UNIT"].names == ["Id", "Name", "Extra"]


def fake_game(root, exe: bytes = b""):
    (root / "INI").mkdir(parents=True)
    (root / "Maps" / "DATA").mkdir(parents=True)
    (root / "Localize").mkdir()
    (root / "INI" / "scen.scenario").write_bytes(KEYED.replace("\n", "\r\n").encode("cp1252"))
    (root / "Maps" / "DATA" / "DEFAULT.UNIT").write_bytes(TABLES.encode("cp1252"))
    (root / "Maps" / "World.OOF").write_bytes(b'&&OOF\t0, \r\n21003, 958, 107, "Caf\xe9"\r\n\0')   # 끝에 NUL 하나
    (root / "Maps" / "World.MAPX").write_bytes(b"`\x01\0\0\x08\x03\0\0binary")
    (root / "Localize" / "skip.csv").write_bytes(b"&&GUITRANS\n")                              # 훑는 폴더가 아니다
    (root / "SupremeRuler2030.exe").write_bytes(exe)
    return root


def test_scan_walks_game_folders_and_skips_binary_files(tmp_path):
    inv = inventory.scan(fake_game(tmp_path))
    assert inv.skipped == [("Maps/World.MAPX", "이진")]
    assert "OOF" in inv.sections and "GUITRANS" not in inv.sections     # 끝의 NUL 하나는 이진이 아니다
    assert inv.sections["OOF"].tables["Maps/World.OOF"].example[3] == "Café"
    assert inv.sections["CVP"].rows["INI/scen.scenario"] == 8           # CRLF 파일도 같게 읽는다
```

자료(`KEYED`, `TABLES`)에는 ASCII 만 쓴다 — `fake_game` 이 CP1252 로 인코딩하므로 한글 주석을 넣으면 `UnicodeEncodeError` 가 난다.

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_inventory.py -q`
Expected: 수집 단계에서 `AttributeError: module 'srkit.inventory' has no attribute 'Section'` (도우미 `scan` 의 반환 형 표기가 먼저 걸린다)

- [ ] **Step 3: 구현한다**

`src/srkit/inventory.py` — import 와 상수를 다음으로 바꾼다:

```python
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import srtext
from .korean import decode_cp1252

SCAN_DIRS = ("INI", "Maps", "Sandbox", "Scenario", "Campaign", "Tutorials", "Common")
KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::|,|\s|$)")
KEYED_SHARE = 0.9       # 행의 이만큼이 소문자 이름으로 시작하면 키 섹션으로 본다
EXAMPLE_MAX = 60
```

`header_names` 아래에 더한다:

```python
@dataclass
class Table:
    """한 파일 안의 한 섹션을 표로 읽은 결과."""
    names: list[str] = field(default_factory=list)
    filled: Counter = field(default_factory=Counter)        # 열 번호 → 값이 있는 행 수
    example: dict[int, str] = field(default_factory=dict)
    width: int = 0


@dataclass
class Section:
    blocks: Counter = field(default_factory=Counter)        # 파일 → 블록 수
    rows: Counter = field(default_factory=Counter)          # 파일 → 행 수
    lower_first: int = 0                                    # 소문자 이름으로 시작하는 행 수
    keys: Counter = field(default_factory=Counter)          # 키 → 등장 횟수 (처음 나온 순서)
    key_files: dict[str, set[str]] = field(default_factory=dict)
    key_example: dict[str, str] = field(default_factory=dict)
    tables: dict[str, Table] = field(default_factory=dict)  # 파일 → 표

    @property
    def keyed(self) -> bool:
        total = sum(self.rows.values())
        return total > 0 and self.lower_first / total >= KEYED_SHARE


@dataclass
class Inventory:
    sections: dict[str, Section] = field(default_factory=dict)
    skipped: list[tuple[str, str]] = field(default_factory=list)   # (파일, 이유)


def scan_text(rel: str, text: str, sections: dict[str, Section]) -> None:
    current: Section | None = None
    table = Table()
    comments: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//"):
            comments.append(line)
            continue
        name = srtext.section_name(line)
        if name is not None:
            current = None if name == "END" else sections.setdefault(name, Section())
            if current is not None:
                current.blocks[rel] += 1
                table = current.tables.setdefault(rel, Table())
                if not table.names:
                    table.names = header_names(comments)
            comments = []
            continue
        comments = []
        if current is None or line.startswith("#"):     # 섹션 밖의 줄, #include · #ifset 지시문
            continue
        current.rows[rel] += 1
        kv = key_value(line)
        if kv:
            key, value = kv
            current.lower_first += key[0].islower()
            current.keys[key] += 1
            current.key_files.setdefault(key, set()).add(rel)
            if value:
                current.key_example.setdefault(key, value[:EXAMPLE_MAX])
        fields = fields_of(line)
        table.width = max(table.width, len(fields))
        for i, value in enumerate(fields):
            if value:
                table.filled[i] += 1
                table.example.setdefault(i, value[:EXAMPLE_MAX])


def is_binary(data: bytes) -> bool:
    """끝에 붙은 NUL(*.OOF 에 하나 있다)은 떼고, 그 밖에 NUL 이 있으면 이진 파일로 본다."""
    return b"\0" in data.rstrip(b"\0")


def scan(game_dir: Path) -> Inventory:
    inv = Inventory()
    for top in SCAN_DIRS:
        for path in sorted((game_dir / top).rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(game_dir).as_posix()
            try:
                data = path.read_bytes()
            except OSError as e:
                inv.skipped.append((rel, f"읽지 못함: {e.strerror}"))
                continue
            if is_binary(data):
                inv.skipped.append((rel, "이진"))
                continue
            scan_text(rel, decode_cp1252(data.rstrip(b"\0")), inv.sections)
    return inv
```

모든 행을 키와 열 양쪽으로 다 세어 두고, 어느 쪽을 내보낼지는 섹션 전체를 본 뒤(`keyed`) 정한다. 그래서 스캔은 한 번만 돈다.

- [ ] **Step 4: 통과를 확인한다**

Run: `uv run pytest -q`
Expected: `67 passed`

- [ ] **Step 5: 커밋**

```bash
git -C E:/SR2030ToyBox add src/srkit/inventory.py tests/test_inventory.py
git -C E:/SR2030ToyBox commit -m "feat: 게임 데이터 스캔 — 키 섹션과 표를 데이터로 구분

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: 실행 파일 대조

**Files:**
- Modify: `src/srkit/inventory.py`
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: 없음(바이트와 이름 집합만 받는다)
- Produces:
  - `inventory.Candidate(string: str, near: str, distance: int, colon: bool)` — frozen dataclass
  - `inventory.exe_candidates(data: bytes, known: set[str]) -> list[Candidate]` — 처음 나온 순서, 같은 이름은 한 번만
  - 상수 `STRING_RE`, `WORD_RE`, `RUN_GAP = 16`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_inventory.py` 끝에 추가:

```python
def test_exe_candidates_come_from_tables_that_hold_known_names():
    table = b"\0".join([b"startymd:", b"hiddenkey:", b"initialfunds:", b"otherkey"])
    lonely = b"\0" * 64 + b"lonely\0"
    sentence = b"Some sentence here.\0"
    unrelated = b"\0" * 64 + b"\0".join([b"alpha", b"beta", b"gamma"])
    found = inventory.exe_candidates(lonely + sentence + table + unrelated, {"startymd", "initialfunds"})
    assert found == [inventory.Candidate("hiddenkey", "startymd", 1, True),
                     inventory.Candidate("otherkey", "initialfunds", 1, False)]


def test_exe_candidates_need_two_known_names_and_a_tight_table():
    one_known = b"\0".join([b"startymd:", b"hiddenkey:"])
    spread = b"startymd:" + b"\0" * 40 + b"hiddenkey:" + b"\0" * 40 + b"initialfunds:"
    assert inventory.exe_candidates(one_known, {"startymd", "initialfunds"}) == []
    assert inventory.exe_candidates(spread, {"startymd", "initialfunds"}) == []
    assert inventory.exe_candidates(b"", {"startymd"}) == []
```

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_inventory.py -q -k exe_candidates`
Expected: 2 failed — `AttributeError: module 'srkit.inventory' has no attribute 'exe_candidates'`

- [ ] **Step 3: 구현한다**

`src/srkit/inventory.py` — 상수 아래(`EXAMPLE_MAX` 다음)에 더한다:

```python
STRING_RE = re.compile(rb"[\x20-\x7e]{3,}")
WORD_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{2,31}:?\Z")
RUN_GAP = 16            # 실행 파일에서 문자열 사이가 이보다 벌어지면 다른 표로 본다
```

`Inventory` 클래스 아래에 더한다:

```python
@dataclass(frozen=True)
class Candidate:
    string: str
    near: str        # 같은 표에서 가장 가까운 알려진 이름
    distance: int    # 그 이름과 몇 칸 떨어져 있는가
    colon: bool      # 실행 파일에 "이름:" 꼴로 들어 있는가 (GMC 형식 키의 표지)
```

`scan` 아래에 더한다:

```python
def exe_candidates(data: bytes, known: set[str]) -> list[Candidate]:
    """실행 파일의 이름 표에서, 알려진 이름과 같은 표에 있으면서 어느 파일에도 쓰이지 않은 이름을 찾는다.

    컴파일러는 한 소스의 문자열 상수를 이어서 놓는다. 이름 꼴 문자열이 붙어 있는 구간을 표 하나로 보고,
    알려진 이름(파일에 쓰인 키·섹션)이 둘 이상 든 표의 나머지를 후보로 낸다. 같은 표에 GUI·글꼴 키도
    섞여 있으므로 후보는 추정일 뿐이다 — distance 가 작고 colon 이 맞는 것부터 본다.
    """
    runs: list[list[str]] = []
    run: list[str] = []
    prev_end = -RUN_GAP - 1
    for m in STRING_RE.finditer(data):
        if WORD_RE.match(m.group()):
            if run and m.start() - prev_end > RUN_GAP:
                runs.append(run)
                run = []
            run.append(m.group().decode("ascii"))
        elif run:
            runs.append(run)
            run = []
        prev_end = m.end()
    if run:
        runs.append(run)
    found: dict[str, Candidate] = {}
    for run in runs:
        names = [s.rstrip(":") for s in run]
        hits = [i for i, name in enumerate(names) if name in known]
        if len(hits) < 2:
            continue
        for i, name in enumerate(names):
            if name in known or name in found:
                continue
            j = min(hits, key=lambda h: abs(h - i))
            found[name] = Candidate(name, names[j], abs(j - i), run[i].endswith(":"))
    return list(found.values())
```

- [ ] **Step 4: 통과를 확인한다**

Run: `uv run pytest -q`
Expected: `69 passed`

- [ ] **Step 5: 커밋**

```bash
git -C E:/SR2030ToyBox add src/srkit/inventory.py tests/test_inventory.py
git -C E:/SR2030ToyBox commit -m "feat: 실행 파일의 이름 표에서 파일에 안 쓰인 키 후보 찾기

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: CSV 쓰기, `srkit inventory` 명령, PR

**Files:**
- Modify: `src/srkit/inventory.py`, `src/srkit/cli.py:9` · `:151` · `:206`, `README.md`
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: `inventory.scan`, `inventory.exe_candidates`, `inventory.Inventory`, `inventory.Candidate` (Task 2 · 3), `deploy.GAME_EXE`, `config.Config`
- Produces:
  - `inventory.write(inv: Inventory, candidates: list[Candidate], out_dir: Path) -> list[Path]`
  - `inventory.run(cfg: Config) -> dict` — 키 `out` `sections` `keyed` `keys` `candidates` `skipped`. 게임 폴더가 아니면 `RuntimeError("게임 폴더가 아닙니다(…)")`
  - 명령 `uv run srkit inventory`
  - 파일 `build/inventory/{sections,keys,columns,exe-candidates,skipped}.csv` — UTF-8 BOM + LF. 머리 행:
    `file,section,kind,blocks,rows` / `section,key,files,count,example` / `file,section,index,name,filled,example` / `string,near,distance,colon` / `file,reason`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_inventory.py` 맨 위의 import 를 다음으로 바꾼다:

```python
import csv
from dataclasses import replace

import pytest

from srkit import inventory
```

파일 끝에 추가:

```python
def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_run_writes_five_tables(cfg, tmp_path):
    exe = b"\0".join([b"startymd:", b"hiddenkey:", b"initialfunds:"])
    fake = replace(cfg, root=tmp_path / "proj", game_dir=fake_game(tmp_path / "game", exe))
    result = inventory.run(fake)
    out = fake.build_dir / "inventory"
    assert result["out"] == out and result["skipped"] == 1 and result["candidates"] == 1
    assert sorted(p.name for p in out.iterdir()) == ["columns.csv", "exe-candidates.csv", "keys.csv", "sections.csv",
                                                     "skipped.csv"]
    kinds = {r["section"]: r["kind"] for r in read(out / "sections.csv")}
    assert kinds["CVP"] == "keyed" and kinds["UNITS"] == "table" and kinds["BUILDSEQUENCE"] == "table"
    assert {"section": "CVP", "key": "gdpc", "files": "1", "count": "2", "example": "3660"} in read(out / "keys.csv")
    cost = [r for r in read(out / "columns.csv") if r["section"] == "UNITS" and r["name"] == "Cost"]
    assert cost == [{"file": "Maps/DATA/DEFAULT.UNIT", "section": "UNITS", "index": "4", "name": "Cost", "filled": "2",
                     "example": "586"}]
    assert read(out / "exe-candidates.csv") == [{"string": "hiddenkey", "near": "startymd", "distance": "1", "colon": "1"}]
    assert read(out / "skipped.csv") == [{"file": "Maps/World.MAPX", "reason": "이진"}]
    assert b"\r\n" not in (out / "keys.csv").read_bytes()               # 번역 테이블과 같은 형식: BOM + LF
    inventory.run(fake)                                                 # 다시 돌려도 같은 다섯 파일
    assert len(list(out.iterdir())) == 5


def test_run_refuses_a_folder_without_the_game(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path, game_dir=tmp_path / "nowhere")
    with pytest.raises(RuntimeError, match="게임 폴더가 아닙니다"):
        inventory.run(fake)
    assert not (fake.build_dir / "inventory").exists()


def test_real_game_inventory(game_dir, cfg, tmp_path):
    """설치본에서: 키 섹션과 표가 맞게 갈리고, 치트 조사에 쓸 키·열이 실제로 나온다."""
    fake = replace(cfg, root=tmp_path)
    result = inventory.run(fake)
    out = fake.build_dir / "inventory"
    kinds = {r["section"]: r["kind"] for r in read(out / "sections.csv")}
    assert {name for name, kind in kinds.items() if kind == "keyed"} >= {"CVP", "GMC", "WMDATA", "WMPRODDATA", "AIPARAMS"}
    for name in ("UNITS", "TTR", "TERRAIN", "NAMESET", "OOB", "OOF", "SEVENTS"):
        assert kinds[name] == "table", name
    keys = {(r["section"], r["key"]) for r in read(out / "keys.csv")}
    assert {("CVP", "treasury"), ("CVP", "gdpc"), ("GMC", "initialfunds"), ("GMC", "fastbuild")} <= keys
    unit_columns = {r["name"] for r in read(out / "columns.csv") if r["file"] == "Maps/DATA/DEFAULT.UNIT"}
    assert {"DaysToBuild", "Cost", "SoftAttack", "GroundDefense"} <= unit_columns
    assert result["sections"] >= 50 and result["candidates"] > 0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_inventory.py -q -k "run or real_game"`
Expected: 3 failed — `AttributeError: module 'srkit.inventory' has no attribute 'run'`

- [ ] **Step 3: 구현한다**

`src/srkit/inventory.py` — import 를 다음으로 바꾼다:

```python
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import srtext
from .config import Config
from .deploy import GAME_EXE
from .korean import decode_cp1252
```

파일 끝에 더한다:

```python
def write(inv: Inventory, candidates: list[Candidate], out_dir: Path) -> list[Path]:
    sections, keys, columns = [], [], []
    for name, sec in sorted(inv.sections.items()):
        kind = "keyed" if sec.keyed else "table"
        for rel in sorted(sec.blocks):
            sections.append((rel, name, kind, sec.blocks[rel], sec.rows[rel]))
        if sec.keyed:
            keys += [(name, key, len(sec.key_files[key]), count, sec.key_example.get(key, ""))
                     for key, count in sec.keys.items()]
            continue
        for rel, table in sorted(sec.tables.items()):
            columns += [(rel, name, i, table.names[i] if i < len(table.names) else "", table.filled[i],
                         table.example.get(i, "")) for i in range(table.width)]
    tables = {
        "sections.csv": (("file", "section", "kind", "blocks", "rows"), sections),
        "keys.csv": (("section", "key", "files", "count", "example"), keys),
        "columns.csv": (("file", "section", "index", "name", "filled", "example"), columns),
        "exe-candidates.csv": (("string", "near", "distance", "colon"),
                               [(c.string, c.near, c.distance, int(c.colon)) for c in candidates]),
        "skipped.csv": (("file", "reason"), inv.skipped),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, (header, rows) in tables.items():
        path = out_dir / filename
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
        paths.append(path)
    return paths


def run(cfg: Config) -> dict:
    exe = cfg.game_dir / GAME_EXE
    if not exe.is_file():
        raise RuntimeError(f"게임 폴더가 아닙니다({GAME_EXE} 없음): {cfg.game_dir}")
    inv = scan(cfg.game_dir)
    keyed = [sec for sec in inv.sections.values() if sec.keyed]
    known = set(inv.sections) | {"END"} | {key for sec in keyed for key in sec.keys}
    candidates = exe_candidates(exe.read_bytes(), known)
    out = cfg.build_dir / "inventory"
    write(inv, candidates, out)
    return {"out": out, "sections": len(inv.sections), "keyed": len(keyed),
            "keys": sum(len(sec.keys) for sec in keyed), "candidates": len(candidates), "skipped": len(inv.skipped)}
```

`src/srkit/cli.py` — 9행의 import 를 바꾼다:

```python
from . import config, deploy, hook, inventory, korean, mt
```

`def cmd_deploy` 위에 더한다:

```python
def cmd_inventory(cfg, _args) -> int:
    r = inventory.run(cfg)
    print(f"산출물         : {r['out']}")
    print(f"섹션           : {r['sections']}종 (키 섹션 {r['keyed']}, 표 {r['sections'] - r['keyed']})")
    print(f"키             : {r['keys']}개")
    print(f"실행 파일 후보 : {r['candidates']}개 (추정 — exe-candidates.csv)")
    print(f"건너뛴 파일    : {r['skipped']}개 (skipped.csv)")
    return 0
```

`main` 의 `for name, fn, text in (("deploy", cmd_deploy, …` 줄 바로 위에 더한다:

```python
    sub.add_parser("inventory", help="게임 데이터의 섹션·키·열 목록을 build/inventory 에 CSV 로").set_defaults(fn=cmd_inventory)
```

- [ ] **Step 4: 통과를 확인하고 설치본에서 돌려 본다**

Run: `uv run pytest -q`
Expected: `72 passed` (`test_real_game_inventory` 가 10초쯤 걸린다)

Run: `uv run srkit inventory`
Expected (빌드 21347933):

```
산출물         : E:\SR2030ToyBox\build\inventory
섹션           : 53종 (키 섹션 8, 표 45)
키             : 210개
실행 파일 후보 : 759개 (추정 — exe-candidates.csv)
건너뛴 파일    : 11개 (skipped.csv)
```

Run: `git -C E:/SR2030ToyBox status --short`
Expected: `build/` 아래 파일은 나오지 않는다(git 제외).

- [ ] **Step 5: README 에 명령과 모듈을 적는다**

`README.md` 의 "빠른 시작" 코드 블록에서 `uv run srkit tcheck-import …` 줄 아래에 한 줄을 더한다:

```
uv run srkit inventory               # 게임 데이터의 섹션·키·열 목록 → build/inventory/*.csv (치트·모드 조사용)
```

"구조" 코드 블록에서 `deploy.py      게임 폴더 설치·제거` 줄 아래에 한 줄을 더한다:

```
  inventory.py   게임 데이터의 섹션·키·열 목록 (읽기 전용)
```

- [ ] **Step 6: 커밋, 푸시, PR, 머지**

```bash
git -C E:/SR2030ToyBox add src/srkit/inventory.py src/srkit/cli.py tests/test_inventory.py README.md
git -C E:/SR2030ToyBox commit -m "feat: srkit inventory — 게임 데이터의 섹션·키·열 목록을 CSV 로

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C E:/SR2030ToyBox push -u origin feat/inventory
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/inventory \
  --title "feat: srkit inventory — 게임 데이터의 섹션·키·열 목록" \
  --body "$(cat <<'EOF'
게임 텍스트 데이터를 읽기만 해서 섹션·키·열 목록을 `build/inventory/*.csv` 로 낸다.
치트·모드 조사 문서(docs/05~09)의 "전부 나열"을 받치는 도구다.

- 키 섹션(CVP, GMC, WMDATA 등)과 표(UNITS, TTR 등)를 섹션 이름표 없이 데이터로 구분한다.
- 실행 파일의 이름 표에서 파일에 안 쓰인 키 후보를 낸다(추정).
- 빌드 21347933: 섹션 53종(키 섹션 8, 표 45), 키 210개, 후보 759개.
- `uv run pytest`: 72 passed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --repo game-mod-project/SR2030Toybox feat/inventory --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

---

## Phase 2 — 파일로 쓰는 문서 (브랜치 `docs/cheat-mod-research`)

시작: `git -C E:/SR2030ToyBox switch -c docs/cheat-mod-research develop` 그리고 `uv run srkit inventory` (CSV 를 최신으로).

문서 공통 규칙: 첫 줄은 `# NN. 제목`, 그 아래에 조사 기준(`Steam appid 2093410, build 21347933`, 조사일)과 표기 설명([확인]/[추정]/[위키])을 둔다. 다른 문서와 겹치는 내용은 쓰지 않고 링크한다. 뜻을 모르는 키·열은 지어내지 않고 "모름"이라고 쓴다.

뜻을 정하는 근거의 우선순위: ① 게임 안 문구(`Localize\LOCALEN\*.csv` · `Variables.ini` 의 라벨 — `mods/korean/translation/*.csv` 의 `en` 열에서 검색) ② 공식 위키의 모딩 문서(<https://supremeruler.fandom.com/wiki/Modding_Supreme_Ruler> 에서 파일 형식 문서로 따라간다. 위키는 내장 브라우저로 읽는다 — WebFetch 는 402) ③ 이름. ①은 [확인: 게임 문구], ②는 [위키], ③은 [추정].

### Task 5: `docs/06-data-reference.md` — 섹션·키·열 참조

**Files:**
- Create: `docs/06-data-reference.md`
- 읽는 것: `build/inventory/sections.csv` `keys.csv` `columns.csv` `exe-candidates.csv` `skipped.csv`, `docs/01-game-structure.md`, `docs/02-modding-system.md`

**Interfaces:**
- Consumes: `srkit inventory` 의 CSV 다섯 개(Task 4)
- Produces: `docs/06-data-reference.md` — Task 6 · 17 이 섹션·키 이름을 이 문서의 표기대로 인용한다. 캐시 절은 Task 16 이 고친다.

- [ ] **Step 1: 뼈대를 쓴다**

```markdown
# 06. 데이터 참조

조사 기준: Steam appid `2093410`, build `21347933`, 2026-10-06. 표는 `uv run srkit inventory` 의 산출물
(`build/inventory/*.csv`)에서 옮긴 것이다 — 게임이 패치되면 다시 돌려 차이를 본다.

표기: **[확인]** 파일·실행 파일·게임 안에서 직접 확인, **[추정]** 정황으로 판단, **[위키]** 공식 위키에 있으나 이 빌드에서 미확인.

## 읽는 법
## 로딩 단계와 캐시
## 키 섹션
## 표 섹션
## 실행 파일에만 있는 이름
## 깊이 다루지 않는 섹션
## 출처
```

- [ ] **Step 2: "읽는 법"과 "로딩 단계와 캐시"를 쓴다**

"읽는 법": 줄 모양(섹션 머리, 이름으로 시작하는 줄 세 가지, 쉼표 행)과 키 섹션/표의 구분을 예시 한 줄씩으로 설명한다. 파일 문법 자체는 `docs/01` 의 "데이터 파일 형식"으로 링크한다.

"로딩 단계와 캐시": `docs/01` 의 "시나리오 로딩" 표를 링크하고, 여기에는 모드 제작자가 알아야 할 것만 쓴다 — 섹션마다 어느 단계(`#ifset 0x01` / `0x02` / `0x04` / 조건 없음)에서 읽히는지. 근거는 시나리오 파일 16개의 `#include` 다:

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
grep -a -n '#ifset\|#endifset\|#include\|^&&' "$G/Sandbox/World2030.scenario" | tr -d '\r'
```

캐시가 수정을 가리는지는 아직 모른다. 이 절 끝에 다음 한 줄을 그대로 넣는다(Task 16 이 결과로 바꾼다):

```markdown
> **[추정]** `0x02` 단계의 원본 데이터를 고치면 `Cache\*.SAV` 와 어긋난다. 게임 안 검증(V2)의 결과는 [09](09-cheat-mod-plan.md)에 있다.
```

- [ ] **Step 3: "키 섹션"을 쓴다 — 8종 전부, 키 전부**

`keys.csv` 의 `section` 값마다 소제목(`### CVP — 지역`)을 두고, 그 섹션의 키를 **하나도 빼지 않고** 표로 옮긴다:

```markdown
| 키 | 뜻 | 예시 | 쓰는 파일 수 | 근거 |
|---|---|---|---|---|
| `treasury` | 시작 국고 | `100` | 3 | [추정] |
```

"예시"는 `keys.csv` 의 `example`, "쓰는 파일 수"는 `files` 다. 섹션 소제목 아래에 그 섹션이 어느 파일들에 있는지(`sections.csv`), 블록이 무엇 단위인지(예: `&&CVP <지역 번호>`)를 한두 줄로 적는다.

- [ ] **Step 4: "표 섹션"을 쓴다**

`sections.csv` 에서 `kind` 가 `table` 인 섹션마다 소제목을 둔다. 치트·모드에 의미가 있는 다음 섹션은 열을 표로 옮긴다:
`UNITS` `TTR` `GOVTYPE` `TERRAIN` `REGIONSCEN` `CVPREL` `SEVENTS` `TRAINING` `RTREATIES` `RAWPROD` `OOB` `REGIONTECHS` `REGIONUNITDESIGNS` `REGIONPRODUCTS` `REGIONSOCIALS` `REGIONRELIGIONS` `GROUPING` `SPOTTING` `UNITWEIGHTING` `MISSILEWEIGHTING` `BUILDSEQUENCE2` `BUILDSEQUENCE3` `AIREQRESPONSE` `CABPRIORITIES` `PROCGENFAC`.

```markdown
| 열 | 이름 | 뜻 | 근거 |
|---|---|---|---|
| 25 | `DaysToBuild` | 건조 일수 | [추정] |
```

`UNITS` 는 `Maps/DATA/DEFAULT.UNIT` 의 155열을 전부 옮긴다(이름이 `0` 인 열은 "쓰이지 않음"). 열 이름이 없는 섹션(`columns.csv` 의 `name` 이 빔)은 열 번호와 `example` 로 짐작한 뜻을 [추정]으로 쓴다. 같은 섹션이 여러 파일에 있으면 대표 파일 하나를 옮기고, 열 수가 다른 파일이 있으면 그 사실을 적는다.

- [ ] **Step 5: "실행 파일에만 있는 이름"을 쓴다**

`exe-candidates.csv` 에서 `colon` 이 `1` 인 것(GMC 형식 키의 표지)을 전부 표로 옮긴다. 이름에서 짐작한 뜻을 [추정]으로 달고, 모르면 "모름". 절 머리에 다음을 적는다: 후보는 실행 파일의 문자열일 뿐이고, 어느 섹션의 키인지도 확인되지 않았다. 치트에 쓸 만해 보이는 것(`ignorecache` `magicresupply` `nounits` `fogofwar` 등)은 굵게 표시해 `docs/09` 가 집어 가게 한다. `colon` 이 `0` 인 후보는 개수만 적고 "GUI·글꼴·현지화 목록 이름이 섞여 있어 옮기지 않는다"고 쓴다.

- [ ] **Step 6: "깊이 다루지 않는 섹션"과 "출처"를 쓴다**

Step 4 에서 열을 옮기지 않은 표 섹션을 전부 이유와 함께 나열한다(예: `BITMAPS` `OBSTYLES` `MENUMAP` `HOTKEYS` `ORDERS` `CURSOR` — GUI 표, `docs/03` 의 범위 / `NAMESET` — 이름 목록 / `OOF` — 지도 위 개체, 한글화가 다룸). `skipped.csv` 의 이진 파일(`*.MAPX`)도 여기에 적는다.

- [ ] **Step 7: 빠진 섹션·키가 없는지 확인한다**

```bash
uv run python -c "
import csv, pathlib
tick = chr(96)
doc = pathlib.Path('docs/06-data-reference.md').read_text(encoding='utf-8')
rows = lambda name: list(csv.DictReader(open('build/inventory/' + name, encoding='utf-8-sig')))
print('빠진 섹션:', sorted({r['section'] for r in rows('sections.csv') if tick + r['section'] + tick not in doc}))
print('빠진 키:', sorted({r['key'] for r in rows('keys.csv') if tick + r['key'] + tick not in doc}))
print('빠진 UNITS 열:', sorted({r['name'] for r in rows('columns.csv') if r['file'] == 'Maps/DATA/DEFAULT.UNIT' and r['name'] not in ('', '0') and tick + r['name'].strip(tick) + tick not in doc}))
"
```

Expected: 세 줄 모두 `[]`

- [ ] **Step 8: 커밋**

```bash
git -C E:/SR2030ToyBox add docs/06-data-reference.md
git -C E:/SR2030ToyBox commit -m "docs: 데이터 참조 — 섹션 53종의 키와 열

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: `docs/05-game-systems.md` — 12개 영역

**Files:**
- Create: `docs/05-game-systems.md`
- 읽는 것: `docs/06-data-reference.md`, `build/inventory/*.csv`, 위키 치트 문서 <https://supremeruler.fandom.com/wiki/Cheats>

**Interfaces:**
- Consumes: `docs/06` 의 섹션·키·열 이름(Task 5)
- Produces: `docs/05-game-systems.md` — Task 17 의 분류표가 영역 이름을 이 문서의 제목대로 쓴다: 국가, 경제, 자원, 산업, 연구, 정치, 외교, 군사, 부대, 장비, 전쟁, AI

- [ ] **Step 1: 뼈대를 쓴다**

머리말(조사 기준, 표기) 아래에 영역 12개를 `## 국가` … `## AI` 로 두고, 영역마다 같은 다섯 소절을 쓴다:

```markdown
## 경제

**게임에서 무엇인가** — 두세 문장. 플레이어가 화면에서 보는 것(국고, GDP/c, 부채, 물가, 실업).

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|

**내장 치트** — 이 영역을 바꾸는 `cheat …` 명령([07](07-cheats.md) 의 행으로 링크). 없으면 "없음".

**바꿀 수 있는 수단** — 내장 치트 / 시나리오 설정 / 데이터 표 가운데 무엇으로 되는지 한 줄씩.

**모르는 것** — 확인하지 못한 것, 계산식이 실행 파일 안에 있어 데이터로 못 바꾸는 것.
```

- [ ] **Step 2: 영역마다 "어디에 들어 있나"를 채운다**

출발점은 아래 표다. 이름에서 짐작한 것이므로 `docs/06` 과 CSV 로 하나씩 확인하고, 맞지 않으면 옮기거나 지운다. 표에 없는 섹션·키 가운데 그 영역에 속하는 것이 `docs/06` 에 있으면 더한다.

| 영역 | 출발점(추정) |
|---|---|
| 국가 | `CVP`(`regionname` `flagnum` `capitalx` `capitaly` `parentregion` `nonplayable` `keepregion`), `REGIONINCL`, `REGIONSCEN`, `GROUPING`, `THEATRES` |
| 경제 | `CVP`(`treasury` `nationaldebtgdp` `gdpc` `inflation` `unemployment` `creditrating` `buyingpower`), `WMDATA`(`gdpcbase` `primerate`), `GMC`(`initialfunds` `debtfree`) |
| 자원 | `WMPRODDATA`, `RAWPROD`, `REGIONPRODUCTS`, `GMC`(`resources`), `WMDATA`(`hexresmults`) |
| 산업 | `UNITS` 의 시설 행(`uIndustry` `HasProduction` `uProdTech` `uBuildCap`), `PROCGENFAC`, `Maps/DATA/production.csv`, `GMC`(`fastbuild`) |
| 연구 | `TTR`, `REGIONTECHS`, `CVP`(`techlevel`), `GMC`(`techtreedefault` `victorytech` `restricttechtrade` `groupresearchmerge`) |
| 정치 | `CVP`(`govtype` `politic` `civapproval` `milapproval` `electiondate` `electionterm`), `GOVTYPE`, `PEOPLE`, `REGIONSOCIALS`, `REGIONRELIGIONS`, `CABPRIORITIES`, `GMC`(`govchoice` `approvaleff`) |
| 외교 | `CVPREL`, `RTREATIES`, `CVP`(`influence` `influenceval` `sphere` `worldintegrity` `treatyintegrity` `bwmmember`), `SEVENTS`, `GMC`(`relationseffect` `regionallies` `regionaxis`) |
| 군사 | `CVP`(`defcon` `poptotalarmy` `popminreserve` `bconscript` `milspendsalary` `milspendmaint`), `TRAINING`, `GMC`(`reservelimit`) |
| 부대 | `OOB`, `NAVALTRANSIT`, `THEATRETRANSF`, `GMC`(`regionequip`), `WMDATA`(`unitgarrison` `unitpartisan` `createbattlegroupsize`) |
| 장비 | `UNITS`(비용·일수·공격·방어·사거리 열), `REGIONUNITDESIGNS`, `CVP`(`armsavail` `worldavail`) |
| 전쟁 | `TERRAIN`, `SPOTTING`, `Maps/DATA/battlezones.csv`, `ORDERS`, `GMC`(`missilenolimit` `limitdareffect` `limitmareffect` `wmdeff` `alliedvictory`) |
| AI | `AIPARAMS`, `AIREQRESPONSE`, `BUILDSEQUENCE2` `BUILDSEQUENCE3`, `UNITWEIGHTING`, `MISSILEWEIGHTING`, `CVP`(`playeragenda` `playeraistance`), `GMC`(`aistance`), `WMDATA`(`aiplayrich` `aiunitbuild*`) |

- [ ] **Step 3: "내장 치트"와 "바꿀 수 있는 수단"을 채운다**

위키 치트 문서를 내장 브라우저로 읽고 명령을 영역에 나눈다. 효과 설명은 [위키]로 표시한다(게임 검증은 Task 12). 치트가 없는 영역은 "없음"이라고 쓰고, 그 경우 데이터 표의 어느 키·열을 바꾸면 될지를 "바꿀 수 있는 수단"에 적는다([추정]).

- [ ] **Step 4: 빠진 영역·소절이 없는지 확인한다**

```bash
uv run python -c "
import pathlib, re
doc = pathlib.Path('docs/05-game-systems.md').read_text(encoding='utf-8')
areas = ['국가', '경제', '자원', '산업', '연구', '정치', '외교', '군사', '부대', '장비', '전쟁', 'AI']
parts = dict(zip(re.findall(r'^## (.+)$', doc, re.M), re.split(r'^## .+$', doc, flags=re.M)[1:]))
print('빠진 영역:', [a for a in areas if a not in parts])
subs = ['게임에서 무엇인가', '어디에 들어 있나', '내장 치트', '바꿀 수 있는 수단', '모르는 것']
print('빠진 소절:', [(a, s) for a in areas if a in parts for s in subs if '**' + s + '**' not in parts[a]])
"
```

Expected: 두 줄 모두 `[]`

- [ ] **Step 5: 커밋**

```bash
git -C E:/SR2030ToyBox add docs/05-game-systems.md
git -C E:/SR2030ToyBox commit -m "docs: 게임 구조 — 12개 영역과 데이터의 대응

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 7: `docs/07-cheats.md` — 내장 치트표 초안

**Files:**
- Create: `docs/07-cheats.md`
- 읽는 것: 실행 파일의 `cheat …` 문자열, 위키 <https://supremeruler.fandom.com/wiki/Cheats>, `INI\hotkeys.csv`

**Interfaces:**
- Consumes: 없음
- Produces: `docs/07-cheats.md` — 표의 "검증" 열은 이 Task 에서 전부 [위키] 또는 [추정]이고, Task 16 이 게임 결과로 바꾼다. 명령은 `` `cheat <이름>` `` 꼴로 적는다(Task 16 · 17 의 확인 스크립트가 이 꼴을 찾는다).

- [ ] **Step 1: 실행 파일의 명령 목록을 뽑는다**

```bash
uv run python -c "
import re
from srkit import config
exe = (config.load().game_dir / 'SupremeRuler2030.exe').read_bytes()
names = sorted({m.decode() for m in re.findall(rb'cheat ([!-~]{1,20})', exe)})
print(len(names)); print(' '.join(names))
"
```

Expected: 첫 줄 `91`, 둘째 줄은 `007 adama airequest allowcheats allunit …` 로 시작한다.

- [ ] **Step 2: 문서를 쓴다**

```markdown
# 07. 내장 치트

조사 기준: Steam appid `2093410`, build `21347933`, 2026-10-06. 명령 목록은 실행 파일의 문자열 91개에서, 설명은 공식 위키에서 왔다.

표기: **[확인]** 게임 안에서 직접 확인, **[추정]** 정황으로 판단, **[위키]** 공식 위키에 있으나 이 빌드에서 미확인.

## 넣는 법
## 치트표
### 경제 · 자원 · 연구 · 생산
### 국가 · 정치 · 인구
### 외교
### 군사 · 부대 · 정보
### 진행 · 화면 · 이벤트
### Galactic Ruler 에서 온 명령
### 개발용 · 위험
## 쓰지 말 것
## 출력 명령
## 출처
```

"넣는 법": `Ctrl+Shift+S`(Game Settings — `INI\hotkeys.csv` 에 행이 있다 [확인: 파일]) → 아래 입력란에 `cheat allowcheats` → 치트 입력. 싱글플레이 전용, 게임을 끝내야 꺼진다 [위키]. 같은 치트를 다시 넣으면 꺼지는 것이 있다 [위키].

"치트표"의 표 형식(묶음마다 하나):

```markdown
| 명령 | 인자 | 효과 | 대상 | 출처 | 검증 |
|---|---|---|---|---|---|
| `cheat treasury` | 금액(백만) | 국고를 그만큼 늘린다 | 플레이어 | 위키 (SR2030) | [위키] |
| `cheat spawnunit` | 모름 | 모름 | 모름 | 실행 파일만 | [추정] |
```

묶음별 명령(이 배치는 Task 12 의 시험 묶음과 같다):

- 경제 · 자원 · 연구 · 생산 (14): `treasury` `georgew` `georgeww` `trumpme` `products` `branson` `bezos` `gates` `technology` `finalexam` `e=mc2` `onedaybuild` `breakground` `allunit`
- 국가 · 정치 · 인구 (12): `populate` `depopulate` `approval` `democracy` `novichok` `becomeregion` `annex` `colonize` `liberate` `revolt` `reviveall` `putin`
- 외교 (16): `love` `hate` `neutral` `treaty` `mutualdef` `dipaccept` `peace` `worldwar` `fight` `saddam` `saddamme` `sanction` `wmsanction` `shelovesme` `shelovesmenot` `moreoffers`
- 군사 · 부대 · 정보 (14): `spawnunit` `unitdesign` `damage` `stranded` `darran` `darren` `launchattack` `selloffunits` `nomove` `007` `maxsat` `satellite` `panic` `beammeup`
- 진행 · 화면 · 이벤트 (13): `endday` `increaseday` `speedlock` `blueskies` `eventnow` `eventclear` `done` `instantwin` `fullmapshow` `airequest` `noaiinit` `fullaiinit` `devcheat`
- Galactic Ruler 에서 온 명령 (17): `voyager` `enterprise` `q` `adama` `warp9` `charge!` `planetcloud` `lightyear` `anomaly` `shielded` `upgradearmour` `upgradecargo` `upgradecommand` `upgradeengine` `upgradeweapon` `discovered` `known`
- 개발용 · 위험 (3): `killeveryone` `stresstest` `meshtest`
- 넣는 법에서 다룸 (1): `allowcheats` / 쓰지 말 것 (1): `resettutorial`

"대상" 열은 플레이어만 / 모든 지역 / 고른 부대 / 지정한 지역 중 하나다. `onedaybuild` `allunit` 처럼 AI 도 혜택을 보는 것은 "모든 지역"으로 적는다 [위키]. 위키에 없는 명령은 효과를 지어내지 않고 "모름"이라고 쓴다.

"쓰지 말 것": `cheat resettutorial` — 튜토리얼 완료 업적을 지운다 [위키]. 이 저장소의 검증에서도 실행하지 않는다.

"출력 명령": 위키의 "Output Functions" 절에 있는 `output…` 명령을 표로 옮기고(명령, 무엇을 파일로 내는가), 실행 파일에 문자열이 있는지 확인한다:

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
grep -a -o 'output[a-z]\{2,20\}' "$G/SupremeRuler2030.exe" | sort -u
```

- [ ] **Step 3: 91개가 다 있는지 확인한다**

```bash
uv run python -c "
import re, pathlib
from srkit import config
tick = chr(96)
exe = (config.load().game_dir / 'SupremeRuler2030.exe').read_bytes()
names = sorted({m.decode() for m in re.findall(rb'cheat ([!-~]{1,20})', exe)})
doc = pathlib.Path('docs/07-cheats.md').read_text(encoding='utf-8')
print(len(names), '개 중 빠진 것:', [n for n in names if tick + 'cheat ' + n + tick not in doc])
"
```

Expected: `91 개 중 빠진 것: []`

- [ ] **Step 4: 커밋**

```bash
git -C E:/SR2030ToyBox add docs/07-cheats.md
git -C E:/SR2030ToyBox commit -m "docs: 내장 치트표 초안 — 실행 파일의 명령 91개와 위키 설명

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: `docs/08-workshop-survey.md` — Workshop 전수 조사, PR

**Files:**
- Create: `docs/08-workshop-survey.md`
- 읽는 것: <https://steamcommunity.com/workshop/browse/?appid=2093410&browsesort=totaluniquesubscribers&section=readytouseitems&actualsort=totaluniquesubscribers&p=1> (과 `&p=2`), 항목 페이지

**Interfaces:**
- Consumes: `docs/05` 의 영역 이름(Task 6), `docs/07` 의 치트 묶음(Task 7) — "겹치는 기능"을 그 이름으로 적는다
- Produces: `docs/08-workshop-survey.md` — Task 17 이 "Workshop 기존 모드" 수단의 행을 여기서 가져온다. 항목 링크는 `https://steamcommunity.com/sharedfiles/filedetails/?id=<번호>` 꼴로 적는다.

- [ ] **Step 1: 목록을 모은다**

내장 브라우저로 목록 두 쪽을 연다. 쪽 머리의 "필터와 일치하는 콘텐츠: N개"를 적어 둔다(2026-10-06 에 53). 항목 링크를 뽑는다:

```
mcp__Claude_Browser__navigate  url=<위 주소, p=1>
mcp__Claude_Browser__javascript_tool  text=[...document.querySelectorAll('a.ugc, .workshopItem a[href*="filedetails"]')].map(a => a.href).filter((v, i, s) => s.indexOf(v) === i)
```

`p=2` 도 같게 한다. 모은 링크 수가 N 과 같아야 한다. 다르면 선택자를 고쳐 다시 뽑는다(`read_page` 로 구조를 본다).

- [ ] **Step 2: 항목마다 페이지를 읽는다**

항목 페이지를 `navigate` → `get_page_text` 로 읽어 다음을 적는다: 제목, 제작자, 태그(유형 `Mods`/`Maps` 포함), 필요 DLC, 올린 날과 고친 날, 파일 크기, 설명이 말하는 바뀌는 것. 구독·평가·댓글은 하지 않는다. 쿠키 안내가 뜨면 필수만 허용한다.

- [ ] **Step 3: 문서를 쓴다**

```markdown
# 08. Workshop 조사

조사일: 2026-10-06. 대상: Supreme Ruler 2030 Workshop 의 항목 N개 전부. 항목을 구독하지 않고 페이지의
제목·설명·태그만 읽었다 — 파일 내용은 보지 않았다. 목록은 시간이 지나면 바뀐다.

## 요약
## 분류별 표
### 치트 · 도구
### 밸런스
### 경제
### 군사 · 장비
### 국가 · 시나리오
### 지도
### 그래픽 · 소리 · UI
## 이미 있는 기능과 없는 기능
## 출처
```

표 형식:

```markdown
| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|
| [Real Unit Stats](https://steamcommunity.com/sharedfiles/filedetails/?id=…) | D-Bassett | MODS | – | 2026-…  | 장비 수치를 실제 제원에 맞춘다 | 장비 — 부대 스탯 | 설명 |
```

"무엇을 바꾸나"는 설명을 우리말 한 줄로 요약한다(설명 문장을 옮겨 적지 않는다). "근거"는 `설명`(설명에 분명히 적힘) / `설명 부족`(제목·태그로만 판단) 중 하나다. 한 항목은 한 분류에만 넣고, 걸치는 것은 주된 쪽에 넣어 "겹치는 기능"에 나머지를 적는다.

"이미 있는 기능과 없는 기능": 원안 ②의 예시 아홉 개(돈, 자원, 연구, 국가 관계, 군사력, 장비 생산, 부대 스탯, 인구, GDP)마다 "이 기능을 주는 Workshop 항목"을 적는다. 없으면 "없음". `Unofficial External Trainer` 와 `SR2030 Save Editor` 는 Workshop 에 올라 있지만 게임 밖 프로그램일 수 있다 — 설명에서 배포 방식(Workshop 이 파일을 어디에 두는지, 따로 내려받는지)을 확인해 적는다.

- [ ] **Step 4: 항목 수를 확인한다**

```bash
uv run python -c "
import re, pathlib
doc = pathlib.Path('docs/08-workshop-survey.md').read_text(encoding='utf-8')
print(len(set(re.findall(r'filedetails/\?id=(\d+)', doc))))
"
```

Expected: Step 1 에서 적어 둔 N (2026-10-06 기준 `53`)

- [ ] **Step 5: 커밋, 푸시, PR, 머지**

```bash
git -C E:/SR2030ToyBox add docs/08-workshop-survey.md
git -C E:/SR2030ToyBox commit -m "docs: Workshop 전수 조사 — 분류와 겹치는 기능

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
uv run pytest -q
git -C E:/SR2030ToyBox push -u origin docs/cheat-mod-research
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/cheat-mod-research \
  --title "docs: 치트·모드 조사 — 게임 구조, 데이터 참조, 내장 치트, Workshop" \
  --body "$(cat <<'EOF'
파일·실행 파일·위키·Workshop 페이지로 조사한 문서 네 개.
게임 안 검증은 아직이다 — 치트 효과는 [위키], 데이터의 뜻은 대부분 [추정]으로 표시했다.

- `docs/05-game-systems.md`: 12개 영역과 데이터의 대응
- `docs/06-data-reference.md`: 섹션 53종의 키와 열
- `docs/07-cheats.md`: 내장 치트 91개
- `docs/08-workshop-survey.md`: Workshop 항목 전수
- `uv run pytest`: 72 passed (문서만 바뀜)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --repo game-mod-project/SR2030Toybox docs/cheat-mod-research --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

---

## Phase 3 — 게임 안 검증

### Task 9: `srkit probe` — 값 한 곳만 바꾼 시험 모드 (브랜치 `feat/probe`)

시작: `git -C E:/SR2030ToyBox switch -c feat/probe develop`

**Files:**
- Create: `src/srkit/probe.py`, `tests/test_probe.py`
- Modify: `src/srkit/cli.py`, `README.md`

**Interfaces:**
- Consumes: `config.Config` (`game_dir`, `build_dir`, `root`)
- Produces:
  - `probe.make(cfg: Config, name: str, rel: str, old: str, new: str, *, after: str | None = None) -> Path` — `build/probe-<name>/<rel>` 을 쓰고 그 경로를 돌려준다. 조건에 안 맞으면 `RuntimeError`, 파일을 만들지 않는다
  - 상수 `probe.NEAR = 4096`
  - 명령 `uv run srkit probe <이름> <파일> <바꿀 문자열> <새 문자열> [--after <기준 문자열>]`
  - 설치할 모드 이름은 `probe-<이름>` (`uv run srkit deploy probe-<이름>`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_probe.py`:

```python
from dataclasses import replace

import pytest

from srkit import probe

# CRLF 와 CP1252 바이트(é = 0xE9)가 든 지역 데이터 대역
CVP = (b"&&CVP 1499\r\nregionname \"Allemagn\xe9\"\r\ngdpc 51203\r\n\r\n"
       b"&&CVP 1500\r\nregionname \"Other\"\r\ngdpc 51203\r\ntechlevel 110\r\n")


@pytest.fixture
def fake(cfg, tmp_path):
    game = tmp_path / "game"
    (game / "Maps").mkdir(parents=True)
    (game / "Maps" / "W2030.CVP").write_bytes(CVP)
    return replace(cfg, root=tmp_path / "proj", game_dir=game)


def test_changes_one_place_and_keeps_every_other_byte(fake):
    out = probe.make(fake, "cvp", "Maps/W2030.CVP", "gdpc 51203", "gdpc 99999", after="&&CVP 1500")
    assert out == fake.build_dir / "probe-cvp" / "Maps" / "W2030.CVP"
    assert out.read_bytes() == CVP[:CVP.rindex(b"gdpc 51203")] + b"gdpc 99999" + b"\r\ntechlevel 110\r\n"
    assert (fake.game_dir / "Maps" / "W2030.CVP").read_bytes() == CVP          # 게임 폴더는 그대로


def test_without_an_anchor_the_text_must_be_unique(fake):
    out = probe.make(fake, "tech", "Maps/W2030.CVP", "techlevel 110", "techlevel 140")
    assert b"techlevel 140" in out.read_bytes()
    with pytest.raises(RuntimeError, match="2번 나옵니다"):
        probe.make(fake, "dup", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1")
    with pytest.raises(RuntimeError, match="0번 나옵니다"):
        probe.make(fake, "none", "Maps/W2030.CVP", "gdpc 7", "gdpc 1")
    assert not (fake.build_dir / "probe-dup").exists() and not (fake.build_dir / "probe-none").exists()


def test_anchor_must_be_unique_and_close(fake, monkeypatch):
    with pytest.raises(RuntimeError, match="기준 문자열이 2번"):
        probe.make(fake, "x", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1", after="&&CVP 1")
    with pytest.raises(RuntimeError, match="기준 문자열이 0번"):
        probe.make(fake, "x", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1", after="&&CVP 777")
    monkeypatch.setattr(probe, "NEAR", 20)      # 기준 블록에 값이 없으면 다음 블록의 값을 바꾸지 않는다
    with pytest.raises(RuntimeError, match="안에 바꿀 문자열이 없습니다"):
        probe.make(fake, "x", "Maps/W2030.CVP", "techlevel 110", "techlevel 1", after="&&CVP 1499")
    assert not (fake.build_dir / "probe-x").exists()


def test_missing_game_file_is_refused(fake):
    with pytest.raises(RuntimeError, match="게임 폴더에 없는 파일"):
        probe.make(fake, "x", "Maps/NOPE.CVP", "a", "b")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_probe.py -q`
Expected: 수집 단계에서 `ImportError: cannot import name 'probe' from 'srkit'`

- [ ] **Step 3: 구현한다**

`src/srkit/probe.py`:

```python
"""실험용 모드(build/probe-<이름>/) 만들기: 설치본의 파일 하나에서 값 한 곳만 바꾼 사본.

게임 파일의 사본이므로 저장소에 넣지 않는다(build/ 는 git 제외). 바이트를 그대로 다뤄 인코딩과 줄 끝을 건드리지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from .config import Config

NEAR = 4096     # --after 로 정한 기준에서 이 바이트 안에 있어야 한다 (다른 블록의 같은 값을 잘못 바꾸지 않게)


def make(cfg: Config, name: str, rel: str, old: str, new: str, *, after: str | None = None) -> Path:
    src = cfg.game_dir / rel
    if not src.is_file():
        raise RuntimeError(f"게임 폴더에 없는 파일입니다: {rel}")
    data = src.read_bytes()
    old_b, new_b = old.encode("cp1252"), new.encode("cp1252")
    if after is None:
        if data.count(old_b) != 1:
            raise RuntimeError(f"바꿀 문자열이 {data.count(old_b)}번 나옵니다(한 번이어야 합니다. --after 로 위치를 정하세요): {old!r}")
        pos = data.index(old_b)
    else:
        anchor = after.encode("cp1252")
        if data.count(anchor) != 1:
            raise RuntimeError(f"기준 문자열이 {data.count(anchor)}번 나옵니다(한 번이어야 합니다): {after!r}")
        start = data.index(anchor) + len(anchor)
        pos = data.find(old_b, start, start + NEAR)
        if pos < 0:
            raise RuntimeError(f"기준 뒤 {NEAR}바이트 안에 바꿀 문자열이 없습니다: {old!r}")
    out = cfg.build_dir / f"probe-{name}" / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data[:pos] + new_b + data[pos + len(old_b):])
    return out
```

`src/srkit/cli.py` — import 를 바꾼다:

```python
from . import config, deploy, hook, inventory, korean, mt, probe
```

`def cmd_deploy` 위에 더한다:

```python
def cmd_probe(cfg, args) -> int:
    out = probe.make(cfg, args.name, args.file, args.old, args.new, after=args.after)
    print(f"시험 모드 : {out.relative_to(cfg.root)}")
    print(f"설치      : uv run srkit deploy probe-{args.name}   (미리보기. --apply 로 실행, 끝나면 undeploy)")
    return 0
```

`main` 의 `for name, fn, text in (("deploy", cmd_deploy, …` 줄 바로 위에 더한다:

```python
    pr = sub.add_parser("probe", help="설치본 파일에서 값 한 곳만 바꾼 시험 모드를 build/probe-<이름> 에 만들기")
    pr.add_argument("name", help="시험 이름 (설치할 때는 probe-<이름>)")
    pr.add_argument("file", help="게임 폴더 기준 경로 (예: Maps/W2030.CVP)")
    pr.add_argument("old", help="바꿀 문자열 (파일에 한 번만 나와야 한다)")
    pr.add_argument("new", help="새 문자열")
    pr.add_argument("--after", help="이 문자열(한 번만 나와야 한다) 뒤의 첫 일치를 바꾼다")
    pr.set_defaults(fn=cmd_probe)
```

- [ ] **Step 4: 통과를 확인하고 설치본에서 돌려 본다**

Run: `uv run pytest -q`
Expected: `76 passed`

Run (Bash): `uv run srkit probe gdpc Maps/W2030.CVP 'gdpc 51203' 'gdpc 99999' --after '&&CVP 1499'`
Expected: `시험 모드 : build\probe-gdpc\Maps\W2030.CVP` 와 설치 안내 한 줄

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
cmp -l "$G/Maps/W2030.CVP" build/probe-gdpc/Maps/W2030.CVP | wc -l
```

Expected: `5` (숫자 다섯 자리만 다르다). 게임 폴더는 바뀌지 않는다 — `srkit deploy probe-gdpc` 는 이 Task 에서 실행하지 않는다.

- [ ] **Step 5: README 에 적는다**

"빠른 시작" 코드 블록의 `uv run srkit inventory …` 줄 아래에:

```
uv run srkit probe <이름> <파일> <바꿀 문자열> <새 문자열>   # 값 한 곳만 바꾼 시험 모드 → build/probe-<이름>/
```

"구조" 코드 블록의 `inventory.py …` 줄 아래에:

```
  probe.py       값 한 곳만 바꾼 시험 모드 만들기 (데이터 수정이 게임에 반영되는지 확인용)
```

- [ ] **Step 6: 커밋, 푸시, PR, 머지**

```bash
git -C E:/SR2030ToyBox add src/srkit/probe.py src/srkit/cli.py tests/test_probe.py README.md
git -C E:/SR2030ToyBox commit -m "feat: srkit probe — 값 한 곳만 바꾼 시험 모드 만들기

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C E:/SR2030ToyBox push -u origin feat/probe
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/probe \
  --title "feat: srkit probe — 값 한 곳만 바꾼 시험 모드" \
  --body "$(cat <<'EOF'
데이터 수정이 게임에 반영되는지(캐시, 시나리오 설정, 지역 값) 확인하는 실험용 도구.
설치본 파일의 사본을 `build/probe-<이름>/` 에 만들 뿐 게임 폴더는 읽기만 한다. 설치는 기존 `srkit deploy`.

- 바이트 단위로 한 곳만 바꾼다(인코딩·줄 끝 보존). 바꿀 곳이 하나로 정해지지 않으면 거부한다.
- `uv run pytest`: 76 passed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --repo game-mod-project/SR2030Toybox feat/probe --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

### Task 10: 기준선 관찰과 치트 입력 경로 확보 (게임, 코드 변경 없음)

**Files:**
- Create (git 제외): `build/verify/baseline/notes.md`, `build/verify/baseline/*.png`

**Interfaces:**
- Consumes: `scripts/gamedrive.py` (`start` `status` `shot` `click` `move` `key` `type` `stop`)
- Produces: `build/verify/baseline/notes.md` — 다음 Task 들이 그대로 따라 하는 기록:
  - **새 게임 시작 경로**: 메인 메뉴 → World 2030 → 독일 → 시작까지의 클릭 좌표 순서
  - **로비 설정**: Initial Funds 의 기본값, "Force Recache For Modding" 옵션의 위치(좌표)
  - **기준 값**: 독일의 시작 국고, GDP/c, `Leopard 2A7+` 의 비용과 건조 일수(각각 어느 화면의 어느 좌표에서 읽는지)
  - **치트 입력 경로**: `chat` / `menu` / `combo` / `blocked` 중 하나와 그 조작 순서

- [ ] **Step 1: 게임을 띄운다**

Run: `uv run python scripts/gamedrive.py status`
Expected: `프로세스: 없음`. "(이 도구가 띄운 것 아님)"이 보이면 사용자의 게임이다 — 건드리지 않고 끝날 때까지 기다린다.

Run (백그라운드): `uv run python scripts/gamedrive.py start`
25초 뒤: `uv run python scripts/gamedrive.py shot build/verify/baseline/01-menu.png`
Expected: 메인 메뉴. 출력에 "빈 화면일 수 있음"이 있으면 10초 뒤 다시 찍는다.

- [ ] **Step 2: World 2030 을 독일로 시작하며 경로와 기본값을 적는다**

화면마다 `shot` 으로 찍어 읽고 `click X Y` 로 넘어간다(좌표는 캡처 이미지의 픽셀). 메인 메뉴 → 싱글 플레이의 샌드박스 → World 2030 → 지역 선택(기본이 독일, `defaultregion 1499`) → 로비 설정 화면. 로비 설정에서:

- Initial Funds(초기 자금)의 현재 값을 적는다(시나리오 파일은 `initialfunds: 2` = "Default").
- "Force Recache For Modding"(한글화 상태면 "모드용 캐시 재생성") 옵션의 위치를 적는다. **켜지 않는다.**

그대로 게임을 시작한다. 클릭한 좌표를 순서대로 `notes.md` 에 적는다.

- [ ] **Step 3: 기준 값을 읽는다**

게임이 시작되면 일시 정지 상태로 둔다(시간을 흘리지 않는다). 다음을 화면에서 읽어 `notes.md` 에 값과 읽은 위치를 적고 화면을 저장한다:

- 시작 국고 → `build/verify/baseline/03-treasury.png`
- GDP/c (재무 또는 국가 정보 화면) → `04-gdpc.png`
- 육군 생산 목록의 `Leopard 2A7+` 비용과 건조 일수 → `05-leopard.png` (파일 값: 비용 `6`, 일수 `1.9`). 목록에 없으면 `Leopard 2A6`(비용 `5.3`, 일수 `1.8`)을 대신 적고, Task 13 의 대상도 그것으로 바꾼다고 적는다.

- [ ] **Step 4: 치트 입력 경로 ① — 채팅 창**

```bash
uv run python scripts/gamedrive.py key ENTER
uv run python scripts/gamedrive.py shot build/verify/baseline/10-chat.png
uv run python scripts/gamedrive.py type cheat allowcheats
uv run python scripts/gamedrive.py key ENTER
uv run python scripts/gamedrive.py shot build/verify/baseline/11-chat-allow.png
uv run python scripts/gamedrive.py key ENTER
uv run python scripts/gamedrive.py type cheat georgew
uv run python scripts/gamedrive.py key ENTER
uv run python scripts/gamedrive.py shot build/verify/baseline/12-chat-georgew.png
```

국고가 Step 3 의 값에서 100억 늘었으면 경로는 `chat` 이다 → Step 7 로. 아니면 `key ESC` 로 창을 닫고 Step 5.

- [ ] **Step 5: 치트 입력 경로 ② — 메뉴**

`Ctrl+Shift+S` 가 여는 것은 "Game Settings" 화면이다(`INI\hotkeys.csv`). 같은 화면을 여는 버튼을 찾는다: 게임 안 메뉴(`key ESC`)와 화면 가장자리의 톱니·설정 버튼을 `shot` 으로 찾아 눌러 본다. 아래쪽에 글자 입력란이 있는 설정 화면이 열리면 입력란을 `click` 하고 Step 4 의 `type cheat allowcheats` → `ENTER` → `type cheat georgew` → `ENTER` 를 한다. 국고가 늘면 경로는 `menu` 다 → Step 7.

- [ ] **Step 6: 둘 다 안 되면**

`notes.md` 에 시도한 것과 화면을 적고 경로를 `combo` 로 적는다. Task 11 을 수행한 뒤 이 Task 의 Step 7 로 돌아온다. Task 11 도 실패하면 경로는 `blocked` 다.

- [ ] **Step 7: 게임을 끄고 기록을 마친다**

```bash
uv run python scripts/gamedrive.py stop
uv run python scripts/gamedrive.py status
```

Expected: `프로세스: 없음`. 저장하겠느냐고 물으면 저장하지 않는다.

`notes.md` 에 네 항목(새 게임 시작 경로, 로비 설정, 기준 값, 치트 입력 경로)이 모두 있는지 확인한다. 치트가 켜졌을 때 화면에 뜬 문구("So, you need to cheat eh?" / "그래, 치트가 필요한가요?")와 업적에 관한 표시가 있었는지도 적는다.

### Task 11 (조건부): `gamedrive.py key` 에 조합키 (브랜치 `feat/gamedrive-combo-keys`)

**Task 10 의 경로가 `combo` 일 때만 한다.** `chat` 이나 `menu` 면 건너뛴다.

시작: 게임이 꺼져 있는지 확인(`status`)한 뒤 `git -C E:/SR2030ToyBox switch -c feat/gamedrive-combo-keys develop`

**Files:**
- Modify: `scripts/gamedrive.py:12` (사용법) · `:95` (`KEYS` 아래) · `:383-391` (`key` 명령)
- Test: `tests/test_gamedrive.py`

**Interfaces:**
- Consumes: `gamedrive.KEYS`, `user32`, `kernel32`, `need_window`
- Produces:
  - `gamedrive.MODS = {"CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12}`
  - `gamedrive.parse_key(name: str) -> tuple[list[int], int]`
  - `gamedrive.held(hwnd: int, mods: list[int])` — 컨텍스트 관리자
  - 명령 `uv run python scripts/gamedrive.py key CTRL+SHIFT+S`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_gamedrive.py` 끝에 추가:

```python
def test_key_names_with_modifiers(gd):
    assert gd.parse_key("ENTER") == ([], 0x0D)
    assert gd.parse_key("0x1B") == ([], 0x1B)
    assert gd.parse_key("27") == ([], 27)                    # 숫자는 지금처럼 가상 키 코드다
    assert gd.parse_key("s") == ([], 0x53)
    assert gd.parse_key("CTRL+SHIFT+S") == ([0x11, 0x10], 0x53)
    assert gd.parse_key("ctrl+enter") == ([0x11], 0x0D)
    with pytest.raises(SystemExit, match="모르는 수정키"):
        gd.parse_key("WIN+S")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `uv run pytest tests/test_gamedrive.py -q`
Expected: 1 failed — `AttributeError: module 'gamedrive' has no attribute 'parse_key'`

- [ ] **Step 3: 구현한다**

`scripts/gamedrive.py` — `KEYS = {…}` 줄 아래에 더한다:

```python
MODS = {"CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12}


def parse_key(name: str) -> tuple[list[int], int]:
    """ "CTRL+SHIFT+S" → ([0x11, 0x10], 0x53). 마지막이 누를 키, 그 앞은 누른 채로 둘 수정키다."""
    *mods, last = name.upper().split("+")
    unknown = [m for m in mods if m not in MODS]
    if unknown:
        raise SystemExit(f"모르는 수정키: {', '.join(unknown)} (쓸 수 있는 것: {', '.join(MODS)})")
    if last in KEYS:
        vk = KEYS[last]
    elif len(last) == 1 and last.isalpha():
        vk = ord(last)
    else:
        vk = int(last, 0)
    return [MODS[m] for m in mods], vk
```

`need_window` 함수 아래에 더한다:

```python
@contextmanager
def held(hwnd: int, mods: list[int]):
    """게임 스레드의 키 상태표에 수정키를 눌린 것으로 적어 둔다(GetKeyState 가 읽는 값). 실제 키보드는 건드리지 않는다.

    메시지만 보내면 게임이 Ctrl·Shift 를 눌린 것으로 읽지 않는다. 게임이 GetAsyncKeyState 로 읽는다면 이 방법도 안 된다.
    """
    if not mods:
        yield
        return
    me, target = kernel32.GetCurrentThreadId(), user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(me, target, True)
    try:
        state = (ctypes.c_ubyte * 256)()
        user32.GetKeyboardState(state)
        saved = bytes(state)
        for vk in mods:
            state[vk] |= 0x80
            user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
        user32.SetKeyboardState(state)
        yield
        for vk in reversed(mods):
            user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
        time.sleep(0.2)             # 게임이 보낸 메시지를 다 읽을 때까지 눌린 상태를 둔다
        user32.SetKeyboardState((ctypes.c_ubyte * 256).from_buffer_copy(saved))
    finally:
        user32.AttachThreadInput(me, target, False)
```

`main` 의 `key` 명령을 바꾼다:

```python
    elif cmd == "key":
        hwnd, _, _ = need_window(cfg)
        for name in args:
            mods, vk = parse_key(name)
            with held(hwnd, mods):
                user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
                time.sleep(0.05)
                user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
                time.sleep(0.1)
        print(f"키 {' '.join(args)}")
```

파일 머리 사용법의 `key` 줄을 바꾼다:

```
    uv run python scripts/gamedrive.py key VK [VK...]         # 가상 키 코드(16진/10진), 이름(ESC, ENTER, SPACE), 글자(S), 조합(CTRL+SHIFT+S)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `uv run pytest -q`
Expected: `77 passed`

- [ ] **Step 5: 게임에서 확인한다**

Task 10 의 `notes.md` 경로대로 World 2030 을 독일로 시작한 뒤:

```bash
uv run python scripts/gamedrive.py key CTRL+SHIFT+S
uv run python scripts/gamedrive.py shot build/verify/baseline/20-combo.png
```

Game Settings 화면이 열렸으면: `type cheat allowcheats` → `key ENTER` → `type cheat georgew` → `key ENTER` → `shot build/verify/baseline/21-combo-georgew.png`. 국고가 100억 늘었으면 성공이다.

열리지 않았으면(화면이 그대로면) **여기서 멈춘다.** 게임을 끄고(`stop`), 브랜치의 변경은 커밋하지 않고 `git -C E:/SR2030ToyBox restore scripts/gamedrive.py tests/test_gamedrive.py && git -C E:/SR2030ToyBox switch develop && git -C E:/SR2030ToyBox branch -D feat/gamedrive-combo-keys` 로 정리한다. `notes.md` 에 경로 `blocked` 와 시도한 것 세 가지를 적고 사용자에게 보고한다 — 남은 방법은 훅 DLL(`native/srhook`)에서 `GetAsyncKeyState` 를 가로채는 것인데, 한글화 모드를 다시 설치해야 해서 이 계획의 범위 밖이다. V1(Task 12)은 "막힘"으로 넘어가고 Task 13 부터 계속한다.

- [ ] **Step 6: (성공했을 때) 게임을 끄고 커밋, 푸시, PR, 머지**

```bash
uv run python scripts/gamedrive.py stop
git -C E:/SR2030ToyBox add scripts/gamedrive.py tests/test_gamedrive.py
git -C E:/SR2030ToyBox commit -m "feat: gamedrive key 에 조합키(CTRL+SHIFT+S) — 화면 밖 게임의 설정 화면 열기

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C E:/SR2030ToyBox push -u origin feat/gamedrive-combo-keys
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/gamedrive-combo-keys \
  --title "feat: gamedrive key 에 조합키" \
  --body "$(cat <<'EOF'
화면 밖 게임에 Ctrl+Shift+S(Game Settings — 치트 입력란이 있는 화면)를 보낸다.
게임 스레드의 키 상태표에 수정키를 눌린 것으로 적어 두고 키 메시지를 보낸다. 실제 키보드는 건드리지 않는다.

- 게임 안 확인: `key CTRL+SHIFT+S` 로 Game Settings 가 열리고 치트가 입력됨(빌드 21347933)
- `uv run pytest`: 77 passed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --repo game-mod-project/SR2030Toybox feat/gamedrive-combo-keys --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

`build/verify/baseline/notes.md` 의 치트 입력 경로를 `combo: key CTRL+SHIFT+S → 입력란 클릭(좌표) → type … → key ENTER` 로 고친다.

### Task 12: V1 — 내장 치트 91개 시험 (게임, 코드 변경 없음)

**Task 10 의 경로가 `blocked` 면 이 Task 는 하지 않는다.** `build/verify/cheats/results.csv` 에 91행을 모두 `not-run`, 관찰 `입력 경로 막힘` 으로 쓰고 Task 13 으로 간다.

**Files:**
- Create (git 제외): `build/verify/cheats/results.csv`, `build/verify/cheats/<묶음>-<명령>-before.png` · `-after.png`

**Interfaces:**
- Consumes: `build/verify/baseline/notes.md` (새 게임 시작 경로, 치트 입력 경로), `docs/07-cheats.md` (묶음과 [위키] 효과)
- Produces: `build/verify/cheats/results.csv` — UTF-8 BOM, 머리 행 `command,args,batch,status,observation,before,after`, 명령당 한 행(91행).
  `status` 는 `effect`(효과를 봄) / `no-reaction`(넣었는데 변화 없음) / `not-run`(넣지 않음 — `observation` 에 이유) 중 하나

- [ ] **Step 1: 지역 번호를 찾아 둔다**

지역을 인자로 받는 치트에 쓸 번호다. 독일(1499)의 이웃 둘을 고른다:

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
grep -a -B2 'regionname "Denmark"\|regionname "Poland"' "$G/Maps/W2030.CVP" | grep -a '&&CVP\|regionname' | tr -d '\r'
```

Expected: `&&CVP <번호>` 와 `regionname` 이 번갈아 나온다. 두 번호를 `results.csv` 를 쓸 때 `args` 에 적는다.

- [ ] **Step 2: 묶음마다 백그라운드 에이전트에 맡긴다**

묶음은 `docs/07-cheats.md` 의 일곱 개다(A 경제·자원·연구·생산 14 / B 국가·정치·인구 12 / C 외교 16 / D 군사·부대·정보 14 / E 진행·화면·이벤트 13 / F Galactic Ruler 17 / G 개발용·위험 3). **한 번에 한 묶음만** 돌린다(게임은 하나만 뜬다). 묶음 순서는 A → B → C → D → E → F → G. 에이전트가 도는 동안 작업 브랜치를 바꾸지 않는다.

지시문(묶음마다 `<…>` 를 채운다):

```
이 작업(Task 12 의 묶음 <A>)만 수행하라.
끝나면 보고하고 정지하라. 다른 Task로 진행하지 말라.
명세에 없는 코드를 추측·즉흥(improvise) 구현하지 말라. 명세가 부족하면 멈추고 `NEEDS_CONTEXT`로 보고하라.
모든 git/파일 명령에 절대경로 또는 `-C E:/SR2030ToyBox` 를 사용하라. `cd` 후 상대경로로 후속 명령을 내지 말 것 —
에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다. 저장소의 파일을 고치거나 git 명령으로 상태를 바꾸지 말라.

목표: Supreme Ruler 2030 의 내장 치트 <N>개가 게임에서 무엇을 하는지 관찰해 표로 적는다.

읽을 것: E:/SR2030ToyBox/CLAUDE.md 의 "명령" 절(게임 조작 규칙), E:/SR2030ToyBox/build/verify/baseline/notes.md
(새 게임 시작 경로와 치트 입력 경로 — 그대로 따른다), E:/SR2030ToyBox/docs/07-cheats.md 의 "<묶음 제목>" 표(예상 효과).

절차:
1. `uv run --project E:/SR2030ToyBox python E:/SR2030ToyBox/scripts/gamedrive.py status` 가 "프로세스: 없음" 인지 본다.
   "(이 도구가 띄운 것 아님)" 이 보이면 아무것도 하지 말고 그대로 보고하고 정지하라.
2. 게임을 띄워(start, 25초 대기) notes.md 의 경로로 World 2030 을 독일로 시작하고 일시 정지 상태로 둔다.
3. notes.md 의 입력 경로로 `cheat allowcheats` 를 넣는다.
4. 명령마다: 효과가 보일 화면을 연다 → shot <before> → 치트 입력 → (필요하면 하루 진행) → shot <after> → 차이를 한 줄로 적는다.
   - 화면 이름: E:/SR2030ToyBox/build/verify/cheats/<묶음>-<명령>-before.png / -after.png (`!` `=` 는 빼고 적는다)
   - 변화가 안 보이면 다른 화면 한 곳을 더 보고, 그래도 없으면 no-reaction.
   - 인자가 필요한 명령은 인자 없이 한 번, 인자와 함께 한 번 넣는다. 지역 번호: <Step 1 의 두 번호>.
5. 묶음의 마지막 명령까지 끝나면 게임을 끈다(stop). 저장하지 않는다. status 로 "프로세스: 없음" 을 확인한다.
6. 결과를 E:/SR2030ToyBox/build/verify/cheats/results-<묶음>.csv 에 쓴다(UTF-8 BOM, LF):
   command,args,batch,status,observation,before,after
   command 는 `cheat treasury` 꼴(인자는 args 에). status 는 effect / no-reaction / not-run.
   observation 은 본 것을 한 줄로(수치가 있으면 전후 수치).

명령: <묶음의 명령 목록, 넣을 순서대로>

금지: `cheat resettutorial` 은 어떤 경우에도 넣지 않는다. 게임을 저장하지 않는다. 게임 폴더의 파일을 바꾸지 않는다.
게임이 멈추거나 꺼지면 그 명령을 observation 에 "게임이 멈춤/꺼짐" 으로 적고, 게임을 다시 띄워 다음 명령부터 이어 간다
(다시 띄우면 `cheat allowcheats` 부터).

보고: 명령별 status 요약, 예상(위키)과 다른 것, 쓰지 못한 것과 이유.
```

묶음별로 덧붙일 것:

- **A**: 넣을 순서 `treasury 1000` `georgew` `georgeww` `trumpme` `products 1000` `branson` `bezos` `gates` `technology 120` `finalexam` `e=mc2` `onedaybuild` `breakground` `allunit`. 볼 곳: 국고(위쪽 띠), 물자 재고(자원 화면), 연구 화면, 생산 목록. `onedaybuild` `breakground` 는 부대·시설을 하나 주문하고 하루를 진행해 본다.
- **B**: 넣을 순서 `populate` `depopulate` `approval` `democracy` `novichok <지역>` `revolt <지역>` `colonize <지역>` `liberate <지역>` `annex <지역>` `putin` `reviveall` `becomeregion <지역>`. 볼 곳: 인구·지지율(국가 정보), 지도의 국경. 지도를 바꾸는 것(`annex` 부터)은 뒤에 둔다.
- **C**: 넣을 순서 `love <지역>` `hate <지역>` `neutral <지역>` `treaty` `mutualdef` `dipaccept` `shelovesme` `shelovesmenot` `moreoffers` `sanction` `wmsanction` `fight <지역>` `saddam` `saddamme` `peace` `worldwar`. 볼 곳: 외교 화면의 관계 수치와 조약 목록. `treaty` `mutualdef` `fight` 는 이웃 지역의 땅을 눌러 고른 채로 넣는다. `worldwar` 는 맨 끝.
- **D**: 넣을 순서 `unitdesign` `spawnunit` `damage` `stranded` `nomove` `007` `maxsat` `satellite` `panic` `beammeup` `launchattack` `selloffunits` `darran` `darren`. 볼 곳: 고른 부대의 정보 창, 생산 가능 목록, 위성 화면. `damage` `stranded` 는 부대 하나를 고른 채로 넣는다. `darren` 은 모든 AI 가 선전포고하므로 맨 끝.
- **E**: 넣을 순서 `airequest` `eventnow` `eventclear` `blueskies` `speedlock` `increaseday 3` `endday` (다시 `endday` 로 끔) `fullmapshow` (다시 넣어 끔) `noaiinit` `fullaiinit` `devcheat` `done` `instantwin`. 볼 곳: 날짜, 속도 표시, 화면 전체. `instantwin` 은 맨 끝.
- **F**: 넣을 순서는 문서의 순서. **반응 여부만** 적는다 — 넣기 전후 화면이 같으면 `no-reaction`, 다르면 `effect` 와 본 것. 화면을 따로 찾아다니지 않는다.
- **G**: 넣을 순서 `killeveryone` `stresstest` `meshtest`. 명령마다 게임을 새로 띄워 하나씩 넣는다. 60초 안에 화면이 돌아오지 않으면 `stop` 하고 "게임이 멈춤"으로 적는다.

- [ ] **Step 3: 묶음이 끝날 때마다 컨트롤러가 직접 확인한다**

```bash
uv run python scripts/gamedrive.py status
git -C E:/SR2030ToyBox status --short
git -C E:/SR2030ToyBox branch --show-current
git -C E:/SR2030ToyBox log --oneline -1
```

Expected: `프로세스: 없음`, 바뀐 파일 없음, 브랜치와 마지막 커밋이 맡기기 전과 같다. 게임이 떠 있으면 `stop` 한다. 저장소가 바뀌어 있으면 그 변경을 받아들이지 않는다(`git restore`).

결과 파일의 행 가운데 셋을 골라 before/after 화면을 직접 열어 `observation` 과 맞는지 본다. 맞지 않으면 그 묶음을 다시 맡긴다.

- [ ] **Step 4: 결과를 하나로 합치고 빠진 것을 채운다**

```bash
uv run python -c "
import csv, pathlib, re
from srkit import config
d = pathlib.Path('build/verify/cheats')
rows = []
for p in sorted(d.glob('results-*.csv')):
    rows += list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))
for r in rows:
    r['command'] = 'cheat ' + r['command'].removeprefix('cheat ').strip()
exe = (config.load().game_dir / 'SupremeRuler2030.exe').read_bytes()
names = {m.decode() for m in re.findall(rb'cheat ([!-~]{1,20})', exe)}
seen = {r['command'].removeprefix('cheat ').strip() for r in rows}
fixed = {'allowcheats': ('effect', '치트 모드가 켜짐 — 묶음마다 처음에 넣었다'), 'resettutorial': ('not-run', 'Steam 업적을 지운다고 되어 있어 넣지 않음')}
for name in sorted(names - seen):
    status, why = fixed.get(name, ('not-run', '시험 묶음에 없었음'))
    rows.append({'command': 'cheat ' + name, 'args': '', 'batch': '-', 'status': status, 'observation': why, 'before': '', 'after': ''})
with (d / 'results.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['command', 'args', 'batch', 'status', 'observation', 'before', 'after'], lineterminator='\n')
    w.writeheader(); w.writerows(rows)
cmds = {r['command'] for r in rows}
bad = [r['command'] for r in rows if r['status'] not in ('effect', 'no-reaction', 'not-run') or not r['observation']]
print(len(cmds), '개 명령,', '시험 묶음에 없었음:', sorted(r['command'] for r in rows if r['observation'] == '시험 묶음에 없었음'), '잘못된 행:', bad)
"
```

Expected: `91 개 명령, 시험 묶음에 없었음: [] 잘못된 행: []`. 인자 없이·인자와 함께 두 번 넣은 명령은 행이 둘이어도 된다(명령 수가 91 이면 된다).

### Task 13: V2 — 장비 값은 캐시 재생성 없이 반영되는가 (게임, 코드 변경 없음)

**Files:**
- Create (git 제외): `build/probe-unit/`, `build/cache-orig/`, `build/verify/v2/` (`*.sha256`, `*.png`, `result.md`)

**Interfaces:**
- Consumes: `srkit probe` (Task 9), `srkit deploy` / `undeploy`, `build/verify/baseline/notes.md` (시작 경로, `Leopard 2A7+` 의 기준 비용과 읽는 위치, "Force Recache For Modding" 의 위치)
- Produces: `build/verify/v2/result.md` — 첫 줄이 결론 한 줄: `캐시 무관` / `재생성 필요 — 로비 옵션으로 됨` / `재생성 필요 — ignorecache 로 됨` / `확정 못 함` 중 하나. 그 아래에 시도한 것, 화면 파일, 캐시 파일이 바뀌었는지. Task 14 · 15 가 "재생성 필요" 여부를 여기서 읽고, Task 16 이 문서로 옮긴다.

- [ ] **Step 1: 게임이 꺼져 있는지 확인한다**

Run: `uv run python scripts/gamedrive.py status`
Expected: `프로세스: 없음`

- [ ] **Step 2: 원본의 해시와 캐시 사본을 남긴다**

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
mkdir -p build/verify/v2 build/cache-orig/Cache
( cd "$G" && sha256sum Maps/DATA/DEFAULT.UNIT Sandbox/World2030.scenario Cache/*.SAV ) > build/verify/v2/before.sha256
cp "$G/Cache/W2030.SAV" build/cache-orig/Cache/W2030.SAV
cat build/verify/v2/before.sha256
```

Expected: 9줄(파일 둘 + 캐시 일곱). `cp` 는 게임 폴더를 읽기만 한다.

- [ ] **Step 3: 시험 모드를 만들고 미리 본다**

`Leopard 2A7+` 의 비용을 `6` 에서 `66` 으로 바꾼다(Task 10 에서 대상이 `Leopard 2A6` 로 바뀌었으면 기준 문자열을 `2342, "Leopard 2A6"`, 바꿀 문자열을 `258, 1780, 1.8, 5.3, ` → `258, 1780, 1.8, 53, ` 으로 한다).

```bash
uv run srkit probe unit Maps/DATA/DEFAULT.UNIT '205, 1781, 1.9, 6, ' '205, 1781, 1.9, 66, ' --after '2413, "Leopard 2A7+"'
uv run srkit deploy probe-unit
```

Expected: 미리보기가 정확히 두 줄 — `교체(원본 백업): Maps/DATA/DEFAULT.UNIT` 와 `미리보기(--apply 로 실행): 1개 파일 → …`. 다른 줄이 있으면 멈춘다(다른 모드와 파일이 겹친다).

- [ ] **Step 4: 설치한다**

Run: `uv run srkit deploy probe-unit --apply`
Expected: `설치 완료: 1개 파일 → …`. "게임이 실행 중입니다" 가 나오면 게임이 꺼질 때까지 기다린다.

- [ ] **Step 5: 재생성 없이 본다**

게임을 띄워(`start`, 25초 대기) `notes.md` 의 경로로 World 2030 을 독일로 시작한다. 로비 설정은 건드리지 않는다. `notes.md` 의 위치에서 `Leopard 2A7+` 의 비용을 읽는다.

```bash
uv run python scripts/gamedrive.py shot build/verify/v2/a-no-recache.png
uv run python scripts/gamedrive.py stop
```

- 비용이 `66` (기준의 11배) → 결론 `캐시 무관`. Step 8 로.
- 비용이 기준 그대로 → Step 6.

- [ ] **Step 6: 재생성 방법 ① — 로비 옵션**

게임을 다시 띄워 로비 설정에서 "Force Recache For Modding" 을 켜고(`notes.md` 의 좌표) 시작한다. 로딩이 평소보다 길 수 있다 — `shot` 이 로딩 화면이면 15초씩 기다리며 다시 찍는다(최대 5분).

```bash
uv run python scripts/gamedrive.py shot build/verify/v2/b-lobby-recache.png
uv run python scripts/gamedrive.py stop
```

- 비용이 `66` → 결론 `재생성 필요 — 로비 옵션으로 됨`. Step 8 로.
- 그대로 → Step 7.

- [ ] **Step 7: 재생성 방법 ② — `ignorecache`**

시나리오의 `&&GMC` 끝에 `ignorecache: 1` 을 더한 시험 모드를 함께 설치한다(실행 파일에만 있는 키 — 효과는 추정):

```bash
uv run srkit probe nocache Sandbox/World2030.scenario 'bzombies:     0' $'bzombies:     0\r\nignorecache:    1'
uv run srkit deploy probe-nocache
uv run srkit deploy probe-nocache --apply
```

Expected: 미리보기가 `교체(원본 백업): Sandbox/World2030.scenario` 한 줄과 요약 한 줄.

게임을 띄워 로비 옵션은 끈 채로 시작해 비용을 읽는다.

```bash
uv run python scripts/gamedrive.py shot build/verify/v2/c-ignorecache.png
uv run python scripts/gamedrive.py stop
```

- 비용이 `66` → 결론 `재생성 필요 — ignorecache 로 됨`.
- 그대로 → 결론 `확정 못 함`. 방법은 여기까지만 시도한다(명세의 한도).

- [ ] **Step 8: 되돌린다**

```bash
uv run python scripts/gamedrive.py status
uv run srkit undeploy probe-unit --apply
uv run srkit undeploy probe-nocache --apply
```

Expected: `프로세스: 없음`, `복원: Maps/DATA/DEFAULT.UNIT` 과 `제거 완료`. `probe-nocache` 를 설치하지 않았으면 둘째 명령은 `설치 내역이 없습니다: probe-nocache` 를 낸다(정상).

- [ ] **Step 9: 게임 폴더가 원래대로인지 확인한다**

```bash
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
( cd "$G" && sha256sum -c "/e/SR2030ToyBox/build/verify/v2/before.sha256" )
```

Expected: 9줄 모두 `OK`.

`Cache/W2030.SAV: FAILED` 면 게임이 캐시를 고쳐 쓴 것이다. 원본으로 되돌린다:

```bash
uv run srkit deploy cache-orig
uv run srkit deploy cache-orig --apply
( cd "$G" && sha256sum -c "/e/SR2030ToyBox/build/verify/v2/before.sha256" )
rm -rf build/.deploy/cache-orig
```

Expected: 미리보기가 `교체(원본 백업): Cache/W2030.SAV` 한 줄, 다시 확인하면 9줄 모두 `OK`. 마지막 줄은 설치 내역만 지운다 — 남겨 두면 나중에 `undeploy cache-orig` 가 고쳐진 캐시를 되살린다.

`DEFAULT.UNIT` 이나 `World2030.scenario` 가 `FAILED` 면 멈추고 사용자에게 보고한다(`undeploy` 가 실패했다는 뜻이다).

- [ ] **Step 10: `build/verify/v2/result.md` 를 쓴다**

첫 줄에 결론, 그 아래에: 단계별로 본 비용과 화면 파일, 로딩에 걸린 시간, `Cache\W2030.SAV` 가 바뀌었는지(바뀌었으면 어느 단계 뒤에), 한글화 모드가 설치된 상태였는지.

### Task 14: V3 — 시나리오 설정은 반영되는가 (게임, 코드 변경 없음)

**Files:**
- Create (git 제외): `build/probe-funds/`, `build/verify/v3/` (`before.sha256`, `*.png`, `result.md`)

**Interfaces:**
- Consumes: `srkit probe`, `srkit deploy` / `undeploy`, `notes.md` (Initial Funds 기본값, 시작 국고), `build/verify/v2/result.md` (재생성이 필요했는지)
- Produces: `build/verify/v3/result.md` — 첫 줄이 `반영됨` / `재생성 뒤 반영됨` / `반영 안 됨` 중 하나. 그 아래에 로비에 보인 값과 시작 국고의 전후

- [ ] **Step 1: 게임이 꺼져 있는지 확인하고 해시를 남긴다**

```bash
uv run python scripts/gamedrive.py status
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
mkdir -p build/verify/v3
( cd "$G" && sha256sum Sandbox/World2030.scenario Cache/*.SAV ) > build/verify/v3/before.sha256
```

Expected: `프로세스: 없음`, 해시 8줄

- [ ] **Step 2: 시험 모드를 만들고 미리 보고 설치한다**

초기 자금을 `2`("Default")에서 `3`("High")로 바꾼다(`Variables.ini` 의 `setinitialfunds`: "No New Bonds", "Low", "Default", "High").

```bash
uv run srkit probe funds Sandbox/World2030.scenario 'initialfunds:   2' 'initialfunds:   3'
uv run srkit deploy probe-funds
uv run srkit deploy probe-funds --apply
```

Expected: 미리보기가 `교체(원본 백업): Sandbox/World2030.scenario` 한 줄과 요약 한 줄.

- [ ] **Step 3: 로비와 시작 국고를 본다**

게임을 띄워 `notes.md` 의 경로로 로비 설정까지 간다.

```bash
uv run python scripts/gamedrive.py shot build/verify/v3/a-lobby.png
```

Initial Funds 가 "High" 로 보이는지 적는다. 그대로 시작해 국고를 읽는다.

```bash
uv run python scripts/gamedrive.py shot build/verify/v3/b-treasury.png
uv run python scripts/gamedrive.py stop
```

- 로비가 "High" 이고 국고가 기준보다 많다 → `반영됨`.
- 로비도 국고도 기준 그대로이고 V2 의 결론이 "재생성 필요" 였다 → V2 에서 통한 방법으로 한 번 더 본다(`c-recache.png`). 바뀌면 `재생성 뒤 반영됨`.
- 그래도 그대로 → `반영 안 됨`.

- [ ] **Step 4: 되돌리고 확인한다**

```bash
uv run srkit undeploy probe-funds --apply
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
( cd "$G" && sha256sum -c "/e/SR2030ToyBox/build/verify/v3/before.sha256" )
```

Expected: 8줄 모두 `OK`. `Cache/W2030.SAV: FAILED` 면 Task 13 Step 9 의 `cache-orig` 복원을 한다.

- [ ] **Step 5: `build/verify/v3/result.md` 를 쓴다**

### Task 15: V4 — 지역 값은 반영되는가 (게임, 코드 변경 없음)

**Files:**
- Create (git 제외): `build/probe-gdpc/`, `build/verify/v4/` (`before.sha256`, `*.png`, `result.md`)

**Interfaces:**
- Consumes: `srkit probe`, `srkit deploy` / `undeploy`, `notes.md` (GDP/c 의 기준 값과 읽는 위치), `build/verify/v2/result.md`
- Produces: `build/verify/v4/result.md` — 첫 줄이 `반영됨` / `재생성 뒤 반영됨` / `반영 안 됨` 중 하나. 그 아래에 GDP/c 의 전후

- [ ] **Step 1: 게임이 꺼져 있는지 확인하고 해시를 남긴다**

```bash
uv run python scripts/gamedrive.py status
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
mkdir -p build/verify/v4
( cd "$G" && sha256sum Maps/W2030.CVP Cache/*.SAV ) > build/verify/v4/before.sha256
```

Expected: `프로세스: 없음`, 해시 8줄

- [ ] **Step 2: 시험 모드를 만들고 미리 보고 설치한다**

독일(`&&CVP 1499`)의 `gdpc` 를 `51203` 에서 `99999` 로 바꾼다.

```bash
uv run srkit probe gdpc Maps/W2030.CVP 'gdpc 51203' 'gdpc 99999' --after '&&CVP 1499'
uv run srkit deploy probe-gdpc
uv run srkit deploy probe-gdpc --apply
```

Expected: 미리보기가 `교체(원본 백업): Maps/W2030.CVP` 한 줄과 요약 한 줄.

- [ ] **Step 3: GDP/c 를 본다**

게임을 띄워 `notes.md` 의 경로로 World 2030 을 독일로 시작하고, `notes.md` 의 위치에서 GDP/c 를 읽는다.

```bash
uv run python scripts/gamedrive.py shot build/verify/v4/a-gdpc.png
uv run python scripts/gamedrive.py stop
```

- 기준의 약 두 배(`99999` 근처) → `반영됨`.
- 기준 그대로이고 V2 의 결론이 "재생성 필요" 였다 → V2 에서 통한 방법으로 한 번 더 본다(`b-recache.png`). 바뀌면 `재생성 뒤 반영됨`.
- 그래도 그대로 → `반영 안 됨`.

`#ifset 0x01`(CVP 로드) 단계의 파일이라 캐시와의 관계가 `DEFAULT.UNIT` 과 다를 수 있다 — V2 와 결과가 다르면 그 사실을 `result.md` 에 분명히 적는다.

- [ ] **Step 4: 되돌리고 확인한다**

```bash
uv run srkit undeploy probe-gdpc --apply
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
( cd "$G" && sha256sum -c "/e/SR2030ToyBox/build/verify/v4/before.sha256" )
uv run srkit deploy korean
```

Expected: 8줄 모두 `OK`(캐시가 `FAILED` 면 Task 13 Step 9 의 복원). 마지막 명령(한글화 모드 미리보기)은 `미리보기(--apply 로 실행): 0개 파일` — 실험이 한글화 설치를 건드리지 않았다는 확인이다.

- [ ] **Step 5: `build/verify/v4/result.md` 를 쓴다**

---

## Phase 4 — 결과 반영과 제작 계획서 (브랜치 `docs/cheat-mod-verify`)

시작: 게임이 꺼져 있는지 확인(`status`)한 뒤 `git -C E:/SR2030ToyBox switch -c docs/cheat-mod-verify develop`

### Task 16: 검증 결과를 문서에 반영한다

**Files:**
- Modify: `docs/07-cheats.md` (검증 열, 넣는 법), `docs/06-data-reference.md` (캐시 절), `docs/01-game-structure.md:75-76` (캐시 [추정] 두 줄)
- 읽는 것: `build/verify/cheats/results.csv`, `build/verify/baseline/notes.md`, `build/verify/v2/result.md` `v3/result.md` `v4/result.md`

**Interfaces:**
- Consumes: Task 10 · 12 ~ 15 의 산출물
- Produces: `docs/07` 의 검증 열이 `[확인: 효과]` / `[확인: 반응 없음]` / `[미시험: <이유>]` 중 하나로 끝난다. `docs/06` 과 `docs/01` 의 캐시 서술이 V2 의 결론과 같다.

- [ ] **Step 1: `docs/07` 의 "넣는 법"을 실제로 통한 방법으로 고친다**

`notes.md` 의 치트 입력 경로를 [확인]으로 적는다(채팅 창인지, Game Settings 화면인지, 입력란이 어디인지). 치트를 켰을 때 뜨는 문구와, 업적 표시를 봤으면 그것도 적는다(못 봤으면 "[미확인] 치트가 업적을 막는지"). 경로가 `blocked` 였으면 "화면 밖 게임에서는 넣지 못했다"와 시도한 세 가지를 적는다.

- [ ] **Step 2: `docs/07` 의 표를 결과로 고친다**

`results.csv` 의 행마다 해당 명령의 "효과"와 "검증"을 고친다:

- `effect` → 검증 `[확인: 효과]`, 효과 칸은 `observation` 으로 바꾼다(위키 설명과 다르면 "위키는 …라고 하나 …였다"로 적는다). 인자를 알아냈으면 "인자" 칸도 고친다.
- `no-reaction` → 검증 `[확인: 반응 없음]`, 효과 칸에 "넣어도 변화가 보이지 않았다"와 본 화면을 적는다.
- `not-run` → 검증 `[미시험: <observation>]`, 효과 칸은 위키 설명을 [위키]로 남긴다.

"대상" 칸(플레이어만 / 모든 지역)은 관찰로 확인된 것만 [확인]으로 바꾼다.

- [ ] **Step 3: 모든 명령에 검증 상태가 붙었는지 확인한다**

```bash
uv run python -c "
import re, pathlib
from srkit import config
tick = chr(96)
exe = (config.load().game_dir / 'SupremeRuler2030.exe').read_bytes()
names = sorted({m.decode() for m in re.findall(rb'cheat ([!-~]{1,20})', exe)} - {'allowcheats'})
doc = pathlib.Path('docs/07-cheats.md').read_text(encoding='utf-8')
rows = {m.group(1): m.group(0) for m in re.finditer(r'^\| ' + tick + r'cheat (\S+)' + tick + r' \|.*$', doc, re.M)}
print('표에 없는 명령:', [n for n in names if n not in rows])
print('검증 상태가 없는 명령:', [n for n in names if n in rows and not re.search(r'\[(확인: 효과|확인: 반응 없음|미시험: [^\]]+)\]', rows[n])])
"
```

Expected: 두 줄 모두 `[]` (`allowcheats` 는 "넣는 법"에서 다루므로 뺀다)

- [ ] **Step 4: 캐시 서술을 고친다**

`docs/06-data-reference.md` 의 "로딩 단계와 캐시" 끝에 넣어 둔 `> **[추정]** …` 줄을 V2 ~ V4 의 결론으로 바꾼다: 무엇을 바꿨고, 재생성 없이 반영됐는지, 필요했다면 어느 방법이 통했는지, 게임이 캐시 파일을 고쳐 쓰는지. 섹션별 로딩 단계 표에 "수정이 반영되려면" 열을 더해 V2(`0x02` 단계) · V3(조건 없음) · V4(`0x01` 단계)의 결과를 넣는다 — 실험하지 않은 단계는 [추정]으로 남긴다.

`docs/01-game-structure.md` 의 두 줄(75 ~ 76행)을 고친다:

```markdown
- `Cache\*.SAV` 는 원본 데이터로 미리 만든 결과다. **원본 데이터(`DEFAULT.UNIT` 등)를 고치는 모드는 캐시 재생성이 필요하다.** [추정: 단계 구조상]
- 현지화 텍스트는 캐시 뒤에 읽으므로 언어 추가는 캐시와 무관하다. [추정: 언어가 6개인데 캐시는 시나리오당 1개]
```

첫 줄은 V2 의 결론으로 다시 쓰고 `[확인: 게임 12.1.1360 / build 21347933, docs/06]` 을 붙인다(결론이 `확정 못 함` 이면 [추정]을 그대로 두고 "두 방법을 시도했으나 확정하지 못했다 — docs/06"을 덧붙인다). 둘째 줄은 이 계획에서 검증하지 않았으므로 그대로 둔다.

- [ ] **Step 5: 커밋**

```bash
git -C E:/SR2030ToyBox add docs/07-cheats.md docs/06-data-reference.md docs/01-game-structure.md
git -C E:/SR2030ToyBox commit -m "docs: 게임 안 검증 결과 반영 — 내장 치트의 실제 효과, 캐시와 데이터 수정

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 17: `docs/09-cheat-mod-plan.md` — 분류표와 제작 계획, PR

**Files:**
- Create: `docs/09-cheat-mod-plan.md`
- Modify: `README.md` (구조 목록, 현재 상태)
- 읽는 것: `docs/05` ~ `docs/08`, `build/verify/*/result.md`

**Interfaces:**
- Consumes: `docs/05` 의 영역 이름, `docs/06` 의 키·열 이름과 캐시 결론, `docs/07` 의 검증된 치트, `docs/08` 의 Workshop 항목
- Produces: `docs/09-cheat-mod-plan.md` — 첫 줄 제목이 `# Supreme Ruler 2030 치트/모드 제작 계획`

- [ ] **Step 1: 뼈대를 쓴다**

```markdown
# Supreme Ruler 2030 치트/모드 제작 계획

조사 기준: Steam appid `2093410`, build `21347933`, 2026-10-06. 목적: 내 싱글플레이에서 쓸 치트 수단.
근거 문서: [05 게임 구조](05-game-systems.md) · [06 데이터 참조](06-data-reference.md) · [07 내장 치트](07-cheats.md) · [08 Workshop 조사](08-workshop-survey.md)

표기: **[확인]** 파일·실행 파일·게임 안에서 직접 확인, **[추정]** 정황으로 판단, **[위키]** 공식 위키에 있으나 이 빌드에서 미확인.

## 결론
## 수단 여섯 가지
## 원안 예시 아홉 개의 결론
## 분류표
## 만들 것
## 만들지 않을 것
## 로드맵
## 미해결 문제
## 검증 기록
```

- [ ] **Step 2: "결론"과 "수단 여섯 가지"를 쓴다**

"결론"은 다섯 줄 안쪽으로, 읽는 사람이 이것만 봐도 되게 쓴다: 무엇은 내장 치트로 끝나고, 무엇을 만들어야 하고, 무엇은 Workshop 에 있고, 무엇이 아직 막혀 있는지.

"수단 여섯 가지"는 표 하나다 — 내장 치트 / 시나리오 설정(`&&GMC`) / 데이터 표 / 실행 중 훅 / 세이브 편집 / Workshop 기존 모드. 열: 수단, 적용 시점(진행 중 · 새 게임), 대상(플레이어만 · 모든 지역), Workshop 배포 가능 여부, 캐시 재생성 필요 여부(V2 ~ V4 의 결과), 검증 상태. "실행 중 훅"과 "세이브 편집"은 이 조사에서 다루지 않았으므로 전부 [추정]이고 그렇게 적는다.

- [ ] **Step 3: "원안 예시 아홉 개의 결론"을 쓴다**

```markdown
| 원하는 것 | 가장 쉬운 수단 | 위치 | 검증 | 결론 |
|---|---|---|---|---|
| 돈 | 내장 치트 | `cheat treasury` | [확인: 효과] | 그대로 쓴다 |
```

행은 정확히 아홉 개, 첫 칸은 이 이름 그대로: 돈, 자원, 연구, 국가 관계, 군사력, 장비 생산, 부대 스탯, 인구, GDP. "결론"은 `그대로 쓴다` / `만든다` / `안 만든다` 중 하나로 시작하고, `만든다` 와 `안 만든다` 는 이유를 덧붙인다. 내장 치트가 `[확인: 효과]` 가 아니면 "그대로 쓴다"라고 쓰지 않는다 — `[위키]` 면 "그대로 쓴다(게임 확인 필요)"로 적는다.

- [ ] **Step 4: "분류표"를 쓴다**

영역 12개를 소제목으로 두고, 영역마다 표 하나:

```markdown
| 항목 | 수단 | 위치 | 적용 시점 | 대상 | 검증 | 결론 |
|---|---|---|---|---|---|---|
| 국고 | 내장 치트 | `cheat treasury N` | 진행 중 | 플레이어 | [확인: 효과] | 그대로 쓴다 |
| 국고 | 데이터 표 | `Maps\W2030.CVP` `&&CVP` `treasury` | 새 게임 | 지정한 지역 | [추정] | 안 만든다 — 치트로 충분 |
```

한 행이 "항목 하나를 수단 하나로 바꾸는 방법"이다. 같은 항목이 수단마다 행을 가진다. 채우는 순서: ① `docs/07` 의 치트를 영역에 넣는다(91개 전부 — 효과가 없던 것은 "결론: 쓸 수 없다") ② `docs/06` 의 키 섹션 키와, 열을 옮긴 표 섹션의 열 가운데 `docs/05` 가 그 영역에 대응시킨 것을 넣는다 ③ `docs/06` 의 "실행 파일에만 있는 이름" 가운데 굵게 표시한 것을 [추정]으로 넣는다 ④ `docs/08` 의 항목을 "Workshop 기존 모드" 수단으로 넣는다. 검증 칸은 근거 문서의 표기를 그대로 옮긴다 — 여기서 올려 적지 않는다.

- [ ] **Step 5: "만들 것" · "만들지 않을 것" · "로드맵" · "미해결 문제" · "검증 기록"을 쓴다**

- "만들 것": 분류표에서 결론이 `만든다` 인 것을 모드 단위로 묶는다. 모드마다: 무엇을 바꾸나, 건드리는 파일·키, 유형(MODS/MAPS — `docs/02`), 캐시 재생성이 필요한가, 먼저 확인할 것. `mods/_template` 로 시작한다는 것과 `srkit probe` → `deploy` 로 시험한다는 것을 적는다.
- "만들지 않을 것": 내장 치트나 Workshop 항목으로 되는 것, 그리고 범위 밖(트레이너, 세이브 편집기, 멀티플레이)을 이유와 함께.
- "로드맵": "만들 것"을 순서대로. 각 단계는 별도의 설계 → 계획 → 구현 주기라고 적는다.
- "미해결 문제": V1 ~ V4 에서 확정하지 못한 것(`확정 못 함`, `blocked`, `[미시험]`), 실행 파일에만 있는 키의 효과, 치트와 업적.
- "검증 기록": V1 ~ V4 마다 한 단락 — 무엇을 했고, 무엇을 봤고, 근거가 어디 있는지(`build/verify/` 는 저장소에 없으므로 "로컬 산출물"이라고 적는다). 게임 폴더를 실험 뒤 원래대로 되돌렸고 해시로 확인했다는 것, 캐시 파일이 바뀌었는지도 적는다.

- [ ] **Step 6: 확인한다**

```bash
uv run python -c "
import re, pathlib
doc = pathlib.Path('docs/09-cheat-mod-plan.md').read_text(encoding='utf-8')
print('제목:', doc.splitlines()[0])
sec = doc.split('## 원안 예시 아홉 개의 결론')[1].split('\n## ')[0]
rows = {c[0]: c[-1] for c in ([x.strip() for x in line.strip().strip('|').split('|')] for line in sec.splitlines() if line.startswith('|'))}
want = ['돈', '자원', '연구', '국가 관계', '군사력', '장비 생산', '부대 스탯', '인구', 'GDP']
print('빠진 예시:', [w for w in want if w not in rows])
print('결론이 없는 예시:', [w for w in want if w in rows and not rows[w].startswith(('그대로 쓴다', '만든다', '안 만든다'))])
areas = ['국가', '경제', '자원', '산업', '연구', '정치', '외교', '군사', '부대', '장비', '전쟁', 'AI']
table = doc.split('## 분류표')[1].split('\n## ')[0]
print('분류표에 없는 영역:', [a for a in areas if '### ' + a not in table])
print('남은 자리 표시:', re.findall(r'TBD|TODO|…\s*\|', doc)[:5])
"
```

Expected: `제목: # Supreme Ruler 2030 치트/모드 제작 계획`, 나머지 네 줄은 `[]`

- [ ] **Step 7: README 를 고친다**

"구조" 코드 블록의 `04-korean-localization.md …` 줄 아래에 더한다:

```
  05-game-systems.md            게임 구조: 12개 영역과 데이터의 대응
  06-data-reference.md          데이터 참조: 섹션·키·열 (srkit inventory 산출물 기준)
  07-cheats.md                  내장 치트표 (게임 안 검증 포함)
  08-workshop-survey.md         Workshop 기존 모드 조사
  09-cheat-mod-plan.md          치트/모드 제작 계획
```

"현재 상태" 절 끝에 한 단락을 더한다 — 치트·모드 조사가 끝났고, 내 플레이용 치트는 무엇으로 되는지 한 문장(`docs/09` 의 "결론"에서), 그리고 [docs/09](docs/09-cheat-mod-plan.md) 링크. 게임에서 확인하지 않은 것을 "된다"고 쓰지 않는다.

- [ ] **Step 8: 커밋, 푸시, PR, 머지**

```bash
git -C E:/SR2030ToyBox add docs/09-cheat-mod-plan.md README.md
git -C E:/SR2030ToyBox commit -m "docs: Supreme Ruler 2030 치트/모드 제작 계획 — 분류표와 로드맵

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
uv run pytest -q
git -C E:/SR2030ToyBox push -u origin docs/cheat-mod-verify
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/cheat-mod-verify \
  --title "docs: 치트/모드 제작 계획과 게임 안 검증 결과" \
  --body "$(cat <<'EOF'
게임 안 검증(V1 내장 치트, V2 캐시, V3 시나리오 설정, V4 지역 값)의 결과를 문서에 반영하고,
수정 가능 항목 분류표와 제작 계획(`docs/09`)을 더한다.

- `docs/07-cheats.md`: 명령마다 [확인: 효과] / [확인: 반응 없음] / [미시험]
- `docs/06` · `docs/01`: 캐시와 데이터 수정의 관계를 실험 결과로 갱신
- `docs/09-cheat-mod-plan.md`: 원안 예시 아홉 개의 결론, 12개 영역 분류표, 만들 것과 만들지 않을 것, 로드맵
- 실험에 쓴 시험 모드는 게임 폴더에서 모두 되돌렸고 해시로 확인했다.
- `uv run pytest`: <실행 결과의 "N passed">

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --repo game-mod-project/SR2030Toybox docs/cheat-mod-verify --merge
git -C E:/SR2030ToyBox switch develop
git -C E:/SR2030ToyBox pull --ff-only
```

PR 본문의 `<실행 결과의 "N passed">` 는 바로 위 `uv run pytest -q` 의 마지막 줄로 바꿔 넣는다(Task 11 을 했으면 77, 건너뛰었으면 76).

- [ ] **Step 9: 끝났는지 확인한다(명세의 완료 기준)**

```bash
uv run srkit inventory
uv run python scripts/gamedrive.py status
uv run srkit deploy korean
ls build/.deploy
git -C E:/SR2030ToyBox status --short
git -C E:/SR2030ToyBox log --oneline -8
```

Expected: 목록 도구가 다섯 CSV 를 만든다 / `프로세스: 없음` / 한글화 미리보기 `0개 파일` / `build/.deploy` 에 `korean` 만 있다(시험 모드가 남아 있지 않다) / 작업 트리가 깨끗하다 / `develop` 에 머지 커밋이 쌓여 있다.
