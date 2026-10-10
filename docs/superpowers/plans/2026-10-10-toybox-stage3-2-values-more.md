# ToyBox 3단계 2 — 그 밖의 값 쓰기(지식 순위 · 세계 시장 여론 · 관계) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ToyBox 의 단추 넷("지식 순위 올리기" · "세계 시장 여론 최고" · "관계 최고" · "관계 중립")이 내장 치트를 거치지 않고 게임의 값을 직접 쓴다 — 단추의 이름 · 탭 · 자리는 그대로이고, 내장 치트로 도는 기능은 19 → 15 가 된다.

**Architecture:** 묶음 1 이 깐 길(치트와 무관한 서명으로 자리 찾기 → 쓰기 직전의 확인 → 요청의 대기열 → 게임 창의 타이머에서 쓰기)에 네 가지를 얹는다: 새 찾기의 묶음 셋 `locate_more`(지식 · 여론 · 관계 — 묶음마다 따로 찾고 따로 실패한다), `game` 의 읽기와 쓰기(관계는 치트처럼 두 지역 객체에 쓴다), `keeper` 의 요청 셋, 기능 표의 `Direct` 와 창의 `direct_row`(쓸 수 없으면 단추 자리에 까닭 한 줄). 설정 파일에 더할 것은 없다.

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Dear ImGui 1.92.9b, Python 3.13 + ctypes + pytest (`uv run`), Win32.

**Spec:** `docs/superpowers/specs/2026-10-10-toybox-stage3-2-design.md` (승인 2026-10-10). 3단계의 여덟 묶음과 요구 셋은 [3단계 1 설계](../specs/2026-10-09-toybox-stage3-1-design.md)에 있다.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 와 자리는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 도 구조체 안의 자리도 적지 않는다(서명이 읽어 낸다).
- **요구 3 — 내장 치트와 별도.** 네 단추의 어떤 동작도 치트 명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다. 치트 닻을 쓰는 곳은 지금의 셋 그대로다: `locate_legacy`(전환 기간), `srkit.sigmine`(개발용), `tests/toybox_cheat_oracle.py`(테스트의 대조).
- **무엇을 찾지 못하거나 쓰지 못할 때 내장 치트로 되돌아가지 않는다.** 그 단추의 자리에 까닭 한 줄만 보인다.
- **묶음마다 따로다.** 지식 · 여론 · 관계 가운데 하나를 못 찾아도 그 단추(들)만 꺼지고, 다른 묶음과 돈 · 물자 · 상태 읽기는 그대로다. 거꾸로 돈 · 물자의 자리를 못 찾아도 이 묶음들은 동작한다.
- **게임의 메모리에 쓰는 곳은 이것뿐이다**(`game.h` 의 머리말): 플레이어 지역 객체의 국고 1칸 · 재고 12칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸, 그리고 **고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸**. 전역 · 치트 허용 비트 · 그 밖의 지역에는 쓰지 않는다. (관계를 양쪽에 쓰는 것은 사용자가 정했다 — 2026-10-10, 설계서의 "결정 사항".)
- **요구 2 — 플레이어의 나라에만.** 쓰는 것은 지금 플레이하는 나라의 값이고, 관계는 그 나라와 창의 목록에서 고른 나라 하나 사이의 것이다. 나라가 바뀌면 그 뒤로는 새 나라의 칸에 쓴다.
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다. (설계서의 승인이 이 바꿔 넣기의 승인을 포함한다.)
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 게임 안을 돌아다니는 확인은 백그라운드 에이전트에 맡긴다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다.** 한 판에서 게임 시간을 3일 넘게 흘리지 않는다(7일마다 자동 저장된다). 게임이 떠 있는 동안 브랜치를 바꾸지 않고 `uv run pytest` 를 돌리지 않는다. **게임을 띄우는 횟수는 한 번을 목표로 한다**(사용자가 같은 PC 를 쓰고 있다).
- **`start` 의 출력에 `돌려주지 못함 N회` 나 `게임이 포커스를 쥐고 있음` 이 나오면 게임을 끄고 사용자에게 알린다**(사용자의 입력이 화면 밖 게임으로 가고 있다).
- **검증용 게임은 `SRTOYBOX_HOME` 을 임시 폴더(`build/verify/…`)로 돌려 띄운다.** 사용자의 실제 `%APPDATA%\SR2030ToyBox` 설정을 읽지도 고치지도 않는다. **이 계획에서는 Steam 으로 띄우지 않는다.**
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.**
- Git: `main` · `develop` 에 직접 커밋하지 않는다. `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고 `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다. **머지 명령이 권한 분류기에 거부되면 다른 형태로 우회하지 않는다** — 사용자에게 그 명령을 그대로 건네고, 머지된 뒤 `git switch develop && git pull --ff-only origin develop` 로 이어 간다.
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`(또는 `PYTHONIOENCODING=utf-8`).
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다.
- **창과 로그에 보이는 새 글에는 한글 · ASCII · `·` · `—` 만 쓴다**(`→` `–` `−` 를 쓰지 않는다 — 글꼴에 한국어 범위의 글리프만 올라가 있다). 로그는 `값 쓰기: 기술 수준 130 -> 131`.
- **시작할 때의 테스트 상태**: `develop`(이 계획 문서가 들어간 뒤)에서 `uv run pytest` 344개 통과.
- 화면 검사 테스트가 실패하면 "흔들림"으로 넘기지 않고 원인을 본다. 테스트는 다른 무거운 일(빌드)과 함께 돌리지 않는다 — 검사 프로세스가 DLL 사본을 뜨는 중에 DLL 이 바뀐다.

## 고칠 곳을 읽는 법

Task 1 ~ 5 의 코드는 **"고칠 곳"** 으로 적었다. 꼴은 다섯 가지이고, 찾을 글은 그 파일에 정확히 한 번 나온다(문맥을 그만큼 넓혀 뒀다). 한 Task 안에서는 적힌 순서대로 옮긴다.

| 꼴 | 뜻 |
|---|---|
| 새 파일 `경로`: + 블록 | 그 내용으로 파일을 만든다 |
| `경로` 를 통째로 다음으로 바꾼다: + 블록 | 파일 전체를 그 내용으로 바꾼다 |
| `경로` 에서 다음을 찾아: + 블록 / 이렇게 바꾼다: + 블록 | 첫 블록을 둘째 블록으로 바꾼다 |
| `경로` 에서 다음 바로 뒤에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 다음 줄에 둘째 블록을 끼운다 |
| `경로` 에서 다음 바로 앞에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 앞에 둘째 블록을 끼운다 |

블록 끝의 빈 줄도 글의 일부다(함수 사이의 빈 줄 둘을 지키려고 그렇게 적었다). 손으로 옮겨도 되고, 옮겨 적는 도구로 옮겨도 된다 — 계획을 쓰며 만든 스크래치의 `apply_plan.py <이 문서> <저장소 루트> <Task 번호> <test|code>` 가 이 문서의 블록을 그대로 읽어 옮긴다(`<!-- 고칠 곳: … -->` 표시 사이. 찾을 글이 한 번이 아니면 아무것도 쓰지 않고 멈춘다). 도구는 저장소에 넣지 않는다.

## 설계서와 달라진 곳 (계획을 쓰며)

- **묶음끼리 자리가 겹치면 두 묶음 다 버린다.** 설계서는 "하나라도 아니면 그 묶음은 못 찾았다"고만 했다. 기술 수준 칸이 관계 표 안에 들어 있다면 어느 쪽이 엉뚱한 것을 읽었는지 알 수 없다. 돈 · 물자의 칸과 겹칠 때는 새 묶음만 버린다(값 묶음은 그대로 — 설계서 그대로).
- **여러 칸을 쓰는 요청은 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 먼저 본다.** 그래서 자리의 보호 때문에 실패할 때는 한 칸도 쓰지 않는다. 설계서의 "도중에 실패하면 거기서 멈추고 어디까지 썼는지 적는다"는 그대로이되(쓴 뒤 다시 읽은 값이 두 번 다 다를 때), 로그의 꼴이 둘이다: 한 칸도 쓰지 않았으면 `값 쓰기 실패 (관계 — 폴란드 (1106)) — 값 쓰기를 끕니다`, 몇 칸을 쓴 뒤면 `값 쓰기 실패 (관계 — 폴란드 (1106), 6칸 가운데 3칸을 쓴 뒤) — …`.
- **쓰기의 판정에 "그 나라가 없다"(`Wrote::NoTarget`)를 더한다.** 없는 번호 · 사람도 AI 도 맡지 않은 지역 · 객체가 아는 인덱스가 표의 자리와 다른 것 · 플레이어 자신.
- **관계를 쓰는 함수는 수준 −1 … 1 을 받는다**(창이 내는 것은 1 과 0 뿐이다). 범위 밖 · 수가 아닌 값은 쓰지 않는다.
- **기능 표의 네 줄은 `Feature::direct`(직접 쓰는 일의 종류)를 갖고 `command` 는 빈 글이다.** 줄의 수(19)와 순서는 그대로이고, "내장 치트로 도는 줄의 수"는 `cheat_feature_count()` 가 센다(15). 테스트용 내보내기 `srtoybox_feature_info` 의 줄에 열두째 칸(하는 길)이 생긴다.
- **기술 수준의 한도(999)는 `keeper.h` 의 `TECH_LIMIT` 다.** 설계서가 `values` 는 바뀌지 않는다고 했으므로 값 계산 모듈에 두지 않았다. 지금 값은 있는 그대로 적는다(`기술 수준 130 -> 131`, 정수가 아니면 `130.5 -> 131.5`).
- **대기열의 문이 바뀐다.** 지금은 "돈 · 물자의 값을 쓸 수 없으면" 대기열을 통째로 비운다. 묶음이 서로 기대지 않게 하려면 문은 "값 쓰기가 켜져 있는가"(`game_writes()` — 게임을 읽고, `SRTOYBOX_WRITE` 가 0 이 아니고, 이번 실행에서 실패한 적이 없다)여야 하고, 요청마다 그 요청이 쓰는 묶음을 본다. 최소 유지는 돈 · 물자의 자리를 못 찾은 게임에서 쉰다(전과 같다 — 조건을 따로 적었을 뿐이다).
- **로그의 줄**: `값을 더 씁니다 (…)` 는 찾은 묶음만 ` · ` 로 이어 적는다(`기술 수준 +0x14CD0 · 세계 시장 여론 +0x14AF4 +0x14AF8 +0x14B10 · 관계 +0x15F10 +0x16F10 전쟁 명분 +0x17F10`). `SRTOYBOX_WRITE=0` 이면 `값을 더 쓰지 않습니다 (SRTOYBOX_WRITE=0. …)`. 못 찾은 묶음은 `기술 수준을 쓸 수 없습니다 (…)` · `세계 시장 여론을 쓸 수 없습니다 (…)` · `관계를 쓸 수 없습니다 (…)`. `맞지 않은 서명: …` 은 찾은 묶음의 것만 적는다(못 찾은 묶음의 서명 셋을 줄줄이 적지 않는다).
- **설계서의 W0 "서명 54개가 모두 맞는다"는 로그의 한 줄로는 보이지 않는다.** 로그의 수는 상태 묶음의 것(21개 가운데 N개)뿐이다. 게임 안에서는 `맞지 않은 서명` 줄이 없는 것과 `값을 씁니다` · `값을 더 씁니다` 의 자리로 본다. 54개가 저마다 한 번 맞는 것은 설치된 실행 파일에 대한 자동 테스트가 본다.
- **"지식 순위 올리기"의 설명 글은 게임 안 확인(W2) 뒤에 정한다**(설계서 그대로). 그 칸이 기술 수준임을 보면 Task 6 에서 한 줄을 고친다.
- **가짜 게임의 지역 객체를 0x200 → 0x1000 바이트로 키운다**(관계 표가 지역 인덱스로 찾는 표라서). 그 크기를 박아 둔 테스트 두 줄을 상수로 바꾼다.
- **이미 있는 화면 테스트 둘이 "관계 최고"에 기대고 있었다.** 그 단추가 더는 게임의 함수를 부르지 않으므로: 오류 가드의 경고를 보는 테스트(`confirm_fault`)는 "동맹 맺기"를 누르고, 고른 나라가 풀리는 테스트(`pick_gone` · `pick_become`)는 명령 처리 함수가 받은 줄 대신 관계의 칸을 본다.
- **`gamedrive.py peek` 의 새 읽기는 순수 함수 `peek_more` 로 떼어 테스트한다**(게임 프로세스 없이). 번호를 준 `peek <지역 번호>` 는 그 지역의 기술 수준 · 여론도 읽는다(국고 · 재고와 같은 규칙).
- **코드 PR 은 하나다**(`feat/toybox-values-more` — 설계서 그대로). 코드의 최종 검토는 그 PR 을 머지하기 전(Task 6)에 받는다.

## 계획을 쓰며 확인한 것

- **서명 21개를 정했다** [확인: 정적 — `uv run srkit sig-mine --offset <자리>` 의 후보에서 명령을 보고 골랐다]. 저마다 실행 구역에 한 번만 맞고, 찾을 것마다 세 서명이 서로 다른 함수에 있고, 맞은 자리가 모두 치트 코드 밖이다(Task 1 의 테스트가 본다).

  | 찾을 것 | 서명 | 맞는 자리 | 그 명령 |
  |---|---|---|---|
  | 기술 수준 칸 `+0x14CD0` | `F3 0F 2C 88 [u32] 41 3B C8 7E 4A` | `0x7ac395` | `cvttss2si ecx,[rax+칸]` / `cmp` / `jle` |
  | | `F3 0F 2C 87 [u32] 83 E8 0F 3B C8` | `0xbbd4cb` | `cvttss2si eax,[rdi+칸]` / `sub eax,0Fh` / `cmp` |
  | | `48 05 [u32] F3 0F 2C 00 05 6C 07 00 00` | `0x55320f` | `add rax,칸` / `cvttss2si eax,[rax]` / `add eax,76Ch`(1900) |
  | 여론 칸 1 `+0x14AF4` | `F3 0F 58 B0 [u32] 48 85 D2 74 48` | `0x4f7c25` | `addss xmm6,[rax+칸]` |
  | | `F3 0F 10 89 [u32] 44 0F 2F D1 76 18` | `0x79925b` | `movss xmm1,[rcx+칸]` / `comiss` |
  | | `F3 0F 59 8B [u32] F3 0F 58 C8 0F 2F F1` | `0x7030f0` | `mulss xmm1,[rbx+칸]` |
  | 여론 칸 2 `+0x14AF8` | `F3 0F 10 88 [u32] 0F 2F CB 76 5D` | `0x799654` | `movss xmm1,[rax+칸]` / `comiss` |
  | | `F3 0F 10 8F [u32] 0F 2E CE 7A 14` | `0xbbc236` | `movss xmm1,[rdi+칸]` / `ucomiss` |
  | | `F3 0F 59 8B [u32] F3 0F 58 C8 0F 28 C2` | `0x702f83` | `mulss xmm1,[rbx+칸]` |
  | 여론 칸 3 `+0x14B10` | `F3 0F 10 B0 [u32] 48 85 D2 74 43` | `0x4f7ebd` | `movss xmm6,[rax+칸]`(rax = 지역 표의 한 칸) |
  | | `F3 0F 10 8A [u32] 0F 2F F9 76 2E` | `0x7996f9` | `movss xmm1,[rdx+칸]` / `comiss` |
  | | `F3 0F 10 81 [u32] 48 8D 44 24 70 F3 0F 5C C1` | `0x731b27` | `movss xmm0,[rcx+칸]` |
  | 관계 표 1 `+0x15F10` | `41 0F 2F 84 8D [u32] 76 0D 40 B6 01` | `0x4baa5b` | `comiss xmm0,[r13+rcx*4+표]` |
  | | `F3 42 0F 10 9C 82 [u32] 0F 2F FB 76 33` | `0x70f93b` | `movss xmm3,[rdx+r8*4+표]`(조약 함수 `0x70cbd0`) |
  | | `F3 0F 10 84 81 [u32] 41 0F 2F C6 76 5F` | `0x799434` | `movss xmm0,[rcx+rax*4+표]` |
  | 관계 표 2 `+0x16F10` | `41 0F 2F 84 84 [u32] 76 7A 48 85 D2` | `0x4b6874` | `comiss xmm0,[r12+rax*4+표]` |
  | | `F3 0F 11 84 88 [u32] 45 85 DB 79 2A` | `0x702b71` | `movss [rax+rcx*4+표],xmm0` |
  | | `F3 0F 10 9C 81 [u32] 8B D0 0F 2F FB` | `0x70f81c` | `movss xmm3,[rcx+rax*4+표]`(조약 함수) |
  | 전쟁 명분 표 `+0x17F10` | `F3 0F 10 9C 8A [u32] 0F 2F FB 76 35` | `0x70f8a7` | `movss xmm3,[rdx+rcx*4+표]`(조약 함수) |
  | | `F3 41 0F 5C 8C 82 [u32] 0F 2F C1 76 02` | `0x7003b0` | `subss xmm1,[r10+rax*4+표]` |
  | | `F3 0F 11 84 88 [u32] 0F 28 C2 48 8B 07` | `0x70331b` | `movss [rax+rcx*4+표],xmm0` |

- **치트 본문과의 대조** [확인: 정적]: 서명이 낸 일곱 자리가 치트 `finalexam`(`movss`/`addss`/`movss` 의 칸) · `shelovesme`(1.0 을 쓰는 세 칸) · `love`(플레이어 쪽과 그 나라 쪽에서 1.0 을 쓰는 표 둘과 0 을 쓰는 표 하나)의 본문에서 읽은 자리와 같고, `neutral` 이 같은 여섯 칸에 0 을 쓴다(Task 1 의 테스트 — `tests/toybox_cheat_oracle.py` 의 `more`).
- **이 계획의 고칠 곳을 모두 저장소의 스크래치 사본에 옮겨 돌려 봤다**(저장소와 게임 폴더는 건드리지 않았다):
  - 도구(`apply_plan.py`)가 이 문서에서 읽어 옮긴 결과가, Task 마다, 따로 구현해 둔 상태와 글자까지 같다.
  - Task 마다 테스트만 옮기고 실패를 보고, 코드를 옮겨 빌드(`/W4 /WX`)하고 통과를 봤다. 단계의 Expected 는 그때 본 것이다.
  - 끝 상태에서 저장소의 테스트 전체가 통과한다(`418 passed` — 시작할 때의 344개에 74개가 더해진다).
- **돌려 보지 못한 것**: 게임 안의 동작 전부(Task 6), `gamedrive.py peek` 이 실제 게임에서 읽는 것(읽는 셈만 가짜 메모리로 테스트했다).

## Review Focus

설계서가 말하지 않았거나 자동 테스트만으로는 다 보지 못하는 것 — 사람이 쓸 때 걸릴 만한 순서로:

1. **게임이 쓴 값을 곧 다시 셈한다.** 관계와 여론은 게임이 날마다 고치는 값일 수 있다 — 눌렀는데 얼마 뒤 되돌아가 있으면 사용자는 "안 된다"로 본다. 자동 테스트로는 볼 수 없다 → Task 6 의 W8 에서 시간을 흘려 얼마나 바뀌는지 보고, 본 대로 `docs/10` 의 한계에 적는다(치트도 같은 칸에 같은 값을 쓸 뿐이다).
2. **단추를 누른 뒤 쓰이기 전에 다른 나라를 고른다.** 쓰는 것은 다음 타이머에서다 — 그 사이에 목록에서 다른 나라를 고르면 누른 때의 나라에 써야 한다 → Task 4 의 `test_a_relation_is_written_with_the_country_picked_when_the_button_was_pressed`.
3. **고른 나라가 쓰기 직전에 없어진다**(다른 판을 불러왔다, 병합됐다). 엉뚱한 객체에 쓰면 안 된다 → Task 2 의 `test_a_relation_is_written_only_with_a_country_that_is_in_this_game`, Task 3 의 `test_a_relation_request_for_a_country_that_is_gone_is_dropped`. 게임이 병합된 나라의 객체를 실제로 어떻게 바꾸는지(상태 값)는 보지 않았다 — 가짜 게임은 "이번 판에 없는 지역"(상태 5)만 흉내 낸다.
4. **두 객체 가운데 한쪽만 쓸 수 있다.** 관계의 반쪽만 쓰고 멈추면 게임이 본 적 없는 상태가 남는다 → Task 2 의 `test_more_on_a_page_that_is_not_read_write_is_not_written`(고른 나라 쪽이 쓸 수 없으면 플레이어 쪽도 쓰지 않는다).
5. **기술 수준이 정수가 아니거나 한도에 닿았다.** 한도 바로 아래에서 넘기지 않고, 수가 아닌 값은 건드리지 않고, 정수가 아닌 값은 있는 그대로 적는다 → Task 3 의 `test_tech_stops_at_its_limit_and_leaves_what_it_cannot_read`.

## 파일 구조

| 파일 | 맡는 일 | Task |
|---|---|---|
| `native/srtoybox/locate.h` · `.cpp` | (더함) `MoreLayout`, 서명 21개, `locate_more`, `locate_more_group` | 1 · 2 |
| `native/srtoybox/game.h` · `.cpp` | (더함) 기술 수준 · 여론 · 관계의 읽기와 쓰기, 묶음마다의 "쓸 수 없는 까닭", 시작할 때의 찾기와 로그 | 2 · 4 |
| `native/srtoybox/keeper.h` · `.cpp` | (더함) 요청 셋(`TECH` · `OPINION` · `RELATION`), 대기열의 문 | 3 |
| `native/srtoybox/features.h` · `.cpp` | (고침) `Direct`, 네 줄의 전환, `cheat_feature_count` | 4 |
| `native/srtoybox/command.h` · `.cpp` | (고침) 직접 쓰는 줄은 게임에 넣을 글이 없다 | 4 |
| `native/srtoybox/ui.cpp` | (더함) `direct_row` | 4 |
| `native/srtoybox/exports.cpp` | (더함) 테스트용 내보내기 | 1 ~ 4 |
| `src/srkit/toybox.py` · `cli.py` | (더함) `MoreLayout` · `more_of`, `srkit locate` 의 새 절 | 1 |
| `scripts/gamedrive.py` | (더함) `peek_more` | 5 |
| `tests/toybox_fake_exe.py` · `toybox_cheat_oracle.py` · `toybox_fake_game.py` · `toybox_overlay_probe.py` | 테스트 도우미: 가짜 이미지의 새 자리, 치트 본문의 대조, 가짜 게임의 새 칸, 화면 검사의 새 모드 | 1 · 2 · 4 |
| `tests/test_toybox_game.py` · `test_toybox_values.py` · `test_toybox.py` · `test_gamedrive.py` | 테스트 | 1 ~ 5 |
| `docs/10` · `11` · `05` · `09` · `README.md` · `CLAUDE.md` · 설계서 | 문서 | 7 |

`sigs` · `values` · `products` · `settings` · `input` · `regions` 은 바뀌지 않는다.

---

### Task 1: 새 찾기의 묶음 셋 — 기술 수준 · 여론 · 관계의 자리

**브랜치:** `feat/toybox-values-more` (`develop` 에서 나눈다)

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`, `src/srkit/cli.py`
- Test: `tests/test_toybox_game.py`, `tests/toybox_fake_exe.py`, `tests/toybox_cheat_oracle.py`

**Interfaces:**
- Consumes: 묶음 1 의 `sigs.h`(`sig_parse` · `sig_scan` · `sig_vote`), `locate.cpp` 의 `vote_table` · `offset_ok` · `name_rows`, `ValueLayout`, `SigRow`, `STATE_SIGS`(3) · `STATE_NEED`(2), `toybox._sig_rows` · `toybox.SigRow`.
- Produces:
  - `struct MoreLayout { uint32_t tech; uint32_t opinion[3]; uint32_t relation[2]; uint32_t casus; }` — 모두 지역 객체 안의 자리. 못 찾은 묶음의 필드는 0.
  - `const int MORE_TECH = 1, MORE_OPINION = 2, MORE_RELATIONS = 4;`(묶음의 비트), `MORE_GROUPS = 3`, `MORE_WANTED = 7`, `REGION_SLOTS = 1024`, `const size_t MORE_WHY = 160`.
  - `int locate_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY])` — 찾은 묶음의 비트를 돌려준다. `why` 는 `MORE_GROUPS` 줄(지식 · 여론 · 관계 순), `rows` 는 `MORE_WANTED * STATE_SIGS` 칸이거나 `nullptr`, `values` 는 값 묶음(찾았을 때)이거나 `nullptr`.
  - 내보내기 `int srtoybox_locate_more(image, size, const ValueLayout *values, MoreLayout *out, char *error, int error_size, char *rows, int rows_size)` — 돌려주는 값은 묶음의 비트, `error` 는 묶음마다 한 줄.
  - Python: `toybox.MORE_FIELDS`(`tech` `opinion0` `opinion1` `opinion2` `relation0` `relation1` `casus`), `toybox.MORE_NAMES`, `toybox.MORE_GROUPS`(`[(이름, [필드…])]` 셋), `toybox.MoreLayout`(ctypes), `toybox.more_of(lib, image, values=None) -> (dict, list[str], list[SigRow])`, `Located.more` · `more_why` · `more_rows`.
  - 테스트 도우미: `toybox_fake_exe.MORE`(가짜 자리), `toybox_cheat_oracle.more(image) -> dict`.

- [ ] **Step 0: 브랜치를 만들고 시작할 때의 상태를 본다**

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py status | head -1 && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-values-more && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -2
```

Expected: `프로세스: 없음`(게임이 떠 있으면 테스트를 돌리지 않고 멈춘다), `빌드 완료: …\build\toybox\srtoybox.dll`, `344 passed`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

가짜 이미지에 새 자리를 더하고(`toybox_fake_exe.MORE`), 치트 본문에서 같은 자리를 읽는 대조(`toybox_cheat_oracle.more`)를 더하고, 찾기의 테스트를 쓴다: 치트 문자열 없이 찾는다 / 서명 하나가 깨져도 찾는다 / 한 묶음이 깨지면 그 묶음만 버린다 / 말이 안 되는 자리 · 겹치는 자리 / 설치된 게임에서의 값 / 치트 본문과의 대조.

<!-- 고칠 곳: test -->
`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
GARBAGE = [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)]
```

이것을 더한다:

```python
BUILD_MORE = {"tech": 0x14CD0, "opinion0": 0x14AF4, "opinion1": 0x14AF8, "opinion2": 0x14B10, "relation0": 0x15F10,
              "relation1": 0x16F10, "casus": 0x17F10}
```

`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
def installed_image(game_dir) -> bytes:
```

이것을 더한다:

```python
@pytest.fixture(scope="module")
def more_sigs(lib):
    """DLL 에 든 "더 쓰는 값"의 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.more_of(lib, b"")[2]]


```

`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
    for row in toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]:
```

이렇게 바꾼다:

```python
    for row in toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]:
```

`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
    rows = toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2]
```

이렇게 바꾼다:

```python
    rows = toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]
```

`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
def test_legacy_finds_the_handler_from_the_cheat_anchor(lib, sigs):
```

이것을 더한다:

```python
def more_without(group: int) -> dict[str, int]:
    """가짜 이미지의 "더 쓰는 값"에서 그 묶음(0 지식, 1 여론, 2 관계)만 못 찾았을 때의 결과."""
    return {**toybox_fake_exe.MORE, **dict.fromkeys(toybox.MORE_GROUPS[group][1], 0)}


def test_the_more_table_has_three_signatures_per_item(more_sigs):
    assert [name for name, _ in more_sigs] == [name for name in toybox.MORE_FIELDS for _ in range(3)]
    assert len({text for _, text in more_sigs}) == 21
    assert [field for _, fields in toybox.MORE_GROUPS for field in fields] == toybox.MORE_FIELDS


def test_more_is_found_in_an_image_without_any_cheat_string(lib, more_sigs):
    """기술 수준 · 여론 · 관계의 자리도 치트 문자열에 기대지 않고 찾는다."""
    image = toybox_fake_exe.sig_image(more_sigs)
    assert b"cheat" not in image
    found, why, rows = toybox.more_of(lib, image)
    assert found == toybox_fake_exe.MORE and why == ["", "", ""]
    assert [row.count for row in rows] == [1] * 21
    assert all(row.value == toybox_fake_exe.MORE[row.name] for row in rows)


@pytest.mark.parametrize("which", range(7))
def test_more_survives_one_broken_signature_per_item(lib, more_sigs, which):
    found, why, rows = toybox.more_of(lib, toybox_fake_exe.sig_image(more_sigs, broken={3 * which + 2}))
    assert found == toybox_fake_exe.MORE and why == ["", "", ""]
    assert rows[3 * which + 2].count == 0


@pytest.mark.parametrize("item, group, label", [(0, 0, "기술 수준 칸"), (2, 1, "여론 칸 2"), (6, 2, "전쟁 명분 표")],
                         ids=["tech", "opinion", "relations"])
def test_a_group_that_cannot_find_one_of_its_items_is_dropped_alone(lib, more_sigs, item, group, label):
    """묶음마다 따로 찾는다: 한 묶음의 한 자리를 못 찾으면 그 묶음만 통째로 버리고(반쪽 묶음은 없다) 나머지 묶음은 그대로 찾는다."""
    found, why, _ = toybox.more_of(lib, toybox_fake_exe.sig_image(more_sigs, broken={3 * item, 3 * item + 1}))
    assert found == more_without(group)
    assert [bool(text) for text in why] == [g == group for g in range(3)]
    assert label in why[group] and "3개 가운데 1개" in why[group]


def test_more_signatures_that_disagree_drop_that_group(lib, more_sigs):
    """셋이 모두 맞았는데 하나가 다른 자리를 낸다 — 다수결로 고르지 않는다(틀린 칸에 쓰느니 쓰지 않는다)."""
    found, why, _ = toybox.more_of(lib, toybox_fake_exe.sig_image(more_sigs, stray={13}))      # 관계 표 1 의 둘째 서명
    assert found == more_without(2)
    assert why[:2] == ["", ""] and "관계 표 1" in why[2] and "서로 다른 값" in why[2]


@pytest.mark.parametrize("targets, dropped, reason", [
    ({"tech": 0x3122}, [0], "기술 수준 칸: 찾은 자리가 4 의 배수가 아닙니다"),
    ({"opinion1": 0}, [1], "여론 칸 2: 찾은 자리가 범위 밖입니다"),
    ({"casus": 0xFFFFC}, [2], "전쟁 명분 표: 찾은 자리가 범위 밖입니다"),                    # 표의 끝이 범위를 넘는다
    ({"opinion2": 0x3004}, [1], "여론 칸 3: 찾은 자리가 여론 칸 1 의 자리와 겹칩니다"),       # 세 칸은 서로 달라야 한다
    ({"relation1": 0x4800}, [2], "관계 표 2: 찾은 자리가 관계 표 1 의 자리와 겹칩니다"),      # 표 하나는 4바이트 × 1024칸이다
    ({"tech": 0x4010}, [0, 2], "관계 표 1: 찾은 자리가 기술 수준 칸 의 자리와 겹칩니다"),     # 어느 쪽이 틀렸는지 모른다 — 둘 다 버린다
], ids=["unaligned", "zero", "table-runs-out", "same-cell", "tables-too-close", "cell-inside-a-table"])
def test_more_that_does_not_add_up_is_dropped(lib, more_sigs, targets, dropped, reason):
    """서명들이 서로 맞아도 읽어 낸 자리가 말이 안 되면 그 묶음은 못 찾은 것이다."""
    found, why, _ = toybox.more_of(lib, toybox_fake_exe.sig_image(more_sigs, targets=targets))
    expected = {**toybox_fake_exe.MORE, **targets}
    for group in dropped:
        expected.update(dict.fromkeys(toybox.MORE_GROUPS[group][1], 0))
    assert found == expected
    assert [text for text in why if text] == [reason] * len(dropped) and [bool(text) for text in why] == [g in dropped for g in range(3)]


def test_more_must_not_sit_on_the_treasury_or_a_stock_slot(lib, more_sigs):
    """값 묶음(돈 · 물자)을 찾았으면 그 칸들과 겹치는 새 묶음은 버린다 — 둘 가운데 하나는 엉뚱한 것을 읽었다. 값 묶음은 그대로 둔다."""
    targets = {"tech": 0x1234, "opinion0": 0x2040}         # 국고 칸(0x1230, 8바이트)의 뒤쪽 절반 / 재고의 셋째 칸
    image = toybox_fake_exe.sig_image(more_sigs, targets=targets)
    found, why, _ = toybox.more_of(lib, image)
    assert found == {**toybox_fake_exe.MORE, **targets} and why == ["", "", ""]      # 값 묶음을 모르면 저마다는 말이 된다
    found, why, _ = toybox.more_of(lib, image, toybox_fake_exe.VALUE_LAYOUT)
    assert found == {**more_without(0), **dict.fromkeys(toybox.MORE_GROUPS[1][1], 0)}
    assert why == ["기술 수준 칸: 찾은 자리가 국고 칸이나 재고 칸과 겹칩니다", "여론 칸 1: 찾은 자리가 국고 칸이나 재고 칸과 겹칩니다", ""]
    assert toybox.more_of(lib, toybox_fake_exe.sig_image(more_sigs), toybox_fake_exe.VALUE_LAYOUT)[1] == ["", "", ""]


def test_more_is_found_beside_the_other_tables(lib, sigs, value_sigs, more_sigs):
    """세 서명 표가 한 이미지에 있어도 저마다 찾는다(서명이 서로의 자리에 맞지 않는다)."""
    image = toybox_fake_exe.sig_image(sigs + value_sigs + more_sigs)
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE
    assert toybox.values_of(lib, image)[0] == toybox_fake_exe.VALUE_LAYOUT
    assert toybox.more_of(lib, image, toybox_fake_exe.VALUE_LAYOUT)[:2] == (toybox_fake_exe.MORE, ["", "", ""])


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_more_survives_garbage(lib, image):
    found, why, _ = toybox.more_of(lib, image)
    assert found == dict.fromkeys(toybox.MORE_FIELDS, 0) and all(why)


def test_more_on_the_installed_game(lib, game_dir):
    """build 21347933: 서명 21개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 자리가 docs/11 의 표와 같다."""
    found, why, rows = toybox.more_of(lib, installed_image(game_dir), BUILD_VALUES)
    assert found == BUILD_MORE and why == ["", "", ""]
    assert [row.count for row in rows] == [1] * 21
    assert all(row.value == BUILD_MORE[row.name] for row in rows)


def test_more_agrees_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 서명으로 읽은 자리 == 치트 finalexam · shelovesme · love · neutral 의 본문이 쓰는 자리."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    assert toybox.more_of(lib, image)[0] == oracle.more(image)


```

`tests/test_toybox_game.py` 에서 다음 바로 뒤에:

```python
    assert located.legacy is not None and set(located.legacy) == set(toybox.LEGACY_FIELDS), located.legacy_why
```

이것을 더한다:

```python
    assert set(located.more) == set(toybox.MORE_FIELDS) and all(located.more.values()) and located.more_why == ["", "", ""]
    assert len(located.more_rows) == 21
```

`tests/toybox_cheat_oracle.py` 에서 다음 바로 앞에:

```python
pytest 가 직접 모으는 테스트 파일이 아니다(tests/test_toybox_game.py 가 쓴다).
```

이것을 더한다:

```python
(3단계 2 의 "더 쓰는 값"은 치트 finalexam · shelovesme · love · neutral 의 본문과 댄다.)
```

`tests/toybox_cheat_oracle.py` 에서 다음 바로 뒤에:

```python
    out["slots"] = len(stock)
```

이것을 더한다:

```python
    return out


def _body(image: sigmine.Image, text: str) -> bytes:
    """그 치트의 본문: 치트 문자열을 쓰는 자리부터, 글이 다를 때 건너뛰는 곳(다음 치트)까지."""
    use = _uses(image, text)[0]
    skip = re.search(rb"\x85\xc0(?:\x0f\x84(....)|\x75(.))", image.data[use:use + 0x20], re.S)     # test eax,eax / je(먼) · jne(가까운) <다음 치트>
    jump = struct.unpack("<i", skip.group(1))[0] if skip.group(1) is not None else struct.unpack("<b", skip.group(2))[0]
    return image.data[use:use + skip.end() + jump]


def _relation_writes(body: bytes) -> dict[str, list[int]]:
    """love · neutral 의 본문이 쓰는 칸(표의 첫 칸): 플레이어 객체 쪽(mine)과 그 나라 객체 쪽(theirs), 1.0 을 쓰는 것과 0 을 쓰는 것."""
    def found(pattern: bytes) -> list[int]:
        return sorted(struct.unpack("<I", d)[0] for d in re.findall(pattern, body, re.S))

    return {"mine_one": found(rb"\xc7\x84\x88(....)\x00\x00\x80\x3f"),                          # mov dword ptr [rax+rcx*4+표],1.0
            "mine_zero": found(rb"\x44\x89\xb4\x88(....)"),                                      # mov [rax+rcx*4+표],r14d (0)
            "theirs_one": found(rb"\xc7\x84\x82(....)\x00\x00\x80\x3f"),                        # mov dword ptr [rdx+rax*4+표],1.0
            "theirs_zero": found(rb"\x44\x89\xb4\x82(....)")}                                    # mov [rdx+rax*4+표],r14d


def more(image_bytes: bytes) -> dict[str, int]:
    """더 쓰는 값의 자리 일곱 — 치트 finalexam · shelovesme · love 의 본문에서 읽은 것. neutral 이 love 와 같은 여섯 칸을 쓰는지도 본다."""
    image = sigmine.Image(image_bytes)
    data = image.data
    out = {}
    at = _after(image, "cheat finalexam", 0x40,
                rb"\xf3\x0f\x10\x80(....)\xf3\x0f\x58\x05....\xf3\x0f\x11\x80\1")              # movss xmm0,[rax+칸] / addss xmm0,[1.0] / movss [rax+칸],xmm0
    out["tech"] = struct.unpack_from("<I", data, at + 4)[0]
    cells = sorted(struct.unpack("<I", d)[0]                                                    # mov dword ptr [rax+칸],1.0 셋
                   for d in re.findall(rb"\xc7\x80(....)\x00\x00\x80\x3f", _body(image, "cheat shelovesme"), re.S))
    assert len(cells) == 3, cells
    out["opinion0"], out["opinion1"], out["opinion2"] = cells
    love, neutral = _relation_writes(_body(image, "cheat love")), _relation_writes(_body(image, "cheat neutral"))
    assert love["mine_one"] == love["theirs_one"] and len(love["mine_one"]) == 2, love          # 관계 표 둘에 1.0 — 양쪽 객체에
    assert love["mine_zero"] == love["theirs_zero"] and len(love["mine_zero"]) == 1, love       # 전쟁 명분 표에 0
    six = sorted(love["mine_one"] + love["mine_zero"])
    assert neutral == {"mine_one": [], "mine_zero": six, "theirs_one": [], "theirs_zero": six}, neutral   # 중립은 같은 칸들에 0
    out["relation0"], out["relation1"] = love["mine_one"]
    out["casus"] = love["mine_zero"][0]
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음과 값 묶음)과, 옛 찾기가 보는
```

이렇게 바꾼다:

```python
게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음, 값 묶음, 더 쓰는 값)과, 옛 찾기가 보는
```

`tests/toybox_fake_exe.py` 에서 다음 바로 앞에:

```python
PLANT, AGAIN = TEXT + 0x1000, TEXT + 0x1800     # 서명을 심는 곳, 같은 서명을 한 번 더 심는 곳
```

이것을 더한다:

```python
# 새 찾기(더 쓰는 값)의 가짜 자리 — 지역 객체 안의 자리다(이미지 안이 아니다). 표 셋은 저마다 0x1000(4바이트 × 1024칸)을 차지한다
MORE = {"tech": 0x3120, "opinion0": 0x3004, "opinion1": 0x3008, "opinion2": 0x3020, "relation0": 0x4000, "relation1": 0x5000,
        "casus": 0x6000}
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
    targets 로 가짜 주소 · 값을 바꾼다(STATE 와 VALUES 의 이름으로).
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **(targets or {})}
```

이렇게 바꾼다:

```python
    targets 로 가짜 주소 · 값을 바꾼다(STATE · VALUES · MORE 의 이름으로).
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **MORE, **(targets or {})}
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -4`

Expected: `9 failed, 80 passed, 21 errors` — 새 테스트가 `AttributeError: module 'srkit.toybox' has no attribute 'more_of'` 로 실패하거나(픽스처 `more_sigs` 를 쓰는 것은 오류), `test_srkit_locate_reports_every_search` 가 `'Located' object has no attribute 'more'` 로 실패한다. 이미 있던 나머지 테스트는 그대로 통과한다.

- [ ] **Step 3: 구현한다**

`vote_table` 을 둘로 나눈다 — 서명을 한 번 맞추는 `scan_table` 과 찾을 것 하나를 투표하는 `vote_item`. 상태 · 값 묶음은 지금처럼 "하나라도 못 찾으면 전부 실패"이고(`vote_table`), 새 표는 한 번 맞춘 뒤 묶음마다 따로 판정한다(`search_more`).

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
// 두 묶음의 대조(locate_fits). 0 이면 맞는다. -1 이면 error 에 까닭.
```

이것을 더한다:

```cpp
// 새 찾기(더 쓰는 값 — 묶음 셋). 돌려주는 값은 찾은 묶음의 비트(1 지식, 2 여론, 4 관계). values 는 값 묶음(찾았을 때)이거나 nullptr.
// error 에는 묶음마다 한 줄(지식 · 여론 · 관계 순. 찾은 묶음은 빈 줄). rows 는 srtoybox_locate_state 와 같다.
EXPORT int srtoybox_locate_more(const unsigned char *image, unsigned long long size, const ValueLayout *values, MoreLayout *out,
                                char *error, int error_size, char *rows, int rows_size)
{
    MoreLayout found = {};
    SigRow table[MORE_WANTED * STATE_SIGS];
    char why[MORE_GROUPS][MORE_WHY] = {};
    const int groups = locate_more(image, static_cast<size_t>(size), values, &found, table, why);
    if (rows != nullptr)
        put(rows_text(table, MORE_WANTED * STATE_SIGS), rows, rows_size);
    std::string all;
    for (int g = 0; g < MORE_GROUPS; g++)
        all += std::string(why[g]) + '\n';
    put(all, error, error_size);
    if (out != nullptr)
        *out = found;
    return groups;
}

```

`native/srtoybox/locate.cpp` 에서 다음 바로 뒤에:

```cpp
#include <cstring>
```

이것을 더한다:

```cpp
#include <initializer_list>
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개)
static_assert(VALUE_WANTED <= STATE_WANTED, "vote_table 의 배열은 상태 묶음의 크기로 잡았다 — 더 큰 표를 더하면 MAX_TABLE 을 키운다");
```

이렇게 바꾼다:

```cpp
// 더 쓰는 값의 자리 일곱 — 기능마다 한 묶음이다(group: 0 지식, 1 여론, 2 관계). 같은 규칙으로 뽑았다
// (uv run srkit sig-mine --offset <자리>). 표의 서명은 모두 "지역 객체 + 인덱스 × 4 + 자리" 꼴의 명령에서 읽는다.
const struct MoreWanted {
    const char *name;                       // srkit locate 와 테스트가 본다(MoreLayout 의 필드 순서와 같다)
    const char *label;                      // 로그와 창에 나오는 이름
    int group;
    uint32_t bytes;                         // 그 자리부터 차지하는 크기: 칸은 4, 표는 4 × REGION_SLOTS
    const char *sigs[STATE_SIGS];
} MORE[MORE_WANTED] = {
    {"tech", "기술 수준 칸", 0, 4,
     {"F3 0F 2C 88 [u32] 41 3B C8 7E 4A", "F3 0F 2C 87 [u32] 83 E8 0F 3B C8", "48 05 [u32] F3 0F 2C 00 05 6C 07 00 00"}},
    {"opinion0", "여론 칸 1", 1, 4,
     {"F3 0F 58 B0 [u32] 48 85 D2 74 48", "F3 0F 10 89 [u32] 44 0F 2F D1 76 18", "F3 0F 59 8B [u32] F3 0F 58 C8 0F 2F F1"}},
    {"opinion1", "여론 칸 2", 1, 4,
     {"F3 0F 10 88 [u32] 0F 2F CB 76 5D", "F3 0F 10 8F [u32] 0F 2E CE 7A 14", "F3 0F 59 8B [u32] F3 0F 58 C8 0F 28 C2"}},
    {"opinion2", "여론 칸 3", 1, 4,
     {"F3 0F 10 B0 [u32] 48 85 D2 74 43", "F3 0F 10 8A [u32] 0F 2F F9 76 2E", "F3 0F 10 81 [u32] 48 8D 44 24 70 F3 0F 5C C1"}},
    {"relation0", "관계 표 1", 2, 4 * REGION_SLOTS,
     {"41 0F 2F 84 8D [u32] 76 0D 40 B6 01", "F3 42 0F 10 9C 82 [u32] 0F 2F FB 76 33", "F3 0F 10 84 81 [u32] 41 0F 2F C6 76 5F"}},
    {"relation1", "관계 표 2", 2, 4 * REGION_SLOTS,
     {"41 0F 2F 84 84 [u32] 76 7A 48 85 D2", "F3 0F 11 84 88 [u32] 45 85 DB 79 2A", "F3 0F 10 9C 81 [u32] 8B D0 0F 2F FB"}},
    {"casus", "전쟁 명분 표", 2, 4 * REGION_SLOTS,
     {"F3 0F 10 9C 8A [u32] 0F 2F FB 76 35", "F3 41 0F 5C 8C 82 [u32] 0F 2F C1 76 02", "F3 0F 11 84 88 [u32] 0F 28 C2 48 8B 07"}},
};

const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개, 더 쓰는 값 21개)
static_assert(VALUE_WANTED <= STATE_WANTED && MORE_WANTED <= STATE_WANTED,
              "서명을 맞추는 배열은 상태 묶음의 크기로 잡았다 — 더 큰 표를 더하면 MAX_TABLE 을 키운다");
static_assert(sizeof(MoreLayout) == MORE_WANTED * sizeof(uint32_t), "MoreLayout 의 필드는 표 MORE 의 순서대로 uint32_t 일곱이다");
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
// 서명 표 하나(찾을 것 n 개 × 서명 STATE_SIGS 개)를 실행 구역에 한 번 훑어 맞추고, 찾을 것마다 투표한다.
// values: n 줄 × SIG_CAPTURES 칸(0 으로 채워서 준다). 못 찾으면 false 와 why. what 은 서명이 읽어 내는 것("주소를" · "값을").
template <class Row>
bool vote_table(const Image &im, const Row *table, int n, const char *what, SigRow *rows, uint64_t (*values)[SIG_CAPTURES],
                char *why, size_t why_size)
```

이렇게 바꾼다:

```cpp
// 서명 표 하나(찾을 것 n 개 × 서명 STATE_SIGS 개)를 실행 구역에 한 번 훑어 맞춘다. sigs · hits 는 MAX_TABLE 칸.
// 표가 틀렸으면 false 와 why.
template <class Row>
bool scan_table(const Image &im, const Row *table, int n, SigRow *rows, Sig *sigs, SigHit *hits, char *why, size_t why_size)
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
        }
    Sig sigs[MAX_TABLE];
    SigHit hits[MAX_TABLE];
```

이렇게 바꾼다:

```cpp
        }
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
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
```

이렇게 바꾼다:

```cpp
    return true;
}

// 찾을 것 하나(표의 w 째)의 투표. value 는 SIG_CAPTURES 칸. 못 찾으면 false 와 why. what 은 서명이 읽어 내는 것("주소를" · "값을").
template <class Row>
bool vote_item(const Row *table, int w, const char *what, const Sig *sigs, const SigHit *hits, uint64_t *value, char *why,
               size_t why_size)
{
    int matched = 0;
    if (sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, STATE_NEED, value, &matched))
        return true;
    if (matched >= STATE_NEED)
        snprintf(why, why_size, "%s: 서명들이 서로 다른 %s 냅니다", table[w].label, what);
    else
        snprintf(why, why_size, "%s: 서명 %d개 가운데 %d개", table[w].label, STATE_SIGS, matched);
    return false;
}

// 서명 표 하나를 맞추고 찾을 것마다 투표한다 — 하나라도 못 찾으면 false 와 why.
// values: n 줄 × SIG_CAPTURES 칸(0 으로 채워서 준다).
template <class Row>
bool vote_table(const Image &im, const Row *table, int n, const char *what, SigRow *rows, uint64_t (*values)[SIG_CAPTURES],
                char *why, size_t why_size)
{
    Sig sigs[MAX_TABLE];
    SigHit hits[MAX_TABLE];
    if (!scan_table(im, table, n, rows, sigs, hits, why, why_size))
        return false;
    for (int w = 0; w < n; w++)
        if (!vote_item(table, w, what, sigs, hits, values[w], why, why_size))
            return false;
```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
// 서명마다의 결과 칸에 이름과 글을 채운다 — 찾기 전에. 머리말조차 못 읽은 이미지에서도 서명 표를 볼 수 있다(테스트와 srkit locate 가 쓴다).
```

이것을 더한다:

```cpp
// [a, a + a_bytes) 와 [b, b + b_bytes) 가 겹치는가.
bool overlap(uint64_t a, uint64_t a_bytes, uint64_t b, uint64_t b_bytes)
{
    return a < b + b_bytes && b < a + a_bytes;
}

// 더 쓰는 값: 서명은 한 번에 맞추고, 묶음마다 따로 판정한다.
int search_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY])
{
    Image im = {};
    im.p = image;
    im.size = size;
    char broken[MORE_WHY] = "";
    Sig sigs[MAX_TABLE];
    SigHit hits[MAX_TABLE];
    if (image == nullptr || !parse(im))
        snprintf(broken, sizeof(broken), "실행 파일의 머리말을 읽을 수 없습니다");
    if (broken[0] != '\0' || !scan_table(im, MORE, MORE_WANTED, rows, sigs, hits, broken, sizeof(broken))) {
        for (int g = 0; g < MORE_GROUPS; g++)
            snprintf(why[g], MORE_WHY, "%s", broken);
        return 0;
    }
    uint64_t at[MORE_WANTED] = {};              // 저마다 찾은 자리. 못 찾았으면 0
    bool ok[MORE_GROUPS];
    for (int g = 0; g < MORE_GROUPS; g++) {
        ok[g] = true;
        why[g][0] = '\0';
    }
    for (int w = 0; w < MORE_WANTED; w++) {
        uint64_t value[SIG_CAPTURES] = {};
        char one[MORE_WHY] = "";
        bool good = vote_item(MORE, w, "값을", sigs, hits, value, one, sizeof(one));
        if (good && (!offset_ok(value[0]) || !offset_ok(value[0] + MORE[w].bytes))) {
            snprintf(one, sizeof(one), "%s: 찾은 자리가 범위 밖입니다", MORE[w].label);
            good = false;
        }
        if (good && value[0] % 4 != 0) {        // 칸이 float 다
            snprintf(one, sizeof(one), "%s: 찾은 자리가 4 의 배수가 아닙니다", MORE[w].label);
            good = false;
        }
        if (good) {
            at[w] = value[0];
        } else if (ok[MORE[w].group]) {         // 묶음의 까닭은 처음 것만 남긴다
            ok[MORE[w].group] = false;
            snprintf(why[MORE[w].group], MORE_WHY, "%s", one);
        }
    }
    // 저마다는 말이 되어도 서로 겹치면 어느 한쪽이 엉뚱한 것을 읽은 것이다 — 어느 쪽인지 모르므로 두 묶음 다 버린다
    for (int w = 0; w < MORE_WANTED; w++)
        for (int v = 0; v < w; v++) {
            if (at[w] == 0 || at[v] == 0 || !overlap(at[w], MORE[w].bytes, at[v], MORE[v].bytes))
                continue;
            for (int g : {MORE[w].group, MORE[v].group})
                if (ok[g]) {
                    ok[g] = false;
                    snprintf(why[g], MORE_WHY, "%s: 찾은 자리가 %s 의 자리와 겹칩니다", MORE[w].label, MORE[v].label);
                }
        }
    if (values != nullptr)                      // 값 묶음(돈 · 물자)을 찾았으면 그 칸들과도 겹치면 안 된다 — 새 묶음을 버린다
        for (int w = 0; w < MORE_WANTED; w++) {
            if (at[w] == 0)
                continue;
            bool hit = overlap(at[w], MORE[w].bytes, values->treasury, 8);
            for (int i = 0; i < STOCK_SLOTS && !hit; i++)
                hit = overlap(at[w], MORE[w].bytes, values->stock_first + static_cast<uint64_t>(values->stock_step) * static_cast<uint64_t>(i), 4);
            if (hit && ok[MORE[w].group]) {
                ok[MORE[w].group] = false;
                snprintf(why[MORE[w].group], MORE_WHY, "%s: 찾은 자리가 국고 칸이나 재고 칸과 겹칩니다", MORE[w].label);
            }
        }
    uint32_t found[MORE_WANTED] = {};
    int groups = 0;
    for (int w = 0; w < MORE_WANTED; w++)
        if (ok[MORE[w].group]) {
            found[w] = static_cast<uint32_t>(at[w]);
            groups |= 1 << MORE[w].group;
        }
    memcpy(out, found, sizeof(found));
    return groups;
}

```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search_legacy · search_state · search_values)과 따로 뗐다.
```

이렇게 바꾼다:

```cpp
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search_legacy · search_state · search_values · search_more)과 따로 뗐다.
```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size)
```

이것을 더한다:

```cpp
int locate_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY])
{
    name_rows(MORE, MORE_WANTED, rows);
    *out = MoreLayout();
    __try {
        return search_more(image, size, values, out, rows, why);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        *out = MoreLayout();
        for (int g = 0; g < MORE_GROUPS; g++)
            snprintf(why[g], MORE_WHY, "실행 파일에 읽을 수 없는 곳이 있습니다");
        return 0;
    }
}

```

`native/srtoybox/locate.h` 에서 다음 바로 앞에:

```cpp
//   옛 찾기 locate_legacy  치트 명령 처리 함수와 그 둘레의 셋. "cheat allowcheats" 문자열을 닻으로. 아직 내장 치트로 도는
```

이것을 더한다:

```cpp
//           locate_more    더 쓰는 값의 자리(기술 수준, 세계 시장 여론, 관계). 기능마다 한 묶음 — 따로 찾고 따로 실패한다.
```

`native/srtoybox/locate.h` 에서 다음 바로 앞에:

```cpp
// 옛 찾기(전환 기간에만): 찾으면 nullptr 과 out 의 handler · context · options(다른 필드는 건드리지 않는다).
```

이것을 더한다:

```cpp
// 더 쓰는 값(3단계 2): 모두 지역 객체 안의 자리(float)다. 필드는 서명 표의 순서대로 uint32_t 일곱이다.
struct MoreLayout {
    uint32_t tech;             // [지식] 기술 수준
    uint32_t opinion[3];       // [여론] 세계 시장 여론과 그 둘레의 세 칸
    uint32_t relation[2];      // [관계] 지역 인덱스로 찾는 표 둘의 첫 칸: 그 지역과의 관계(-1 … 1)
    uint32_t casus;            // [관계] 같은 꼴의 표: 그 지역에 대한 전쟁 명분(0 … 1)
};

const int MORE_TECH = 1, MORE_OPINION = 2, MORE_RELATIONS = 4;   // 묶음의 비트
const int MORE_GROUPS = 3;      // 묶음의 수(지식 · 여론 · 관계 순)
const int MORE_WANTED = 7;      // 찾을 것의 수: 기술 수준 칸, 여론 칸 셋, 관계 표 둘, 전쟁 명분 표
const int REGION_SLOTS = 1024;  // 지역 표의 칸 수 = 관계 표 하나의 칸 수
const size_t MORE_WHY = 160;    // 까닭 한 줄의 크기

// 새 찾기(더 쓰는 값): 서명의 규칙은 locate_state 와 같다. 돌려주는 값은 찾은 묶음의 비트다 — 찾은 묶음의 필드만 채우고
// 못 찾은 묶음의 필드는 0 으로 둔다. 한 묶음은 그 안의 것을 모두 찾아야 찾은 것이다(반쪽 묶음은 없다).
// why 는 MORE_GROUPS 줄: 못 찾은 묶음의 까닭(UTF-8). 찾은 묶음은 빈 글.
// 읽어 낸 자리가 말이 되는지도 본다: 0 보다 크고 0x100000 보다 작은 4 의 배수, 칸(4바이트)과 표(4바이트 × REGION_SLOTS)가
// 서로 겹치지 않는다 — 겹치면 어느 쪽이 엉뚱한 것을 읽었는지 모르므로 두 묶음 다 버린다.
// values 를 주면(값 묶음을 찾았을 때) 국고 칸 · 재고 칸들과 겹치는 묶음도 버린다(값 묶음은 그대로 둔다).
// rows: MORE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
int locate_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY]);

```

`src/srkit/cli.py` 에서 다음 바로 앞에:

```python
    print("옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):")
```

이것을 더한다:

```python
    print("새 찾기 — 더 쓰는 값(서명. 기능마다 한 묶음 — 따로 찾고 따로 꺼진다. 모두 지역 객체 안의 자리):")
    _print_sig_rows(found.more_rows)
    for (group, fields), why in zip(toybox.MORE_GROUPS, found.more_why):
        if why:
            print(f"  {group}: 찾지 못했습니다: {why}")
        else:
            for name in fields:
                print(f"  {found.more[name]:#010x}  {toybox.MORE_NAMES[name]}")
    if any(found.more_why):
        print("ToyBox 에서 그 묶음의 단추만 꺼집니다. uv run srkit sig-mine --offset 으로 서명을 다시 뽑습니다(docs/11).")
```

`src/srkit/cli.py` 에서 다음을 찾아:

```python
    if found.state is not None and found.values is not None and found.legacy is not None:
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if found.state is not None and found.values is not None else 1
```

이렇게 바꾼다:

```python
    if found.state is not None and found.values is not None and found.legacy is not None and not any(found.more_why):
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if found.state is not None and found.values is not None and not any(found.more_why) else 1
```

`src/srkit/toybox.py` 에서 다음 바로 뒤에:

```python
STOCK_SLOTS = 12        # 재고의 칸 수(native/srtoybox/locate.h 의 STOCK_SLOTS)
```

이것을 더한다:

```python
# 새 찾기(서명)가 채우는 "더 쓰는 값" — native/srtoybox/locate.h 의 MoreLayout 과 같은 순서다. 모두 지역 객체 안의 자리(float)
MORE_FIELDS = ["tech", "opinion0", "opinion1", "opinion2", "relation0", "relation1", "casus"]
MORE_NAMES = {"tech": "기술 수준 칸", "opinion0": "세계 시장 여론의 칸 1", "opinion1": "세계 시장 여론의 칸 2",
              "opinion2": "세계 시장 여론의 칸 3", "relation0": "관계 표 1 의 첫 칸(지역 인덱스 × 4 를 더한다)",
              "relation1": "관계 표 2 의 첫 칸", "casus": "전쟁 명분 표의 첫 칸"}
# 묶음: 기능마다 따로 찾고 따로 꺼진다 — (이름, 그 묶음의 필드들). locate.h 의 MORE_TECH · MORE_OPINION · MORE_RELATIONS 순서다
MORE_GROUPS = [("기술 수준", ["tech"]), ("세계 시장 여론", ["opinion0", "opinion1", "opinion2"]),
               ("관계", ["relation0", "relation1", "casus"])]
```

`src/srkit/toybox.py` 에서 다음 바로 뒤에:

```python
    legacy_why: str
```

이것을 더한다:

```python
    more: dict[str, int]             # 새 찾기(서명): 더 쓰는 값. 못 찾은 묶음의 자리는 0
    more_why: list[str]              # 묶음마다(MORE_GROUPS 순서)의 까닭. 찾았으면 빈 글
    more_rows: list[SigRow]
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def output(cfg: Config) -> Path:
```

이것을 더한다:

```python
class MoreLayout(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in MORE_FIELDS]


```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
    lib.srtoybox_function_root.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint]
```

이것을 더한다:

```python
    lib.srtoybox_locate_more.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(ValueLayout), ctypes.POINTER(MoreLayout),
                                         ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def legacy_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str]:
```

이것을 더한다:

```python
def more_of(lib: ctypes.CDLL, image: bytes, values: dict[str, int] | None = None) -> tuple[dict[str, int], list[str], list[SigRow]]:
    """새 찾기(더 쓰는 값)를 그 이미지에 돌린다: (이름 → 자리 — 못 찾은 묶음의 것은 0, 묶음마다의 까닭 — 찾았으면 빈 글, 서명마다의 결과).

    values 는 값 묶음(찾았을 때)이다 — 그 칸들과 겹치는 묶음은 못 찾은 것이 된다.
    """
    found, error, rows = MoreLayout(), ctypes.create_string_buffer(1024), ctypes.create_string_buffer(8192)
    lib.srtoybox_locate_more(image, len(image), ctypes.byref(ValueLayout(**values)) if values else None, ctypes.byref(found),
                             error, len(error), rows, len(rows))
    why = error.value.decode("utf-8").split("\n")[:len(MORE_GROUPS)]
    return {name: getattr(found, name) for name in MORE_FIELDS}, why, _sig_rows(rows.value)


```

`src/srkit/toybox.py` 에서 다음을 찾아:

```python
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why)
```

이렇게 바꾼다:

```python
    more, more_why, more_rows = more_of(lib, image, values)
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why, more, more_why, more_rows)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `110 passed`

Run: `PYTHONIOENCODING=utf-8 uv run srkit locate | tail -13`

Expected(설치된 게임이 build 21347933 일 때):

```
  0x00014cd0  기술 수준 칸
  0x00014af4  세계 시장 여론의 칸 1
  0x00014af8  세계 시장 여론의 칸 2
  0x00014b10  세계 시장 여론의 칸 3
  0x00015f10  관계 표 1 의 첫 칸(지역 인덱스 × 4 를 더한다)
  0x00016f10  관계 표 2 의 첫 칸
  0x00017f10  전쟁 명분 표의 첫 칸
옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):
  0x00522330  명령 처리 함수
  0x01764310  그 함수의 첫 인자(전역 객체)
  0x01eb556c  옵션 묶음(dword, 0x40 = 치트 허용)
모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.
```

그 위에는 `새 찾기 — 더 쓰는 값(…)` 아래로 서명 21줄이 모두 `한 번` 이다.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/exports.cpp src/srkit/toybox.py src/srkit/cli.py tests/test_toybox_game.py tests/toybox_fake_exe.py tests/toybox_cheat_oracle.py && git commit -q -F - <<'EOF'
feat: ToyBox 새 찾기 — 기술 수준 · 세계 시장 여론 · 관계의 자리(묶음마다 따로)

- locate_more: 지역 객체 안의 자리 일곱을 치트와 무관한 서명 21개로 찾는다. 기능마다 한 묶음(지식 · 여론 · 관계)이고
  한 묶음을 못 찾아도 나머지는 찾는다. 반쪽 묶음은 없다.
- 읽어 낸 자리의 대조: 범위 · 4 의 배수 · 칸과 표(4바이트 × 1024칸)가 서로 겹치지 않는다(겹치면 두 묶음 다 버린다) ·
  값 묶음을 찾았으면 국고 칸 · 재고 칸과도 겹치지 않는다.
- vote_table 을 scan_table(한 번 맞추기) + vote_item(찾을 것 하나의 투표)으로 나눴다. 상태 · 값 묶음의 판정은 그대로다.
- srkit locate 가 새 묶음을 보인다. 테스트는 치트 finalexam · shelovesme · love · neutral 의 본문과 대조한다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `371 passed`, 새 커밋.

---

### Task 2: 읽기와 쓰기 — 기술 수준, 여론, 한 나라와의 관계

**브랜치:** `feat/toybox-values-more`

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/game.h`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_values.py`, `tests/toybox_fake_game.py`

**Interfaces:**
- Consumes: Task 1 의 `MoreLayout` · `locate_more` · `MORE_*` · `REGION_SLOTS` · `toybox.MoreLayout` · `toybox.more_of` · `toybox_fake_exe.MORE`. 묶음 1 의 `game.cpp` 안쪽 함수 `read_player` · `peek` · `peek_at` · `peek_in` · `peek_region` · `usable` · `in_play` · `writable` · `poke`, `region_label`(regions.h).
- Produces:
  - `int locate_more_group(int wanted)` — 서명 표의 `wanted` 째가 든 묶음(0 지식, 1 여론, 2 관계. 없으면 -1).
  - `struct GameMore { bool ok; float tech; float opinion[3]; }`, `struct Relation { bool ok; float mine[3]; float theirs[3]; }`(`[0]` `[1]` 관계 표 둘, `[2]` 전쟁 명분).
  - `Wrote::NoTarget`(값 6) — `Wrote` 의 끝에 더한다(앞의 값은 그대로다).
  - 순수 함수: `GameMore read_more(base, at, more)`, `Relation read_relation(base, at, more, int number)`, `Wrote write_tech(base, at, more, float value)`, `Wrote write_opinion(base, at, more, int *done)`, `Wrote write_relation(base, at, more, int number, float level, int *done)`.
  - 프로세스의 게임: `bool game_writes()`, `std::string game_more_off(int group)`(group 은 `MORE_TECH` · `MORE_OPINION` · `MORE_RELATIONS`), `GameMore game_more()`, `Relation game_relation(int number)`, `Wrote game_write_tech(float value)`, `Wrote game_write_opinion()`, `Wrote game_write_relation(int number, float level)`, `void game_set_more_for_test(const MoreLayout *layout)`.
  - 내보내기: `srtoybox_more_read(base, at, more, out, size)`, `srtoybox_relation_read(base, at, more, number, out, size)`, `srtoybox_more_write(base, at, more, what, number, value, int *done)`(what: 0 기술 수준, 1 여론, 2 관계), `srtoybox_test_more(const MoreLayout *)`, `srtoybox_more_off(group, out, size)`, `srtoybox_game_flags` 의 새 비트 8 · 16 · 32.
  - 테스트 도우미: `toybox_fake_game.MORE` · `RELATION_TABLES` · `OBJECT_SIZE`(0x1000), `FakeGame.more` · `tech` · `set_tech` · `opinion` · `set_opinion` · `relation(index, other)` · `set_relation`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

가짜 게임에 새 칸을 더하고(지역 객체가 0x1000 바이트가 된다 — 관계 표가 지역 인덱스로 찾는 표다), 읽기 · 쓰기 · 시작할 때의 찾기를 테스트한다. 쓰기의 테스트는 "그 칸만 바뀐다"를 바이트로 본다.

<!-- 고칠 곳: test -->
`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
from toybox_fake_game import LAYOUT, MULTIPLAYER, OPTIONS, POINTER, TABLE, WORLD_POINTER, FakeGame
```

이렇게 바꾼다:

```python
from toybox_fake_game import LAYOUT, MORE, MULTIPLAYER, OBJECT_SIZE, OPTIONS, POINTER, RELATION_TABLES, TABLE, WORLD_POINTER, FakeGame
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF = range(6)      # native/srtoybox/game.h 의 Wrote
TREASURY, ALL_STOCK = -1, -2                                        # 쓰기의 대상: 국고 / 쓰는 물자 모두. 0 … 11 은 그 칸의 재고
READS, CALLS, WRITES = 1, 2, 4                                      # srtoybox_game_flags 의 비트
```

이렇게 바꾼다:

```python
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF, NO_TARGET = range(7)   # native/srtoybox/game.h 의 Wrote
TREASURY, ALL_STOCK = -1, -2                                        # 쓰기의 대상: 국고 / 쓰는 물자 모두. 0 … 11 은 그 칸의 재고
READS, CALLS, WRITES = 1, 2, 4                                      # srtoybox_game_flags 의 비트
CAN_TECH, CAN_OPINION, CAN_RELATIONS = 8, 16, 32                    # 〃 더 쓰는 값의 묶음마다
TECH_TO, OPINION_BEST, RELATION_TO = 0, 1, 2                        # srtoybox_more_write 의 what
MORE_TECH, MORE_OPINION, MORE_RELATIONS = 1, 2, 4                   # native/srtoybox/locate.h 의 묶음의 비트
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
    lib.srtoybox_test_init.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong]
```

이것을 더한다:

```python
    lib.srtoybox_more_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.MoreLayout), ctypes.c_char_p,
                                       ctypes.c_int]
    lib.srtoybox_relation_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.MoreLayout), ctypes.c_int,
                                           ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_more_write.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.MoreLayout), ctypes.c_int,
                                        ctypes.c_int, ctypes.c_double, pointer(ctypes.c_int)]
    lib.srtoybox_test_more.argtypes = [ctypes.c_void_p]
    lib.srtoybox_more_off.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 국고 $14.43 B. 물자 0 · 3 · 7 을 쓰고 재고가 1000 · 2500 · 0. 폴란드(141)의 국고는 $5 B."""
```

이렇게 바꾼다:

```python
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임. 국고 $14.43 B. 물자 0 · 3 · 7 을 쓰고 재고가 1000 · 2500 · 0. 폴란드(141)의 국고는 $5 B.

    기술 수준은 독일 130 · 폴란드 128, 독일의 여론 세 칸은 0.5 · 0.25 · 0.75, 독일 → 폴란드의 관계는 0.25 · -0.5(전쟁 명분 0.75),
    폴란드 → 독일은 0.125 · 0.5(전쟁 명분 1)."""
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
    for slot, amount in ((0, 1000.0), (3, 2500.0), (7, 0.0)):
```

이것을 더한다:

```python
    fake.set_tech(176, 130.0)
    fake.set_tech(141, 128.0)
    fake.set_opinion(176, (0.5, 0.25, 0.75))
    fake.set_relation(176, 141, (0.25, -0.5, 0.75))
    fake.set_relation(141, 176, (0.125, 0.5, 1.0))
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
    assert changed and set(changed) <= set(range(len(before) - 0x200 + LAYOUT["treasury"], len(before) - 0x200 + LAYOUT["treasury"] + 8))
```

이렇게 바꾼다:

```python
    assert changed and set(changed) <= set(range(len(before) - OBJECT_SIZE + LAYOUT["treasury"],
                                                 len(before) - OBJECT_SIZE + LAYOUT["treasury"] + 8))
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
    slot = len(before) - 0x200 + LAYOUT["stock_first"] + LAYOUT["stock_step"] * 3
```

이렇게 바꾼다:

```python
    slot = len(before) - OBJECT_SIZE + LAYOUT["stock_first"] + LAYOUT["stock_step"] * 3
```

`tests/test_toybox_values.py` 에서 다음 바로 뒤에:

```python
    assert fake.snapshot(176) == before


```

이것을 더한다:

```python
def more(lib, fake: FakeGame, layout: toybox.MoreLayout | None = None) -> dict[str, str]:
    out = ctypes.create_string_buffer(1024)
    assert lib.srtoybox_more_read(fake.base, ctypes.byref(fake.at), ctypes.byref(layout or fake.more), out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def relation(lib, fake: FakeGame, number: int) -> dict[str, str]:
    out = ctypes.create_string_buffer(1024)
    assert lib.srtoybox_relation_read(fake.base, ctypes.byref(fake.at), ctypes.byref(fake.more), number, out, len(out)) >= 0
    return dict(pair.split("=", 1) for pair in out.value.decode().split())


def write_more(lib, fake: FakeGame, what: int, number: int = 0, value: float = 0.0,
               layout: toybox.MoreLayout | None = None) -> tuple[int, int]:
    """(Wrote, 쓴 칸의 수)."""
    done = ctypes.c_int(-1)
    wrote = lib.srtoybox_more_write(fake.base, ctypes.byref(fake.at), ctypes.byref(layout or fake.more), what, number, value,
                                    ctypes.byref(done))
    return wrote, done.value


def where(fake: FakeGame, index: int, offset: int, size: int = 4) -> set[int]:
    """everything(fake) 안에서 그 지역 객체의 그 자리가 차지하는 바이트들."""
    start = len(fake.mem) + len(fake.world) + OBJECT_SIZE * sorted(fake.objects).index(index) + offset
    return set(range(start, start + size))


def changed(before: bytes, after: bytes) -> set[int]:
    return {i for i in range(len(before)) if before[i] != after[i]}


def with_denmark() -> FakeGame:
    """germany() 에 덴마크(인덱스 150, 번호 1201)를 더한 것. 독일 ↔ 덴마크, 폴란드 ↔ 덴마크의 관계도 0 이 아니다."""
    fake = germany()
    fake.region(150, 1201, alive=3)
    for a, b in ((176, 150), (150, 176), (141, 150), (150, 141)):
        fake.set_relation(a, b, (0.5, 0.5, 0.5))
    return fake


def test_more_is_read_from_the_players_region(lib):
    fake = germany()
    assert more(lib, fake) == {"ok": "1", "tech": "130", "opinion": "0.5,0.25,0.75"}
    assert relation(lib, fake, 1106) == {"ok": "1", "mine": "0.25,-0.5,0.75", "theirs": "0.125,0.5,1"}
    assert relation(lib, fake, 1499)["ok"] == "0" and relation(lib, fake, 9999)["ok"] == "0"      # 자기 자신, 없는 번호
    fake.menu()
    assert more(lib, fake)["ok"] == "0" and relation(lib, fake, 1106)["ok"] == "0"


def test_a_tech_write_changes_only_that_cell(lib):
    """쓰는 곳은 플레이어 지역 객체의 그 칸뿐이다. 둘레의 바이트 · 다른 지역 · 전역 · 치트 허용 비트는 그대로다."""
    fake = germany()
    before = everything(fake)
    assert write_more(lib, fake, TECH_TO, value=131.0) == (DONE, 1)
    assert fake.tech(176) == 131.0 and fake.tech(141) == 128.0
    assert changed(before, everything(fake)) <= where(fake, 176, MORE["tech"])
    assert fake.peek(OPTIONS, "<I") == 0


def test_an_opinion_write_changes_only_the_three_cells(lib):
    fake = germany()
    before = everything(fake)
    assert write_more(lib, fake, OPINION_BEST) == (DONE, 3)
    assert fake.opinion(176) == [1.0, 1.0, 1.0] and fake.opinion(141) == [0.0, 0.0, 0.0]
    cells = set().union(*(where(fake, 176, MORE[name]) for name in ("opinion0", "opinion1", "opinion2")))
    assert changed(before, everything(fake)) <= cells


def test_a_relation_write_changes_only_the_six_cells(lib):
    """관계는 치트처럼 양쪽에 쓴다: 플레이어 객체의 표 셋에서 그 나라의 칸, 그 나라 객체의 표 셋에서 플레이어의 칸.
    같은 표의 이웃 칸, 다른 나라와의 관계, 다른 나라의 객체는 그대로다."""
    fake = with_denmark()
    before = everything(fake)
    assert write_more(lib, fake, RELATION_TO, 1106, 1.0) == (DONE, 6)
    assert fake.relation(176, 141) == [1.0, 1.0, 0.0] and fake.relation(141, 176) == [1.0, 1.0, 0.0]   # 관계 둘은 최고, 전쟁 명분은 0
    six = set().union(*(where(fake, 176, MORE[name] + 4 * 141) | where(fake, 141, MORE[name] + 4 * 176) for name in RELATION_TABLES))
    assert changed(before, everything(fake)) <= six
    assert fake.relation(176, 150) == [0.5, 0.5, 0.5] and fake.relation(150, 176) == [0.5, 0.5, 0.5]
    assert write_more(lib, fake, RELATION_TO, 1106, 0.0) == (DONE, 6)                                  # 중립: 여섯 칸 모두 0
    assert fake.relation(176, 141) == [0.0, 0.0, 0.0] and fake.relation(141, 176) == [0.0, 0.0, 0.0]
    assert changed(before, everything(fake)) <= six and fake.peek(OPTIONS, "<I") == 0


@pytest.mark.parametrize("flaw", ["menu", "multiplayer", "inconsistent", "unreadable"])
def test_more_is_not_written_outside_a_game_it_can_trust(lib, flaw):
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
    assert write_more(lib, fake, TECH_TO, value=131.0) == (NOT_IN_GAME, 0)
    assert write_more(lib, fake, OPINION_BEST) == (NOT_IN_GAME, 0)
    assert write_more(lib, fake, RELATION_TO, 1106, 1.0) == (NOT_IN_GAME, 0)
    assert everything(fake) == before


@pytest.mark.parametrize("flaw", ["no-such-number", "self", "not-in-play", "inconsistent", "unreadable"])
def test_a_relation_is_written_only_with_a_country_that_is_in_this_game(lib, flaw):
    """고른 나라가 쓰기 직전에 없어졌거나(다른 판, 병합됨) 플레이어 자신이면 쓰지 않는다 — 엉뚱한 객체를 건드리지 않는다."""
    fake = with_denmark()
    number = 1106
    if flaw == "no-such-number":
        number = 9999
    elif flaw == "self":
        number = 1499
    elif flaw == "not-in-play":
        struct.pack_into("<I", fake.objects[141], 0, 5)                   # 사람도 AI 도 맡지 않은 지역이 됐다
    elif flaw == "inconsistent":
        struct.pack_into("<H", fake.objects[141], 4, 140)                 # 객체가 아는 자기 인덱스가 표에서의 자리와 다르다
    else:
        fake.poke(TABLE + 8 * 141, "<Q", 0x00007FFFFFFF0000)
    before = everything(fake)
    assert write_more(lib, fake, RELATION_TO, number, 1.0) == (NO_TARGET, 0)
    assert everything(fake) == before


def test_more_values_that_make_no_sense_are_not_written(lib):
    fake = germany()
    before = everything(fake)
    for value in (NAN, INF, -INF, -1.0):
        assert write_more(lib, fake, TECH_TO, value=value) == (BAD_VALUE, 0)
    for level in (NAN, INF, 1.5, -1.5):
        assert write_more(lib, fake, RELATION_TO, 1106, level) == (BAD_VALUE, 0)
    assert everything(fake) == before
    assert write_more(lib, fake, RELATION_TO, 1106, -1.0) == (DONE, 6)        # 범위의 끝은 된다(최저)


def test_a_group_whose_place_is_not_known_is_not_written(lib):
    """묶음마다 따로다: 못 찾은 묶음(자리 0)에는 쓰지 않고, 찾은 묶음은 그대로 쓴다."""
    fake = germany()
    before = everything(fake)
    assert write_more(lib, fake, TECH_TO, value=131.0, layout=toybox.MoreLayout(**{**MORE, "tech": 0})) == (OFF, 0)
    assert write_more(lib, fake, OPINION_BEST, layout=toybox.MoreLayout(**{**MORE, "opinion1": 0})) == (OFF, 0)
    assert write_more(lib, fake, RELATION_TO, 1106, 1.0, layout=toybox.MoreLayout(**{**MORE, "casus": 0})) == (OFF, 0)
    assert everything(fake) == before
    no_tech = toybox.MoreLayout(**{**MORE, "tech": 0})
    assert more(lib, fake, no_tech) == {"ok": "1", "tech": "0", "opinion": "0.5,0.25,0.75"}
    assert write_more(lib, fake, OPINION_BEST, layout=no_tech) == (DONE, 3)


@pytest.mark.parametrize("protection", [0x02, 0x20], ids=["read-only", "execute-read"])
def test_more_on_a_page_that_is_not_read_write_is_not_written(lib, protection):
    """쓸 수 없는 쪽이면 실패로 돌아온다. 여러 칸을 쓰는 것은 먼저 모든 칸을 보고 — 한 칸도 쓰지 않는다."""
    fake = germany()
    fake.lock(176, protection)
    fake.play(176)
    theirs = fake.snapshot(141)
    assert write_more(lib, fake, TECH_TO, value=131.0) == (FAILED, 0)
    assert write_more(lib, fake, OPINION_BEST) == (FAILED, 0)
    assert write_more(lib, fake, RELATION_TO, 1106, 1.0) == (FAILED, 0)
    assert fake.tech(176) == 130.0 and fake.snapshot(141) == theirs          # 폴란드 쪽 칸도 쓰지 않았다
    fake = germany()
    fake.lock(141, protection)                                                # 이번에는 고른 나라의 객체가 쓸 수 없는 쪽에 있다
    mine = fake.snapshot(176)
    assert write_more(lib, fake, RELATION_TO, 1106, 1.0) == (FAILED, 0)
    assert fake.snapshot(176) == mine                                         # 플레이어 쪽 칸도 쓰지 않았다


def test_more_follows_the_country_being_played(lib):
    """요구 2: 쓰는 것은 지금 플레이하는 나라의 값이다. 나라를 바꾸면 새 플레이어의 칸에 쓴다."""
    fake = with_denmark()
    fake.play(141)                                                            # 폴란드로 플레이한다
    assert write_more(lib, fake, TECH_TO, value=129.0) == (DONE, 1)
    assert write_more(lib, fake, OPINION_BEST) == (DONE, 3)
    assert fake.tech(141) == 129.0 and fake.tech(176) == 130.0
    assert fake.opinion(141) == [1.0, 1.0, 1.0] and fake.opinion(176) == [0.5, 0.25, 0.75]
    assert write_more(lib, fake, RELATION_TO, 1201, 1.0) == (DONE, 6)         # 폴란드 ↔ 덴마크
    assert fake.relation(141, 150) == [1.0, 1.0, 0.0] and fake.relation(150, 141) == [1.0, 1.0, 0.0]
    assert fake.relation(176, 150) == [0.5, 0.5, 0.5] and fake.relation(176, 141) == [0.25, -0.5, 0.75]   # 독일의 것은 그대로다


```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def test_startup_finds_the_state_and_the_values_without_any_cheat(lib, all_sigs, tmp_path, monkeypatch):
```

이것을 더한다:

```python
@pytest.fixture(scope="module")
def more_sigs(lib):
    """DLL 에 든 "더 쓰는 값"의 서명 21개 — (찾을 것, 서명 글)."""
    return [(row.name, row.text) for row in toybox.more_of(lib, b"")[2]]


def init_more(lib, image: bytes, tmp_path, monkeypatch) -> tuple[int, list[str], str]:
    """init 과 같되 더 쓰는 값을 본다: (아는 것의 비트, 묶음마다(지식 · 여론 · 관계) 쓸 수 없는 까닭, 로그)."""
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    try:
        lib.srtoybox_test_init(image, len(image))
        flags = lib.srtoybox_game_flags()
        off = [text(lib.srtoybox_more_off, group) for group in (MORE_TECH, MORE_OPINION, MORE_RELATIONS)]
    finally:
        lib.srtoybox_test_game(None, None, None)
    log = tmp_path / "toybox.log"
    return flags, off, log.read_text(encoding="utf-8") if log.is_file() else ""


FOUND_MORE = "기술 수준 +0x3120 · 세계 시장 여론 +0x3004 +0x3008 +0x3020 · 관계 +0x4000 +0x5000 전쟁 명분 +0x6000"


def test_startup_finds_more_without_any_cheat(lib, all_sigs, more_sigs, tmp_path, monkeypatch):
    state, values = all_sigs
    flags, off, log = init_more(lib, toybox_fake_exe.sig_image(state + values + more_sigs), tmp_path, monkeypatch)
    assert flags == READS | WRITES | CAN_TECH | CAN_OPINION | CAN_RELATIONS and off == ["", "", ""]
    assert f"값을 더 씁니다 ({FOUND_MORE})" in log
    assert "쓸 수 없습니다" not in log and "맞지 않은 서명" not in log


def test_startup_drops_only_the_group_it_cannot_find(lib, all_sigs, more_sigs, tmp_path, monkeypatch):
    """한 묶음의 서명이 깨지면 그 단추만 꺼진다. 까닭이 로그와 창에 같은 글로 남는다. 돈 · 물자와 다른 묶음은 그대로다."""
    state, values = all_sigs
    first = len(state) + len(values) + 3 * 4                  # 관계 표 1 의 서명 셋 가운데 앞의 둘
    image = toybox_fake_exe.sig_image(state + values + more_sigs, broken={first, first + 1})
    flags, off, log = init_more(lib, image, tmp_path, monkeypatch)
    assert flags == READS | WRITES | CAN_TECH | CAN_OPINION
    assert off == ["", "", "이 게임 판에서는 쓸 수 없습니다 (관계 표 1: 서명 3개 가운데 1개)"]
    assert "값을 더 씁니다 (기술 수준 +0x3120 · 세계 시장 여론 +0x3004 +0x3008 +0x3020)" in log
    assert "관계를 쓸 수 없습니다 (관계 표 1: 서명 3개 가운데 1개)" in log
    assert "맞지 않은 서명" not in log                         # 못 찾은 묶음의 서명을 줄줄이 적지 않는다


def test_startup_without_any_of_more_keeps_money_and_stock(lib, all_sigs, tmp_path, monkeypatch):
    state, values = all_sigs
    flags, off, log = init_more(lib, toybox_fake_exe.sig_image(state + values), tmp_path, monkeypatch)
    assert flags == READS | WRITES and all(off)
    assert "값을 씁니다 (국고 +0x1230" in log and "값을 더 씁니다" not in log
    for line in ("기술 수준을 쓸 수 없습니다 (기술 수준 칸: 서명 3개 가운데 0개)", "세계 시장 여론을 쓸 수 없습니다 (여론 칸 1: 서명 3개 가운데 0개)",
                 "관계를 쓸 수 없습니다 (관계 표 1: 서명 3개 가운데 0개)"):
        assert line in log


def test_startup_finds_more_when_money_and_stock_are_not_found(lib, all_sigs, more_sigs, tmp_path, monkeypatch):
    """묶음은 서로 기대지 않는다: 값 묶음(돈 · 물자)을 못 찾아도 더 쓰는 값은 찾아서 쓴다."""
    state, _values = all_sigs
    flags, off, log = init_more(lib, toybox_fake_exe.sig_image(state + more_sigs), tmp_path, monkeypatch)
    assert flags == READS | CAN_TECH | CAN_OPINION | CAN_RELATIONS and off == ["", "", ""]
    assert "값을 쓸 수 없습니다 (세계 자료 포인터" in log and f"값을 더 씁니다 ({FOUND_MORE})" in log


def test_startup_names_an_unmatched_signature_of_a_group_it_found(lib, all_sigs, more_sigs, tmp_path, monkeypatch):
    state, values = all_sigs
    image = toybox_fake_exe.sig_image(state + values + more_sigs, broken={len(state) + len(values) + 2})
    flags, _off, log = init_more(lib, image, tmp_path, monkeypatch)
    assert flags & CAN_TECH and "맞지 않은 서명: tech #3 (안 맞음)" in log


def test_startup_drops_a_group_that_sits_on_the_treasury(lib, all_sigs, more_sigs, tmp_path, monkeypatch):
    """새 묶음의 칸이 국고 칸과 겹치면 그 묶음을 버린다(값 묶음은 그대로 쓴다)."""
    state, values = all_sigs
    image = toybox_fake_exe.sig_image(state + values + more_sigs, targets={"tech": 0x1234})
    flags, off, log = init_more(lib, image, tmp_path, monkeypatch)
    assert flags == READS | WRITES | CAN_OPINION | CAN_RELATIONS
    assert off[0] == "이 게임 판에서는 쓸 수 없습니다 (기술 수준 칸: 찾은 자리가 국고 칸이나 재고 칸과 겹칩니다)"
    assert "기술 수준을 쓸 수 없습니다 (기술 수준 칸: 찾은 자리가 국고 칸이나 재고 칸과 겹칩니다)" in log


```

`tests/toybox_fake_game.py` 에서 다음을 찾아:

```python
from srkit.toybox import GameAddresses, ValueLayout

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, WORLD_POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x1000
LAYOUT = dict(world_pointer=WORLD_POINTER, treasury=0x40, stock_first=0x60, stock_step=0x10, used_first=0x18, used_step=0x84)
OBJECT_SIZE = 0x200
```

이렇게 바꾼다:

```python
from srkit.toybox import GameAddresses, MoreLayout, ValueLayout

MULTIPLAYER, OPTIONS, PROGRAM, MODE, INDEX, COUNT, POINTER, WORLD_POINTER, TABLE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x1000
LAYOUT = dict(world_pointer=WORLD_POINTER, treasury=0x40, stock_first=0x60, stock_step=0x10, used_first=0x18, used_step=0x84)
# 더 쓰는 값의 자리: 기술 수준, 여론의 세 칸, 지역 인덱스로 찾는 표 셋(가짜 게임의 표는 256칸 — 인덱스 255 까지 쓴다)
MORE = dict(tech=0x130, opinion0=0x134, opinion1=0x138, opinion2=0x150, relation0=0x200, relation1=0x600, casus=0xA00)
RELATION_TABLES = ("relation0", "relation1", "casus")
OBJECT_SIZE = 0x1000
```

`tests/toybox_fake_game.py` 에서 다음 바로 앞에:

```python
        self.objects: dict[int, ctypes.Array] = {}
```

이것을 더한다:

```python
        self.more = MoreLayout(**MORE)
```

`tests/toybox_fake_game.py` 에서 다음 바로 앞에:

```python
    def snapshot(self, index: int) -> bytes:
```

이것을 더한다:

```python
    def tech(self, index: int) -> float:
        return self._read(index, MORE["tech"], "<f")

    def set_tech(self, index: int, value: float) -> None:
        self._write(index, MORE["tech"], "<f", value)

    def opinion(self, index: int) -> list[float]:
        return [self._read(index, MORE[name], "<f") for name in ("opinion0", "opinion1", "opinion2")]

    def set_opinion(self, index: int, values: tuple[float, float, float]) -> None:
        for name, value in zip(("opinion0", "opinion1", "opinion2"), values):
            self._write(index, MORE[name], "<f", value)

    def relation(self, index: int, other: int) -> list[float]:
        """index 의 지역 객체가 other(인덱스)에 대해 가진 값: [관계 표 1, 관계 표 2, 전쟁 명분]."""
        return [self._read(index, MORE[name] + 4 * other, "<f") for name in RELATION_TABLES]

    def set_relation(self, index: int, other: int, values: tuple[float, float, float]) -> None:
        for name, value in zip(RELATION_TABLES, values):
            self._write(index, MORE[name] + 4 * other, "<f", value)

```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_values.py tests/test_toybox_game.py -q 2>&1 | tail -4`

Expected: `110 passed, 72 errors` — `tests/test_toybox_values.py` 의 테스트가 모두 픽스처에서 `AttributeError: function 'srtoybox_more_read' not found` 로 오류가 난다(DLL 에 아직 그 함수가 없다). `tests/test_toybox_game.py` 의 110개는 통과한다.

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
// 테스트: 게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다. 이미지는 srtoybox_test_game(nullptr, …) 로 비울 때까지 살아 있어야 한다.
```

이것을 더한다:

```cpp
// 테스트: 가짜 메모리에서 더 쓰는 값을 읽는다. "ok=1 tech=130 opinion=0.5,0.25,0.75"
EXPORT int srtoybox_more_read(const unsigned char *base, const GameAddresses *at, const MoreLayout *more, char *out, int size)
{
    if (at == nullptr || more == nullptr)
        return -1;
    const GameMore v = read_more(base, *at, *more);
    char line[160];
    snprintf(line, sizeof(line), "ok=%d tech=%.9g opinion=%.9g,%.9g,%.9g", v.ok ? 1 : 0, static_cast<double>(v.tech),
             static_cast<double>(v.opinion[0]), static_cast<double>(v.opinion[1]), static_cast<double>(v.opinion[2]));
    return put(line, out, size);
}

// 테스트: 가짜 메모리에서 그 번호의 나라와의 관계를 읽는다. "ok=1 mine=0.5,0.25,0 theirs=-1,0,1"(관계 표 둘, 전쟁 명분)
EXPORT int srtoybox_relation_read(const unsigned char *base, const GameAddresses *at, const MoreLayout *more, int number, char *out,
                                  int size)
{
    if (at == nullptr || more == nullptr)
        return -1;
    const Relation r = read_relation(base, *at, *more, number);
    char line[200];
    snprintf(line, sizeof(line), "ok=%d mine=%.9g,%.9g,%.9g theirs=%.9g,%.9g,%.9g", r.ok ? 1 : 0, static_cast<double>(r.mine[0]),
             static_cast<double>(r.mine[1]), static_cast<double>(r.mine[2]), static_cast<double>(r.theirs[0]),
             static_cast<double>(r.theirs[1]), static_cast<double>(r.theirs[2]));
    return put(line, out, size);
}

// 테스트: 가짜 메모리에 더 쓰는 값을 쓴다. what: 0 기술 수준(value 로), 1 세계 시장 여론(최고), 2 관계(number 의 나라와 value 로).
// 돌려주는 값은 Wrote(…, 5 꺼져 있다 · 자리를 모른다, 6 그 나라가 없다). done 에 쓴 칸의 수.
EXPORT int srtoybox_more_write(const unsigned char *base, const GameAddresses *at, const MoreLayout *more, int what, int number,
                               double value, int *done)
{
    int cells = 0;
    Wrote wrote = Wrote::BadValue;
    if (at == nullptr || more == nullptr || what < 0 || what > 2)
        return -1;
    if (what == 0) {
        wrote = write_tech(base, *at, *more, static_cast<float>(value));
        cells = wrote == Wrote::Done ? 1 : 0;
    } else if (what == 1) {
        wrote = write_opinion(base, *at, *more, &cells);
    } else {
        wrote = write_relation(base, *at, *more, number, static_cast<float>(value), &cells);
    }
    if (done != nullptr)
        *done = cells;
    return static_cast<int>(wrote);
}

// 테스트: 이 프로세스의 "게임"에 더 쓰는 값의 자리를 준다(srtoybox_test_game 다음에 부른다). 자리가 0 인 묶음 · nullptr 은 못 찾은 것으로.
EXPORT void srtoybox_test_more(const MoreLayout *layout)
{
    game_set_more_for_test(layout);
}

// 더 쓰는 값의 묶음(1 지식, 2 여론, 4 관계)을 쓸 수 없는 까닭. 쓸 수 있으면 빈 글.
EXPORT int srtoybox_more_off(int group, char *out, int size)
{
    return put(game_more_off(group), out, size);
}

```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
// 테스트: 이 프로세스의 "게임"에 대해 아는 것. 비트 1 = 상태를 읽는다, 2 = 명령 처리 함수를 부를 수 있다, 4 = 값을 쓸 수 있다.
EXPORT int srtoybox_game_flags(void)
{
    return (game_reads() ? 1 : 0) | (game_can_call() ? 2 : 0) | (game_values_off().empty() ? 4 : 0);
```

이렇게 바꾼다:

```cpp
// 테스트: 이 프로세스의 "게임"에 대해 아는 것. 비트 1 = 상태를 읽는다, 2 = 명령 처리 함수를 부를 수 있다, 4 = 값(국고 · 재고)을 쓸 수 있다,
// 8 = 기술 수준을, 16 = 세계 시장 여론을, 32 = 관계를 쓸 수 있다.
EXPORT int srtoybox_game_flags(void)
{
    return (game_reads() ? 1 : 0) | (game_can_call() ? 2 : 0) | (game_values_off().empty() ? 4 : 0)
        | (game_more_off(MORE_TECH).empty() ? 8 : 0) | (game_more_off(MORE_OPINION).empty() ? 16 : 0)
        | (game_more_off(MORE_RELATIONS).empty() ? 32 : 0);
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
#include "products.h"
```

이것을 더한다:

```cpp
#include "regions.h"
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
bool g_write_failed;      // 값 쓰기가 실패했다 — 이번 실행에서는 더 쓰지 않는다
```

이것을 더한다:

```cpp
MoreLayout g_more;        // 더 쓰는 값의 자리(못 찾은 묶음의 것은 0)
int g_more_groups;        // 찾은 묶음의 비트
char g_more_why[MORE_GROUPS][MORE_WHY];   // 묶음마다 못 찾은 까닭
```

`native/srtoybox/game.cpp` 에서 다음을 찾아:

```cpp
void log_unmatched(const SigRow *rows, int n)
{
    for (int i = 0; i < n; i++)
        if (rows[i].count != 1)
            log_line("맞지 않은 서명: %s #%d (%s)", rows[i].name, i % STATE_SIGS + 1, rows[i].count == 0 ? "안 맞음" : "여러 번 맞음");
```

이렇게 바꾼다:

```cpp
void log_unmatched(const SigRow &row, int number)
{
    if (row.count != 1)
        log_line("맞지 않은 서명: %s #%d (%s)", row.name, number, row.count == 0 ? "안 맞음" : "여러 번 맞음");
}

void log_unmatched(const SigRow *rows, int n)
{
    for (int i = 0; i < n; i++)
        log_unmatched(rows[i], i % STATE_SIGS + 1);
}

// 그 번호의 나라(이번 판에 실제로 있는 것)의 객체와 인덱스. 없으면 false.
bool find_region(const uint8_t *base, const GameAddresses &at, int number, uint64_t *object, int *index)
{
    int32_t count = 0;
    if (number <= 0 || !peek_at(base, at.region_count, &count) || count < 1 || count >= MAX_REGIONS)
        return false;
    std::vector<uint64_t> table(static_cast<size_t>(count) + 1);
    if (!peek(base + at.region_table, table.data(), table.size() * sizeof(uint64_t)))
        return false;
    for (int i = 1; i <= count; i++) {
        Region r = {};
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i) && in_play(r) && r.number == number) {
            *object = table[static_cast<size_t>(i)];
            *index = i;
            return true;
        }
    }
    return false;
}

// 플레이어와 그 번호의 나라: 두 객체의 주소와 인덱스. 판정은 Wrote 로(Done 이면 넷을 채웠다).
Wrote find_pair(const uint8_t *base, const GameAddresses &at, int number, bool writing, uint64_t *mine, int *me, uint64_t *theirs,
                int *them)
{
    int32_t index = 0;
    const GameState s = read_player(base, at, mine);
    if (!s.in_game || (writing && s.multiplayer) || !peek_at(base, at.player_index, &index) || index < 1 || index >= MAX_REGIONS)
        return Wrote::NotInGame;
    *me = index;
    if (number == s.player || !find_region(base, at, number, theirs, them))
        return Wrote::NoTarget;
    return Wrote::Done;
}

// 한 나라와의 관계가 놓인 여섯 칸의 주소: [0 … 2] 플레이어 객체의 그 나라 칸(관계 표 둘 · 전쟁 명분), [3 … 5] 그 나라 객체의 플레이어 칸.
void relation_cells(const MoreLayout &more, uint64_t mine, int me, uint64_t theirs, int them, uint64_t *cells)
{
    const uint32_t tables[3] = {more.relation[0], more.relation[1], more.casus};
    for (int i = 0; i < 3; i++) {
        cells[i] = mine + tables[i] + 4ull * static_cast<uint64_t>(them);
        cells[3 + i] = theirs + tables[i] + 4ull * static_cast<uint64_t>(me);
    }
}

// float 여러 칸을 쓴다. 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다 — 반쪽만 쓰고 멈추는 일을 줄인다. done 에 쓴 칸의 수.
Wrote poke_floats(const uint64_t *cells, const float *values, int n, int *done)
{
    *done = 0;
    for (int i = 0; i < n; i++)
        if (!writable(cells[i], sizeof(float)))
            return Wrote::Failed;
    for (int i = 0; i < n; i++) {
        if (!poke(cells[i], &values[i], sizeof(float)))
            return Wrote::Failed;
        ++*done;
    }
    return Wrote::Done;
}

// 값을 쓸 수 없는 까닭(found: 그 묶음의 자리를 찾았는가, why: 못 찾은 까닭). g_lock 을 쥔 채로 부른다.
std::string off_text(bool found, const char *why)
{
    if (!g_located || !reading_wanted())
        return "게임 상태를 읽을 수 있을 때만 씁니다.";
    if (!found)
        return std::string("이 게임 판에서는 쓸 수 없습니다 (") + why + ")";
    if (!write_wanted())
        return "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)";
    if (g_write_failed)
        return "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.";
    return std::string();
}

// 묶음의 비트 → 까닭이 든 줄(0 지식, 1 여론, 2 관계). 묶음이 아니면 -1.
int more_index(int group)
{
    return group == MORE_TECH ? 0 : group == MORE_OPINION ? 1 : group == MORE_RELATIONS ? 2 : -1;
}

// 지금의 "게임"과 더 쓰는 값의 자리. 그 묶음을 쓸 수 없으면 false.
bool more_ready(int group, const uint8_t **base, GameAddresses *at, MoreLayout *more)
{
    if (!game_more_off(group).empty())
        return false;
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    *more = g_more;
    return true;
}

// 더 쓰는 값의 쓰기가 실패했다: 이번 실행에서는 값 쓰기 전체를 끄고 로그에 적는다.
Wrote write_failed(const std::string &what, int cells, int done)
{
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_write_failed = true;
    }
    if (done > 0)
        log_line("값 쓰기 실패 (%s, %d칸 가운데 %d칸을 쓴 뒤) — 값 쓰기를 끕니다", what.c_str(), cells, done);
    else
        log_line("값 쓰기 실패 (%s) — 값 쓰기를 끕니다", what.c_str());
    return Wrote::Failed;
```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
void game_init()
```

이것을 더한다:

```cpp
GameMore read_more(const uint8_t *base, const GameAddresses &at, const MoreLayout &more)
{
    GameMore v;
    uint64_t object = 0;
    if (!read_player(base, at, &object).in_game || (more.tech != 0 && !peek_in(object, more.tech, &v.tech)))
        return v;
    for (int i = 0; i < 3; i++)
        if (more.opinion[i] != 0 && !peek_in(object, more.opinion[i], &v.opinion[i]))
            return v;
    v.ok = true;
    return v;
}

Relation read_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number)
{
    Relation r;
    uint64_t mine = 0, theirs = 0, cells[6];
    int me = 0, them = 0;
    if (more.relation[0] == 0 || more.relation[1] == 0 || more.casus == 0
        || find_pair(base, at, number, false, &mine, &me, &theirs, &them) != Wrote::Done)
        return r;
    relation_cells(more, mine, me, theirs, them, cells);
    for (int i = 0; i < 3; i++)
        if (!peek(reinterpret_cast<const void *>(cells[i]), &r.mine[i], sizeof(float))
            || !peek(reinterpret_cast<const void *>(cells[3 + i]), &r.theirs[i], sizeof(float)))
            return r;
    r.ok = true;
    return r;
}

Wrote write_tech(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, float value)
{
    uint64_t object = 0;
    if (more.tech == 0)
        return Wrote::Off;
    if (!std::isfinite(value) || value < 0.0f)
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    return poke(object + more.tech, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

Wrote write_opinion(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int *done)
{
    uint64_t object = 0;
    *done = 0;
    if (more.opinion[0] == 0 || more.opinion[1] == 0 || more.opinion[2] == 0)
        return Wrote::Off;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    const uint64_t cells[3] = {object + more.opinion[0], object + more.opinion[1], object + more.opinion[2]};
    const float best[3] = {1.0f, 1.0f, 1.0f};
    return poke_floats(cells, best, 3, done);
}

Wrote write_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number, float level, int *done)
{
    uint64_t mine = 0, theirs = 0, cells[6];
    int me = 0, them = 0;
    *done = 0;
    if (more.relation[0] == 0 || more.relation[1] == 0 || more.casus == 0)
        return Wrote::Off;
    if (!std::isfinite(level) || level < -1.0f || level > 1.0f)
        return Wrote::BadValue;
    const Wrote found = find_pair(base, at, number, true, &mine, &me, &theirs, &them);
    if (found != Wrote::Done)
        return found;
    relation_cells(more, mine, me, theirs, them, cells);
    const float values[6] = {level, level, 0.0f, level, level, 0.0f};
    return poke_floats(cells, values, 6, done);
}

```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
    const unsigned long long took = GetTickCount64() - started;
```

이것을 더한다:

```cpp

    // 새 찾기: 더 쓰는 값(기술 수준 · 세계 시장 여론 · 관계) — 묶음마다 따로 찾는다. 값 묶음을 찾았으면 그 칸들과 겹치지 않아야 한다
    MoreLayout more = {};
    SigRow more_rows[MORE_WANTED * STATE_SIGS];
    char more_why[MORE_GROUPS][MORE_WHY] = {};
    const int groups = state ? locate_more(base, size, values ? &layout : nullptr, &more, more_rows, more_why) : 0;
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
        snprintf(g_values_why, sizeof(g_values_why), "%s", value_why);
```

이것을 더한다:

```cpp
        g_more = more;
        g_more_groups = groups;
        memcpy(g_more_why, more_why, sizeof(g_more_why));
```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
    if (can_call)
```

이것을 더한다:

```cpp
    static const char *const MISSING[MORE_GROUPS] = {"기술 수준을 쓸 수 없습니다 (%s)", "세계 시장 여론을 쓸 수 없습니다 (%s)",
                                                     "관계를 쓸 수 없습니다 (%s)"};
    if (groups != 0) {
        char found[160] = "";
        size_t used = 0;
        const auto add = [&](const char *format, uint32_t a, uint32_t b, uint32_t c) {
            used += static_cast<size_t>(snprintf(found + used, sizeof(found) - used, format, used == 0 ? "" : " · ", a, b, c));
        };
        if (groups & MORE_TECH)
            add("%s기술 수준 +0x%X", more.tech, 0, 0);
        if (groups & MORE_OPINION)
            add("%s세계 시장 여론 +0x%X +0x%X +0x%X", more.opinion[0], more.opinion[1], more.opinion[2]);
        if (groups & MORE_RELATIONS)
            add("%s관계 +0x%X +0x%X 전쟁 명분 +0x%X", more.relation[0], more.relation[1], more.casus);
        log_line(write_wanted() ? "값을 더 씁니다 (%s)" : "값을 더 쓰지 않습니다 (SRTOYBOX_WRITE=0. %s)", found);
    }
    for (int g = 0; g < MORE_GROUPS; g++)
        if ((groups & (1 << g)) == 0)
            log_line(MISSING[g], more_why[g]);
    for (int i = 0; i < MORE_WANTED * STATE_SIGS; i++)   // 찾은 묶음에서만: 셋 가운데 둘로 찾았을 때 맞지 않은 하나
        if ((groups & (1 << locate_more_group(i / STATE_SIGS))) != 0)
            log_unmatched(more_rows[i], i % STATE_SIGS + 1);
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
    snprintf(g_values_why, sizeof(g_values_why), "값의 자리를 주지 않았습니다");
```

이것을 더한다:

```cpp
    g_more = MoreLayout();
    g_more_groups = 0;
    for (int g = 0; g < MORE_GROUPS; g++)
        snprintf(g_more_why[g], MORE_WHY, "값의 자리를 주지 않았습니다");
```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
bool game_can_call()
```

이것을 더한다:

```cpp
void game_set_more_for_test(const MoreLayout *layout)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_more = layout != nullptr ? *layout : MoreLayout();
    g_more_groups = (g_more.tech != 0 ? MORE_TECH : 0)
        | (g_more.opinion[0] != 0 && g_more.opinion[1] != 0 && g_more.opinion[2] != 0 ? MORE_OPINION : 0)
        | (g_more.relation[0] != 0 && g_more.relation[1] != 0 && g_more.casus != 0 ? MORE_RELATIONS : 0);
    g_write_failed = false;
}

```

`native/srtoybox/game.cpp` 에서 다음을 찾아:

```cpp
    if (!g_located || !reading_wanted())
        return "게임 상태를 읽을 수 있을 때만 씁니다.";
    if (!g_values)
        return std::string("이 게임 판에서는 쓸 수 없습니다 (") + g_values_why + ")";
    if (!write_wanted())
        return "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)";
    if (g_write_failed)
        return "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.";
    return std::string();
```

이렇게 바꾼다:

```cpp
    return off_text(g_values, g_values_why);
}

bool game_writes()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && reading_wanted() && write_wanted() && !g_write_failed;
}

std::string game_more_off(int group)
{
    const int index = more_index(group);
    std::lock_guard<std::mutex> lock(g_lock);
    return index < 0 ? std::string("없는 묶음입니다") : off_text((g_more_groups & group) != 0, g_more_why[index]);
}

GameMore game_more()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !reading_wanted())
            return GameMore();
        base = g_base;
        at = g_at;
        more = g_more;
    }
    return read_more(base, at, more);
}

Relation game_relation(int number)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !reading_wanted())
            return Relation();
        base = g_base;
        at = g_at;
        more = g_more;
    }
    return read_relation(base, at, more, number);
}

Wrote game_write_tech(float value)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    if (!more_ready(MORE_TECH, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_tech(base, at, more, value);
    return wrote == Wrote::Failed ? write_failed("기술 수준", 1, 0) : wrote;
}

Wrote game_write_opinion()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    int done = 0;
    if (!more_ready(MORE_OPINION, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_opinion(base, at, more, &done);
    return wrote == Wrote::Failed ? write_failed("세계 시장 여론", 3, done) : wrote;
}

Wrote game_write_relation(int number, float level)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    int done = 0;
    if (!more_ready(MORE_RELATIONS, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_relation(base, at, more, number, level, &done);
    return wrote == Wrote::Failed
        ? write_failed("관계 — " + region_label(number) + " (" + std::to_string(number) + ")", 6, done) : wrote;
```

`native/srtoybox/game.h` 에서 다음을 찾아:

```cpp
// 찾은 주소(locate.h)로 게임의 상태와 값을 읽고, 플레이어의 국고와 물자 재고를 고친다.
// 게임의 메모리에 쓰는 곳은 그 둘뿐이다: 플레이어 지역 객체의 국고 1칸과 재고 STOCK_SLOTS 칸.
// 다른 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다. 내장 치트를 거치지 않는다.
```

이렇게 바꾼다:

```cpp
// 찾은 주소(locate.h)로 게임의 상태와 값을 읽고 고친다. 내장 치트를 거치지 않는다.
// 게임의 메모리에 쓰는 곳은 이것뿐이다:
//   플레이어 지역 객체의 국고 1칸 · 재고 STOCK_SLOTS 칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸,
//   그리고 고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸.
// 그 밖의 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다.
```

`native/srtoybox/game.h` 에서 다음 바로 앞에:

```cpp
enum class Wrote {
```

이것을 더한다:

```cpp
// 더 쓰는 값(locate_more 가 찾은 자리에서 읽는다): 플레이어의 기술 수준과 세계 시장 여론의 세 칸.
struct GameMore {
    bool ok = false;         // 읽었다: 게임을 진행 중이다. 못 찾은 묶음의 값은 0 으로 둔다
    float tech = 0;          // 기술 수준. 유한한 수가 아닐 수 있다 — 쓰는 쪽(keeper)이 거른다
    float opinion[3] = {};
};

// 한 나라와의 관계: [0] · [1] 은 관계 표 둘, [2] 는 전쟁 명분 표.
struct Relation {
    bool ok = false;         // 읽었다: 게임을 진행 중이고 그 나라가 이번 판에 있다(플레이어 자신이 아니다)
    float mine[3] = {};      // 플레이어 객체의 표에서 그 나라의 칸
    float theirs[3] = {};    // 그 나라 객체의 표에서 플레이어의 칸
};

```

`native/srtoybox/game.h` 에서 다음을 찾아:

```cpp
    Off,         // 값 쓰기가 꺼져 있다(game_values_off)
```

이렇게 바꾼다:

```cpp
    Off,         // 값 쓰기가 꺼져 있다(game_values_off · game_more_off), 그 묶음의 자리를 모른다
    NoTarget,    // 그 번호의 나라가 이번 판에 없다(없는 번호, 사람도 AI 도 맡지 않은 지역, 플레이어 자신)
```

`native/srtoybox/game.h` 에서 다음 바로 뒤에:

```cpp
Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value);
```

이것을 더한다:

```cpp
GameMore read_more(const uint8_t *base, const GameAddresses &at, const MoreLayout &more);
Relation read_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number);
// 쓰기 직전의 확인은 write_treasury 와 같다. 그 묶음의 자리를 모르면(0) Wrote::Off.
// 여러 칸을 쓰는 것은 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 먼저 본다(반쪽만 쓰고 멈추지 않게). done 에 쓴 칸의 수.
Wrote write_tech(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, float value);   // 0 이상의 유한한 수
Wrote write_opinion(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int *done);  // 세 칸에 1.0
// 그 번호의 나라와의 관계를 level(-1 … 1)로, 전쟁 명분을 0 으로: 플레이어 객체의 그 나라 칸 셋, 그 나라 객체의 플레이어 칸 셋.
Wrote write_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number, float level, int *done);
```

`native/srtoybox/game.h` 에서 다음 바로 앞에:

```cpp
// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
```

이것을 더한다:

```cpp
// 값 쓰기가 켜져 있다: 게임을 읽고, SRTOYBOX_WRITE 가 0 이 아니고, 이번 실행에서 쓰기가 실패한 적이 없다.
// 어느 묶음의 자리를 찾았는지는 보지 않는다(game_values_off · game_more_off 가 본다).
bool game_writes();
// 더 쓰는 값의 묶음(MORE_TECH · MORE_OPINION · MORE_RELATIONS)을 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글.
// 묶음마다 따로다 — 한 묶음을 못 찾아도 다른 묶음과 국고 · 재고는 그대로다.
std::string game_more_off(int group);
GameMore game_more();                  // 지금의 값. 부를 때마다 읽는다
Relation game_relation(int number);
Wrote game_write_tech(float value);    // 실패하면 game_write_treasury 처럼 값 쓰기 전체를 끈다
Wrote game_write_opinion();
Wrote game_write_relation(int number, float level);

```

`native/srtoybox/game.h` 에서 다음 바로 뒤에:

```cpp
void game_set_values_for_test(const ValueLayout *layout);
```

이것을 더한다:

```cpp
// 더 쓰는 값의 자리를 준다 — 자리가 0 이 아닌 묶음을 찾은 것으로 친다. nullptr 이면 모두 못 찾은 것으로.
void game_set_more_for_test(const MoreLayout *layout);
```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size)
```

이것을 더한다:

```cpp
int locate_more_group(int wanted)
{
    return wanted >= 0 && wanted < MORE_WANTED ? MORE[wanted].group : -1;
}

```

`native/srtoybox/locate.h` 에서 다음 바로 뒤에:

```cpp
int locate_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY]);
```

이것을 더한다:

```cpp
// 찾을 것(표의 wanted 째. rows 의 칸 번호 / STATE_SIGS)이 든 묶음: 0 지식, 1 여론, 2 관계.
int locate_more_group(int wanted);
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_values.py tests/test_toybox_game.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `182 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/exports.cpp tests/test_toybox_values.py tests/toybox_fake_game.py && git commit -q -F - <<'EOF'
feat: ToyBox — 기술 수준 · 세계 시장 여론 · 관계를 읽고 쓴다(내장 치트 없이)

- 쓰는 곳이 늘어난다(설계서 2026-10-10): 플레이어 객체의 기술 수준 1칸 · 여론 3칸 · 관계 표 셋에서 고른 나라의 칸,
  그리고 고른 나라 객체의 관계 표 셋에서 플레이어의 칸. 관계는 치트처럼 양쪽에 쓴다.
- 쓰기 직전의 확인은 국고 · 재고와 같고, 관계는 대상도 본다: 이번 판에 실제로 있는 나라이고 플레이어 자신이 아니다(Wrote::NoTarget).
- 여러 칸은 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 먼저 본다 — 반쪽만 쓰고 멈추지 않는다.
- 게임이 뜰 때 묶음마다 찾는다: "값을 더 씁니다 (…)" / "<묶음>을 쓸 수 없습니다 (…)". 한 묶음을 못 찾아도 나머지와 돈 · 물자는 그대로다.
- 쓰기가 실패하면 묶음 1 의 규칙대로 이번 실행의 값 쓰기 전체를 끈다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `395 passed`, 새 커밋.

---

### Task 3: 요청과 대기열 — 기술 수준 +1, 여론 최고, 관계

**브랜치:** `feat/toybox-values-more`

**Files:**
- Modify: `native/srtoybox/keeper.h`, `native/srtoybox/keeper.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: Task 2 의 `game_writes` · `game_more_off` · `game_more` · `game_write_tech` · `game_write_opinion` · `game_write_relation` · `Wrote::NoTarget` · `srtoybox_test_more` · `srtoybox_more_off`, `FakeGame` 의 새 칸. 묶음 1 의 `Request` · `keeper_enqueue` · `keeper_tick` · `drain` · `LEFT_GAME`, `region_label`.
- Produces:
  - `const int TECH = -3, OPINION = -4, RELATION = -5;`(`Request.slot`), `Request` 의 새 필드 `int region = 0;`(넷째 — `{slot, change, amount}` 로 적은 지금의 코드는 그대로 된다), `const float TECH_LIMIT = 999.0f`.
  - `keeper_enqueue({TECH, Change::Set, 0.0, 0})` · `{OPINION, Change::Set, 0.0, 0}` · `{RELATION, Change::Set, 1.0 또는 0.0, 지역 번호}`.
  - `keeper_last()` 의 새 글: `기술 수준 130 -> 131` · `세계 시장 여론 최고` · `관계 최고 — 폴란드 (1106)` · `관계 중립 — 폴란드 (1106)`.
  - `keeper_notice()` 의 새 글: `기술 수준이 한도(999)라 쓰지 않았습니다.` · `기술 수준을 읽을 수 없어 쓰지 않았습니다.` · `그 나라는 이번 판에 없어 쓰지 않았습니다.`
  - 내보내기 `int srtoybox_keeper_more(int slot, int region, double amount)` — 받았으면 1, 받지 못했으면 0, 그런 요청이 없으면 -1.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
UNREAD = "게임 상태를 읽을 수 있을 때만 씁니다."
```

이것을 더한다:

```python
TECH, OPINION, RELATION = -3, -4, -5                                # native/srtoybox/keeper.h 의 Request.slot(더 쓰는 값의 요청)
BEST, NEUTRAL = 1.0, 0.0                                            # 관계의 수준
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
    lib.srtoybox_keeper_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
```

이것을 더한다:

```python
    lib.srtoybox_keeper_more.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
```

`tests/test_toybox_values.py` 에서 다음 바로 뒤에:

```python
    lib.srtoybox_test_values(ctypes.byref(fake.layout))
```

이것을 더한다:

```python
    lib.srtoybox_test_more(ctypes.byref(fake.more))
```

`tests/test_toybox_values.py` 에서 다음 바로 뒤에:

```python
    assert not ask(lib, TREASURY, ADD, 1e9)
    lib.srtoybox_keeper_tick()
    assert game.treasury(176) == 14.43e9
```

이것을 더한다:

```python


def ask_more(lib, slot: int, region: int = 0, amount: float = 0.0) -> bool:
    """더 쓰는 값의 요청(기술 수준 +1 · 세계 시장 여론 최고 · 관계)."""
    return lib.srtoybox_keeper_more(slot, region, amount) == 1


def logged(tmp_path) -> list[str]:
    """로그의 줄들(때를 뗀 것)."""
    log = tmp_path / "toybox.log"
    return [line.split(" ", 2)[2] for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


def test_a_tech_request_adds_one_on_the_next_tick(lib, game, tmp_path):
    assert ask_more(lib, TECH) and ask_more(lib, TECH)
    assert game.tech(176) == 130.0                             # 누른 것만으로는 쓰지 않는다 — 창 스레드의 틱에서 쓴다
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 132.0 and game.tech(141) == 128.0
    assert told(lib) == ("기술 수준 131 -> 132", "")
    assert logged(tmp_path) == ["값 쓰기: 기술 수준 130 -> 131", "값 쓰기: 기술 수준 131 -> 132"]
    assert game.peek(OPTIONS, "<I") == 0                       # 치트 허용 비트는 그대로다


def test_tech_stops_at_its_limit_and_leaves_what_it_cannot_read(lib, game):
    game.set_tech(176, 998.0)
    assert ask_more(lib, TECH)
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 999.0 and told(lib) == ("기술 수준 998 -> 999", "")
    assert ask_more(lib, TECH)
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 999.0 and told(lib)[1] == "기술 수준이 한도(999)라 쓰지 않았습니다."
    game.set_tech(176, 130.5)                                  # 정수가 아니어도 1 을 더하고, 있는 그대로 적는다
    assert ask_more(lib, TECH)
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 131.5 and told(lib) == ("기술 수준 130.5 -> 131.5", "")
    for odd in (NAN, INF, -5.0):
        game.set_tech(176, odd)
        before = game.snapshot(176)
        assert ask_more(lib, TECH)
        lib.srtoybox_keeper_tick()
        assert game.snapshot(176) == before and told(lib)[1] == "기술 수준을 읽을 수 없어 쓰지 않았습니다."


def test_an_opinion_request_sets_the_three_cells(lib, game, tmp_path):
    assert ask_more(lib, OPINION)
    lib.srtoybox_keeper_tick()
    assert game.opinion(176) == [1.0, 1.0, 1.0] and game.opinion(141) == [0.0, 0.0, 0.0]
    assert told(lib) == ("세계 시장 여론 최고", "") and logged(tmp_path) == ["값 쓰기: 세계 시장 여론 최고"]


def test_relation_requests_write_both_sides(lib, game, tmp_path):
    assert ask_more(lib, RELATION, 1106, BEST)
    lib.srtoybox_keeper_tick()
    assert game.relation(176, 141) == [1.0, 1.0, 0.0] and game.relation(141, 176) == [1.0, 1.0, 0.0]
    assert told(lib) == ("관계 최고 — 폴란드 (1106)", "")
    assert ask_more(lib, RELATION, 1106, NEUTRAL)
    lib.srtoybox_keeper_tick()
    assert game.relation(176, 141) == [0.0, 0.0, 0.0] and game.relation(141, 176) == [0.0, 0.0, 0.0]
    assert told(lib) == ("관계 중립 — 폴란드 (1106)", "")
    assert logged(tmp_path) == ["값 쓰기: 관계 최고 — 폴란드 (1106)", "값 쓰기: 관계 중립 — 폴란드 (1106)"]
    assert game.treasury(176) == 14.43e9 and game.peek(OPTIONS, "<I") == 0


def test_a_relation_request_for_a_country_that_is_gone_is_dropped(lib, game, tmp_path):
    """누른 뒤 쓰기 전에 그 나라가 없어졌다(다른 판, 병합됨) — 쓰지 않고 알린다. 자기 나라 · 없는 번호도 같다."""
    gone = "그 나라는 이번 판에 없어 쓰지 않았습니다."
    assert ask_more(lib, RELATION, 1106, BEST)
    struct.pack_into("<I", game.objects[141], 0, 5)            # 폴란드가 이번 판에 없는 지역이 됐다
    before = everything(game)
    lib.srtoybox_keeper_tick()
    assert everything(game) == before and told(lib) == ("", gone)
    for number in (1499, 9999):
        assert ask_more(lib, RELATION, number, BEST)
        lib.srtoybox_keeper_tick()
        assert everything(game) == before and told(lib) == ("", gone)
    assert logged(tmp_path) == []


def test_more_requests_are_dropped_outside_a_game(lib, game):
    assert ask_more(lib, TECH) and ask_more(lib, OPINION) and ask_more(lib, RELATION, 1106, BEST)
    game.menu()
    before = everything(game)
    lib.srtoybox_keeper_tick()
    game.play(176)
    lib.srtoybox_keeper_tick()                                 # 버린 요청이 돌아온 뒤에 쓰이지 않는다
    assert game.tech(176) == 130.0 and game.opinion(176) == [0.5, 0.25, 0.75] and told(lib) == ("", LEFT_GAME)
    assert game.relation(176, 141) == [0.25, -0.5, 0.75] and len(before) == len(everything(game))


def test_money_stock_and_more_requests_are_written_in_the_order_asked(lib, game, tmp_path):
    assert ask(lib, TREASURY, ADD, 1e9) and ask_more(lib, TECH) and ask(lib, 3, ADD, 1.0) and ask_more(lib, OPINION)
    lib.srtoybox_keeper_tick()
    assert logged(tmp_path) == ["값 쓰기: 국고 14.43 B -> 15.43 B", "값 쓰기: 기술 수준 130 -> 131", "값 쓰기: 석유 2.5 K -> 2.5 K",
                                "값 쓰기: 세계 시장 여론 최고"]
    assert told(lib) == ("세계 시장 여론 최고", "")


def test_more_requests_do_not_need_money_and_stock(lib, game):
    """묶음은 서로 기대지 않는다: 국고 · 재고의 자리를 못 찾은 게임에서도 더 쓰는 값은 쓴다. 유지는 쉰다."""
    lib.srtoybox_test_values(None)
    keep(lib, TREASURY, 50e9)
    assert not ask(lib, TREASURY, ADD, 1e9) and ask_more(lib, TECH)
    lib.srtoybox_keeper_tick_at(1000)
    assert game.tech(176) == 131.0 and game.treasury(176) == 14.43e9 and told(lib) == ("기술 수준 130 -> 131", "")


def test_a_request_is_not_taken_for_a_group_that_is_off(lib, game):
    """그 묶음의 자리를 못 찾았으면 그 요청만 받지 않는다. 다른 묶음과 국고 · 재고는 그대로 받는다."""
    lib.srtoybox_test_more(ctypes.byref(toybox.MoreLayout(**{**MORE, "tech": 0})))
    assert not ask_more(lib, TECH)
    assert ask_more(lib, OPINION) and ask_more(lib, RELATION, 1106, NEUTRAL) and ask(lib, TREASURY, ADD, 1.0)
    assert text(lib.srtoybox_more_off, MORE_TECH) == "이 게임 판에서는 쓸 수 없습니다 (값의 자리를 주지 않았습니다)"
    assert text(lib.srtoybox_more_off, MORE_OPINION) == "" and lib.srtoybox_keeper_more(7, 0, 0.0) == -1
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 130.0 and game.opinion(176) == [1.0, 1.0, 1.0]


def test_a_failed_relation_write_turns_all_value_writing_off(lib, game, tmp_path):
    """쓰기가 실패하면 묶음 1 의 규칙 그대로 그 실행에서는 값 쓰기 전체를 끈다(돈 · 물자 · 유지 포함). 반쪽은 남지 않는다."""
    game.lock(141)                                             # 고른 나라의 객체가 읽기 전용 쪽에 있다
    mine = game.snapshot(176)
    assert ask_more(lib, RELATION, 1106, BEST) and ask_more(lib, TECH)
    lib.srtoybox_keeper_tick()
    assert game.snapshot(176) == mine                          # 플레이어 쪽 칸도, 뒤따르던 요청도 쓰지 않았다
    assert text(lib.srtoybox_values_off) == FAILED_OFF
    assert [text(lib.srtoybox_more_off, group) for group in (MORE_TECH, MORE_OPINION, MORE_RELATIONS)] == [FAILED_OFF] * 3
    assert not ask_more(lib, TECH) and not ask(lib, TREASURY, ADD, 1e9)
    assert logged(tmp_path) == ["값 쓰기 실패 (관계 — 폴란드 (1106)) — 값 쓰기를 끕니다"]


def test_a_failed_tech_write_says_so(lib, game, tmp_path):
    game.lock(176)
    game.play(176)
    assert ask_more(lib, TECH) and ask_more(lib, OPINION)
    lib.srtoybox_keeper_tick()
    assert game.tech(176) == 130.0 and game.opinion(176) == [0.5, 0.25, 0.75]
    assert logged(tmp_path) == ["값 쓰기 실패 (기술 수준) — 값 쓰기를 끕니다"] and told(lib)[0] == ""
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -4`

Expected: `83 errors` — 픽스처에서 `AttributeError: function 'srtoybox_keeper_more' not found`.

- [ ] **Step 3: 구현한다**

대기열의 문을 "돈 · 물자의 값을 쓸 수 있는가"에서 "값 쓰기가 켜져 있는가"(`game_writes`)로 바꾸고, 요청을 받을 때 그 요청이 쓰는 묶음을 본다(`request_off`). 새 요청은 국고 · 재고를 읽지 않는다.

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
EXPORT void srtoybox_keeper_tick(void)
```

이것을 더한다:

```cpp
// 테스트: 더 쓰는 값의 요청. slot: -3 기술 수준 +1, -4 세계 시장 여론 최고, -5 region 의 나라와의 관계를 amount(1 최고, 0 중립)로.
// 받았으면 1. 그런 요청이 없으면 -1.
EXPORT int srtoybox_keeper_more(int slot, int region, double amount)
{
    if (slot != TECH && slot != OPINION && slot != RELATION)
        return -1;
    return keeper_enqueue({slot, Change::Set, amount, region}) ? 1 : 0;
}

```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
#include <cstring>
```

이것을 더한다:

```cpp
#include <cmath>
#include <cstdio>
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
#include "runner_win.h"
```

이것을 더한다:

```cpp
#include "regions.h"
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
// 한 칸(국고나 물자 하나)에 대한 셈: 지금 값(*from)과 쓸 값(*to).
```

이것을 더한다:

```cpp
// 그 요청이 쓰는 값을 쓸 수 없는 까닭. 쓸 수 있으면 빈 글. 묶음마다 따로다.
std::string request_off(const Request &r)
{
    return r.slot == TECH ? game_more_off(MORE_TECH) : r.slot == OPINION ? game_more_off(MORE_OPINION)
        : r.slot == RELATION ? game_more_off(MORE_RELATIONS) : game_values_off();
}

// 수를 있는 그대로 적는다: 130, 130.5
std::string plain(double value)
{
    char text[32];
    snprintf(text, sizeof(text), "%.6g", value);
    return text;
}

// 더 쓰는 값의 요청 하나(기술 수준 · 여론 · 관계). 국고 · 재고는 읽지 않는다 — 그 묶음을 못 찾은 게임에서도 된다.
// 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다. g_lock 을 쥔 채로 부른다.
bool apply_more(const Request &r)
{
    Wrote wrote = Wrote::Off;
    std::string what;
    if (r.slot == TECH) {
        const GameMore now = game_more();
        if (!now.ok || !std::isfinite(now.tech) || now.tech < 0.0f) {
            g_notice = "기술 수준을 읽을 수 없어 쓰지 않았습니다.";
            return true;
        }
        if (now.tech + 1.0f > TECH_LIMIT) {
            g_notice = "기술 수준이 한도(999)라 쓰지 않았습니다.";
            return true;
        }
        what = "기술 수준 " + plain(now.tech) + " -> " + plain(now.tech + 1.0f);
        wrote = game_write_tech(now.tech + 1.0f);
    } else if (r.slot == OPINION) {
        what = "세계 시장 여론 최고";
        wrote = game_write_opinion();
    } else {
        what = std::string(r.amount > 0.5 ? "관계 최고" : "관계 중립") + " — " + region_label(r.region) + " (" + std::to_string(r.region) + ")";
        wrote = game_write_relation(r.region, static_cast<float>(r.amount));
    }
    if (wrote == Wrote::Done) {
        g_last = what;
        log_line("값 쓰기: %s", what.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 그 단추의 자리에 보인다(game_more_off)
    g_notice = wrote == Wrote::NoTarget ? "그 나라는 이번 판에 없어 쓰지 않았습니다." : LEFT_GAME;
    return true;
}

```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
        const GameValues now = game_values();  // 요청마다 다시 읽는다 — 앞의 요청이 값을 바꿨다
```

이것을 더한다:

```cpp
        if (r.slot <= TECH) {                  // 더 쓰는 값: 국고 · 재고와 따로다
            if (!apply_more(r)) {
                g_queue.clear();
                return false;
            }
            continue;
        }
```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
    if (g_queue.size() >= MAX_QUEUE || !game_values_off().empty())
```

이렇게 바꾼다:

```cpp
    if (g_queue.size() >= MAX_QUEUE || !request_off(request).empty())
```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
    if (runner_faulted() || !game_values_off().empty()) {
```

이렇게 바꾼다:

```cpp
    if (runner_faulted() || !game_writes()) {
```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
    if (due)
```

이렇게 바꾼다:

```cpp
    if (due && game_values_off().empty())      // 유지는 국고와 물자다 — 그 자리를 못 찾은 게임에서는 쉰다
```

`native/srtoybox/keeper.h` 에서 다음 바로 앞에:

```cpp
#pragma once
```

이것을 더한다:

```cpp
// 요청은 다섯 가지다: 국고, 물자 한 칸, 쓰는 물자 모두(3단계 1), 기술 수준 +1, 세계 시장 여론 최고, 한 나라와의 관계(3단계 2).
```

`native/srtoybox/keeper.h` 에서 다음 바로 뒤에:

```cpp
const int ALL_STOCK = -2;                      // Request.slot: 이번 판에서 쓰는 물자 모두 — 쓸 때 칸마다의 요청으로 풀린다
```

이것을 더한다:

```cpp
const int TECH = -3;                           // Request.slot: 기술 수준에 1 을 더한다(change · amount 는 보지 않는다)
const int OPINION = -4;                        // Request.slot: 세계 시장 여론의 세 칸을 최고(1.0)로(〃)
const int RELATION = -5;                       // Request.slot: region 의 나라와의 관계를 amount 로, 전쟁 명분을 0 으로(change 는 보지 않는다)
```

`native/srtoybox/keeper.h` 에서 다음을 찾아:

```cpp
    double amount;                             // 국고는 달러, 재고는 수량
};
```

이렇게 바꾼다:

```cpp
    double amount;                             // 국고는 달러, 재고는 수량, 관계는 수준(1 최고, 0 중립)
    int region = 0;                            // RELATION: 대상 나라의 지역 번호
};

const float TECH_LIMIT = 999.0f;               // 기술 수준의 한도 — 이것을 넘게 되면 올리지 않는다
```

`native/srtoybox/keeper.h` 에서 다음을 찾아:

```cpp
bool keeper_enqueue(const Request &request);   // 받지 못하면 false: 가득 찼다(32개), 값 쓰기가 꺼져 있다
```

이렇게 바꾼다:

```cpp
// 받지 못하면 false: 가득 찼다(32개), 그 요청이 쓰는 값을 쓸 수 없다(국고 · 재고는 game_values_off, 나머지는 그 묶음의 game_more_off)
bool keeper_enqueue(const Request &request);
```

`native/srtoybox/keeper.h` 에서 다음을 찾아:

```cpp
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개". 없으면 빈 글
```

이렇게 바꾼다:

```cpp
// 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개" · "기술 수준 130 -> 131" ·
// "세계 시장 여론 최고" · "관계 최고 — 폴란드 (1106)". 없으면 빈 글
std::string keeper_last();
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `83 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/keeper.h native/srtoybox/keeper.cpp native/srtoybox/exports.cpp tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox 대기열 — 기술 수준 +1 · 세계 시장 여론 최고 · 관계의 요청

- 요청 셋을 더한다. 길은 국고 · 재고와 같다: 단추가 넣고 게임 창의 타이머가 쓴다. 게임 밖 · 오류 가드 뒤에는 버린다.
- 대기열의 문은 "값 쓰기가 켜져 있는가"이고, 요청을 받을 때 그 요청이 쓰는 묶음을 본다 — 묶음은 서로 기대지 않는다
  (돈 · 물자의 자리를 못 찾은 게임에서도 이 요청들은 쓰인다. 최소 유지는 그때 쉰다).
- 기술 수준은 한도(999)를 넘기지 않고, 수가 아닌 값은 건드리지 않는다. 고른 나라가 쓰기 전에 없어졌으면 쓰지 않고 알린다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `406 passed`, 새 커밋.

---

### Task 4: 기능 표와 창 — 단추 넷을 직접 쓰기로

**브랜치:** `feat/toybox-values-more`

**Files:**
- Modify: `native/srtoybox/features.h`, `native/srtoybox/features.cpp`, `native/srtoybox/command.h`, `native/srtoybox/command.cpp`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`, `native/srtoybox/ui.cpp`
- Test: `tests/test_toybox.py`, `tests/toybox_overlay_probe.py`

**Interfaces:**
- Consumes: Task 2 의 `game_more_off` · `MORE_TECH` · `MORE_OPINION` · `MORE_RELATIONS` · `srtoybox_test_more` · `FakeGame` 의 새 칸. Task 3 의 `TECH` · `OPINION` · `RELATION` · `Request.region` · `keeper_enqueue`. `ui.cpp` 의 `row` · `note` · `g_picked` · `g_confirm` · `g_notice`.
- Produces:
  - `enum class Direct { None, TechUp, OpinionBest, RelationBest, RelationNeutral }`, `Feature::direct`(끝 필드. 적지 않으면 `None`), `int cheat_feature_count()`.
  - 기능 표의 네 줄: `command` 는 `""`, `direct` 는 차례로 `TechUp` · `OpinionBest` · `RelationBest` · `RelationNeutral`. 표의 줄 수(19)와 순서는 그대로다.
  - `build_command` 는 직접 쓰는 줄에 빈 글을 준다.
  - 창: 직접 쓰는 줄의 단추는 `run:<id>`(지금과 같은 이름), 쓸 수 없을 때 단추 대신 나오는 한 줄은 `off:<id>`(글: `<단추 이름> — <까닭>`).
  - 내보내기: `srtoybox_cheat_feature_count()`, `srtoybox_feature_info` 의 열두째 칸(`cheat` · `tech_up` · `opinion_best` · `relation_best` · `relation_neutral`).
  - 화면 검사의 새 모드 `more` · `more_alone` · `more_menu` · `more_leave` · `more_notfound` · `more_write_off` · `more_unread` · `more_repick` · `more_fail` · `more_reenter` · `more_fault`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

화면 검사 도구의 가짜 게임에 새 값을 채우고(`fake_game`), 새 모드(`run_more`)를 더한다. 이미 있는 모드 둘은 "관계 최고"가 더는 게임의 함수를 부르지 않는 것에 맞춘다: `confirm_fault` 는 "동맹 맺기"를 누르고, `pick_gone` · `pick_become` 은 관계의 칸을 본다.

<!-- 고칠 곳: test -->
`tests/test_toybox.py` 에서 다음을 찾아:

```python
        ident, tab, label, command, has_value, default, low, high, confirm, help_, target = \
            text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_,
                    "target": target})
```

이렇게 바꾼다:

```python
        ident, tab, label, command, has_value, default, low, high, confirm, help_, target, how = \
            text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_,
                    "target": target, "how": how})
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert len(fs) == 19
    assert len({f["id"] for f in fs}) == 19 and len({f["command"] for f in fs}) == 19
    # 국고와 물자는 내장 치트를 거치지 않는다(돈 탭 · 물자 탭)
    assert not {"treasury", "georgew", "georgeww", "products", "branson", "bezos"} & {f["id"] for f in fs}
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    for f in fs:
        assert f["command"] == "cheat " + f["id"] and f["label"] and f["help"]
```

이렇게 바꾼다:

```python
    assert len(fs) == 19 and len({f["id"] for f in fs}) == 19
    # 국고와 물자는 내장 치트를 거치지 않는다(돈 탭 · 물자 탭)
    assert not {"treasury", "georgew", "georgeww", "products", "branson", "bezos"} & {f["id"] for f in fs}
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    # 네 줄은 ToyBox 가 값을 직접 쓴다(3단계 2) — 자리와 이름은 그대로이고 게임에 넣는 글이 없다. 나머지 열다섯이 내장 치트로 돈다
    assert {f["id"]: f["how"] for f in fs if f["how"] != "cheat"} == {"finalexam": "tech_up", "shelovesme": "opinion_best",
                                                                     "love": "relation_best", "neutral": "relation_neutral"}
    cheats = [f for f in fs if f["how"] == "cheat"]
    assert len(cheats) == 15 == dll.srtoybox_cheat_feature_count() and len({f["command"] for f in cheats}) == 15
    assert [f["id"] for f in fs][:3] == ["technology", "e=mc2", "finalexam"]            # 줄의 자리는 옮기기 전과 같다
    for f in fs:
        assert f["label"] and f["help"]
        if f["how"] == "cheat":
            assert f["command"] == "cheat " + f["id"]
        else:
            assert f["command"] == "" and not f["has_value"] and not f["confirm"]
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert text(dll.srtoybox_command, b"finalexam", 999, 1106) == "cheat finalexam"            # 값도 대상도 없는 기능은 둘 다 무시한다
    assert text(dll.srtoybox_command, b"e=mc2", 0, 0) == "cheat e=mc2"
    assert text(dll.srtoybox_command, b"approval", 0, 1499) == "cheat approval 1499"           # 대상이 있는 기능은 지역 번호가 붙는다
    assert text(dll.srtoybox_command, b"love", 0, 1106) == "cheat love 1106"
    assert text(dll.srtoybox_command, b"treaty", 0, 1106) == "cheat treaty"                    # 게임이 지도에서 고른 나라를 쓴다
    assert text(dll.srtoybox_command, b"love", 0, 0) is None                                   # 나라를 고르지 않았으면 만들지 않는다
```

이렇게 바꾼다:

```python
    assert text(dll.srtoybox_command, b"e=mc2", 999, 1106) == "cheat e=mc2"                    # 값도 대상도 없는 기능은 둘 다 무시한다
    assert text(dll.srtoybox_command, b"approval", 0, 1499) == "cheat approval 1499"           # 대상이 있는 기능은 지역 번호가 붙는다
    assert text(dll.srtoybox_command, b"annex", 0, 1106) == "cheat annex 1106"
    assert text(dll.srtoybox_command, b"treaty", 0, 1106) == "cheat treaty"                    # 게임이 지도에서 고른 나라를 쓴다
    assert text(dll.srtoybox_command, b"annex", 0, 0) is None                                  # 나라를 고르지 않았으면 만들지 않는다
    for moved in (b"finalexam", b"shelovesme", b"love", b"neutral"):                           # 직접 쓰는 줄은 게임에 넣을 글이 없다
        assert text(dll.srtoybox_command, moved, 0, 1106) is None
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert got["first"] == ["cheat allowcheats", "cheat love 1106"]
    assert got["status"] == status and got["row"] == "-"
    assert got["picked"] == "고른 나라: 없음 — 아래 목록에서 고르십시오"
    assert got["lines"] == got["first"]                         # 풀린 뒤의 누름은 아무것도 실행하지 않는다
```

이렇게 바꾼다:

```python
    assert got["first"] == [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]   # 고른 동안에는 "관계 최고"가 폴란드와의 관계를 쓴다(양쪽에)
    assert got["status"] == status and got["row"] == "-"
    assert got["picked"] == "고른 나라: 없음 — 아래 목록에서 고르십시오"
    assert got["later"] == [[0.25, -0.5, 0.75], [0.125, 0.5, 1.0]] and got["unwritten"] == "-"   # 풀린 뒤의 누름은 아무것도 쓰지 않는다
    assert got["lines"] == []                                   # 이 단추는 게임의 함수를 부르지 않는다
```

`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
def test_prologue_length_knows_only_plain_function_heads(dll):
```

이것을 더한다:

```python
MORE_START = {"tech": 130.0, "opinion": [0.5, 0.25, 0.75], "poland": [[0.25, -0.5, 0.75], [0.125, 0.5, 1.0]],
              "denmark": [[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]]}
MORE_DONE = {"tech": 132.0, "opinion": [1.0, 1.0, 1.0], "poland": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], "denmark": MORE_START["denmark"]}
RESEARCH_ROWS = ["run:technology", "run:e=mc2", "run:finalexam"]
PEOPLE_ROWS = ["run:populate", "run:shelovesme", "run:approval"]
DIPLOMACY_ROWS = ["run:love", "run:neutral", "run:treaty", "run:annex", "run:colonize", "run:novichok", "run:fight", "run:becomeregion"]


@pytest.mark.parametrize("mode", ["more", "more_alone"], ids=["with-money-and-stock", "alone"])
def test_the_four_moved_buttons_write_without_any_cheat(dll, cfg, tmp_path, mode):
    """요구 3: 지식 순위 · 세계 시장 여론 · 관계 최고 · 관계 중립은 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고,
    글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다. 단추의 이름과 자리는 그대로다. 쓰는 곳은 플레이어의 칸과,
    관계라면 고른 나라의 "플레이어" 칸뿐이다(덴마크와의 관계는 그대로다). 국고 · 재고의 자리를 못 찾은 게임에서도 된다."""
    got = json.loads(_probe(cfg, tmp_path, mode))
    assert list(got["research"]) == RESEARCH_ROWS and got["research"]["run:finalexam"] == "지식 순위 올리기"
    assert list(got["people"]) == PEOPLE_ROWS and got["people"]["run:shelovesme"] == "세계 시장 여론 최고"
    assert list(got["diplomacy"]) == DIPLOMACY_ROWS
    assert (got["diplomacy"]["run:love"], got["diplomacy"]["run:neutral"]) == ("관계 최고", "관계 중립")
    assert got["wrote_tech"] == "기술 수준 131 -> 132" and got["wrote_opinion"] == "세계 시장 여론 최고"
    assert got["unpicked"] == {**MORE_START, "tech": 132.0, "opinion": [1.0, 1.0, 1.0]}       # 나라를 고르기 전의 누름은 쓰지 않는다
    assert got["after_love"] == {**got["unpicked"], "poland": [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]}
    assert got["wrote_love"] == "관계 최고 — 폴란드 (1106)" and got["wrote_neutral"] == "관계 중립 — 폴란드 (1106)"
    assert got["state"] == MORE_DONE and got["status"] == "플레이 중: 독일 (1499)"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["treasury"] == 14.43e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: ") == 5 and "직접 실행" not in log and "값 쓰기 실패" not in log


def test_the_moved_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "more_menu"))
    assert list(got["research"]) == RESEARCH_ROWS and list(got["people"]) == PEOPLE_ROWS    # 단추는 보이지만 꺼져 있다
    assert got["state"] == MORE_START and got["wrote_neutral"] == "-"
    assert got["lines"] == [] and got["text"] == "" and got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_moved_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "more_leave"))
    assert got["dropped"] == 130.0 and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["state"]["tech"] == 131.0 and got["unwritten_after"] == "-"


def test_a_relation_is_written_with_the_country_picked_when_the_button_was_pressed(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰이기 전(다음 타이머 전)에 다른 나라를 골라도, 쓰는 것은 누른 때에 골라 둔 나라와의 관계다."""
    got = json.loads(_probe(cfg, tmp_path, "more_repick"))
    assert got["picked"] == "고른 나라: 덴마크 (1201)" and got["wrote"] == "관계 최고 — 폴란드 (1106)"
    assert got["state"] == {**MORE_START, "poland": [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]}     # 덴마크와의 관계는 그대로다
    assert got["lines"] == []


def test_a_group_that_was_not_found_turns_off_only_its_own_button(dll, cfg, tmp_path):
    """묶음마다 따로 꺼진다: 기술 수준의 자리만 못 찾은 게임에서는 "지식 순위 올리기"의 자리에 까닭 한 줄만 보이고,
    같은 탭의 다른 줄과 나머지 직접 쓰는 줄은 그대로 동작한다. 내장 치트로 되돌아가지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_notfound"))
    assert list(got["research"]) == ["run:technology", "run:e=mc2", "off:finalexam"]
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — 이 게임 판에서는 쓸 수 없습니다 (값의 자리를 주지 않았습니다)"
    assert list(got["people"]) == PEOPLE_ROWS and list(got["diplomacy"]) == DIPLOMACY_ROWS
    assert got["state"] == {**MORE_DONE, "tech": 130.0}
    assert got["lines"] == [] and got["text"] == ""


@pytest.mark.parametrize("mode, env, why", [
    ("more_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)"),
    ("more_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다."),
], ids=["write-off", "unread"])
def test_the_moved_buttons_say_why_they_are_off_and_offer_no_cheat(dll, cfg, tmp_path, mode, env, why):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 그 줄의 단추 자리에 까닭 한 줄만 보인다. 내장 치트로 도는 줄은 그대로다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert list(got["research"]) == ["run:technology", "run:e=mc2", "off:finalexam"]
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — " + why
    assert list(got["people"]) == ["run:populate", "off:shelovesme", "run:approval"]
    assert got["people"]["off:shelovesme"] == "세계 시장 여론 최고 — " + why
    if mode == "more_unread":
        assert got["diplomacy"] == {}                           # 게임을 읽지 못하면 이 탭은 통째로 쓸 수 없다(나라 목록이 없다)
    else:
        assert list(got["diplomacy"]) == ["off:love", "off:neutral"] + DIPLOMACY_ROWS[2:]
        assert got["diplomacy"]["off:love"] == "관계 최고 — " + why and got["diplomacy"]["off:neutral"] == "관계 중립 — " + why
    assert got["state"] == MORE_START and got["lines"] == [] and got["text"] == ""


def test_a_failed_write_of_a_moved_button_turns_value_writing_off_and_says_why(dll, cfg, tmp_path):
    """쓸 수 없는 곳을 만나면 죽지 않고, 이번 실행에서 값 쓰기 전체를 끄고 까닭을 보인다. 반쪽만 쓴 관계는 남지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_fail"))
    assert got["state"] == MORE_START
    assert got["diplomacy"]["off:love"] == "관계 최고 — " + VALUES_FAILED and "run:love" not in got["diplomacy"]
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — " + VALUES_FAILED and got["money_off"] == VALUES_FAILED
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (관계 — 폴란드 (1106)) — 값 쓰기를 끕니다") == 1 and "값 쓰기: " not in log


def test_a_moved_button_does_not_write_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 와도, 그 안에서는 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_reenter"))
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [130.0, 130.0]                      # 그 함수 안에서 다시 온 타이머의 앞뒤
    assert got["state"]["tech"] == 131.0                        # 함수가 끝난 뒤에 쓴다


def test_moved_buttons_do_not_write_after_the_fault_guard_trips(dll, cfg, tmp_path):
    """직접 실행의 오류 가드가 걸린 뒤에는 값 쓰기도 멈춘다 — 대기열에 먼저 들어와 있던 요청도 버린다."""
    got = json.loads(_probe(cfg, tmp_path, "more_fault"))
    assert got["fault"] == FAULT_WARNING and got["state"] == MORE_START
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "값 쓰기: " not in log


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
물자 탭이 창 안에 들어오는가 (출력은 JSON 한 줄):
```

이것을 더한다:

```python
직접 쓰는 줄 넷 — 내장 치트를 거치지 않고 기술 수준 · 세계 시장 여론 · 관계를 고친다 (출력은 JSON 한 줄):
    more             게임 안에서 "지식 순위 올리기" 두 번, "세계 시장 여론 최고", (나라를 고르기 전과 뒤에) "관계 최고", "관계 중립"
    more_alone       같은 일을, 국고 · 재고의 자리를 찾지 못한 게임에서 — 묶음은 서로 기대지 않는다
    more_menu        메뉴에 있다 — 단추가 꺼져 있다
    more_leave       단추를 누른 뒤 쓰기 전에 게임에서 나간다 — 쓰지 않고 버린다. 돌아오면 다시 된다
    more_notfound    기술 수준의 자리만 찾지 못한 게임 — 그 줄에만 까닭이 보이고 나머지 줄은 그대로다
    more_write_off   SRTOYBOX_WRITE=0 — 네 줄 모두 까닭만 보인다. 내장 치트로 도는 줄은 그대로다
    more_unread      SRTOYBOX_READ=0 — 〃
    more_repick      폴란드를 골라 "관계 최고"를 누르고, 쓰이기 전에 덴마크로 바꿔 고른다 — 누른 때의 나라(폴란드)에 쓴다
    more_fail        고른 나라의 객체가 읽기 전용 쪽에 있다 — 쓰기가 실패하고, 값 쓰기 전체가 꺼진다
    more_reenter     옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 온다 — 그 안에서는 쓰지 않는다
    more_fault       옮기지 않은 기능의 직접 실행이 죽는다(오류 가드) — 함께 대기열에 있던 요청을 쓰지 않는다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    confirm_fault    같은 탭에서 직접 실행이 죽는다 — 경고가 스크롤을 내려도 보인다
    hints            메뉴에 있을 때와 게임 안에 있을 때의 바닥 안내
    leave            직접 실행: 단추를 누른 뒤 실행되기 전에 게임에서 나간다 — 부르지 않고, 돌아오면 다시 된다
    multiplayer      직접 실행: 단추를 누른 뒤 실행되기 전에 멀티플레이 표시가 선다
    pick_gone        폴란드를 고른 뒤 폴란드가 이번 판에서 없어진다 — 고른 것이 풀린다
    pick_become      폴란드를 고른 뒤 플레이하는 나라가 폴란드가 된다 — 고른 것이 풀린다
```

이렇게 바꾼다:

```python
    confirm_fault    같은 탭에서 직접 실행("동맹 맺기")이 죽는다 — 경고가 스크롤을 내려도 보인다
    hints            메뉴에 있을 때와 게임 안에 있을 때의 바닥 안내
    leave            직접 실행: 단추를 누른 뒤 실행되기 전에 게임에서 나간다 — 부르지 않고, 돌아오면 다시 된다
    multiplayer      직접 실행: 단추를 누른 뒤 실행되기 전에 멀티플레이 표시가 선다
    pick_gone        폴란드를 골라 "관계 최고"를 누른 뒤 폴란드가 이번 판에서 없어진다 — 고른 것이 풀리고 단추가 꺼진다
    pick_become      폴란드를 골라 "관계 최고"를 누른 뒤 플레이하는 나라가 폴란드가 된다 — 〃
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
from toybox_fake_game import MULTIPLAYER, OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)
```

이렇게 바꾼다:

```python
from toybox_fake_game import MORE, MULTIPLAYER, OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
def fake_game(hook: str, handler: int | None = None, values: bool = True) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106. 국고 $5 B)와 독일(176, 1499. 국고 $14.43 B)이 있고 메뉴 상태다.

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    values 가 False 면 값의 자리를 찾지 못한 게임이다(돈 탭이 꺼진다).
```

이렇게 바꾼다:

```python
def fake_game(hook: str, handler: int | None = None, values: bool = True, more: dict | None = MORE) -> FakeGame:
    """ToyBox 가 보는 "게임"을 가짜 메모리로 바꾼다. 폴란드(141, 1106. 국고 $5 B)와 독일(176, 1499. 국고 $14.43 B)이 있고 메뉴 상태다.
    기술 수준은 독일 130 · 폴란드 128, 독일의 여론 세 칸은 0.5 · 0.25 · 0.75, 독일 → 폴란드의 관계는 0.25 · -0.5(전쟁 명분 0.75),
    폴란드 → 독일은 0.125 · 0.5(전쟁 명분 1).

    handler 는 명령 처리 함수 자리에 둘 함수의 주소(없으면 직접 실행을 쓰는 테스트가 아니다).
    values 가 False 면 값의 자리를 찾지 못한 게임이다(돈 탭이 꺼진다).
    more 는 더 쓰는 값의 자리다 — 자리를 0 으로 둔 묶음은 못 찾은 것이 된다. None 이면 모두 못 찾은 게임이다.
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    fake = FakeGame()
```

이것을 더한다:

```python
    toybox.srtoybox_test_more.argtypes = [ctypes.c_void_p]
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    if values:
        toybox.srtoybox_test_values(ctypes.byref(fake.layout))
```

이렇게 바꾼다:

```python
    fake.set_tech(141, 128.0)
    fake.set_tech(176, 130.0)
    fake.set_opinion(176, (0.5, 0.25, 0.75))
    fake.set_relation(176, 141, (0.25, -0.5, 0.75))
    fake.set_relation(141, 176, (0.125, 0.5, 1.0))
    toybox.srtoybox_test_game(fake.base, ctypes.byref(fake.at), handler)
    if values:
        toybox.srtoybox_test_values(ctypes.byref(fake.layout))
    if more is not None:
        toybox.srtoybox_test_more(ctypes.byref(type(fake.more)(**more)))
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    elif mode == "confirm_fault":
        game.click("run:love")
```

이렇게 바꾼다:

```python
    elif mode == "confirm_fault":
        game.click("run:treaty")                              # 아직 내장 치트로 도는 줄 — 명령 처리 함수가 죽는다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
        game.click("run:love")
        game.wait(0.3)
        out["first"] = list(lines)
```

이렇게 바꾼다:

```python
        game.click("run:love")                                # 직접 쓰는 줄: 폴란드와의 관계를 쓴다
        game.wait(0.3)
        out["first"] = [fake.relation(176, 141), fake.relation(141, 176)]
        fake.set_relation(176, 141, (0.25, -0.5, 0.75))       # 되돌려 둔다 — 뒤의 누름이 다시 쓰면 알아본다
        fake.set_relation(141, 176, (0.125, 0.5, 1.0))
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    elif mode == "pick_again":
```

이것을 더한다:

```python
        out["later"], out["unwritten"] = [fake.relation(176, 141), fake.relation(141, 176)], game.shown("unwritten")
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
def run_layout(hook: str, mode: str) -> int:
```

이것을 더한다:

```python
RESEARCH, PEOPLE = "tab:연구", "tab:인구·여론"


def run_more(hook: str, mode: str) -> int:
    """직접 쓰는 줄 넷: 내장 치트를 거치지 않고 기술 수준 · 세계 시장 여론 · 관계를 고친다. 출력은 JSON 한 줄(보이지 않는 글은 "-").

    fake_game 의 게임에 덴마크(150, 1201)를 더했다. 독일 ↔ 덴마크의 관계는 모두 0.5 다.
    """
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
        elif mode == "more_reenter":                          # 게임의 함수가 일하는 도중에 ToyBox 의 타이머가 다시 온다
            inside.append(box["fake"].tech(176))
            user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)
            inside.append(box["fake"].tech(176))

    game.handler = HANDLER(body)                              # 게임이 살아 있는 동안 붙들어 둔다
    handler = crash_stub() if mode == "more_fault" else ctypes.cast(game.handler, ctypes.c_void_p).value
    fake = box["fake"] = fake_game(hook, handler, values=mode != "more_alone",
                                   more={**MORE, "tech": 0} if mode == "more_notfound" else MORE)
    fake.region(150, 1201, alive=3)
    fake.set_relation(176, 150, (0.5, 0.5, 0.5))
    fake.set_relation(150, 176, (0.5, 0.5, 0.5))
    if mode == "more_fail":
        fake.lock(141)                                        # 폴란드의 객체가 읽기 전용 쪽에 있다(읽을 수는 있다)
    if mode != "more_menu":
        fake.play(176)
    game.hotkey()
    game.got.clear()
    out: dict[str, object] = {}

    def seen(tab: str) -> dict[str, str]:
        """그 탭에 그려진 줄들을 그린 순서대로: "run:<id>" 는 단추(글은 이름), "off:<id>" 는 단추 대신 나온 까닭 한 줄."""
        game.click(tab)
        facts = game.facts()
        return {name: facts[name][3] for name in facts if name.startswith(("run:", "off:"))}

    def state() -> dict[str, object]:
        return {"tech": fake.tech(176), "opinion": fake.opinion(176), "poland": [fake.relation(176, 141), fake.relation(141, 176)],
                "denmark": [fake.relation(176, 150), fake.relation(150, 176)]}

    def press(name: str) -> None:
        game.click(name)
        game.wait(0.2)                                        # 쓰는 것은 다음 타이머에서다

    if mode in ("more", "more_alone", "more_notfound", "more_write_off", "more_unread", "more_menu"):
        out["research"] = seen(RESEARCH)
        if "run:finalexam" in out["research"]:
            press("run:finalexam")
            press("run:finalexam")
        out["wrote_tech"] = game.shown("wrote")
        out["people"] = seen(PEOPLE)
        if "run:shelovesme" in out["people"]:
            press("run:shelovesme")
        out["wrote_opinion"] = game.shown("wrote")
        out["diplomacy"] = seen(DIPLOMACY)
        if "run:love" in out["diplomacy"]:
            press("run:love")                                 # 아직 나라를 고르지 않았다 — 단추가 꺼져 있다
            out["unpicked"] = state()
            game.wait(1.2)                                    # 나라 목록은 1초마다 읽는다
            if mode != "more_menu":
                game.click("row:1106")
            press("run:love")
            out["after_love"], out["wrote_love"] = state(), game.shown("wrote")
            press("run:neutral")
            out["wrote_neutral"] = game.shown("wrote")
        out["hint"], out["status"] = game.shown("hint"), game.shown("status")
    elif mode == "more_leave":
        game.click(RESEARCH)
        game.click("run:finalexam")                           # 눌렀다. 쓰는 것은 다음 타이머에서다(메시지를 돌릴 때 온다)
        fake.menu()                                           # 그 전에 게임에서 나갔다
        game.wait(0.3)
        out["dropped"], out["unwritten"] = fake.tech(176), game.shown("unwritten")
        fake.play(176)
        press("run:finalexam")                                # 돌아오면 다시 된다
        out["unwritten_after"] = game.shown("unwritten")
    elif mode == "more_repick":
        game.click(DIPLOMACY)
        game.wait(1.2)                                        # 나라 목록은 1초마다 읽는다
        game.click("row:1106")
        game.click("run:love")                                # 눌렀다. 쓰는 것은 다음 타이머에서다(메시지를 돌릴 때 온다)
        game.click("row:1201")                                # 그 전에 덴마크로 바꿔 골랐다
        game.wait(0.3)
        out["picked"], out["wrote"] = game.shown("picked"), game.shown("wrote")
    elif mode == "more_fail":
        game.click(DIPLOMACY)
        game.wait(1.2)
        game.click("row:1106")
        press("run:love")
        out["diplomacy"] = seen(DIPLOMACY)
        out["research"] = seen(RESEARCH)
        game.click(MONEY)
        out["money_off"] = game.shown("money:off")
    elif mode in ("more_reenter", "more_fault"):
        game.click(CHEAT_TAB)
        game.click(BUTTON)                                    # 옮기지 않은 기능 하나(직접 실행)가 대기열에 든다
        game.click(RESEARCH)
        game.click("run:finalexam")                           # 기술 수준의 요청도 대기열에 든다
        game.wait(0.5)
        out["inside"], out["fault"] = inside, game.shown("fault")
    out["state"], out["lines"], out["text"], out["options"] = state(), lines, game.text(), fake.peek(OPTIONS, "<I")
    out["treasury"] = fake.treasury(176)
    print(json.dumps(out, ensure_ascii=False))
    return 0


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    if mode.startswith("stock"):
```

이것을 더한다:

```python
    if mode.startswith("more"):
        return run_more(hook, mode)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox.py -q 2>&1 | tail -4`

Expected: `14 failed, 70 passed` — 실패하는 것: `test_feature_table` · `test_only_cheats_that_were_seen_working_and_reach_what_the_user_chose`(기능 표의 줄에 아직 열두째 칸이 없다 — `ValueError: not enough values to unpack`) · `test_command_text` · `test_the_pick_is_dropped_when_that_country_can_no_longer_be_a_target` 둘 · 새 테스트 아홉. **이미 통과하는 것이 셋 있다**: 새 테스트 `test_the_moved_buttons_are_off_outside_a_game` · `test_moved_buttons_do_not_write_after_the_fault_guard_trips` 와 고친 `test_the_fault_warning_stays_in_sight` — 메뉴에서 꺼져 있는 것, 오류 가드 뒤에 쓰지 않는 것은 내장 치트로 돌던 때에도 참이다(옮긴 뒤에도 지켜지는지를 보는 테스트다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/command.cpp` 에서 다음 바로 앞에:

```cpp
    std::string out = f.command;
```

이것을 더한다:

```cpp
    if (f.direct != Direct::None)
        return std::string();
```

`native/srtoybox/command.h` 에서 다음 바로 앞에:

```cpp
std::string build_command(const Feature &f, long long value, int region);
```

이것을 더한다:

```cpp
// 직접 쓰는 줄(f.direct)은 게임에 넣을 글이 없다 — 늘 빈 글이다.
```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명, 대상(none/player/picked) — 탭 문자로 나눈다
```

이렇게 바꾼다:

```cpp
EXPORT int srtoybox_cheat_feature_count(void)
{
    return cheat_feature_count();
}

// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명, 대상(none/player/picked),
// 하는 길(cheat = 내장 치트 / tech_up · opinion_best · relation_best · relation_neutral = 직접 쓴다) — 탭 문자로 나눈다
```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help + '\t' + targets[static_cast<int>(f.target)];
```

이렇게 바꾼다:

```cpp
    static const char *const how[] = {"cheat", "tech_up", "opinion_best", "relation_best", "relation_neutral"};
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help + '\t' + targets[static_cast<int>(f.target)] + '\t'
        + how[static_cast<int>(f.direct)];
```

`native/srtoybox/features.cpp` 에서 다음을 찾아:

```cpp
// 남은 줄은 아직 내장 치트로 돈다. 묶음마다 옮기고 지운다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다", "cheat technology", true, 120, 1, 999, false},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 연구가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "cheat e=mc2", false, 0, 0, 0, false},
    {"finalexam", "연구", "지식 순위 올리기", "지식 지수 순위가 오른다", "cheat finalexam", false, 0, 0, 0, false},
    {"populate", "인구·여론", "인구 +100만", "인구가 100만 늘어난다", "cheat populate", false, 0, 0, 0, false},
    {"shelovesme", "인구·여론", "세계 시장 여론 최고", "세계 시장 여론과 보조금률이 최고가 된다", "cheat shelovesme", false, 0, 0, 0, false},
    {"approval", "인구·여론", "내 나라 지지율 100%", "국내 지지율이 100% 가 된다", "cheat approval", false, 0, 0, 0, false, Target::Player},
    {"love", "외교·영토", "관계 최고", "고른 나라와의 외교 · 민간 관계가 가득 차고 전쟁 명분이 0 이 된다", "cheat love", false, 0, 0, 0, false, Target::Picked},
    {"neutral", "외교·영토", "관계 중립", "고른 나라와의 관계가 절반이 되고 전쟁 명분이 0 이 된다", "cheat neutral", false, 0, 0, 0, false, Target::Picked},
```

이렇게 바꾼다:

```cpp
// 네 줄(finalexam · shelovesme · love · neutral)은 3단계 2 에서 직접 쓰기로 바꿨다 — 자리와 이름은 그대로이고
// 게임에 넣는 글이 없다(ui.cpp 의 direct_row).
// 나머지 줄은 아직 내장 치트로 돈다. 묶음마다 옮긴다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다", "cheat technology", true, 120, 1, 999, false},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 연구가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "cheat e=mc2", false, 0, 0, 0, false},
    {"finalexam", "연구", "지식 순위 올리기", "지식 지수 순위가 오른다", "", false, 0, 0, 0, false, Target::None, Direct::TechUp},
    {"populate", "인구·여론", "인구 +100만", "인구가 100만 늘어난다", "cheat populate", false, 0, 0, 0, false},
    {"shelovesme", "인구·여론", "세계 시장 여론 최고", "세계 시장 여론과 보조금률이 최고가 된다", "", false, 0, 0, 0, false, Target::None,
     Direct::OpinionBest},
    {"approval", "인구·여론", "내 나라 지지율 100%", "국내 지지율이 100% 가 된다", "cheat approval", false, 0, 0, 0, false, Target::Player},
    {"love", "외교·영토", "관계 최고", "고른 나라와의 외교 · 민간 관계가 가득 차고 전쟁 명분이 0 이 된다", "", false, 0, 0, 0, false, Target::Picked,
     Direct::RelationBest},
    {"neutral", "외교·영토", "관계 중립", "고른 나라와의 관계가 절반이 되고 전쟁 명분이 0 이 된다", "", false, 0, 0, 0, false, Target::Picked,
     Direct::RelationNeutral},
```

`native/srtoybox/features.cpp` 에서 다음 바로 앞에:

```cpp
const Feature *find_feature(const char *id)
```

이것을 더한다:

```cpp
int cheat_feature_count()
{
    int count = 0;
    for (int i = 0; i < FEATURE_COUNT; i++)
        count += FEATURES[i].direct == Direct::None ? 1 : 0;
    return count;
}

```

`native/srtoybox/features.h` 에서 다음 바로 앞에:

```cpp
#pragma once
```

이것을 더한다:

```cpp
// 줄은 두 가지다: 아직 내장 치트로 도는 줄(command 를 게임에 넣는다)과, ToyBox 가 값을 직접 쓰는 줄(direct — 3단계 2 부터).
// 직접 쓰는 줄은 자리와 이름만 표에 두고, 하는 일은 keeper 의 요청이다 — 내장 치트를 거치지 않는다.
```

`native/srtoybox/features.h` 에서 다음을 찾아:

```cpp
struct Feature {
    const char *id;       // 치트 이름. 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다
    bool has_value;
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
    Target target;        // 명령 뒤에 붙일 지역
```

이렇게 바꾼다:

```cpp
// 내장 치트를 거치지 않고 ToyBox 가 직접 쓰는 일의 종류. None 이면 아직 내장 치트로 도는 줄이다.
enum class Direct {
    None,
    TechUp,            // 플레이어의 기술 수준 +1
    OpinionBest,       // 플레이어의 세계 시장 여론 세 칸을 최고로
    RelationBest,      // 고른 나라와의 관계 최고, 전쟁 명분 0(양쪽 객체에)
    RelationNeutral,   // 고른 나라와의 관계 중립, 전쟁 명분 0(〃)
};

struct Feature {
    const char *id;       // 치트 이름(직접 쓰는 줄은 그 일을 하던 치트의 이름). 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다. 직접 쓰는 줄은 빈 글이다
    bool has_value;
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
    Target target;        // 명령 뒤에 붙일 지역(직접 쓰는 줄: Picked 면 고른 나라가 대상이다)
    Direct direct;        // 직접 쓰는 일
```

`native/srtoybox/features.h` 에서 다음 바로 뒤에:

```cpp
extern const int FEATURE_COUNT;
```

이것을 더한다:

```cpp
int cheat_feature_count();   // 아직 내장 치트로 도는 줄의 수
```

`native/srtoybox/game.cpp` 에서 다음을 찾아:

```cpp
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", FEATURE_COUNT, at.handler);
```

이렇게 바꾼다:

```cpp
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", cheat_feature_count(), at.handler);
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
void row(const Feature &f, const GameState &game)
{
```

이렇게 바꾼다:

```cpp
// 직접 쓰는 줄(3단계 2): 내장 치트를 거치지 않는다 — 누르면 값 쓰기 요청을 대기열에 넣고, 쓰는 것은 게임 창의 타이머에서다(keeper.h).
// 쓸 수 없으면 단추 자리에 까닭 한 줄만 그린다(그 줄에만. 같은 탭의 다른 줄은 그대로다). 내장 치트로 되돌아가지 않는다.
void direct_row(const Feature &f, const GameState &game)
{
    const int group = f.direct == Direct::TechUp ? MORE_TECH : f.direct == Direct::OpinionBest ? MORE_OPINION : MORE_RELATIONS;
    const std::string off = game.known ? game_more_off(group) : std::string("게임 상태를 읽을 수 있을 때만 씁니다.");
    ImGui::PushID(f.id);
    if (!off.empty()) {
        const std::string line = std::string(f.label) + " — " + off;
        ImGui::TextWrapped("%s", line.c_str());
        note(std::string("off:") + f.id, line);
    } else {
        ImGui::BeginDisabled(f.target == Target::Picked && g_picked <= 0);   // 나라를 고르지 않았다
        const bool pressed = ImGui::Button((std::string(f.label) + "###run").c_str());
        note(std::string("run:") + f.id, f.label);
        if (pressed) {
            Request request = {TECH, Change::Set, 0.0, 0};
            if (f.direct == Direct::OpinionBest)
                request.slot = OPINION;
            else if (f.direct != Direct::TechUp)
                request = {RELATION, Change::Set, f.direct == Direct::RelationBest ? 1.0 : 0.0, g_picked};
            g_confirm.clear();
            g_notice = keeper_enqueue(request) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
        }
        ImGui::EndDisabled();
    }
    ImGui::TextDisabled("%s", f.help);
    ImGui::Spacing();
    ImGui::PopID();
}

void row(const Feature &f, const GameState &game)
{
    if (f.direct != Direct::None) {
        direct_row(f, game);
        return;
    }
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `84 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/features.h native/srtoybox/features.cpp native/srtoybox/command.h native/srtoybox/command.cpp native/srtoybox/game.cpp native/srtoybox/exports.cpp native/srtoybox/ui.cpp tests/test_toybox.py tests/toybox_overlay_probe.py && git commit -q -F - <<'EOF'
feat: ToyBox — 지식 순위 · 세계 시장 여론 · 관계 최고 · 관계 중립이 내장 치트 없이 동작한다

- 기능 표의 네 줄이 "게임에 넣는 글" 대신 "직접 쓰는 일"(Direct)을 갖는다. 단추의 이름 · 탭 · 자리는 그대로다.
  내장 치트로 도는 줄은 19 → 15(로그의 "옛 방식 …개 남아 있습니다").
- 누르면 값 쓰기 요청을 대기열에 넣는다 — 명령 처리 함수를 부르지 않고, 글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다.
- 쓸 수 없으면 그 단추의 자리에 까닭 한 줄만 보인다(그 줄에만). 내장 치트로 되돌아가지 않는다.
- 화면 테스트 둘을 맞췄다: 오류 가드의 경고는 "동맹 맺기"로, 고른 나라가 풀리는 것은 관계의 칸으로 본다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `417 passed`, 새 커밋.

---

### Task 5: 검증 도구 — `gamedrive.py peek` 이 새 값을 읽는다

**브랜치:** `feat/toybox-values-more`

**Files:**
- Modify: `scripts/gamedrive.py`
- Test: `tests/test_gamedrive.py`

**Interfaces:**
- Consumes: Task 1 의 `Located.more`(`toybox.locate(cfg).more` — 이름 → 자리, 못 찾은 묶음은 0), Task 2 의 `toybox_fake_game.MORE` · `FakeGame` 의 새 칸. `peek_game` 안의 `read(주소, 형식)`.
- Produces:
  - `peek_more(read, more: dict[str, int], player: int, me: int, who: int) -> dict` — `{"tech": …, "opinion": [a, b, c], "relations": {"mine": [표 1, 표 2, 전쟁 명분], "theirs": […]}}`. `relations` 는 `who` 가 플레이어가 아닐 때만, 못 찾은 묶음의 것은 없다.
  - `gamedrive.py peek` 의 출력에 `tech` · `opinion` 이, `peek <지역 번호>` 의 출력에 `relations` 가 더해진다. Task 6 의 게임 안 확인이 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_gamedrive.py` 에서 다음 바로 뒤에:

```python
    assert "앞 창 잠금" in capsys.readouterr().out
```

이것을 더한다:

```python


def test_peek_reads_tech_opinion_and_the_relation_with_one_region(gd):
    """peek 은 더 쓰는 값도 읽는다: 그 지역의 기술 수준 · 여론, 그리고 플레이어가 아닌 지역이면 둘 사이의 관계 여섯 칸.
    못 찾은 묶음(자리 0)의 값은 결과에 없다. 읽기만 한다."""
    import ctypes
    import struct

    from toybox_fake_game import MORE, FakeGame

    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.set_tech(176, 130.0)
    fake.set_tech(141, 128.0)
    fake.set_opinion(176, (0.5, 0.25, 0.75))
    fake.set_relation(176, 141, (0.25, -0.5, 0.75))           # 독일 객체의 표에서 폴란드의 칸
    fake.set_relation(141, 176, (0.125, 0.5, 1.0))            # 폴란드 객체의 표에서 독일의 칸
    before = fake.snapshot(176) + fake.snapshot(141)

    def read(address: int, fmt: str):
        return struct.unpack(fmt, ctypes.string_at(address, struct.calcsize(fmt)))[0]

    germany, poland = fake.where[176], fake.where[141]
    assert gd.peek_more(read, MORE, germany, 176, germany) == {"tech": 130.0, "opinion": [0.5, 0.25, 0.75]}
    assert gd.peek_more(read, MORE, germany, 176, poland) == {
        "tech": 128.0, "opinion": [0.0, 0.0, 0.0], "relations": {"mine": [0.25, -0.5, 0.75], "theirs": [0.125, 0.5, 1.0]}}
    assert gd.peek_more(read, {**MORE, "tech": 0, "relation0": 0}, germany, 176, poland) == {"opinion": [0.0, 0.0, 0.0]}
    assert gd.peek_more(read, dict.fromkeys(MORE, 0), germany, 176, poland) == {}
    assert fake.snapshot(176) + fake.snapshot(141) == before
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_gamedrive.py -q 2>&1 | tail -4`

Expected: `1 failed, 11 passed` — `AttributeError: module 'gamedrive' has no attribute 'peek_more'`.

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`scripts/gamedrive.py` 에서 다음을 찾아:

```python
                                                              # 번호를 주면 플레이어 대신 그 지역의 국고 · 재고를 읽는다
```

이렇게 바꾼다:

```python
                                                              # 번호를 주면 플레이어 대신 그 지역의 국고 · 재고 · 기술 수준 · 여론을 읽고,
                                                              # 플레이어와 그 지역 사이의 관계 여섯 칸도 읽는다
```

`scripts/gamedrive.py` 에서 다음 바로 앞에:

```python
def peek_game(cfg: config.Config, number: int | None = None) -> dict:
```

이것을 더한다:

```python
def peek_more(read, more: dict[str, int], player: int, me: int, who: int) -> dict:
    """더 쓰는 값(기술 수준 · 세계 시장 여론 · 관계)을 읽는다(읽기만). 못 찾은 묶음(자리 0)의 것은 결과에 없다.

    read(주소, 형식) 은 값 하나를 읽는 함수, more 는 srkit.toybox.locate 가 찾은 자리. who 는 값을 읽을 지역 객체,
    player 는 플레이어의 지역 객체, me 는 플레이어의 인덱스다. who 가 플레이어가 아니면 둘 사이의 관계도 읽는다:
    mine 은 플레이어 객체의 표에서 그 지역의 칸, theirs 는 그 지역 객체의 표에서 플레이어의 칸 — 저마다 [관계 표 1, 관계 표 2, 전쟁 명분].
    """
    out: dict = {}
    if more["tech"]:
        out["tech"] = read(who + more["tech"], "<f")
    if more["opinion0"]:
        out["opinion"] = [read(who + more[name], "<f") for name in ("opinion0", "opinion1", "opinion2")]
    if more["relation0"] and who != player:
        them = read(who + 4, "<H")
        tables = ("relation0", "relation1", "casus")
        out["relations"] = {"mine": [read(player + more[name] + 4 * them, "<f") for name in tables],
                            "theirs": [read(who + more[name] + 4 * me, "<f") for name in tables]}
    return out


```

`scripts/gamedrive.py` 에서 다음을 찾아:

```python
    number 를 주면 국고 · 재고를 플레이어 대신 그 번호의 지역 객체에서 읽는다(지역 표에서 찾는다. 결과의 region 이 그 번호다) —
    플레이하는 나라를 바꾼 뒤 앞 나라의 값이 그대로인지 볼 때 쓴다.
```

이렇게 바꾼다:

```python
    number 를 주면 국고 · 재고 · 기술 수준 · 여론을 플레이어 대신 그 번호의 지역 객체에서 읽고(지역 표에서 찾는다. 결과의 region 이
    그 번호다), 플레이어와 그 지역 사이의 관계(relations)도 읽는다 — 플레이하는 나라를 바꾼 뒤 앞 나라의 값이 그대로인지,
    관계의 단추가 양쪽 객체에 썼는지 볼 때 쓴다.
```

`scripts/gamedrive.py` 에서 다음 바로 뒤에:

```python
                           for i in range(toybox.STOCK_SLOTS)] if world else None
```

이것을 더한다:

```python
            out.update(peek_more(read, found.more, player, out["player_index"], who))
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 통과를 본다**

Run: `uv run pytest tests/test_gamedrive.py -q 2>&1 | tail -1`

Expected: `12 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add scripts/gamedrive.py tests/test_gamedrive.py && git commit -q -F - <<'EOF'
chore: gamedrive.py peek — 기술 수준 · 여론 · 한 지역과의 관계도 읽는다(검증용, 읽기만)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `418 passed`, 새 커밋.

---

### Task 6: 게임 안 확인(W0 ~ W9) · 코드의 최종 검토 · 머지

**브랜치:** `feat/toybox-values-more` (게임이 떠 있는 동안 바꾸지 않는다)

**Files:**
- Modify(조건부, Step 5): `native/srtoybox/features.cpp` 의 한 줄(설명 글).
- 그 밖의 코드는 최종 검토의 지적을 고칠 때만 고친다. 근거 화면과 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.

**Interfaces:**
- Consumes: Task 1 ~ 5 의 빌드, `gamedrive.py peek`(`tech` · `opinion` · `relations` · `cheats_allowed` · `player` · `in_game`).
- Produces: 이 Task 의 결과(스크래치의 `w-more.md` — Task 7 이 `docs/10` 에 적는다)와 `develop` 에 머지된 PR.

**이 Task 가 가르는 것**: 설계의 전제 — ToyBox 가 그 칸들에 직접 쓴 뒤의 게임 화면이 치트를 넣었을 때([docs/07](../../07-cheats.md))와 같은가. 다르면 머지하지 않고 멈춘다.

- [ ] **Step 1: PR 을 올린다 (머지는 게임 안 확인과 최종 검토 뒤에)**

스크래치에 `pr-values-more.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 1 ~ 5 의 커밋 요약), **쓰는 곳이 늘어난 것**(관계는 고른 나라의 객체에도 쓴다 — 설계서의 결정), 요구 2 · 3 에 대해 자동 테스트가 보는 것(명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다 · 정해진 칸만 바뀐다 · 없는 나라 · 자기 나라에는 쓰지 않는다 · 묶음마다 따로 꺼진다), 설계서와 달라진 곳(이 계획의 같은 이름의 절), "게임 안 확인과 최종 검토의 결과는 아래 댓글에", `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-values-more && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-values-more --title "feat: ToyBox — 지식 순위 · 세계 시장 여론 · 관계를 내장 치트 없이 직접 쓴다" --body-file "<스크래치>/pr-values-more.md"
```

- [ ] **Step 2: 시험용 빌드를 게임 폴더에 바꿔 넣고, 검증 전의 상태를 적어 둔다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-w && rm -f build/verify/toybox-home-w/* && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/W-saves-before.txt && cat build/verify/toybox/W-saves-before.txt && uv run python -c "import hashlib, os, pathlib; p = pathlib.Path(os.environ['APPDATA'], 'SR2030ToyBox', 'toybox.ini'); print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'none')" > build/verify/toybox/W-ini-before.txt && cat build/verify/toybox/W-ini-before.txt
```

`build/verify/toybox-home-w` 는 검증용 게임의 ToyBox 설정 폴더다(비어 있으므로 단축키는 기본값 `Ctrl+Shift+T`, 최소 유지는 모두 꺼짐). 사용자의 `%APPDATA%\SR2030ToyBox` 는 건드리지 않는다 — 끝난 뒤 저장 폴더의 목록과 설정 파일의 해시(없으면 `none`)가 그대로인지 본다.

- [ ] **Step 3: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)의 단추 넷 — "지식 순위 올리기", "세계 시장 여론 최고", "관계 최고", "관계 중립" — 을 게임에서 확인한다.
이 작업(W)만 수행하라. 끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다). uv run pytest 를 돌리지 말라.
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 읽는다: E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법), E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법"과 "확인한 것"의 H5(관계 막대를
본 방법) · VB · VC 표(게임에 들어가는 길, 시간을 흘리는 법, 나라를 고르는 법), E:\SR2030ToyBox\docs\07-cheats.md 의 finalexam · shelovesme · love · neutral 줄과
그 표 위의 "관계 수치는 화면에 나오지 않는다 …" 줄.

규칙:
- 게임은 다음으로만, 한 번만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-w' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  start 의 출력을 그대로 적는다. "돌려주지 못함 N회" 나 "게임이 포커스를 쥐고 있음" 이 나오면 바로 stop 으로 게임을 끄고 보고한다.
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|peek|stop> …
- gamedrive.py peek 은 게임의 메모리에서 읽은 값을 JSON 으로 낸다(읽기만): in_game, player(플레이하는 나라의 번호), cheats_allowed(치트 허용 비트),
  tech(기술 수준), opinion(세계 시장 여론의 세 칸), treasury, stock.
  peek <지역 번호> 는 그 지역의 tech · opinion 과, 플레이어와 그 지역 사이의 relations 를 낸다:
  relations.mine = 플레이어 객체의 그 지역 칸 [관계 표 1, 관계 표 2, 전쟁 명분], relations.theirs = 그 지역 객체의 플레이어 칸(같은 순서).
  독일 1499, 폴란드 1106, 덴마크 1201. ToyBox 의 창에 보이는 글과 따로, 메모리의 값은 이것으로 본다.
- 화면 밖 게임에 보낸 조합키(key CTRL+SHIFT+T)가 듣지 않으면 한 번 더 보낸다(화면을 찍어 창이 열렸는지 본다).
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간은 9 에서만, 거기 적힌 만큼만 흘린다. 그 밖에는 일시 정지인 채로 둔다.
- cheat resettutorial · cheat depopulate 는 어떤 경우에도 넣지 않는다. ToyBox 에서는 아래에 적힌 단추만 누른다.
- ToyBox 창은 처음에 화면의 왼쪽 위(40,60)에 720x600 으로 열린다. 게임의 패널을 가리면 창을 닫고(같은 단축키) 본다.
- 화면은 E:\SR2030ToyBox\build\verify\toybox\W-<번호>-<이름>.png 로 찍는다. ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-w\toybox.log 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다. peek 의 출력은 그대로 옮긴다):
1. 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다(20초쯤. 빈 화면이면 기다렸다 다시 찍는다).
   로그에서 "게임 상태를 읽습니다 (…)", "값을 씁니다 (…)", "값을 더 씁니다 (…)", "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (…)" 네 줄을 그대로 옮겨 적는다
   (기능의 수는 15 여야 한다). "쓸 수 없습니다" 나 "맞지 않은 서명" 이 든 줄이 있으면 그대로 옮긴다(없어야 한다).
2. 메인 메뉴에서 ToyBox 창을 열고 "연구" 탭, "인구·여론" 탭, "외교·영토" 탭을 차례로 연다. 탭마다 단추의 이름을 위에서부터 적고,
   "지식 순위 올리기" · "세계 시장 여론 최고" · "관계 최고" · "관계 중립"이 흐린지(꺼져 있는지) 적는다. 앞의 둘을 한 번씩 눌러 보고 로그에 새 줄이 생겼는지 적는다(생기면 안 된다).
3. 창을 닫고, 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 게임 화면이 뜨면 일시 정지 상태인지 본다. 게임의 날짜를 적는다.
   peek (P0), peek 1106 (R0), peek 1201 (D0) 을 찍는다. cheats_allowed 는 0 이어야 한다.
   누르기 전의 게임 화면을 찍는다: (가) 지식 지수 순위가 나오는 화면(07 에서 "지식 지수 순위 6위 → 1위"를 본 화면. 연구 쪽 패널이나 나라의 순위 화면에서 찾는다 —
   찾지 못하면 찾아본 곳을 적는다). 기술 수준이나 연도로 보이는 숫자가 그 근처에 있으면 그것도 적는다.
   (나) 세계 시장 여론, 보조금률, 조약 신뢰도가 나오는 화면(국무 · 외교 쪽 패널). 세 숫자(글)를 적는다.
   (다) 외교 패널에서 폴란드를 고른 화면과 관계 툴팁의 막대(외교 · 민간), 전쟁 명분. 덴마크도 같은 방법으로 찍는다.
4. [W2] ToyBox 의 "연구" 탭에서 "지식 순위 올리기"를 한 번 누른다. peek 의 tech 가 P0 보다 정확히 1.0 큰지, 창 바닥의 "마지막으로 쓴 값: …" 을 적는다.
   두 번 더 누르고 peek 을 찍는다(모두 3.0 늘어야 한다). 창을 닫고 3 의 (가) 화면을 다시 찍는다 — 순위가 어떻게 바뀌었는지 적는다
   (숫자가 그대로면 그 패널을 닫았다 다시 연다. 그래도 그대로면 그대로라고 적는다).
   tech 의 값이 얼마인지 적는다: 게임의 해(예: 2030)에서 1900 을 뺀 수 근처인가.
5. [W3] "인구·여론" 탭에서 "세계 시장 여론 최고"를 한 번 누른다. peek 의 opinion 이 [1.0, 1.0, 1.0] 인지, "마지막으로 쓴 값" 을 적는다.
   창을 닫고 3 의 (나) 화면을 다시 찍는다: 세계 시장 여론, 보조금률, 조약 신뢰도. 07 의 shelovesme("매우 기쁨", 보조금률 100%, 조약 신뢰도 92.5%)와 견준다.
   P0 의 opinion 세 값과 3 에서 본 세 숫자를 나란히 적는다(어느 칸이 어느 숫자인지 짐작할 수 있으면 근거와 함께. 짐작이 안 되면 그렇게 적는다).
6. [W4] "외교·영토" 탭의 검색란에 pol 을 치고 목록에서 "폴란드 (1106)" 를 고른다("고른 나라: 폴란드 (1106)" 가 보여야 한다). "관계 최고"를 누른다.
   peek 1106 의 relations 가 mine [1.0, 1.0, 0.0], theirs [1.0, 1.0, 0.0] 인지, "마지막으로 쓴 값" 을 적는다. peek 1201 을 찍어 D0 의 relations 와 같은지 적는다(같아야 한다).
   창을 닫고 3 의 (다) 화면(폴란드)을 다시 찍는다: 두 막대가 가득 찼는가, 전쟁 명분이 0 인가.
   R0 의 relations 와 3 에서 본 막대를 나란히 적는다(어느 표가 외교이고 어느 표가 민간인지 짐작할 수 있으면 근거와 함께).
7. [W5] "관계 중립"을 누른다. peek 1106 의 relations 가 모두 0.0 인지 적고, 폴란드의 화면을 다시 찍는다(막대가 절반인가). peek 1201 은 여전히 D0 와 같은가.
8. [W7] 4 ~ 7 에서 찍은 모든 peek 의 cheats_allowed 가 0 이었는지 적는다. 게임의 설정 창(치트를 넣는 입력줄이 있는 창)이 한 번이라도 떴는지 적는다(뜨면 안 된다).
9. [W8] "관계 최고"를 한 번 더 눌러 폴란드와의 관계를 최고로 둔 채 ToyBox 창을 닫는다. peek, peek 1106 을 찍는다(T0).
   게임의 속도를 "매우 느림"으로 실제 25초 흘린 뒤 다시 일시 정지한다(게임 날짜가 하루를 넘기지 않게 — 넘길 것 같으면 더 일찍 멈춘다).
   게임이 살아 있는지, 게임의 날짜 · 시각, 화면에 뜬 경고를 적는다. peek, peek 1106 을 찍어 T0 와 견준다: tech, opinion 세 칸, relations 여섯 칸이 그대로인가, 바뀌었으면 얼마나.
10. [W9] ToyBox 창을 열고 "외교·영토" 탭에서 폴란드를 고른 채 맨 아래의 "이 나라로 플레이"를 누른다(되돌릴 수 없는 단추라 두 번 눌러야 한다 — 이것은 아직 내장 치트로 도는 단추다).
    상태 줄이 "플레이 중: 폴란드 (1106)" 가 됐는지 본다. peek (플레이어가 폴란드인 것, opinion 을 적는다 = Q0), peek 1499 (독일의 opinion · tech 를 적는다 = G0).
    "인구·여론" 탭에서 "세계 시장 여론 최고"를 누른다. peek 의 opinion 이 [1.0, 1.0, 1.0] 인지, peek 1499 의 opinion · tech 가 G0 그대로인지 적는다.
    (cheats_allowed 는 "이 나라로 플레이" 뒤로 1 이다 — 그 단추가 내장 치트라서다. 그대로 적는다.)
11. 창을 닫고, 게임의 메뉴(ESC) → "게임 종료" → 저장하지 않고 메인 메뉴로 나온다. gamedrive.py stop 으로 게임을 끈다. status 로 꺼진 것을 확인한다.
    로그를 E:\SR2030ToyBox\build\verify\toybox\W.log 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). peek 의 출력은 줄여 쓰지 말고 그대로. 로그에 "예외" 나 "실패" 가 든 줄이 있으면 그대로 옮긴다.
보지 못한 것은 "보지 못했다"와 까닭(찾아본 곳). 기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않고 `uv run pytest` 를 돌리지 않는다. Step 6 의 최종 검토(읽기만 하는 검토자)는 이 동안 받아도 된다.

- [ ] **Step 4: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "게임 상태를\|값을 \|옛 방식\|쓸 수 없습니다\|맞지 않은\|직접 실행\|예외\|실패" build/verify/toybox/W.log; grep -n "값 쓰기: " build/verify/toybox/W.log; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/W-saves-before.txt && echo "저장 폴더 그대로"; uv run python -c "import hashlib, os, pathlib; p = pathlib.Path(os.environ['APPDATA'], 'SR2030ToyBox', 'toybox.ini'); print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'none')" | diff - build/verify/toybox/W-ini-before.txt && echo "사용자의 설정 그대로"
```

Expected:
- `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`, `값을 씁니다 (국고 +0x14B88, 재고 +0x14DA4 간격 0x150 × 12)`, `값을 더 씁니다 (기술 수준 +0x14CD0 · 세계 시장 여론 +0x14AF4 +0x14AF8 +0x14B10 · 관계 +0x15F10 +0x16F10 전쟁 명분 +0x17F10)`, `옛 방식(내장 치트)으로 도는 기능이 15개 남아 있습니다 (명령 처리 함수 +0x522330)` 가 한 줄씩. `쓸 수 없습니다` · `맞지 않은 서명` · `예외` · `실패` 가 든 줄이 없다.
- `값 쓰기: 기술 수준 …` 셋, `값 쓰기: 세계 시장 여론 최고` 둘(5 와 10), `값 쓰기: 관계 최고 — 폴란드 (1106)` 둘(6 과 9), `값 쓰기: 관계 중립 — 폴란드 (1106)` 하나.
- `직접 실행` 은 10 의 `cheat becomeregion 1106`(과 그 앞의 `cheat allowcheats`)뿐이다.
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-values-more` 다. `저장 폴더 그대로`, `사용자의 설정 그대로`.

Read 도구로 화면을 직접 본다: 4 의 앞뒤(지식 지수 순위), 5 의 앞뒤(세계 시장 여론), 6 · 7 의 폴란드 화면 셋(앞 · 최고 · 중립). 에이전트가 적은 글 · 숫자와 화면이 같은지 본다.

**전제가 틀리면 멈춘다**: 4 ~ 7 에서 메모리의 값은 기대대로인데 게임 화면이 07 의 치트 결과와 다르면(막대가 차지 않는다, 여론이 그대로다) 머지하지 않는다 — 본 것을 그대로 사용자에게 알리고, 치트 본문을 다시 읽는 일은 사용자의 확인 뒤에 한다. peek 의 값이 기대와 다르거나(다른 칸이 바뀌었다, 덴마크의 값이 바뀌었다), 게임이 죽었거나, `값 쓰기 실패` 가 나왔어도 멈춘다. 게임 화면에서 그 숫자를 찾지 못한 단계는 [확인: 실행](메모리의 값만 봤다)으로 적고 이어 간다.

- [ ] **Step 5: (W2 에서 기술 수준임을 봤을 때만) 설명 글을 고친다**

조건: 4 에서 `tech` 가 게임의 해에서 1900 을 뺀 수 근처였고(2030 년 시작이면 130 안팎) 누를 때마다 정확히 1.0 씩 늘었다. 아니면 이 Step 을 건너뛰고 지금 글("지식 지수 순위가 오른다")을 둔다 — 건너뛴 것과 본 값을 `w-more.md` 에 적는다.

`native/srtoybox/features.cpp` 에서 다음을 찾아:

```cpp
    {"finalexam", "연구", "지식 순위 올리기", "지식 지수 순위가 오른다", "", false, 0, 0, 0, false, Target::None, Direct::TechUp},
```

이렇게 바꾼다:

```cpp
    {"finalexam", "연구", "지식 순위 올리기", "기술 수준이 1 오른다 — 지식 지수 순위가 따라 오른다", "", false, 0, 0, 0, false, Target::None, Direct::TechUp},
```

(4 에서 순위가 오르는 것을 화면으로 보지 못했으면 뒤의 "— 지식 지수 순위가 따라 오른다"를 빼고 `"기술 수준이 1 오른다"` 로 적는다.)

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py status | head -1 && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/features.cpp && git commit -q -F - <<'EOF'
fix: ToyBox "지식 순위 올리기"의 설명 — 올리는 것은 기술 수준이다(게임에서 본 대로)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `프로세스: 없음`, `빌드 완료: …`, `418 passed`(설명 글을 보는 테스트는 없다 — 수가 그대로다).

- [ ] **Step 6: 코드의 최종 검토를 받고 고친다**

범위는 이 브랜치가 `develop` 에서 갈라진 곳부터 머리까지다(`git merge-base develop HEAD`). 실행 방식의 최종 검토 절차대로 받는다 — 검토자에게 이 문서의 Review Focus 와 "설계서와 달라진 곳", 설계서, 그리고 게임 안 확인에서 본 것(`w-more.md` 의 초안)을 함께 준다. Critical · Important 를 고친다 — 고칠 때마다 실패하는 테스트를 먼저 쓴다. Minor 는 고치지 않고 적어 둔다.

고친 것이 있으면: `uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -1` 로 통과를 보고 커밋한다. 고친 것이 게임 안의 동작을 바꾸면 Step 3 의 해당 단계만 다시 본다(게임을 한 번 더 띄워야 하므로, 화면만 바뀌는 고침은 자동 테스트로 갈음하고 그렇게 적는다).

- [ ] **Step 7: 최종 빌드를 넣고, 결과를 PR 에 적고, 머지한다**

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py status | head -1 && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -1 && uv run srkit deploy toybox
```

Expected: `프로세스: 없음`, `빌드 완료: …`, 통과. 미리보기는 Step 2 뒤로 코드를 고쳤으면 `갱신: srtoybox.dll` 한 줄(→ `uv run srkit deploy toybox --apply`), 고치지 않았으면 0개 파일이다. 다른 줄이 있으면 멈춘다.

스크래치에 `w-more.md` 를 쓴다(Write 도구): 단계마다 한 것 / 본 것 / 근거 화면의 이름(W0 ~ W9 의 번호로), peek 의 값 그대로, 로그의 줄 그대로, 칸과 화면의 숫자를 견준 것(어느 칸이 무엇인지 — 본 만큼만), 쓴 값이 시간이 흐른 뒤 얼마나 바뀌었는지(W8), 보지 못한 것, 최종 검토의 결과(고친 것 · 미룬 Minor). `gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/w-more.md"` 로 PR 에 단다.

```bash
cd /e/SR2030ToyBox && git push && gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && git switch develop && git pull --ff-only origin develop && git log --oneline -1 && uv run srkit deploy toybox | tail -1
```

Expected: 머지 커밋이 `develop` 의 머리다. 게임 폴더에는 최종 빌드가 들어 있다(미리보기 0개 파일).

---

### Task 7: 문서

**브랜치:** `docs/toybox-values-more` (Task 6 의 PR 이 들어간 `develop` 에서 나눈다)

**Files:**
- Modify: `docs/10-toybox.md`, `docs/11-game-internals.md`, `docs/05-game-systems.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-10-10-toybox-stage3-2-design.md`(끝에 "보완 내역" 한 절)

**Interfaces:**
- Consumes: Task 6 의 `w-more.md`(본 것 · 보지 못한 것 · 최종 검토의 결과), 이 계획의 "설계서와 달라진 곳" · "계획을 쓰며 확인한 것".
- Produces: 문서. 게임 안에서 보지 않은 것은 "보지 못했다"로 적는다 — `w-more.md` 에 없는 것을 본 것처럼 쓰지 않는다.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-values-more && git log --oneline -1
```

- [ ] **Step 2: `docs/10-toybox.md`**

1. "무엇인가": 3단계 문단의 "지금까지 옮긴 것"에 **단추 넷**(지식 순위 올리기 · 세계 시장 여론 최고 · 관계 최고 · 관계 중립 — 3단계 2, 2026-10-10)을 더하고, "묶음 2 가 끝났다. 내장 치트로 도는 기능은 15개다"로 고친다.
2. "쓰는 법": 네 단추가 내장 치트를 거치지 않는다는 것 — 이름 · 탭 · 자리는 그대로이고, 누르면 값이 바로 바뀌며 창 바닥에 `마지막으로 쓴 값: 관계 최고 — 폴란드 (1106)` 같은 한 줄이 나온다. 게임의 설정 창이 뜨지 않고 치트 허용 비트가 그대로다. 게임 밖에서는 꺼져 있다. "관계 최고" · "관계 중립"은 지금처럼 목록에서 나라를 고른 뒤 누른다. 검증 번호는 `w-more.md` 의 W 번호로 단다.
3. "기능"의 표: 네 줄의 "게임에 넣는 것" 칸을 "없다 — 그 칸에 직접 쓴다(내장 치트가 아니다)"로, 검증 칸을 `[확인: W2]` 같은 번호로 고친다. "지식 순위 올리기"의 효과 칸은 본 대로(기술 수준 +1 을 봤으면 그렇게). 표 아래의 문단: 내장 치트로 도는 수 19 → 15, "창에서"가 [확인]인 수를 다시 센다(`love` · `neutral` 의 H5 는 지난 방식의 확인이므로 "확인한 것"에 남기고 표의 검증은 W 번호로 바꾼다). 지운 치트에 `finalexam` · `shelovesme` · `love` · `neutral` 을 더한다.
4. "한계"에 더한다(본 대로 고쳐 적는다):
   - **관계는 양쪽에 쓴다** — 내 나라 객체의 그 나라 칸 셋과, 그 나라 객체의 내 나라 칸 셋(치트와 같다. 사용자가 정했다). ToyBox 가 플레이어가 아닌 나라의 객체에 쓰는 것은 이 칸 셋뿐이다.
   - 쓴 값이 얼마나 가는가(W8 에서 본 대로: 25초 동안 그대로였는지, 바뀌었으면 얼마나). 게임이 날마다 다시 셈하는지는 날짜를 넘겨 보지 않았다는 것.
   - 이 넷만 쓴 판도 게임이 "치트를 쓴 판"으로 알지 못한다(W7 에서 본 대로).
   - 한 묶음의 자리를 못 찾으면 그 단추만 꺼지고 자리에 까닭 한 줄이 보인다. 값 쓰기가 한 번 실패하면 돈 · 물자 · 유지와 함께 이 넷도 그 실행 내내 꺼진다.
   - "지식 순위 올리기"는 999 에서 멈춘다. 그 칸이 무엇인지는 본 만큼만(기술 수준 [확인: 실행] / [추정]).
   - 여론의 세 칸과 관계의 두 표가 화면의 어느 숫자 · 막대인지 — W3 · W4 에서 본 만큼만. 모르면 모른다고.
   - 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라온다(묶음 1 과 같다 — 본 대로).
   - 고른 나라가 병합된 뒤의 지역 객체를 게임이 어떻게 바꾸는지는 보지 않았다(쓰기 직전에 "이번 판에 있는 나라"인지 다시 본다).
5. "구조"의 표: `locate`(더 쓰는 값의 묶음 셋 — 서명 21개, 묶음마다 따로) · `game`(기술 수준 · 여론 · 관계의 읽기와 쓰기) · `keeper`(요청 셋) · `features`(19줄 가운데 직접 쓰는 넷, 내장 치트로 도는 15) · `ui`(직접 쓰는 줄 — 쓸 수 없으면 단추 자리에 까닭)의 줄을 고친다. "게임 읽기 · 값 쓰기" 문단의 "쓰는 곳"을 새 목록으로 고친다.
6. 로그의 표에 더한다: `값을 더 씁니다 (…)` · `값을 더 쓰지 않습니다 (SRTOYBOX_WRITE=0. …)` · `기술 수준을 쓸 수 없습니다 (…)`(여론 · 관계도) · `값 쓰기: 기술 수준 130 -> 131` · `값 쓰기: 세계 시장 여론 최고` · `값 쓰기: 관계 최고 — 폴란드 (1106)` · `값 쓰기 실패 (관계 — 폴란드 (1106)) — 값 쓰기를 끕니다`. `옛 방식 … 19개` 를 `15개` 로.
7. "확인한 것": 새 표 **"3단계 2 — 그 밖의 값 쓰기"**(`w-more.md` 에서. 번호 W0 … W9, 칸은 VC 표와 같다: # · 한 것 · 본 것 · 근거 화면). 설계서의 "아직 보지 않은 것" 1 ~ 4 가운데 본 것을 표 아래에 적고, 보지 못한 것을 따로 적는다(`SRTOYBOX_WRITE=0` 과 묶음을 못 찾았을 때의 화면은 자동 테스트만 — 설계서 그대로).
8. "문제가 생기면": 단추 대신 `<단추 이름> — 이 게임 판에서는 쓸 수 없습니다 (…)` 가 보일 때 할 일(`uv run srkit locate` → 깨진 묶음의 서명을 `sig-mine --offset` 으로 다시 뽑는다 — [11](11-game-internals.md)). `SRTOYBOX_WRITE=0` 이 이 넷도 끈다는 것.
9. "다음 단계"의 표: 묶음 2 를 "끝 (2026-10-10)"으로, 다음이 묶음 3(연구 — 기술 수준 N 이하 보유, 대기열의 연구 즉시 완료, 일부 연구가 완료되지 않는 원인, 개별 연구 미/완료)임을 적는다.

- [ ] **Step 3: `docs/11-game-internals.md` · `docs/05-game-systems.md`**

`docs/11`:
1. "전역과 필드"의 지역 객체 표에 더한다: `+0x14CD0`(float, 기술 수준 — 본 대로 [확인: 실행]/[추정]. 치트 밖의 코드가 1900 을 더해 쓴다 [확인: 정적]), `+0x14AF4` · `+0x14AF8` · `+0x14B10`(float, 세계 시장 여론과 그 둘레 — 어느 칸이 무엇인지는 본 만큼만), `+0x15F10 + 4·i` · `+0x16F10 + 4·i`(float × 1024, 지역 `i` 와의 관계. −1 … 1), `+0x17F10 + 4·i`(float × 1024, 지역 `i` 에 대한 전쟁 명분. 0 … 1). **이 칸들에 직접 쓰면 게임이 그 값을 쓴다**는 것은 W2 ~ W5 에서 본 만큼만 [확인: 게임].
2. "주소를 찾는 법"에 새 절 **"새 찾기 — 더 쓰는 값 (3단계 2 부터)"**: 이 계획의 "계획을 쓰며 확인한 것"의 서명 표(맞는 자리와 그 자리가 든 함수 — 함수는 `uv run srkit locate` 와 `srtoybox_function_root` 로 채운다)를 싣고, 묶음마다 따로 찾는다는 것 · 읽어 낸 자리의 대조(범위, 4 의 배수, 서로 겹치지 않는다 — 겹치면 두 묶음 다, 값 묶음과 겹치면 새 묶음만) · 다시 뽑는 법(`uv run srkit sig-mine --offset 14cd0` 등 일곱 줄)을 적는다. 올라와 있는 게임에서도 21개가 맞았는지는 W0 의 로그(`값을 더 씁니다 (…)`, `맞지 않은 서명` 없음)로 [확인: 실행].
3. "이번에 알게 된 치트의 사실"에 더한다 [확인: 정적]: `finalexam` 은 `+0x14CD0` 에 1.0 을 더한다 / `shelovesme` 는 세 칸에 1.0 을 쓴다 / `love` · `neutral` · `hate` 는 두 객체의 표 셋에 쓴다(값은 1 · 0 · −1, 전쟁 명분은 0 · 0 · 1) — 게임의 함수를 부르지 않는다.
4. "보지 않은 것"을 고친다: 본 것을 지우고, 남은 것을 적는다(날짜를 넘길 때 게임이 관계 · 여론을 다시 셈하는지, 병합된 나라의 객체, DLC 의 판, 다른 빌드).

`docs/05`: "연구" 절의 `finalexam` 줄과 "모르는 것"(기술 수준을 실제로 올리는지)을 본 대로 고친다. "외교" 절의 `love` · `neutral` · `shelovesme` 를 적은 곳에 "ToyBox 는 3단계 2 부터 이 치트를 쓰지 않고 그 칸에 직접 쓴다([10](10-toybox.md))"를 덧붙이고, 관계가 지역 객체 안의 표 셋(지역 인덱스로 찾는다)이라는 것을 한 줄로 적는다([11](11-game-internals.md)).

- [ ] **Step 4: `docs/09` · `README.md` · `CLAUDE.md` · 설계서**

- `docs/09-cheat-mod-plan.md`: 로드맵의 3단계 줄에 묶음 2 의 완료와 날짜, 남은 수(15). 표의 `finalexam` · `love` · `neutral` · `shelovesme` 줄("그대로 쓴다")에 "치트는 그대로다. ToyBox 는 3단계 2 부터 쓰지 않는다 — 그 칸에 직접 쓴다([10](10-toybox.md))"를 적는다. 치트 자체의 사실(07 의 검증)은 그대로 둔다.
- `README.md`: 현재 상태의 3단계 문단(묶음 2 가 끝났다. 내장 치트로 도는 기능 19 → 15).
- `CLAUDE.md`:
  - "명령"의 `gamedrive.py peek` 줄: 읽는 값에 기술 수준 · 세계 시장 여론을, `peek <지역 번호>` 에 "플레이어와 그 지역 사이의 관계 여섯 칸"을 더한다.
  - "지켜야 할 것"의 "ToyBox 가 게임의 메모리에 쓰는 곳은 …" 줄을 새 목록으로 고친다: **플레이어 지역 객체의 국고 1칸 · 물자 재고 12칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸, 그리고 고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸뿐이다**(`native/srtoybox/game.h`).
- 설계서(`docs/superpowers/specs/2026-10-10-toybox-stage3-2-design.md`)의 "상태" 줄을 "구현 끝(2026-10-10)"으로 고치고, 끝에 절 **"보완 내역 (2026-10-10, 계획을 쓰고 실행하며)"** 를 더한다: 이 계획의 "설계서와 달라진 곳"을 옮기고 [계획](../plans/2026-10-10-toybox-stage3-2-values-more.md)을 가리킨다. "아직 보지 않은 것" 1 ~ 4 를 본 대로 적는다. 완료 기준 여섯 가지를 하나씩 짚어, 채운 것과 남은 것(보지 못한 W 가 있으면 그것)을 적는다. 최종 검토가 남긴 것(미룬 Minor)을 적는다.

- [ ] **Step 5: 링크와 사실을 대조하고 커밋 · PR · 머지**

```bash
cd /e/SR2030ToyBox && PYTHONIOENCODING=utf-8 uv run python "<스크래치>/linkcheck.py" . 2>&1 | grep -v "docs/superpowers/plans/" | tail -3; grep -n "19개\|19 개\|cheat love\|cheat finalexam" docs/10-toybox.md README.md CLAUDE.md | head -20; uv run pytest -q 2>&1 | tail -1
```

Expected: 계획 문서 밖의 깨진 상대 링크가 없다(`linkcheck.py` 는 앞 계획에서 쓴 스크래치의 스크립트다 — 없으면 `docs/` · `README.md` · `CLAUDE.md` 의 `](…)` 링크가 가리키는 파일이 있는지 보는 열 줄짜리를 다시 쓴다). 남은 `19개` · `cheat love` 는 지난 단계의 기록(확인한 것의 표, 07 을 가리키는 줄)뿐이다. 테스트는 Task 6 의 끝과 같은 수가 통과한다(문서만 바꿨다).

```bash
cd /e/SR2030ToyBox && git add docs README.md CLAUDE.md && git commit -q -F - <<'EOF'
docs: ToyBox 3단계 2 — 지식 순위 · 세계 시장 여론 · 관계를 내장 치트 없이, 게임에서 본 것

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox-values-more
```

스크래치에 `pr-docs-values-more.md` 를 쓰고(무엇을 고쳤나의 표, 게임에서 본 것과 보지 못한 것, `uv run pytest` 결과), PR 을 올려 머지한다:

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/toybox-values-more --title "docs: ToyBox 3단계 2 — 그 밖의 값 쓰기" --body-file "<스크래치>/pr-docs-values-more.md"
```

```bash
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git log --oneline -3
```

---

## 끝난 뒤의 상태

- `develop` 에 PR 셋(이 계획 문서와 설계서 · 코드 · 문서)이 들어가 있다. `uv run pytest` 418개 통과(최종 검토에서 테스트가 더해졌으면 그만큼 더). 게임 폴더에는 최종 빌드의 `srtoybox.dll` 이 있고 그 밖의 게임 파일은 그대로다.
- 사용자의 `%APPDATA%\SR2030ToyBox` 설정은 그대로다(이 묶음은 설정 파일에 더하는 것이 없다).
- **묶음 2 가 끝난다.** 설계서의 완료 기준 여섯을 Task 7 에서 하나씩 짚는다. 내장 치트로 도는 기능은 15개가 남는다(연구 2, 인구 · 여론 2, 외교 · 영토 6, 부대 3, 화면 · 진행 2).
- **다음**: 묶음 3(연구)의 설계 — 사용자가 처음에 청한 "일부 연구가 완료되지 않는 원인"과 "개별 연구 미/완료 체크"가 여기에 든다. 사용자의 말이 있을 때 시작한다.
- **이 계획이 미룬 것**: 지금 값의 표시, 관계 최저 · 임의 값, 여론 최저(설계서의 "넣지 않는 것"). 묶음 1 의 최종 검토가 남긴 것들(요청을 받지 못한 까닭의 구분, 유지의 로그 등)은 그대로다.
