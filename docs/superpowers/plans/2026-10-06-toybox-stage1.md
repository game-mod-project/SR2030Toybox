# ToyBox 1단계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 게임 화면 위에 모드 설정 창을 띄우고, 플레이어 국가에만 닿는 내장 치트 16개를 그 창에서 실행한다.

**Architecture:** 한글화 훅(`WTSAPI32.dll`)이 옆에 있는 `srtoybox.dll` 을 불러온다. `srtoybox.dll` 은 swap chain 의 가상 함수 표에 끼어들어 Dear ImGui 로 창을 그리고, 게임 창의 창 프로시저를 감싸 입력을 가로챈다. 단추를 누르면 명령이 대기열에 들어가고, 창 스레드의 타이머가 게임의 설정 창(`Ctrl+Shift+S`)에 치트를 대신 넣는다. 실행 파일의 주소는 쓰지 않는다.

**Tech Stack:** C(`native/srhook`), C++17 + Dear ImGui(Win32 · DirectX 11 백엔드, `native/srtoybox`), MSVC Build Tools(`/MT`), Python 3.13 + uv(`srkit`), pytest + ctypes, `scripts/gamedrive.py`(게임 안 확인).

**Spec:** [docs/superpowers/specs/2026-10-06-toybox-stage1-design.md](../specs/2026-10-06-toybox-stage1-design.md)

## Global Constraints

- Python 은 `uv run` 으로만 실행한다. 코드를 고치면 `uv run pytest` 를 돌린다.
- `main` · `develop` 에 직접 커밋하지 않는다. Task 마다 적힌 브랜치를 `develop` 에서 내고 `develop` 으로 PR 을 올려 merge commit 으로 머지한다. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다.
- 커밋 메시지는 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` 로, PR 본문은 `🤖 Generated with [Claude Code](https://claude.com/claude-code)` 로 끝낸다.
- **게임 설치 폴더를 바꾸는 경로는 `srkit deploy/undeploy --apply` 뿐이다.** 이 계획이 실행하는 것은 승인된 시험 설치 둘이다: `korean`(갱신: `WTSAPI32.dll` 한 개), `toybox`(추가: `srtoybox.dll` 한 개). `--apply` 전에 미리보기를 보고, 그 밖의 줄이 있으면 멈춘다.
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서 띄운다. 사용자가 직접 켠 게임은 건드리지 않는다. 게임을 저장하지 않는다. 게임이 떠 있는 동안 작업 브랜치를 바꾸지 않는다.
- `cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.
- 공개 저장소다: 게임 파일 · 글꼴 파일 · 빌드 산출물(`build/`)을 커밋하지 않는다. 실행 파일의 주소를 적을 때는 빌드 번호를 함께 적는다.
- 외부 소스는 Dear ImGui 하나다(MIT). 버전을 고정하고 `LICENSE.txt` 를 함께 둔다. 필요한 파일만 넣는다.
- 우리 C++ 는 `/std:c++17 /utf-8 /W4 /WX /MT` 로 경고 없이 빌드한다. 외부 소스는 `/W3` 로 빌드한다.
- 기본 단축키는 `Ctrl+Shift+T`. 설정은 `%APPDATA%\SR2030ToyBox\`(환경 변수 `SRTOYBOX_HOME` 이 있으면 그 폴더). 게임 폴더와 문서 폴더에 쓰지 않는다.
- 실행기의 간격: 키 누름 50 ms, 글자 사이 30 ms. 대기열은 최대 8개.
- 창에 넣는 기능은 설계서의 16개뿐이다. 설계서의 "넣지 않는 것"에 든 치트는 하나도 넣지 않는다.
- 문서와 메시지는 한국어. 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다([확인] / [추정]).
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일(C · C++ · 정규식)은 Write · Edit 도구로 쓴다.

## Review Focus

테스트가 다루지 않으면 사용자를 물 가능성이 큰 것 다섯. 줄마다 그것을 못박는 테스트나 확인이 해당 Task 에 들어 있다.

1. **`srtoybox.dll` 자리에 깨진 파일이 있다** → 오류 창 없이 무시되고 한글화는 평소대로다. (Task 1: `test_a_broken_toybox_file_is_ignored`)
2. **단추를 연달아 눌러 대기열이 넘친다** → 8개까지 받고 나머지는 버리며, 받은 것은 순서대로 간격을 지켜 끝까지 들어간다. (Task 2: `test_runner_takes_eight_and_rejects_the_rest`)
3. **명령을 넣는 중에 사용자가 실제 키를 누르거나 뗀다 / 넣은 뒤에 수정키가 남는다** → 끝난 뒤 맨 `S` 는 설정 창이 아니라 보급 지도를 켠다. (Task 4 Step 9: G2 뒤의 확인)
4. **메뉴나 로비에서 단추를 누른다** → 게임이 죽지 않고 메뉴를 쓸 수 있는 상태로 남는다. 무슨 일이 일어나는지 문서에 적는다. (Task 4 Step 12)
5. **창이 떠 있는 채 게임 창의 크기가 바뀐다** → 게임이 죽지 않고 창이 다시 그려진다. (Task 4 Step 13)

---

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `native/srhook/srhook.c` | (수정) 옆의 `srtoybox.dll` 을 불러온다 | 1 |
| `tests/test_hook.py` | (추가) 불러오기 테스트 | 1 |
| `src/srkit/hook.py` | (수정) `_vcvars` → `vcvars`, `_text` → `output_text` (toybox 빌드가 함께 쓴다) | 2 |
| `src/srkit/toybox.py` | ToyBox DLL 빌드 | 2, 3, 4 |
| `src/srkit/cli.py` | (수정) `toybox-build`, `info` 에 한 줄 | 2 |
| `native/srtoybox/features.h` `.cpp` | 기능 표 | 2 |
| `native/srtoybox/command.h` `.cpp` | 명령 조립, 한 명령의 동작 목록(순수) | 2 |
| `native/srtoybox/runner.h` `.cpp` | 대기열과 시간 맞추기(순수 — 보내는 쪽은 `Sink`) | 2 |
| `native/srtoybox/settings.h` `.cpp` | 설정의 해석 · 형식 · 파일 | 2 |
| `native/srtoybox/exports.cpp` | 테스트와 `srhook` 이 쓰는 C 인터페이스, `srtoybox_start` | 2, 4 |
| `tests/test_toybox.py` | DLL 을 직접 불러 확인 | 2, 3, 4 |
| `mods/toybox/README.md` | 모드 설명 | 2 |
| `native/third_party/imgui/` | Dear ImGui(필요한 파일) + `LICENSE.txt` + `README.md` | 3 |
| `native/srtoybox/log.h` `.cpp` | `toybox.log` | 4 |
| `native/srtoybox/runner_win.h` `.cpp` | 게임 창에 실제로 보내는 `Sink`, 전역 실행기 | 4 |
| `native/srtoybox/overlay.h` `.cpp` | `Present` · `ResizeBuffers` 끼어들기, ImGui 초기화 · 그리기 | 4 |
| `native/srtoybox/input.h` `.cpp` | 창 프로시저 감싸기, 타이머, 단축키 | 4 |
| `native/srtoybox/ui.h` `.cpp` | 창의 내용 | 4 |
| `docs/10-toybox.md`, `docs/09-cheat-mod-plan.md`, `docs/06-data-reference.md`, `README.md` | 문서 | 5 |

경로와 명령의 약속(모든 Task 에서 같다):

```bash
cd /e/SR2030ToyBox
G="/e/SteamLibrary/steamapps/common/Supreme Ruler 2030"
S="/c/Users/deepe/AppData/Local/Temp/claude/E--SR2030ToyBox/b1c682f5-b97e-4b98-8900-51969e5deaa7/scratchpad"
gd()  { uv run python scripts/gamedrive.py "$@"; }
nap() { uv run python -c "import time; time.sleep($1)"; }
```

---

### Task 0: 설계서와 계획을 `develop` 에 올린다

**Files:**
- 이미 있음: `docs/superpowers/specs/2026-10-06-toybox-stage1-design.md`, `docs/superpowers/plans/2026-10-06-toybox-stage1.md` (브랜치 `docs/toybox-spec`)

**Interfaces:**
- Produces: `develop` 에 설계서와 이 계획이 있다. 이후의 Task 는 모두 `develop` 에서 브랜치를 낸다.

- [ ] **Step 1: 커밋 확인**

Run: `git -C /e/SR2030ToyBox log --oneline develop..docs/toybox-spec`
Expected: 설계서 커밋과 계획 커밋이 보인다. 작업 트리는 깨끗하다(`git status --short` 가 비어 있다).

- [ ] **Step 2: 테스트**

Run: `uv run pytest -q`
Expected: `98 passed`

- [ ] **Step 3: PR 을 올리고 머지**

```bash
git push -u origin docs/toybox-spec
gh pr create --base develop --head docs/toybox-spec --title "docs: ToyBox 1단계 설계와 구현 계획" --body-file - <<'EOF'
게임 안 모드 설정 창(ToyBox)의 첫 단계 설계서와 구현 계획.

사용자 요구 둘: 게임 안 설정 창에서 모든 기능을 설정한다 / 설정은 플레이어가 플레이 중인 국가에만 적용한다.
제작 계획(docs/09)의 "실행 중 트레이너는 만들지 않는다"를 뒤집는다 — 09 는 구현 뒤 문서 작업에서 고친다.

문서만 바뀐다. `uv run pytest` → 98 passed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr merge --merge docs/toybox-spec
git switch develop && git pull origin develop
```

Expected: `develop` 의 `git log --oneline -1` 이 이 PR 의 머지 커밋이다.

---

### Task 1: `srhook` 이 ToyBox 를 불러온다

브랜치: `feat/toybox-loader` (`develop` 에서)

**Files:**
- Modify: `native/srhook/srhook.c` (`DllMain` 과 그 위)
- Test: `tests/test_hook.py` (끝에 추가)

**Interfaces:**
- Consumes: `srkit.hook.output(cfg) -> Path` (`build/srhook/WTSAPI32.dll`), `uv run srkit hook-build`
- Produces: 훅 DLL 이 로드되면 자기 폴더의 `srtoybox.dll` 을 `LoadLibraryW` 로 불러오고, 그 DLL 이 `srtoybox_start`(`void WINAPI (void)`)를 내보내면 부른다. 환경 변수 `SRTOYBOX=0` 이면 불러오지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hook.py` 의 import 에 `shutil`, `subprocess`, `sys`, `from pathlib import Path` 를 더하고(이미 있는 것은 두 번 넣지 않는다) 파일 끝에 붙인다:

```python
# 훅을 새 프로세스에 불러 놓고, 옆에 둔 srtoybox.dll 이 그 프로세스에 로드됐는지 본다
LOADER_PROBE = """
import ctypes, sys, time
ctypes.WinDLL(sys.argv[1])
k32 = ctypes.WinDLL("kernel32")
k32.GetModuleHandleW.restype = ctypes.c_void_p
k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
deadline = time.time() + float(sys.argv[2])
while time.time() < deadline and not k32.GetModuleHandleW("srtoybox.dll"):
    time.sleep(0.05)
print("loaded" if k32.GetModuleHandleW("srtoybox.dll") else "absent")
"""


def _probe_loader(cfg, tmp_path, toybox: bytes | None, *, wait: float, env: dict[str, str] | None = None) -> str:
    built = hook.output(cfg)
    if not built.is_file():
        pytest.skip("훅 DLL 미빌드 (srkit hook-build)")
    copy = tmp_path / "hookcopy.dll"
    shutil.copyfile(built, copy)
    if toybox is not None:
        (tmp_path / "srtoybox.dll").write_bytes(toybox)
    run = subprocess.run([sys.executable, "-c", LOADER_PROBE, str(copy), str(wait)], capture_output=True, text=True,
                         env={**os.environ, **(env or {})}, timeout=30)
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


def _any_dll() -> bytes:
    """불러올 수 있는 아무 DLL. 불러오는지만 보므로 내용은 상관없다(srtoybox_start 가 없으면 부르지 않는다)."""
    return (Path(os.environ["SystemRoot"]) / "System32" / "version.dll").read_bytes()


def test_toybox_next_to_the_hook_is_loaded(cfg, tmp_path):
    assert _probe_loader(cfg, tmp_path, _any_dll(), wait=3) == "loaded"


def test_nothing_is_loaded_when_the_file_is_missing(cfg, tmp_path):
    assert _probe_loader(cfg, tmp_path, None, wait=1) == "absent"


def test_toybox_can_be_switched_off(cfg, tmp_path):
    assert _probe_loader(cfg, tmp_path, _any_dll(), wait=1, env={"SRTOYBOX": "0"}) == "absent"


def test_a_broken_toybox_file_is_ignored(cfg, tmp_path):
    """깨진 파일이어도 프로세스가 죽지 않는다(오류 창을 막는 것은 SetThreadErrorMode — 창이 떴는지는 여기서 볼 수 없다)."""
    assert _probe_loader(cfg, tmp_path, b"not a dll", wait=1) == "absent"
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_hook.py -q`
Expected: `test_toybox_next_to_the_hook_is_loaded` 가 `assert 'absent' == 'loaded'` 로 FAIL. 나머지 셋과 기존 테스트는 PASS.

- [ ] **Step 3: 불러오기를 구현한다**

`native/srhook/srhook.c` 의 머리 주석 끝(`* 그 밖에 검증 도구(...)` 줄 다음)에 한 줄을 더한다:

```c
 * 그리고 옆에 srtoybox.dll(게임 안 모드 설정 창)이 있으면 불러온다(아래 toybox_loader).
```

`BOOL WINAPI DllMain(` 바로 위에 넣는다:

```c
/* ToyBox(게임 안 모드 설정 창)를 불러온다: 이 DLL 옆에 srtoybox.dll 이 있으면 로드하고 srtoybox_start 를 부른다.
 * DllMain 안에서는 LoadLibrary 를 부르지 않는다(로더 잠금) — DllMain 은 이 스레드만 만든다.
 * 파일이 없거나 깨져 있으면 아무 일도 없고 한글 디코딩은 그대로 동작한다. */
static DWORD WINAPI toybox_loader(LPVOID instance)
{
    static const wchar_t name[] = L"srtoybox.dll";
    wchar_t path[MAX_PATH];
    DWORD n = GetModuleFileNameW((HMODULE)instance, path, MAX_PATH), old = 0;
    HMODULE toybox;
    FARPROC start;

    while (n > 0 && path[n - 1] != L'\\' && path[n - 1] != L'/')
        n--;
    if (n == 0 || n + sizeof(name) / sizeof(name[0]) > MAX_PATH)
        return 0;
    lstrcpyW(path + n, name);
    if (GetFileAttributesW(path) == INVALID_FILE_ATTRIBUTES)
        return 0;
    SetThreadErrorMode(SEM_FAILCRITICALERRORS, &old); /* 깨진 파일이어도 Windows 의 오류 창을 띄우지 않는다 */
    toybox = LoadLibraryW(path);
    SetThreadErrorMode(old, NULL);
    if (toybox == NULL)
        return 0;
    start = GetProcAddress(toybox, "srtoybox_start");
    if (start != NULL)
        ((void(WINAPI *)(void))start)();
    return 0;
}
```

`DllMain` 안, `GetCursorPos` 를 바꿔 끼우는 `if` 문 다음(`#ifdef SRHOOK_TRACE` 앞)에 넣는다:

```c
        if (!(GetEnvironmentVariableA("SRTOYBOX", env, sizeof(env)) == 1 && env[0] == '0')) {
            HANDLE thread = CreateThread(NULL, 0, toybox_loader, instance, 0, NULL);
            if (thread != NULL)
                CloseHandle(thread);
        }
```

- [ ] **Step 4: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit hook-build && uv run pytest tests/test_hook.py -q`
Expected: `빌드 완료: …\build\srhook\WTSAPI32.dll`, 그리고 `test_hook.py` 전부 PASS(경고 없이 — `/W4 /WX` 라 경고는 빌드 실패다).

- [ ] **Step 5: 전체 테스트**

Run: `uv run pytest -q`
Expected: `102 passed`

- [ ] **Step 6: 커밋 · PR · 머지**

```bash
git add native/srhook/srhook.c tests/test_hook.py
git commit -F - <<'EOF'
feat: srhook 이 옆의 srtoybox.dll 을 불러온다 (ToyBox 의 입구)

DllMain 은 스레드만 만들고, 그 스레드가 자기 폴더의 srtoybox.dll 을 불러와 srtoybox_start 를 부른다.
파일이 없거나 깨져 있으면 아무 일도 없다(오류 창도 띄우지 않는다). SRTOYBOX=0 이면 끈다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin feat/toybox-loader
gh pr create --base develop --head feat/toybox-loader --title "feat: srhook 이 옆의 srtoybox.dll 을 불러온다" --body-file - <<'EOF'
ToyBox 1단계의 첫 조각. 한글화 훅(WTSAPI32.dll)이 로드될 때 스레드 하나를 만들어, 자기 옆에 `srtoybox.dll` 이 있으면 불러오고 `srtoybox_start` 를 부른다.

- 없으면 아무 일도 없다. 깨진 파일이어도 프로세스는 그대로다(`SetThreadErrorMode` 로 오류 창을 막는다).
- 환경 변수 `SRTOYBOX=0` 이면 불러오지 않는다.
- 게임 폴더에는 아직 아무것도 설치하지 않았다.

테스트: 훅을 새 프로세스에 불러 놓고 옆의 DLL 이 로드됐는지 본다(있을 때 / 없을 때 / 껐을 때 / 깨졌을 때).
`uv run pytest` → 102 passed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr merge --merge feat/toybox-loader
git switch develop && git pull origin develop
```

---

### Task 2: ToyBox 의 화면 없는 부분 — 기능 표 · 명령 · 실행기 · 설정 · 빌드

브랜치: `feat/toybox-core` (`develop` 에서)

**Files:**
- Modify: `src/srkit/hook.py` (`_vcvars` → `vcvars`, `_text` → `output_text`), `src/srkit/cli.py`
- Create: `src/srkit/toybox.py`, `native/srtoybox/features.h`, `features.cpp`, `command.h`, `command.cpp`, `runner.h`, `runner.cpp`, `settings.h`, `settings.cpp`, `exports.cpp`, `mods/toybox/README.md`
- Test: `tests/test_toybox.py`

**Interfaces:**
- Consumes: `srkit.hook.vcvars() -> Path`, `srkit.hook.output_text(raw: bytes) -> str` (이 Task 에서 이름을 바꾼다)
- Produces (Python): `srkit.toybox.DLL_NAME = "srtoybox.dll"`, `toybox.output(cfg) -> Path`(`build/toybox/srtoybox.dll`), `toybox.status(cfg) -> str`, `toybox.build(cfg) -> Path`, 모듈 상수 `toybox.SOURCES: list[str]`, `toybox.LIBS: list[str]`; 명령 `uv run srkit toybox-build`
- Produces (C++):
  - `struct Feature { const char *id, *tab, *label, *help, *command; bool has_value; long long def, min, max; bool confirm; }`, `extern const Feature FEATURES[]`, `extern const int FEATURE_COUNT`, `const Feature *find_feature(const char *id)`
  - `std::string build_command(const Feature &f, long long value)`; `enum class Act { Mods, Down, Up, Char, Wait }`; `struct Action { Act act; int value; }`; `std::vector<Action> plan_command(const std::string &command)`(넣을 수 없는 글이면 빈 목록); `std::string describe(const std::vector<Action> &plan)`
  - `struct Sink { virtual void mods(bool on) = 0; virtual void key(Act act, int value) = 0; virtual unsigned long long now_ms() = 0; }`; `class Runner { bool enqueue(const std::string &); void tick(Sink &); bool busy() const; size_t pending() const; const std::string &last() const; static const size_t MAX_QUEUE = 8; }`
  - `struct Settings { int hotkey_vk; int hotkey_mods; std::map<std::string, long long> values; }`; `const int HOTKEY_CTRL = 1, HOTKEY_SHIFT = 2, HOTKEY_ALT = 4`; `Settings default_settings()`; `Settings parse_settings(const std::string &ini)`; `std::string format_settings(const Settings &)`; `bool valid_hotkey(int vk, int mods)`; `std::string hotkey_name(int vk, int mods)`; `std::wstring settings_dir()`; `Settings load_settings()`; `bool save_settings(const Settings &)`
- Produces (DLL 내보내기, 모두 `int` 반환 · 글은 UTF-8 · 버퍼가 작거나 대상이 없으면 `-1`): `srtoybox_feature_count()`, `srtoybox_feature_info(int index, char *out, int size)`, `srtoybox_command(const char *id, long long value, char *out, int size)`, `srtoybox_plan(const char *command, char *out, int size)`, `srtoybox_simulate(const char *commands, int tick_ms, char *out, int size)`, `srtoybox_settings_normalize(const char *ini, char *out, int size)`, `srtoybox_settings_store(const char *ini)`(성공 1), `srtoybox_settings_file(char *out, int size)`, `srtoybox_hotkey_name(int vk, int mods, char *out, int size)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

Create `tests/test_toybox.py`:

```python
"""ToyBox DLL(native/srtoybox)을 직접 불러 화면 없는 부분을 확인한다(게임은 띄우지 않는다)."""
import ctypes
import re

import pytest

from srkit import toybox

# 설계서의 "넣지 않는 것": 모든 지역·AI 에 닿거나, 불리해지거나, 지역 번호가 필요하거나, 넣지 않기로 한 것
EXCLUDED = {
    "onedaybuild", "allunit", "gates", "devcheat", "endday", "increaseday", "eventnow", "peace", "worldwar", "darren",
    "democracy", "saddam", "breakground", "depopulate", "trumpme", "sanction", "wmsanction", "shelovesmenot", "saddamme",
    "approval", "love", "hate", "neutral", "annex", "colonize", "novichok", "fight", "treaty", "becomeregion",
    "resettutorial", "allowcheats",
}
TABS = ["돈", "물자", "연구", "인구·여론", "부대", "화면·진행"]
TEXT_CALLS = ["srtoybox_feature_info", "srtoybox_command", "srtoybox_plan", "srtoybox_simulate",
              "srtoybox_settings_normalize", "srtoybox_settings_file", "srtoybox_hotkey_name"]


@pytest.fixture(scope="module")
def dll(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_feature_info.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_command.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_plan.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_simulate.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_settings_normalize.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_settings_store.argtypes = [ctypes.c_char_p]
    lib.srtoybox_settings_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_hotkey_name.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib


def text(call, *args, size: int = 1 << 17) -> str | None:
    """글을 돌려주는 내보내기 함수를 부른다. 함수가 -1 을 주면 None."""
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return None if n < 0 else buf.raw[:n].decode("utf-8")


def features(dll) -> list[dict]:
    out = []
    for i in range(dll.srtoybox_feature_count()):
        ident, tab, label, command, has_value, default, low, high, confirm, help_ = text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_})
    return out


def documented(cfg) -> dict[str, tuple[str, str]]:
    """docs/07 의 치트표: 이름 → (대상, 검증)."""
    rows = {}
    for line in (cfg.root / "docs" / "07-cheats.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        m = re.fullmatch(r"`cheat ([^` ]+)`", cells[0]) if len(cells) == 6 else None
        if m:
            rows[m[1]] = (cells[3], cells[5])
    return rows


def test_feature_table(dll):
    fs = features(dll)
    assert len(fs) == 16
    assert len({f["id"] for f in fs}) == 16 and len({f["command"] for f in fs}) == 16
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    for f in fs:
        assert f["command"] == "cheat " + f["id"] and f["label"] and f["help"]
        if f["has_value"]:
            assert f["min"] <= f["default"] <= f["max"]
    assert {f["id"] for f in fs if f["has_value"]} == {"treasury", "products", "technology", "spawnunit"}
    assert [f["id"] for f in fs if f["confirm"]] == ["instantwin"]
    assert dll.srtoybox_feature_info(16, ctypes.create_string_buffer(8), 8) == -1


def test_only_player_cheats_that_were_seen_working(dll, cfg):
    """요구: 설정은 플레이어가 플레이 중인 국가에만 적용된다. 게임이 플레이어에게만 적용하는 것으로 확인된 치트만 내놓는다."""
    rows = documented(cfg)
    for f in features(dll):
        target, verdict = rows[f["id"]]
        assert verdict == "[확인: 효과]", f["id"]
        assert target.startswith("플레이어") or target == "고른 부대", (f["id"], target)
        assert f["id"] not in EXCLUDED


def test_command_text(dll):
    assert text(dll.srtoybox_command, b"treasury", 1234) == "cheat treasury 1234"
    assert text(dll.srtoybox_command, b"treasury", 0) == "cheat treasury 1"                    # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"treasury", -5) == "cheat treasury 1"
    assert text(dll.srtoybox_command, b"treasury", 10**12) == "cheat treasury 1000000"
    assert text(dll.srtoybox_command, b"georgew", 999) == "cheat georgew"                      # 값이 없는 기능은 값을 무시한다
    assert text(dll.srtoybox_command, b"e=mc2", 0) == "cheat e=mc2"
    assert text(dll.srtoybox_command, b"depopulate", 0) is None                                # 표에 없는 것은 만들지 않는다
    assert text(dll.srtoybox_command, b"treasury", 1, size=4) is None                          # 버퍼가 작으면 넘치지 않고 -1


def expected_plan(command: str) -> list[str]:
    """gamedrive.py 가 밖에서 넣는 것과 같은 순서: 설정 창 열기 → cheat allowcheats → 명령 → ESC."""
    out = ["MODS 1", "DOWN 17", "DOWN 16", "DOWN 83", "WAIT 50", "UP 83", "WAIT 100", "UP 16", "UP 17", "WAIT 200", "MODS 0",
           "WAIT 300"]
    for line in ("cheat allowcheats", command):
        for ch in line:
            out += [f"CHAR {ord(ch)}", "WAIT 30"]
        out += ["DOWN 13", "WAIT 50", "UP 13", "WAIT 300"]
    return out + ["DOWN 27", "WAIT 50", "UP 27", "WAIT 300"]


def test_plan_follows_the_route_checked_in_game(dll):
    plan = text(dll.srtoybox_plan, b"cheat treasury 1234").splitlines()
    assert plan == expected_plan("cheat treasury 1234")
    assert plan.index("MODS 0") < min(i for i, step in enumerate(plan) if step.startswith("CHAR"))   # 수정키를 뗀 뒤에 글자를 넣는다


def test_plan_refuses_text_the_game_input_cannot_take(dll):
    for bad in (b"", "cheat 한글".encode("utf-8"), b"cheat a\nb", b"cheat a\tb", b"x" * 65, b"cheat \x7f"):
        assert text(dll.srtoybox_plan, bad) is None, bad
    assert text(dll.srtoybox_plan, b"x" * 64) is not None


def events(log: str) -> list[tuple[int, str]]:
    return [(int(t), f"{act} {value}") for t, act, value in (line.split() for line in log.splitlines() if not line.startswith("REJECT"))]


def assert_gaps_kept(evs: list[tuple[int, str]], plan: list[str]) -> None:
    """계획의 WAIT 만큼은 반드시 벌어져 있어야 한다(프레임이 빨라도 게임이 읽을 시간을 준다)."""
    assert [step for _, step in evs] == [step for step in plan if not step.startswith("WAIT")]
    at, owed, last = 0, 0, None
    for step in plan:
        if step.startswith("WAIT"):
            owed += int(step.split()[1])
            continue
        t = evs[at][0]
        if last is not None:
            assert t - last >= owed, (step, t - last, owed)
        at, owed, last = at + 1, 0, t


def test_runner_keeps_the_gaps_however_fast_it_is_ticked(dll):
    for tick_ms in (1, 10, 16, 40):
        evs = events(text(dll.srtoybox_simulate, b"cheat georgew", tick_ms))
        assert_gaps_kept(evs, expected_plan("cheat georgew"))


def test_runner_runs_commands_in_order(dll):
    evs = events(text(dll.srtoybox_simulate, b"cheat georgew\ncheat populate", 10))
    first, second = expected_plan("cheat georgew"), expected_plan("cheat populate")
    assert_gaps_kept(evs, first + second)                       # 첫 명령의 마지막 WAIT 가 둘째 명령 앞의 간격이 된다


def test_runner_takes_eight_and_rejects_the_rest(dll):
    """단추를 연달아 눌러도 8개까지만 받는다. 받은 것은 순서대로 끝까지 들어간다."""
    commands = [f"cheat treasury {n}" for n in range(1, 11)]
    log = text(dll.srtoybox_simulate, "\n".join(commands).encode(), 10)
    assert [line for line in log.splitlines() if line.startswith("REJECT")] == ["REJECT cheat treasury 9", "REJECT cheat treasury 10"]
    assert_gaps_kept(events(log), [step for c in commands[:8] for step in expected_plan(c)])
    assert text(dll.srtoybox_simulate, "cheat 한글".encode("utf-8"), 10) == "REJECT cheat 한글\n"   # 넣을 수 없는 글은 받지 않는다


DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\ntreasury=10000\nproducts=100000\ntechnology=120\nspawnunit=2413\n"


def test_settings_fall_back_to_defaults(dll):
    norm = lambda ini: text(dll.srtoybox_settings_normalize, ini.encode("utf-8"))
    assert norm("") == DEFAULTS
    assert norm("\xff garbage\n===\n[x]\nhotkey_vk\n=5\n") == DEFAULTS                      # 깨진 파일
    assert norm("treasury=0\nproducts=999999999999\ntechnology=abc\nspawnunit=12x\n") == DEFAULTS   # 범위 밖·숫자 아님 → 기본값
    assert norm("unknown=5\ngeorgew=7\ndepopulate=1\n") == DEFAULTS                          # 모르는 키, 값이 없는 기능
    assert norm("hotkey_vk=16\nhotkey_mods=1\n") == DEFAULTS                                 # 수정키만으로는 단축키가 못 된다
    assert norm("hotkey_vk=27\nhotkey_mods=0\n") == DEFAULTS                                 # ESC 만은 취소다
    assert norm("hotkey_vk=84\nhotkey_mods=9\n") == DEFAULTS
    assert norm(" hotkey_vk = 123 \r\nhotkey_mods=0\r\ntreasury= 500 \r\n") == DEFAULTS.replace("=84", "=123").replace("mods=3", "mods=0").replace("treasury=10000", "treasury=500")


def test_settings_file_round_trip(dll, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    assert text(dll.srtoybox_settings_file) == DEFAULTS                                      # 파일이 없으면 기본값
    assert dll.srtoybox_settings_store(b"hotkey_vk=120\nhotkey_mods=4\ntechnology=140\n") == 1
    saved = DEFAULTS.replace("=84", "=120").replace("mods=3", "mods=4").replace("=120\nspawn", "=140\nspawn")
    assert (tmp_path / "toybox.ini").read_text(encoding="utf-8") == saved
    assert text(dll.srtoybox_settings_file) == saved
    (tmp_path / "toybox.ini").write_bytes(b"\xff\xfe\x00broken")
    assert text(dll.srtoybox_settings_file) == DEFAULTS


def test_hotkey_names(dll):
    name = lambda vk, mods: text(dll.srtoybox_hotkey_name, vk, mods)
    assert name(84, 3) == "Ctrl+Shift+T"
    assert name(0x7B, 0) == "F12"
    assert name(0x31, 4) == "Alt+1"
    assert name(0xC0, 7) == "Ctrl+Shift+Alt+0xC0"


def test_mod_folder_holds_only_the_dll(dll, cfg):
    """build/toybox 는 게임 루트 구조의 모드 폴더다. deploy 가 통째로 복사하므로 DLL 말고는 없어야 한다."""
    assert sorted(p.name for p in toybox.output(cfg).parent.iterdir()) == [toybox.DLL_NAME]
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox.py -q`
Expected: 수집 단계에서 `ImportError: cannot import name 'toybox' from 'srkit'` 로 ERROR.

- [ ] **Step 3: 빌드 도구를 쓴다**

`src/srkit/hook.py` 에서 `_vcvars` 를 `vcvars` 로, `_text` 를 `output_text` 로 바꾼다(정의 2곳, 사용 3곳 — `grep -n "_vcvars\|_text(" src/srkit/hook.py` 로 확인).

Create `src/srkit/toybox.py`:

```python
"""ToyBox DLL(native/srtoybox) 빌드. 게임 안 모드 설정 창이다 — 한글화 훅(WTSAPI32.dll)이 게임 폴더에서 불러온다."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import hook
from .config import Config

DLL_NAME = "srtoybox.dll"
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp"]
LIBS = ["kernel32.lib", "user32.lib"]
FLAGS = "/nologo /c /utf-8 /std:c++17 /O2 /MT /EHsc /DNDEBUG /DNOMINMAX"   # NDEBUG: 게임 안에서 assert 로 죽지 않게. NOMINMAX: windows.h 의 min · max 매크로를 끈다


def output(cfg: Config) -> Path:
    """모드 폴더(build/toybox, 게임 루트 구조) 안의 DLL. 이 폴더에는 DLL 만 둔다 — deploy 가 통째로 복사한다."""
    return cfg.build_dir / "toybox" / DLL_NAME


def status(cfg: Config) -> str:
    out = output(cfg)
    return f"{out} (빌드됨)" if out.is_file() else "빌드 안 됨 — srkit toybox-build"


def _quoted(paths) -> str:
    return " ".join(f'"{p}"' for p in paths)


def build(cfg: Config) -> Path:
    src = cfg.root / "native" / "srtoybox"
    out, obj = output(cfg), cfg.build_dir / "toybox-obj"      # 중간 산출물(.obj .lib .exp)은 모드 폴더 밖에 둔다
    out.parent.mkdir(parents=True, exist_ok=True)
    obj.mkdir(parents=True, exist_ok=True)
    ours = [src / name for name in SOURCES]
    objs = [obj / (p.stem + ".obj") for p in ours]
    script = obj / "build.cmd"
    script.write_text(
        "@echo off\r\n"
        f'call "{hook.vcvars()}" >nul || exit /b 1\r\n'
        f'cl {FLAGS} /W4 /WX /Fo"{obj}\\\\" {_quoted(ours)} || exit /b 1\r\n'
        f'link /NOLOGO /DLL /OUT:"{out}" /IMPLIB:"{obj / "srtoybox.lib"}" {_quoted(objs)} {" ".join(LIBS)} || exit /b 1\r\n',
        encoding="mbcs")
    result = subprocess.run(["cmd", "/d", "/c", str(script)], cwd=obj, capture_output=True)
    if result.returncode != 0 or not out.is_file():
        raise RuntimeError(f"ToyBox DLL 빌드 실패:\n{hook.output_text(result.stdout)}\n{hook.output_text(result.stderr)}")
    return out
```

`src/srkit/cli.py`: import 줄을 `from . import cheats, config, deploy, hook, inventory, korean, mt, probe, toybox` 로 바꾸고, `cmd_info` 의 `디코딩 훅` 줄 다음에 넣는다:

```python
    print(f"ToyBox        : {toybox.status(cfg)}")
```

`cmd_hook_build` 다음에 넣는다:

```python
def cmd_toybox_build(cfg, _args) -> int:
    print(f"빌드 완료: {toybox.build(cfg)}")
    return 0
```

`hook-build` 파서(`h.set_defaults(fn=cmd_hook_build)`) 다음 줄에 넣는다:

```python
    sub.add_parser("toybox-build", help="ToyBox DLL(srtoybox.dll, 게임 안 모드 설정 창) 빌드 → build/toybox") \
        .set_defaults(fn=cmd_toybox_build)
```

- [ ] **Step 4: 기능 표를 쓴다**

Create `native/srtoybox/features.h`:

```cpp
// ToyBox 가 창에서 내놓는 기능 표.
// 넣는 기준: docs/07 에서 검증이 [확인: 효과]이고 대상이 "플레이어" 또는 "고른 부대"인 치트 가운데 불리해지지 않는 것.
// tests/test_toybox.py 가 이 표를 docs/07 과 대조한다.
#pragma once

struct Feature {
    const char *id;       // 치트 이름. 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다
    bool has_value;
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
};

extern const Feature FEATURES[];
extern const int FEATURE_COUNT;

const Feature *find_feature(const char *id);
```

Create `native/srtoybox/features.cpp`:

```cpp
#include "features.h"

#include <cstring>

const Feature FEATURES[] = {
    {"treasury", "돈", "국고 추가", "입력한 금액(백만 달러)만큼 국고가 늘어난다", "cheat treasury", true, 10000, 1, 1000000, false},
    {"georgew", "돈", "국고 +$10 B", "국고가 100억 달러 늘어난다", "cheat georgew", false, 0, 0, 0, false},
    {"georgeww", "돈", "국고 +$100 B", "국고가 1000억 달러 늘어난다", "cheat georgeww", false, 0, 0, 0, false},
    {"products", "물자", "모든 물자 추가", "입력한 수량만큼 모든 물자의 재고가 늘어난다", "cheat products", true, 100000, 1, 100000000, false},
    {"branson", "물자", "모든 물자 +100만", "모든 물자의 재고가 100만씩 늘어난다", "cheat branson", false, 0, 0, 0, false},
    {"bezos", "물자", "모든 물자 +1억", "모든 물자의 재고가 약 1억씩 늘어난다", "cheat bezos", false, 0, 0, 0, false},
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다", "cheat technology", true, 120, 1, 999, false},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 연구가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "cheat e=mc2", false, 0, 0, 0, false},
    {"finalexam", "연구", "지식 순위 올리기", "지식 지수 순위가 오른다", "cheat finalexam", false, 0, 0, 0, false},
    {"populate", "인구·여론", "인구 +100만", "인구가 100만 늘어난다", "cheat populate", false, 0, 0, 0, false},
    {"shelovesme", "인구·여론", "세계 시장 여론 최고", "세계 시장 여론과 보조금률이 최고가 된다", "cheat shelovesme", false, 0, 0, 0, false},
    {"spawnunit", "부대", "고른 칸에 부대 생성", "지도에서 칸을 고른 뒤 누른다. 입력한 장비 번호의 부대가 생긴다(보급은 빈 채)", "cheat spawnunit", true, 2413, 1, 99999, false},
    {"stranded", "부대", "고른 부대 보급 채우기/비우기", "부대를 고른 뒤 누른다. 연료·보급·탄약이 100% 가 되고, 다시 누르면 0% 가 된다", "cheat stranded", false, 0, 0, 0, false},
    {"darran", "부대", "최강 부대 묶음 받기", "병과마다 강한 부대를 한 묶음 받는다", "cheat darran", false, 0, 0, 0, false},
    {"fullmapshow", "화면·진행", "GUI 숨기기/보이기", "게임의 GUI 를 모두 숨긴다. 다시 누르면 돌아온다", "cheat fullmapshow", false, 0, 0, 0, false},
    {"instantwin", "화면·진행", "즉시 승리", "승리 창이 뜬다. 이어서 할 수 있다", "cheat instantwin", false, 0, 0, 0, true},
};

const int FEATURE_COUNT = static_cast<int>(sizeof(FEATURES) / sizeof(FEATURES[0]));

const Feature *find_feature(const char *id)
{
    for (int i = 0; i < FEATURE_COUNT; i++)
        if (strcmp(FEATURES[i].id, id) == 0)
            return &FEATURES[i];
    return nullptr;
}
```

- [ ] **Step 5: 명령 조립과 동작 목록을 쓴다**

Create `native/srtoybox/command.h`:

```cpp
// 기능 → 게임에 넣을 글, 그리고 그 글을 게임의 설정 창에 넣는 동작의 순서. 창도 게임도 모르는 순수 함수다.
#pragma once

#include <string>
#include <vector>

#include "features.h"

// 값은 기능의 범위로 잘라 맞춘다. 값이 없는 기능은 값을 무시한다.
std::string build_command(const Feature &f, long long value);

enum class Act { Mods, Down, Up, Char, Wait };

struct Action {
    Act act;
    int value;   // Mods: 1 누름 / 0 되돌림, Down·Up: 가상 키 코드, Char: 글자, Wait: 밀리초
};

// 명령 한 개를 넣는 동작의 순서: 설정 창 열기(Ctrl+Shift+S) → cheat allowcheats → 명령 → ESC.
// scripts/gamedrive.py 가 밖에서 넣는(게임에서 확인된) 순서와 간격을 그대로 따른다.
// 게임의 입력란이 받을 수 없는 글(빈 글, ASCII 밖, 64자 초과)이면 빈 목록을 준다.
std::vector<Action> plan_command(const std::string &command);

std::string describe(const std::vector<Action> &plan);   // 한 줄에 동작 하나: "DOWN 83"
```

Create `native/srtoybox/command.cpp`:

```cpp
#include "command.h"

namespace {

const int VK_SHIFT_ = 0x10, VK_CONTROL_ = 0x11, VK_RETURN_ = 0x0D, VK_ESCAPE_ = 0x1B, VK_S_ = 0x53;
const int KEY_MS = 50;          // 키를 누르고 있는 시간
const int CHAR_MS = 30;         // 글자 사이
const int AFTER_KEY_MS = 100;   // 키를 뗀 뒤
const int AFTER_MODS_MS = 200;  // 수정키를 뗀 뒤, 키 상태표를 되돌리기 전(게임이 보낸 메시지를 다 읽을 때까지)
const int SETTLE_MS = 300;      // 창이 뜨거나 명령이 처리될 시간
const size_t MAX_COMMAND = 64;

void press(std::vector<Action> &plan, int vk, int after_ms)
{
    plan.push_back({Act::Down, vk});
    plan.push_back({Act::Wait, KEY_MS});
    plan.push_back({Act::Up, vk});
    plan.push_back({Act::Wait, after_ms});
}

void enter_line(std::vector<Action> &plan, const std::string &text)
{
    for (unsigned char c : text) {
        plan.push_back({Act::Char, c});
        plan.push_back({Act::Wait, CHAR_MS});
    }
    press(plan, VK_RETURN_, SETTLE_MS);
}

}  // namespace

std::string build_command(const Feature &f, long long value)
{
    std::string out = f.command;
    if (f.has_value) {
        const long long v = value < f.min ? f.min : value > f.max ? f.max : value;
        out += ' ';
        out += std::to_string(v);
    }
    return out;
}

std::vector<Action> plan_command(const std::string &command)
{
    std::vector<Action> plan;
    if (command.empty() || command.size() > MAX_COMMAND)
        return plan;
    for (unsigned char c : command)
        if (c < 0x20 || c > 0x7E)
            return plan;

    plan.push_back({Act::Mods, 1});
    plan.push_back({Act::Down, VK_CONTROL_});
    plan.push_back({Act::Down, VK_SHIFT_});
    plan.push_back({Act::Down, VK_S_});
    plan.push_back({Act::Wait, KEY_MS});
    plan.push_back({Act::Up, VK_S_});
    plan.push_back({Act::Wait, AFTER_KEY_MS});
    plan.push_back({Act::Up, VK_SHIFT_});
    plan.push_back({Act::Up, VK_CONTROL_});
    plan.push_back({Act::Wait, AFTER_MODS_MS});
    plan.push_back({Act::Mods, 0});
    plan.push_back({Act::Wait, SETTLE_MS});
    enter_line(plan, "cheat allowcheats");   // 두 번 넣어도 치트는 켜진 채다 [확인: 게임] — 그래서 매번 보낸다
    enter_line(plan, command);
    press(plan, VK_ESCAPE_, SETTLE_MS);      // 설정 창은 ESC 로 닫힌다 [확인: 게임]
    return plan;
}

std::string describe(const std::vector<Action> &plan)
{
    static const char *const names[] = {"MODS", "DOWN", "UP", "CHAR", "WAIT"};
    std::string out;
    for (const Action &a : plan) {
        out += names[static_cast<int>(a.act)];
        out += ' ';
        out += std::to_string(a.value);
        out += '\n';
    }
    return out;
}
```

- [ ] **Step 6: 실행기를 쓴다**

Create `native/srtoybox/runner.h`:

```cpp
// 명령의 대기열과 시간 맞추기. 동작을 실제로 보내는 일은 Sink 가 한다
// (게임 안에서는 창 메시지와 키 상태표 — runner_win.cpp, 테스트에서는 기록만).
#pragma once

#include <deque>
#include <string>
#include <vector>

#include "command.h"

struct Sink {
    virtual void mods(bool on) = 0;             // 수정키(Ctrl·Shift)를 눌린 것으로 적는다 / 되돌린다
    virtual void key(Act act, int value) = 0;   // Down · Up · Char
    virtual unsigned long long now_ms() = 0;
    virtual ~Sink() {}
};

class Runner {
public:
    static const size_t MAX_QUEUE = 8;          // 넣는 중인 것까지 합쳐서

    bool enqueue(const std::string &command);   // 가득 찼거나 넣을 수 없는 글이면 받지 않는다
    void tick(Sink &sink);                      // 한 번에 동작 하나. WAIT 가 다 지나기 전에는 아무것도 하지 않는다
    bool busy() const { return !plan_.empty() || !queue_.empty(); }
    size_t pending() const { return queue_.size() + (plan_.empty() ? 0 : 1); }
    const std::string &last() const { return last_; }

private:
    std::deque<std::string> queue_;
    std::vector<Action> plan_;
    size_t at_ = 0;
    unsigned long long wait_until_ = 0;         // 명령이 끝나도 지우지 않는다 — 마지막 WAIT 가 다음 명령 앞의 간격이 된다
    std::string last_;
};
```

Create `native/srtoybox/runner.cpp`:

```cpp
#include "runner.h"

bool Runner::enqueue(const std::string &command)
{
    if (pending() >= MAX_QUEUE || plan_command(command).empty())
        return false;
    queue_.push_back(command);
    return true;
}

void Runner::tick(Sink &sink)
{
    if (plan_.empty()) {
        if (queue_.empty())
            return;
        last_ = queue_.front();
        queue_.pop_front();
        plan_ = plan_command(last_);
        at_ = 0;
    }
    if (sink.now_ms() < wait_until_)
        return;
    const Action a = plan_[at_++];
    switch (a.act) {
    case Act::Mods:
        sink.mods(a.value != 0);
        break;
    case Act::Wait:
        wait_until_ = sink.now_ms() + static_cast<unsigned long long>(a.value);
        break;
    default:
        sink.key(a.act, a.value);
        break;
    }
    if (at_ >= plan_.size())
        plan_.clear();
}
```

- [ ] **Step 7: 설정을 쓴다**

Create `native/srtoybox/settings.h`:

```cpp
// 창에서 바꾸는 설정: 여닫는 단축키와 기능마다 마지막에 넣은 값.
// 글 형식은 한 줄에 "키=값". 모르는 줄은 버리고 틀린 값은 기본값으로 돌린다.
#pragma once

#include <map>
#include <string>

const int HOTKEY_CTRL = 1, HOTKEY_SHIFT = 2, HOTKEY_ALT = 4;

struct Settings {
    int hotkey_vk = 0x54;                            // T
    int hotkey_mods = HOTKEY_CTRL | HOTKEY_SHIFT;
    std::map<std::string, long long> values;         // 값이 있는 기능의 id → 값
};

Settings default_settings();
Settings parse_settings(const std::string &ini);
std::string format_settings(const Settings &s);
bool valid_hotkey(int vk, int mods);                 // 수정키만으로는 안 되고, ESC 만 누른 것은 취소다
std::string hotkey_name(int vk, int mods);           // "Ctrl+Shift+T"

// 파일: %APPDATA%\SR2030ToyBox\ (환경 변수 SRTOYBOX_HOME 이 있으면 그 폴더). 게임 폴더와 문서 폴더에는 쓰지 않는다.
std::wstring settings_dir();                         // 없으면 만든다. 구하지 못하면 빈 글
Settings load_settings();                            // 파일이 없거나 깨져 있으면 기본값
bool save_settings(const Settings &s);
```

Create `native/srtoybox/settings.cpp`:

```cpp
#include "settings.h"

#include <windows.h>

#include <cstdio>
#include <cstdlib>

#include "features.h"

namespace {

std::string trim(const std::string &s)
{
    size_t a = 0, b = s.size();
    while (a < b && (s[a] == ' ' || s[a] == '\t' || s[a] == '\r'))
        a++;
    while (b > a && (s[b - 1] == ' ' || s[b - 1] == '\t' || s[b - 1] == '\r'))
        b--;
    return s.substr(a, b - a);
}

bool parse_int(const std::string &s, long long &out)
{
    if (s.empty() || s.size() > 18)
        return false;
    char *end = nullptr;
    const long long v = strtoll(s.c_str(), &end, 10);
    if (end == s.c_str() || *end != '\0')
        return false;
    out = v;
    return true;
}

std::wstring env(const wchar_t *name)
{
    wchar_t buf[MAX_PATH];
    const DWORD n = GetEnvironmentVariableW(name, buf, MAX_PATH);
    return n > 0 && n < MAX_PATH ? std::wstring(buf, n) : std::wstring();
}

std::wstring settings_path()
{
    const std::wstring dir = settings_dir();
    return dir.empty() ? dir : dir + L"\\toybox.ini";
}

}  // namespace

bool valid_hotkey(int vk, int mods)
{
    if (mods < 0 || mods > 7 || vk < 0x08 || vk > 0xFE)
        return false;
    if (vk == 0x10 || vk == 0x11 || vk == 0x12 || vk == 0x5B || vk == 0x5C || (vk >= 0xA0 && vk <= 0xA5))
        return false;   // Shift · Ctrl · Alt · Win 과 그 좌우
    return !(vk == 0x1B && mods == 0);
}

std::string hotkey_name(int vk, int mods)
{
    std::string out;
    if (mods & HOTKEY_CTRL)
        out += "Ctrl+";
    if (mods & HOTKEY_SHIFT)
        out += "Shift+";
    if (mods & HOTKEY_ALT)
        out += "Alt+";
    if ((vk >= '0' && vk <= '9') || (vk >= 'A' && vk <= 'Z')) {
        out += static_cast<char>(vk);
    } else if (vk >= 0x70 && vk <= 0x87) {
        out += "F" + std::to_string(vk - 0x6F);
    } else {
        char hex[8];
        snprintf(hex, sizeof(hex), "0x%02X", vk & 0xFF);
        out += hex;
    }
    return out;
}

Settings default_settings()
{
    Settings s;
    for (int i = 0; i < FEATURE_COUNT; i++)
        if (FEATURES[i].has_value)
            s.values[FEATURES[i].id] = FEATURES[i].def;
    return s;
}

Settings parse_settings(const std::string &ini)
{
    Settings s = default_settings();
    long long vk = s.hotkey_vk, mods = s.hotkey_mods;
    size_t pos = 0;
    while (pos <= ini.size()) {
        size_t end = ini.find('\n', pos);
        if (end == std::string::npos)
            end = ini.size();
        const std::string line = ini.substr(pos, end - pos);
        pos = end + 1;
        const size_t eq = line.find('=');
        long long n = 0;
        if (eq == std::string::npos || !parse_int(trim(line.substr(eq + 1)), n))
            continue;
        const std::string key = trim(line.substr(0, eq));
        if (key == "hotkey_vk") {
            vk = n;
        } else if (key == "hotkey_mods") {
            mods = n;
        } else {
            const Feature *f = find_feature(key.c_str());
            if (f != nullptr && f->has_value && n >= f->min && n <= f->max)
                s.values[f->id] = n;
        }
    }
    if (vk >= 0 && vk <= 0xFE && mods >= 0 && mods <= 7 && valid_hotkey(static_cast<int>(vk), static_cast<int>(mods))) {
        s.hotkey_vk = static_cast<int>(vk);
        s.hotkey_mods = static_cast<int>(mods);
    }
    return s;
}

std::string format_settings(const Settings &s)
{
    std::string out = "hotkey_vk=" + std::to_string(s.hotkey_vk) + "\nhotkey_mods=" + std::to_string(s.hotkey_mods) + "\n";
    for (int i = 0; i < FEATURE_COUNT; i++) {
        if (!FEATURES[i].has_value)
            continue;
        const auto found = s.values.find(FEATURES[i].id);
        out += std::string(FEATURES[i].id) + "=" + std::to_string(found == s.values.end() ? FEATURES[i].def : found->second) + "\n";
    }
    return out;
}

std::wstring settings_dir()
{
    std::wstring dir = env(L"SRTOYBOX_HOME");
    if (dir.empty()) {
        dir = env(L"APPDATA");
        if (dir.empty())
            return dir;
        dir += L"\\SR2030ToyBox";
    }
    CreateDirectoryW(dir.c_str(), nullptr);   // 이미 있으면 실패하지만 그대로 쓴다
    return dir;
}

Settings load_settings()
{
    const std::wstring path = settings_path();
    std::string ini;
    if (!path.empty()) {
        const HANDLE f = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (f != INVALID_HANDLE_VALUE) {
            char buf[4096];
            DWORD n = 0;
            if (ReadFile(f, buf, sizeof(buf), &n, nullptr))   // 설정 파일은 100바이트 남짓이다. 4096 을 넘는 부분은 읽지 않는다
                ini.assign(buf, n);
            CloseHandle(f);
        }
    }
    return parse_settings(ini);
}

bool save_settings(const Settings &s)
{
    const std::wstring path = settings_path();
    if (path.empty())
        return false;
    const std::string ini = format_settings(s);
    const HANDLE f = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE)
        return false;
    DWORD n = 0;
    const BOOL ok = WriteFile(f, ini.data(), static_cast<DWORD>(ini.size()), &n, nullptr);
    CloseHandle(f);
    return ok && n == ini.size();
}
```

- [ ] **Step 8: 내보내기를 쓴다**

Create `native/srtoybox/exports.cpp`:

```cpp
// 테스트(tests/test_toybox.py)가 쓰는 C 인터페이스. 글은 UTF-8, 버퍼가 작거나 대상이 없으면 -1.
#include <cstring>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "runner.h"
#include "settings.h"

#define EXPORT extern "C" __declspec(dllexport)

namespace {

int put(const std::string &text, char *out, int size)
{
    if (out == nullptr || size <= 0 || text.size() + 1 > static_cast<size_t>(size))
        return -1;
    memcpy(out, text.c_str(), text.size() + 1);
    return static_cast<int>(text.size());
}

// 보내는 대신 적어 두는 Sink. 시계는 부르는 쪽이 돌린다.
struct RecordingSink : Sink {
    unsigned long long now = 0;
    std::string log;

    void line(const char *what, int value) { log += std::to_string(now) + ' ' + what + ' ' + std::to_string(value) + '\n'; }
    void mods(bool on) override { line("MODS", on ? 1 : 0); }
    void key(Act act, int value) override { line(act == Act::Down ? "DOWN" : act == Act::Up ? "UP" : "CHAR", value); }
    unsigned long long now_ms() override { return now; }
};

}  // namespace

EXPORT int srtoybox_feature_count(void)
{
    return FEATURE_COUNT;
}

// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명 — 탭 문자로 나눈다
EXPORT int srtoybox_feature_info(int index, char *out, int size)
{
    if (index < 0 || index >= FEATURE_COUNT)
        return -1;
    const Feature &f = FEATURES[index];
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help;
    return put(line, out, size);
}

EXPORT int srtoybox_command(const char *id, long long value, char *out, int size)
{
    const Feature *f = id == nullptr ? nullptr : find_feature(id);
    return f == nullptr ? -1 : put(build_command(*f, value), out, size);
}

EXPORT int srtoybox_plan(const char *command, char *out, int size)
{
    const std::vector<Action> plan = plan_command(command == nullptr ? "" : command);
    return plan.empty() ? -1 : put(describe(plan), out, size);
}

// 명령들(줄바꿈으로 나눈다)을 한꺼번에 대기열에 넣고 가짜 시계로 끝까지 돌린다.
// 줄마다 "<밀리초> <동작> <값>". 받지 못한 명령은 맨 앞에 "REJECT <명령>".
EXPORT int srtoybox_simulate(const char *commands, int tick_ms, char *out, int size)
{
    Runner runner;
    RecordingSink sink;
    const std::string all = commands == nullptr ? "" : commands;
    std::string rejected;
    size_t pos = 0;
    while (pos < all.size()) {
        size_t end = all.find('\n', pos);
        if (end == std::string::npos)
            end = all.size();
        const std::string one = all.substr(pos, end - pos);
        if (!runner.enqueue(one))
            rejected += "REJECT " + one + '\n';
        pos = end + 1;
    }
    for (int guard = 0; runner.busy() && guard < 1000000; guard++) {
        runner.tick(sink);
        sink.now += static_cast<unsigned long long>(tick_ms > 0 ? tick_ms : 1);
    }
    return put(rejected + sink.log, out, size);
}

EXPORT int srtoybox_settings_normalize(const char *ini, char *out, int size)
{
    return put(format_settings(parse_settings(ini == nullptr ? "" : ini)), out, size);
}

EXPORT int srtoybox_settings_store(const char *ini)
{
    return save_settings(parse_settings(ini == nullptr ? "" : ini)) ? 1 : 0;
}

EXPORT int srtoybox_settings_file(char *out, int size)
{
    return put(format_settings(load_settings()), out, size);
}

EXPORT int srtoybox_hotkey_name(int vk, int mods, char *out, int size)
{
    return put(hotkey_name(vk, mods), out, size);
}
```

- [ ] **Step 9: 모드 설명을 쓴다**

Create `mods/toybox/README.md`:

```markdown
# ToyBox — 게임 안 모드 설정 창

Supreme Ruler 2030 의 싱글플레이에서 쓰는 치트 창이다. 게임 화면 위에 창을 띄우고, 창의 단추가 게임의 내장 치트를 대신 넣는다.
설정은 플레이어가 지금 플레이 중인 국가에만 적용된다(게임이 플레이어에게만 적용하는 치트만 넣었다).

- 소스: `native/srtoybox/` (C++, Dear ImGui). 이 폴더에는 설명만 있다 — 모드의 파일은 DLL 하나다.
- 빌드: `uv run srkit toybox-build` → `build/toybox/srtoybox.dll`
- 설치: `uv run srkit deploy toybox --apply` (게임 폴더에 `srtoybox.dll` 한 개를 추가한다). 제거는 `undeploy`.
- **한글화 모드가 설치되어 있어야 동작한다.** 한글화의 훅(`WTSAPI32.dll`)이 이 DLL 을 불러온다.
- Workshop 으로는 배포할 수 없다(DLL 은 게임의 파일 로더를 거치지 않는다).

쓰는 법, 기능 목록, 한계는 [docs/10-toybox.md](../../docs/10-toybox.md).
```

- [ ] **Step 10: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox.py -q`
Expected: `빌드 완료: …\build\toybox\srtoybox.dll`, 그리고 `12 passed`. 빌드가 경고로 멈추면(`/WX`) 그 줄의 형 변환을 명시적으로 고친다 — 동작은 바꾸지 않는다.

- [ ] **Step 11: 전체 테스트와 명령 확인**

Run: `uv run pytest -q && uv run srkit info | tail -2`
Expected: `114 passed`. `info` 의 마지막 줄이 `ToyBox        : …\build\toybox\srtoybox.dll (빌드됨)`.

- [ ] **Step 12: 커밋 · PR · 머지**

```bash
git add src/srkit/hook.py src/srkit/toybox.py src/srkit/cli.py native/srtoybox mods/toybox tests/test_toybox.py
git status --short        # build/ 의 파일이 없어야 한다
git commit -F - <<'EOF'
feat: ToyBox 의 화면 없는 부분 — 기능 표, 명령, 실행기, 설정, 빌드

- 기능 16개: docs/07 에서 효과를 확인했고 게임이 플레이어에게만 적용하는 내장 치트. 테스트가 07 과 대조한다.
- 명령 한 개를 게임의 설정 창에 넣는 동작의 순서를 순수 함수로 만든다(gamedrive 가 밖에서 넣는 순서와 간격 그대로).
- 실행기: 대기열(최대 8개)과 간격 지키기. 보내는 쪽은 Sink 로 갈아 끼워 가짜 시계로 테스트한다.
- 설정: 단축키와 마지막 값. 깨진 파일과 범위 밖의 값은 기본값.
- srkit toybox-build → build/toybox/srtoybox.dll (모드 폴더에는 DLL 만 둔다)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin feat/toybox-core
gh pr create --base develop --head feat/toybox-core --title "feat: ToyBox 의 화면 없는 부분 — 기능 표, 명령, 실행기, 설정, 빌드" --body-file - <<'EOF'
ToyBox 1단계의 둘째 조각. 창을 그리기 전에, 화면 없이 테스트되는 부분을 먼저 만든다.

- **기능 표** 16개 — docs/07 에서 [확인: 효과]이고 대상이 "플레이어" 또는 "고른 부대"인 치트만. 테스트가 07 의 표와 대조하고, 넣지 않기로 한 치트가 하나도 없는지 본다.
- **명령 → 동작 목록**: 설정 창 열기(Ctrl+Shift+S) → `cheat allowcheats` → 명령 → ESC. `gamedrive.py` 가 밖에서 넣는(게임에서 확인된) 순서와 간격이다.
- **실행기**: 대기열 최대 8개, 틱이 아무리 빨라도 간격을 지킨다. 가짜 시계로 테스트한다.
- **설정**: 단축키와 기능별 마지막 값. 깨진 파일 · 범위 밖 · 모르는 키는 기본값.
- `srkit toybox-build`, `srkit info` 에 한 줄.

아직 게임에 붙는 코드는 없다(`srtoybox_start` 가 없어 훅이 불러와도 아무 일도 하지 않는다). 게임 폴더에 설치하지 않았다.

`uv run pytest` → 114 passed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr merge --merge feat/toybox-core
git switch develop && git pull origin develop
```

---

### Task 3: Dear ImGui 를 가져와 DLL 에 넣는다

브랜치: `feat/toybox-overlay` (`develop` 에서. Task 4 도 이 브랜치에서 이어서 한다 — PR 은 Task 4 끝에 올린다)

**Files:**
- Create: `native/third_party/imgui/` 아래 `imgui.cpp` `imgui_draw.cpp` `imgui_tables.cpp` `imgui_widgets.cpp` `imgui.h` `imgui_internal.h` `imconfig.h` `imstb_rectpack.h` `imstb_textedit.h` `imstb_truetype.h` `backends/imgui_impl_win32.h` `backends/imgui_impl_win32.cpp` `backends/imgui_impl_dx11.h` `backends/imgui_impl_dx11.cpp` `LICENSE.txt` `README.md`
- Modify: `src/srkit/toybox.py`
- Test: `tests/test_toybox.py` (추가)

**Interfaces:**
- Consumes: `toybox.build(cfg)`, `toybox.SOURCES`, `toybox.LIBS`, `toybox.FLAGS`
- Produces: `toybox.IMGUI_DIR = "native/third_party/imgui"`, `toybox.IMGUI_SOURCES: list[str]`; 우리 소스는 `#include "imgui.h"` · `"imgui_impl_win32.h"` · `"imgui_impl_dx11.h"` 를 쓸 수 있다(포함 경로에 `imgui/` 와 `imgui/backends/`). DLL 에 ImGui 가 링크된다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_toybox.py` 끝에 붙인다:

```python
IMGUI_FILES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp", "imgui.h", "imgui_internal.h", "imconfig.h",
               "imstb_rectpack.h", "imstb_textedit.h", "imstb_truetype.h", "backends/imgui_impl_win32.h",
               "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.h", "backends/imgui_impl_dx11.cpp", "LICENSE.txt", "README.md"]


def test_imgui_is_vendored_with_its_license_and_version(cfg):
    """외부 소스는 필요한 파일만, 라이선스와 함께, 버전을 적어 둔다."""
    root = cfg.root / toybox.IMGUI_DIR
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) == sorted(IMGUI_FILES)
    assert "MIT" in (root / "LICENSE.txt").read_text(encoding="utf-8")
    version = re.search(r'#define IMGUI_VERSION\s+"([^"]+)"', (root / "imgui.h").read_text(encoding="utf-8"))[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert f"v{version}" in readme and "github.com/ocornut/imgui" in readme
    assert [s for s in toybox.IMGUI_SOURCES if not (root / s).is_file()] == []
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox.py::test_imgui_is_vendored_with_its_license_and_version -q`
Expected: `AttributeError: module 'srkit.toybox' has no attribute 'IMGUI_DIR'` 로 FAIL.

- [ ] **Step 3: 받을 것을 확인하고 내려받는다**

출처는 공식 저장소의 최신 릴리스다(설계 승인에 포함된 내려받기). 태그와 크기를 먼저 보고 채팅에 한 줄로 알린다("Dear ImGui `<태그>` 소스 묶음, github.com/ocornut/imgui, 약 N MB").

```bash
TAG=$(gh api repos/ocornut/imgui/releases/latest --jq .tag_name); echo "$TAG"
curl -sIL "https://github.com/ocornut/imgui/archive/refs/tags/$TAG.zip" | grep -i "^content-length\|^HTTP" | tail -2
curl -sL -o "$S/imgui-$TAG.zip" "https://github.com/ocornut/imgui/archive/refs/tags/$TAG.zip" && ls -la "$S/imgui-$TAG.zip"
```

Expected: 태그가 `v1.9x.y` 꼴이고(뒤에 `-docking` 이 붙지 않은 것) zip 이 1 ~ 3 MB 다. 태그가 그 꼴이 아니면 멈추고 `gh api repos/ocornut/imgui/releases --jq '.[].tag_name' | head` 로 `-docking` 이 아닌 가장 새 태그를 고른다.

- [ ] **Step 4: 필요한 파일만 꺼내고 README 를 쓴다**

`$S/vendor_imgui.py` 를 Write 도구로 만든다(임시 스크립트 — 저장소에 넣지 않는다):

```python
"""Dear ImGui 릴리스 묶음에서 필요한 파일만 native/third_party/imgui/ 로 꺼낸다. 인자: <zip 경로> <태그>"""
import sys
import zipfile
from datetime import date
from pathlib import Path

zip_path, tag = Path(sys.argv[1]), sys.argv[2]
out = Path("native/third_party/imgui")
files = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp", "imgui.h", "imgui_internal.h", "imconfig.h",
         "imstb_rectpack.h", "imstb_textedit.h", "imstb_truetype.h", "backends/imgui_impl_win32.h", "backends/imgui_impl_win32.cpp",
         "backends/imgui_impl_dx11.h", "backends/imgui_impl_dx11.cpp", "LICENSE.txt"]
with zipfile.ZipFile(zip_path) as z:
    top = z.namelist()[0].split("/")[0]
    for name in files:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(f"{top}/{name}"))
(out / "README.md").write_text(
    f"# Dear ImGui {tag}\n\n"
    f"- 출처: <https://github.com/ocornut/imgui> 의 릴리스 `{tag}` (받은 날 {date.today().isoformat()})\n"
    "- 라이선스: MIT (`LICENSE.txt`)\n"
    "- 넣은 것: 코어 4개와 헤더, Win32 · DirectX 11 백엔드. 데모(`imgui_demo.cpp`)와 다른 백엔드 · 예제는 넣지 않았다\n"
    "- 고치지 않았다. 버전을 올릴 때는 같은 파일을 새 릴리스의 것으로 통째로 바꾼다\n"
    "- 쓰는 곳: `native/srtoybox/` (게임 안 모드 설정 창). 빌드는 `uv run srkit toybox-build`\n",
    encoding="utf-8", newline="\n")
print(sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()))
```

Run: `uv run python "$S/vendor_imgui.py" "$S/imgui-$TAG.zip" "$TAG" && du -sh native/third_party/imgui`
Expected: 파일 16개의 목록, 크기 2 ~ 4 MB.

- [ ] **Step 5: 빌드에 넣는다**

`src/srkit/toybox.py` 의 상수와 `build` 를 고친다. `LIBS` 와 `FLAGS` 다음에 넣는다:

```python
IMGUI_DIR = "native/third_party/imgui"
IMGUI_SOURCES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp",
                 "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.cpp"]
IMGUI_DEFINES = "/DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD"    # 게임패드는 쓰지 않는다(XInput 을 불러오지 않게)
```

`LIBS` 를 바꾼다:

```python
LIBS = ["kernel32.lib", "user32.lib", "gdi32.lib", "imm32.lib", "dwmapi.lib", "d3d11.lib", "dxgi.lib", "d3dcompiler.lib"]
```

`build` 의 `ours`/`objs`/`script` 부분을 바꾼다:

```python
    imgui = cfg.root / IMGUI_DIR
    ours = [src / name for name in SOURCES]
    theirs = [imgui / name for name in IMGUI_SOURCES]
    objs = [obj / (p.stem + ".obj") for p in ours + theirs]
    include = f'/I"{imgui}" /I"{imgui / "backends"}" {IMGUI_DEFINES}'
    script = obj / "build.cmd"
    script.write_text(
        "@echo off\r\n"
        f'call "{hook.vcvars()}" >nul || exit /b 1\r\n'
        f'cl {FLAGS} /W3 {include} /Fo"{obj}\\\\" {_quoted(theirs)} || exit /b 1\r\n'          # 외부 소스: 경고를 오류로 치지 않는다
        f'cl {FLAGS} /W4 /WX {include} /Fo"{obj}\\\\" {_quoted(ours)} || exit /b 1\r\n'
        f'link /NOLOGO /DLL /OUT:"{out}" /IMPLIB:"{obj / "srtoybox.lib"}" {_quoted(objs)} {" ".join(LIBS)} || exit /b 1\r\n',
        encoding="mbcs")
```

- [ ] **Step 6: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox.py -q && ls -la build/toybox/`
Expected: 빌드 완료, `13 passed`, `build/toybox/` 에 `srtoybox.dll` 하나(크기가 Task 2 때보다 커졌다 — 링커가 안 쓰는 코드를 버리므로 크게 늘지 않을 수 있다).

- [ ] **Step 7: 전체 테스트와 커밋** (PR 은 Task 4 끝에)

```bash
uv run pytest -q          # 115 passed
git add native/third_party/imgui src/srkit/toybox.py tests/test_toybox.py
git commit -F - <<'EOF'
build: Dear ImGui 를 가져와 ToyBox DLL 에 넣는다

공식 릴리스에서 코어 4개, 헤더, Win32 · DirectX 11 백엔드와 LICENSE(MIT)만 가져왔다. 고치지 않았다.
버전과 출처는 native/third_party/imgui/README.md. 외부 소스는 /W3, 우리 소스는 /W4 /WX 로 빌드한다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: 게임 화면에 창이 뜨고, 단추가 치트를 넣는다

브랜치: `feat/toybox-overlay` (Task 3 에 이어서)

**Files:**
- Create: `native/srtoybox/log.h`, `log.cpp`, `runner_win.h`, `runner_win.cpp`, `overlay.h`, `overlay.cpp`, `input.h`, `input.cpp`, `ui.h`, `ui.cpp`
- Modify: `native/srtoybox/exports.cpp` (`srtoybox_start`), `src/srkit/toybox.py` (`SOURCES`)
- Test: `tests/test_toybox.py` (추가), 게임 안 확인(근거는 `build/verify/toybox/`)

**Interfaces:**
- Consumes: Task 2 의 `FEATURES` `FEATURE_COUNT` `build_command` `Runner` `Sink` `Act` `Settings` `load_settings` `save_settings` `valid_hotkey` `hotkey_name` `settings_dir` `HOTKEY_*`; Task 1 의 불러오기(`srtoybox_start` 를 부른다); Task 3 의 ImGui
- Produces:
  - `void log_line(const char *fmt, ...)` — `settings_dir()\toybox.log` 에 한 줄
  - `bool runner_enqueue(const std::string &command)`, `void runner_tick(HWND hwnd)`(창 스레드에서만), `bool runner_injecting()`, `int runner_pending()`, `std::string runner_last()`
  - `bool overlay_install()`, `bool overlay_ready()`, `std::recursive_mutex &ui_mutex()`
  - `void input_install(HWND game_window)`
  - `void ui_init()`, `bool ui_visible()`, `void ui_toggle()`, `bool ui_is_hotkey(int vk, int mods)`, `bool ui_hit(int x, int y)`, `bool ui_capturing_hotkey()`, `void ui_capture_key(int vk, int mods)`, `void ui_draw()`
  - DLL 내보내기 `void WINAPI srtoybox_start(void)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_toybox.py` 의 import 에 `os`, `shutil`, `subprocess`, `sys`, `time` 과 `from srkit import hook` 을 더하고 끝에 붙인다:

```python
START_PROBE = "import ctypes, sys, time; ctypes.WinDLL(sys.argv[1]); time.sleep(float(sys.argv[2]))"


def test_the_hook_starts_toybox_and_it_writes_a_log(dll, cfg, tmp_path):
    """훅이 불러와 srtoybox_start 를 부르면 로그에 시작 줄이 생긴다. 게임이 아닌 프로세스에서도 죽지 않는다."""
    if not hook.output(cfg).is_file():
        pytest.skip("훅 DLL 미빌드 (srkit hook-build)")
    home = tmp_path / "home"
    home.mkdir()
    shutil.copyfile(hook.output(cfg), tmp_path / "hookcopy.dll")
    shutil.copyfile(toybox.output(cfg), tmp_path / toybox.DLL_NAME)
    run = subprocess.run([sys.executable, "-c", START_PROBE, str(tmp_path / "hookcopy.dll"), "8"], capture_output=True, text=True,
                         env={**os.environ, "SRTOYBOX_HOME": str(home)}, timeout=60)
    assert run.returncode == 0, run.stderr
    log = (home / "toybox.log").read_text(encoding="utf-8")
    assert "시작" in log and ("끼어들었습니다" in log or "끼어들지 못했습니다" in log), log
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox.py::test_the_hook_starts_toybox_and_it_writes_a_log -q`
Expected: `FileNotFoundError: … toybox.log` 로 FAIL(DLL 에 `srtoybox_start` 가 없어 아무 일도 일어나지 않는다).

- [ ] **Step 3: 로그와 게임 쪽 실행기를 쓴다**

Create `native/srtoybox/log.h`:

```cpp
// 설정 폴더의 toybox.log 에 한 줄씩 덧붙인다. 문제가 생겼을 때 볼 곳은 여기 하나다.
#pragma once

void log_line(const char *fmt, ...);
```

Create `native/srtoybox/log.cpp`:

```cpp
#include "log.h"

#include <windows.h>

#include <cstdarg>
#include <cstdio>
#include <string>

#include "settings.h"

void log_line(const char *fmt, ...)
{
    char text[400], line[480];
    va_list args;
    va_start(args, fmt);
    vsnprintf(text, sizeof(text), fmt, args);
    va_end(args);

    SYSTEMTIME t;
    GetLocalTime(&t);
    int n = snprintf(line, sizeof(line), "%04d-%02d-%02d %02d:%02d:%02d %s\r\n", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute,
                     t.wSecond, text);
    if (n <= 0)
        return;
    if (n >= static_cast<int>(sizeof(line)))
        n = static_cast<int>(sizeof(line)) - 1;

    const std::wstring dir = settings_dir();
    if (dir.empty())
        return;
    const HANDLE f = CreateFileW((dir + L"\\toybox.log").c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                                 OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE)
        return;
    DWORD written = 0;
    WriteFile(f, line, static_cast<DWORD>(n), &written, nullptr);
    CloseHandle(f);
}
```

Create `native/srtoybox/runner_win.h`:

```cpp
// 게임 안의 실행기: Runner(runner.h)에 게임 창으로 실제로 보내는 Sink 를 물린 것.
#pragma once

#include <windows.h>

#include <string>

bool runner_enqueue(const std::string &command);   // 받지 못하면 false (가득 참)
void runner_tick(HWND hwnd);                       // 게임 창을 가진 스레드에서만 부른다(키 상태표가 그 스레드의 것이다)
bool runner_injecting();                           // 넣는 중인가 — 그동안의 키 메시지는 입력 끼어들기가 게임에 그대로 넘긴다
int runner_pending();
std::string runner_last();
```

Create `native/srtoybox/runner_win.cpp`:

```cpp
#include "runner_win.h"

#include <mutex>

#include "runner.h"

namespace {

std::mutex g_lock;      // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
Runner g_runner;
BYTE g_before[2];       // 넣기 전의 Ctrl · Shift 상태

// scripts/gamedrive.py 가 밖에서 하는 일과 같다: 키 상태표에 수정키를 눌린 것으로 적고 메시지를 보낸다.
struct GameSink : Sink {
    HWND hwnd;
    explicit GameSink(HWND h) : hwnd(h) {}

    void mods(bool on) override
    {
        static const int keys[2] = {VK_CONTROL, VK_SHIFT};
        BYTE state[256];
        if (!GetKeyboardState(state))
            return;
        for (int i = 0; i < 2; i++) {
            bool down = true;
            if (on) {
                g_before[i] = state[keys[i]];
            } else if (GetForegroundWindow() == hwnd) {
                down = GetAsyncKeyState(keys[i]) < 0;   // 넣는 동안 사용자가 키를 떼거나 눌렀을 수 있다 — 실제 상태에 맞춘다
            } else {
                down = (g_before[i] & 0x80) != 0;       // 창이 뒤에 있으면 실제 키는 이 창의 것이 아니다 — 넣기 전으로
            }
            state[keys[i]] = static_cast<BYTE>((state[keys[i]] & 0x7F) | (down ? 0x80 : 0));
        }
        SetKeyboardState(state);
    }

    void key(Act act, int value) override
    {
        const WPARAM w = static_cast<WPARAM>(value);
        if (act == Act::Down)
            PostMessageW(hwnd, WM_KEYDOWN, w, 1);
        else if (act == Act::Up)
            PostMessageW(hwnd, WM_KEYUP, w, 0xC0000001);
        else
            PostMessageW(hwnd, WM_CHAR, w, 1);
    }

    unsigned long long now_ms() override { return GetTickCount64(); }
};

}  // namespace

bool runner_enqueue(const std::string &command)
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.enqueue(command);
}

void runner_tick(HWND hwnd)
{
    std::lock_guard<std::mutex> lock(g_lock);
    GameSink sink(hwnd);
    g_runner.tick(sink);
}

bool runner_injecting()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.busy();
}

int runner_pending()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return static_cast<int>(g_runner.pending());
}

std::string runner_last()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.last();
}
```

- [ ] **Step 4: 창의 내용을 쓴다**

Create `native/srtoybox/ui.h`:

```cpp
// 모드 설정 창의 상태와 내용. 그리기(ui_draw)는 ImGui 프레임 안에서, 나머지는 어느 스레드에서 불러도 된다.
#pragma once

void ui_init();                           // 설정을 읽는다
bool ui_visible();
void ui_toggle();
bool ui_is_hotkey(int vk, int mods);      // 창을 여닫는 단축키인가
bool ui_hit(int x, int y);                // 이 점(창의 클라이언트 좌표)이 열려 있는 설정 창 위인가
bool ui_capturing_hotkey();               // "단축키 바꾸기"를 누르고 새 조합을 기다리는 중인가
void ui_capture_key(int vk, int mods);    // 그때 눌린 키. 수정키만이면 더 기다리고, ESC 만이면 취소한다
void ui_draw();
```

Create `native/srtoybox/ui.cpp`:

```cpp
#include "ui.h"

#include <cstring>
#include <mutex>
#include <string>

#include "command.h"
#include "features.h"
#include "imgui.h"
#include "overlay.h"
#include "runner_win.h"
#include "settings.h"

namespace {

typedef std::lock_guard<std::recursive_mutex> Lock;

Settings g_settings;
bool g_visible, g_capturing;
float g_rect[4];          // 창의 왼쪽 · 위 · 오른쪽 · 아래 (지난 프레임)
std::string g_confirm;    // 한 번 더 누르기를 기다리는 기능의 id
std::string g_notice;

void row(const Feature &f)
{
    ImGui::PushID(f.id);
    long long value = 0;
    if (f.has_value) {
        long long &stored = g_settings.values[f.id];
        ImGui::SetNextItemWidth(150.0f);
        if (ImGui::InputScalar("##value", ImGuiDataType_S64, &stored)) {
            stored = stored < f.min ? f.min : stored > f.max ? f.max : stored;
            save_settings(g_settings);
        }
        value = stored;
        ImGui::SameLine();
    }
    const bool asking = f.confirm && g_confirm == f.id;
    const std::string label = std::string(asking ? "한 번 더 누르면 실행합니다" : f.label) + "###run";
    if (ImGui::Button(label.c_str())) {
        if (f.confirm && !asking) {
            g_confirm = f.id;
        } else {
            g_confirm.clear();
            g_notice = runner_enqueue(build_command(f, value)) ? "" : "대기 중인 명령이 많아 받지 못했습니다.";
        }
    }
    ImGui::TextDisabled("%s", f.help);
    ImGui::Spacing();
    ImGui::PopID();
}

void settings_tab()
{
    ImGui::Text("창 여닫기: %s", hotkey_name(g_settings.hotkey_vk, g_settings.hotkey_mods).c_str());
    if (g_capturing)
        ImGui::TextUnformatted("새 조합을 누르십시오. ESC 는 취소입니다.");
    else if (ImGui::Button("단축키 바꾸기"))
        g_capturing = true;
    ImGui::Spacing();
    ImGui::TextDisabled("설정은 %%APPDATA%%\\SR2030ToyBox 에 저장됩니다.");
}

}  // namespace

void ui_init()
{
    Lock lock(ui_mutex());
    g_settings = load_settings();
}

bool ui_visible()
{
    Lock lock(ui_mutex());
    return g_visible;
}

void ui_toggle()
{
    Lock lock(ui_mutex());
    g_visible = !g_visible;
    g_capturing = false;
    g_confirm.clear();
}

bool ui_is_hotkey(int vk, int mods)
{
    Lock lock(ui_mutex());
    return vk == g_settings.hotkey_vk && mods == g_settings.hotkey_mods;
}

bool ui_hit(int x, int y)
{
    Lock lock(ui_mutex());
    const float fx = static_cast<float>(x), fy = static_cast<float>(y);
    return g_visible && fx >= g_rect[0] && fx < g_rect[2] && fy >= g_rect[1] && fy < g_rect[3];
}

bool ui_capturing_hotkey()
{
    Lock lock(ui_mutex());
    return g_visible && g_capturing;
}

void ui_capture_key(int vk, int mods)
{
    Lock lock(ui_mutex());
    if (vk == 0x10 || vk == 0x11 || vk == 0x12)   // Shift · Ctrl · Alt 만 눌린 동안은 더 기다린다
        return;
    g_capturing = false;
    if (valid_hotkey(vk, mods)) {                 // ESC 만 누른 것은 valid_hotkey 가 거른다 = 취소
        g_settings.hotkey_vk = vk;
        g_settings.hotkey_mods = mods;
        save_settings(g_settings);
    }
}

void ui_draw()
{
    Lock lock(ui_mutex());
    ImGui::SetNextWindowPos(ImVec2(40.0f, 60.0f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(500.0f, 460.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("SR2030 ToyBox", nullptr, ImGuiWindowFlags_NoCollapse)) {
        if (ImGui::BeginTabBar("tabs")) {
            const char *tab = nullptr;
            for (int i = 0; i < FEATURE_COUNT; i++) {
                if (tab != nullptr && strcmp(tab, FEATURES[i].tab) == 0)
                    continue;   // 이 탭은 앞에서 그렸다(같은 탭의 기능은 표에서 이어져 있다)
                tab = FEATURES[i].tab;
                if (ImGui::BeginTabItem(tab)) {
                    for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                        row(FEATURES[j]);
                    ImGui::EndTabItem();
                }
            }
            if (ImGui::BeginTabItem("설정")) {
                settings_tab();
                ImGui::EndTabItem();
            }
            ImGui::EndTabBar();
        }
        ImGui::Separator();
        const int pending = runner_pending();
        const std::string last = runner_last();
        if (pending > 0)
            ImGui::Text("넣는 중: %s (남은 것 %d)", last.c_str(), pending);
        else if (!last.empty())
            ImGui::Text("마지막으로 넣은 것: %s", last.c_str());
        if (!g_notice.empty())
            ImGui::TextUnformatted(g_notice.c_str());
        ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        ImGui::TextWrapped("게임을 진행하는 중에만 누르십시오. 메뉴나 로비에서는 글자가 다른 곳에 들어갈 수 있습니다.");
    }
    const ImVec2 pos = ImGui::GetWindowPos(), size = ImGui::GetWindowSize();
    g_rect[0] = pos.x;
    g_rect[1] = pos.y;
    g_rect[2] = pos.x + size.x;
    g_rect[3] = pos.y + size.y;
    ImGui::End();
}
```

- [ ] **Step 5: 입력 끼어들기를 쓴다**

Create `native/srtoybox/input.h`:

```cpp
// 게임 창의 창 프로시저를 감싼다: 실행기의 타이머, 여닫는 단축키, 설정 창으로 가는 입력.
#pragma once

#include <windows.h>

void input_install(HWND game_window);
```

Create `native/srtoybox/input.cpp`:

```cpp
#include "input.h"

#include <windowsx.h>

#include <mutex>

#include "imgui.h"
#include "imgui_impl_win32.h"
#include "overlay.h"
#include "runner_win.h"
#include "settings.h"
#include "ui.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

namespace {

const UINT_PTR TIMER_ID = 0x7B0C0001;   // 게임의 타이머와 겹치지 않을 값
WNDPROC g_original;
bool g_unicode, g_timer;

// 게임 창의 문자 방식(A/W)대로 넘긴다 — 글자 메시지의 변환이 달라지지 않게
LRESULT pass(HWND h, UINT m, WPARAM w, LPARAM l)
{
    return g_unicode ? CallWindowProcW(g_original, h, m, w, l) : CallWindowProcA(g_original, h, m, w, l);
}

int mods_now()
{
    return (GetKeyState(VK_CONTROL) < 0 ? HOTKEY_CTRL : 0) | (GetKeyState(VK_SHIFT) < 0 ? HOTKEY_SHIFT : 0)
        | (GetKeyState(VK_MENU) < 0 ? HOTKEY_ALT : 0);
}

bool is_key(UINT m) { return m >= WM_KEYFIRST && m <= WM_KEYLAST; }
bool is_mouse(UINT m) { return m >= WM_MOUSEFIRST && m <= WM_MOUSELAST; }

LRESULT CALLBACK wrapped(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!g_timer)
        g_timer = SetTimer(h, TIMER_ID, 10, nullptr) != 0;   // 이 함수는 창을 가진 스레드에서 불린다 — 타이머도 그 스레드의 것이 된다
    if (m == WM_TIMER && w == TIMER_ID) {
        runner_tick(h);
        return 0;
    }
    if (is_key(m) && runner_injecting())
        return pass(h, m, w, l);                             // 실행기가 넣는 중이다 — 설정 창이 가로채지 않는다
    if (m == WM_KEYDOWN || m == WM_SYSKEYDOWN) {
        const int vk = static_cast<int>(w);
        if (ui_capturing_hotkey()) {
            ui_capture_key(vk, mods_now());
            return 0;
        }
        if (!(l & 0x40000000) && ui_is_hotkey(vk, mods_now())) {   // 누르고 있어서 반복되는 것은 세지 않는다
            ui_toggle();
            return 0;
        }
    }
    // WM_MOUSELEAVE 는 넘기지 않는다: 화면 밖 검증에서는 실제 마우스가 창 밖이라, 넘기면 ImGui 가 마우스 위치를 지운다
    if ((is_key(m) || is_mouse(m)) && ui_visible() && overlay_ready()) {
        bool swallow = false;
        {
            std::lock_guard<std::recursive_mutex> lock(ui_mutex());
            ImGuiIO &io = ImGui::GetIO();
            const bool positioned = is_mouse(m) && m != WM_MOUSEWHEEL && m != WM_MOUSEHWHEEL;   // 휠의 좌표는 화면 좌표다
            if (positioned)
                io.AddMousePosEvent(static_cast<float>(GET_X_LPARAM(l)), static_cast<float>(GET_Y_LPARAM(l)));
            ImGui_ImplWin32_WndProcHandler(h, m, w, l);
            if (is_mouse(m))   // 창 위인지는 사각형으로 직접 가린다 — ImGui 의 판단(WantCaptureMouse)은 한 프레임 늦다
                swallow = (positioned && ui_hit(GET_X_LPARAM(l), GET_Y_LPARAM(l))) || io.WantCaptureMouse;
            else
                swallow = io.WantCaptureKeyboard;
        }
        if (swallow)
            return 0;
    }
    return pass(h, m, w, l);
}

}  // namespace

void input_install(HWND game)
{
    g_unicode = IsWindowUnicode(game) != FALSE;
    if (g_unicode) {
        g_original = reinterpret_cast<WNDPROC>(GetWindowLongPtrW(game, GWLP_WNDPROC));
        SetWindowLongPtrW(game, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wrapped));
    } else {
        g_original = reinterpret_cast<WNDPROC>(GetWindowLongPtrA(game, GWLP_WNDPROC));
        SetWindowLongPtrA(game, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wrapped));
    }
}
```

- [ ] **Step 6: 화면 끼어들기를 쓴다**

Create `native/srtoybox/overlay.h`:

```cpp
// 게임이 화면을 내보내는 자리(swap chain 의 Present)에 끼어들어 ImGui 로 설정 창을 그린다.
// 실행 파일의 주소를 쓰지 않는다: 임시 swap chain 에서 가상 함수 표의 주소를 얻는다.
#pragma once

#include <mutex>

bool overlay_install();                 // 끼어든다. 실패하면 false — 게임은 그대로 돈다
bool overlay_ready();                   // ImGui 가 준비됐다(게임의 첫 Present 뒤)
std::recursive_mutex &ui_mutex();       // ImGui 와 창의 상태를 만지는 곳은 이 잠금 안에서 (그리기 · 입력 전달 · ui_*)
```

Create `native/srtoybox/overlay.cpp`:

```cpp
#include "overlay.h"

#include <windows.h>

#include <d3d11.h>
#include <dxgi1_2.h>

#include <string>

#include "imgui.h"
#include "imgui_impl_dx11.h"
#include "imgui_impl_win32.h"
#include "input.h"
#include "log.h"
#include "settings.h"
#include "ui.h"

namespace {

typedef HRESULT(STDMETHODCALLTYPE *PresentFn)(IDXGISwapChain *, UINT, UINT);
typedef HRESULT(STDMETHODCALLTYPE *Present1Fn)(IDXGISwapChain1 *, UINT, UINT, const DXGI_PRESENT_PARAMETERS *);
typedef HRESULT(STDMETHODCALLTYPE *ResizeFn)(IDXGISwapChain *, UINT, UINT, UINT, DXGI_FORMAT, UINT);

const int SLOT_PRESENT = 8, SLOT_RESIZE = 13, SLOT_PRESENT1 = 22;   // IDXGISwapChain · IDXGISwapChain1 의 가상 함수 번호

PresentFn g_present;
Present1Fn g_present1;
ResizeFn g_resize;
IDXGISwapChain *g_swap;                  // 게임의 swap chain (처음 걸린 것)
ID3D11Device *g_device;
ID3D11DeviceContext *g_context;
ID3D11RenderTargetView *g_target;
bool g_ready, g_failed;
std::string g_ini_path;
thread_local bool t_inside;              // Present 가 안에서 Present1 을 부르는 경우에 두 번 그리지 않게

std::string utf8(const std::wstring &w)
{
    if (w.empty())
        return std::string();
    const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), nullptr, 0, nullptr, nullptr);
    std::string out(static_cast<size_t>(n), '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), &out[0], n, nullptr, nullptr);
    return out;
}

// 게임의 첫 Present 에서 한 번. 게임이 그리는 창이 곧 주 창이다.
bool init(IDXGISwapChain *swap)
{
    DXGI_SWAP_CHAIN_DESC desc;
    DWORD pid = 0;
    if (FAILED(swap->GetDesc(&desc)) || desc.OutputWindow == nullptr)
        return false;
    GetWindowThreadProcessId(desc.OutputWindow, &pid);
    if (pid != GetCurrentProcessId())
        return false;
    if (FAILED(swap->GetDevice(__uuidof(ID3D11Device), reinterpret_cast<void **>(&g_device)))) {
        g_failed = true;
        log_line("DirectX 11 장치가 아닙니다 — ToyBox 는 그리지 않습니다");
        return false;
    }
    g_device->GetImmediateContext(&g_context);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    const std::wstring dir = settings_dir();
    g_ini_path = dir.empty() ? std::string() : utf8(dir + L"\\imgui.ini");
    io.IniFilename = g_ini_path.empty() ? nullptr : g_ini_path.c_str();
    io.ConfigFlags |= ImGuiConfigFlags_NoMouseCursorChange;   // 게임의 마우스 커서를 건드리지 않는다

    wchar_t windir[MAX_PATH];
    std::wstring font;
    if (GetWindowsDirectoryW(windir, MAX_PATH) > 0)
        font = std::wstring(windir) + L"\\Fonts\\malgun.ttf";
    if (!font.empty() && GetFileAttributesW(font.c_str()) != INVALID_FILE_ATTRIBUTES)
        io.Fonts->AddFontFromFileTTF(utf8(font).c_str(), 18.0f, nullptr, io.Fonts->GetGlyphRangesKorean());
    else
        log_line("맑은 고딕(malgun.ttf)이 없습니다 — 한글이 깨져 보입니다");
    ImGui::StyleColorsDark();

    if (!ImGui_ImplWin32_Init(desc.OutputWindow) || !ImGui_ImplDX11_Init(g_device, g_context)) {
        g_failed = true;
        log_line("ImGui 초기화에 실패했습니다 — ToyBox 는 그리지 않습니다");
        return false;
    }
    g_swap = swap;
    g_ready = true;
    input_install(desc.OutputWindow);
    log_line("창 준비됨 (%ux%u)", desc.BufferDesc.Width, desc.BufferDesc.Height);
    return true;
}

void draw(IDXGISwapChain *swap)
{
    std::lock_guard<std::recursive_mutex> lock(ui_mutex());
    if (g_failed || (!g_ready && !init(swap)) || swap != g_swap || !ui_visible())
        return;
    if (g_target == nullptr) {
        ID3D11Texture2D *back = nullptr;
        if (FAILED(swap->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void **>(&back))))
            return;
        const HRESULT hr = g_device->CreateRenderTargetView(back, nullptr, &g_target);
        back->Release();
        if (FAILED(hr)) {
            g_target = nullptr;
            return;
        }
    }
    ImGui_ImplDX11_NewFrame();
    ImGui_ImplWin32_NewFrame();
    ImGui::NewFrame();
    ui_draw();
    ImGui::Render();

    ID3D11RenderTargetView *old_target = nullptr;   // 게임이 걸어 둔 렌더 대상을 돌려놓는다
    ID3D11DepthStencilView *old_depth = nullptr;
    g_context->OMGetRenderTargets(1, &old_target, &old_depth);
    g_context->OMSetRenderTargets(1, &g_target, nullptr);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    g_context->OMSetRenderTargets(1, &old_target, old_depth);
    if (old_target != nullptr)
        old_target->Release();
    if (old_depth != nullptr)
        old_depth->Release();
}

void draw_once(IDXGISwapChain *swap, UINT flags)
{
    if (t_inside || (flags & DXGI_PRESENT_TEST))
        return;
    t_inside = true;
    draw(swap);
    t_inside = false;
}

HRESULT STDMETHODCALLTYPE hooked_present(IDXGISwapChain *swap, UINT sync, UINT flags)
{
    draw_once(swap, flags);
    t_inside = true;
    const HRESULT hr = g_present(swap, sync, flags);
    t_inside = false;
    return hr;
}

HRESULT STDMETHODCALLTYPE hooked_present1(IDXGISwapChain1 *swap, UINT sync, UINT flags, const DXGI_PRESENT_PARAMETERS *params)
{
    const bool outer = !t_inside;
    if (outer)
        draw_once(swap, flags);
    t_inside = true;
    const HRESULT hr = g_present1(swap, sync, flags, params);
    if (outer)
        t_inside = false;
    return hr;
}

HRESULT STDMETHODCALLTYPE hooked_resize(IDXGISwapChain *swap, UINT count, UINT width, UINT height, DXGI_FORMAT format, UINT flags)
{
    {
        std::lock_guard<std::recursive_mutex> lock(ui_mutex());
        if (swap == g_swap && g_target != nullptr) {   // 뒷면을 쥐고 있으면 크기를 바꾸지 못한다
            g_target->Release();
            g_target = nullptr;
        }
    }
    return g_resize(swap, count, width, height, format, flags);
}

bool patch(void **table, int index, void *replacement, void **original)
{
    DWORD old = 0;
    if (!VirtualProtect(&table[index], sizeof(void *), PAGE_READWRITE, &old))
        return false;
    *original = table[index];   // 원래 것을 먼저 적어 둔다 — 바꾸자마자 불려도 넘길 곳이 있다
    table[index] = replacement;
    VirtualProtect(&table[index], sizeof(void *), old, &old);
    return true;
}

}  // namespace

std::recursive_mutex &ui_mutex()
{
    static std::recursive_mutex m;   // Present 안에서 창 메시지가 같은 스레드로 들어올 수 있어 재진입을 허용한다
    return m;
}

bool overlay_ready()
{
    std::lock_guard<std::recursive_mutex> lock(ui_mutex());
    return g_ready;
}

bool overlay_install()
{
    const HINSTANCE instance = GetModuleHandleW(nullptr);
    WNDCLASSEXW wc = {};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = instance;
    wc.lpszClassName = L"srtoybox.probe";
    RegisterClassExW(&wc);
    const HWND probe = CreateWindowExW(0, wc.lpszClassName, L"", WS_OVERLAPPEDWINDOW, 0, 0, 64, 64, nullptr, nullptr, instance, nullptr);
    if (probe == nullptr) {
        log_line("임시 창을 만들지 못했습니다 (%lu)", GetLastError());
        return false;
    }

    DXGI_SWAP_CHAIN_DESC desc = {};
    desc.BufferCount = 1;
    desc.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.OutputWindow = probe;
    desc.SampleDesc.Count = 1;
    desc.Windowed = TRUE;
    IDXGISwapChain *swap = nullptr;
    ID3D11Device *device = nullptr;
    ID3D11DeviceContext *context = nullptr;
    HRESULT hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &desc,
                                               &swap, &device, nullptr, &context);
    if (FAILED(hr))
        hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &desc, &swap,
                                           &device, nullptr, &context);
    bool ok = false;
    if (SUCCEEDED(hr)) {
        void **table = *reinterpret_cast<void ***>(swap);
        ok = patch(table, SLOT_PRESENT, reinterpret_cast<void *>(hooked_present), reinterpret_cast<void **>(&g_present))
            && patch(table, SLOT_RESIZE, reinterpret_cast<void *>(hooked_resize), reinterpret_cast<void **>(&g_resize));
        IDXGISwapChain1 *swap1 = nullptr;
        if (ok && SUCCEEDED(swap->QueryInterface(__uuidof(IDXGISwapChain1), reinterpret_cast<void **>(&swap1)))) {
            patch(*reinterpret_cast<void ***>(swap1), SLOT_PRESENT1, reinterpret_cast<void *>(hooked_present1),
                  reinterpret_cast<void **>(&g_present1));
            swap1->Release();
        }
        context->Release();
        device->Release();
        swap->Release();
    }
    DestroyWindow(probe);
    UnregisterClassW(wc.lpszClassName, instance);
    if (ok)
        log_line("화면에 끼어들었습니다");
    else
        log_line("화면에 끼어들지 못했습니다 (0x%08lX) — ToyBox 는 동작하지 않습니다", static_cast<unsigned long>(hr));
    return ok;
}
```

- [ ] **Step 7: 시작 함수를 더하고 빌드 목록을 늘린다**

`native/srtoybox/exports.cpp` 의 include 에 `<windows.h>`(맨 위), `"log.h"`, `"overlay.h"`, `"ui.h"` 를 더하고, 머리 주석을 `// 테스트(tests/test_toybox.py)와 불러오는 쪽(srhook)이 쓰는 C 인터페이스. …` 로 고친 뒤 파일 끝에 붙인다:

```cpp
// srhook 이 이 DLL 을 불러온 뒤 한 번 부른다(불러온 스레드에서). 게임의 창은 기다리지 않는다 — 첫 Present 에서 얻는다.
EXPORT void WINAPI srtoybox_start(void)
{
    log_line("시작 (프로세스 %lu)", GetCurrentProcessId());
    ui_init();
    overlay_install();
}
```

`src/srkit/toybox.py` 의 `SOURCES` 를 바꾼다:

```python
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "overlay.cpp"]
```

- [ ] **Step 8: 빌드하고 자동 테스트가 통과하는지 본다**

Run: `uv run srkit hook-build && uv run srkit toybox-build && uv run pytest -q`
Expected: 빌드 완료 두 줄, `116 passed`. 빌드가 경고로 멈추면 그 줄을 고친다(형 변환을 명시적으로 — 동작은 바꾸지 않는다). ImGui 의 함수 이름이 받은 버전과 달라 컴파일이 안 되면 `native/third_party/imgui/imgui.h` 에서 같은 일을 하는 선언을 찾아 맞추고, 무엇을 바꿨는지 ledger 에 `Ruling:` 으로 적는다.

- [ ] **Step 9: 게임에 설치하고 창이 뜨는지 본다 — G1, G2 와 수정키 확인**

게임이 꺼져 있는지 먼저 본다: `gd status` → `프로세스: 없음`. 사용자가 켠 게임이 떠 있으면 건드리지 않고 기다린다.

```bash
cp build/srhook/WTSAPI32.dll build/korean/WTSAPI32.dll      # srkit build 가 하는 복사와 같다(한글화의 다른 파일은 건드리지 않는다)
uv run srkit deploy korean                                   # 미리보기
uv run srkit deploy toybox                                   # 미리보기
```

Expected: `korean` 은 `갱신: WTSAPI32.dll` 한 줄 + `미리보기(--apply 로 실행): 1개 파일`, `toybox` 는 `추가: srtoybox.dll` 한 줄 + `1개 파일`. **그 밖의 줄이 있으면 멈추고 사용자에게 보인다.**

```bash
uv run srkit deploy korean --apply && uv run srkit deploy toybox --apply
export SRTOYBOX_HOME="E:/SR2030ToyBox/build/verify/toybox/home"; mkdir -p "$SRTOYBOX_HOME" build/verify/toybox
```

게임을 띄워 새 게임(2030 - 세계, 독일)에 들어간다. 백그라운드 작업으로 돌린다:

```bash
gd start; nap 38
gd click 512 340; nap 3          # 샌드박스
gd click 797 240; nap 2          # 2030 - 세계
gd click 601 725; nap 32         # 시작
gd shot build/verify/toybox/0-game.png
cat "$SRTOYBOX_HOME/toybox.log"
```

Expected: 로그에 `시작`, `화면에 끼어들었습니다`, `창 준비됨 (1024x768)`. 화면은 평소의 게임이고 한글이 그대로다(한글화가 깨지지 않았다).

**G1** — 창을 연다:

```bash
gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/G1-open.png
```

Expected: 화면 왼쪽 위(40,60)에 제목 `SR2030 ToyBox`, 탭 `돈 물자 연구 인구·여론 부대 화면·진행 설정`, "국고 추가" 줄과 안내 두 줄이 **한글로** 보인다. Read 도구로 열어 확인하고, "국고 +$10 B" 단추와 "국고 추가" 입력란 · 단추, 각 탭의 좌표를 적어 둔다(아래에서 쓴다).

창이 캡처에 안 보이면: 로그에 `창 준비됨` 이 있는지 본다. 있는데 안 보이면 `PrintWindow` 가 덧그린 프레임을 못 잡는 것이다 — 이 경우 멈추고, `overlay.cpp` 의 `draw` 끝에 뒷면을 BMP 로 떠내는 진단(환경 변수 `SRTOYBOX_DUMP` 가 있을 때만)을 넣는 것을 ledger 에 `Ruling:` 으로 적고 진행한다.

```bash
gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/G1-closed.png     # 닫힌다
```

**G2** — 국고 +$10 B. 먼저 지금 국고를 본다(시작 국고는 $14.43 B):

```bash
gd click 205 738; nap 1.5; gd move 560 420; nap 1; gd shot build/verify/toybox/G2-before.png   # 재무 패널
gd key CTRL+SHIFT+T; nap 1
gd click <"국고 +$10 B" 단추의 x> <y>; nap 6                 # 한 명령은 4초쯤 걸린다
gd shot build/verify/toybox/G2-after.png
```

Expected: 재무 패널의 국고가 $14.43 B → $24.43 B. 게임의 설정 창은 닫혀 있다(화면에 "게임 설정" 창이 없다). ToyBox 창의 아래쪽에 `마지막으로 넣은 것: cheat georgew`.

국고가 그대로면: 넣는 동안의 화면을 본다(`gd click …; nap 1.5; gd shot …` 로 중간을 찍는다). 설정 창이 안 열리면 수정키가 안 읽힌 것이고, 열렸는데 글자가 안 들어가면 간격이 짧은 것이다. `command.cpp` 의 간격 상수를 늘려(먼저 `SETTLE_MS` 300 → 600) 다시 빌드 · 설치하고, 바꾼 값과 이유를 ledger 에 `Ruling:` 으로 적는다(`tests/test_toybox.py` 의 `expected_plan` 도 같은 값으로 고친다).

**수정키가 남지 않는가** (Review Focus 3) — ToyBox 창을 닫고 맨 `S` 를 보낸다:

```bash
gd key CTRL+SHIFT+T; nap 1; gd key S; nap 1.5; gd shot build/verify/toybox/G2-plain-s.png; gd key S; nap 1
```

Expected: "게임 설정" 창이 뜨지 않고 지도에 보급 지도(짙은 색 구역)가 켜진다. 설정 창이 뜨면 수정키가 남은 것이다 — `runner_win.cpp` 의 `mods(false)` 를 고친다.

- [ ] **Step 10: 값 입력과 탭 — G3, G4**

**G3** — "국고 추가" 입력란에 1234 를 넣고 실행:

```bash
gd key CTRL+SHIFT+T; nap 1
gd click <입력란의 x> <y>; nap 0.5
gd key CTRL+A; gd type 1234; gd key ENTER; nap 0.5
gd click <"국고 추가" 단추의 x> <y>; nap 6
gd shot build/verify/toybox/G3-after.png
cat "$SRTOYBOX_HOME/toybox.ini"
```

Expected: 국고 +$1.23 B($24.43 B → $25.66 B 또는 표시 반올림에 따라 $25.67 B). `toybox.ini` 에 `treasury=1234`. 입력란에 넣은 숫자 글쇠가 게임으로 새지 않았다(게임의 패널이 바뀌지 않았다).

**G4** — 탭마다 하나씩. 탭을 누르고 단추를 누른 뒤 07 에 적힌 효과를 본다:

| 탭 | 단추 | 볼 곳 | 기대 |
|---|---|---|---|
| 물자 | 모든 물자 +100만 | 자원 패널(`gd click 259 738`)의 재고 | 재고가 100만 늘어난다 |
| 연구 | 기술 수준 N 이하 전부 보유(기본 120) | 연구 패널(`gd click 313 738`)의 보유 기술 수 | 늘어난다(07: +46) |
| 인구·여론 | 인구 +100만 | 재무 패널의 `gd move 40 510` 툴팁의 인구 | 82,615,760 → 83,615,760 |

각각 앞뒤 화면을 `build/verify/toybox/G4-<이름>-before.png` · `-after.png` 로 남긴다. 연구 패널의 "보유 기술" 목록이 열려 있으면 글자가 그 검색란으로 들어가므로(07 의 "알아 둘 것") 다른 패널을 연 채로 누른다.

- [ ] **Step 11: 입력이 새지 않는가, 단축키 바꾸기 — G5, G6, G7**

**G5 · G6** — ToyBox 창 아래에 게임의 단추가 있는 자리를 누른다. 환영 메시지 패널의 닫기(빨간 X, 461,137 근처 — `0-game.png` 에서 좌표를 확인한다)가 ToyBox 창(40..540, 60..520) 아래에 있다:

```bash
gd key CTRL+SHIFT+T; nap 1                                   # 열려 있지 않으면 연다
gd click 461 137; nap 1                                      # ToyBox 창 위를 누른다
gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/G5-still-there.png     # 닫고 본다
gd click 461 137; nap 1; gd shot build/verify/toybox/G6-closed-by-game.png
```

Expected: G5 — 환영 메시지 패널이 그대로 있다(누름이 게임으로 새지 않았다). G6 — ToyBox 창을 닫은 뒤의 누름은 게임이 받아 패널이 닫힌다.

**G7** — 단축키를 `F12` 로 바꾼다("설정" 탭 → "단축키 바꾸기" → `F12`):

```bash
gd key CTRL+SHIFT+T; nap 1
gd click <"설정" 탭의 x> <y>; nap 0.5; gd click <"단축키 바꾸기"의 x> <y>; nap 0.5
gd key 0x7B; nap 0.5; gd shot build/verify/toybox/G7-changed.png
gd key 0x7B; nap 1; gd shot build/verify/toybox/G7-closed-by-f12.png
gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/G7-old-does-nothing.png
grep hotkey "$SRTOYBOX_HOME/toybox.ini"
```

Expected: "창 여닫기: F12" 로 바뀐다. `F12` 로 닫히고, 예전 조합은 아무 일도 하지 않는다. `toybox.ini` 에 `hotkey_vk=123`, `hotkey_mods=0`.

게임을 끄고 다시 띄워 새 조합이 남아 있는지 본다:

```bash
gd stop; nap 2; gd start; nap 38
gd key 0x7B; nap 1; gd shot build/verify/toybox/G7-after-restart.png
```

Expected: 메인 메뉴 위에 ToyBox 창이 뜬다(다시 띄운 뒤에도 `F12`). 기본값으로 되돌려 둔다: 설정 탭 → "단축키 바꾸기" → `gd key CTRL+SHIFT+T` → `toybox.ini` 에 `hotkey_vk=84`, `hotkey_mods=3`.

- [ ] **Step 12: 메뉴에서 단추를 누르면 (Review Focus 4)**

지금 메인 메뉴이고 ToyBox 창이 열려 있다. "국고 +$10 B" 를 누른다:

```bash
gd shot build/verify/toybox/menu-before.png
gd click <돈 탭> ; gd click <"국고 +$10 B" 단추>; nap 6
gd shot build/verify/toybox/menu-after.png
gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/menu-closed.png
gd status
```

Expected: 게임이 살아 있다(`gd status` 가 창을 보여 준다). 메뉴가 쓸 수 있는 상태다 — 종료 확인 창이 떠 있으면 "아니오"를 눌러 닫을 수 있어야 한다. **무슨 일이 일어났는지(글자가 어디로 갔는지, `ESC` 가 무엇을 했는지) 그대로 적어 둔다** — Task 5 의 문서 "한계"에 들어간다. 게임이 죽거나 메뉴를 못 쓰게 되면 멈추고 사용자에게 보고한다(안내만으로는 부족하다는 뜻이다).

- [ ] **Step 13: 창 크기가 바뀌면 (Review Focus 5)**

게임 창의 크기를 밖에서 바꾼다(`$S/resize_game.py` 를 Write 도구로 만든다 — 임시 스크립트):

```python
"""게임 창의 크기를 바꾼다(화면 밖 위치는 그대로). 인자: 폭 높이"""
import ctypes
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("gamedrive", Path("scripts/gamedrive.py"))
gd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gd)
hwnd, _title, size = gd.game_window()
SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x2, 0x4, 0x10
ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, int(sys.argv[1]), int(sys.argv[2]), SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE)
print("전", size, "→ 요청", sys.argv[1:])
```

```bash
gd key CTRL+SHIFT+T; nap 1                                   # 창을 연 채로
uv run python "$S/resize_game.py" 1296 839; nap 3
gd status; gd shot build/verify/toybox/resize-after.png
uv run python "$S/resize_game.py" 1040 807; nap 3            # 클라이언트 1024x768 로 되돌린다(테두리 포함 크기는 gd status 로 맞춘다)
gd status; gd shot build/verify/toybox/resize-back.png
gd stop
```

Expected: 게임이 살아 있고 ToyBox 창이 계속 그려진다(게임이 swap chain 의 크기를 바꾸지 않아 화면이 늘어나 보일 수 있다 — 그것은 게임의 동작이다). 로그에 새 오류 줄이 없다. 게임이 죽으면 `hooked_resize` 와 `draw` 의 렌더 대상 처리를 본다.

- [ ] **Step 14: ToyBox 만 빼고 게임이 평소대로인지 — G8**

```bash
gd status                                                    # 프로세스: 없음
uv run srkit undeploy toybox --apply
gd start; nap 38; gd key CTRL+SHIFT+T; nap 1; gd shot build/verify/toybox/G8-without-toybox.png; gd stop
(cd "$G" && sha256sum -c /e/SR2030ToyBox/build/verify/v5/before.sha256 | awk '{print $NF}' | sort | uniq -c)
ls build/.deploy; ls "$G/srtoybox.dll" 2>&1 | tail -1
```

Expected: 메인 메뉴가 한글로 뜨고 ToyBox 창은 없다. 해시 `10 OK`. `build/.deploy` 는 `korean` 뿐. 게임 폴더에 `srtoybox.dll` 이 없다.

- [ ] **Step 15: 실제 환경에서 창이 뜨는지 (Steam 으로 띄운 게임, 짧게)**

화면 크기 창으로 뜨고 포커스를 가져간다. **띄우기 전에 채팅에 한 줄로 알린다**("Steam 으로 게임을 1분쯤 띄워 창이 뜨는지 봅니다 — 화면에 게임이 나타납니다").

```bash
uv run srkit deploy toybox --apply
unset SRTOYBOX_HOME
gd steam; nap 45
gd key CTRL+SHIFT+T; nap 1.5; gd shot build/verify/toybox/steam-open.png
gd stop
uv run srkit undeploy toybox --apply
uv run python -c "import os, pathlib; p = pathlib.Path(os.environ['APPDATA']) / 'SR2030ToyBox' / 'toybox.log'; print(p.read_text(encoding='utf-8')[-400:] if p.is_file() else '로그 없음: ' + str(p))"
```

Expected: 메인 메뉴 위에 ToyBox 창이 한글로 보인다. 로그에 `창 준비됨 (<화면 크기>)`. `gd steam` 이 이 환경에서 동작하지 않거나(Steam 이 꺼져 있다 등) 창이 안 뜨면 그 사실과 로그를 그대로 적고 진행한다 — 완료 기준 3 은 "확인하지 못함"으로 남기고 사용자에게 알린다.

- [ ] **Step 16: 전체 테스트와 커밋 · PR · 머지**

```bash
uv run pytest -q                                             # 116 passed
git add native/srtoybox src/srkit/toybox.py tests/test_toybox.py
git status --short                                           # build/ 의 파일이 없어야 한다
git commit -F - <<'EOF'
feat: ToyBox — 게임 화면에 모드 설정 창을 띄우고 단추로 내장 치트를 넣는다

- 화면: swap chain 의 Present · ResizeBuffers 에 끼어들어(임시 swap chain 에서 가상 함수 표를 얻는다) Dear ImGui 로 그린다.
  게임이 그리는 창을 주 창으로 삼는다. 실행 파일의 주소를 쓰지 않는다.
- 입력: 게임 창의 창 프로시저를 감싼다. 여닫는 단축키(기본 Ctrl+Shift+T), 창 위의 마우스와 입력란의 글쇠는 게임으로 가지 않는다.
- 실행: 단추 → 대기열 → 창 스레드의 10 ms 타이머가 게임의 설정 창에 치트를 넣는다(gamedrive 가 밖에서 넣는 경로 그대로).
- 실패하면 ToyBox 만 꺼지고 %APPDATA%\SR2030ToyBox\toybox.log 에 이유를 적는다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin feat/toybox-overlay
```

PR 본문은 Write 도구로 `$S/pr-overlay.md` 에 쓴다. G1 ~ G8 과 Review Focus 3 · 4 · 5 의 결과(본 값 그대로), Steam 확인의 결과, `uv run pytest` 결과, 그리고 "게임 폴더: `WTSAPI32.dll` 은 갱신된 채(한글화 모드의 파일), `srtoybox.dll` 은 제거함, 해시 10 OK"를 적는다. 제목: `feat: ToyBox — 게임 안 모드 설정 창과 플레이어 대상 내장 치트`.

```bash
gh pr create --base develop --head feat/toybox-overlay --title "feat: ToyBox — 게임 안 모드 설정 창과 플레이어 대상 내장 치트" --body-file "$S/pr-overlay.md"
gh pr merge --merge feat/toybox-overlay
git switch develop && git pull origin develop
```

---

### Task 5: 문서

브랜치: `docs/toybox` (`develop` 에서)

**Files:**
- Create: `docs/10-toybox.md`
- Modify: `docs/09-cheat-mod-plan.md`, `docs/06-data-reference.md`, `README.md`

**Interfaces:**
- Consumes: Task 4 의 확인 결과(`build/verify/toybox/` 의 화면과 ledger 의 기록), `native/third_party/imgui/README.md` 의 버전

- [ ] **Step 1: 확인 스크립트를 쓰고 실패하는지 본다**

`$S/check_toybox_docs.py` 를 Write 도구로 만든다:

```python
"""ToyBox 문서가 갖춰야 할 것을 확인한다. 저장소 루트에서 실행한다."""
import ctypes
import pathlib
import re
import sys

from srkit import config, toybox

sys.stdout.reconfigure(encoding="utf-8")
cfg = config.load()
read = lambda p: (cfg.root / p).read_text(encoding="utf-8") if (cfg.root / p).is_file() else ""
d10, d09, d06, readme = read("docs/10-toybox.md"), read("docs/09-cheat-mod-plan.md"), read("docs/06-data-reference.md"), read("README.md")
fails = []
for heading in ("## 무엇인가", "## 설치와 제거", "## 쓰는 법", "## 기능", "## 한계", "## 구조", "## 확인한 것", "## 문제가 생기면", "## 다음 단계"):
    if heading not in d10:
        fails.append(f"10: 절이 없다 — {heading}")
lib = ctypes.CDLL(str(toybox.output(cfg)))
lib.srtoybox_feature_info.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
for i in range(lib.srtoybox_feature_count()):
    buf = ctypes.create_string_buffer(4096)
    n = lib.srtoybox_feature_info(i, buf, 4096)
    ident, _tab, label = buf.raw[:n].decode("utf-8").split("\t")[:3]
    if f"`cheat {ident}" not in d10 or label not in d10:
        fails.append(f"10: 기능이 빠졌다 — {ident} ({label})")
for must in ("Ctrl+Shift+T", "SRTOYBOX=0", "toybox.log", "한글화 모드가 설치", "[확인", "설정 창이 잠깐"):
    if must not in d10:
        fails.append(f"10: 빠진 말 — {must}")
for n in range(1, 9):
    if not re.search(rf"\|\s*G{n}\s*\|", d10):
        fails.append(f"10: 확인 결과가 없다 — G{n}")
if "실행 중 트레이너(훅 DLL 확장) | 치트로 충분하다" in d09:
    fails.append("09: '만들지 않을 것'에 실행 중 트레이너가 남아 있다")
if "10-toybox.md" not in d09 or "ToyBox" not in d09:
    fails.append("09: ToyBox 로 가는 길이 없다")
if "World2030X" not in d09 and "World2030X" not in d06:
    fails.append("06/09: 새 이름의 시나리오 확인 결과가 없다")
for must in ("toybox-build", "docs/10-toybox.md", "srtoybox"):
    if must not in readme:
        fails.append(f"README: 빠진 말 — {must}")
print("\n".join(fails) if fails else "모두 통과")
sys.exit(1 if fails else 0)
```

Run: `uv run python "$S/check_toybox_docs.py"`
Expected: `10: 절이 없다 — …` 를 비롯해 여러 줄이 나오고 종료 코드 1.

- [ ] **Step 2: `docs/10-toybox.md` 를 쓴다**

머리: `# 10. ToyBox — 게임 안 모드 설정 창`, 조사 기준 줄(appid · build `21347933` · 게임 12.1.1360 · 날짜), 표기 줄([확인] / [추정]).

절과 그 안에 반드시 들어갈 것(값과 화면 이름은 Task 4 에서 본 그대로 적는다 — 보지 않은 것은 [추정]이나 "확인하지 못함"으로):

| 절 | 내용 |
|---|---|
| `## 무엇인가` | 게임 화면 위의 치트 창. 사용자 요구 둘(게임 안에서 설정 / 플레이어가 플레이 중인 국가에만). 싱글플레이 전용, Workshop 배포 불가 |
| `## 설치와 제거` | 설계서의 명령 여섯 줄. "한글화 모드가 설치되어 있어야 동작한다"와 그 이유. 제거 뒤 `WTSAPI32.dll` 은 한글화 모드의 파일로 남는다 |
| `## 쓰는 법` | `Ctrl+Shift+T` 로 여닫는다, 탭, 값 입력, "즉시 승리"는 두 번, 단축키 바꾸는 법, "설정 창이 잠깐 열렸다 닫힌다"는 안내 |
| `## 기능` | 16줄의 표: 탭 / 창의 이름 / 넣는 명령(`` `cheat …` ``) / 값의 범위 / 07 에서 본 효과 한 줄. 넣지 않은 것과 이유(모든 지역 · 불리 · 지역 번호 필요) |
| `## 한계` | ① 단추마다 게임의 설정 창이 잠깐 보인다 ② 게임이 진행 중인지 모른다 — **Task 4 Step 12 에서 메뉴에서 눌렀을 때 실제로 일어난 일** ③ `Ctrl+Shift+S` 나 치트가 게임에서 사라지면 안 된다(`srkit cheats-check`) ④ 치트가 Steam 업적을 막는지 모른다 ⑤ GDP · 장비 수치 · 지역을 고르는 치트는 아직 없다 |
| `## 구조` | 설계서의 구성 그림과 파일 표. 화면 끼어들기(가상 함수 표), 입력 끼어들기, 실행기(창 스레드의 타이머), 실행 파일의 주소를 쓰지 않는다는 점. Dear ImGui 의 버전(`native/third_party/imgui/README.md`) |
| `## 확인한 것` | G1 ~ G8 의 표(`\| G1 \| 무엇을 했나 \| 본 것 \| 근거 화면 \|`), Review Focus 3 · 4 · 5 의 결과, Steam 으로 띄운 게임에서의 결과. 근거는 로컬의 `build/verify/toybox/` |
| `## 문제가 생기면` | `%APPDATA%\SR2030ToyBox\toybox.log` 의 줄과 뜻(`화면에 끼어들지 못했습니다`, `DirectX 11 장치가 아닙니다`, `맑은 고딕…`), 끄는 법 `SRTOYBOX=0` 과 `srkit undeploy toybox --apply`, 설정을 처음으로 돌리는 법(`toybox.ini` 삭제) |
| `## 다음 단계` | 설계서의 단계 2 · 3 · 4. 명령 처리 코드의 위치(RVA `0x5228b3`–`0x5284c2`, build `21347933`)와 "호출 방법은 분석하지 않았다" |

- [ ] **Step 3: `docs/09` · `docs/06` · `README.md` 를 고친다**

`docs/09-cheat-mod-plan.md`:

- "만들지 않을 것" 표에서 `| 실행 중 트레이너(훅 DLL 확장) | … |` 줄을 지운다.
- "## 만들 것" 바로 아래(첫 소절 앞)에 소절을 넣는다:

```markdown
### ToyBox — 게임 안 모드 설정 창 (1단계를 만들었다)

2026-10-06 에 사용자가 요구를 둘 정했다: 모드의 모든 기능은 **게임 안의 설정 창**에서 설정하고, 설정은 **플레이어가 플레이 중인 국가에만** 적용한다.
아래의 시나리오 모드는 지역 번호에 고정이고 새 게임을 시작할 때만 적용되어 이 요구를 채우지 못한다. 그래서 이 문서가 처음에
"만들지 않는다"고 했던 실행 중 수단(훅 DLL 확장)으로 방향을 바꿨다 — [10 ToyBox](10-toybox.md).

1단계는 창과, 게임이 플레이어에게만 적용하는 내장 치트 16개다. 내장 치트가 없는 GDP 와 장비 수치는 뒷단계다(10 의 "다음 단계").
아래의 시나리오 덮어쓰기는 그때의 후보로 남긴다.
```

- "먼저 확인할 것" 의 ① 뒤에 덧붙인다: ` → **된다** [확인: 게임]. `Sandbox\World2030X.scenario` 와 같은 이름의 폴더(지역 설정 csv, `World2030XStart.csv`)를 두면 샌드박스 목록에 뜨고 덮어쓰기가 반영된다. 표시 이름은 `LocalText-START.csv` 의 `&&FILETEXT` 에서 온다.`
- "## 로드맵" 의 번호 목록을 바꾼다:

```markdown
1. **ToyBox 1단계 (끝).** 게임 안 설정 창 + 플레이어 대상 내장 치트 — [10](10-toybox.md).
2. **ToyBox 2단계.** 플레이어 국가 식별, 지역을 고르는 치트(지지율 · 관계 · 병합), 명령 처리 함수의 직접 호출, 게임 진행 중인지 감지.
3. **ToyBox 3단계.** GDP 처럼 내장 치트가 없는 값, 값을 유지하는 토글.
4. **ToyBox 4단계.** 장비 수치 — 설계가 지역끼리 공유되어 "플레이어만"이 가장 어렵다.
5. **(업데이트가 오면)** `srkit cheats-check` → 달라진 치트를 게임에서 다시 넣어 보고 [07](07-cheats.md) 갱신 → `srkit inventory` 로 형식 변화 확인 → ToyBox 가 뜨는지 확인.
```

- "수단 여섯 가지" 표의 `실행 중 훅` 줄의 검증 칸을 `[확인] 창을 그리고 내장 치트를 넣는 것까지 — [10](10-toybox.md)` 로 바꾼다.

`docs/06-data-reference.md` 의 "로딩 단계와 캐시" 절, 덮어쓰기 블록의 모양 코드 블록 바로 앞에 한 줄을 넣는다:

```markdown
- **덮어쓰기를 붙인 시나리오를 새 이름으로 따로 둘 수 있다.** [확인: 게임] `Sandbox\World2030X.scenario` + `Sandbox\World2030X\`(`World 2030 Regions.csv`, `World2030XStart.csv`)로 두면 샌드박스 목록에 파일 이름으로 뜨고, 캐시는 `W2030` 을 그대로 쓴다. 원본 시나리오는 건드리지 않는다.
```

`README.md`:

- "빠른 시작"의 명령 목록에서 `hook-build` 줄 다음에 넣는다: `uv run srkit toybox-build              # ToyBox DLL(게임 안 모드 설정 창) 빌드 → build/toybox/`
- "구조"의 `docs/` 목록에 `  10-toybox.md                 ToyBox — 게임 안 모드 설정 창` 을, `mods/` 에 `  toybox/        ToyBox 설명 (모드의 파일은 DLL 하나다)` 를, `src/srkit/` 에 `  toybox.py      ToyBox DLL 빌드` 를, `native/` 줄을 `native/srhook/   디코딩 훅 DLL 소스` · `native/srtoybox/ ToyBox DLL 소스 (C++)` · `native/third_party/imgui/  Dear ImGui (MIT)` 세 줄로 바꾼다.
- "현재 상태"의 치트·모드 조사 단락 뒤에 단락을 더한다:

```markdown
셋째로 **ToyBox**(게임 안 모드 설정 창)의 1단계를 만들었다(2026-10-06). `Ctrl+Shift+T` 로 여는 창에서 플레이어 국가에만 닿는 내장 치트 16개를
실행한다. 한글화 모드가 설치되어 있어야 동작하고, 지금은 게임 폴더에 설치해 두지 않았다 — 쓰는 법과 한계는 [docs/10](docs/10-toybox.md).
```

(마지막 문장의 "설치해 두지 않았다"는 Task 5 Step 5 의 실제 상태에 맞춘다.)

- [ ] **Step 4: 확인 스크립트와 전체 테스트**

Run: `uv run python "$S/check_toybox_docs.py" && uv run srkit cheats-check | tail -3 && uv run pytest -q`
Expected: `모두 통과`, 치트 대조는 사라진·새로 생긴 치트 없음, `116 passed`.

- [ ] **Step 5: 마지막 상태 확인**

```bash
gd status                                                    # 프로세스: 없음
uv run srkit deploy korean | tail -1                         # 미리보기: 0개 파일
ls build/.deploy                                             # korean
(cd "$G" && sha256sum -c /e/SR2030ToyBox/build/verify/v5/before.sha256 | awk '{print $NF}' | sort | uniq -c)   # 10 OK
git status --short
```

Expected: 위 주석대로. ToyBox 는 게임 폴더에 설치되어 있지 않다(사용자가 쓰겠다고 하면 `uv run srkit deploy toybox --apply` — 마지막 보고에서 묻는다).

- [ ] **Step 6: 커밋 · PR · 머지**

```bash
git add docs/10-toybox.md docs/09-cheat-mod-plan.md docs/06-data-reference.md README.md
git commit -F - <<'EOF'
docs: ToyBox — 쓰는 법 · 한계 · 확인한 것, 제작 계획의 방향 수정

- docs/10: 게임 안 모드 설정 창의 설치 · 사용 · 기능 16개 · 한계 · 구조 · 게임 안 확인 결과(G1~G8).
- docs/09: "실행 중 트레이너는 만들지 않는다"를 뒤집고(사용자 요구: 게임 안 설정 창, 플레이어 국가에만) 로드맵을 ToyBox 단계로 바꿨다.
- docs/06 · 09: 덮어쓰기를 붙인 시나리오를 새 이름으로 둘 수 있다는 확인 결과.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox
gh pr create --base develop --head docs/toybox --title "docs: ToyBox — 쓰는 법 · 한계 · 확인한 것, 제작 계획의 방향 수정" --body-file - <<'EOF'
ToyBox 1단계의 문서.

- `docs/10-toybox.md` — 설치와 제거, 쓰는 법, 기능 16개, 한계, 구조, 게임 안 확인 결과(G1~G8), 문제가 생기면 볼 곳, 다음 단계.
- `docs/09` — 사용자 요구(게임 안 설정 창 / 플레이어 국가에만)에 따라 "실행 중 트레이너는 만들지 않는다"를 뒤집고 로드맵을 고쳤다.
- `docs/06` · `09` — 새 이름의 시나리오가 된다는 확인 결과.
- `README.md` — 명령과 구조, 현재 상태.

문서만 바뀐다. `uv run pytest` → 116 passed. `srkit cheats-check` 통과.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr merge --merge docs/toybox
git switch develop && git pull origin develop
```

---

## 계획 밖에 두는 것

- 2 ~ 4단계(플레이어 국가 식별, 지역을 고르는 치트, 명령의 직접 호출, GDP, 장비 수치).
- 한글화 없이 쓰는 불러오기 전용 프록시.
- `CLAUDE.md` 의 수정(사용자의 상시 지침 파일이다 — 필요하면 마지막 보고에서 제안만 한다).
- ToyBox 를 게임 폴더에 설치해 두는 일(시험 설치는 끝에 제거한다 — 설치는 사용자가 정한다).
