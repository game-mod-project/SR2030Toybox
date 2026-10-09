# ToyBox 3단계 1 (나) — 값 쓰기의 바탕과 돈 탭 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ToyBox 의 "돈" 탭이 내장 치트를 거치지 않고 플레이어의 국고를 직접 읽고 고친다(입력란 + 더하기 · 빼기 · 이 값으로, 빠른 단추 `-$100 B` · `-$10 B` · `$0` · `+$10 B` · `+$100 B`). 그 바탕(값의 자리를 서명으로 찾기, 읽기와 쓰기, 값 계산, 요청의 대기열)은 물자 재고까지 함께 깐다.

**Architecture:** 값의 자리 넷(세계 자료 포인터, 국고 칸, 재고 칸의 첫 자리와 간격, "쓰는 물자" 표의 첫 자리와 간격)을 계획 (가)의 서명 방식으로 찾는다(`locate_values`). `game` 이 플레이어 지역 객체의 그 칸을 `ReadProcessMemory` / `WriteProcessMemory` 로 읽고 쓰고, `values`(순수 함수)가 "지금 값 + 요청 → 쓸 값"을 셈하고, `keeper` 가 단추의 요청을 대기열에 받아 게임 창의 타이머에서 쓴다. 돈 탭은 기능 표가 아니라 전용 화면이 그리고, 국고의 치트 단추 셋은 지운다.

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Dear ImGui, Python 3.13 + ctypes + pytest + numpy + capstone(개발 의존성) (`uv run`), Win32.

**Spec:** `docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md` (승인 2026-10-09). 이 계획은 그 문서의 "작업 순서와 브랜치" **3**(값 묶음, 읽기와 쓰기, 값 계산, 요청의 대기열, 돈 탭 — 유지는 빼고, 국고의 치트 세 줄 삭제)을 구현한다. 4 · 5(물자 탭, 물자 이름표, 최소 유지, 상태 줄의 "유지 중")는 이 계획이 끝난 뒤 계획 (다)로 쓴다 — 이 계획의 게임 안 확인(V3: 직접 쓴 값을 게임이 그대로 쓰는가)이 그 전제이고, 물자 탭의 첫 일(V5 · V6: 칸과 이름의 대응)이 이 계획이 만드는 쓰기 위에 서기 때문이다.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 와 자리는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 도 구조체 안의 자리도 적지 않는다(테스트의 기대값과 문서에만) — 서명(짧은 바이트 꼴)이 읽어 낸다. 예외는 설계서가 상수로 둔 둘이다: 지역 객체 머리의 자리(`+0` · `+4` · `+8`, 2단계부터)와 재고의 칸 수 12.
- **요구 3 — 내장 치트와 별도.** 돈 탭의 어떤 동작도 치트 명령 처리 함수를 부르지 않고 글쇠를 넣지 않는다. `locate_values` · `values` · `keeper` 와 `game` 의 값 읽기 · 쓰기는 치트 문자열도 치트 코드도 쓰지 않는다. 치트 닻을 쓰는 곳은 지금의 셋 그대로다: `locate_legacy`(전환 기간), `srkit.sigmine`(서명이 치트 코드 밖임을 가리는 개발용 코드), `tests/toybox_cheat_oracle.py`(테스트의 대조).
- **무엇을 찾지 못하거나 쓰지 못할 때 내장 치트로 되돌아가지 않는다.** 돈 탭에는 까닭 한 줄만 보인다.
- **게임의 메모리에 쓰는 곳은 플레이어 지역 객체의 국고 1칸과 재고 12칸뿐이다.** 다른 지역, 다른 칸, 전역, 치트 허용 비트에는 쓰지 않는다. 쓰기 직전에 매번 다시 확인한다: 값 묶음을 찾았다 / 게임을 진행 중이다(읽은 값의 일관성 포함) / 멀티플레이가 아니다 / (재고) 그 칸이 쓰는 물자다 / 쓸 값이 유한한 수다 / 쓸 자리가 읽기 · 쓰기 쪽(`PAGE_READWRITE`)이다.
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다. (설계서의 승인이 이 바꿔 넣기의 승인을 포함한다.)
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다. 서명은 하나에 12 ~ 45바이트다. `srkit sig-mine` 의 출력은 저장소에 넣지 않는다.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다.** 한 판에서 게임 시간을 3일 넘게 흘리지 않는다(7일마다 자동 저장된다). 게임이 떠 있는 동안 브랜치를 바꾸지 않는다. **검증용 게임은 `SRTOYBOX_HOME` 을 임시 폴더로 돌려 띄운다**(사용자의 실제 `%APPDATA%\SR2030ToyBox` 를 건드리지 않는다). Steam 으로 띄우는 것은 Task 7 의 한 번, 띄우기 전에 채팅에 알린다.
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.**
- Git: `main` · `develop` 에 직접 커밋하지 않는다. `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고 `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다. **머지 명령이 권한 분류기에 거부되면 다른 형태로 우회하지 않는다** — 사용자에게 그 명령을 그대로 건네고, 머지된 뒤 `git switch develop && git pull --ff-only origin develop` 로 이어 간다.
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`.
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다.
- **창에 보이는 새 글에는 한글 · ASCII · `·` · `—` 만 쓴다.** 글꼴에는 한국어 범위의 글리프만 올라가 있다 — `→` `–` `−` 는 `?` 로 보일 수 있다(로그의 줄에도 같은 글을 쓰므로 거기서도 쓰지 않는다).
- **시작할 때의 테스트 상태**: `develop`(`b0abf1d`)에서 `uv run pytest` 235개 통과.
- **화면 검사 테스트는 드물게 흔들린다.** `tests/test_toybox.py` 가운데 검사 프로세스를 새로 띄우는 것들이, 전체 실행에서 드물게 아무것이나 하나 실패한다(이 계획의 코드로 혼자 돌린 일곱 번 가운데 두 번, 다른 무거운 일과 함께 돌린 세 번은 모두. 그 전의 코드로도 네 번 가운데 한 번). 실패한 것을 따로 돌리면 통과한다. 잡힌 한 번은 단축키를 보낸 직후 창이 그린 것의 목록에 탭이 없었다(`KeyError: 'tab:…'`) — 원인은 모른다(이 계획의 범위 밖이다). 그런 실패가 나오면 그 테스트만 다시 돌려 통과하는지 보고, 본 것을 PR 본문에 그대로 적는다. **테스트는 다른 무거운 일(서명 뽑기, 빌드)과 함께 돌리지 않는다.**

## 설계서와 달라진 곳 (계획을 쓰며)

- **계획을 한 번 더 나눈다.** (나) = 설계서의 작업 순서 3. (다) = 4 · 5(물자 탭 · 이름표 · 최소 유지 · 설정 · 상태 줄). 값의 자리 찾기와 읽기 · 쓰기 · 대기열은 물자 재고까지 (나)에서 만든다(한 단위다) — (다)는 화면과 유지 검사만 얹는다.
- **작업 순서 3 을 PR 둘로 낸다**: `feat/toybox-values-locate`(Task 1 · 2 — 게임의 메모리에 쓰지 않는다)와 `feat/toybox-values-write`(Task 3 ~ 7). 문서는 `docs/toybox-values-money`(Task 8).
- **쓴 뒤 다시 읽은 값이 다르면 한 번 더 쓰고 읽는다.** 두 번 다 다를 때만 실패로 친다. 설계서는 "다르면 값 쓰기를 끈다"고 했으나, 게임이 그 사이에 같은 칸을 고쳤을 뿐인 경우(시간이 흐르는 중의 국고)까지 이번 실행 내내 끄게 된다.
- **쓰기 전에 그 자리가 읽기 · 쓰기 쪽인지 `VirtualQuery` 로 본다.** `WriteProcessMemory` 는 실행 쪽(`PAGE_EXECUTE_READ`)이면 보호를 풀고 쓴다 — 낡은 포인터가 코드를 가리켜도 쓰지 않게 한다.
- **찾은 전역의 주소가 쓸 수 있는 자료 구역 안인지, 서로 겹치지 않는지를 본다**(상태 묶음 일곱 + 세계 자료 포인터). 계획 (가)의 최종 검토가 미룬 것이다.
- **줄임 표기는 K 에도 소수 둘째 자리를 쓴다**(`50.00 K`, `14.43 B`). 게임의 재무 패널이 그렇게 보인다(`$50.00 K` — [06](../../06-data-reference.md), `$ 14.43 B` — [10](../../10-toybox.md) H3). 설계서의 `129 K` 는 물자 표의 예였다 — 물자의 표기는 (다)에서 게임 화면을 보고 정한다.
- **화살표와 긴 빼기 기호를 쓰지 않는다**: 로그와 창의 `값 쓰기: 국고 14.43 B -> 24.43 B`, 단추 `-$100 B`. 까닭은 Global Constraints 의 글꼴 줄.
- **`srkit sig-mine` 이 빼는 치트 코드를 넓힌다**: 명령 처리 함수에 더해, 치트 코드에서만 불리는 함수들(이 빌드에서 11개 — `0x528510` 포함). 치트 문자열은 있는데 그 함수를 못 찾으면 오류로 멈춘다. 계획 (가)의 최종 검토가 미룬 것이다.
- **맞지 않은 서명의 이름을 로그에 적는다**(셋 가운데 둘로 찾았을 때도 — 다음 업데이트에서 깨질 것을 미리 안다). 〃
- **`game_init` 의 갈래를 테스트가 밟게 한다**: 찾기와 로그를 `game_init_from(base, size)` 로 떼어 가짜 이미지로 부른다("상태는 찾고 명령 처리 함수는 못 찾는" 갈래 포함). 〃
- **밖에서 게임의 메모리를 읽는 검증 명령을 저장소에 둔다**: `scripts/gamedrive.py peek`(자기가 띄운 게임만, 읽기만). V3 의 "메모리의 값 · 치트 허용 비트"를 ToyBox 자신의 표시가 아닌 것으로 본다. 2단계에서는 저장소 밖의 스크립트로 했다.
- **V3(직접 쓴 값을 게임이 그대로 쓰는가)은 돈 탭이 선 뒤(Task 7)에 본다.** 설계서는 작업 순서 3 의 "첫 일"이라 했으나, 게임 안에서 쓰려면 누를 단추가 있어야 한다. 전제는 치트 `treasury` 가 하는 일이 그 칸에 쓰는 것뿐이라는 정적 확인과 2단계의 H3(치트가 쓴 값이 다시 연 패널에 보였다)이 받친다. 전제가 틀리면 Task 7 에서 멈춘다 — 머지 전이다.
- **검증 도구가 누르는 치트 단추를 `화면·진행` 탭의 "GUI 숨기기/보이기"(`cheat fullmapshow`)로 바꾼다.** 지금까지 쓰던 "국고 +$10 B"(`cheat georgew`)가 이 계획에서 없어진다. 묶음 6 에서 옮길 기능이라 그때까지 남는다.

## 계획을 쓰며 확인한 것 [확인: 정적, build 21347933]

설치된 실행 파일을 읽기만 했다(스크래치의 스크립트. 저장소에 넣지 않았다).

- **값 묶음의 서명 12개를 정했다**(Task 2 의 표). 저마다 실행 구역에 정확히 한 번 맞고(DLL 의 `srtoybox_sig_find` 로 대조), 찾을 것마다 세 서명이 서로 다른 함수에 있고, 맞은 자리가 치트 코드의 범위 12곳 밖이다. 읽어 낸 값: 세계 자료 포인터 `0x1af5868`, 국고 칸 `+0x14B88`, 재고 `(간격 0x150, 첫 칸 +0x14DA4)`, 쓰는 물자 표 `(간격 0x84, 첫 칸 +0x18)`.
- **서명의 문맥을 봤다**: 국고의 세 자리는 기준 레지스터에서 지역 객체의 다른 필드(`+4` 의 인덱스, `+0x14B48` 의 인구 등)도 읽는다. 재고의 세 자리는 `imul r, r, 0x150` 뒤에 지역 객체 + `0x14DA4` 를 읽거나 쓴다. 쓰는 물자 표의 세 자리는 `[rip]` 로 읽은 세계 자료 포인터에 `imul r, r, 0x84` 한 것과 `+0x18` 을 더해 float 를 읽는다(둘은 바로 `comiss` · `jbe`).
- **"간격 0x84 … 0x18" 을 든 코드에는 뜻이 다른 것이 섞여 있다**(다른 구조체의 `+0x84`, 스택의 `+0x18`, 표의 첫 칸이 아니라 줄 안의 `+0x18`). 후보 25개 함수 가운데 뜻이 맞는 것은 4개였다 — 그래서 `sig-mine` 이 후보마다 명령을 함께 보이게 한다(Task 1).
- **재고의 칸 수 12 의 근거 둘**: 치트 `products` 의 본문이 `+0x14DA4 + 0x150·i` 를 `i` = 0 … 11 로 펼쳐 놓았고("쓰는가" 검사도 12번), 치트 밖의 코드(`0x69fdab`)가 물자 번호를 `cmp eax, 0Bh` / `ja` 로 거른 뒤 재고 칸으로 간다.
- **국고의 단위는 달러다**: 치트 `treasury N` 이 `N × 1000000.0`(`0xcac768` 의 float)을 그 double 에 더한다.
- **찾는 전역 여덟이 모두 `.data`(쓸 수 있는 자료 구역, `0xce0000` + `0x1225524`)에 있고 서로 겹치지 않는다.**
- **치트 코드의 범위**: 명령 처리 함수 `0x522330 – 0x5284fd` 와, 치트 코드에서만 `call` 로 불리는 함수 11개(`0x51d370` · `0x51d3c0` · `0x51d860` · `0x51e110` · `0x51e3a0` · `0x51e640` · `0x51ea70` · `0x51ed50` · `0x51f0b0` · `0x528510` · `0x6f7100`). 계획 (가)의 상태 서명 21개는 모두 그 밖이다.
- **이 계획의 코드 블록을 모두 저장소의 스크래치 사본에 옮겨 돌려 봤다**(Task 1 ~ 7. 저장소와 게임 폴더는 건드리지 않았다): DLL 이 `/W4 /WX` 로 빌드되고, 서명 · 찾기 · 값 테스트 141개(`test_sigmine` 14 · `test_toybox_sigs` 17 · `test_toybox_game` 76 · `test_toybox_values` 34)와 창 · 입력 테스트 58개(`test_toybox`)가 통과했다(뒤의 것은 Global Constraints 에 적은 흔들림이 있다). `srkit locate` 의 출력이 Task 2 Step 9 의 기대와 같다. 설치본에서 재고 서명 후보는 함수 19개에서 나온다(6초).
- **돌려 보지 못한 것**: 게임 안의 동작(Task 7 — 직접 쓴 국고를 게임이 쓰는가), `gamedrive.py peek` 의 읽기(게임이 떠 있어야 한다. 구문과 "게임이 떠 있지 않습니다"만 봤다), 단계마다의 "실패하는지 본다"(모든 Task 를 옮긴 뒤의 상태만 돌렸다).

## Review Focus

설계서가 함의하지만 그대로 두면 테스트가 밟지 않을 다섯 가지. 각 줄의 테스트를 해당 Task 에 넣었다.

1. **낡은 포인터가 읽을 수는 있지만 쓰면 안 되는 곳(읽기 전용 · 실행 쪽)을 가리킨다** → 쓰지 않고 실패로 돌아오며, 값 쓰기가 꺼지고 탭에 까닭이 보인다. 죽지 않는다. (Task 4 `test_a_slot_on_a_page_that_is_not_read_write_is_not_written`, Task 6 `test_a_failed_write_turns_the_money_tab_off_and_says_why`)
2. **단추를 누른 뒤 쓰기 전에 게임에서 나가거나 멀티플레이가 된다** → 쓰지 않고 요청을 버린다. 돌아오면 다시 된다. (Task 5 `test_requests_are_dropped_outside_a_game`, Task 6 `test_a_money_request_is_dropped_when_the_game_ends_first`)
3. **옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 온다** → 그 안에서는 쓰지 않는다. (Task 6 `test_money_is_not_written_while_the_games_handler_is_running`)
4. **지금 값이 수가 아니다(NaN · 무한대)** → 쓰지 않고 알린다. 국고가 한도 밖이어도 바닥 요청이 값을 내리지 않는다. (Task 3 `test_values_refuse_what_is_not_a_number`, Task 5 `test_a_value_that_is_not_a_number_is_left_alone`)
5. **값 묶음의 서명이 서로 맞지만 엉뚱한 것을 읽었다(국고 칸과 재고 칸이 겹친다, 간격이 4 의 배수가 아니다, 전역이 읽기 전용 구역에 있다)** → "못 찾았다"다. (Task 2 `test_values_that_do_not_add_up_are_refused`, `test_an_address_outside_the_writable_data_is_refused`)

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `src/srkit/sigmine.py` (고침) | 치트 코드의 범위(`cheat_ranges`), 상수를 읽어 내는 서명 뽑기(`mine_constants`), 후보의 명령 보이기(`listing`) | 1 |
| `src/srkit/cli.py` (고침) | `srkit sig-mine --offset`, `srkit locate` 의 값 묶음 | 1 · 2 |
| `native/srtoybox/locate.h` · `locate.cpp` (고침) | `ValueLayout`, `locate_values`, 서명 표 맞추기의 공통부, 주소의 구역 · 겹침 대조 | 2 |
| `native/srtoybox/exports.cpp` (고침) | 테스트용 내보내기 | 2 ~ 6 |
| `src/srkit/toybox.py` (고침) | `ValueLayout` 의 거울, `values_of`, `Located.values`, 빌드 목록 | 2 · 3 · 5 |
| `native/srtoybox/values.h` · `values.cpp` (새로) | 지금 값 + 요청 → 쓸 값, 줄임 표기 — 순수 함수 | 3 |
| `native/srtoybox/game.h` · `game.cpp` (고침) | 값 읽기 · 쓰기, 값을 쓸 수 없는 까닭, `game_init_from` | 4 |
| `native/srtoybox/keeper.h` · `keeper.cpp` (새로) | 값 쓰기 요청의 대기열 | 5 |
| `native/srtoybox/runner_win.h` · `runner_win.cpp` (고침) | `runner_calling` | 5 |
| `native/srtoybox/input.cpp` (고침) | 타이머에서 `keeper_tick` | 6 |
| `native/srtoybox/features.cpp` (고침) | 국고의 치트 세 줄 삭제(25 → 22줄) | 6 |
| `native/srtoybox/settings.h` · `settings.cpp` (고침) | `money.amount` | 6 |
| `native/srtoybox/ui.cpp` (고침) | 돈 탭, 바닥의 "마지막으로 쓴 값" | 6 |
| `scripts/gamedrive.py` (고침) | `peek` — 자기가 띄운 게임의 메모리 읽기(검증용) | 7 |
| `tests/toybox_fake_exe.py` · `toybox_fake_game.py` · `toybox_cheat_oracle.py` · `toybox_overlay_probe.py` (고침) | 가짜 이미지 · 가짜 게임 · 대조 · 창 검사 | 2 · 4 · 6 |
| `tests/test_sigmine.py` · `test_toybox_game.py` · `test_toybox.py` (고침), `tests/test_toybox_values.py` (새로) | 테스트 | 1 ~ 6 |
| `docs/10` · `docs/11` · `docs/09` · `README.md` · `CLAUDE.md` (고침) | 문서 | 8 |

---

### Task 1: 서명 뽑기 — 상수와 치트 코드의 범위 (`srkit sig-mine --offset`)

**브랜치:** `feat/toybox-values-locate` (`develop` 에서 나눈다)

**Files:**
- Modify: `src/srkit/sigmine.py` (머리의 import, `mine_address` 의 `exclude`, 파일 끝에 덧붙임)
- Modify: `src/srkit/cli.py:188-202` (`cmd_sig_mine`), `:294-298` (파서)
- Test: `tests/test_sigmine.py`

**Interfaces:**
- Consumes: 계획 (가)의 `sigmine.Image` · `handler_range` · `count` · `Candidate` · `best_per_function` · `_md` · `ANCHOR`.
- Produces:
  - `sigmine.cheat_ranges(image: Image) -> list[tuple[int, int]]` — 명령 처리 함수가 맨 앞. 치트가 없으면 `[]`. 닻은 있는데 함수를 못 찾으면 `LookupError`.
  - `sigmine.mine_constants(image, constants: list[int], *, exclude: Sequence[tuple[int, int]] = (), fewest=3, most=9, fixed=8, longest=60, within=4, sites=400) -> list[Candidate]`
  - `sigmine.mine_address(…, exclude: Sequence[tuple[int, int]] = (), …)` — **`exclude` 가 범위 하나에서 범위들로 바뀐다.**
  - `sigmine.listing(image, candidate) -> str`
  - `uv run srkit sig-mine <값> [<값>] [--offset] [--limit N] [--sites N]` (`args.values: list[str]`, `args.offset: bool`)

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-values-locate && uv run pytest -q 2>&1 | tail -3
```

Expected: `235 passed` (건너뛴 것이 있으면 그 수도 적어 둔다).

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_sigmine.py` 의 `test_mining_skips_the_excluded_range` 를 다음으로 바꾼다(`exclude` 가 범위들이 된다):

```python
def test_mining_skips_the_excluded_ranges(image):
    """치트 코드에서는 서명을 뽑지 않는다. 뺄 범위는 여럿일 수 있다."""
    assert [c.at for c in sigmine.mine_address(image, G, exclude=[(0x1000, 0x1040)])] == [0x1040, 0x1100]
    assert [c.at for c in sigmine.mine_address(image, G, exclude=[(0x1000, 0x1040), (0x1100, 0x1140)])] == [0x1040]
```

같은 파일의 `test_mining_the_installed_game_stays_out_of_the_cheat_handler` 와 `test_srkit_sig_mine_prints_candidates` 를 다음으로 바꾼다:

```python
def test_mining_the_installed_game_stays_out_of_the_cheat_code(cfg, game_dir):
    """build 21347933: 플레이어 포인터를 쓰는 코드에서, 치트 코드 밖의 서로 다른 함수 셋 이상에서 후보가 나온다."""
    image = sigmine.Image(installed(game_dir))
    cheats = sigmine.cheat_ranges(image)
    assert cheats[0] == (0x522330, 0x5284FD)                              # 명령 처리 함수가 맨 앞이다
    assert (0x528510, 0x52853E) in cheats and len(cheats) == 12           # 치트 코드에서만 불리는 함수 11개
    picks = sigmine.best_per_function(sigmine.mine_address(image, 0x18295F8, exclude=cheats, sites=40))
    assert len(picks) >= 3
    assert all(sigmine.count(image, c.text) == 1 and not any(a <= c.at < z for a, z in cheats) for c in picks)


def test_mining_constants_on_the_installed_game(cfg, game_dir):
    """build 21347933: 재고 칸의 간격과 첫 자리를 함께 읽어 내는 서명이 치트 코드 밖의 서로 다른 함수 셋 이상에서 나온다."""
    image = sigmine.Image(installed(game_dir))
    cheats = sigmine.cheat_ranges(image)
    picks = sigmine.best_per_function(sigmine.mine_constants(image, [0x150, 0x14DA4], exclude=cheats, sites=40))
    assert len(picks) >= 3
    assert all(c.text.count("[u32]") == 2 and sigmine.count(image, c.text) == 1 for c in picks)
    assert not any(a <= c.at < z for c in picks for a, z in cheats)


def test_srkit_sig_mine_prints_candidates(cfg, game_dir, capsys):
    installed(game_dir)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["18295f8"], offset=False, limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert sum(out.count(word) for word in ("[rip]", "[rip+1]", "[rip+4]")) == 3     # 후보 셋(명령 줄의 "[rip + …]" 는 세지 않는다)
    assert "0x522330" in out                                               # 뺀 치트 코드
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["150", "14da4"], offset=True, limit=3, sites=40)) == 0
    out = capsys.readouterr().out
    assert out.count("[u32]") == 6 and "imul" in out                       # 후보 셋(상수 둘씩)과 그 명령
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1", "2", "3"], offset=True, limit=3, sites=40)) == 1
```

같은 파일의 `test_handler_range_comes_from_the_cheat_anchor` 뒤에 덧붙인다:

```python
def cheat_image(anchor_in_function: bool = True) -> bytes:
    """명령 처리 함수(0x1040) · 거기서만 불리는 A(0x1100) · 밖에서도 불리는 B(0x1140) · A 에서만 불리는 C(0x1180)."""
    image = fake.shell([(0x1000, 0x1040), (0x1040, 0x1100), (0x1100, 0x1140), (0x1140, 0x1180), (0x1180, 0x11C0)])
    fake.put(image, fake.RDATA + 0x10, b"\0cheat allowcheats\0")
    fake.rip(image, 0x1050 if anchor_in_function else 0x2F00, bytes([0x48, 0x8D, 0x15]), fake.RDATA + 0x11)
    fake.rip(image, 0x1060, bytes([0xE8]), 0x1100)      # 명령 처리 함수 → A
    fake.rip(image, 0x1070, bytes([0xE8]), 0x1140)      # 명령 처리 함수 → B
    fake.rip(image, 0x1010, bytes([0xE8]), 0x1140)      # 치트와 무관한 함수 → B
    fake.rip(image, 0x1110, bytes([0xE8]), 0x1180)      # A → C
    return bytes(image)


def test_cheat_ranges_cover_the_handler_and_what_only_cheat_code_calls(image):
    assert sigmine.cheat_ranges(sigmine.Image(cheat_image())) == [(0x1040, 0x1100), (0x1100, 0x1140), (0x1180, 0x11C0)]
    assert sigmine.cheat_ranges(image) == []                               # 치트가 없는 빌드


def test_cheat_ranges_refuse_an_anchor_they_cannot_place():
    """치트 문자열은 있는데 그것을 쓰는 함수를 못 찾으면, 치트 코드를 가리지 못한 채 뽑게 두지 않는다."""
    with pytest.raises(LookupError):
        sigmine.cheat_ranges(sigmine.Image(cheat_image(anchor_in_function=False)))


NOPS = bytes([0x90]) * 48
P, Q, T, U = 0x1000 + 48, 0x1080 + 48, 0x1180 + 48, 0x1200 + 48


def constants_image() -> bytes:
    """상수를 든 자리들. 저마다 nop 48개(명령의 경계가 분명하다) 뒤에 놓고 ret 로 끝낸다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(6)])
    for at, code in [
            (0x1000, "48 69 C0 50 01 00 00  48 05 A4 4D 01 00  48 03 C6"),             # P: imul rax,rax,150h / add rax,14DA4h / add rax,rsi
            (0x1080, "48 69 C8 50 01 00 00  42 0F 2F 84 21 A4 4D 01 00  76 40"),       # Q: imul rcx,rax,150h / comiss xmm0,[rcx+r12+14DA4h] / jbe
            (0x1100, "48 69 C0 50 01 00 00" + "  48 03 C6" * 5 + "  48 05 A4 4D 01 00"),   # 둘째 상수가 멀다(명령 다섯 뒤)
            (0x1180, "F2 0F 10 87 88 4B 01 00  66 0F 2F C1  76 5B"),                   # T: movsd xmm0,[rdi+14B88h] / comisd / jbe
            (0x1200, "49 69 CE 84 00 00 00  F3 0F 10 44 01 18  0F 2F C6"),             # U: imul rcx,r14,84h / movss xmm0,[rcx+rax+18h] / comiss
            (0x1280, "48 8B 05 50 01 00 00  48 85 C0 48 85 C0")]:                      # rip 상대 거리가 우연히 150h — 상수가 아니다
        fake.put(image, at, NOPS + bytes.fromhex(code) + b"\xC3")
    return bytes(image)


def test_constants_are_mined_as_values_to_read():
    """구조체 안의 자리와 간격은 서명이 읽어 낼 자리가 된다 — 4바이트는 [u32], 1바이트는 [u8]."""
    image = sigmine.Image(constants_image())
    assert {c.at: c.text for c in sigmine.mine_constants(image, [0x150, 0x14DA4])} == {
        P: "48 69 C0 [u32] 48 05 [u32] 48 03 C6", Q: "48 69 C8 [u32] 42 0F 2F 84 21 [u32] 76 40"}   # 둘째 상수가 먼 자리는 뺀다
    assert {c.at: (c.text, c.function, c.length) for c in sigmine.mine_constants(image, [0x14B88])} == {
        T: ("F2 0F 10 87 [u32] 66 0F 2F C1 76 5B", 0x1180, 14)}
    assert {c.at: c.text for c in sigmine.mine_constants(image, [0x84, 0x18])} == {U: "49 69 CE [u32] F3 0F 10 44 01 [u8] 0F 2F C6"}
    assert all(c.at != 0x1280 + 48 for c in sigmine.mine_constants(image, [0x150]))            # rip 상대 거리는 상수로 치지 않는다
    assert [c.at for c in sigmine.mine_constants(image, [0x150, 0x14DA4], exclude=[(0x1000, 0x1080)])] == [Q]


def test_a_candidate_can_be_shown_as_instructions():
    image = sigmine.Image(constants_image())
    found = sigmine.mine_constants(image, [0x84, 0x18])[0]
    assert sigmine.listing(image, found) == "imul rcx, r14, 0x84; movss xmm0, dword ptr [rcx + rax + 0x18]; comiss xmm0, xmm6"
```

- [ ] **Step 3: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -15`
Expected: FAIL — `AttributeError: module 'srkit.sigmine' has no attribute 'cheat_ranges'` / `'mine_constants'`, `test_mining_skips_the_excluded_ranges` 는 `TypeError`(범위들의 목록을 `exclude[0] <= p` 로 비교한다), `test_srkit_sig_mine_prints_candidates` 는 `AttributeError: 'Namespace' object has no attribute 'address'`.

- [ ] **Step 4: `sigmine` 을 고친다**

`src/srkit/sigmine.py` 의 import 에 `Sequence` 를 더한다 — `from dataclasses import dataclass` 다음 줄에:

```python
from typing import Sequence
```

`mine_address` 의 머리와 설명, 그리고 `places` 줄을 다음으로 바꾼다(나머지 본문은 그대로):

```python
def mine_address(image: Image, target: int, *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400) -> list[Candidate]:
    """target 을 가리키는 명령에서 시작해 실행 구역 전체에서 한 번만 맞는 가장 짧은 서명을, 쓰는 자리마다 하나씩.

    exclude 의 범위들 안의 자리는 보지 않는다(치트 코드 — cheat_ranges). 명령 fewest 개 · 정해진 바이트 fixed 개 이상이어야
    서명으로 친다. 쓰는 자리가 sites 보다 많으면 고르게 골라 그만큼만 본다.
    """
    found: list[Candidate] = []
    places = [p for p in image.refs(target) if not any(a <= p < z for a, z in exclude)]
```

파일 끝(`best_per_function` 뒤)에 덧붙인다:

```python


_lite = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)     # 명령의 경계만 본다(자세히 풀지 않는다 — 빠르다)


def cheat_ranges(image: Image) -> list[tuple[int, int]]:
    """치트 코드의 [시작, 끝) 들: 명령 처리 함수(맨 앞)와, 치트 코드에서만 불리는 함수들. 치트가 없는 빌드면 빈 목록.

    서명은 이 범위 밖의 코드에서만 뽑는다. 치트 문자열은 있는데 그것을 쓰는 함수를 못 찾으면 LookupError —
    치트 코드를 가리지 못한 채 서명을 뽑게 두지 않는다.
    """
    if image.data.find(b"\0" + ANCHOR) < 0:
        return []
    handler = handler_range(image)
    if handler is None:
        raise LookupError("치트 문자열은 있는데 그것을 쓰는 함수를 찾지 못했습니다 — 치트 코드를 가리지 못한 채 서명을 뽑지 않습니다")
    starts = set(image._starts)
    callers: dict[int, list[int]] = {}                 # 함수의 시작 → 그것을 부르는 call rel32 의 자리들
    for lo, hi in image.code:
        b = np.frombuffer(image.data, dtype=np.uint8)[lo:hi]
        calls = np.nonzero(b[:-4] == 0xE8)[0]
        disp = (b[calls + 1].astype(np.uint32) | (b[calls + 2].astype(np.uint32) << 8) | (b[calls + 3].astype(np.uint32) << 16)
                | (b[calls + 4].astype(np.uint32) << 24)).astype(np.int32).astype(np.int64)
        for site, target in zip((lo + calls).tolist(), (lo + calls + 5 + disp).tolist()):
            if target in starts:
                callers.setdefault(target, []).append(site)
    ranges = [handler]
    grew = True
    while grew:                                        # 치트에서만 불리는 함수가 부르는 함수까지
        grew = False
        for target, sites in callers.items():
            if all(any(a <= s < z for a, z in ranges) for s in sites) and not any(a <= target < z for a, z in ranges) \
                    and image.root(target) == target:
                ranges.append(image.extent(target))
                grew = True
    return [handler] + sorted(ranges[1:])


def _boundary(image: Image, pos: int) -> int | None:
    """pos 를 품은 명령의 시작. 앞쪽 여러 자리에서 풀어 내려와 가장 많이 닿는 경계다(x86 의 풀이는 몇 명령 안에 제 경계로 모인다)."""
    votes: dict[int, int] = {}
    for start in range(max(0, pos - 40), pos - 15):
        for address, size, _mnemonic, _operands in _lite.disasm_lite(image.data[start:pos + 16], start):
            if address + size > pos:
                if address <= pos:
                    votes[address] = votes.get(address, 0) + 1
                break
    return max(votes, key=lambda a: (votes[a], -a)) if votes else None


def _holds(ins, value: int) -> tuple[int, int] | None:
    """명령이 value 를 상수(imm)나 메모리 자리(disp. rip 상대는 아니다)로 들고 있으면 (명령 안의 자리, 크기 1 또는 4)."""
    rip = any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    for offset, size in ((ins.imm_offset, ins.imm_size), (ins.disp_offset, 0 if rip else ins.disp_size)):
        if size in (1, 4) and offset and (size == 4 or value < 0x80) \
                and int.from_bytes(bytes(ins.bytes[offset:offset + size]), "little") == value:
            return offset, size
    return None


def _constant_words(ins, held: tuple[int, int] | None) -> list[str]:
    """명령 하나의 서명 글. 든 상수는 읽어 낼 자리, rip 상대 거리와 call · jmp 의 4바이트 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    spans: list[tuple[int, int, list[str]]] = []
    if held:
        spans.append((held[0], held[1], ["[u32]" if held[1] == 4 else "[u8]"]))
    if ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands):
        spans.append((ins.disp_offset, 4, ["?"] * 4))
    elif (ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands \
            and ins.operands[0].type == X.X86_OP_IMM:
        spans.append((ins.size - 4, 4, ["?"] * 4))
    for offset, size, words in sorted(spans, reverse=True):      # 뒤에서부터 바꿔야 앞의 자리가 밀리지 않는다
        out[offset:offset + size] = words
    return out


def _grow(image: Image, start: int, constants: list[int], *, fewest: int, most: int, fixed: int, longest: int, within: int,
          unique: bool) -> str | None:
    """start 의 명령부터 constants 를 차례로 든 명령들을 지나, (unique 면) 실행 구역에서 한 번만 맞을 때까지 늘린 서명 글."""
    words: list[str] = []
    length, wanted, since = 0, 0, 0
    for n, ins in enumerate(_md.disasm(image.data[start:start + 200], start), start=1):
        held = _holds(ins, constants[wanted]) if wanted < len(constants) else None
        if n == 1 and (held is None or held[1] != 4):
            return None                        # 첫 명령이 첫 상수를 4바이트로 들고 있어야 한다
        if wanted < len(constants) and held is None:
            since += 1
            if since > within:
                return None                    # 다음 상수가 가까이에 없다
        if length + ins.size > longest:
            return None
        words += _constant_words(ins, held)
        length += ins.size
        if held:
            wanted, since = wanted + 1, 0
        if wanted == len(constants):
            text = " ".join(words)
            if not unique:
                return text
            if n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                return text
        if n >= most or ins.id in (X.X86_INS_RET, X.X86_INS_INT3, X.X86_INS_JMP):
            return None
    return None


def mine_constants(image: Image, constants: list[int], *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 9,
                   fixed: int = 8, longest: int = 60, within: int = 4, sites: int = 400) -> list[Candidate]:
    """constants(하나 또는 둘 — 구조체 안의 자리 · 간격)를 차례로 든 명령들에서 시작해, 한 번만 맞는 가장 짧은 서명을 자리마다.

    첫 상수는 4바이트로 든 것만 찾는다(imul r,r,간격 · [r+자리]). 다음 상수는 그 뒤 명령 within 개 안에 있어야 한다.
    상수의 자리는 읽어 낼 자리([u32] · [u8])가 된다. 뜻이 같은 코드인지는 사람이 본다(srkit sig-mine 이 명령을 함께 보인다) —
    값만 우연히 같은 코드도 후보로 나온다.
    """
    options = dict(fewest=fewest, most=most, fixed=fixed, longest=longest, within=within)
    needle = struct.pack("<I", constants[0])
    starts: list[int] = []
    seen: set[int] = set()
    for lo, hi in image.code:
        for m in re.finditer(re.escape(needle), image.data[lo:hi]):
            pos = lo + m.start()
            if any(a <= pos < z for a, z in exclude):
                continue
            start = _boundary(image, pos)
            if start is None or start in seen:
                continue
            seen.add(start)
            first = next(_md.disasm(image.data[start:start + 16], start), None)
            held = _holds(first, constants[0]) if first is not None else None
            if held == (pos - start, 4) and _grow(image, start, constants, unique=False, **options):
                starts.append(start)                   # 상수를 모두 든 자리만 남긴다 — 고르게 고르는 것은 그 뒤다
    found: list[Candidate] = []
    for start in starts[::max(1, len(starts) // sites)]:
        text = _grow(image, start, constants, unique=True, **options)
        if text:
            length = sum(4 if w.startswith("[rip") or w == "[u32]" else 1 for w in text.split())
            found.append(Candidate(image.root(start), start, length, text))
    return found


def listing(image: Image, candidate: Candidate) -> str:
    """후보가 덮는 명령들을 한 줄로(사람이 뜻을 보고 고른다). 저장소에는 넣지 않는다."""
    return "; ".join(f"{ins.mnemonic} {ins.op_str}".strip()
                     for ins in _md.disasm(image.data[candidate.at:candidate.at + candidate.length], candidate.at))
```

- [ ] **Step 5: `srkit sig-mine` 을 고친다**

`src/srkit/cli.py` 의 `cmd_sig_mine` 전체를 다음으로 바꾼다:

```python
def cmd_sig_mine(cfg, args) -> int:
    from . import sigmine      # capstone 은 개발 의존성이다 — 이 명령에서만 불러온다

    exe = cfg.game_dir / toybox.EXE_NAME
    image = sigmine.Image(toybox.image_of(exe.read_bytes()))
    values = [int(value, 16) for value in args.values]
    if len(values) > (2 if args.offset else 1):
        print("주소는 하나, --offset 의 상수는 하나나 둘입니다(서명 하나가 읽어 내는 값은 둘까지다).")
        return 1
    try:
        cheats = sigmine.cheat_ranges(image)
    except LookupError as error:
        print(error)
        return 1
    if args.offset:
        found = sigmine.mine_constants(image, values, exclude=cheats, sites=args.sites)
        what = "상수 " + " · ".join(f"{value:#x}" for value in values) + " 을 차례로 든 코드에서"
    else:
        found = sigmine.mine_address(image, values[0], exclude=cheats, sites=args.sites)
        what = f"{values[0]:#x} 를 가리키는 코드에서"
    picks = sigmine.best_per_function(found)
    left_out = (f"치트 코드 {len(cheats)}곳은 뺐다 — 명령 처리 함수 {cheats[0][0]:#x} – {cheats[0][1]:#x} 와 치트 코드에서만 불리는 함수"
                if cheats else "치트 명령 처리 함수가 없는 빌드다")
    print(f"{exe.name}: {what} ({left_out})")
    for c in picks[:args.limit]:
        function = f"{c.function:#x}" if c.function is not None else "표에 없음"
        print(f"  자리 {c.at:#010x}  함수 {function:>10}  {c.length:>2}바이트  {c.text}")
        print(f"      {sigmine.listing(image, c)}")
    print(f"서로 다른 함수 {len(picks)}개에서 후보가 나왔습니다. 서명 표에는 서로 다른 함수의 것 셋을 골라 옮깁니다.")
    if args.offset:
        print("상수가 우연히 같은 코드도 섞여 나옵니다 — 명령을 보고 뜻이 맞는 것만 고릅니다(docs/11).")
    return 0 if len(picks) >= 3 else 1
```

같은 파일의 파서에서 `sig-mine` 의 세 줄(`m = sub.add_parser("sig-mine", …)` 과 `m.add_argument("address", …)`)을 다음으로 바꾼다(`--limit` · `--sites` · `set_defaults` 는 그대로):

```python
    m = sub.add_parser("sig-mine", help="(개발용) 설치된 게임에서 주소나 상수를 읽어 낼 서명 후보 뽑기 — 치트 코드 밖에서")
    m.add_argument("values", nargs="+", help="주소(RVA, 16진수. 예: 18295f8). --offset 이면 차례로 나올 상수 하나나 둘(예: 150 14da4)")
    m.add_argument("--offset", action="store_true", help="값이 주소가 아니라 구조체 안의 자리 · 간격(상수)이다")
```

같은 파일 `cmd_locate` 의 안내 한 줄에서 `uv run srkit sig-mine <RVA> 로` 는 그대로 둔다(Task 2 에서 그 함수를 고친다).

- [ ] **Step 6: 테스트가 통과하는지 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -5`
Expected: `14 passed` (9개에 다섯을 더했다. 게임 설치본이 없으면 셋이 건너뛰어진다).

- [ ] **Step 7: 명령을 직접 돌려 본다**

Run: `uv run srkit sig-mine --offset 14b88 --limit 4`
Expected: 첫 줄에 `치트 코드 12곳은 뺐다 — 명령 처리 함수 0x522330 – 0x5284fd`, 후보마다 `[u32]` 하나가 든 서명과 `movsd …[r… + 0x14b88]` 이 든 명령 줄, 끝에 `서로 다른 함수 N개에서 후보가 나왔습니다`(N ≥ 3). 출력은 저장소에 넣지 않는다.

- [ ] **Step 8: 전체 테스트를 돌리고 커밋한다**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `240 passed` (235 + 5).

```bash
cd /e/SR2030ToyBox && git add src/srkit/sigmine.py src/srkit/cli.py tests/test_sigmine.py && git commit -q -F - <<'EOF'
feat: srkit sig-mine — 구조체 안의 자리 · 간격을 읽어 내는 서명, 치트 코드의 범위

- mine_constants: 상수 하나나 둘을 차례로 든 명령들에서 한 번만 맞는 서명을 뽑는다([u32] · [u8])
- cheat_ranges: 명령 처리 함수에 더해 치트 코드에서만 불리는 함수들도 뺀다. 닻은 있는데 함수를 못 찾으면 멈춘다
- sig-mine --offset, 후보마다 명령을 함께 보인다(값만 우연히 같은 코드를 사람이 거른다)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 2: 값의 자리를 서명으로 찾는다 (`locate_values`)

**브랜치:** `feat/toybox-values-locate`

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp` (구역 표에 "쓸 수 있는가", `:235` 부터 끝까지 다시 쓴다), `native/srtoybox/exports.cpp`
- Modify: `src/srkit/toybox.py`, `src/srkit/cli.py:157-185` (`cmd_locate`)
- Modify: `tests/toybox_fake_exe.py`, `tests/toybox_cheat_oracle.py`
- Test: `tests/test_toybox_game.py`

**Interfaces:**
- Consumes: 계획 (가)의 `sig_parse` · `sig_scan` · `sig_vote`(`sigs.h`), `locate.cpp` 의 `Image` · `parse` · 표 `STATE`, Task 1 의 `sigmine.cheat_ranges`.
- Produces (C++ — `locate.h`):
  - `struct ValueLayout { uint32_t world_pointer, treasury, stock_first, stock_step, used_first, used_step; };`
  - `const int VALUE_WANTED = 4;` `const int STOCK_SLOTS = 12;`
  - `struct SigRow` 에 `uint32_t value2;` (둘째로 읽어 낸 값. 없으면 0)
  - `bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);` — `rows` 는 `VALUE_WANTED * STATE_SIGS` 칸이거나 `nullptr`
- Produces (내보내기): `int srtoybox_locate_values(const unsigned char *image, unsigned long long size, ValueLayout *out, char *error, int error_size, char *rows, int rows_size)`, `int srtoybox_stock_slots(void)`. **서명 줄의 글이 여섯 칸이 된다**: `이름\t서명\t횟수\t자리\t값\t둘째 값`(`srtoybox_locate_state` 도).
- Produces (Python — `srkit.toybox`): `VALUE_FIELDS`, `VALUE_NAMES`, `STOCK_SLOTS`, `ValueLayout`(ctypes), `SigRow.value2`, `values_of(lib, image) -> (dict | None, str, list[SigRow])`, `Located.values` · `.values_why` · `.value_rows`.
- Produces (테스트 도구): `toybox_fake_exe.sig_image`(지금의 `state_image` 를 고쳐 이름을 바꾼다) · `VALUES` · `VALUE_LAYOUT`, `toybox_cheat_oracle.values(image) -> dict`.

값 묶음의 서명 표(build 21347933. 자리는 맞는 곳, 함수는 그 자리가 든 함수의 시작):

| 찾을 것 | 서명 | 자리 | 함수 | 읽어 낸 값 |
|---|---|---|---|---|
| `world_pointer` | `4C 8B 2D [rip] 41 8B F9 B3 01` | `0x746fff` | `0x746c90` | `0x1af5868` |
| | `48 8B 0D [rip] 99 45 0F BF 45 48` | `0x510974` | `0x50e7c0` | 〃 |
| | `4C 8B 0D [rip] 66 0F 6E E7 0F 5B E4` | `0x4fdbd0` | `0x4fd540` | 〃 |
| `treasury` | `F2 0F 10 87 [u32] 66 0F 2F C1 76 5B` | `0x49625f` | `0x495180` | `0x14b88` |
| | `F2 0F 11 89 [u32] 33 C9 89 4C 24 60` | `0x6fea15` | `0x6fe990` | 〃 |
| | `F2 0F 11 9B [u32] 76 18 0F 28 C1` | `0x76b0d1` | `0x76a5d0` | 〃 |
| `stock` | `48 69 C8 [u32] 42 0F 2F 84 21 [u32] 76 40` | `0x726f63` | `0x726280` | 간격 `0x150`, 첫 칸 `0x14da4` |
| | `48 69 C7 [u32] 48 03 C3 F3 0F 10 80 [u32]` | `0x7a222e` | `0x7a2110` | 〃 |
| | `49 69 C0 [u32] 0F 2F 94 08 [u32] 76 0E` | `0x78d0fd` | `0x78a790` | 〃 |
| `used` | `49 69 CE [u32] F3 0F 10 44 01 [u8] 0F 2F C6` | `0x4f8317` | `0x4f8290` | 간격 `0x84`, 첫 칸 `0x18` |
| | `48 69 D0 [u32] F3 42 0F 10 44 02 [u8] 41 0F 2F C5` | `0x4b71da` | `0x4b4b30` | 〃 |
| | `4C 69 C2 [u32] 48 69 CA ? ? ? ? 0F 28 C2 F3 41 0F 59 44 01 [u8]` | `0x79bb1b` | `0x7961b0` | 〃 |

(`used` 의 셋째는 `sig-mine` 이 낸 것에서 가운데 명령 `imul rcx, rdx, 150h` 의 상수 4바이트를 손으로 구멍으로 바꿨다 — 재고의 간격이 바뀌어도 이 서명이 함께 깨지지 않게.)

- [ ] **Step 1: 가짜 이미지를 값 묶음까지 심을 수 있게 고친다**

`tests/toybox_fake_exe.py`:

머리말의 둘째 문단을 다음으로 바꾼다:

```python
게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음과 값 묶음)과, 옛 찾기가 보는
닻(치트 문자열)과 명령의 바이트 꼴만 같은 자리 관계로 놓았다. pytest 가 직접 모으는 테스트 파일이 아니다.
```

`LEGACY = …` 줄 다음에 더한다:

```python
# 새 찾기(값 묶음)의 가짜 값: 서명의 이름 → 읽어 낼 것. 둘을 읽는 서명은 (간격, 첫 칸).
# 진짜 게임의 값과 다르게 뒀다 — 코드에 박아 둔 값으로는 통과하지 못한다
VALUES = {"world_pointer": DATA + 0x40, "treasury": 0x1230, "stock": (0x20, 0x2000), "used": (0x44, 0x28)}
VALUE_LAYOUT = {"world_pointer": DATA + 0x40, "treasury": 0x1230, "stock_first": 0x2000, "stock_step": 0x20,
                "used_first": 0x28, "used_step": 0x44}
```

`shell` 의 구역 표에서 `.data` 가 이미지의 끝까지 가게 한다(지역 표 8바이트 × 1024칸이 그 안에 든다) — `0x2000 if rva == TEXT else 0x1000` 을 다음으로:

```python
0x2000 if rva == TEXT else size - DATA if rva == DATA else 0x1000
```

`plant` 전체를 다음으로 바꾼다:

```python
def plant(image: bytearray, at: int, text: str, target) -> int:
    """서명 글 하나를 at 에 심는다: 정해진 바이트는 그대로, 구멍은 건드리지 않고, 읽어 낼 자리는 target 이 나오게.
    target 이 튜플이면 읽어 낼 자리마다 차례로 하나씩 쓴다. 끝 자리를 돌려준다."""
    values = iter(target if isinstance(target, tuple) else (target, target))
    pos = at
    for m in TOKEN.finditer(text):
        word = m.group(0)
        if word.startswith("[rip"):
            struct.pack_into("<i", image, pos, next(values) - (pos + 4 + int(m.group(1) or 0)))
            pos += 4
        elif word == "[u32]":
            struct.pack_into("<I", image, pos, next(values))
            pos += 4
        elif word == "[u8]":
            image[pos] = next(values)
            pos += 1
        elif word == "?":
            pos += 1
        else:
            image[pos] = int(word, 16)
            pos += 1
    return pos
```

`state_image` 전체를 다음 둘로 바꾼다(이름이 `sig_image` 가 된다):

```python
def beside(target):
    """그 값의 옆: 주소는 8바이트 옆, (간격, 첫 칸)은 저마다 4 큰 값."""
    return tuple(value + 4 for value in target) if isinstance(target, tuple) else target + 8


def sig_image(sigs: list[tuple[str, str]], *, broken=(), twice=(), stray=(), targets: dict | None = None,
              into: bytearray | None = None) -> bytes:
    """DLL 의 서명 표(sigs: [(찾을 것, 서명 글)])를 심은 이미지. into 가 없으면 치트 문자열이 하나도 없는 빈 틀에 심는다.

    broken · twice · stray 는 sigs 의 칸 번호들이다: 심지 않는다 / 한 번 더 심는다(두 번 맞는다) / 옆의 값을 가리키게 심는다.
    targets 로 가짜 주소 · 값을 바꾼다(STATE 와 VALUES 의 이름으로).
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **(targets or {})}
    places: dict[str, int] = {}
    for i, (name, text) in enumerate(sigs):
        if i in broken:
            continue
        place = places.setdefault(shape(text), PLANT + 0x40 * len(places))
        plant(image, place, text, beside(at[name]) if i in stray else at[name])
        if i in twice:
            plant(image, AGAIN + 0x40 * i, text, at[name])
    return bytes(image)
```

`build` 의 마지막 줄에서 `state_image(` 를 `sig_image(` 로 바꾼다.

`tests/test_toybox_game.py` 에서 `toybox_fake_exe.state_image(` 를 모두 `toybox_fake_exe.sig_image(` 로 바꾼다:

```bash
cd /e/SR2030ToyBox && sed -i 's/toybox_fake_exe\.state_image(/toybox_fake_exe.sig_image(/g' tests/test_toybox_game.py && grep -c "sig_image(" tests/test_toybox_game.py && grep -c "state_image" tests/test_toybox_game.py tests/toybox_fake_exe.py
```

Expected: 첫 줄 `9`(바뀐 곳), 이어서 두 파일 모두 `:0`.

Run: `uv run pytest tests/test_toybox_game.py tests/test_sigmine.py -q 2>&1 | tail -3`
Expected: `69 passed` (55 + 14) — 가짜 이미지를 고친 것이 지금의 테스트를 깨지 않는다.

- [ ] **Step 2: 대조용 오라클에 값 묶음을 더한다**

`tests/toybox_cheat_oracle.py` 의 머리말 첫 줄을 다음으로 바꾼다:

```python
"""자동 테스트의 대조용: 2단계가 쓰던 방식(치트 문자열을 닻으로)으로 실행 파일의 이미지에서 상태 전역의 주소와 값의 자리를 읽는다.
```

파일 끝에 덧붙인다:

```python


def values(image_bytes: bytes) -> dict[str, int]:
    """값 묶음(세계 자료 포인터, 국고 칸, 재고와 "쓰는 물자"의 첫 칸 · 간격)과 재고의 칸 수(slots) — 치트 treasury · products 의 본문에서 읽은 것."""
    image = sigmine.Image(image_bytes)
    data = image.data
    out = {}
    at = _after(image, "cheat treasury", 0x80, rb"\xf2\x0f\x58\x80....\xf2\x0f\x11\x80")        # addsd xmm0,[rax+국고] / movsd [rax+국고],xmm0
    out["treasury"] = struct.unpack_from("<I", data, at + 4)[0]
    use = _uses(image, "cheat products")[0]
    skip = re.search(rb"\x0f\x84(....)", data[use:use + 0x20], re.S)                             # je <다음 치트> — 거기까지가 본문이다
    body = data[use:use + skip.start() + 6 + struct.unpack("<i", skip.group(1))[0]]
    first = re.search(rb"\x48\x8b\x05....\x4c\x8d\x3d....\xf3\x0f\x10\x40(.)", body, re.S)       # mov rax,[세계 자료] / lea r15,[월드] / movss xmm0,[rax+첫 칸]
    out["world_pointer"] = _target(data, use + first.start(), 3, 7)
    used = [first.group(1)[0]] + [struct.unpack("<I", d)[0] for d in re.findall(rb"\xf3\x0f\x10\x80(....)\x0f\x2f\xc2", body, re.S)]
    stock = [struct.unpack("<I", d)[0]                                                           # addss xmm,[rcx+칸] / movss [rcx+칸],xmm
             for d in re.findall(rb"\xf3\x0f\x58[\x81\x89](....)\xf3\x0f\x11[\x81\x89]", body, re.S)]
    out["used_first"], out["used_step"] = used[0], used[1] - used[0]
    out["stock_first"], out["stock_step"] = stock[0], stock[1] - stock[0]
    assert used == [out["used_first"] + out["used_step"] * i for i in range(len(used))], used    # 물자마다 펼쳐 놓았다 — 간격이 고르다
    assert stock == [out["stock_first"] + out["stock_step"] * i for i in range(len(stock))], stock
    assert len(used) == len(stock), (len(used), len(stock))
    out["slots"] = len(stock)
    return out
```

- [ ] **Step 3: Python 의 거울과 실패하는 테스트를 쓴다**

`src/srkit/toybox.py`:

`LEGACY_FIELDS = …` 줄 다음에 더한다:

```python
# 새 찾기(서명)가 채우는 값 묶음 — native/srtoybox/locate.h 의 ValueLayout 과 같은 순서다
VALUE_FIELDS = ["world_pointer", "treasury", "stock_first", "stock_step", "used_first", "used_step"]
VALUE_NAMES = {"world_pointer": "세계 자료 객체의 포인터(qword. 이것만 RVA 다)", "treasury": "국고 칸 — 지역 객체 안의 자리(double, 달러)",
               "stock_first": "재고의 첫 칸 — 지역 객체 안의 자리(float)", "stock_step": "재고 칸의 간격",
               "used_first": "\"쓰는 물자\" 표의 첫 칸 — 세계 자료 객체 안의 자리(float. 0 보다 크면 쓴다)", "used_step": "그 표의 간격"}
STOCK_SLOTS = 12        # 재고의 칸 수(native/srtoybox/locate.h 의 STOCK_SLOTS)
```

`SigRow` 의 `value` 줄을 다음 둘로 바꾼다:

```python
    value: int      # 거기서 읽어 낸 주소나 상수(둘을 읽는 서명이면 간격)
    value2: int = 0  # 둘째로 읽어 낸 상수(재고 · "쓰는 물자" 표의 첫 칸). 없으면 0
```

`Located` 의 `ms` 줄 다음에 더한다(필드의 순서가 바뀐다 — 만드는 곳은 `locate` 하나다):

```python
    values: dict[str, int] | None    # 새 찾기(서명): 값 묶음. 못 찾았으면 None
    values_why: str
    value_rows: list[SigRow]
```

`GameAddresses` 클래스 다음에 더한다:

```python
class ValueLayout(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in VALUE_FIELDS]
```

`library` 의 `lib.srtoybox_function_root.argtypes` 줄 앞에 더한다:

```python
    lib.srtoybox_locate_values.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(ValueLayout), ctypes.c_char_p,
                                           ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
```

`state_of` 전체를 다음 셋으로 바꾼다:

```python
def _sig_rows(text: bytes) -> list[SigRow]:
    """DLL 이 내는 서명마다의 결과(한 줄에 "이름\\t서명\\t횟수\\t자리\\t값\\t둘째 값", 뒤의 넷은 16진수)."""
    return [SigRow(name, sig, int(count, 16), int(at, 16), int(value, 16), int(value2, 16))
            for name, sig, count, at, value, value2 in (line.split("\t") for line in text.decode("utf-8").splitlines())]


def state_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(상태 묶음)를 그 이미지에 돌린다: (이름 → RVA 또는 None, 까닭, 서명마다의 결과)."""
    found, error, rows = GameAddresses(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_state(image, len(image), ctypes.byref(found), error, len(error), rows, len(rows)) == 0
    return ({name: getattr(found, name) for name in STATE_FIELDS} if ok else None), error.value.decode("utf-8"), _sig_rows(rows.value)


def values_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(값 묶음)를 그 이미지에 돌린다: (이름 → 값 또는 None, 까닭, 서명마다의 결과)."""
    found, error, rows = ValueLayout(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_values(image, len(image), ctypes.byref(found), error, len(error), rows, len(rows)) == 0
    return ({name: getattr(found, name) for name in VALUE_FIELDS} if ok else None), error.value.decode("utf-8"), _sig_rows(rows.value)
```

`locate` 의 본문에서 `legacy, legacy_why = legacy_of(lib, image)` 줄과 `return` 줄을 다음으로 바꾼다:

```python
    values, values_why, value_rows = values_of(lib, image)
    legacy, legacy_why = legacy_of(lib, image)
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why)
```

`tests/test_toybox_game.py`:

`BUILD_LEGACY = …` 줄 다음에 더한다:

```python
BUILD_VALUES = {"world_pointer": 0x1AF5868, "treasury": 0x14B88, "stock_first": 0x14DA4, "stock_step": 0x150,
                "used_first": 0x18, "used_step": 0x84}
```

`sigs` 고정물 다음에 더한다:

```python
@pytest.fixture(scope="module")
def value_sigs(lib):
    """DLL 에 든 값 묶음의 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.values_of(lib, b"")[2]]
```

`test_state_signatures_lie_outside_the_cheat_handler` 와 `test_each_address_takes_its_signatures_from_different_functions` 를 다음 둘로 바꾼다:

```python
def test_signatures_lie_outside_the_cheat_code(lib, game_dir):
    """요구 3: 서명은 치트 코드(명령 처리 함수와, 치트 코드에서만 불리는 함수들)에서 뽑지 않는다."""
    sigmine = pytest.importorskip("srkit.sigmine", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    cheats = sigmine.cheat_ranges(sigmine.Image(image))
    assert len(cheats) == 12
    for row in toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]:
        assert not any(begin <= row.at < end for begin, end in cheats), row


def test_each_item_takes_its_signatures_from_different_functions(lib, game_dir):
    image = installed_image(game_dir)
    rows = toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]
    for i in range(0, len(rows), 3):
        roots = {lib.srtoybox_function_root(image, len(image), row.at) or -row.at for row in rows[i:i + 3]}   # 함수 표에 없으면 0
        assert len(roots) == 3, rows[i].name
```

`test_state_agrees_with_what_the_cheat_code_says` 다음에 더한다:

```python
def test_an_address_outside_the_writable_data_is_refused(lib, sigs, value_sigs):
    """서명들이 서로 맞아도, 읽어 낸 주소가 전역 변수가 있을 수 없는 구역(코드 · 읽기 전용 자료)이면 엉뚱한 것을 읽은 것이다."""
    for target in (toybox_fake_exe.RDATA + 0x100, toybox_fake_exe.TEXT + 0x100):
        found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, targets={"player_index": target}))
        assert found is None and "플레이어 인덱스" in why and "자료 구역" in why, why
        found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, targets={"world_pointer": target}))
        assert found is None and "세계 자료 포인터" in why and "자료 구역" in why, why


def test_state_addresses_that_overlap_are_refused(lib, sigs):
    targets = {"region_count": toybox_fake_exe.STATE["player_pointer"] + 4}     # 지역 수(4바이트)가 플레이어 포인터(8바이트) 안이다
    found, why, _ = toybox.state_of(lib, toybox_fake_exe.sig_image(sigs, targets=targets))
    assert found is None and "지역 수" in why and "겹칩니다" in why, why


def test_the_value_table_has_three_signatures_per_item(lib, value_sigs):
    assert [name for name, _ in value_sigs] == [name for name in ("world_pointer", "treasury", "stock", "used") for _ in range(3)]
    assert len({text for _, text in value_sigs}) == 12
    assert lib.srtoybox_stock_slots() == toybox.STOCK_SLOTS == 12


def test_values_are_found_in_an_image_without_any_cheat_string(lib, value_sigs):
    """값의 자리도 치트 문자열에 기대지 않고 찾는다."""
    image = toybox_fake_exe.sig_image(value_sigs)
    assert b"cheat" not in image
    found, why, rows = toybox.values_of(lib, image)
    assert found == toybox_fake_exe.VALUE_LAYOUT, why
    assert [row.count for row in rows] == [1] * 12
    assert (rows[6].value, rows[6].value2) == (0x20, 0x2000)                    # 재고의 서명은 (간격, 첫 칸)을 함께 읽는다
    assert (rows[9].value, rows[9].value2) == (0x44, 0x28)


@pytest.mark.parametrize("which", range(4))
def test_values_survive_one_broken_signature_per_item(lib, value_sigs, which):
    found, why, rows = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, broken={3 * which + 1}))
    assert found == toybox_fake_exe.VALUE_LAYOUT, why
    assert rows[3 * which + 1].count == 0


def test_values_are_not_found_when_two_signatures_of_one_item_break(lib, value_sigs):
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, broken={3, 4}))
    assert found is None and "국고 칸" in why and "3개 가운데 1개" in why


def test_value_signatures_that_disagree_are_refused(lib, value_sigs):
    """셋이 모두 맞았는데 하나가 다른 자리를 낸다 — 다수결로 고르지 않는다(틀린 칸에 쓰느니 쓰지 않는다)."""
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, stray={7}))
    assert found is None and "재고 칸" in why and "서로 다른 값" in why


@pytest.mark.parametrize("targets, reason", [
    ({"treasury": 0x2040}, "국고 칸과 재고 칸이 겹칩니다"),      # 국고 8바이트가 재고의 셋째 칸(0x2040)을 덮는다
    ({"stock": (0x22, 0x2000)}, "재고 칸"),                     # 간격이 4 의 배수가 아니다
    ({"stock": (0x20, 0x100000)}, "재고 칸"),                   # 자리가 터무니없이 멀다
    ({"used": (0, 0x28)}, "쓰는 물자 표"),                      # 간격이 0
    ({"treasury": 0}, "국고 칸"),                               # 자리가 0
], ids=["overlap", "odd-step", "far", "zero-step", "zero-offset"])
def test_values_that_do_not_add_up_are_refused(lib, value_sigs, targets, reason):
    """서명들이 서로 맞아도 읽어 낸 자리가 말이 안 되면 못 찾은 것이다."""
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, targets=targets))
    assert found is None and reason in why, why


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_values_survive_garbage(lib, image):
    found, why, _ = toybox.values_of(lib, image)
    assert found is None and why


def test_values_on_the_installed_game(lib, game_dir):
    """build 21347933: 값 묶음의 서명 12개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 값이 docs/11 의 표와 같다."""
    found, why, rows = toybox.values_of(lib, installed_image(game_dir))
    assert found == BUILD_VALUES, why
    assert [row.count for row in rows] == [1] * 12


def test_values_agree_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 서명으로 읽은 값 == 치트 treasury · products 의 본문에서 읽은 값. 칸 수도 거기서 센다."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    said = oracle.values(image)
    assert said.pop("slots") == toybox.STOCK_SLOTS
    assert toybox.values_of(lib, image)[0] == said
```

`test_srkit_locate_reports_both_searches` 를 다음으로 바꾼다:

```python
def test_srkit_locate_reports_every_search(lib, cfg, game_dir):
    located = toybox.locate(cfg)
    assert located.state is not None and set(located.state) == set(toybox.STATE_FIELDS), located.state_why
    assert len(located.rows) == 21 and located.ms >= 0
    assert located.values is not None and set(located.values) == set(toybox.VALUE_FIELDS), located.values_why
    assert len(located.value_rows) == 12
    assert located.legacy is not None and set(located.legacy) == set(toybox.LEGACY_FIELDS), located.legacy_why
```

- [ ] **Step 4: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -6`
Expected: 모든 테스트가 ERROR — 고정물 `lib` 에서 `AttributeError: function 'srtoybox_locate_values' not found`.

- [ ] **Step 5: `locate.h` 를 고친다**

머리말의 "찾는 길이 둘이다" 문단에서 `새 찾기 locate_state …` 줄 다음에 한 줄을 더한다:

```cpp
//           locate_values  값을 읽고 쓰는 자리(국고 칸, 재고 칸 …). 같은 규칙의 서명으로.
```

`SigRow` 의 `value` 줄을 다음 둘로 바꾼다:

```cpp
    uint32_t value;             // 거기서 읽어 낸 주소나 상수(둘을 읽는 서명이면 첫째 — 간격)
    uint32_t value2;            // 둘째로 읽어 낸 상수(첫 칸). 없으면 0
```

`locate_state` 선언 다음에 더한다:

```cpp

// 값 묶음: 플레이어의 국고와 물자 재고를 읽고 쓰는 자리. world_pointer 만 RVA 이고 나머지는 객체 안의 자리다.
struct ValueLayout {
    uint32_t world_pointer;    // qword. 세계 자료 객체("이 물자를 쓰는가"의 표가 그 안에 있다)
    uint32_t treasury;         // 지역 객체 안. double, 달러
    uint32_t stock_first;      // 지역 객체 안. 첫 물자의 재고(float)
    uint32_t stock_step;       // 물자 사이의 간격
    uint32_t used_first;       // 세계 자료 객체 안. 첫 물자의 "쓰는가"(float. 0 보다 크면 이번 판에서 쓴다)
    uint32_t used_step;
};

const int VALUE_WANTED = 4;     // 값 묶음에서 찾을 것의 수: 세계 자료 포인터, 국고 칸, 재고 칸(간격 · 첫 칸), 쓰는 물자 표(간격 · 첫 칸)
const int STOCK_SLOTS = 12;     // 재고의 칸 수. 코드에서 한 가지 꼴로 읽어 낼 자리가 없어 상수로 둔다(docs/11-game-internals.md)

// 새 찾기(값 묶음): 규칙은 locate_state 와 같다. 찾으면 true 와 out. 못 찾으면 false 와 why(UTF-8) — out 은 그대로다.
// 읽어 낸 값이 말이 되는지도 본다: 포인터는 쓸 수 있는 자료 구역 안, 자리는 0 보다 크고 0x100000 보다 작다, 간격은 4 의 배수,
// 국고 칸(8바이트)과 재고 칸들(4바이트 × STOCK_SLOTS)이 겹치지 않는다.
// rows: VALUE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);
```

`locate_state` 선언 위의 설명 첫 줄 뒤에 한 줄을 더한다:

```cpp
// 찾은 주소는 쓸 수 있는 자료 구역 안이어야 하고 서로 겹치지 않아야 한다.
```

- [ ] **Step 6: `locate.cpp` 를 고친다**

`struct Section` 에 필드를 더한다 — `bool constant;` 줄 다음에:

```cpp
    bool writable;    // 쓸 수 있는 자료(전역 변수가 여기 있다)
```

`parse` 에서 `s.constant = …` 줄 다음에:

```cpp
        s.writable = !s.code && (flags & 0x80000000) != 0;
```

`// 게임 상태를 읽는 데 쓰는 전역 일곱.` 주석(`:235`)부터 파일 끝까지를 다음으로 바꾼다:

```cpp
// 게임 상태를 읽는 데 쓰는 전역 일곱. 서명은 모두 치트 코드 밖에서 뽑았다(uv run srkit sig-mine <RVA>):
// build 21347933 에서 저마다 실행 구역에 한 번만 맞고, 찾을 것마다 세 서명이 서로 다른 함수에 있다(docs/11-game-internals.md).
// 프로그램 상태와 모드 상태의 셋째 서명은 같은 자리(게임 진입의 mov [모드 상태],2 / mov [프로그램 상태],1)를 읽는다.
const struct Wanted {
    const char *name;                       // GameAddresses 의 필드 이름(srkit locate 와 테스트가 본다)
    const char *label;                      // 로그에 나오는 이름
    uint32_t GameAddresses::*field;
    uint32_t bytes;                         // 그 주소에서 이만큼은 쓸 수 있는 자료 구역 안이어야 한다
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

// 값을 읽고 쓰는 자리 넷. 같은 규칙으로 뽑았다(uv run srkit sig-mine <RVA> / --offset <간격> <첫 칸>). 둘을 읽는 서명은
// 간격이 먼저, 첫 칸이 나중이다. "쓰는 물자" 표의 셋째 서명은 가운데 명령(imul r,r,재고 간격)의 상수를 구멍으로 뒀다.
const struct ValueWanted {
    const char *name;                       // srkit locate 와 테스트가 본다
    const char *label;                      // 로그와 창에 나오는 이름
    const char *sigs[STATE_SIGS];
} VALUES[VALUE_WANTED] = {
    {"world_pointer", "세계 자료 포인터",
     {"4C 8B 2D [rip] 41 8B F9 B3 01", "48 8B 0D [rip] 99 45 0F BF 45 48", "4C 8B 0D [rip] 66 0F 6E E7 0F 5B E4"}},
    {"treasury", "국고 칸",
     {"F2 0F 10 87 [u32] 66 0F 2F C1 76 5B", "F2 0F 11 89 [u32] 33 C9 89 4C 24 60", "F2 0F 11 9B [u32] 76 18 0F 28 C1"}},
    {"stock", "재고 칸",
     {"48 69 C8 [u32] 42 0F 2F 84 21 [u32] 76 40", "48 69 C7 [u32] 48 03 C3 F3 0F 10 80 [u32]",
      "49 69 C0 [u32] 0F 2F 94 08 [u32] 76 0E"}},
    {"used", "쓰는 물자 표",
     {"49 69 CE [u32] F3 0F 10 44 01 [u8] 0F 2F C6", "48 69 D0 [u32] F3 42 0F 10 44 02 [u8] 41 0F 2F C5",
      "4C 69 C2 [u32] 48 69 CA ? ? ? ? 0F 28 C2 F3 41 0F 59 44 01 [u8]"}},
};

const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개)

// 전역 변수가 있을 수 있는 곳인가: 쓸 수 있는 자료 구역 안.
bool in_data(const Image &im, uint64_t rva, uint64_t bytes)
{
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (sec.writable && rva >= sec.rva && rva + bytes <= static_cast<uint64_t>(sec.rva) + sec.size)
            return true;
    }
    return false;
}

// 객체 안의 자리로 말이 되는가.
bool offset_ok(uint64_t offset)
{
    return offset > 0 && offset < 0x100000;
}

// 서명 표 하나(찾을 것 n 개 × 서명 STATE_SIGS 개)를 실행 구역에 한 번 훑어 맞추고, 찾을 것마다 투표한다.
// values: n 줄 × SIG_CAPTURES 칸(0 으로 채워서 준다). 못 찾으면 false 와 why. what 은 서명이 읽어 내는 것("주소를" · "값을").
template <class Row>
bool vote_table(const Image &im, const Row *table, int n, const char *what, SigRow *rows, uint64_t (*values)[SIG_CAPTURES],
                char *why, size_t why_size)
{
    const int total = n * STATE_SIGS;
    SigRange ranges[32];
    int range_count = 0;
    for (int s = 0; s < im.count; s++)
        if (im.sections[s].code) {
            ranges[range_count].begin = im.sections[s].rva;
            ranges[range_count].end = im.sections[s].rva + im.sections[s].size;
            range_count++;
        }
    Sig sigs[MAX_TABLE];
    SigHit hits[MAX_TABLE];
    for (int i = 0; i < total; i++)
        if (!sig_parse(table[i / STATE_SIGS].sigs[i % STATE_SIGS], &sigs[i])) {
            snprintf(why, why_size, "서명 표가 틀렸습니다 (%s)", table[i / STATE_SIGS].name);
            return false;
        }
    sig_scan(im.p, im.size, ranges, range_count, sigs, total, hits);
    if (rows != nullptr)
        for (int i = 0; i < total; i++) {
            rows[i].count = hits[i].count;
            rows[i].at = hits[i].at;
            rows[i].value = static_cast<uint32_t>(hits[i].value[0]);
            rows[i].value2 = static_cast<uint32_t>(hits[i].value[1]);
        }
    for (int w = 0; w < n; w++) {
        int matched = 0;
        if (!sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, STATE_NEED, values[w], &matched)) {
            if (matched >= STATE_NEED)
                snprintf(why, why_size, "%s: 서명들이 서로 다른 %s 냅니다", table[w].label, what);
            else
                snprintf(why, why_size, "%s: 서명 %d개 가운데 %d개", table[w].label, STATE_SIGS, matched);
            return false;
        }
    }
    return true;
}

bool search_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    Image im = {};
    im.p = image;
    im.size = size;
    if (image == nullptr || !parse(im)) {
        snprintf(why, why_size, "실행 파일의 머리말을 읽을 수 없습니다");
        return false;
    }
    uint64_t values[STATE_WANTED][SIG_CAPTURES] = {};
    if (!vote_table(im, STATE, STATE_WANTED, "주소를", rows, values, why, why_size))
        return false;
    GameAddresses found = *out;
    for (int w = 0; w < STATE_WANTED; w++) {
        const uint64_t rva = values[w][0];
        if (rva == 0 || rva >= size || !im.has(rva, STATE[w].bytes)) {
            snprintf(why, why_size, "%s: 찾은 주소가 실행 파일 밖입니다", STATE[w].label);
            return false;
        }
        if (!in_data(im, rva, STATE[w].bytes)) {
            snprintf(why, why_size, "%s: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다", STATE[w].label);
            return false;
        }
        for (int v = 0; v < w; v++)
            if (rva < values[v][0] + STATE[v].bytes && values[v][0] < rva + STATE[w].bytes) {
                snprintf(why, why_size, "%s: 찾은 주소가 %s 의 자리와 겹칩니다", STATE[w].label, STATE[v].label);
                return false;
            }
        found.*(STATE[w].field) = static_cast<uint32_t>(rva);
    }
    *out = found;
    snprintf(why, why_size, "%s", "");
    return true;
}

bool search_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size)
{
    Image im = {};
    im.p = image;
    im.size = size;
    if (image == nullptr || !parse(im)) {
        snprintf(why, why_size, "실행 파일의 머리말을 읽을 수 없습니다");
        return false;
    }
    uint64_t v[VALUE_WANTED][SIG_CAPTURES] = {};
    if (!vote_table(im, VALUES, VALUE_WANTED, "값을", rows, v, why, why_size))
        return false;
    const uint64_t world = v[0][0], treasury = v[1][0];
    if (world == 0 || world >= size || !im.has(world, 8)) {
        snprintf(why, why_size, "%s: 찾은 주소가 실행 파일 밖입니다", VALUES[0].label);
        return false;
    }
    if (!in_data(im, world, 8)) {
        snprintf(why, why_size, "%s: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다", VALUES[0].label);
        return false;
    }
    if (!offset_ok(treasury)) {
        snprintf(why, why_size, "%s: 찾은 자리가 범위 밖입니다", VALUES[1].label);
        return false;
    }
    for (int w = 2; w < VALUE_WANTED; w++) {    // 표 둘: (간격, 첫 칸). 칸이 float 라 간격은 4 의 배수다
        const uint64_t step = v[w][0], first = v[w][1];
        if (!offset_ok(first) || step == 0 || step % 4 != 0 || !offset_ok(first + step * (STOCK_SLOTS - 1) + 4)) {
            snprintf(why, why_size, "%s: 찾은 자리나 간격이 범위 밖입니다", VALUES[w].label);
            return false;
        }
    }
    for (int i = 0; i < STOCK_SLOTS; i++) {
        const uint64_t slot = v[2][1] + v[2][0] * static_cast<uint64_t>(i);
        if (slot < treasury + 8 && treasury < slot + 4) {
            snprintf(why, why_size, "국고 칸과 재고 칸이 겹칩니다");
            return false;
        }
    }
    out->world_pointer = static_cast<uint32_t>(world);
    out->treasury = static_cast<uint32_t>(treasury);
    out->stock_step = static_cast<uint32_t>(v[2][0]);
    out->stock_first = static_cast<uint32_t>(v[2][1]);
    out->used_step = static_cast<uint32_t>(v[3][0]);
    out->used_first = static_cast<uint32_t>(v[3][1]);
    snprintf(why, why_size, "%s", "");
    return true;
}

// 서명마다의 결과 칸에 이름과 글을 채운다 — 찾기 전에. 머리말조차 못 읽은 이미지에서도 서명 표를 볼 수 있다(테스트와 srkit locate 가 쓴다).
template <class Row>
void name_rows(const Row *table, int n, SigRow *rows)
{
    if (rows == nullptr)
        return;
    for (int i = 0; i < n * STATE_SIGS; i++) {
        rows[i].name = table[i / STATE_SIGS].name;
        rows[i].text = table[i / STATE_SIGS].sigs[i % STATE_SIGS];
        rows[i].count = 0;
        rows[i].at = 0;
        rows[i].value = 0;
        rows[i].value2 = 0;
    }
}

}  // namespace

// 올라와 있는 실행 파일에는 읽을 수 없는 쪽이 있을 수 있다(보호된 구역). 그때도 죽지 않는다 — 여기서 예외가 새면 게임이 뜨다가 죽는다.
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search_legacy · search_state · search_values)과 따로 뗐다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out)
{
    __try {
        return search_legacy(image, size, out);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return "실행 파일에 읽을 수 없는 곳이 있습니다";
    }
}

bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    name_rows(STATE, STATE_WANTED, rows);
    __try {
        return search_state(image, size, out, rows, why, why_size);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        snprintf(why, why_size, "실행 파일에 읽을 수 없는 곳이 있습니다");
        return false;
    }
}

bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size)
{
    name_rows(VALUES, VALUE_WANTED, rows);
    __try {
        return search_values(image, size, out, rows, why, why_size);
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

- [ ] **Step 7: 내보내기를 고친다**

`native/srtoybox/exports.cpp`:

익명 이름공간 안, `struct RecordingSink` 앞에 더한다:

```cpp
// 서명마다의 결과를 글로: 한 줄에 "<찾을 것>\t<서명 글>\t<맞은 횟수>\t<처음 맞은 자리>\t<읽어 낸 값>\t<둘째 값>"(뒤의 넷은 16진수).
std::string rows_text(const SigRow *rows, int n)
{
    std::string text;
    char numbers[80];
    for (int i = 0; i < n; i++) {
        snprintf(numbers, sizeof(numbers), "\t%x\t%x\t%x\t%x\n", static_cast<unsigned>(rows[i].count), rows[i].at, rows[i].value,
                 rows[i].value2);
        text += std::string(rows[i].name) + '\t' + rows[i].text + numbers;
    }
    return text;
}
```

`srtoybox_locate_state` 위의 주석 둘째 줄과 본문의 `if (rows != nullptr) { … }` 블록을 다음으로 바꾼다:

```cpp
// rows 에는 서명마다 한 줄(rows_text). 필요 없으면 nullptr.
```

```cpp
    if (rows != nullptr)
        put(rows_text(table, STATE_WANTED * STATE_SIGS), rows, rows_size);
```

`srtoybox_locate_state` 다음에 더한다:

```cpp
// 새 찾기(값 묶음, 서명으로). 0 이면 out 을 채웠다. -1 이면 error 에 까닭. rows 는 srtoybox_locate_state 와 같다.
EXPORT int srtoybox_locate_values(const unsigned char *image, unsigned long long size, ValueLayout *out, char *error, int error_size,
                                  char *rows, int rows_size)
{
    ValueLayout found = {};
    SigRow table[VALUE_WANTED * STATE_SIGS];
    char why[160] = "";
    const bool ok = locate_values(image, static_cast<size_t>(size), &found, table, why, sizeof(why));
    if (rows != nullptr)
        put(rows_text(table, VALUE_WANTED * STATE_SIGS), rows, rows_size);
    if (!ok) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

EXPORT int srtoybox_stock_slots(void)
{
    return STOCK_SLOTS;
}
```

- [ ] **Step 8: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -5`
Expected: 빌드 성공, `76 passed` (55 + 21).

- [ ] **Step 9: `srkit locate` 가 값 묶음도 보이게 한다**

`src/srkit/cli.py` 의 `cmd_locate` 전체를 다음으로 바꾼다:

```python
def _print_sig_rows(rows) -> None:
    for row in rows:
        mark = "한 번" if row.count == 1 else "안 맞음" if row.count == 0 else "여러 번"
        value = f"{row.value:#x}" + (f" · {row.value2:#x}" if row.value2 else "")
        print(f"  {row.name:<15} {mark:<5} 자리 {row.at:#010x} → {value:<16} {row.text}")


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
    _print_sig_rows(found.rows)
    if found.state is None:
        print(f"찾지 못했습니다: {found.state_why}")
        print("ToyBox 는 이 빌드에서 게임을 읽지 못합니다. uv run srkit sig-mine <RVA> 로 서명을 다시 뽑습니다(docs/11).")
    else:
        for name in toybox.STATE_FIELDS:
            print(f"  {found.state[name]:#010x}  {toybox.ADDRESS_NAMES[name]}")
    print("새 찾기 — 값을 읽고 쓰는 자리(서명. 내장 치트와 무관하다. 둘을 읽는 서명은 간격 · 첫 칸):")
    _print_sig_rows(found.value_rows)
    if found.values is None:
        print(f"찾지 못했습니다: {found.values_why}")
        print("ToyBox 의 돈 탭이 이 빌드에서 꺼집니다. uv run srkit sig-mine [--offset] 으로 서명을 다시 뽑습니다(docs/11).")
    else:
        for name in toybox.VALUE_FIELDS:
            print(f"  {found.values[name]:#010x}  {toybox.VALUE_NAMES[name]}")
    print("옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):")
    if found.legacy is None:
        print(f"  찾지 못했습니다: {found.legacy_why}")
        print("  내장 치트로 도는 기능은 글쇠 방식으로 동작합니다(docs/10).")
    else:
        for name in toybox.LEGACY_FIELDS:
            print(f"  {found.legacy[name]:#010x}  {toybox.ADDRESS_NAMES[name]}")
    if found.state is not None and found.values is not None and found.legacy is not None:
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if found.state is not None and found.values is not None else 1
```

Run: `uv run srkit locate; echo "exit=$?"`
Expected: 상태 묶음 21줄이 모두 `한 번`, 값 묶음 12줄이 모두 `한 번`(재고 줄은 `0x150 · 0x14da4`, 쓰는 물자 줄은 `0x84 · 0x18`), `0x01af5868  세계 자료 객체의 포인터…` · `0x00014b88  국고 칸…` 등 여섯 줄, 옛 찾기 셋, `모두 찾았습니다`, `exit=0`.

- [ ] **Step 10: 전체 테스트를 돌리고 커밋한다**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `261 passed` (240 + 21).

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/exports.cpp src/srkit/toybox.py src/srkit/cli.py tests/toybox_fake_exe.py tests/toybox_cheat_oracle.py tests/test_toybox_game.py && git commit -q -F - <<'EOF'
feat: ToyBox — 값의 자리(국고 칸 · 재고 칸 · 쓰는 물자 표)를 치트와 무관한 서명으로 찾는다

- locate_values: 서명 12개(찾을 것 넷 × 셋). 읽어 낸 자리가 말이 되는지도 본다(범위, 간격, 겹침)
- 상태 묶음: 찾은 주소가 쓸 수 있는 자료 구역 안이고 서로 겹치지 않아야 한다
- srkit locate 가 값 묶음을 함께 보인다. 테스트: 치트 코드 밖 · 서로 다른 함수 · 치트 본문에서 읽은 값과 같다
- 아직 게임의 메모리에 쓰지 않는다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -2
```

- [ ] **Step 11: PR 을 올리고 머지한다**

스크래치에 `pr-values-locate.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 1 · 2 의 커밋 요약), 값 묶음의 서명 표, "이 PR 은 게임의 메모리에 쓰지 않는다", 계획 (가)의 최종 검토가 미룬 것 가운데 이 PR 이 다룬 둘(주소의 구역 · 겹침 대조, `sig-mine` 이 빼는 범위), `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-values-locate && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-values-locate --title "feat: ToyBox — 값의 자리를 내장 치트와 무관한 서명으로 찾는다" --body-file "<스크래치>/pr-values-locate.md"
```

```bash
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git log --oneline -1
```

Expected: 머지 커밋이 `develop` 의 머리다. (머지가 거부되면 Global Constraints 대로 한다.)

---

### Task 3: 값 계산 (`values`)

**브랜치:** `feat/toybox-values-write` (PR #A 가 들어간 `develop` 에서 나눈다)

**Files:**
- Create: `native/srtoybox/values.h`, `native/srtoybox/values.cpp`, `tests/test_toybox_values.py`
- Modify: `native/srtoybox/exports.cpp`, `src/srkit/toybox.py` (`SOURCES`)

**Interfaces:**
- Consumes: 없음(순수 함수).
- Produces (`values.h`):
  - `enum class Change { Add, Set, Floor };` — 더하기(음수면 빼기) · 이 값으로 · 바닥
  - `enum class Verdict { Write, Nothing, Refuse };`
  - `const double TREASURY_LIMIT = 1e15;` `const double STOCK_LIMIT = 1e9;`
  - `Verdict treasury_value(double now, Change change, double amount, double *out);`
  - `Verdict stock_value(float now, Change change, double amount, float *out);`
  - `std::string short_number(double value);` — `14.43 B` · `50.00 K` · `999` · `-1.00 T` · 수가 아니면 `?`
- Produces (내보내기): `int srtoybox_value(int stock, double now, int change, double amount, double *out)`(돌려주는 값은 `Verdict`), `int srtoybox_short_number(double value, char *out, int size)`.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-values-write && git log --oneline -1
```

Expected: PR #A 의 머지 커밋.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_toybox_values.py` 를 만든다:

```python
"""ToyBox 의 값 쓰기: 값 계산(values) · 게임의 값 읽기와 쓰기(game) · 요청의 대기열(keeper). 게임은 띄우지 않는다."""
import ctypes

import pytest

from srkit import toybox

ADD, SET, FLOOR = 0, 1, 2                 # native/srtoybox/values.h 의 Change
WRITE, NOTHING, REFUSE = 0, 1, 2          # 〃 Verdict
NAN, INF = float("nan"), float("inf")


@pytest.fixture(scope="module")
def lib(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = toybox.library(cfg)
    lib.srtoybox_value.argtypes = [ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    lib.srtoybox_short_number.argtypes = [ctypes.c_double, ctypes.c_char_p, ctypes.c_int]
    return lib


def text(call, *args, size: int = 4096) -> str | None:
    """글을 돌려주는 내보내기 함수를 부른다. 함수가 -1 을 주면 None."""
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return None if n < 0 else buf.raw[:n].decode("utf-8")


def value(lib, stock: bool, now: float, change: int, amount: float) -> tuple[int, float | None]:
    """(판정, 쓸 값). 쓰지 않으면 쓸 값은 None."""
    out = ctypes.c_double(-1.0)
    verdict = lib.srtoybox_value(int(stock), now, change, amount, ctypes.byref(out))
    return verdict, (out.value if verdict == WRITE else None)


def test_treasury_values(lib):
    assert value(lib, False, 14.43e9, ADD, 10e9) == (WRITE, 24.43e9)
    assert value(lib, False, 14.43e9, ADD, -100e9) == (WRITE, 14.43e9 - 100e9)    # 국고는 음수가 될 수 있다
    assert value(lib, False, 14.43e9, SET, 0.0) == (WRITE, 0.0)
    assert value(lib, False, 5.0, SET, 5.0) == (NOTHING, None)                    # 이미 그 값이다
    assert value(lib, False, 1e9, FLOOR, 5e9) == (WRITE, 5e9)
    assert value(lib, False, 9e9, FLOOR, 5e9) == (NOTHING, None)                  # 바닥 위다
    assert value(lib, False, 9.99e14, ADD, 1e14) == (WRITE, 1e15)                 # ±$1,000 T 안으로 자른다
    assert value(lib, False, -9.99e14, ADD, -1e14) == (WRITE, -1e15)
    assert value(lib, False, 5e15, FLOOR, 1e9) == (NOTHING, None)                 # 바닥은 값을 내리지 않는다 — 한도 밖의 값이어도


def test_stock_values(lib):
    assert value(lib, True, 1000.0, ADD, 1e6) == (WRITE, 1001000.0)
    assert value(lib, True, 1000.0, ADD, -1e8) == (WRITE, 0.0)                    # 0 아래로 내려가지 않는다
    assert value(lib, True, 0.0, ADD, -5.0) == (NOTHING, None)
    assert value(lib, True, 1000.0, SET, -3.0) == (WRITE, 0.0)
    assert value(lib, True, 9.99e8, ADD, 1e8) == (WRITE, 1e9)                     # 10억 이하로 자른다
    assert value(lib, True, 800.0, FLOOR, 1000.0) == (WRITE, 1000.0)
    assert value(lib, True, 1200.0, FLOOR, 1000.0) == (NOTHING, None)
    assert value(lib, True, 16777216.0, ADD, 1.0) == (NOTHING, None)              # float 의 눈금보다 작은 변화는 쓸 것이 없다


@pytest.mark.parametrize("now, amount", [(NAN, 1.0), (INF, 1.0), (-INF, 1.0), (1.0, NAN), (1.0, INF)],
                         ids=["now-nan", "now-inf", "now-minus-inf", "amount-nan", "amount-inf"])
def test_values_refuse_what_is_not_a_number(lib, now, amount):
    """지금 값이 수가 아니면 구조가 바뀐 것일 수 있다 — "이 값으로"조차 쓰지 않는다."""
    for stock in (False, True):
        for change in (ADD, SET, FLOOR):
            assert value(lib, stock, now, change, amount) == (REFUSE, None)


def test_short_numbers_look_like_the_games(lib):
    """게임의 재무 패널과 같은 줄임 표기($ 14.43 B, $50.00 K)."""
    short = lambda v: text(lib.srtoybox_short_number, v)
    assert [short(v) for v in (0, 7, 999.4, 1000, 50000, 14.43e9, 1.1e6, 999999, 1e12, -1e12, -24.5e9, 0.3, -0.3)] == \
        ["0", "7", "999", "1.00 K", "50.00 K", "14.43 B", "1.10 M", "1.00 M", "1.00 T", "-1.00 T", "-24.50 B", "0", "0"]
    assert short(NAN) == "?" and short(INF) == "?"
```

- [ ] **Step 3: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -4`
Expected: 모두 ERROR — `AttributeError: function 'srtoybox_value' not found`.

- [ ] **Step 4: `values` 를 만든다**

`native/srtoybox/values.h`:

```cpp
// 값 계산: 지금 값 + 요청 → 쓸 값. 창도 게임도 모르는 순수 함수다.
#pragma once

#include <string>

enum class Change {
    Add,      // 더한다(음수면 뺀다)
    Set,      // 이 값으로
    Floor,    // 바닥: 지금 값이 이보다 작으면 이 값으로, 아니면 그대로(최소 유지)
};

enum class Verdict {
    Write,    // *out 을 쓴다
    Nothing,  // 바꿀 것이 없다(이미 그 값이다, 바닥 위다)
    Refuse,   // 쓰지 않는다: 지금 값이나 요청이 유한한 수가 아니다 — 구조가 바뀐 것일 수 있다
};

const double TREASURY_LIMIT = 1e15;   // 국고의 결과는 ±$1,000 T 안으로 자른다. 음수는 된다(게임이 허용한다)
const double STOCK_LIMIT = 1e9;       // 재고의 결과는 0 이상 10억 이하로 자른다

Verdict treasury_value(double now, Change change, double amount, double *out);
// 셈은 double 로 하고 결과를 float 로 바꾼다(재고 칸이 float 다 — 약 1,677만부터 낱개 단위가 반올림된다).
Verdict stock_value(float now, Change change, double amount, float *out);

// 게임의 재무 패널과 같은 줄임 표기: 999 · 50.00 K · 1.10 M · 14.43 B · -1.00 T. 유한한 수가 아니면 "?".
std::string short_number(double value);
```

`native/srtoybox/values.cpp`:

```cpp
#include "values.h"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace {

// 자르기 전의 바라는 값. 쓸 것이 없거나 쓰면 안 되면 그 판정을, 셈했으면 Verdict::Write 와 *out.
Verdict wanted(double now, Change change, double amount, double *out)
{
    if (!std::isfinite(now) || !std::isfinite(amount))
        return Verdict::Refuse;
    if (change == Change::Floor && now >= amount)
        return Verdict::Nothing;     // 바닥은 값을 내리지 않는다 — 한도 밖의 값이어도 자르지 않는다
    *out = change == Change::Add ? now + amount : amount;
    return Verdict::Write;
}

}  // namespace

Verdict treasury_value(double now, Change change, double amount, double *out)
{
    double value = 0;
    const Verdict verdict = wanted(now, change, amount, &value);
    if (verdict != Verdict::Write)
        return verdict;
    value = std::min(TREASURY_LIMIT, std::max(-TREASURY_LIMIT, value));
    if (value == now)
        return Verdict::Nothing;
    *out = value;
    return Verdict::Write;
}

Verdict stock_value(float now, Change change, double amount, float *out)
{
    double value = 0;
    const Verdict verdict = wanted(now, change, amount, &value);
    if (verdict != Verdict::Write)
        return verdict;
    const float next = static_cast<float>(std::min(STOCK_LIMIT, std::max(0.0, value)));
    if (next == now)
        return Verdict::Nothing;
    *out = next;
    return Verdict::Write;
}

std::string short_number(double value)
{
    if (!std::isfinite(value))
        return "?";
    const double size = std::fabs(value);
    if (size < 0.5)
        return "0";                  // "-0" 이 되지 않게
    char text[40];
    if (size < 999.5)
        snprintf(text, sizeof(text), "%.0f", value);
    else if (size < 999.995e3)
        snprintf(text, sizeof(text), "%.2f K", value / 1e3);
    else if (size < 999.995e6)
        snprintf(text, sizeof(text), "%.2f M", value / 1e6);
    else if (size < 999.995e9)
        snprintf(text, sizeof(text), "%.2f B", value / 1e9);
    else
        snprintf(text, sizeof(text), "%.2f T", value / 1e12);
    return text;
}
```

`native/srtoybox/exports.cpp` — include 에 `#include "values.h"` 를 더하고(`#include "ui.h"` 다음), `srtoybox_hotkey_name` 다음에 더한다:

```cpp
// 테스트: 값 계산(values.h). stock 이 0 이면 국고, 아니면 재고. change: 0 더하기, 1 이 값으로, 2 바닥.
// 돌려주는 값은 Verdict: 0 쓴다(*out 에 쓸 값), 1 바꿀 것이 없다, 2 쓰지 않는다. 인자가 틀리면 -1.
EXPORT int srtoybox_value(int stock, double now, int change, double amount, double *out)
{
    if (change < 0 || change > 2 || out == nullptr)
        return -1;
    double next = 0;
    float next_stock = 0;       // (small 은 windows.h 가 매크로로 쓴다)
    const Verdict verdict = stock != 0 ? stock_value(static_cast<float>(now), static_cast<Change>(change), amount, &next_stock)
                                       : treasury_value(now, static_cast<Change>(change), amount, &next);
    if (verdict == Verdict::Write)
        *out = stock != 0 ? static_cast<double>(next_stock) : next;
    return static_cast<int>(verdict);
}

EXPORT int srtoybox_short_number(double value, char *out, int size)
{
    return put(short_number(value), out, size);
}
```

`src/srkit/toybox.py` 의 `SOURCES` 에서 `"sigs.cpp", "locate.cpp",` 를 `"sigs.cpp", "locate.cpp", "values.cpp",` 로 바꾼다.

- [ ] **Step 5: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -3`
Expected: `8 passed`.

- [ ] **Step 6: 커밋한다**

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/values.h native/srtoybox/values.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox — 값 계산(더하기 · 이 값으로 · 바닥)과 줄임 표기

국고는 음수가 되고 ±$1,000 T 안으로, 재고는 0 이상 10억 이하로 자른다. 지금 값이 수가 아니면 쓰지 않는다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 4: 게임의 값을 읽고 쓴다 (`game`)

**브랜치:** `feat/toybox-values-write`

**Files:**
- Modify: `native/srtoybox/game.h`, `native/srtoybox/game.cpp` (둘 다 통째로 다시 쓴다), `native/srtoybox/exports.cpp`
- Modify: `tests/toybox_fake_game.py`
- Test: `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: Task 2 의 `ValueLayout` · `locate_values` · `STOCK_SLOTS` · `SigRow.value2`, 테스트 도구 `toybox_fake_exe.sig_image` · `build`.
- Produces (`game.h`):
  - `struct GameValues { bool ok; double treasury; bool used[STOCK_SLOTS]; float stock[STOCK_SLOTS]; };`
  - `enum class Wrote { Done, NotInGame, NotUsed, BadValue, Failed, Off };`
  - `GameValues read_values(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout);`
  - `Wrote write_treasury(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, double value);`
  - `Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value);`
  - `void game_init_from(const uint8_t *base, size_t size);` `bool game_reads();`
  - `std::string game_values_off();` — 값을 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글
  - `GameValues game_values();` `Wrote game_write_treasury(double value);` `Wrote game_write_stock(int slot, float value);`
  - `void game_set_values_for_test(const ValueLayout *layout);`
- Produces (내보내기): `srtoybox_values_read(base, at, layout, out, size)`, `srtoybox_values_write(base, at, layout, slot, value) -> int`(`Wrote`. `slot` −1 = 국고), `srtoybox_test_values(layout)`, `srtoybox_test_init(image, size)`, `srtoybox_game_flags() -> int`(1 읽는다 · 2 부를 수 있다 · 4 값을 쓸 수 있다), `srtoybox_values_off(out, size)`.
- Produces (테스트 도구 — `toybox_fake_game.FakeGame`): `.layout`(`ValueLayout`), `.world`, `.use(slot, on=True)`, `.treasury(index)` · `.set_treasury(index, value)`, `.stock(index, slot)` · `.set_stock(index, slot, value)`, `.lock(index, protection=0x02) -> int`. 상수 `WORLD_POINTER`, `LAYOUT`.

값을 쓸 수 없는 까닭의 글(창과 테스트가 그대로 쓴다):

| 상황 | `game_values_off()` |
|---|---|
| 게임을 읽지 못한다(상태 묶음을 못 찾았다, `SRTOYBOX_READ=0`) | `게임 상태를 읽을 수 있을 때만 씁니다.` |
| 값 묶음을 찾지 못했다 | `이 게임 판에서는 쓸 수 없습니다 (<locate_values 의 까닭>)` |
| `SRTOYBOX_WRITE=0` | `값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)` |
| 쓰기가 실패해 이번 실행에서 꺼졌다 | `값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.` |

- [ ] **Step 1: 가짜 게임에 값을 더한다**

`tests/toybox_fake_game.py` 전체를 다음으로 바꾼다:

```python
"""가짜 게임 메모리: ToyBox 가 읽고 쓰는 전역과 지역 객체를 Python 버퍼로 흉내 낸다.

tests/test_toybox_game.py · test_toybox_values.py 와 tests/toybox_overlay_probe.py 가 쓴다(pytest 가 직접 모으는 테스트 파일이 아니다).
전역은 mem 의 앞쪽에, 지역 표는 0x1000 부터 있다. 지역 객체와 세계 자료 객체는 게임처럼 따로 잡은 버퍼이고 표와 포인터가 그 주소를 가리킨다.
값의 자리(LAYOUT)는 진짜 게임의 것보다 작게 잡았다 — ToyBox 는 자리를 찾은 것(ValueLayout)에서만 읽는다.
"""
import ctypes
import struct
from ctypes import wintypes

from srkit.toybox import GameAddresses, ValueLayout

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, WORLD_POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x1000
LAYOUT = dict(world_pointer=WORLD_POINTER, treasury=0x40, stock_first=0x60, stock_step=0x10, used_first=0x18, used_step=0x84)
OBJECT_SIZE = 0x200

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]


class FakeGame:
    def __init__(self):
        self.mem = (ctypes.c_ubyte * 0x4000)()
        self.base = ctypes.addressof(self.mem)
        self.at = GameAddresses(handler=0, context=0x40, multiplayer=MULTIPLAYER, options=OPTIONS, program_state=PROGRAM,
                                mode_state=MODE, player_index=INDEX, player_pointer=POINTER, region_table=TABLE, region_count=COUNT)
        self.layout = ValueLayout(**LAYOUT)
        self.objects: dict[int, ctypes.Array] = {}
        self.where: dict[int, int] = {}                           # 지역 객체가 지금 있는 주소(lock 으로 옮기면 바뀐다)
        self.world = (ctypes.c_ubyte * 0x800)()                   # 세계 자료 객체: "이 물자를 쓰는가"의 표가 있다
        self.poke(WORLD_POINTER, "<Q", ctypes.addressof(self.world))
        self.menu()

    def poke(self, offset: int, fmt: str, value: int) -> None:
        struct.pack_into(fmt, self.mem, offset, value)

    def peek(self, offset: int, fmt: str) -> int:
        return struct.unpack_from(fmt, self.mem, offset)[0]

    def region(self, index: int, number: int, alive: int = 2) -> None:
        """지역 객체 하나: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word). 값의 칸은 0 으로 차 있다."""
        obj = (ctypes.c_ubyte * OBJECT_SIZE)()
        struct.pack_into("<IHHH", obj, 0, alive, index, 0, number)
        self.objects[index] = obj
        self.where[index] = ctypes.addressof(obj)
        self.poke(TABLE + 8 * index, "<Q", self.where[index])
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
        self.poke(POINTER, "<Q", self.where[index])

    def use(self, slot: int, on: bool = True) -> None:
        """이번 판에서 그 물자를 쓴다(세계 자료 객체의 float 가 0 보다 크다) / 안 쓴다."""
        struct.pack_into("<f", self.world, LAYOUT["used_first"] + LAYOUT["used_step"] * slot, 1.0 if on else 0.0)

    def _read(self, index: int, offset: int, fmt: str):
        return struct.unpack(fmt, ctypes.string_at(self.where[index] + offset, struct.calcsize(fmt)))[0]

    def _write(self, index: int, offset: int, fmt: str, value) -> None:
        ctypes.memmove(self.where[index] + offset, struct.pack(fmt, value), struct.calcsize(fmt))

    def treasury(self, index: int) -> float:
        return self._read(index, LAYOUT["treasury"], "<d")

    def set_treasury(self, index: int, value: float) -> None:
        self._write(index, LAYOUT["treasury"], "<d", value)

    def stock(self, index: int, slot: int) -> float:
        return self._read(index, LAYOUT["stock_first"] + LAYOUT["stock_step"] * slot, "<f")

    def set_stock(self, index: int, slot: int, value: float) -> None:
        self._write(index, LAYOUT["stock_first"] + LAYOUT["stock_step"] * slot, "<f", value)

    def snapshot(self, index: int) -> bytes:
        """그 지역 객체의 지금 바이트 전부."""
        return ctypes.string_at(self.where[index], OBJECT_SIZE)

    def lock(self, index: int, protection: int = 0x02) -> int:
        """그 지역 객체를 따로 잡은 쪽으로 옮기고 그 쪽을 쓸 수 없게 한다(0x02 읽기 전용, 0x20 실행 · 읽기). 새 주소를 돌려준다.

        읽을 수는 있으므로 게임 상태는 그대로 읽힌다 — 쓰기만 안 된다. 그 지역으로 play 하고 있었으면 다시 play 해야 한다.
        (쪽은 돌려주지 않는다. 테스트 프로세스가 끝나면 없어진다.)
        """
        page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
        ctypes.memmove(page, self.where[index], OBJECT_SIZE)
        old = wintypes.DWORD()
        assert kernel32.VirtualProtect(page, 0x1000, protection, ctypes.byref(old))
        self.where[index] = page
        self.poke(TABLE + 8 * index, "<Q", page)
        return page
```

`tests/test_toybox_game.py` 와 `tests/toybox_overlay_probe.py` 가 지역 객체에 직접 쓰는 곳(`struct.pack_into(…, fake.objects[…], …)`)은 그대로 된다(객체가 커졌을 뿐이다).

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -3`
Expected: `76 passed` — 가짜 게임을 고친 것이 지금의 테스트를 깨지 않는다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_toybox_values.py`:

import 를 다음으로 바꾼다:

```python
import ctypes
import struct

import pytest

import toybox_fake_exe
from toybox_fake_game import LAYOUT, MULTIPLAYER, OPTIONS, POINTER, TABLE, WORLD_POINTER, FakeGame
from srkit import toybox
```

상수 줄(`NAN, INF = …`) 다음에 더한다:

```python
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF = range(6)      # native/srtoybox/game.h 의 Wrote
TREASURY = -1                                                       # 쓰기의 대상: 국고. 0 … 11 은 그 칸의 재고
READS, CALLS, WRITES = 1, 2, 4                                      # srtoybox_game_flags 의 비트
UNREAD = "게임 상태를 읽을 수 있을 때만 씁니다."
FAILED_OFF = "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다."
```

고정물 `lib` 의 `return lib` 앞에 더한다:

```python
    pointer = ctypes.POINTER
    lib.srtoybox_values_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ValueLayout), ctypes.c_char_p,
                                         ctypes.c_int]
    lib.srtoybox_values_write.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ValueLayout), ctypes.c_int,
                                          ctypes.c_double]
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    lib.srtoybox_test_init.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong]
    lib.srtoybox_values_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
```

파일 끝에 덧붙인다:

```python


def germany() -> FakeGame:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 국고 $14.43 B. 물자 0 · 3 · 7 을 쓰고 재고가 1000 · 2500 · 0. 폴란드(141)의 국고는 $5 B."""
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.play(176)
    fake.set_treasury(176, 14.43e9)
    fake.set_treasury(141, 5e9)
    for slot, amount in ((0, 1000.0), (3, 2500.0), (7, 0.0)):
        fake.use(slot)
        fake.set_stock(176, slot, amount)
    return fake


def read(lib, fake: FakeGame) -> dict[str, str]:
    out = ctypes.create_string_buffer(1024)
    assert lib.srtoybox_values_read(fake.base, ctypes.byref(fake.at), ctypes.byref(fake.layout), out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def write(lib, fake: FakeGame, slot: int, amount: float) -> int:
    return lib.srtoybox_values_write(fake.base, ctypes.byref(fake.at), ctypes.byref(fake.layout), slot, amount)


def everything(fake: FakeGame) -> bytes:
    """가짜 게임의 메모리 전부(전역 · 세계 자료 · 지역 객체들) — 쓰기가 다른 곳을 건드리지 않았는지 볼 때 쓴다."""
    return bytes(fake.mem) + bytes(fake.world) + b"".join(fake.snapshot(index) for index in sorted(fake.objects))


def test_values_are_read_from_the_players_region(lib):
    assert read(lib, germany()) == {"ok": "1", "treasury": "14430000000", "used": "100100010000",
                                    "stock": "1000,0,0,2500,0,0,0,0,0,0,0,0"}


@pytest.mark.parametrize("flaw", ["menu", "no-world", "unreadable-world", "stock-nan"])
def test_values_are_not_read_when_the_game_does_not_add_up(lib, flaw):
    fake = germany()
    if flaw == "menu":
        fake.menu()
    elif flaw == "no-world":
        fake.poke(WORLD_POINTER, "<Q", 0)
    elif flaw == "unreadable-world":
        fake.poke(WORLD_POINTER, "<Q", 0x00007FFFFFFF0000)
    else:
        fake.set_stock(176, 9, float("nan"))                 # 쓰지 않는 물자의 칸이어도: 구조가 바뀐 것일 수 있다
    assert read(lib, fake)["ok"] == "0"


def test_a_write_changes_only_that_slot(lib):
    """쓰는 곳은 플레이어 지역 객체의 그 칸뿐이다. 둘레의 바이트 · 다른 지역 · 전역 · 치트 허용 비트는 그대로다."""
    fake = germany()
    before = everything(fake)
    assert write(lib, fake, TREASURY, 24.43e9) == DONE
    assert fake.treasury(176) == 24.43e9
    after = everything(fake)
    changed = [i for i in range(len(before)) if before[i] != after[i]]
    assert changed and set(changed) <= set(range(len(before) - 0x200 + LAYOUT["treasury"], len(before) - 0x200 + LAYOUT["treasury"] + 8))
    assert fake.treasury(141) == 5e9 and fake.peek(OPTIONS, "<I") == 0
    assert write(lib, fake, 3, 9999.0) == DONE
    assert fake.stock(176, 3) == 9999.0
    last = everything(fake)
    slot = len(before) - 0x200 + LAYOUT["stock_first"] + LAYOUT["stock_step"] * 3
    assert set(i for i in range(len(after)) if after[i] != last[i]) <= set(range(slot, slot + 4))
    assert write(lib, fake, TREASURY, -1e12) == DONE and fake.treasury(176) == -1e12      # 국고는 음수가 된다


@pytest.mark.parametrize("flaw", ["menu", "multiplayer", "inconsistent", "unreadable"])
def test_nothing_is_written_outside_a_game_it_can_trust(lib, flaw):
    fake = germany()
    if flaw == "menu":
        fake.menu()
    elif flaw == "multiplayer":
        fake.poke(MULTIPLAYER, "<B", 1)
    elif flaw == "inconsistent":
        struct.pack_into("<H", fake.objects[176], 4, 175)                 # 객체가 아는 자기 인덱스가 다르다
    else:
        fake.poke(POINTER, "<Q", 0x00007FFFFFFF0000)
        fake.poke(TABLE + 8 * 176, "<Q", 0x00007FFFFFFF0000)
    before = everything(fake)
    assert write(lib, fake, TREASURY, 1.0) == NOT_IN_GAME
    assert write(lib, fake, 3, 1.0) == NOT_IN_GAME
    assert everything(fake) == before


def test_a_value_or_a_slot_that_makes_no_sense_is_not_written(lib):
    fake = germany()
    before = everything(fake)
    for amount in (float("nan"), float("inf"), float("-inf")):
        assert write(lib, fake, TREASURY, amount) == BAD_VALUE
        assert write(lib, fake, 3, amount) == BAD_VALUE
    assert write(lib, fake, 3, -1.0) == BAD_VALUE                         # 재고는 음수가 되지 않는다
    assert write(lib, fake, 12, 1.0) == BAD_VALUE and write(lib, fake, -2, 1.0) == BAD_VALUE   # 없는 칸
    assert write(lib, fake, 5, 1.0) == NOT_USED                           # 이번 판에서 쓰지 않는 물자
    struct.pack_into("<f", fake.world, LAYOUT["used_first"] + LAYOUT["used_step"] * 3, float("nan"))
    assert write(lib, fake, 3, 1.0) == NOT_USED                           # "쓰는가"가 수가 아니다
    fake.poke(WORLD_POINTER, "<Q", 0)
    assert write(lib, fake, 0, 1.0) == NOT_USED                           # 세계 자료를 읽을 수 없다
    objects = len(fake.mem) + len(fake.world)
    assert everything(fake)[objects:] == before[objects:]                 # 지역 객체들은 그대로다(전역과 세계 자료는 방금 테스트가 고쳤다)


@pytest.mark.parametrize("protection", [0x02, 0x20], ids=["read-only", "execute-read"])
def test_a_slot_on_a_page_that_is_not_read_write_is_not_written(lib, protection):
    """낡은 포인터가 읽을 수는 있지만 쓰면 안 되는 곳을 가리킨다. WriteProcessMemory 는 실행 쪽이면 보호를 풀고 쓴다 —
    그 전에 가려야 한다. 죽지 않고 실패로 돌아온다."""
    fake = germany()
    fake.lock(176, protection)
    fake.play(176)
    assert read(lib, fake)["ok"] == "1"                                   # 읽기는 된다
    before = fake.snapshot(176)
    assert write(lib, fake, TREASURY, 1.0) == FAILED
    assert write(lib, fake, 3, 1.0) == FAILED
    assert fake.snapshot(176) == before


@pytest.fixture(scope="module")
def all_sigs(lib):
    """DLL 에 든 서명 표 둘: ([상태 묶음 21개], [값 묶음 12개]) — 저마다 (찾을 것, 서명 글)."""
    return ([(row.name, row.text) for row in toybox.state_of(lib, b"")[2]],
            [(row.name, row.text) for row in toybox.values_of(lib, b"")[2]])


def init(lib, image: bytes, tmp_path, monkeypatch) -> tuple[int, str, str]:
    """게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다: (아는 것의 비트, 값을 쓸 수 없는 까닭, 로그)."""
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    try:
        lib.srtoybox_test_init(image, len(image))
        flags, off = lib.srtoybox_game_flags(), text(lib.srtoybox_values_off)
    finally:
        lib.srtoybox_test_game(None, None, None)              # 이미지를 놓기 전에 이 프로세스의 "게임"을 비운다
    log = tmp_path / "toybox.log"
    return flags, off, log.read_text(encoding="utf-8") if log.is_file() else ""


def test_startup_finds_the_state_and_the_values_without_any_cheat(lib, all_sigs, tmp_path, monkeypatch):
    """치트가 없는 빌드: 상태를 읽고 값을 쓴다. 명령 처리 함수는 없다 — 그것으로 도는 기능만 글쇠 방식이다."""
    state, values = all_sigs
    flags, off, log = init(lib, toybox_fake_exe.sig_image(state + values), tmp_path, monkeypatch)
    assert flags == READS | WRITES and off == ""
    assert "게임 상태를 읽습니다 (서명 21개 가운데 21개" in log
    assert "값을 씁니다 (국고 +0x1230, 재고 +0x2000 간격 0x20 × 12)" in log
    assert "명령 처리 함수를 찾지 못했습니다" in log and "맞지 않은 서명" not in log


def test_startup_without_the_values_keeps_everything_else(lib, all_sigs, tmp_path, monkeypatch):
    """값 묶음만 못 찾으면 돈 탭만 꺼진다. 까닭이 로그와 창에 같은 글로 남는다."""
    state, _values = all_sigs
    flags, off, log = init(lib, toybox_fake_exe.build(state), tmp_path, monkeypatch)
    assert flags == READS | CALLS
    assert off == "이 게임 판에서는 쓸 수 없습니다 (세계 자료 포인터: 서명 3개 가운데 0개)"
    assert "값을 쓸 수 없습니다 (세계 자료 포인터: 서명 3개 가운데 0개)" in log
    assert "옛 방식(내장 치트)으로 도는 기능이" in log


def test_startup_names_the_signatures_that_did_not_match(lib, all_sigs, tmp_path, monkeypatch):
    """셋 가운데 둘로 찾았을 때도, 맞지 않은 서명이 무엇인지 로그에 남는다 — 다음 업데이트에서 깨질 것을 미리 안다."""
    state, values = all_sigs
    flags, _off, log = init(lib, toybox_fake_exe.sig_image(state + values, broken={0, 22}), tmp_path, monkeypatch)
    assert flags == READS | WRITES
    assert "게임 상태를 읽습니다 (서명 21개 가운데 20개" in log
    assert "맞지 않은 서명: multiplayer #1 (안 맞음)" in log and "맞지 않은 서명: world_pointer #2 (안 맞음)" in log


def test_startup_with_everything(lib, all_sigs, tmp_path, monkeypatch):
    state, values = all_sigs
    flags, off, _log = init(lib, toybox_fake_exe.build(state + values), tmp_path, monkeypatch)
    assert flags == READS | CALLS | WRITES and off == ""


@pytest.mark.parametrize("image", [b"", bytes(0x1000)], ids=["empty", "zeros"])
def test_startup_in_something_that_is_not_the_game(lib, image, tmp_path, monkeypatch):
    flags, off, log = init(lib, image, tmp_path, monkeypatch)
    assert flags == 0 and off == UNREAD
    assert "게임 상태를 읽을 수 없습니다" in log and "맞지 않은 서명" not in log     # 스물한 줄을 쏟아 내지 않는다
```

- [ ] **Step 3: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -4`
Expected: 모두 ERROR — 고정물에서 `AttributeError: function 'srtoybox_values_read' not found`.

- [ ] **Step 4: `game.h` 를 다시 쓴다**

`native/srtoybox/game.h` 전체:

```cpp
// 찾은 주소(locate.h)로 게임의 상태와 값을 읽고, 플레이어의 국고와 물자 재고를 고친다.
// 게임의 메모리에 쓰는 곳은 그 둘뿐이다: 플레이어 지역 객체의 국고 1칸과 재고 STOCK_SLOTS 칸.
// 다른 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다. 내장 치트를 거치지 않는다.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "locate.h"

struct GameState {
    bool known = false;         // 주소를 찾았고(새 찾기 — 서명), 읽은 값이 서로 맞는다. 거짓이면 내장 치트로 도는 기능은 글쇠 방식으로 동작한다
    bool in_game = false;       // 게임을 진행 중이다
    bool multiplayer = false;
    bool cheats_on = false;     // 치트 허용 비트. 옛 찾기가 옵션 묶음을 찾았을 때만 읽는다(못 찾았으면 늘 false)
    int player = 0;             // 플레이어 지역의 번호(in_game 일 때만)
};

// 플레이어의 값(locate_values 가 찾은 자리에서 읽는다).
struct GameValues {
    bool ok = false;                 // 읽었다: 게임을 진행 중이고 재고 열두 칸이 모두 유한한 수다
    double treasury = 0;             // 국고(달러). 유한한 수가 아닐 수 있다 — 쓰는 쪽(values.h)이 거른다
    bool used[STOCK_SLOTS] = {};     // 이번 판에서 쓰는 물자인가
    float stock[STOCK_SLOTS] = {};   // 재고
};

enum class Wrote {
    Done,        // 썼고, 다시 읽어 그 값인 것을 봤다
    NotInGame,   // 게임을 진행 중이 아니다(멀티플레이, 읽은 값이 서로 맞지 않는 것 포함)
    NotUsed,     // 이번 판에서 쓰지 않는 물자의 칸이다
    BadValue,    // 쓸 값이 유한한 수가 아니다, 재고가 음수다, 없는 칸이다
    Failed,      // 쓸 수 없는 자리이거나 쓴 값이 남지 않았다
    Off,         // 값 쓰기가 꺼져 있다(game_values_off)
};

// base: 실행 파일이 올라온 주소(테스트에서는 가짜 메모리). 읽을 수 없는 주소를 만나도 죽지 않는다.
GameState read_game(const uint8_t *base, const GameAddresses &at);
// 이번 게임에 실제로 있는 나라(사람이나 AI 가 맡은 지역)의 번호들(오름차순). 진행 중이 아니면 빈 목록.
std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at);
GameValues read_values(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout);
// 쓰기 직전에 다시 확인한다: 게임을 진행 중이다(일관성 포함) · 멀티플레이가 아니다 · (재고) 그 칸이 쓰는 물자다 ·
// 쓸 값이 유한한 수다 · 쓸 자리가 읽기 · 쓰기 쪽이다. 쓴 뒤 다시 읽어 그 값인지 본다(아니면 한 번 더).
Wrote write_treasury(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, double value);
Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value);

void game_init();                  // 올라와 있는 실행 파일에서 주소와 자리를 찾는다(시작할 때 한 번). 결과를 로그에 적는다
void game_init_from(const uint8_t *base, size_t size);   // 그 일의 몸통(테스트는 가짜 이미지로 부른다)
GameState game_state();            // 지금의 상태. 부를 때마다 읽는다 — 플레이어는 게임 중에 바뀔 수 있다(cheat becomeregion)
std::vector<int> game_regions();
bool game_reads();                 // 상태 묶음을 찾았다(게임을 읽는다)
bool game_can_call();              // 명령 처리 함수의 주소를 안다
// 명령 처리 함수에 한 줄을 넘긴다 — 게임이 설정 창의 입력줄에서 하는 것과 같은 호출이다.
// 창 스레드에서, 게임이 진행 중일 때만 부른다(함수는 그것을 검사하지 않고 플레이어 포인터를 그대로 따라간다).
// 함수 안에서 예외가 나면 잡고 false 를 돌려준다(code 에 예외 코드). 그 뒤로 게임의 상태는 믿을 수 없다.
bool game_call(const char *line, unsigned long *code);

std::string game_values_off();     // 값을 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글
GameValues game_values();          // 지금의 값. 부를 때마다 읽는다
// 쓰기가 실패하면(Wrote::Failed) 이번 실행에서는 값 쓰기를 끄고 로그에 적는다 — 그 뒤로는 Wrote::Off 다.
Wrote game_write_treasury(double value);
Wrote game_write_stock(int slot, float value);

// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
// 값의 자리는 비워 두고 값 쓰기의 실패 표시도 지운다 — 자리는 game_set_values_for_test 로 따로 준다.
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);
void game_set_values_for_test(const ValueLayout *layout);
```

- [ ] **Step 5: `game.cpp` 를 다시 쓴다**

`native/srtoybox/game.cpp` 전체:

```cpp
#include "game.h"

#include <windows.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>

#include "features.h"
#include "log.h"

namespace {

const int MAX_REGIONS = 1024;   // 지역 표의 칸 수
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)

std::mutex g_lock;
const uint8_t *g_base;
GameAddresses g_at;
bool g_located, g_told;
void *g_handler;          // 명령 처리 함수
void *g_context;          // 그 첫 인자(게임이 넘기는 것과 같은 전역 객체)
ValueLayout g_layout;     // 값의 자리
bool g_values;            // 그것을 찾았다
char g_values_why[200];   // 못 찾은 까닭
bool g_write_failed;      // 값 쓰기가 실패했다 — 이번 실행에서는 더 쓰지 않는다

typedef void (*Handler)(void *context, const char *line);

bool env_is_zero(const char *name)
{
    char value[8];
    return GetEnvironmentVariableA(name, value, sizeof(value)) == 1 && value[0] == '0';
}

// 탈출구: SRTOYBOX_READ=0 이면 게임을 읽지 않는다 — 1단계처럼 단추가 늘 켜져 있고 글쇠 방식으로 동작한다.
// ToyBox 가 게임 안인데도 "게임 밖"으로 잘못 알아(다른 빌드, 보지 못한 화면) 단추가 꺼진 채 풀리지 않을 때 쓴다.
bool reading_wanted()
{
    static const bool wanted = !env_is_zero("SRTOYBOX_READ");
    return wanted;
}

// 탈출구: SRTOYBOX_WRITE=0 이면 게임의 메모리에 쓰지 않는다(자리는 찾아 로그에 적는다).
bool write_wanted()
{
    static const bool wanted = !env_is_zero("SRTOYBOX_WRITE");
    return wanted;
}

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

// 객체(주소)에서 offset 만큼 떨어진 값 하나.
template <class T>
bool peek_in(uint64_t object, uint64_t offset, T *out)
{
    return peek(reinterpret_cast<const void *>(object + offset), out, sizeof(T));
}

// 읽기 · 쓰기 쪽(PAGE_READWRITE)에 통째로 든 자리인가. WriteProcessMemory 는 실행 쪽(PAGE_EXECUTE_READ)이면 보호를 풀고
// 쓴다 — 낡은 포인터가 코드를 가리켜도 쓰지 않게 먼저 가린다.
bool writable(uint64_t address, size_t size)
{
    MEMORY_BASIC_INFORMATION info;
    if (VirtualQuery(reinterpret_cast<const void *>(address), &info, sizeof(info)) == 0)
        return false;
    const uint64_t end = reinterpret_cast<uint64_t>(info.BaseAddress) + info.RegionSize;
    return info.State == MEM_COMMIT && info.Protect == PAGE_READWRITE && address + size <= end;
}

// 안전한 쓰기: 쓰고, 다시 읽어 그 값인지 본다. 게임이 그 사이에 같은 칸을 고쳤을 수 있으므로 한 번 더 해 본다.
bool poke(uint64_t address, const void *data, size_t size)
{
    uint8_t back[8] = {};
    void *const where = reinterpret_cast<void *>(address);
    if (size > sizeof(back))
        return false;
    for (int attempt = 0; attempt < 2; attempt++) {
        SIZE_T done = 0;
        if (!writable(address, size) || !WriteProcessMemory(GetCurrentProcess(), where, data, size, &done) || done != size)
            return false;
        if (peek(where, back, size) && memcmp(back, data, size) == 0)
            return true;
    }
    return false;
}

// 지역 객체의 머리: +0 상태(dword), +4 자기 인덱스(word), +8 지역 번호(word).
// 상태는 2030 - 세계에서 읽은 분포로 본 것이다 [확인: 실행 / 뜻은 추정]: 0 쓸 수 없다, 1 유엔, 2 사람이 고른 나라,
// 3 AI 가 맡은 나라(223개), 5 이번 판에 없는 지역(서독 · 소련 · 네브래스카 등 128개).
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

// 이번 판에 실제로 있는 나라인가(사람이나 AI 가 맡고 있다). 창의 나라 목록에는 이것만 올린다 —
// 없는 지역에 "이 나라로 플레이" 같은 치트를 넣게 두지 않는다.
bool in_play(const Region &r)
{
    return r.alive == 2 || r.alive == 3;
}

// 게임의 상태와, 진행 중이면 플레이어 지역 객체의 주소(object).
GameState read_player(const uint8_t *base, const GameAddresses &at, uint64_t *object)
{
    GameState s;
    uint8_t multiplayer = 0;
    uint32_t options = 0;
    int32_t program = 0, mode = 0, index = 0, count = 0;
    uint64_t pointer = 0, slot = 0;
    if (base == nullptr || !peek_at(base, at.multiplayer, &multiplayer)
        || (at.options != 0 && !peek_at(base, at.options, &options))
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
    *object = pointer;
    return s;
}

// 이 물자를 이번 판에서 쓰는가: 세계 자료 객체의 그 칸(float)이 0 보다 크다. 읽을 수 없으면 false.
bool slot_used(const uint8_t *base, const ValueLayout &layout, int slot)
{
    uint64_t world = 0;
    float used = 0;
    return peek_at(base, layout.world_pointer, &world) && world != 0
        && peek_in(world, layout.used_first + static_cast<uint64_t>(layout.used_step) * static_cast<uint64_t>(slot), &used)
        && std::isfinite(used) && used > 0.0f;
}

bool located(const uint8_t **base, GameAddresses *at)
{
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    return g_located && reading_wanted();
}

// 맞지 않은 서명을 로그에 적는다 — 셋 가운데 둘로 찾았어도, 다음 업데이트에서 깨질 것을 미리 안다.
void log_unmatched(const SigRow *rows, int n)
{
    for (int i = 0; i < n; i++)
        if (rows[i].count != 1)
            log_line("맞지 않은 서명: %s #%d (%s)", rows[i].name, i % STATE_SIGS + 1, rows[i].count == 0 ? "안 맞음" : "여러 번 맞음");
}

// 프로세스의 게임에 값 하나를 쓴다. slot 이 음수면 국고.
Wrote write(int slot, double value)
{
    if (!game_values_off().empty())
        return Wrote::Off;
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ValueLayout layout = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        base = g_base;
        at = g_at;
        layout = g_layout;
    }
    const Wrote wrote = slot < 0 ? write_treasury(base, at, layout, value) : write_stock(base, at, layout, slot, static_cast<float>(value));
    if (wrote == Wrote::Failed) {
        {
            std::lock_guard<std::mutex> lock(g_lock);
            g_write_failed = true;
        }
        if (slot < 0)
            log_line("값 쓰기 실패 (국고) — 값 쓰기를 끕니다");
        else
            log_line("값 쓰기 실패 (재고 칸 %d) — 값 쓰기를 끕니다", slot);
    }
    return wrote;
}

}  // namespace

GameState read_game(const uint8_t *base, const GameAddresses &at)
{
    uint64_t object = 0;
    return read_player(base, at, &object);
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
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i) && in_play(r))
            out.push_back(r.number);
    }
    std::sort(out.begin(), out.end());
    return out;
}

GameValues read_values(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout)
{
    GameValues v;
    uint64_t object = 0;
    if (!read_player(base, at, &object).in_game || !peek_in(object, layout.treasury, &v.treasury))
        return v;
    for (int i = 0; i < STOCK_SLOTS; i++) {
        const uint64_t slot = layout.stock_first + static_cast<uint64_t>(layout.stock_step) * static_cast<uint64_t>(i);
        if (!peek_in(object, slot, &v.stock[i]) || !std::isfinite(v.stock[i]))
            return v;   // 재고 칸이 수가 아니면 구조가 바뀐 것일 수 있다 — 모르는 것으로 친다(쓰지 않는 물자의 칸이어도)
    }
    uint64_t world = 0;
    float probe = 0;
    if (!peek_at(base, layout.world_pointer, &world) || world == 0 || !peek_in(world, layout.used_first, &probe))
        return v;       // 세계 자료를 읽을 수 없다 — 어느 물자를 쓰는지 모른다
    for (int i = 0; i < STOCK_SLOTS; i++)
        v.used[i] = slot_used(base, layout, i);
    v.ok = true;
    return v;
}

Wrote write_treasury(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, double value)
{
    uint64_t object = 0;
    if (!std::isfinite(value))
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    return poke(object + layout.treasury, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value)
{
    uint64_t object = 0;
    if (slot < 0 || slot >= STOCK_SLOTS || !std::isfinite(value) || value < 0.0f)
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    if (!slot_used(base, layout, slot))
        return Wrote::NotUsed;
    const uint64_t where = object + layout.stock_first + static_cast<uint64_t>(layout.stock_step) * static_cast<uint64_t>(slot);
    return poke(where, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

void game_init()
{
    if (!reading_wanted()) {
        log_line("게임 상태를 읽지 않습니다 (SRTOYBOX_READ=0) — 글쇠 방식");
        return;
    }
    const uint8_t *base = reinterpret_cast<const uint8_t *>(GetModuleHandleW(nullptr));
    const IMAGE_DOS_HEADER *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    const IMAGE_NT_HEADERS64 *nt = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    game_init_from(base, nt->OptionalHeader.SizeOfImage);
}

void game_init_from(const uint8_t *base, size_t size)
{
    // 새 찾기: 게임 상태를 읽는 전역 일곱 — 내장 치트와 무관한 서명으로
    GameAddresses at = {};
    SigRow rows[STATE_WANTED * STATE_SIGS];
    char why[160] = "";
    const ULONGLONG started = GetTickCount64();
    const bool state = locate_state(base, size, &at, rows, why, sizeof(why));
    int matched = 0;
    for (const SigRow &row : rows)
        matched += row.count == 1 ? 1 : 0;

    // 새 찾기: 값을 읽고 쓰는 자리 — 같은 규칙의 서명으로. 상태를 읽지 못하면 값도 쓰지 않으므로 찾지 않는다
    ValueLayout layout = {};
    SigRow value_rows[VALUE_WANTED * STATE_SIGS];
    char value_why[160] = "";
    const bool values = state && locate_values(base, size, &layout, value_rows, value_why, sizeof(value_why));
    const unsigned long long took = GetTickCount64() - started;

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
        g_layout = layout;
        g_values = values;
        g_write_failed = false;
        snprintf(g_values_why, sizeof(g_values_why), "%s", value_why);
    }
    if (!state) {
        log_line("게임 상태를 읽을 수 없습니다 (%s) — 글쇠 방식", why);
        return;
    }
    log_line("게임 상태를 읽습니다 (서명 %d개 가운데 %d개, %llu ms)", STATE_WANTED * STATE_SIGS, matched, took);
    log_unmatched(rows, STATE_WANTED * STATE_SIGS);
    if (!values) {
        log_line("값을 쓸 수 없습니다 (%s)", value_why);
    } else {
        if (write_wanted())
            log_line("값을 씁니다 (국고 +0x%X, 재고 +0x%X 간격 0x%X × %d)", layout.treasury, layout.stock_first, layout.stock_step,
                     STOCK_SLOTS);
        else
            log_line("값을 쓰지 않습니다 (SRTOYBOX_WRITE=0. 국고 +0x%X, 재고 +0x%X 간격 0x%X × %d)", layout.treasury,
                     layout.stock_first, layout.stock_step, STOCK_SLOTS);
        log_unmatched(value_rows, VALUE_WANTED * STATE_SIGS);
    }
    if (can_call)
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", FEATURE_COUNT, at.handler);
    else
        log_line("명령 처리 함수를 찾지 못했습니다 (%s) — 내장 치트로 도는 기능은 글쇠 방식", legacy);
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

bool game_reads()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && reading_wanted();
}

void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_base = base;
    g_at = at != nullptr ? *at : GameAddresses();
    g_located = base != nullptr && at != nullptr;
    g_told = false;
    g_handler = g_located ? handler : nullptr;
    g_context = g_located ? const_cast<uint8_t *>(base) + g_at.context : nullptr;
    g_layout = ValueLayout();
    g_values = false;
    g_write_failed = false;
    snprintf(g_values_why, sizeof(g_values_why), "값의 자리를 주지 않았습니다");
}

void game_set_values_for_test(const ValueLayout *layout)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_layout = layout != nullptr ? *layout : ValueLayout();
    g_values = layout != nullptr;
    g_write_failed = false;
}

bool game_can_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && g_handler != nullptr && reading_wanted();
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

std::string game_values_off()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (!g_located || !reading_wanted())
        return "게임 상태를 읽을 수 있을 때만 씁니다.";
    if (!g_values)
        return std::string("이 게임 판에서는 쓸 수 없습니다 (") + g_values_why + ")";
    if (!write_wanted())
        return "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)";
    if (g_write_failed)
        return "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.";
    return std::string();
}

GameValues game_values()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ValueLayout layout = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !g_values || !reading_wanted())
            return GameValues();
        base = g_base;
        at = g_at;
        layout = g_layout;
    }
    return read_values(base, at, layout);
}

Wrote game_write_treasury(double value)
{
    return write(-1, value);
}

Wrote game_write_stock(int slot, float value)
{
    return slot < 0 ? Wrote::BadValue : write(slot, value);
}
```

- [ ] **Step 6: 내보내기를 더한다**

`native/srtoybox/exports.cpp` 의 `srtoybox_test_game` 다음에 더한다:

```cpp
// 테스트: 가짜 메모리에서 값을 읽는다. "ok=1 treasury=14430000000 used=100100010000 stock=1000,0,0,2500,…"
EXPORT int srtoybox_values_read(const unsigned char *base, const GameAddresses *at, const ValueLayout *layout, char *out, int size)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    const GameValues v = read_values(base, *at, *layout);
    char number[40];
    snprintf(number, sizeof(number), "%.17g", v.treasury);
    std::string used, stock;
    for (int i = 0; i < STOCK_SLOTS; i++) {
        used += v.used[i] ? '1' : '0';
        char one[32];
        snprintf(one, sizeof(one), "%s%.9g", i == 0 ? "" : ",", static_cast<double>(v.stock[i]));
        stock += one;
    }
    return put("ok=" + std::to_string(v.ok) + " treasury=" + number + " used=" + used + " stock=" + stock, out, size);
}

// 테스트: 가짜 메모리에 쓴다. slot 이 -1 이면 국고, 아니면 그 칸의 재고. 돌려주는 값은 Wrote
// (0 썼다, 1 게임 밖, 2 쓰지 않는 물자, 3 쓸 수 없는 값이나 칸, 4 실패).
EXPORT int srtoybox_values_write(const unsigned char *base, const GameAddresses *at, const ValueLayout *layout, int slot, double value)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    return static_cast<int>(slot == -1 ? write_treasury(base, *at, *layout, value)
                                       : write_stock(base, *at, *layout, slot, static_cast<float>(value)));
}

// 테스트: 이 프로세스의 "게임"에 값의 자리를 준다(srtoybox_test_game 다음에 부른다). nullptr 이면 못 찾은 것으로.
EXPORT void srtoybox_test_values(const ValueLayout *layout)
{
    game_set_values_for_test(layout);
}

// 테스트: 게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다. 이미지는 srtoybox_test_game(nullptr, …) 로 비울 때까지 살아 있어야 한다.
EXPORT void srtoybox_test_init(const unsigned char *image, unsigned long long size)
{
    game_init_from(image, static_cast<size_t>(size));
}

// 테스트: 이 프로세스의 "게임"에 대해 아는 것. 비트 1 = 상태를 읽는다, 2 = 명령 처리 함수를 부를 수 있다, 4 = 값을 쓸 수 있다.
EXPORT int srtoybox_game_flags(void)
{
    return (game_reads() ? 1 : 0) | (game_can_call() ? 2 : 0) | (game_values_off().empty() ? 4 : 0);
}

EXPORT int srtoybox_values_off(char *out, int size)
{
    return put(game_values_off(), out, size);
}
```

- [ ] **Step 7: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_values.py tests/test_toybox_game.py -q 2>&1 | tail -4`
Expected: `103 passed` (값 8 + 19, 게임 76).

- [ ] **Step 8: 전체 테스트를 돌리고 커밋한다**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `288 passed` (261 + 8 + 19).

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/exports.cpp tests/toybox_fake_game.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox — 플레이어의 국고와 물자 재고를 읽고 쓴다(내장 치트를 거치지 않는다)

- 쓰는 곳은 플레이어 지역 객체의 국고 1칸과 재고 12칸뿐. 쓰기 직전에 게임 상태 · 쓰는 물자 · 값 · 쪽의 보호를 다시 본다
- 쓴 뒤 다시 읽는다(다르면 한 번 더). 실패하면 이번 실행에서 값 쓰기를 끈다. SRTOYBOX_WRITE=0 은 탈출구
- game_init 의 몸통을 game_init_from 으로 떼어 갈래마다 테스트한다. 맞지 않은 서명의 이름을 로그에 적는다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 5: 값 쓰기 요청의 대기열 (`keeper`)

**브랜치:** `feat/toybox-values-write`

**Files:**
- Create: `native/srtoybox/keeper.h`, `native/srtoybox/keeper.cpp`
- Modify: `native/srtoybox/runner_win.h`, `native/srtoybox/runner_win.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py` (`SOURCES`)
- Test: `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: Task 3 의 `Change` · `treasury_value` · `stock_value` · `short_number`, Task 4 의 `game_state` · `game_values` · `game_write_treasury` · `game_write_stock` · `game_values_off`, `runner_faulted`.
- Produces (`keeper.h`):
  - `const int TREASURY = -1;` `struct Request { int slot; Change change; double amount; };`
  - `bool keeper_enqueue(const Request &request);` — 가득 찼거나(32개) 값 쓰기가 꺼져 있으면 `false`
  - `void keeper_tick();` — 게임 창을 가진 스레드에서. 대기열을 비운다
  - `std::string keeper_last();` — `국고 14.43 B -> 24.43 B`. 없으면 빈 글
  - `std::string keeper_notice();` — 쓰지 못한 까닭. 없으면 빈 글
  - `void keeper_reset_for_test();`
- Produces (`runner_win.h`): `bool runner_calling();` — 지금 게임의 명령 처리 함수 안이다
- Produces (내보내기): `int srtoybox_keeper_request(int slot, int change, double amount)`, `void srtoybox_keeper_tick(void)`, `int srtoybox_keeper_text(char *out, int size)`(`마지막으로 쓴 것\t알림`), `void srtoybox_keeper_reset(void)`.

알림의 글(창과 테스트가 그대로 쓴다):

| 상황 | `keeper_notice()` |
|---|---|
| 게임 밖 · 멀티플레이에서 대기열에 남은 요청을 버렸다 / 쓰는 사이에 게임에서 나갔다 | `게임이 진행 중이 아니어서 쓰지 않았습니다.` |
| 지금 값이 수가 아니다 | `지금 값이 수가 아니어서 쓰지 않았습니다.` |
| 게임의 값을 읽지 못했다 | `게임의 값을 읽을 수 없어 쓰지 않았습니다.` |
| 쓰지 않는 물자의 칸 | `이번 판에서 쓰지 않는 물자입니다.` |

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_toybox_values.py`:

고정물 `lib` 의 `return lib` 앞에 더한다:

```python
    lib.srtoybox_keeper_request.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
    lib.srtoybox_keeper_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
```

상수 줄들 다음에 더한다:

```python
LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다."
```

파일 끝에 덧붙인다:

```python


@pytest.fixture
def game(lib, tmp_path, monkeypatch):
    """이 프로세스의 "게임"을 독일로 진행 중인 가짜 게임으로 바꾼다. 로그는 tmp_path 에 남는다."""
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    fake = germany()
    lib.srtoybox_test_game(fake.base, ctypes.byref(fake.at), None)
    lib.srtoybox_test_values(ctypes.byref(fake.layout))
    lib.srtoybox_keeper_reset()
    yield fake
    lib.srtoybox_keeper_reset()
    lib.srtoybox_test_game(None, None, None)


def ask(lib, slot: int, change: int, amount: float) -> bool:
    return lib.srtoybox_keeper_request(slot, change, amount) == 1


def told(lib) -> tuple[str, str]:
    """(마지막으로 쓴 것, 알림)."""
    last, notice = text(lib.srtoybox_keeper_text).split("\t")
    return last, notice


def test_requests_are_written_in_order_on_the_next_tick(lib, game, tmp_path):
    assert ask(lib, TREASURY, SET, 100.0) and ask(lib, TREASURY, ADD, 50.0) and ask(lib, TREASURY, ADD, -200.0)
    assert game.treasury(176) == 14.43e9                       # 누른 것만으로는 쓰지 않는다 — 창 스레드의 틱에서 쓴다
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == -50.0
    assert told(lib) == ("국고 150 -> -50", "")
    log = (tmp_path / "toybox.log").read_text(encoding="utf-8")
    assert [line.split(" ", 2)[2] for line in log.splitlines()] == ["값 쓰기: 국고 14.43 B -> 100", "값 쓰기: 국고 100 -> 150",
                                                                    "값 쓰기: 국고 150 -> -50"]
    assert game.treasury(141) == 5e9 and game.peek(OPTIONS, "<I") == 0     # 다른 나라와 치트 허용 비트는 그대로다


def test_stock_requests_reach_only_products_in_use(lib, game):
    assert ask(lib, 3, ADD, 1e6) and ask(lib, 0, ADD, -1e8) and ask(lib, 5, ADD, 1e6)
    lib.srtoybox_keeper_tick()
    assert game.stock(176, 3) == 1002500.0 and game.stock(176, 0) == 0.0    # 0 아래로 내려가지 않는다
    assert game.stock(176, 5) == 0.0                                        # 쓰지 않는 물자의 칸에는 쓰지 않는다
    assert told(lib) == ("재고 칸 0 1.00 K -> 0", "이번 판에서 쓰지 않는 물자입니다.")


def test_requests_are_dropped_outside_a_game(lib, game):
    """누른 뒤 쓰기 전에 게임에서 나가거나 멀티플레이가 되면 쓰지 않고 버린다. 돌아오면 다시 된다."""
    assert ask(lib, TREASURY, ADD, 1e9)
    game.menu()
    lib.srtoybox_keeper_tick()
    game.play(176)
    lib.srtoybox_keeper_tick()                                 # 버린 요청이 돌아온 뒤에 쓰이지 않는다
    assert game.treasury(176) == 14.43e9 and told(lib) == ("", LEFT_GAME)
    assert ask(lib, TREASURY, ADD, 1e9)
    game.poke(MULTIPLAYER, "<B", 1)
    lib.srtoybox_keeper_tick()
    game.poke(MULTIPLAYER, "<B", 0)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 14.43e9
    assert ask(lib, TREASURY, ADD, 1e9)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 15.43e9 and told(lib) == ("국고 14.43 B -> 15.43 B", "")     # 알림은 다음에 쓸 때 지워진다


def test_a_value_that_is_not_a_number_is_left_alone(lib, game):
    game.set_treasury(176, float("nan"))
    assert ask(lib, TREASURY, SET, 5.0)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) != game.treasury(176)            # 아직 NaN 이다
    assert told(lib) == ("", "지금 값이 수가 아니어서 쓰지 않았습니다.")
    game.set_treasury(176, 1.0)
    game.set_stock(176, 9, float("inf"))                       # 재고 칸 하나가 수가 아니면 값을 통째로 믿지 않는다
    assert ask(lib, TREASURY, SET, 5.0)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 1.0 and told(lib) == ("", "게임의 값을 읽을 수 없어 쓰지 않았습니다.")


def test_the_queue_takes_thirty_two(lib, game):
    assert all(ask(lib, TREASURY, ADD, 1.0) for _ in range(32))
    assert not ask(lib, TREASURY, ADD, 1.0)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 14.43e9 + 32
    assert ask(lib, TREASURY, ADD, 1.0)


def test_a_failed_write_turns_value_writing_off_for_this_run(lib, game, tmp_path):
    game.lock(176)                                             # 플레이어 객체가 읽기 전용 쪽에 있다
    game.play(176)
    assert ask(lib, TREASURY, ADD, 1e9) and ask(lib, TREASURY, ADD, 1e9)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 14.43e9
    assert text(lib.srtoybox_values_off) == FAILED_OFF
    assert not ask(lib, TREASURY, ADD, 1e9)                    # 그 뒤로는 받지 않는다
    log = (tmp_path / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (국고) — 값 쓰기를 끕니다") == 1 and "값 쓰기: " not in log


def test_nothing_is_asked_when_values_cannot_be_written(lib, game):
    lib.srtoybox_test_values(None)                             # 값의 자리를 찾지 못한 게임
    assert not ask(lib, TREASURY, ADD, 1e9)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 14.43e9
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -4`
Expected: 모두 ERROR — 고정물에서 `AttributeError: function 'srtoybox_keeper_request' not found`.

- [ ] **Step 3: `runner_calling` 을 더한다**

`native/srtoybox/runner_win.h` 의 `bool runner_faulted();` 줄 다음에:

```cpp
bool runner_calling();                             // 지금 게임의 명령 처리 함수 안이다 — 그동안 ToyBox 는 게임의 메모리에 쓰지 않는다
```

`native/srtoybox/runner_win.cpp` 의 `runner_faulted` 다음에:

```cpp
bool runner_calling()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_calling;
}
```

- [ ] **Step 4: `keeper` 를 만든다**

`native/srtoybox/keeper.h`:

```cpp
// 값 쓰기 요청의 대기열. 창의 단추(그리는 스레드)가 넣고, 게임 창의 타이머(창 스레드)가 비운다.
// 내장 치트를 거치지 않는다 — 지금 값을 읽고(game.h) 쓸 값을 셈해(values.h) 그 칸에 쓴다.
#pragma once

#include <string>

#include "values.h"

const int TREASURY = -1;                       // Request.slot: 국고. 0 … STOCK_SLOTS - 1 은 그 칸의 물자 재고

struct Request {
    int slot;
    Change change;
    double amount;                             // 국고는 달러, 재고는 수량
};

bool keeper_enqueue(const Request &request);   // 받지 못하면 false: 가득 찼다(32개), 값 쓰기가 꺼져 있다
// 대기열을 비운다. 게임 창을 가진 스레드에서 부른다. 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고,
// 게임의 명령 처리 함수(옮기지 않은 기능의 직접 실행) 안에서 다시 온 틱이면 아무것도 하지 않는다.
void keeper_tick();
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B". 없으면 빈 글
std::string keeper_notice();                   // 쓰지 못한 까닭(창에 보인다). 없으면 빈 글
void keeper_reset_for_test();
```

`native/srtoybox/keeper.cpp`:

```cpp
#include "keeper.h"

#include <deque>
#include <mutex>

#include "game.h"
#include "log.h"
#include "runner_win.h"

namespace {

const size_t MAX_QUEUE = 32;
const char *const LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다.";

std::mutex g_lock;          // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
std::deque<Request> g_queue;
std::string g_last, g_notice;

std::string target_name(int slot)
{
    return slot == TREASURY ? std::string("국고") : "재고 칸 " + std::to_string(slot);
}

// 요청 하나를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now)
{
    double from = 0, to = 0;
    Verdict verdict = Verdict::Refuse;
    if (r.slot == TREASURY) {
        from = now.treasury;
        verdict = treasury_value(now.treasury, r.change, r.amount, &to);
    } else {
        if (r.slot < 0 || r.slot >= STOCK_SLOTS || !now.used[r.slot]) {
            g_notice = "이번 판에서 쓰지 않는 물자입니다.";
            return true;
        }
        float next = 0;
        from = now.stock[r.slot];
        verdict = stock_value(now.stock[r.slot], r.change, r.amount, &next);
        to = next;
    }
    if (verdict == Verdict::Refuse)
        g_notice = "지금 값이 수가 아니어서 쓰지 않았습니다.";
    if (verdict != Verdict::Write)
        return true;
    const Wrote wrote = r.slot == TREASURY ? game_write_treasury(to) : game_write_stock(r.slot, static_cast<float>(to));
    if (wrote == Wrote::Done) {
        g_last = target_name(r.slot) + " " + short_number(from) + " -> " + short_number(to);
        log_line("값 쓰기: %s", g_last.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 탭이 보인다(game_values_off)
    g_notice = LEFT_GAME;                      // 읽은 뒤 쓰기 전에 게임이 바뀌었다
    return true;
}

}  // namespace

bool keeper_enqueue(const Request &request)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_queue.size() >= MAX_QUEUE || !game_values_off().empty())
        return false;
    g_queue.push_back(request);
    return true;
}

void keeper_tick()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_queue.empty() || runner_calling())
        return;                                // 게임의 함수 안에서 다시 온 틱이면 기다린다 — 그 함수가 읽고 있는 값을 바꾸지 않는다
    const GameState game = game_state();
    if (runner_faulted() || !game_values_off().empty()) {
        g_queue.clear();                       // 까닭은 창이 보인다(빨간 경고, 탭의 한 줄)
        return;
    }
    if (!game.known || !game.in_game || game.multiplayer) {
        g_queue.clear();                       // 누른 뒤 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다
        g_notice = LEFT_GAME;
        return;
    }
    g_notice.clear();
    while (!g_queue.empty()) {
        const Request r = g_queue.front();
        g_queue.pop_front();
        const GameValues now = game_values();  // 요청마다 다시 읽는다 — 앞의 요청이 값을 바꿨다
        if (!now.ok) {
            g_queue.clear();
            g_notice = "게임의 값을 읽을 수 없어 쓰지 않았습니다.";
            return;
        }
        if (!apply(r, now)) {
            g_queue.clear();
            return;
        }
    }
}

std::string keeper_last()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_last;
}

std::string keeper_notice()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_notice;
}

void keeper_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_queue.clear();
    g_last.clear();
    g_notice.clear();
}
```

`native/srtoybox/exports.cpp` — include 에 `#include "keeper.h"` 를 더하고(`#include "input.h"` 다음), `srtoybox_values_off` 다음에 더한다:

```cpp
// 테스트: 값 쓰기 요청(keeper.h). slot 이 -1 이면 국고. change: 0 더하기, 1 이 값으로, 2 바닥. 받았으면 1.
EXPORT int srtoybox_keeper_request(int slot, int change, double amount)
{
    if (change < 0 || change > 2)
        return -1;
    return keeper_enqueue({slot, static_cast<Change>(change), amount}) ? 1 : 0;
}

EXPORT void srtoybox_keeper_tick(void)
{
    keeper_tick();
}

// 테스트: "<마지막으로 쓴 것>\t<알림>".
EXPORT int srtoybox_keeper_text(char *out, int size)
{
    return put(keeper_last() + '\t' + keeper_notice(), out, size);
}

EXPORT void srtoybox_keeper_reset(void)
{
    keeper_reset_for_test();
}
```

`src/srkit/toybox.py` 의 `SOURCES` 에서 `"game.cpp", "regions.cpp",` 를 `"game.cpp", "keeper.cpp", "regions.cpp",` 로 바꾼다.

- [ ] **Step 5: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -3`
Expected: `34 passed` (27 + 7).

- [ ] **Step 6: 전체 테스트를 돌리고 커밋한다**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `295 passed` (288 + 7).

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/keeper.h native/srtoybox/keeper.cpp native/srtoybox/runner_win.h native/srtoybox/runner_win.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox — 값 쓰기 요청의 대기열(keeper)

단추가 넣고 게임 창의 타이머가 비운다. 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 요청을 버리고,
게임의 명령 처리 함수 안에서 다시 온 틱에는 쓰지 않는다. 아직 타이머에 물리지 않았다(다음 커밋).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 6: 돈 탭 — 국고를 직접 고친다, 국고의 치트 단추를 지운다

**브랜치:** `feat/toybox-values-write`

**Files:**
- Modify: `native/srtoybox/features.cpp` (세 줄 삭제), `native/srtoybox/settings.h`, `native/srtoybox/settings.cpp`, `native/srtoybox/input.cpp`, `native/srtoybox/ui.cpp`
- Modify: `tests/toybox_overlay_probe.py`
- Test: `tests/test_toybox.py`

**Interfaces:**
- Consumes: Task 5 의 `keeper_enqueue` · `keeper_tick` · `keeper_last` · `keeper_notice` · `TREASURY` · `Request`, Task 4 의 `game_values` · `game_values_off`, Task 3 의 `short_number` · `Change`, 가짜 게임의 `.layout` · `.set_treasury` · `.treasury` · `.lock`.
- Produces:
  - `Settings::money_amount`(`long long`, 기본 10000), `MONEY_AMOUNT_MIN = 1` · `MONEY_AMOUNT_MAX = 1000000`. 설정 파일의 줄 `money.amount=<백만 달러>`(단축키 두 줄 다음).
  - 기능 표 22줄(`treasury` · `georgew` · `georgeww` 가 없다). 탭 "돈"은 기능 표에 없고 `ui.cpp` 의 `money_tab` 이 그린다.
  - 창이 그린 것의 이름(테스트가 본다): `tab:돈`, `money:now`(`국고: $ 14.43 B` / 게임 밖이면 `국고: -`), `money:amount`, `money:add` · `money:sub` · `money:set`, `money:-100b` · `money:-10b` · `money:zero` · `money:+10b` · `money:+100b`, `money:off`(쓸 수 없는 까닭 — 이때는 다른 `money:` 항목이 없다), 바닥의 `wrote`(마지막으로 쓴 값) · `unwritten`(쓰지 못한 까닭).
  - 검사 도구: `Game.open()`, `CHEAT_TAB = "tab:화면·진행"`, `BUTTON = "run:fullmapshow"`, `fake_game(hook, handler=None, values=True)`, 새 mode `money` · `money_menu` · `money_leave` · `money_write_off` · `money_notfound` · `money_unread` · `money_fail` · `money_reenter`.

돈 탭의 모양(설계서의 그림에서 최소 유지 줄을 뺀 것 — 유지는 계획 (다)):

```
국고: $ 14.43 B

[ 10000 ] 백만 달러   [더하기] [빼기] [이 값으로]
입력한 금액만큼 국고를 더하거나 빼거나, 국고를 그 금액으로 맞춘다

[-$100 B] [-$10 B] [$0] [+$10 B] [+$100 B]
```

- [ ] **Step 1: 검사 도구를 고친다 — 누르는 치트 단추를 바꾸고, 가짜 게임에 값을 주고, 돈 탭의 mode 를 더한다**

`tests/toybox_overlay_probe.py`:

머리말의 `설정 창에 보이는 글 …` 문단 앞에 더한다:

```python
돈 탭 — 내장 치트를 거치지 않고 국고를 고친다 (출력은 JSON 한 줄):
    money            게임 안에서 빠른 단추 다섯과 입력란(1234)의 더하기 · 빼기 · 이 값으로를 누른다
    money_menu       메뉴에 있다 — 단추가 꺼져 있다
    money_leave      단추를 누른 뒤 쓰기 전에 게임에서 나간다 — 쓰지 않고 버린다. 돌아오면 다시 된다
    money_write_off  SRTOYBOX_WRITE=0 — 까닭 한 줄만 보인다
    money_notfound   값의 자리를 찾지 못한 게임 — 〃
    money_unread     SRTOYBOX_READ=0 — 〃
    money_fail       플레이어 지역 객체가 읽기 전용 쪽에 있다 — 쓰기가 실패하고 탭이 꺼진다
    money_reenter    옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 온다 — 그 안에서는 쓰지 않는다
```

`BUTTON = …` 줄을 다음 둘로 바꾼다:

```python
CHEAT_TAB = "tab:화면·진행"   # 아직 내장 치트로 도는 단추가 있는 탭(첫 탭 "돈"은 값 쓰기 전용 화면이다)
BUTTON = "run:fullmapshow"   # 그 탭의 첫 줄 "GUI 숨기기/보이기" (cheat fullmapshow) — 묶음 6 에서 옮길 때까지 남는다
```

`class Game` 의 `hotkey` 메서드 다음에 더한다:

```python
    def open(self, lparam: int = 1) -> str:
        """단축키로 창을 열고 CHEAT_TAB 으로 간다. 단축키를 받은 쪽("toybox" / "game")을 돌려준다."""
        who = self.hotkey(lparam)
        self.click(CHEAT_TAB)
        return who
```

`fake_game` 전체를 다음으로 바꾼다:

```python
def fake_game(hook: str, handler: int | None = None, values: bool = True) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106. 국고 $5 B)와 독일(176, 1499. 국고 $14.43 B)이 있고 메뉴 상태다.

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    values 가 False 면 값의 자리를 찾지 못한 게임이다(돈 탭이 꺼진다).
    """
    toybox = ctypes.WinDLL(str(Path(hook).with_name("srtoybox.dll")))
    toybox.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    toybox.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.set_treasury(141, 5e9)
    fake.set_treasury(176, 14.43e9)
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    if values:
        toybox.srtoybox_test_values(ctypes.byref(fake.layout))
    return fake
```

단추를 누르기 전의 `game.hotkey()` 를 `game.open()` 으로 바꾼다 — 다섯 곳:

| 함수 | 지금 | 바꾼 뒤 |
|---|---|---|
| `run_gate` | `game.hotkey()` (그 다음 줄이 `button = game.click(BUTTON)`) | `game.open()` |
| `run_direct` | `game.hotkey()` (그 다음 줄이 `game.got.clear()`) | `game.open()` |
| `run_window` 의 `if mode in ("leave", "multiplayer"):` 갈래 | `game.hotkey()` | `game.open()` |
| `run_reenter` | `game.hotkey()` | `game.open()` |
| `run_input` | `out = {"hotkey": game.hotkey()}` | `out = {"hotkey": game.open()}` |

(`run_window` 의 나머지 갈래 · `run_scale` · `run_present_fault` 의 `game.hotkey()` 는 치트 단추를 누르지 않으므로 그대로 둔다.)

`run_reenter` 다음(`crash_once_stub` 앞)에 더한다:

```python
MONEY = "tab:돈"


def run_money(hook: str, mode: str) -> int:
    """돈 탭: 내장 치트를 거치지 않고 국고를 고친다. 출력은 JSON 한 줄(보이지 않는 글은 "-")."""
    home = os.environ.get("SRTOYBOX_HOME")
    if mode == "money" and home:
        Path(home, "toybox.ini").write_text("money.amount=1234\n", encoding="utf-8")   # 입력란의 값(백만 달러). ToyBox 가 뜰 때 읽는다
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    inside: list[float] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)
        elif mode == "money_reenter":                         # 게임의 함수가 일하는 도중에 ToyBox 의 타이머가 다시 온다
            inside.append(box["fake"].treasury(176))
            user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)
            inside.append(box["fake"].treasury(176))

    game.handler = HANDLER(body)                              # 게임이 살아 있는 동안 붙들어 둔다
    fake = box["fake"] = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value, values=mode != "money_notfound")
    if mode == "money_fail":
        fake.lock(176)                                        # 플레이어 지역 객체가 읽기 전용 쪽에 있다(읽을 수는 있다)
    if mode != "money_menu":
        fake.play(176)
    game.hotkey()                                             # 창이 열리면 첫 탭이 "돈"이다
    game.got.clear()
    facts = game.facts()
    out: dict[str, object] = {"now": game.shown("money:now"), "off": game.shown("money:off")}
    out["cheat_buttons"] = sorted(name for name in facts if name.startswith("run:"))
    out["buttons"] = sorted(name for name in facts
                            if name.startswith("money:") and name not in ("money:now", "money:off", "money:amount"))

    def press(name: str) -> float:
        game.click(name)
        game.wait(0.2)                                        # 쓰는 것은 다음 타이머에서다
        return fake.treasury(176)

    if mode == "money":
        out["steps"] = [press(name) for name in ("money:+10b", "money:+100b", "money:-10b", "money:-100b", "money:zero",
                                                 "money:add", "money:add", "money:sub", "money:+10b", "money:set")]
        out["amount"], out["now_after"], out["wrote"] = game.shown("money:amount"), game.shown("money:now"), game.shown("wrote")
    elif mode == "money_menu":
        out["steps"] = [press("money:+10b")]
        out["status"] = game.shown("status")
    elif mode == "money_leave":
        game.click("money:+10b")                              # 눌렀다. 쓰는 것은 다음 타이머에서다(메시지를 돌릴 때 온다)
        fake.menu()                                           # 그 전에 게임에서 나갔다
        game.wait(0.3)
        out["dropped"], out["unwritten"] = fake.treasury(176), game.shown("unwritten")
        fake.play(176)
        out["steps"] = [press("money:+10b")]                  # 돌아오면 다시 된다
        out["unwritten_after"] = game.shown("unwritten")
    elif mode == "money_fail":
        out["steps"] = [press("money:+10b")]
        out["off_after"] = game.shown("money:off")
        out["buttons_after"] = sorted(name for name in game.facts() if name.startswith("money:") and name != "money:off")
    elif mode == "money_reenter":
        game.click(CHEAT_TAB)
        game.click(BUTTON)                                    # 옮기지 않은 기능 하나(직접 실행)가 대기열에 든다
        game.click(MONEY)
        game.click("money:+10b")                              # 국고 요청도 대기열에 든다
        game.wait(0.5)
        out["inside"], out["after"] = inside, fake.treasury(176)
    out["lines"], out["text"], out["options"], out["poland"] = lines, game.text(), fake.peek(OPTIONS, "<I"), fake.treasury(141)
    print(json.dumps(out, ensure_ascii=False))
    return 0
```

`main` 의 `if mode.startswith("reenter_"):` 두 줄 다음에 더한다:

```python
    if mode.startswith("money"):
        return run_money(hook, mode)
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_toybox.py`:

`TABS` 줄을 다음으로 바꾼다:

```python
TABS = ["물자", "연구", "인구·여론", "외교·영토", "부대", "화면·진행"]     # 기능 표의 탭. "돈" 탭은 기능 표가 아니라 전용 화면이 그린다
```

`test_feature_table` 의 머리 세 줄(`fs = …` · `assert len(fs) == 25` · `assert len({f["id"] …}) == 25 …`)을 다음으로 바꾼다:

```python
    fs = features(dll)
    assert len(fs) == 22
    assert len({f["id"] for f in fs}) == 22 and len({f["command"] for f in fs}) == 22
    assert not {"treasury", "georgew", "georgeww"} & {f["id"] for f in fs}   # 국고는 내장 치트를 거치지 않는다(돈 탭)
```

같은 함수에서 `{"treasury", "products", "technology", "spawnunit"}` 을 `{"products", "technology", "spawnunit"}` 으로, 마지막 줄의 `srtoybox_feature_info(25, …)` 를 `srtoybox_feature_info(22, …)` 로 바꾼다.

`test_command_text` 의 처음 다섯 `assert`(`treasury` 넷과 `georgew` 하나)와 마지막 줄을 다음으로 바꾼다:

```python
    assert text(dll.srtoybox_command, b"technology", 140, 0) == "cheat technology 140"
    assert text(dll.srtoybox_command, b"technology", 0, 0) == "cheat technology 1"             # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"technology", -5, 0) == "cheat technology 1"
    assert text(dll.srtoybox_command, b"technology", 10**12, 0) == "cheat technology 999"
    assert text(dll.srtoybox_command, b"finalexam", 999, 1106) == "cheat finalexam"            # 값도 대상도 없는 기능은 둘 다 무시한다
```

```python
    assert text(dll.srtoybox_command, b"treasury", 1, 0) is None                               # 지운 기능 — 국고는 돈 탭이 직접 한다
    assert text(dll.srtoybox_command, b"technology", 1, 0, size=4) is None                     # 버퍼가 작으면 넘치지 않고 -1
```

(가운데의 `e=mc2` · `approval` · `love` · `treaty` · `depopulate` 줄들은 그대로 둔다.)

`DEFAULTS` 줄을 다음으로 바꾼다:

```python
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\nproducts=100000\ntechnology=120\nspawnunit=2413\n"
```

`test_settings_fall_back_to_defaults` 에서 세 줄을 바꾼다:

```python
    assert norm("money.amount=0\nproducts=999999999999\ntechnology=abc\nspawnunit=12x\n") == DEFAULTS   # 범위 밖·숫자 아님 → 기본값
    assert norm("unknown=5\ngeorgew=7\ndepopulate=1\ntreasury=500\n") == DEFAULTS            # 모르는 키, 값이 없는 기능, 지운 기능
```

```python
    assert norm(" hotkey_vk = 123 \r\nhotkey_mods=0\r\nmoney.amount= 500 \r\n") == DEFAULTS.replace("=84", "=123").replace("mods=3", "mods=0").replace("amount=10000", "amount=500")
    assert norm("money.amount=1000001\n") == DEFAULTS and norm("money.amount=1000000\n") == DEFAULTS.replace("=10000\n", "=1000000\n")
```

(첫 줄은 지금의 `norm("treasury=0\n…")` 줄을, 둘째 줄은 `norm("unknown=5\n…")` 줄을, 셋째 줄은 마지막의 `norm(" hotkey_vk = 123 …")` 줄을 대신한다. 넷째 줄은 새로 더한다.)

`_probe` 의 `subprocess.run(…)` 에서 `encoding="utf-8", env=` 를 `encoding="utf-8", errors="replace", env=` 로 바꾼다 — 검사 프로세스가 죽으며 남긴 오류 글이 UTF-8 이 아니어도(한글이 든 줄은 CP949 로 나온다) 테스트가 그 글을 보여 준다. 지금은 `TypeError: 'NoneType' object is not subscriptable` 로 가려진다.

화면 검사 도구가 누르는 치트 단추가 바뀌었으므로, 그 도구를 쓰는 테스트들의 기대값을 바꾼다:

```bash
cd /e/SR2030ToyBox && sed -i '/^def test_keys_and_clicks_reach_only/,$ s/cheat georgew/cheat fullmapshow/g' tests/test_toybox.py && grep -c "cheat fullmapshow" tests/test_toybox.py && grep -n "cheat georgew" tests/test_toybox.py
```

Expected: 첫 줄 `10`(그 글이 든 줄의 수). 남은 `cheat georgew` 는 실행기 테스트(`test_runner_keeps_the_gaps_…` · `test_runner_runs_commands_in_order`)의 네 줄뿐이다 — 실행기에 넣는 글 그대로이므로 둔다.

파일 끝의 `test_prologue_length_knows_only_plain_function_heads` 앞에 더한다:

```python
MONEY_BUTTONS = ["money:+100b", "money:+10b", "money:-100b", "money:-10b", "money:add", "money:set", "money:sub", "money:zero"]
VALUES_FAILED = "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다."


def test_the_money_tab_writes_the_treasury_without_any_cheat(dll, cfg, tmp_path):
    """요구 3: 돈 탭은 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고, 글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다.
    쓰는 곳은 플레이어의 국고뿐이다(다른 나라의 국고는 그대로다)."""
    got = json.loads(_probe(cfg, tmp_path, "money"))
    assert got["now"] == "국고: $ 14.43 B" and got["off"] == "-"
    assert got["buttons"] == MONEY_BUTTONS and got["cheat_buttons"] == []
    # +$10 B, +$100 B, -$10 B, -$100 B, $0, 더하기 × 2, 빼기, +$10 B, 이 값으로 (입력란은 1234 백만 달러)
    assert got["steps"] == [24.43e9, 124.43e9, 114.43e9, 14.43e9, 0.0, 1.234e9, 2.468e9, 1.234e9, 11.234e9, 1.234e9]
    assert got["amount"] == "1234" and got["now_after"] == "국고: $ 1.23 B" and got["wrote"] == "국고 11.23 B -> 1.23 B"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["poland"] == 5e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: 국고") == 10 and "직접 실행" not in log


def test_money_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "money_menu"))
    assert got["now"] == "국고: -" and got["buttons"] == MONEY_BUTTONS       # 단추는 보이지만 꺼져 있다
    assert got["steps"] == [14.43e9] and got["lines"] == [] and got["text"] == ""
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_money_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "money_leave"))
    assert got["dropped"] == 14.43e9 and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["steps"] == [24.43e9] and got["unwritten_after"] == "-"


@pytest.mark.parametrize("mode, env, why", [
    ("money_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)"),
    ("money_notfound", {}, "이 게임 판에서는 쓸 수 없습니다 (값의 자리를 주지 않았습니다)"),
    ("money_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다."),
], ids=["write-off", "not-found", "unread"])
def test_the_money_tab_says_why_it_is_off_and_offers_no_cheat(dll, cfg, tmp_path, mode, env, why):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 까닭 한 줄만 보이고 단추가 없다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert got["off"] == why and got["now"] == "-"
    assert got["buttons"] == [] and got["cheat_buttons"] == []
    assert got["lines"] == [] and got["text"] == ""


def test_a_failed_write_turns_the_money_tab_off_and_says_why(dll, cfg, tmp_path):
    """쓸 수 없는 곳을 만나면 죽지 않고, 이번 실행에서 값 쓰기를 끄고 까닭을 보인다."""
    got = json.loads(_probe(cfg, tmp_path, "money_fail"))
    assert got["now"] == "국고: $ 14.43 B" and got["steps"] == [14.43e9]
    assert got["off_after"] == VALUES_FAILED and got["buttons_after"] == []
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (국고) — 값 쓰기를 끕니다") == 1


def test_money_is_not_written_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 와도, 그 안에서는 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "money_reenter"))
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [14.43e9, 14.43e9]                  # 그 함수 안에서 다시 온 타이머의 앞뒤
    assert got["after"] == 24.43e9                              # 함수가 끝난 뒤에 쓴다
```

- [ ] **Step 3: 테스트가 실패하는지 본다**

Run: `uv run pytest tests/test_toybox.py -q 2>&1 | tail -25`
Expected: FAIL — `test_feature_table`(25 != 22), `test_command_text`, 설정 둘(`money.amount` 줄이 없다), 돈 탭의 여덟(검사 도구가 `money:+10b` 를 찾지 못해 죽거나 `now` 가 `-` 다). 화면 검사 도구로 치트 단추를 누르는 지금의 테스트들은 이 단계에서도 통과한다(누르는 단추만 바뀌었다).

- [ ] **Step 4: 국고의 치트 세 줄을 지운다**

`native/srtoybox/features.cpp` 에서 `{"treasury", …}` · `{"georgew", …}` · `{"georgeww", …}` 세 줄을 지우고, `const Feature FEATURES[] = {` 앞에 주석을 더한다:

```cpp
// 국고의 세 줄(treasury · georgew · georgeww)은 3단계 1 에서 지웠다 — 돈 탭이 내장 치트 없이 직접 한다(ui.cpp 의 money_tab).
// 남은 줄은 아직 내장 치트로 돈다. 묶음마다 옮기고 지운다(docs/10-toybox.md 의 "다음 단계").
```

- [ ] **Step 5: 설정에 `money.amount` 를 더한다**

`native/srtoybox/settings.h`:

머리말의 첫 줄을 `// 창에서 바꾸는 설정: 여닫는 단축키, 돈 탭의 입력란, 기능마다 마지막에 넣은 값.` 으로 바꾸고, `const int HOTKEY_CTRL …` 줄 다음에:

```cpp
const long long MONEY_AMOUNT_MIN = 1, MONEY_AMOUNT_MAX = 1000000, MONEY_AMOUNT_DEFAULT = 10000;   // 돈 탭의 입력란(백만 달러)
```

`Settings` 의 `hotkey_mods` 줄 다음에:

```cpp
    long long money_amount = MONEY_AMOUNT_DEFAULT;   // 돈 탭의 입력란. 파일의 줄은 "money.amount"
```

`native/srtoybox/settings.cpp`:

`parse_settings` 의 `} else if (key == "hotkey_mods") {` 갈래 다음에 갈래를 더한다:

```cpp
        } else if (key == "money.amount") {
            if (n >= MONEY_AMOUNT_MIN && n <= MONEY_AMOUNT_MAX)
                s.money_amount = n;
```

`format_settings` 의 첫 줄을 다음으로 바꾼다:

```cpp
    std::string out = "hotkey_vk=" + std::to_string(s.hotkey_vk) + "\nhotkey_mods=" + std::to_string(s.hotkey_mods)
        + "\nmoney.amount=" + std::to_string(s.money_amount) + "\n";
```

- [ ] **Step 6: 타이머에서 대기열을 비운다**

`native/srtoybox/input.cpp` — `#include "input.h"` 다음 묶음에 `#include "keeper.h"` 를 더하고(`#include "imgui_impl_win32.h"` 다음), 타이머 갈래를 다음으로 바꾼다:

```cpp
    if (m == WM_TIMER && w == TIMER_ID) {
        runner_tick(h);
        keeper_tick();                                       // 값 쓰기 요청(돈 탭). 게임의 함수 안에서 다시 온 틱이면 스스로 쉰다
        return 0;
    }
```

- [ ] **Step 7: 돈 탭을 그린다**

`native/srtoybox/ui.cpp`:

include 에 `#include <algorithm>`(`<cfloat>` 앞)과 `#include "keeper.h"`(`#include "imgui.h"` 다음)를 더한다.

`settings_tab` 앞에 더한다:

```cpp
// 돈 탭의 단추 하나: 누르면 국고에 대한 요청을 대기열에 넣는다. 쓰는 것은 게임 창의 타이머에서다(keeper.h).
void money_button(const char *label, const char *name, Change change, double amount)
{
    const bool pressed = ImGui::Button(label);
    note(name, label);
    if (pressed)
        g_notice = keeper_enqueue({TREASURY, change, amount}) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
}

// 돈 탭: 내장 치트를 거치지 않고 플레이어의 국고를 직접 고친다(기능 표가 아니라 여기서 그린다).
// 쓸 수 없으면 까닭 한 줄만 보인다 — 내장 치트로 되돌아가지 않는다.
void money_tab(const GameState &game, bool blocked)
{
    const std::string off = game.known ? game_values_off() : std::string("게임 상태를 읽을 수 있을 때만 씁니다.");
    if (!off.empty()) {
        ImGui::TextWrapped("%s", off.c_str());
        note("money:off", off);
        return;
    }
    const GameValues now = game.in_game ? game_values() : GameValues();   // 탭이 보이는 동안 프레임마다 읽는다
    const std::string have = now.ok ? "국고: $ " + short_number(now.treasury) : std::string("국고: -");
    ImGui::TextUnformatted(have.c_str());
    note("money:now", have);
    ImGui::Spacing();

    ImGui::BeginDisabled(blocked || !now.ok);
    ImGui::SetNextItemWidth(150.0f);
    if (ImGui::InputScalar("##amount", ImGuiDataType_S64, &g_settings.money_amount)) {
        g_settings.money_amount = std::min(MONEY_AMOUNT_MAX, std::max(MONEY_AMOUNT_MIN, g_settings.money_amount));
        save_settings(g_settings);
    }
    note("money:amount", std::to_string(g_settings.money_amount));
    const double amount = static_cast<double>(g_settings.money_amount) * 1e6;
    ImGui::SameLine();
    ImGui::TextUnformatted("백만 달러");
    ImGui::SameLine();
    money_button("더하기", "money:add", Change::Add, amount);
    ImGui::SameLine();
    money_button("빼기", "money:sub", Change::Add, -amount);
    ImGui::SameLine();
    money_button("이 값으로", "money:set", Change::Set, amount);
    ImGui::TextDisabled("입력한 금액만큼 국고를 더하거나 빼거나, 국고를 그 금액으로 맞춘다");
    ImGui::Spacing();

    money_button("-$100 B", "money:-100b", Change::Add, -100e9);
    ImGui::SameLine();
    money_button("-$10 B", "money:-10b", Change::Add, -10e9);
    ImGui::SameLine();
    money_button("$0", "money:zero", Change::Set, 0.0);
    ImGui::SameLine();
    money_button("+$10 B", "money:+10b", Change::Add, 10e9);
    ImGui::SameLine();
    money_button("+$100 B", "money:+100b", Change::Add, 100e9);
    ImGui::TextDisabled("국고는 음수가 될 수 있다. 다른 나라의 국고는 건드리지 않는다");
    ImGui::EndDisabled();
}
```

`ui_draw` 에서 `if (ImGui::BeginTabBar("tabs")) {` 다음 줄(`const char *tab = nullptr;` 앞)에 더한다:

```cpp
            const bool money = ImGui::BeginTabItem("돈");   // 첫 탭. 기능 표에 없다 — 내장 치트 없이 직접 한다
            note("tab:돈", "돈");
            if (money) {
                if (ImGui::BeginChild("body", body))
                    money_tab(game, blocked);
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
```

같은 함수의 바닥 줄들에서, `if (!g_notice.empty()) {` 앞에 더한다:

```cpp
        const std::string wrote = keeper_last();
        if (!wrote.empty()) {
            ImGui::Text("마지막으로 쓴 값: %s", wrote.c_str());
            note("wrote", wrote);
        }
        const std::string unwritten = keeper_notice();
        if (!unwritten.empty()) {
            ImGui::TextWrapped("%s", unwritten.c_str());
            note("unwritten", unwritten);
        }
```

- [ ] **Step 8: 빌드하고 테스트가 통과하는지 본다**

Run: `uv run srkit toybox-build && uv run pytest tests/test_toybox.py -q 2>&1 | tail -8`
Expected: 실패 없이 모두 통과한다(Step 2 에서 더한 여덟 포함).

화면 검사 테스트가 `tab:화면·진행 이 창에 보이지 않는다` 로 실패하면(탭이 여덟이라 좁은 창에서 가려질 수 있다 — 2026-10-09 의 화면에서는 500 폭에 여덟이 다 들어갔다): `CHEAT_TAB = "tab:부대"`, `BUTTON = "run:darran"` 으로 바꾸고 `tests/test_toybox.py` 의 `cheat fullmapshow` 를 `cheat darran` 으로 바꾼다. 그 결정을 기록한다.

- [ ] **Step 9: 전체 테스트를 돌리고 커밋한다**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `303 passed` (295 + 8).

```bash
cd /e/SR2030ToyBox && git add native/srtoybox/features.cpp native/srtoybox/settings.h native/srtoybox/settings.cpp native/srtoybox/input.cpp native/srtoybox/ui.cpp tests/toybox_overlay_probe.py tests/test_toybox.py && git commit -q -F - <<'EOF'
feat: ToyBox 돈 탭 — 국고를 내장 치트 없이 직접 고친다

- 입력란(백만 달러) + 더하기 · 빼기 · 이 값으로, 빠른 단추 -$100 B · -$10 B · $0 · +$10 B · +$100 B
- 국고의 치트 단추 셋(treasury · georgew · georgeww)을 지운다. 기능 표 25 → 22줄
- 쓸 수 없으면 까닭 한 줄만 보인다(내장 치트로 되돌아가지 않는다). 설정 money.amount
- 화면 검사 도구가 누르는 치트 단추를 "GUI 숨기기/보이기"(cheat fullmapshow)로 바꾼다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

---

### Task 7: 게임 안 확인 — 직접 쓴 국고를 게임이 그대로 쓰는가 (V1 ~ V4 · V12 · V14 의 일부)

**브랜치:** `feat/toybox-values-write` (게임이 떠 있는 동안 바꾸지 않는다)

**Files:**
- Modify: `scripts/gamedrive.py` (`peek` 명령)
- 근거 화면과 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.

**Interfaces:**
- Consumes: Task 2 의 `toybox.locate(cfg)`(`.state` · `.values` · `.legacy`) · `toybox.STOCK_SLOTS`, Task 6 의 빌드와 로그의 줄.
- Produces: `uv run python scripts/gamedrive.py peek` — 이 도구가 띄운 게임의 메모리에서 읽은 것을 JSON 한 줄로: `program` · `mode` · `multiplayer` · `player_index` · `in_game` · (게임 안이면) `player` · `treasury` · `stock`(12칸) · `used`(12칸) · (옛 찾기가 됐으면) `cheats_allowed`. 그리고 이 Task 의 결과(Task 8 이 `docs/10` 에 적는다).

- [ ] **Step 1: `gamedrive.py peek` 을 더한다**

`scripts/gamedrive.py`:

머리말의 명령 목록에서 `stop` 줄 앞에 한 줄을 더한다:

```python
    uv run python scripts/gamedrive.py peek                   # 이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다(읽기만, JSON)
```

`kernel32.GetProcessTimes.argtypes = …` 줄 다음에:

```python
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
```

`need_window` 다음에 더한다:

```python
def peek_game(cfg: config.Config) -> dict:
    """이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 것을 읽는다(읽기만). 주소는 srkit locate 와 같은 방법(서명)으로 찾는다.

    ToyBox 의 창에 보이는 값이 아니라 게임의 메모리 그 자체다 — ToyBox 가 쓴 값과 치트 허용 비트를 따로 확인하는 데 쓴다.
    """
    import struct

    from srkit import toybox

    mine = owned_pids(cfg)
    if not mine:
        raise SystemExit(not_ours() if game_pids() else "게임이 떠 있지 않습니다")
    found = toybox.locate(cfg)
    if found.state is None or found.values is None:
        raise SystemExit(f"주소를 찾지 못했습니다: {found.state_why or found.values_why}")
    state, values, legacy = found.state, found.values, found.legacy
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    process = kernel32.OpenProcess(0x0410, False, sorted(mine)[0])      # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if not process:
        raise SystemExit("게임 프로세스를 열 수 없습니다")
    try:
        module, needed = ctypes.c_void_p(), wintypes.DWORD()
        if not psapi.EnumProcessModules(process, ctypes.byref(module), ctypes.sizeof(module), ctypes.byref(needed)):
            raise SystemExit("게임의 모듈 목록을 읽을 수 없습니다")
        base = module.value                                             # 첫 모듈이 실행 파일이다

        def read(address: int, fmt: str):
            buf, got = ctypes.create_string_buffer(struct.calcsize(fmt)), ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(process, address, buf, len(buf), ctypes.byref(got))
            return struct.unpack(fmt, buf.raw)[0] if ok and got.value == len(buf) else None

        out = {"program": read(base + state["program_state"], "<i"), "mode": read(base + state["mode_state"], "<i"),
               "multiplayer": read(base + state["multiplayer"], "<B"), "player_index": read(base + state["player_index"], "<i")}
        if legacy is not None:
            out["cheats_allowed"] = int(bool((read(base + legacy["options"], "<I") or 0) & 0x40))
        player = read(base + state["player_pointer"], "<Q")
        out["in_game"] = bool(out["mode"] == 2 and out["program"] == 1 and player)
        if out["in_game"]:
            world = read(base + values["world_pointer"], "<Q")
            out["player"] = read(player + 8, "<H")
            out["treasury"] = read(player + values["treasury"], "<d")
            out["stock"] = [read(player + values["stock_first"] + values["stock_step"] * i, "<f") for i in range(toybox.STOCK_SLOTS)]
            out["used"] = [bool((read(world + values["used_first"] + values["used_step"] * i, "<f") or 0) > 0)
                           for i in range(toybox.STOCK_SLOTS)] if world else None
        return out
    finally:
        kernel32.CloseHandle(process)
```

`main` 의 `elif cmd == "stop":` 앞에 갈래를 더한다:

```python
    elif cmd == "peek":
        print(json.dumps(peek_game(cfg), ensure_ascii=False))
```

Run: `uv run python scripts/gamedrive.py peek; echo "exit=$?"`
Expected: 게임이 떠 있지 않으므로 `게임이 떠 있지 않습니다`, `exit=1`. (게임이 뜬 뒤의 동작은 Step 4 에서 본다.)

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add scripts/gamedrive.py && git commit -q -F - <<'EOF'
chore: gamedrive.py peek — 자기가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다(검증용, 읽기만)

ToyBox 가 쓴 국고와 치트 허용 비트를 ToyBox 자신의 표시가 아닌 것으로 확인한다. 주소는 srkit locate 와 같은 서명으로 찾는다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `303 passed`.

- [ ] **Step 2: PR 을 올린다 (머지는 게임 안 확인과 최종 검토 뒤에)**

스크래치에 `pr-values-write.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 3 ~ 7 의 커밋 요약), 요구 3 에 대해 자동 테스트가 보는 것(돈 탭이 명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다 · 쓰는 곳은 플레이어의 그 칸뿐이다), 설계서와 달라진 곳(이 계획의 같은 이름의 절에서 코드에 닿는 것들), "게임 안 확인은 아래 댓글에", `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-values-write && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-values-write --title "feat: ToyBox 돈 탭 — 국고를 내장 치트 없이 직접 고친다" --body-file "<스크래치>/pr-values-write.md"
```

- [ ] **Step 3: 시험용 빌드를 게임 폴더에 바꿔 넣고, 검증 전의 상태를 적어 둔다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-vb build/verify/toybox-home-vb-off && rm -f build/verify/toybox-home-vb/* build/verify/toybox-home-vb-off/* && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/VB-saves-before.txt && cat build/verify/toybox/VB-saves-before.txt
```

두 폴더는 검증용 게임의 ToyBox 설정 폴더다(비어 있으므로 단축키는 기본값 `Ctrl+Shift+T`, 입력란은 10000). 사용자의 `%APPDATA%\SR2030ToyBox` 는 건드리지 않는다.

- [ ] **Step 4: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)의 "돈" 탭을 게임에서 확인한다. 이 작업(VB)만 수행하라.
끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다).
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법)과 E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법" · "확인한 것"의 H3(재무 패널을 여는 법)을 읽는다.

규칙:
- 게임은 다음으로만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-vb' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|peek|stop> …
- gamedrive.py peek 은 게임의 메모리에서 읽은 값을 JSON 으로 낸다(treasury = 국고(달러), cheats_allowed = 치트 허용 비트, in_game). ToyBox 의 창에 보이는 숫자와 따로 본다.
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간은 9 에서만, 거기 적힌 만큼만 흘린다. 그 밖에는 일시 정지인 채로 둔다.
- cheat resettutorial · cheat depopulate 는 어떤 경우에도 넣지 않는다. 10 에 적힌 단추 말고는 "돈" 탭 밖의 ToyBox 단추를 누르지 않는다.
- 화면은 E:\SR2030ToyBox\build\verify\toybox\VB-<번호>-<이름>.png 로 찍는다.
- ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-vb\toybox.log 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다. peek 의 출력은 그대로 옮긴다):
1. 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다(20초쯤. 빈 화면이면 기다렸다 다시 찍는다).
   로그에서 "게임 상태를 읽습니다 (…)", "값을 씁니다 (국고 +0x…, 재고 +0x… 간격 0x… × 12)", "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (…)" 세 줄을 그대로 옮겨 적는다.
   "값을 쓸 수 없습니다 (…)" 나 "게임 상태를 읽을 수 없습니다 (…)" 가 있으면 그 줄을 옮겨 적고, 2 만 하고 게임을 끈 뒤 보고한다.
2. 메인 메뉴에서 key CTRL+SHIFT+T 로 ToyBox 창을 연다. 맨 위의 상태 줄, "돈" 탭의 첫 줄("국고: …"), 단추들이 흐린지(꺼져 있는지)를 적는다.
   "+$10 B" 를 한 번 누른다. 로그에 새 줄이 생겼는지 적는다(생기면 안 된다). peek 을 한 번 찍는다(in_game 이 false 여야 한다).
3. 창을 닫고(같은 글쇠), 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 게임 화면이 뜨면 일시 정지 상태인지 본다.
4. peek 을 찍는다(T0 = treasury, cheats_allowed 는 0 이어야 한다). ToyBox 창을 열어 상태 줄과 "돈" 탭의 "국고: $ …" 를 적는다.
   게임의 재무 패널(또는 화면 위쪽의 국고 표시)을 열어 그 숫자를 찍는다. 셋(peek · ToyBox · 게임 화면)이 같은 금액인지 적는다.
5. "돈" 탭에서 차례로 누르고, 누를 때마다 peek 의 treasury 와 cheats_allowed, ToyBox 의 "국고: $ …", 바닥의 "마지막으로 쓴 값: …" 을 적는다:
   (a) "+$10 B"  (b) "-$10 B"  (c) 입력란이 10000 인 채로 "더하기"  (d) "빼기"  (e) "이 값으로"  (f) "$0"  (g) "+$100 B"
   기대: (a) T0 + 1e10, (b) T0, (c) T0 + 1e10, (d) T0, (e) 1e10, (f) 0, (g) 1e11. cheats_allowed 는 끝까지 0.
   게임의 설정 창(빨간 제목의 창)이 한 번이라도 떴는지 적는다(뜨면 안 된다).
6. (g) 뒤에 ToyBox 창을 닫고, 게임의 재무 패널을 다시 열어(이미 열려 있으면 닫았다 다시 열어) 국고 숫자를 찍는다(기대: $100.00 B).
   패널을 다시 열기 전의 숫자가 옛 값이었는지도 적는다.
7. ToyBox 창을 열어 "-$100 B" 를 두 번 누른다(기대: 0, 이어서 -1e11). peek 과 "국고: $ …"(기대: -100.00 B)를 적는다.
8. ToyBox 창을 닫고 재무 패널을 다시 열어 음수 국고가 어떻게 보이는지 찍는다.
9. 게임의 속도를 "매우 느림"으로 흘리고 실제 10초 뒤 다시 일시 정지한다(게임 날짜가 하루를 넘기지 않게 — 넘길 것 같으면 더 일찍 멈춘다).
   게임이 살아 있는지(화면이 그려지는지), peek 의 treasury(게임이 그 사이에 고쳤을 수 있다 — 본 값을 그대로), 게임의 날짜 · 시각을 적는다.
10. ToyBox 창을 열어 "화면·진행" 탭의 "GUI 숨기기/보이기" 를 한 번 누르고 화면을 찍은 뒤, 한 번 더 눌러 GUI 를 되돌린다.
    로그의 새 줄(기대: "직접 실행: cheat fullmapshow" 두 줄)과 peek 의 cheats_allowed(기대: 1 — 이 단추는 아직 내장 치트로 돈다)를 적는다.
11. "돈" 탭에서 "이 값으로"(입력란 10000)를 눌러 국고를 $10 B 로 두고, 창을 닫고, 게임의 메뉴(ESC) → "게임 종료" → 저장하지 않고 메인 메뉴로 나온다.
    ToyBox 창을 열어 상태 줄과 "돈" 탭의 첫 줄을 적는다(기대: "국고: -"). peek 을 찍는다.
12. gamedrive.py stop 으로 게임을 끈다. gamedrive.py status 로 꺼진 것을 확인한다. 로그를 E:\SR2030ToyBox\build\verify\toybox\VB.log 로 복사한다.
13. 한 번 더 띄운다 — 값 쓰기를 끈 채로:
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-vb-off' SRTOYBOX_WRITE=0 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
    메인 메뉴에서 ToyBox 창을 열어 "돈" 탭에 보이는 글을 적는다(기대: "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)" 한 줄만, 단추 없음).
    로그(…\toybox-home-vb-off\toybox.log)에서 "값을 쓰지 않습니다 (…)" 줄을 그대로 옮겨 적는다. 게임을 끄고 status 로 확인한다.
    로그를 E:\SR2030ToyBox\build\verify\toybox\VB-off.log 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). 로그에 "예외" 나 "실패" 가 든 줄이 있으면 그대로 옮긴다. 보지 못한 것은 "보지 못했다"와 까닭.
기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않는다. Task 8 의 문서 초안은 써도 된다(커밋은 브랜치를 바꿔야 하므로 에이전트가 끝난 뒤에).

- [ ] **Step 5: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "게임 상태를\|값을 \|값 쓰기\|옛 방식\|직접 실행\|예외\|실패" build/verify/toybox/VB.log; echo ---; grep -n "값을 \|값 쓰기" build/verify/toybox/VB-off.log; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/VB-saves-before.txt && echo "저장 폴더 그대로"
```

Expected:
- `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`, `값을 씁니다 (국고 +0x14B88, 재고 +0x14DA4 간격 0x150 × 12)`, `옛 방식(내장 치트)으로 도는 기능이 22개 남아 있습니다 (명령 처리 함수 +0x522330)` 가 한 줄씩.
- `값 쓰기: 국고 … -> …` 가 열 줄(5 의 일곱, 7 의 둘, 11 의 하나). 2 의 누름에 해당하는 줄은 없다. `직접 실행: cheat fullmapshow` 두 줄. `예외` · `실패` 가 든 줄이 없다.
- `VB-off.log` 에 `값을 쓰지 않습니다 (SRTOYBOX_WRITE=0. 국고 +0x14B88, …)` 한 줄, `값 쓰기` 줄은 없다.
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-values-write` 다. `저장 폴더 그대로`.

Read 도구로 화면을 직접 본다: 게임 안의 돈 탭(4), (g) 뒤의 재무 패널(6), 음수 국고의 재무 패널(8), `SRTOYBOX_WRITE=0` 의 돈 탭(13). 에이전트가 적은 글 · 숫자와 화면이 같은지 본다.

**전제가 틀리면 멈춘다**(설계서의 "3번의 V3 에서 전제가 틀리면 멈추고 사용자에게 알린다"): peek 의 값은 바뀌는데 다시 연 재무 패널이 옛 값이거나, 게임이 죽거나, `cheats_allowed` 가 5 ~ 9 사이에 1 이 됐거나, `값 쓰기 실패` 가 나왔으면 — 머지하지 않고 본 것을 그대로 사용자에게 알린다.

- [ ] **Step 6: Steam 으로 띄운 게임에서 로그를 본다 (한 번)**

채팅에 먼저 알린다: "Steam 으로 게임을 한 번 띄웁니다. 화면 크기 창으로 뜨고 시작하는 동안 포커스를 가져갑니다. 메인 메뉴에서 로그와 돈 탭만 보고 바로 끕니다. 게임에는 들어가지 않습니다."

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py steam
```

(백그라운드 작업으로. 메인 메뉴가 그려질 때까지 기다린다.) Steam 으로 띄운 게임은 사용자의 실제 설정 폴더(`%APPDATA%\SR2030ToyBox`)를 읽는다 — **설정을 바꾸지 않는다**(단축키도 거기 적힌 것을 쓴다. 입력란을 건드리지 않는다).

```bash
tail -n 12 "$APPDATA/SR2030ToyBox/toybox.log" | tee /e/SR2030ToyBox/build/verify/toybox/VB-steam.log; grep -n "^hotkey" "$APPDATA/SR2030ToyBox/toybox.ini"
```

Expected: `화면에 끼어들었습니다 (다른 훅이 먼저 있습니다)`, `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`, `값을 씁니다 (국고 +0x14B88, 재고 +0x14DA4 간격 0x150 × 12)`. 그 설정의 단축키(`gamedrive.py key <글쇠>`)로 창을 열어 `shot build/verify/toybox/VB-steam-menu.png` — 돈 탭의 첫 줄이 `국고: -` 이고 단추가 흐리다. 창을 닫고 `uv run python scripts/gamedrive.py stop`, 이어서 `status` 로 꺼진 것을 본다. `git diff --stat` 과 `ls -la "$APPDATA/SR2030ToyBox/toybox.ini"` 로 설정 파일이 고쳐지지 않았는지(시각) 본다.

Steam 이 꺼져 있거나 게임이 뜨지 않으면 "보지 못했다"로 적고 넘어간다(다시 시도하지 않는다).

- [ ] **Step 7: 최종 검토를 받고, 결과를 PR 에 적고, 머지한다**

**코드의 최종 검토는 여기서 한다**(이 PR 이 값 쓰기 코드의 전부다 — Task 8 은 문서뿐이다): 실행 방식의 최종 검토 절차대로 `develop` 과 이 브랜치의 차이 전체를 검토받고, Critical · Important 를 고친 뒤(고쳤으면 `uv run srkit toybox-build` → `uv run pytest` → 게임이 꺼진 채로 `uv run srkit deploy toybox` 미리보기 → `--apply` 로 최종 빌드를 다시 넣는다) 이어 간다.

스크래치에 `vb.md` 를 쓴다(Write 도구): 단계마다 한 것 / 본 것 / 근거 화면의 이름, peek 의 값 그대로, 로그의 줄 그대로, 보지 못한 것. `gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/vb.md"` 로 PR 에 단다.

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git push && gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && git switch develop && git pull --ff-only origin develop && git log --oneline -1
```

Expected: 테스트 통과, 머지 커밋이 `develop` 의 머리다. 게임 폴더에는 이 브랜치의 마지막 빌드가 들어 있다(`uv run srkit deploy toybox` 의 미리보기가 0개 파일).

---

### Task 8: 문서

**브랜치:** `docs/toybox-values-money` (PR #B 가 들어간 `develop` 에서 나눈다)

**Files:**
- Modify: `docs/10-toybox.md`, `docs/11-game-internals.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md` ("보완 내역"에 한 절)

**Interfaces:**
- Consumes: Task 7 의 `vb.md`(본 것 · 보지 못한 것), `uv run srkit locate` 의 출력, 이 계획의 "계획을 쓰며 확인한 것".
- Produces: 문서. 게임 안에서 보지 않은 것은 "보지 못했다"로 적는다 — `vb.md` 에 없는 것을 본 것처럼 쓰지 않는다.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-values-money && uv run srkit locate | tee "<스크래치>/locate-after.txt" | tail -30
```

- [ ] **Step 2: `docs/11-game-internals.md`**

1. "전역과 필드"의 표에 줄을 더한다(없는 것만): 세계 자료 객체의 포인터 `0x1af5868`(qword) — 그 객체의 `+0x18 + 0x84·i` 가 물자 `i` 의 "쓰는가"(float. 0 보다 크면 이번 판에서 쓴다. 값의 뜻은 모른다); 지역 객체의 `+0x14DA4 + 0x150·i`(`i` = 0 … 11) 가 물자 `i` 의 재고(float). 국고 줄(`+0x14B88`)에는 "단위는 달러 — 치트 `treasury N` 이 `N × 1000000.0` 을 더한다 [확인: 정적]"를 덧붙인다. 모두 "build 21347933" 을 적는다.
2. "새 찾기 — 게임 상태를 읽는 전역 일곱" 절 다음에 새 절 **"새 찾기 — 값을 읽고 쓰는 자리 (3단계 1 (나)부터)"** 를 쓴다. 들어갈 것:
   - 이 계획 Task 2 의 서명 표 12줄(찾을 것 · 서명 · 자리 · 함수 · 읽어 낸 값)을 그대로.
   - 읽어 낸 값의 대조 다섯 가지(`locate.h` 의 `locate_values` 설명과 같은 말로): 포인터는 쓸 수 있는 자료 구역 안 / 자리는 0 보다 크고 `0x100000` 보다 작다 / 간격은 4 의 배수 / 국고 칸과 재고 칸이 겹치지 않는다 / 못 찾으면 돈 탭만 꺼진다(내장 치트로 되돌아가지 않는다).
   - 재고의 칸 수 12 가 상수인 까닭과 근거 둘(이 계획의 "계획을 쓰며 확인한 것").
   - 상수를 읽어 내는 서명을 다시 뽑는 법: `uv run srkit sig-mine --offset 14b88` · `--offset 150 14da4` · `--offset 84 18`, 주소는 `uv run srkit sig-mine 1af5868`. **`--offset 84 18` 은 뜻이 다른 코드가 많이 섞여 나온다**(25개 함수 가운데 4개만 맞았다) — 명령 줄을 보고, `[rip]` 로 읽은 세계 자료 포인터에 `imul r, r, 84h` 와 `+18h` 를 더해 float 를 읽는 것만 고른다.
   - 치트 코드의 범위가 12곳이라는 것(명령 처리 함수 + 치트 코드에서만 불리는 함수 11개)과, `sig-mine` 이 그 안에서는 뽑지 않는다는 것.
   - 올라와 있는 게임에서 본 것: `vb.md` 의 로그 줄(`값을 씁니다 (…)`)과 걸린 시간을 그대로 — [확인: 실행]. Steam 으로 띄운 게임의 것도 본 대로.
3. "상태 묶음"의 절에 한 줄을 더한다: 찾은 주소가 쓸 수 있는 자료 구역(`.data`) 안이고 서로 겹치지 않아야 한다(3단계 1 (나)부터).
4. "자동 테스트의 설치본 대조는 빌드에 묶여 있다" 문단에 값 묶음의 기대값(`BUILD_VALUES`)과 `tests/toybox_cheat_oracle.py` 의 `values` 를 더한다.
5. "보지 않은 것"에서 이 계획이 본 것을 지우고(직접 쓴 국고를 게임이 쓰는가 — `vb.md` 대로), 남은 것을 적는다: 재고 칸에 쓴 값(계획 (다)의 V5), 칸과 물자 이름의 대응, 12번째 칸, 시간이 흐르는 동안의 쓰기가 게임의 계산과 겹치는지(본 만큼만).

- [ ] **Step 3: `docs/10-toybox.md`**

1. "무엇인가": 3단계 문단에 "돈 탭은 내장 치트를 거치지 않는다(3단계 1 (나), 2026-10-09). 나머지 22개 기능은 옮길 때까지 내장 치트로 돈다"를 더한다.
2. "쓰는 법": 돈 탭의 쓰는 법 — 첫 줄의 국고, 입력란(백만 달러, 1 ~ 1,000,000) + 더하기 · 빼기 · 이 값으로, 빠른 단추 다섯, 바닥의 `마지막으로 쓴 값`. 게임의 재무 패널은 다시 열어야 따라온다는 것(`vb.md` 의 6 에서 본 대로 — 보지 못했으면 2단계의 H3 을 가리킨다).
3. "기능"의 표: 돈의 세 줄(`cheat treasury N` · `cheat georgew` · `cheat georgeww`)을 지우고 돈 탭의 줄들로 바꾼다. "게임에 넣는 것" 칸은 "없다 — 국고 칸(double)에 직접 쓴다". 검증 칸은 `vb.md` 의 단계 번호([확인: VB-5] 등). 표 위의 기능 수(25 → 22 + 돈 탭)를 고친다.
4. "한계"에 더한다: 돈 탭만 쓴 판은 게임이 "치트를 쓴 판"으로 표시하지 않는다(치트 허용 비트를 건드리지 않는다 — `vb.md` 의 5 에서 본 대로) / 국고는 음수가 된다(±$1,000 T 안) / 쓴 뒤 열려 있던 패널은 스스로 다시 그려지지 않는다 / 값 쓰기가 한 번 실패하면 게임을 다시 띄울 때까지 꺼진다 / 물자 탭 · 최소 유지는 아직 없다(계획 (다)) / 물자의 세 단추는 아직 내장 치트다.
5. "구조"의 표: `values`(값 계산 — 순수 함수), `keeper`(값 쓰기 요청의 대기열)를 더하고, `locate`(값 묶음) · `game`(값 읽기 · 쓰기. 쓰는 곳은 둘뿐) · `features`(22줄) · `settings`(`money.amount`) · `ui`(돈 탭)의 줄을 고친다. 로그의 표에 새 줄 여섯을 더한다: `값을 씁니다 (…)` · `값을 쓸 수 없습니다 (…)` · `값을 쓰지 않습니다 (SRTOYBOX_WRITE=0. …)` · `값 쓰기: 국고 A -> B` · `값 쓰기 실패 (…) — 값 쓰기를 끕니다` · `맞지 않은 서명: <이름> #<번호> (…)`. `옛 방식 … 25개` 를 22개로.
6. "확인한 것": 새 표 **"3단계 1 (나) — 돈 탭"** 을 `vb.md` 에서 옮긴다(번호 VB-1 … VB-13, VB-S = Steam). 칸은 지금의 V0 표와 같다(# · 한 것 · 본 것 · 근거 화면). 설계서의 V 번호와의 대응을 표 아래에 적는다(VB-2 = V1 의 일부, VB-4 = V2, VB-5 · 6 = V3, VB-7 · 8 = V4, VB-13 = V12, VB-S = V14 의 일부). 보지 못한 것을 따로 적는다.
7. "문제가 생기면": `SRTOYBOX_WRITE=0`(값 쓰기를 끈다 — 돈 탭에 그 까닭이 보인다)을 탈출구 목록에 더한다. 돈 탭에 `이 게임 판에서는 쓸 수 없습니다 (…)` 가 보일 때 할 일(`uv run srkit locate` → [11](11-game-internals.md))을 적는다.
8. "다음 단계"의 표: 묶음 1 의 줄을 "(가) 완료 · (나) 완료 — 돈 탭 · (다) 물자 탭 · 최소 유지"로 고친다.

- [ ] **Step 4: `docs/09` · `README.md` · `CLAUDE.md` · 설계서**

- `docs/09-cheat-mod-plan.md`: 로드맵의 3단계 줄에 (나)의 완료와 날짜. "국고"의 표(72 ~ 74줄 근처, `cheat treasury` · `georgew` · `georgeww` 가 "그대로 쓴다"인 곳)에 "ToyBox 의 돈 탭은 3단계 1 (나)부터 이 치트를 쓰지 않고 국고 칸에 직접 쓴다([10](10-toybox.md))"를 덧붙인다. 치트 자체의 사실(07 의 검증)은 그대로 둔다.
- `README.md`: 현재 상태의 3단계 줄을 고친다(돈 탭이 내장 치트 없이 동작한다).
- `CLAUDE.md`:
  - "명령"의 `gamedrive.py` 줄들에 `peek`(자기가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다 — 값 쓰기를 확인할 때 ToyBox 의 표시 대신 이것으로 본다)을 더한다.
  - "게임이 업데이트된 뒤에는"의 서명 줄에 `uv run srkit sig-mine --offset <간격> <첫 칸>` 을 더한다.
  - "지켜야 할 것"에 더한다: "ToyBox 가 게임의 메모리에 쓰는 곳은 플레이어 지역 객체의 국고 1칸과 재고 12칸뿐이다(`game.h`). 쓰는 곳을 늘릴 때는 설계서에서 정하고 `game.h` 의 머리말을 함께 고친다."
- 설계서(`docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md`)의 끝에 절 **"보완 내역 (2026-10-09, 계획 (나)를 쓰며)"** 를 더한다: 이 계획의 "설계서와 달라진 곳"을 그대로 옮기고, [계획 (나)](../plans/2026-10-09-toybox-stage3-1b-values-money.md)를 가리킨다. 앞의 "보완 내역"에서 "(나) = 3 ~ 5" 라고 한 것이 "(나) = 3, (다) = 4 · 5" 로 바뀌었음을 적는다.

- [ ] **Step 5: 링크와 사실을 대조하고 커밋 · PR · 머지**

```bash
cd /e/SR2030ToyBox && uv run python "<스크래치>/linkcheck.py" 2>&1 | tail -5; grep -n "25개\|25 개\|georgew" docs/10-toybox.md README.md CLAUDE.md | head -20; uv run pytest -q 2>&1 | tail -2
```

Expected: 깨진 상대 링크가 없다(`linkcheck.py` 는 계획 (가)에서 쓴 스크래치의 스크립트다 — 없으면 `docs/` · `README.md` · `CLAUDE.md` 의 `](…)` 링크가 가리키는 파일이 있는지 보는 열 줄짜리를 다시 쓴다). 남은 `25개` · `georgew` 는 지난 단계의 기록(확인한 것의 G · R · H · V0 줄)뿐이다. `303 passed`(문서만 바꿨다).

```bash
cd /e/SR2030ToyBox && git add docs README.md CLAUDE.md && git commit -q -F - <<'EOF'
docs: ToyBox 3단계 1 (나) — 돈 탭(내장 치트 없이 국고를 직접 고친다), 값의 자리 찾기, 게임에서 본 것

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox-values-money
```

스크래치에 `pr-docs-values.md` 를 쓰고(무엇을 고쳤나의 표, 게임에서 본 것과 보지 못한 것, `uv run pytest` 결과), PR 을 올려 머지한다:

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/toybox-values-money --title "docs: ToyBox 3단계 1 (나) — 돈 탭과 값의 자리 찾기" --body-file "<스크래치>/pr-docs-values.md"
```

```bash
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git log --oneline -3
```

---

## 끝난 뒤의 상태와 계획 (다)로 넘기는 것

- `develop` 에 PR 셋(값의 자리 찾기 · 돈 탭 · 문서)이 들어가 있다. `uv run pytest` 303개 통과. 게임 폴더에는 최종 빌드의 `srtoybox.dll` 이 있고 그 밖의 게임 파일은 그대로다. 사용자의 `%APPDATA%\SR2030ToyBox` 설정은 그대로다(새 빌드가 처음 설정을 저장할 때 `money.amount=10000` 줄이 생기고 `treasury=…` 줄이 없어진다 — 사용자가 창에서 무언가를 바꿀 때다).
- **계획 (다)가 쓰는 것**(이 계획이 만든 것): `game_values()` 의 `used` · `stock`, `keeper_enqueue({칸, Change, 수량})`(재고의 요청은 이미 된다 — 테스트 `test_stock_requests_reach_only_products_in_use`), `Change::Floor`(바닥 — 최소 유지의 셈), `short_number`, `gamedrive.py peek` 의 `stock` · `used`.
- **계획 (다)가 할 것**: 물자 이름표(`products`), 물자 탭(물자마다 재고 · −1억 · −100만 · 0 · +100만 · +1억, "모든 물자" 줄), 물자의 치트 세 줄 삭제(22 → 19줄), 최소 유지(국고 · 물자. 0.5초마다, 설정 저장, 상태 줄의 "유지 중"), 창의 첫 크기 720×520, `docs/05`(재고 칸이 12개라는 것). 첫 일은 설계서의 V5 · V6(칸과 이름의 대응, 12번째 칸) — 이름표를 그 뒤에 확정한다. 물자 수량의 줄임 표기도 그때 게임 화면을 보고 정한다.
- **이 계획이 미룬 것**: 계획 (가)의 최종 검토가 남긴 "나중에" 넷(설치본 테스트가 TimeDateStamp 에 묶여 있다 — 문서에 적어 뒀다, 새 찾기가 `.pdata` 를 요구한다, `__try` 길의 `std::vector`, 작은 테스트 빈틈)은 그대로다.
