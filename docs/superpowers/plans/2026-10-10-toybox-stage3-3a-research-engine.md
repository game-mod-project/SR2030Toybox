# ToyBox 3단계 3 (가) — 연구의 엔진과 옮기는 단추 둘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 연구 탭의 단추 둘("기술 수준 N 이하 전부 보유" · "대기열의 연구 즉시 완료")이 내장 치트를 거치지 않고 기술 · 부대 설계의 보유를 직접 쓴다 — 대기열에 건 **부대 설계도 끝나고**(사용자가 알린 문제), 모든 나라가 함께 쓰는 연구 기간을 건드리지 않는다. 내장 치트로 도는 기능은 15 → 13 이 된다.

**Architecture:** 앞 묶음이 깐 길(치트와 무관한 서명으로 자리 찾기 → 쓰기 직전의 확인 → 요청의 줄 → 게임 창의 타이머에서 쓰기)에 연구를 얹는다: 새 찾기의 묶음 `locate_research`(표 둘 · 세계 객체 · 연구 목록 · 게임의 "효과를 다시 셈" 함수 — 표와 목록의 꼴이 서명에 박혀 있다), 게임이 스스로 쓰는 규칙을 옮긴 순수 모듈 `research`(선행 기술 · 딸린 것 · 대기열), `game` 의 스냅숏과 쓰기(플레이어의 비트 · 새 묶음 · 노드의 깃발, 끝에 다시 셈을 플레이어 지역으로 한 번), `keeper` 의 연구 요청 줄. ToyBox 가 치트가 아닌 게임의 함수를 부르는 첫 기능이라, 직접 실행의 겹침 방지와 오류 가드를 함께 쓴다(`runner_enter_call` · `runner_leave_call`).

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Dear ImGui 1.92.9b, Python 3.13 + ctypes + pytest (`uv run`), capstone(`srkit sig-mine` — 개발용), Win32.

**Spec:** `docs/superpowers/specs/2026-10-10-toybox-stage3-3-design.md` (승인 2026-10-10). 그 설계서의 "구현 순서"대로 계획은 둘이다 — **이 문서가 (가)**(엔진과 옮기는 단추 둘, 게임 안 확인 R0 ~ R5)이고, (나)(연구의 목록, R6 ~ R11)는 (가)의 전제 확인 뒤에 따로 쓴다. 3단계의 여덟 묶음과 요구 셋은 [3단계 1 설계](../specs/2026-10-09-toybox-stage3-1-design.md)에 있다.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 와 자리는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 를 적지 않는다(서명이 읽어 낸다). 표와 목록의 꼴(레코드의 크기 · 칸의 자리)은 `native/srtoybox/locate.h` 의 상수 한 곳에만 두고, 그 상수가 박힌 명령을 서명에 넣는다.
- **요구 3 — 내장 치트와 별도.** 두 단추의 어떤 동작도 치트 명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다. 치트 닻을 쓰는 곳은 지금의 셋 그대로다: `locate_legacy`(전환 기간), `srkit.sigmine`(개발용 — 치트 코드를 후보에서 빼는 데), `tests/toybox_cheat_oracle.py`(테스트의 대조).
- **무엇을 찾지 못하거나 쓰지 못할 때 내장 치트로 되돌아가지 않는다.** 그 단추의 자리에 까닭 한 줄만 보인다.
- **묶음은 서로 기대지 않는다.** 연구 묶음을 못 찾아도 돈 · 물자 · 지식 · 여론 · 관계는 그대로이고, 거꾸로도 같다. 상태 묶음을 못 찾으면 연구도 쓰지 않는다(플레이어를 모른다).
- **게임의 메모리에 쓰는 곳은 이것뿐이다**(`game.h` 의 머리말): 지금까지의 것(플레이어 지역 객체의 국고 1칸 · 재고 12칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸, 고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸)에 **연구**를 더한다 — 기술 · 부대 설계의 보유 비트 묶음에서 **플레이어의 비트**, 묶음이 없는 항목의 포인터 칸(새 묶음을 걸 때), 플레이어의 연구 목록 노드의 깃발 두 칸. 다른 나라의 비트 · 연구 기간 · 비용 · 전역 깃발 · 치트 허용 비트에는 쓰지 않는다.
- **게임의 함수는 "지역의 효과를 다시 셈" 하나만 부른다 — 플레이어의 지역 인덱스로만, 요청 하나에 많아야 한 번, 구조적 예외 가드 안에서.** −1(모든 지역)로 부르지 않는다. 그 함수에서 예외가 나면 ToyBox 를 멈춘다(그 뒤로 아무것도 쓰지도 부르지도 않는다).
- **요구 2 — 플레이어의 나라에만.** 기술 표와 부대 설계 표는 모든 나라가 함께 쓰는 표다. 거기에 쓰는 것은 플레이어의 비트와, 플레이어의 비트 하나만 켜질 빈 묶음을 거는 것뿐이다.
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다. (설계서의 승인이 이 바꿔 넣기의 승인을 포함한다 — "묶음이 끝날 때마다 설치본을 갱신한다".)
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 게임 안을 돌아다니는 확인은 백그라운드 에이전트에 맡긴다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다.** 한 판에서 게임 시간을 3일 넘게 흘리지 않는다(7일마다 자동 저장된다). 게임이 떠 있는 동안 브랜치를 바꾸지 않고 `uv run pytest` 를 돌리지 않는다. **게임을 띄우는 횟수는 한 번을 목표로 한다**(사용자가 같은 PC 를 쓰고 있다).
- **`start` 의 출력에 `돌려주지 못함 N회` 나 `게임이 포커스를 쥐고 있음` 이 나오면 게임을 끄고 사용자에게 알린다**(사용자의 입력이 화면 밖 게임으로 가고 있다).
- **검증용 게임은 `SRTOYBOX_HOME` 을 임시 폴더(`build/verify/…`)로 돌려 띄운다.** 사용자의 실제 `%APPDATA%\SR2030ToyBox` 설정을 읽지도 고치지도 않는다. **이 계획에서는 Steam 으로 띄우지 않는다.**
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.** 게임 안 확인에서 내장 치트는 하나도 넣지 않는다.
- Git: `main` · `develop` 에 직접 커밋하지 않는다. `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고 `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다. **머지 명령이 권한 분류기에 거부되면 다른 형태로 우회하지 않는다** — 사용자에게 그 명령을 그대로 건네고, 머지된 뒤 `git switch develop && git pull --ff-only origin develop` 로 이어 간다.
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`(또는 `PYTHONIOENCODING=utf-8`).
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다. `__try` 를 쓰는 함수에는 소멸자가 있는 지역 객체를 두지 않는다(C2712).
- **창과 로그에 보이는 새 글에는 한글 · ASCII · `·` · `—` 만 쓴다**(`→` `–` `−` 를 쓰지 않는다 — 글꼴에 한국어 범위의 글리프만 올라가 있다).
- **시작할 때의 테스트 상태**: `develop`(이 계획 문서가 들어간 뒤)에서 `uv run pytest` 418개 통과.
- 화면 검사 테스트가 실패하면 "흔들림"으로 넘기지 않고 원인을 본다. 테스트는 다른 무거운 일(빌드)과 함께 돌리지 않는다 — 검사 프로세스가 DLL 사본을 뜨는 중에 DLL 이 바뀐다.

## 고칠 곳을 읽는 법

Task 1 ~ 7 의 코드는 **"고칠 곳"** 으로 적었다. 꼴은 다섯 가지이고, 찾을 글은 그 파일에 정확히 한 번 나온다(문맥을 그만큼 넓혀 뒀다). 한 Task 안에서는 적힌 순서대로 옮긴다.

| 꼴 | 뜻 |
|---|---|
| 새 파일 `경로`: + 블록 | 그 내용으로 파일을 만든다 |
| `경로` 를 통째로 다음으로 바꾼다: + 블록 | 파일 전체를 그 내용으로 바꾼다 |
| `경로` 에서 다음을 찾아: + 블록 / 이렇게 바꾼다: + 블록 | 첫 블록을 둘째 블록으로 바꾼다 |
| `경로` 에서 다음 바로 뒤에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 다음 줄에 둘째 블록을 끼운다 |
| `경로` 에서 다음 바로 앞에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 앞에 둘째 블록을 끼운다 |

블록 끝의 빈 줄도 글의 일부다(함수 사이의 빈 줄 둘을 지키려고 그렇게 적었다). 손으로 옮겨도 되고, 옮겨 적는 도구로 옮겨도 된다 — 계획을 쓰며 만든 스크래치의 `apply_plan.py <이 문서> <저장소 루트> <Task 번호> <test|code>` 가 이 문서의 블록을 그대로 읽어 옮긴다(`<!-- 고칠 곳: … -->` 표시 사이. 찾을 글이 한 번이 아니면 아무것도 쓰지 않고 멈춘다). 도구는 저장소에 넣지 않는다.

## 설계서와 달라진 곳 (계획을 쓰며)

Task 9 가 이것을 설계서의 "보완 내역"으로 옮긴다.

- **연구 묶음은 찾을 것마다 서명 셋이 모두 정확히 한 번 맞고 같은 값을 내야 찾은 것이다**(`RESEARCH_NEED = 3`). 설계서는 앞 묶음처럼 "둘 이상"이라 했다. 까닭: 꼴의 상수 가운데 "한 찾을 것 안에서 둘 이상의 서명"에 박을 수 없는 것이 있다(기술의 수준 `+1`, 노드의 둘째 깃발 `+0x24`, 설계의 보유 묶음 `+0xf8`, 묶음의 크기 128). 셋이 다 맞아야 하면 한 서명에만 박힌 상수도 지켜진다. 값이 한 번의 게임 업데이트에 더 쉽게 꺼지는 대신, 꼴이 바뀐 빌드에서 엉뚱한 칸에 쓰지 않는다.
- **세계 객체의 서명은 값 둘을 읽는다** — 세계 객체의 RVA 와 "지역 표까지의 거리". `세계 객체 + 거리` 가 상태 묶음이 따로 찾은 지역 표와 **정확히 같아야** 한다(설계서의 "거리가 말이 된다"를 이렇게 정했다).
- **묶음의 크기 128 도 서명에 박는다**(`mov ecx, 80h`). 새 묶음을 만들기 전의 확인은 `HeapValidate` 가 참이고 `HeapSize` 가 **정확히 128** 이다(설계서는 "128 이상"). 게임이 묶음을 키운 빌드(지역이 늘었다)에서 작은 묶음을 걸지 않는다.
- **연구의 전역과 값 묶음의 세계 자료 포인터의 겹침은 따로 본다**(`locate_research_fits` — 둘 다 찾은 뒤에. 겹치면 연구 묶음만 버린다). 연구 묶음을 찾는 함수는 값 묶음을 모른다(묶음은 서로 기대지 않는다).
- **비트와 노드의 깃발은 원자적으로 쓴다**(`InterlockedOr8` · `InterlockedAnd8` · `InterlockedOr`). 설계서는 "그 바이트를 읽어 한 비트만 고쳐 쓴다(WriteProcessMemory)"라 했다. 보유 묶음의 한 바이트에는 여덟 나라의 비트가 함께 있다 — 읽고 되쓰는 사이에 게임이 다른 나라의 비트를 바꾸면 그것을 덮어쓰게 된다. 원자적으로 쓰면 다른 나라의 비트는 읽지도 쓰지도 않는다. 쓰기 전에 그 쪽이 읽기 · 쓰기인지 보는 것, 쓴 뒤 다시 읽어 보는 것(아니면 한 번 더)은 그대로다. 묶음의 포인터 칸은 지금처럼 쓴다(8바이트 통째).
- **쓰기가 실패하면 연구만이 아니라 값 쓰기 전체를 끈다**(돈 · 물자 · 유지 · 직접 쓰는 줄 넷도 — 앞 묶음의 규칙과 같다). 로그는 `연구 쓰기 실패 (<어디>, N칸 가운데 M칸을 쓴 뒤) — 값 쓰기를 끕니다`, 한 칸도 쓰지 않았으면 `연구 쓰기 실패 (<어디>) — 값 쓰기를 끕니다`. 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 먼저 보므로, 자리의 보호 때문에 실패할 때는 한 칸도 쓰지 않는다.
- **규칙에 "묶음을 만들 수 있는가"(`can_house`)가 인자로 들어간다.** 만들 수 없으면 묶음이 없는 항목을 계획에서 빼고 그 수(`skipped`)를 센다 — 그 항목의 선행은 따라가지 않고, 대기열에 있어도 빼지 않는다. 그래야 알림의 "고른 것 · 딸려 온 것"의 수가 쓴 것과 맞는다.
- **(가)의 스냅숏은 요청을 쓸 때만 뜬다.** 설계서의 "연구 탭이 보이는 동안 0.5초마다" · 부대 설계의 이름 · 창에 넘기는 일은 (나)(목록)의 것이다. 다만 `read_research` 는 고른 나라의 번호를 이미 받는다(행마다 `picked` · `others`).
- **연구 요청은 `keeper` 의 잠금을 놓고 쓴다.** 끝에 게임의 함수가 불리기 때문이다 — 그 함수가 안에서 ToyBox 로 되돌아와도(타이머 · 단추) 서로 기다리지 않는다. "게임의 함수 안" 깃발과 오류 가드는 직접 실행의 것을 함께 쓴다: `runner_enter_call()` · `runner_leave_call(무엇, 예외 코드)`.
- **알림이 둘 더 있다.** 바꿀 것이 없으면 창에도 `바꿀 것이 없습니다 — 대기열`(설계서는 로그만). 보유는 그대로이고 대기열의 노드만 뺐으면 `마지막으로 쓴 값: 대기열에서 1개를 뺌 — 대기열`(내장 치트로 "끝낸" 판의 남은 노드).
- **요청을 쓸 때 표를 읽을 수 없으면** 알림과 로그에 `연구의 표를 읽을 수 없습니다 (<무엇>)` 한 줄(설계서는 "목록 자리에" — (가)에는 목록이 없다). 쓰기는 꺼지지 않는다(다음 요청에서 다시 읽는다).
- **묶음을 만들 수 없는 까닭은 둘인데**(게임의 묶음이 프로세스 힙의 128바이트 블록이 아니다 · `HeapAlloc` 이 실패했다) 알림의 글은 설계서의 하나다(`묶음을 만들 수 없는 게임 판입니다 — …`).
- **`Wrote` 에 둘을 더한다**: `Unreadable`(표나 목록을 읽을 수 없다 — 쓰지 않았다) · `Crashed`(비트는 썼는데 다시 셈에서 예외).
- **다시 셈의 예외를 알리는 글**: `효과를 다시 셈하는 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.`(창 맨 위의 빨간 경고 — 직접 실행의 오류와 같은 자리).
- **연구 탭의 바닥 안내.** 그 탭의 세 줄이 모두 직접 쓰는 줄이 됐다 — 내장 치트로 도는 줄이 없는 탭은 글쇠 방식(`SRTOYBOX_DIRECT=0` · 옛 찾기 실패)과 상관없이 돈 · 물자 탭처럼 `값은 바로 바뀝니다. …` 를 보이고, 쓸 수 있는 줄이 하나도 없으면 안내를 띄우지 않는다.
- **"기술 수준 N 이하 전부 보유"의 입력란은 쓸 수 있을 때만 그린다**(쓸 수 없으면 까닭 한 줄뿐).
- **`srkit sig-mine` 에 더한 것이 `call` · `jmp` 의 목표만이 아니다**: `--with <상수…>`(서명 안의 명령이 그 상수들을 들고 있어야 한다), `--back N`(가리키는 명령보다 앞선 명령부터), `--most N` · `--longest N`(서명의 길이), `--through-jumps`. 그리고 "명령이 그 상수를 들고 있는가"가 분기의 거리(`je +24h`)를 상수로 치던 것을 고쳤다.
- **`gamedrive.py research` 의 결과**: `player` · `region` · `index` · `techs` · `designs` · `used` · `unhoused` · `queue` · `days`, build 21347933 에서만 `effects`(`mul` 200칸 · `add` 176칸 · `cell`). `--out <파일>` 을 주면 거기에 적고 화면에는 수만 보인다(보유한 부대 설계가 수천 줄이다).
- **화면 검사의 가짜 게임은 연구의 자리를 기본으로 준다.** 그래서 앞 묶음의 테스트 가운데 "쓸 수 없을 때"를 보는 것(`SRTOYBOX_WRITE=0` · `SRTOYBOX_READ=0`)의 연구 탭 기대가 바뀐다(세 줄 모두 까닭). 명령 글의 테스트는 값을 받는 예를 `technology` 에서 `spawnunit` 으로 바꾼다.
- **코드 PR 은 하나다**(`feat/toybox-research-engine`). 코드의 최종 검토는 그 PR 을 머지하기 전(Task 8)에 받는다. 문서는 그 뒤의 PR 이다(Task 9).

## 계획을 쓰며 확인한 것

- **서명 21개를 정했다** [확인: 정적 — `uv run srkit sig-mine` 의 후보에서 명령을 보고 골랐다]. 저마다 실행 구역에 한 번만 맞고, 찾을 것마다 세 서명이 서로 다른 함수에 있고, 맞은 자리가 모두 치트 코드(`0x522330` – `0x5284fd`) 밖이다(Task 2 의 테스트가 본다).

  | 찾을 것 → 값 | 서명 | 맞는 자리 (함수) |
  |---|---|---|
  | 기술 표 → `0x1829620` | `48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48 48 8D 7A 50 44 0F B7 71 04 41 8B EE 48 03 FE 74 3C 48 8B 17 48 85 D2 75 10 B9 80 00 00 00` | `0x6f52f3` (`0x6f52c0` 기술을 준다) |
  | | `48 8B 0D [rip] 4C 69 CE 88 00 00 00 48 83 C1 50` | `0x6f5456` (`0x6f5430` 기술을 뺀다) |
  | | `48 8B 05 [rip] 44 38 24 03 76 33 8B 54 03 4C F6 C2 40 75 2A 0F B6 4C 03 01` | `0xbbd4b0` (`0xbbbf40`) |
  | 기술 수 → `0x1829098` | `39 3D [rip] 7E 7B 48 89 5C 24 30 48 8B DF 0F 1F 00 48 8B 0D ? ? ? ? 48 03 CB 80 39 00 76 4B 0F BF 41 04 3B C6 74 08 0F BF 41 06` | `0x6f554d` (`0x6f5430`) |
  | | `44 8B 0D [rip] 33 DB 48 89 7C 24 40 45 85 C9 0F 8E ? ? ? ? 33 FF 0F 1F 00 48 8B 0D ? ? ? ? 80 3C 39 00 76 7E 0F BF 44 39 04 8B 55 18 3B C2 74 09 0F BF 44 39 06` | `0x6fc634` (`0x6fc5d0` 대기열에서 뺀다) |
  | | `44 3B 35 [rip] 0F 8D ? ? ? ? 49 69 D6 88 00 00 00 48 03 15 ? ? ? ? F6 05 ? ? ? ? 02 0F BF 42 04 89 44 24 60 0F BF 42 06` | `0x6f0c81` (`0x6f0b90`) |
  | 부대 설계 표 → `0x1829610` | `4C 8B 3D [rip] 49 63 04 24 49 8D 9F F8 00 00 00 44 0F B7 77 04 48 69 C8 68 01 00 00 41 8B FE 48 03 D9 74 2B 48 8B 03 48 85 C0 75 0D B9 80 00 00 00` | `0x754436` (`0x750f10` 연구가 끝날 때) |
  | | `4C 8B 05 [rip] 4D 03 C2 49 39 38 74 3B 41 F7 80 F0 00 00 00 00 00 00 01 75 2E 41 F6 80 EC 00 00 00 01 75 24 66 41 39 78 20` | `0x6f54c0` (`0x6f5430`) |
  | | `48 8B 1D [rip] 48 83 3C 2B 00 0F 84 ? ? ? ? F7 84 2B F0 00 00 00 00 00 00 01 0F 85 ? ? ? ? F6 84 2B EC 00 00 00 01 0F 85 ? ? ? ? 66 83 7C 2B 20 00` | `0x6f5620` (`0x6f55f0` 설계의 선행을 준다) |
  | 부대 설계 수 → `0x182909c` | `3B 1D [rip] 0F 8D ? ? ? ? 48 69 CB 68 01 00 00 4A 83 3C 39 00 0F 84 ? ? ? ? 66 42 83 7C 39 20 00 0F 84 ? ? ? ? 33 C0 4D 8D 4F 34` | `0x75415c` (`0x750f10`) |
  | | `44 3B 35 [rip] 0F 8D ? ? ? ? 48 8B 0D ? ? ? ? 49 69 DE 68 01 00 00 F6 05 ? ? ? ? 02 0F B7 44 0B 34` | `0x6f0bd0` (`0x6f0b90`) |
  | | `41 FF C1 49 81 C2 68 01 00 00 44 3B 0D [rip]` | `0x6f5536` (`0x6f5430`) |
  | 세계 객체 → `0x17a9020`, 지역 표까지 `0x34e8a0` | `4C 8D 15 [rip] 4D 8B 84 F2 [u32] 85 DB` | `0x70f1db` (`0x70cbd0`) |
  | | `48 8D 05 [rip] 48 8B 9C D8 [u32] 8B F5` | `0x703d88` (`0x7038d0`) |
  | | `48 8D 05 [rip] B2 01 48 8B 8C D8 [u32]` | `0x67ec0d` (`0x65e3e0`) |
  | 연구 목록 → `0x3568c0` | `48 8D 0C 40 48 8B 94 CA [u32] 48 8B CA 48 85 D2 74 31 80 79 1C 02 75 10 44 3B 59 18 74 18 48 85 C9 75 05 48 8B CA EB EA 48 8B 41 10 48 8B C8 48 85 C0 75 DE EB 0D F7 41 20 00 00 00 88` | `0x7ac43c` (`0x7abbb0`) |
  | | `49 8B 94 CF [u32] 48 8B C2 48 85 D2 74 30 48 8B CA 80 79 1C 01 75 10 44 3B 49 18 74 18 48 85 C0 75 05 48 8B C2 EB E7 48 8B 40 10 48 8B C8 48 85 C0 75 DE EB 09 F7 41 24 00 00 00 88` | `0x6f10f3` (`0x6f0ff0`) |
  | | `48 8D 0C 40 49 8B 94 CC [u32] 48 8B C2 48 85 D2 74 5B 48 8B DA 0F 1F 80 00 00 00 00 80 7B 1C 01 75 0F 3B 7B 18 74 18 48 85 C0 75 05 48 8B C2 EB E1 48 8B 40 10` | `0x70f4c2` (`0x70cbd0`) |
  | 다시 셈 함수 → `0xbdd380` | `BA FF FF FF FF 49 8B C9 E8 [rip]` | `0x726e7c` (`0x726280`) |
  | | `BA FF FF FF FF 49 8B CA E8 [rip]` | `0x79a861` (`0x7961b0`) |
  | | `BA FF FF FF FF 49 8B CC E8 [rip] 4C 63 84 24 50 41 00 00` | `0x70f5de` (`0x70cbd0`) |

  다시 셈 함수의 서명은 게임이 그것을 −1(모든 지역)로 부르는 자리의 것이다(`mov edx, -1` / `mov rcx, <세계 객체>` / `call`) — ToyBox 는 그 자리에서 함수의 주소만 읽는다(−1 로 부르지 않는다).

- **꼴의 상수 → 그것이 박힌 서명** [확인: 정적]. Task 2 의 테스트(`RESEARCH_PINS`)가 이 표대로 서명의 바이트에 `locate.h` 의 상수가 들어 있는지 본다.

  | 상수 | 박힌 서명(찾을 것의 몇째) |
  |---|---|
  | 기술 레코드 `0x88` | 기술 표 1 · 2, 기술 수 3 |
  | 기술의 보유 묶음 `+0x50` | 기술 표 1 · 2 |
  | 기술의 빈 자리(`+0` byte) | 기술 표 3, 기술 수 1 · 2 |
  | 기술의 수준 `+1` | 기술 표 3 |
  | 기술의 선행 `+4` · `+6` | 기술 수 1 · 2 · 3 |
  | 설계 레코드 `0x168` | 설계 표 1, 설계 수 1 · 2 · 3 |
  | 설계의 보유 묶음 `+0xf8` | 설계 표 1 |
  | 설계의 빈 자리(`+0` qword) | 설계 표 2 · 3, 설계 수 1 |
  | 설계의 깃발 `+0xf0 & 0x1000000` · `+0xec & 1` | 설계 표 2 · 3 |
  | 설계의 연구 대상 `+0x20` | 설계 표 2 · 3, 설계 수 1 |
  | 설계의 선행 `+0x34` | 설계 수 1 · 2 |
  | 묶음의 크기 128 | 기술 표 1, 설계 표 1 |
  | 목록 칸 24(× 3 × 8) | 연구 목록 1 · 3 |
  | 노드의 종류 `+0x1c` · 번호 `+0x18` · 다음 `+0x10` | 연구 목록 1 · 2 · 3 |
  | 노드의 깃발 `+0x20` / `+0x24` / `0x88000000` | 연구 목록 1 / 2 / 1 · 2 |

  **박지 못한 것**(표시에만 쓴다 — (나)의 목록): 설계의 병과 `+0x08` · 연도 `+0x0a`, 기술 분류의 값 1 ~ 6(빈 자리인지만 박혔다).
- **치트 본문과의 대조** [확인: 정적]: 서명이 낸 세계 객체 · 기술 수 · 기술 표 · 연구 목록 · 다시 셈 함수와 꼴의 상수 일곱(레코드의 크기 · 수준 · 보유 묶음 · 묶음의 크기 · 노드의 종류 · 번호 · 다음)이 치트 `technology` 의 본문에서 읽은 것과 같다(Task 2 의 테스트 — `tests/toybox_cheat_oracle.py` 의 `research`. 치트 코드는 테스트의 대조에서만 본다).
- **다시 셈 함수(`0xbdd380`)는 다른 함수를 부르지 않는다** [확인: 정적] — `call` 이 하나도 없고, 끝에서 `0x52fb30` 으로 뛴다(전역 객체의 바이트 둘을 1 로 만드는 잎 함수. 화면을 다시 그리라는 표시로 보인다 [추정]). 그래서 불러도 ToyBox 로 되돌아오지 않는다. 그래도 연구 요청은 잠금을 놓고 쓰고, 그 안에서 다시 온 타이머는 아무것도 하지 않게 했다(다른 빌드에서 달라져도 서로 기다리지 않는다).
- **연구 목록은 1023칸으로 보인다** [확인: 정적]: 1024째 칸 자리에 다른 전역(`0x1b058d8`)이 있다. 플레이어 인덱스의 상한은 지금처럼 1023 이다.
- **이 계획의 고칠 곳을 모두 저장소의 스크래치 사본에 옮겨 돌려 봤다**(저장소와 게임 폴더는 건드리지 않았다):
  - 도구(`apply_plan.py`)가 이 문서에서 읽어 옮긴 결과가, Task 마다, 따로 구현해 둔 상태와 글자까지 같다.
  - Task 마다 테스트만 옮기고 실패를 보고, 코드를 옮겨 빌드(`/W4 /WX`)하고 통과를 봤다. 단계의 Expected 는 그때 본 것이다.
  - 끝 상태에서 저장소의 테스트 전체가 통과한다(`559 passed`).
  - 끝 상태의 `uv run srkit locate` 가 설치된 게임(build 21347933)에서 연구 묶음의 일곱을 위의 값으로 찾는다.
- **돌려 보지 못한 것**: 게임 안의 동작 전부(Task 8) — 비트를 쓴 뒤의 게임 화면, 진짜 "효과를 다시 셈"을 부르는 것, `gamedrive.py research` 가 실제 게임에서 읽는 것(읽는 셈만 가짜 메모리로 테스트했다).

## Review Focus

설계서가 말하지 않았거나 자동 테스트만으로는 다 보지 못하는 것 — 사람이 쓸 때 걸릴 만한 순서로:

1. **비트를 켠 뒤 게임이 그것을 "보유"로 쓰는가.** 메모리의 비트는 켜졌는데 연구 화면이 그대로이거나 그 부대를 생산할 수 없으면 사용자는 "안 된다"로 본다(처음에 알린 문제가 그대로다). 자동 테스트로는 볼 수 없다 → Task 8 의 R1(연구 화면 · 생산 목록). 어긋나면 머지하지 않고 멈춘다.
2. **진짜 "효과를 다시 셈"을 ToyBox 가 부른다.** 자동 테스트의 그 함수는 가짜다 — 진짜 함수가 플레이어의 보정 표만 바꾸고 다른 지역의 것은 그대로 두는지, 예외 없이 돌아오는지는 게임에서만 본다 → Task 8 의 R2(`gamedrive.py research` 의 `effects` 를 플레이어와 다른 두 지역에서 앞뒤로 견준다). 가드와 "게임의 함수 안" 깃발은 Task 5 의 `test_a_fault_in_the_games_function_stops_toybox` · `test_a_tick_that_comes_back_inside_the_games_function_does_nothing`, Task 6 의 `test_no_cheat_starts_while_the_game_is_recomputing` 이 본다.
3. **대기열에서 뺀 뒤의 게임.** 노드의 깃발만 켰다 — 화면의 대기열에서 사라지는지, 다음에 건 연구가 정상으로 진행되는지, 하루 뒤에도 그대로인지 → Task 8 의 R1 · R5. 내장 치트로 "끝낸" 판의 남은 노드는 Task 5 의 `test_a_queued_item_that_is_already_held_is_only_cleared_from_the_queue`.
4. **같은 바이트의 다른 나라.** 보유 묶음의 한 바이트에 여덟 나라의 비트가 있다. 그 순간 게임이 다른 나라의 연구를 끝내도 그 비트를 덮어쓰면 안 된다(요구 2) → 원자적으로 쓴다(`poke_bits`). 기능은 Task 4 의 `test_only_the_players_bit_in_its_byte_changes` 가 보지만 경쟁 자체는 테스트로 만들 수 없다 — 검토자가 `write_research` 에 "읽고 되쓰는" 길이 남아 있지 않은지 본다. 게임에서는 R1 · R3 이 다른 나라(둘 이상)의 보유가 그대로인지 본다.
5. **ToyBox 가 건 묶음을 게임이 푼다.** 아무도 보유하지 않던 기술에 건 128바이트는 판을 끝낼 때 게임이 푼다 — 다른 힙의 것이면 그때 죽는다. 걸기 전의 확인은 Task 4 의 `test_a_new_set_is_made_only_when_the_games_sets_are_heap_blocks_of_that_size` 가 보고, 실제로 푸는 순간은 게임에서만 본다 → Task 8 의 R3(새 묶음이 생기는 요청) 뒤 R5 의 끝에서 메인 메뉴로 나온다(죽지 않는다). 저장 → 불러오기는 보지 않는다(설계서 그대로).

## 파일 구조

| 파일 | 맡는 일 | Task |
|---|---|---|
| `src/srkit/sigmine.py` · `cli.py` | (더함) 함수의 목표(`call` · `jmp`)도 캔다, `--with` · `--back` · `--most` · `--longest` · `--through-jumps`. `srkit locate` 의 새 절 | 1 · 2 |
| `native/srtoybox/locate.h` · `.cpp` | (더함) `ResearchLayout`, 꼴의 상수, 서명 21개, `locate_research` · `locate_research_fits` · `locate_research_shape` | 2 |
| `native/srtoybox/research.h` · `.cpp` | (새로) 순수한 규칙: 표의 스냅숏 → 완료 · 미완료가 바꿀 항목(선행 · 딸린 것 · 대기열의 노드), 알림의 글 | 3 |
| `native/srtoybox/game.h` · `.cpp` | (더함) 연구의 스냅숏(`read_research`) · 쓰기(`write_research` — 비트 · 새 묶음 · 노드의 깃발 · 다시 셈), 시작할 때의 찾기와 로그 | 4 |
| `native/srtoybox/runner_win.h` · `.cpp` | (더함) `runner_enter_call` · `runner_leave_call` — ToyBox 가 게임의 함수를 스스로 부를 때의 겹침 방지와 오류 가드 | 5 |
| `native/srtoybox/keeper.h` · `.cpp` | (더함) 연구 요청의 줄(4개까지), 틱마다 값 요청 뒤에 하나 | 5 |
| `native/srtoybox/features.h` · `.cpp` | (고침) `Direct::TechLevel` · `QueueDone`, 연구의 두 줄 | 6 |
| `native/srtoybox/ui.cpp` | (고침) `direct_row` 가 연구의 두 줄도 그린다, 내장 치트 줄이 없는 탭의 바닥 안내 | 6 |
| `native/srtoybox/exports.cpp` | (더함) 테스트용 내보내기 | 2 ~ 6 |
| `src/srkit/toybox.py` | (더함) `ResearchLayout` · `research_of` · `research_fits` · `research_shape`, `Located.research*`, 빌드할 소스에 `research.cpp` | 2 · 3 |
| `scripts/gamedrive.py` | (더함) `research` 명령(`peek_research` · `research_game`) | 7 |
| `tests/toybox_fake_exe.py` · `toybox_cheat_oracle.py` · `toybox_fake_game.py` · `toybox_overlay_probe.py` | 테스트 도우미: 가짜 이미지의 연구 자리, 치트 본문의 대조, 가짜 게임의 연구(`Lab` · `standard_lab`), 화면 검사의 새 모드 | 2 · 4 · 6 |
| `tests/test_sigmine.py` · `test_toybox_game.py` · `test_toybox_research.py`(새로) · `test_toybox_values.py` · `test_toybox.py` · `test_gamedrive.py` | 테스트 | 1 ~ 7 |
| `docs/10` · `11` · `05` · `07` · `09` · `README.md` · `CLAUDE.md` · 설계서 | 문서 | 9 |

`sigs` · `values` · `products` · `regions` · `settings` · `input` · `command` · `overlay` 는 바뀌지 않는다.

---

### Task 1: `srkit sig-mine` — 함수의 목표, 꼴의 상수, 앞의 명령부터

**브랜치:** `feat/toybox-research-engine` (`develop` 에서 나눈다)

**Files:**
- Modify: `src/srkit/sigmine.py`, `src/srkit/cli.py`
- Test: `tests/test_sigmine.py`

**Interfaces:**
- Consumes: 지금의 `sigmine.Image` · `Candidate` · `mine_address` · `mine_constants` · `cheat_ranges` · `listing`, `cli.cmd_sig_mine`.
- Produces:
  - `sigmine.mine_address(image, target, *, exclude=(), fewest=3, most=8, fixed=8, longest=60, sites=400, holding=(), back=0, through_jumps=False) -> list[Candidate]` — `target` 을 `rip` 상대로 가리키는 명령뿐 아니라 **`call`(`E8`) · `jmp`(`E9`)의 목표**인 자리에서도 뽑는다. `holding`: 서명 안의 명령이 정해진 바이트로 들고 있어야 하는 상수들. `back`: 가리키는 명령보다 그만큼 앞선 명령부터 시작한다. `through_jumps`: 무조건 `jmp` 를 지나서도 늘린다.
  - `sigmine.mine_constants(image, constants, *, …, holding=(), back=0, through_jumps=False)` — 같은 세 인자.
  - `uv run srkit sig-mine <값…> [--offset] [--with <상수…>] [--back N] [--most N] [--longest N] [--through-jumps]`. `--longest` 가 64 를 넘으면 `서명 하나는 64바이트까지입니다(…)` 를 찍고 1 로 끝난다.
  - 이 Task 는 개발 도구만 고친다 — ToyBox 의 DLL 은 바뀌지 않는다. Task 2 의 서명 21개는 이 도구로 뽑았다(다시 뽑는 명령은 Task 9 가 `docs/11` 에 적는다).

- [ ] **Step 0: 브랜치를 만들고 시작할 때의 상태를 본다**

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py status | head -1 && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-research-engine && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -2
```

Expected: `프로세스: 없음`(게임이 떠 있으면 테스트를 돌리지 않고 멈춘다), `빌드 완료: …\build\toybox\srtoybox.dll`, `418 passed`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

가짜 이미지 셋을 더한다 — 함수를 부르는 코드(`call` · `jmp`), 꼴의 상수를 든 코드(같은 전역을 가리키되 한 곳은 `je +50h` 의 거리만 50h 다), 무조건 `jmp` 로 갈래가 나뉘는 코드. 그리고 명령줄의 새 인자.

<!-- 고칠 곳: test -->
`tests/test_sigmine.py` 에서 다음 바로 앞에:

```python
def installed(game_dir) -> bytes:
```

이것을 더한다:

```python
F = 0x1300                                    # 가짜 함수(부르는 자리들이 가리킨다)
A, B, C = 0x1000 + 48, 0x1080 + 48, 0x1100 + 48


def calls_image() -> bytes:
    """함수 F 를 부르는 자리: A · B 는 뒤따르는 명령이 서로 다르고, C 는 앞에 인자를 싣는 명령 둘이 있고 바로 ret 다.
    넷째 자리는 call 이 아니다 — 다른 명령(movabs)의 상수 안에 E8 과 F 까지의 거리가 우연히 들어 있다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(4)] + [(F, F + 0x40)])
    end = fake.rip(image, fake.put(image, 0x1000, NOPS), bytes([0xE8]), F)     # A: call F / mov r9b,1 / xor r8d,r8d / xor edx,edx / ret
    fake.put(image, end, bytes.fromhex("41 B1 01 45 33 C0 33 D2 C3"))
    end = fake.rip(image, fake.put(image, 0x1080, NOPS), bytes([0xE8]), F)     # B: call F / mov r15,[rbp-48h] / mov r14,[rbp-50h] / ret
    fake.put(image, end, bytes.fromhex("4C 8B 7D B8 4C 8B 75 B0 C3"))
    end = fake.put(image, 0x1100, NOPS + bytes.fromhex("BA FF FF FF FF 49 8B CC"))   # C: mov edx,-1 / mov rcx,r12 / call F / ret
    fake.put(image, fake.rip(image, end, bytes([0xE8]), F), b"\xC3")
    end = fake.put(image, 0x1180, NOPS + bytes([0x48, 0xB8, 0x11]))            # movabs rax,<11 E8 거리 22 33> / ret
    fake.put(image, fake.rip(image, end, bytes([0xE8]), F), bytes([0x22, 0x33, 0xC3]))
    fake.put(image, F, b"\xC3")
    return bytes(image)


def test_a_function_is_mined_from_the_calls_that_reach_it():
    """call rel32 의 목표는 rip 상대 거리와 같은 셈이다 — 함수의 주소를 읽어 낼 서명이 된다."""
    image = sigmine.Image(calls_image())
    assert {A + 1, B + 1, C + 9, 0x1180 + 48 + 4} <= set(image.refs(F))    # 거리만 보면 넷째 자리도 F 를 가리킨다
    assert {c.at: c.text for c in sigmine.mine_address(image, F)} == {
        A: "E8 [rip] 41 B1 01 45 33 C0 33 D2", B: "E8 [rip] 4C 8B 7D B8 4C 8B 75 B0"}   # C 는 call 뒤가 바로 ret 다. 넷째는 call 이 아니다
    assert all(sigmine.count(image, c.text) == 1 for c in sigmine.mine_address(image, F))


def test_a_signature_can_start_before_the_instruction_that_points():
    """back: 가리키는 명령보다 앞선 명령부터 — 함수를 부르기 전에 인자를 싣는 명령을 서명에 넣는다."""
    image = sigmine.Image(calls_image())
    found = {c.at: c.text for c in sigmine.mine_address(image, F, back=2)}
    assert found[C - 0] == "BA FF FF FF FF 49 8B CC E8 [rip]"              # 서명의 자리는 그 앞선 명령이다
    assert found[A - 2].startswith("90 90 E8 [rip]") and len(found) == 3
    assert sigmine.mine_address(image, F, back=60) == []                   # 앞에 명령이 그만큼 없다


def shapes_image() -> bytes:
    """전역 G 를 읽는 자리 셋(mov rdx,[G]). X · Y 는 꼴의 상수 88h · 50h 를 든 명령이 뒤따르고, Z 는 50h 가 분기의 거리로만 나온다."""
    image = fake.shell([(0x1000 + 0x80 * i, 0x1080 + 0x80 * i) for i in range(3)])
    for at, code in [
            (0x1000, "48 69 F0 88 00 00 00  4C 89 74 24 48  48 8D 7A 50  C3"),      # X: imul rsi,rax,88h / mov [rsp+48h],r14 / lea rdi,[rdx+50h]
            (0x1080, "48 63 C7  48 83 C3 50  48 69 C8 88 00 00 00  C3"),             # Y: movsxd rax,edi / add rbx,50h / imul rcx,rax,88h
            (0x1100, "48 69 C8 88 00 00 00  48 85 C0  74 50  48 8B C8  C3")]:        # Z: imul rcx,rax,88h / test rax,rax / je +50h / mov rcx,rax
        end = fake.rip(image, fake.put(image, at, NOPS), bytes([0x48, 0x8B, 0x15]), G)
        fake.put(image, end, bytes.fromhex(code))
    return bytes(image)


def test_holding_grows_the_signature_over_the_shape_constants():
    """holding: 서명 안의 명령이 그 상수들을 정해진 바이트로 들 때까지 늘린다 — 꼴이 바뀐 빌드에서는 서명이 맞지 않는다."""
    image = sigmine.Image(shapes_image())
    plain = {c.at: c.text for c in sigmine.mine_address(image, G)}
    assert plain[A] == "48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48" and len(plain) == 3     # 한 번만 맞으면 거기서 멈춘다
    assert {c.at: c.text for c in sigmine.mine_address(image, G, holding=[0x88, 0x50])} == {
        A: "48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48 48 8D 7A 50",
        B: "48 8B 15 [rip] 48 63 C7 48 83 C3 50 48 69 C8 88 00 00 00"}     # Z 의 50h 는 je 의 거리다 — 든 것이 아니다
    assert sigmine.mine_address(image, G, holding=[0x99]) == []


def walk_image() -> bytes:
    """목록을 훑는 코드의 꼴: lea rcx,[rax+rax*2] / mov rdx,[rdi+rcx*8+3568C0h] / test rdx,rdx / je / cmp byte ptr [rdx+1Ch],1 /
    jmp(다음 명령으로) / mov rax,[rdx+10h] / ret"""
    image = fake.shell([(0x1000, 0x1080)])
    fake.put(image, 0x1000, NOPS + bytes.fromhex("48 8D 0C 40  48 8B 94 CF C0 68 35 00  48 85 D2  74 0B  80 7A 1C 01  EB 00  48 8B 42 10  C3"))
    return bytes(image)


def test_constants_can_hold_shape_constants_pass_jumps_and_start_earlier():
    image = sigmine.Image(walk_image())
    assert sigmine.mine_constants(image, [0x3568C0], holding=[0x1C, 0x10]) == []            # jmp 에서 멈춘다 — 10h 에 닿지 못한다
    found = sigmine.mine_constants(image, [0x3568C0], holding=[0x1C, 0x10], through_jumps=True)
    assert [(c.at, c.text) for c in found] == [(A + 4, "48 8B 94 CF [u32] 48 85 D2 74 0B 80 7A 1C 01 EB 00 48 8B 42 10")]
    found = sigmine.mine_constants(image, [0x3568C0], holding=[0x1C], back=1)
    assert [(c.at, c.text, c.length) for c in found] == [(A, "48 8D 0C 40 48 8B 94 CF [u32] 48 85 D2 74 0B 80 7A 1C 01", 21)]
    assert sigmine.mine_constants(image, [0x3568C0], holding=[0x0B]) == []                  # je 의 거리 0Bh 는 든 것이 아니다


```

`tests/test_sigmine.py` 에서 다음 바로 뒤에:

```python
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1", "2", "3"], offset=True, limit=3, sites=40)) == 1
```

이것을 더한다:

```python


def test_srkit_sig_mine_finds_functions_and_shape_constants(cfg, game_dir, capsys):
    """build 21347933: 함수의 목표(앞의 명령부터), 꼴의 상수를 든 서명, 서명의 길이 한도."""
    installed(game_dir)
    base = dict(offset=False, limit=3, sites=400, holding=None, back=0, most=None, longest=None, through_jumps=False)
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["bdd380"], **{**base, "back": 2})) == 0
    out = capsys.readouterr().out
    assert out.count("E8 [rip]") == 3 and out.count("call 0xbdd380") == 3  # 지역의 효과를 다시 셈하는 함수를 부르는 자리 셋
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1829620"], **{**base, "holding": ["88", "50"], "most": 14})) == 0
    out = capsys.readouterr().out
    assert "상수 0x88 · 0x50 을 든 것만" in out and out.count("88 00 00 00") == 3     # 기술 표: 레코드의 크기와 보유 묶음의 자리가 박힌 것
    assert cli.cmd_sig_mine(cfg, argparse.Namespace(values=["1829620"], **{**base, "longest": 65})) == 1
    assert "64바이트" in capsys.readouterr().out
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -8`

Expected: `5 failed, 14 passed` — 새 테스트 다섯이 실패한다: `TypeError: mine_address() got an unexpected keyword argument 'holding'`(와 `'back'`, `mine_constants() … 'holding'`), 함수를 부르는 자리에서 후보가 하나도 나오지 않는다(`assert {} == {…: 'E8 [rip] …'}`), `srkit sig-mine bdd380` 이 후보 없이 1 로 끝난다(`assert 1 == 0`).

- [ ] **Step 3: 구현한다**

`_first_instruction` 이 `E8` · `E9` 의 목표도 "가리키는 명령"으로 치고(명령의 경계는 `_boundary` 로 확인한다), 서명의 첫 낱말은 그 4바이트를 `[rip]` 로 적는다. `_holds` 는 `call` · `jmp` · 조건 분기의 거리를 상수로 치지 않는다.

<!-- 고칠 곳: code -->
`src/srkit/cli.py` 에서 다음을 찾아:

```python
    if args.offset:
        found = sigmine.mine_constants(image, values, exclude=cheats, sites=args.sites)
        what = "상수 " + " · ".join(f"{value:#x}" for value in values) + " 을 차례로 든 코드에서"
    else:
        found = sigmine.mine_address(image, values[0], exclude=cheats, sites=args.sites)
        what = f"{values[0]:#x} 를 가리키는 코드에서"
```

이렇게 바꾼다:

```python
    shape = dict(holding=[int(value, 16) for value in getattr(args, "holding", None) or []], back=getattr(args, "back", 0),
                 through_jumps=getattr(args, "through_jumps", False))
    for name in ("most", "longest"):                   # 주지 않으면 뽑는 쪽의 기본값(주소 8 · 상수 9 명령, 60바이트)
        if getattr(args, name, None):
            shape[name] = getattr(args, name)
    if shape.get("longest", 0) > 64:
        print("서명 하나는 64바이트까지입니다(native/srtoybox/sigs.h 의 SIG_MAX).")
        return 1
    if args.offset:
        found = sigmine.mine_constants(image, values, exclude=cheats, sites=args.sites, **shape)
        what = "상수 " + " · ".join(f"{value:#x}" for value in values) + " 을 차례로 든 코드에서"
    else:
        found = sigmine.mine_address(image, values[0], exclude=cheats, sites=args.sites, **shape)
        what = f"{values[0]:#x} 를 가리키는 코드에서"
    if shape["holding"]:
        what += ", 상수 " + " · ".join(f"{value:#x}" for value in shape["holding"]) + " 을 든 것만"
```

`src/srkit/cli.py` 에서 다음 바로 앞에:

```python
    m.set_defaults(fn=cmd_sig_mine)
```

이것을 더한다:

```python
    m.add_argument("--with", dest="holding", nargs="+", metavar="상수", help="서명 안의 명령이 들고 있어야 하는 상수들(16진수. 구조체의 "
                   "크기 · 칸의 자리) — 꼴이 바뀐 빌드에서 서명이 맞지 않게 한다")
    m.add_argument("--back", type=int, default=0, help="가리키는 명령보다 이만큼 앞선 명령부터 서명을 시작한다")
    m.add_argument("--most", type=int, help="서명의 최대 명령 수(기본: 주소 8, 상수 9)")
    m.add_argument("--longest", type=int, help="서명의 최대 바이트 수(기본 60. 서명 하나는 64바이트까지다)")
    m.add_argument("--through-jumps", action="store_true", help="무조건 jmp 를 지나서도 서명을 늘린다(목록을 훑는 코드처럼 갈래가 많은 곳)")
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
def _first_instruction(image: Image, pos: int, target: int):
    """4바이트 rip 상대 거리가 pos 에 있고 target 을 가리키는 명령."""
```

이렇게 바꾼다:

```python
def _branch(ins) -> bool:
    """4바이트 목표를 가진 call · jmp 다(목표는 명령의 마지막 4바이트)."""
    return bool((ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands
                and ins.operands[0].type == X.X86_OP_IMM)


def _first_instruction(image: Image, pos: int, target: int):
    """4바이트 rip 상대 거리가 pos 에 있고 target 을 가리키는 명령. call · jmp rel32 의 목표도 같은 셈이다(함수를 찾을 때)."""
```

`src/srkit/sigmine.py` 에서 다음 바로 뒤에:

```python
            return ins
```

이것을 더한다:

```python
    if image.data[pos - 1] in (0xE8, 0xE9) and _boundary(image, pos) == pos - 1:     # 앞의 바이트가 우연히 E8 인 자리는 거른다
        ins = next(_md.disasm(image.data[pos - 1:pos + 15], pos - 1), None)
        if ins is not None and ins.size == 5 and _branch(ins) and ins.operands[0].imm == target:
            return ins
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
    """명령 하나의 서명 글. 첫 명령의 rip 상대 거리는 읽어 낼 자리, 그 밖의 rip 상대 거리와 call · jmp 의 4바이트 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    rip = ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    if first:
```

이렇게 바꾼다:

```python
    """명령 하나의 서명 글. 첫 명령의 rip 상대 거리(call · jmp 면 목표)는 읽어 낼 자리, 그 밖의 rip 상대 거리와 목표는 구멍."""
    out = [f"{b:02X}" for b in ins.bytes]
    rip = ins.disp_size == 4 and any(op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP for op in ins.operands)
    if first and _branch(ins):
        out[ins.size - 4:] = ["[rip]"]
    elif first:
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
        out[ins.disp_offset:ins.disp_offset + 4] = ["?"] * 4
    elif (ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP)) and ins.size >= 5 and ins.operands \
            and ins.operands[0].type == X.X86_OP_IMM:
```

이렇게 바꾼다:

```python
        out[ins.disp_offset:ins.disp_offset + 4] = ["?"] * 4
    elif _branch(ins):
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
def mine_address(image: Image, target: int, *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400) -> list[Candidate]:
```

이렇게 바꾼다:

```python
def _back(image: Image, address: int, n: int) -> int | None:
    """address 의 명령보다 n 개 앞선 명령의 시작. 그 함수 조각을 처음부터 풀어 내려와 찾는다 — 조각이 함수 표에 없거나,
    풀이가 address 에 닿지 않거나, 앞에 명령이 n 개가 안 되면 None."""
    i = bisect.bisect_right(image._starts, address) - 1
    if i < 0 or not (image.funcs[i][0] <= address < image.funcs[i][1]):
        return None
    begin = image.funcs[i][0]
    starts: list[int] = []
    for at, _size, _mnemonic, _operands in _lite.disasm_lite(image.data[begin:address + 16], begin):
        if at >= address:
            return starts[-n] if at == address and len(starts) >= n else None
        starts.append(at)
    return None


def _stops(ins, through_jumps: bool) -> bool:
    """이 명령 뒤로는 서명을 늘리지 않는다: 함수의 끝. 무조건 jmp 는 through_jumps 가 아니면 끝으로 친다."""
    return ins.id in (X.X86_INS_RET, X.X86_INS_INT3) or (ins.id == X.X86_INS_JMP and not through_jumps)


def mine_address(image: Image, target: int, *, exclude: Sequence[tuple[int, int]] = (), fewest: int = 3, most: int = 8,
                 fixed: int = 8, longest: int = 60, sites: int = 400, holding: Sequence[int] = (), back: int = 0,
                 through_jumps: bool = False) -> list[Candidate]:
```

`src/srkit/sigmine.py` 에서 다음 바로 뒤에:

```python
    서명으로 친다. 쓰는 자리가 sites 보다 많으면 고르게 골라 그만큼만 본다.
```

이것을 더한다:

```python
    holding: 서명 안의 명령이 정해진 바이트로 들고 있어야 하는 상수들(구조체의 크기 · 칸의 자리 — 꼴이 바뀐 빌드에서 서명이
    맞지 않게 한다). back: 가리키는 명령보다 그만큼 앞선 명령부터 시작한다. through_jumps: 무조건 jmp 를 지나서도 늘린다.
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
        words: list[str] = []
        length = 0
        for n, ins in enumerate(_md.disasm(image.data[first.address:first.address + 160], first.address), start=1):
            more = _words(ins, first=n == 1)
```

이렇게 바꾼다:

```python
        start = _back(image, first.address, back) if back else first.address
        if start is None:
            continue
        words: list[str] = []
        length = 0
        missing = list(holding)
        for n, ins in enumerate(_md.disasm(image.data[start:start + 200], start), start=1):
            more = _words(ins, first=ins.address == first.address)
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
            text = " ".join(words)
            if n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                found.append(Candidate(image.root(first.address), first.address, length, text))
                break
            if n >= most or ins.id in (X.X86_INS_RET, X.X86_INS_INT3, X.X86_INS_JMP):
```

이렇게 바꾼다:

```python
            missing = [value for value in missing if _holds(ins, value) is None]
            text = " ".join(words)
            if ins.address >= first.address and not missing and n >= fewest and sum(len(w) == 2 for w in words) >= fixed \
                    and count(image, text, exact=False) == 1 and count(image, text) == 1:
                found.append(Candidate(image.root(start), start, length, text))
                break
            if n >= most or _stops(ins, through_jumps):
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
    """명령이 value 를 상수(imm)나 메모리 자리(disp. rip 상대는 아니다)로 들고 있으면 (명령 안의 자리, 크기 1 또는 4)."""
```

이렇게 바꾼다:

```python
    """명령이 value 를 상수(imm)나 메모리 자리(disp. rip 상대는 아니다)로 들고 있으면 (명령 안의 자리, 크기 1 또는 4).

    call · jmp · 조건 분기의 거리는 상수가 아니다(`je +0x24` 는 0x24 를 "들고" 있지 않다).
    """
    if ins.id == X.X86_INS_CALL or ins.group(X.X86_GRP_JUMP):
        return None
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
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
```

이렇게 바꾼다:

```python
def _grow(image: Image, first: int, constants: list[int], *, fewest: int, most: int, fixed: int, longest: int, within: int,
          unique: bool, holding: Sequence[int] = (), back: int = 0, through_jumps: bool = False) -> tuple[int, str] | None:
    """first 의 명령부터 constants 를 차례로 든 명령들을 지나, (unique 면) holding 의 상수를 든 명령들도 지나고 실행 구역에서
    한 번만 맞을 때까지 늘린 서명의 (시작, 글). back 이면 first 보다 그만큼 앞선 명령부터 시작한다."""
    start = _back(image, first, back) if back else first
    if start is None:
        return None
    words: list[str] = []
    length, wanted, since = 0, 0, 0
    missing = list(holding)
    for n, ins in enumerate(_md.disasm(image.data[start:start + 200], start), start=1):
        reached = ins.address >= first
        held = _holds(ins, constants[wanted]) if reached and wanted < len(constants) else None
        if ins.address == first and (held is None or held[1] != 4):
            return None                        # 첫 명령이 첫 상수를 4바이트로 들고 있어야 한다
        if reached and wanted < len(constants) and held is None:
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
        if wanted == len(constants):
            text = " ".join(words)
            if not unique:
                return text
            if n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                return text
        if n >= most or ins.id in (X.X86_INS_RET, X.X86_INS_INT3, X.X86_INS_JMP):
```

이렇게 바꾼다:

```python
        else:
            missing = [value for value in missing if _holds(ins, value) is None]
        if wanted == len(constants):
            text = " ".join(words)
            if not unique:
                return start, text
            if not missing and n >= fewest and sum(len(w) == 2 for w in words) >= fixed and count(image, text, exact=False) == 1 \
                    and count(image, text) == 1:
                return start, text
        if n >= most or _stops(ins, through_jumps):
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
                   fixed: int = 8, longest: int = 60, within: int = 4, sites: int = 400) -> list[Candidate]:
```

이렇게 바꾼다:

```python
                   fixed: int = 8, longest: int = 60, within: int = 4, sites: int = 400, holding: Sequence[int] = (),
                   back: int = 0, through_jumps: bool = False) -> list[Candidate]:
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
    값만 우연히 같은 코드도 후보로 나온다.
```

이렇게 바꾼다:

```python
    값만 우연히 같은 코드도 후보로 나온다. holding · back · through_jumps 는 mine_address 의 것과 같다.
```

`src/srkit/sigmine.py` 에서 다음을 찾아:

```python
    for start in starts[::max(1, len(starts) // sites)]:
        text = _grow(image, start, constants, unique=True, **options)
        if text:
```

이렇게 바꾼다:

```python
    for first in starts[::max(1, len(starts) // sites)]:
        grown = _grow(image, first, constants, unique=True, holding=holding, back=back, through_jumps=through_jumps, **options)
        if grown:
            start, text = grown
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 통과를 본다**

Run: `uv run pytest tests/test_sigmine.py -q 2>&1 | tail -1`

Expected: `19 passed`

Run: `PYTHONIOENCODING=utf-8 uv run srkit sig-mine bdd380 --back 2 --limit 3 2>&1 | head -12`

Expected(설치된 게임이 build 21347933 일 때): 후보마다 `BA FF FF FF FF 49 8B … E8 [rip]` 꼴의 서명과 그 명령들(`mov edx, 0xffffffff; mov rcx, r9; call 0xbdd380`), 끝 줄에 `서로 다른 함수 7개에서 후보가 나왔습니다. …`. 고치기 전에는 후보가 0개였다.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add src/srkit/sigmine.py src/srkit/cli.py tests/test_sigmine.py && git commit -q -F - <<'EOF'
feat: srkit sig-mine — 함수의 목표(call · jmp)도 캐고, 꼴의 상수를 든 서명을 고른다

- call · jmp 의 목표인 자리에서도 서명을 뽑는다(게임의 함수를 찾는 서명 — ToyBox 3단계 3).
- --with <상수…>: 서명 안의 명령이 그 상수(구조체의 크기 · 칸의 자리)를 들고 있어야 한다 — 꼴이 바뀐 빌드에서 맞지 않는 서명을 고른다.
- --back N(앞선 명령부터) · --most · --longest(64바이트까지) · --through-jumps.
- 명령이 상수를 "들고 있는가"가 분기의 거리(je +24h)를 상수로 치던 것을 고쳤다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `423 passed`, 새 커밋.

---

### Task 2: 새 찾기의 묶음 "연구" — 표 둘 · 세계 객체 · 연구 목록 · 다시 셈 함수

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`, `src/srkit/cli.py`
- Test: `tests/test_toybox_game.py`, `tests/toybox_fake_exe.py`, `tests/toybox_cheat_oracle.py`

**Interfaces:**
- Consumes: `sigs.h`(`sig_parse` · `sig_scan` · `sig_vote` — 읽어 낼 자리 둘까지), `locate.cpp` 의 `vote_table` · `vote_item` · `in_data` · `overlap` · `function_root` · `name_rows`, `GameAddresses`, `ValueLayout`, `SigRow`, `STATE_SIGS`(3) · `STATE_NEED`(2) · `REGION_SLOTS`(1024), `toybox._sig_rows` · `toybox.SigRow`.
- Produces:
  - `struct ResearchLayout { uint32_t tech_table, tech_count, design_table, design_count, world, lists, recompute; }` — 앞의 넷과 `world` · `recompute` 는 RVA, `lists` 는 세계 객체 안의 자리.
  - `RESEARCH_WANTED = 7`, `RESEARCH_NEED = 3`, 꼴의 상수 `TECH_SIZE`(0x88) · `TECH_KIND`(0) · `TECH_LEVEL`(1) · `TECH_NEEDS`(4) · `TECH_NEED_COUNT`(2) · `TECH_OWNERS`(0x50) · `DESIGN_SIZE`(0x168) · `DESIGN_NAME`(0) · `DESIGN_CLASS`(8) · `DESIGN_YEAR`(0xA) · `DESIGN_OPEN`(0x20) · `DESIGN_NEEDS`(0x34) · `DESIGN_NEED_COUNT`(4) · `DESIGN_HOLD_A`(0xEC) · `DESIGN_HOLD_A_BIT`(1) · `DESIGN_HOLD_B`(0xF0) · `DESIGN_HOLD_B_BIT`(0x1000000) · `DESIGN_OWNERS`(0xF8) · `OWNERS_BYTES`(128) · `LIST_STEP`(24) · `NODE_NEXT`(0x10) · `NODE_ID`(0x18) · `NODE_KIND`(0x1C) · `NODE_FLAGS`(0x20) · `NODE_GONE`(0x80000000) · `NODE_ENDED`(0x08000000).
  - `bool locate_research(const uint8_t *image, size_t size, const GameAddresses &state, ResearchLayout *out, SigRow *rows, char *why, size_t why_size)` — `rows` 는 `RESEARCH_WANTED * STATE_SIGS` 칸이거나 `nullptr`.
  - `bool locate_research_fits(const ResearchLayout &research, const ValueLayout &values, char *why, size_t why_size)` — 연구의 전역 넷이 세계 자료 포인터와 겹치지 않는가.
  - `const char *locate_research_shape()` — 꼴의 상수를 `이름\t값(16진수)` 줄로.
  - `vote_item` · `vote_table` 에 끝 인자 `int need = STATE_NEED`.
  - 내보내기: `srtoybox_locate_research(image, size, const GameAddresses *state, ResearchLayout *out, char *error, int error_size, char *rows, int rows_size)`(0 이면 찾았다), `srtoybox_locate_research_fits(const ResearchLayout *, const ValueLayout *, char *error, int error_size)`, `srtoybox_research_shape(char *out, int size)`.
  - Python: `toybox.RESEARCH_FIELDS` · `RESEARCH_NAMES` · `ResearchLayout`(ctypes), `toybox.research_of(lib, image, state) -> (dict | None, 까닭, list[SigRow])`, `toybox.research_fits(lib, research, values) -> str`, `toybox.research_shape(lib) -> dict[str, int]`, `Located.research` · `research_why` · `research_rows`. `srkit locate` 가 새 절을 보이고, 연구 묶음을 못 찾으면 1 로 끝난다.
  - 테스트 도우미: `toybox_fake_exe.SIZE`(0x10000) · `RECOMPUTE` · `WORLD` · `RESEARCH` · `RESEARCH_LAYOUT`, `toybox_cheat_oracle.research(image) -> dict`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

가짜 이미지에 연구의 자리를 더하고(가짜 "다시 셈 함수"는 함수 표에 시작으로 들어 있다), 치트 `technology` 의 본문에서 같은 것을 읽는 대조를 더하고, 찾기의 테스트를 쓴다: 치트 문자열 없이 찾는다 / 서명 하나만 깨져도 못 찾는다(스물한 가지) / 두 번 맞는 서명 · 값이 어긋나는 서명 / 말이 안 되는 값(열두 가지) / 세계 객체와 지역 표 / 세계 자료 포인터와의 겹침 / 설치된 게임에서의 값과 "상수 → 서명"의 표 / 치트 본문과의 대조.

<!-- 고칠 곳: test -->
`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
import struct
```

이것을 더한다:

```python
import re
```

`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
# build 21347933 (게임 12.1.1360, PE TimeDateStamp 0x695377b6) 의 주소. docs/11-game-internals.md 의 표와 같다.
```

이것을 더한다:

```python
FAKE = toybox_fake_exe
```

`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
GARBAGE = [b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)]
```

이렇게 바꾼다:

```python
BUILD_RESEARCH = {"tech_table": 0x1829620, "tech_count": 0x1829098, "design_table": 0x1829610, "design_count": 0x182909C,
                  "world": 0x17A9020, "lists": 0x3568C0, "recompute": 0xBDD380}
# 연구의 표와 목록의 꼴(native/srtoybox/locate.h 의 상수)이 박힌 서명: (찾을 것, 몇째 서명, 그 명령의 바이트).
# {이름:b} · {이름:d} 자리에 DLL 이 아는 그 상수가 1바이트 · 4바이트로 들어간다({이름+2:b} 는 2 를 더한 값).
# 게임이 업데이트되어 서명을 다시 뽑을 때 이 표도 함께 고친다 — 꼴의 상수가 서명에서 빠지면 여기서 걸린다.
RESEARCH_PINS = [
    ("tech_table", 0, "48 69 F0 {tech_size:d}"),                       # imul rsi,rax,<기술 레코드>
    ("tech_table", 0, "48 8D 7A {tech_owners:b}"),                     # lea rdi,[rdx+<보유 묶음>]
    ("tech_table", 0, "B9 {owners_bytes:d}"),                          # mov ecx,<묶음의 크기> (게임이 새 묶음을 받는 곳)
    ("tech_table", 1, "4C 69 CE {tech_size:d} 48 83 C1 {tech_owners:b}"),
    ("tech_table", 2, "44 38 24 03"),                                  # cmp byte ptr [rbx+rax],r12b — 빈 자리는 +0 의 바이트로 가린다
    ("tech_table", 2, "0F B6 4C 03 {tech_level:b}"),                   # movzx ecx,byte ptr [rbx+rax+<수준>]
    ("tech_count", 0, "80 39 00"),                                     # cmp byte ptr [rcx],0
    ("tech_count", 0, "0F BF 41 {tech_needs:b} 3B C6 74 08 0F BF 41 {tech_needs+2:b}"),   # movsx eax,word ptr [rcx+<선행>] 둘
    ("tech_count", 1, "0F BF 44 39 {tech_needs:b}"),
    ("tech_count", 1, "0F BF 44 39 {tech_needs+2:b}"),
    ("tech_count", 2, "49 69 D6 {tech_size:d}"),
    ("tech_count", 2, "0F BF 42 {tech_needs:b} 89 44 24 60 0F BF 42 {tech_needs+2:b}"),
    ("design_table", 0, "49 8D 9F {design_owners:d}"),                 # lea rbx,[r15+<보유 묶음>]
    ("design_table", 0, "48 69 C8 {design_size:d}"),                   # imul rcx,rax,<부대 설계 레코드>
    ("design_table", 0, "B9 {owners_bytes:d}"),
    ("design_table", 1, "49 39 38"),                                   # cmp qword ptr [r8],rdi — 빈 자리는 +0 의 포인터로 가린다
    ("design_table", 1, "41 F7 80 {design_hold_b:d} {design_hold_b_bit:d}"),     # test dword ptr [r8+<깃발 B>],<비트>
    ("design_table", 1, "41 F6 80 {design_hold_a:d} {design_hold_a_bit:b}"),     # test byte ptr [r8+<깃발 A>],<비트>
    ("design_table", 1, "66 41 39 78 {design_open:b}"),                # cmp word ptr [r8+<연구 대상>],di
    ("design_table", 2, "48 83 3C 2B 00"),                             # cmp qword ptr [rbx+rbp],0
    ("design_table", 2, "F7 84 2B {design_hold_b:d} {design_hold_b_bit:d}"),
    ("design_table", 2, "F6 84 2B {design_hold_a:d} {design_hold_a_bit:b}"),
    ("design_table", 2, "66 83 7C 2B {design_open:b} 00"),
    ("design_count", 0, "48 69 CB {design_size:d}"),
    ("design_count", 0, "66 42 83 7C 39 {design_open:b} 00"),
    ("design_count", 0, "4D 8D 4F {design_needs:b}"),                  # lea r9,[r15+<선행>]
    ("design_count", 1, "49 69 DE {design_size:d}"),
    ("design_count", 1, "0F B7 44 0B {design_needs:b}"),               # movzx eax,word ptr [rbx+rcx+<선행>]
    ("design_count", 2, "49 81 C2 {design_size:d}"),                   # add r10,<부대 설계 레코드>
    ("lists", 0, "48 8D 0C 40 48 8B 94 CA"),                           # lea rcx,[rax+rax*2] / mov rdx,[rdx+rcx*8+…] — 칸 하나가 24바이트
    ("lists", 0, "80 79 {node_kind:b} 02"),                            # cmp byte ptr [rcx+<종류>],2
    ("lists", 0, "44 3B 59 {node_id:b}"),                              # cmp r11d,[rcx+<번호>]
    ("lists", 0, "48 8B 41 {node_next:b}"),                            # mov rax,[rcx+<다음>]
    ("lists", 0, "F7 41 {node_flags:b} 00 00 00 88"),                  # test dword ptr [rcx+<깃발>],88000000h
    ("lists", 1, "80 79 {node_kind:b} 01"),
    ("lists", 1, "44 3B 49 {node_id:b}"),
    ("lists", 1, "48 8B 40 {node_next:b}"),
    ("lists", 1, "F7 41 {node_flags+4:b} 00 00 00 88"),                # 둘째 쪽의 깃발
    ("lists", 2, "48 8D 0C 40 49 8B 94 CC"),
    ("lists", 2, "80 7B {node_kind:b} 01"),
    ("lists", 2, "3B 7B {node_id:b}"),
    ("lists", 2, "48 8B 40 {node_next:b}"),
    ("recompute", 0, "BA FF FF FF FF 49 8B C9 E8"),                    # mov edx,-1 / mov rcx,r9 / call — 인자는 (세계 객체, 지역 인덱스)
    ("recompute", 1, "BA FF FF FF FF 49 8B CA E8"),
    ("recompute", 2, "BA FF FF FF FF 49 8B CC E8"),
]
# 서명에 박혀 있어야 하는 상수(쓰기를 가른다). 박지 못한 것: design_class · design_year(표시에만 쓴다), 선행의 개수(tech_need_count 는
# 선행 둘의 자리로 드러난다. design_need_count 는 드러나지 않는다), tech_kind · design_name(자리가 0 이라 명령에 상수가 없다 — 명령의 꼴로 박았다)
RESEARCH_PINNED = {"tech_size", "tech_level", "tech_needs", "tech_owners", "design_size", "design_open", "design_needs", "design_hold_a",
                   "design_hold_a_bit", "design_hold_b", "design_hold_b_bit", "design_owners", "owners_bytes", "node_next", "node_id",
                   "node_kind", "node_flags"}
GARBAGE =[b"", b"MZ", bytes(0x1000), b"MZ" + bytes(0x3A) + struct.pack("<I", 0x7FFFFFF0) + bytes(0x100)]
```

`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
def installed_image(game_dir) -> bytes:
```

이것을 더한다:

```python
@pytest.fixture(scope="module")
def research_sigs(lib):
    """DLL 에 든 연구의 서명 표: [(찾을 것, 서명 글)] — 찾을 것마다 셋, 표의 순서대로."""
    return [(row.name, row.text) for row in toybox.research_of(lib, b"", None)[2]]


```

`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
    for row in toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]:
```

이렇게 바꾼다:

```python
    for row in (toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]
                + toybox.research_of(lib, image, BUILD_STATE)[2]):
```

`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
    rows = toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]
```

이렇게 바꾼다:

```python
    rows = (toybox.state_of(lib, image)[2] + toybox.values_of(lib, image)[2] + toybox.more_of(lib, image)[2]
            + toybox.research_of(lib, image, BUILD_STATE)[2])
```

`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
def test_legacy_finds_the_handler_from_the_cheat_anchor(lib, sigs):
```

이것을 더한다:

```python
def research(lib, image: bytes, state: dict | None = toybox_fake_exe.STATE):
    """연구의 찾기를 그 이미지에 돌린다. state 는 이미 찾은 상태 묶음(가짜 이미지의 것) — 서명을 심지 않아도 값만 넘기면 된다."""
    return toybox.research_of(lib, image, state)


def test_the_research_table_has_three_signatures_per_item(research_sigs):
    assert [name for name, _ in research_sigs] == [name for name in toybox.RESEARCH_FIELDS for _ in range(3)]
    assert len({text for _, text in research_sigs}) == 21


def test_research_is_found_in_an_image_without_any_cheat_string(lib, research_sigs):
    """연구의 표 · 목록 · 다시 셈 함수도 치트 문자열에 기대지 않고 찾는다."""
    image = toybox_fake_exe.sig_image(research_sigs)
    assert b"cheat" not in image
    found, why, rows = research(lib, image)
    assert found == toybox_fake_exe.RESEARCH_LAYOUT, why
    assert [row.count for row in rows] == [1] * 21
    assert [(row.value, row.value2) for row in rows if row.name == "world"] == [toybox_fake_exe.RESEARCH["world"]] * 3   # 주소 · 지역 표까지의 거리
    assert all(row.value == toybox_fake_exe.RESEARCH_LAYOUT[row.name] for row in rows)


@pytest.mark.parametrize("which", range(21))
def test_research_needs_all_three_signatures_of_every_item(lib, research_sigs, which):
    """다른 묶음과 다르다: 서명 하나만 깨져도 못 찾은 것이다 — 표와 목록의 꼴(레코드의 크기 · 칸의 자리)이 서명마다 박혀 있어,
    하나라도 맞지 않으면 꼴이 바뀐 것일 수 있다. 틀린 꼴로 모든 나라가 함께 쓰는 표에 쓰느니 쓰지 않는다."""
    found, why, rows = research(lib, toybox_fake_exe.sig_image(research_sigs, broken={which}))
    assert found is None and "3개 가운데 2개" in why
    assert rows[which].count == 0 and sum(row.count for row in rows) == 20


def test_a_research_signature_that_matches_twice_does_not_count(lib, research_sigs):
    found, why, rows = research(lib, toybox_fake_exe.sig_image(research_sigs, twice={6}))     # 부대 설계 표의 첫 서명
    assert found is None and rows[6].count == 2 and "부대 설계 표: 서명 3개 가운데 2개" in why


def test_research_signatures_that_disagree_are_refused(lib, research_sigs):
    found, why, _ = research(lib, toybox_fake_exe.sig_image(research_sigs, stray={13}))       # 세계 객체의 둘째 서명
    assert found is None and why == "세계 객체: 서명들이 서로 다른 값을 냅니다"



@pytest.mark.parametrize("targets, reason", [
    ({"tech_table": FAKE.DATA + 0x4C}, "기술 표: 찾은 주소가 8 의 배수가 아닙니다"),
    ({"tech_table": FAKE.SIZE + 0x100}, "기술 표: 찾은 주소가 실행 파일 밖입니다"),
    ({"design_table": FAKE.RDATA + 0x100}, "부대 설계 표: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다"),
    ({"tech_count": FAKE.DATA + 0x48}, "기술 수: 찾은 주소가 기술 표 의 자리와 겹칩니다"),
    ({"design_count": FAKE.STATE["player_index"]}, "부대 설계 수: 찾은 주소가 플레이어 인덱스 의 자리와 겹칩니다"),
    ({"world": (FAKE.WORLD, 0x88)}, "세계 객체: 지역 표까지의 거리가 맞지 않습니다"),
    ({"world": (FAKE.RDATA + 0x100, FAKE.STATE["region_table"] - FAKE.RDATA - 0x100)}, "세계 객체: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다"),
    ({"lists": 0x2104}, "연구 목록: 찾은 자리가 범위 밖입니다"),                           # 포인터가 든 칸은 8 의 배수 자리다
    ({"lists": 0x9000}, "연구 목록: 찾은 자리가 범위 밖입니다"),                           # 24바이트 × 1024칸이 자료 구역을 넘는다
    ({"lists": 0x1000}, "연구 목록: 찾은 자리가 지역 표 의 자리와 겹칩니다"),
    ({"recompute": FAKE.RECOMPUTE + 4}, "다시 셈 함수: 찾은 주소가 함수의 시작이 아닙니다"),
    ({"recompute": FAKE.DATA + 0x400}, "다시 셈 함수: 찾은 주소가 함수의 시작이 아닙니다"),   # 코드가 아니다
], ids=["unaligned", "outside", "read-only", "on-another-item", "on-a-state-global", "wrong-distance", "world-not-data",
        "list-unaligned", "list-runs-out", "list-on-the-region-table", "inside-a-function", "not-code"])
def test_research_that_does_not_add_up_is_refused(lib, research_sigs, targets, reason):
    """서명 셋이 모두 맞아도 읽어 낸 값이 말이 안 되면 못 찾은 것이다."""
    found, why, _ = research(lib, toybox_fake_exe.sig_image(research_sigs, targets=targets))
    assert found is None and why == reason


def test_research_checks_the_world_object_against_the_region_table_found_elsewhere(lib, research_sigs):
    """세계 객체의 서명은 "지역 표까지의 거리"도 읽는다. 세계 객체 + 그 거리가 상태 묶음이 따로 찾은 지역 표가 아니면 엉뚱한 객체다."""
    image = toybox_fake_exe.sig_image(research_sigs)
    moved = {**toybox_fake_exe.STATE, "region_table": toybox_fake_exe.STATE["region_table"] + 8}
    assert research(lib, image, moved)[:2] == (None, "세계 객체: 지역 표까지의 거리가 맞지 않습니다")
    assert research(lib, image, None)[:2] == (None, "세계 객체: 지역 표까지의 거리가 맞지 않습니다")     # 상태 묶음을 못 찾았다


def test_research_is_found_beside_the_state_table(lib, sigs, research_sigs):
    """상태의 서명과 한 이미지에 있어도 저마다 찾는다. 연구의 서명 하나가 깨지면 연구만 못 찾는다."""
    image = toybox_fake_exe.sig_image(sigs + research_sigs)
    state = toybox.state_of(lib, image)[0]
    assert state == toybox_fake_exe.STATE and research(lib, image, state)[0] == toybox_fake_exe.RESEARCH_LAYOUT
    image = toybox_fake_exe.sig_image(sigs + research_sigs, broken={21 + 20})
    assert toybox.state_of(lib, image)[0] == toybox_fake_exe.STATE and research(lib, image)[0] is None


def test_research_must_not_sit_on_the_world_pointer_of_the_values(lib):
    """연구 묶음과 값 묶음을 저마다 찾았어도, 연구의 전역이 세계 자료 포인터와 겹치면 어느 쪽이 엉뚱한 것을 읽었는지 알 수 없다 —
    연구 묶음을 버린다(값 묶음은 그대로 쓴다). 바로 옆은 겹침이 아니다."""
    found, values = toybox_fake_exe.RESEARCH_LAYOUT, toybox_fake_exe.VALUE_LAYOUT
    assert toybox.research_fits(lib, found, values) == ""
    for name, label in (("tech_table", "기술 표"), ("tech_count", "기술 수"), ("design_table", "부대 설계 표")):
        clash = {**values, "world_pointer": found[name]}
        assert toybox.research_fits(lib, found, clash) == f"{label}: 찾은 주소가 세계 자료 포인터 의 자리와 겹칩니다"
    # 가짜 이미지에서 부대 설계 수(4바이트) 바로 뒤가 부대 설계 표다 — 8바이트 포인터는 둘에 걸치고, 표의 순서로 먼저인 것을 든다
    assert toybox.research_fits(lib, found, {**values, "world_pointer": found["design_count"]}).endswith("세계 자료 포인터 의 자리와 겹칩니다")
    assert toybox.research_fits(lib, found, {**values, "world_pointer": found["tech_table"] - 4}) != ""          # 끝이 걸친다
    assert toybox.research_fits(lib, found, {**values, "world_pointer": found["tech_table"] + 0x100}) == ""


@pytest.mark.parametrize("image", GARBAGE, ids=GARBAGE_IDS)
def test_research_survives_garbage(lib, image):
    found, why, _ = research(lib, image)
    assert found is None and why


def test_research_on_the_installed_game(lib, game_dir):
    """build 21347933: 서명 21개가 저마다 실행 구역에 정확히 한 번 맞고, 읽어 낸 값이 docs/11 의 표와 같다."""
    found, why, rows = toybox.research_of(lib, installed_image(game_dir), BUILD_STATE)
    assert found == BUILD_RESEARCH, why
    assert [row.count for row in rows] == [1] * 21
    assert all(row.value == BUILD_RESEARCH[row.name] for row in rows)
    assert {row.value2 for row in rows if row.name == "world"} == {BUILD_STATE["region_table"] - BUILD_RESEARCH["world"]}


def test_the_shape_of_the_research_tables_is_pinned_in_the_signatures(lib, research_sigs):
    """표와 목록의 꼴은 읽어 내지 않고 상수로 둔다(locate.h). 그 상수가 서명의 명령에 그대로 박혀 있어야 한다 —
    꼴이 바뀐 빌드에서 서명이 맞지 않게. DLL 의 상수를 고치면서 서명을 그대로 두면 여기서 걸린다."""
    shape = toybox.research_shape(lib)
    assert shape["need"] == 3 and shape["list_step"] == 24 and shape["tech_kind"] == 0 and shape["design_name"] == 0
    assert shape["tech_need_count"] == 2 and shape["node_gone"] | shape["node_ended"] == 0x88000000
    texts = {(name, i % 3): text for i, (name, text) in enumerate(research_sigs)}
    pinned = set()

    def fill(m) -> str:
        pinned.add(m[1])
        value = shape[m[1]] + int(m[2] or 0)
        return " ".join(f"{b:02X}" for b in value.to_bytes(1 if m[3] == "b" else 4, "little"))

    for item, which, template in RESEARCH_PINS:
        wanted = re.sub(r"\{([a-z_]+)(\+\d+)?:([bd])\}", fill, template)
        assert wanted in texts[item, which], (item, which, wanted)
    assert pinned == RESEARCH_PINNED
    assert {item for item, _, _ in RESEARCH_PINS} == set(toybox.RESEARCH_FIELDS) - {"world"}     # 세계 객체는 거리를 읽어 견준다


def test_research_agrees_with_what_the_cheat_code_says(lib, game_dir):
    """치트 코드가 남아 있는 빌드에서의 대조: 서명으로 찾은 것과 DLL 이 아는 꼴 == 치트 technology 의 본문이 쓰는 것."""
    oracle = pytest.importorskip("toybox_cheat_oracle", reason="capstone 이 없다 (uv sync)")
    image = installed_image(game_dir)
    said = oracle.research(image)
    found, shape = toybox.research_of(lib, image, BUILD_STATE)[0], toybox.research_shape(lib)
    assert {name: found[name] for name in ("world", "tech_count", "tech_table", "lists", "recompute")} == \
        {name: said[name] for name in ("world", "tech_count", "tech_table", "lists", "recompute")}
    names = ("tech_size", "tech_level", "tech_owners", "owners_bytes", "node_kind", "node_id", "node_next")
    assert {name: shape[name] for name in names} == {name: said[name] for name in names}


```

`tests/test_toybox_game.py` 에서 다음 바로 뒤에:

```python
    assert len(located.more_rows) == 21
```

이것을 더한다:

```python
    assert located.research is not None and set(located.research) == set(toybox.RESEARCH_FIELDS), located.research_why
    assert len(located.research_rows) == 21
```

`tests/toybox_cheat_oracle.py` 에서 다음을 찾아:

```python
(3단계 2 의 "더 쓰는 값"은 치트 finalexam · shelovesme · love · neutral 의 본문과 댄다.)
```

이렇게 바꾼다:

```python
(3단계 2 의 "더 쓰는 값"은 치트 finalexam · shelovesme · love · neutral 의 본문과, 3단계 3 의 연구는 치트 technology 의 본문과 댄다.)
```

`tests/toybox_cheat_oracle.py` 에서 다음 바로 뒤에:

```python
    out["casus"] = love["mine_zero"][0]
```

이것을 더한다:

```python
    return out


def research(image_bytes: bytes) -> dict[str, int]:
    """연구 묶음 가운데 치트 technology 의 본문에서 읽을 수 있는 것: 세계 객체 · 기술 수 · 기술 표 · 연구 목록의 자리 · 다시 셈 함수,
    그리고 꼴의 상수(tech_size · tech_level · tech_owners · owners_bytes · node_kind · node_id · node_next).
    부대 설계의 표는 이 치트가 건드리지 않는다 — 여기에 없다."""
    image = sigmine.Image(image_bytes)
    data = image.data
    use = _uses(image, "cheat technology")[0]
    body = _body(image, "cheat technology")

    def find(pattern: bytes) -> re.Match:
        m = re.search(pattern, body, re.S)
        assert m is not None, pattern
        return m

    out = {}
    m = find(rb"\x4c\x8d\x3d....\x44\x39\x35....")                          # lea r15,[세계 객체] / cmp [기술 수],r14d
    out["world"] = _target(data, use + m.start(), 3, 7)
    out["tech_count"] = _target(data, use + m.start() + 7, 3, 7)
    m = find(rb"\x48\x8d\x0c\x52\x49\x8b\x94\xcf(....)")                    # lea rcx,[rdx+rdx*2] / mov rdx,[r15+rcx*8+연구 목록]
    out["lists"] = struct.unpack("<I", m.group(1))[0]
    m = find(rb"\x80\x7f(.)\x01\x75.\x44\x3b\x77(.)")                       # cmp byte ptr [rdi+종류],1 / jne / cmp r14d,[rdi+번호]
    out["node_kind"], out["node_id"] = m.group(1)[0], m.group(2)[0]
    out["node_next"] = find(rb"\x48\x8b\x40(.)\x48\x8b\xf8").group(1)[0]     # mov rax,[rax+다음] / mov rdi,rax
    m = find(rb"\x48\x8b\x0d....\x41\x0f\xb6\x44\x0c(.)")                    # mov rcx,[기술 표] / movzx eax,byte ptr [r12+rcx+수준]
    out["tech_table"] = _target(data, use + m.start(), 3, 7)
    out["tech_level"] = m.group(1)[0]
    out["tech_owners"] = find(rb"\x48\x8d\x79(.)\x49\x03\xfc").group(1)[0]   # lea rdi,[rcx+보유 묶음] / add rdi,r12
    out["owners_bytes"] = struct.unpack("<I", find(rb"\xb9(....)\xe8....\x4c\x8b\xc8").group(1))[0]   # mov ecx,묶음의 크기 / call / mov r9,rax
    out["tech_size"] = struct.unpack("<I", find(rb"\x49\x81\xc4(....)").group(1))[0]                  # add r12,레코드의 크기
    m = find(rb"\xba\xff\xff\xff\xff\x49\x8b\xcf\xe8....")                  # mov edx,-1 / mov rcx,r15 / call 다시 셈
    out["recompute"] = _target(data, use + m.start() + 8, 1, 5)
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음, 값 묶음, 더 쓰는 값)과, 옛 찾기가 보는
```

이렇게 바꾼다:

```python
게임의 코드를 옮긴 것이 아니다. 새 찾기가 보는 서명(DLL 의 서명 표에서 받아 심는다 — 상태 묶음, 값 묶음, 더 쓰는 값, 연구)과, 옛 찾기가 보는
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
SIZE = 0x8000                                 # 지역 표(8바이트 × 1024칸)가 DATA + 0x200 부터 들어갈 만큼
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER = 0x1000, 0x1800
```

이렇게 바꾼다:

```python
SIZE = 0x10000                                # 지역 표(8바이트 × 1024칸)와 그 뒤의 연구 목록(24바이트 × 1024칸)이 들어갈 만큼
TEXT, RDATA, PDATA, DATA = 0x1000, 0x3000, 0x4000, 0x5000
HANDLER, CALLER = 0x1000, 0x1800
RECOMPUTE = TEXT + 0xC00                      # 가짜 "다시 셈 함수" — 함수 표에 그 시작으로 들어 있다
```

`tests/toybox_fake_exe.py` 에서 다음 바로 앞에:

```python
PLANT, AGAIN = TEXT + 0x1000, TEXT + 0x1800     # 서명을 심는 곳, 같은 서명을 한 번 더 심는 곳
```

이것을 더한다:

```python
# 새 찾기(연구)의 가짜 값. 세계 객체의 서명은 (주소, 지역 표까지의 거리)를 함께 읽는다. 연구 목록은 세계 객체 안의 자리다 —
# 지역 표(WORLD + 0x80 부터 0x2000 바이트)의 뒤, 0x6000 바이트
RESEARCH = {"tech_table": DATA + 0x48, "tech_count": DATA + 0x50, "design_table": DATA + 0x58, "design_count": DATA + 0x54,
            "world": (WORLD, 0x80), "lists": 0x2100, "recompute": RECOMPUTE}
RESEARCH_LAYOUT = {**RESEARCH, "world": WORLD}
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
    targets 로 가짜 주소 · 값을 바꾼다(STATE · VALUES · MORE 의 이름으로).
    """
    image = into if into is not None else shell([(PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **MORE, **(targets or {})}
```

이렇게 바꾼다:

```python
    targets 로 가짜 주소 · 값을 바꾼다(STATE · VALUES · MORE · RESEARCH 의 이름으로).
    """
    image = into if into is not None else shell([(RECOMPUTE, RECOMPUTE + 0x40), (PLANT, TEXT + 0x2000)])
    at = {**STATE, **VALUES, **MORE, **RESEARCH, **(targets or {})}
```

`tests/toybox_fake_exe.py` 에서 다음을 찾아:

```python
    image = shell([(HANDLER, HANDLER + 0x200), (CALLER, CALLER + 0x20), (CALLER + 0x20, CALLER + 0x100), (PLANT, TEXT + 0x2000)])
```

이렇게 바꾼다:

```python
    image = shell([(HANDLER, HANDLER + 0x200), (CALLER, CALLER + 0x20), (CALLER + 0x20, CALLER + 0x100), (RECOMPUTE, RECOMPUTE + 0x40),
                   (PLANT, TEXT + 0x2000)])
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -4`

Expected: `10 failed, 107 passed, 40 errors` — 새 테스트는 `AttributeError: module 'srkit.toybox' has no attribute 'research_of'`(· `'research_fits'` · `'Located' object has no attribute 'research'`)로 실패하거나, 서명 표를 읽는 fixture(`research_sigs`)에서 같은 까닭으로 오류가 난다. 지금 있던 테스트 가운데 연구의 줄을 더한 셋(서명이 치트 코드 밖인가 · 서로 다른 함수인가 · `srkit locate` 의 출력)도 함께 실패한다.

- [ ] **Step 3: 구현한다**

서명 표 `RESEARCH`(일곱 × 셋)와 `search_research` 를 더한다. 투표는 지금의 `vote_table` 을 쓰되 "셋 가운데 몇이 맞아야 하는가"를 인자로 받는다(연구는 셋 모두).

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
// 두 묶음의 대조(locate_fits). 0 이면 맞는다. -1 이면 error 에 까닭.
```

이것을 더한다:

```cpp
// 새 찾기(연구, 서명으로). state 는 이미 찾은 상태 묶음이다(지역 표를 견준다. nullptr 이면 못 찾은 것으로 친다).
// 0 이면 out 을 채웠다. -1 이면 error 에 까닭. rows 는 srtoybox_locate_state 와 같다.
EXPORT int srtoybox_locate_research(const unsigned char *image, unsigned long long size, const GameAddresses *state,
                                    ResearchLayout *out, char *error, int error_size, char *rows, int rows_size)
{
    ResearchLayout found = {};
    SigRow table[RESEARCH_WANTED * STATE_SIGS];
    char why[160] = "";
    const bool ok = locate_research(image, static_cast<size_t>(size), state != nullptr ? *state : GameAddresses(), &found, table, why,
                                    sizeof(why));
    if (rows != nullptr)
        put(rows_text(table, RESEARCH_WANTED * STATE_SIGS), rows, rows_size);
    if (!ok) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

// 연구 묶음과 값 묶음의 대조(locate_research_fits). 0 이면 맞는다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate_research_fits(const ResearchLayout *research, const ValueLayout *values, char *error, int error_size)
{
    char why[160] = "";
    if (research == nullptr || values == nullptr)
        return -1;
    if (locate_research_fits(*research, *values, why, sizeof(why)))
        return 0;
    put(why, error, error_size);
    return -1;
}

// 연구의 표와 목록의 꼴(locate.h 의 상수): 한 줄에 "이름\t값(16진수)". 테스트가 서명에 박힌 바이트와 댄다.
EXPORT int srtoybox_research_shape(char *out, int size)
{
    return put(locate_research_shape(), out, size);
}

```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개, 더 쓰는 값 21개)
static_assert(VALUE_WANTED <= STATE_WANTED && MORE_WANTED <= STATE_WANTED,
              "서명을 맞추는 배열은 상태 묶음의 크기로 잡았다 — 더 큰 표를 더하면 MAX_TABLE 을 키운다");
static_assert(sizeof(MoreLayout) == MORE_WANTED * sizeof(uint32_t), "MoreLayout 의 필드는 표 MORE 의 순서대로 uint32_t 일곱이다");
```

이렇게 바꾼다:

```cpp
// 연구의 일곱. 같은 규칙으로 뽑되(uv run srkit sig-mine …) 꼴의 상수가 박힌 명령까지 늘렸다(--with · --back · --through-jumps).
// 서명마다 무엇이 박혀 있는지는 docs/11-game-internals.md 의 표와 tests/test_toybox_game.py 의 RESEARCH_PINS 에 있다:
//   기술 표        레코드 88h · 보유 묶음 +50h · 묶음 80h 바이트 / 수준 +1 · 빈 자리(+0 이 0)
//   기술 수        선행 +4 · +6, 레코드 88h
//   부대 설계 표   보유 묶음 +F8h · 레코드 168h · 묶음 80h 바이트 / 깃발 +F0h(1000000h) · +ECh(1) · 연구 대상 +20h · 빈 자리(+0 이 0)
//   부대 설계 수   레코드 168h · 연구 대상 +20h · 선행 +34h
//   세계 객체      lea 의 목표와, 바로 뒤 명령의 "지역 표까지의 거리"(둘을 읽는다 — 상태 묶음의 지역 표와 견준다)
//   연구 목록      칸 24바이트(×3 ×8) · 노드의 종류 +1Ch · 번호 +18h · 다음 +10h · 깃발 +20h · +24h
//   다시 셈 함수   call 의 목표. 앞의 두 명령(mov edx,-1 / mov rcx,<세계 객체>)이 인자의 꼴을 박는다
const struct ResearchWanted {
    const char *name;                       // srkit locate 와 테스트가 본다(ResearchLayout 의 필드 순서와 같다)
    const char *label;                      // 로그와 창에 나오는 이름
    const char *sigs[STATE_SIGS];
} RESEARCH[RESEARCH_WANTED] = {
    {"tech_table", "기술 표",
     {"48 8B 15 [rip] 48 69 F0 88 00 00 00 4C 89 74 24 48 48 8D 7A 50 44 0F B7 71 04 41 8B EE 48 03 FE 74 3C 48 8B 17 48 85 D2 75 10 "
      "B9 80 00 00 00",
      "48 8B 0D [rip] 4C 69 CE 88 00 00 00 48 83 C1 50",
      "48 8B 05 [rip] 44 38 24 03 76 33 8B 54 03 4C F6 C2 40 75 2A 0F B6 4C 03 01"}},
    {"tech_count", "기술 수",
     {"39 3D [rip] 7E 7B 48 89 5C 24 30 48 8B DF 0F 1F 00 48 8B 0D ? ? ? ? 48 03 CB 80 39 00 76 4B 0F BF 41 04 3B C6 74 08 "
      "0F BF 41 06",
      "44 8B 0D [rip] 33 DB 48 89 7C 24 40 45 85 C9 0F 8E ? ? ? ? 33 FF 0F 1F 00 48 8B 0D ? ? ? ? 80 3C 39 00 76 7E "
      "0F BF 44 39 04 8B 55 18 3B C2 74 09 0F BF 44 39 06",
      "44 3B 35 [rip] 0F 8D ? ? ? ? 49 69 D6 88 00 00 00 48 03 15 ? ? ? ? F6 05 ? ? ? ? 02 0F BF 42 04 89 44 24 60 0F BF 42 06"}},
    {"design_table", "부대 설계 표",
     {"4C 8B 3D [rip] 49 63 04 24 49 8D 9F F8 00 00 00 44 0F B7 77 04 48 69 C8 68 01 00 00 41 8B FE 48 03 D9 74 2B 48 8B 03 "
      "48 85 C0 75 0D B9 80 00 00 00",
      "4C 8B 05 [rip] 4D 03 C2 49 39 38 74 3B 41 F7 80 F0 00 00 00 00 00 00 01 75 2E 41 F6 80 EC 00 00 00 01 75 24 66 41 39 78 20",
      "48 8B 1D [rip] 48 83 3C 2B 00 0F 84 ? ? ? ? F7 84 2B F0 00 00 00 00 00 00 01 0F 85 ? ? ? ? F6 84 2B EC 00 00 00 01 "
      "0F 85 ? ? ? ? 66 83 7C 2B 20 00"}},
    {"design_count", "부대 설계 수",
     {"3B 1D [rip] 0F 8D ? ? ? ? 48 69 CB 68 01 00 00 4A 83 3C 39 00 0F 84 ? ? ? ? 66 42 83 7C 39 20 00 0F 84 ? ? ? ? 33 C0 "
      "4D 8D 4F 34",
      "44 3B 35 [rip] 0F 8D ? ? ? ? 48 8B 0D ? ? ? ? 49 69 DE 68 01 00 00 F6 05 ? ? ? ? 02 0F B7 44 0B 34",
      "41 FF C1 49 81 C2 68 01 00 00 44 3B 0D [rip]"}},
    {"world", "세계 객체",
     {"4C 8D 15 [rip] 4D 8B 84 F2 [u32] 85 DB", "48 8D 05 [rip] 48 8B 9C D8 [u32] 8B F5", "48 8D 05 [rip] B2 01 48 8B 8C D8 [u32]"}},
    {"lists", "연구 목록",
     {"48 8D 0C 40 48 8B 94 CA [u32] 48 8B CA 48 85 D2 74 31 80 79 1C 02 75 10 44 3B 59 18 74 18 48 85 C9 75 05 48 8B CA EB EA "
      "48 8B 41 10 48 8B C8 48 85 C0 75 DE EB 0D F7 41 20 00 00 00 88",
      "49 8B 94 CF [u32] 48 8B C2 48 85 D2 74 30 48 8B CA 80 79 1C 01 75 10 44 3B 49 18 74 18 48 85 C0 75 05 48 8B C2 EB E7 "
      "48 8B 40 10 48 8B C8 48 85 C0 75 DE EB 09 F7 41 24 00 00 00 88",
      "48 8D 0C 40 49 8B 94 CC [u32] 48 8B C2 48 85 D2 74 5B 48 8B DA 0F 1F 80 00 00 00 00 80 7B 1C 01 75 0F 3B 7B 18 74 18 "
      "48 85 C0 75 05 48 8B C2 EB E1 48 8B 40 10"}},
    {"recompute", "다시 셈 함수",
     {"BA FF FF FF FF 49 8B C9 E8 [rip]", "BA FF FF FF FF 49 8B CA E8 [rip]",
      "BA FF FF FF FF 49 8B CC E8 [rip] 4C 63 84 24 50 41 00 00"}},
};

const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개, 더 쓰는 값 21개, 연구 21개)
static_assert(VALUE_WANTED <= STATE_WANTED && MORE_WANTED <= STATE_WANTED && RESEARCH_WANTED <= STATE_WANTED,
              "서명을 맞추는 배열은 상태 묶음의 크기로 잡았다 — 더 큰 표를 더하면 MAX_TABLE 을 키운다");
static_assert(sizeof(MoreLayout) == MORE_WANTED * sizeof(uint32_t), "MoreLayout 의 필드는 표 MORE 의 순서대로 uint32_t 일곱이다");
static_assert(sizeof(ResearchLayout) == RESEARCH_WANTED * sizeof(uint32_t),
              "ResearchLayout 의 필드는 표 RESEARCH 의 순서대로 uint32_t 일곱이다");
static_assert(RESEARCH_NEED <= STATE_SIGS, "모두 맞아야 한다는 것은 서명의 수까지다");
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
template <class Row>
bool vote_item(const Row *table, int w, const char *what, const Sig *sigs, const SigHit *hits, uint64_t *value, char *why,
               size_t why_size)
{
    int matched = 0;
    if (sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, STATE_NEED, value, &matched))
        return true;
    if (matched >= STATE_NEED)
```

이렇게 바꾼다:

```cpp
// need: 정확히 한 번 맞아야 하는 서명의 수(연구 묶음은 셋 모두).
template <class Row>
bool vote_item(const Row *table, int w, const char *what, const Sig *sigs, const SigHit *hits, uint64_t *value, char *why,
               size_t why_size, int need = STATE_NEED)
{
    int matched = 0;
    if (sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, need, value, &matched))
        return true;
    if (matched >= need)
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
                char *why, size_t why_size)
```

이렇게 바꾼다:

```cpp
                char *why, size_t why_size, int need = STATE_NEED)
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
        if (!vote_item(table, w, what, sigs, hits, values[w], why, why_size))
```

이렇게 바꾼다:

```cpp
        if (!vote_item(table, w, what, sigs, hits, values[w], why, why_size, need))
```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
// 서명마다의 결과 칸에 이름과 글을 채운다 — 찾기 전에. 머리말조차 못 읽은 이미지에서도 서명 표를 볼 수 있다(테스트와 srkit locate 가 쓴다).
```

이것을 더한다:

```cpp
// 연구: 일곱을 모두 찾아야 한다. 저마다 서명 셋이 모두 맞아야 하고(RESEARCH_NEED), 읽어 낸 값이 서로 · 상태 묶음과 맞아야 한다.
bool search_research(const uint8_t *image, size_t size, const GameAddresses &state, ResearchLayout *out, SigRow *rows, char *why,
                     size_t why_size)
{
    Image im = {};
    im.p = image;
    im.size = size;
    if (image == nullptr || !parse(im)) {
        snprintf(why, why_size, "실행 파일의 머리말을 읽을 수 없습니다");
        return false;
    }
    uint64_t v[RESEARCH_WANTED][SIG_CAPTURES] = {};
    if (!vote_table(im, RESEARCH, RESEARCH_WANTED, "값을", rows, v, why, why_size, RESEARCH_NEED))
        return false;
    static const uint32_t BYTES[4] = {8, 4, 8, 4};      // 기술 표 · 기술 수 · 부대 설계 표 · 부대 설계 수(포인터는 8, 수는 4바이트)
    for (int w = 0; w < 4; w++) {
        const uint64_t rva = v[w][0];
        if (rva == 0 || rva >= size || !im.has(rva, BYTES[w])) {
            snprintf(why, why_size, "%s: 찾은 주소가 실행 파일 밖입니다", RESEARCH[w].label);
            return false;
        }
        if (!in_data(im, rva, BYTES[w])) {
            snprintf(why, why_size, "%s: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다", RESEARCH[w].label);
            return false;
        }
        if (rva % BYTES[w] != 0) {
            snprintf(why, why_size, "%s: 찾은 주소가 %u 의 배수가 아닙니다", RESEARCH[w].label, BYTES[w]);
            return false;
        }
        for (int u = 0; u < w; u++)
            if (overlap(rva, BYTES[w], v[u][0], BYTES[u])) {
                snprintf(why, why_size, "%s: 찾은 주소가 %s 의 자리와 겹칩니다", RESEARCH[w].label, RESEARCH[u].label);
                return false;
            }
        for (int s = 0; s < STATE_WANTED; s++) {
            const uint64_t other = state.*(STATE[s].field);
            if (other != 0 && overlap(rva, BYTES[w], other, STATE[s].bytes)) {
                snprintf(why, why_size, "%s: 찾은 주소가 %s 의 자리와 겹칩니다", RESEARCH[w].label, STATE[s].label);
                return false;
            }
        }
    }
    const uint64_t world = v[4][0], distance = v[4][1], lists = v[5][0], recompute = v[6][0];
    if (world == 0 || world >= size || !in_data(im, world, 8)) {
        snprintf(why, why_size, "%s: 찾은 주소가 쓸 수 있는 자료 구역이 아닙니다", RESEARCH[4].label);
        return false;
    }
    if (state.region_table == 0 || world + distance != state.region_table) {      // 세계 객체 안에 지역 표가 있다 — 따로 찾은 것과 맞아야 한다
        snprintf(why, why_size, "%s: 지역 표까지의 거리가 맞지 않습니다", RESEARCH[4].label);
        return false;
    }
    const uint64_t list_bytes = static_cast<uint64_t>(LIST_STEP) * REGION_SLOTS;
    if (lists == 0 || lists % 8 != 0 || !in_data(im, world + lists, list_bytes)) {
        snprintf(why, why_size, "%s: 찾은 자리가 범위 밖입니다", RESEARCH[5].label);
        return false;
    }
    if (overlap(world + lists, list_bytes, state.region_table, 8ull * REGION_SLOTS)) {
        snprintf(why, why_size, "%s: 찾은 자리가 %s 의 자리와 겹칩니다", RESEARCH[5].label, STATE[5].label);
        return false;
    }
    if (recompute == 0 || recompute >= size || function_root(im, static_cast<uint32_t>(recompute)) != recompute) {
        snprintf(why, why_size, "%s: 찾은 주소가 함수의 시작이 아닙니다", RESEARCH[6].label);
        return false;
    }
    uint32_t found[RESEARCH_WANTED];
    for (int w = 0; w < RESEARCH_WANTED; w++)
        found[w] = static_cast<uint32_t>(v[w][0]);
    memcpy(out, found, sizeof(found));
    snprintf(why, why_size, "%s", "");
    return true;
}

```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size)
```

이것을 더한다:

```cpp
bool locate_research(const uint8_t *image, size_t size, const GameAddresses &state, ResearchLayout *out, SigRow *rows, char *why,
                     size_t why_size)
{
    name_rows(RESEARCH, RESEARCH_WANTED, rows);
    __try {
        return search_research(image, size, state, out, rows, why, why_size);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        snprintf(why, why_size, "실행 파일에 읽을 수 없는 곳이 있습니다");
        return false;
    }
}

const char *locate_research_shape()
{
    static char text[640];
    snprintf(text, sizeof(text),
             "tech_size\t%x\ntech_kind\t%x\ntech_level\t%x\ntech_needs\t%x\ntech_need_count\t%x\ntech_owners\t%x\n"
             "design_size\t%x\ndesign_name\t%x\ndesign_class\t%x\ndesign_year\t%x\ndesign_open\t%x\ndesign_needs\t%x\n"
             "design_need_count\t%x\ndesign_hold_a\t%x\ndesign_hold_a_bit\t%x\ndesign_hold_b\t%x\ndesign_hold_b_bit\t%x\n"
             "design_owners\t%x\nowners_bytes\t%x\nlist_step\t%x\nnode_next\t%x\nnode_id\t%x\nnode_kind\t%x\nnode_flags\t%x\n"
             "node_gone\t%x\nnode_ended\t%x\nneed\t%x\n",
             TECH_SIZE, TECH_KIND, TECH_LEVEL, TECH_NEEDS, TECH_NEED_COUNT, TECH_OWNERS, DESIGN_SIZE, DESIGN_NAME, DESIGN_CLASS,
             DESIGN_YEAR, DESIGN_OPEN, DESIGN_NEEDS, DESIGN_NEED_COUNT, DESIGN_HOLD_A, DESIGN_HOLD_A_BIT, DESIGN_HOLD_B,
             DESIGN_HOLD_B_BIT, DESIGN_OWNERS, OWNERS_BYTES, LIST_STEP, NODE_NEXT, NODE_ID, NODE_KIND, NODE_FLAGS, NODE_GONE,
             NODE_ENDED, RESEARCH_NEED);
    return text;
}

bool locate_research_fits(const ResearchLayout &research, const ValueLayout &values, char *why, size_t why_size)
{
    const uint64_t at[4] = {research.tech_table, research.tech_count, research.design_table, research.design_count};
    static const uint32_t BYTES[4] = {8, 4, 8, 4};
    for (int w = 0; w < 4; w++)
        if (overlap(at[w], BYTES[w], values.world_pointer, 8)) {
            snprintf(why, why_size, "%s: 찾은 주소가 %s 의 자리와 겹칩니다", RESEARCH[w].label, VALUES[0].label);
            return false;
        }
    snprintf(why, why_size, "%s", "");
    return true;
}

```

`native/srtoybox/locate.h` 에서 다음 바로 앞에:

```cpp
//   옛 찾기 locate_legacy  치트 명령 처리 함수와 그 둘레의 셋. "cheat allowcheats" 문자열을 닻으로. 아직 내장 치트로 도는
```

이것을 더한다:

```cpp
//           locate_research 연구: 기술 · 부대 설계의 표, 지역별 연구 목록, 지역의 효과를 다시 셈하는 게임의 함수.
```

`native/srtoybox/locate.h` 에서 다음 바로 앞에:

```cpp
// 옛 찾기(전환 기간에만): 찾으면 nullptr 과 out 의 handler · context · options(다른 필드는 건드리지 않는다).
```

이것을 더한다:

```cpp
// 연구(3단계 3). 앞의 넷은 전역의 RVA, world 는 전역 객체의 RVA, lists 는 그 객체 안의 자리, recompute 는 함수의 RVA 다.
struct ResearchLayout {
    uint32_t tech_table;       // qword. 기술 표(레코드 TECH_SIZE 바이트 × 자리 수)의 포인터
    uint32_t tech_count;       // dword. 기술 표의 자리 수
    uint32_t design_table;     // qword. 부대 설계 표(레코드 DESIGN_SIZE 바이트 × 자리 수)의 포인터
    uint32_t design_count;     // dword. 설계 표의 자리 수
    uint32_t world;            // 세계 객체(큰 전역 구조체)의 시작. 지역 표와 연구 목록이 그 안에 있다
    uint32_t lists;            // 세계 객체 안. 지역 인덱스마다 LIST_STEP 바이트 — 그 지역의 연구 목록(맨 앞이 머리 노드의 포인터)
    uint32_t recompute;        // void f(void *세계 객체, int 지역 인덱스): 그 지역의 효과를 다시 셈한다(-1 이면 모든 지역)
};

const int RESEARCH_WANTED = 7;  // 찾을 것의 수(ResearchLayout 의 필드 순서와 같다)
const int RESEARCH_NEED = 3;    // 찾을 것마다 서명 셋이 모두 정확히 한 번 맞아야 한다 — 한 서명에만 박힌 꼴의 상수도 지켜지게

// 표와 목록의 꼴. 읽어 내지 않고 상수로 둔다 — 대신 이 상수가 박힌 명령을 서명에 넣었다(locate.cpp 의 표 RESEARCH,
// docs/11-game-internals.md). 꼴이 바뀐 빌드에서는 서명이 맞지 않아 묶음을 못 찾는다.
const uint32_t TECH_SIZE = 0x88;            // 기술 레코드. 번호가 곧 자리다
const uint32_t TECH_KIND = 0x00;            // byte. 분류(1 … 6). 0 이면 빈 자리
const uint32_t TECH_LEVEL = 0x01;           // byte. 기술 수준
const uint32_t TECH_NEEDS = 0x04;           // word × TECH_NEED_COUNT. 선행 기술의 번호(0 이면 없다)
const int TECH_NEED_COUNT = 2;
const uint32_t TECH_OWNERS = 0x50;          // qword. 보유 비트 묶음의 포인터(아무도 보유하지 않았으면 0)
const uint32_t DESIGN_SIZE = 0x168;         // 부대 설계 레코드. 번호가 곧 자리다
const uint32_t DESIGN_NAME = 0x00;          // qword. 이름 글의 포인터. 0 이면 빈 자리
const uint32_t DESIGN_CLASS = 0x08;         // byte. 병과 번호 — 표시에만 쓴다(서명에 박지 못했다)
const uint32_t DESIGN_YEAR = 0x0A;          // byte. 등장 연도 - 1900 — 〃
const uint32_t DESIGN_OPEN = 0x20;          // word. 0 이면 연구 대상이 아니다
const uint32_t DESIGN_NEEDS = 0x34;         // word × DESIGN_NEED_COUNT. 선행 기술의 번호
const int DESIGN_NEED_COUNT = 4;
const uint32_t DESIGN_HOLD_A = 0xEC;        // dword. DESIGN_HOLD_A_BIT 이 켜진 설계는 게임이 "기술을 뺄 때" 건드리지 않는다
const uint32_t DESIGN_HOLD_A_BIT = 0x1;
const uint32_t DESIGN_HOLD_B = 0xF0;        // dword. DESIGN_HOLD_B_BIT 〃
const uint32_t DESIGN_HOLD_B_BIT = 0x1000000;
const uint32_t DESIGN_OWNERS = 0xF8;        // qword. 보유 비트 묶음의 포인터
const uint32_t OWNERS_BYTES = 128;          // 보유 비트 묶음 하나 = 지역 인덱스로 찾는 1024비트
const uint32_t LIST_STEP = 24;              // 지역 하나의 연구 목록 칸
const uint32_t NODE_NEXT = 0x10;            // qword. 다음 노드
const uint32_t NODE_ID = 0x18;              // dword. 기술이나 설계의 번호
const uint32_t NODE_KIND = 0x1C;            // byte. 1 기술, 2 부대 설계
const uint32_t NODE_FLAGS = 0x20;           // dword × 2. 쪽마다의 깃발
const uint32_t NODE_GONE = 0x80000000;      // 그 쪽에서 뺐다
const uint32_t NODE_ENDED = 0x08000000;     // 내장 치트가 켜는 "끝냄"

// 새 찾기(연구): 서명의 규칙은 locate_state 와 같되 찾을 것마다 **셋이 모두** 정확히 한 번 맞고 같은 값을 내야 한다(RESEARCH_NEED).
// 일곱을 모두 찾아야 찾은 것이다(반쪽 묶음은 없다). state 는 이미 찾은 상태 묶음이다.
// 읽어 낸 값이 말이 되는지도 본다: 전역 넷은 쓸 수 있는 자료 구역 안의 제 크기의 배수 자리이고 서로 · 상태 전역과 겹치지 않는다 /
// 세계 객체 + (세계 객체의 서명이 함께 읽어 낸 거리) == 상태 묶음의 지역 표 / 연구 목록 전체가 쓸 수 있는 자료 구역 안이고 지역 표와
// 겹치지 않는다 / 다시 셈 함수는 함수 표에서 함수의 시작이다.
// 찾으면 true 와 out. 못 찾으면 false 와 why(UTF-8) — out 은 그대로다.
// rows: RESEARCH_WANTED * STATE_SIGS 칸(서명마다의 결과. 세계 객체의 둘째 값은 지역 표까지의 거리)이거나 nullptr.
bool locate_research(const uint8_t *image, size_t size, const GameAddresses &state, ResearchLayout *out, SigRow *rows, char *why,
                     size_t why_size);
// 꼴의 상수를 "이름\t값(16진수)" 줄로(테스트가 서명에 박힌 바이트와 댄다).
const char *locate_research_shape();
// 연구 묶음과 값 묶음을 함께 본다(둘 다 찾은 뒤에): 연구의 전역 넷이 세계 자료 포인터와 겹치지 않아야 한다.
// 겹치면 false 와 why(UTF-8) — 연구 묶음을 못 찾은 것으로 친다(값 묶음은 그대로 쓴다).
bool locate_research_fits(const ResearchLayout &research, const ValueLayout &values, char *why, size_t why_size);

```

`src/srkit/cli.py` 에서 다음 바로 앞에:

```python
    print("옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):")
```

이것을 더한다:

```python
    print("새 찾기 — 연구(서명. 셋이 모두 맞아야 한다 — 표와 목록의 꼴이 서명에 박혀 있다. 세계 객체는 주소 · 지역 표까지의 거리):")
    _print_sig_rows(found.research_rows)
    if found.research is None:
        print(f"찾지 못했습니다: {found.research_why}")
        print("ToyBox 의 연구 기능이 이 빌드에서 꺼집니다. uv run srkit sig-mine [--with · --back · --through-jumps] 로 서명을 다시 "
              "뽑고 꼴의 상수를 확인합니다(docs/11).")
    else:
        for name in toybox.RESEARCH_FIELDS:
            print(f"  {found.research[name]:#010x}  {toybox.RESEARCH_NAMES[name]}")
```

`src/srkit/cli.py` 에서 다음을 찾아:

```python
    if found.state is not None and found.values is not None and found.legacy is not None and not any(found.more_why):
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if found.state is not None and found.values is not None and not any(found.more_why) else 1
```

이렇게 바꾼다:

```python
    new = found.state is not None and found.values is not None and not any(found.more_why) and found.research is not None
    if new and found.legacy is not None:
        print("모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.")
    return 0 if new else 1
```

`src/srkit/toybox.py` 에서 다음 바로 뒤에:

```python
               ("관계", ["relation0", "relation1", "casus"])]
```

이것을 더한다:

```python
# 새 찾기(서명)가 채우는 연구 묶음 — native/srtoybox/locate.h 의 ResearchLayout 과 같은 순서다
RESEARCH_FIELDS = ["tech_table", "tech_count", "design_table", "design_count", "world", "lists", "recompute"]
RESEARCH_NAMES = {"tech_table": "기술 표의 포인터(qword)", "tech_count": "기술 표의 자리 수(dword)",
                  "design_table": "부대 설계 표의 포인터(qword)", "design_count": "부대 설계 표의 자리 수(dword)",
                  "world": "세계 객체(전역 구조체. 지역 표와 연구 목록이 그 안에 있다)",
                  "lists": "지역별 연구 목록의 첫 칸 — 세계 객체 안의 자리(지역 인덱스 × 24 를 더한다)",
                  "recompute": "지역의 효과를 다시 셈하는 함수(세계 객체, 지역 인덱스)"}
```

`src/srkit/toybox.py` 에서 다음 바로 뒤에:

```python
    more_rows: list[SigRow]
```

이것을 더한다:

```python
    research: dict[str, int] | None  # 새 찾기(서명): 연구 묶음. 못 찾았으면 None
    research_why: str
    research_rows: list[SigRow]      # 세계 객체의 value2 는 지역 표까지의 거리
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def output(cfg: Config) -> Path:
```

이것을 더한다:

```python
class ResearchLayout(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in RESEARCH_FIELDS]


```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
    lib.srtoybox_function_root.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint]
```

이것을 더한다:

```python
    lib.srtoybox_locate_research.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses),
                                             ctypes.POINTER(ResearchLayout), ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_locate_research_fits.argtypes = [ctypes.POINTER(ResearchLayout), ctypes.POINTER(ValueLayout), ctypes.c_char_p,
                                                  ctypes.c_int]
    lib.srtoybox_research_shape.argtypes = [ctypes.c_char_p, ctypes.c_int]
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def legacy_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str]:
```

이것을 더한다:

```python
def research_of(lib: ctypes.CDLL, image: bytes, state: dict[str, int] | None) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(연구)를 그 이미지에 돌린다: (이름 → 값 또는 None, 까닭, 서명마다의 결과).

    state 는 상태 묶음(찾았을 때)이다 — 세계 객체에서 읽어 낸 "지역 표까지의 거리"를 그 지역 표와 견준다. 없으면 못 찾은 것이 된다.
    """
    found, error, rows = ResearchLayout(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_research(image, len(image), ctypes.byref(GameAddresses(**state)) if state else None, ctypes.byref(found),
                                      error, len(error), rows, len(rows)) == 0
    return ({name: getattr(found, name) for name in RESEARCH_FIELDS} if ok else None), error.value.decode("utf-8"), _sig_rows(rows.value)


def research_fits(lib: ctypes.CDLL, research: dict[str, int], values: dict[str, int]) -> str:
    """연구 묶음과 값 묶음의 대조(연구의 전역이 세계 자료 포인터와 겹치지 않는가). 맞으면 빈 글, 아니면 까닭."""
    error = ctypes.create_string_buffer(256)
    ok = lib.srtoybox_locate_research_fits(ctypes.byref(ResearchLayout(**research)), ctypes.byref(ValueLayout(**values)), error,
                                           len(error)) == 0
    return "" if ok else error.value.decode("utf-8")


def research_shape(lib: ctypes.CDLL) -> dict[str, int]:
    """DLL 이 아는 연구의 표와 목록의 꼴(native/srtoybox/locate.h 의 상수): 이름 → 값."""
    out = ctypes.create_string_buffer(2048)
    lib.srtoybox_research_shape(out, len(out))
    return {name: int(value, 16) for name, value in (line.split("\t") for line in out.value.decode("utf-8").splitlines())}


```

`src/srkit/toybox.py` 에서 다음을 찾아:

```python
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why, more, more_why, more_rows)
```

이렇게 바꾼다:

```python
    research, research_why, research_rows = research_of(lib, image, state)
    clash = research_fits(lib, research, values) if research is not None and values is not None else ""
    if clash:
        research, research_why = None, clash  # 게임 안의 ToyBox 도 이때 연구 묶음을 버린다(game_init_from)
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why, more, more_why, more_rows,
                   research, research_why, research_rows)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_game.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `157 passed`

Run: `PYTHONIOENCODING=utf-8 uv run srkit locate | tail -12`

Expected(설치된 게임이 build 21347933 일 때):

```
  0x01829620  기술 표의 포인터(qword)
  0x01829098  기술 표의 자리 수(dword)
  0x01829610  부대 설계 표의 포인터(qword)
  0x0182909c  부대 설계 표의 자리 수(dword)
  0x017a9020  세계 객체(전역 구조체. 지역 표와 연구 목록이 그 안에 있다)
  0x003568c0  지역별 연구 목록의 첫 칸 — 세계 객체 안의 자리(지역 인덱스 × 24 를 더한다)
  0x00bdd380  지역의 효과를 다시 셈하는 함수(세계 객체, 지역 인덱스)
옛 찾기 — 아직 내장 치트로 도는 기능이 쓰는 주소(치트 문자열이 닻이다. 전환 기간에만):
  0x00522330  명령 처리 함수
  0x01764310  그 함수의 첫 인자(전역 객체)
  0x01eb556c  옵션 묶음(dword, 0x40 = 치트 허용)
모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.
```

그 위에는 `새 찾기 — 연구(서명. 셋이 모두 맞아야 한다 — …)` 아래로 서명 21줄이 모두 `한 번` 이다.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/exports.cpp src/srkit/toybox.py src/srkit/cli.py tests/test_toybox_game.py tests/toybox_fake_exe.py tests/toybox_cheat_oracle.py && git commit -q -F - <<'EOF'
feat: ToyBox 새 찾기 — 연구(기술 · 부대 설계의 표, 연구 목록, 효과를 다시 셈하는 함수)

- locate_research: 일곱을 치트와 무관한 서명 21개로 찾는다. 찾을 것마다 셋이 모두 정확히 한 번 맞고 같은 값을 내야 한다 —
  표와 목록의 꼴(레코드의 크기 · 칸의 자리 · 묶음의 크기)이 서명에 박혀 있어, 꼴이 바뀐 빌드에서는 묶음을 못 찾는다.
- 읽어 낸 값의 대조: 전역 넷은 쓸 수 있는 자료 구역의 제 크기의 배수 자리이고 서로 · 상태 전역과 겹치지 않는다 /
  세계 객체 + (서명이 함께 읽어 낸 거리) == 상태 묶음의 지역 표 / 연구 목록 전체가 자료 구역 안 / 다시 셈 함수는 함수의 시작.
- locate_research_fits: 값 묶음도 찾았으면 그 세계 자료 포인터와 겹치지 않아야 한다(겹치면 연구 묶음만 버린다).
- srkit locate 가 새 묶음을 보인다. 테스트는 치트 technology 의 본문과 대조하고, "상수 → 서명"의 표를 서명의 바이트로 본다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `470 passed`, 새 커밋.

---

### Task 3: 연구의 규칙 — 완료 · 미완료가 바꿀 항목

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Create: `native/srtoybox/research.h`, `native/srtoybox/research.cpp`
- Modify: `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`(빌드할 소스에 `research.cpp`)
- Test: `tests/test_toybox_research.py`(새로)

**Interfaces:**
- Consumes: 없다(순수 모듈 — 게임도 창도 모른다. 표는 값으로 받는다).
- Produces(`research.h`):
  - `struct TechRow { int id, kind, level; int needs[2]; bool mine, picked; int others; bool queued, housed; }` · `struct DesignRow { int id, cls, year; int needs[4]; bool open, held, mine, picked; int others; bool queued, housed; }` — `mine` 플레이어의 비트, `picked` 고른 나라의 비트, `others` 플레이어를 뺀 보유 나라의 수, `housed` 보유 묶음이 있는가, `held` 게임이 "기술을 뺄 때" 건너뛰는 설계인가.
  - `struct QueueRow { int kind, id; uint32_t flags[2]; }`, `QUEUE_TECH = 1` · `QUEUE_DESIGN = 2`.
  - `struct ResearchTables { int tech_slots, design_slots; std::vector<TechRow> techs; std::vector<DesignRow> designs; std::vector<QueueRow> queue; }`(행은 번호순, 대기열은 목록의 순서).
  - `bool queue_live(const QueueRow &node)`, `void research_mark_queued(ResearchTables *tables)`.
  - `enum class Research { Complete, Revoke }`, `struct ResearchWhat { enum Kind { Items, Level, Queue } kind; std::vector<int> techs, designs; int level; }`.
  - `struct ResearchPlan { std::vector<int> techs, designs, nodes; int asked_techs, asked_designs, skipped; }` — `nodes` 는 `tables.queue` 의 칸 번호.
  - `ResearchPlan research_plan(const ResearchTables &tables, Research action, const ResearchWhat &what, bool can_house = true)`.
  - `std::string research_summary(const ResearchPlan &plan, Research action)` — `기술 12개(선행 5개 포함) · 부대 설계 1개 · 대기열에서 2개` / 미완료는 `(딸린 것 N개 포함)`. 바꿀 것이 없으면 빈 글.
  - 내보내기(테스트): `srtoybox_research_plan(const char *tables, int action, const char *what, int can_house, char *out, int size)` — 표의 글은 줄마다 `slots <기술 자리 수> <설계 자리 수>` / `t <번호> <분류> <수준> <선행 1> <선행 2> <보유 0/1> <묶음 0/1>` / `d <번호> <연구 대상 0/1> <건너뛰는 설계 0/1> <보유 0/1> <묶음 0/1> <선행 넷>` / `q <종류> <번호> <깃발 1(16진)> <깃발 2(16진)>`, "무엇을"의 글은 `items t1 d5` · `level 120` · `queue`. 나오는 글은 일곱 줄(`techs` · `designs` · `nodes` · `asked` · `skipped` · `queued` · `text`).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

표를 글로 지어 규칙만 본다. 규칙은 게임이 스스로 쓰는 것 그대로다(설계서의 "게임이 스스로 하는 일"): 기술을 주면 보유하지 않은 선행도 거슬러 올라가며 준다 / 설계를 주면 선행 기술 넷도 준다(게임이 건너뛰는 설계는 비트만) / 기술을 빼면 그것에 기대는 보유 기술과 보유 설계도 뺀다 / 대기열의 기준(깃발의 여러 값).

<!-- 고칠 곳: test -->
새 파일 `tests/test_toybox_research.py`:

```python
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
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_research.py -q 2>&1 | tail -4`

Expected: `32 errors` — 모두 `AttributeError: function 'srtoybox_research_plan' not found`(DLL 에 아직 그 내보내기가 없다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
#include <string>
```

이것을 더한다:

```cpp
#include <sstream>
```

`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
#include "runner.h"
```

이것을 더한다:

```cpp
#include "research.h"
```

`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
}  // namespace
```

이것을 더한다:

```cpp
// 테스트가 글로 주는 연구의 표. 한 줄에 하나:
//   slots <기술 자리 수> <설계 자리 수>
//   t <번호> <분류> <수준> <선행 0> <선행 1> <보유> <묶음이 있다>
//   d <번호> <연구 대상> <게임이 건너뛰는 설계> <보유> <묶음이 있다> <선행 0> <선행 1> <선행 2> <선행 3>
//   q <종류> <번호> <깃발 0(16진수)> <깃발 1(16진수)>
ResearchTables tables_from(const std::string &text)
{
    ResearchTables t;
    std::istringstream lines(text);
    std::string line, word;
    while (std::getline(lines, line)) {
        std::istringstream in(line);
        int mine = 0, housed = 0, open = 0, held = 0;
        in >> word;
        if (word == "slots") {
            in >> t.tech_slots >> t.design_slots;
        } else if (word == "t") {
            TechRow row;
            in >> row.id >> row.kind >> row.level >> row.needs[0] >> row.needs[1] >> mine >> housed;
            row.mine = mine != 0;
            row.housed = housed != 0;
            t.techs.push_back(row);
        } else if (word == "d") {
            DesignRow row;
            in >> row.id >> open >> held >> mine >> housed >> row.needs[0] >> row.needs[1] >> row.needs[2] >> row.needs[3];
            row.open = open != 0;
            row.held = held != 0;
            row.mine = mine != 0;
            row.housed = housed != 0;
            t.designs.push_back(row);
        } else if (word == "q") {
            QueueRow row;
            in >> row.kind >> row.id >> std::hex >> row.flags[0] >> row.flags[1];
            t.queue.push_back(row);
        }
    }
    research_mark_queued(&t);
    return t;
}

// 테스트가 글로 주는 "무엇을": "items t1 t2 d5" · "level 120" · "queue".
ResearchWhat what_from(const std::string &text)
{
    ResearchWhat what;
    std::istringstream in(text);
    std::string word;
    in >> word;
    if (word == "level") {
        what.kind = ResearchWhat::Level;
        in >> what.level;
    } else if (word == "queue") {
        what.kind = ResearchWhat::Queue;
    } else {
        while (in >> word)
            if (word.size() > 1)
                (word[0] == 't' ? what.techs : what.designs).push_back(atoi(word.c_str() + 1));
    }
    return what;
}

std::string numbers(const char *name, const std::vector<int> &values)
{
    std::string text = name;
    for (int value : values)
        text += ' ' + std::to_string(value);
    return text + '\n';
}

```

`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
// 두 묶음의 대조(locate_fits). 0 이면 맞는다. -1 이면 error 에 까닭.
```

이것을 더한다:

```cpp
// 테스트: 연구의 규칙(research_plan)을 글로 준 표(tables_from)와 "무엇을"(what_from)에 돌린다. action: 0 완료, 1 미완료.
// can_house: 묶음이 없는 항목에 새 묶음을 걸 수 있는가(0 이면 그런 항목을 건너뛴다).
// 나오는 글은 일곱 줄이다: "techs 1 2 3" / "designs 5" / "nodes 0 1" / "asked <고른 기술의 수> <고른 설계의 수>" /
// "skipped <건너뛴 항목의 수>" / "queued t3 d5"(표에서 대기열에 있는 것으로 읽힌 항목) / "text <알림의 글>".
EXPORT int srtoybox_research_plan(const char *tables, int action, const char *what, int can_house, char *out, int size)
{
    const ResearchTables t = tables_from(tables != nullptr ? tables : "");
    const Research how = action == 0 ? Research::Complete : Research::Revoke;
    const ResearchPlan plan = research_plan(t, how, what_from(what != nullptr ? what : ""), can_house != 0);
    std::string queued = "queued";
    for (const TechRow &row : t.techs)
        if (row.queued)
            queued += " t" + std::to_string(row.id);
    for (const DesignRow &row : t.designs)
        if (row.queued)
            queued += " d" + std::to_string(row.id);
    return put(numbers("techs", plan.techs) + numbers("designs", plan.designs) + numbers("nodes", plan.nodes)
               + "asked " + std::to_string(plan.asked_techs) + ' ' + std::to_string(plan.asked_designs) + "\nskipped "
               + std::to_string(plan.skipped) + '\n' + queued + "\ntext " + research_summary(plan, how), out, size);
}

```

새 파일 `native/srtoybox/research.cpp`:

```cpp
#include "research.h"

#include <algorithm>

#include "locate.h"

namespace {

// 번호 → 행의 칸(없으면 -1).
template <class Row>
std::vector<int> index_of(const std::vector<Row> &rows, int slots)
{
    std::vector<int> at(static_cast<size_t>(std::max(slots, 0)), -1);
    for (size_t i = 0; i < rows.size(); i++)
        if (rows[i].id > 0 && rows[i].id < slots)
            at[static_cast<size_t>(rows[i].id)] = static_cast<int>(i);
    return at;
}

int find(const std::vector<int> &at, int id)
{
    return id > 0 && id < static_cast<int>(at.size()) ? at[static_cast<size_t>(id)] : -1;
}

ResearchPlan complete(const ResearchTables &t, const ResearchWhat &what, bool can_house)
{
    const std::vector<int> tech_at = index_of(t.techs, t.tech_slots), design_at = index_of(t.designs, t.design_slots);
    std::vector<char> tech_seen(t.techs.size()), tech_asked(t.techs.size()), design_seen(t.designs.size());
    std::vector<char> tech_left(t.techs.size()), design_left(t.designs.size());   // 묶음이 없어 건너뛴 것
    std::vector<int> stack;                     // 볼 기술의 칸
    ResearchPlan plan;
    const auto pull_tech = [&](int id) {        // 딸려 오는 선행
        const int i = find(tech_at, id);
        if (i >= 0 && !tech_seen[static_cast<size_t>(i)]) {
            tech_seen[static_cast<size_t>(i)] = 1;
            stack.push_back(i);
        }
    };
    const auto ask_tech = [&](int id) {         // 고른 것
        const int i = find(tech_at, id);
        if (i >= 0)
            tech_asked[static_cast<size_t>(i)] = 1;
        pull_tech(id);
    };
    const auto ask_design = [&](int id) {
        const int i = find(design_at, id);
        if (i < 0 || design_seen[static_cast<size_t>(i)])
            return;
        design_seen[static_cast<size_t>(i)] = 1;
        const DesignRow &d = t.designs[static_cast<size_t>(i)];
        if (d.mine)
            return;
        if (!d.housed && !can_house) {
            design_left[static_cast<size_t>(i)] = 1;
            plan.skipped++;
            return;
        }
        plan.designs.push_back(d.id);
        plan.asked_designs++;
        if (d.open && !d.held)                  // 게임이 "보유한 설계의 선행 기술을 준다"에서 건너뛰는 설계는 설계의 비트만
            for (int need : d.needs)
                pull_tech(need);
    };
    switch (what.kind) {
    case ResearchWhat::Items:
        for (int id : what.techs)
            ask_tech(id);
        for (int id : what.designs)
            ask_design(id);
        break;
    case ResearchWhat::Level:
        for (const TechRow &row : t.techs)
            if (row.level <= what.level)
                ask_tech(row.id);
        break;
    case ResearchWhat::Queue:
        for (const QueueRow &node : t.queue)
            if (queue_live(node)) {
                if (node.kind == QUEUE_TECH)
                    ask_tech(node.id);
                else if (node.kind == QUEUE_DESIGN)
                    ask_design(node.id);
            }
        break;
    }
    while (!stack.empty()) {
        const size_t i = static_cast<size_t>(stack.back());
        stack.pop_back();
        const TechRow &row = t.techs[i];
        if (row.mine)
            continue;                           // 이미 보유했다 — 그 선행은 보지 않는다(게임과 같다)
        if (!row.housed && !can_house) {
            tech_left[i] = 1;
            plan.skipped++;
            continue;
        }
        plan.techs.push_back(row.id);
        plan.asked_techs += tech_asked[i];
        for (int need : row.needs)
            pull_tech(need);
    }
    for (size_t n = 0; n < t.queue.size(); n++) {
        const QueueRow &node = t.queue[n];
        if (!queue_live(node))
            continue;
        const int i = node.kind == QUEUE_TECH ? find(tech_at, node.id) : node.kind == QUEUE_DESIGN ? find(design_at, node.id) : -1;
        if (i >= 0 && (node.kind == QUEUE_TECH ? tech_seen : design_seen)[static_cast<size_t>(i)]
            && !(node.kind == QUEUE_TECH ? tech_left : design_left)[static_cast<size_t>(i)])
            plan.nodes.push_back(static_cast<int>(n));
    }
    return plan;
}

ResearchPlan revoke(const ResearchTables &t, const ResearchWhat &what)
{
    ResearchPlan plan;
    if (what.kind != ResearchWhat::Items)
        return plan;
    const std::vector<int> tech_at = index_of(t.techs, t.tech_slots), design_at = index_of(t.designs, t.design_slots);
    std::vector<char> tech_gone(t.techs.size()), design_gone(t.designs.size());
    std::vector<std::vector<int>> needed_by(t.techs.size());   // 기술의 칸 → 그것을 선행으로 갖는 기술의 칸들
    for (size_t i = 0; i < t.techs.size(); i++)
        for (int need : t.techs[i].needs) {
            const int j = find(tech_at, need);
            if (j >= 0 && static_cast<size_t>(j) != i)
                needed_by[static_cast<size_t>(j)].push_back(static_cast<int>(i));
        }
    std::vector<int> stack;
    for (int id : what.techs) {
        const int i = find(tech_at, id);
        if (i >= 0 && t.techs[static_cast<size_t>(i)].mine && !tech_gone[static_cast<size_t>(i)]) {
            tech_gone[static_cast<size_t>(i)] = 1;
            plan.asked_techs++;
            stack.push_back(i);
        }
    }
    while (!stack.empty()) {
        const size_t i = static_cast<size_t>(stack.back());
        stack.pop_back();
        plan.techs.push_back(t.techs[i].id);
        for (int j : needed_by[i])
            if (t.techs[static_cast<size_t>(j)].mine && !tech_gone[static_cast<size_t>(j)]) {
                tech_gone[static_cast<size_t>(j)] = 1;
                stack.push_back(j);
            }
    }
    for (int id : what.designs) {
        const int i = find(design_at, id);
        if (i >= 0 && t.designs[static_cast<size_t>(i)].mine && !design_gone[static_cast<size_t>(i)]) {
            design_gone[static_cast<size_t>(i)] = 1;
            plan.asked_designs++;
            plan.designs.push_back(id);
        }
    }
    for (size_t i = 0; i < t.designs.size(); i++) {
        const DesignRow &d = t.designs[i];
        if (!d.mine || design_gone[i] || d.held || !d.open)
            continue;
        for (int need : d.needs) {
            const int j = find(tech_at, need);
            if (j >= 0 && tech_gone[static_cast<size_t>(j)]) {
                design_gone[i] = 1;
                plan.designs.push_back(d.id);
                break;
            }
        }
    }
    return plan;
}

void add(std::string *text, const std::string &part)
{
    if (!text->empty())
        *text += " · ";
    *text += part;
}

}  // namespace

bool queue_live(const QueueRow &node)
{
    for (uint32_t flags : node.flags)
        if ((flags & 3) != 0 && (flags & NODE_GONE) == 0)
            return true;
    return false;
}

void research_mark_queued(ResearchTables *tables)
{
    const std::vector<int> tech_at = index_of(tables->techs, tables->tech_slots);
    const std::vector<int> design_at = index_of(tables->designs, tables->design_slots);
    for (TechRow &row : tables->techs)
        row.queued = false;
    for (DesignRow &row : tables->designs)
        row.queued = false;
    for (const QueueRow &node : tables->queue) {
        if (!queue_live(node))
            continue;
        if (node.kind == QUEUE_TECH && find(tech_at, node.id) >= 0)
            tables->techs[static_cast<size_t>(find(tech_at, node.id))].queued = true;
        else if (node.kind == QUEUE_DESIGN && find(design_at, node.id) >= 0)
            tables->designs[static_cast<size_t>(find(design_at, node.id))].queued = true;
    }
}

ResearchPlan research_plan(const ResearchTables &tables, Research action, const ResearchWhat &what, bool can_house)
{
    ResearchPlan plan = action == Research::Complete ? complete(tables, what, can_house) : revoke(tables, what);
    std::sort(plan.techs.begin(), plan.techs.end());
    std::sort(plan.designs.begin(), plan.designs.end());
    return plan;
}

std::string research_summary(const ResearchPlan &plan, Research action)
{
    const int techs = static_cast<int>(plan.techs.size()), designs = static_cast<int>(plan.designs.size());
    const char *const extra = action == Research::Complete ? "선행" : "딸린 것";
    std::string text;
    if (techs > 0)
        add(&text, "기술 " + std::to_string(techs) + "개"
            + (techs > plan.asked_techs ? "(" + std::string(extra) + " " + std::to_string(techs - plan.asked_techs) + "개 포함)" : ""));
    if (designs > 0)
        add(&text, "부대 설계 " + std::to_string(designs) + "개"
            + (designs > plan.asked_designs ? "(" + std::string(extra) + " " + std::to_string(designs - plan.asked_designs) + "개 포함)" : ""));
    if (!plan.nodes.empty())
        add(&text, "대기열에서 " + std::to_string(plan.nodes.size()) + "개");
    return text;
}
```

새 파일 `native/srtoybox/research.h`:

```cpp
// 연구의 규칙: 표의 스냅숏에서 "완료 · 미완료가 바꿀 항목"을 셈한다. 게임도 창도 메모리도 모르는 순수 함수다.
// 게임이 스스로 쓰는 규칙 그대로다(docs/11-game-internals.md): 기술을 주면 선행 기술도 주고, 빼면 그 기술에 기대는 기술 · 부대 설계도 뺀다.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct TechRow {
    int id = 0;                 // 번호(표의 자리)
    int kind = 0;               // 분류(1 … 6)
    int level = 0;              // 기술 수준
    int needs[2] = {};          // 선행 기술의 번호(0 이면 없다)
    bool mine = false;          // 플레이어가 보유했다
    bool picked = false;        // 고른 나라가 보유했다(고른 나라가 없으면 false)
    int others = 0;             // 보유한 다른 나라의 수(플레이어는 세지 않는다)
    bool queued = false;        // 플레이어의 연구 대기열에 있다
    bool housed = false;        // 보유 비트 묶음이 있다(없으면 아무도 보유한 적이 없다)
};

struct DesignRow {
    int id = 0;
    int cls = 0;                // 병과 번호
    int year = 0;               // 등장 연도 - 1900
    int needs[4] = {};          // 선행 기술의 번호
    bool open = false;          // 연구 대상이다
    bool held = false;          // 게임이 "기술을 뺄 때" 건드리지 않는 설계(깃발)
    bool mine = false, picked = false;
    int others = 0;
    bool queued = false, housed = false;
};

const int QUEUE_TECH = 1, QUEUE_DESIGN = 2;   // 노드의 종류

struct QueueRow {
    int kind = 0;
    int id = 0;
    uint32_t flags[2] = {};     // 쪽마다의 깃발
};

struct ResearchTables {
    int tech_slots = 0, design_slots = 0;   // 표의 자리 수(번호는 이것보다 작다)
    std::vector<TechRow> techs;             // 쓰는 기술, 번호순
    std::vector<DesignRow> designs;         // 쓰는 부대 설계, 번호순
    std::vector<QueueRow> queue;            // 플레이어의 연구 목록의 노드, 목록의 순서
};

// 그 노드가 대기열에 있는가(게임의 기준): 깃발 둘 가운데 하나라도 아래 두 비트가 0 이 아니고 "뺐다"(NODE_GONE)가 꺼져 있다.
bool queue_live(const QueueRow &node);
// 행마다의 queued 를 노드에서 채운다(스냅숏을 뜬 쪽이 부른다).
void research_mark_queued(ResearchTables *tables);

enum class Research { Complete, Revoke };

struct ResearchWhat {
    enum Kind { Items, Level, Queue } kind = Items;
    std::vector<int> techs, designs;        // Items: 번호들
    int level = 0;                          // Level: 기술 수준이 이것 이하인 기술 모두
};

struct ResearchPlan {
    std::vector<int> techs, designs;        // 비트를 바꿀 항목의 번호(오름차순). 완료면 켜고 미완료면 끈다
    std::vector<int> nodes;                 // 대기열에서 뺄 노드(tables.queue 의 칸 번호, 오름차순). 완료에서만
    int asked_techs = 0, asked_designs = 0; // 그 가운데 고른 것. 나머지는 딸려 온 것(완료: 선행 기술, 미완료: 그것에 기대던 것)
    int skipped = 0;                        // 보유 비트 묶음이 없어 건너뛴 항목의 수(can_house 가 false 일 때만)
};

// 완료(Complete)
//   기술      그 기술 + 선행 둘 가운데 보유하지 않은 것(거슬러 올라가며 전부). 이미 보유한 선행의 선행은 보지 않는다.
//             선행의 번호가 0 이거나 자리 수 이상이거나 빈 자리면 건너뛴다.
//   부대 설계 그 설계 + 선행 기술 넷을 위 규칙으로. 게임이 건너뛰는 설계(held 이거나 open 이 아닌 것)는 설계의 비트만.
//   대기열    이 요청이 닿은 항목(고른 것과 딸려 온 선행 — 이미 보유한 것도) 가운데 대기열에 있는 것의 노드를 뺀다.
//   무엇을    Items: 그 번호들 / Level: 수준이 level 이하인 기술 모두 / Queue: 대기열에 있는 기술 · 부대 설계 모두.
// 미완료(Revoke) — Items 만
//   기술      그 기술(보유한 것만) + 그것을 선행으로 갖는 보유 기술(따라 내려가며 전부)
//             + 그 기술들 가운데 하나를 선행 넷에 갖는 보유 설계(held 이거나 open 이 아닌 것은 뺀다)
//   부대 설계 그 설계만(보유한 것만)
// 이미 그 상태인 항목은 넣지 않는다.
// can_house: 보유 비트 묶음이 없는 항목(아무도 보유한 적이 없다)에 새 묶음을 걸 수 있는가. 없으면 완료에서 그런 항목을 건너뛰고
// skipped 에 센다 — 그 선행은 따라가지 않고, 대기열에 있어도 빼지 않는다.
ResearchPlan research_plan(const ResearchTables &tables, Research action, const ResearchWhat &what, bool can_house = true);

// 알림과 로그의 글: "기술 12개(선행 5개 포함) · 부대 설계 1개 · 대기열에서 2개" /
// 미완료는 "기술 3개(딸린 것 2개 포함) · 부대 설계 7개(딸린 것 7개 포함)". 바꿀 것이 없으면 빈 글.
std::string research_summary(const ResearchPlan &plan, Research action);
```

`src/srkit/toybox.py` 에서 다음을 찾아:

```python
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "values.cpp", "game.cpp", "keeper.cpp", "regions.cpp", "products.cpp",
```

이렇게 바꾼다:

```python
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "values.cpp", "research.cpp", "game.cpp", "keeper.cpp", "regions.cpp", "products.cpp",
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_research.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `32 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/research.h native/srtoybox/research.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_research.py && git commit -q -F - <<'EOF'
feat: ToyBox 연구의 규칙 — 완료 · 미완료가 바꿀 항목(선행 기술, 딸린 것, 대기열)

- research: 표의 스냅숏과 "무엇을 어떻게"를 받아 바꿀 항목을 내는 순수 함수. 게임이 연구를 끝내고 뺄 때의 규칙 그대로다 —
  완료는 보유하지 않은 선행 기술을 거슬러 올라가며 데려오고(설계는 선행 넷), 미완료는 그것에 기대는 보유 기술 · 설계를 데려온다.
- "무엇을"은 셋: 고른 번호들 / 기술 수준 N 이하 / 대기열에 있는 것 모두(기술과 부대 설계).
- 묶음을 만들 수 없으면(can_house) 묶음이 없는 항목을 빼고 그 수를 센다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `502 passed`, 새 커밋.

---

### Task 4: 연구의 스냅숏 · 쓰기 · 다시 셈

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Modify: `native/srtoybox/game.h`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_research.py`, `tests/toybox_fake_game.py`, `tests/test_toybox_values.py`(한 줄)

**Interfaces:**
- Consumes: Task 2 의 `ResearchLayout` · 꼴의 상수 · `locate_research` · `locate_research_fits`, Task 3 의 `ResearchTables` · `research_plan` · `research_mark_queued` · `ResearchPlan` · `ResearchWhat` · `Research`. `game.cpp` 안쪽의 `read_player` · `peek` · `peek_at` · `find_region` · `writable` · `poke` · `off_text` · `reading_wanted`, 전역 `g_write_failed`.
- Produces:
  - `Wrote::Unreadable`(7) · `Wrote::Crashed`(8) — 끝에 더한다(앞의 값은 그대로다).
  - `struct ResearchDone { ResearchPlan plan; int housed, skipped, cells, written; bool recomputed; unsigned long code; std::string why; }`.
  - `typedef void (*Recompute)(void *world, int index);`
  - 순수 함수: `bool read_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, int picked, ResearchTables *out, std::string *why)`, `Wrote write_research(base, at, research, Recompute recompute, Research action, const ResearchWhat &what, ResearchDone *done)`.
  - 프로세스의 게임: `std::string game_research_off()`, `bool game_research(int picked, ResearchTables *out, std::string *why)`, `Wrote game_write_research(Research action, const ResearchWhat &what, ResearchDone *done)`(실패하면 값 쓰기 전체를 끄고 로그에 적는다. `Crashed` 는 부른 쪽이 처리한다), `void game_set_research_for_test(const ResearchLayout *layout, void *recompute)`.
  - 시작할 때의 로그: `연구를 씁니다 (기술 표 +0x… · 부대 설계 표 +0x… · 연구 목록 +0x… · 다시 셈 +0x…)` / `연구를 쓰지 않습니다 (SRTOYBOX_WRITE=0. …)` / `연구를 쓸 수 없습니다 (<까닭>)`.
  - 내보내기(테스트): `srtoybox_research_read(base, at, layout, picked, out, size)`(1 과 표의 글 / 0 과 까닭), `srtoybox_research_write(base, at, layout, void *recompute, action, what, out, size)`(돌려주는 값은 `Wrote`, 글은 `techs` · `designs` · `nodes` · `asked` · `skipped` · `housed` · `cells` · `written` · `recomputed` · `code` · `why` · `text` 줄), `srtoybox_test_research(layout, recompute)`, `srtoybox_research_off(out, size)`, `srtoybox_game_flags` 의 새 비트 64.
  - 테스트 도우미(`toybox_fake_game`): `RESEARCH` · `TECH_SIZE` · `DESIGN_SIZE` · `OWNERS_BYTES` · `LIST_STEP` · `NODE_SIZE` · `TECH` · `DESIGN` · `GONE` · `ENDED`, `kernel32`(힙 함수의 인자 형), `locked_page(protection)`, `class Lab`(`tech` · `design` · `block` · `house` · `own` · `owners` · `held` · `queue` · `flags` · `everything` · `world` · `layout` · `nodes`), `standard_lab(fake, germany=176, poland=141, denmark=150) -> Lab`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

가짜 게임에 연구를 붙인다(`Lab` — 표는 따로 잡은 버퍼, 보유 묶음은 게임처럼 프로세스 힙의 128바이트). 테스트들이 함께 쓰는 판은 `standard_lab` 이다: 기술 1 ~ 7, 부대 설계 10 ~ 14, 독일의 대기열에 기술 2 와 부대 설계 11. 읽기 · 쓰기의 테스트는 "그 칸만 바뀐다"를 바이트로 본다(`Lab.everything()` 의 앞뒤). 값 테스트 한 곳은 시작 로그에 연구의 줄이 생기는 것에 맞춘다.

<!-- 고칠 곳: test -->
`tests/test_toybox_research.py` 에서 다음을 찾아:

```python
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
```

이렇게 바꾼다:

```python
"""ToyBox 의 연구: 규칙(research) · 게임의 표 읽기와 쓰기(game). 게임은 띄우지 않는다.

규칙은 게임이 스스로 쓰는 것 그대로다(docs/11-game-internals.md): 기술을 주면 선행 기술도 주고, 빼면 그 기술에 기대는 기술 · 설계도 뺀다.
앞쪽은 표를 글로 지어 규칙만 보고, 뒤쪽은 가짜 게임 메모리(toybox_fake_game.Lab)에서 표를 읽고 비트를 쓰는 것을 본다.
"""
import ctypes
import struct

import pytest

import toybox_fake_exe
from toybox_fake_game import DESIGN, DESIGN_SIZE, ENDED, GONE, INDEX, MULTIPLAYER, OWNERS_BYTES, RESEARCH, TECH, TECH_SIZE, FakeGame, \
    Lab, kernel32, locked_page, standard_lab
from srkit import toybox

COMPLETE, REVOKE = 0, 1
DONE, NOT_IN_GAME, NOT_USED, BAD_VALUE, FAILED, OFF, NO_TARGET, UNREADABLE, CRASHED = range(9)   # native/srtoybox/game.h 의 Wrote
GERMANY, POLAND, DENMARK = 176, 141, 150                                                         # 지역 인덱스
RECOMPUTE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)                                # "다시 셈" 자리에 두는 함수의 꼴
```

`tests/test_toybox_research.py` 에서 다음을 찾아:

```python
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_research_plan.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
```

이렇게 바꾼다:

```python
    lib = toybox.library(cfg)
    pointer = ctypes.POINTER
    lib.srtoybox_research_plan.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_research_read.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ResearchLayout), ctypes.c_int,
                                           ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_research_write.argtypes = [ctypes.c_void_p, pointer(toybox.GameAddresses), pointer(toybox.ResearchLayout), ctypes.c_void_p,
                                            ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
```

`tests/test_toybox_research.py` 에서 다음 바로 뒤에:

```python
    assert len(got["techs"]) == 2999 and len(got["designs"]) == len(range(1, 22000, 7))
```

이것을 더한다:

```python


# ---------------------------------------------------------------------------------------------------------------------
# 게임의 메모리에서: 표 읽기(read_research)와 쓰기(write_research)

def lab() -> tuple[FakeGame, Lab]:
    """독일(인덱스 176, 번호 1499)로 진행 중인 게임과 그 연구(toybox_fake_game.standard_lab — 기술 1 ~ 7, 부대 설계 10 ~ 14, 독일의 대기열).
    폴란드(141, 1106) · 덴마크(150, 1201)가 함께 있다."""
    fake = FakeGame()
    fake.region(POLAND, 1106, alive=3)
    fake.region(DENMARK, 1201, alive=3)
    fake.region(GERMANY, 1499)
    fake.play(GERMANY)
    return fake, standard_lab(fake, GERMANY, POLAND, DENMARK)


def read(lib, fake: FakeGame, lab: Lab, picked: int = 0):
    """표를 읽는다. 읽었으면 {slots, techs: {번호: 행}, designs: {번호: 행}, queue: [(종류, 번호, 깃발 0, 깃발 1)]}, 못 읽었으면 까닭의 글."""
    out = ctypes.create_string_buffer(1 << 16)
    ok = lib.srtoybox_research_read(fake.base, ctypes.byref(fake.at), ctypes.byref(lab.layout), picked, out, len(out))
    assert ok >= 0
    if ok == 0:
        return out.value.decode("utf-8")
    table = {"techs": {}, "designs": {}, "queue": []}
    for line in out.value.decode("utf-8").splitlines():
        word, *rest = line.split()
        if word == "slots":
            table["slots"] = tuple(int(n) for n in rest)
        elif word == "t":
            number, kind, level, first, second, mine, chosen, others, queued, housed = (int(n) for n in rest)
            table["techs"][number] = dict(kind=kind, level=level, needs=(first, second), mine=bool(mine), picked=bool(chosen),
                                          others=others, queued=bool(queued), housed=bool(housed))
        elif word == "d":
            number, cls, year, is_open, held, mine, chosen, others, queued, housed, *needs = (int(n) for n in rest)
            table["designs"][number] = dict(cls=cls, year=year, open=bool(is_open), held=bool(held), mine=bool(mine), picked=bool(chosen),
                                            others=others, queued=bool(queued), housed=bool(housed), needs=tuple(needs))
        else:
            table["queue"].append((int(rest[0]), int(rest[1]), int(rest[2], 16), int(rest[3], 16)))
    return table


def write(lib, fake: FakeGame, lab: Lab, what: str, action: int = COMPLETE, recompute=None) -> tuple[int, dict]:
    """연구를 바꾼다: (Wrote, 결과). 결과의 calls 는 "다시 셈" 자리의 함수가 불린 인자들 — [(세계 객체의 주소, 지역 인덱스)].
    recompute 를 주면 그 주소를 함수로 넘긴다(잘못된 주소로 예외를 낼 때)."""
    out = ctypes.create_string_buffer(1 << 16)
    calls: list[tuple[int, int]] = []
    hook = RECOMPUTE(lambda world, index: calls.append((world, index)))
    wrote = lib.srtoybox_research_write(fake.base, ctypes.byref(fake.at), ctypes.byref(lab.layout),
                                        recompute if recompute is not None else ctypes.cast(hook, ctypes.c_void_p), action,
                                        what.encode(), out, len(out))
    lines = dict(line.split(" ", 1) if " " in line else (line, "") for line in out.value.decode("utf-8").split("\n"))
    done = {name: [int(n) for n in lines[name].split()] for name in ("techs", "designs", "nodes")}
    done.update({name: int(lines[name]) for name in ("skipped", "housed", "cells", "written", "recomputed")})
    done.update(asked=tuple(int(n) for n in lines["asked"].split()), code=int(lines["code"], 16), why=lines["why"], text=lines["text"],
                calls=calls)
    return wrote, done


def differing(before: bytes, after: bytes) -> set[int]:
    return {i for i in range(len(before)) if before[i] != after[i]}


def test_the_tables_are_read_from_the_game(lib):
    fake, lab_ = lab()
    table = read(lib, fake, lab_)
    assert table["slots"] == (64, 64)
    assert sorted(table["techs"]) == [1, 2, 3, 4, 6, 7] and sorted(table["designs"]) == [10, 11, 12, 13, 14]     # 빈 자리는 없다
    assert table["techs"][1] == dict(kind=1, level=10, needs=(0, 0), mine=True, picked=False, others=1, queued=False, housed=True)
    assert table["techs"][2] == dict(kind=1, level=20, needs=(1, 0), mine=False, picked=False, others=1, queued=True, housed=True)
    assert table["techs"][3] == dict(kind=1, level=30, needs=(2, 0), mine=False, picked=False, others=0, queued=False, housed=False)
    assert table["designs"][11] == dict(cls=2, year=95, open=True, held=False, mine=False, picked=False, others=1, queued=True,
                                        housed=True, needs=(3, 0, 0, 0))
    assert table["designs"][12]["housed"] is False and table["designs"][14]["held"] is True and table["designs"][13]["others"] == 1
    assert table["queue"] == [(DESIGN, 11, 1, 0x60000001), (TECH, 2, 1, 0)]


def test_the_picked_country_is_marked(lib):
    """고른 나라의 보유를 행마다 적는다 — "타국의 연구"를 목록에 보이는 데 쓴다. 이번 판에 없는 번호와 플레이어 자신은 아무것도 고르지 않은 것과 같다."""
    fake, lab_ = lab()

    def picked(number: int) -> tuple[list[int], list[int]]:
        table = read(lib, fake, lab_, number)
        return ([n for n, row in table["techs"].items() if row["picked"]], [n for n, row in table["designs"].items() if row["picked"]])

    assert picked(1106) == ([1, 2], [11, 13])            # 폴란드
    assert picked(1201) == ([4, 7], [])                  # 덴마크
    assert picked(1499) == ([], []) and picked(9999) == ([], []) and picked(0) == ([], [])


def broken(flaw: str) -> tuple[FakeGame, Lab]:
    """lab() 에 흠 하나를 낸 것."""
    fake, lab_ = lab()
    tail = lab_.nodes[0]                                  # 먼저 건 노드가 목록의 끝이다
    if flaw == "menu":
        fake.menu()
    elif flaw == "multiplayer":
        fake.poke(MULTIPLAYER, "<B", 1)
    elif flaw == "wrong-index":
        fake.poke(INDEX, "<i", POLAND)                        # 전역의 인덱스가 플레이어의 객체가 아는 인덱스와 다르다
    elif flaw == "no-table":
        fake.poke(RESEARCH["tech_table"], "<Q", 0)
    elif flaw == "one-slot":
        fake.poke(RESEARCH["tech_count"], "<i", 1)
    elif flaw == "too-many":
        fake.poke(RESEARCH["design_count"], "<i", 70000)
    elif flaw == "techs-gone":
        fake.poke(RESEARCH["tech_table"], "<Q", 0x10)     # 읽을 수 없는 주소
    elif flaw == "designs-gone":
        fake.poke(RESEARCH["design_table"], "<Q", 0x10)
    elif flaw == "owners-gone":
        lab_.house(TECH, 3, block=0x10)
    elif flaw == "node-gone":
        ctypes.memmove(tail + 0x10, struct.pack("<Q", 0x10), 8)
    elif flaw == "loop":
        ctypes.memmove(tail + 0x10, struct.pack("<Q", lab_.nodes[1]), 8)     # 끝이 머리를 가리킨다
    return fake, lab_


@pytest.mark.parametrize("flaw, why, wrote", [
    ("menu", "게임이 진행 중이 아닙니다", NOT_IN_GAME),
    ("multiplayer", "멀티플레이에서는 연구를 읽지 않습니다", NOT_IN_GAME),
    ("wrong-index", "게임이 진행 중이 아닙니다", NOT_IN_GAME),
    ("no-table", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("one-slot", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("too-many", "표가 없거나 자리 수가 범위 밖입니다", UNREADABLE),
    ("techs-gone", "기술 표를 읽을 수 없습니다", UNREADABLE),
    ("designs-gone", "부대 설계 표를 읽을 수 없습니다", UNREADABLE),
    ("owners-gone", "기술 3 의 보유 묶음을 읽을 수 없습니다", UNREADABLE),
    ("node-gone", "연구 목록의 노드를 읽을 수 없습니다", UNREADABLE),
    ("loop", "연구 목록이 끝나지 않습니다", UNREADABLE),
])
def test_a_game_that_does_not_add_up_is_neither_read_nor_written(lib, flaw, why, wrote):
    """표의 꼴이 다른 게임일 수 있다 — 읽지 않고, 한 칸도 쓰지 않고, 게임의 함수도 부르지 않는다."""
    fake, lab_ = broken(flaw)
    assert read(lib, fake, lab_) == why
    before = lab_.everything()
    result, done = write(lib, fake, lab_, "items t3 d11")
    assert result == wrote and done["written"] == 0 and done["calls"] == []
    assert lab_.everything() == before


def test_completing_a_tech_sets_the_players_bit_on_it_and_on_what_it_needs(lib):
    """기술 3 을 완료로: 3 과 그 선행 2 의 독일 비트가 켜진다(1 은 이미 보유했다). 3 에는 묶음이 없었다 — 게임처럼 프로세스 힙에서
    128바이트를 받아 건다. 대기열에 있던 2 는 대기열에서 빠진다. 끝에 독일의 효과를 한 번 다시 셈하게 한다."""
    fake, lab_ = lab()
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t3")
    assert wrote == DONE and done["techs"] == [2, 3] and done["designs"] == [] and done["asked"] == (1, 0)
    assert done["nodes"] == [1] and done["housed"] == 1 and done["skipped"] == 0
    assert done["cells"] == done["written"] == 5                                     # 비트 둘, 새 묶음의 포인터 하나, 노드의 깃발 둘
    assert done["recomputed"] == 1 and done["calls"] == [(lab_.world, GERMANY)]      # 플레이어 지역만. -1(모든 지역)이 아니다
    assert done["text"] == "기술 2개(선행 1개 포함) · 대기열에서 1개"
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY} and lab_.owners(TECH, 3) == {GERMANY} and lab_.owners(TECH, 1) == {GERMANY, POLAND}
    heap, block = kernel32.GetProcessHeap(), lab_.block(TECH, 3)
    assert kernel32.HeapValidate(heap, 0, block) and kernel32.HeapSize(heap, 0, block) == OWNERS_BYTES
    assert lab_.flags(lab_.nodes[0]) == (GONE | 1, GONE) and lab_.flags(lab_.nodes[1]) == (1, 0x60000001)   # 기술 2 의 노드만

    after = lab_.everything()
    assert set(after) - set(before) == {"t3"}                                         # 새 묶음 하나
    same = set(before) - {"techs", "t2", "n0"}
    assert all(after[name] == before[name] for name in same)                          # 전역 · 부대 설계 표 · 다른 묶음 · 다른 노드는 그대로다
    cell = 3 * TECH_SIZE + 0x50
    assert differing(before["techs"], after["techs"]) <= set(range(cell, cell + 8))   # 기술 표에서는 3 의 묶음 칸만(연구 기간은 그대로다)
    assert differing(before["t2"], after["t2"]) == {GERMANY // 8}
    assert differing(before["n0"], after["n0"]) == {0x23, 0x27}                       # 깃발 둘의 맨 위 비트


def test_only_the_players_bit_in_its_byte_changes(lib):
    """같은 바이트에 든 다른 나라 일곱의 비트는 읽은 그대로 쓴다."""
    fake, lab_ = lab()
    for index in (177, 183, 168, 175):                    # 176 과 같은 바이트(176 … 183), 그 앞 바이트
        lab_.own(TECH, 2, index)
    assert write(lib, fake, lab_, "items t2")[0] == DONE
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY, 177, 183, 168, 175}
    assert write(lib, fake, lab_, "items t2", REVOKE)[0] == DONE
    assert lab_.owners(TECH, 2) == {POLAND, 177, 183, 168, 175}


def test_completing_a_design_sets_its_bit_and_brings_the_techs_it_needs(lib):
    """부대 설계 11(선행 3 ← 2 ← 1)을 완료로: 설계의 비트와 기술 2 · 3. 내장 치트의 연구 단추들은 부대 설계를 건드리지 않았다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items d11")
    assert wrote == DONE and done["designs"] == [11] and done["techs"] == [2, 3] and done["asked"] == (0, 1) and done["nodes"] == [0, 1]
    assert done["text"] == "기술 2개(선행 2개 포함) · 부대 설계 1개 · 대기열에서 2개"
    assert lab_.owners(DESIGN, 11) == {POLAND, GERMANY} and lab_.owners(TECH, 3) == {GERMANY} and len(done["calls"]) == 1
    assert lab_.flags(lab_.nodes[1]) == (GONE | 1, GONE | 0x60000001)                 # 다른 비트는 그대로 두고 "뺐다"만 켠다


def test_a_design_alone_does_not_ask_the_game_to_recompute(lib):
    """부대 설계 12 는 선행(4)을 이미 보유했다 — 설계의 비트만 켠다. 효과의 표는 기술에서만 나온다: 다시 셈을 부르지 않는다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items d12")
    assert wrote == DONE and done["designs"] == [12] and done["techs"] == [] and done["housed"] == 1
    assert done["recomputed"] == 0 and done["calls"] == [] and lab_.owners(DESIGN, 12) == {GERMANY}


def test_the_queue_is_finished_without_touching_how_long_research_takes(lib):
    """"대기열의 연구 즉시 완료": 걸린 기술과 부대 설계를 모두 끝내고 대기열에서 뺀다. 내장 치트(e=mc2)는 부대 설계를 남겨 두었고,
    모든 기술의 연구 기간(+0x30)을 1일로 바꿨다 — 모든 나라가 함께 쓰는 표다. ToyBox 는 그 칸에 쓰지 않는다."""
    fake, lab_ = lab()
    days = [struct.unpack_from("<f", lab_.techs, n * TECH_SIZE + 0x30)[0] for n in range(64)]
    wrote, done = write(lib, fake, lab_, "queue")
    assert wrote == DONE and done["techs"] == [2, 3] and done["designs"] == [11] and done["asked"] == (1, 1) and done["nodes"] == [0, 1]
    assert all(flags[0] & GONE and flags[1] & GONE for flags in map(lab_.flags, lab_.nodes))
    assert [struct.unpack_from("<f", lab_.techs, n * TECH_SIZE + 0x30)[0] for n in range(64)] == days
    assert write(lib, fake, lab_, "queue")[1]["text"] == ""                           # 한 번 더 — 대기열이 비었다


def test_level_takes_the_techs_at_or_below_it(lib):
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "level 40")
    assert wrote == DONE and done["techs"] == [2, 3] and done["asked"] == (2, 0) and done["designs"] == []
    assert lab_.held(TECH, 64, GERMANY) == [1, 2, 3, 4, 6] and lab_.held(DESIGN, 64, GERMANY) == [10, 13, 14]


def test_revoking_a_tech_clears_the_players_bit_on_what_leaned_on_it(lib):
    """기술 4 를 미완료로: 4 와, 4 를 선행으로 갖는 6, 6 을 선행으로 갖는 설계 13. 14 는 게임이 건너뛰는 설계라 그대로다.
    다른 나라의 비트는 그대로이고 묶음도 그대로 둔다(풀지 않는다)."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items t4", REVOKE)
    assert wrote == DONE and done["techs"] == [4, 6] and done["designs"] == [13] and done["asked"] == (1, 0) and done["nodes"] == []
    assert done["text"] == "기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)"
    assert lab_.owners(TECH, 4) == {DENMARK} and lab_.owners(TECH, 6) == set() and lab_.block(TECH, 6) != 0
    assert lab_.owners(DESIGN, 13) == {POLAND} and lab_.owners(DESIGN, 14) == {GERMANY}
    assert done["housed"] == 0 and done["calls"] == [(lab_.world, GERMANY)]
    wrote, done = write(lib, fake, lab_, "items d10", REVOKE)
    assert wrote == DONE and done["designs"] == [10] and done["calls"] == [] and lab_.owners(DESIGN, 10) == set()


def rehouse(lab_: Lab, make) -> None:
    """모든 보유 묶음을 make() 가 주는 자리로 옮긴다(내용은 그대로)."""
    for kind, count in ((TECH, 64), (DESIGN, 64)):
        for number in range(1, count):
            old = lab_.block(kind, number)
            if old:
                new = make()
                ctypes.memmove(new, old, OWNERS_BYTES)
                lab_.house(kind, number, block=new)


@pytest.mark.parametrize("where", ["a-buffer", "a-bigger-block"])
def test_a_new_set_is_made_only_when_the_games_sets_are_heap_blocks_of_that_size(lib, where):
    """새 묶음은 게임이 나중에 풀 것이다 — 게임이 묶음을 받는 힙 · 크기와 같아야 한다. 이미 있는 묶음이 프로세스 힙의 128바이트 블록이
    아니면(다른 할당기를 쓰는 빌드, 지역이 늘어난 빌드) 만들지 않는다: 묶음이 없는 항목만 건너뛰고 나머지는 쓴다."""
    fake, lab_ = lab()
    pool = (ctypes.c_ubyte * 0x4000)()
    used = iter(range(0, 0x4000, 0x100))
    if where == "a-buffer":
        rehouse(lab_, lambda: ctypes.addressof(pool) + next(used))
    else:
        rehouse(lab_, lambda: kernel32.HeapAlloc(kernel32.GetProcessHeap(), 8, 2 * OWNERS_BYTES))
    wrote, done = write(lib, fake, lab_, "items t3 d12 d10 t7")
    assert wrote == DONE and done["techs"] == [7] and done["designs"] == [] and done["skipped"] == 2 and done["housed"] == 0
    assert lab_.block(TECH, 3) == 0 and lab_.block(DESIGN, 12) == 0 and lab_.owners(TECH, 7) == {DENMARK, GERMANY}
    assert lab_.owners(TECH, 2) == {POLAND}                                           # 건너뛴 3 의 선행은 따라가지 않았다


def test_nothing_is_written_when_one_of_the_sets_cannot_be_written(lib):
    """쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다. 하나라도 아니면 한 칸도 쓰지 않는다 — 받아 둔 새 묶음도 돌려준다."""
    fake, lab_ = lab()
    lab_.house(TECH, 2, block=locked_page())              # 기술 2 의 묶음이 읽기 전용 쪽에 있다
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t3")
    assert wrote == FAILED and done["why"] == "기술 2 의 보유 묶음" and done["written"] == 0 and done["cells"] == 5
    assert done["calls"] == [] and lab_.everything() == before and lab_.block(TECH, 3) == 0


def test_nothing_is_written_when_a_queue_node_cannot_be_written(lib):
    fake, lab_ = lab()
    page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
    lab_.queue(GERMANY, TECH, 7, at=page)
    assert kernel32.VirtualProtect(page, 0x1000, 0x02, ctypes.byref(ctypes.c_ulong()))
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t7")
    assert wrote == FAILED and done["why"] == "연구 목록의 노드" and done["written"] == 0
    assert done["calls"] == [] and lab_.everything() == before


def test_a_fault_in_the_games_function_is_caught(lib):
    """"다시 셈"에서 예외가 나면 죽지 않고 그 코드를 돌려준다(부른 쪽이 ToyBox 를 멈춘다). 비트는 이미 썼다."""
    fake, lab_ = lab()
    wrote, done = write(lib, fake, lab_, "items t2", recompute=ctypes.c_void_p(8))    # 부를 수 없는 주소
    assert wrote == CRASHED and done["code"] == 0xC0000005 and done["recomputed"] == 0
    assert lab_.owners(TECH, 2) == {POLAND, GERMANY}


def test_an_empty_request_writes_nothing_and_calls_nothing(lib):
    fake, lab_ = lab()
    before = lab_.everything()
    wrote, done = write(lib, fake, lab_, "items t1 d10 t5 t63")      # 이미 보유한 것, 빈 자리, 표에 없는 번호
    assert wrote == DONE and done["text"] == "" and done["cells"] == 0 and done["calls"] == [] and lab_.everything() == before


# ---------------------------------------------------------------------------------------------------------------------
# 이 프로세스의 "게임"에서: 연구를 쓸 수 있는가, 게임이 뜰 때의 찾기와 로그

CAN_RESEARCH = 64                                         # srtoybox_game_flags 의 비트


def text(call, *args, size: int = 4096) -> str:
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return buf.raw[:max(n, 0)].decode("utf-8")


def test_research_is_off_until_its_place_is_known(lib):
    """연구는 제 묶음을 찾았을 때만 쓴다. 못 찾았으면 까닭을 그대로 보인다 — 내장 치트로 되돌아가지 않는다."""
    fake, lab_ = lab()
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    hook = RECOMPUTE(lambda world, index: None)
    try:
        lib.srtoybox_test_game(fake.base, ctypes.byref(fake.at), None)
        assert not lib.srtoybox_game_flags() & CAN_RESEARCH
        assert text(lib.srtoybox_research_off) == "이 게임 판에서는 쓸 수 없습니다 (연구의 자리를 주지 않았습니다)"
        lib.srtoybox_test_research(ctypes.byref(lab_.layout), ctypes.cast(hook, ctypes.c_void_p))
        assert lib.srtoybox_game_flags() & CAN_RESEARCH and text(lib.srtoybox_research_off) == ""
        lib.srtoybox_test_research(None, None)
        assert not lib.srtoybox_game_flags() & CAN_RESEARCH
    finally:
        lib.srtoybox_test_game(None, None, None)
    assert text(lib.srtoybox_research_off) == "게임 상태를 읽을 수 있을 때만 씁니다."


@pytest.fixture(scope="module")
def sigs(lib):
    """DLL 에 든 서명 표: (상태 21개, 값 12개, 연구 21개) — 저마다 [(찾을 것, 서명 글)]."""
    rows = lambda found: [(row.name, row.text) for row in found[2]]
    return rows(toybox.state_of(lib, b"")), rows(toybox.values_of(lib, b"")), rows(toybox.research_of(lib, b"", None))


def startup(lib, image: bytes, tmp_path, monkeypatch) -> tuple[int, str, list[str]]:
    """게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다: (아는 것의 비트, 연구를 쓸 수 없는 까닭, 로그의 줄들 — 때를 뗀 것)."""
    lib.srtoybox_test_init.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong]
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    try:
        lib.srtoybox_test_init(image, len(image))
        flags, off = lib.srtoybox_game_flags(), text(lib.srtoybox_research_off)
    finally:
        lib.srtoybox_test_game(None, None, None)              # 이미지를 놓기 전에 이 프로세스의 "게임"을 비운다
    log = tmp_path / "toybox.log"
    return flags, off, [line.split(" ", 2)[2] for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


FOUND = "연구를 씁니다 (기술 표 +0x5048 · 부대 설계 표 +0x5058 · 연구 목록 +0x2100 · 다시 셈 +0x1C00)"


def test_startup_finds_research_without_any_cheat(lib, sigs, tmp_path, monkeypatch):
    """치트 문자열이 하나도 없는 이미지에서도 연구의 자리와 다시 셈 함수를 찾는다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(state + values + research_)
    assert b"cheat" not in image
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    assert flags & CAN_RESEARCH and off == "" and FOUND in log
    assert not any("맞지 않은 서명" in line for line in log)


def test_startup_without_research_keeps_everything_else(lib, sigs, tmp_path, monkeypatch):
    """연구의 서명이 없는 게임: 연구만 꺼지고(까닭 한 줄) 상태 읽기와 돈 · 물자는 그대로다."""
    state, values, _ = sigs
    flags, off, log = startup(lib, toybox_fake_exe.sig_image(state + values), tmp_path, monkeypatch)
    assert flags & 5 == 5 and not flags & CAN_RESEARCH                                # 상태를 읽고 값(국고 · 재고)을 쓴다
    assert off == "이 게임 판에서는 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)"
    assert "연구를 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)" in log and not any(line.startswith("연구를 씁니다") for line in log)


def test_startup_drops_research_when_one_signature_is_missing(lib, sigs, tmp_path, monkeypatch):
    """연구는 서명 하나만 맞지 않아도 쓰지 않는다 — 표의 꼴이 서명마다 박혀 있다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(research_ + state + values, broken={17})        # 연구 목록의 셋째 서명
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    assert flags & 5 == 5 and not flags & CAN_RESEARCH and "연구를 쓸 수 없습니다 (연구 목록: 서명 3개 가운데 2개)" in log


def test_startup_drops_research_that_sits_on_the_world_pointer(lib, sigs, tmp_path, monkeypatch):
    """저마다 찾았어도 연구의 전역이 값 묶음의 세계 자료 포인터와 겹치면 연구는 쓰지 않는다. 돈 · 물자는 그대로다."""
    state, values, research_ = sigs
    image = toybox_fake_exe.sig_image(state + values + research_, targets={"tech_table": toybox_fake_exe.VALUE_LAYOUT["world_pointer"]})
    flags, off, log = startup(lib, image, tmp_path, monkeypatch)
    clash = "기술 표: 찾은 주소가 세계 자료 포인터 의 자리와 겹칩니다"
    assert flags & 5 == 5 and not flags & CAN_RESEARCH and off == f"이 게임 판에서는 쓸 수 없습니다 ({clash})"
    assert f"연구를 쓸 수 없습니다 ({clash})" in log and any(line.startswith("값을 씁니다 (국고 ") for line in log)


def test_startup_without_the_state_does_not_look_for_research(lib, sigs, tmp_path, monkeypatch):
    _, _, research_ = sigs
    flags, off, log = startup(lib, toybox_fake_exe.sig_image(research_), tmp_path, monkeypatch)
    assert flags == 0 and off == "게임 상태를 읽을 수 있을 때만 씁니다." and not any("연구" in line for line in log)
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
    assert "쓸 수 없습니다" not in log and "맞지 않은 서명" not in log
```

이렇게 바꾼다:

```python
    unwritable = [line.split(" ", 2)[2] for line in log.splitlines() if "쓸 수 없습니다" in line]
    assert unwritable == ["연구를 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)"]      # 이 이미지에 연구의 서명은 넣지 않았다
    assert "맞지 않은 서명" not in log
```

`tests/toybox_fake_game.py` 에서 다음 바로 뒤에:

```python
값의 자리(LAYOUT)는 진짜 게임의 것보다 작게 잡았다 — ToyBox 는 자리를 찾은 것(ValueLayout)에서만 읽는다.
```

이것을 더한다:

```python
연구(Lab)는 따로 붙인다: 기술 표 · 부대 설계 표 · 보유 비트 묶음 · 지역별 연구 목록.
```

`tests/toybox_fake_game.py` 에서 다음을 찾아:

```python
from srkit.toybox import GameAddresses, MoreLayout, ValueLayout
```

이렇게 바꾼다:

```python
from srkit.toybox import GameAddresses, MoreLayout, ResearchLayout, ValueLayout
```

`tests/toybox_fake_game.py` 에서 다음 바로 뒤에:

```python
OBJECT_SIZE = 0x1000
```

이것을 더한다:

```python
# 연구의 자리: 전역 넷은 mem 의 앞쪽, 세계 객체는 mem 의 0x800 부터(지역 표가 그 +0x800), 연구 목록은 그 +0x1800(지역마다 24바이트 × 256칸).
# "다시 셈" 함수는 자리가 아니라 함수로 준다(srtoybox_research_write · srtoybox_test_research 의 인자)
RESEARCH = dict(tech_table=0x50, tech_count=0x58, design_table=0x60, design_count=0x5C, world=0x800, lists=0x1800, recompute=0)
TECH_SIZE, DESIGN_SIZE, OWNERS_BYTES, LIST_STEP, NODE_SIZE = 0x88, 0x168, 128, 24, 0x60   # native/srtoybox/locate.h 의 꼴
TECH, DESIGN = 1, 2                                                                        # 연구 목록 노드의 종류
GONE, ENDED = 0x80000000, 0x08000000                                                       # 노드의 깃발: 그 쪽에서 뺐다 / 치트의 "끝냄"
```

`tests/toybox_fake_game.py` 에서 다음 바로 뒤에:

```python
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
```

이것을 더한다:

```python
kernel32.GetProcessHeap.restype = ctypes.c_void_p
kernel32.HeapAlloc.restype = ctypes.c_void_p
kernel32.HeapAlloc.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t]
kernel32.HeapSize.restype = ctypes.c_size_t
kernel32.HeapSize.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
kernel32.HeapValidate.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
```

`tests/toybox_fake_game.py` 에서 다음 바로 뒤에:

```python
        return page
```

이것을 더한다:

```python


def locked_page(protection: int = 0x02) -> int:
    """0 으로 찬 한 쪽을 잡아 쓸 수 없게 한다(0x02 읽기 전용, 0x20 실행 · 읽기). 그 주소를 돌려준다(돌려주지 않는다 — 프로세스가 끝나면 없어진다)."""
    page = kernel32.VirtualAlloc(None, 0x1000, 0x3000, 0x04)
    old = wintypes.DWORD()
    assert kernel32.VirtualProtect(page, 0x1000, protection, ctypes.byref(old))
    return page


class Lab:
    """가짜 게임의 연구: 기술 표 · 부대 설계 표 · 보유 비트 묶음 · 지역별 연구 목록.

    표는 따로 잡은 버퍼이고 mem 의 전역이 그 주소와 자리 수를 가리킨다. 보유 묶음은 게임처럼 프로세스 힙에서 128바이트를 받는다 —
    ToyBox 는 새 묶음을 만들기 전에 게임의 묶음이 그 힙의 것인지 본다. block 을 주면 그 주소를 묶음으로 건다(그 힙의 블록이 아닌 것,
    쓸 수 없는 쪽에 있는 것을 흉내 낼 때).
    """

    def __init__(self, fake: FakeGame, techs: int = 64, designs: int = 64):
        self.fake = fake
        self.layout = ResearchLayout(**RESEARCH)
        self.techs = (ctypes.c_ubyte * (techs * TECH_SIZE))()
        self.designs = (ctypes.c_ubyte * (designs * DESIGN_SIZE))()
        self.kept: list = []                                      # 이름 글과 노드의 버퍼(살려 둔다)
        self.nodes: list[int] = []                                # 노드의 주소(건 순서)
        fake.poke(RESEARCH["tech_table"], "<Q", ctypes.addressof(self.techs))
        fake.poke(RESEARCH["tech_count"], "<i", techs)
        fake.poke(RESEARCH["design_table"], "<Q", ctypes.addressof(self.designs))
        fake.poke(RESEARCH["design_count"], "<i", designs)

    @property
    def world(self) -> int:
        """세계 객체의 주소("다시 셈" 함수의 첫 인자)."""
        return self.fake.base + RESEARCH["world"]

    def tech(self, number: int, *needs: int, level: int = 10, kind: int = 1, days: float = 100.0, owners=()) -> None:
        """기술 레코드: +0 분류, +1 수준, +4 · +6 선행, +0x30 연구 기간(ToyBox 는 건드리지 않는다), +0x50 보유 묶음."""
        at = number * TECH_SIZE
        struct.pack_into("<BB", self.techs, at, kind, level)
        struct.pack_into("<HH", self.techs, at + 4, *(list(needs) + [0, 0])[:2])
        struct.pack_into("<f", self.techs, at + 0x30, days)
        for index in owners:
            self.own(TECH, number, index)

    def design(self, number: int, *needs: int, cls: int = 0, year: int = 50, is_open: bool = True, hold: tuple[int, int] = (0, 0),
               name: bytes = b"Unit", owners=()) -> None:
        """부대 설계 레코드: +0 이름 글, +8 병과, +0xA 연도, +0x20 연구 대상, +0x34 선행 넷, +0xEC · +0xF0 깃발, +0xF8 보유 묶음."""
        at = number * DESIGN_SIZE
        text = ctypes.create_string_buffer(name)
        self.kept.append(text)
        struct.pack_into("<Q", self.designs, at, ctypes.addressof(text))
        struct.pack_into("<BxB", self.designs, at + 8, cls, year)
        struct.pack_into("<H", self.designs, at + 0x20, int(is_open))
        struct.pack_into("<4H", self.designs, at + 0x34, *(list(needs) + [0] * 4)[:4])
        struct.pack_into("<II", self.designs, at + 0xEC, *hold)
        for index in owners:
            self.own(DESIGN, number, index)

    def _cell(self, kind: int, number: int) -> tuple[ctypes.Array, int]:
        """그 항목의 보유 묶음 포인터가 든 칸: (표, 표 안의 자리)."""
        return (self.techs, number * TECH_SIZE + 0x50) if kind == TECH else (self.designs, number * DESIGN_SIZE + 0xF8)

    def block(self, kind: int, number: int) -> int:
        """그 항목의 보유 묶음의 주소. 없으면 0."""
        table, at = self._cell(kind, number)
        return struct.unpack_from("<Q", table, at)[0]

    def house(self, kind: int, number: int, block: int | None = None) -> int:
        """보유 묶음을 건다. block 을 주지 않으면 프로세스 힙에서 0 으로 찬 128바이트를 받는다(게임이 하는 그대로)."""
        table, at = self._cell(kind, number)
        if block is None:
            block = kernel32.HeapAlloc(kernel32.GetProcessHeap(), 8, OWNERS_BYTES)      # HEAP_ZERO_MEMORY
        struct.pack_into("<Q", table, at, block)
        return block

    def own(self, kind: int, number: int, index: int, on: bool = True) -> None:
        """그 지역(인덱스)이 그 항목을 보유한다 / 하지 않는다. 묶음이 없으면 만든다."""
        block = self.block(kind, number) or self.house(kind, number)
        byte = ctypes.string_at(block + index // 8, 1)[0]
        byte = byte | (1 << index % 8) if on else byte & ~(1 << index % 8)
        ctypes.memmove(block + index // 8, bytes([byte]), 1)

    def owners(self, kind: int, number: int) -> set[int]:
        """그 항목을 보유한 지역의 인덱스들. 묶음이 없으면 빈 집합."""
        block = self.block(kind, number)
        bits = int.from_bytes(ctypes.string_at(block, OWNERS_BYTES), "little") if block else 0
        return {index for index in range(OWNERS_BYTES * 8) if bits >> index & 1}

    def held(self, kind: int, count: int, index: int) -> list[int]:
        """그 지역이 보유한 항목의 번호들(1 … count - 1 에서)."""
        return [number for number in range(1, count) if index in self.owners(kind, number)]

    def queue(self, index: int, kind: int, number: int, flags: tuple[int, int] = (1, 0), at: int | None = None) -> int:
        """그 지역의 연구 목록의 머리에 노드를 건다(게임처럼 새 노드가 머리가 된다). 노드의 주소를 돌려준다.
        노드: +0x08 앞, +0x10 다음, +0x18 번호, +0x1C 종류, +0x20 · +0x24 깃발, +0x28 남은 기간. at 을 주면 그 주소에 짓는다."""
        if at is None:
            buffer = (ctypes.c_ubyte * NODE_SIZE)()
            self.kept.append(buffer)
            at = ctypes.addressof(buffer)
        head = RESEARCH["world"] + RESEARCH["lists"] + LIST_STEP * index
        after = self.fake.peek(head, "<Q")
        ctypes.memmove(at, struct.pack("<QQQIIIIf", 0x1234, 0, after, number, kind, flags[0], flags[1], 115.0), 0x2C)
        if after:
            ctypes.memmove(after + 8, struct.pack("<Q", at), 8)
        self.fake.poke(head, "<Q", at)
        self.fake.poke(head + 8, "<Q", self.fake.peek(head + 8, "<Q") + 1)
        self.nodes.append(at)
        return at

    def flags(self, node: int) -> tuple[int, int]:
        return struct.unpack("<II", ctypes.string_at(node + 0x20, 8))

    def everything(self) -> dict[str, bytes]:
        """연구에 딸린 메모리 전부: 표 둘, 묶음마다(t<번호> · d<번호>), 노드마다(n<건 순서>), 그리고 가짜 게임의 전역(mem).
        쓰기가 다른 곳을 건드리지 않았는지 볼 때 앞뒤를 견준다."""
        out = {"mem": bytes(self.fake.mem), "techs": bytes(self.techs), "designs": bytes(self.designs)}
        for kind, letter, count in ((TECH, "t", len(self.techs) // TECH_SIZE), (DESIGN, "d", len(self.designs) // DESIGN_SIZE)):
            for number in range(1, count):
                if self.block(kind, number):
                    try:
                        out[f"{letter}{number}"] = ctypes.string_at(self.block(kind, number), OWNERS_BYTES)
                    except OSError:                   # 읽을 수 없는 주소를 묶음으로 걸어 둔 테스트
                        out[f"{letter}{number}"] = b""
        for i, node in enumerate(self.nodes):
            out[f"n{i}"] = ctypes.string_at(node, NODE_SIZE)
        return out


def standard_lab(fake: FakeGame, germany: int = 176, poland: int = 141, denmark: int = 150) -> Lab:
    """테스트들이 함께 쓰는 연구의 판. 지역은 인덱스로 준다(독일이 플레이어다).

    기술      1(수준 10. 독일 · 폴란드 보유) ← 2(수준 20. 폴란드만) ← 3(수준 30. 아무도 — 묶음이 없다) / 4(수준 40. 독일 · 덴마크) ← 6(수준 60. 독일)
              / 7(수준 70. 덴마크만). 5 는 빈 자리다.
    부대 설계 10(선행 1. 독일) / 11(선행 3. 폴란드. 병과 2, 1995년) / 12(선행 4. 아무도 — 묶음이 없다) / 13(선행 6. 독일 · 폴란드)
              / 14(선행 6. 독일. 게임이 "기술을 뺄 때" 건너뛰는 설계다 — 깃발)
    독일의 대기열: 기술 2 를 걸고(막 건 것) 그 뒤에 부대 설계 11 을 걸었다(연구 중). 게임처럼 나중에 건 것이 목록의 앞이다.
    """
    lab = Lab(fake)
    lab.tech(1, level=10, owners=(germany, poland))
    lab.tech(2, 1, level=20, owners=(poland,))
    lab.tech(3, 2, level=30)
    lab.tech(4, level=40, owners=(germany, denmark))
    lab.tech(6, 4, level=60, owners=(germany,))
    lab.tech(7, level=70, owners=(denmark,))
    lab.design(10, 1, owners=(germany,))
    lab.design(11, 3, cls=2, year=95, owners=(poland,))
    lab.design(12, 4)
    lab.design(13, 6, owners=(germany, poland))
    lab.design(14, 6, hold=(1, 0), owners=(germany,))
    lab.queue(germany, TECH, 2)
    lab.queue(germany, DESIGN, 11, flags=(1, 0x60000001))
    return lab
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_research.py tests/test_toybox_values.py -q 2>&1 | tail -4`

Expected: `1 failed, 82 passed, 64 errors` — 연구 테스트 64개가 모두 fixture(`lib`)에서 `AttributeError: function 'srtoybox_research_read' not found` 로 오류가 나고(Task 3 의 규칙 테스트 32개도 같은 fixture 를 쓴다), 값 테스트 하나(`test_startup_finds_more_without_any_cheat`)가 시작 로그에 연구의 줄이 아직 없어 실패한다(`assert [] == ['연구를 쓸 수 없습니다 (기술 표: 서명 3개 가운데 0개)']`).

- [ ] **Step 3: 구현한다**

순서는 설계서 그대로다: 스냅숏(`shoot`) → 규칙 → 모든 칸의 확인 → 새 묶음 → 비트 → 노드의 깃발 → 다시 셈. 비트와 깃발은 `poke_bits` 로 원자적으로 쓴다(같은 바이트의 다른 나라의 비트를 읽어서 되쓰지 않는다). `__try` 를 쓰는 함수(`guarded_recompute` · `heap_block` · `poke_bits`)에는 소멸자가 있는 지역 객체가 없다.

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
// 테스트: 게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다. 이미지는 srtoybox_test_game(nullptr, …) 로 비울 때까지 살아 있어야 한다.
```

이것을 더한다:

```cpp
// 테스트: 가짜 메모리에서 연구의 표를 읽는다(read_research). 읽었으면 1 과 표의 글, 못 읽었으면 0 과 까닭.
// 표의 글은 한 줄에 하나: "slots <기술 자리 수> <설계 자리 수>" /
//   "t <번호> <분류> <수준> <선행 0> <선행 1> <보유> <고른 나라가 보유> <다른 나라의 수> <대기열에 있다> <묶음이 있다>" /
//   "d <번호> <병과> <연도> <연구 대상> <게임이 건너뛰는 설계> <보유> <고른 나라가 보유> <다른 나라의 수> <대기열에 있다> <묶음이 있다> <선행 넷>" /
//   "q <종류> <번호> <깃발 0(16진수)> <깃발 1(16진수)>"
EXPORT int srtoybox_research_read(const unsigned char *base, const GameAddresses *at, const ResearchLayout *layout, int picked, char *out,
                                  int size)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    ResearchTables t;
    std::string why;
    if (!read_research(base, *at, *layout, picked, &t, &why))
        return put(why, out, size) < 0 ? -1 : 0;
    std::ostringstream text;
    text << "slots " << t.tech_slots << ' ' << t.design_slots << '\n';
    for (const TechRow &row : t.techs)
        text << "t " << row.id << ' ' << row.kind << ' ' << row.level << ' ' << row.needs[0] << ' ' << row.needs[1] << ' ' << row.mine
             << ' ' << row.picked << ' ' << row.others << ' ' << row.queued << ' ' << row.housed << '\n';
    for (const DesignRow &row : t.designs)
        text << "d " << row.id << ' ' << row.cls << ' ' << row.year << ' ' << row.open << ' ' << row.held << ' ' << row.mine << ' '
             << row.picked << ' ' << row.others << ' ' << row.queued << ' ' << row.housed << ' ' << row.needs[0] << ' ' << row.needs[1]
             << ' ' << row.needs[2] << ' ' << row.needs[3] << '\n';
    for (const QueueRow &row : t.queue)
        text << "q " << row.kind << ' ' << row.id << ' ' << std::hex << row.flags[0] << ' ' << row.flags[1] << std::dec << '\n';
    return put(text.str(), out, size) < 0 ? -1 : 1;
}

// 테스트: 가짜 메모리의 연구를 완료(action 0) · 미완료(1)로 바꾼다(write_research). what 은 what_from 의 글,
// recompute 는 "다시 셈" 자리에 둘 함수(없으면 nullptr). 돌려주는 값은 Wrote. out 에는 한 줄에 하나:
// "techs …" / "designs …" / "nodes …" / "asked <기술> <설계>" / "skipped N" / "housed N" / "cells N" / "written N" /
// "recomputed 0|1" / "code <예외 코드(16진수)>" / "why <까닭>" / "text <알림의 글>"
EXPORT int srtoybox_research_write(const unsigned char *base, const GameAddresses *at, const ResearchLayout *layout, void *recompute,
                                   int action, const char *what, char *out, int size)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    const Research how = action == 0 ? Research::Complete : Research::Revoke;
    ResearchDone done;
    const Wrote wrote = write_research(base, *at, *layout, reinterpret_cast<Recompute>(recompute), how,
                                       what_from(what != nullptr ? what : ""), &done);
    std::ostringstream text;
    text << numbers("techs", done.plan.techs) << numbers("designs", done.plan.designs) << numbers("nodes", done.plan.nodes) << "asked "
         << done.plan.asked_techs << ' ' << done.plan.asked_designs << "\nskipped " << done.skipped << "\nhoused " << done.housed
         << "\ncells " << done.cells << "\nwritten " << done.written << "\nrecomputed " << done.recomputed << "\ncode " << std::hex
         << done.code << "\nwhy " << done.why << "\ntext " << research_summary(done.plan, how);
    put(text.str(), out, size);
    return static_cast<int>(wrote);
}

// 테스트: 이 프로세스의 "게임"에 연구의 자리와 "다시 셈" 자리에 둘 함수를 준다(srtoybox_test_game 다음에 부른다). nullptr 이면 못 찾은 것으로.
EXPORT void srtoybox_test_research(const ResearchLayout *layout, void *recompute)
{
    game_set_research_for_test(layout, recompute);
}

// 연구를 쓸 수 없는 까닭. 쓸 수 있으면 빈 글.
EXPORT int srtoybox_research_off(char *out, int size)
{
    return put(game_research_off(), out, size);
}

```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
// 8 = 기술 수준을, 16 = 세계 시장 여론을, 32 = 관계를 쓸 수 있다.
```

이렇게 바꾼다:

```cpp
// 8 = 기술 수준을, 16 = 세계 시장 여론을, 32 = 관계를, 64 = 연구를 쓸 수 있다.
```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
        | (game_more_off(MORE_RELATIONS).empty() ? 32 : 0);
```

이렇게 바꾼다:

```cpp
        | (game_more_off(MORE_RELATIONS).empty() ? 32 : 0) | (game_research_off().empty() ? 64 : 0);
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)
```

이것을 더한다:

```cpp
const int MAX_ITEMS = 65536;    // 기술 · 부대 설계 표의 자리 수의 상한(선행의 번호가 16비트다)
const int MAX_NODES = 4096;     // 지역 하나의 연구 목록에서 따라가는 노드의 상한
const char *const NOT_PLAYING = "게임이 진행 중이 아닙니다";
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
char g_more_why[MORE_GROUPS][MORE_WHY];   // 묶음마다 못 찾은 까닭
```

이것을 더한다:

```cpp
ResearchLayout g_research;    // 연구의 자리
bool g_research_found;        // 그것을 찾았다
char g_research_why[200];     // 못 찾은 까닭
void *g_recompute;            // 게임의 "지역의 효과를 다시 셈"
```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
// 안전한 읽기: 낡은 포인터를 만나도 죽지 않는다.
```

이것을 더한다:

```cpp
// 게임의 "지역의 효과를 다시 셈"을 부른다. 예외는 잡아 code 에 적는다.
bool guarded_recompute(Recompute recompute, void *world, int index, unsigned long *code)
{
    __try {
        recompute(world, index);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        *code = GetExceptionCode();
        return false;
    }
}

// 그 주소가 프로세스 힙에서 받은 size 바이트짜리 블록인가. 게임이 보유 묶음을 받는 힙이 ToyBox 가 받을 힙과 같은지 볼 때 쓴다 —
// 다른 힙의 블록을 걸면 게임이 그것을 풀 때 깨진다. 힙의 블록이 아닌 주소를 넘겨도 죽지 않게 예외를 잡는다.
bool heap_block(uint64_t address, size_t size)
{
    __try {
        const HANDLE heap = GetProcessHeap();
        void *const block = reinterpret_cast<void *>(address);
        return HeapValidate(heap, 0, block) != 0 && HeapSize(heap, 0, block) == size;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
// 지역 객체의 머리: +0 상태(dword), +4 자기 인덱스(word), +8 지역 번호(word).
```

이것을 더한다:

```cpp
// 칸(1바이트나 4바이트)의 비트들만 켜거나 끈다 — 원자적으로. 그 칸의 다른 비트는 읽어서 되쓰지 않으므로, 그 순간 게임이 그것들을
// 바꿔도 덮어쓰지 않는다(보유 묶음의 한 바이트에는 여덟 나라의 비트가 함께 있다). 쓴 뒤 그 비트들을 다시 읽어 본다(아니면 한 번 더).
bool poke_bits(uint64_t address, uint32_t mask, bool on, size_t size)
{
    for (int attempt = 0; attempt < 2; attempt++) {
        if (!writable(address, size))
            return false;
        __try {
            if (size == 1 && on)
                InterlockedOr8(reinterpret_cast<char *>(address), static_cast<char>(mask));
            else if (size == 1)
                InterlockedAnd8(reinterpret_cast<char *>(address), static_cast<char>(~mask));
            else if (on)
                InterlockedOr(reinterpret_cast<LONG *>(address), static_cast<LONG>(mask));
            else
                InterlockedAnd(reinterpret_cast<LONG *>(address), static_cast<LONG>(~mask));
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            return false;
        }
        uint32_t back = 0;
        if (peek(reinterpret_cast<const void *>(address), &back, size) && (back & mask) == (on ? mask : 0u))
            return true;
    }
    return false;
}

```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
}  // namespace
```

이것을 더한다:

```cpp
// 연구의 스냅숏과, 그것을 쓸 때 필요한 주소들.
struct Shot {
    ResearchTables tables;
    std::vector<uint64_t> tech_owners, design_owners;   // tables 의 행과 같은 순서: 보유 묶음의 주소(없으면 0)
    std::vector<uint64_t> tech_cells, design_cells;     // 〃 레코드에서 그 포인터가 든 칸의 주소
    std::vector<uint64_t> nodes;                        // tables.queue 와 같은 순서: 노드의 주소
    uint64_t world = 0;                                 // 세계 객체의 주소
    int me = 0;                                         // 플레이어의 인덱스
    bool multiplayer = false;
};

// 레코드의 한 칸.
template <class T>
T field(const uint8_t *record, uint32_t offset)
{
    T value;
    memcpy(&value, record + offset, sizeof(T));
    return value;
}

// 보유 묶음에서 플레이어(me)와 고른 나라(them. 없으면 0)의 비트, 그리고 플레이어를 뺀 보유 나라의 수. 묶음이 없으면(0) 아무도 없다.
bool owners_of(uint64_t owners, int me, int them, bool *mine, bool *picked, int *others)
{
    *mine = *picked = false;
    *others = 0;
    if (owners == 0)
        return true;
    uint8_t bits[OWNERS_BYTES];
    if (!peek(reinterpret_cast<const void *>(owners), bits, sizeof(bits)))
        return false;
    int count = 0;
    for (uint8_t byte : bits)
        for (; byte != 0; byte = static_cast<uint8_t>(byte & (byte - 1)))
            count++;
    *mine = (bits[me / 8] >> (me % 8) & 1) != 0;
    *picked = them > 0 && (bits[them / 8] >> (them % 8) & 1) != 0;
    *others = count - (*mine ? 1 : 0);
    return true;
}

// 표 둘과 플레이어의 연구 목록을 읽는다. 게임을 진행 중이 아니면 why 는 NOT_PLAYING 이다(멀티플레이는 진행 중으로 읽고 표시만 한다).
bool shoot(const uint8_t *base, const GameAddresses &at, const ResearchLayout &r, int picked, Shot *shot, std::string *why)
{
    uint64_t player = 0, other = 0, tech_table = 0, design_table = 0, node = 0;
    int32_t me = 0, tech_count = 0, design_count = 0;
    int them = 0;
    const GameState s = read_player(base, at, &player);
    if (!s.in_game || !peek_at(base, at.player_index, &me) || me < 1 || me >= MAX_REGIONS) {
        *why = NOT_PLAYING;
        return false;
    }
    if (picked > 0 && picked != s.player && !find_region(base, at, picked, &other, &them))
        them = 0;
    if (!peek_at(base, r.tech_count, &tech_count) || !peek_at(base, r.design_count, &design_count)
        || !peek_at(base, r.tech_table, &tech_table) || !peek_at(base, r.design_table, &design_table)) {
        *why = "표의 전역을 읽을 수 없습니다";
        return false;
    }
    if (tech_count < 2 || tech_count > MAX_ITEMS || design_count < 2 || design_count > MAX_ITEMS || tech_table == 0 || design_table == 0) {
        *why = "표가 없거나 자리 수가 범위 밖입니다";
        return false;
    }
    shot->me = me;
    shot->multiplayer = s.multiplayer;
    shot->world = reinterpret_cast<uint64_t>(base) + r.world;
    ResearchTables &t = shot->tables;
    t.tech_slots = tech_count;
    t.design_slots = design_count;

    std::vector<uint8_t> raw(static_cast<size_t>(tech_count) * TECH_SIZE);
    if (!peek(reinterpret_cast<const void *>(tech_table), raw.data(), raw.size())) {
        *why = "기술 표를 읽을 수 없습니다";
        return false;
    }
    for (int i = 1; i < tech_count; i++) {
        const uint8_t *record = raw.data() + static_cast<size_t>(i) * TECH_SIZE;
        if (record[TECH_KIND] == 0)
            continue;                           // 빈 자리
        TechRow row;
        row.id = i;
        row.kind = record[TECH_KIND];
        row.level = record[TECH_LEVEL];
        for (int n = 0; n < TECH_NEED_COUNT; n++)
            row.needs[n] = field<uint16_t>(record, TECH_NEEDS + 2 * static_cast<uint32_t>(n));
        const uint64_t owners = field<uint64_t>(record, TECH_OWNERS);
        if (!owners_of(owners, me, them, &row.mine, &row.picked, &row.others)) {
            *why = "기술 " + std::to_string(i) + " 의 보유 묶음을 읽을 수 없습니다";
            return false;
        }
        row.housed = owners != 0;
        t.techs.push_back(row);
        shot->tech_owners.push_back(owners);
        shot->tech_cells.push_back(tech_table + static_cast<uint64_t>(i) * TECH_SIZE + TECH_OWNERS);
    }

    raw.assign(static_cast<size_t>(design_count) * DESIGN_SIZE, 0);
    if (!peek(reinterpret_cast<const void *>(design_table), raw.data(), raw.size())) {
        *why = "부대 설계 표를 읽을 수 없습니다";
        return false;
    }
    for (int i = 1; i < design_count; i++) {
        const uint8_t *record = raw.data() + static_cast<size_t>(i) * DESIGN_SIZE;
        if (field<uint64_t>(record, DESIGN_NAME) == 0)
            continue;                           // 빈 자리
        DesignRow row;
        row.id = i;
        row.cls = record[DESIGN_CLASS];
        row.year = record[DESIGN_YEAR];
        row.open = field<uint16_t>(record, DESIGN_OPEN) != 0;
        row.held = (field<uint32_t>(record, DESIGN_HOLD_A) & DESIGN_HOLD_A_BIT) != 0
            || (field<uint32_t>(record, DESIGN_HOLD_B) & DESIGN_HOLD_B_BIT) != 0;
        for (int n = 0; n < DESIGN_NEED_COUNT; n++)
            row.needs[n] = field<uint16_t>(record, DESIGN_NEEDS + 2 * static_cast<uint32_t>(n));
        const uint64_t owners = field<uint64_t>(record, DESIGN_OWNERS);
        if (!owners_of(owners, me, them, &row.mine, &row.picked, &row.others)) {
            *why = "부대 설계 " + std::to_string(i) + " 의 보유 묶음을 읽을 수 없습니다";
            return false;
        }
        row.housed = owners != 0;
        t.designs.push_back(row);
        shot->design_owners.push_back(owners);
        shot->design_cells.push_back(design_table + static_cast<uint64_t>(i) * DESIGN_SIZE + DESIGN_OWNERS);
    }

    // 플레이어의 연구 목록: 머리 노드부터 "다음"을 따라간다
    if (!peek(reinterpret_cast<const void *>(shot->world + r.lists + static_cast<uint64_t>(me) * LIST_STEP), &node, sizeof(node))) {
        *why = "연구 목록을 읽을 수 없습니다";
        return false;
    }
    while (node != 0) {
        uint8_t record[NODE_FLAGS + 8];
        if (shot->nodes.size() >= static_cast<size_t>(MAX_NODES)) {
            *why = "연구 목록이 끝나지 않습니다";
            return false;
        }
        if (!peek(reinterpret_cast<const void *>(node), record, sizeof(record))) {
            *why = "연구 목록의 노드를 읽을 수 없습니다";
            return false;
        }
        QueueRow row;
        row.id = field<int32_t>(record, NODE_ID);
        row.kind = record[NODE_KIND];
        row.flags[0] = field<uint32_t>(record, NODE_FLAGS);
        row.flags[1] = field<uint32_t>(record, NODE_FLAGS + 4);
        t.queue.push_back(row);
        shot->nodes.push_back(node);
        node = field<uint64_t>(record, NODE_NEXT);
    }
    research_mark_queued(&t);
    return true;
}

// 바꿀 항목 하나: 보유 묶음의 주소(없으면 0)와 레코드에서 그 포인터가 든 칸.
struct Item {
    bool tech;
    int id;
    uint64_t owners, cell;
};

// 계획의 번호들(오름차순)에 묶음과 칸의 주소를 붙인다. rows 도 번호순이다.
template <class Row>
void attach(const std::vector<int> &ids, const std::vector<Row> &rows, const std::vector<uint64_t> &owners,
            const std::vector<uint64_t> &cells, bool tech, std::vector<Item> *items)
{
    size_t k = 0;
    for (size_t i = 0; i < rows.size() && k < ids.size(); i++)
        if (rows[i].id == ids[k]) {
            items->push_back({tech, ids[k], owners[i], cells[i]});
            k++;
        }
}

// 쓰기가 막혔다: 어디서(where), 몇 칸 가운데 몇 칸을 쓴 뒤인지 적는다.
Wrote research_failed(ResearchDone *done, const std::string &where)
{
    done->why = where;
    return Wrote::Failed;
}

std::string item_name(const Item &item)
{
    return std::string(item.tech ? "기술 " : "부대 설계 ") + std::to_string(item.id);
}

```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
void game_init()
```

이것을 더한다:

```cpp
bool read_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, int picked, ResearchTables *out,
                   std::string *why)
{
    Shot shot;
    std::string reason;
    bool ok = shoot(base, at, research, picked, &shot, &reason);
    if (ok && shot.multiplayer) {
        ok = false;
        reason = "멀티플레이에서는 연구를 읽지 않습니다";
    }
    if (why != nullptr)
        *why = reason;
    if (ok)
        *out = std::move(shot.tables);
    return ok;
}

Wrote write_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, Recompute recompute, Research action,
                     const ResearchWhat &what, ResearchDone *done)
{
    *done = ResearchDone();
    Shot shot;
    if (!shoot(base, at, research, 0, &shot, &done->why))
        return done->why == NOT_PLAYING ? Wrote::NotInGame : Wrote::Unreadable;
    if (shot.multiplayer)
        return Wrote::NotInGame;

    // 새 묶음을 걸 수 있는가: 이미 있는 묶음 하나가 프로세스 힙의 OWNERS_BYTES 짜리 블록이어야 한다(게임이 그 힙에서 그 크기로 받는다는 뜻)
    uint64_t sample = 0;
    for (uint64_t owners : shot.tech_owners)
        sample = sample != 0 ? sample : owners;
    for (uint64_t owners : shot.design_owners)
        sample = sample != 0 ? sample : owners;
    bool can_house = sample != 0 && heap_block(sample, OWNERS_BYTES);

    const HANDLE heap = GetProcessHeap();
    std::vector<Item> items;
    std::vector<void *> fresh;                  // 새로 받은 묶음. 앞에서부터 차례로 건다
    size_t hung = 0;                            // 그 가운데 이미 건 것의 수(건 것은 게임의 것이다 — 풀지 않는다)
    const auto release = [&]() {
        for (size_t i = hung; i < fresh.size(); i++)
            HeapFree(heap, 0, fresh[i]);
        fresh.clear();
        hung = 0;
    };
    ResearchPlan plan;
    for (int pass = 0; pass < 2; pass++) {      // 묶음을 받지 못하면, 묶음이 없는 항목을 건너뛰는 계획으로 한 번 더
        plan = research_plan(shot.tables, action, what, can_house);
        items.clear();
        attach(plan.techs, shot.tables.techs, shot.tech_owners, shot.tech_cells, true, &items);
        attach(plan.designs, shot.tables.designs, shot.design_owners, shot.design_cells, false, &items);
        bool short_of = false;
        for (const Item &item : items)
            if (item.owners == 0 && !short_of) {
                void *const block = HeapAlloc(heap, HEAP_ZERO_MEMORY, OWNERS_BYTES);
                if (block == nullptr)
                    short_of = true;
                else
                    fresh.push_back(block);
            }
        if (!short_of)
            break;
        release();
        can_house = false;
    }
    done->plan = plan;
    done->skipped = plan.skipped;

    // 쓰기 전에: 모든 칸이 읽기 · 쓰기 쪽인가(반쪽만 쓰고 멈추지 않게)
    const uint64_t byte = static_cast<uint64_t>(shot.me) / 8;
    const uint8_t mask = static_cast<uint8_t>(1u << (shot.me % 8));
    done->cells = static_cast<int>(items.size() + fresh.size() + 2 * plan.nodes.size());
    for (const Item &item : items)
        if (item.owners != 0 ? !writable(item.owners + byte, 1) : !writable(item.cell, sizeof(uint64_t))) {
            release();
            return research_failed(done, item_name(item) + (item.owners != 0 ? " 의 보유 묶음" : " 의 묶음 칸"));
        }
    for (int n : plan.nodes)
        if (!writable(shot.nodes[static_cast<size_t>(n)] + NODE_FLAGS, 2 * sizeof(uint32_t))) {
            release();
            return research_failed(done, "연구 목록의 노드");
        }

    // 묶음(없는 항목만) → 비트
    for (Item &item : items) {
        if (item.owners == 0) {
            const uint64_t block = reinterpret_cast<uint64_t>(fresh[hung]);
            if (!poke(item.cell, &block, sizeof(block))) {
                release();
                return research_failed(done, item_name(item) + " 의 묶음 칸");
            }
            hung++;
            item.owners = block;
            done->housed++;
            done->written++;
        }
        if (!poke_bits(item.owners + byte, mask, action == Research::Complete, 1)) {
            release();
            return research_failed(done, item_name(item) + " 의 보유 묶음");
        }
        done->written++;
    }

    // 대기열에서 뺀다: 노드의 깃발 둘에 "뺐다"를 켠다(다른 비트는 그대로)
    for (int n : plan.nodes)
        for (uint32_t side = 0; side < 2; side++) {
            if (!poke_bits(shot.nodes[static_cast<size_t>(n)] + NODE_FLAGS + 4 * side, NODE_GONE, true, sizeof(uint32_t)))
                return research_failed(done, "연구 목록의 노드");
            done->written++;
        }

    // 기술의 효과는 지역마다 미리 계산해 둔 표로 쓰인다 — 기술의 보유가 바뀌었으면 플레이어 지역의 것을 다시 셈하게 한다
    if (!plan.techs.empty() && recompute != nullptr) {
        if (!guarded_recompute(recompute, reinterpret_cast<void *>(shot.world), shot.me, &done->code))
            return Wrote::Crashed;
        done->recomputed = true;
    }
    return Wrote::Done;
}

```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
    const unsigned long long took = GetTickCount64() - started;
```

이것을 더한다:

```cpp

    // 새 찾기: 연구 — 기술 · 부대 설계의 표, 지역별 연구 목록, 지역의 효과를 다시 셈하는 함수. 일곱을 모두, 서명도 셋씩 모두 맞아야 한다.
    // 값 묶음을 찾았으면 그 세계 자료 포인터와 겹치지 않아야 한다(겹치면 연구 묶음만 버린다)
    ResearchLayout research = {};
    char research_why[160] = "";
    const bool researching = state && locate_research(base, size, at, &research, nullptr, research_why, sizeof(research_why))
        && (!values || locate_research_fits(research, layout, research_why, sizeof(research_why)));
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
        memcpy(g_more_why, more_why, sizeof(g_more_why));
```

이것을 더한다:

```cpp
        g_research = research;
        g_research_found = researching;
        snprintf(g_research_why, sizeof(g_research_why), "%s", research_why);
        g_recompute = researching ? const_cast<uint8_t *>(base) + research.recompute : nullptr;
```

`native/srtoybox/game.cpp` 에서 다음 바로 앞에:

```cpp
    if (can_call)
```

이것을 더한다:

```cpp
    if (researching)
        log_line(write_wanted() ? "연구를 씁니다 (기술 표 +0x%X · 부대 설계 표 +0x%X · 연구 목록 +0x%X · 다시 셈 +0x%X)"
                                : "연구를 쓰지 않습니다 (SRTOYBOX_WRITE=0. 기술 표 +0x%X · 부대 설계 표 +0x%X · 연구 목록 +0x%X · 다시 셈 +0x%X)",
                 research.tech_table, research.design_table, research.lists, research.recompute);
    else
        log_line("연구를 쓸 수 없습니다 (%s)", research_why);
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
        snprintf(g_more_why[g], MORE_WHY, "값의 자리를 주지 않았습니다");
```

이것을 더한다:

```cpp
    g_research = ResearchLayout();
    g_research_found = false;
    g_recompute = nullptr;
    snprintf(g_research_why, sizeof(g_research_why), "연구의 자리를 주지 않았습니다");
}

void game_set_research_for_test(const ResearchLayout *layout, void *recompute)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_research = layout != nullptr ? *layout : ResearchLayout();
    g_research_found = layout != nullptr;
    g_recompute = layout != nullptr ? recompute : nullptr;
    g_write_failed = false;
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
    return slot < 0 ? Wrote::BadValue : write(slot, value);
```

이것을 더한다:

```cpp
}

std::string game_research_off()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return off_text(g_research_found, g_research_why);
}

bool game_research(int picked, ResearchTables *out, std::string *why)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ResearchLayout research = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !g_research_found || !reading_wanted()) {
            if (why != nullptr)
                *why = !g_located || !reading_wanted() ? "게임 상태를 읽을 수 없습니다" : g_research_why;
            return false;
        }
        base = g_base;
        at = g_at;
        research = g_research;
    }
    return read_research(base, at, research, picked, out, why);
}

Wrote game_write_research(Research action, const ResearchWhat &what, ResearchDone *done)
{
    *done = ResearchDone();
    if (!game_research_off().empty())
        return Wrote::Off;
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ResearchLayout research = {};
    Recompute recompute = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        base = g_base;
        at = g_at;
        research = g_research;
        recompute = reinterpret_cast<Recompute>(g_recompute);
    }
    const Wrote wrote = write_research(base, at, research, recompute, action, what, done);
    if (wrote == Wrote::Failed) {
        {
            std::lock_guard<std::mutex> lock(g_lock);
            g_write_failed = true;
        }
        if (done->written > 0)
            log_line("연구 쓰기 실패 (%s, %d칸 가운데 %d칸을 쓴 뒤) — 값 쓰기를 끕니다", done->why.c_str(), done->cells, done->written);
        else
            log_line("연구 쓰기 실패 (%s) — 값 쓰기를 끕니다", done->why.c_str());
    }
    return wrote;
```

`native/srtoybox/game.h` 에서 다음을 찾아:

```cpp
// 그 밖의 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다.
```

이렇게 바꾼다:

```cpp
//   연구(3단계 3): 기술 · 부대 설계의 보유 비트 묶음에서 플레이어의 비트, 묶음이 없는 항목의 포인터 칸(새 묶음을 걸 때),
//   플레이어의 연구 목록 노드의 깃발 두 칸.
// 그 밖의 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다. 기술 표와 부대 설계 표는 모든 나라가 함께 쓰는 표다 — 거기에 쓰는 것은
// 플레이어의 비트와, 플레이어의 비트 하나만 켜질 빈 묶음을 거는 것뿐이다(다른 나라의 비트 · 연구 기간 · 비용은 건드리지 않는다).
// 게임의 함수는 하나만 부른다: "지역의 효과를 다시 셈"(치트가 아니다 — 게임이 연구가 끝날 때 스스로 부르는 함수), 플레이어 지역에 대해서만.
```

`native/srtoybox/game.h` 에서 다음 바로 뒤에:

```cpp
#include "locate.h"
```

이것을 더한다:

```cpp
#include "research.h"
```

`native/srtoybox/game.h` 에서 다음을 찾아:

```cpp
    NoTarget,    // 그 번호의 나라가 이번 판에 없다(없는 번호, 사람도 AI 도 맡지 않은 지역, 플레이어 자신)
};
```

이렇게 바꾼다:

```cpp
    NoTarget,    // 그 번호의 나라가 이번 판에 없다(없는 번호, 사람도 AI 도 맡지 않은 지역, 플레이어 자신)
    Unreadable,  // (연구) 표나 연구 목록을 읽을 수 없다 — 꼴이 다른 게임일 수 있다. 쓰지 않았다
    Crashed,     // (연구) 비트는 썼는데 효과를 다시 셈하는 게임의 함수에서 예외가 났다 — 게임의 상태를 믿을 수 없다
};

// 연구를 쓴 결과(write_research).
struct ResearchDone {
    ResearchPlan plan;           // 바꾼 것(묶음을 만들 수 없어 건너뛴 항목은 빠져 있다)
    int housed = 0;              // 새로 만들어 건 보유 비트 묶음의 수
    int skipped = 0;             // 묶음을 만들 수 없어 건너뛴 항목의 수(아무도 보유하지 않은 항목)
    int cells = 0, written = 0;  // 쓰려던 칸의 수 · 쓴 칸의 수(비트 하나, 포인터 하나, 노드의 깃발 하나가 저마다 한 칸)
    bool recomputed = false;     // 플레이어 지역의 효과를 다시 셈했다
    unsigned long code = 0;      // 다시 셈에서 난 예외의 코드(Wrote::Crashed)
    std::string why;             // 읽지 못한 까닭(Wrote::Unreadable) · 쓰지 못한 곳(Wrote::Failed)
};

// 게임의 "지역의 효과를 다시 셈": 그 지역이 보유한 기술의 효과를 처음부터 다시 쌓는다. 다른 함수를 부르지 않는다(docs/11).
typedef void (*Recompute)(void *world, int index);
```

`native/srtoybox/game.h` 에서 다음 바로 앞에:

```cpp
void game_init();                  // 올라와 있는 실행 파일에서 주소와 자리를 찾는다(시작할 때 한 번). 결과를 로그에 적는다
```

이것을 더한다:

```cpp
// 연구의 표 둘과 플레이어의 연구 목록을 읽는다(행의 queued 까지 채운다). picked: 고른 나라의 번호 — 이번 판에 없거나 0 이면 행의
// picked 는 모두 false 다. 읽을 수 없으면 false 와 why: 게임을 진행 중이 아니다(일관성 포함) / 멀티플레이다 / 표의 자리 수가 2 … 65536 이
// 아니다 / 표 · 보유 묶음 · 연구 목록의 노드 가운데 읽을 수 없는 것이 있다 / 연구 목록이 4096 노드 안에 끝나지 않는다.
bool read_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, int picked, ResearchTables *out,
                   std::string *why);
// 연구를 완료 · 미완료로 바꾼다. 방금 읽은 표에 규칙(research_plan)을 돌려 바꿀 것을 정하고, 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다.
//   비트    보유 묶음의 (플레이어 인덱스 / 8)째 바이트에서 그 비트만, 원자적으로 — 같은 바이트의 다른 나라의 비트는 읽어서
//           되쓰지 않는다(그 순간 게임이 다른 나라의 연구를 끝내도 덮어쓰지 않는다).
//   묶음    완료로 바꿀 항목에 묶음이 없으면 프로세스 힙에서 OWNERS_BYTES 를 0 으로 받아 레코드의 포인터 칸에 건다(게임이 하는 그대로).
//           먼저 이미 있는 묶음 하나가 그 힙의 OWNERS_BYTES 짜리 블록인지 본다 — 아니면 만들지 않고 그 항목들을 건너뛴다(skipped).
//   노드    대기열에서 뺄 노드의 깃발 둘에 NODE_GONE 을 켠다(게임이 연구를 끝낼 때 하는 그대로). 그 비트만, 원자적으로.
//   다시 셈 기술의 비트를 하나라도 바꿨으면 끝에 recompute(세계 객체, 플레이어 인덱스)를 한 번 부른다. -1(모든 지역)로는 부르지 않는다.
// 순서는 칸의 확인 → 묶음 → 비트 → 노드 → 다시 셈. 도중에 쓰기가 실패하면 거기서 멈춘다(Wrote::Failed. 앞서 쓴 것은 되돌리지 않고
// 다시 셈도 부르지 않는다). 바꿀 것이 없어도 Wrote::Done 이다(done->plan 이 비어 있다).
Wrote write_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, Recompute recompute, Research action,
                     const ResearchWhat &what, ResearchDone *done);

```

`native/srtoybox/game.h` 에서 다음 바로 앞에:

```cpp
// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
```

이것을 더한다:

```cpp
// 연구를 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글. 다른 묶음과 따로다.
std::string game_research_off();
// 지금의 연구의 표(read_research). 연구 묶음을 못 찾았으면 false 와 그 까닭.
bool game_research(int picked, ResearchTables *out, std::string *why);
// 연구를 완료 · 미완료로 바꾼다(write_research). 쓰기가 실패하면(Wrote::Failed) 값 쓰기 전체를 끄고 로그에 적는다 — 그 뒤로는 Wrote::Off 다.
// Wrote::Crashed 는 부른 쪽이 처리한다(오류 가드를 건다 — runner_win.h).
Wrote game_write_research(Research action, const ResearchWhat &what, ResearchDone *done);

```

`native/srtoybox/game.h` 에서 다음 바로 뒤에:

```cpp
void game_set_more_for_test(const MoreLayout *layout);
```

이것을 더한다:

```cpp
// 연구의 자리와 "다시 셈" 자리에 둘 함수를 준다(layout 의 recompute 는 보지 않는다). nullptr 이면 못 찾은 것으로.
void game_set_research_for_test(const ResearchLayout *layout, void *recompute);
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_research.py tests/test_toybox_values.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `147 passed`

(테스트 출력의 `Windows fatal exception: access violation` 줄은 일부러 읽을 수 없는 주소를 준 테스트에서 pytest 의 faulthandler 가 적는 것이다 — ToyBox 가 그 예외를 잡았다. 실패가 아니다.)

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/game.h native/srtoybox/game.cpp native/srtoybox/exports.cpp tests/test_toybox_research.py tests/toybox_fake_game.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox 연구의 읽기와 쓰기 — 플레이어의 보유 비트, 새 묶음, 대기열의 노드, 효과를 다시 셈

- read_research: 기술 · 부대 설계의 표와 플레이어의 연구 목록을 읽는다(읽을 수 없는 주소 · 말이 안 되는 자리 수 · 끝나지 않는 목록은 까닭과 함께 거절).
- write_research: 방금 읽은 표에 규칙을 돌려 바꿀 것을 정하고, 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본 뒤에 쓴다.
  비트는 플레이어의 것만, 원자적으로(같은 바이트의 다른 나라의 비트는 건드리지 않는다). 아무도 보유하지 않던 항목에는 게임처럼
  프로세스 힙의 128바이트를 건다 — 게임의 묶음이 그 힙의 그 크기일 때만. 대기열에서 뺄 노드에는 게임이 연구를 끝낼 때의 깃발을 켠다.
- 기술의 보유가 바뀌었으면 끝에 게임의 "효과를 다시 셈"을 플레이어 지역으로 한 번 부른다(예외 가드 안에서. -1 로는 부르지 않는다).
- 쓰는 곳이 늘어난다(game.h 의 머리말). 기술의 연구 기간 · 다른 나라의 비트에는 쓰지 않는다 — 테스트가 바이트로 본다.
- 시작할 때 연구 묶음을 찾고 로그에 적는다. 못 찾아도 다른 기능은 그대로다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `534 passed`, 새 커밋.

---

### Task 5: 연구 요청의 줄 — 창이 넣고 타이머가 쓴다

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Modify: `native/srtoybox/runner_win.h`, `native/srtoybox/runner_win.cpp`, `native/srtoybox/keeper.h`, `native/srtoybox/keeper.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_research.py`

**Interfaces:**
- Consumes: Task 4 의 `game_write_research` · `game_research_off` · `ResearchDone` · `Wrote::Unreadable` · `Wrote::Crashed`, Task 3 의 `research_summary` · `ResearchWhat` · `Research`. `keeper.cpp` 의 `drain` · `keep_check` · `g_queue` · `g_last` · `g_notice` · `LEFT_GAME`, `runner_win.cpp` 의 `g_calling` · `g_faulted` · `g_runner` · `g_notice`. `exports.cpp` 의 `what_from`(Task 3).
- Produces:
  - `bool runner_enter_call()` — 오류 가드가 걸렸거나 이미 게임의 함수 안이면 false. true 를 받았으면 반드시 `runner_leave_call` 로 나온다.
  - `void runner_leave_call(const char *what, unsigned long code)` — `what` 이 `nullptr` 이면 탈 없이 나왔다. 아니면 오류 가드를 건다: 알림 `<what> 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.`, 로그 `<what> 중 예외 0x… — ToyBox 를 멈춥니다`.
  - `void runner_reset_for_test()`.
  - `struct ResearchRequest { Research action; ResearchWhat what; std::string label; }`, `const size_t RESEARCH_QUEUE = 4`, `bool keeper_enqueue_research(const ResearchRequest &request)`(가득 찼거나 연구를 쓸 수 없으면 false).
  - `keeper_tick` 이 값 요청을 비우고 유지를 본 뒤 연구 요청을 **하나** 쓴다 — `keeper` 의 잠금을 놓고.
  - 알림과 로그: `마지막으로 쓴 값` 에 `기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열` / `대기열에서 1개를 뺌 — 대기열`, 알림에 `바꿀 것이 없습니다 — <이름>` / `묶음을 만들 수 없는 게임 판입니다 — 보유한 나라가 없는 항목 N개를 건너뜁니다` / `연구의 표를 읽을 수 없습니다 (<무엇>)`, 로그에 `연구 완료 (<이름>): <요약>[ · 새 묶음 N개]` · `연구 미완료 (<이름>): <요약>` · `연구 완료 (<이름>): 바꿀 것이 없습니다`.
  - 내보내기(테스트): `srtoybox_keeper_research(int action, const char *what, const char *label)`(1 받았다 / 0 받지 못했다 / -1 그런 요청이 없다), `srtoybox_runner_text(char *out, int size)`(`<오류 가드 0/1>\t<게임의 함수 안 0/1>\t<알림>`), `srtoybox_keeper_reset` 이 실행기의 오류 가드와 깃발도 지운다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

이 프로세스의 "게임"을 `standard_lab` 으로 두고 요청을 넣어 틱을 돌린다. "다시 셈" 자리의 함수는 불린 인자를 적고, 그 안에서 시킨 일(다시 온 틱 · 단추)을 한다.

<!-- 고칠 곳: test -->
`tests/test_toybox_research.py` 에서 다음 바로 뒤에:

```python
    assert flags == 0 and off == "게임 상태를 읽을 수 있을 때만 씁니다." and not any("연구" in line for line in log)
```

이것을 더한다:

```python


# ---------------------------------------------------------------------------------------------------------------------
# 연구 요청의 줄(keeper): 창의 단추가 넣고, 게임 창의 타이머가 하나씩 쓴다

LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다."
FAULT = "효과를 다시 셈하는 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오."


class Playing:
    """이 프로세스의 "게임"이 lab() 인 동안. "다시 셈" 자리의 함수는 불린 인자를 calls 에 적고, inside 에 든 일을 그 안에서 한다."""

    def __init__(self, lib, home):
        self.lib, self.home = lib, home
        self.fake, self.lab = lab()
        self.calls: list[tuple[int, int]] = []
        self.inside: list = []
        self.hook = RECOMPUTE(self._recompute)

    def _recompute(self, world: int, index: int) -> None:
        self.calls.append((world, index))
        for act in self.inside:
            act()

    def ask(self, what: str, label: str, action: int = COMPLETE) -> int:
        return self.lib.srtoybox_keeper_research(action, what.encode(), label.encode())

    def tick(self) -> None:
        self.lib.srtoybox_keeper_tick()

    def told(self) -> tuple[str, str]:
        """(창 바닥의 "마지막으로 쓴 값", 알림)."""
        last, notice = text(self.lib.srtoybox_keeper_text).split("\t")
        return last, notice

    def runner(self) -> tuple[str, str, str]:
        """(오류 가드가 걸렸는가, 게임의 함수 안인가, 빨간 경고의 글)."""
        faulted, calling, notice = text(self.lib.srtoybox_runner_text).split("\t")
        return faulted, calling, notice

    def log(self) -> list[str]:
        path = self.home / "toybox.log"
        return [line.split(" ", 2)[2] for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

    def mine(self) -> tuple[list[int], list[int]]:
        """독일이 보유한 (기술, 부대 설계)."""
        return self.lab.held(TECH, 64, GERMANY), self.lab.held(DESIGN, 64, GERMANY)


@pytest.fixture
def playing(lib, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    lib.srtoybox_test_game.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.srtoybox_research_off.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_keeper_research.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
    lib.srtoybox_keeper_text.argtypes = lib.srtoybox_runner_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
    game = Playing(lib, tmp_path)
    lib.srtoybox_test_game(game.fake.base, ctypes.byref(game.fake.at), None)
    lib.srtoybox_test_research(ctypes.byref(game.lab.layout), ctypes.cast(game.hook, ctypes.c_void_p))
    lib.srtoybox_keeper_reset()
    yield game
    lib.srtoybox_keeper_reset()                              # 오류 가드도 지운다 — 다음 테스트는 멈추지 않은 ToyBox 에서 시작한다
    lib.srtoybox_test_game(None, None, None)


MINE = ([1, 4, 6], [10, 13, 14])                             # lab() 에서 독일이 보유한 것


def test_research_requests_are_written_one_per_tick_in_order(playing):
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    assert playing.mine() == MINE and playing.calls == []     # 누른 것만으로는 쓰지 않는다 — 창 스레드의 틱에서 쓴다
    playing.tick()
    assert playing.mine() == ([1, 2, 3, 4, 6], [10, 11, 13, 14])
    assert playing.told() == ("기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열", "")
    assert playing.calls == [(playing.lab.world, GERMANY)]
    playing.tick()                                            # 다음 요청은 다음 틱에
    assert playing.mine() == ([1, 2, 3, 4, 6, 7], [10, 11, 13, 14])
    assert playing.told() == ("기술 1개를 완료로 — 기술 수준 70 이하", "")
    playing.tick()
    assert len(playing.calls) == 2 and playing.runner() == ("0", "0", "")
    assert playing.log() == ["연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개",
                             "연구 완료 (기술 수준 70 이하): 기술 1개"]
    assert playing.lab.owners(TECH, 7) == {DENMARK, GERMANY} and playing.lab.owners(DESIGN, 11) == {POLAND, GERMANY}   # 다른 나라는 그대로다


def test_a_request_that_changes_nothing_says_so(playing):
    """대기열이 비었을 때의 "대기열의 연구 즉시 완료": 한 칸도 쓰지 않고, 게임의 함수도 부르지 않고, 그렇다고 알린다."""
    assert playing.ask("items t1 d10", "고른 것") == 1
    before = playing.lab.everything()
    playing.tick()
    assert playing.told() == ("", "바꿀 것이 없습니다 — 고른 것") and playing.calls == [] and playing.lab.everything() == before
    assert playing.log() == ["연구 완료 (고른 것): 바꿀 것이 없습니다"]


def test_a_queued_item_that_is_already_held_is_only_cleared_from_the_queue(playing):
    """내장 치트로 "끝낸" 판에는 보유한 기술의 노드가 대기열에 남아 있다 — 그 노드만 뺀다. 비트를 바꾸지 않았으니 다시 셈도 없다."""
    head = RESEARCH["world"] + RESEARCH["lists"] + GERMANY * 24
    playing.lab.nodes.clear()
    playing.fake.poke(head, "<Q", 0)                          # 독일의 대기열을 비우고
    playing.fake.poke(head + 8, "<Q", 0)
    held = playing.lab.queue(GERMANY, TECH, 1, flags=(1, ENDED))
    assert playing.ask("queue", "대기열") == 1
    playing.tick()
    assert playing.told() == ("대기열에서 1개를 뺌 — 대기열", "") and playing.calls == [] and playing.mine() == MINE
    assert playing.lab.flags(held) == (GONE | 1, GONE | ENDED) and playing.log() == ["연구 완료 (대기열): 대기열에서 1개"]


def test_revoking_is_requested_the_same_way(playing):
    assert playing.ask("items t4", "고른 것", REVOKE) == 1
    playing.tick()
    assert playing.mine() == ([1], [10, 14])
    assert playing.told() == ("기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)를 미완료로 — 고른 것", "")
    assert playing.log() == ["연구 미완료 (고른 것): 기술 2개(딸린 것 1개 포함) · 부대 설계 1개(딸린 것 1개 포함)"]
    assert playing.lab.owners(TECH, 4) == {DENMARK} and playing.lab.owners(DESIGN, 13) == {POLAND}


def test_value_requests_of_the_tick_are_written_before_its_research_request(lib, playing):
    """틱마다 값 요청을 먼저 비우고, 그 뒤에 연구 요청을 하나 쓴다."""
    lib.srtoybox_test_values.argtypes = [ctypes.c_void_p]
    lib.srtoybox_keeper_request.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
    lib.srtoybox_test_values(ctypes.byref(playing.fake.layout))
    seen: list[float] = []
    playing.inside.append(lambda: seen.append(playing.fake.treasury(GERMANY)))
    assert playing.ask("queue", "대기열") == 1 and lib.srtoybox_keeper_request(-1, 1, 100.0) == 1      # 국고를 100 으로
    playing.tick()
    assert seen == [100.0]                                    # 게임의 함수가 불렸을 때 국고는 이미 쓰여 있었다
    assert playing.log() == ["값 쓰기: 국고 0 -> 100", "연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개"]
    assert playing.told() == ("기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열", "")


def test_only_four_research_requests_wait(playing):
    assert [playing.ask("queue", "대기열") for _ in range(5)] == [1, 1, 1, 1, 0]
    playing.tick()
    assert playing.ask("queue", "대기열") == 1                 # 하나가 처리됐다
    assert playing.ask("bogus", "대기열", action=2) == -1


@pytest.mark.parametrize("leave", ["menu", "multiplayer"])
def test_research_requests_are_dropped_outside_a_game(playing, leave):
    """누른 뒤 쓰기 전에 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다."""
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    before = playing.lab.everything()
    if leave == "menu":
        playing.fake.menu()
    else:
        playing.fake.poke(MULTIPLAYER, "<B", 1)
    playing.tick()
    assert playing.told() == ("", LEFT_GAME) and playing.calls == []
    if leave == "menu":
        playing.fake.play(GERMANY)
    else:
        playing.fake.poke(MULTIPLAYER, "<B", 0)
    playing.tick()
    assert playing.lab.everything() == before and playing.calls == [] and playing.log() == []


def test_a_tick_that_comes_back_inside_the_games_function_does_nothing(playing):
    """게임의 함수가 일하는 동안 ToyBox 의 타이머가 다시 올 수 있다(게임이 메시지를 돌릴 때) — 그 안에서는 쓰지도 부르지도 않는다.
    그 안에서 누른 단추의 요청은 받아 두었다가 다음 틱에 쓴다."""
    seen: list = []

    def reenter() -> None:
        seen.append(playing.runner()[1])
        playing.tick()                                        # 그 안에서 다시 온 틱
        seen.append((playing.mine(), len(playing.calls)))
        seen.append(playing.ask("items d12", "고른 것"))

    playing.inside.append(reenter)
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    playing.tick()
    assert seen == ["1", (([1, 2, 3, 4, 6], [10, 11, 13, 14]), 1), 1]      # 수준 70 의 요청은 그 안에서 쓰이지 않았다
    assert playing.runner() == ("0", "0", "")
    playing.inside.clear()
    playing.tick()
    playing.tick()
    assert playing.mine() == ([1, 2, 3, 4, 6, 7], [10, 11, 12, 13, 14]) and len(playing.calls) == 2      # 설계 12 만으로는 부르지 않는다


def test_a_fault_in_the_games_function_stops_toybox(lib, playing):
    """"효과를 다시 셈"에서 예외가 나면 게임의 상태를 믿을 수 없다 — 직접 실행의 오류와 같이 ToyBox 를 멈춘다:
    빨간 경고를 띄우고, 그 뒤로는 아무것도 쓰지도 부르지도 않는다."""
    lib.srtoybox_test_research(ctypes.byref(playing.lab.layout), ctypes.c_void_p(8))      # 부를 수 없는 주소
    assert playing.ask("queue", "대기열") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    playing.tick()
    assert playing.runner() == ("1", "0", FAULT)
    assert playing.log() == ["효과를 다시 셈하는 중 예외 0xC0000005 — ToyBox 를 멈춥니다"]
    after = playing.lab.everything()
    playing.tick()
    playing.ask("level 70", "기술 수준 70 이하")
    playing.tick()
    assert playing.lab.everything() == after and playing.told() == ("", "")
    assert playing.lab.held(TECH, 64, GERMANY) == [1, 2, 3, 4, 6]      # 비트는 예외가 나기 전에 썼다. 수준 70 의 요청은 버려졌다


def test_a_table_that_cannot_be_read_is_reported_and_nothing_is_written(playing):
    assert playing.ask("queue", "대기열") == 1
    playing.fake.poke(RESEARCH["tech_count"], "<i", 1)        # 표의 꼴이 다른 게임
    before = playing.lab.everything()
    playing.tick()
    why = "연구의 표를 읽을 수 없습니다 (표가 없거나 자리 수가 범위 밖입니다)"
    assert playing.told() == ("", why) and playing.log() == [why] and playing.calls == [] and playing.lab.everything() == before


def test_a_failed_write_turns_writing_off(lib, playing):
    """쓸 수 없는 칸을 만나면 한 칸도 쓰지 않고, 그 뒤로는 값 쓰기 전체를 끈다 — 까닭은 단추의 자리에 보인다."""
    playing.lab.house(TECH, 2, block=locked_page())           # 기술 2 의 묶음이 읽기 전용 쪽에 있다
    assert playing.ask("items t3", "고른 것") == 1 and playing.ask("level 70", "기술 수준 70 이하") == 1
    before = playing.lab.everything()
    playing.tick()
    playing.tick()
    assert playing.lab.everything() == before and playing.calls == [] and playing.told() == ("", "")
    assert playing.log() == ["연구 쓰기 실패 (기술 2 의 보유 묶음) — 값 쓰기를 끕니다"]
    assert not lib.srtoybox_game_flags() & CAN_RESEARCH and text(lib.srtoybox_research_off) != ""
    assert playing.ask("level 70", "기술 수준 70 이하") == 0     # 더 받지 않는다


def test_items_nobody_holds_are_skipped_and_counted_when_a_set_cannot_be_made(playing):
    pool = (ctypes.c_ubyte * 0x4000)()
    used = iter(range(0, 0x4000, 0x100))
    rehouse(playing.lab, lambda: ctypes.addressof(pool) + next(used))      # 게임의 묶음이 프로세스 힙의 것이 아니다
    skipped = "묶음을 만들 수 없는 게임 판입니다 — 보유한 나라가 없는 항목 {}개를 건너뜁니다"
    assert playing.ask("items t3 d12 t7", "고른 것") == 1 and playing.ask("items t3", "보이는 것") == 1
    playing.tick()
    assert playing.told() == ("기술 1개를 완료로 — 고른 것", skipped.format(2)) and playing.mine() == ([1, 4, 6, 7], MINE[1])
    playing.tick()
    assert playing.told() == ("기술 1개를 완료로 — 고른 것", skipped.format(1))
    assert playing.log() == [skipped.format(2), "연구 완료 (고른 것): 기술 1개", skipped.format(1)]
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_research.py -q 2>&1 | tail -4`

Expected: `64 passed, 13 errors` — 새 테스트 13개가 fixture(`playing`)에서 `AttributeError: function 'srtoybox_keeper_research' not found` 로 오류가 난다.

- [ ] **Step 3: 구현한다**

`keeper_tick` 을 둘로 나눈다 — 잠금 안의 앞쪽(`tick_locked`: 값 요청 · 유지, 그리고 이번 틱에 쓸 연구 요청 하나를 꺼내며 "게임의 함수 안" 깃발을 세운다)과 잠금 밖의 `run_research`.

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
#include "settings.h"
```

이것을 더한다:

```cpp
#include "runner_win.h"
```

`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
EXPORT void srtoybox_keeper_tick(void)
```

이것을 더한다:

```cpp
// 테스트: 연구 요청(keeper.h). action: 0 완료, 1 미완료. what: "items t1 d5" · "level 120" · "queue"(what_from).
// label: 알림과 로그에 적을 이름. 받았으면 1, 받지 못했으면 0(가득 찼다 · 연구를 쓸 수 없다). 그런 요청이 없으면 -1.
EXPORT int srtoybox_keeper_research(int action, const char *what, const char *label)
{
    if (action < 0 || action > 1 || what == nullptr || label == nullptr)
        return -1;
    return keeper_enqueue_research({action == 0 ? Research::Complete : Research::Revoke, what_from(what), label}) ? 1 : 0;
}

```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
EXPORT void srtoybox_keeper_reset(void)
{
    keeper_reset_for_test();
```

이렇게 바꾼다:

```cpp
// 테스트: keeper 와, 그것이 함께 쓰는 실행기의 오류 가드 · "게임의 함수 안" 깃발을 지운다.
EXPORT void srtoybox_keeper_reset(void)
{
    keeper_reset_for_test();
    runner_reset_for_test();
}

// 테스트: "<오류 가드가 걸렸는가 0/1>\t<게임의 함수 안인가 0/1>\t<실행기의 알림>".
EXPORT int srtoybox_runner_text(char *out, int size)
{
    return put(std::string(runner_faulted() ? "1" : "0") + '\t' + (runner_calling() ? "1" : "0") + '\t' + runner_notice(), out, size);
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
std::string g_last, g_notice;
```

이것을 더한다:

```cpp
std::deque<ResearchRequest> g_research;     // 연구 요청은 따로 줄을 선다 — 틱마다 값 요청을 비운 뒤 하나
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
}  // namespace
```

이것을 더한다:

```cpp
// 틱의 앞쪽: 값 요청을 비우고, 때가 됐으면 유지를 본다. 이번 틱에 처리할 연구 요청이 있으면 *next 에 꺼내고 true —
// 그때는 "게임의 함수 안" 깃발을 세워 둔다(부른 쪽이 runner_leave_call 로 내린다). g_lock 을 쥔 채로 부른다.
bool tick_locked(unsigned long long now_ms, ResearchRequest *next)
{
    if (runner_calling())
        return false;                          // 게임의 함수 안에서 다시 온 틱이면 기다린다 — 그 함수가 읽고 있는 값을 바꾸지 않는다
    const bool due = keep_count(g_keep) > 0 && (g_keep_due || now_ms - g_keep_at >= KEEP_EVERY_MS);
    if (g_queue.empty() && g_research.empty() && !due)
        return false;
    if (due) {                                 // 쓰든 쉬든, 다음에 보는 것은 지금부터 0.5초 뒤다
        g_keep_due = false;
        g_keep_at = now_ms;
    }
    const GameState game = game_state();
    if (runner_faulted() || !game_writes()) {
        g_queue.clear();                       // 까닭은 창이 보인다(빨간 경고, 탭의 한 줄). 유지도 쉰다
        g_research.clear();
        return false;
    }
    if (!game.known || !game.in_game || game.multiplayer) {
        if (!g_queue.empty() || !g_research.empty()) {
            g_queue.clear();                   // 누른 뒤 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다
            g_research.clear();
            g_notice = LEFT_GAME;
        }
        return false;                          // 유지는 게임 밖 · 멀티플레이에서 쉰다
    }
    const bool values = !g_queue.empty();
    if (values && !drain()) {
        g_research.clear();                    // 값 쓰기가 꺼졌다 — 연구도 쓰지 않는다
        return false;
    }
    if (due && game_values_off().empty())      // 유지는 국고와 물자다 — 그 자리를 못 찾은 게임에서는 쉰다
        keep_check();                          // 단추의 요청을 쓴 뒤에 본다 — 방금 내린 값도 바닥 아래면 올린다
    if (g_research.empty() || !runner_enter_call())
        return false;
    if (!values)
        g_notice.clear();                      // 이번 틱에 쓴 값 요청의 알림은 남긴다 — 연구의 알림이 생기면 그것이 덮는다
    *next = g_research.front();
    g_research.pop_front();
    return true;
}

// 연구 요청 하나를 쓴다. g_lock 을 쥐지 않은 채로 부른다 — 끝에 게임의 "효과를 다시 셈"이 불리고, 그 함수가 안에서
// ToyBox 로 되돌아오면(타이머 · 단추) 그것들이 g_lock 을 잡는다. "게임의 함수 안" 깃발은 tick_locked 가 세워 뒀다.
void run_research(const ResearchRequest &r)
{
    ResearchDone done;
    const Wrote wrote = game_write_research(r.action, r.what, &done);
    runner_leave_call(wrote == Wrote::Crashed ? "효과를 다시 셈하는" : nullptr, done.code);

    std::lock_guard<std::mutex> lock(g_lock);
    const char *const verb = r.action == Research::Complete ? "완료" : "미완료";
    if (wrote == Wrote::NotInGame) {           // 읽은 뒤 쓰기 전에 게임이 바뀌었다
        g_notice = LEFT_GAME;
        return;
    }
    if (wrote == Wrote::Unreadable) {
        g_notice = "연구의 표를 읽을 수 없습니다 (" + done.why + ")";
        log_line("%s", g_notice.c_str());
        return;
    }
    if (wrote != Wrote::Done) {                // 실패 · 꺼짐 · 예외: 까닭은 그 단추의 자리와 빨간 경고에 보인다. 남은 요청을 버린다
        g_queue.clear();
        g_research.clear();
        return;
    }
    const std::string skipped = done.skipped == 0 ? std::string()
        : "묶음을 만들 수 없는 게임 판입니다 — 보유한 나라가 없는 항목 " + std::to_string(done.skipped) + "개를 건너뜁니다";
    if (!skipped.empty()) {
        g_notice = skipped;
        log_line("%s", skipped.c_str());
    }
    const std::string summary = research_summary(done.plan, r.action);
    if (summary.empty()) {
        if (skipped.empty()) {
            g_notice = "바꿀 것이 없습니다 — " + r.label;
            log_line("연구 %s (%s): 바꿀 것이 없습니다", verb, r.label.c_str());
        }
        return;
    }
    ResearchPlan bits = done.plan;             // 창의 한 줄에는 바뀐 기술 · 부대 설계만 적는다
    bits.nodes.clear();
    const std::string changed = research_summary(bits, r.action);
    g_last = (changed.empty() ? "대기열에서 " + std::to_string(done.plan.nodes.size()) + "개를 뺌" : changed + "를 " + verb + "로")
        + " — " + r.label;
    log_line("연구 %s (%s): %s%s", verb, r.label.c_str(), summary.c_str(),
             done.housed > 0 ? (" · 새 묶음 " + std::to_string(done.housed) + "개").c_str() : "");
}

```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
void keeper_tick(unsigned long long now_ms)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (runner_calling())
        return;                                // 게임의 함수 안에서 다시 온 틱이면 기다린다 — 그 함수가 읽고 있는 값을 바꾸지 않는다
    const bool due = keep_count(g_keep) > 0 && (g_keep_due || now_ms - g_keep_at >= KEEP_EVERY_MS);
    if (g_queue.empty() && !due)
        return;
    if (due) {                                 // 쓰든 쉬든, 다음에 보는 것은 지금부터 0.5초 뒤다
        g_keep_due = false;
        g_keep_at = now_ms;
    }
    const GameState game = game_state();
    if (runner_faulted() || !game_writes()) {
        g_queue.clear();                       // 까닭은 창이 보인다(빨간 경고, 탭의 한 줄). 유지도 쉰다
        return;
    }
    if (!game.known || !game.in_game || game.multiplayer) {
        if (!g_queue.empty()) {
            g_queue.clear();                   // 누른 뒤 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다
            g_notice = LEFT_GAME;
        }
        return;                                // 유지는 게임 밖 · 멀티플레이에서 쉰다
    }
    if (!g_queue.empty() && !drain())
        return;
    if (due && game_values_off().empty())      // 유지는 국고와 물자다 — 그 자리를 못 찾은 게임에서는 쉰다
        keep_check();                          // 단추의 요청을 쓴 뒤에 본다 — 방금 내린 값도 바닥 아래면 올린다
```

이렇게 바꾼다:

```cpp
bool keeper_enqueue_research(const ResearchRequest &request)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_research.size() >= RESEARCH_QUEUE || !game_research_off().empty())
        return false;
    g_research.push_back(request);
    return true;
}

void keeper_tick(unsigned long long now_ms)
{
    ResearchRequest research;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!tick_locked(now_ms, &research))
            return;
    }
    run_research(research);
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
    g_last.clear();
```

이것을 더한다:

```cpp
    g_research.clear();
```

`native/srtoybox/keeper.h` 에서 다음 바로 앞에:

```cpp
#pragma once
```

이것을 더한다:

```cpp
// 연구 요청(3단계 3)은 따로 줄을 선다 — 기술 · 부대 설계를 완료 · 미완료로 바꾸고, 게임의 "효과를 다시 셈"을 부른다.
```

`native/srtoybox/keeper.h` 에서 다음 바로 앞에:

```cpp
#include "values.h"
```

이것을 더한다:

```cpp
#include "research.h"
```

`native/srtoybox/keeper.h` 에서 다음 바로 앞에:

```cpp
// 최소 유지: 켜진 항목이 바닥보다 작아지면 바닥으로 올린다. KEEP_EVERY_MS 마다 보고, 설정 창이 닫혀 있어도 돈다.
```

이것을 더한다:

```cpp
// 연구 요청: 무엇을(what) 완료로 · 미완료로(action). 쓸 때 그때의 표를 다시 읽어 규칙(research.h)으로 바꿀 것을 정한다.
struct ResearchRequest {
    Research action;
    ResearchWhat what;
    std::string label;                         // 알림과 로그에 적을 이름: "고른 것" · "보이는 것" · "기술 수준 120 이하" · "대기열"
};

const size_t RESEARCH_QUEUE = 4;               // 기다리는 연구 요청은 이것까지

```

`native/srtoybox/keeper.h` 에서 다음을 찾아:

```cpp
// 대기열을 비우고, 때가 됐으면 유지를 본다. 게임 창을 가진 스레드에서 부른다(now_ms: 흐르는 시계, 밀리초).
// 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고 유지는 쉰다.
// 게임의 명령 처리 함수(옮기지 않은 기능의 직접 실행) 안에서 다시 온 틱이면 아무것도 하지 않는다.
void keeper_tick(unsigned long long now_ms);
// 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개" · "기술 수준 130 -> 131" ·
// "세계 시장 여론 최고" · "관계 최고 — 폴란드 (1106)". 없으면 빈 글
```

이렇게 바꾼다:

```cpp
// 받지 못하면 false: 가득 찼다(RESEARCH_QUEUE), 연구를 쓸 수 없다(game_research_off)
bool keeper_enqueue_research(const ResearchRequest &request);
// 대기열을 비우고, 때가 됐으면 유지를 보고, 연구 요청을 하나 처리한다. 게임 창을 가진 스레드에서 부른다(now_ms: 흐르는 시계, 밀리초).
// 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고 유지는 쉰다.
// 게임의 함수(옮기지 않은 기능의 직접 실행, 연구의 "효과를 다시 셈") 안에서 다시 온 틱이면 아무것도 하지 않는다.
// 연구 요청은 keeper 의 잠금을 놓고 처리한다 — 게임의 함수가 안에서 ToyBox 로 되돌아와도(타이머 · 단추) 서로 기다리지 않는다.
// 그 함수에서 예외가 나면 오류 가드를 건다(runner_win.h): 그 뒤로 ToyBox 는 아무것도 실행하지도 쓰지도 않는다.
void keeper_tick(unsigned long long now_ms);
// 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개" · "기술 수준 130 -> 131" ·
// "세계 시장 여론 최고" · "관계 최고 — 폴란드 (1106)" · "기술 12개(선행 5개 포함) · 부대 설계 1개를 완료로 — 대기열" ·
// "대기열에서 2개를 뺌 — 대기열". 없으면 빈 글
```

`native/srtoybox/runner_win.cpp` 에서 다음 바로 뒤에:

```cpp
    return direct_wanted() && game_can_call();
```

이것을 더한다:

```cpp
}

bool runner_enter_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_faulted || g_calling)
        return false;
    g_calling = true;
    return true;
}

void runner_leave_call(const char *what, unsigned long code)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_calling = false;
    if (what == nullptr)
        return;
    // 게임의 상태가 어긋났을 수 있다. 더 실행하지도 쓰지도 않는다 — 직접 실행의 오류와 같다
    g_faulted = true;
    g_runner.clear();
    g_notice = std::string(what) + " 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.";
    log_line("%s 중 예외 0x%08lX — ToyBox 를 멈춥니다", what, code);
}

void runner_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_runner.clear();
    g_notice.clear();
    g_faulted = false;
    g_calling = false;
```

`native/srtoybox/runner_win.h` 에서 다음을 찾아:

```cpp
bool runner_faulted();                             // 직접 실행 중 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 실행하지 않는다
bool runner_calling();                             // 지금 게임의 명령 처리 함수 안이다 — 그동안 ToyBox 는 게임의 메모리에 쓰지 않는다
bool runner_direct();                              // 명령을 게임의 함수에 바로 넘기는가(아니면 글쇠 방식)
```

이렇게 바꾼다:

```cpp
bool runner_faulted();                             // 게임의 함수 안에서 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 실행하지도 쓰지도 않는다
bool runner_calling();                             // 지금 게임의 함수 안이다 — 그동안 ToyBox 는 게임의 메모리에 쓰지 않는다
bool runner_direct();                              // 명령을 게임의 함수에 바로 넘기는가(아니면 글쇠 방식)

// ToyBox 가 게임의 함수를 스스로 부를 때(연구의 "효과를 다시 셈" — keeper.cpp)의 겹침 방지와 오류 가드.
// 직접 실행과 한 쌍의 깃발을 쓴다: 한쪽이 게임의 함수 안이면 다른 쪽은 시작하지 않고, 한쪽에서 예외가 나면 둘 다 멈춘다.
// 들어갈 수 없으면 false(오류 가드가 걸렸다 · 이미 게임의 함수 안이다). true 를 받았으면 반드시 runner_leave_call 로 나온다.
bool runner_enter_call();
// what 이 nullptr 이면 탈 없이 나왔다. 아니면 그 일을 하다 예외(code)가 났다 — 오류 가드를 건다.
// what 은 "효과를 다시 셈하는" 처럼 "… 중 오류가 났습니다" 의 앞에 놓일 말이다.
void runner_leave_call(const char *what, unsigned long code);
void runner_reset_for_test();                      // 테스트: 대기열 · 알림 · 오류 가드 · 깃발을 지운다
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_research.py tests/test_toybox_values.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `160 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/runner_win.h native/srtoybox/runner_win.cpp native/srtoybox/keeper.h native/srtoybox/keeper.cpp native/srtoybox/exports.cpp tests/test_toybox_research.py && git commit -q -F - <<'EOF'
feat: ToyBox 연구 요청의 줄 — 창이 넣고 게임 창의 타이머가 하나씩 쓴다

- keeper: 연구 요청은 값 요청과 따로 줄을 선다(4개까지). 틱마다 값 요청을 비우고 유지를 본 뒤 하나를 쓴다.
  게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버린다.
- 요청은 keeper 의 잠금을 놓고 쓴다 — 끝에 게임의 함수가 불리고, 그 안에서 다시 온 타이머 · 단추가 서로 기다리지 않게.
- runner_enter_call · runner_leave_call: ToyBox 가 게임의 함수를 스스로 부를 때의 겹침 방지와 오류 가드. 직접 실행과 한 쌍의
  깃발을 쓴다 — 한쪽이 게임의 함수 안이면 다른 쪽은 시작하지 않고, 예외가 나면 둘 다 멈춘다(빨간 경고).
- 알림과 로그: 무엇을 몇 개 바꿨는가(선행 · 딸린 것 · 대기열 · 새 묶음), 바꿀 것이 없다, 묶음을 만들 수 없어 건너뛴 수.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `547 passed`, 새 커밋.

---

### Task 6: 연구 탭의 두 줄을 직접 쓰기로

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Modify: `native/srtoybox/features.h`, `native/srtoybox/features.cpp`, `native/srtoybox/ui.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox.py`, `tests/toybox_overlay_probe.py`

**Interfaces:**
- Consumes: Task 5 의 `keeper_enqueue_research` · `ResearchRequest`, Task 4 의 `game_research_off` · `srtoybox_test_research`, `toybox_fake_game.standard_lab`. `ui.cpp` 의 `direct_row` · `row` · `note` · `g_settings` · `save_settings` · `g_notice` · `g_confirm`, `features.h` 의 `Direct` · `Feature`.
- Produces:
  - `Direct::TechLevel`(입력한 수준 이하의 기술을 모두 플레이어의 보유로) · `Direct::QueueDone`(플레이어의 대기열에 있는 기술 · 부대 설계를 모두 보유로 만들고 대기열에서 뺀다). `Direct` 의 끝에 더한다.
  - 기능 표의 두 줄: `technology`(`has_value`, 기본 120, 범위 1 ~ **255**, `Direct::TechLevel`) · `e=mc2`(`Direct::QueueDone`). `command` 는 빈 글이다. 줄의 수(19)와 순서 · 이름 · 탭은 그대로, `cheat_feature_count()` 는 13.
  - `bool direct_row(const Feature &, const GameState &)` — 단추를 그렸으면(쓸 수 있으면) true. 연구의 두 줄은 `game_research_off()` 를 보고, 누르면 `keeper_enqueue_research` 를 부른다(이름은 `기술 수준 N 이하` · `대기열`). 값이 있는 줄은 단추 앞에 입력란을 그린다(그린 것의 이름 `value:<id>`).
  - 내장 치트로 도는 줄이 없는 탭의 바닥 안내는 돈 · 물자 탭과 같다(글쇠 방식과 상관없다).
  - `srtoybox_feature_info` 의 "하는 길"에 `tech_level` · `queue_done`.
  - 화면 검사(`toybox_overlay_probe.py`): `fake_game(…, research=True, recompute=None)` — 연구의 판을 `fake.lab` 에, 불린 지역 인덱스를 `fake.recomputed` 에. 새 모드 `research` · `research_menu` · `research_leave` · `research_notfound` · `research_write_off` · `research_unread` · `research_fault` · `research_reenter`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

기능 표의 테스트(직접 쓰는 줄 여섯, 내장 치트 열셋)와 명령 글의 테스트를 고치고, 화면 검사에 연구의 모드를 더한다. 화면 검사는 진짜 창 메시지로 단추를 누르고 타이머를 돌린다 — 명령 처리 함수(가짜)가 불리지 않는 것, 글쇠가 가지 않는 것, 치트 허용 비트가 그대로인 것을 본다.

<!-- 고칠 곳: test -->
`tests/test_toybox.py` 에서 다음을 찾아:

```python
    # 네 줄은 ToyBox 가 값을 직접 쓴다(3단계 2) — 자리와 이름은 그대로이고 게임에 넣는 글이 없다. 나머지 열다섯이 내장 치트로 돈다
    assert {f["id"]: f["how"] for f in fs if f["how"] != "cheat"} == {"finalexam": "tech_up", "shelovesme": "opinion_best",
                                                                     "love": "relation_best", "neutral": "relation_neutral"}
    cheats = [f for f in fs if f["how"] == "cheat"]
    assert len(cheats) == 15 == dll.srtoybox_cheat_feature_count() and len({f["command"] for f in cheats}) == 15
    assert [f["id"] for f in fs][:3] == ["technology", "e=mc2", "finalexam"]            # 줄의 자리는 옮기기 전과 같다
```

이렇게 바꾼다:

```python
    # 여섯 줄은 ToyBox 가 직접 쓴다(3단계 2 의 넷, 3단계 3 의 연구 둘) — 자리와 이름은 그대로이고 게임에 넣는 글이 없다.
    # 나머지 열셋이 내장 치트로 돈다
    assert {f["id"]: f["how"] for f in fs if f["how"] != "cheat"} == {
        "technology": "tech_level", "e=mc2": "queue_done", "finalexam": "tech_up", "shelovesme": "opinion_best",
        "love": "relation_best", "neutral": "relation_neutral"}
    cheats = [f for f in fs if f["how"] == "cheat"]
    assert len(cheats) == 13 == dll.srtoybox_cheat_feature_count() and len({f["command"] for f in cheats}) == 13
    assert [f["id"] for f in fs][:3] == ["technology", "e=mc2", "finalexam"]            # 줄의 자리는 옮기기 전과 같다
    assert [(f["label"], f["default"], f["min"], f["max"]) for f in fs[:2]] == [("기술 수준 N 이하 전부 보유", 120, 1, 255),
                                                                              ("대기열의 연구 즉시 완료", 0, 0, 0)]
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
            assert f["command"] == "" and not f["has_value"] and not f["confirm"]
```

이렇게 바꾼다:

```python
            assert f["command"] == "" and not f["confirm"]
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert text(dll.srtoybox_command, b"technology", 140, 0) == "cheat technology 140"
    assert text(dll.srtoybox_command, b"technology", 0, 0) == "cheat technology 1"             # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"technology", -5, 0) == "cheat technology 1"
    assert text(dll.srtoybox_command, b"technology", 10**12, 0) == "cheat technology 999"
    assert text(dll.srtoybox_command, b"e=mc2", 999, 1106) == "cheat e=mc2"                    # 값도 대상도 없는 기능은 둘 다 무시한다
```

이렇게 바꾼다:

```python
    assert text(dll.srtoybox_command, b"spawnunit", 140, 0) == "cheat spawnunit 140"
    assert text(dll.srtoybox_command, b"spawnunit", 0, 0) == "cheat spawnunit 1"               # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"spawnunit", -5, 0) == "cheat spawnunit 1"
    assert text(dll.srtoybox_command, b"spawnunit", 10**12, 0) == "cheat spawnunit 99999"
    assert text(dll.srtoybox_command, b"populate", 999, 1106) == "cheat populate"              # 값도 대상도 없는 기능은 둘 다 무시한다
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    for moved in (b"finalexam", b"shelovesme", b"love", b"neutral"):                           # 직접 쓰는 줄은 게임에 넣을 글이 없다
        assert text(dll.srtoybox_command, moved, 0, 1106) is None
```

이렇게 바꾼다:

```python
    for moved in (b"technology", b"e=mc2", b"finalexam", b"shelovesme", b"love", b"neutral"):   # 직접 쓰는 줄은 게임에 넣을 글이 없다
        assert text(dll.srtoybox_command, moved, 120, 1106) is None
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert text(dll.srtoybox_command, b"technology", 1, 0, size=4) is None                     # 버퍼가 작으면 넘치지 않고 -1
```

이렇게 바꾼다:

```python
    assert text(dll.srtoybox_command, b"spawnunit", 1, 0, size=4) is None                      # 버퍼가 작으면 넘치지 않고 -1
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert list(got["research"]) == ["run:technology", "run:e=mc2", "off:finalexam"]
```

이렇게 바꾼다:

```python
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert list(got["research"]) == ["off:technology", "off:e=mc2", "off:finalexam"]          # 연구 탭의 세 줄은 모두 직접 쓰는 줄이다
```

`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
def test_prologue_length_knows_only_plain_function_heads(dll):
```

이것을 더한다:

```python
# 연구의 판(toybox_fake_game.standard_lab)에서 [독일의 기술, 독일의 부대 설계, 폴란드의 기술, 폴란드의 부대 설계]
HELD_START = [[1, 4, 6], [10, 13, 14], [1, 2], [11, 13]]
HELD_QUEUE = [[1, 2, 3, 4, 6], [10, 11, 13, 14], [1, 2], [11, 13]]          # 대기열의 기술 2(+ 선행은 이미 보유) · 부대 설계 11(+ 선행 3)
HELD_LEVEL = [[1, 2, 3, 4, 6, 7], [10, 11, 13, 14], [1, 2], [11, 13]]       # 거기에 수준 120 이하의 남은 기술 7
RESEARCH_BUTTONS = {"value:technology": "120", "run:technology": "기술 수준 N 이하 전부 보유", "run:e=mc2": "대기열의 연구 즉시 완료",
                    "run:finalexam": "지식 순위 올리기"}
RESEARCH_FAULT = "효과를 다시 셈하는 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오."


@pytest.mark.parametrize("env", [{}, {"SRTOYBOX_DIRECT": "0"}], ids=["direct", "typing"])
def test_the_two_research_buttons_write_without_any_cheat(dll, cfg, tmp_path, env):
    """요구 3: "대기열의 연구 즉시 완료"와 "기술 수준 N 이하 전부 보유"는 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고,
    글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다. 단추의 이름과 자리는 그대로다.
    사용자가 알린 문제: 내장 치트는 대기열의 부대 설계를 끝내지 않았다 — 이제 설계 11 도 끝난다.
    내장 치트는 모든 기술의 연구 기간을 1일로 바꿨다(모든 나라의 표) — 이제 그대로다. 다른 나라의 보유도 그대로다.
    게임의 함수는 "효과를 다시 셈" 하나만, 플레이어의 지역 인덱스로만 부른다. 내장 치트가 글쇠 방식이어도 이 탭은 상관없다."""
    got = json.loads(_probe(cfg, tmp_path, "research", env=env))
    assert got["rows"] == RESEARCH_BUTTONS and list(got["rows"]) == list(RESEARCH_BUTTONS)
    assert got["after_queue"] == HELD_QUEUE and got["wrote_queue"] == "기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열"
    assert got["held"] == HELD_LEVEL and got["wrote_level"] == "기술 1개를 완료로 — 기술 수준 120 이하"
    assert got["unwritten"] == "바꿀 것이 없습니다 — 대기열"                 # 세 번째 누름: 대기열이 비었다
    assert got["days"] == [100.0] and got["recomputed"] == [176, 176]
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0
    assert got["hint"] == DIRECT_HINT and got["status"] == "플레이 중: 독일 (1499)"
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개" in log
    assert "연구 완료 (기술 수준 120 이하): 기술 1개" in log and "연구 완료 (대기열): 바꿀 것이 없습니다" in log
    assert "직접 실행" not in log and "실패" not in log


def test_the_research_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "research_menu"))
    assert got["rows"] == RESEARCH_BUTTONS                      # 단추는 보이지만 꺼져 있다
    assert got["held"] == HELD_START and got["wrote_level"] == "-" and got["recomputed"] == []
    assert got["lines"] == [] and got["text"] == "" and got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_research_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "research_leave"))
    assert got["dropped"] == HELD_START and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["held"] == HELD_QUEUE and got["unwritten_after"] == "-" and got["recomputed"] == [176]


@pytest.mark.parametrize("mode, env, why, third", [
    ("research_notfound", {}, "이 게임 판에서는 쓸 수 없습니다 (연구의 자리를 주지 않았습니다)", None),
    ("research_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)", "off"),
    ("research_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다.", "off"),
], ids=["not-found", "write-off", "unread"])
def test_the_research_buttons_say_why_they_are_off_and_offer_no_cheat(dll, cfg, tmp_path, mode, env, why, third):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 단추 자리에 까닭 한 줄만 보인다(입력란도 없다).
    연구의 자리만 못 찾은 게임에서는 두 줄만 꺼지고 "지식 순위 올리기"는 제 묶음대로 남는다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    rows = got["rows"]
    assert list(rows) == ["off:technology", "off:e=mc2", "run:finalexam" if third is None else "off:finalexam"]
    assert rows["off:technology"] == "기술 수준 N 이하 전부 보유 — " + why and rows["off:e=mc2"] == "대기열의 연구 즉시 완료 — " + why
    assert got["lines"] == [] and got["text"] == "" and got["recomputed"] == []
    if mode != "research_notfound":
        assert got["held"] == HELD_START and got["hint"] == "-"      # 쓸 수 있는 줄이 없다 — 바닥의 안내도 없다


def test_a_fault_while_recomputing_stops_toybox_and_says_so(dll, cfg, tmp_path):
    """게임의 "효과를 다시 셈"에서 예외가 나면 ToyBox 가 잡는다: 게임은 죽지 않고, 빨간 경고가 뜨고, 그 뒤로는 아무것도 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "research_fault"))
    assert got["fault"] == RESEARCH_FAULT
    assert got["after_fault"] == HELD_QUEUE == got["held"]      # 비트는 예외 전에 썼다. 그 뒤의 "기술 수준" 단추는 듣지 않는다
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "효과를 다시 셈하는 중 예외 0xC0000005 — ToyBox 를 멈춥니다" in log and "기술 수준 120 이하" not in log


def test_no_cheat_starts_while_the_game_is_recomputing(dll, cfg, tmp_path):
    """"효과를 다시 셈" 안에서 타이머가 다시 와도 그 안에서는 대기열의 내장 치트를 시작하지 않는다 — 직접 실행과 한 쌍의 깃발을 쓴다."""
    got = json.loads(_probe(cfg, tmp_path, "research_reenter"))
    assert len(got["inside"]) == 2 and got["inside"][0] == got["inside"][1]      # 그 안에서 다시 온 타이머의 앞뒤로 명령 처리 함수가 불린 수
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow", "cheat fullmapshow"]      # 둘째 치트는 그 뒤에 돈다
    assert got["held"] == HELD_QUEUE and got["recomputed"] == [176]


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
물자 탭이 창 안에 들어오는가 (출력은 JSON 한 줄):
```

이것을 더한다:

```python
연구의 두 줄 — 내장 치트를 거치지 않고 기술 · 부대 설계의 보유를 고친다 (출력은 JSON 한 줄. 연구의 판은 toybox_fake_game.standard_lab):
    research           게임 안에서 "대기열의 연구 즉시 완료", 그리고 "기술 수준 N 이하 전부 보유"(입력란은 처음 값 120)
    research_menu      메뉴에 있다 — 단추가 꺼져 있다
    research_leave     단추를 누른 뒤 쓰기 전에 게임에서 나간다 — 쓰지 않고 버린다. 돌아오면 다시 된다
    research_notfound  연구의 자리를 찾지 못한 게임 — 두 줄에만 까닭이 보이고 "지식 순위 올리기"는 그대로다
    research_write_off SRTOYBOX_WRITE=0 — 세 줄 모두 까닭만 보인다
    research_unread    SRTOYBOX_READ=0 — 〃
    research_fault     게임의 "효과를 다시 셈"이 죽는다 — ToyBox 가 잡고 빨간 경고를 띄운다. 그 뒤로는 아무것도 쓰지 않는다
    research_reenter   "효과를 다시 셈" 안에서 타이머가 다시 온다 — 그 안에서는 대기열의 내장 치트를 시작하지 않는다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
from toybox_fake_game import MORE, MULTIPLAYER, OPTIONS, FakeGame  # noqa: E402  (이 파일과 같은 폴더)
```

이렇게 바꾼다:

```python
from toybox_fake_game import DESIGN, MORE, MULTIPLAYER, OPTIONS, TECH, FakeGame, standard_lab  # noqa: E402  (이 파일과 같은 폴더)
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
```

이것을 더한다:

```python
RECOMPUTE = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)     # 게임의 "효과를 다시 셈": void f(void *world, int index)
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
def fake_game(hook: str, handler: int | None = None, values: bool = True, more: dict | None = MORE) -> FakeGame:
```

이렇게 바꾼다:

```python
def fake_game(hook: str, handler: int | None = None, values: bool = True, more: dict | None = MORE, research: bool = True,
              recompute: int | None = None) -> FakeGame:
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 뒤에:

```python
    more 는 더 쓰는 값의 자리다 — 자리를 0 으로 둔 묶음은 못 찾은 것이 된다. None 이면 모두 못 찾은 게임이다.
```

이것을 더한다:

```python
    research 가 False 면 연구의 자리를 찾지 못한 게임이다. 아니면 연구의 판(standard_lab)이 fake.lab 에 붙는다.
    recompute 는 "효과를 다시 셈" 자리에 둘 함수의 주소다 — 주지 않으면 불린 지역 인덱스를 fake.recomputed 에 적는 함수를 둔다.
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 뒤에:

```python
        toybox.srtoybox_test_more(ctypes.byref(type(fake.more)(**more)))
```

이것을 더한다:

```python
    fake.recomputed = []
    fake.recompute = RECOMPUTE(lambda _world, index: fake.recomputed.append(index))     # 게임이 살아 있는 동안 붙들어 둔다
    if research:
        toybox.srtoybox_test_research.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        fake.lab = standard_lab(fake)
        toybox.srtoybox_test_research(ctypes.byref(fake.lab.layout),
                                      recompute if recompute is not None else ctypes.cast(fake.recompute, ctypes.c_void_p))
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
def run_layout(hook: str, mode: str) -> int:
```

이것을 더한다:

```python
def run_research(hook: str, mode: str) -> int:
    """연구의 두 줄: 내장 치트를 거치지 않고 기술 · 부대 설계의 보유를 고친다. 출력은 JSON 한 줄(보이지 않는 글은 "-").

    held 는 [독일의 기술, 독일의 부대 설계, 폴란드의 기술, 폴란드의 부대 설계] — 처음에는 [[1, 4, 6], [10, 13, 14], [1, 2], [11, 13]].
    """
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    inside: list[int] = []
    box: dict[str, FakeGame] = {}

    def body(_context, line):
        lines.append(line.decode())
        if line == b"cheat allowcheats":
            box["fake"].poke(OPTIONS, "<I", box["fake"].peek(OPTIONS, "<I") | 0x40)

    def recompute(_world, index):
        box["fake"].recomputed.append(index)
        if mode == "research_reenter":                        # 게임의 함수가 일하는 도중에 ToyBox 의 타이머가 다시 온다
            inside.append(len(lines))
            user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)
            inside.append(len(lines))

    game.handler, game.recompute = HANDLER(body), RECOMPUTE(recompute)      # 게임이 살아 있는 동안 붙들어 둔다
    fake = box["fake"] = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value, research=mode != "research_notfound",
                                   recompute=crash_stub() if mode == "research_fault" else ctypes.cast(game.recompute, ctypes.c_void_p))
    if mode != "research_menu":
        fake.play(176)
    game.hotkey()
    game.got.clear()
    out: dict[str, object] = {}

    def held() -> list[list[int]]:
        lab = fake.lab
        return [lab.held(TECH, 64, 176), lab.held(DESIGN, 64, 176), lab.held(TECH, 64, 141), lab.held(DESIGN, 64, 141)]

    def press(name: str) -> None:
        game.click(name)
        game.wait(0.2)                                        # 쓰는 것은 다음 타이머에서다

    game.click(RESEARCH)
    facts = game.facts()
    out["rows"] = {name: facts[name][3] for name in facts if name.startswith(("run:", "off:", "value:"))}
    if mode in ("research", "research_menu"):
        press("run:e=mc2")
        out["after_queue"], out["wrote_queue"] = held(), game.shown("wrote")
        press("run:technology")
        out["wrote_level"] = game.shown("wrote")
        press("run:e=mc2")                                    # 한 번 더 — 대기열이 비었다
        out["unwritten"] = game.shown("unwritten")
    elif mode == "research_leave":
        game.click("run:e=mc2")                               # 눌렀다. 쓰는 것은 다음 타이머에서다(메시지를 돌릴 때 온다)
        fake.menu()                                           # 그 전에 게임에서 나갔다
        game.wait(0.3)
        out["dropped"], out["unwritten"] = held(), game.shown("unwritten")
        fake.play(176)
        press("run:e=mc2")                                    # 돌아오면 다시 된다
        out["unwritten_after"] = game.shown("unwritten")
    elif mode == "research_fault":
        press("run:e=mc2")
        out["fault"] = game.shown("fault")
        out["after_fault"] = held()
        press("run:technology")                               # 오류 가드가 걸렸다 — 단추가 꺼져 있다
    elif mode == "research_reenter":
        game.click(CHEAT_TAB)
        game.click(BUTTON)
        game.click(BUTTON)                                    # 내장 치트로 도는 기능 둘이 실행기의 대기열에 든다
        game.click(RESEARCH)
        game.click("run:e=mc2")                               # 연구 요청도 든다
        game.wait(1.0)
        out["inside"] = inside
    if mode != "research_notfound":
        out["held"] = held()
        out["days"] = sorted({struct.unpack_from("<f", fake.lab.techs, n * 0x88 + 0x30)[0] for n in (1, 2, 3, 4, 6, 7)})
    out["hint"], out["status"] = game.shown("hint"), game.shown("status")
    out["recomputed"], out["lines"], out["text"], out["options"] = fake.recomputed, lines, game.text(), fake.peek(OPTIONS, "<I")
    print(json.dumps(out, ensure_ascii=False))
    return 0


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    if mode.startswith("stock"):
```

이것을 더한다:

```python
    if mode.startswith("research"):
        return run_research(hook, mode)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox.py -q 2>&1 | tail -4`

Expected: `13 failed, 80 passed` — 기능 표와 명령 글의 테스트 둘(직접 쓰는 줄이 아직 넷이고 `technology` 가 아직 치트의 글을 낸다), 앞 묶음의 "쓸 수 없을 때" 테스트 둘(`'run:technology' != 'off:technology'`), 새 연구 테스트 아홉(두 단추가 아직 내장 치트의 단추다 — 입력란의 이름 `value:technology` 가 없고, 누르면 명령 처리 함수가 불리거나 글쇠가 간다). 화면 검사라 2 ~ 3분 걸린다.

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
// 하는 길(cheat = 내장 치트 / tech_up · opinion_best · relation_best · relation_neutral = 직접 쓴다) — 탭 문자로 나눈다
```

이렇게 바꾼다:

```cpp
// 하는 길(cheat = 내장 치트 / tech_up · opinion_best · relation_best · relation_neutral · tech_level · queue_done = 직접 쓴다)
// — 탭 문자로 나눈다
```

`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
    static const char *const how[] = {"cheat", "tech_up", "opinion_best", "relation_best", "relation_neutral"};
```

이렇게 바꾼다:

```cpp
    static const char *const how[] = {"cheat", "tech_up", "opinion_best", "relation_best", "relation_neutral", "tech_level", "queue_done"};
```

`native/srtoybox/features.cpp` 에서 다음을 찾아:

```cpp
// 나머지 줄은 아직 내장 치트로 돈다. 묶음마다 옮긴다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다", "cheat technology", true, 120, 1, 999, false},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 연구가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "cheat e=mc2", false, 0, 0, 0, false},
```

이렇게 바꾼다:

```cpp
// 두 줄(technology · e=mc2)은 3단계 3 에서 직접 쓰기로 바꿨다. 내장 치트는 부대 설계를 건드리지 않았고, e=mc2 는 모든 기술의
// 연구 기간을 1일로 바꿨다(모든 나라가 함께 쓰는 표) — 이제 플레이어의 보유 비트만 쓴다. 기술 수준은 한 바이트라 255 까지다.
// 나머지 줄은 아직 내장 치트로 돈다. 묶음마다 옮긴다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다(선행 기술 포함)", "", true, 120, 1, 255, false,
     Target::None, Direct::TechLevel},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 기술과 부대 설계가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "", false, 0, 0, 0, false,
     Target::None, Direct::QueueDone},
```

`native/srtoybox/features.h` 에서 다음 바로 앞에:

```cpp
#pragma once
```

이것을 더한다:

```cpp
// 연구의 두 줄(technology · e=mc2)은 3단계 3 에서 직접 쓰는 줄이 됐다 — 기술 · 부대 설계의 보유 비트를 쓴다(research.h).
```

`native/srtoybox/features.h` 에서 다음 바로 뒤에:

```cpp
    RelationNeutral,   // 고른 나라와의 관계 중립, 전쟁 명분 0(〃)
```

이것을 더한다:

```cpp
    TechLevel,         // 입력한 수준 이하의 기술을 모두 플레이어의 보유로(선행 기술 포함)
    QueueDone,         // 플레이어의 대기열에 있는 기술 · 부대 설계를 모두 보유로 만들고 대기열에서 뺀다
```

`native/srtoybox/features.h` 에서 다음을 찾아:

```cpp
    bool has_value;
```

이렇게 바꾼다:

```cpp
    bool has_value;       // 단추 앞에 수를 받는다(내장 치트: 명령 뒤에 붙는다, TechLevel: 기술 수준)
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
// 직접 쓰는 줄(3단계 2): 내장 치트를 거치지 않는다 — 누르면 값 쓰기 요청을 대기열에 넣고, 쓰는 것은 게임 창의 타이머에서다(keeper.h).
// 쓸 수 없으면 단추 자리에 까닭 한 줄만 그린다(그 줄에만. 같은 탭의 다른 줄은 그대로다). 내장 치트로 되돌아가지 않는다.
void direct_row(const Feature &f, const GameState &game)
{
    const int group = f.direct == Direct::TechUp ? MORE_TECH : f.direct == Direct::OpinionBest ? MORE_OPINION : MORE_RELATIONS;
    const std::string off = game.known ? game_more_off(group) : std::string("게임 상태를 읽을 수 있을 때만 씁니다.");
```

이렇게 바꾼다:

```cpp
// 직접 쓰는 줄(3단계 2 · 3): 내장 치트를 거치지 않는다 — 누르면 요청을 대기열에 넣고, 쓰는 것은 게임 창의 타이머에서다(keeper.h).
// 쓸 수 없으면 단추 자리에 까닭 한 줄만 그린다(그 줄에만. 같은 탭의 다른 줄은 그대로다). 내장 치트로 되돌아가지 않는다.
// 단추를 그렸으면(쓸 수 있으면) true.
bool direct_row(const Feature &f, const GameState &game)
{
    const bool research = f.direct == Direct::TechLevel || f.direct == Direct::QueueDone;   // 연구의 두 줄은 제 묶음(연구)을 본다
    const int group = f.direct == Direct::TechUp ? MORE_TECH : f.direct == Direct::OpinionBest ? MORE_OPINION : MORE_RELATIONS;
    const std::string off = !game.known ? std::string("게임 상태를 읽을 수 있을 때만 씁니다.")
        : research ? game_research_off() : game_more_off(group);
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
        ImGui::BeginDisabled(f.target == Target::Picked && g_picked <= 0);   // 나라를 고르지 않았다
        const bool pressed = ImGui::Button((std::string(f.label) + "###run").c_str());
        note(std::string("run:") + f.id, f.label);
        if (pressed) {
```

이렇게 바꾼다:

```cpp
        long long value = 0;
        if (f.has_value) {                                                   // 기술 수준. 쓸 수 없을 때는 입력란도 그리지 않는다
            long long &stored = g_settings.values[f.id];
            ImGui::SetNextItemWidth(150.0f);
            if (ImGui::InputScalar("##value", ImGuiDataType_S64, &stored)) {
                stored = stored < f.min ? f.min : stored > f.max ? f.max : stored;
                save_settings(g_settings);
            }
            note(std::string("value:") + f.id, std::to_string(stored));
            value = stored;
            ImGui::SameLine();
        }
        ImGui::BeginDisabled(f.target == Target::Picked && g_picked <= 0);   // 나라를 고르지 않았다
        const bool pressed = ImGui::Button((std::string(f.label) + "###run").c_str());
        note(std::string("run:") + f.id, f.label);
        if (pressed && research) {
            ResearchRequest request = {Research::Complete, ResearchWhat(), "대기열"};
            request.what.kind = ResearchWhat::Queue;
            if (f.direct == Direct::TechLevel) {
                request.what.kind = ResearchWhat::Level;
                request.what.level = static_cast<int>(value);
                request.label = "기술 수준 " + std::to_string(value) + " 이하";
            }
            g_confirm.clear();
            g_notice = keeper_enqueue_research(request) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
        } else if (pressed) {
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
}

void row(const Feature &f, const GameState &game)
{
    if (f.direct != Direct::None) {
        direct_row(f, game);
        return;
    }
```

이렇게 바꾼다:

```cpp
    return off.empty();
}

// 아직 내장 치트로 도는 줄: 누르면 명령을 실행기의 대기열에 넣는다.
void row(const Feature &f, const GameState &game)
{
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
        bool values_tab = false, values_ok = false;         // 지금 보이는 탭이 값을 직접 쓰는 탭(돈 · 물자)인가, 그 탭을 쓸 수 있는가
```

이렇게 바꾼다:

```cpp
        // 지금 보이는 탭이 내장 치트로 도는 줄이 없는 탭(돈 · 물자, 그리고 줄이 모두 직접 쓰는 줄인 연구)인가, 그 탭을 쓸 수 있는가
        bool values_tab = false, values_ok = false;
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
                        for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++)
                            row(FEATURES[j], game);
                        ImGui::EndDisabled();
```

이렇게 바꾼다:

```cpp
                        bool cheats = false, direct_ok = false;
                        for (int j = i; j < FEATURE_COUNT && strcmp(FEATURES[j].tab, tab) == 0; j++) {
                            if (FEATURES[j].direct == Direct::None) {
                                cheats = true;
                                row(FEATURES[j], game);
                            } else if (direct_row(FEATURES[j], game)) {
                                direct_ok = true;
                            }
                        }
                        ImGui::EndDisabled();
                        if (!cheats) {                   // 이 탭의 바닥 안내는 글쇠 방식과 상관없다
                            values_tab = true;
                            values_ok = direct_ok;
                        }
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
        // 값을 직접 쓰는 탭(돈 · 물자)은 글쇠 방식과 상관없다 — 쓸 수 있으면 늘 바로 바뀌고, 쓸 수 없으면 탭의 까닭 한 줄이 전부다.
```

이렇게 바꾼다:

```cpp
        // 내장 치트로 도는 줄이 없는 탭(돈 · 물자 · 연구)은 글쇠 방식과 상관없다 — 쓸 수 있으면 늘 바로 바뀌고, 쓸 수 없으면 까닭의 줄이 전부다.
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox.py -q 2>&1 | tail -1`

Expected: `빌드 완료: …`, `93 passed`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add native/srtoybox/features.h native/srtoybox/features.cpp native/srtoybox/ui.cpp native/srtoybox/exports.cpp tests/test_toybox.py tests/toybox_overlay_probe.py && git commit -q -F - <<'EOF'
feat: ToyBox 연구 탭의 두 단추를 내장 치트 없이 — 대기열의 부대 설계도 끝난다

- "대기열의 연구 즉시 완료"(e=mc2) · "기술 수준 N 이하 전부 보유"(technology)가 직접 쓰는 줄이 된다. 단추의 이름 · 탭 · 자리는
  그대로이고 내장 치트로 도는 기능은 15 → 13.
- 내장 치트와 달라지는 것: 대기열의 부대 설계도 끝낸다(사용자가 알린 문제) / 모든 나라가 함께 쓰는 연구 기간을 1일로 바꾸지 않는다 /
  끝낸 것을 대기열에서 뺀다 / 선행 기술을 함께 준다. 기술 수준의 범위는 1 ~ 255(한 바이트다).
- 쓸 수 없으면 단추 자리에 까닭 한 줄만 보인다(내장 치트로 되돌아가지 않는다).
- 연구 탭에는 이제 내장 치트로 도는 줄이 없다 — 바닥의 안내가 글쇠 방식과 상관없이 "값은 바로 바뀝니다"다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `556 passed`, 새 커밋.

---

### Task 7: `gamedrive.py research` — 게임의 메모리에서 연구를 읽는다(검증용)

**브랜치:** `feat/toybox-research-engine`

**Files:**
- Modify: `scripts/gamedrive.py`
- Test: `tests/test_gamedrive.py`

**Interfaces:**
- Consumes: `toybox.locate(cfg)` 의 `Located.state` · `research` · `research_why`, `toybox.research_shape` · `toybox.library`(Task 2), `gamedrive.py` 의 `owned_pids` · `game_pids` · `not_ours` · `EXE`, `toybox_fake_game.standard_lab`(Task 4).
- Produces:
  - `peek_research(read, research, shape, base, index, me, region=None) -> dict` — `read(주소, 바이트 수) -> bytes | None`. 결과: `index` · `techs` · `designs`(그 지역이 보유한 번호들) · `used` · `unhoused`(`{"techs": n, "designs": n}`) · `queue`(플레이어의 목록: `[종류, 번호, 깃발 1, 깃발 2]`, 깃발은 16진 글) · `days`(모든 기술의 연구 기간의 합), `region` 을 주면 `effects`(`mul` · `add` · `cell`).
  - `research_game(cfg, number=None) -> dict` — 이 도구가 띄운 게임에서. 위의 것에 `player` · `region`(번호)을 더한다. 보정 표는 실행 파일의 TimeDateStamp 가 `RESEARCH_BUILD`(`0x695377B6`)일 때만.
  - 명령 `uv run python scripts/gamedrive.py research [지역 번호] [--out 파일]`.
  - 상수 `RESEARCH_BUILD` · `EFFECT_TABLES` · `EFFECT_CELL` · `TECH_DAYS` · `MAX_NODES` — 검증에만 쓴다(ToyBox 는 이 자리들을 모른다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_gamedrive.py` 에서 다음 바로 뒤에:

```python
    assert fake.snapshot(176) + fake.snapshot(141) == before
```

이것을 더한다:

```python


@pytest.fixture
def lab_game(cfg):
    """독일(176)로 진행 중인 가짜 게임과 그 연구(toybox_fake_game.standard_lab), 표의 꼴(ToyBox 의 DLL 이 아는 것 — locate.h), 읽는 함수."""
    import ctypes

    from srkit import toybox
    from toybox_fake_game import FakeGame, standard_lab

    if not toybox.output(cfg).is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.play(176)
    return fake, standard_lab(fake), toybox.research_shape(toybox.library(cfg)), lambda address, size: ctypes.string_at(address, size)


def test_research_reads_what_a_region_holds_and_the_players_queue(gd, lab_game):
    """research 는 게임의 메모리에서 연구를 읽는다(읽기만): 그 지역이 보유한 기술 · 부대 설계, 쓰는 항목과 묶음이 없는 항목의 수,
    플레이어의 대기열(나중에 건 것이 앞이다), 모든 기술의 연구 기간의 합. ToyBox 가 쓴 것을 창의 숫자가 아니라 이것으로 본다."""
    from toybox_fake_game import RESEARCH

    fake, lab, shape, read = lab_game
    before = lab.everything()
    germany = gd.peek_research(read, RESEARCH, shape, fake.base, 176, 176)
    assert germany == {"index": 176, "techs": [1, 4, 6], "designs": [10, 13, 14], "used": {"techs": 6, "designs": 5},
                       "unhoused": {"techs": 1, "designs": 1}, "days": 600.0,
                       "queue": [[2, 11, "00000001", "60000001"], [1, 2, "00000001", "00000000"]]}
    poland = gd.peek_research(read, RESEARCH, shape, fake.base, 141, 176)
    assert (poland["index"], poland["techs"], poland["designs"]) == (141, [1, 2], [11, 13])
    assert poland["queue"] == germany["queue"] and "effects" not in poland     # 대기열은 플레이어의 것이다. 보정 표는 달라고 할 때만
    assert lab.everything() == before


def test_research_reads_the_effect_tables_of_the_build_it_knows(gd, lab_game, monkeypatch):
    """지역의 보정 표(게임의 "효과를 다시 셈"이 쌓는 것)의 자리는 한 빌드에서만 안다 — 지역 객체의 주소를 줄 때만 읽는다.
    표는 세계 객체 안에 지역마다 있고(첫 자리 + 간격 × 지역 인덱스), 한 칸은 지역 객체 안에 있다."""
    import struct

    from toybox_fake_game import RESEARCH

    fake, _lab, shape, read = lab_game
    world = fake.base + RESEARCH["world"]
    monkeypatch.setattr(gd, "EFFECT_TABLES", {"mul": (0x100000, 0x10, 3), "add": (0x200000, 0x20, 2)})
    monkeypatch.setattr(gd, "EFFECT_CELL", 0x800)
    far = {world + 0x100000 + 0x10 * 176: struct.pack("<3f", 1.0, 1.5, 2.0), world + 0x200000 + 0x20 * 176: struct.pack("<2f", 0.25, 0.5)}
    fake._write(176, 0x800, "<I", 7)
    got = gd.peek_research(lambda address, size: far[address] if address in far else read(address, size), RESEARCH, shape, fake.base,
                           176, 176, region=fake.where[176])
    assert got["effects"] == {"mul": [1.0, 1.5, 2.0], "add": [0.25, 0.5], "cell": 7} and got["techs"] == [1, 4, 6]


def test_research_stops_when_the_game_cannot_be_read(gd, lab_game):
    """표를 읽을 수 없거나 자리 수가 말이 안 되면 반쯤 읽은 것을 내지 않는다."""
    from toybox_fake_game import RESEARCH

    fake, _lab, shape, read = lab_game
    with pytest.raises(SystemExit, match="게임의 메모리를 읽을 수 없습니다"):
        gd.peek_research(lambda address, size: None if size > 64 else read(address, size), RESEARCH, shape, fake.base, 176, 176)
    fake.poke(RESEARCH["tech_count"], "<i", 70000)
    with pytest.raises(SystemExit, match="자리 수가 범위 밖입니다"):
        gd.peek_research(read, RESEARCH, shape, fake.base, 176, 176)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_gamedrive.py -q 2>&1 | tail -4`

Expected: `3 failed, 12 passed` — 새 테스트 셋이 `AttributeError: module 'gamedrive' has no attribute 'peek_research'`(와 `'EFFECT_TABLES'`)로 실패한다.

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`scripts/gamedrive.py` 에서 다음 바로 앞에:

```python
    uv run python scripts/gamedrive.py stop                   # 이 도구가 띄운 게임만 끝낸다 (--all: 전부)
```

이것을 더한다:

```python
    uv run python scripts/gamedrive.py research [지역 번호] [--out 파일]   # 그 지역(없으면 플레이어)이 보유한 기술 · 부대 설계,
                                                              # 플레이어의 연구 대기열, 모든 기술의 연구 기간의 합(읽기만, JSON).
                                                              # 앞뒤 두 번을 견줘 ToyBox 가 무엇을 바꿨고 무엇이 그대로인지 본다
```

`scripts/gamedrive.py` 에서 다음 바로 뒤에:

```python
        kernel32.CloseHandle(process)


```

이것을 더한다:

```python
RESEARCH_BUILD = 0x695377B6     # 아래 보정 표의 자리를 본 빌드(21347933)의 PE TimeDateStamp
# 그 빌드에서만 아는 자리: 게임의 "효과를 다시 셈"이 지역마다 쌓는 보정 표 — (세계 객체 안의 자리, 지역마다의 간격, float 칸의 수).
# 검증에만 쓰는 상수다. ToyBox 는 이 자리를 모르고 건드리지 않는다(docs/11-game-internals.md)
EFFECT_TABLES = {"mul": (0x5456A8, 0x320, 200), "add": (0x60D6A8, 0x2C0, 176)}
EFFECT_CELL = 0x14D38           # 지역 객체 안의 한 칸(dword) — 같은 함수가 0 으로 되돌리고 다시 쌓는다
TECH_DAYS = 0x30                # 기술 레코드의 연구 기간(float). ToyBox 는 읽지도 쓰지도 않는다 — "그대로인가"만 본다
MAX_NODES = 4096                # 연구 목록이 이 안에 끝나지 않으면 읽지 않는다(ToyBox 의 스냅숏과 같다)


def peek_research(read, research: dict[str, int], shape: dict[str, int], base: int, index: int, me: int,
                  region: int | None = None) -> dict:
    """연구의 표와 목록을 읽는다(읽기만). ToyBox 의 창이 아니라 게임의 메모리 그 자체다.

    read(주소, 바이트 수) 는 그만큼을 읽어 주는 함수(못 읽으면 None), research 는 srkit.toybox.locate 가 찾은 자리,
    shape 는 표의 꼴(srkit.toybox.research_shape), base 는 실행 파일이 올라온 주소다. index 는 보유를 볼 지역의 인덱스, me 는 플레이어의 인덱스.
    region 은 그 지역의 객체의 주소 — 주면 그 지역의 보정 표(effects)도 읽는다(RESEARCH_BUILD 에서만 부른다).

    결과: techs · designs(그 지역이 보유한 번호들), used(쓰는 항목의 수), unhoused(보유 묶음이 없는 항목의 수 — 아무도 보유한 적이 없다),
    queue(플레이어의 연구 목록: [종류(1 기술, 2 부대 설계), 번호, 깃발 1, 깃발 2] — 깃발은 16진 글), days(모든 기술의 연구 기간의 합).
    """
    import struct

    def chunk(address: int, size: int) -> bytes:
        raw = read(address, size)
        if raw is None:
            raise SystemExit(f"게임의 메모리를 읽을 수 없습니다: {address:#x} 부터 {size}바이트")
        return raw

    def value(address: int, fmt: str):
        return struct.unpack(fmt, chunk(address, struct.calcsize(fmt)))[0]

    def owned(pointer: int) -> bool:
        return bool(pointer) and bool(value(pointer + index // 8, "<B") >> index % 8 & 1)

    out: dict = {"index": index, "techs": [], "designs": [], "used": {"techs": 0, "designs": 0},
                 "unhoused": {"techs": 0, "designs": 0}, "queue": [], "days": 0.0}
    tables = (("techs", "tech_table", "tech_count", shape["tech_size"], shape["tech_kind"], "<B", shape["tech_owners"]),
              ("designs", "design_table", "design_count", shape["design_size"], shape["design_name"], "<Q", shape["design_owners"]))
    for name, table, count, size, alive, alive_fmt, owners in tables:
        start, slots = value(base + research[table], "<Q"), value(base + research[count], "<i")
        if not start or not 2 <= slots <= 65536:
            raise SystemExit(f"연구의 표가 없거나 자리 수가 범위 밖입니다: {name} {slots}")
        records = chunk(start, slots * size)                # 표는 한 번에 읽는다(부대 설계는 22000 × 0x168)
        for number in range(1, slots):
            at = number * size
            if not struct.unpack_from(alive_fmt, records, at + alive)[0]:
                continue                                    # 빈 자리
            pointer = struct.unpack_from("<Q", records, at + owners)[0]
            out["used"][name] += 1
            out["unhoused"][name] += 0 if pointer else 1
            if owned(pointer):
                out[name].append(number)
            if name == "techs":
                out["days"] += struct.unpack_from("<f", records, at + TECH_DAYS)[0]
    node = value(base + research["world"] + research["lists"] + shape["list_step"] * me, "<Q")
    while node:
        if len(out["queue"]) >= MAX_NODES:
            raise SystemExit("연구 목록이 끝나지 않습니다")
        first, second = value(node + shape["node_flags"], "<I"), value(node + shape["node_flags"] + 4, "<I")
        out["queue"].append([value(node + shape["node_kind"], "<B"), value(node + shape["node_id"], "<i"), f"{first:08x}", f"{second:08x}"])
        node = value(node + shape["node_next"], "<Q")
    if region is not None:
        world = base + research["world"]
        out["effects"] = {name: list(struct.unpack(f"<{cells}f", chunk(world + start + step * index, 4 * cells)))
                          for name, (start, step, cells) in EFFECT_TABLES.items()}
        out["effects"]["cell"] = value(region + EFFECT_CELL, "<I")
    return out


def research_game(cfg: config.Config, number: int | None = None) -> dict:
    """이 도구가 띄운 게임의 메모리에서 연구를 읽는다(peek_research). number 를 주면 플레이어 대신 그 번호의 지역이 보유한 것을 읽는다."""
    import struct

    from srkit import toybox

    mine = owned_pids(cfg)
    if not mine:
        raise SystemExit(not_ours() if game_pids() else "게임이 떠 있지 않습니다")
    found = toybox.locate(cfg)
    if found.state is None or found.research is None:
        raise SystemExit(f"주소를 찾지 못했습니다: {found.state_why or found.research_why}")
    state, shape = found.state, toybox.research_shape(toybox.library(cfg))
    exe = (cfg.game_dir / EXE).read_bytes()
    stamp = struct.unpack_from("<I", exe, struct.unpack_from("<I", exe, 0x3C)[0] + 8)[0]
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

        def read(address: int, size: int):
            buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(process, ctypes.c_void_p(address), buf, size, ctypes.byref(got))
            return buf.raw if ok and got.value == size else None

        def value(address: int, fmt: str):
            raw = read(address, struct.calcsize(fmt))
            return struct.unpack(fmt, raw)[0] if raw is not None else None

        player, me = value(base + state["player_pointer"], "<Q"), value(base + state["player_index"], "<i")
        if not (value(base + state["mode_state"], "<i") == 2 and value(base + state["program_state"], "<i") == 1 and player):
            raise SystemExit("게임이 진행 중이 아닙니다")
        who, index = player, me
        if number is not None:                                          # 지역 표(인덱스 1 … 지역 수)에서 그 번호의 객체를 찾는다
            count = min(value(base + state["region_count"], "<i") or 0, 1023)
            table = ((i, value(base + state["region_table"] + 8 * i, "<Q")) for i in range(1, count + 1))
            index, who = next(((i, pointer) for i, pointer in table if pointer and value(pointer + 8, "<H") == number), (0, None))
            if who is None:
                raise SystemExit(f"그 번호의 지역이 지역 표에 없습니다: {number}")
        out = {"player": value(player + 8, "<H"), "region": value(who + 8, "<H")}
        out.update(peek_research(read, found.research, shape, base, index, me, who if stamp == RESEARCH_BUILD else None))
        return out
    finally:
        kernel32.CloseHandle(process)


```

`scripts/gamedrive.py` 에서 다음 바로 앞에:

```python
    elif cmd == "stop":
```

이것을 더한다:

```python
    elif cmd == "research":
        # research [지역 번호] [--out 파일]: 보유한 부대 설계가 수천 줄이라, 파일을 주면 거기에 적고 화면에는 수만 보인다
        target = args[args.index("--out") + 1] if "--out" in args else None
        numbers = [a for a in args if a not in ("--out", target)]
        got = research_game(cfg, int(numbers[0]) if numbers else None)
        if target is None:
            print(json.dumps(got, ensure_ascii=False))
        else:
            Path(target).write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
            print(f"{target}: 지역 {got['region']} — 기술 {len(got['techs'])}개 · 부대 설계 {len(got['designs'])}개 보유, "
                  f"대기열 {len(got['queue'])}개, 연구 기간의 합 {got['days']:g}")
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 통과를 본다**

Run: `uv run pytest tests/test_gamedrive.py -q 2>&1 | tail -1`

Expected: `15 passed`

Run: `uv run python scripts/gamedrive.py research 2>&1 | tail -1`

Expected: `게임이 떠 있지 않습니다`(사용자가 켠 게임이 떠 있으면 `실행 중인 게임은 이 도구가 띄운 것이 아닙니다 — …` — 어느 쪽이든 아무것도 읽지 않고 끝난다).

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -1 && git add scripts/gamedrive.py tests/test_gamedrive.py && git commit -q -F - <<'EOF'
chore: gamedrive.py research — 보유한 기술 · 부대 설계, 대기열, 연구 기간의 합(검증용, 읽기만)

- 이 도구가 띄운 게임의 메모리에서 그 지역(없으면 플레이어)이 보유한 기술 · 부대 설계의 번호, 쓰는 항목과 묶음이 없는 항목의 수,
  플레이어의 대기열, 모든 기술의 연구 기간의 합을 JSON 으로 낸다. 표의 꼴은 ToyBox 의 DLL 이 아는 것을 그대로 쓴다.
- build 21347933 에서만: 그 지역의 보정 표(게임의 "효과를 다시 셈"이 쌓는 것)도 읽는다 — 그 자리는 검증에만 쓰는 상수다.
- ToyBox 가 쓴 것과 건드리지 않은 것을 창의 글이 아니라 메모리로 본다(앞뒤 두 번을 견준다).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `559 passed`, 새 커밋.

---

### Task 8: 게임 안 확인(R0 ~ R5) · 코드의 최종 검토 · 머지

**브랜치:** `feat/toybox-research-engine` (게임이 떠 있는 동안 바꾸지 않는다)

**Files:**
- 코드는 최종 검토의 지적을 고칠 때만 고친다. 근거 화면 · 메모리의 스냅숏 · 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.
- 스크래치: `rcheck.py`(스냅숏을 견주는 스크립트 — Step 2 에서 쓴다), `pr-research-engine.md`, `r-engine.md`.

**Interfaces:**
- Consumes: Task 1 ~ 7 의 빌드, `gamedrive.py research [지역 번호] --out <파일>`(`techs` · `designs` · `used` · `unhoused` · `queue` · `days` · `effects`) · `gamedrive.py peek`(`cheats_allowed` · `player` · `in_game`).
- Produces: 이 Task 의 결과(스크래치의 `r-engine.md` — Task 9 가 `docs/10` 에 적는다)와 `develop` 에 머지된 PR.

**이 Task 가 가르는 것**: 설계의 전제 넷(설계서의 "아직 보지 않은 것" 1 ~ 4) — ① 비트만 켠 뒤 게임 화면과 생산이 따라오는가 ② "효과를 다시 셈"을 ToyBox 가 불러도 되는가 ③ 노드에 깃발을 쓰면 대기열에서 빠지고 다음 연구가 진행되는가 ④ ToyBox 가 만든 묶음이 그 뒤로 문제없는가. 어긋나면 머지하지 않고 멈춘다 — **(나)를 쓰기 전에 사용자에게 알리고 설계서를 고친다**(설계서의 "구현 순서").

- [ ] **Step 1: PR 을 올린다 (머지는 게임 안 확인과 최종 검토 뒤에)**

스크래치에 `pr-research-engine.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 1 ~ 7 의 커밋 요약), **쓰는 곳이 늘어난 것**(기술 · 부대 설계의 보유 묶음에서 플레이어의 비트, 새 묶음의 포인터 칸, 플레이어의 대기열 노드의 깃발)과 **게임의 함수를 부르는 것**("효과를 다시 셈" 하나, 플레이어 지역으로만 — 설계서의 결정 A), 요구 2 · 3 에 대해 자동 테스트가 보는 것(명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다 · 플레이어의 비트와 정해진 칸만 바뀐다 · 연구 기간의 칸은 그대로다 · 다시 셈은 플레이어의 인덱스로 한 번 · 예외가 나면 멈춘다 · 묶음을 못 찾으면 그 줄만 꺼진다), 설계서와 달라진 곳(이 계획의 같은 이름의 절), "게임 안 확인과 최종 검토의 결과는 아래 댓글에", `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-research-engine && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-research-engine --title "feat: ToyBox — 연구 탭의 두 단추를 내장 치트 없이(대기열의 부대 설계도 끝난다)" --body-file "<스크래치>/pr-research-engine.md"
```

- [ ] **Step 2: 시험용 빌드를 게임 폴더에 바꿔 넣고, 검증 전의 상태를 적어 두고, 견주는 스크립트를 쓴다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-r && rm -f build/verify/toybox-home-r/* build/verify/toybox/R-*.json && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/R-saves-before.txt && cat build/verify/toybox/R-saves-before.txt && uv run python -c "import hashlib, os, pathlib; p = pathlib.Path(os.environ['APPDATA'], 'SR2030ToyBox', 'toybox.ini'); print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'none')" > build/verify/toybox/R-ini-before.txt && cat build/verify/toybox/R-ini-before.txt
```

`build/verify/toybox-home-r` 는 검증용 게임의 ToyBox 설정 폴더다(비어 있으므로 단축키는 기본값 `Ctrl+Shift+T`, 최소 유지는 모두 꺼짐, "기술 수준"의 입력란은 120). 사용자의 `%APPDATA%\SR2030ToyBox` 는 건드리지 않는다 — 끝난 뒤 저장 폴더의 목록과 설정 파일의 해시(없으면 `none`)가 그대로인지 본다.

스크래치에 `rcheck.py` 를 쓴다(Write 도구. 저장소에 넣지 않는다):

```python
"""gamedrive.py research 가 낸 JSON 을 견준다(게임 안 확인용. 읽기만 한다).

    uv run python rcheck.py diff <앞.json> <뒤.json>     # 무엇이 바뀌었고 무엇이 그대로인가
    uv run python rcheck.py level <파일.json> <N>         # 수준이 N 이하인 기술을 모두 보유했는가(게임 폴더의 DEFAULT.TTRX 로 수준을 본다)
    uv run python rcheck.py tech <번호…>                  # 그 기술들의 수준 · 선행 · 효과 번호와 값(DEFAULT.TTRX)
"""
import json
import sys
from pathlib import Path

from srkit import config

sys.stdout.reconfigure(encoding="utf-8")


def ttrx() -> dict[int, list[str]]:
    """게임 폴더의 기술 표: 번호 → 열들(0 번호, 2 수준, 4 · 5 선행, 6 ~ 9 효과 번호, 10 ~ 13 효과의 값). 읽기만 한다."""
    path = config.load().game_dir / "Maps" / "DATA" / "DEFAULT.TTRX"
    rows = {}
    for line in path.read_bytes().decode("cp1252").splitlines():
        if line[:1].isdigit():
            cells = [cell.strip() for cell in line.split("//")[0].split(",")]
            rows[int(cells[0])] = cells
    return rows


def some(numbers: list[int]) -> str:
    return f"{len(numbers)}개" + (f" {numbers[:40]}{' …' if len(numbers) > 40 else ''}" if numbers else "")


def diff(before: dict, after: dict) -> None:
    for name, label in (("techs", "기술"), ("designs", "부대 설계")):
        a, b = set(before[name]), set(after[name])
        print(f"{label}: {len(a)} -> {len(b)}  더해진 것 {some(sorted(b - a))}  빠진 것 {some(sorted(a - b))}")
    print(f"쓰는 항목 {before['used']} -> {after['used']}  묶음이 없는 항목 {before['unhoused']} -> {after['unhoused']}")
    print(f"연구 기간의 합 {before['days']:.6g} -> {after['days']:.6g}  " + ("그대로" if before["days"] == after["days"] else "바뀌었다"))
    print(f"대기열 {before['queue']}\n    -> {after['queue']}")
    if "effects" in before and "effects" in after:
        for name in ("mul", "add"):
            changed = [(i, x, y) for i, (x, y) in enumerate(zip(before["effects"][name], after["effects"][name])) if x != y]
            print(f"보정 표 {name}: " + ("그대로" if not changed else "  ".join(f"[{i}] {x:.6g} -> {y:.6g}" for i, x, y in changed)))
        print(f"보정 칸 {before['effects']['cell']:#x} -> {after['effects']['cell']:#x}")


def level(snapshot: dict, limit: int) -> None:
    held, rows = set(snapshot["techs"]), ttrx()
    wanted = sorted(number for number, cells in rows.items() if cells[2].isdigit() and int(cells[2]) <= limit)
    missing = [number for number in wanted if number not in held]
    print(f"수준 {limit} 이하의 기술 {len(wanted)}개 가운데 보유하지 않은 것 {some(missing)}")
    above = sorted(number for number in held if number in rows and rows[number][2].isdigit() and int(rows[number][2]) > limit)
    print(f"보유한 기술 {len(held)}개 가운데 수준이 {limit} 보다 높은 것 {some(above)}")


def tech(numbers: list[int]) -> None:
    rows = ttrx()
    for number in numbers:
        cells = rows.get(number)
        if cells is None:
            print(f"{number}: 표에 없다")
            continue
        effects = [(cells[6 + i], cells[10 + i]) for i in range(4) if cells[6 + i]]
        print(f"{number}: 수준 {cells[2]}  선행 {cells[4] or '-'} · {cells[5] or '-'}  효과(번호, 값) {effects}")


def main() -> int:
    what, *args = sys.argv[1:]
    if what == "diff":
        diff(*(json.loads(Path(name).read_text(encoding="utf-8")) for name in args[:2]))
    elif what == "level":
        level(json.loads(Path(args[0]).read_text(encoding="utf-8")), int(args[1]))
    elif what == "tech":
        tech([int(number) for number in args])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `cd /e/SR2030ToyBox && PYTHONIOENCODING=utf-8 uv run python "<스크래치>/rcheck.py" tech 2 4`
Expected(build 21347933 의 게임 폴더): `2: 수준 81  선행 1048 · 17  효과(번호, 값) [('9', '0.1')]`, `4: 수준 105  선행 1767 · 1780  효과(번호, 값) [('154', '0.5'), ('155', '0.2'), ('157', '0.2')]`.

- [ ] **Step 3: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)의 "연구" 탭의 단추 둘 — "대기열의 연구 즉시 완료", "기술 수준 N 이하 전부 보유" — 을 게임에서 확인한다.
이 작업(R)만 수행하라. 끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다). uv run pytest 를 돌리지 말라.
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 읽는다: E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법), E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법"과 "확인한 것"의 VB · VC 표
(게임에 들어가는 길, 시간을 흘리는 법 — 속도 단추는 목록을 연다, 일시 정지).

규칙:
- 게임은 다음으로만, 한 번만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-r' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  start 의 출력을 그대로 적는다. "돌려주지 못함 N회" 나 "게임이 포커스를 쥐고 있음" 이 나오면 바로 stop 으로 게임을 끄고 보고한다.
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|peek|research|stop> …
- gamedrive.py research --out <파일> 은 게임의 메모리에서 플레이어가 보유한 기술 · 부대 설계의 번호, 플레이어의 연구 대기열, 모든 기술의 연구 기간의 합,
  플레이어의 보정 표를 그 파일에 JSON 으로 적고 한 줄을 찍는다(읽기만). research <지역 번호> --out <파일> 은 그 지역이 보유한 것과 그 지역의 보정 표를 적는다.
  독일 1499, 폴란드 1106, 덴마크 1201. 파일은 E:\SR2030ToyBox\build\verify\toybox\R-<이름>.json 으로 적는다. 찍힌 한 줄을 그대로 옮긴다.
  gamedrive.py peek 은 in_game, player(플레이하는 나라의 번호), cheats_allowed(치트 허용 비트) 등을 JSON 으로 낸다(읽기만).
- 화면 밖 게임에 보낸 조합키(key CTRL+SHIFT+T)가 듣지 않으면 한 번 더 보낸다(화면을 찍어 창이 열렸는지 본다).
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간은 9 에서만, 거기 적힌 만큼만 흘린다. 그 밖에는 일시 정지인 채로 둔다.
- 내장 치트는 하나도 넣지 않는다(게임의 설정 창의 입력줄에 아무것도 치지 않는다). ToyBox 에서는 아래에 적힌 단추만 누른다.
- ToyBox 창은 처음에 화면의 왼쪽 위(40,60)에 720x600 으로 열린다. 게임의 패널을 가리면 창을 닫고(같은 단축키) 본다.
- 게임의 연구 패널에서 연구를 거는 법(1024x768 창에서 전에 본 자리 — 달라졌으면 화면을 보고 찾는다): 아래쪽 단추 줄의 연구 패널(308,738) →
  "장관 권고" 줄의 아이콘(27,577 / 27,605)을 누르면 상세 창이 뜬다 → "연구 시작"(618,296)이나 "연구 대기열에 추가"(585,137).
  "가능한 연구"의 줄을 눌러서는 걸리지 않았다. "가능한 연구"는 탭 다섯이다: 기술 / 지상 / 공중 / 해상 / 미사일(뒤의 넷이 부대 설계다).
- 화면은 E:\SR2030ToyBox\build\verify\toybox\R-<번호>-<이름>.png 로 찍는다. ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-r\toybox.log 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다):
1. [R0] 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다(20초쯤. 빈 화면이면 기다렸다 다시 찍는다).
   로그에서 "게임 상태를 읽습니다 (…)", "값을 씁니다 (…)", "값을 더 씁니다 (…)", "연구를 씁니다 (…)", "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (…)"
   다섯 줄을 그대로 옮겨 적는다(기능의 수는 13 이어야 한다). "쓸 수 없습니다" 나 "맞지 않은 서명" 이 든 줄이 있으면 그대로 옮긴다(없어야 한다).
2. 메인 메뉴에서 ToyBox 창을 열고 "연구" 탭을 연다. 위에서부터 보이는 것을 적는다(입력란의 수, 단추 셋의 이름).
   "대기열의 연구 즉시 완료"와 "기술 수준 N 이하 전부 보유"가 흐린지(꺼져 있는지) 적는다. 한 번씩 눌러 보고 로그에 새 줄이 생겼는지 적는다(생기면 안 된다).
3. 창을 닫고, 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 게임 화면이 뜨면 일시 정지 상태인지 본다. 게임의 날짜를 적는다.
   research --out …\R-G0.json, research 1106 --out …\R-P0.json, research 1201 --out …\R-D0.json, peek 을 찍는다. cheats_allowed 는 0 이어야 한다.
4. [R1 준비] 게임의 연구 패널에서 **기술 하나**("기술" 탭의 것)와 **부대 설계 하나**("지상" 탭의 것 — 보병 · 전차 같은 부대)를 대기열에 건다.
   건 것의 이름(화면의 글 그대로)과, 화면의 대기열에 둘이 보이는지 적는다. 대기열의 화면을 찍는다.
   research --out …\R-G1.json 을 찍는다(한 줄의 "대기열 2개" 여야 한다 — 아니면 본 대로 적는다).
5. [R1] ToyBox 의 "연구" 탭에서 "대기열의 연구 즉시 완료"를 한 번 누른다. 창 바닥의 "마지막으로 쓴 값: …" 을 그대로 적는다.
   research --out …\R-G2.json, research 1106 --out …\R-P2.json, research 1201 --out …\R-D2.json, peek 을 찍는다.
   ToyBox 창을 닫고, 게임의 연구 패널을 닫았다 다시 열어 화면을 찍는다:
   (가) 화면의 대기열에 그 둘이 남아 있는가(없어야 한다). "최근 완료" 같은 칸에 나오는가.
   (나) 그 기술이 "가능한 연구"의 "기술" 탭에서 사라졌는가. (다) 그 부대 설계가 "지상" 탭에서 사라졌는가.
   (라) 그 부대를 생산할 수 있는가: 지상 부대를 주문하는 패널(생산 · 건설 쪽)의 목록에서 그 이름을 찾는다. 찾으면 화면을 찍는다 — **주문은 하지 않는다.**
        찾지 못하면 찾아본 곳(누른 자리와 화면)을 적는다.
6. [R5 준비] 연구 패널에서 다른 기술 하나를 "연구 시작"으로 건다(이름을 적는다). 화면의 대기열에 "연구 중"으로 보이는지 적는다.
   research --out …\R-G3.json 을 찍는다.
7. [R3] ToyBox 의 "연구" 탭에서 입력란이 120 인 것을 확인하고 "기술 수준 N 이하 전부 보유"를 한 번 누른다.
   누른 직후 게임이 멈칫했는지(화면이 몇 초 굳었는지) 적는다. 창 바닥의 "마지막으로 쓴 값: …" 을 그대로 적는다.
   research --out …\R-G4.json, research 1106 --out …\R-P4.json, research 1201 --out …\R-D4.json, peek 을 찍는다.
   ToyBox 창을 닫고 연구 패널을 다시 열어 "가능한 연구"의 탭마다 줄의 수가 어떻게 바뀌었는지(3 의 화면이 없으면 지금의 수만) 찍고 적는다.
   6 에서 건 기술이 대기열에 그대로 있는지 적는다(수준이 120 이하였다면 빠졌을 수 있다 — 본 대로).
8. [R4] 5 ~ 7 에서 찍은 모든 peek 의 cheats_allowed 가 0 이었는지 적는다. 게임의 설정 창(치트를 넣는 입력줄이 있는 창)이 한 번이라도 떴는지 적는다(뜨면 안 된다).
9. [R5] 화면의 대기열이 비어 있으면 "기술" 탭에 남은 기술 하나를 "연구 시작"으로 건다(이름과, 화면에 보이는 남은 기간을 적는다).
   research --out …\R-G5.json 을 찍는다. ToyBox 창을 닫은 채로 게임의 속도를 올려 **게임의 날짜가 하루 지나면 바로 일시 정지한다**(이틀을 넘기지 않는다).
   "매우 느림"은 실제 1초에 게임 5분쯤이라 하루에 5분 가까이 걸린다 — 한두 단계 빠른 속도를 고르고, 화면을 자주 찍어 날짜가 바뀌면 바로 멈춘다.
   게임이 살아 있는지, 게임의 날짜, 화면에 뜬 경고 · 오류 창을 적는다. 연구 패널을 열어 건 연구의 남은 기간이 줄었는지 적고 찍는다.
   research --out …\R-G6.json, research 1106 --out …\R-P6.json 을 찍는다.
10. 게임의 메뉴(ESC) → "게임 종료" → **저장하지 않고** 메인 메뉴로 나온다. 메인 메뉴가 정상으로 뜨는지(게임이 죽지 않았는지) 화면을 찍는다.
    gamedrive.py stop 으로 게임을 끈다. status 로 꺼진 것을 확인한다.
    로그를 E:\SR2030ToyBox\build\verify\toybox\R.log 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). research 와 peek 이 찍은 줄은 줄여 쓰지 말고 그대로. 로그에 "예외" 나 "실패" 가 든 줄이 있으면 그대로 옮긴다.
보지 못한 것은 "보지 못했다"와 까닭(찾아본 곳). 기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않고 `uv run pytest` 를 돌리지 않는다. Step 5 의 최종 검토(읽기만 하는 검토자)는 이 동안 받아도 된다.

- [ ] **Step 4: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "게임 상태를\|값을 \|연구를 \|옛 방식\|쓸 수 없습니다\|맞지 않은\|직접 실행\|예외\|실패" build/verify/toybox/R.log; grep -n "연구 완료\|연구 미완료\|묶음을 만들 수 없는" build/verify/toybox/R.log; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/R-saves-before.txt && echo "저장 폴더 그대로"; uv run python -c "import hashlib, os, pathlib; p = pathlib.Path(os.environ['APPDATA'], 'SR2030ToyBox', 'toybox.ini'); print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'none')" | diff - build/verify/toybox/R-ini-before.txt && echo "사용자의 설정 그대로"
```

Expected:
- `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`, `값을 씁니다 (…)`, `값을 더 씁니다 (…)`, `연구를 씁니다 (기술 표 +0x1829620 · 부대 설계 표 +0x1829610 · 연구 목록 +0x3568C0 · 다시 셈 +0xBDD380)`, `옛 방식(내장 치트)으로 도는 기능이 13개 남아 있습니다 (명령 처리 함수 +0x522330)` 가 한 줄씩. `쓸 수 없습니다` · `맞지 않은 서명` · `직접 실행` · `예외` · `실패` 가 든 줄이 없다.
- `연구 완료 (대기열): 기술 N개(…) · 부대 설계 1개 · 대기열에서 2개[ · 새 묶음 M개]` 한 줄(5), `연구 완료 (기술 수준 120 이하): 기술 N개(…)[ · 대기열에서 1개] · 새 묶음 M개` 한 줄(7).
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-research-engine` 이다. `저장 폴더 그대로`, `사용자의 설정 그대로`.

메모리의 스냅숏을 견준다(스크립트가 찍는 것을 그대로 `r-engine.md` 에 옮긴다):

```bash
cd /e/SR2030ToyBox && R="<스크래치>/rcheck.py" && V=build/verify/toybox && export PYTHONIOENCODING=utf-8 && for pair in "G1 G2" "P0 P2" "D0 D2" "G3 G4" "P2 P4" "D2 D4" "G5 G6" "P4 P6"; do set -- $pair; echo "== $1 -> $2"; uv run python "$R" diff $V/R-$1.json $V/R-$2.json; done; echo "== 수준 120"; uv run python "$R" level $V/R-G4.json 120
```

Expected — 이 가운데 하나라도 아니면 멈춘다(아래 "전제가 틀리면"):

| 견줌 | 봐야 하는 것 |
|---|---|
| `G1 -> G2` (R1 · R2) | 기술: 건 기술(과 보유하지 않았던 선행)만 더해졌다, 빠진 것 0. 부대 설계: 건 설계 하나만 더해졌다(그 선행 기술이 기술 쪽에 더해졌을 수 있다). **연구 기간의 합 그대로.** 대기열: 두 노드의 깃발 둘의 첫 글자가 모두 `8` 이상(`0x80000000` 이 켜졌다)이고 나머지 비트는 그대로. 보정 표: 더해진 기술에 효과가 있으면(`rcheck.py tech <번호…>`) `mul` · `add` 나 보정 칸이 바뀌었다 — 바뀐 칸의 번호 · 변화량을 그 기술의 효과 번호 · 값과 나란히 적는다(같은지는 본 대로. 효과가 없는 기술만 더해졌으면 "그대로"가 맞다) |
| `P0 -> P2`, `D0 -> D2` (R1 · R2) | 기술 · 부대 설계 · 묶음이 없는 항목 · 연구 기간의 합 · 보정 표 `mul` · `add` · 보정 칸이 **모두 그대로**(일시 정지 중이다). 대기열(플레이어의 것)은 `G1 -> G2` 와 같다 |
| `G3 -> G4` (R3) | 기술: 더해진 것만 있다(수십 개), 빠진 것 0. **부대 설계 그대로.** 묶음이 없는 기술의 수가 줄었다(새 묶음 — 로그의 `새 묶음 M개` 와 같은 수). 연구 기간의 합 그대로. 보정 표가 바뀌었다 |
| `수준 120` | `수준 120 이하의 기술 N개 가운데 보유하지 않은 것 0개`. (`보유한 기술 가운데 수준이 120 보다 높은 것`은 0 이 아니어도 된다 — 처음부터 보유했거나 선행으로 딸려 온 것이다. 번호를 `G0` 과 견줘 적는다) |
| `P2 -> P4`, `D2 -> D4` (R3) | 모두 그대로 |
| `G5 -> G6` (R5) | 기술 · 부대 설계: 빠진 것 0(그사이 연구가 자연히 끝났으면 그것만 더해진다). 연구 기간의 합 그대로. 대기열: 9 에서 건 연구의 노드가 살아 있다(깃발의 첫 글자가 `8` 미만) |
| `P4 -> P6` (R5) | 하루가 흘렀다 — 폴란드가 스스로 연구를 끝냈으면 더해진 것이 있을 수 있다. **빠진 것 0**, 연구 기간의 합 그대로 |

Read 도구로 화면을 직접 본다: 4 의 대기열, 5 의 (가) ~ (라), 7 의 "가능한 연구", 9 의 남은 기간, 10 의 메인 메뉴. 에이전트가 적은 글 · 숫자와 화면이 같은지 본다.

**전제가 틀리면 멈춘다** — 머지하지 않고, 본 것을 그대로 사용자에게 알린다(설계서의 "아직 보지 않은 것"에 적힌 대로):
- ① 메모리는 기대대로인데 연구 화면이 그대로다 · 그 부대가 생산 목록에 없다 → 패널을 다시 연 화면까지 본 뒤에도 그러면 멈춘다. (나)를 쓰기 전에 설계를 고쳐야 한다.
- ② 다시 셈에서 예외(로그의 `효과를 다시 셈하는 중 예외`), 다른 지역의 보정 표가 바뀌었다, 플레이어의 보정 표가 말이 안 되는 값이 됐다 → 멈춘다. 호출을 빼는 쪽("효과는 내 연구가 자연히 끝날 때나 불러온 뒤에 반영된다")을 사용자에게 묻는다.
- ③ 깃발을 켰는데 화면의 대기열에 남아 있다 · 새로 건 연구가 진행되지 않는다 → 멈춘다. 설계서의 물러설 길(치트처럼 `0x08000000` 만 / 대기열을 건드리지 않는다)을 사용자에게 묻는다.
- ④ 게임이 죽었다(하루를 흘리는 동안, 메인 메뉴로 나올 때) · `연구 쓰기 실패` 가 나왔다 · 다른 나라의 보유가 바뀌었다 · 연구 기간의 합이 바뀌었다 → 멈춘다.

게임 화면에서 찾지 못한 것(예: 생산 목록)은 [확인: 실행](메모리만 봤다)으로 적고 이어 간다 — 다만 ① 의 "생산할 수 있는가"를 화면으로 보지 못했으면 그 사실을 PR 의 댓글과 사용자에게 분명히 알린다(사용자가 처음에 알린 문제가 그것이다).

- [ ] **Step 5: 코드의 최종 검토를 받고 고친다**

범위는 이 브랜치가 `develop` 에서 갈라진 곳부터 머리까지다(`git merge-base develop HEAD`). 실행 방식의 최종 검토 절차대로 받는다 — 검토자에게 이 문서의 Review Focus 와 "설계서와 달라진 곳", 설계서, 그리고 게임 안 확인에서 본 것(`r-engine.md` 의 초안)을 함께 준다. Critical · Important 를 고친다 — 고칠 때마다 실패하는 테스트를 먼저 쓴다. Minor 는 고치지 않고 적어 둔다.

고친 것이 있으면: `uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -1` 로 통과를 보고 커밋한다. 고친 것이 게임 안의 동작(쓰는 칸 · 쓰는 순서 · 함수 호출)을 바꾸면 Step 3 의 해당 단계만 다시 본다(게임을 한 번 더 띄워야 하므로, 화면의 글만 바뀌는 고침은 자동 테스트로 갈음하고 그렇게 적는다).

- [ ] **Step 6: 최종 빌드를 넣고, 결과를 PR 에 적고, 머지한다**

```bash
cd /e/SR2030ToyBox && uv run python scripts/gamedrive.py status | head -1 && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -1 && uv run srkit deploy toybox
```

Expected: `프로세스: 없음`, `빌드 완료: …`, 통과. 미리보기는 Step 2 뒤로 코드를 고쳤으면 `갱신: srtoybox.dll` 한 줄(→ `uv run srkit deploy toybox --apply`), 고치지 않았으면 0개 파일이다. 다른 줄이 있으면 멈춘다.

스크래치에 `r-engine.md` 를 쓴다(Write 도구): 단계마다 한 것 / 본 것 / 근거 화면의 이름(R0 ~ R5 의 번호로), `research` 가 찍은 줄과 `rcheck.py` 가 찍은 것 그대로, 로그의 줄 그대로, 건 기술 · 부대 설계의 이름과 번호, 보정 표의 바뀐 칸과 그 기술의 효과(같았는지), "기술 수준 120 이하"가 더한 기술의 수 · 새 묶음의 수 · 걸린 시간, 하루 뒤의 상태, 보지 못한 것, 설계의 전제 넷(①~④)을 하나씩 — 본 것과 판정, 최종 검토의 결과(고친 것 · 미룬 Minor). `gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/r-engine.md"` 로 PR 에 단다.

```bash
cd /e/SR2030ToyBox && git push && gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && git switch develop && git pull --ff-only origin develop && git log --oneline -1 && uv run srkit deploy toybox | tail -1
```

Expected: 머지 커밋이 `develop` 의 머리다. 게임 폴더에는 최종 빌드가 들어 있다(미리보기 0개 파일) — 설치된 "대기열의 연구 즉시 완료"가 부작용(모든 나라의 연구 기간 1일) 없는 것으로 바뀌었다.

---

### Task 9: 문서

**브랜치:** `docs/toybox-research-engine` (Task 8 의 PR 이 들어간 `develop` 에서 나눈다)

**Files:**
- Modify: `docs/10-toybox.md`, `docs/11-game-internals.md`, `docs/05-game-systems.md`, `docs/07-cheats.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-10-10-toybox-stage3-3-design.md`(끝에 "보완 내역" 한 절)

**Interfaces:**
- Consumes: Task 8 의 `r-engine.md`(본 것 · 보지 못한 것 · 전제 넷의 판정 · 최종 검토의 결과), 이 계획의 "설계서와 달라진 곳" · "계획을 쓰며 확인한 것".
- Produces: 문서. 게임 안에서 보지 않은 것은 "보지 못했다"로 적는다 — `r-engine.md` 에 없는 것을 본 것처럼 쓰지 않는다. 이 문서들은 (나)(목록)의 계획이 딛는 바닥이다.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-research-engine && git log --oneline -1
```

- [ ] **Step 2: `docs/10-toybox.md`**

1. "무엇인가": 3단계 문단의 "지금까지 옮긴 것"에 **연구 탭의 단추 둘**(대기열의 연구 즉시 완료 · 기술 수준 N 이하 전부 보유 — 3단계 3 (가), 날짜)을 더하고, "내장 치트로 도는 기능은 13개다"로 고친다. 묶음 3 은 (가)가 끝났고 (나)(연구의 목록)가 남았다고 적는다.
2. "쓰는 법": 두 단추가 내장 치트를 거치지 않는다는 것 — 이름 · 탭 · 자리는 그대로이고, 누르면 바로 바뀌며 창 바닥에 `마지막으로 쓴 값: 기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열` 같은 한 줄이 나온다. **전과 달라진 것 넷**을 눈에 띄게 적는다: 대기열의 **부대 설계도 끝난다** / 다른 기술의 연구 기간을 건드리지 않는다(전에는 모든 나라의 모든 기술이 1일이 됐다) / 끝낸 것이 화면의 대기열에서 빠진다 / "기술 수준 N 이하"가 선행 기술도 함께 준다. 입력란은 1 ~ 255. 게임의 설정 창이 뜨지 않고 치트 허용 비트가 그대로다. 게임 밖에서는 꺼져 있다. 검증 번호는 `r-engine.md` 의 R 번호로 단다.
3. "기능"의 표: 두 줄의 "게임에 넣는 것" 칸을 "없다 — 보유 비트를 직접 쓴다(내장 치트가 아니다)"로, 효과 칸을 본 대로, 검증 칸을 `[확인: R1]` · `[확인: R3]` 로 고친다. 표 아래의 문단: 내장 치트로 도는 수 15 → 13. 지운 치트에 `technology` · `e=mc2` 를 더한다.
4. "한계"에 더한다(본 대로 고쳐 적는다):
   - **이미 내장 치트로 "대기열의 연구 즉시 완료"를 누른 판**은 모든 기술의 연구 기간이 1일인 채다(본래 값이 판에 남아 있지 않다). 새 단추는 그 판의 대기열에 남은 "끝냄" 노드를 정리한다(자동 테스트만 봤다).
   - ToyBox 가 부르는 게임의 함수는 "효과를 다시 셈" 하나다(플레이어 지역으로만). 거기서 오류가 나면 ToyBox 가 멈추고 빨간 경고가 뜬다 — 저장하지 말고 게임을 다시 시작한다.
   - 아무도 보유하지 않던 기술에는 ToyBox 가 새 묶음(128바이트)을 건다 — 게임과 같은 힙의 같은 꼴이다. 저장 → 불러오기는 보지 않았다.
   - 한 번이라도 쓰기가 실패하면 연구만이 아니라 돈 · 물자 · 유지 · 직접 쓰는 줄 넷도 그 실행 내내 꺼진다.
   - 연구 묶음은 서명 21개가 **모두** 맞아야 한다 — 게임이 업데이트되면 다른 기능보다 먼저 꺼질 수 있다(꼴이 바뀐 빌드에서 엉뚱한 칸에 쓰지 않으려는 것이다).
   - 지역 마스크가 맞지 않는 기술(다른 지역 전용 [추정])도 "기술 수준 N 이하"가 준다(치트와 같다).
   - 게임 화면은 그 패널을 닫았다 열 때 따라온다(본 대로 — R1).
   - 화면에서 보지 못한 것(예: 생산 목록)을 그대로 적는다.
5. "구조"의 표: `locate`(연구 묶음 — 서명 21개, 셋이 모두) · `research`(새 줄: 순수한 규칙) · `game`(연구의 스냅숏과 쓰기, 다시 셈) · `keeper`(연구 요청의 줄) · `runner_win`(게임의 함수를 부를 때의 깃발과 가드) · `features`(19줄 가운데 직접 쓰는 여섯, 내장 치트로 도는 13) · `ui` 의 줄을 고친다. "게임 읽기 · 값 쓰기" 문단의 "쓰는 곳"을 새 목록으로 고치고 "부르는 함수"를 한 줄 더한다.
6. 로그의 표에 더한다: `연구를 씁니다 (…)` · `연구를 쓰지 않습니다 (SRTOYBOX_WRITE=0. …)` · `연구를 쓸 수 없습니다 (…)` · `연구 완료 (대기열): …` · `연구 완료 (기술 수준 120 이하): …` · `연구 완료 (대기열): 바꿀 것이 없습니다` · `묶음을 만들 수 없는 게임 판입니다 — …` · `연구의 표를 읽을 수 없습니다 (…)` · `연구 쓰기 실패 (…) — 값 쓰기를 끕니다` · `효과를 다시 셈하는 중 예외 0x… — ToyBox 를 멈춥니다`. `옛 방식 … 15개` 를 `13개` 로.
7. "확인한 것": 새 표 **"3단계 3 (가) — 연구의 엔진"**(`r-engine.md` 에서. 번호 R0 … R5, 칸은 앞 표와 같다: # · 한 것 · 본 것 · 근거). 설계서의 "아직 보지 않은 것" 1 ~ 4 를 표 아래에 하나씩 — 본 것과 판정. 보지 못한 것을 따로 적는다(`SRTOYBOX_WRITE=0`, 묶음을 못 찾았을 때, 힙이 다른 게임, 다시 셈의 예외는 자동 테스트만 — 설계서 그대로).
8. "문제가 생기면": 단추 대신 `대기열의 연구 즉시 완료 — 이 게임 판에서는 쓸 수 없습니다 (…)` 가 보일 때 할 일(`uv run srkit locate` → 깨진 서명을 `sig-mine` 으로 다시 뽑는다 — [11](11-game-internals.md). 연구는 서명 하나만 깨져도 꺼진다). 빨간 경고 `효과를 다시 셈하는 중 오류가 났습니다. …` 가 떴을 때(저장하지 않고 다시 시작, 로그의 예외 코드).
9. "다음 단계"의 표: 묶음 3 을 "(가) 끝 · (나) 목록이 남음"으로 고친다.

- [ ] **Step 3: `docs/11-game-internals.md` · `docs/05-game-systems.md` · `docs/07-cheats.md`**

`docs/11`:
1. "전역과 필드"에 새 절 **"연구 — 기술 · 부대 설계의 표와 연구 목록"**: 설계서의 "게임이 연구를 담는 꼴"의 표 넷(전역 · 기술 레코드 · 부대 설계 레코드 · 노드)을 옮기고, R1 ~ R3 에서 본 것에 [확인: 게임]/[확인: 실행]을 단다. 지역의 보정 표(곱 200칸 — 세계 객체 `+0x5456a8` + 인덱스 × `0x320`, 합 176칸 — `+0x60d6a8` + 인덱스 × `0x2c0`, 지역 객체 `+0x14d38`)와, R2 에서 본 "효과 번호 → 바뀐 칸"의 대응(본 만큼만).
2. 새 절 **"게임이 연구를 끝내고 빼는 함수"** [확인: 정적]: `0x6f52c0` · `0x6f5430` · `0x6f55f0` · `0x6fc5d0` · `0xbdd380` · `0x750f10` 의 하는 일(설계서의 표). `0xbdd380` 은 다른 함수를 부르지 않고 끝에서 `0x52fb30` 으로 뛴다는 것. 묶음을 받는 `0xc11900` 은 UCRT 의 `calloc` 이라는 것. **ToyBox 가 부르는 것은 `0xbdd380` 하나**(플레이어의 인덱스로)이고 R2 에서 본 것.
3. "주소를 찾는 법"에 새 절 **"새 찾기 — 연구 (3단계 3 부터)"**: 이 계획의 "계획을 쓰며 확인한 것"의 서명 표와 "상수 → 서명"의 표를 싣는다. 규칙이 다른 점을 적는다 — 셋이 모두 맞아야 한다 · 세계 객체의 서명은 지역 표까지의 거리도 읽는다 · 다시 셈 함수는 함수의 시작이어야 한다 · 값 묶음의 세계 자료 포인터와 겹치면 연구 묶음을 버린다. 다시 뽑는 법:

   ```
   uv run srkit sig-mine 1829620 --with 88 50 80 --most 16 --longest 64 --sites 2500     # 기술 표(준다: 크기 · 보유 묶음 · 묶음의 크기)
   uv run srkit sig-mine 1829620 --with 88 50                                            # 기술 표(뺀다)
   uv run srkit sig-mine 1829620 --with 1 --sites 2500                                   # 기술 표(수준)
   uv run srkit sig-mine 1829098 --with 4 6 --most 16 --longest 64                       # 기술 수(선행)
   uv run srkit sig-mine 1829610 --with 168 f8 80 --most 16 --longest 64 --sites 2500    # 부대 설계 표(크기 · 보유 묶음 · 묶음의 크기)
   uv run srkit sig-mine 1829610 --with f0 ec 20 --most 16 --longest 64 --sites 2500     # 부대 설계 표(깃발 둘 · 연구 대상)
   uv run srkit sig-mine 182909c --with 168                                              # 부대 설계 수(크기)
   uv run srkit sig-mine 182909c --with 34 --most 16 --longest 64                        # 부대 설계 수(선행)
   uv run srkit sig-mine 17a9020 --with 34e8a0                                           # 세계 객체 — 그 4바이트를 [u32] 로 바꿔 적는다
   uv run srkit sig-mine 3568c0 --offset --with 1c 18 10 20 --back 1 --most 26 --longest 64 --through-jumps   # 연구 목록(깃발 1)
   uv run srkit sig-mine 3568c0 --offset --with 1c 18 24 --most 26 --longest 64 --through-jumps               # 연구 목록(깃발 2)
   uv run srkit sig-mine bdd380 --back 2                                                 # 다시 셈 함수(그것을 부르는 자리)
   ```

   후보 가운데 서로 다른 함수의 것 셋을 고르고(명령을 읽어 뜻이 같은 코드인지 본다), `tests/test_toybox_game.py` 의 `RESEARCH_PINS` 를 새 서명에 맞춘다. 올라와 있는 게임에서도 21개가 맞았는지는 R0 의 로그로 [확인: 실행].
4. "이번에 알게 된 치트의 사실"에 더한다 [확인: 정적 + 게임]: `technology N`(1 ~ 255. 수준 N 이하인 기술의 비트만 — 선행도 부대 설계도 보지 않는다. 끝에 `0xbdd380(−1)`) / `e=mc2`(대기열의 **기술**만. **대기열에 없는 모든 기술의 연구 기간을 1.0 으로** — 모든 나라가 함께 쓰는 표다. 끝낸 노드를 대기열에서 빼지 않는다) / `stresstest` / `allunit`.
5. "보지 않은 것"을 고친다: 본 것을 지우고 남은 것을 적는다(저장 → 불러오기 뒤의 묶음, 미완료로 되돌리기 — (나), 지역 마스크, DLC 의 판, 다른 빌드, 보정 표의 칸과 효과 번호의 대응 가운데 보지 못한 것).

`docs/05`: "연구" 절에 — 게임의 "연구"가 둘(기술 · 부대 설계)이고 따로 저장된다는 것, 설계를 보유하면 그 선행 기술도 보유한다는 것, 기술의 효과는 지역마다 미리 계산해 둔 표로 쓰인다는 것([11](11-game-internals.md)), 2030 - 세계 · 독일에서 본 수(기술 1054 가운데 보유 762, 부대 설계 7490 가운데 보유 442 — 설계서의 표). `technology` · `e=mc2` 를 적은 곳에 "ToyBox 는 3단계 3 부터 이 치트를 쓰지 않는다([10](10-toybox.md))"를 덧붙인다.

`docs/07`: `cheat technology` 와 `cheat e=mc2` 줄의 효과 칸에 설계서의 "치트가 하는 일"에서 본 것을 더한다 — `technology`: **부대 설계는 그대로다**(기술 763 → 808, 부대 설계 442 그대로) / `e=mc2`: **기술만 끝낸다(건 부대 설계는 이틀 뒤에도 "연구 중")**, **기술 1054개 가운데 1053개의 연구 기간이 1일이 된다 — 모든 나라의 것이다**, 끝낸 기술이 화면의 대기열에 남는다. **표의 꼴(여섯 칸)과 끝 칸의 `[확인: 효과]` 는 그대로 둔다**(`tests/test_toybox.py` 가 이 표를 기능 표와 대조한다). 표 아래에 "ToyBox 는 3단계 3 부터 이 둘을 쓰지 않는다"를 한 줄.

- [ ] **Step 4: `docs/09` · `README.md` · `CLAUDE.md` · 설계서**

- `docs/09-cheat-mod-plan.md`: 로드맵의 3단계 줄에 묶음 3 (가)의 완료와 날짜, 남은 수(13). 표의 `technology` · `e=mc2` 줄에 "치트는 그대로다. ToyBox 는 3단계 3 부터 쓰지 않는다 — 보유 비트를 직접 쓴다([10](10-toybox.md))"를 적는다.
- `README.md`: 현재 상태의 3단계 문단(연구 탭의 두 단추가 내장 치트를 떠났다. 내장 치트로 도는 기능 15 → 13. 대기열의 부대 설계도 끝난다).
- `CLAUDE.md`:
  - "명령"에 한 줄: `gamedrive.py research [지역 번호] [--out 파일]` — 자기가 띄운 게임의 메모리에서 그 지역(없으면 플레이어)이 보유한 기술 · 부대 설계, 플레이어의 대기열, 연구 기간의 합, (이 빌드에서만) 보정 표를 읽는다(읽기만). ToyBox 가 연구를 쓴 것을 확인할 때는 창의 글이 아니라 이것의 앞뒤를 견준다.
  - "게임이 업데이트된 뒤에는" 줄: `srkit locate` 가 연구 묶음도 본다는 것과 `sig-mine <함수의 RVA>`(함수의 목표) · `--with <상수…>`(꼴의 상수)를 덧붙인다.
  - "지켜야 할 것"의 "ToyBox 가 게임의 메모리에 쓰는 곳은 …" 줄에 연구를 더한다: **기술 · 부대 설계의 보유 비트 묶음에서 플레이어의 비트, 묶음이 없는 항목의 포인터 칸(새 묶음을 걸 때), 플레이어의 연구 목록 노드의 깃발 두 칸**. 그리고 한 줄을 더한다: **ToyBox 가 부르는 게임의 함수는 "지역의 효과를 다시 셈" 하나뿐이다 — 플레이어 지역으로만, 예외 가드 안에서**(치트 명령 처리 함수는 옮기지 않은 기능의 전환 기간에만). 부르는 함수를 늘릴 때는 설계서에서 정한다.
- 설계서(`docs/superpowers/specs/2026-10-10-toybox-stage3-3-design.md`)의 "상태" 줄을 "(가) 구현 끝(날짜) · (나) 계획을 기다린다"로 고치고, 끝에 절 **"보완 내역 (계획 (가)를 쓰고 실행하며)"** 를 더한다: 이 계획의 "설계서와 달라진 곳"을 옮기고 [계획](../plans/2026-10-10-toybox-stage3-3a-research-engine.md)을 가리킨다. "아직 보지 않은 것" 1 ~ 4 를 본 대로 적는다(판정과 근거의 R 번호). (나)에 넘기는 것을 적는다: 스냅숏을 0.5초마다 뜨는 일 · 부대 설계의 이름 · 고른 나라의 열 · 미완료의 단추 · R6 ~ R11. 최종 검토가 남긴 것(미룬 Minor)을 적는다.

- [ ] **Step 5: 링크와 사실을 대조하고 커밋 · PR · 머지**

```bash
cd /e/SR2030ToyBox && PYTHONIOENCODING=utf-8 uv run python "<스크래치>/linkcheck.py" . 2>&1 | grep -v "docs/superpowers/plans/" | tail -3; grep -n "15개\|15 개\|cheat e=mc2\|cheat technology" docs/10-toybox.md README.md CLAUDE.md | head -20; uv run pytest -q 2>&1 | tail -1
```

Expected: 계획 문서 밖의 깨진 상대 링크가 없다(`linkcheck.py` 는 앞 계획에서 쓴 스크래치의 스크립트다 — 없으면 `docs/` · `README.md` · `CLAUDE.md` 의 `](…)` 링크가 가리키는 파일이 있는지 보는 열 줄짜리를 다시 쓴다). 남은 `15개` · `cheat e=mc2` 는 지난 단계의 기록(확인한 것의 표, 07 을 가리키는 줄)뿐이다. 테스트는 Task 8 의 끝과 같은 수가 통과한다(문서만 바꿨다 — `docs/07` 의 표를 고쳤으므로 기능 표와의 대조 테스트가 그대로 통과하는지가 이 줄이다).

```bash
cd /e/SR2030ToyBox && git add docs README.md CLAUDE.md && git commit -q -F - <<'EOF'
docs: ToyBox 3단계 3 (가) — 연구 탭의 두 단추를 내장 치트 없이, 게임에서 본 것

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox-research-engine
```

스크래치에 `pr-docs-research-engine.md` 를 쓰고(무엇을 고쳤나의 표, 게임에서 본 것과 보지 못한 것, 설계의 전제 넷의 판정, `uv run pytest` 결과), PR 을 올려 머지한다:

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/toybox-research-engine --title "docs: ToyBox 3단계 3 (가) — 연구의 엔진" --body-file "<스크래치>/pr-docs-research-engine.md"
```

```bash
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git log --oneline -3
```

---

## 끝난 뒤의 상태

- `develop` 에 PR 셋(이 계획 문서와 설계서 · 코드 · 문서)이 들어가 있다. `uv run pytest` 559개 통과(최종 검토에서 테스트가 더해졌으면 그만큼 더). 게임 폴더에는 최종 빌드의 `srtoybox.dll` 이 있고 그 밖의 게임 파일은 그대로다.
- 사용자의 `%APPDATA%\SR2030ToyBox` 설정은 그대로다. 설정 파일에 더하는 것은 없다 — 다만 `technology`(기술 수준의 입력값)의 범위가 1 ~ 255 로 줄어, 255 보다 큰 값을 저장해 둔 사용자는 다음에 읽을 때 기본값 120 이 된다.
- **묶음 3 의 (가)가 끝난다.** 내장 치트로 도는 기능은 13개가 남는다(인구 · 여론 2, 외교 · 영토 6, 부대 3, 화면 · 진행 2). 사용자가 처음에 알린 문제(대기열의 부대 설계가 끝나지 않는다)는 R1 에서 본 만큼 풀렸다.
- **다음**: 계획 (나) — 연구의 목록(기술 · 부대 설계, 자국의 상태와 타국의 보유, 거르개, 고른 것 / 보이는 것 전부를 완료 · 미완료로, 게임 안 확인 R6 ~ R11). Task 8 에서 설계의 전제 넷이 모두 섰을 때 쓴다 — 하나라도 어긋났으면 먼저 사용자와 설계서를 고친다.
- **이 계획이 미룬 것**: 미완료의 단추(규칙과 쓰기는 들어 있고 자동 테스트가 본다 — 창에서 부르는 것은 (나)), 스냅숏을 창에 넘기는 일, 부대 설계 · 기술의 이름. 앞 묶음의 최종 검토가 남긴 것들은 그대로다.
