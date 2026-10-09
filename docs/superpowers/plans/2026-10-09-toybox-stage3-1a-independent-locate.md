# ToyBox 3단계 1 (가) — 내장 치트와 무관한 주소 찾기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ToyBox(`srtoybox.dll`)가 게임의 상태(진행 중 여부 · 플레이어 국가 · 이번 게임의 나라들)를 읽는 데 쓰는 주소 일곱 개를, 치트 문자열과 치트 명령 처리 함수의 코드에 기대지 않고 찾는다.

**Architecture:** 게임의 코드에서 주소를 읽어 내는 짧은 바이트 꼴인 "서명"을 도입한다(`sigs`, 순수 함수). 찾을 것마다 서로 다른 함수에서 뽑은 서명 셋을 두고, 실행 구역 전체에서 정확히 한 번 맞은 것이 둘 이상이며 그 값이 모두 같을 때만 "찾았다"로 친다(`locate_state`). 지금의 치트 닻 찾기는 아직 옮기지 않은 기능이 쓰는 셋(명령 처리 함수 · `this` · 옵션 묶음)만 남겨 `locate_legacy` 로 줄인다. 서명 후보는 개발용 명령 `srkit sig-mine` 이 설치된 실행 파일에서 뽑는다.

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Python 3.13 + ctypes + pytest + numpy (`uv run`), capstone(개발 의존성, 새로 더한다), Win32.

**Spec:** `docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md` (승인 2026-10-09). 이 계획은 그 문서의 "작업 순서와 브랜치" 1 · 2 를 구현한다. 3 ~ 5(값 쓰기, 돈 · 물자 탭, 최소 유지)는 이 계획이 끝난 뒤 계획 (나)로 따로 쓴다 — (가)가 만드는 인터페이스 위에 서기 때문이다.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 RVA 를 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 를 적지 않는다(테스트의 기대값과 문서에만). 서명(짧은 바이트 꼴)은 제품 코드에 든다.
- **요구 3 — 내장 치트와 별도.** `sigs` 와 `locate_state` 는 치트 문자열(`"cheat …"`)도 치트 명령 처리 함수의 코드도 쓰지 않는다. 치트 닻을 쓰는 곳은 셋뿐이다: `locate_legacy`(전환 기간에만. 마지막 묶음에서 지운다), `srkit.sigmine.handler_range`(서명이 치트 함수 밖임을 가리는 개발용 코드), `tests/toybox_cheat_oracle.py`(테스트의 대조). 뒤의 둘은 DLL 밖이다.
- **무엇을 찾지 못했을 때 내장 치트로 되돌아가는 길을 새로 만들지 않는다.** 옮기지 않은 기능의 글쇠 방식은 지금 있는 그대로 둔다.
- **이 계획에서는 게임의 메모리에 쓰지 않는다**(값 쓰기는 계획 (나)).
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다. (설계서의 승인이 이 바꿔 넣기의 승인을 포함한다.)
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다. 서명은 하나에 12 ~ 45바이트다. `srkit sig-mine` 의 출력은 저장소에 넣지 않는다.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다.** 한 판에서 게임 시간을 3일 넘게 흘리지 않는다(7일마다 자동 저장된다). 게임이 떠 있는 동안 브랜치를 바꾸지 않는다. **검증용 게임은 `SRTOYBOX_HOME` 을 임시 폴더로 돌려 띄운다**(사용자의 실제 `%APPDATA%\SR2030ToyBox` 를 건드리지 않는다). Steam 으로 띄우는 것은 Task 5 의 한 번, 띄우기 전에 채팅에 알린다.
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.**
- Git: `main` · `develop` 에 직접 커밋하지 않는다. `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고 `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다. **머지 명령이 권한 분류기에 거부되면 다른 형태로 우회하지 않는다** — 사용자에게 그 명령을 그대로 건네고, 머지된 뒤 `git switch develop && git pull --ff-only origin develop` 로 이어 간다.
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`.
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다.
- **시작할 때의 테스트 상태**: PR #29(`fix/korean-extra-regions-root-only`)가 들어간 `develop` 에서 `uv run pytest` 186개 통과. 그 PR 이 아직 열려 있으면 Task 1 을 시작하기 전에 사용자에게 머지를 부탁한다(그 전의 `develop` 은 `tests/test_korean.py` 1개가 실패한다). `tests/test_toybox.py::test_toybox_keeps_drawing_after_an_exception_passes_through_present` 는 드물게 한 번 실패한 적이 있다(원인 모름) — 그것만 실패하면 한 번 다시 돌리고, 결과를 PR 본문에 그대로 적는다.

## 설계서와 달라진 곳 (계획을 쓰며)

- **계획을 둘로 나눈다.** (가) = 설계서의 작업 순서 1 · 2(서명, 새 찾기의 상태 묶음, 상태 읽기 옮기기, 옛 찾기 줄이기). (나) = 3 ~ 5(값 묶음, 돈 · 물자, 유지). 문서(6)는 (가)의 몫만 Task 6 에서 쓴다 — (가)가 `develop` 에 들어간 뒤에도 문서가 사실이어야 해서다.
- **`srkit sig-mine` 은 (가)에서 주소만 뽑는다.** 구조체 안의 자리와 간격(상수) 뽑기는 그것이 필요한 (나)에서 더한다. 서명 맞추기(`sigs`)는 상수 읽기까지 (가)에서 만든다(한 단위다).
- **서명의 최소 조건을 정했다**: 명령 셋 이상, 정해진 바이트 여덟 개 이상(나머지는 구멍). `sig-mine` 이 그보다 짧은 것은 내지 않는다.
- **`GameAddresses` 의 모양은 그대로 둔다**(필드 10개). 채우는 길만 둘로 나눈다: 일곱은 `locate_state`, 셋은 `locate_legacy`. Python 의 거울(`srkit.toybox.GameAddresses`)과 가짜 게임(`tests/toybox_fake_game.py`)이 그대로 쓰인다.
- **프로그램 상태와 모드 상태는 서명 하나씩을 같은 자리에서 읽는다**(게임 진입 `0x735b6e` 의 `mov [모드 상태],2` / `mov [프로그램 상태],1`). 2단계가 쓰던 서명이고 치트 함수 밖이다.
- **서명 맞추기는 처음부터 실행 구역을 한 번만 훑는다**(첫 바이트가 같은 서명끼리 줄을 세운다). 설계서는 "0.5초를 넘으면 바꾼다"고 했으나 서명이 늘어날 것이 분명하다.
- 로그의 줄에 걸린 시간을 넣는다: `게임 상태를 읽습니다 (서명 21개 가운데 21개, 18 ms)`.

## 설계 전에 확인한 것에 더해, 계획을 쓰며 확인한 것 [확인: 정적, build 21347933]

- 이 계획의 `sigs.h` · `sigs.cpp` 는 스크래치에서 `/W4 /WX` 로 컴파일하고 자체 점검(서명 글 읽기, 주소 · 상수 읽기, 횟수, 구역의 끝, 투표)을 통과시킨 것이다.
- 이 계획의 `sigmine.py` 는 스크래치에서 Task 2 의 테스트와 같은 가짜 이미지 · 같은 기대값으로 통과시킨 것이다. 설치된 실행 파일에서 치트 함수의 범위를 `(0x522330, 0x5284fd)` 로 구했다.
- Task 3 의 서명 21개는 설치된 실행 파일에서 하나씩 대조했다: 실행 구역에서 정확히 한 번 맞고, 읽어 낸 주소가 2단계의 값과 같고, 맞은 자리가 치트 명령 처리 함수 밖이고, 찾을 것마다 세 서명이 서로 다른 함수에 있다.

| 찾을 것 | RVA | 서명이 맞는 자리 (든 함수) |
|---|---|---|
| 멀티플레이 표시 | `0xf19634` | `0x4c3f14` (`0x4c3e30`) · `0x51c216` (`0x51c210`) · `0x52a8f4` (`0x52a8f0`) |
| 프로그램 상태 | `0x1eed11c` | `0x52fd15` (`0x52fcc0`) · `0x688739` (`0x688720`) · `0x735b6e` (`0x735b30`) |
| 모드 상태 | `0xe7be30` | `0x4f2996` (`0x4f2990`) · `0x6a7b7f` (`0x6a7b70`) · `0x735b6e` (`0x735b30`) |
| 플레이어 지역의 인덱스 | `0x18294e0` | `0x93db9` (`0x85290`) · `0x502e83` (`0x502d50`) · `0x57d65e` (`0x5391a0`) |
| 플레이어 지역 객체의 포인터 | `0x18295f8` | `0x4c3c1f` (`0x4c3bc0`) · `0x4e3db0` (`0x4e37e0`) · `0x6d14c2` (`0x6d0d80`) |
| 지역 포인터 표 | `0x1af78c0` | `0xbe8a0b` (`0xbe8760`) · `0x69fe98` (`0x69e490`) · `0x6d7407` (함수 표에 없는 작은 함수) |
| 지역 수 | `0x18294d8` | `0x812ef` (`0x810d0`) · `0x83342` (`0x82cb0`) · `0x916b0` (`0x85290`) |

## Review Focus

설계서가 함의하지만 그대로 두면 테스트가 밟지 않을 다섯 가지. 각 줄의 테스트를 해당 Task 에 넣었다.

1. **업데이트로 코드가 바뀌어 서명 하나가 두 번 맞게 된다** → 그 서명은 세지 않는다(첫 번째 맞은 자리를 믿지 않는다). (Task 1 `test_a_signature_that_matches_twice_has_no_vote`, Task 3 `test_a_signature_that_matches_twice_does_not_count`)
2. **서명 둘은 같은 주소를, 하나는 다른 주소를 낸다** → "못 찾았다"다. 다수결로 틀린 쪽을 버리지 않는다. (Task 1 `test_the_vote_needs_two_signatures_that_agree`, Task 3 `test_signatures_that_disagree_are_refused`)
3. **게임이 치트를 없앴다(치트 문자열이 없다)** → 상태는 읽고(단추가 게임 밖에서 꺼진다), 옮기지 않은 기능은 글쇠 방식으로 가고, 죽지 않는다. (Task 3 `test_state_is_found_in_an_image_without_any_cheat_string`, Task 4 `test_game_state_without_the_legacy_addresses`)
4. **올라와 있는 실행 파일에 읽을 수 없는 쪽이 있다** → 죽지 않고 "못 찾았다"다. 여기서 예외가 새면 게임이 뜨다가 죽는다. (Task 3 `test_state_survives_an_image_with_a_page_it_cannot_read`)
5. **서명이 실행 구역의 끝이나 이미지의 끝에 걸친다** → 범위 밖을 읽지 않는다. (Task 1 `test_a_match_must_lie_inside_the_range`)

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `native/srtoybox/sigs.h` · `.cpp` (새로) | 서명 글 읽기, 실행 구역에서 맞추기, 투표. 순수 함수 | 1 |
| `src/srkit/sigmine.py` (새로) | 서명 후보 뽑기(개발용, capstone) | 2 |
| `native/srtoybox/locate.h` · `.cpp` | 새 찾기 `locate_state`(서명 표), 옛 찾기 `locate_legacy`(치트 닻 — 셋만) | 3 · 4 |
| `native/srtoybox/game.h` · `.cpp` | 상태 읽기의 주소를 새 찾기에서, 옵션 묶음이 없을 때의 읽기, 로그 | 4 |
| `native/srtoybox/exports.cpp` | 테스트와 `srkit` 이 쓰는 C 인터페이스 | 1 · 3 · 4 |
| `src/srkit/toybox.py`, `src/srkit/cli.py` | 빌드 목록, `srkit locate`, `srkit sig-mine` | 1 · 2 · 3 · 4 |
| `pyproject.toml`, `uv.lock` | 개발 의존성 `capstone` | 2 |
| `tests/test_toybox_sigs.py` (새로) | 서명 맞추기 · 투표의 테스트 | 1 |
| `tests/test_sigmine.py` (새로) | 서명 뽑기의 테스트 | 2 |
| `tests/toybox_fake_exe.py` | 가짜 실행 파일 이미지: 빈 틀, 서명 심기, 옛 찾기의 닻 | 2 · 3 · 4 |
| `tests/toybox_cheat_oracle.py` (새로) | 테스트의 대조용: 치트 닻으로 읽은 주소(2단계의 방식) | 3 |
| `tests/test_toybox_game.py` | 새 찾기 · 옛 찾기 · 상태 읽기의 테스트 | 3 · 4 |
| `docs/10-toybox.md`, `docs/11-game-internals.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md` | 문서 | 2 · 6 |

---

### Task 1: 서명 맞추기와 투표 (`sigs`)

**브랜치:** `feat/toybox-sigs` (`develop` 에서)

**Files:**
- Create: `native/srtoybox/sigs.h`, `native/srtoybox/sigs.cpp`
- Create: `tests/test_toybox_sigs.py`
- Modify: `native/srtoybox/exports.cpp`, `src/srkit/toybox.py:15-16`

**Interfaces:**
- Consumes: 없음.
- Produces:
  - C++ `struct Sig`, `bool sig_parse(const char *text, Sig *out);`
  - C++ `struct SigRange { uint32_t begin, end; };`, `struct SigHit { int count; uint32_t at; uint64_t value[SIG_CAPTURES]; };`
  - C++ `void sig_scan(const uint8_t *image, size_t size, const SigRange *ranges, int range_count, const Sig *sigs, int n, SigHit *hits);`
  - C++ `bool sig_vote(const Sig *sigs, const SigHit *hits, int n, int need, uint64_t *value, int *matched);`
  - 상수 `SIG_MAX = 64`, `SIG_CAPTURES = 2`
  - 서명 글의 낱말: 16진수 두 자리, `?`, `[rip]`, `[rip+1]`, `[rip+4]`, `[u32]`, `[u8]`
  - 내보내기 `int srtoybox_sig_find(const unsigned char *image, unsigned long long size, unsigned begin, unsigned end, const char *sigs, int need, char *out, int out_size)`

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-sigs
```

- [ ] **Step 2: 실패하는 테스트를 쓴다** — `tests/test_toybox_sigs.py` (Write 도구로)

```python
"""ToyBox 의 서명(native/srtoybox/sigs): 서명 글 읽기, 실행 구역에서 맞추기, 투표.

게임의 코드를 옮긴 것이 아니다 — 서명이 다루는 명령의 꼴만 작은 버퍼에 놓고 본다.
"""
import ctypes
import struct

import pytest

from srkit import toybox


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_sig_find.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p,
                                      ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib


def find(lib, image: bytes, sigs: list[str], begin: int = 0, end: int | None = None, need: int = 2):
    """서명마다 (맞은 횟수, 처음 맞은 자리, 값0, 값1) 또는 "bad". 그리고 투표 (찾았는가, 한 번만 맞은 수, 값0, 값1)."""
    out = ctypes.create_string_buffer(4096)
    assert lib.srtoybox_sig_find(image, len(image), begin, len(image) if end is None else end, "\n".join(sigs).encode(), need,
                                 out, len(out)) >= 0
    lines = out.value.decode().splitlines()
    rows = ["bad" if line == "bad" else tuple(int(x, 16) for x in line.split()) for line in lines[:-1]]
    vote = lines[-1].split()
    assert vote[0] == "vote"
    return rows, (vote[1] == "1", int(vote[2]), int(vote[3], 16), int(vote[4], 16))


def image_with(*pieces: tuple[int, bytes], size: int = 0x400) -> bytes:
    image = bytearray(size)
    for at, data in pieces:
        image[at:at + len(data)] = data
    return bytes(image)


def test_a_signature_reads_an_address_relative_to_the_end_of_its_instruction(lib):
    """rip 상대 거리는 명령의 끝이 기준이다. 거리 뒤에 상수가 붙는 명령은 그만큼 더 뒤가 끝이다."""
    image = image_with(
        (0x40, bytes([0x80, 0x3D]) + struct.pack("<i", 0x150 - 0x47) + bytes([0x00, 0x8B, 0xD8])),   # cmp byte ptr [rip+d],0 / mov ebx,eax
        (0x80, bytes([0x48, 0x8B, 0x05]) + struct.pack("<i", 0x150 - 0x87) + b"\x90"),               # mov rax,[rip+d] / nop
        (0xC0, bytes([0xC7, 0x05]) + struct.pack("<i", 0x150 - 0xCA) + struct.pack("<I", 2)))        # mov dword ptr [rip+d],2
    rows, _ = find(lib, image, ["80 3D [rip+1] 00 8B D8", "48 8B 05 [rip] 90", "C7 05 [rip+4] 02 00 00 00"])
    assert rows == [(1, 0x40, 0x150, 0), (1, 0x80, 0x150, 0), (1, 0xC0, 0x150, 0)]


def test_a_signature_reads_constants(lib):
    """구조체 안의 자리와 간격 같은 상수를 4바이트나 1바이트로 읽는다. 한 서명에서 둘까지. 16진수는 소문자여도 된다."""
    image = image_with(
        (0x100, bytes([0x48, 0x69, 0xC0]) + struct.pack("<I", 0x150) + bytes([0x48, 0x81, 0xC1]) + struct.pack("<I", 0x14DA4)),
        (0x140, bytes([0xF3, 0x0F, 0x10, 0x44, 0x01, 0x18, 0x90])))                                  # movss xmm0,[rcx+rax+18h]
    rows, _ = find(lib, image, ["48 69 C0 [u32] 48 81 C1 [u32]", "f3 0F 10 44 01 [u8] ?"])
    assert rows == [(1, 0x100, 0x150, 0x14DA4), (1, 0x140, 0x18, 0)]


def test_matches_are_counted_and_the_count_stops_at_two(lib):
    piece = bytes([0x48, 0x8B, 0x05, 1, 2, 3, 4, 0x90])
    image = image_with((0x40, piece), (0x80, piece), (0xC0, piece))
    rows, _ = find(lib, image, ["48 8B 05 [rip] 90", "48 8B 05 [rip] 91", "48 8B 05 ? ? ? ? [u8]"])
    assert [row[0] for row in rows] == [2, 0, 2]      # 알고 싶은 것은 "정확히 한 번인가"뿐이다
    assert rows[0][1] == 0x40                         # 처음 맞은 자리


def test_overlapping_matches_are_all_counted(lib):
    rows, _ = find(lib, image_with((0x40, bytes([0xAA, 0xAA, 0xAA, 0x01]))), ["AA AA [u8]"])
    assert rows[0][0] == 2


def test_a_match_must_lie_inside_the_range(lib):
    """서명이 구역의 끝이나 이미지의 끝에 걸치면 맞지 않은 것이다 — 범위 밖을 읽지 않는다."""
    piece = bytes([0x80, 0x3D, 0, 0, 0, 0, 0x00, 0x8B, 0xD8])
    sig = ["80 3D [rip+1] 00 8B D8"]
    image = image_with((0x40, piece))
    assert find(lib, image, sig, begin=0x40, end=0x49)[0][0][0] == 1
    assert find(lib, image, sig, begin=0x40, end=0x48)[0][0][0] == 0        # 끝이 구역 밖이다
    assert find(lib, image, sig, begin=0x41, end=0x100)[0][0][0] == 0       # 시작이 구역 밖이다
    assert find(lib, image, sig, begin=0, end=0x100000)[0][0][0] == 1       # 이미지보다 큰 구역은 이미지에서 잘린다
    at_the_end = image_with((0x400 - 9, piece))
    assert find(lib, at_the_end, sig, end=0x100000)[0][0][0] == 1           # 이미지의 마지막 바이트까지
    cut = image_with((0x400 - 5, piece[:5]))
    assert find(lib, cut, sig, end=0x100000)[0][0][0] == 0                  # 이미지의 끝에서 잘린 꼴


@pytest.mark.parametrize("text", ["", "? 48 [rip]", "48 8B 05", "48 [rip] [rip] [rip]", "48 8 [rip]", "48 [rop]", "48 [RIP]",
                                  " ".join(["90"] * 61) + " [rip]"],
                         ids=["empty", "hole-first", "nothing-to-read", "three-reads", "half-byte", "unknown-word", "upper-case-word",
                              "too-long"])
def test_a_signature_that_is_not_well_formed_is_refused(lib, text):
    rows, vote = find(lib, bytes(0x100), [text])
    assert rows == ["bad"] and vote[0] is False


A, B, C, OTHER, NOWHERE = "48 8B 05 [rip]", "48 8B 0D [rip]", "48 8B 15 [rip]", "48 8B 1D [rip]", "48 8B 3D [rip]"


def vote_image() -> bytes:
    """같은 곳(0x300)을 가리키는 서로 다른 꼴 셋(A · B · C)과, 다른 곳(0x308)을 가리키는 꼴 하나(OTHER)."""
    def mov(at: int, opcode: bytes, target: int) -> tuple[int, bytes]:
        return at, opcode + struct.pack("<i", target - (at + len(opcode) + 4))
    return image_with(mov(0x40, bytes([0x48, 0x8B, 0x05]), 0x300), mov(0x80, bytes([0x48, 0x8B, 0x0D]), 0x300),
                      mov(0xC0, bytes([0x48, 0x8B, 0x15]), 0x300), mov(0x100, bytes([0x48, 0x8B, 0x1D]), 0x308))


def test_the_vote_needs_two_signatures_that_agree(lib):
    image = vote_image()
    assert find(lib, image, [A, B, C])[1] == (True, 3, 0x300, 0)
    assert find(lib, image, [A, B, NOWHERE])[1] == (True, 2, 0x300, 0)        # 하나가 깨져도 된다
    assert find(lib, image, [A, NOWHERE, NOWHERE])[1][:2] == (False, 1)       # 하나만으로는 믿지 않는다
    assert find(lib, image, [A, B, OTHER])[1][:2] == (False, 3)               # 둘이 같아도 하나가 다른 값을 내면 못 찾은 것이다
    assert find(lib, image, [A, OTHER, NOWHERE])[1][:2] == (False, 2)


def test_a_signature_that_matches_twice_has_no_vote(lib):
    """두 번 맞는 서명은 어느 자리가 진짜인지 모른다 — 처음 맞은 자리의 값을 표로 치지 않는다."""
    image = image_with(*[(at, bytes([0x48, 0x8B, 0x05]) + struct.pack("<i", 0x300 - (at + 7))) for at in (0x40, 0x80)],
                       (0xC0, bytes([0x48, 0x8B, 0x0D]) + struct.pack("<i", 0x300 - 0xC7)))
    rows, vote = find(lib, image, [A, B, NOWHERE])
    assert rows[0][0] == 2 and vote[:2] == (False, 1)
```

- [ ] **Step 3: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox_sigs.py -q 2>&1 | tail -n 5`
Expected: 모든 테스트가 `AttributeError: function 'srtoybox_sig_find' not found` 로 ERROR (DLL 에 그 내보내기가 아직 없다). DLL 이 없어 건너뛰면 `uv run srkit toybox-build` 부터 한다.

- [ ] **Step 4: `sigs.h` 를 쓴다** — `native/srtoybox/sigs.h` (Write 도구로)

```cpp
// 서명: 게임의 코드에서 주소나 상수를 읽어 내는 짧은 바이트 꼴. 창도 게임도 PE 형식도 모르는 순수 함수다.
//
// 서명 글은 낱말을 빈칸으로 나눠 적는다:
//   48        정해진 바이트(16진수 두 자리)
//   ?         아무 바이트
//   [rip]     읽어 낼 주소: 4바이트 rip 상대 거리. 명령이 그 4바이트에서 끝난다
//   [rip+1]   〃 그 뒤에 상수 1바이트가 더 있고 명령이 끝난다 (cmp byte ptr [rip+d],0 같은 것)
//   [rip+4]   〃 상수 4바이트가 더 있다 (mov dword ptr [rip+d],2 같은 것)
//   [u32]     읽어 낼 상수 4바이트 (구조체 안의 자리, 간격)
//   [u8]      읽어 낼 상수 1바이트
// 첫 낱말은 정해진 바이트여야 하고, 읽어 낼 자리가 하나 이상 있어야 한다.
#pragma once

#include <cstddef>
#include <cstdint>

const int SIG_MAX = 64;         // 서명 하나의 최대 길이(바이트)
const int SIG_CAPTURES = 2;     // 서명 하나가 읽어 내는 값의 최대 개수

struct Sig {
    uint8_t bytes[SIG_MAX];
    bool any[SIG_MAX];          // 아무 바이트나 되는 자리(읽어 낼 자리도 여기에 든다)
    uint32_t length;
    int captures;
    struct Capture {
        uint32_t at;            // 서명 안에서의 자리
        uint32_t size;          // 1 또는 4
        bool rip;               // 4바이트 rip 상대 거리다 — 주소(RVA)로 푼다
        uint32_t tail;          // rip: 그 4바이트 뒤로 명령이 끝날 때까지의 바이트 수
    } capture[SIG_CAPTURES];
};

// 서명 글을 읽는다. 글이 틀리면 false.
bool sig_parse(const char *text, Sig *out);

struct SigRange {
    uint32_t begin, end;        // 훑을 곳 [begin, end) — image 안의 자리(RVA)
};

struct SigHit {
    int count;                          // 맞은 횟수. 2 에서 멈춘다 — 알고 싶은 것은 "정확히 한 번인가"뿐이다
    uint32_t at;                        // 처음 맞은 자리
    uint64_t value[SIG_CAPTURES];       // 그 자리에서 읽어 낸 값: 주소는 RVA, 상수는 그 값
};

// ranges 를 한 번 훑어 서명 n 개가 각각 몇 번 맞는지 센다. hits 는 n 칸.
void sig_scan(const uint8_t *image, size_t size, const SigRange *ranges, int range_count, const Sig *sigs, int n, SigHit *hits);

// 투표: 정확히 한 번 맞은 서명이 need 개 이상이고 그것들이 읽어 낸 값이 모두 같으면 true 와 value(SIG_CAPTURES 칸).
// matched 에 정확히 한 번 맞은 서명의 수. 값이 갈리면 false 다 — 틀린 주소를 내느니 못 찾은 것으로 친다.
bool sig_vote(const Sig *sigs, const SigHit *hits, int n, int need, uint64_t *value, int *matched);
```

- [ ] **Step 5: `sigs.cpp` 를 쓴다** — `native/srtoybox/sigs.cpp` (Write 도구로)

```cpp
#include "sigs.h"

#include <cstring>
#include <vector>

namespace {

int hex(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    c = static_cast<char>(c | 0x20);
    return c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
}

// 읽어 낼 자리의 낱말들. 긴 것이 먼저다("[rip+1]" 이 "[rip]" 보다).
const struct Word {
    const char *text;
    uint32_t size;
    bool rip;
    uint32_t tail;
} WORDS[] = {{"[rip+1]", 4, true, 1}, {"[rip+4]", 4, true, 4}, {"[rip]", 4, true, 0}, {"[u32]", 4, false, 0}, {"[u8]", 1, false, 0}};

uint64_t read(const uint8_t *image, uint64_t rva, const Sig::Capture &c)
{
    if (c.size == 1)
        return image[rva + c.at];
    uint32_t raw = 0;
    memcpy(&raw, image + rva + c.at, sizeof(raw));
    if (!c.rip)
        return raw;
    return static_cast<uint64_t>(static_cast<int64_t>(rva) + c.at + 4 + c.tail + static_cast<int32_t>(raw));
}

}  // namespace

bool sig_parse(const char *text, Sig *out)
{
    Sig s = {};
    if (text == nullptr || out == nullptr)
        return false;
    for (const char *c = text; *c != '\0'; ) {
        if (*c == ' ') {
            c++;
            continue;
        }
        const Word *word = nullptr;
        for (const Word &w : WORDS)
            if (strncmp(c, w.text, strlen(w.text)) == 0) {
                word = &w;
                break;
            }
        if (word != nullptr) {
            if (s.captures >= SIG_CAPTURES || s.length + word->size > SIG_MAX)
                return false;
            Sig::Capture &capture = s.capture[s.captures++];
            capture.at = s.length;
            capture.size = word->size;
            capture.rip = word->rip;
            capture.tail = word->tail;
            for (uint32_t i = 0; i < word->size; i++)
                s.any[s.length++] = true;
            c += strlen(word->text);
        } else if (*c == '?') {
            if (s.length >= SIG_MAX)
                return false;
            s.any[s.length++] = true;
            c++;
        } else {
            const int high = hex(c[0]), low = high < 0 ? -1 : hex(c[1]);
            if (low < 0 || s.length >= SIG_MAX)
                return false;
            s.bytes[s.length++] = static_cast<uint8_t>(high * 16 + low);
            c += 2;
        }
    }
    if (s.length == 0 || s.any[0] || s.captures == 0)
        return false;       // 첫 바이트로 후보를 거르므로 첫 낱말은 정해진 바이트여야 한다
    *out = s;
    return true;
}

void sig_scan(const uint8_t *image, size_t size, const SigRange *ranges, int range_count, const Sig *sigs, int n, SigHit *hits)
{
    if (n <= 0)
        return;
    // 첫 바이트가 같은 서명끼리 줄을 세운다 — 구역을 서명의 수만큼이 아니라 한 번만 훑는다
    int head[256];
    for (int &h : head)
        h = -1;
    std::vector<int> next(static_cast<size_t>(n), -1);
    for (int i = n - 1; i >= 0; i--) {
        hits[i] = SigHit();
        next[static_cast<size_t>(i)] = head[sigs[i].bytes[0]];
        head[sigs[i].bytes[0]] = i;
    }
    for (int r = 0; r < range_count; r++) {
        const uint64_t end = ranges[r].end < size ? ranges[r].end : size;
        for (uint64_t rva = ranges[r].begin; rva < end; rva++) {
            for (int i = head[image[rva]]; i >= 0; i = next[static_cast<size_t>(i)]) {
                const Sig &s = sigs[i];
                if (hits[i].count >= 2 || rva + s.length > end)
                    continue;
                uint32_t k = 1;
                while (k < s.length && (s.any[k] || image[rva + k] == s.bytes[k]))
                    k++;
                if (k < s.length)
                    continue;
                if (hits[i].count++ == 0) {
                    hits[i].at = static_cast<uint32_t>(rva);
                    for (int c = 0; c < s.captures; c++)
                        hits[i].value[c] = read(image, rva, s.capture[c]);
                }
            }
        }
    }
}

bool sig_vote(const Sig *sigs, const SigHit *hits, int n, int need, uint64_t *value, int *matched)
{
    int once = 0, first = -1;
    bool same = true;
    for (int i = 0; i < n; i++) {
        if (hits[i].count != 1)
            continue;
        once++;
        if (first < 0)
            first = i;
        else if (sigs[i].captures != sigs[first].captures
                 || memcmp(hits[i].value, hits[first].value, sizeof(uint64_t) * static_cast<size_t>(sigs[first].captures)) != 0)
            same = false;
    }
    if (matched != nullptr)
        *matched = once;
    if (once < need || !same)
        return false;
    for (int c = 0; c < sigs[first].captures; c++)
        value[c] = hits[first].value[c];
    return true;
}
```

- [ ] **Step 6: 내보내기를 더한다** — `native/srtoybox/exports.cpp`

머리의 `#include` 묶음에 두 줄을 더한다(`<cstring>` 위에 `<cstdio>`, `"settings.h"` 아래에 `"sigs.h"`):

```cpp
#include <cstdio>
```

```cpp
#include "sigs.h"
```

`srtoybox_prologue_length` 함수 바로 아래에 더한다:

```cpp
// 테스트: 서명 글들(줄바꿈으로 나눈다)을 image 의 [begin, end) 에서 맞춰 본다.
// 서명마다 한 줄 "<맞은 횟수> <처음 맞은 자리> <값0> <값1>"(16진수. 글이 틀리면 "bad"),
// 끝 줄은 투표 "vote <찾았는가 0/1> <한 번만 맞은 수> <값0> <값1>".
EXPORT int srtoybox_sig_find(const unsigned char *image, unsigned long long size, unsigned begin, unsigned end, const char *sigs,
                             int need, char *out, int out_size)
{
    std::vector<Sig> parsed;
    std::vector<int> where;      // 줄 → parsed 의 칸. 틀린 글이면 -1
    const std::string all = sigs == nullptr ? "" : sigs;
    for (size_t pos = 0; pos <= all.size(); ) {
        size_t stop = all.find('\n', pos);
        if (stop == std::string::npos)
            stop = all.size();
        Sig sig = {};
        if (sig_parse(all.substr(pos, stop - pos).c_str(), &sig)) {
            where.push_back(static_cast<int>(parsed.size()));
            parsed.push_back(sig);
        } else {
            where.push_back(-1);
        }
        pos = stop + 1;
    }
    std::vector<SigHit> hits(parsed.size());
    const SigRange range = {begin, end};
    if (image != nullptr && !parsed.empty())
        sig_scan(image, static_cast<size_t>(size), &range, 1, parsed.data(), static_cast<int>(parsed.size()), hits.data());
    std::string text;
    char line[96];
    for (int at : where) {
        if (at < 0) {
            text += "bad\n";
            continue;
        }
        const SigHit &hit = hits[static_cast<size_t>(at)];
        snprintf(line, sizeof(line), "%x %x %llx %llx\n", static_cast<unsigned>(hit.count), hit.at, hit.value[0], hit.value[1]);
        text += line;
    }
    uint64_t value[SIG_CAPTURES] = {};
    int matched = 0;
    const bool found = !parsed.empty()
        && sig_vote(parsed.data(), hits.data(), static_cast<int>(parsed.size()), need, value, &matched);
    snprintf(line, sizeof(line), "vote %d %d %llx %llx", found ? 1 : 0, matched, value[0], value[1]);
    return put(text + line, out, out_size);
}
```

- [ ] **Step 7: 빌드 목록에 더한다** — `src/srkit/toybox.py` 의 `SOURCES`

```python
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "game.cpp", "regions.cpp",
           "overlay.cpp"]
```

- [ ] **Step 8: 빌드하고 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_sigs.py -q 2>&1 | tail -n 3`
Expected: `빌드 완료: …\build\toybox\srtoybox.dll`, 이어서 `15 passed`

- [ ] **Step 9: 전체 테스트**

Run: `uv run pytest -q 2>&1 | tail -n 3`
Expected: `201 passed` (186 + 15). 실패가 있으면 이름을 적어 두고 고친다(Global Constraints 의 드문 실패 하나는 다시 돌려 본다).

- [ ] **Step 10: 커밋**

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/sigs.h native/srtoybox/sigs.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_sigs.py && git commit -q -F - <<'EOF'
feat: ToyBox — 서명으로 주소와 상수를 읽어 내는 순수 함수(sigs)

서명은 명령 몇 개의 바이트 꼴이다(주소 자리는 비운다). 실행 구역을 한 번 훑어
서명마다 맞은 횟수를 세고, 정확히 한 번 맞은 서명 둘 이상이 같은 값을 낼 때만
"찾았다"로 친다. 치트 문자열도 PE 형식도 모른다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 2: 서명 뽑기 (`srkit sig-mine`)

**브랜치:** `feat/toybox-sigs` (Task 1 에 이어서). 이 Task 가 끝나면 PR 을 올린다.

**Files:**
- Create: `src/srkit/sigmine.py`, `tests/test_sigmine.py`
- Modify: `pyproject.toml:15`, `uv.lock`(`uv sync` 가 고친다), `src/srkit/cli.py`, `tests/toybox_fake_exe.py`, `README.md`

**Interfaces:**
- Consumes: `srkit.toybox.image_of(exe: bytes) -> bytes`, `srkit.toybox.EXE_NAME`. 서명 글의 낱말(Task 1).
- Produces:
  - Python `srkit.sigmine.Image(image: bytes)` — `.data`, `.code: list[tuple[int, int]]`, `.root(rva) -> int | None`, `.extent(root) -> tuple[int, int]`, `.refs(target) -> list[int]`
  - Python `srkit.sigmine.regex(text, overlapping=True) -> re.Pattern[bytes]`, `srkit.sigmine.count(image, text, exact=True) -> int`
  - Python `srkit.sigmine.handler_range(image) -> tuple[int, int] | None`
  - Python `srkit.sigmine.Candidate(function, at, length, text)`, `srkit.sigmine.mine_address(image, target, *, exclude=None, fewest=3, most=8, fixed=8, longest=60, sites=400) -> list[Candidate]`, `srkit.sigmine.best_per_function(candidates) -> list[Candidate]`
  - Python `tests/toybox_fake_exe.py`: `shell(functions, size=SIZE) -> bytearray`, `put(image, rva, data) -> int`, `rip(image, rva, opcode, target, tail=b"") -> int`
  - CLI `uv run srkit sig-mine <RVA> [--limit N] [--sites N]`

- [ ] **Step 1: 개발 의존성을 더한다** — `pyproject.toml`

```toml
[dependency-groups]
dev = ["pytest>=8", "capstone>=5"]
```

Run: `uv sync 2>&1 | tail -n 3 && uv run python -c "import capstone; print(capstone.__version__)"`
Expected: `+ capstone==5.…` 한 줄과 버전 번호. `uv.lock` 이 바뀐다(커밋에 넣는다). 내려받기가 막혀 실패하면 멈추고 사용자에게 알린다.

- [ ] **Step 2: 가짜 이미지의 빈 틀을 더한다** — `tests/toybox_fake_exe.py`

`STRINGS = {…}` 줄 바로 아래(`def build` 위)에 더한다. `build()` 는 건드리지 않는다(Task 4 에서 이 틀 위로 옮긴다).

```python
def shell(functions: list[tuple[int, int]], size: int = SIZE) -> bytearray:
    """머리말 · 구역 표 · 함수 표만 있는 빈 이미지. functions: 함수 표에 넣을 [시작, 끝) 들(시작순)."""
    image = bytearray(size)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x98] = b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 4, 0, 0, 0, 0xF0, 0x22)
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<II", image, optional + 56, size, 0x400)                 # SizeOfImage, SizeOfHeaders
    struct.pack_into("<I", image, optional + 108, 16)                          # NumberOfRvaAndSizes
    struct.pack_into("<II", image, optional + 112 + 3 * 8, PDATA, 12 * len(functions))
    for i, (name, rva, flags) in enumerate([(b".text", TEXT, 0x60000020), (b".rdata", RDATA, 0x40000040),
                                            (b".pdata", PDATA, 0x40000040), (b".data", DATA, 0xC0000040)]):
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else 0x1000, rva,
                         0, 0, 0, 0, 0, 0, flags)
    unwind = RDATA + 0x800
    image[unwind:unwind + 4] = bytes([1, 0, 0, 0])                             # 풀기 정보: 뿌리(플래그 없음)
    for i, (begin, end) in enumerate(functions):
        struct.pack_into("<III", image, PDATA + 12 * i, begin, end, unwind)
    return image


def put(image: bytearray, rva: int, data: bytes) -> int:
    image[rva:rva + len(data)] = data
    return rva + len(data)


def rip(image: bytearray, rva: int, opcode: bytes, target: int, tail: bytes = b"") -> int:
    """RIP 상대 변위가 든 명령 하나: opcode + 변위(4) + tail. 변위는 명령의 끝을 기준으로 한다."""
    length = len(opcode) + 4 + len(tail)
    return put(image, rva, opcode + struct.pack("<i", target - (rva + length)) + tail)
```

- [ ] **Step 3: 실패하는 테스트를 쓴다** — `tests/test_sigmine.py` (Write 도구로)

```python
"""서명 뽑기(src/srkit/sigmine.py, 개발용): 주소를 가리키는 코드에서 한 번만 맞는 서명 후보를 찾는다."""
import argparse
import struct

import pytest

import toybox_fake_exe as fake
from srkit import cli, toybox

sigmine = pytest.importorskip("srkit.sigmine", reason="capstone 이 없다 (uv sync)")

G = fake.DATA + 0x40     # 가짜 전역


def code() -> bytes:
    """전역 G 를 쓰는 자리 다섯: A · B 는 뒤따르는 명령이 서로 다르고, C · D 는 똑같고, E 는 거리 뒤에 상수가 붙는 명령이다."""
    image = fake.shell([(0x1000, 0x1040), (0x1040, 0x1080), (0x1080, 0x10C0), (0x10C0, 0x1100), (0x1100, 0x1140)])
    end = fake.rip(image, 0x1000, bytes([0x48, 0x8B, 0x05]), G)             # A: mov rax,[G] / test rax,rax / je / mov ecx,[rax+10h] / ret
    fake.put(image, end, bytes([0x48, 0x85, 0xC0, 0x74, 0x10, 0x8B, 0x48, 0x10, 0xC3]))
    end = fake.rip(image, 0x1040, bytes([0x48, 0x8B, 0x05]), G)             # B: mov rax,[G] / mov eax,[rax+6Ch] / test eax,eax / jne / ret
    fake.put(image, end, bytes([0x8B, 0x40, 0x6C, 0x85, 0xC0, 0x75, 0x08, 0xC3]))
    for at in (0x1080, 0x10C0):                                             # C · D: mov rax,[G] / mov rcx,[rax] / test rcx,rcx / je / ret
        end = fake.rip(image, at, bytes([0x48, 0x8B, 0x05]), G)
        fake.put(image, end, bytes([0x48, 0x8B, 0x08, 0x48, 0x85, 0xC9, 0x74, 0x05, 0xC3]))
    end = fake.rip(image, 0x1100, bytes([0x83, 0x3D]), G, b"\x06")          # E: cmp dword ptr [G],6 / mov r15,rdx / mov r14,rcx / ret
    fake.put(image, end, bytes([0x4C, 0x8B, 0xFA, 0x4C, 0x8B, 0xF1, 0xC3]))
    return bytes(image)


@pytest.fixture(scope="module")
def image():
    return sigmine.Image(code())


def test_refs_find_every_instruction_that_points_at_the_address(image):
    assert image.refs(G) == [0x1003, 0x1043, 0x1083, 0x10C3, 0x1102]      # 4바이트 거리의 자리


def test_root_is_the_function_that_holds_the_place(image):
    assert image.root(0x1045) == 0x1040
    assert image.root(0x2F00) is None                                      # 함수 표에 없는 자리


def test_mining_gives_one_unique_signature_per_place_and_skips_ambiguous_places(image):
    found = {c.at: c for c in sigmine.mine_address(image, G)}
    assert {at: c.text for at, c in found.items()} == {
        0x1000: "48 8B 05 [rip] 48 85 C0 74 10",
        0x1040: "48 8B 05 [rip] 8B 40 6C 85 C0",
        0x1100: "83 3D [rip+1] 06 4C 8B FA 4C 8B F1"}       # C · D 는 똑같아서 어느 길이로도 한 번만 맞지 않는다
    assert {at: c.function for at, c in found.items()} == {0x1000: 0x1000, 0x1040: 0x1040, 0x1100: 0x1100}
    assert all(sigmine.count(image, c.text) == 1 for c in found.values())


def test_mining_skips_the_excluded_range(image):
    """치트 명령 처리 함수의 코드에서는 서명을 뽑지 않는다."""
    assert [c.at for c in sigmine.mine_address(image, G, exclude=(0x1000, 0x1040))] == [0x1040, 0x1100]


def test_count_agrees_with_the_dll_about_overlapping_matches():
    overlap = fake.shell([(0x1000, 0x1040)])
    fake.put(overlap, 0x1000, bytes([0xAA, 0xAA, 0xAA, 0x01]))
    image = sigmine.Image(bytes(overlap))
    assert sigmine.count(image, "AA AA [u8]") == 2                         # DLL 처럼 겹친 것까지 센다
    assert sigmine.count(image, "AA AA [u8]", exact=False) == 1            # 빠른 어림(뽑는 동안 먼저 거르는 데 쓴다)


def test_best_per_function_keeps_the_shortest_of_each_function():
    Candidate = sigmine.Candidate
    picks = sigmine.best_per_function([Candidate(0x1000, 0x1010, 30, "long"), Candidate(0x1000, 0x1000, 12, "short"),
                                       Candidate(0x1040, 0x1040, 12, "other"), Candidate(None, 0x2000, 5, "loose"),
                                       Candidate(None, 0x2100, 5, "loose too")])
    assert [(c.function, c.at) for c in picks] == [(None, 0x2000), (None, 0x2100), (0x1000, 0x1000), (0x1040, 0x1040)]


def test_handler_range_comes_from_the_cheat_anchor(image):
    assert sigmine.handler_range(image) is None                            # 치트가 없는 빌드
    anchored = fake.shell([(0x1000, 0x1040), (0x1040, 0x1100)])
    fake.put(anchored, fake.RDATA + 0x10, b"\0cheat allowcheats\0")
    fake.rip(anchored, 0x1050, bytes([0x48, 0x8D, 0x15]), fake.RDATA + 0x11)     # lea rdx,["cheat allowcheats"]
    assert sigmine.handler_range(sigmine.Image(bytes(anchored))) == (0x1040, 0x1100)


def installed(game_dir) -> bytes:
    exe = (game_dir / toybox.EXE_NAME).read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    if stamp != 0x695377B6:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x})")
    return toybox.image_of(exe)


def test_mining_the_installed_game_stays_out_of_the_cheat_handler(cfg, game_dir):
    """build 21347933: 플레이어 포인터를 쓰는 코드에서, 치트 명령 처리 함수 밖의 서로 다른 함수 셋 이상에서 후보가 나온다."""
    image = sigmine.Image(installed(game_dir))
    handler = sigmine.handler_range(image)
    assert handler == (0x522330, 0x5284FD)
    picks = sigmine.best_per_function(sigmine.mine_address(image, 0x18295F8, exclude=handler, sites=40))
    assert len(picks) >= 3
    assert all(sigmine.count(image, c.text) == 1 and not handler[0] <= c.at < handler[1] for c in picks)


def test_srkit_sig_mine_prints_candidates(cfg, game_dir, capsys):
    installed(game_dir)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(address="18295f8", limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert out.count("[rip") == 3 and "0x522330" in out                    # 후보 셋, 그리고 뺀 치트 함수의 범위
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -n 3`
Expected: `1 skipped` — `srkit.sigmine` 이 아직 없어 파일 전체가 건너뛰어진다(`importorskip`). 모듈을 쓴 뒤에 진짜로 돈다.

- [ ] **Step 5: `sigmine.py` 를 쓴다** — `src/srkit/sigmine.py` (Write 도구로)

```python
"""서명 뽑기(개발용): 게임의 코드에서 주소를 읽어 낼 서명 후보를 찾는다. 설치된 실행 파일을 읽기만 한다.

ToyBox 는 게임이 뜰 때 서명(native/srtoybox/sigs.h)으로 주소를 찾는다. 서명은 내장 치트와 무관한 코드에서 뽑아야 하고
(docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md 의 요구 3), 실행 구역 전체에서 정확히 한 번 맞아야 한다.
이 모듈은 그런 후보를 찾아 줄 뿐이다 — 서명 표(native/srtoybox/locate.cpp)에는 사람이 골라 옮긴다.

디스어셈블러 capstone 을 쓴다(개발 의존성). 게임 안에서 도는 DLL 과 srkit 의 다른 명령은 쓰지 않는다.
"""
from __future__ import annotations

import bisect
import re
import struct
from dataclasses import dataclass

import capstone
import numpy as np
from capstone import x86_const as X

# 서명 글의 낱말(native/srtoybox/sigs.h 와 같다)
TOKEN = re.compile(r"\[rip(?:\+([14]))?\]|\[u(?:8|32)\]|\?|[0-9A-Fa-f]{2}")
ANCHOR = b"cheat allowcheats\0"      # 치트 명령 처리 함수를 가려내는 데만 쓴다(그 함수의 코드에서는 서명을 뽑지 않는다)


class Image:
    """RVA 대로 펼친 실행 파일(srkit.toybox.image_of 의 결과): 실행 구역과 함수 표."""

    def __init__(self, image: bytes):
        self.data = image
        pe = struct.unpack_from("<I", image, 0x3C)[0]
        count, optional_size = struct.unpack_from("<H", image, pe + 6)[0], struct.unpack_from("<H", image, pe + 20)[0]
        optional = pe + 24
        self.code: list[tuple[int, int]] = []          # 실행 구역 [시작, 끝)
        for i in range(count):
            _name, size, rva, _rs, _raw, _a, _b, _c, _d, flags = struct.unpack_from(
                "<8sIIIIIIHHI", image, optional + optional_size + 40 * i)
            if flags & 0x20000000 and size:            # IMAGE_SCN_MEM_EXECUTE
                self.code.append((rva, rva + size))
        pdata, pdata_size = struct.unpack_from("<II", image, optional + 112 + 3 * 8)
        self.funcs = [struct.unpack_from("<III", image, pdata + 12 * i) for i in range(pdata_size // 12)]
        self._starts = [f[0] for f in self.funcs]

    def _root_of(self, begin: int, unwind: int) -> int | None:
        for _ in range(32):                            # chained unwind 를 뿌리까지
            if not (self.data[unwind] >> 3) & 4:
                return begin
            parent = unwind + 4 + 2 * ((self.data[unwind + 2] + 1) & ~1)
            begin, _end, unwind = struct.unpack_from("<III", self.data, parent)
        return None

    def root(self, rva: int) -> int | None:
        """rva 가 든 함수의 시작. 함수 표에 없으면 None."""
        i = bisect.bisect_right(self._starts, rva) - 1
        if i < 0 or not (self.funcs[i][0] <= rva < self.funcs[i][1]):
            return None
        return self._root_of(self.funcs[i][0], self.funcs[i][2])

    def extent(self, root: int) -> tuple[int, int]:
        """그 함수의 모든 조각을 덮는 [시작, 끝)."""
        parts = [(begin, end) for begin, end, unwind in self.funcs if self._root_of(begin, unwind) == root]
        return min(b for b, _ in parts), max(e for _, e in parts)

    def refs(self, target: int) -> list[int]:
        """target 을 rip 상대로 가리키는 4바이트 거리의 자리들(그 뒤에 상수 0 · 1 · 4바이트가 붙는 명령)."""
        out: set[int] = set()
        for lo, hi in self.code:
            b = np.frombuffer(self.data, dtype=np.uint8)[lo:hi].astype(np.uint32)
            if len(b) < 4:
                continue
            disp = (b[:-3] | (b[1:-2] << 8) | (b[2:-1] << 16) | (b[3:] << 24)).astype(np.int32).astype(np.int64)
            after = lo + np.arange(len(disp), dtype=np.int64) + 4 + disp
            for tail in (0, 1, 4):
                out.update(int(lo + i) for i in np.nonzero(after + tail == target)[0])
        return sorted(out)


def regex(text: str, overlapping: bool = True) -> re.Pattern[bytes]:
    """서명 글 → 정규식. overlapping 이면 겹쳐 맞는 것까지 센다(DLL 의 세는 법과 같다. 느리다)."""
    out = b""
    for m in TOKEN.finditer(text):
        token = m.group(0)
        if token == "?" or token == "[u8]":
            out += b"."
        elif token.startswith("["):
            out += b"...."
        else:
            out += re.escape(bytes([int(token, 16)]))
    return re.compile(b"(?=" + out + b")" if overlapping else out, re.S)


def count(image: Image, text: str, exact: bool = True) -> int:
    """실행 구역에서 서명이 맞는 횟수."""
    pattern = regex(text, overlapping=exact)
    return sum(1 for lo, hi in image.code for _ in pattern.finditer(image.data, lo, hi))


def handler_range(image: Image) -> tuple[int, int] | None:
    """치트 명령 처리 함수의 [시작, 끝). 치트가 없는 빌드면 None.

    치트 코드를 "보는" 곳이지만 DLL 밖이다: 여기서 뽑는 서명이 그 함수의 코드가 아님을 가리는 데만 쓴다.
    """
    at = image.data.find(b"\0" + ANCHOR)
    if at < 0:
        return None
    string = at + 1
    for lo, hi in image.code:
        for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", image.data[lo:hi]):
            use = lo + m.start()
            if use + 7 + struct.unpack_from("<i", image.data, use + 3)[0] == string:
                root = image.root(use)
                return image.extent(root) if root is not None else None
    return None


@dataclass
class Candidate:
    function: int | None     # 서명이 든 함수의 시작(함수 표에 없으면 None)
    at: int                  # 서명이 맞는 자리
    length: int              # 바이트 수
    text: str                # 서명 글


_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_md.detail = True


def _first_instruction(image: Image, pos: int, target: int):
    """4바이트 rip 상대 거리가 pos 에 있고 target 을 가리키는 명령."""
    for back in (3, 4, 5, 2, 6, 7, 1):                 # 흔한 꼴부터: REX + 연산 + ModRM, 0F 가 낀 것, 접두 없는 것
        start = pos - back
        ins = next(_md.disasm(image.data[start:start + 16], start), None)
        if ins is None or ins.disp_size != 4 or start + ins.disp_offset != pos:
            continue
        if any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP and ins.address + ins.size + op.mem.disp == target
               for op in ins.operands):
            return ins
    return None


def _words(ins, first: bool) -> list[str] | None:
    """명령 하나의 서명 글. 첫 명령의 rip 상대 거리는 읽어 낼 자리, 그 밖의 rip 상대 거리와 call · jmp 의 4바이트 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    rip = ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    if first:
        tail = ins.size - (ins.disp_offset + 4)
        if tail not in (0, 1, 4):
            return None
        out[ins.disp_offset:ins.disp_offset + 4] = ["[rip]" if tail == 0 else f"[rip+{tail}]"]
    elif rip:
        out[ins.disp_offset:ins.disp_offset + 4] = ["?"] * 4
    elif (ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands \
            and ins.operands[0].type == X.X86_OP_IMM:
        out[ins.size - 4:] = ["?"] * 4
    return out


def mine_address(image: Image, target: int, *, exclude: tuple[int, int] | None = None, fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400) -> list[Candidate]:
    """target 을 가리키는 명령에서 시작해 실행 구역 전체에서 한 번만 맞는 가장 짧은 서명을, 쓰는 자리마다 하나씩.

    exclude 안의 자리는 보지 않는다(치트 명령 처리 함수). 명령 fewest 개 · 정해진 바이트 fixed 개 이상이어야 서명으로 친다.
    쓰는 자리가 sites 보다 많으면 고르게 골라 그만큼만 본다.
    """
    found: list[Candidate] = []
    places = [p for p in image.refs(target) if not (exclude and exclude[0] <= p < exclude[1])]
    for pos in places[::max(1, len(places) // sites)]:
        first = _first_instruction(image, pos, target)
        if first is None:
            continue
        words: list[str] = []
        length = 0
        for n, ins in enumerate(_md.disasm(image.data[first.address:first.address + 160], first.address), start=1):
            more = _words(ins, first=n == 1)
            if more is None or length + ins.size > longest:
                break
            words += more
            length += ins.size
            text = " ".join(words)
            if n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                found.append(Candidate(image.root(first.address), first.address, length, text))
                break
            if n >= most or ins.id in (X.X86_INS_RET, X.X86_INS_INT3, X.X86_INS_JMP):
                break
    return found


def best_per_function(candidates: list[Candidate]) -> list[Candidate]:
    """함수마다 가장 짧은 것 하나. 짧은 것부터(같으면 앞의 것부터)."""
    best: dict[int, Candidate] = {}
    for c in candidates:
        key = c.function if c.function is not None else -c.at      # 함수 표에 없는 자리는 저마다 다른 함수로 친다
        if key not in best or (c.length, c.at) < (best[key].length, best[key].at):
            best[key] = c
    return sorted(best.values(), key=lambda c: (c.length, c.at))
```

- [ ] **Step 6: 명령을 더한다** — `src/srkit/cli.py`

`cmd_locate` 함수 바로 아래에 더한다:

```python
def cmd_sig_mine(cfg, args) -> int:
    from . import sigmine      # capstone 은 개발 의존성이다 — 이 명령에서만 불러온다

    exe = cfg.game_dir / toybox.EXE_NAME
    image = sigmine.Image(toybox.image_of(exe.read_bytes()))
    target = int(args.address, 16)
    handler = sigmine.handler_range(image)
    picks = sigmine.best_per_function(sigmine.mine_address(image, target, exclude=handler, sites=args.sites))
    left_out = f"치트 명령 처리 함수 {handler[0]:#x} – {handler[1]:#x} 는 뺐다" if handler else "치트 명령 처리 함수가 없는 빌드다"
    print(f"{exe.name}: {target:#x} 를 가리키는 코드에서 ({left_out})")
    for c in picks[:args.limit]:
        function = f"{c.function:#x}" if c.function is not None else "표에 없음"
        print(f"  자리 {c.at:#010x}  함수 {function:>10}  {c.length:>2}바이트  {c.text}")
    print(f"서로 다른 함수 {len(picks)}개에서 후보가 나왔습니다. 서명 표에는 서로 다른 함수의 것 셋을 골라 옮깁니다.")
    return 0 if len(picks) >= 3 else 1
```

`main()` 의 `sub.add_parser("locate", …)` 두 줄 바로 아래에 더한다:

```python
    m = sub.add_parser("sig-mine", help="(개발용) 설치된 게임에서 그 주소를 읽어 낼 서명 후보 뽑기 — 치트 함수 밖의 코드에서")
    m.add_argument("address", help="주소(RVA, 16진수. 예: 18295f8)")
    m.add_argument("--limit", type=int, default=12, help="보여 줄 후보의 수")
    m.add_argument("--sites", type=int, default=400, help="살펴볼 자리의 수(많으면 오래 걸린다)")
    m.set_defaults(fn=cmd_sig_mine)
```

- [ ] **Step 7: 테스트가 통과하는 것을 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -n 3`
Expected: `9 passed` (게임 설치본이 없으면 뒤의 둘이 건너뛰어져 `7 passed, 2 skipped`)

- [ ] **Step 8: 명령을 직접 돌려 본다**

Run: `uv run srkit sig-mine 18295f8 --limit 5 --sites 60`
Expected: 첫 줄에 `치트 명령 처리 함수 0x522330 – 0x5284fd 는 뺐다`, 이어서 `[rip]` 가 든 후보 다섯 줄(모두 12바이트 안팎), 끝 줄에 `서로 다른 함수 …개에서 후보가 나왔습니다`.

- [ ] **Step 9: README 에 명령을 적는다** — `README.md`

"빠른 시작"의 `uv run srkit locate …` 줄 아래에 한 줄:

```
uv run srkit sig-mine <RVA>          # (개발용) ToyBox 가 주소를 찾는 서명의 후보 뽑기 — 치트 함수 밖의 코드에서
```

"구조"의 `toybox.py      ToyBox DLL 빌드` 줄 아래에 한 줄:

```
  sigmine.py     ToyBox 의 서명 후보 뽑기 (개발용. 디스어셈블러 capstone)
```

- [ ] **Step 10: 전체 테스트, 커밋, PR**

Run: `uv run pytest -q 2>&1 | tail -n 3`
Expected: `210 passed` (201 + 9)

```bash
cd /e/SR2030ToyBox && git add pyproject.toml uv.lock src/srkit/sigmine.py src/srkit/cli.py tests/test_sigmine.py tests/toybox_fake_exe.py README.md && git commit -q -F - <<'EOF'
feat: srkit sig-mine — ToyBox 의 서명 후보를 치트 함수 밖의 코드에서 뽑는다

주소를 가리키는 명령에서 시작해 실행 구역 전체에서 한 번만 맞는 가장 짧은 서명을
자리마다 찾는다(명령 셋 · 정해진 바이트 여덟 개 이상). 치트 명령 처리 함수의
범위는 빼고 본다. 개발용이다 — 디스어셈블러 capstone 을 개발 의존성으로 더했다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin feat/toybox-sigs
```

PR 본문(스크래치에 Write 도구로 `pr-sigs.md`): 무엇을 더했나(서명 맞추기 `sigs`, `srkit sig-mine`, 개발 의존성 capstone), 왜(설계서의 요구 3 — 주소 찾기를 치트에서 떼기 위한 기반. 이 PR 은 아직 ToyBox 의 동작을 바꾸지 않는다), `uv run pytest` 결과(통과 수와 실패한 테스트의 이름), 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-sigs --title "feat: ToyBox — 서명으로 주소를 읽는 순수 함수와 서명 뽑기(srkit sig-mine)" --body-file "<스크래치>/pr-sigs.md"
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge
```

머지가 거부되면 Global Constraints 대로 한다. 머지된 뒤: `git switch develop && git pull --ff-only origin develop`

---

### Task 3: 새 찾기 — 상태 전역 일곱 (`locate_state`)

**브랜치:** `feat/toybox-locate-independent` (`develop` 에서. Task 2 의 PR 이 들어간 뒤)

이 Task 는 새 찾기를 **더하기만** 한다. 게임 안에서 도는 ToyBox 는 아직 옛 찾기(`locate_game`)를 쓴다 — 바꾸는 것은 Task 4 다.

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`
- Modify: `tests/toybox_fake_exe.py`, `tests/test_toybox_game.py`
- Create: `tests/toybox_cheat_oracle.py`

**Interfaces:**
- Consumes: `sig_parse` · `sig_scan` · `sig_vote` · `Sig` · `SigHit` · `SigRange` · `SIG_CAPTURES`(Task 1), `srkit.sigmine.Image` · `handler_range`(Task 2), `tests/toybox_fake_exe.shell`(Task 2).
- Produces:
  - C++ 상수 `STATE_WANTED = 7`, `STATE_SIGS = 3`, `STATE_NEED = 2`
  - C++ `struct SigRow { const char *name; const char *text; int count; uint32_t at; uint32_t value; };`
  - C++ `bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size);` — 찾으면 `true` 와 `out` 의 일곱 필드(`multiplayer` `program_state` `mode_state` `player_index` `player_pointer` `region_table` `region_count`). `handler` · `context` · `options` 는 건드리지 않는다. `rows` 는 `STATE_WANTED * STATE_SIGS` 칸 또는 `nullptr`. `why` 는 `nullptr` 이면 안 된다.
  - C++ `uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);`
  - 내보내기 `int srtoybox_locate_state(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size, char *rows, int rows_size)`, `unsigned srtoybox_function_root(const unsigned char *image, unsigned long long size, unsigned rva)`
  - Python `srkit.toybox.STATE_FIELDS: list[str]`, `srkit.toybox.SigRow(name, text, count, at, value)`, `srkit.toybox.state_of(lib, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]`
  - Python `tests/toybox_fake_exe.py`: `STATE: dict[str, int]`, `PLANT`, `plant(image, at, text, target) -> int`, `state_image(sigs, *, broken=(), twice=(), stray=(), targets=None, into=None) -> bytes`
  - Python `tests/toybox_cheat_oracle.py`: `handler(image: bytes) -> tuple[int, int]`, `state(image: bytes) -> dict[str, int]`

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-locate-independent
```

- [ ] **Step 2: 가짜 이미지에 서명을 심는 도구를 더한다** — `tests/toybox_fake_exe.py`

파일 머리의 `import struct` 를 두 줄로 바꾼다:

```python
import re
import struct
```

`rip()` 함수 아래(`def build` 위)에 더한다:

```python
# 새 찾기(상태 묶음)의 가짜 주소. 지역 표(8바이트 × 1024칸)는 WORLD + 0x80 부터다
STATE = {"multiplayer": DATA, "program_state": DATA + 8, "mode_state": DATA + 12, "player_index": DATA + 16,
         "player_pointer": DATA + 24, "region_table": WORLD + 0x80, "region_count": DATA + 20}
PLANT, AGAIN = TEXT + 0x1000, TEXT + 0x1800     # 서명을 심는 곳, 같은 서명을 한 번 더 심는 곳
TOKEN = re.compile(r"\[rip(?:\+([14]))?\]|\[u(?:8|32)\]|\?|[0-9A-Fa-f]{2}")   # 서명 글의 낱말(native/srtoybox/sigs.h)


def plant(image: bytearray, at: int, text: str, target: int) -> int:
    """서명 글 하나를 at 에 심는다: 정해진 바이트는 그대로, 구멍은 건드리지 않고, 읽어 낼 자리는 target 이 나오게. 끝 자리를 돌려준다."""
    pos = at
    for m in TOKEN.finditer(text):
        word = m.group(0)
        if word.startswith("[rip"):
            struct.pack_into("<i", image, pos, target - (pos + 4 + int(m.group(1) or 0)))
            pos += 4
        elif word == "[u32]":
            struct.pack_into("<I", image, pos, target)
            pos += 4
        elif word == "[u8]":
            image[pos] = target
            pos += 1
        elif word == "?":
            pos += 1
        else:
            image[pos] = int(word, 16)
            pos += 1
    return pos


def shape(text: str) -> str:
    """읽어 낼 자리를 구멍으로 바꾼 글. 꼴이 같은 서명들은 게임에서 같은 자리의 명령을 읽는다
    (프로그램 상태와 모드 상태가 게임 진입의 두 mov 에서 하나씩 읽는다) — 한 곳에만 심어야 저마다 한 번씩 맞는다."""
    return " ".join("? ? ? ?" if w.startswith("[rip") or w == "[u32]" else "?" if w in ("?", "[u8]") else w.upper()
                    for w in (m.group(0) for m in TOKEN.finditer(text)))


def state_image(sigs: list[tuple[str, str]], *, broken=(), twice=(), stray=(), targets: dict[str, int] | None = None,
                into: bytearray | None = None) -> bytes:
    """DLL 의 서명 표(sigs: [(찾을 것, 서명 글)])를 심은 이미지. 치트 문자열은 하나도 없다.

    broken · twice · stray 는 sigs 의 칸 번호들이다: 심지 않는다 / 한 번 더 심는다(두 번 맞는다) / 8바이트 옆을 가리키게 심는다.
    targets 로 가짜 주소를 바꾼다. into 를 주면 그 이미지에 심는다(없으면 빈 틀).
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = dict(STATE, **(targets or {}))
    places: dict[str, int] = {}
    for i, (name, text) in enumerate(sigs):
        if i in broken:
            continue
        place = places.setdefault(shape(text), PLANT + 0x40 * len(places))
        plant(image, place, text, at[name] + (8 if i in stray else 0))
        if i in twice:
            plant(image, AGAIN + 0x40 * i, text, at[name])
    return bytes(image)
```

- [ ] **Step 3: 대조용 읽기를 쓴다** — `tests/toybox_cheat_oracle.py` (Write 도구로)

```python
"""자동 테스트의 대조용: 2단계가 쓰던 방식(치트 문자열을 닻으로)으로 실행 파일의 이미지에서 상태 전역의 주소를 읽는다.

게임 안에서 도는 DLL 은 이 방식을 쓰지 않는다(docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md 의 요구 3).
치트 코드가 남아 있는 빌드에서 "새 찾기(서명)가 낸 값이 치트 코드에서 읽은 값과 같은가"를 보는 데만 쓴다.
pytest 가 직접 모으는 테스트 파일이 아니다(tests/test_toybox_game.py 가 쓴다).
"""
import re
import struct

from srkit import sigmine

LEA = rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]"     # lea r64,[rip+d]


def _target(data: bytes, at: int, disp: int, length: int) -> int:
    """rip 상대 주소가 든 명령이 가리키는 곳. at: 명령의 시작, disp: 변위의 자리, length: 명령의 길이."""
    return at + length + struct.unpack_from("<i", data, at + disp)[0]


def _uses(image: sigmine.Image, text: str) -> list[int]:
    """그 치트 문자열을 가리키는 lea 의 자리들."""
    string = image.data.find(b"\0" + text.encode() + b"\0") + 1
    assert string > 0, text
    return [lo + m.start() for lo, hi in image.code for m in re.finditer(LEA, image.data[lo:hi])
            if _target(image.data, lo + m.start(), 3, 7) == string]


def _after(image: sigmine.Image, text: str, span: int, pattern: bytes) -> int:
    """그 치트 문자열을 쓰는 자리 뒤 span 바이트 안에서 pattern(정규식)이 처음 맞는 자리."""
    for use in _uses(image, text):
        m = re.search(pattern, image.data[use:use + span], re.S)
        if m:
            return use + m.start()
    raise AssertionError(f"{text}: 서명이 맞지 않는다")


def handler(image_bytes: bytes) -> tuple[int, int]:
    """치트 명령 처리 함수의 [시작, 끝)."""
    found = sigmine.handler_range(sigmine.Image(image_bytes))
    assert found is not None, "치트 문자열이 없는 이미지다"
    return found


def state(image_bytes: bytes) -> dict[str, int]:
    """상태 전역 일곱의 RVA — 치트 코드에서 읽은 것."""
    image = sigmine.Image(image_bytes)
    data = image.data
    begin, _end = handler(image_bytes)
    out = {}
    at = begin + re.search(rb"\x80\x3d....\x00", data[begin:begin + 0x60], re.S).start()        # cmp byte ptr [멀티플레이],0
    out["multiplayer"] = _target(data, at, 2, 7)
    at = _after(image, "cheat georgew", 0x40, rb"\x48\x8b\x05....\xf2\x0f\x10\x80")              # mov rax,[플레이어 포인터]
    out["player_pointer"] = _target(data, at, 3, 7)
    at = _after(image, "cheat populate", 0x40, rb"\x48\x63\x05....\x4c\x8d\x3d....")             # movsxd rax,[인덱스] / lea r15,[월드]
    out["player_index"] = _target(data, at, 3, 7)
    world = _target(data, at + 7, 3, 7)
    m = re.search(rb"\x49\x8b\x8c\xc7", data[at:at + 0x40])                                     # mov rcx,[r15+rax*8+지역 표]
    out["region_table"] = world + struct.unpack_from("<I", data, at + m.start() + 4)[0]
    at = _after(image, "cheat becomeregion", 0x190,
                rb"\x44\x8b\x0d....\x45\x33\xf6\x45\x85\xc9\x0f\x88....\x48\x8d\x0d....")       # mov r9d,[지역 수] … lea rcx,[지역 표]
    out["region_count"] = _target(data, at, 3, 7)
    calls = [lo + m.start() for lo, hi in image.code for m in re.finditer(rb"\xe8", data[lo:hi])
             if _target(data, lo + m.start(), 1, 5) == begin]
    assert len(calls) == 1                                                                      # 명령 처리 함수를 부르는 곳
    caller = image.root(calls[0])
    at = caller + re.search(rb"\x83\x3d....\x06", data[caller:caller + 0x40], re.S).start()     # cmp dword ptr [프로그램 상태],6
    out["program_state"] = _target(data, at, 2, 7)
    enter = [lo + m.start() for lo, hi in image.code
             for m in re.finditer(rb"\xc7\x05....\x02\x00\x00\x00\xc7\x05....\x01\x00\x00\x00", data[lo:hi], re.S)]
    assert len(enter) == 1                                                                      # mov [모드 상태],2 / mov [프로그램 상태],1
    out["mode_state"] = _target(data, enter[0], 2, 10)
    return out
```

- [ ] **Step 4: Python 쪽의 읽는 함수를 더한다** — `src/srkit/toybox.py`

`import` 묶음의 `from pathlib import Path` 줄 바로 위에 `from dataclasses import dataclass` 를 더한다.

`ADDRESS_NAMES = {…}` 아래에 더한다:

```python
# 새 찾기(서명)가 채우는 일곱 — native/srtoybox/locate.cpp 의 표 STATE 와 같은 순서다
STATE_FIELDS = ["multiplayer", "program_state", "mode_state", "player_index", "player_pointer", "region_table", "region_count"]


@dataclass
class SigRow:
    """서명 하나의 결과."""
    name: str       # 찾을 것(GameAddresses 의 필드 이름)
    text: str       # 서명 글
    count: int      # 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    at: int         # 처음 맞은 자리
    value: int      # 거기서 읽어 낸 주소
```

`library()` 의 `return lib` 위에 더한다:

```python
    lib.srtoybox_locate_state.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_function_root.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint]
    lib.srtoybox_function_root.restype = ctypes.c_uint
```

`image_of()` 아래에 더한다:

```python
def state_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(상태 묶음)를 그 이미지에 돌린다: (이름 → RVA 또는 None, 까닭, 서명마다의 결과)."""
    found, error, rows = GameAddresses(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_state(image, len(image), ctypes.byref(found), error, len(error), rows, len(rows)) == 0
    table = [SigRow(name, text, int(count, 16), int(at, 16), int(value, 16))
             for name, text, count, at, value in (line.split("\t") for line in rows.value.decode("utf-8").splitlines())]
    return ({name: getattr(found, name) for name in STATE_FIELDS} if ok else None), error.value.decode("utf-8"), table
```

- [ ] **Step 5: 실패하는 테스트를 쓴다** — `tests/test_toybox_game.py`

`BUILD_21347933_STAMP = 0x695377B6` 줄 아래에 더한다:

```python
BUILD_STATE = {name: BUILD_21347933[name] for name in toybox.STATE_FIELDS}
GARBAGE = [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)]
GARBAGE_IDS = ["empty", "two-bytes", "zeros", "header-far-outside"]
```

`test_srkit_locate_reports_the_addresses` 함수 아래(`def state(lib, fake…` 위)에 더한다:

```python
@pytest.fixture(scope="module")
def sigs(lib):
    """DLL 에 든 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.state_of(lib, b"")[2]]


def installed_image(game_dir) -> bytes:
    """설치된 게임의 실행 파일을 펼친 것. 아는 빌드(21347933)가 아니면 건너뛴다."""
    exe = (game_dir / "SupremeRuler2030.exe").read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
    if stamp != BUILD_21347933_STAMP:
        pytest.skip(f"다른 빌드(TimeDateStamp {stamp:#x})")
    return toybox.image_of(exe)


def test_the_signature_table_has_three_signatures_per_address(sigs):
    assert [name for name, _ in sigs] == [name for name in toybox.STATE_FIELDS for _ in range(3)]
    assert len({text for _, text in sigs}) == 21


def test_state_is_found_in_an_image_without_any_cheat_string(lib, sigs):
    """새 찾기는 치트 문자열에 기대지 않는다 — 게임이 치트를 없애도 상태를 읽는다."""
    image = toybox_fake_exe.state_image(sigs)
    assert b"cheat" not in image
    found, why, rows = toybox.state_of(lib, image)
    assert found == toybox_fake_exe.STATE, why
    assert [row.count for row in rows] == [1] * 21


@pytest.mark.parametrize("which", range(7))
def test_state_survives_one_broken_signature_per_address(lib, sigs, which):
    """업데이트로 서명 하나가 깨져도 나머지 둘이 같은 주소를 내면 찾은 것이다."""
    found, why, rows = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, broken={3 * which}))
    assert found == toybox_fake_exe.STATE, why
    assert rows[3 * which].count == 0


def test_state_is_not_found_when_two_signatures_of_one_address_break(lib, sigs):
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, broken={0, 1}))
    assert found is None and "멀티플레이 표시" in why and "3개 가운데 1개" in why


def test_a_signature_that_matches_twice_does_not_count(lib, sigs):
    found, why, rows = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, twice={0}))
    assert found == toybox_fake_exe.STATE and rows[0].count == 2, why        # 나머지 둘로 찾는다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, twice={0}, broken={1}))
    assert found is None and "3개 가운데 1개" in why                          # 두 번 맞은 것은 표가 아니다


def test_signatures_that_disagree_are_refused(lib, sigs):
    """셋이 모두 맞았는데 하나가 다른 주소를 낸다 — 다수결로 고르지 않고 못 찾은 것으로 친다."""
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, stray={12}))
    assert found is None and "플레이어 포인터" in why and "서로 다른 주소" in why


def test_a_state_address_outside_the_image_is_refused(lib, sigs):
    targets = {"region_table": toybox_fake_exe.SIZE - 0x100}      # 지역 표(8바이트 × 1024칸)가 이미지의 끝을 넘는다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.state_image(sigs, targets=targets))
    assert found is None and "지역 표" in why and "실행 파일 밖" in why


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_state_survives_garbage(lib, image):
    found, why, _ = toybox.state_of(lib, image)
    assert found is None and why


def test_state_survives_an_image_with_a_page_it_cannot_read(lib, sigs):
    """올라와 있는 실행 파일에 읽을 수 없는 쪽이 있어도(보호된 구역) 죽지 않고 "못 찾았다"로 친다."""
    image = toybox_fake_exe.state_image(sigs)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    memory = kernel32.VirtualAlloc(None, len(image), 0x3000, 0x04)            # 예약+확정, 읽기 · 쓰기
    ctypes.memmove(memory, image, len(image))
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(memory + toybox_fake_exe.PLANT, 0x1000, 0x01, ctypes.byref(old))   # 서명이 든 쪽: PAGE_NOACCESS
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    try:
        result = lib.srtoybox_locate_state(ctypes.c_char_p(memory), len(image), ctypes.byref(found), error, len(error), None, 0)
    finally:
        kernel32.VirtualFree(memory, 0, 0x8000)
    assert result == -1 and "읽을 수 없는 곳" in error.value.decode("utf-8")


def test_state_on_the_installed_game(lib, game_dir):
    """build 21347933: 서명 21개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 주소가 docs/11 의 표와 같다."""
    found, why, rows = toybox.state_of(lib, installed_image(game_dir))
    assert found == BUILD_STATE, why
    assert [row.count for row in rows] == [1] * 21
    assert all(row.value == BUILD_STATE[row.name] for row in rows)


def test_state_signatures_lie_outside_the_cheat_handler(lib, game_dir):
    """요구 3: 서명은 치트 명령 처리 함수의 코드에서 뽑지 않는다."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    begin, end = oracle.handler(image)
    for row in toybox.state_of(lib, image)[2]:
        assert not begin <= row.at < end, row
        assert lib.srtoybox_function_root(image, len(image), row.at) != begin, row


def test_each_address_takes_its_signatures_from_different_functions(lib, game_dir):
    image = installed_image(game_dir)
    rows = toybox.state_of(lib, image)[2]
    for i in range(0, 21, 3):
        roots = {lib.srtoybox_function_root(image, len(image), row.at) or -row.at for row in rows[i:i + 3]}   # 함수 표에 없으면 0
        assert len(roots) == 3, rows[i].name


def test_state_agrees_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 새 찾기(서명)의 값 == 2단계의 방식(치트 닻)으로 읽은 값."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    assert toybox.state_of(lib, image)[0] == oracle.state(image)
```

- [ ] **Step 6: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -n 5`
Expected: 모듈의 `lib` fixture 가 `AttributeError: function 'srtoybox_locate_state' not found` 를 내어 이 파일의 테스트가 모두 ERROR (DLL 에 새 내보내기가 아직 없다).

- [ ] **Step 7: `locate.h` 에 새 찾기를 더한다** — `native/srtoybox/locate.h`

파일 끝(`locate_game` 선언 아래)에 더한다:

```cpp

const int STATE_WANTED = 7;     // 상태 묶음에서 찾을 것의 수
const int STATE_SIGS = 3;       // 찾을 것마다의 서명 수
const int STATE_NEED = 2;       // 그 가운데 정확히 한 번 맞아야 하는 수

// 서명 하나의 결과(로그와 srkit locate 가 쓴다).
struct SigRow {
    const char *name;           // 찾을 것(GameAddresses 의 필드 이름)
    const char *text;           // 서명 글
    int count;                  // 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    uint32_t at;                // 처음 맞은 자리
    uint32_t value;             // 거기서 읽어 낸 주소
};

// 새 찾기: 게임 상태를 읽는 데 쓰는 전역 일곱을 서명으로 찾는다(sigs.h). 치트 문자열도 치트 명령 처리 함수의 코드도 쓰지 않는다 —
// 게임이 치트를 없애도 된다. 찾을 것마다 서명 STATE_SIGS 개 가운데 STATE_NEED 개 이상이 정확히 한 번 맞고 같은 주소를 내야 한다.
// 찾으면 true 와 out 의 일곱 필드(handler · context · options 는 건드리지 않는다). 못 찾으면 false 와 why(UTF-8).
// rows: STATE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr. 읽을 수 없는 쪽을 만나도 죽지 않는다.
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size);

// rva 가 든 함수의 시작(함수 표에서. chained unwind 를 뿌리까지). 없으면 0. 테스트와 srkit 이 쓴다.
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);
```

- [ ] **Step 8: `locate.cpp` 에 새 찾기를 더한다** — `native/srtoybox/locate.cpp`

머리의 `#include` 를 다음으로 바꾼다:

```cpp
#include "locate.h"

#include <excpt.h>

#include <cstdio>
#include <cstring>

#include "sigs.h"
```

이름 없는 namespace 안, `search()` 함수 아래(`}  // namespace` 위)에 더한다:

```cpp
// 게임 상태를 읽는 데 쓰는 전역 일곱. 서명은 모두 치트 명령 처리 함수 밖의 코드에서 뽑았다(uv run srkit sig-mine <RVA>):
// build 21347933 에서 저마다 실행 구역에 한 번만 맞고, 찾을 것마다 세 서명이 서로 다른 함수에 있다(docs/11-game-internals.md).
// 프로그램 상태와 모드 상태의 셋째 서명은 같은 자리(게임 진입의 mov [모드 상태],2 / mov [프로그램 상태],1)를 읽는다.
const struct Wanted {
    const char *name;                       // GameAddresses 의 필드 이름(srkit locate 와 테스트가 본다)
    const char *label;                      // 로그에 나오는 이름
    uint32_t GameAddresses::*field;
    uint32_t bytes;                         // 그 주소에서 이만큼은 실행 파일 안이어야 한다
    const char *sigs[STATE_SIGS];
} STATE[STATE_WANTED] = {
    {"multiplayer", "멀티플레이 표시", &GameAddresses::multiplayer, 1,
     {"80 3D [rip+1] 00 74 18 8B 47 3C", "80 3D [rip+1] 00 0F B6 FA 74 47", "80 3D [rip+1] 00 74 13 8B 41 14"}},
    {"program_state", "프로그램 상태", &GameAddresses::program_state, 4,
     {"83 3D [rip+1] 01 75 08 48 8B CB", "83 3D [rip+1] 06 48 8B F2 4C 8B F9",
      "C7 05 ? ? ? ? 02 00 00 00 C7 05 [rip+4] 01 00 00 00"}},
    {"mode_state", "모드 상태", &GameAddresses::mode_state, 4,
     {"83 3D [rip+1] 02 48 8B D9 75 40", "83 3D [rip+1] 00 48 8B D9 75 21",
      "C7 05 [rip+4] 02 00 00 00 C7 05 ? ? ? ? 01 00 00 00"}},
    {"player_index", "플레이어 인덱스", &GameAddresses::player_index, 4,
     {"44 3B 05 [rip] 49 63 C8 74 16", "44 8B 35 [rip] 45 84 ED 74 05", "44 8B 0D [rip] 45 33 C0 33 D2"}},
    {"player_pointer", "플레이어 포인터", &GameAddresses::player_pointer, 8,
     {"48 8B 15 [rip] 8B 42 6C 85 C0", "48 8B 0D [rip] 48 85 C9 74 58", "4C 8B 35 [rip] FF C7 3B 7D 38"}},
    {"region_table", "지역 표", &GameAddresses::region_table, 8 * 1024,
     {"4C 8D 05 [rip] 49 8B 10 48 85 D2", "48 8D 0D [rip] 90 48 8B 31 48 85 F6", "48 8D 0D [rip] 48 8B 0C C1 48 85 C9"}},
    {"region_count", "지역 수", &GameAddresses::region_count, 4,
     {"44 8B 35 [rip] 44 8B DF 8B D6", "44 8B 0D [rip] 8B D7 45 85 C9", "44 8B 15 [rip] 43 8D 04 0C 99"}},
};

bool search_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    const int total = STATE_WANTED * STATE_SIGS;
    Image im = {};
    im.p = image;
    im.size = size;
    if (image == nullptr || !parse(im)) {
        snprintf(why, why_size, "실행 파일의 머리말을 읽을 수 없습니다");
        return false;
    }
    SigRange ranges[32];
    int range_count = 0;
    for (int s = 0; s < im.count; s++)
        if (im.sections[s].code) {
            ranges[range_count].begin = im.sections[s].rva;
            ranges[range_count].end = im.sections[s].rva + im.sections[s].size;
            range_count++;
        }
    Sig sigs[STATE_WANTED * STATE_SIGS];
    SigHit hits[STATE_WANTED * STATE_SIGS];
    for (int i = 0; i < total; i++)
        if (!sig_parse(STATE[i / STATE_SIGS].sigs[i % STATE_SIGS], &sigs[i])) {
            snprintf(why, why_size, "서명 표가 틀렸습니다 (%s)", STATE[i / STATE_SIGS].name);
            return false;
        }
    sig_scan(image, size, ranges, range_count, sigs, total, hits);
    if (rows != nullptr)
        for (int i = 0; i < total; i++) {
            rows[i].count = hits[i].count;
            rows[i].at = hits[i].at;
            rows[i].value = static_cast<uint32_t>(hits[i].value[0]);
        }
    GameAddresses found = *out;
    for (int w = 0; w < STATE_WANTED; w++) {
        uint64_t value[SIG_CAPTURES] = {};
        int matched = 0;
        if (!sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, STATE_NEED, value, &matched)) {
            if (matched >= STATE_NEED)
                snprintf(why, why_size, "%s: 서명들이 서로 다른 주소를 냅니다", STATE[w].label);
            else
                snprintf(why, why_size, "%s: 서명 %d개 가운데 %d개", STATE[w].label, STATE_SIGS, matched);
            return false;
        }
        if (value[0] == 0 || value[0] >= size || !im.has(value[0], STATE[w].bytes)) {
            snprintf(why, why_size, "%s: 찾은 주소가 실행 파일 밖입니다", STATE[w].label);
            return false;
        }
        found.*(STATE[w].field) = static_cast<uint32_t>(value[0]);
    }
    *out = found;
    snprintf(why, why_size, "%s", "");
    return true;
}
```

파일 끝(`locate_game` 아래)에 더한다:

```cpp

// 서명을 맞추다 읽을 수 없는 쪽을 만나도 죽지 않는다(locate_game 과 같은 까닭). rows 의 이름과 글은 찾기 전에 채운다 —
// 머리말조차 못 읽은 이미지에서도 서명 표를 볼 수 있다(테스트와 srkit locate 가 쓴다).
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    if (rows != nullptr)
        for (int i = 0; i < STATE_WANTED * STATE_SIGS; i++) {
            rows[i].name = STATE[i / STATE_SIGS].name;
            rows[i].text = STATE[i / STATE_SIGS].sigs[i % STATE_SIGS];
            rows[i].count = 0;
            rows[i].at = 0;
            rows[i].value = 0;
        }
    __try {
        return search_state(image, size, out, rows, why, why_size);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        snprintf(why, why_size, "실행 파일에 읽을 수 없는 곳이 있습니다");
        return false;
    }
}

uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva)
{
    __try {
        Image im = {};
        im.p = image;
        im.size = size;
        return image != nullptr && parse(im) ? function_root(im, rva) : 0;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return 0;
    }
}
```

- [ ] **Step 9: 내보내기를 더한다** — `native/srtoybox/exports.cpp`

`srtoybox_locate` 함수 아래에 더한다:

```cpp
// 새 찾기(상태 묶음, 서명으로). 0 이면 out 의 일곱 필드를 채웠다. -1 이면 error 에 까닭.
// rows 에는 서명마다 한 줄 "<찾을 것>\t<서명 글>\t<맞은 횟수>\t<처음 맞은 자리>\t<읽어 낸 주소>"(뒤의 셋은 16진수). 필요 없으면 nullptr.
EXPORT int srtoybox_locate_state(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size,
                                 char *rows, int rows_size)
{
    GameAddresses found = {};
    SigRow table[STATE_WANTED * STATE_SIGS];
    char why[160] = "";
    const bool ok = locate_state(image, static_cast<size_t>(size), &found, table, why, sizeof(why));
    if (rows != nullptr) {
        std::string text;
        char numbers[64];
        for (const SigRow &row : table) {
            snprintf(numbers, sizeof(numbers), "\t%x\t%x\t%x\n", static_cast<unsigned>(row.count), row.at, row.value);
            text += std::string(row.name) + '\t' + row.text + numbers;
        }
        put(text, rows, rows_size);
    }
    if (!ok) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

EXPORT unsigned srtoybox_function_root(const unsigned char *image, unsigned long long size, unsigned rva)
{
    return locate_function_root(image, static_cast<size_t>(size), rva);
}
```

- [ ] **Step 10: 빌드하고 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -n 3`
Expected: 빌드 완료, 이어서 `54 passed` (이 파일의 32 + 새 22. 게임 설치본이 없으면 설치본을 쓰는 것들이 건너뛰어진다)

설치본에서 `test_state_on_the_installed_game` 이 실패하면(서명이 한 번만 맞지 않거나 값이 다르다) 서명 표를 옮겨 적다 틀린 것이다 — 이 계획의 표("계획을 쓰며 확인한 것")와 `STATE` 의 글을 한 글자씩 견준다. 견줘도 같으면 `uv run srkit sig-mine <그 RVA>` 로 다시 뽑아 바꾸고, 바꾼 서명과 까닭을 PR 본문에 적는다.

- [ ] **Step 11: 전체 테스트와 커밋**

Run: `uv run pytest -q 2>&1 | tail -n 3`
Expected: `232 passed` (210 + 22)

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/toybox_fake_exe.py tests/toybox_cheat_oracle.py tests/test_toybox_game.py && git commit -q -F - <<'EOF'
feat: ToyBox — 게임 상태의 주소 일곱을 치트와 무관한 서명으로 찾는다(locate_state)

찾을 것마다 서로 다른 함수에서 뽑은 서명 셋을 두고, 둘 이상이 정확히 한 번 맞으며
같은 주소를 낼 때만 찾은 것으로 친다. 서명은 모두 치트 명령 처리 함수 밖의 코드다
(build 21347933 에서 대조). 아직 ToyBox 의 동작은 바꾸지 않는다 — 다음 커밋에서 옮긴다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 4: 상태 읽기를 새 찾기로 옮기고, 옛 찾기를 셋으로 줄인다

**브랜치:** `feat/toybox-locate-independent` (Task 3 에 이어서). 이 Task 가 끝나면 PR 을 올린다(머지는 Task 5 의 확인 뒤).

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/game.h`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`
- Modify: `src/srkit/toybox.py`, `src/srkit/cli.py:157-170`
- Modify: `tests/toybox_fake_exe.py`(다시 쓴다), `tests/test_toybox_game.py`

**Interfaces:**
- Consumes: `locate_state` · `SigRow` · `STATE_WANTED` · `STATE_SIGS`(Task 3), `tests/toybox_fake_exe.shell` · `put` · `rip` · `state_image` · `STATE`(Task 2 · 3), `srkit.toybox.state_of` · `STATE_FIELDS`(Task 3).
- Produces:
  - C++ `const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out);` — 찾으면 `nullptr` 과 `out` 의 `handler` · `context` · `options`(다른 필드는 건드리지 않는다). 못 찾으면 까닭이고 `out` 은 그대로다.
  - C++ `locate_game` 은 없어진다.
  - `GameState::cheats_on` 은 옵션 묶음의 주소가 0 이면 늘 `false`.
  - 내보내기 `int srtoybox_locate_legacy(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)`. `srtoybox_locate` 는 없어진다.
  - Python `srkit.toybox.LEGACY_FIELDS`, `srkit.toybox.legacy_of(lib, image) -> tuple[dict[str, int] | None, str]`, `srkit.toybox.Located(state, state_why, rows, ms, legacy, legacy_why)`, `srkit.toybox.locate(cfg) -> Located`
  - Python `tests/toybox_fake_exe.py`: `LEGACY: dict[str, int]`, `build(sigs=None, *, extra_anchor=False, second_call=False, no_options=False, outside=False) -> bytes`. `EXPECTED` · `STRINGS` · `ENTER` 는 없어진다.
  - 로그의 줄: `게임 상태를 읽습니다 (서명 21개 가운데 N개, M ms)` / `게임 상태를 읽을 수 없습니다 (<까닭>) — 글쇠 방식` / `옛 방식(내장 치트)으로 도는 기능이 N개 남아 있습니다 (명령 처리 함수 +0x…)` / `명령 처리 함수를 찾지 못했습니다 (<까닭>) — 내장 치트로 도는 기능은 글쇠 방식`

- [ ] **Step 1: 가짜 이미지를 다시 쓴다** — `tests/toybox_fake_exe.py` (Write 도구로 파일 전체를)

```python
"""주소 찾기(native/srtoybox/locate.cpp) 테스트용: 작은 가짜 실행 파일 이미지(RVA 대로 펼친 것).

게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다)과, 옛 찾기가 보는 닻(치트 문자열)과
명령의 바이트 꼴만 같은 자리 관계로 놓았다. pytest 가 직접 모으는 테스트 파일이 아니다.
"""
import re
import struct

SIZE = 0x8000                                 # 지역 표(8바이트 × 1024칸)가 DATA + 0x200 부터 들어갈 만큼
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER = 0x1000, 0x1800
WORLD = DATA + 0x180                          # 지역 표 = WORLD + 0x80
ANCHOR = RDATA                                # "cheat allowcheats"
# 새 찾기(상태 묶음)의 가짜 주소
STATE = {"multiplayer": DATA, "program_state": DATA + 8, "mode_state": DATA + 12, "player_index": DATA + 16,
         "player_pointer": DATA + 24, "region_table": WORLD + 0x80, "region_count": DATA + 20}
# 옛 찾기(치트 닻)의 가짜 주소
LEGACY = {"handler": HANDLER, "context": DATA + 0x100, "options": DATA + 4}
PLANT, AGAIN = TEXT + 0x1000, TEXT + 0x1800     # 서명을 심는 곳, 같은 서명을 한 번 더 심는 곳
TOKEN = re.compile(r"\[rip(?:\+([14]))?\]|\[u(?:8|32)\]|\?|[0-9A-Fa-f]{2}")   # 서명 글의 낱말(native/srtoybox/sigs.h)


def shell(functions: list[tuple[int, int]], size: int = SIZE) -> bytearray:
    """머리말 · 구역 표 · 함수 표만 있는 빈 이미지. functions: 함수 표에 넣을 [시작, 끝) 들(시작순)."""
    image = bytearray(size)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x98] = b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 4, 0, 0, 0, 0xF0, 0x22)
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<II", image, optional + 56, size, 0x400)                 # SizeOfImage, SizeOfHeaders
    struct.pack_into("<I", image, optional + 108, 16)                          # NumberOfRvaAndSizes
    struct.pack_into("<II", image, optional + 112 + 3 * 8, PDATA, 12 * len(functions))
    for i, (name, rva, flags) in enumerate([(b".text", TEXT, 0x60000020), (b".rdata", RDATA, 0x40000040),
                                            (b".pdata", PDATA, 0x40000040), (b".data", DATA, 0xC0000040)]):
        struct.pack_into("<8sIIIIIIHHI", image, optional + 0xF0 + 40 * i, name, 0x2000 if rva == TEXT else 0x1000, rva,
                         0, 0, 0, 0, 0, 0, flags)
    unwind = RDATA + 0x800
    image[unwind:unwind + 4] = bytes([1, 0, 0, 0])                             # 풀기 정보: 뿌리(플래그 없음)
    for i, (begin, end) in enumerate(functions):
        struct.pack_into("<III", image, PDATA + 12 * i, begin, end, unwind)
    return image


def put(image: bytearray, rva: int, data: bytes) -> int:
    image[rva:rva + len(data)] = data
    return rva + len(data)


def rip(image: bytearray, rva: int, opcode: bytes, target: int, tail: bytes = b"") -> int:
    """RIP 상대 변위가 든 명령 하나: opcode + 변위(4) + tail. 변위는 명령의 끝을 기준으로 한다."""
    length = len(opcode) + 4 + len(tail)
    return put(image, rva, opcode + struct.pack("<i", target - (rva + length)) + tail)


def plant(image: bytearray, at: int, text: str, target: int) -> int:
    """서명 글 하나를 at 에 심는다: 정해진 바이트는 그대로, 구멍은 건드리지 않고, 읽어 낼 자리는 target 이 나오게. 끝 자리를 돌려준다."""
    pos = at
    for m in TOKEN.finditer(text):
        word = m.group(0)
        if word.startswith("[rip"):
            struct.pack_into("<i", image, pos, target - (pos + 4 + int(m.group(1) or 0)))
            pos += 4
        elif word == "[u32]":
            struct.pack_into("<I", image, pos, target)
            pos += 4
        elif word == "[u8]":
            image[pos] = target
            pos += 1
        elif word == "?":
            pos += 1
        else:
            image[pos] = int(word, 16)
            pos += 1
    return pos


def shape(text: str) -> str:
    """읽어 낼 자리를 구멍으로 바꾼 글. 꼴이 같은 서명들은 게임에서 같은 자리의 명령을 읽는다
    (프로그램 상태와 모드 상태가 게임 진입의 두 mov 에서 하나씩 읽는다) — 한 곳에만 심어야 저마다 한 번씩 맞는다."""
    return " ".join("? ? ? ?" if w.startswith("[rip") or w == "[u32]" else "?" if w in ("?", "[u8]") else w.upper()
                    for w in (m.group(0) for m in TOKEN.finditer(text)))


def state_image(sigs: list[tuple[str, str]], *, broken=(), twice=(), stray=(), targets: dict[str, int] | None = None,
                into: bytearray | None = None) -> bytes:
    """DLL 의 서명 표(sigs: [(찾을 것, 서명 글)])를 심은 이미지. into 가 없으면 치트 문자열이 하나도 없는 빈 틀에 심는다.

    broken · twice · stray 는 sigs 의 칸 번호들이다: 심지 않는다 / 한 번 더 심는다(두 번 맞는다) / 8바이트 옆을 가리키게 심는다.
    targets 로 가짜 주소를 바꾼다.
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = dict(STATE, **(targets or {}))
    places: dict[str, int] = {}
    for i, (name, text) in enumerate(sigs):
        if i in broken:
            continue
        place = places.setdefault(shape(text), PLANT + 0x40 * len(places))
        plant(image, place, text, at[name] + (8 if i in stray else 0))
        if i in twice:
            plant(image, AGAIN + 0x40 * i, text, at[name])
    return bytes(image)


def build(sigs: list[tuple[str, str]] | None = None, *, extra_anchor: bool = False, second_call: bool = False,
          no_options: bool = False, outside: bool = False) -> bytes:
    """옛 찾기의 닻(치트 문자열, 명령 처리 함수, 그것을 부르는 곳)이 든 이미지. sigs 를 주면 새 찾기의 서명도 심는다.

    나머지 인자는 옛 찾기가 거부해야 하는 흠을 하나씩 낸다.
    """
    image = shell([(HANDLER, HANDLER + 0x200), (CALLER, CALLER + 0x20), (CALLER + 0x20, CALLER + 0x100), (PLANT, TEXT + 0x2000)])
    unwind = RDATA + 0x800
    put(image, unwind + 0x10, bytes([0x21, 0, 0, 0]) + struct.pack("<III", CALLER, CALLER + 0x20, unwind))   # UNW_FLAG_CHAININFO
    struct.pack_into("<I", image, PDATA + 12 * 2 + 8, unwind + 0x10)           # 부르는 함수의 뒤 조각은 앞 조각에 묶인다
    put(image, ANCHOR, b"cheat allowcheats\0")
    if extra_anchor:
        put(image, RDATA + 0x400, b"cheat allowcheats\0")

    # 명령 처리 함수: lea rdx,["cheat allowcheats"] / or dword ptr [옵션],40h
    end = put(image, HANDLER, bytes([0x40, 0x55, 0x53, 0x57]))
    end = rip(image, end, bytes([0x48, 0x8D, 0x15]), ANCHOR)
    if not no_options:
        end = rip(image, end, bytes([0x83, 0x0D]), SIZE + 0x100 if outside else LEGACY["options"], b"\x40")
    put(image, end, b"\xC3")

    # 부르는 함수의 뒤쪽 조각: lea rcx,[this] / call 명령 처리 함수
    end = rip(image, CALLER + 0x30, bytes([0x48, 0x8D, 0x0D]), LEGACY["context"])
    rip(image, end, bytes([0xE8]), HANDLER)
    if second_call:
        rip(image, CALLER + 0x60, bytes([0xE8]), HANDLER)
    return state_image(sigs, into=image) if sigs is not None else bytes(image)
```

- [ ] **Step 2: 테스트를 고친다** — `tests/test_toybox_game.py`

머리의 주석과 상수를 고친다:

```python
"""ToyBox: 주소 찾기(새 찾기 = 서명, 옛 찾기 = 치트 닻) · 게임 상태 읽기 · 나라 이름표 (native/srtoybox 의 locate · game · regions)."""
```

`BUILD_STATE = …` 줄 아래에 한 줄을 더한다:

```python
BUILD_LEGACY = {name: BUILD_21347933[name] for name in toybox.LEGACY_FIELDS}
```

**지운다**(옛 `locate_game` 의 테스트 — 새 찾기와 옛 찾기의 테스트가 대신한다): 함수 `find`, `test_locate_finds_every_address_from_the_anchor_string`, `test_locate_refuses_an_image_that_does_not_add_up`, `test_locate_survives_garbage`, `test_locate_survives_an_image_with_a_page_it_cannot_read`, `test_locate_on_the_installed_game`, `test_srkit_locate_reports_the_addresses`.

`test_state_agrees_with_what_the_cheat_code_says` 아래(`def state(lib, fake…` 위)에 더한다:

```python
def test_legacy_finds_the_handler_from_the_cheat_anchor(lib, sigs):
    """옛 찾기(전환 기간): 아직 내장 치트로 도는 기능이 쓰는 셋만 치트 문자열을 닻으로 찾는다."""
    assert toybox.legacy_of(lib, toybox_fake_exe.build(sigs)) == (toybox_fake_exe.LEGACY, "")


@pytest.mark.parametrize("flaw, reason", [
    ("extra_anchor", "닻 문자열"),                   # 같은 문자열이 둘이면 어느 것이 진짜인지 모른다
    ("second_call", "부르는 곳"),                    # 부르는 곳이 둘이면 this 를 어디서 얻을지 모른다
    ("no_options", "치트 허용 비트"),                # 함수 머리의 모양이 다르다 = 다른 함수이거나 바뀐 빌드
    ("outside", "실행 파일 밖"),                     # 찾은 주소가 이미지 밖이다
])
def test_legacy_refuses_an_image_that_does_not_add_up(lib, flaw, reason):
    found, why = toybox.legacy_of(lib, toybox_fake_exe.build(**{flaw: True}))
    assert found is None and reason in why, why


def test_an_image_without_cheats_gives_the_state_but_not_the_handler(lib, sigs):
    """게임이 치트를 없앤 빌드: 상태는 읽고(새 찾기) 명령 처리 함수는 못 찾는다(옛 찾기) — 옮기지 않은 기능만 글쇠 방식이 된다."""
    image = toybox_fake_exe.state_image(sigs)
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE
    found, why = toybox.legacy_of(lib, image)
    assert found is None and "닻 문자열" in why


def test_an_image_with_both_gives_both(lib, sigs):
    """치트의 닻과 서명이 함께 든 이미지(지금의 게임): 두 찾기가 서로를 방해하지 않는다."""
    image = toybox_fake_exe.build(sigs)
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE
    assert toybox.legacy_of(lib, image)[0] == toybox_fake_exe.LEGACY


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_legacy_survives_garbage(lib, image):
    found, why = toybox.legacy_of(lib, image)
    assert found is None and why


def test_legacy_survives_an_image_with_a_page_it_cannot_read(lib):
    image = toybox_fake_exe.build()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    memory = kernel32.VirtualAlloc(None, len(image), 0x3000, 0x04)            # 예약+확정, 읽기 · 쓰기
    ctypes.memmove(memory, image, len(image))
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(memory + toybox_fake_exe.TEXT, 0x1000, 0x01, ctypes.byref(old))   # 코드의 첫 쪽: PAGE_NOACCESS
    found, error = toybox.GameAddresses(), ctypes.create_string_buffer(256)
    try:
        result = lib.srtoybox_locate_legacy(ctypes.c_char_p(memory), len(image), ctypes.byref(found), error, len(error))
    finally:
        kernel32.VirtualFree(memory, 0, 0x8000)
    assert result == -1 and "읽을 수 없는 곳" in error.value.decode("utf-8")


def test_legacy_on_the_installed_game(lib, game_dir):
    assert toybox.legacy_of(lib, installed_image(game_dir)) == (BUILD_LEGACY, "")


def test_srkit_locate_reports_both_searches(lib, cfg, game_dir):
    located = toybox.locate(cfg)
    assert located.state is not None and set(located.state) == set(toybox.STATE_FIELDS), located.state_why
    assert len(located.rows) == 21 and located.ms >= 0
    assert located.legacy is not None and set(located.legacy) == set(toybox.LEGACY_FIELDS), located.legacy_why
```

`test_game_state_reads_the_cheat_bit_and_the_multiplayer_flag` 아래에 더한다:

```python
def test_game_state_without_the_legacy_addresses(lib):
    """옛 찾기가 실패하면(치트가 없는 빌드) 옵션 묶음의 주소가 없다(0). 그래도 상태는 읽는다 — 치트 허용만 모르고, 꺼진 것으로 친다."""
    fake = germany()
    fake.at.options = 0
    fake.at.handler = 0
    fake.at.context = 0
    fake.poke(OPTIONS, "<I", 0x40)
    assert state(lib, fake) == {"known": "1", "in_game": "1", "multiplayer": "0", "cheats": "0", "player": "1499",
                                "regions": "1106,1201,1499"}
```

- [ ] **Step 3: Python 쪽을 고친다** — `src/srkit/toybox.py`

`import` 묶음의 `import subprocess` 아래에 `import time` 을 더한다.

`STATE_FIELDS = […]` 줄 아래에 더한다:

```python
# 옛 찾기(치트 닻)가 채우는 셋 — 아직 내장 치트로 도는 기능이 쓴다(전환 기간에만)
LEGACY_FIELDS = ["handler", "context", "options"]
```

`SigRow` 아래에 더한다:

```python
@dataclass
class Located:
    """설치된 게임의 실행 파일에서 찾은 것."""
    state: dict[str, int] | None     # 새 찾기(서명): 상태 전역 일곱. 못 찾았으면 None
    state_why: str
    rows: list[SigRow]               # 서명마다의 결과
    ms: float                        # 새 찾기에 걸린 시간
    legacy: dict[str, int] | None    # 옛 찾기(치트 닻): 명령 처리 함수 · this · 옵션 묶음. 못 찾았으면 None
    legacy_why: str
```

`library()` 에서 `lib.srtoybox_locate.argtypes = …` 줄을 다음으로 바꾼다:

```python
    lib.srtoybox_locate_legacy.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p,
                                           ctypes.c_int]
```

`state_of()` 아래에 더하고, 지금의 `locate()` 함수를 통째로 다음의 `locate()` 로 바꾼다:

```python
def legacy_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str]:
    """옛 찾기(치트 닻)를 그 이미지에 돌린다: (이름 → RVA, "") 또는 (None, 까닭)."""
    found, error = GameAddresses(), ctypes.create_string_buffer(256)
    if lib.srtoybox_locate_legacy(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in LEGACY_FIELDS}, ""


def locate(cfg: Config) -> Located:
    """설치된 게임의 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 게임 안에서 도는 것과 같은 코드(DLL)를 쓴다. 파일을 읽기만 한다.

    DLL 이 빌드되어 있어야 한다(srkit toybox-build).
    """
    lib = library(cfg)
    image = image_of((cfg.game_dir / EXE_NAME).read_bytes())
    started = time.perf_counter()
    state, state_why, rows = state_of(lib, image)
    ms = (time.perf_counter() - started) * 1000
    legacy, legacy_why = legacy_of(lib, image)
    return Located(state, state_why, rows, ms, legacy, legacy_why)
```

- [ ] **Step 4: 테스트가 실패하는 것을 본다**

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -n 5`
Expected: `lib` fixture 가 `AttributeError: function 'srtoybox_locate_legacy' not found` 를 내어 이 파일의 테스트가 모두 ERROR.

- [ ] **Step 5: `locate.h` 를 다시 쓴다** — `native/srtoybox/locate.h` (Write 도구로 파일 전체를)

```cpp
// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다.
// 창도 게임의 상태도 모르는 순수 함수다. 읽다가 예외가 나면(읽을 수 없는 쪽) "못 찾았다"로 친다.
//
// 찾는 길이 둘이다(docs/11-game-internals.md):
//   새 찾기 locate_state   게임 상태를 읽는 전역 일곱. 내장 치트와 무관한 코드의 서명으로(sigs.h) — 게임이 치트를 없애도 된다.
//   옛 찾기 locate_legacy  치트 명령 처리 함수와 그 둘레의 셋. "cheat allowcheats" 문자열을 닻으로. 아직 내장 치트로 도는
//                          기능이 쓴다 — 모든 기능을 옮긴 뒤(3단계의 마지막 묶음) 직접 실행 · 글쇠 방식과 함께 지운다.
#pragma once

#include <cstddef>
#include <cstdint>

// 모두 이미지의 시작으로부터의 거리(RVA). 0 이면 찾지 못한 것이다.
struct GameAddresses {
    uint32_t handler;          // [옛 찾기] 명령 처리 함수: void f(void *context, const char *line)
    uint32_t context;          // [옛 찾기] 그 함수의 첫 인자로 넘기는 전역 객체(게임이 넘기는 것과 같은 주소)
    uint32_t multiplayer;      // byte. 0 이 아니면 멀티플레이다
    uint32_t options;          // [옛 찾기] dword. 비트 0x40 = 치트 허용
    uint32_t program_state;    // dword. 1 = 월드가 돌고 있다
    uint32_t mode_state;       // dword. 2 = 게임
    uint32_t player_index;     // dword. 플레이어 지역의 인덱스(지역 표의 칸)
    uint32_t player_pointer;   // qword. 플레이어 지역 객체
    uint32_t region_table;     // qword × 1024. 인덱스순 지역 객체 포인터
    uint32_t region_count;     // dword. 지역 표의 마지막 인덱스
};

const int STATE_WANTED = 7;     // 상태 묶음에서 찾을 것의 수
const int STATE_SIGS = 3;       // 찾을 것마다의 서명 수
const int STATE_NEED = 2;       // 그 가운데 정확히 한 번 맞아야 하는 수

// 서명 하나의 결과(로그와 srkit locate 가 쓴다).
struct SigRow {
    const char *name;           // 찾을 것(GameAddresses 의 필드 이름)
    const char *text;           // 서명 글
    int count;                  // 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    uint32_t at;                // 처음 맞은 자리
    uint32_t value;             // 거기서 읽어 낸 주소
};

// image: RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈의 시작 주소), size: 그 크기.

// 새 찾기: 찾을 것마다 서명 STATE_SIGS 개 가운데 STATE_NEED 개 이상이 정확히 한 번 맞고 같은 주소를 내야 한다.
// 찾으면 true 와 out 의 일곱 필드(handler · context · options 는 건드리지 않는다). 못 찾으면 false 와 why(UTF-8).
// rows: STATE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size);

// 옛 찾기(전환 기간에만): 찾으면 nullptr 과 out 의 handler · context · options(다른 필드는 건드리지 않는다).
// 못 찾으면 까닭(UTF-8, 정적 문자열)이고 out 은 그대로다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out);

// rva 가 든 함수의 시작(함수 표에서. chained unwind 를 뿌리까지). 없으면 0. 테스트와 srkit 이 쓴다.
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);
```

- [ ] **Step 6: `locate.cpp` 의 옛 찾기를 줄인다** — `native/srtoybox/locate.cpp`

**지운다**: 함수 `count_in_code`, `find_in_cheat`, `search`(쓰이지 않는 함수가 남으면 `/W4 /WX` 에서 빌드 오류다), 그리고 파일 끝쪽의 `locate_game` 과 그 위의 주석 두 줄.

`search` 가 있던 자리(`function_root` 아래)에 넣는다:

```cpp
// 옛 찾기: 닻 문자열 → 그것을 쓰는 자리 → 그 자리가 든 함수(명령 처리 함수) → 머리의 옵션 묶음, 부르는 곳의 this.
// 상태 전역(멀티플레이 표시 · 플레이어 · 지역 표 …)은 여기서 읽지 않는다 — 새 찾기(search_state)의 일이다.
const char *search_legacy(const uint8_t *image, size_t size, GameAddresses *out)
{
    Image im = {};
    im.p = image;
    im.size = size;
    GameAddresses a = *out;
    uint32_t anchor = 0, use = 0, call = 0, at = 0;
    if (image == nullptr || !parse(im))
        return "실행 파일의 머리말을 읽을 수 없습니다";

    if (count_string(im, "cheat allowcheats", &anchor) != 1)
        return "닻 문자열(cheat allowcheats)이 하나가 아닙니다";
    if (count_lea_to(im, anchor, &use) != 1)
        return "닻 문자열을 쓰는 자리가 하나가 아닙니다";
    if ((a.handler = function_root(im, use)) == 0)
        return "명령 처리 함수의 시작을 찾지 못했습니다";

    // 함수 머리: or dword ptr [옵션],40h
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("83 0D ? ? ? ? 40"))) == 0)
        return "함수 머리에 치트 허용 비트를 세우는 명령이 없습니다";
    a.options = target(im, at, 2, 7);

    // 부르는 곳은 하나이고, 바로 앞에서 lea rcx,[this]
    if (count_calls_to(im, a.handler, &call) != 1)
        return "명령 처리 함수를 부르는 곳이 하나가 아닙니다";
    if (call < 7 || !matches(im, call - 7, pattern("48 8D 0D ? ? ? ?")))
        return "부르는 곳 바로 앞에 this 를 채우는 명령이 없습니다";
    a.context = target(im, call - 7, 3, 7);

    const uint32_t all[] = {a.handler, a.context, a.options};
    for (uint32_t rva : all)
        if (rva == 0 || !im.has(rva, 8))
            return "찾은 주소가 실행 파일 밖입니다";
    *out = a;
    return nullptr;
}
```

`locate_game` 이 있던 자리(`}  // namespace` 아래, `locate_state` 위)에 넣는다:

```cpp
// 올라와 있는 실행 파일에는 읽을 수 없는 쪽이 있을 수 있다(보호된 구역). 그때도 죽지 않는다 — 여기서 예외가 새면 게임이 뜨다가 죽는다.
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search_legacy · search_state)과 따로 뗐다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out)
{
    __try {
        return search_legacy(image, size, out);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return "실행 파일에 읽을 수 없는 곳이 있습니다";
    }
}
```

`locate_state` 위에 Task 3 에서 쓴 주석의 `(locate_game 과 같은 까닭)` 을 `(locate_legacy 와 같은 까닭)` 으로 고친다.

- [ ] **Step 7: `game` 이 새 찾기로 읽게 한다** — `native/srtoybox/game.h`, `native/srtoybox/game.cpp`

`game.h` 의 `GameState` 두 줄을 고친다:

```cpp
    bool known = false;         // 주소를 찾았고(새 찾기 — 서명), 읽은 값이 서로 맞는다. 거짓이면 내장 치트로 도는 기능은 글쇠 방식으로 동작한다
```

```cpp
    bool cheats_on = false;     // 치트 허용 비트. 옛 찾기가 옵션 묶음을 찾았을 때만 읽는다(못 찾았으면 늘 false)
```

`game.cpp` 의 `#include "log.h"` 위에 한 줄을 더한다:

```cpp
#include "features.h"
```

`read_game()` 의 첫 `if` 를 고친다(옵션 묶음의 주소가 없으면 읽지 않는다):

```cpp
    if (base == nullptr || !peek_at(base, at.multiplayer, &multiplayer)
        || (at.options != 0 && !peek_at(base, at.options, &options))
        || !peek_at(base, at.program_state, &program) || !peek_at(base, at.mode_state, &mode)
        || !peek_at(base, at.player_index, &index) || !peek_at(base, at.player_pointer, &pointer)
        || !peek_at(base, at.region_count, &count))
        return s;
```

`game_init()` 을 통째로 바꾼다:

```cpp
void game_init()
{
    if (!reading_wanted()) {
        log_line("게임 상태를 읽지 않습니다 (SRTOYBOX_READ=0) — 글쇠 방식");
        return;
    }
    const uint8_t *base = reinterpret_cast<const uint8_t *>(GetModuleHandleW(nullptr));
    const IMAGE_DOS_HEADER *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    const IMAGE_NT_HEADERS64 *nt = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    const size_t size = nt->OptionalHeader.SizeOfImage;

    // 새 찾기: 게임 상태를 읽는 전역 일곱 — 내장 치트와 무관한 서명으로
    GameAddresses at = {};
    SigRow rows[STATE_WANTED * STATE_SIGS];
    char why[160] = "";
    const ULONGLONG started = GetTickCount64();
    const bool state = locate_state(base, size, &at, rows, why, sizeof(why));
    const unsigned long long took = GetTickCount64() - started;
    int matched = 0;
    for (const SigRow &row : rows)
        matched += row.count == 1 ? 1 : 0;

    // 옛 찾기(전환 기간에만): 아직 내장 치트로 도는 기능의 직접 실행이 쓴다. 상태를 읽지 못하면 그 기능들도 글쇠 방식이라 찾지 않는다
    const char *legacy = state ? locate_legacy(base, size, &at) : "게임 상태를 읽지 못했습니다";
    const bool can_call = state && legacy == nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_base = base;
        g_at = at;
        g_located = state;
        g_told = false;
        g_handler = can_call ? const_cast<uint8_t *>(base) + at.handler : nullptr;
        g_context = can_call ? const_cast<uint8_t *>(base) + at.context : nullptr;
    }
    if (!state) {
        log_line("게임 상태를 읽을 수 없습니다 (%s) — 글쇠 방식", why);
        return;
    }
    log_line("게임 상태를 읽습니다 (서명 %d개 가운데 %d개, %llu ms)", STATE_WANTED * STATE_SIGS, matched, took);
    if (can_call)
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", FEATURE_COUNT, at.handler);
    else
        log_line("명령 처리 함수를 찾지 못했습니다 (%s) — 내장 치트로 도는 기능은 글쇠 방식", legacy);
}
```

- [ ] **Step 8: 내보내기와 `srkit locate` 를 고친다**

`native/srtoybox/exports.cpp` — `srtoybox_locate` 함수(주석 한 줄 포함)를 통째로 바꾼다:

```cpp
// 옛 찾기(전환 기간에만): 명령 처리 함수 · this · 옵션 묶음을 치트 닻으로. 0 이면 out 의 그 셋을 채웠다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate_legacy(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)
{
    GameAddresses found = {};
    const char *why = locate_legacy(image, static_cast<size_t>(size), &found);
    if (why != nullptr) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}
```

`src/srkit/cli.py` — `cmd_locate` 를 통째로 바꾼다:

```python
def cmd_locate(cfg, _args) -> int:
    exe = cfg.game_dir / toybox.EXE_NAME
    data = exe.read_bytes()
    stamp = int.from_bytes(data[int.from_bytes(data[0x3C:0x40], "little") + 8:][:4], "little")
    print(f"{exe.name}: {len(data):,} 바이트, PE TimeDateStamp {stamp:#x}")
    if not toybox.output(cfg).is_file():
        print("ToyBox DLL 이 없습니다 — srkit toybox-build")
        return 1
    found = toybox.locate(cfg)
    print(f"새 찾기 — 게임 상태를 읽는 주소(서명. 내장 치트와 무관하다): {found.ms:.0f} ms")
    for row in found.rows:
        mark = "한 번" if row.count == 1 else "안 맞음" if row.count == 0 else "여러 번"
        print(f"  {row.name:<15} {mark:<5} 자리 {row.at:#010x} → {row.value:#010x}  {row.text}")
    if found.state is None:
        print(f"찾지 못했습니다: {found.state_why}")
        print("ToyBox 는 이 빌드에서 게임을 읽지 못합니다. uv run srkit sig-mine <RVA> 로 서명을 다시 뽑습니다(docs/11).")
    else:
        for name in toybox.STATE_FIELDS:
            print(f"  {found.state[name]:#010x}  {toybox.ADDRESS_NAMES[name]}")
    print("옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):")
    if found.legacy is None:
        print(f"  찾지 못했습니다: {found.legacy_why}")
        print("  내장 치트로 도는 기능은 글쇠 방식으로 동작합니다(docs/10).")
    else:
        for name in toybox.LEGACY_FIELDS:
            print(f"  {found.legacy[name]:#010x}  {toybox.ADDRESS_NAMES[name]}")
    if found.state is not None and found.legacy is not None:
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if found.state is not None else 1
```

- [ ] **Step 9: 빌드하고 테스트가 통과하는 것을 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -n 3`
Expected: 빌드 완료, 이어서 `55 passed` (54 − 지운 14 + 새 15)

빌드가 `C4505`(쓰이지 않는 함수)로 실패하면 Step 6 에서 지울 것을 덜 지운 것이다.

- [ ] **Step 10: `srkit locate` 를 돌려 본다**

Run: `uv run srkit locate`
Expected: `새 찾기 — … : N ms` 아래에 서명 21줄이 모두 `한 번`, 이어서 일곱 주소(`0x00f19634  멀티플레이 표시(byte)` …), `옛 찾기 — …` 아래에 셋(`0x00522330  명령 처리 함수` …), 끝 줄 `모두 찾았습니다.` **N 을 적어 둔다**(Task 6 의 문서에 쓴다).

- [ ] **Step 11: 전체 테스트, 커밋, PR 올리기(머지는 아직)**

Run: `uv run pytest -q 2>&1 | tail -n 3`
Expected: `233 passed` (232 + 1)

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/exports.cpp src/srkit/toybox.py src/srkit/cli.py tests/toybox_fake_exe.py tests/test_toybox_game.py && git commit -q -F - <<'EOF'
feat: ToyBox — 게임 상태를 치트와 무관한 서명으로 읽는다. 옛 찾기는 셋만 남긴다

게임 상태(진행 중 여부, 플레이어, 나라 목록)의 주소를 새 찾기(locate_state)에서 얻는다.
치트 문자열을 닻으로 쓰는 옛 찾기는 아직 내장 치트로 도는 기능의 직접 실행이 쓰는
명령 처리 함수 · this · 옵션 묶음만 찾는다(locate_legacy — 전환 기간에만).
게임이 치트를 없애도 상태는 읽는다: 그때 옮기지 않은 기능만 글쇠 방식이 된다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin feat/toybox-locate-independent
```

PR 본문(스크래치에 Write 도구로 `pr-locate.md`): 무엇을 바꿨나(새 찾기 = 서명 21개, 상태 읽기의 주소 출처, 옛 찾기 축소, `srkit locate` 의 출력), 요구 3 과의 관계(상태 읽기는 치트에서 떨어졌다 / 남은 치트 의존은 25개 기능의 실행 경로뿐이다), 서명 표(찾을 것 · 서명 글 · build 21347933 에서 맞는 자리), `uv run pytest` 결과, "게임 안 확인(V0)은 이 PR 의 댓글로 더한다", 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-locate-independent --title "feat: ToyBox — 게임 상태를 내장 치트와 무관한 서명으로 읽는다" --body-file "<스크래치>/pr-locate.md"
```

---

### Task 5: 게임 안 확인 (V0) — 새 찾기로 읽은 상태가 2단계와 같은가

**브랜치:** `feat/toybox-locate-independent` (바꾸지 않는다 — 게임이 떠 있는 동안 브랜치를 바꾸면 `gamedrive.py` 가 바뀐다)

**Files:** 코드 없음. 근거 화면과 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.

**Interfaces:**
- Consumes: Task 4 의 빌드(`build/toybox/srtoybox.dll`), 로그의 줄.
- Produces: V0 의 결과(Task 6 이 `docs/10` 에 적는다), PR 의 댓글.

- [ ] **Step 1: 시험용 빌드를 게임 폴더에 바꿔 넣는다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

- [ ] **Step 2: 검증 전의 상태를 적어 둔다**

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-v0 && rm -f build/verify/toybox-home-v0/* && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/V0-saves-before.txt && cat build/verify/toybox/V0-saves-before.txt
```

`build/verify/toybox-home-v0` 는 검증용 게임의 ToyBox 설정 폴더다(비어 있으므로 단축키는 기본값 `Ctrl+Shift+T`). 사용자의 `%APPDATA%\SR2030ToyBox` 는 건드리지 않는다.

- [ ] **Step 3: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)를 게임에서 확인한다. 이 작업(V0)만 수행하라.
끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다).
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법)과 E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법"을 읽는다.

규칙:
- 게임은 다음으로만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-v0' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|stop> …
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간을 흘리지 않는다(일시 정지인 채로 둔다).
- cheat resettutorial · cheat depopulate 는 어떤 경우에도 넣지 않는다.
- 화면은 E:\SR2030ToyBox\build\verify\toybox\V0-<번호>-<이름>.png 로 찍는다.
- ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-v0\toybox.log 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다):
1. 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다(20초쯤. 빈 화면이면 기다렸다 다시 찍는다).
   로그에서 "게임 상태를 읽습니다 (서명 21개 가운데 …개, … ms)" 줄과 "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (명령 처리 함수 +0x…)" 줄을 그대로 옮겨 적는다.
   이 줄이 없고 "게임 상태를 읽을 수 없습니다 (…)" 가 있으면 그 줄을 옮겨 적고, 2 만 하고 게임을 끈 뒤 보고한다.
2. 메인 메뉴에서 key CTRL+SHIFT+T 로 ToyBox 창을 연다. 창 맨 위의 상태 줄의 글과, "돈" 탭의 단추가 흐린지(꺼져 있는지)를 적는다.
   "국고 +$10 B" 단추를 한 번 누른다. 로그에 새 줄이 생겼는지 적는다(생기면 안 된다).
3. 창을 닫고(같은 글쇠), 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 게임 화면이 뜨면 일시 정지 상태인지 본다.
4. ToyBox 창을 연다. 상태 줄의 글을 적는다(기대: "플레이 중: 독일 (1499)").
5. "외교·영토" 탭을 연다. 목록에 나라들이 보이는지, 검색란에 pol 을 넣으면 무엇이 남는지 적는다. 폴란드를 고르고 "관계 최고"를 누른다.
   로그의 새 줄을 옮겨 적는다(기대: "직접 실행: cheat love 1106"). 게임의 설정 창(빨간 제목의 창)이 떴는지 적는다(뜨면 안 된다).
6. "돈" 탭의 "국고 +$10 B" 를 누른다. 로그의 새 줄을 옮겨 적는다(기대: "직접 실행: cheat georgew").
7. ToyBox 창을 닫고, 게임의 메뉴(ESC) → "게임 종료" → 저장하지 않고 메인 메뉴로 나온다. ToyBox 창을 열어 상태 줄의 글을 적는다.
8. gamedrive.py stop 으로 게임을 끈다. gamedrive.py status 로 꺼진 것을 확인한다.
9. 로그를 E:\SR2030ToyBox\build\verify\toybox\V0.log 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). 로그에 "예외" 가 든 줄이 있으면 그대로 옮긴다. 보지 못한 것은 "보지 못했다"와 까닭.
기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않는다. Task 6 의 문서 초안은 써도 된다(커밋은 브랜치를 바꿔야 하므로 에이전트가 끝난 뒤에).

- [ ] **Step 4: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "게임 상태를\|옛 방식\|명령 처리 함수를 찾지\|직접 실행\|예외" build/verify/toybox/V0.log; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/V0-saves-before.txt && echo "저장 폴더 그대로"
```

Expected:
- `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)` 한 줄(게임을 한 번 띄웠으므로), `옛 방식(내장 치트)으로 도는 기능이 25개 남아 있습니다 (명령 처리 함수 +0x522330)` 한 줄.
- `직접 실행: cheat love 1106` 과 `직접 실행: cheat georgew` 가 한 줄씩. `예외` 가 든 줄이 없다.
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-locate-independent` 다. `저장 폴더 그대로`.

Read 도구로 화면 셋을 직접 본다: 메뉴에서의 상태 줄(2), 게임 안의 상태 줄(4), 메뉴로 돌아온 뒤의 상태 줄(7). 에이전트가 적은 글과 화면이 같은지 본다.

**서명이 21개가 아니거나 "게임 상태를 읽을 수 없습니다"가 나오면**(파일에서는 맞는데 올라온 게임에서는 맞지 않는다 — 설계서의 "아직 보지 않은 것" 6): 멈추고 사용자에게 그 줄을 그대로 알린다. 머지하지 않는다.

- [ ] **Step 5: Steam 으로 띄운 게임에서 로그를 본다 (한 번)**

채팅에 먼저 알린다: "Steam 으로 게임을 한 번 띄웁니다. 화면 크기 창으로 뜨고 시작하는 동안 포커스를 가져갑니다. 메인 메뉴에서 로그와 상태 줄만 보고 바로 끕니다."

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py steam
```

(백그라운드 작업으로. 메인 메뉴가 그려질 때까지 기다린다.) Steam 으로 띄운 게임은 사용자의 실제 설정 폴더(`%APPDATA%\SR2030ToyBox`)를 읽는다 — **설정을 바꾸지 않는다**(단축키도 거기 적힌 것을 쓴다).

```bash
tail -n 12 "$APPDATA/SR2030ToyBox/toybox.log" | tee /e/SR2030ToyBox/build/verify/toybox/V0-steam.log; grep -n "^hotkey" "$APPDATA/SR2030ToyBox/toybox.ini"
```

Expected: `화면에 끼어들었습니다 (다른 훅이 먼저 있습니다)` 와 `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`. 그 설정의 단축키(`gamedrive.py key <글쇠>`)로 창을 열어 `shot build/verify/toybox/V0-steam-menu.png` — 상태 줄이 `게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다`. 창을 닫고 `uv run python scripts/gamedrive.py stop`, 이어서 `status` 로 꺼진 것을 본다.

Steam 이 꺼져 있거나 게임이 뜨지 않으면 "보지 못했다"로 적고 넘어간다(다시 시도하지 않는다).

- [ ] **Step 6: 결과를 PR 에 적고 머지한다**

스크래치에 `v0.md` 를 쓴다(Write 도구): V0 의 단계마다 한 것 / 본 것 / 근거 화면의 이름, 로그의 줄 그대로, 서명을 맞추는 데 걸린 시간(화면 밖 게임 · Steam), 보지 못한 것.

```bash
gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/v0.md"
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge
```

머지가 거부되면 Global Constraints 대로 한다. 머지된 뒤: `git switch develop && git pull --ff-only origin develop`

---

### Task 6: 문서

**브랜치:** `docs/toybox-locate-independent` (`develop` 에서. Task 5 의 PR 이 들어간 뒤)

**Files:**
- Modify: `docs/11-game-internals.md`, `docs/10-toybox.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: Task 4 Step 10 의 걸린 시간, Task 5 의 V0 결과(본 것과 보지 못한 것).
- Produces: 문서. 계획 (나)가 `docs/10` 의 기능 표 · 한계 · 확인한 것에 이어 쓴다.

게임에서 보지 않은 것을 [확인]으로 쓰지 않는다. V0 에서 본 것만 [확인: 게임] / [확인: 실행]으로, 나머지는 "보지 못했다"로 적는다.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-locate-independent
```

- [ ] **Step 2: `docs/11-game-internals.md` — "주소를 찾는 법"을 다시 쓴다**

`## 주소를 찾는 법 (`locate`)` 부터 `## 이번에 알게 된 치트의 사실 [확인: 정적]` 바로 앞까지를 다음으로 바꾼다. `<N>` 은 Task 4 Step 10 에서 적어 둔 값, `<V0 …>` 는 Task 5 에서 본 것이다(보지 못했으면 그 문장을 "올라와 있는 게임에서는 보지 못했다"로 쓴다).

```markdown
## 주소를 찾는 법 (`locate`)

ToyBox 는 주소를 코드에 적어 두지 않는다. 게임이 뜰 때 올라와 있는 실행 파일에서 찾는다(`native/srtoybox/locate.cpp`).
같은 코드를 `uv run srkit locate` 가 설치된 파일에 대고 돌린다. 찾는 길은 둘이다.

### 새 찾기 — 게임 상태를 읽는 전역 일곱 (3단계 1부터)

**내장 치트와 무관하다.** 치트 문자열도 치트 명령 처리 함수의 코드도 쓰지 않는다 — 게임이 업데이트로 치트를 없애도 ToyBox 는 게임을 읽는다
(사용자의 요구, 2026-10-09: 모드의 모든 기능은 게임의 내장 치트와 완전히 별도로 동작한다).

- **서명**(`native/srtoybox/sigs.h`)은 명령 몇 개의 바이트 꼴이다. `[rip]` 은 읽어 낼 주소(4바이트 rip 상대 거리)이고, `[rip+1]` · `[rip+4]` 는
  그 4바이트 뒤에 상수 1 · 4바이트가 더 있고 명령이 끝난다는 뜻이다. `?` 는 아무 바이트다.
- 서명은 실행 구역 전체에서 **정확히 한 번** 맞을 때만 "맞았다"다. 한 번도 안 맞거나 두 번 이상 맞으면 맞지 않은 것이다.
- 찾을 것마다 **서로 다른 함수에서 뽑은 서명 셋**을 둔다. **둘 이상이 맞고, 맞은 것이 모두 같은 주소**를 내야 "찾았다"다.
  값이 갈리면 못 찾은 것이다 — 다수결로 고르지 않는다.
- 일곱 가운데 하나라도 못 찾으면 ToyBox 는 게임을 읽지 못한다(내장 치트로 도는 기능은 글쇠 방식으로 동작한다).

| 찾을 것 | 서명 | 맞는 자리 (든 함수) |
|---|---|---|
| 멀티플레이 표시 | `80 3D [rip+1] 00 74 18 8B 47 3C` | `0x4c3f14` (`0x4c3e30`) |
| | `80 3D [rip+1] 00 0F B6 FA 74 47` | `0x51c216` (`0x51c210`) |
| | `80 3D [rip+1] 00 74 13 8B 41 14` | `0x52a8f4` (`0x52a8f0`) |
| 프로그램 상태 | `83 3D [rip+1] 01 75 08 48 8B CB` | `0x52fd15` (`0x52fcc0`) |
| | `83 3D [rip+1] 06 48 8B F2 4C 8B F9` | `0x688739` (`0x688720`) |
| | `C7 05 ? ? ? ? 02 00 00 00 C7 05 [rip+4] 01 00 00 00` | `0x735b6e` (`0x735b30`) — 게임 진입 |
| 모드 상태 | `83 3D [rip+1] 02 48 8B D9 75 40` | `0x4f2996` (`0x4f2990`) |
| | `83 3D [rip+1] 00 48 8B D9 75 21` | `0x6a7b7f` (`0x6a7b70`) |
| | `C7 05 [rip+4] 02 00 00 00 C7 05 ? ? ? ? 01 00 00 00` | `0x735b6e` (`0x735b30`) — 위와 같은 자리의 앞 명령 |
| 플레이어 지역의 인덱스 | `44 3B 05 [rip] 49 63 C8 74 16` | `0x93db9` (`0x85290`) |
| | `44 8B 35 [rip] 45 84 ED 74 05` | `0x502e83` (`0x502d50`) |
| | `44 8B 0D [rip] 45 33 C0 33 D2` | `0x57d65e` (`0x5391a0`) |
| 플레이어 지역 객체의 포인터 | `48 8B 15 [rip] 8B 42 6C 85 C0` | `0x4c3c1f` (`0x4c3bc0`) |
| | `48 8B 0D [rip] 48 85 C9 74 58` | `0x4e3db0` (`0x4e37e0`) |
| | `4C 8B 35 [rip] FF C7 3B 7D 38` | `0x6d14c2` (`0x6d0d80`) |
| 지역 포인터 표 | `4C 8D 05 [rip] 49 8B 10 48 85 D2` | `0xbe8a0b` (`0xbe8760`) |
| | `48 8D 0D [rip] 90 48 8B 31 48 85 F6` | `0x69fe98` (`0x69e490`) |
| | `48 8D 0D [rip] 48 8B 0C C1 48 85 C9` | `0x6d7407` (함수 표에 없는 작은 함수) |
| 지역 수 | `44 8B 35 [rip] 44 8B DF 8B D6` | `0x812ef` (`0x810d0`) |
| | `44 8B 0D [rip] 8B D7 45 85 C9` | `0x83342` (`0x82cb0`) |
| | `44 8B 15 [rip] 43 8D 04 0C 99` | `0x916b0` (`0x85290`) |

- [확인: 정적] 서명 21개가 저마다 실행 구역(12.8 MB)에 한 번만 맞고, 맞은 자리가 모두 치트 명령 처리 함수(`0x522330` – `0x5284fd`) 밖이며,
  읽어 낸 주소가 위 "전역과 필드"의 값과 같다. 자동 테스트가 설치된 실행 파일에서 이것을 보고, 치트 코드에서 읽은 값(2단계의 방식)과도 대조한다
  (`tests/test_toybox_game.py`, `tests/toybox_cheat_oracle.py` — 치트 코드를 보는 것은 테스트뿐이다).
- 서명을 맞추는 데 설치된 파일에서 <N> ms 가 걸렸다(실행 구역을 한 번 훑는다). <V0: 올라와 있는 게임에서 본 줄 — 화면 밖 게임과 Steam 으로 띄운 게임의 "서명 21개 가운데 …개, … ms">
- 지역 객체 안의 자리(`+0` `+4` `+8`)는 서명으로 찾지 않는다. 읽을 때마다 "서로 맞을 것"으로 거른다(위 "값의 흐름").
- 다른 빌드에서는 돌려 보지 못했다(이 빌드 하나뿐이다) [추정: 함수가 다시 컴파일되면 서명이 깨질 수 있다. 셋 가운데 둘이면 된다].

**서명을 다시 뽑는 법**(게임이 업데이트되어 `uv run srkit locate` 에 "안 맞음" · "여러 번"이 나올 때): 새 빌드에서 그 전역의 주소를 알아낸 뒤
(맞은 서명이 하나라도 있으면 그것이 낸 주소다) `uv run srkit sig-mine <RVA>` 를 돌린다. 치트 명령 처리 함수 밖의 코드에서, 한 번만 맞는
가장 짧은 서명(명령 셋 · 정해진 바이트 여덟 개 이상)을 함수별로 낸다. 서로 다른 함수의 것 셋을 골라 `native/srtoybox/locate.cpp` 의 표 `STATE` 에
옮기고, 이 표와 `tests/test_toybox_game.py` 의 기대값을 고친다.

### 옛 찾기 — 치트 명령 처리 함수와 그 둘레 (전환 기간에만)

아직 내장 치트로 도는 기능의 직접 실행이 쓰는 셋이다. `"cheat allowcheats"` 문자열을 닻으로 찾는다. 3단계의 마지막 묶음에서
직접 실행 · 글쇠 방식과 함께 지운다([10](10-toybox.md)).

| 찾을 것 | 절차 |
|---|---|
| 명령 처리 함수 | `"cheat allowcheats\0"`(읽기 전용 자료에 1개) → 그것을 가리키는 `lea r,[rip+d]`(1곳) → 그 자리가 든 함수 표 항목 → chained unwind 의 뿌리 |
| 옵션 묶음 | 함수 머리(0x60 바이트 안)의 `83 0D d32 40` |
| `this` | 함수를 부르는 `E8 rel32`(1곳) 바로 앞의 `48 8D 0D d32` |

대조 — 하나라도 어긋나면 "못 찾았다"이고, 내장 치트로 도는 기능은 글쇠 방식으로 동작한다(게임 상태 읽기에는 영향이 없다):

1. 닻 문자열이 1개이고 그것을 쓰는 자리가 1곳이다.
2. 함수 머리에 `or …,40h` 가 있다.
3. 함수를 부르는 곳이 1곳이고 바로 앞이 `lea rcx,[rip+d]` 다.
4. 찾은 주소가 모두 이미지 안에 있다.

```

- [ ] **Step 3: `docs/10-toybox.md` 를 고친다**

(가) "## 무엇인가"의 `게임이 업데이트되어 ToyBox 가 게임을 읽지 못하게 되면 …` 로 시작하는 단락 **위**에 단락을 더한다:

```markdown
**3단계(진행 중)**: 사용자의 요구가 하나 더해졌다(2026-10-09) — **모드의 모든 기능은 게임의 내장 치트와 완전히 별도로 동작한다.**
기능을 묶음별로 내장 치트에서 떼어 내는 중이고([설계](superpowers/specs/2026-10-09-toybox-stage3-1-design.md)에 여덟 묶음의 표가 있다),
옮기지 않은 기능은 옮길 때까지 지금처럼 내장 치트로 동작한다. **지금까지 옮긴 것: 게임 상태 읽기**(진행 중 여부 · 플레이어 · 나라 목록) —
주소를 치트 문자열이 아니라 치트와 무관한 코드의 서명으로 찾는다([11](11-game-internals.md)). 아래 표의 기능 25개는 아직 모두 내장 치트로 돈다.
```

(나) "## 구조"의 파일 표에서 `locate` 줄을 바꾸고 그 위에 `sigs` 줄을 더한다:

```markdown
| `sigs` | 서명(명령 몇 개의 바이트 꼴)으로 주소 읽기: 맞추기와 투표(순수 함수) |
| `locate` | 올라와 있는 실행 파일에서 주소 찾기(순수 함수). 새 찾기 = 게임 상태의 전역 일곱(서명), 옛 찾기 = 명령 처리 함수 · `this` · 옵션 묶음(치트 닻. 전환 기간에만). `srkit locate` 도 이 코드를 쓴다 |
```

(다) 같은 절의 `- **실행 파일의 주소를 적어 두지 않는다.**` 항목을 통째로 바꾼다:

```markdown
- **실행 파일의 주소를 적어 두지 않는다.** 화면은 임시 swap chain 에서 가상 함수 표의 주소를 얻어 `Present` 의 칸을 바꾼다. 게임 상태를 읽는
  전역 일곱은 게임이 뜰 때 **치트와 무관한 코드의 서명**으로 찾는다 — 찾을 것마다 서명 셋 가운데 둘 이상이 정확히 한 번 맞고 같은 주소를 내야 한다.
  아직 내장 치트로 도는 기능이 쓰는 명령 처리 함수와 그 둘레의 둘은 `"cheat allowcheats"` 문자열을 닻으로 찾는다(전환 기간에만).
  찾지 못했거나 읽다가 예외가 나면(읽을 수 없는 쪽) 못 찾은 것으로 친다([11](11-game-internals.md)).
```

(라) "## 문제가 생기면"의 로그 표에서 `게임 상태를 읽습니다 (명령 처리 함수 +0x…)` 줄과 `게임 상태를 읽을 수 없습니다 (<까닭>) — 글쇠 방식` 줄을 다음 넷으로 바꾼다:

```markdown
| `게임 상태를 읽습니다 (서명 21개 가운데 N개, M ms)` | 게임 상태의 주소를 찾았다. 상태 줄과 단추 끄기가 동작한다. N 이 21 보다 작으면 서명 몇 개가 이 빌드에서 깨진 것이다(`uv run srkit locate` 가 어느 것인지 알려 준다) |
| `게임 상태를 읽을 수 없습니다 (<무엇>: 서명 3개 가운데 1개) — 글쇠 방식` | 그 주소를 찾지 못했다(게임이 바뀌었다). 내장 치트로 도는 기능은 1단계처럼 동작한다. `<무엇>: 서명들이 서로 다른 주소를 냅니다` 도 같은 뜻이다 |
| `옛 방식(내장 치트)으로 도는 기능이 N개 남아 있습니다 (명령 처리 함수 +0x…)` | 직접 실행이 동작한다. 괄호 안은 찾은 함수의 자리(build `21347933` 에서 `+0x522330`). N 은 아직 내장 치트에서 떼어 내지 않은 기능의 수다 |
| `명령 처리 함수를 찾지 못했습니다 (<까닭>) — 내장 치트로 도는 기능은 글쇠 방식` | 게임 상태는 읽지만(단추는 게임 밖에서 꺼진다) 치트 명령 처리 함수를 찾지 못했다 — 게임이 치트를 바꿨거나 없앴다 |
```

(마) "## 한계"의 `- **게임이 업데이트되면 ToyBox 가 게임을 읽지 못할 수 있다.**` 항목을 통째로 바꾼다:

```markdown
- **게임이 업데이트되면 ToyBox 가 게임을 읽지 못할 수 있다.** 서명이 깨지면(찾을 것 하나에서 셋 가운데 둘 이상) 상태 줄에 "읽을 수 없습니다"가 뜨고
  내장 치트로 도는 기능은 글쇠 방식으로 동작하며, "외교·영토" 탭과 "내 나라 지지율"은 쓸 수 없다(나라 목록과 내 번호를 모른다).
  게임이 치트만 없앤 경우에는 게임 상태는 계속 읽는다 — 내장 치트로 도는 기능만 동작하지 않는다(글쇠로 넣어도 게임이 받지 않는다) [추정: 그런 빌드를 만나지 못했다.
  자동 테스트는 치트 문자열이 없는 가짜 이미지로 본다]. `uv run srkit locate` 가 무엇이 어긋났는지 알려 준다([11](11-game-internals.md)). 다른 빌드에서는 돌려 보지 못했다.
```

(바) "## 확인한 것"에서 `- H15 ~ H19 는 백그라운드 에이전트가 눌러 보고, …` 로 시작하는 항목 **위**에 표를 더한다. "본 것"은 Task 5 에서 본 것을 그대로 적는다 — 아래의 글은 기대이지 결과가 아니다. 보지 못한 것은 "보지 못했다"와 까닭을 적는다.

```markdown
3단계 1 (가) — 게임 상태를 새 찾기(서명)로 읽게 바꾼 빌드로 본 것(<날짜>, 같은 방법. 일시 정지 상태):

| # | 한 것 | 본 것 | 근거 화면 |
|---|---|---|---|
| V0-1 | 화면 밖에서 띄움 | 로그에 `<본 줄 그대로: 게임 상태를 읽습니다 (서명 21개 가운데 …개, … ms)>` 와 `<본 줄 그대로: 옛 방식(내장 치트)으로 도는 기능이 …>` | – |
| V0-2 | 메인 메뉴에서 창을 열고 "국고 +$10 B"를 누름 | <상태 줄의 글, 단추가 꺼져 있는지, 로그에 줄이 생겼는지> | `V0-…` |
| V0-3 | 게임에 들어가 창을 엶 | <상태 줄의 글> | `V0-…` |
| V0-4 | "외교·영토" 탭에서 `pol` 을 검색하고 폴란드를 골라 "관계 최고" | <목록, 로그의 줄, 게임의 설정 창이 떴는지> | `V0-…` |
| V0-5 | "국고 +$10 B" | <로그의 줄> | `V0-…` |
| V0-6 | 게임 메뉴 → "게임 종료"(저장하지 않음)로 메인 메뉴에 나옴 | <상태 줄의 글> | `V0-…` |
| V0-S | Steam 으로 띄움 | <로그의 줄, 메인 메뉴에서의 상태 줄, 스스로 끝났는지> | `V0-steam-menu` |
```

(사) "## 다음 단계"의 표를 통째로 바꾼다:

```markdown
3단계는 기능을 내장 치트에서 떼어 내면서 사용자가 요구한 세분화를 더한다. 묶음의 표와 결정 사항은
[3단계 1 설계](superpowers/specs/2026-10-09-toybox-stage3-1-design.md)에 있다.

| 묶음 | 내용 | 상태 |
|---|---|---|
| 1 (가) | 내장 치트와 무관한 주소 찾기(서명), 게임 상태 읽기를 그것으로 | 끝 |
| 1 (나) | 값 쓰기. 돈 · 물자: 국고 −/0/+ · 최소 유지, 물자별 재고 −/0/+ · 최소 유지 | 다음 |
| 2 ~ 6 | 나머지 기능의 분리(값 쓰기 넷, 연구, 인구 · 외교 · 영토, 부대, 화면 · 진행)와 세분화 | – |
| 7 | 배율(세금/지출, 국방비, 물자 생산 · 소비, 연구 속도) | – |
| 끝 | 치트 경로 제거(직접 실행, 글쇠 방식, 옛 찾기) | – |
```

- [ ] **Step 4: `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md` 를 고친다**

`docs/09-cheat-mod-plan.md` "## 로드맵"의 3 · 4 · 5번을 바꾼다:

```markdown
3. **ToyBox 3단계 (진행 중).** 모든 기능을 내장 치트에서 떼어 내고(사용자의 요구, 2026-10-09), 돈 · 물자 · 연구 · 부대를 세분화한다 —
   여덟 묶음([설계](superpowers/specs/2026-10-09-toybox-stage3-1-design.md)). 첫 묶음의 앞 절반(치트와 무관한 주소 찾기)이 끝났다 — [10](10-toybox.md).
4. **(3단계 뒤)** GDP 와 장비 수치처럼 내장 치트가 처음부터 없던 값.
5. **(업데이트가 오면)** `srkit cheats-check` → `srkit locate`(서명이 아직 맞는가, 치트 명령 처리 함수가 남아 있는가) → 깨진 서명은 `srkit sig-mine` 으로 다시 뽑고([11](11-game-internals.md))
   → 달라진 치트를 게임에서 다시 넣어 보고 [07](07-cheats.md) 갱신 → `srkit inventory` 로 형식 변화 확인 → ToyBox 가 뜨는지 확인.
```

`README.md` "현재 상태"의 ToyBox 문단(`셋째로 **ToyBox** …` 로 시작) 끝에 문장을 더한다:

```markdown
3단계(진행 중, 2026-10-09 ~)에서는 모든 기능을 게임의 내장 치트에서 떼어 낸다 — 첫걸음으로 게임 상태 읽기가 치트와 무관한 코드의 서명으로 주소를 찾게 됐다.
```

`CLAUDE.md` "명령"의 `- **게임이 업데이트된 뒤에는** …` 항목을 통째로 바꾼다:

```markdown
- **게임이 업데이트된 뒤에는** `uv run srkit cheats-check`(내장 치트가 문서와 같은가) → `uv run srkit locate`(ToyBox 의 서명이 아직 맞는가) →
  `uv run srkit inventory`(데이터 형식이 바뀌었는가)부터 돌린다. 서명이 깨졌으면 `uv run srkit sig-mine <RVA>` 로 다시 뽑는다
  ([docs/09](docs/09-cheat-mod-plan.md)의 "게임 업데이트 대비", [docs/11](docs/11-game-internals.md)의 "주소를 찾는 법").
```

`CLAUDE.md` "지켜야 할 것"의 끝에 항목을 더한다:

```markdown
- **ToyBox 의 기능은 게임의 내장 치트와 별도로 동작해야 한다**(사용자의 요구, 2026-10-09). 새 기능과 옮긴 기능은 치트 명령 처리 함수를 부르지 않고,
  치트 문자열 · 치트 함수의 코드를 주소 찾기의 닻으로 쓰지 않으며, 못 찾았을 때 내장 치트로 되돌아가지 않는다. 치트 코드를 보는 것은 개발 중의 분석과
  자동 테스트의 대조뿐이다([설계](docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md)).
```

- [ ] **Step 5: 링크와 테스트를 확인하고 커밋, PR**

Run: `grep -n "locate_game" docs/10-toybox.md docs/11-game-internals.md README.md CLAUDE.md; grep -n "주소를 찾았다. 상태 줄과 직접 실행이 동작한다" docs/10-toybox.md; uv run pytest -q 2>&1 | tail -n 2`
Expected: 두 grep 에 나오는 줄이 없다(옛 함수 이름과 옛 로그 줄의 설명이 남아 있지 않다). `233 passed`.

```bash
cd /e/SR2030ToyBox && git add docs/10-toybox.md docs/11-game-internals.md docs/09-cheat-mod-plan.md README.md CLAUDE.md && git commit -q -F - <<'EOF'
docs: ToyBox 3단계 1 (가) — 내장 치트와 무관한 주소 찾기(서명), 게임에서 본 것(V0)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox-locate-independent
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/toybox-locate-independent --title "docs: ToyBox 3단계 1 (가) — 내장 치트와 무관한 주소 찾기" --body-file "<스크래치>/pr-docs.md"
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge
```

PR 본문(`pr-docs.md`): 고친 문서와 까닭, V0 에서 본 것과 보지 못한 것, `uv run pytest` 결과, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

---

## 끝난 뒤의 상태와 계획 (나)로 넘기는 것

- 게임 폴더에는 이 계획의 최종 빌드(`srtoybox.dll`)가 설치되어 있다. 사용자가 보는 동작은 2단계와 같다(기능 25개는 아직 모두 내장 치트로 돈다). 달라진 것은 로그의 줄과, 게임이 치트를 없앴을 때에도 게임 상태를 읽는다는 것이다.
- 계획 (나)가 이 위에 쓰는 것: `sigs`(상수 읽기 `[u32]` · `[u8]` 와 한 서명의 값 둘), `locate` 의 서명 표와 투표의 틀(값 묶음을 같은 꼴로 더한다), `srkit sig-mine`(상수 뽑기를 더한다), `tests/toybox_fake_exe.py` 의 `plant` · `state_image`, `tests/toybox_cheat_oracle.py`(국고 · 물자의 본문에서 읽는 값을 더한다).
- 계획 (나)는 이 계획이 `develop` 에 들어간 뒤, 그때의 코드를 읽고 쓴다.

