# ToyBox 2단계 — 게임 상태 읽기, 직접 실행, 지역 치트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ToyBox(`srtoybox.dll`)가 게임의 상태(진행 중 여부 · 플레이어 국가 · 이번 게임의 나라들)를 읽고, 치트를 게임의 명령 처리 함수에 직접 넘기고, 나라를 골라 쓰는 치트 9개를 창에 더한다.

**Architecture:** 게임이 뜰 때 올라와 있는 실행 파일에서 `"cheat allowcheats"` 문자열을 닻으로 주소를 찾는다(`locate`, 순수 함수). 찾은 주소로 상태를 안전하게 읽고(`game`), 창 스레드의 타이머에서 진행 중일 때만 명령 처리 함수를 부른다(`runner_win`). 주소를 못 찾거나 읽은 값이 서로 맞지 않으면 1단계의 글쇠 방식 그대로 동작한다. 나라 이름표는 빌드할 때 저장소의 번역 테이블에서 만들어 DLL 에 넣는다(`regions`).

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Dear ImGui v1.92.9b(이미 저장소에 있다), Python 3.13 + ctypes + pytest (`uv run`), Win32.

**Spec:** `docs/superpowers/specs/2026-10-07-toybox-stage2-design.md` (승인 2026-10-07). 앞 단계의 설계와 쓰는 법은 `docs/superpowers/specs/2026-10-06-toybox-stage1-design.md`, `docs/10-toybox.md`.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 RVA 를 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 를 적지 않는다(테스트의 기대값과 문서에만).
- **게임의 메모리에 쓰지 않는다.** 이 단계에서 ToyBox 가 게임에 가하는 변화는 게임의 명령 처리 함수를 거친 것(직접 호출 또는 글쇠)뿐이다. 치트 허용 비트도 직접 세우지 않는다.
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다.
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다. 생성물은 `build/`(git 제외)에만.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다**("저장 후 종료"를 누르지 않는다). 게임이 떠 있는 동안 브랜치를 바꾸지 않는다. Steam 으로 띄우는 것은 H12 한 번, 띄우기 전에 채팅에 알린다.
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.**
- Git: `main` · `develop` 에 직접 커밋하지 않는다. Task 마다 `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고
  `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다.
- `CLAUDE.md` 는 고치지 않는다(넣을 줄은 마지막 보고에서 제안만).
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`.
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다.

## 설계서와 달라진 곳 (계획을 쓰며)

- **지역 수의 주소도 찾는다.** 설계서의 주소 찾기 표에는 지역 수(`0x18294d8`)가 빠져 있었다. `becomeregion` 블록의 `mov r9d,[rip+d]` … `lea rcx,[rip+d]` 에서 지역 수와 지역 표를 함께 얻고, 지역 표가 `populate` 에서 얻은 것과 같은지를 대조에 더한다(조건 8). 설계서에는 Task 5 에서 "보완 내역"으로 적는다.
- **나라 이름표는 Task 2 에 둔다**(설계서의 작업 순서로는 4번). 상태 줄이 플레이어의 이름을 보여야 해서다. 나라 고르기와 지역 치트는 그대로 Task 4.
- `GameAddresses` 의 `this` 자리는 필드 이름을 `context` 로 한다(C++ 과 Python 양쪽에서 `this` · `self` 는 쓰기 불편하다).
- 로그의 줄은 `게임 상태를 읽습니다 (명령 처리 함수 +0x…)` 로 한다(설계서는 `(직접 실행)`). 찾은 함수의 자리가 로그에 남아야 문제가 생겼을 때 빌드를 가릴 수 있다.
- 가짜 게임에 "게임 밖에서는 명령 처리 함수를 부르지 않는다"는 테스트를 하나 더 둔다(Task 3 의 `direct_menu`).

## Review Focus

설계서가 함의하지만 그대로 두면 테스트가 밟지 않을 다섯 가지. 각 줄의 테스트를 해당 Task 에 넣었다.

1. **다른 판을 불러와 고른 나라가 이번 게임에 없게 된다** → 선택이 지워져야 한다. (Task 4, `test_region_view_drops_a_pick_that_is_gone`)
2. **단추를 누른 뒤 실행되기 전에 게임에서 나간다** → 실행하지 않고 버려야 한다. (Task 2, `test_a_queued_command_is_dropped_when_the_game_ends_first`)
3. **이름에 따옴표나 역슬래시가 든 지역** → 이름표 생성물이 C++ 로 컴파일되어야 한다. (Task 2, `test_region_table_escapes_names`)
4. **이름표에 없는 지역 번호** → `#번호` 로 보이고 고를 수 있어야 한다. (Task 2 `test_region_names`, Task 4 `test_region_view_lists_this_games_regions`)
5. **치트 허용이 꺼진 채(메뉴에 나갔다 온 뒤) 누른다** → `cheat allowcheats` 를 다시 불러야 한다. (Task 3, `test_direct_run_calls_the_games_handler`)

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `native/srtoybox/locate.h` · `.cpp` (새로) | 실행 파일의 이미지에서 주소 찾기. 순수 함수 | 1 |
| `native/srtoybox/game.h` · `.cpp` (새로) | 찾은 주소로 게임 상태 읽기(읽기만), 명령 처리 함수 부르기 | 2 · 3 |
| `native/srtoybox/regions.h` · `.cpp` (새로) | 지역 번호 → 이름, 나라 목록의 보기(정렬 · 검색 · 선택 유지) | 2 · 4 |
| `native/srtoybox/runner.h` · `.cpp` | 대기열(다음 명령 꺼내기 · 비우기) | 2 |
| `native/srtoybox/runner_win.h` · `.cpp` | 실행 전 상태 검사, 직접 실행, 오류 가드 | 2 · 3 |
| `native/srtoybox/features.h` · `.cpp`, `command.h` · `.cpp` | 기능 표의 "대상" 열, 대상이 붙는 명령 | 4 |
| `native/srtoybox/ui.cpp` | 상태 줄, 단추 끄기, "외교·영토" 탭 | 2 · 4 |
| `native/srtoybox/input.h` · `.cpp` | ANSI 창의 2바이트 글자 합치기 | 4 |
| `native/srtoybox/exports.cpp` | 테스트와 `srkit` 이 쓰는 C 인터페이스 | 1 ~ 4 |
| `src/srkit/toybox.py`, `src/srkit/cli.py` | 빌드(이름표 생성), `srkit locate` | 1 · 2 |
| `tests/toybox_fake_exe.py` (새로) | 주소 찾기 테스트용 가짜 실행 파일 이미지 | 1 |
| `tests/toybox_fake_game.py` (새로) | 가짜 게임 메모리(전역 · 지역 객체) | 2 |
| `tests/test_toybox_game.py` (새로) | 주소 찾기 · 상태 읽기 · 이름표 · 나라 목록의 테스트 | 1 · 2 · 4 |
| `tests/test_toybox.py`, `tests/toybox_overlay_probe.py` | 가짜 게임 창으로 보는 단추 끄기 · 직접 실행, 기능 표 | 2 · 3 · 4 |
| `docs/10-toybox.md`, `docs/11-game-internals.md`(새로), `docs/07-cheats.md`, `docs/09-cheat-mod-plan.md`, `README.md`, 설계서 | 문서 | 5 |

---

### Task 1: 주소 찾기 (`locate`) 와 `srkit locate`

**브랜치:** `feat/toybox-locate` (`develop` 에서)

**Files:**
- Create: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`
- Create: `tests/toybox_fake_exe.py`, `tests/test_toybox_game.py`
- Modify: `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`, `src/srkit/cli.py`

**Interfaces:**
- Consumes: 없음.
- Produces:
  - C++ `struct GameAddresses { uint32_t handler, context, multiplayer, options, program_state, mode_state, player_index, player_pointer, region_table, region_count; };` (모두 이미지 시작으로부터의 RVA)
  - C++ `const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out);` — 성공 `nullptr`, 실패하면 까닭(정적 UTF-8 문자열). `image` 는 RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈).
  - 내보내기 `int srtoybox_locate(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)` — 0 성공, -1 실패(`error` 에 까닭).
  - Python `srkit.toybox.ADDRESS_FIELDS: list[str]`, `srkit.toybox.GameAddresses`(ctypes 구조체), `srkit.toybox.image_of(exe: bytes) -> bytes`, `srkit.toybox.locate(cfg) -> tuple[dict[str, int] | None, str]`
  - CLI `uv run srkit locate`

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-locate
```

- [ ] **Step 2: 가짜 실행 파일 이미지를 쓴다** — `tests/toybox_fake_exe.py` (Write 도구로)

```python
"""주소 찾기(native/srtoybox/locate.cpp) 테스트용: 작은 가짜 실행 파일 이미지(RVA 대로 펼친 것).

게임의 코드를 옮긴 것이 아니다. locate 가 찾는 닻(문자열)과 서명(명령의 바이트 꼴)만 같은 자리 관계로 놓았다.
pytest 가 직접 모으는 테스트 파일이 아니다(tests/test_toybox_game.py 가 쓴다).
"""
import struct

SIZE = 0x6000
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER, ENTER = 0x1000, 0x1800, 0x1A00
WORLD = DATA + 0x180                          # 지역 표 = WORLD + 0x80
EXPECTED = {"handler": HANDLER, "context": DATA + 0x100, "multiplayer": DATA, "options": DATA + 4, "program_state": DATA + 8,
            "mode_state": DATA + 12, "player_index": DATA + 16, "player_pointer": DATA + 24, "region_table": WORLD + 0x80,
            "region_count": DATA + 20}
STRINGS = {"cheat allowcheats": RDATA, "cheat georgew": RDATA + 0x20, "cheat georgeww": RDATA + 0x40,
           "cheat populate": RDATA + 0x60, "cheat becomeregion": RDATA + 0x80}


def build(extra_anchor: bool = False, second_call: bool = False, no_head_check: bool = False, other_pointer: bool = False,
          outside: bool = False, other_table: bool = False) -> bytes:
    """가짜 이미지. 인자는 주소 찾기가 거부해야 하는 흠을 하나씩 낸다."""
    image = bytearray(SIZE)
    at = dict(EXPECTED)
    if outside:
        at["program_state"] = SIZE + 0x100     # 이미지 밖을 가리키는 주소

    def put(rva: int, data: bytes) -> int:
        image[rva:rva + len(data)] = data
        return rva + len(data)

    def rip(rva: int, opcode: bytes, target: int, tail: bytes = b"") -> int:
        """RIP 상대 변위가 든 명령 하나: opcode + 변위(4) + tail. 변위는 명령의 끝을 기준으로 한다."""
        length = len(opcode) + 4 + len(tail)
        return put(rva, opcode + struct.pack("<i", target - (rva + length)) + tail)

    # 머리말: DOS · NT · 구역 표
    put(0, b"MZ")
    struct.pack_into("<I", image, 0x3C, 0x80)
    put(0x80, b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 4, 0, 0, 0, 0xF0, 0x22))
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<II", image, optional + 56, SIZE, 0x400)                 # SizeOfImage, SizeOfHeaders
    struct.pack_into("<I", image, optional + 108, 16)                          # NumberOfRvaAndSizes
    struct.pack_into("<II", image, optional + 112 + 3 * 8, PDATA, 4 * 12)      # 예외 디렉터리(.pdata)
    for i, (name, rva, flags) in enumerate([(b".text", TEXT, 0x60000020), (b".rdata", RDATA, 0x40000040),
                                            (b".pdata", PDATA, 0x40000040), (b".data", DATA, 0xC0000040)]):
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else 0x1000, rva,
                         0, 0, 0, 0, 0, 0, flags)

    for text, rva in STRINGS.items():
        put(rva, text.encode() + b"\0")
    if extra_anchor:
        put(RDATA + 0x400, b"cheat allowcheats\0")

    # 명령 처리 함수
    end = put(HANDLER, bytes([0x40, 0x55, 0x53, 0x57]))
    if not no_head_check:
        end = rip(end, bytes([0x80, 0x3D]), at["multiplayer"], b"\0")          # cmp byte ptr [멀티플레이],0
    end = rip(end, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat allowcheats"])    # lea rdx,["cheat allowcheats"]
    end = rip(end, bytes([0x83, 0x0D]), at["options"], b"\x40")                # or dword ptr [옵션],40h
    put(end, b"\xC3")

    def player_read(rva: int, text: str, pointer: int) -> None:                # lea rdx,[문자열] / mov rax,[포인터] / movsd xmm0,[rax+14B88h]
        end = rip(rva, bytes([0x48, 0x8D, 0x15]), STRINGS[text])
        end = rip(end, bytes([0x48, 0x8B, 0x05]), pointer)
        put(end, bytes([0xF2, 0x0F, 0x10, 0x80, 0x88, 0x4B, 0x01, 0x00]))

    player_read(0x1040, "cheat georgew", at["player_pointer"])
    player_read(0x1080, "cheat georgeww", at["player_pointer"] + (8 if other_pointer else 0))

    end = rip(0x10C0, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat populate"])
    end = rip(end, bytes([0x48, 0x63, 0x05]), at["player_index"])              # movsxd rax,dword ptr [인덱스]
    end = rip(end, bytes([0x4C, 0x8D, 0x3D]), WORLD)                           # lea r15,[월드]
    put(end, bytes([0x49, 0x8B, 0x8C, 0xC7]) + struct.pack("<I", 0x80))        # mov rcx,[r15+rax*8+80h]

    end = rip(0x1100, bytes([0x48, 0x8D, 0x15]), STRINGS["cheat becomeregion"])
    end = put(end, bytes([0x0F, 0xB7, 0x4A, 0x04, 0x33, 0xD2]))                # movzx ecx,word ptr [rdx+4] / xor edx,edx
    end = rip(end, bytes([0x89, 0x0D]), at["player_index"])                    # mov [인덱스],ecx
    end = rip(end, bytes([0x89, 0x0D]), DATA + 0x1C)                           # mov [인덱스의 사본],ecx
    end = put(end, bytes([0x48, 0x63, 0xC1]))                                  # movsxd rax,ecx
    end = rip(0x1120, bytes([0x44, 0x8B, 0x0D]), at["region_count"])           # mov r9d,[지역 수]
    end = put(end, bytes([0x45, 0x33, 0xF6, 0x45, 0x85, 0xC9, 0x0F, 0x88, 0, 0, 0, 0]))
    rip(end, bytes([0x48, 0x8D, 0x0D]), at["region_table"] + (8 if other_table else 0))   # lea rcx,[지역 표]

    # 부르는 함수: 머리에 프로그램 상태 검사, 뒤쪽 조각에 호출
    end = put(CALLER, bytes([0x48, 0x81, 0xEC, 0xC0, 0x0D, 0x00, 0x00]))
    rip(end, bytes([0x83, 0x3D]), at["program_state"], b"\x06")                # cmp dword ptr [프로그램 상태],6
    end = rip(CALLER + 0x30, bytes([0x48, 0x8D, 0x0D]), at["context"])         # lea rcx,[this]
    rip(end, bytes([0xE8]), HANDLER)                                           # call 명령 처리 함수
    if second_call:
        rip(CALLER + 0x60, bytes([0xE8]), HANDLER)

    # 게임 진입: mov [모드 상태],2 / mov [프로그램 상태],1
    end = rip(ENTER, bytes([0xC7, 0x05]), at["mode_state"], struct.pack("<I", 2))
    rip(end, bytes([0xC7, 0x05]), at["program_state"], struct.pack("<I", 1))

    # .pdata: 부르는 함수는 조각 둘(뒤 조각이 앞 조각에 chained unwind 로 묶인다)
    unwind = RDATA + 0x800
    put(unwind, bytes([1, 0, 0, 0]))                                                         # 뿌리(플래그 없음)
    put(unwind + 0x10, bytes([0x21, 0, 0, 0]) + struct.pack("<III", CALLER, CALLER + 0x20, unwind))   # UNW_FLAG_CHAININFO
    put(PDATA, struct.pack("<III", HANDLER, HANDLER + 0x200, unwind)
        + struct.pack("<III", CALLER, CALLER + 0x20, unwind)
        + struct.pack("<III", CALLER + 0x20, CALLER + 0x100, unwind + 0x10)
        + struct.pack("<III", ENTER, ENTER + 0x20, unwind))
    return bytes(image)
```

- [ ] **Step 3: 실패하는 테스트를 쓴다** — `tests/test_toybox_game.py` (Write 도구로)

```python
"""ToyBox 2단계: 주소 찾기 · 게임 상태 읽기 · 나라 이름표 (native/srtoybox 의 locate · game · regions)."""
import ctypes
import struct

import pytest

import toybox_fake_exe
from srkit import toybox

# build 21347933 (게임 12.1.1360, PE TimeDateStamp 0x695377b6) 의 주소. docs/11-game-internals.md 의 표와 같다.
BUILD_21347933 = {"handler": 0x522330, "context": 0x1764310, "multiplayer": 0xF19634, "options": 0x1EB556C,
                  "program_state": 0x1EED11C, "mode_state": 0xE7BE30, "player_index": 0x18294E0, "player_pointer": 0x18295F8,
                  "region_table": 0x1AF78C0, "region_count": 0x18294D8}
BUILD_21347933_STAMP = 0x695377B6


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    return toybox.library(cfg)


def find(lib, image: bytes) -> tuple[dict[str, int] | None, str]:
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    if lib.srtoybox_locate(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in toybox.ADDRESS_FIELDS}, ""


def test_locate_finds_every_address_from_the_anchor_string(lib):
    found, why = find(lib, toybox_fake_exe.build())
    assert found == toybox_fake_exe.EXPECTED, why


@pytest.mark.parametrize("flaw, reason", [
    ("extra_anchor", "닻 문자열"),                   # 같은 문자열이 둘이면 어느 것이 진짜인지 모른다
    ("second_call", "부르는 곳"),                    # 부르는 곳이 둘이면 this 를 어디서 얻을지 모른다
    ("no_head_check", "멀티플레이"),                 # 함수 머리의 모양이 다르다 = 다른 함수이거나 바뀐 빌드
    ("other_pointer", "georgeww"),                   # 두 치트가 서로 다른 플레이어 포인터를 쓴다
    ("other_table", "지역 표"),                      # 지역 표의 주소가 두 곳에서 다르다
    ("outside", "실행 파일 밖"),                     # 찾은 주소가 이미지 밖이다
])
def test_locate_refuses_an_image_that_does_not_add_up(lib, flaw, reason):
    """대조가 하나라도 어긋나면 "못 찾았다"다 — 그때 ToyBox 는 1단계의 글쇠 방식으로 동작한다."""
    found, why = find(lib, toybox_fake_exe.build(**{flaw: True}))
    assert found is None and reason in why, why


@pytest.mark.parametrize("image", [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)])
def test_locate_survives_garbage(lib, image):
    found, why = find(lib, image)
    assert found is None and why


def test_locate_on_the_installed_game(lib, cfg, game_dir):
    """설치된 게임의 실행 파일에서. 아는 빌드(21347933)면 주소까지 대조하고, 다른 빌드면 찾았는지 못 찾았는지만 적는다."""
    exe = (game_dir / "SupremeRuler2030.exe").read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    found, why = find(lib, toybox.image_of(exe))
    if stamp != BUILD_21347933_STAMP:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x}): " + ("주소를 찾았다" if found else f"못 찾았다 — {why}"))
    assert found == BUILD_21347933, why


def test_srkit_locate_reports_the_addresses(lib, cfg, game_dir):
    found, why = toybox.locate(cfg)
    assert why == "" and found is not None and set(found) == set(toybox.ADDRESS_FIELDS)
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox_game.py -q --no-header 2>&1 | tail -5`
Expected: 수집 단계에서 오류 — `AttributeError: module 'srkit.toybox' has no attribute 'library'` (또는 `GameAddresses`).

- [ ] **Step 5: `locate.h` 를 쓴다** — `native/srtoybox/locate.h`

```cpp
// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다 —
// "cheat allowcheats" 문자열을 닻으로 삼아 그것을 쓰는 함수와 그 안의 명령에서 얻는다(docs/11-game-internals.md).
// 창도 Windows 도 모르는 순수 함수다. 대조가 하나라도 어긋나면 "못 찾았다"로 친다.
#pragma once

#include <cstddef>
#include <cstdint>

// 모두 이미지의 시작으로부터의 거리(RVA).
struct GameAddresses {
    uint32_t handler;          // 명령 처리 함수: void f(void *context, const char *line)
    uint32_t context;          // 그 함수의 첫 인자로 넘기는 전역 객체(게임이 넘기는 것과 같은 주소)
    uint32_t multiplayer;      // byte. 0 이 아니면 함수가 아무것도 하지 않는다
    uint32_t options;          // dword. 비트 0x40 = 치트 허용
    uint32_t program_state;    // dword. 1 = 월드가 돌고 있다
    uint32_t mode_state;       // dword. 2 = 게임
    uint32_t player_index;     // dword. 플레이어 지역의 인덱스(지역 표의 칸)
    uint32_t player_pointer;   // qword. 플레이어 지역 객체
    uint32_t region_table;     // qword × 1024. 인덱스순 지역 객체 포인터
    uint32_t region_count;     // dword. 지역 표의 마지막 인덱스
};

// image: RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈의 시작 주소), size: 그 크기.
// 찾으면 out 을 채우고 nullptr, 못 찾으면 까닭(UTF-8, 정적 문자열)을 돌려준다.
const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out);
```

- [ ] **Step 6: `locate.cpp` 를 쓴다** — `native/srtoybox/locate.cpp`

```cpp
#include "locate.h"

#include <cstring>

namespace {

struct Section {
    uint32_t rva, size;
    bool code;        // 실행 구역
    bool constant;    // 읽기 전용 자료(문자열이 여기 있다. 쓸 수 있는 구역에는 사용자가 친 글이 남을 수 있어 닻을 찾지 않는다)
};

struct Image {
    const uint8_t *p;
    size_t size;
    Section sections[32];
    int count;
    uint32_t pdata, pdata_size;

    bool has(uint64_t rva, uint64_t n) const { return rva + n <= size; }
    uint16_t u16(uint32_t rva) const { uint16_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
    uint32_t u32(uint32_t rva) const { uint32_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
    int32_t i32(uint32_t rva) const { int32_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
};

bool parse(Image &im)
{
    if (!im.has(0, 0x40) || im.u16(0) != 0x5A4D)                        // "MZ"
        return false;
    const uint32_t nt = im.u32(0x3C);
    if (!im.has(nt, 24 + 112 + 16 * 8) || im.u32(nt) != 0x00004550)     // "PE\0\0"
        return false;
    const uint32_t sections = im.u16(nt + 6), optional_size = im.u16(nt + 20), optional = nt + 24;
    if (im.u16(optional) != 0x20B || optional_size < 112 + 4 * 8)       // PE32+
        return false;
    im.pdata = im.u32(optional + 112 + 3 * 8);                          // 예외 디렉터리 = 함수 표(.pdata)
    im.pdata_size = im.u32(optional + 112 + 3 * 8 + 4);
    if (im.pdata_size < 12 || !im.has(im.pdata, im.pdata_size))
        return false;
    im.count = 0;
    for (uint32_t i = 0; i < sections && im.count < 32; i++) {
        const uint64_t header = static_cast<uint64_t>(optional) + optional_size + 40ull * i;
        if (!im.has(header, 40))
            return false;
        const uint32_t h = static_cast<uint32_t>(header), flags = im.u32(h + 36);
        Section s;
        s.size = im.u32(h + 8);
        s.rva = im.u32(h + 12);
        s.code = (flags & 0x20000000) != 0;                             // IMAGE_SCN_MEM_EXECUTE
        s.constant = !s.code && (flags & 0x80000000) == 0;              // IMAGE_SCN_MEM_WRITE 가 아니다
        if (s.size == 0)
            continue;
        if (!im.has(s.rva, s.size))
            return false;
        im.sections[im.count++] = s;
    }
    return im.count > 0;
}

// 서명: 16진수 바이트와 '?'(아무 바이트)를 빈칸으로 나눠 적는다. 예: "48 8D 0D ? ? ? ?"
struct Pattern {
    uint8_t bytes[40];
    bool any[40];
    uint32_t length;
};

Pattern pattern(const char *text)
{
    Pattern p = {};
    for (const char *c = text; *c != '\0' && p.length < 40; ) {
        if (*c == ' ') {
            c++;
        } else if (*c == '?') {
            p.any[p.length++] = true;
            c++;
        } else {
            unsigned value = 0;
            for (int i = 0; i < 2; i++, c++)
                value = value * 16 + static_cast<unsigned>(*c <= '9' ? *c - '0' : (*c | 0x20) - 'a' + 10);
            p.bytes[p.length++] = static_cast<uint8_t>(value);
        }
    }
    return p;
}

bool matches(const Image &im, uint64_t rva, const Pattern &pt)
{
    if (!im.has(rva, pt.length))
        return false;
    for (uint32_t i = 0; i < pt.length; i++)
        if (!pt.any[i] && im.p[rva + i] != pt.bytes[i])
            return false;
    return true;
}

// [from, to) 에서 처음 맞는 자리. 없으면 0.
uint32_t find(const Image &im, uint32_t from, uint32_t to, const Pattern &pt)
{
    for (uint64_t rva = from; rva < to; rva++)
        if (matches(im, rva, pt))
            return static_cast<uint32_t>(rva);
    return 0;
}

// 실행 구역 전체에서 맞는 자리의 수. first 에 가장 앞의 것.
int count_in_code(const Image &im, const Pattern &pt, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < pt.length)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - pt.length; rva++)
            if (im.p[rva] == pt.bytes[0] && matches(im, rva, pt) && n++ == 0)
                *first = rva;
    }
    return n;
}

// RIP 상대 주소가 든 명령이 가리키는 곳. at: 명령의 시작, disp: 변위의 자리, length: 명령의 길이.
uint32_t target(const Image &im, uint32_t at, uint32_t disp, uint32_t length)
{
    return static_cast<uint32_t>(static_cast<int64_t>(at) + length + im.i32(at + disp));
}

// 읽기 전용 자료에서 NUL 로 끝나는 글의 수. first 에 가장 앞의 것.
int count_string(const Image &im, const char *text, uint32_t *first)
{
    const uint32_t length = static_cast<uint32_t>(strlen(text)) + 1;
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.constant || sec.size < length)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - length; rva++)
            if (im.p[rva] == static_cast<uint8_t>(text[0]) && memcmp(im.p + rva, text, length) == 0 && n++ == 0)
                *first = rva;
    }
    return n;
}

// where 를 가리키는 lea r64,[rip+d] (48|4C 8D 05|0D|…|3D d32)의 수. first 에 가장 앞의 것.
int count_lea_to(const Image &im, uint32_t where, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 7)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 7; rva++)
            if ((im.p[rva] == 0x48 || im.p[rva] == 0x4C) && im.p[rva + 1] == 0x8D && (im.p[rva + 2] & 0xC7) == 0x05
                && target(im, rva, 3, 7) == where && n++ == 0)
                *first = rva;
    }
    return n;
}

// where 를 부르는 call rel32 (E8 d32)의 수. first 에 가장 앞의 것.
int count_calls_to(const Image &im, uint32_t where, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 5)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 5; rva++)
            if (im.p[rva] == 0xE8 && target(im, rva, 1, 5) == where && n++ == 0)
                *first = rva;
    }
    return n;
}

// rva 가 든 함수의 시작. 함수 표의 한 항목은 함수의 한 조각일 수 있다(큰 함수는 조각이 여럿이다) —
// chained unwind 를 뿌리까지 따라간다. 못 찾으면 0.
uint32_t function_root(const Image &im, uint32_t rva)
{
    uint32_t lo = 0, hi = im.pdata_size / 12, entry = 0;                // 항목은 시작 주소순이다
    while (lo < hi) {
        const uint32_t mid = lo + (hi - lo) / 2, e = im.pdata + 12 * mid;
        if (rva < im.u32(e)) {
            hi = mid;
        } else if (rva >= im.u32(e + 4)) {
            lo = mid + 1;
        } else {
            entry = e;
            break;
        }
    }
    if (entry == 0)
        return 0;
    uint32_t begin = im.u32(entry), unwind = im.u32(entry + 8);
    for (int depth = 0; depth < 32; depth++) {
        if (!im.has(unwind, 4))
            return 0;
        if (((im.p[unwind] >> 3) & 4) == 0)                             // UNW_FLAG_CHAININFO 가 없으면 뿌리다
            return begin;
        const uint32_t parent = unwind + 4 + 2 * ((im.p[unwind + 2] + 1u) & ~1u);   // 풀기 코드(짝수 개로 맞춘다) 뒤에 부모 항목
        if (!im.has(parent, 12))
            return 0;
        begin = im.u32(parent);
        unwind = im.u32(parent + 8);
    }
    return 0;
}

// 그 치트 문자열을 쓰는 자리(lea) 뒤 span 바이트 안에서 서명이 맞는 곳. 쓰는 자리가 여럿이면 앞에서부터 본다.
// 문자열이 하나가 아니거나 어디에도 맞지 않으면 0.
uint32_t find_in_cheat(const Image &im, const char *text, uint32_t span, const Pattern &pt)
{
    uint32_t string = 0;
    if (count_string(im, text, &string) != 1)
        return 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 7)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 7; rva++)
            if ((im.p[rva] == 0x48 || im.p[rva] == 0x4C) && im.p[rva + 1] == 0x8D && (im.p[rva + 2] & 0xC7) == 0x05
                && target(im, rva, 3, 7) == string) {
                const uint32_t hit = find(im, rva, rva + span, pt);
                if (hit != 0)
                    return hit;
            }
    }
    return 0;
}

}  // namespace

const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out)
{
    Image im = {};
    im.p = image;
    im.size = size;
    GameAddresses a = {};
    uint32_t anchor = 0, use = 0, call = 0, at = 0;
    if (image == nullptr || !parse(im))
        return "실행 파일의 머리말을 읽을 수 없습니다";

    // 1. 닻 문자열 → 그것을 쓰는 자리 → 그 자리가 든 함수
    if (count_string(im, "cheat allowcheats", &anchor) != 1)
        return "닻 문자열(cheat allowcheats)이 하나가 아닙니다";
    if (count_lea_to(im, anchor, &use) != 1)
        return "닻 문자열을 쓰는 자리가 하나가 아닙니다";
    if ((a.handler = function_root(im, use)) == 0)
        return "명령 처리 함수의 시작을 찾지 못했습니다";

    // 2. 함수 머리: cmp byte ptr [멀티플레이],0 과 or dword ptr [옵션],40h
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("80 3D ? ? ? ? 00"))) == 0)
        return "함수 머리에 멀티플레이 검사가 없습니다";
    a.multiplayer = target(im, at, 2, 7);
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("83 0D ? ? ? ? 40"))) == 0)
        return "함수 머리에 치트 허용 비트를 세우는 명령이 없습니다";
    a.options = target(im, at, 2, 7);

    // 3. 부르는 곳은 하나이고, 바로 앞에서 lea rcx,[this]
    if (count_calls_to(im, a.handler, &call) != 1)
        return "명령 처리 함수를 부르는 곳이 하나가 아닙니다";
    if (call < 7 || !matches(im, call - 7, pattern("48 8D 0D ? ? ? ?")))
        return "부르는 곳 바로 앞에 this 를 채우는 명령이 없습니다";
    a.context = target(im, call - 7, 3, 7);

    // 4. 부르는 함수의 머리: cmp dword ptr [프로그램 상태],6
    const uint32_t caller = function_root(im, call);
    if (caller == 0 || (at = find(im, caller, caller + 0x40, pattern("83 3D ? ? ? ? 06"))) == 0)
        return "부르는 함수의 머리에 프로그램 상태 검사가 없습니다";
    a.program_state = target(im, at, 2, 7);

    // 5. georgew · georgeww: mov rax,[플레이어 포인터] / movsd xmm0,[rax+…] — 둘이 같은 포인터를 써야 한다
    const Pattern read_pointer = pattern("48 8B 05 ? ? ? ? F2 0F 10 80");
    if ((at = find_in_cheat(im, "cheat georgew", 0x40, read_pointer)) == 0)
        return "cheat georgew 에서 플레이어 포인터를 읽는 명령을 찾지 못했습니다";
    a.player_pointer = target(im, at, 3, 7);
    if ((at = find_in_cheat(im, "cheat georgeww", 0x40, read_pointer)) == 0 || target(im, at, 3, 7) != a.player_pointer)
        return "georgew 와 georgeww 가 같은 플레이어 포인터를 쓰지 않습니다";

    // 6. populate: movsxd rax,[인덱스] / lea r15,[월드] / mov rcx,[r15+rax*8+지역 표]
    if ((at = find_in_cheat(im, "cheat populate", 0x40, pattern("48 63 05 ? ? ? ? 4C 8D 3D ? ? ? ?"))) == 0)
        return "cheat populate 에서 플레이어 인덱스를 읽는 명령을 찾지 못했습니다";
    a.player_index = target(im, at, 3, 7);
    const uint32_t world = target(im, at + 7, 3, 7);
    if ((at = find(im, at, at + 0x40, pattern("49 8B 8C C7 ? ? ? ?"))) == 0)
        return "cheat populate 에서 지역 표를 읽는 명령을 찾지 못했습니다";
    a.region_table = world + im.u32(at + 4);

    // 7. becomeregion: 인덱스를 쓰는 곳이 populate 가 읽는 곳과 같아야 하고, 그 뒤의 훑기에서 지역 수와 지역 표
    if ((at = find_in_cheat(im, "cheat becomeregion", 0x100, pattern("0F B7 4A 04 33 D2 89 0D ? ? ? ? 89 0D ? ? ? ? 48 63 C1"))) == 0)
        return "cheat becomeregion 에서 플레이어 인덱스를 쓰는 명령을 찾지 못했습니다";
    if (target(im, at + 6, 2, 6) != a.player_index)
        return "becomeregion 이 쓰는 곳과 populate 가 읽는 곳이 다릅니다";
    if ((at = find(im, at, at + 0x90, pattern("44 8B 0D ? ? ? ? 45 33 F6 45 85 C9 0F 88 ? ? ? ? 48 8D 0D ? ? ? ?"))) == 0)
        return "지역 수를 읽는 명령을 찾지 못했습니다";
    a.region_count = target(im, at, 3, 7);
    if (target(im, at + 19, 3, 7) != a.region_table)
        return "지역 표의 주소가 두 곳에서 다릅니다";

    // 8. 게임 진입: mov [모드 상태],2 / mov [프로그램 상태],1 — 둘째 주소가 4 에서 얻은 것과 같아야 한다
    if (count_in_code(im, pattern("C7 05 ? ? ? ? 02 00 00 00 C7 05 ? ? ? ? 01 00 00 00"), &at) != 1)
        return "게임 진입에서 상태를 쓰는 자리가 하나가 아닙니다";
    a.mode_state = target(im, at, 2, 10);
    if (target(im, at + 10, 2, 10) != a.program_state)
        return "프로그램 상태의 주소가 두 곳에서 다릅니다";

    const uint32_t all[] = {a.handler, a.context, a.multiplayer, a.options, a.program_state, a.mode_state, a.player_index,
                            a.player_pointer, a.region_table, a.region_count};
    for (uint32_t rva : all)
        if (rva == 0 || !im.has(rva, 8))
            return "찾은 주소가 실행 파일 밖입니다";
    if (!im.has(static_cast<uint64_t>(a.region_table), 8 * 1024))
        return "찾은 주소가 실행 파일 밖입니다";
    *out = a;
    return nullptr;
}
```

- [ ] **Step 7: 내보내기를 더한다** — `native/srtoybox/exports.cpp`

`#include "features.h"` 아래에 `#include "locate.h"` 를 넣고(머리말은 알파벳순이다), `srtoybox_prologue_length` 아래에 다음을 더한다.

```cpp
// 실행 파일의 이미지(RVA 대로 펼친 것)에서 주소를 찾는다. 0 이면 out 을 채웠다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)
{
    GameAddresses found = {};
    const char *why = locate_game(image, static_cast<size_t>(size), &found);
    if (why != nullptr) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}
```

- [ ] **Step 8: 빌드 목록과 Python 쪽을 더한다** — `src/srkit/toybox.py`

`import subprocess` 를 다음으로 바꾼다.

```python
import ctypes
import struct
import subprocess
```

`SOURCES` 에 `"locate.cpp"` 를 더한다(`"prologue.cpp"` 뒤).

```python
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "locate.cpp", "overlay.cpp"]
```

`IMGUI_DEFINES = …` 줄 아래에 더한다.

```python
EXE_NAME = "SupremeRuler2030.exe"
# native/srtoybox/locate.h 의 GameAddresses 와 같은 순서다
ADDRESS_FIELDS = ["handler", "context", "multiplayer", "options", "program_state", "mode_state", "player_index",
                  "player_pointer", "region_table", "region_count"]
ADDRESS_NAMES = {"handler": "명령 처리 함수", "context": "그 함수의 첫 인자(전역 객체)", "multiplayer": "멀티플레이 표시(byte)",
                 "options": "옵션 묶음(dword, 0x40 = 치트 허용)", "program_state": "프로그램 상태(dword)",
                 "mode_state": "모드 상태(dword)", "player_index": "플레이어 지역의 인덱스(dword)",
                 "player_pointer": "플레이어 지역 객체의 포인터(qword)", "region_table": "지역 포인터 표(qword × 1024)",
                 "region_count": "지역 수(dword)"}


class GameAddresses(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ADDRESS_FIELDS]
```

파일 끝에 더한다.

```python
def library(cfg: Config) -> ctypes.CDLL:
    """빌드한 DLL 을 불러 주소 찾기 함수의 인자 형을 적어 둔다(srkit locate 와 테스트가 쓴다)."""
    lib = ctypes.CDLL(str(output(cfg)))
    lib.srtoybox_locate.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p, ctypes.c_int]
    return lib


def image_of(exe: bytes) -> bytes:
    """실행 파일을 RVA 대로 펼친다 — 게임이 메모리에 올린 모양이다. 파일에 없는(초기화되지 않은) 자리는 0."""
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    sections, optional = struct.unpack_from("<H", exe, pe + 6)[0], struct.unpack_from("<H", exe, pe + 20)[0]
    size, headers = struct.unpack_from("<II", exe, pe + 24 + 56)
    image = bytearray(size)
    image[:headers] = exe[:headers]
    for i in range(sections):
        _name, virtual_size, rva, raw_size, raw = struct.unpack_from("<8sIIII", exe, pe + 24 + optional + 40 * i)
        n = min(virtual_size, raw_size)
        image[rva:rva + n] = exe[raw:raw + n]
    return bytes(image)


def locate(cfg: Config) -> tuple[dict[str, int] | None, str]:
    """설치된 게임의 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다: (이름 → RVA, "") 또는 (None, 까닭).

    게임 안에서 ToyBox 가 도는 것과 같은 코드(DLL 의 locate)를 쓴다. 파일을 읽기만 한다.
    """
    if not output(cfg).is_file():
        return None, "ToyBox DLL 이 없습니다 — srkit toybox-build"
    image = image_of((cfg.game_dir / EXE_NAME).read_bytes())
    found, error = GameAddresses(), ctypes.create_string_buffer(256)
    if library(cfg).srtoybox_locate(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in ADDRESS_FIELDS}, ""
```

- [ ] **Step 9: 빌드하고 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest tests/test_toybox_game.py -q --no-header 2>&1 | tail -5`
Expected: `빌드 완료: …srtoybox.dll`, `13 passed` (게임 설치본이 없으면 `11 passed, 2 skipped`).

`test_locate_on_the_installed_game` 이 실패하면 계획의 서명이 틀린 것이다. 멈추고, 어느 조건의 까닭이 나왔는지와 함께 보고한다(설계의 전제다).

- [ ] **Step 10: `srkit locate` 명령을 더한다** — `src/srkit/cli.py`

`cmd_toybox_build` 아래에 더한다.

```python
def cmd_locate(cfg, _args) -> int:
    exe = cfg.game_dir / toybox.EXE_NAME
    data = exe.read_bytes()
    stamp = int.from_bytes(data[int.from_bytes(data[0x3C:0x40], "little") + 8:][:4], "little")
    print(f"{exe.name}: {len(data):,} 바이트, PE TimeDateStamp {stamp:#x}")
    found, why = toybox.locate(cfg)
    if found is None:
        print(f"주소를 찾지 못했습니다: {why}")
        print("ToyBox 는 이 빌드에서 글쇠 방식으로만 동작합니다(docs/10).")
        return 1
    for name in toybox.ADDRESS_FIELDS:
        print(f"  {found[name]:#010x}  {toybox.ADDRESS_NAMES[name]}")
    print("주소를 모두 찾았습니다(대조 통과). docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0
```

`sub.add_parser("toybox-build", …)` 두 줄 아래에 더한다.

```python
    sub.add_parser("locate", help="설치된 게임에서 ToyBox 가 쓰는 주소를 찾아 보고(게임 업데이트 뒤 cheats-check 다음에)") \
        .set_defaults(fn=cmd_locate)
```

- [ ] **Step 11: 명령을 돌려 본다**

Run: `uv run srkit locate`
Expected (build 21347933):

```
SupremeRuler2030.exe: 15,494,144 바이트, PE TimeDateStamp 0x695377b6
  0x00522330  명령 처리 함수
  0x01764310  그 함수의 첫 인자(전역 객체)
  0x00f19634  멀티플레이 표시(byte)
  0x01eb556c  옵션 묶음(dword, 0x40 = 치트 허용)
  0x01eed11c  프로그램 상태(dword)
  0x00e7be30  모드 상태(dword)
  0x018294e0  플레이어 지역의 인덱스(dword)
  0x018295f8  플레이어 지역 객체의 포인터(qword)
  0x01af78c0  지역 포인터 표(qword × 1024)
  0x018294d8  지역 수(dword)
주소를 모두 찾았습니다(대조 통과). docs/11 의 표와 다르면 게임이 바뀐 것입니다.
```

- [ ] **Step 12: 전체 테스트**

Run: `uv run pytest -q --no-header 2>&1 | tail -2`
Expected: `143 passed` (130 + 13).

- [ ] **Step 13: 커밋 · PR · 머지**

```bash
git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/exports.cpp src/srkit/toybox.py src/srkit/cli.py tests/toybox_fake_exe.py tests/test_toybox_game.py
git commit -m "feat: ToyBox — 올라와 있는 실행 파일에서 주소를 찾는다 (locate, srkit locate)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/toybox-locate
```

PR 을 `develop` 으로 올린다(본문: 무엇을 찾는지, 대조 8가지, `uv run pytest` 결과, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`). `gh pr merge <번호> --merge` 로 머지하고 `git switch develop && git pull --ff-only origin develop`.

---

### Task 2: 게임 상태 읽기, 나라 이름표, 상태 줄, 게임 밖에서 단추 끄기

**브랜치:** `feat/toybox-game-state` (`develop` 에서)

**Files:**
- Create: `native/srtoybox/game.h`, `native/srtoybox/game.cpp`, `native/srtoybox/regions.h`, `native/srtoybox/regions.cpp`
- Create: `tests/toybox_fake_game.py`
- Modify: `native/srtoybox/runner.h`, `native/srtoybox/runner.cpp`, `native/srtoybox/runner_win.h`, `native/srtoybox/runner_win.cpp`, `native/srtoybox/ui.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`
- Modify: `tests/test_toybox_game.py`, `tests/test_toybox.py`, `tests/toybox_overlay_probe.py`

**Interfaces:**
- Consumes: Task 1 의 `GameAddresses`, `locate_game`, `srkit.toybox.ADDRESS_FIELDS` · `GameAddresses` · `library`.
- Produces:
  - C++ `struct GameState { bool known, in_game, multiplayer, cheats_on; int player; };`
  - C++ `GameState read_game(const uint8_t *base, const GameAddresses &at);` `std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at);`
  - C++ `void game_init();` `GameState game_state();` `std::vector<int> game_regions();` `void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);`
  - C++ `struct RegionName { int number; const char *ko; const char *en; };` `const RegionName *find_region(int number);` `std::string region_label(int number);`
  - C++ `bool Runner::starting() const;` `void Runner::clear();` `std::string runner_notice();`
  - 내보내기 `int srtoybox_game_state(const unsigned char *base, const GameAddresses *at, char *out, int size)` — `known=1 in_game=1 multiplayer=0 cheats=0 player=1499 regions=1106,1499`
  - 내보내기 `void srtoybox_test_game(const unsigned char *base, const GameAddresses *at, void *handler)`, `int srtoybox_region_label(int number, char *out, int size)`
  - Python `srkit.toybox.region_rows(cfg) -> list[tuple[int, str, str]]`, `srkit.toybox.c_string(text) -> str`
  - Python `tests/toybox_fake_game.py` 의 `FakeGame`(`.base`, `.at`, `.menu()`, `.play(index)`, `.region(index, number, alive=2)`, `.poke(offset, fmt, value)`, `.peek(offset, fmt)`)
  - 프로브: `fake_game(hook, handler=None) -> FakeGame`, 모드 `gate_menu` · `gate_leave` · `gate_typing`. `BUTTON = (90, 208)`.
  - 테스트 도우미: `_probe(cfg, tmp_path, mode, env=None)`, `typed_keys(command) -> str`

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-game-state
```

- [ ] **Step 2: 가짜 게임 메모리를 쓴다** — `tests/toybox_fake_game.py`

```python
"""가짜 게임 메모리: ToyBox 가 읽는 전역과 지역 객체를 Python 버퍼로 흉내 낸다.

tests/test_toybox_game.py 와 tests/toybox_overlay_probe.py 가 쓴다(pytest 가 직접 모으는 테스트 파일이 아니다).
전역은 mem 의 앞쪽에, 지역 표는 0x1000 부터 있다. 지역 객체는 게임처럼 따로 잡은 버퍼이고 표가 그 주소를 가리킨다.
"""
import ctypes
import struct

from srkit.toybox import GameAddresses

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x1000


class FakeGame:
    def __init__(self):
        self.mem = (ctypes.c_ubyte * 0x4000)()
        self.base = ctypes.addressof(self.mem)
        self.at = GameAddresses(handler=0, context=0x40, multiplayer=MULTIPLAYER, options=OPTIONS, program_state=PROGRAM,
                                mode_state=MODE, player_index=INDEX, player_pointer=POINTER, region_table=TABLE, region_count=COUNT)
        self.objects: dict[int, ctypes.Array] = {}
        self.menu()

    def poke(self, offset: int, fmt: str, value: int) -> None:
        struct.pack_into(fmt, self.mem, offset, value)

    def peek(self, offset: int, fmt: str) -> int:
        return struct.unpack_from(fmt, self.mem, offset)[0]

    def region(self, index: int, number: int, alive: int = 2) -> None:
        """지역 객체 하나: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word)."""
        obj = (ctypes.c_ubyte * 16)()
        struct.pack_into("<IHHH", obj, 0, alive, index, 0, number)
        self.objects[index] = obj
        self.poke(TABLE + 8 * index, "<Q", ctypes.addressof(obj))
        self.poke(COUNT, "<i", max(self.peek(COUNT, "<i"), index))

    def menu(self) -> None:
        """메인 메뉴 · 로비: 상태 3 / 1, 플레이어 포인터는 비어 있다(인덱스는 낡은 값이 남는다)."""
        self.poke(PROGRAM, "<i", 3)
        self.poke(MODE, "<i", 1)
        self.poke(POINTER, "<Q", 0)

    def play(self, index: int) -> None:
        """그 인덱스의 지역으로 게임을 진행 중이다."""
        self.poke(PROGRAM, "<i", 1)
        self.poke(MODE, "<i", 2)
        self.poke(INDEX, "<i", index)
        self.poke(POINTER, "<Q", ctypes.addressof(self.objects[index]))
```

- [ ] **Step 3: 실패하는 테스트를 쓴다** — `tests/test_toybox_game.py`

`import toybox_fake_exe` 아래에 `from toybox_fake_game import INDEX, MULTIPLAYER, OPTIONS, POINTER, TABLE, FakeGame` 를 넣고, `lib` 픽스처를 다음으로 바꾼다(인자 형을 더 적는다).

```python
@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_game_state.argtypes = [ctypes.c_void_p, ctypes.POINTER(toybox.GameAddresses), ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_region_label.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib
```

파일 끝에 더한다.

```python
def state(lib, fake: FakeGame) -> dict[str, str]:
    out = ctypes.create_string_buffer(8192)
    assert lib.srtoybox_game_state(fake.base, ctypes.byref(fake.at), out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def germany() -> FakeGame:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 폴란드(141, 1106)와 덴마크(150, 1201)가 있다."""
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(150, 1201)
    fake.region(176, 1499)
    fake.play(176)
    return fake


def test_game_state_in_a_game(lib):
    assert state(lib, germany()) == {"known": "1", "in_game": "1", "multiplayer": "0", "cheats": "0", "player": "1499",
                                     "regions": "1106,1201,1499"}


def test_game_state_outside_a_game(lib):
    """메뉴 · 로비: 플레이어 포인터가 비어 있다. 인덱스에 낡은 값이 남아 있어도 진행 중이 아니다."""
    fake = germany()
    fake.menu()
    assert state(lib, fake) == {"known": "1", "in_game": "0", "multiplayer": "0", "cheats": "0", "player": "0", "regions": ""}


def test_game_state_reads_the_cheat_bit_and_the_multiplayer_flag(lib):
    fake = germany()
    fake.poke(OPTIONS, "<I", 0x6072B0C1)
    fake.poke(MULTIPLAYER, "<B", 1)
    got = state(lib, fake)
    assert got["cheats"] == "1" and got["multiplayer"] == "1"
    fake.poke(OPTIONS, "<I", 0x6072B081)            # 비트 0x40 만 꺼진 값(다른 비트는 다른 옵션이다)
    assert state(lib, fake)["cheats"] == "0"


def test_game_state_survives_a_pointer_it_cannot_read(lib):
    """낡은 포인터를 만나도 죽지 않는다. 읽을 수 없으면 모르는 것으로 친다(→ 글쇠 방식)."""
    fake = germany()
    for address in (0x00007FFFFFFF0000, 0x8000000000000000, 8):
        fake.poke(POINTER, "<Q", address)
        fake.poke(TABLE + 8 * 176, "<Q", address)
        assert state(lib, fake)["known"] == "0"


@pytest.mark.parametrize("flaw", ["table", "number", "dead", "index", "self_index"])
def test_game_state_that_does_not_add_up_is_unknown(lib, flaw):
    """게임 안인데 읽은 값이 서로 맞지 않으면 구조가 바뀐 빌드일 수 있다 — 모르는 것으로 친다."""
    fake = germany()
    if flaw == "table":
        fake.poke(TABLE + 8 * 176, "<Q", fake.peek(TABLE + 8 * 141, "<Q"))    # 표[인덱스] 가 플레이어 포인터와 다르다
    elif flaw == "number":
        struct.pack_into("<H", fake.objects[176], 8, 0)                       # 지역 번호가 0
    elif flaw == "dead":
        struct.pack_into("<I", fake.objects[176], 0, 0)                       # 죽은 지역
    elif flaw == "index":
        fake.poke(INDEX, "<i", 2000)                                          # 표 밖의 인덱스
    else:
        struct.pack_into("<H", fake.objects[176], 4, 175)                     # 객체가 아는 자기 인덱스가 다르다
    got = state(lib, fake)
    assert got["known"] == "0" and got["in_game"] == "0"


def test_regions_skip_empty_dead_and_inconsistent_slots(lib):
    fake = germany()
    fake.region(10, 500, alive=0)                                             # 죽은 지역
    fake.region(11, 501)
    struct.pack_into("<H", fake.objects[11], 4, 12)                           # 자기 인덱스가 칸과 다르다
    fake.region(12, 0)                                                        # 번호가 없다
    fake.poke(TABLE + 8 * 13, "<Q", 0x00007FFFFFFF0000)                       # 읽을 수 없는 포인터
    assert state(lib, fake)["regions"] == "1106,1201,1499"


def label(lib, number: int) -> str:
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_region_label(number, out, len(out)) >= 0
    return out.value.decode("utf-8")


def test_region_names(lib):
    """이름표는 저장소의 번역 테이블에서 온다. 표에 없는 번호는 #번호 로 보인다."""
    assert label(lib, 1499) == "독일" and label(lib, 1106) == "폴란드"
    assert label(lib, 12345) == "#12345" and label(lib, 0) == "#0" and label(lib, -7) == "#-7"


def test_region_rows_come_from_the_translation_table(cfg):
    rows = toybox.region_rows(cfg)
    assert [n for n, _, _ in rows] == sorted({n for n, _, _ in rows}) and len(rows) > 300
    assert (1499, "독일", "Germany") in rows
    assert all(ko and en for _, ko, en in rows)


def test_region_table_escapes_names():
    """이름에 따옴표나 역슬래시가 있어도 생성물이 C++ 문자열로 컴파일되어야 한다."""
    assert toybox.c_string('Côte d\'Ivoire') == '"Côte d\'Ivoire"'
    assert toybox.c_string('a"b') == '"a\\"b"'
    assert toybox.c_string("a\\b") == '"a\\\\b"'
    assert toybox.regions_inc([(7, 'x"y', "z\\")]) == '{7, "x\\"y", "z\\\\"},\n'
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox_game.py -q --no-header 2>&1 | tail -4`
Expected: 새 테스트가 `AttributeError: function 'srtoybox_game_state' not found` 로 오류(먼저 있던 13개도 픽스처가 깨져 함께 오류).

- [ ] **Step 5: 이름표 생성을 더한다** — `src/srkit/toybox.py`

머리말을 다음으로 바꾼다.

```python
import csv
import ctypes
import re
import struct
import subprocess
```

`SOURCES` 에 `"game.cpp"`, `"regions.cpp"` 를 더한다.

```python
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "locate.cpp", "game.cpp", "regions.cpp", "overlay.cpp"]
```

`EXE_NAME = …` 줄 아래에 더한다.

```python
REGION_TABLE = "mods/korean/translation/localtext-regions.csv"   # REGIONTEXT|<지역 번호>|0 행이 지역의 이름이다
```

`_quoted` 함수 아래에 더한다.

```python
def region_rows(cfg: Config) -> list[tuple[int, str, str]]:
    """번역 테이블에서 (지역 번호, 한글 이름, 영문 이름)을 번호순으로. 번역이 빈 행은 영문 이름을 쓴다."""
    rows: dict[int, tuple[str, str]] = {}
    with (cfg.root / REGION_TABLE).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            m = re.fullmatch(r"REGIONTEXT\|(\d+)\|0", row["key"])
            en = row["en"].strip()
            if m and en:
                rows[int(m[1])] = (row["ko"].strip() or en, en)
    return [(number, *rows[number]) for number in sorted(rows)]


def c_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def regions_inc(rows: list[tuple[int, str, str]]) -> str:
    """native/srtoybox/regions.cpp 가 끼워 넣는 초기화 목록(한 줄에 지역 하나)."""
    return "".join(f"{{{number}, {c_string(ko)}, {c_string(en)}}},\n" for number, ko, en in rows)
```

`build()` 에서 `include = …` 줄을 다음 두 줄로 바꾼다(생성물은 `build/toybox-obj/` 에 두고 그 폴더를 포함 경로에 넣는다).

```python
    (obj / "regions_table.inc").write_text(regions_inc(region_rows(cfg)), encoding="utf-8", newline="\n")
    include = f'/I"{imgui}" /I"{imgui / "backends"}" /I"{obj}" {IMGUI_DEFINES}'
```

- [ ] **Step 6: `regions.h` · `regions.cpp` 를 쓴다**

`native/srtoybox/regions.h`:

```cpp
// 지역 번호 → 이름. 표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/localtext-regions.csv)에서 만든다
// (src/srkit/toybox.py 의 regions_inc → build/toybox-obj/regions_table.inc).
#pragma once

#include <string>

struct RegionName {
    int number;
    const char *ko;   // UTF-8
    const char *en;
};

const RegionName *find_region(int number);   // 표에 없으면 nullptr
std::string region_label(int number);        // "독일". 표에 없으면 "#1499"
```

`native/srtoybox/regions.cpp`:

```cpp
#include "regions.h"

namespace {

const RegionName NAMES[] = {   // 번호 오름차순
#include "regions_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

}  // namespace

const RegionName *find_region(int number)
{
    int lo = 0, hi = NAME_COUNT;
    while (lo < hi) {
        const int mid = lo + (hi - lo) / 2;
        if (NAMES[mid].number == number)
            return &NAMES[mid];
        if (NAMES[mid].number < number)
            lo = mid + 1;
        else
            hi = mid;
    }
    return nullptr;
}

std::string region_label(int number)
{
    const RegionName *name = find_region(number);
    return name != nullptr ? std::string(name->ko) : "#" + std::to_string(number);
}
```

- [ ] **Step 7: `game.h` · `game.cpp` 를 쓴다**

`native/srtoybox/game.h`:

```cpp
// 찾은 주소(locate.h)로 게임의 상태를 읽는다. 읽기만 한다 — 게임의 메모리에 쓰지 않는다.
#pragma once

#include <cstdint>
#include <vector>

#include "locate.h"

struct GameState {
    bool known = false;         // 주소를 찾았고, 읽은 값이 서로 맞는다. 거짓이면 ToyBox 는 1단계처럼(글쇠 방식으로) 동작한다
    bool in_game = false;       // 게임을 진행 중이다
    bool multiplayer = false;
    bool cheats_on = false;     // 치트 허용 비트
    int player = 0;             // 플레이어 지역의 번호(in_game 일 때만)
};

// base: 실행 파일이 올라온 주소(테스트에서는 가짜 메모리). 읽을 수 없는 주소를 만나도 죽지 않는다.
GameState read_game(const uint8_t *base, const GameAddresses &at);
// 이번 게임에 있는 지역의 번호들(오름차순). 진행 중이 아니면 빈 목록.
std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at);

void game_init();                  // 올라와 있는 실행 파일에서 주소를 찾는다(시작할 때 한 번). 결과를 로그에 적는다
GameState game_state();            // 지금의 상태. 부를 때마다 읽는다 — 플레이어는 게임 중에 바뀔 수 있다(cheat becomeregion)
std::vector<int> game_regions();
// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);
```

`native/srtoybox/game.cpp`:

```cpp
#include "game.h"

#include <windows.h>

#include <algorithm>
#include <cstring>
#include <mutex>

#include "log.h"

namespace {

const int MAX_REGIONS = 1024;   // 지역 표의 칸 수
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)

std::mutex g_lock;
const uint8_t *g_base;
GameAddresses g_at;
bool g_located, g_told;

// 안전한 읽기: 낡은 포인터를 만나도 죽지 않는다.
bool peek(const void *address, void *out, size_t size)
{
    SIZE_T got = 0;
    return ReadProcessMemory(GetCurrentProcess(), address, out, size, &got) != 0 && got == size;
}

// base 에서 offset 만큼 떨어진 값 하나.
template <class T>
bool peek_at(const uint8_t *base, uint64_t offset, T *out)
{
    return peek(base + offset, out, sizeof(T));
}

// 지역 객체의 머리: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word)
struct Region {
    uint32_t alive;
    int index, number;
};

bool peek_region(uint64_t pointer, Region *out)
{
    uint8_t raw[10];
    uint16_t index = 0, number = 0;
    if (pointer == 0 || !peek(reinterpret_cast<const void *>(pointer), raw, sizeof(raw)))
        return false;
    memcpy(&out->alive, raw, 4);
    memcpy(&index, raw + 4, 2);
    memcpy(&number, raw + 8, 2);
    out->index = index;
    out->number = number;
    return true;
}

bool usable(const Region &r, int index)
{
    return r.alive != 0 && r.index == index && r.number > 0 && r.number < MAX_NUMBER;
}

bool located(const uint8_t **base, GameAddresses *at)
{
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    return g_located;
}

}  // namespace

GameState read_game(const uint8_t *base, const GameAddresses &at)
{
    GameState s;
    uint8_t multiplayer = 0;
    uint32_t options = 0;
    int32_t program = 0, mode = 0, index = 0, count = 0;
    uint64_t pointer = 0, slot = 0;
    if (base == nullptr || !peek_at(base, at.multiplayer, &multiplayer) || !peek_at(base, at.options, &options)
        || !peek_at(base, at.program_state, &program) || !peek_at(base, at.mode_state, &mode)
        || !peek_at(base, at.player_index, &index) || !peek_at(base, at.player_pointer, &pointer)
        || !peek_at(base, at.region_count, &count))
        return s;
    s.known = true;
    s.multiplayer = multiplayer != 0;
    s.cheats_on = (options & 0x40) != 0;
    if (mode != 2 || program != 1 || pointer == 0)
        return s;   // 게임 밖(메뉴 · 로비). 인덱스는 낡은 값이 남으므로 보지 않는다

    // 게임 안이라면 읽은 값들이 서로 맞아야 한다. 안 맞으면 구조가 바뀐 빌드일 수 있다 — 모르는 것으로 친다
    Region player = {};
    if (index < 1 || index >= MAX_REGIONS || count < 1 || count >= MAX_REGIONS
        || !peek_at(base, at.region_table + 8ull * static_cast<uint64_t>(index), &slot) || slot != pointer
        || !peek_region(pointer, &player) || !usable(player, index)) {
        s.known = false;
        return s;
    }
    s.in_game = true;
    s.player = player.number;
    return s;
}

std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at)
{
    std::vector<int> out;
    int32_t count = 0;
    if (!read_game(base, at).in_game || !peek_at(base, at.region_count, &count) || count < 1 || count >= MAX_REGIONS)
        return out;   // 지역 수는 방금 다시 읽은 값이다 — 그 사이에 바뀌었을 수 있다
    std::vector<uint64_t> table(static_cast<size_t>(count) + 1);
    if (!peek(base + at.region_table, table.data(), table.size() * sizeof(uint64_t)))
        return out;
    for (int i = 1; i <= count; i++) {
        Region r = {};
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i))
            out.push_back(r.number);
    }
    std::sort(out.begin(), out.end());
    return out;
}

void game_init()
{
    const uint8_t *base = reinterpret_cast<const uint8_t *>(GetModuleHandleW(nullptr));
    const IMAGE_DOS_HEADER *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    const IMAGE_NT_HEADERS64 *nt = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    GameAddresses at = {};
    const char *why = locate_game(base, nt->OptionalHeader.SizeOfImage, &at);
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_base = base;
        g_at = at;
        g_located = why == nullptr;
        g_told = false;
    }
    if (why == nullptr)
        log_line("게임 상태를 읽습니다 (명령 처리 함수 +0x%X)", at.handler);
    else
        log_line("게임 상태를 읽을 수 없습니다 (%s) — 글쇠 방식", why);
}

GameState game_state()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    if (!located(&base, &at))
        return GameState();
    const GameState s = read_game(base, at);
    if (!s.known) {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_told) {
            g_told = true;
            log_line("게임에서 읽은 값이 서로 맞지 않습니다 — 글쇠 방식");
        }
    }
    return s;
}

std::vector<int> game_regions()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    return located(&base, &at) ? read_regions(base, at) : std::vector<int>();
}

void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler)
{
    (void)handler;   // 명령 처리 함수는 직접 실행(Task 3)에서 쓴다
    std::lock_guard<std::mutex> lock(g_lock);
    g_base = base;
    g_at = at != nullptr ? *at : GameAddresses();
    g_located = base != nullptr && at != nullptr;
    g_told = false;
}
```

- [ ] **Step 8: 내보내기를 더하고 시작할 때 주소를 찾게 한다** — `native/srtoybox/exports.cpp`

머리말에 `#include "game.h"` 와 `#include "regions.h"` 를 넣는다(알파벳순: `features.h` 다음에 `game.h`, `prologue.h` 다음에 `regions.h`). `srtoybox_locate` 아래에 더한다.

```cpp
// 테스트: 가짜 메모리에서 상태를 읽는다. "known=1 in_game=1 multiplayer=0 cheats=0 player=1499 regions=1106,1499"
EXPORT int srtoybox_game_state(const unsigned char *base, const GameAddresses *at, char *out, int size)
{
    if (at == nullptr)
        return -1;
    const GameState s = read_game(base, *at);
    std::string regions;
    for (int number : read_regions(base, *at))
        regions += (regions.empty() ? "" : ",") + std::to_string(number);
    return put("known=" + std::to_string(s.known) + " in_game=" + std::to_string(s.in_game) + " multiplayer="
               + std::to_string(s.multiplayer) + " cheats=" + std::to_string(s.cheats_on) + " player=" + std::to_string(s.player)
               + " regions=" + regions, out, size);
}

// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다(주소 찾기의 결과를 덮어쓴다).
EXPORT void srtoybox_test_game(const unsigned char *base, const GameAddresses *at, void *handler)
{
    game_set_for_test(base, at, handler);
}

EXPORT int srtoybox_region_label(int number, char *out, int size)
{
    return put(region_label(number), out, size);
}
```

`srtoybox_start` 를 다음으로 바꾼다.

```cpp
EXPORT void WINAPI srtoybox_start(void)
{
    log_line("시작 (프로세스 %lu)", GetCurrentProcessId());
    ui_init();
    game_init();          // 화면에 끼어들기 전에 끝낸다 — 창이 뜰 때는 게임을 읽을 수 있는지가 이미 정해져 있다
    overlay_install();
}
```

- [ ] **Step 9: 빌드하고 상태 · 이름표 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest tests/test_toybox_game.py -q --no-header 2>&1 | tail -3`
Expected: `빌드 완료`, `26 passed` (먼저 있던 13 + 새 13: 상태 4 · 맞지 않음 5 · 지역 1 · 이름표 3).

- [ ] **Step 10: 프로브에 가짜 게임과 "단추 끄기" 모드를 더한다** — `tests/toybox_overlay_probe.py`

(가) 문서 주석의 `scale …` 줄 아래에 더한다.

```
게임 상태에 따른 단추 (출력 "button=<창 위 누름이 게임에 갔는가> text=<게임이 받은 글>"):
    gate_menu        ToyBox 가 게임을 읽을 수 있고 메뉴에 있다 — 단추가 꺼져 있다
    gate_leave       게임 안에서 단추를 누른 직후(실행되기 전) 메뉴로 나갔다 — 실행하지 않는다
    gate_typing      게임 안, 글쇠 방식(SRTOYBOX_DIRECT=0) — 1단계처럼 글쇠가 간다
```

(나) `BUTTON` 을 고친다 — 탭 위에 상태 줄(글자 18px + 줄 간격 4px = 22px)이 생겨 그 아래가 22px 내려간다.

```python
BUTTON = (90, 208)          # 돈 탭의 둘째 줄 "국고 +$10 B" (cheat georgew). 상태 줄이 생기기 전에는 (90, 186)
```

(다) 머리말의 `sys.stdout.reconfigure(encoding="utf-8")` 아래에 더한다.

```python
from toybox_fake_game import FakeGame  # noqa: E402  (이 파일과 같은 폴더)
```

(라) `start_game` 함수 아래에 더한다.

```python
def fake_game(hook: str, handler: int | None = None) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106)와 독일(176, 1499)이 있고 메뉴 상태다.

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    """
    toybox = ctypes.WinDLL(str(Path(hook).with_name("srtoybox.dll")))
    toybox.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    return fake


def run_gate(hook: str, mode: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    fake = fake_game(hook)
    if mode != "gate_menu":
        fake.play(176)
    game.hotkey()
    button = game.click(BUTTON)
    if mode == "gate_leave":
        fake.menu()                                           # 눌린 명령이 실행되기 전에 게임에서 나갔다
    game.got.clear()
    game.pump(lambda: game.has("up", 0x1B), 20 if mode == "gate_typing" else 2)
    game.wait(0.4)
    print(f"button={button} text={game.text()}")
    return 0
```

(마) `main()` 의 `if mode == "scale":` 두 줄 아래에 더한다.

```python
    if mode.startswith("gate_"):
        return run_gate(hook, mode)
```

- [ ] **Step 11: 실패하는 프로브 테스트를 쓴다** — `tests/test_toybox.py`

(가) `_probe` 가 환경 변수를 받게 한다. 함수의 머리와 `subprocess.run` 줄을 다음으로 바꾼다.

```python
def _probe(cfg, tmp_path, mode: str, env: dict[str, str] | None = None) -> str:
```

```python
    run = subprocess.run([sys.executable, str(probe), str(tmp_path / "hookcopy.dll"), mode], capture_output=True, text=True,
                         encoding="utf-8", env={**os.environ, "SRTOYBOX_HOME": str(home), **(env or {})}, timeout=120)
```

(나) `expected_plan` 함수 아래에 도우미를 더하고,

```python
def typed_keys(command: str) -> str:
    """글쇠 방식으로 그 명령을 넣을 때 게임이 받는 것(프로브의 Game.text 와 같은 표기): 글자는 그대로, 누름은 <이름>."""
    keys = {13: "<Enter>", 27: "<Esc>", 83: "<S>", 17: "<Ctrl>", 16: "<Shift>"}
    steps = [step.split() for step in expected_plan(command)]
    return "".join(chr(int(v)) if act == "CHAR" else keys[int(v)] for act, v in steps if act in ("CHAR", "DOWN"))
```

`test_keys_and_clicks_reach_only_the_side_they_are_meant_for` 안의 `keys = …` · `steps = …` · `assert got["text"] == "".join(…)` 세 줄을 다음 한 줄로 바꾼다.

```python
    assert got["text"] == typed_keys("cheat georgew")
```

(다) `test_the_hook_starts_toybox_and_it_writes_a_log` 의 마지막 `assert` 아래에 한 줄을 더한다.

```python
    assert "게임 상태를 읽을 수 없습니다" in log, log     # 게임이 아닌 프로세스다 — 주소를 못 찾고 글쇠 방식으로 남는다
```

(라) `test_mouse_follows_the_size_the_game_draws_at` 아래에 더한다.

```python
def test_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    """ToyBox 가 게임을 읽을 수 있으면, 메뉴에서는 단추를 눌러도 게임에 아무것도 가지 않는다."""
    got = _fields(_probe(cfg, tmp_path, "gate_menu"))
    assert got["button"] == "none" and got["text"] == ""


def test_a_queued_command_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 실행되기 전에 게임에서 나가면, 그 명령을 메뉴에 넣지 않고 버린다."""
    got = _fields(_probe(cfg, tmp_path, "gate_leave"))
    assert got["button"] == "none" and got["text"] == ""


def test_the_typing_route_still_works_in_a_game_toybox_can_read(dll, cfg, tmp_path):
    got = _fields(_probe(cfg, tmp_path, "gate_typing", env={"SRTOYBOX_DIRECT": "0"}))
    assert got["text"] == typed_keys("cheat georgew")
```

- [ ] **Step 12: 창에 상태 줄을 넣는다** — `native/srtoybox/ui.cpp`

(단추 끄기는 Step 16 에서 한다. 여기서는 상태 줄만 — 이 줄이 생겨야 프로브의 `BUTTON` 자리가 맞는다.)

머리말에 `#include "game.h"` (`features.h` 다음)와 `#include "regions.h"` (`overlay.h` 다음)를 넣는다. `settings_tab()` 함수 아래(이름 없는 namespace 안)에 더한다.

```cpp
// 상태 줄: ToyBox 가 게임을 어떻게 보고 있는지 한 줄로.
void status_line(const GameState &game)
{
    if (!game.known)
        ImGui::TextDisabled("게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다");
    else if (game.multiplayer)
        ImGui::TextUnformatted("멀티플레이에서는 동작하지 않습니다");
    else if (!game.in_game)
        ImGui::TextUnformatted("게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다");
    else
        ImGui::Text("플레이 중: %s (%d)", region_label(game.player).c_str(), game.player);
}
```

`ui_draw()` 에서 `if (ImGui::Begin(…)) {` 바로 아래에 두 줄을 넣는다.

```cpp
        const GameState game = game_state();
        status_line(game);
```

- [ ] **Step 13: 빌드하고 프로브 테스트가 실패하는 것을 본다**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest tests/test_toybox.py -q --no-header -k "outside_a_game or dropped or typing_route or keys_and_clicks" 2>&1 | grep -E "^(FAILED|E  |[0-9]+ (failed|passed))" | cut -c1-200`
Expected: `2 failed, 2 passed`.
- `test_buttons_are_off_outside_a_game` 과 `test_a_queued_command_is_dropped_when_the_game_ends_first` 가 FAIL — 메뉴 상태인데 `text` 에 `<Ctrl><Shift><S>cheat allowcheats…` 가 들어 있다(아직 상태를 보지 않고 넣는다).
- `test_keys_and_clicks…` 와 `test_the_typing_route…` 는 PASS — 단추가 `BUTTON` 자리에 있다는 뜻이다.

`test_keys_and_clicks…` 가 "게임이 받은 글이 비었다"로 실패하면 단추의 자리가 `BUTTON` 과 다른 것이다. 상태 줄 한 줄의 높이는 `ImGui::GetTextLineHeightWithSpacing()` 이다 — 프로브의 `BUTTON` 의 y 를 196 … 220 사이에서 바꿔 가며 글이 들어오는 값을 찾아 고치고, 그 까닭을 주석에 적는다.

- [ ] **Step 14: 실행기가 시작 전에 상태를 보게 한다**

`native/srtoybox/runner.h` 의 `bool busy() const …` 줄 위에 더한다.

```cpp
    bool starting() const { return plan_.empty() && !queue_.empty(); }   // 다음 틱에 새 명령을 시작한다
    void clear();                               // 대기열을 비운다(넣던 것이 있으면 그것도)
```

`native/srtoybox/runner.cpp` 끝에 더한다.

```cpp
void Runner::clear()
{
    queue_.clear();
    plan_.clear();
}
```

`native/srtoybox/runner_win.h` 끝에 더한다.

```cpp
std::string runner_notice();                       // 실행하지 못한 까닭(창에 보인다). 없으면 빈 글
```

`native/srtoybox/runner_win.cpp`: 머리말에 `#include "game.h"` 를 넣고(`#include "runner.h"` 위), `BYTE g_before[2];` 줄 아래에 `std::string g_notice;   // 실행하지 못한 까닭` 을 더하고, `runner_tick` 을 다음으로 바꾸고, 파일 끝에 `runner_notice` 를 더한다.

```cpp
void runner_tick(HWND hwnd)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_runner.starting()) {
        const GameState game = game_state();
        if (game.known && (!game.in_game || game.multiplayer)) {
            g_runner.clear();   // 누른 뒤 게임에서 나갔다 — 메뉴에 글쇠를 넣지 않는다
            g_notice = "게임이 진행 중이 아니어서 실행하지 않았습니다.";
            return;
        }
        g_notice.clear();
    }
    GameSink sink(hwnd);
    g_runner.tick(sink);
}
```

```cpp
std::string runner_notice()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_notice;
}
```

- [ ] **Step 15: 빌드하고 프로브 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest tests/test_toybox.py -q --no-header -k "outside_a_game or dropped or typing_route or keys_and_clicks" 2>&1 | tail -1`
Expected: `4 passed`.

- [ ] **Step 16: 게임 밖에서 단추를 끄고, 실행하지 못한 까닭을 보인다** — `native/srtoybox/ui.cpp`

(단추가 흐려지는 것은 화면으로만 볼 수 있다 — Step 18 의 H1 에서 본다. 프로브의 `gate_menu` 는 실행기의 검사만으로도 통과한다.)

`status_line(game);` 줄 위에 한 줄을 넣는다.

```cpp
        const bool blocked = game.known && (!game.in_game || game.multiplayer);   // 게임을 읽을 수 있는데 진행 중이 아니다
```

기능 탭의 줄을 그리는 `for` 를 끄기로 감싼다 — 다음 두 줄을

```cpp
                    for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                        row(FEATURES[j]);
```

다음으로 바꾼다.

```cpp
                    ImGui::BeginDisabled(blocked);
                    for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                        row(FEATURES[j]);
                    ImGui::EndDisabled();
```

창 아래쪽의 안내를 바꾼다 — 이 네 줄을

```cpp
        if (!g_notice.empty())
            ImGui::TextUnformatted(g_notice.c_str());
        ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        ImGui::TextWrapped("게임을 진행하는 중에만 누르십시오. 메뉴나 로비에서는 글자가 다른 곳에 들어갈 수 있습니다.");
```

다음으로.

```cpp
        if (!g_notice.empty())
            ImGui::TextUnformatted(g_notice.c_str());
        const std::string trouble = runner_notice();
        if (!trouble.empty())
            ImGui::TextUnformatted(trouble.c_str());
        ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        if (!game.known)   // 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로 이 주의가 필요 없다
            ImGui::TextWrapped("게임을 진행하는 중에만 누르십시오. 메뉴나 로비에서는 글자가 다른 곳에 들어갈 수 있습니다.");
```

- [ ] **Step 17: 빌드하고 전체 테스트**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest -q --no-header 2>&1 | tail -2`
Expected: `빌드 완료`, `159 passed` (143 + 상태 · 이름표 13 + 프로브 3).

- [ ] **Step 18: 게임에서 본다 (H1 · H2 · H10)**

시험용 빌드를 넣는다. 미리보기에 `갱신: srtoybox.dll` 한 줄만 있어야 한다.

```bash
uv run srkit deploy toybox
uv run srkit deploy toybox --apply
```

게임을 화면 밖에서 띄우고(백그라운드 작업) 메인 메뉴 → 게임 → 메인 메뉴로 몰면서 창을 찍는다. `build/verify/toybox/` 에 `H1-menu.png` `H2-game.png` `H10-back.png`. 괄호 안의 시간만큼 기다린 뒤 다음 줄로 간다.

```bash
export SRTOYBOX_HOME="E:/SR2030ToyBox/build/verify/toybox/home"
uv run python scripts/gamedrive.py start            # (38초)
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py shot build/verify/toybox/H1-menu.png
uv run python scripts/gamedrive.py click 90 208     # 꺼진 단추 — 아무 일도 없어야 한다
uv run python scripts/gamedrive.py shot build/verify/toybox/H1-menu-clicked.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py click 512 340    # 샌드박스 (3초)
uv run python scripts/gamedrive.py click 797 240    # 2030 - 세계 (2초)
uv run python scripts/gamedrive.py click 601 725    # 시작 (32초)
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py shot build/verify/toybox/H2-game.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py key ESC          # 게임 메뉴 (1.5초)
uv run python scripts/gamedrive.py click 205 456    # 게임 종료 (2.5초)
uv run python scripts/gamedrive.py click 512 325    # 게임 종료(저장하지 않음). 바로 아래의 "저장 후 종료"(y 369)는 누르지 않는다 (12초)
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py shot build/verify/toybox/H10-back.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py click 607 605    # 메인 메뉴의 종료 단추 (4초)
uv run python scripts/gamedrive.py status           # "프로세스: 없음" 이어야 한다
```

Expected:
- `H1-menu.png`: 상태 줄 "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다", 단추가 흐리다. `H1-menu-clicked.png`: "마지막으로 넣은 것"이 생기지 않았다.
- `H2-game.png`: 상태 줄 "플레이 중: 독일 (1499)", 단추가 켜져 있다.
- `H10-back.png`: 다시 "게임을 진행 중이 아닙니다".
- `build/verify/toybox/home/toybox.log` 에 `게임 상태를 읽습니다 (명령 처리 함수 +0x522330)`.

로그에 `게임 상태를 읽을 수 없습니다` 가 나오면 멈추고 그 까닭과 함께 보고한다. 본 것은 Task 5 에서 `docs/10` 에 적는다.

- [ ] **Step 19: 커밋 · PR · 머지**

```bash
git add native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/regions.h native/srtoybox/regions.cpp native/srtoybox/runner.h native/srtoybox/runner.cpp native/srtoybox/runner_win.h native/srtoybox/runner_win.cpp native/srtoybox/ui.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/toybox_fake_game.py tests/test_toybox_game.py tests/test_toybox.py tests/toybox_overlay_probe.py
git commit -m "feat: ToyBox — 게임 상태를 읽어 상태 줄에 보이고, 게임 밖에서는 단추를 끈다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/toybox-game-state
```

PR 을 `develop` 으로 올리고(본문에 `uv run pytest` 결과와 H1 · H2 · H10 에서 본 것) 머지한 뒤 `git switch develop && git pull --ff-only origin develop`. 게임이 꺼져 있을 때만 브랜치를 바꾼다.

---

### Task 3: 직접 실행, 자동 전환, 오류 가드

**브랜치:** `feat/toybox-direct` (`develop` 에서)

**Files:**
- Modify: `native/srtoybox/game.h`, `native/srtoybox/game.cpp`, `native/srtoybox/runner.h`, `native/srtoybox/runner.cpp`, `native/srtoybox/runner_win.h`, `native/srtoybox/runner_win.cpp`, `native/srtoybox/ui.cpp`
- Modify: `tests/toybox_overlay_probe.py`, `tests/test_toybox.py`

**Interfaces:**
- Consumes: Task 2 의 `game_state()`, `GameState`, `game_set_for_test`, `Runner::starting()` · `clear()`, `runner_notice()`, 프로브의 `fake_game(hook, handler)` · `FakeGame` · `BUTTON`, 테스트의 `_probe(…, env=)` · `typed_keys`.
- Produces:
  - C++ `bool game_can_call();` `bool game_call(const char *line, unsigned long *code);`
  - C++ `std::string Runner::take();` `bool runner_faulted();` `bool runner_direct();`
  - 환경 변수 `SRTOYBOX_DIRECT=0` — 주소를 찾아도 명령은 글쇠 방식으로 넣는다.
  - 로그 줄 `직접 실행: <명령>`, `직접 실행 중 예외 0x… (<명령>)`.
  - 프로브 모드 `direct` · `direct_fault` · `direct_off` · `direct_menu` (출력 `lines=<명령 처리 함수가 받은 줄들, 빈칸은 _ 로, | 로 나눔> text=<게임이 받은 글>`).

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-direct
```

- [ ] **Step 2: 프로브에 직접 실행 모드를 더한다** — `tests/toybox_overlay_probe.py`

(가) 문서 주석의 `gate_typing …` 줄 아래에 더한다.

```
직접 실행 (출력 "lines=<명령 처리 함수가 받은 줄들. 빈칸은 _, 줄 사이는 |> text=<게임이 받은 글>"):
    direct           게임 안에서 단추를 세 번 — 둘째 뒤에 치트 허용이 꺼진다(메뉴에 나갔다 온 것처럼)
    direct_fault     명령 처리 함수가 잘못된 주소에 쓴다 — ToyBox 가 잡고, 그 뒤로는 아무것도 실행하지 않는다
    direct_off       SRTOYBOX_DIRECT=0 — 명령 처리 함수를 부르지 않고 글쇠를 넣는다
    direct_menu      명령 처리 함수를 부를 수 있지만 게임 밖이다 — 부르지 않는다
```

(나) `from toybox_fake_game import FakeGame` 줄을 다음으로 바꾼다.

```python
from toybox_fake_game import OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)
```

(다) `WNDPROC = …` 줄 아래에 더한다.

```python
HANDLER = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)    # 게임의 명령 처리 함수: void f(void *context, const char *line)
```

(라) `run_gate` 함수 아래에 더한다.

```python
def crash_stub() -> int:
    """부르면 0 번지에 쓰는 함수(mov dword ptr [0],1 / ret) — 게임의 함수 안에서 나는 접근 위반을 흉내 낸다."""
    code = kernel32.VirtualAlloc(None, 16, 0x3000, 0x40)
    ctypes.memmove(code, bytes([0xC7, 0x04, 0x25, 0, 0, 0, 0, 1, 0, 0, 0, 0xC3]), 12)
    return code


def run_direct(hook: str, mode: str) -> int:
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":                      # 게임이 하듯 치트 허용 비트를 세운다
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)

    handler = HANDLER(body)
    fake = box["fake"] = fake_game(hook, crash_stub() if mode == "direct_fault" else ctypes.cast(handler, ctypes.c_void_p).value)
    if mode != "direct_menu":
        fake.play(176)
    game.hotkey()
    game.got.clear()
    if mode == "direct_off":
        game.click(BUTTON)
        game.pump(lambda: game.has("up", 0x1B), 20)
        game.wait(0.4)
    elif mode == "direct_menu":
        game.click(BUTTON)
        game.wait(1.0)
    else:
        for press in range(3):
            if press == 2:
                fake.poke(OPTIONS, "<I", 0)                   # 메뉴에 나갔다 온 것처럼 치트 허용이 꺼졌다
            game.click(BUTTON)
            game.wait(0.4)
    print("lines=" + "|".join(line.replace(" ", "_") for line in lines) + " text=" + game.text())
    return 0
```

(마) `main()` 의 `if mode.startswith("gate_"):` 두 줄 아래에 더한다.

```python
    if mode.startswith("direct"):
        return run_direct(hook, mode)
```

- [ ] **Step 3: 실패하는 테스트를 쓴다** — `tests/test_toybox.py`

`test_the_typing_route_still_works_in_a_game_toybox_can_read` 아래에 더한다.

```python
def test_direct_run_calls_the_games_handler(dll, cfg, tmp_path):
    """게임 안에서는 글쇠를 넣지 않고 게임의 명령 처리 함수에 바로 넘긴다.

    치트 허용이 꺼져 있으면 먼저 cheat allowcheats 를 부르고, 켜져 있으면 다시 부르지 않는다
    (메뉴에 나갔다 오면 게임이 꺼 두므로 그때는 다시 부른다).
    """
    got = _fields(_probe(cfg, tmp_path, "direct"))
    assert got["lines"].replace("_", " ").split("|") == ["cheat allowcheats", "cheat georgew", "cheat georgew",
                                                        "cheat allowcheats", "cheat georgew"]
    assert got["text"] == ""                                    # 글쇠는 가지 않는다 — 게임의 설정 창이 뜨지 않는다
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("직접 실행: cheat georgew") == 3


def test_a_fault_in_the_games_handler_is_caught_and_nothing_runs_after(dll, cfg, tmp_path):
    """명령 처리 함수 안에서 예외가 나도 프로세스가 죽지 않는다. 게임의 상태가 어긋났을 수 있으므로 그 뒤로는
    직접으로도 글쇠로도 실행하지 않는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_fault"))
    assert got["lines"] == "" and got["text"] == ""
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("직접 실행 중 예외 0xC0000005") == 1         # 한 번 잡은 뒤로는 다시 부르지 않는다


def test_the_games_handler_is_not_called_outside_a_game(dll, cfg, tmp_path):
    """명령 처리 함수는 게임이 진행 중인지 검사하지 않고 플레이어 포인터를 따라간다 — 게임 밖에서 부르면 죽는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_menu"))
    assert got["lines"] == "" and got["text"] == ""


def test_srtoybox_direct_0_keeps_the_typing_route(dll, cfg, tmp_path):
    """탈출구: SRTOYBOX_DIRECT=0 이면 명령 처리 함수를 부를 수 있어도 글쇠를 넣는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_off", env={"SRTOYBOX_DIRECT": "0"}))
    assert got["lines"] == "" and got["text"] == typed_keys("cheat georgew")
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox.py -q --no-header -k "direct or handler" 2>&1 | grep -E "^(FAILED|E  |[0-9]+ (failed|passed))" | cut -c1-220`
Expected: `2 failed, 2 passed`.
- `test_direct_run…`: `lines` 가 비어 있고 `text` 에 글쇠가 들어 있다(아직 직접 부르지 않는다).
- `test_a_fault…`: 같은 까닭(가짜 함수가 불리지 않아 예외 줄이 없고, 글쇠가 간다).
- `test_srtoybox_direct_0…` 은 PASS(지금은 늘 글쇠 방식이다). `test_the_games_handler_is_not_called…` 도 PASS — Task 2 의 검사가 이미 막는다.
  직접 실행을 넣은 뒤에도 그대로여야 하는 것을 지키는 테스트다.

- [ ] **Step 5: 명령 처리 함수를 부르는 길을 더한다** — `native/srtoybox/game.h`, `native/srtoybox/game.cpp`

`game.h` 의 `std::vector<int> game_regions();` 아래에 더한다.

```cpp
bool game_can_call();              // 명령 처리 함수의 주소를 안다
// 명령 처리 함수에 한 줄을 넘긴다 — 게임이 설정 창의 입력줄에서 하는 것과 같은 호출이다.
// 창 스레드에서, 게임이 진행 중일 때만 부른다(함수는 그것을 검사하지 않고 플레이어 포인터를 그대로 따라간다).
// 함수 안에서 예외가 나면 잡고 false 를 돌려준다(code 에 예외 코드). 그 뒤로 게임의 상태는 믿을 수 없다.
bool game_call(const char *line, unsigned long *code);
```

`game.cpp`: `bool g_located, g_told;` 줄 아래에 더한다.

```cpp
void *g_handler;    // 명령 처리 함수
void *g_context;    // 그 첫 인자(게임이 넘기는 것과 같은 전역 객체)

typedef void (*Handler)(void *context, const char *line);

// 구조적 예외(잘못된 주소 접근 등)를 잡는다. __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 따로 뗐다.
bool guarded_call(Handler handler, void *context, const char *line, unsigned long *code)
{
    __try {
        handler(context, line);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        *code = GetExceptionCode();
        return false;
    }
}
```

`game_init()` 의 잠금 블록 안, `g_told = false;` 아래에 두 줄을 더한다.

```cpp
        g_handler = why == nullptr ? const_cast<uint8_t *>(base) + at.handler : nullptr;
        g_context = why == nullptr ? const_cast<uint8_t *>(base) + at.context : nullptr;
```

`game_set_for_test` 를 다음으로 바꾼다.

```cpp
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_base = base;
    g_at = at != nullptr ? *at : GameAddresses();
    g_located = base != nullptr && at != nullptr;
    g_told = false;
    g_handler = g_located ? handler : nullptr;
    g_context = g_located ? const_cast<uint8_t *>(base) + g_at.context : nullptr;
}
```

파일 끝에 더한다.

```cpp
bool game_can_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && g_handler != nullptr;
}

bool game_call(const char *line, unsigned long *code)
{
    Handler handler = nullptr;
    void *context = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        handler = reinterpret_cast<Handler>(g_handler);
        context = g_context;
    }
    *code = 0;
    return handler != nullptr && guarded_call(handler, context, line, code);
}
```

- [ ] **Step 6: 실행기에 직접 실행을 더한다**

`native/srtoybox/runner.h` 의 `void clear();` 줄 아래에 더한다.

```cpp
    std::string take();                         // 대기열의 맨 앞 명령을 꺼낸다(직접 실행). 마지막으로 넣은 것으로 적는다
```

`native/srtoybox/runner.cpp` 끝에 더한다.

```cpp
std::string Runner::take()
{
    last_ = queue_.front();
    queue_.pop_front();
    return last_;
}
```

`native/srtoybox/runner_win.h` 끝에 더한다.

```cpp
bool runner_faulted();                             // 직접 실행 중 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 실행하지 않는다
bool runner_direct();                              // 명령을 게임의 함수에 바로 넘기는가(아니면 글쇠 방식)
```

`native/srtoybox/runner_win.cpp`: 머리말에 `#include "log.h"` 를 넣는다(`game.h` 다음). `std::string g_notice;` 줄 아래에 더한다.

```cpp
bool g_faulted;         // 직접 실행 중 예외가 났다

// 탈출구: SRTOYBOX_DIRECT=0 이면 주소를 찾아도 명령은 글쇠 방식으로 넣는다.
bool direct_wanted()
{
    static const bool wanted = [] {
        char value[8];
        return !(GetEnvironmentVariableA("SRTOYBOX_DIRECT", value, sizeof(value)) == 1 && value[0] == '0');
    }();
    return wanted;
}
```

`GameSink` 구조체 아래(이름 없는 namespace 안)에 더한다.

```cpp
// 게임의 명령 처리 함수에 바로 넘긴다. 치트 허용이 꺼져 있으면 먼저 켠다 — 게임의 함수로(비트를 직접 세우지 않는다).
// g_lock 을 쥔 채로 부른다.
void run_direct(const std::string &command, bool cheats_on)
{
    unsigned long code = 0;
    const char *failed = nullptr;
    if (!cheats_on && !game_call("cheat allowcheats", &code))
        failed = "cheat allowcheats";
    else if (!game_call(command.c_str(), &code))
        failed = command.c_str();
    if (failed == nullptr) {
        log_line("직접 실행: %s", command.c_str());
        return;
    }
    // 게임의 상태가 어긋났을 수 있다. 치트를 더 넣지 않는다 — 글쇠 방식으로도
    g_faulted = true;
    g_runner.clear();
    g_notice = "직접 실행 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.";
    log_line("직접 실행 중 예외 0x%08lX (%s)", code, failed);
}
```

`runner_enqueue` 와 `runner_tick` 을 다음으로 바꾼다.

```cpp
bool runner_enqueue(const std::string &command)
{
    std::lock_guard<std::mutex> lock(g_lock);
    return !g_faulted && g_runner.enqueue(command);
}

void runner_tick(HWND hwnd)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_faulted)
        return;
    if (g_runner.starting()) {
        const GameState game = game_state();
        if (game.known && (!game.in_game || game.multiplayer)) {
            g_runner.clear();   // 누른 뒤 게임에서 나갔다 — 메뉴에 글쇠를 넣지 않고, 게임 밖에서 함수를 부르지 않는다
            g_notice = "게임이 진행 중이 아니어서 실행하지 않았습니다.";
            return;
        }
        g_notice.clear();
        if (game.known && direct_wanted() && game_can_call()) {
            run_direct(g_runner.take(), game.cheats_on);
            return;
        }
    }
    GameSink sink(hwnd);
    g_runner.tick(sink);
}
```

파일 끝에 더한다.

```cpp
bool runner_faulted()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_faulted;
}

bool runner_direct()
{
    return direct_wanted() && game_can_call();
}
```

- [ ] **Step 7: 창이 오류와 실행 방식을 알게 한다** — `native/srtoybox/ui.cpp`

`const bool blocked = …` 줄을 다음으로 바꾼다.

```cpp
        const bool faulted = runner_faulted();
        const bool blocked = faulted || (game.known && (!game.in_game || game.multiplayer));
```

창 아래쪽의 다음 다섯 줄을

```cpp
        const std::string trouble = runner_notice();
        if (!trouble.empty())
            ImGui::TextUnformatted(trouble.c_str());
        ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        if (!game.known)   // 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로 이 주의가 필요 없다
```

다음으로 바꾼다.

```cpp
        const std::string trouble = runner_notice();
        if (faulted)
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f), "%s", trouble.c_str());
        else if (!trouble.empty())
            ImGui::TextUnformatted(trouble.c_str());
        if (!(game.known && runner_direct()))   // 직접 실행에서는 게임의 설정 창이 뜨지 않는다
            ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        if (!game.known)   // 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로 이 주의가 필요 없다
```

- [ ] **Step 8: 빌드하고 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest -q --no-header 2>&1 | tail -2`
Expected: `빌드 완료`, `163 passed` (159 + 4).

- [ ] **Step 9: 게임에서 본다 (H3) — 이 설계의 전제**

실제 게임의 명령 처리 함수를 처음 부르는 자리다. 미리보기에 `갱신: srtoybox.dll` 한 줄만 있는 것을 보고 넣는다.

```bash
uv run srkit deploy toybox
uv run srkit deploy toybox --apply
```

게임을 화면 밖에서 띄워(백그라운드 작업) 게임에 들어간 뒤, 재무 패널을 열어 국고를 찍고 단추를 누른다. 괄호 안의 시간만큼 기다린다.

```bash
export SRTOYBOX_HOME="E:/SR2030ToyBox/build/verify/toybox/home"
uv run python scripts/gamedrive.py start            # (38초)
uv run python scripts/gamedrive.py click 512 340    # 샌드박스 (3초)
uv run python scripts/gamedrive.py click 797 240    # 2030 - 세계 (2초)
uv run python scripts/gamedrive.py click 601 725    # 시작 (32초)
uv run python scripts/gamedrive.py click 205 738    # 게임의 재무($) 단추 (1.5초)
uv run python scripts/gamedrive.py move 700 300     # 툴팁을 치운다 (1초)
uv run python scripts/gamedrive.py shot build/verify/toybox/H3-before.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T # (1초)
uv run python scripts/gamedrive.py click 90 208     # 국고 +$10 B (0.3초)
uv run python scripts/gamedrive.py shot build/verify/toybox/H3-mid.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T # (1초)
uv run python scripts/gamedrive.py move 700 300     # (1초)
uv run python scripts/gamedrive.py shot build/verify/toybox/H3-after.png
```

Expected:
- `H3-before.png` 의 국고 $14.43 B → `H3-after.png` 에서 $24.43 B.
- `H3-mid.png`: ToyBox 창에 `마지막으로 넣은 것: cheat georgew`. **게임의 설정 창(빨간 제목)이 보이지 않는다**(1단계의 `G2-mid` 에는 보였다).
- `toybox.log` 에 `직접 실행: cheat georgew`.

**국고가 그대로이거나, 게임이 죽거나, 로그에 `직접 실행 중 예외` 가 있으면 여기서 멈춘다.** 게임을 끄고(`gamedrive.py stop`), 본 것(화면 · 로그 · Windows 이벤트 로그의 충돌 기록)과 함께 사용자에게 알린다 — 직접 실행은 이 설계의 전제이고, 안 되면 설계를 다시 정해야 한다.

- [ ] **Step 10: 게임에서 본다 (H11) — 글쇠 방식의 회귀**

Step 9 의 게임을 끈다(게임 메뉴 → "게임 종료" → "게임 종료" → 메인 메뉴의 종료 단추. Task 2 Step 18 의 끝 다섯 줄과 같다). `SRTOYBOX_DIRECT=0` 을 준 채 다시 띄워 같은 일을 한다.

```bash
export SRTOYBOX_HOME="E:/SR2030ToyBox/build/verify/toybox/home"
SRTOYBOX_DIRECT=0 uv run python scripts/gamedrive.py start    # (38초) — 이어서 Step 9 의 "샌드박스"부터 "국고 +$10 B"까지 같은 줄들
uv run python scripts/gamedrive.py shot build/verify/toybox/H11-mid.png      # 단추를 누르고 1.5초 뒤
# (6초 기다린 뒤 창을 닫고 마우스를 치우고)
uv run python scripts/gamedrive.py shot build/verify/toybox/H11-after.png
```

Expected: `H11-mid.png` 에 게임의 설정 창이 떠 있다(글쇠 방식). `H11-after.png` 의 국고가 +$10 B. 로그에 `직접 실행` 줄이 새로 생기지 않는다. 끝나면 게임을 같은 길로 끈다.

- [ ] **Step 11: 커밋 · PR · 머지**

```bash
git add native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/runner.h native/srtoybox/runner.cpp native/srtoybox/runner_win.h native/srtoybox/runner_win.cpp native/srtoybox/ui.cpp tests/toybox_overlay_probe.py tests/test_toybox.py
git commit -m "feat: ToyBox — 치트를 게임의 명령 처리 함수에 바로 넘긴다 (자동 전환, 오류 가드)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/toybox-direct
```

PR 을 `develop` 으로 올리고(본문에 `uv run pytest` 결과, H3 · H11 에서 본 것) 머지한 뒤 `git switch develop && git pull --ff-only origin develop`.

---

### Task 4: 나라 고르기와 지역 치트

**브랜치:** `feat/toybox-regions` (`develop` 에서)

**Files:**
- Modify: `native/srtoybox/features.h`, `native/srtoybox/features.cpp`, `native/srtoybox/command.h`, `native/srtoybox/command.cpp`, `native/srtoybox/regions.h`, `native/srtoybox/regions.cpp`, `native/srtoybox/input.h`, `native/srtoybox/input.cpp`, `native/srtoybox/ui.cpp`, `native/srtoybox/exports.cpp`
- Modify: `tests/test_toybox.py`, `tests/test_toybox_game.py`

**Interfaces:**
- Consumes: Task 2 의 `GameState`, `game_state()`, `game_regions()`, `find_region`, `region_label`, `runner_notice()`; Task 3 의 `runner_faulted()`, `runner_direct()`.
- Produces:
  - C++ `enum class Target { None, Player, Picked };` 와 `Feature::target`
  - C++ `std::string build_command(const Feature &f, long long value, int region);` — 대상이 필요한데 `region <= 0` 이면 빈 글
  - C++ `struct RegionView { int picked; std::vector<int> rows; };` `RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter);`
  - C++ `unsigned dbcs_combine(unsigned char lead, unsigned char trail, unsigned codepage);`
  - 내보내기: `srtoybox_feature_info` 의 줄 끝에 대상(`none` · `player` · `picked`)이 붙는다. `int srtoybox_command(const char *id, long long value, int region, char *out, int size)`. `int srtoybox_region_view(const int *numbers, int count, int player, int picked, const char *filter, char *out, int size)` — 첫 줄 `picked=<번호>`, 이어서 한 줄에 `<번호>\t<이름>`. `unsigned srtoybox_dbcs(unsigned char lead, unsigned char trail, unsigned codepage)`.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-regions
```

- [ ] **Step 2: 기능 표의 테스트를 고친다(실패하게)** — `tests/test_toybox.py`

(가) `EXCLUDED` 와 `TABS` 를 다음으로 바꾼다(지역 치트 아홉을 제외 목록에서 빼고, 탭 하나를 더한다).

```python
# 넣지 않는 것: 모든 지역 · AI 에 닿거나, 불리해지거나, 반응이 없었거나, 넣지 않기로 한 것
EXCLUDED = {
    "onedaybuild", "allunit", "gates", "devcheat", "endday", "increaseday", "eventnow", "peace", "worldwar", "darren",
    "democracy", "saddam", "breakground", "depopulate", "trumpme", "sanction", "wmsanction", "shelovesmenot", "saddamme",
    "hate", "liberate", "revolt", "resettutorial", "allowcheats",
}
TABS = ["돈", "물자", "연구", "인구·여론", "외교·영토", "부대", "화면·진행"]
```

(나) `dll` 픽스처의 `srtoybox_command` 줄을 다음으로 바꾼다.

```python
    lib.srtoybox_command.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
```

(다) `features` · `test_feature_table` · `test_only_player_cheats_that_were_seen_working` · `test_command_text` 를 다음으로 바꾼다.

```python
def features(dll) -> list[dict]:
    out = []
    for i in range(dll.srtoybox_feature_count()):
        ident, tab, label, command, has_value, default, low, high, confirm, help_, target = \
            text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_,
                    "target": target})
    return out
```

```python
def test_feature_table(dll):
    fs = features(dll)
    assert len(fs) == 25
    assert len({f["id"] for f in fs}) == 25 and len({f["command"] for f in fs}) == 25
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    for f in fs:
        assert f["command"] == "cheat " + f["id"] and f["label"] and f["help"]
        assert not (f["has_value"] and f["target"] != "none")           # 한 기능의 인자는 하나다
        if f["has_value"]:
            assert f["min"] <= f["default"] <= f["max"]
    assert {f["id"] for f in fs if f["has_value"]} == {"treasury", "products", "technology", "spawnunit"}
    assert {f["id"] for f in fs if f["target"] == "player"} == {"approval"}
    assert {f["id"] for f in fs if f["target"] == "picked"} == {"love", "neutral", "annex", "colonize", "novichok", "fight",
                                                                "becomeregion"}
    # 되돌릴 수 없는 것은 한 번 더 누르게 한다
    assert [f["id"] for f in fs if f["confirm"]] == ["annex", "colonize", "novichok", "fight", "becomeregion", "instantwin"]
    assert {f["id"] for f in fs if f["tab"] == "외교·영토"} == {"love", "neutral", "treaty", "annex", "colonize", "novichok",
                                                              "fight", "becomeregion"}
    assert dll.srtoybox_feature_info(25, ctypes.create_string_buffer(8), 8) == -1


def test_only_cheats_that_were_seen_working_and_reach_what_the_user_chose(dll, cfg):
    """요구: 설정은 플레이어가 플레이 중인 국가에만 적용된다. 게임에서 효과를 확인한 치트만 내놓고,
    플레이어 밖에 닿는 것은 사용자가 창이나 지도에서 고른 나라 하나에만 닿는 것이어야 한다(2026-10-07, 사용자가 범위를 정했다)."""
    rows = documented(cfg)
    for f in features(dll):
        target, verdict = rows[f["id"]]
        assert verdict == "[확인: 효과]", f["id"]
        assert f["id"] not in EXCLUDED
        if f["tab"] == "외교·영토" or f["target"] == "player":
            assert target in ("지정한 지역", "고른 지역", "플레이어"), (f["id"], target)
        else:
            assert target.startswith("플레이어") or target == "고른 부대", (f["id"], target)
```

```python
def test_command_text(dll):
    assert text(dll.srtoybox_command, b"treasury", 1234, 0) == "cheat treasury 1234"
    assert text(dll.srtoybox_command, b"treasury", 0, 0) == "cheat treasury 1"                 # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"treasury", -5, 0) == "cheat treasury 1"
    assert text(dll.srtoybox_command, b"treasury", 10**12, 0) == "cheat treasury 1000000"
    assert text(dll.srtoybox_command, b"georgew", 999, 1106) == "cheat georgew"                # 값도 대상도 없는 기능은 둘 다 무시한다
    assert text(dll.srtoybox_command, b"e=mc2", 0, 0) == "cheat e=mc2"
    assert text(dll.srtoybox_command, b"approval", 0, 1499) == "cheat approval 1499"           # 대상이 있는 기능은 지역 번호가 붙는다
    assert text(dll.srtoybox_command, b"love", 0, 1106) == "cheat love 1106"
    assert text(dll.srtoybox_command, b"treaty", 0, 1106) == "cheat treaty"                    # 게임이 지도에서 고른 나라를 쓴다
    assert text(dll.srtoybox_command, b"love", 0, 0) is None                                   # 나라를 고르지 않았으면 만들지 않는다
    assert text(dll.srtoybox_command, b"approval", 0, -1) is None
    assert text(dll.srtoybox_command, b"depopulate", 0, 0) is None                             # 표에 없는 것은 만들지 않는다
    assert text(dll.srtoybox_command, b"treasury", 1, 0, size=4) is None                       # 버퍼가 작으면 넘치지 않고 -1
```

- [ ] **Step 3: 나라 목록과 2바이트 글자의 테스트를 쓴다(실패하게)** — `tests/test_toybox_game.py`

`lib` 픽스처의 `return lib` 위에 두 줄을 더한다.

```python
    lib.srtoybox_region_view.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                         ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_dbcs.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint]
```

파일 끝에 더한다.

```python
def view(lib, numbers: list[int], player: int, picked: int, search: str = "") -> tuple[int, list[tuple[int, str]]]:
    """창의 나라 목록: (유지된 선택, [(번호, 이름) …])."""
    out = ctypes.create_string_buffer(1 << 16)
    array = (ctypes.c_int * len(numbers))(*numbers)
    assert lib.srtoybox_region_view(array, len(numbers), player, picked, search.encode("utf-8"), out, len(out)) >= 0
    head, *rows = out.value.decode("utf-8").splitlines()
    return int(head.removeprefix("picked=")), [(int(n), name) for n, name in (row.split("\t") for row in rows)]


GAME = [1106, 1201, 1499, 12345]      # 폴란드, 덴마크, 독일, 이름표에 없는 지역


def test_region_view_lists_this_games_regions(lib):
    """이번 게임에 있는 나라만, 플레이어 자신은 빼고, 한글 이름순으로. 이름표에 없는 번호는 #번호 로 보이고 고를 수 있다."""
    picked, rows = view(lib, GAME, player=1499, picked=12345)
    assert rows == [(12345, "#12345"), (1201, "덴마크"), (1106, "폴란드")]
    assert picked == 12345


def test_region_view_filters_by_name_and_number(lib):
    assert [n for n, _ in view(lib, GAME, 1499, 0, "폴란")[1]] == [1106]
    assert [n for n, _ in view(lib, GAME, 1499, 0, "DEN")[1]] == [1201]            # 영문 이름, 대소문자를 가리지 않는다
    assert [n for n, _ in view(lib, GAME, 1499, 0, "12")[1]] == [12345, 1201]       # 번호의 일부
    assert view(lib, GAME, 1499, 0, "없는이름")[1] == []
    assert view(lib, GAME, 1499, 1106, "덴마")[0] == 1106                           # 검색으로 가려져도 선택은 그대로다


def test_region_view_drops_a_pick_that_is_gone(lib):
    """다른 판을 불러와 고른 나라가 없어졌거나, 그 나라로 플레이하게 됐으면 선택을 지운다."""
    assert view(lib, [1201, 1499], player=1499, picked=1106)[0] == 0
    assert view(lib, GAME, player=1106, picked=1106)[0] == 0
    assert view(lib, [], player=0, picked=1106) == (0, [])


def test_two_byte_characters_are_put_back_together(lib):
    """게임 창은 ANSI 창이라 한글 한 글자가 WM_CHAR 두 번(CP949 의 앞 · 뒤 바이트)으로 온다. 합쳐서 한 글자로 넘긴다."""
    lead, trail = "독".encode("cp949")
    assert lib.srtoybox_dbcs(lead, trail, 949) == ord("독")
    assert lib.srtoybox_dbcs(lead, 0x20, 949) == 0          # 앞 바이트 뒤에 엉뚱한 것이 왔다
    assert lib.srtoybox_dbcs(0x41, 0x42, 949) == 0          # 2바이트 글자가 아니다
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox.py tests/test_toybox_game.py -q --no-header 2>&1 | tail -4`
Expected: `test_toybox.py` 의 `test_feature_table` · `test_only_cheats…` · `test_command_text` 가 FAIL(줄에 대상이 없어 `ValueError: not enough values to unpack`, 기능이 16개), `test_toybox_game.py` 는 픽스처에서 `AttributeError: function 'srtoybox_region_view' not found`.

- [ ] **Step 5: 기능 표에 "대상"과 지역 치트를 더한다**

`native/srtoybox/features.h` 의 `struct Feature {` 위에 더하고,

```cpp
// 명령 뒤에 붙는 지역 번호. 한 기능의 인자는 하나다 — 값(has_value)이 있는 기능에는 대상이 없다.
enum class Target {
    None,
    Player,   // 플레이어의 지역(ToyBox 가 게임에서 읽는다)
    Picked,   // 창의 목록에서 고른 나라
};
```

구조체의 `bool confirm;` 줄 아래에 한 줄을 더한다(먼저 있던 16줄은 고치지 않아도 된다 — 적지 않은 마지막 필드는 `Target::None` 이 된다).

```cpp
    Target target;        // 명령 뒤에 붙일 지역
```

파일 머리의 주석 둘째 줄을 다음으로 바꾼다.

```cpp
// 넣는 기준: docs/07 에서 검증이 [확인: 효과]인 치트 가운데 불리해지지 않는 것 — 대상이 "플레이어" · "고른 부대"이거나,
// 사용자가 창이나 지도에서 고른 나라 하나에만 닿는 것("외교·영토" 탭. 2026-10-07 에 사용자가 범위를 정했다).
```

`native/srtoybox/features.cpp` 의 `shelovesme` 줄 아래(`spawnunit` 줄 위)에 아홉 줄을 더한다.

```cpp
    {"approval", "인구·여론", "내 나라 지지율 100%", "국내 지지율이 100% 가 된다", "cheat approval", false, 0, 0, 0, false, Target::Player},
    {"love", "외교·영토", "관계 최고", "고른 나라와의 외교 · 민간 관계가 가득 차고 전쟁 명분이 0 이 된다", "cheat love", false, 0, 0, 0, false, Target::Picked},
    {"neutral", "외교·영토", "관계 중립", "고른 나라와의 관계가 절반이 되고 전쟁 명분이 0 이 된다", "cheat neutral", false, 0, 0, 0, false, Target::Picked},
    {"treaty", "외교·영토", "동맹 맺기", "지도에서 나라를 고른 뒤 누른다. 그 나라와 동맹이 된다(조약 13종). 위 목록과는 상관없다", "cheat treaty", false, 0, 0, 0, false, Target::None},
    {"annex", "외교·영토", "병합", "고른 나라의 땅이 내 영토가 된다", "cheat annex", false, 0, 0, 0, true, Target::Picked},
    {"colonize", "외교·영토", "식민지화", "고른 나라가 내 식민지이자 동맹국이 된다", "cheat colonize", false, 0, 0, 0, true, Target::Picked},
    {"novichok", "외교·영토", "지도자 제거", "고른 나라의 지도자가 죽는다", "cheat novichok", false, 0, 0, 0, true, Target::Picked},
    {"fight", "외교·영토", "전쟁 붙이기", "지도에서 한 나라를 고른 뒤 누른다. 그 나라와 목록에서 고른 나라가 싸운다", "cheat fight", false, 0, 0, 0, true, Target::Picked},
    {"becomeregion", "외교·영토", "이 나라로 플레이", "플레이하는 나라가 고른 나라로 바뀐다", "cheat becomeregion", false, 0, 0, 0, true, Target::Picked},
```

탭 이름의 가운뎃점은 먼저 있던 `"인구·여론"` 의 것(U+00B7)을 그대로 복사해 쓴다.

- [ ] **Step 6: 대상이 붙는 명령** — `native/srtoybox/command.h`, `native/srtoybox/command.cpp`

`command.h` 의 `build_command` 선언과 그 위의 주석을 다음으로 바꾼다.

```cpp
// 값은 기능의 범위로 잘라 맞춘다. 대상이 있는 기능은 region(지역 번호)을 뒤에 붙인다 — region 이 0 이하이면
// (플레이어를 모르거나 나라를 고르지 않았다) 빈 글을 준다. 값도 대상도 없는 기능은 둘 다 무시한다.
std::string build_command(const Feature &f, long long value, int region);
```

`command.cpp` 의 `build_command` 를 다음으로 바꾼다.

```cpp
std::string build_command(const Feature &f, long long value, int region)
{
    std::string out = f.command;
    if (f.has_value) {
        const long long v = value < f.min ? f.min : value > f.max ? f.max : value;
        out += ' ';
        out += std::to_string(v);
    } else if (f.target != Target::None) {
        if (region <= 0)
            return std::string();
        out += ' ';
        out += std::to_string(region);
    }
    return out;
}
```

- [ ] **Step 7: 나라 목록의 보기** — `native/srtoybox/regions.h`, `native/srtoybox/regions.cpp`

`regions.h`: 머리말에 `#include <vector>` 를 더하고 파일 끝에 더한다.

```cpp
// 창의 나라 목록.
struct RegionView {
    int picked;               // 고른 나라. 이번 게임에 없거나 플레이어 자신이면 0
    std::vector<int> rows;    // 목록에 보일 지역 번호, 이름순(이름표에 없는 것은 "#번호"로 친다)
};

// numbers: 이번 게임에 있는 지역. 플레이어 자신은 뺀다. filter(이름이나 번호의 일부. 영문은 대소문자를 가리지 않는다)로 거른다 —
// 거르는 것은 목록뿐이고, 고른 나라는 목록에서 가려져도 그대로다.
RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter);
```

`regions.cpp`: 머리말에 `#include <algorithm>` 을 더하고(`"regions.h"` 아래 빈 줄 다음), 이름 없는 namespace 안의 `NAME_COUNT` 아래에 더한다.

```cpp
char lower(char c)
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c + ('a' - 'A')) : c;
}

// part 가 text 안에 있는가. ASCII 는 대소문자를 가리지 않는다.
bool contains(const std::string &text, const std::string &part)
{
    if (part.size() > text.size())
        return false;
    for (size_t i = 0; i + part.size() <= text.size(); i++) {
        size_t j = 0;
        while (j < part.size() && lower(text[i + j]) == lower(part[j]))
            j++;
        if (j == part.size())
            return true;
    }
    return false;
}

bool matches(int number, const std::string &filter)
{
    const RegionName *name = find_region(number);
    return contains(std::to_string(number), filter)
        || (name != nullptr && (contains(name->ko, filter) || contains(name->en, filter)));
}
```

파일 끝에 더한다.

```cpp
RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter)
{
    RegionView view;
    view.picked = 0;
    const std::string wanted = filter == nullptr ? "" : filter;
    for (int number : numbers) {
        if (number == player)
            continue;
        if (number == picked)
            view.picked = picked;
        if (matches(number, wanted))
            view.rows.push_back(number);
    }
    std::sort(view.rows.begin(), view.rows.end(), [](int a, int b) {
        const std::string la = region_label(a), lb = region_label(b);
        return la != lb ? la < lb : a < b;   // UTF-8 의 바이트순 = 한글의 가나다순
    });
    return view;
}
```

- [ ] **Step 8: 2바이트 글자 합치기** — `native/srtoybox/input.h`, `native/srtoybox/input.cpp`

`input.h` 끝에 더한다.

```cpp
// 코드 페이지의 앞 · 뒤 바이트를 한 글자(UTF-16)로. 2바이트 글자가 아니면 0.
unsigned dbcs_combine(unsigned char lead, unsigned char trail, unsigned codepage);
```

`input.cpp` 의 `from_keyboard` 줄 아래(이름 없는 namespace 안)에 더한다.

```cpp
// ANSI 창에서는 한글 한 글자가 WM_CHAR 두 번(코드 페이지의 앞 · 뒤 바이트)으로 온다. ImGui 의 Win32 백엔드는 한 바이트씩
// 바꿔서 깨뜨리므로, 설정 창이 글을 받는 동안에는 여기서 둘을 합쳐 한 글자로 넘긴다. 삼켰으면 true.
bool take_dbcs(ImGuiIO &io, WPARAM w)
{
    static unsigned char lead;
    if (!io.WantTextInput) {
        lead = 0;
        return false;
    }
    const unsigned char byte = static_cast<unsigned char>(w);
    if (lead != 0) {
        const unsigned unit = dbcs_combine(lead, byte, CP_ACP);
        lead = 0;
        if (unit != 0)
            io.AddInputCharacterUTF16(static_cast<ImWchar16>(unit));
        return true;
    }
    if (IsDBCSLeadByteEx(CP_ACP, byte)) {
        lead = byte;
        return true;
    }
    return false;
}
```

`wrapped()` 안의 다음 다섯 줄을

```cpp
            ImGui_ImplWin32_WndProcHandler(h, m, w, drawn);
            if (is_mouse(m))   // 창 위인지는 사각형으로 직접 가린다 — ImGui 의 판단(WantCaptureMouse)은 한 프레임 늦다
                swallow = (positioned && ui_hit(x, y)) || io.WantCaptureMouse;
            else
                swallow = io.WantCaptureKeyboard;
```

다음으로 바꾼다.

```cpp
            if (!g_unicode && m == WM_CHAR && take_dbcs(io, w)) {
                swallow = true;
            } else {
                ImGui_ImplWin32_WndProcHandler(h, m, w, drawn);
                if (is_mouse(m))   // 창 위인지는 사각형으로 직접 가린다 — ImGui 의 판단(WantCaptureMouse)은 한 프레임 늦다
                    swallow = (positioned && ui_hit(x, y)) || io.WantCaptureMouse;
                else
                    swallow = io.WantCaptureKeyboard;
            }
```

파일 끝(`input_install` 아래)에 더한다.

```cpp
unsigned dbcs_combine(unsigned char lead, unsigned char trail, unsigned codepage)
{
    const char bytes[2] = {static_cast<char>(lead), static_cast<char>(trail)};
    wchar_t unit = 0;
    return MultiByteToWideChar(codepage, MB_ERR_INVALID_CHARS, bytes, 2, &unit, 1) == 1 ? static_cast<unsigned>(unit) : 0;
}
```

- [ ] **Step 9: 내보내기를 고친다** — `native/srtoybox/exports.cpp`

머리말에 `#include "input.h"` 를 넣는다(`game.h` 다음). `srtoybox_feature_info` 의 주석과 `line` 을 다음으로 바꾼다.

```cpp
// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명, 대상(none/player/picked) — 탭 문자로 나눈다
```

```cpp
    static const char *const targets[] = {"none", "player", "picked"};
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help + '\t' + targets[static_cast<int>(f.target)];
```

`srtoybox_command` 를 다음으로 바꾼다.

```cpp
EXPORT int srtoybox_command(const char *id, long long value, int region, char *out, int size)
{
    const Feature *f = id == nullptr ? nullptr : find_feature(id);
    const std::string command = f == nullptr ? std::string() : build_command(*f, value, region);
    return command.empty() ? -1 : put(command, out, size);
}
```

`srtoybox_region_label` 아래에 더한다.

```cpp
// 테스트: 창의 나라 목록. 첫 줄 "picked=<번호>", 이어서 한 줄에 "<번호>\t<이름>".
EXPORT int srtoybox_region_view(const int *numbers, int count, int player, int picked, const char *filter, char *out, int size)
{
    const std::vector<int> all(numbers, numbers + (numbers == nullptr || count < 0 ? 0 : count));
    const RegionView view = region_view(all, player, picked, filter);
    std::string text = "picked=" + std::to_string(view.picked) + '\n';
    for (int number : view.rows)
        text += std::to_string(number) + '\t' + region_label(number) + '\n';
    return put(text, out, size);
}

EXPORT unsigned srtoybox_dbcs(unsigned char lead, unsigned char trail, unsigned codepage)
{
    return dbcs_combine(lead, trail, codepage);
}
```

- [ ] **Step 10: 창에 "외교·영토" 탭을 넣는다** — `native/srtoybox/ui.cpp`

파일 전체를 다음으로 바꾼다(Task 2 · 3 에서 고친 것이 들어 있다. 바뀌는 곳: `g_picked` 등 상태 넷, `row` 의 대상, `picker`, 탭 그리기).

```cpp
#include "ui.h"

#include <cfloat>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "game.h"
#include "imgui.h"
#include "overlay.h"
#include "regions.h"
#include "runner_win.h"
#include "settings.h"

namespace {

typedef std::lock_guard<std::recursive_mutex> Lock;

const char *const DIPLOMACY_TAB = "외교·영토";   // features.cpp 의 탭 이름과 같아야 한다

Settings g_settings;
bool g_visible, g_capturing;
float g_rect[4];              // 창의 왼쪽 · 위 · 오른쪽 · 아래 (지난 프레임)
std::string g_confirm;        // 한 번 더 누르기를 기다리는 기능의 id
std::string g_notice;
int g_picked;                 // "외교·영토" 탭에서 고른 나라의 번호(없으면 0)
char g_filter[64];            // 나라 검색란
std::vector<int> g_regions;   // 이번 게임에 있는 지역
double g_regions_at = -10.0;  // 그것을 읽은 때(ImGui 의 시계, 초)

void row(const Feature &f, const GameState &game)
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
    const int region = f.target == Target::Player ? game.player : f.target == Target::Picked ? g_picked : 0;
    const bool missing = f.target != Target::None && region <= 0;   // 플레이어를 모르거나 나라를 고르지 않았다
    const bool asking = f.confirm && g_confirm == f.id;
    const std::string label = std::string(asking ? "한 번 더 누르면 실행합니다" : f.label) + "###run";
    ImGui::BeginDisabled(missing);
    if (ImGui::Button(label.c_str())) {
        if (f.confirm && !asking) {
            g_confirm = f.id;
        } else {
            g_confirm.clear();
            g_notice = runner_enqueue(build_command(f, value, region)) ? "" : "대기 중인 명령이 많아 받지 못했습니다.";
        }
    }
    ImGui::EndDisabled();
    ImGui::TextDisabled("%s", f.help);
    ImGui::Spacing();
    ImGui::PopID();
}

// 나라 고르기: 이번 게임에 있는 나라를 이름순으로. 검색은 이름(한글 · 영문)이나 번호의 일부.
void picker(const GameState &game)
{
    if (ImGui::GetTime() - g_regions_at > 1.0) {   // 지역 수백 개를 읽는다 — 프레임마다 하지 않는다
        g_regions = game_regions();
        g_regions_at = ImGui::GetTime();
    }
    const RegionView view = region_view(g_regions, game.player, g_picked, g_filter);
    if (view.picked != g_picked) {                 // 다른 판을 불러와 그 나라가 없어졌거나, 그 나라로 플레이하게 됐다
        g_picked = view.picked;
        g_confirm.clear();
    }
    if (g_picked != 0)
        ImGui::Text("고른 나라: %s (%d)", region_label(g_picked).c_str(), g_picked);
    else
        ImGui::TextDisabled("고른 나라: 없음 — 아래 목록에서 고르십시오");
    ImGui::SetNextItemWidth(220.0f);
    ImGui::InputTextWithHint("##search", "검색 (이름 · 번호)", g_filter, sizeof(g_filter));
    if (ImGui::BeginListBox("##regions", ImVec2(-FLT_MIN, 6.5f * ImGui::GetTextLineHeightWithSpacing()))) {
        for (int number : view.rows) {
            const std::string label = region_label(number) + " (" + std::to_string(number) + ")";
            if (ImGui::Selectable(label.c_str(), number == g_picked)) {
                g_picked = number;
                g_confirm.clear();   // 한 번 더 누르기를 기다리던 것은 다른 나라에 대한 것이었다
            }
        }
        ImGui::EndListBox();
    }
    ImGui::Spacing();
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

// 상태 줄: ToyBox 가 게임을 어떻게 보고 있는지 한 줄로.
void status_line(const GameState &game)
{
    if (!game.known)
        ImGui::TextDisabled("게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다");
    else if (game.multiplayer)
        ImGui::TextUnformatted("멀티플레이에서는 동작하지 않습니다");
    else if (!game.in_game)
        ImGui::TextUnformatted("게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다");
    else
        ImGui::Text("플레이 중: %s (%d)", region_label(game.player).c_str(), game.player);
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
        const GameState game = game_state();
        const bool faulted = runner_faulted();
        const bool blocked = faulted || (game.known && (!game.in_game || game.multiplayer));
        status_line(game);
        if (ImGui::BeginTabBar("tabs")) {
            const char *tab = nullptr;
            for (int i = 0; i < FEATURE_COUNT; i++) {
                if (tab != nullptr && strcmp(tab, FEATURES[i].tab) == 0)
                    continue;   // 이 탭은 앞에서 그렸다(같은 탭의 기능은 표에서 이어져 있다)
                tab = FEATURES[i].tab;
                if (ImGui::BeginTabItem(tab)) {
                    const bool diplomacy = strcmp(tab, DIPLOMACY_TAB) == 0;
                    if (diplomacy && !game.known) {
                        ImGui::TextWrapped("게임 상태를 읽을 수 있을 때만 씁니다.");   // 이번 게임의 나라 목록을 모른다
                    } else {
                        ImGui::BeginDisabled(blocked);
                        if (diplomacy)
                            picker(game);
                        for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                            row(FEATURES[j], game);
                        ImGui::EndDisabled();
                    }
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
        const std::string trouble = runner_notice();
        if (faulted)
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f), "%s", trouble.c_str());
        else if (!trouble.empty())
            ImGui::TextUnformatted(trouble.c_str());
        if (!(game.known && runner_direct()))   // 직접 실행에서는 게임의 설정 창이 뜨지 않는다
            ImGui::TextWrapped("단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.");
        if (!game.known)   // 게임을 읽을 수 있으면 게임 밖에서는 단추가 꺼져 있으므로 이 주의가 필요 없다
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

바꾸기 전에 지금의 `ui.cpp` 와 견줘, 위에 적지 않은 차이(다른 Task 에서 생긴 줄)가 있으면 그 줄을 살린다.

- [ ] **Step 11: 빌드하고 전체 테스트**

Run: `uv run srkit toybox-build 2>&1 | tail -3 && uv run pytest -q --no-header 2>&1 | tail -2`
Expected: `빌드 완료`, `167 passed` (163 + 나라 목록 3 + 2바이트 글자 1).

`test_only_cheats…` 가 `KeyError` 나 대상 불일치로 실패하면 `docs/07-cheats.md` 의 그 치트 줄(대상 · 검증 칸)을 읽고, 표가 틀렸으면 표를, 테스트의 허용 목록이 좁으면 목록을 고친다 — 07 의 내용은 고치지 않는다.

- [ ] **Step 12: 게임에서 본다 (H4 ~ H9)**

시험용 빌드를 넣는다(미리보기에 `갱신: srtoybox.dll` 한 줄만).

```bash
uv run srkit deploy toybox
uv run srkit deploy toybox --apply
```

게임을 화면 밖에서 띄워 게임에 들어간다(Task 3 Step 9 의 앞 네 줄). 이 확인은 오래 걸린다 — 백그라운드 에이전트에 맡겨도 된다(맡길 때는 사용자의 범위 고정 문구를 넣고, 돌려받은 화면을 직접 확인한다). **저장하지 않는다. 되돌릴 수 없는 치트를 쓰므로 이 판은 버린다.**

새 탭의 단추 자리는 화면을 찍어 읽는다: 창을 열고(`key CTRL+SHIFT+T`) "외교·영토" 탭을 누른 뒤 `shot build/verify/toybox/H5-tab.png` 로 찍어 단추와 목록의 좌표를 읽는다. 목록과 단추가 창보다 길어 세로로 넘친다 — 아래쪽 단추는 창 위에서 `wheel -3 300 400` 으로 내려서 누른다.

| # | 하는 일 | 볼 것(화면에서) |
|---|---|---|
| H4 | "인구·여론" 탭의 "내 나라 지지율 100%" | 국내 지지율이 100% (07 의 `approval` 을 볼 때 본 화면) |
| H5 | "외교·영토" 탭에서 폴란드를 골라 "관계 최고", 이어서 "관계 중립" | 폴란드와의 외교 화면: 관계 막대가 가득 → 절반 |
| H6 | 덴마크를 골라 "병합", 룩셈부르크를 골라 "식민지화", 오스트리아를 골라 "지도자 제거" — 각각 단추가 "한 번 더 누르면 실행합니다"로 바뀐 뒤 한 번 더 | 07 에서 본 효과: 덴마크 땅이 내 영토, 룩셈부르크가 식민지 · 동맹, 지도자 사망 알림 |
| H7 | 지도에서 프랑스 땅을 누르고 "동맹 맺기". 지도에서 오스트리아 땅을 누르고, 목록에서 체코를 골라 "전쟁 붙이기" | 프랑스와 동맹(외교 화면). "동맹국 공격받음" 류의 알림 |
| H8 | 폴란드를 골라 "이 나라로 플레이" | 상태 줄이 "플레이 중: 폴란드 (1106)". 목록에서 폴란드가 빠지고 독일이 들어온다. "고른 나라"가 "없음"이 된다 |
| H9 | 검색란을 누르고 `uv run python scripts/gamedrive.py type den` | 목록에 덴마크만(병합했으면 없다 — 그때는 `fra`). 지우고(`key BACK` 세 번) `type 14` → 번호에 14 가 든 나라들 |

H9 의 한글: 게임 창이 ANSI 창인지 먼저 본다. 스크래치에 스크립트를 써서(Write 도구) 돌린다.

```python
"""H9: 검색란에 초점을 둔 채, 한글 한 글자를 CP949 의 두 바이트로 보낸다(입력기가 ANSI 창에 보내는 꼴)."""
import ctypes
import sys
import time

sys.path.insert(0, r"E:\SR2030ToyBox\scripts")
sys.stdout.reconfigure(encoding="utf-8")
import gamedrive  # noqa: E402
from srkit import config  # noqa: E402

hwnd, _, _ = gamedrive.need_window(config.load())
print("게임 창은", "유니코드 창" if gamedrive.user32.IsWindowUnicode(hwnd) else "ANSI 창")
for byte in "독".encode("cp949"):
    ctypes.windll.user32.PostMessageA(hwnd, 0x0102, byte, 1)      # WM_CHAR
    time.sleep(0.05)
```

Expected: "ANSI 창"이고, 검색란에 `독` 이 찍히고 목록에 독일만 남는다(H8 뒤라 독일이 목록에 있다). "유니코드 창"이면 두 바이트가 따로 찍힌다 — 그때는 합치는 코드가 돌지 않는 것이 맞고(유니코드 창에서는 한 글자가 `WM_CHAR` 한 번으로 온다), 본 대로 적는다.

효과를 보지 못한 것이 있으면 그 단추를 지우지 말고, 본 것을 그대로 적어 Task 5 의 문서에 [추정] 또는 "효과를 보지 못했다"로 남긴다. 직접 실행에서만 안 되고 `SRTOYBOX_DIRECT=0` 으로는 되는 치트가 있으면 멈추고 보고한다(설계서의 위험 표 — 그 치트는 글쇠 방식으로만 실행하게 해야 한다).

끝나면 게임을 끈다(게임 메뉴 → "게임 종료" → "게임 종료" → 메인 메뉴의 종료 단추).

- [ ] **Step 13: 커밋 · PR · 머지**

```bash
git add native/srtoybox/features.h native/srtoybox/features.cpp native/srtoybox/command.h native/srtoybox/command.cpp native/srtoybox/regions.h native/srtoybox/regions.cpp native/srtoybox/input.h native/srtoybox/input.cpp native/srtoybox/ui.cpp native/srtoybox/exports.cpp tests/test_toybox.py tests/test_toybox_game.py
git commit -m "feat: ToyBox — 나라를 골라 쓰는 치트 (지지율, 관계, 동맹, 병합, 식민지화, 지도자 제거, 전쟁, 플레이 국가)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/toybox-regions
```

PR 을 `develop` 으로 올리고(본문에 `uv run pytest` 결과, H4 ~ H9 에서 본 것과 보지 못한 것) 머지한 뒤 `git switch develop && git pull --ff-only origin develop`.

---

### Task 5: Steam 확인, 문서, 마무리

**브랜치:** `docs/toybox-stage2` (`develop` 에서)

**Files:**
- Create: `docs/11-game-internals.md`
- Modify: `docs/10-toybox.md`, `docs/07-cheats.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `mods/toybox/README.md`, `docs/superpowers/specs/2026-10-07-toybox-stage2-design.md`

**Interfaces:**
- Consumes: Task 1 ~ 4 의 결과와, 각 Task 에서 게임에서 본 것(H1 ~ H11 의 화면 · 로그).
- Produces: 문서. 코드는 바꾸지 않는다.

- [ ] **Step 1: 브랜치를 만들고 최종 빌드를 넣는다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-stage2
uv run srkit toybox-build
uv run pytest -q --no-header 2>&1 | tail -1
uv run srkit deploy toybox
uv run srkit deploy toybox --apply
```

Expected: `167 passed`. 미리보기는 `갱신: srtoybox.dll` 한 줄(이미 같은 파일이면 바뀌는 것이 없다고 나온다 — 그때는 `--apply` 를 하지 않는다).

- [ ] **Step 2: Steam 으로 띄워 본다 (H12)**

`overlay.cpp` 는 이 단계에서 고치지 않았지만, 실제 환경에서 주소 찾기와 상태 읽기가 되는지는 여기서만 볼 수 있다. **띄우기 전에 채팅에 알린다**(창이 1 ~ 2분 뜨고 포커스를 가져갈 수 있다).

```bash
unset SRTOYBOX_HOME
uv run python scripts/gamedrive.py steam 75        # (이어서 20초)
uv run python scripts/gamedrive.py status
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
uv run python scripts/gamedrive.py shot build/verify/toybox/H12-steam-menu.png
uv run python scripts/gamedrive.py click 90 208    # 꺼진 단추
uv run python scripts/gamedrive.py shot build/verify/toybox/H12-steam-clicked.png
uv run python scripts/gamedrive.py key CTRL+SHIFT+T
tail -6 "$APPDATA/SR2030ToyBox/toybox.log"
```

Expected: 로그에 `화면에 끼어들었습니다 (다른 훅이 먼저 있습니다)` 와 `게임 상태를 읽습니다 (명령 처리 함수 +0x522330)`. `H12-steam-menu.png` 의 상태 줄이 "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다". 누른 뒤에도 "마지막으로 넣은 것"이 생기지 않는다.

게임을 스스로 끝나게 한다(창의 닫기와 같은 길 — `taskkill` 을 쓰지 않는다). 스크래치의 `fx_close.py` 가 없으면 다음을 써서 돌린다.

```python
"""이 도구가 띄운 게임에 WM_CLOSE 를 보내 스스로 끝나는지 본다."""
import sys
import time

sys.path.insert(0, r"E:\SR2030ToyBox\scripts")
sys.stdout.reconfigure(encoding="utf-8")
import gamedrive  # noqa: E402
from srkit import config  # noqa: E402

cfg = config.load()
hwnd, _, _ = gamedrive.need_window(cfg)
gamedrive.user32.PostMessageW(hwnd, 0x0010, 0, 0)      # WM_CLOSE
start = time.time()
while time.time() - start < 30 and gamedrive.owned_pids(cfg):
    time.sleep(0.5)
print("스스로 끝남" if not gamedrive.owned_pids(cfg) else "30초 뒤에도 살아 있음", f"({time.time() - start:.1f}초)")
```

Expected: "스스로 끝남". 이어서 Windows 이벤트 로그에 게임의 충돌 기록(Application 로그의 ID 1000, `SupremeRuler2030.exe`)이 새로 없는 것을 본다.

Steam 으로 띄운 게임에서는 검증 도구로 게임의 메뉴를 누를 수 없어(가상 마우스가 없다) 게임 안의 직접 실행은 볼 수 없다. 그대로 적는다.

- [ ] **Step 3: 게임 폴더의 상태를 확인한다**

```bash
ls build/.deploy
sha256sum build/toybox/srtoybox.dll "/e/SteamLibrary/steamapps/common/Supreme Ruler 2030/srtoybox.dll" | cut -c1-16
(cd "/e/SteamLibrary/steamapps/common/Supreme Ruler 2030" && sha256sum -c /e/SR2030ToyBox/build/verify/v5/before.sha256 2>&1 | grep -c OK)
```

Expected: `korean` `toybox`, 두 해시가 같다, `10`.

- [ ] **Step 4: 새 문서 `docs/11-game-internals.md` 를 쓴다**

아래 내용으로 쓴다. `[확인: 게임]` 을 붙이는 줄은 Task 2 ~ 4 에서 실제로 본 것만이다 — 보지 못한 것은 `[추정]` 이나 "보지 않았다"로 바꿔 적는다.

````markdown
# 11. 게임의 안쪽 — ToyBox 가 읽고 부르는 것

조사 기준: Steam appid `2093410`, build `21347933`(게임 12.1.1360), `SupremeRuler2030.exe` 15,494,144 바이트, PE TimeDateStamp `0x695377b6`.
**이 문서의 RVA 는 모두 이 빌드의 것이다.** 게임이 업데이트되면 `uv run srkit locate` 로 다시 본다.

표기: **[확인: 정적]** 실행 파일의 명령을 직접 읽었다 · **[확인: 실행]** 화면 밖에서 띄운 게임의 메모리를 읽어 봤다 ·
**[확인: 게임]** 게임 화면에서 봤다 · **[추정]** 정황으로 판단했다.

조사 방법: 실행 파일을 읽어 MSVC 의 `dumpbin /disasm` 과 Python 으로 봤고(정적), 검증 도구가 띄운 게임의 메모리를 밖에서 읽기만 했다(실행).
분석에 쓴 스크립트와 디스어셈블리는 저장소에 넣지 않았다.

## 명령 처리 함수

게임 설정 창(`Ctrl+Shift+S`)의 입력줄에 넣은 한 줄을 처리하는 함수다. 치트 문자열 91개를 모두 이 함수가 참조한다 [확인: 정적].

- RVA `0x522330` – `0x5284fd` (25,037 바이트). 큰 함수라 함수 표(`.pdata`)에는 조각 11개로 나뉘어 있고 chained unwind 로 묶인다.
- `void f(void *this /*RCX*/, const char *line /*RDX*/)`. `line` 은 `cheat ` 까지 포함한 입력줄 전체. 길이 인자와 반환값은 없다.
- 부르는 곳은 `.text` 전체에서 **`0x6649af` 한 곳**이다. 바로 앞에서 `lea rcx,[0x1764310]` — `this` 는 정적 전역 객체의 주소 그 자체다.
- 인자 없는 치트 66개는 `strcmp`(줄 전체가 같아야 한다), 인자를 받는 25개는 `strstr` 로 맞춘 뒤 **마지막 공백 뒤**를 정수로 읽는다. 모두 소문자여야 한다.
- 머리에서 검사하는 것은 멀티플레이 표시 하나다. **게임이 진행 중인지는 검사하지 않고** 플레이어 포인터를 그대로 따라간다 — 게임 밖에서 부르면 안 된다.
- 치트 허용 비트의 검사는 함수 안 `0x522b3e` 한 곳이고, 그 앞에 있는 것(`cheat allowcheats`, `cheat devcheat`, `output…` 등)은 비트 없이도 된다.
- 게임의 메시지 루프와 창 프로시저, 프레임 갱신이 한 스레드에서 번갈아 돈다. ToyBox 는 창 프로시저 안의 타이머에서 이 함수를 부른다.

ToyBox 가 이 함수를 불렀을 때: (H3 에서 본 것을 적는다 — 국고의 변화, 게임 설정 창이 뜨지 않았는지) **[확인: 게임]**

## 전역과 필드

| 무엇 | RVA | 형 | 근거 |
|---|---|---|---|
| 명령 처리 함수 | `0x522330` | 함수 | [확인: 정적] |
| 그 함수의 `this` | `0x1764310` | 정적 객체 | [확인: 정적] |
| 멀티플레이 표시 | `0xf19634` | byte | [확인: 정적] 쓰는 자리. 싱글에서 0 [확인: 실행] |
| 옵션 묶음 (치트 허용 = 비트 `0x40`) | `0x1eb556c` | dword | [확인: 정적] · [확인: 실행] |
| 프로그램 상태 | `0x1eed11c` | dword | [확인: 정적] · [확인: 실행] |
| 모드 상태 | `0xe7be30` | dword | [확인: 정적] · [확인: 실행] |
| 플레이어 지역의 인덱스 (사본 `0x18294ec`) | `0x18294e0` | dword | [확인: 정적] · [확인: 실행] |
| 플레이어 지역 객체의 포인터 (사본 `0x1829600`) | `0x18295f8` | qword | [확인: 정적] · [확인: 실행] |
| 지역 포인터 표 (인덱스순) | `0x1af78c0` | qword × 1024 | [확인: 정적] · [확인: 실행] |
| 지역 수 (표의 마지막 인덱스) | `0x18294d8` | dword | [확인: 정적] · 게임 안에서 352 [확인: 실행] |

지역 객체:

| 자리 | 형 | 뜻 | 근거 |
|---|---|---|---|
| `+0` | dword | 0 이면 쓸 수 없는 지역 | [확인: 정적]. 독일 2, 폴란드 3 [확인: 실행] |
| `+4` | word | 자기 인덱스 | [확인: 정적] · [확인: 실행] |
| `+8` | word | 지역 번호(`&&CVP` 의 번호) | 독일 1499, 폴란드 1106 [확인: 실행] |
| `+0x14B48` | float | 인구 | 82,615,760 — 화면과 같다 [확인: 실행] |
| `+0x14B88` | double | 국고(달러) | 14.43 B — 화면과 같다 [확인: 실행] |

옵션 묶음의 dword 는 비트마다 다른 옵션이다. 통째로 쓰면 안 된다.

## 값의 흐름 [확인: 실행]

| 때 | 프로그램 상태 | 모드 상태 | 플레이어 포인터 | 치트 비트 |
|---|---|---|---|---|
| 뜨는 중 · 메인 메뉴 | 3 | 1 | NULL | 0 |
| 로비 | 3 | 1 | NULL (인덱스는 이미 차 있다) | 0 |
| "시작"을 누르고 2초 뒤 ~ 게임 안 | 1 | 2 | 있다 | 0 |
| 게임의 설정 창 · 게임 메뉴가 열려 있을 때 | 1 | 2 | 그대로 | 그대로 |
| `cheat allowcheats` 뒤 | 1 | 2 | 그대로 | 1 |
| `cheat becomeregion <번호>` 뒤 | 1 | 2 | 그 지역으로 바뀐다 | 1 |
| 게임에서 메인 메뉴로 나온 뒤 | 3 | 1 | NULL (인덱스는 낡은 값이 남는다) | 0 |

- ToyBox 의 "진행 중" 판정: `모드 상태 == 2 && 프로그램 상태 == 1 && 플레이어 포인터 != NULL`, 그리고 읽은 값들이 서로 맞을 것
  (표[인덱스] == 포인터, 객체[+4] == 인덱스, 0 < 객체[+8] < 12900, 객체[+0] != 0).
- 치트 허용은 메뉴로 나오면 꺼진다. ToyBox 는 명령마다 비트를 보고, 꺼져 있으면 `cheat allowcheats` 를 먼저 넘긴다.
- "시작"을 누른 직후(불러오는 화면)에도 값은 이미 진행 중이다. 그때 치트가 듣는지는 보지 않았다.

## 주소를 찾는 법 (`locate`)

ToyBox 는 주소를 코드에 적어 두지 않는다. 게임이 뜰 때 올라와 있는 실행 파일에서 찾는다(`native/srtoybox/locate.cpp`).
같은 코드를 `uv run srkit locate` 가 설치된 파일에 대고 돌린다.

| 찾을 것 | 절차 |
|---|---|
| 명령 처리 함수 | `"cheat allowcheats\0"`(읽기 전용 자료에 1개) → 그것을 가리키는 `lea r,[rip+d]`(1곳) → 그 자리가 든 함수 표 항목 → chained unwind 의 뿌리 |
| 멀티플레이 표시 | 함수 머리(0x60 바이트 안)의 `80 3D d32 00` |
| 옵션 묶음 | 함수 머리의 `83 0D d32 40` |
| `this` | 함수를 부르는 `E8 rel32`(1곳) 바로 앞의 `48 8D 0D d32` |
| 프로그램 상태 | 부르는 함수(뿌리)의 머리(0x40 바이트 안)의 `83 3D d32 06` |
| 플레이어 포인터 | `"cheat georgew"` 를 쓰는 자리 뒤의 `48 8B 05 d32 F2 0F 10 80` |
| 플레이어 인덱스 · 지역 표 | `"cheat populate"` 를 쓰는 자리 뒤의 `48 63 05 d32 4C 8D 3D d32` 와 `49 8B 8C C7 off32` |
| 지역 수 | `"cheat becomeregion"` 블록의 `44 8B 0D d32 45 33 F6 45 85 C9 0F 88 d32 48 8D 0D d32` |
| 모드 상태 | `C7 05 d32 02 00 00 00 C7 05 d32 01 00 00 00` (`.text` 에 1곳) |

대조 — 하나라도 어긋나면 "못 찾았다"이고, ToyBox 는 글쇠 방식으로 동작한다:

1. 닻 문자열이 1개이고 그것을 쓰는 자리가 1곳이다.
2. 함수를 부르는 곳이 1곳이고 바로 앞이 `lea rcx,[rip+d]` 다.
3. 함수 머리에 멀티플레이 검사와 `or …,40h` 가 둘 다 있다.
4. `georgew` 와 `georgeww` 가 같은 플레이어 포인터를 쓴다.
5. `becomeregion` 이 쓰는 인덱스가 `populate` 가 읽는 것과 같다.
6. 지역 표의 주소가 `populate` 와 `becomeregion` 에서 같다.
7. 모드 상태 서명이 1곳이고 그 둘째 주소가 프로그램 상태와 같다.
8. 찾은 주소가 모두 이미지 안에 있다.

지역 객체 안의 자리(`+0` `+4` `+8`)는 서명으로 찾을 수 없다. 그래서 읽을 때마다 위의 "서로 맞을 것"으로 거른다.

다른 빌드에서는 돌려 보지 못했다(이 빌드 하나뿐이다) [추정: 함수가 다시 컴파일되어 레지스터 배정이 바뀌면 서명이 깨질 수 있다. 문자열 닻은 남는다].

## 이번에 알게 된 치트의 사실 [확인: 정적]

- `cheat damage` 는 줄 전체가 `cheat damage` 여야 맞는다. `cheat damage 5` 처럼 인자를 붙이면 영영 맞지 않는다.
- `cheat trumpme` 는 번갈아가 아니라 난수의 한 비트로 부호를 골라 ±$1 T 를 더한다.
- `cheat depopulate` 는 인구에 1 을 쓴다.
- 인자를 받는 지역 치트는 인자가 0 이면(주지 않으면) 전역 객체의 `+0x10` 이 가리키는 지역을 쓴다 — "지도에서 고른 지역"으로 보인다 [추정].
- 치트 허용 비트를 검사하는 25곳 가운데 19곳은 바로 뒤의 Steam 업적 호출(`"ACH%03d"`)을 건너뛴다. 치트를 켠 판에서는 그 업적들이 주어지지 않는 것으로 읽힌다 [추정: 실행해 본 것이 아니다].

## 보지 않은 것

- 멀티플레이 로비에서 멀티플레이 표시가 1 이 되는지(멀티플레이는 띄우지 않았다).
- 다른 시나리오 · 캠페인 · 불러온 저장에서 값의 흐름이 같은지(2030 - 세계 샌드박스에서만 봤다).
- 치트 허용 비트가 저장 파일에 들어가는지.
````

- [ ] **Step 5: `docs/10-toybox.md` 를 고친다**

각 절을 다음과 같이 고친다. **[확인]을 붙이는 것은 H1 ~ H12 에서 실제로 본 것만**이고, 근거 화면의 이름(`H3-after` 등)을 함께 적는다.

| 절 | 고칠 내용 |
|---|---|
| 머리(`조사 기준`) | 날짜에 2026-10-07 을 더한다 |
| `## 무엇인가` | "지금은 1단계다 …" 문단을 2단계까지로: 게임 상태를 읽는다 / 치트를 게임의 함수에 직접 넘긴다 / 나라를 골라 쓰는 치트. 주소를 못 찾는 빌드에서는 1단계처럼 동작한다 |
| `## 쓰는 법` | 상태 줄의 네 가지 글과 뜻. 게임 밖 · 멀티플레이에서는 단추가 꺼진다. "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힌다"는 글쇠 방식일 때만 — 직접 실행에서는 뜨지 않고 바로 끝난다. "외교·영토" 탭: 목록에서 나라를 고른다(검색: 한글 · 영문 · 번호), "동맹 맺기"와 "전쟁 붙이기"는 지도에서 나라를 고른 뒤. 되돌릴 수 없는 것은 한 번 더 누른다 |
| `## 기능` | 표에 아홉 줄을 더한다(탭 · 창의 이름 · 넣는 명령 · 대상 · 07 에서 본 효과 · 창에서). "창에서" 칸은 H4 ~ H8 에서 본 것만 [확인]. "넣지 않은 것"에서 지역 번호가 필요한 것의 줄을 지우고 `hate`(불리) · `liberate` · `revolt`(07 에서 반응 없음)를 적는다 |
| `## 한계` | (가) "게임이 진행 중인지 ToyBox 는 모른다"를 고친다: 주소를 찾은 빌드에서는 안다 — 게임 밖에서는 단추가 꺼진다. 못 찾은 빌드에서는 1단계 그대로다. (나) 더한다: 게임이 업데이트되면 주소 찾기가 깨질 수 있다(그때는 글쇠 방식, `srkit locate` 로 본다) / 직접 실행 중 오류가 나면 창에 경고가 뜨고 그 뒤로 실행하지 않는다 — 저장하지 말고 게임을 다시 시작한다 / 2030 - 세계 샌드박스에서만 봤다 / 한글 검색은 바이트 두 개를 보내 본 것이고 실제 입력기로는 보지 않았다 [추정] / 치트 허용이 켜진 판에서는 업적이 주어지지 않는 것으로 읽힌다([11](11-game-internals.md)) |
| `## 구조` | 그림과 파일 표에 `locate` · `game` · `regions` 를 더한다. "실행 파일의 주소를 쓰지 않는다" 항목을 고친다: 주소를 **적어 두지** 않는다 — 화면은 가상 함수 표에서, 게임의 함수와 전역은 문자열을 닻으로 찾는다([11](11-game-internals.md)). "명령 실행기" 항목에 직접 실행과 자동 전환, 오류 가드, `SRTOYBOX_DIRECT=0` |
| `## 확인한 것` | 새 표 "2단계에서 본 것": H1 ~ H12 한 줄씩(한 것 · 본 것 · 근거 화면). 보지 못한 것은 "보지 못했다"로 그 줄에 적는다. 자동 테스트 문단에 주소 찾기(가짜 이미지 · 설치된 게임), 상태 읽기(가짜 메모리), 가짜 게임으로 본 단추 끄기 · 직접 실행 · 오류 가드를 더한다 |
| `## 문제가 생기면` | 로그 표에 네 줄: `게임 상태를 읽습니다 (…)` / `게임 상태를 읽을 수 없습니다 (<까닭>) — 글쇠 방식` / `직접 실행: <명령>` / `직접 실행 중 예외 0x… (<명령>)`. 끄는 법에 `SRTOYBOX_DIRECT=0`(직접 실행만 끈다) |
| `## 다음 단계` | 2단계의 줄을 지우고 3 · 4단계를 남긴다. "2단계의 출발점" 문단을 지운다(이제 [11](11-game-internals.md)에 있다) |

- [ ] **Step 6: 나머지 문서를 고친다**

- `docs/07-cheats.md`: "알아 둘 것"(또는 맨 앞의 요약 목록)에 세 줄을 더한다 — `cheat damage` 는 인자를 붙이면 맞지 않는다 / `cheat trumpme` 의 부호는 무작위다 / 치트 허용 비트와 업적의 정적 근거. 각 줄 끝에 `[확인: 정적 — docs/11]`. 치트표의 칸은 고치지 않는다(자동 테스트가 읽는다).
- `docs/09-cheat-mod-plan.md`: 로드맵의 2번을 `2. **ToyBox 2단계 (끝).** 게임 상태 읽기, 직접 실행, 나라를 골라 쓰는 치트 — [10](10-toybox.md), [11](11-game-internals.md).` 로. "게임 업데이트 대비"의 점검 순서에 `uv run srkit locate` 를 `cheats-check` 다음에 넣는다. "미해결 문제"의 업적 항목에 정적 근거 한 줄.
- `README.md`: 명령 목록에 `uv run srkit locate                    # 설치된 게임에서 ToyBox 가 쓰는 주소를 찾아 보고` 를 `toybox-build` 줄 아래에, 문서 목록에 `  11-game-internals.md          게임의 안쪽 — ToyBox 가 읽고 부르는 것` 을 `10-toybox.md` 줄 아래에. ToyBox 를 소개하는 문단이 "1단계"만 말하면 2단계까지로 고친다.
- `mods/toybox/README.md`: ToyBox 가 하는 일의 요약을 2단계까지로(한두 줄).
- `docs/superpowers/specs/2026-10-07-toybox-stage2-design.md` 끝에 더한다.

```markdown

## 보완 내역 (2026-10-07, 구현 계획을 쓰며)

- **지역 수의 주소도 찾는다.** 주소 찾기 표에 지역 수가 빠져 있었다. `becomeregion` 블록의
  `44 8B 0D d32 45 33 F6 45 85 C9 0F 88 d32 48 8D 0D d32` 에서 지역 수와 지역 표를 함께 얻고, 지역 표가 `populate` 에서 얻은 것과
  같은지를 대조에 더했다(대조는 여덟 가지가 됐다).
- **나라 이름표는 상태 읽기와 함께 만들었다**(작업 순서의 2번). 상태 줄이 플레이어의 이름을 보여야 해서다.
- **지역 목록은 창이 "외교·영토" 탭을 보이는 동안 1초마다 읽는다**(프레임마다가 아니다).
```

구현하며 달라진 것이 더 있으면(각 Task 의 판단) 같은 절에 한 줄씩 더한다.

- [ ] **Step 7: 문서를 점검한다**

```bash
grep -n "0x[0-9a-f]\{5,\}" docs/10-toybox.md docs/11-game-internals.md docs/07-cheats.md | grep -v "21347933" | head -20
grep -c "\[확인: 게임\]" docs/11-game-internals.md
uv run pytest -q --no-header 2>&1 | tail -1
```

Expected: 첫 줄의 결과를 훑어 RVA 가 적힌 문서마다 빌드 번호가 머리에 있는지 본다(`docs/11` 은 머리에 한 번, `docs/10` 에 RVA 를 적었다면 그 줄에 빌드 번호). `167 passed`(07 의 표를 읽는 테스트가 깨지지 않았다).

- [ ] **Step 8: 커밋 · PR · 머지**

```bash
git add docs/10-toybox.md docs/11-game-internals.md docs/07-cheats.md docs/09-cheat-mod-plan.md README.md mods/toybox/README.md docs/superpowers/specs/2026-10-07-toybox-stage2-design.md
git commit -m "docs: ToyBox 2단계 — 쓰는 법 · 한계 · 확인한 것, 게임의 안쪽(주소 · 전역 · 찾는 법)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin docs/toybox-stage2
```

PR 을 `develop` 으로 올리고 머지한 뒤 `git switch develop && git pull --ff-only origin develop`.

- [ ] **Step 9: 마지막 보고에 넣을 것**

- H1 ~ H12 가운데 본 것과 보지 못한 것.
- 게임 폴더의 상태(최종 빌드의 `srtoybox.dll`, 다른 파일의 해시 10개).
- `CLAUDE.md` 에 넣을 줄의 제안(고치지는 않는다): `uv run srkit toybox-build` / 게임 업데이트 뒤의 순서에 `uv run srkit locate` / "`overlay.cpp` · `input.cpp` 를 고치면 `gamedrive.py steam` 으로 확인".
- `develop` → `main` 릴리스는 사용자가 원할 때.

## 계획 밖에 두는 것

- 게임의 메모리에 값을 쓰는 것(GDP · 국고를 직접 고치기), 값을 유지하는 토글, 장비 수치 — 3 · 4단계.
- 지도에서 고른 나라를 창에 보여 주는 것(게임의 "고른 지역"을 읽는 것은 [추정]이다).
- `cheat treaty <조약 번호>`(번호를 준 경우는 07 에서 시험하지 않았다), `hate` · `liberate` · `revolt`.
- 멀티플레이, 2030 - 세계 밖의 시나리오에서의 확인.
- 1단계 최종 리뷰의 미룬 항목들(단축키 검증, 입력 잔가지 등).
