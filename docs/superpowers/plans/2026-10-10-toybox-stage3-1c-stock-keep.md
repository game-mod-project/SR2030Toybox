# ToyBox 3단계 1 (다) — 물자 탭과 최소 유지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ToyBox 의 "물자" 탭이 내장 치트를 거치지 않고 플레이어의 물자 재고를 물자마다 고치고(`-1억` · `-100만` · `0` · `+100만` · `+1억`, "모든 물자" 줄), 국고와 물자마다 "최소 유지"를 켤 수 있다 — 값이 정해 둔 수준보다 적어지면 그 수준으로 올린다(0.5초마다, 설정 창을 닫아도, 게임을 다시 켜거나 새 판을 시작해도). 물자의 치트 단추 셋을 지운다(내장 치트로 도는 기능 22 → 19).

**Architecture:** 계획 (나)가 깐 바탕(값의 자리 찾기 `locate_values`, 읽기 · 쓰기 `game`, 값 계산 `values`, 요청의 대기열 `keeper`) 위에 화면과 유지 검사만 얹는다. 물자 이름은 빌드할 때 번역 표에서 만든 표(`products`)에서 오고, 물자 탭은 기능 표가 아니라 전용 화면(`stock_tab`)이 그린다. 최소 유지는 `keeper` 가 게임 창의 타이머에서 0.5초마다 바닥 요청(`Change::Floor`)을 내는 것이고, 켜짐과 값은 `toybox.ini` 에 저장되며, 창 맨 위의 상태 줄이 무엇이 유지되는지 늘 보인다.

**Tech Stack:** C++17 (MSVC `/W4 /WX /EHsc`), Dear ImGui 1.92.9b, Python 3.13 + ctypes + pytest (`uv run`), Win32.

**Spec:** `docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md` (승인 2026-10-09). 이 계획은 그 문서의 "작업 순서와 브랜치" **4**(물자 이름표, 물자 탭, 물자의 치트 세 줄 삭제) · **5**(유지, 설정, 상태 줄)와 **6** 가운데 남은 문서(`docs/05` 포함)를 구현한다. 1 · 2 는 [계획 (가)](2026-10-09-toybox-stage3-1a-independent-locate.md), 3 은 [계획 (나)](2026-10-09-toybox-stage3-1b-values-money.md)에서 끝났다. 이 계획이 끝나면 묶음 1(기반 + 돈 · 물자)이 끝난다.

## Global Constraints

- 응답 · 주석 · 문서는 한국어. Python 은 `uv run` 으로만. 코드를 고치면 `uv run pytest`.
- **이 문서의 RVA 와 자리는 모두 build `21347933`(게임 12.1.1360, `SupremeRuler2030.exe` 의 PE TimeDateStamp `0x695377b6`)의 것이다.** 문서 · 코드에 적을 때는 빌드 번호를 함께 적는다. 제품 코드에는 RVA 도 구조체 안의 자리도 적지 않는다(서명이 읽어 낸다 — 계획 (가) · (나)).
- **요구 3 — 내장 치트와 별도.** 물자 탭과 최소 유지의 어떤 동작도 치트 명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다. 치트 닻을 쓰는 곳은 지금의 셋 그대로다: `locate_legacy`(전환 기간), `srkit.sigmine`(개발용), `tests/toybox_cheat_oracle.py`(테스트의 대조).
- **무엇을 찾지 못하거나 쓰지 못할 때 내장 치트로 되돌아가지 않는다.** 돈 · 물자 탭에는 까닭 한 줄만 보이고, 최소 유지는 쉰다.
- **게임의 메모리에 쓰는 곳은 플레이어 지역 객체의 국고 1칸과 재고 12칸뿐이다**(`game.h`). 이 계획은 쓰는 곳을 늘리지 않는다 — 최소 유지도 같은 두 함수(`game_write_treasury` · `game_write_stock`)로 쓴다. 쓰기 직전의 확인(게임을 진행 중이다 · 멀티플레이가 아니다 · 그 칸이 쓰는 물자다 · 쓸 값이 유한한 수다 · 쓸 자리가 `PAGE_READWRITE` 다)은 그 함수들이 한다.
- **요구 2 — 플레이어의 나라에만.** 최소 유지는 지금 플레이하는 나라의 값만 본다. 나라가 바뀌면 그 뒤로는 새 나라의 값을 보고, 앞의 나라는 건드리지 않는다.
- **게임 설치 폴더를 바꾸는 길은 `uv run srkit deploy toybox --apply` 하나다.** 먼저 `uv run srkit deploy toybox` 로 미리보기를 보고, `갱신: srtoybox.dll` 한 줄만 있을 때 `--apply` 한다. 다른 줄이 있으면 멈춘다. 한글화 훅(`WTSAPI32.dll`)은 고치지 않는다. (설계서의 승인이 이 바꿔 넣기의 승인을 포함한다.)
- 실행 파일의 바이트 · 디스어셈블리 덤프 · 게임 파일을 저장소에 넣지 않는다. 물자 이름표의 생성물(`build/toybox-obj/products_table.inc`)은 저장소에 넣지 않는다(지역 이름표와 같다).
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. 표기 [확인: 정적] / [확인: 실행] / [확인: 게임] / [추정].
- 게임은 `uv run python scripts/gamedrive.py start` 로 화면 밖에서, 백그라운드 작업으로 띄운다. 게임 안을 돌아다니는 확인은 백그라운드 에이전트에 맡긴다. 사용자가 켠 게임은 건드리지 않는다. **게임을 저장하지 않는다.** 한 판에서 게임 시간을 3일 넘게 흘리지 않는다(7일마다 자동 저장된다). 게임이 떠 있는 동안 브랜치를 바꾸지 않는다.
- **검증용 게임은 `SRTOYBOX_HOME` 을 임시 폴더(`build/verify/…`)로 돌려 띄운다.** 최소 유지는 저장되는 설정이다 — 사용자의 실제 `%APPDATA%\SR2030ToyBox\toybox.ini` 에 켜진 채로 남으면 사용자의 판에 적용된다. **이 계획에서는 Steam 으로 띄우지 않는다**(Steam 으로 띄운 게임은 실제 설정을 읽는다. 서명이 Steam 으로 띄운 게임에서도 맞는 것은 계획 (나)의 VB-S 에서 봤다).
- **`cheat resettutorial` 과 `cheat depopulate` 는 어떤 경우에도 넣지 않는다.**
- Git: `main` · `develop` 에 직접 커밋하지 않는다. `develop` 에서 브랜치를 나눠 PR → merge commit. CI 가 없으므로 PR 본문에 `uv run pytest` 결과를 적는다. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, PR 본문 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- PR 은 `gh pr create --repo game-mod-project/SR2030Toybox --base develop --head <브랜치> --title "<제목>" --body-file <본문 파일>` 로 올리고 `gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge` 로 머지한다. 본문 파일은 스크래치에 Write 도구로 쓴다. **머지 명령이 권한 분류기에 거부되면 다른 형태로 우회하지 않는다** — 사용자에게 그 명령을 그대로 건네고, 머지된 뒤 `git switch develop && git pull --ff-only origin develop` 로 이어 간다.
- Bash heredoc 은 `\\` 를 `\` 로 뭉갠다. 역슬래시가 든 파일 · 스크립트는 Write/Edit 도구로 쓴다. 파이프 출력은 CP949 라 한글을 찍는 스크립트에는 `sys.stdout.reconfigure(encoding="utf-8")`.
- C++ 은 `/W4 /WX` 다: 부호가 다른 비교, 쓰지 않는 함수 · 변수, 초기화되지 않았을 수 있는 변수가 모두 빌드 오류가 된다.
- **창과 로그에 보이는 새 글에는 한글 · ASCII · `·` · `—` 만 쓴다**(`→` `–` `−` 를 쓰지 않는다 — 계획 (나)와 같다). 빼기 단추는 `-1억`, 로그는 `유지: 석유 2.5 M -> 5.0 M`.
- **시작할 때의 테스트 상태**: `develop`(`8991bd1`)에서 `uv run pytest` 305개 통과.
- **화면 검사 테스트의 흔들림은 PR #37 에서 고쳤다**(검사 도구의 가짜 수정키가 실제 수정키 입력에 지워지던 것). 이 계획의 코드로 ToyBox 테스트 전체를 이어서 세 번 돌렸을 때 결과가 세 번 다 같았다. 화면 검사 테스트가 실패하면 "흔들림"으로 넘기지 않고 원인을 본다. 테스트는 다른 무거운 일(빌드)과 함께 돌리지 않는다 — 검사 프로세스가 DLL 사본을 뜨는 중에 DLL 이 바뀐다.

## 고칠 곳을 읽는 법

Task 1 ~ 4 · 6 ~ 8 의 코드는 **"고칠 곳"** 으로 적었다. 꼴은 다섯 가지이고, 찾을 글은 그 파일에 정확히 한 번 나온다(문맥을 그만큼 넓혀 뒀다). 한 Task 안에서는 적힌 순서대로 옮긴다.

| 꼴 | 뜻 |
|---|---|
| 새 파일 `경로`: + 블록 | 그 내용으로 파일을 만든다 |
| `경로` 를 통째로 다음으로 바꾼다: + 블록 | 파일 전체를 그 내용으로 바꾼다 |
| `경로` 에서 다음을 찾아: + 블록 / 이렇게 바꾼다: + 블록 | 첫 블록을 둘째 블록으로 바꾼다 |
| `경로` 에서 다음 바로 뒤에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 다음 줄에 둘째 블록을 끼운다 |
| `경로` 에서 다음 바로 앞에: + 블록 / 이것을 더한다: + 블록 | 첫 블록 바로 앞에 둘째 블록을 끼운다 |

블록 끝의 빈 줄도 글의 일부다(함수 사이의 빈 줄 둘을 지키려고 그렇게 적었다). 손으로 옮겨도 되고, 옮겨 적는 도구로 옮겨도 된다 — 계획을 쓰며 만든 스크래치의 `apply_plan.py <이 문서> <저장소 루트> <Task 번호> <test|code>` 가 이 문서의 블록을 그대로 읽어 옮긴다(`<!-- 고칠 곳: … -->` 표시 사이. 찾을 글이 한 번이 아니면 아무것도 쓰지 않고 멈춘다). 도구는 저장소에 넣지 않는다.

## 설계서와 달라진 곳 (계획을 쓰며)

- **PR 은 설계서대로 둘(`feat/toybox-values-stock` · `feat/toybox-values-keep`)과 문서 하나다. 코드의 최종 검토는 둘째 PR 을 머지하기 전에 한 번, 두 PR 의 차이 전체(`8991bd1` 부터)를 놓고 받는다**(Task 9). 첫 PR 은 게임 안 확인(V5 ~ V7)을 거쳐 먼저 머지한다 — 둘째가 그 위에 선다.
- **V5 · V6(칸과 이름의 대응, 열두째 칸)은 물자 탭이 선 뒤(Task 5)에 본다.** 설계서는 작업 순서 4 의 "첫 일"이라 했으나, 한 칸씩 올려 보려면 누를 단추가 있어야 한다. 이름표는 추정(번역 표의 물자 목록 순서 = 재고 칸의 순서)대로 만들어 두고, Task 5 에서 하나라도 다르면 머지 전에 멈춘다. 추정의 근거: 계획 (나)의 VB 에서 `gamedrive.py peek` 이 읽은 재고가 게임의 위쪽 자원 표시줄의 여섯(목재 · 석유 · 석탄 · 금속 광석 · 우라늄 · 전력)과 그 순서로 맞았다 [확인: 실행].
- **물자의 수량은 게임의 위쪽 자원 표시줄처럼 적는다**(`short_amount`): 100 아래는 소수 첫째 자리까지(`1.8 M` · `23.7 M`), 그 위는 정수(`129 K` · `779 M`) [확인: 게임 — VB 의 화면]. 국고는 재무 패널처럼 둘째 자리까지(`14.43 B` — 계획 (나) 그대로). 창의 재고 칸, `마지막으로 쓴 값`, 로그가 모두 이 표기다.
- **이름표에 없는 칸은 `물자 #11` 로 보인다**(칸 번호는 0 부터 — 설정 파일의 `keep.stock.<칸>` 과 같은 수). 설계서의 예 `물자 #12` 는 "표에 없는 칸"의 예였다.
- **게임 밖에서는 물자 탭에 이름표의 물자 열하나가 재고 없이(`-`) 나온다.** 설계서는 "이번 판에서 쓰는 물자만 줄로"라고 했는데, 게임 밖에서는 어느 물자를 쓰는지 모르고, 최소 유지를 게임 밖에서도 보고 끌 수 있어야 한다(아래).
- **최소 유지가 켜진 물자는 이번 판에서 쓰지 않아도 줄이 남는다**(재고 칸에 `쓰지 않음`, 단추는 꺼져 있다. 유지되지도 않는다). 켜 둔 유지를 끌 수 없게 되지 않도록.
- **최소 유지의 칸(체크와 수량)은 단추가 꺼져 있을 때(게임 밖 · 멀티플레이)도 고칠 수 있다.** 유지는 설정이고, 쓰는 것은 게임 안에서만이다. 탭에 까닭 한 줄만 보일 때(값을 쓸 수 없다)는 칸도 없다.
- **수량은 입력을 마쳐야(Enter, 다른 곳을 누름) 쓰인다.** 들어 있는 ImGui 의 `InputScalar` 가 그렇게 동작한다 [확인: 소스 — `imgui_widgets.cpp` 의 `InputScalar`, `LiveEditOnInputScalar` 가 아니면 비활성이 될 때 적용]. 치는 동안의 값(5, 50, 500 …)이 바닥으로 쓰이지 않는다. 치던 채로 창을 닫으면 친 것은 버려진다.
- **상태 줄의 유지 글**: 게임 안에서는 지금 유지되는 것만 이름으로(`· 유지 중: 국고, 석유` — 이번 판에서 쓰지 않는 물자는 빠진다), 쉬는 동안에는 켜진 수와 까닭으로 — `게임에 들어가면 적용`(설계서) 말고도 `멀티플레이에서는 쉽니다` · `게임을 읽을 수 없어 쉽니다` · `값을 쓸 수 없어 쉽니다` · `값을 읽을 수 없어 쉽니다`.
- **로그**: 국고의 유지는 `유지 켬: 국고 20000 (백만 달러)`(단위를 적는다). ToyBox 가 뜰 때 저장돼 있던 유지도 `유지 켬: …` 으로 적는다. 켜진 채로 수량을 고치면 `유지 켬: …` 을 새 수량으로 다시 적고, 그 항목의 `유지: …` (처음 올린 것)도 다시 한 번 적는다. 화살표는 `->`.
- **유지는 창 바닥의 `마지막으로 쓴 값` 을 덮지 않고 알림도 남기지 않는다**(0.5초마다 온다). 무엇이 유지되는지는 상태 줄이, 처음 올린 것은 로그가 말한다.
- **"모든 물자" 줄을 누른 뒤의 `마지막으로 쓴 값` 은 `모든 물자 11개`** 다(고친 물자의 수). 로그에는 물자마다 한 줄씩 남는다.
- **`toybox.ini` 에 유지의 스물여섯 줄을 늘 쓴다**(국고 둘 + 물자 열두 칸 × 둘. 꺼진 것은 0). 파일은 1 KB 를 넘지 않는다(읽는 쪽은 4096 바이트까지 읽는다).
- **게임 창의 타이머를 빈 메시지(`WM_NULL`)로 깨워서 건다.** 지금은 감싼 창 프로시저가 처음 불릴 때(아무 메시지나 올 때) 건다 — 유지는 사용자가 아무것도 누르지 않아도 돌아야 한다.
- **창의 첫 크기를 720×520 으로 넓힌다**(설계서 그대로). **첫 자리(40,60)는 그대로 둔다** — 그 자리가 게임의 속도 목록을 덮는다는 것(계획 (나)의 VB)은 문서의 한계에 적는다. 창을 옮기면 그 자리가 저장된다.
- **계획 (나)의 최종 검토가 남긴 다섯을 여기서 다룬다**:
  1. 값 계산의 더하기 · 바닥이 한도 밖의 값을 한도 쪽으로 끌어오지 않는다(`1.5e15` 에 바닥 `2e15` → 그대로). "이 값으로"만 한도 안으로 자른다. (Task 1)
  2. 돈 · 물자 탭의 바닥 안내는 글쇠 방식과 상관없다 — 옛 찾기가 실패했거나 `SRTOYBOX_DIRECT=0` 이어도 "게임의 설정 창이 잠깐 열렸다 닫힙니다"가 아니다. 탭을 쓸 수 없을 때는 안내가 없다. (Task 4)
  3. 오류 가드가 걸린 뒤의 값 쓰기를 밟는 테스트. (Task 4)
  4. 서명 표의 배열 크기 가드(`static_assert` + 실행 때의 대조). (Task 2)
  5. 세계 자료 포인터와 상태 전역의 겹침 대조(`locate_fits`), 자리의 정렬 대조(포인터 · 국고 칸은 8 의 배수, 표의 첫 칸은 4 의 배수). (Task 2)
  나머지 넷(요청을 받지 못한 까닭의 구분, 찾기가 실패했을 때 맞지 않은 서명을 적지 않는 것, `cheat_ranges` 가 `call rel32` 만 세는 것, `마지막으로 쓴 값` 이 판을 넘어 남는 것)은 그대로 둔다.
- **검사 도구의 `hints` 는 내장 치트로 도는 탭에서 본다.** 창을 열면 첫 탭이 "돈"이라, 위 2 를 고치면 그 탭의 안내가 글쇠 방식과 상관없어진다.
- **`gamedrive.py peek` 에 지역 번호를 줄 수 있게 한다**(`peek 1499`). V10(나라를 바꾼 뒤 앞 나라의 값이 그대로인가)을 메모리로 보려면 플레이어가 아닌 지역의 값을 읽어야 한다. 읽기만 한다.

## 계획을 쓰며 확인한 것

- **물자 이름** [확인: 파일]: `mods/korean/translation/variables.csv` 의 `LOCALIZE|productsl|0` ~ `|10` 이 농산물 · 고무 · 목재 · 석유 · 석탄 · 금속 광석 · 우라늄 · 전력 · 소비재 · 산업재 · 군수품(영문 Agriculture … Military Goods)이고, 같은 목록의 11 은 전체, 12 금융, 13 인구, 14 민간 수요, 15 군 수요다 — 물자가 아니다. (`docs/05` 는 "광석" · "공업재"라고 적었다 — Task 10 에서 번역 표의 이름으로 맞춘다.)
- **열두째 칸** [확인: 실행 — 계획 (나)의 VB]: 독일 · 샌드박스 2030 에서 `peek` 의 `used` 가 앞의 열하나는 참, 열두째(칸 11)는 거짓이고 재고가 0 이었다. 다른 판(DLC)에서는 보지 않았다.
- **들어 있는 ImGui(1.92.9b)의 `InputScalar`** [확인: 소스]: 값은 입력이 끝날 때 적용되고 그때 한 번 `true` 를 돌려준다. 누르면 글이 통째로 골라진다(`AutoSelectAll` 이 늘 켜진다). 돈 탭의 입력란(`money.amount`)도 그렇게 동작하고 있다.
- **이 계획의 고칠 곳을 모두 저장소의 스크래치 사본에 옮겨 돌려 봤다**(저장소와 게임 폴더는 건드리지 않았다):
  - 도구(`apply_plan.py`)가 이 문서에서 읽어 옮긴 결과가, Task 마다, 따로 구현해 둔 상태와 글자까지 같다.
  - Task 마다 테스트만 옮기고 실패를 보고, 코드를 옮겨 빌드(`/W4 /WX`)하고 통과를 봤다. 단계의 Expected 는 그때 본 것이다.
  - 끝 상태에서 ToyBox 테스트 전체(`test_toybox` · `test_toybox_game` · `test_toybox_values` · `test_toybox_sigs` · `test_sigmine`)를 이어서 여러 번 돌려 결과가 늘 같았다(세 번 — 세 번 다 `232 passed`. 스크래치 사본에서 저장소의 테스트 전체는 `336 passed`).
  - 이미 있는 동작을 밟는 테스트 둘(오류 가드 뒤의 값 쓰기, 게임의 함수 안에서 다시 온 타이머)은 그 가드를 뺀 빌드에서 실패하는 것을 봤다 — 통과하기만 하는 테스트가 아니다.
  - 물자 탭에 그려진 항목의 자리를 찍어 봤다: 넷째 칸(최소 유지)의 입력란의 오른쪽 끝이 x = 552 다(창은 x = 40 에서 760 까지). 표가 가로로 구를 일은 창을 좁혔을 때뿐이다.
- **돌려 보지 못한 것**: 게임 안의 동작 전부(Task 5 · 9), `gamedrive.py peek <지역 번호>`(게임이 떠 있어야 한다), 물자 탭의 생김새(스크래치의 검사 창은 화면에 보이지 않는다 — 항목의 자리와 글만 봤다).

## Review Focus

설계서가 함의하지만 그대로 두면 테스트가 밟지 않을 다섯 가지. 각 줄의 테스트를 해당 Task 에 넣었다.

1. **유지를 켜 둔 채 게임 밖 · 멀티플레이에 있다, 또는 그 물자를 쓰지 않는 판이다** → 쓰지 않고 쉰다(알림도 없다). 상태 줄에 켜진 수가 보이고, 그 자리에서 끌 수 있다. 게임에 들어가면 창을 열지 않아도 적용된다. (Task 7 `test_keep_rests_outside_a_game_and_says_nothing` · `test_keep_leaves_products_this_game_does_not_use`, Task 8 `test_keep_rests_in_the_menu_and_can_be_turned_off_there` · `test_keep_works_with_the_window_closed_and_shows_in_the_status_line`)
2. **유지할 수량을 치는 중이다(5, 50, 500 …)** → 치는 동안의 값은 쓰이지 않는다. 입력을 마쳐야 쓰이고, 치던 채로 창을 닫으면 버려진다. (Task 8 `test_a_typed_keep_amount_takes_effect_when_the_typing_is_done`)
3. **유지 중에 쓰기가 실패한다(낡은 포인터가 쓸 수 없는 곳을 가리킨다)** → 한 번만 실패를 적고, 그 뒤로는 0.5초마다 다시 시도하지 않는다. (Task 7 `test_keep_stops_when_a_write_fails`)
4. **게임이 한도 밖의 값을 만들어 놓았다(국고 $1,500 T)** → 더하기와 바닥이 그 값을 한도 쪽으로 끌어내리지 않는다 — 올리라는 요청이 값을 내리면 안 된다. (Task 1 `test_a_value_already_beyond_the_limit_is_not_pulled_back`)
5. **설정 파일의 유지 줄이 틀렸다(없는 칸, 범위 밖의 값, 0 / 1 이 아닌 켜짐)** → 그 줄만 버린다. 다른 유지와 다른 설정은 그대로다. (Task 6 `test_keep_settings`)

그리고 설계서의 테스트 목록과 계획 (나)의 최종 검토가 남긴 것: 게임의 함수 안에서 다시 온 타이머에서는 유지도 쓰지 않는다(Task 8 `test_keep_does_not_write_while_the_games_handler_is_running`), 오류 가드가 걸린 뒤에는 대기열의 값 쓰기도 버린다(Task 4 `test_values_are_not_written_after_the_fault_guard_trips`), 두 묶음의 주소가 겹치면 값 묶음을 버린다(Task 2 `test_the_world_pointer_must_not_sit_on_a_state_global` · `test_startup_drops_the_values_when_the_two_searches_clash`).

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `native/srtoybox/products.h` · `products.cpp` (새로) | 재고 칸 → 물자 이름 | 1 |
| `native/srtoybox/values.h` · `values.cpp` (고침) | 물자 수량의 줄임 표기(`short_amount`), 한도 밖의 값 | 1 |
| `src/srkit/toybox.py` (고침) | 물자 이름표 만들기(`product_rows` · `products_inc`), 빌드 목록, 두 묶음의 대조(`fits`) | 1 · 2 |
| `native/srtoybox/locate.h` · `locate.cpp` (고침) | 자리의 정렬 대조, `locate_fits`, 서명 표의 크기 가드 | 2 |
| `native/srtoybox/game.cpp` (고침) | 뜰 때 `locate_fits`, 실패한 칸의 이름 | 2 · 3 |
| `native/srtoybox/keeper.h` · `keeper.cpp` (고침) | 물자의 이름 · 표기, "모든 물자"(`ALL_STOCK`) / 최소 유지(`Keep`, `keeper_set_keep`, 0.5초마다의 검사), 상태 줄의 글 | 3 · 7 |
| `native/srtoybox/features.cpp` (고침) | 물자의 치트 세 줄 삭제(22 → 19줄) | 4 |
| `native/srtoybox/ui.cpp` (고침) | 물자 탭, 바닥 안내, 창의 첫 크기 / 유지의 칸, 상태 줄 | 4 · 8 |
| `src/srkit/cli.py` (고침) | `srkit locate` 의 안내 문구 | 4 |
| `native/srtoybox/settings.h` · `settings.cpp` (고침) | 유지의 켜짐과 값(`keep.*`) | 6 |
| `native/srtoybox/input.cpp` (고침) | 타이머에 시계를 넘긴다 / 타이머를 빈 메시지로 깨운다 | 7 · 8 |
| `native/srtoybox/exports.cpp` (고침) | 테스트용 내보내기 | 1 · 2 · 3 · 7 |
| `scripts/gamedrive.py` (고침) | `peek <지역 번호>` | 9 |
| `tests/test_toybox_game.py` · `test_toybox_values.py` · `test_toybox.py` · `toybox_overlay_probe.py` (고침) | 테스트와 검사 도구 | 1 ~ 4 · 6 ~ 8 |
| `docs/10` · `docs/11` · `docs/05` · `docs/09` · `README.md` · `CLAUDE.md` · 설계서 (고침) | 문서 | 10 |

---

### Task 1: 물자 이름표, 수량의 표기, 한도 밖의 값

**브랜치:** `feat/toybox-values-stock` (`develop` 에서 나눈다)

**Files:**
- Create: `native/srtoybox/products.h`, `native/srtoybox/products.cpp`
- Modify: `native/srtoybox/values.h`, `native/srtoybox/values.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`
- Test: `tests/test_toybox_game.py`, `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: 계획 (나)의 `values.h`(`Change` · `Verdict` · `treasury_value` · `stock_value` · `short_number`), `toybox.regions_inc` · `c_string`(지역 이름표의 생성 — 같은 꼴을 쓴다).
- Produces:
  - `const ProductName *find_product(int slot)`(표에 없으면 `nullptr`), `std::string product_label(int slot)`(`"석유"`, 표에 없으면 `"물자 #11"`). `struct ProductName { int slot; const char *ko; const char *en; }`.
  - `std::string short_amount(double value)` — 물자 수량의 줄임 표기(`1.8 M` · `129 K` · `999` · `?`).
  - `treasury_value` · `stock_value` 의 바뀐 약속: 더하기 · 바닥은 한도 밖의 값을 한도 쪽으로 끌어오지 않는다.
  - Python: `toybox.product_rows(cfg) -> list[tuple[int, str, str]]`, `toybox.products_inc(rows) -> str`, `toybox.PRODUCT_TABLE`, `toybox.PRODUCT_NAMES = 11`.
  - 내보내기: `srtoybox_product_label(slot, out, size)`, `srtoybox_product_names(slot, out, size)`(`"<한글>\t<영문>"`, 표에 없으면 -1), `srtoybox_short_amount(value, out, size)`.

- [ ] **Step 0: 브랜치를 만들고 시작할 때의 상태를 본다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-values-stock && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -2
```

Expected: `빌드 완료: …\build\toybox\srtoybox.dll`, `305 passed`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

물자 이름표(DLL 의 이름과, 번역 표에서 표를 만드는 Python 쪽), 수량의 표기, 한도 밖의 값.

<!-- 고칠 곳: test -->
`tests/test_toybox_game.py` 에서 다음 바로 앞에:

```python
def test_region_rows_come_from_the_translation_table(cfg):
```

이것을 더한다:

```python
def product(lib, slot: int) -> str:
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_product_label(slot, out, len(out)) >= 0
    return out.value.decode("utf-8")


def test_product_names(lib):
    """물자 이름표도 저장소의 번역 테이블에서 온다(재고 칸의 순서 = 게임의 물자 목록의 순서). 표에 없는 칸은 "물자 #칸" 으로 보인다."""
    assert [product(lib, slot) for slot in range(11)] == ["농산물", "고무", "목재", "석유", "석탄", "금속 광석", "우라늄", "전력", "소비재",
                                                           "산업재", "군수품"]
    assert product(lib, 11) == "물자 #11" and product(lib, 12) == "물자 #12" and product(lib, -1) == "물자 #-1"   # 열두째 칸에는 이름이 없다
    out = ctypes.create_string_buffer(256)
    assert lib.srtoybox_product_names(3, out, len(out)) > 0 and out.value.decode("utf-8") == "석유\tPetroleum"
    assert lib.srtoybox_product_names(11, out, len(out)) == -1


def test_product_rows_come_from_the_translation_table(cfg):
    rows = toybox.product_rows(cfg)
    assert [slot for slot, _, _ in rows] == list(range(11))                  # 같은 목록의 11(전체) · 12(금융) · 13(인구) … 는 물자가 아니다
    assert rows[3] == (3, "석유", "Petroleum") and rows[10] == (10, "군수품", "Military Goods")
    assert toybox.products_inc(rows[:1]) == '{0, "농산물", "Agriculture"},\n'


```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
    pointer = ctypes.POINTER
```

이것을 더한다:

```python
    lib.srtoybox_short_amount.argtypes = [ctypes.c_double, ctypes.c_char_p, ctypes.c_int]
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def test_stock_values(lib):
```

이것을 더한다:

```python
def test_a_value_already_beyond_the_limit_is_not_pulled_back(lib):
    """한도는 "여기까지만 민다"는 뜻이다. 게임이 한도 밖으로 만든 값을 더하기 · 바닥이 한도 쪽으로 끌어오면, 올리라는 요청이 값을 내린다."""
    assert value(lib, False, 1.5e15, FLOOR, 2e15) == (NOTHING, None)              # 바닥이 한도 위여도 내리지 않는다
    assert value(lib, False, 1.5e15, ADD, 1.0) == (NOTHING, None)                 # 더 밀지 않을 뿐이다
    assert value(lib, False, 1.5e15, ADD, -1e14) == (WRITE, 1.4e15)               # 한도 쪽으로는 청한 만큼만 간다
    assert value(lib, False, -1.5e15, ADD, -1.0) == (NOTHING, None)
    assert value(lib, False, -1.5e15, ADD, 1e14) == (WRITE, -1.4e15)
    assert value(lib, False, 1.5e15, SET, 2e15) == (WRITE, 1e15)                  # "이 값으로"만 한도 안으로 자른다
    assert value(lib, True, 2e9, FLOOR, 3e9) == (NOTHING, None)
    assert value(lib, True, 2e9, ADD, 1e6) == (NOTHING, None)
    assert value(lib, True, 2e9, ADD, -1e9) == (WRITE, 1e9)
    assert value(lib, True, 2e9, SET, 3e9) == (WRITE, 1e9)


```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def germany() -> FakeGame:
```

이것을 더한다:

```python
def test_short_amounts_look_like_the_resource_bar(lib):
    """물자의 수량은 게임의 위쪽 자원 표시줄처럼: 100 아래는 소수 첫째 자리까지(1.8 M · 23.7 M), 그 위는 정수(129 K · 779 M)."""
    short = lambda v: text(lib.srtoybox_short_amount, v)
    assert [short(v) for v in (0, 7, 999.4, 1000, 2500, 129000, 1.8e6, 23.7e6, 779e6, 1e9, -5, 0.3, -0.3)] == \
        ["0", "7", "999", "1.0 K", "2.5 K", "129 K", "1.8 M", "23.7 M", "779 M", "1.0 B", "-5", "0", "0"]
    assert [short(v) for v in (99.94e3, 99.96e3, 999.4e3, 999.6e3, 5e15)] == ["99.9 K", "100 K", "999 K", "1.0 M", "5000 T"]
    assert short(NAN) == "?" and short(INF) == "?"


```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_game.py tests/test_toybox_values.py -q 2>&1 | tail -6`

Expected: `2 failed, 76 passed, 36 errors` — `test_product_names`(`AttributeError: function 'srtoybox_product_label' not found`), `test_product_rows_come_from_the_translation_table`(`module 'srkit.toybox' has no attribute 'product_rows'`), 그리고 `tests/test_toybox_values.py` 의 서른여섯이 모두 고정물에서 오류다(`function 'srtoybox_short_amount' not found` — `lib` 고정물이 그 함수의 인자 형을 적는다. 새 테스트 둘도 그 안에 있다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
#include "prologue.h"
```

이것을 더한다:

```cpp
#include "products.h"
```

`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
EXPORT int srtoybox_region_label(int number, char *out, int size)
```

이것을 더한다:

```cpp
EXPORT int srtoybox_product_label(int slot, char *out, int size)
{
    return put(product_label(slot), out, size);
}

// 물자 이름표의 한 줄: "<한글 이름>\t<영문 이름>". 표에 없는 칸이면 -1.
EXPORT int srtoybox_product_names(int slot, char *out, int size)
{
    const ProductName *name = find_product(slot);
    return name == nullptr ? -1 : put(std::string(name->ko) + '\t' + name->en, out, size);
}

```

`native/srtoybox/exports.cpp` 에서 다음 바로 뒤에:

```cpp
    return put(short_number(value), out, size);
}

```

이것을 더한다:

```cpp
EXPORT int srtoybox_short_amount(double value, char *out, int size)
{
    return put(short_amount(value), out, size);
}

```

새 파일 `native/srtoybox/products.cpp`:

```cpp
#include "products.h"

namespace {

const ProductName NAMES[] = {   // 칸 오름차순
#include "products_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

}  // namespace

const ProductName *find_product(int slot)
{
    for (int i = 0; i < NAME_COUNT; i++)
        if (NAMES[i].slot == slot)
            return &NAMES[i];
    return nullptr;
}

std::string product_label(int slot)
{
    const ProductName *name = find_product(slot);
    return name != nullptr ? std::string(name->ko) : "물자 #" + std::to_string(slot);
}
```

새 파일 `native/srtoybox/products.h`:

```cpp
// 재고 칸 번호 → 물자 이름. 표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/variables.csv 의
// LOCALIZE|productsl|0 … 10)에서 만든다(src/srkit/toybox.py 의 products_inc → build/toybox-obj/products_table.inc).
#pragma once

#include <string>

struct ProductName {
    int slot;         // 재고 칸(0 … STOCK_SLOTS - 1)
    const char *ko;   // UTF-8
    const char *en;
};

const ProductName *find_product(int slot);   // 표에 없으면 nullptr
std::string product_label(int slot);         // "석유". 표에 없으면 "물자 #11"
```

`native/srtoybox/values.cpp` 를 통째로 다음으로 바꾼다:

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
    const bool set = change == Change::Set;      // 더하기 · 바닥은 한도 밖에 있던 값을 한도 쪽으로 끌어오지 않는다
    const double high = set ? TREASURY_LIMIT : std::max(TREASURY_LIMIT, now);
    const double low = set ? -TREASURY_LIMIT : std::min(-TREASURY_LIMIT, now);
    value = std::min(high, std::max(low, value));
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
    const double high = change == Change::Set ? STOCK_LIMIT : std::max(STOCK_LIMIT, static_cast<double>(now));
    const float next = static_cast<float>(std::min(high, std::max(0.0, value)));
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

std::string short_amount(double value)
{
    static const struct {
        double unit;
        char letter;
    } UNITS[] = {{1e3, 'K'}, {1e6, 'M'}, {1e9, 'B'}, {1e12, 'T'}};
    const int last = static_cast<int>(sizeof(UNITS) / sizeof(UNITS[0])) - 1;
    if (!std::isfinite(value))
        return "?";
    const double size = std::fabs(value);
    if (size < 0.5)
        return "0";                  // "-0" 이 되지 않게
    char text[40] = "";
    if (size < 999.5) {
        snprintf(text, sizeof(text), "%.0f", value);
        return text;
    }
    int u = 0;
    while (u < last && size / UNITS[u].unit >= 999.5)
        u++;                         // 999.5 K 부터는 1.0 M 이다
    snprintf(text, sizeof(text), size / UNITS[u].unit < 99.95 ? "%.1f %c" : "%.0f %c", value / UNITS[u].unit, UNITS[u].letter);
    return text;
}
```

`native/srtoybox/values.h` 에서 다음을 찾아:

```cpp
const double TREASURY_LIMIT = 1e15;   // 국고의 결과는 ±$1,000 T 안으로 자른다. 음수는 된다(게임이 허용한다)
const double STOCK_LIMIT = 1e9;       // 재고의 결과는 0 이상 10억 이하로 자른다
```

이렇게 바꾼다:

```cpp
// 한도는 "여기까지만 민다"는 뜻이다. "이 값으로"는 한도 안으로 자르고, 더하기 · 바닥은 한도를 넘겨 밀지 않을 뿐
// 이미 한도 밖에 있는 값(게임이 그렇게 만든 값)을 한도 쪽으로 끌어오지 않는다.
const double TREASURY_LIMIT = 1e15;   // 국고: ±$1,000 T. 음수는 된다(게임이 허용한다)
const double STOCK_LIMIT = 1e9;       // 재고: 0 이상 10억 이하
```

`native/srtoybox/values.h` 에서 다음 바로 뒤에:

```cpp
std::string short_number(double value);
```

이것을 더한다:

```cpp
// 게임의 위쪽 자원 표시줄과 같은 줄임 표기(물자의 수량): 999 · 1.8 M · 23.7 M · 129 K · 779 M — 100 아래는 소수 첫째 자리까지.
std::string short_amount(double value);
```

`src/srkit/toybox.py` 에서 다음을 찾아:

```python
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "values.cpp", "game.cpp", "keeper.cpp", "regions.cpp",
```

이렇게 바꾼다:

```python
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "values.cpp", "game.cpp", "keeper.cpp", "regions.cpp", "products.cpp",
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
# native/srtoybox/locate.h 의 GameAddresses 와 같은 순서다
```

이것을 더한다:

```python
# LOCALIZE|productsl|<칸> 행이 물자의 이름이다. 재고 칸과 같은 순서로 0 … 10 의 열하나다 — 11 부터는 물자가 아니다(전체 · 금융 · 인구 …)
PRODUCT_TABLE = "mods/korean/translation/variables.csv"
PRODUCT_NAMES = 11
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def build(cfg: Config) -> Path:
```

이것을 더한다:

```python
def product_rows(cfg: Config) -> list[tuple[int, str, str]]:
    """번역 테이블에서 (재고 칸, 한글 이름, 영문 이름)을 칸순으로. 번역이 빈 행은 영문 이름을 쓴다."""
    rows: dict[int, tuple[str, str]] = {}
    with (cfg.root / PRODUCT_TABLE).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            m = re.fullmatch(r"LOCALIZE\|productsl\|(\d+)", row["key"])
            en = row["en"].strip()
            if m and en and int(m[1]) < PRODUCT_NAMES:
                rows[int(m[1])] = (row["ko"].strip() or en, en)
    return [(slot, *rows[slot]) for slot in sorted(rows)]


def products_inc(rows: list[tuple[int, str, str]]) -> str:
    """native/srtoybox/products.cpp 가 끼워 넣는 초기화 목록(한 줄에 물자 하나). 꼴은 지역 이름표와 같다."""
    return regions_inc(rows)


```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
    include = f'/I"{imgui}" /I"{imgui / "backends"}" /I"{obj}" {IMGUI_DEFINES}'
```

이것을 더한다:

```python
    (obj / "products_table.inc").write_text(products_inc(product_rows(cfg)), encoding="utf-8", newline="\n")
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_game.py tests/test_toybox_values.py -q 2>&1 | tail -2`

Expected: `빌드 완료: …`, `114 passed`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/products.h native/srtoybox/products.cpp native/srtoybox/values.h native/srtoybox/values.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_game.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox 물자 이름표와 수량의 표기, 한도 밖의 값은 끌어오지 않는다

- products: 재고 칸 → 물자 이름. 빌드할 때 번역 표(variables.csv 의 LOCALIZE|productsl|0 … 10)에서 만든다. 표에 없는 칸은 "물자 #칸".
- short_amount: 물자의 수량을 게임의 위쪽 자원 표시줄처럼 적는다(1.8 M · 129 K).
- 값 계산: 더하기와 바닥이 이미 한도 밖에 있는 값을 한도 쪽으로 끌어오지 않는다("이 값으로"만 자른다).
  계획 (나)의 최종 검토가 남긴 것 — 올리라는 요청이 값을 내리면 안 된다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `309 passed`.

---

### Task 2: 찾기의 대조를 조인다 — 정렬, 두 묶음의 겹침, 서명 표의 크기

**브랜치:** `feat/toybox-values-stock`

**Files:**
- Modify: `native/srtoybox/locate.h`, `native/srtoybox/locate.cpp`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`, `src/srkit/toybox.py`
- Test: `tests/test_toybox_game.py`, `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: 계획 (가) · (나)의 `locate_state` · `locate_values`, `GameAddresses` · `ValueLayout`, `tests/toybox_fake_exe.py` 의 `sig_image(…, targets=…)` · `STATE` · `VALUE_LAYOUT` · `DATA`.
- Produces:
  - `bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size)` — 세계 자료 포인터(8바이트)가 상태 전역 일곱과 겹치지 않으면 `true`. 겹치면 `false` 와 `"세계 자료 포인터: 찾은 주소가 <이름> 의 자리와 겹칩니다"`.
  - `locate_values` 가 더 보는 것: 세계 자료 포인터와 국고 칸은 8 의 배수, 재고 · 쓰는 물자 표의 첫 칸은 4 의 배수. 아니면 못 찾은 것(`"…: 찾은 주소가 8 의 배수가 아닙니다"` · `"…: 찾은 자리가 8 의 배수가 아닙니다"` · `"…: 찾은 자리가 4 의 배수가 아닙니다"`).
  - `game_init_from` 이 두 묶음을 다 찾은 뒤 `locate_fits` 를 본다 — 겹치면 값 묶음만 버린다(돈 · 물자 탭이 꺼지고 까닭이 보인다. 상태 읽기는 그대로다).
  - Python: `toybox.fits(lib, state: dict, values: dict) -> str`(맞으면 빈 글), `toybox.locate()` 가 겹치면 `values=None` 과 그 까닭.
  - 내보내기: `srtoybox_locate_fits(const GameAddresses *, const ValueLayout *, char *error, int error_size)` — 0 맞는다, -1 까닭.

진짜 게임의 값(build 21347933: 세계 자료 포인터 `0x1af5868`, 국고 `+0x14B88`, 재고 `+0x14DA4`, 쓰는 물자 `+0x18`)은 이 대조를 모두 지난다 — 설치본 테스트(`test_values_on_the_installed_game`)가 그대로 통과해야 한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_toybox_game.py` 에서 다음을 찾아:

```python
], ids=["overlap", "odd-step", "far", "zero-step", "zero-offset"])
```

이렇게 바꾼다:

```python
    ({"world_pointer": toybox_fake_exe.DATA + 0x44}, "세계 자료 포인터: 찾은 주소가 8 의 배수가 아닙니다"),
    ({"treasury": 0x1234}, "국고 칸: 찾은 자리가 8 의 배수가 아닙니다"),          # double 이 놓일 수 없는 자리
    ({"stock": (0x20, 0x2002)}, "재고 칸: 찾은 자리가 4 의 배수가 아닙니다"),
    ({"used": (0x44, 0x2A)}, "쓰는 물자 표: 찾은 자리가 4 의 배수가 아닙니다"),
], ids=["overlap", "odd-step", "far", "zero-step", "zero-offset", "pointer-unaligned", "treasury-unaligned", "stock-unaligned",
        "used-unaligned"])
```

`tests/test_toybox_game.py` 에서 다음 바로 뒤에:

```python
    found, why, _ = toybox.values_of(lib, toybox_fake_exe.sig_image(value_sigs, targets=targets))
    assert found is None and reason in why, why


```

이것을 더한다:

```python
def test_the_world_pointer_must_not_sit_on_a_state_global(lib, sigs, value_sigs):
    """두 묶음을 저마다 찾았어도, 세계 자료 포인터가 상태 전역과 겹치면 둘 가운데 하나는 엉뚱한 것을 읽은 것이다 — 값 묶음을 버린다."""
    clash = {"world_pointer": toybox_fake_exe.STATE["player_pointer"]}
    image = toybox_fake_exe.sig_image(sigs + value_sigs, targets=clash)
    state, why, _ = toybox.state_of(lib, image)
    assert state == toybox_fake_exe.STATE, why
    values, why, _ = toybox.values_of(lib, image)
    assert values == {**toybox_fake_exe.VALUE_LAYOUT, **clash}, why          # 저마다는 말이 된다
    assert toybox.fits(lib, state, values) == "세계 자료 포인터: 찾은 주소가 플레이어 포인터 의 자리와 겹칩니다"
    assert toybox.fits(lib, state, toybox_fake_exe.VALUE_LAYOUT) == ""
    inside = {**toybox_fake_exe.VALUE_LAYOUT, "world_pointer": toybox_fake_exe.STATE["region_table"] + 0x800}
    assert "지역 표" in toybox.fits(lib, state, inside)                       # 지역 표(8바이트 × 1024칸)의 한가운데
    edge = {**toybox_fake_exe.VALUE_LAYOUT, "world_pointer": toybox_fake_exe.STATE["player_pointer"] + 8}
    assert toybox.fits(lib, state, edge) == ""                               # 바로 옆은 겹침이 아니다


```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def test_startup_with_everything(lib, all_sigs, tmp_path, monkeypatch):
```

이것을 더한다:

```python
def test_startup_drops_the_values_when_the_two_searches_clash(lib, all_sigs, tmp_path, monkeypatch):
    """두 묶음을 저마다 찾았어도 세계 자료 포인터가 상태 전역과 겹치면 값은 쓰지 않는다. 상태 읽기는 그대로다."""
    state, values = all_sigs
    image = toybox_fake_exe.sig_image(state + values, targets={"world_pointer": toybox_fake_exe.STATE["player_pointer"]})
    flags, off, log = init(lib, image, tmp_path, monkeypatch)
    clash = "세계 자료 포인터: 찾은 주소가 플레이어 포인터 의 자리와 겹칩니다"
    assert flags == READS and off == f"이 게임 판에서는 쓸 수 없습니다 ({clash})"
    assert f"값을 쓸 수 없습니다 ({clash})" in log and "게임 상태를 읽습니다 (서명 21개 가운데 21개" in log


```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_game.py tests/test_toybox_values.py -q 2>&1 | tail -10`

Expected: `6 failed, 114 passed` — `test_values_that_do_not_add_up_are_refused` 의 새 네 줄(`pointer-unaligned` · `treasury-unaligned` · `stock-unaligned` · `used-unaligned`: 정렬이 틀린 자리를 그대로 찾아 낸다 — `assert ({…} is None)`), `test_the_world_pointer_must_not_sit_on_a_state_global`(`module 'srkit.toybox' has no attribute 'fits'`), `test_startup_drops_the_values_when_the_two_searches_clash`(겹쳤는데도 값 쓰기가 켜져 있다 — `assert (5 == 1)`).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음 바로 앞에:

```cpp
EXPORT int srtoybox_stock_slots(void)
```

이것을 더한다:

```cpp
// 두 묶음의 대조(locate_fits). 0 이면 맞는다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate_fits(const GameAddresses *state, const ValueLayout *values, char *error, int error_size)
{
    char why[160] = "";
    if (state == nullptr || values == nullptr)
        return -1;
    if (locate_fits(*state, *values, why, sizeof(why)))
        return 0;
    put(why, error, error_size);
    return -1;
}

```

`native/srtoybox/game.cpp` 에서 다음을 찾아:

```cpp
    const bool values = state && locate_values(base, size, &layout, value_rows, value_why, sizeof(value_why));
```

이렇게 바꾼다:

```cpp
    const bool values = state && locate_values(base, size, &layout, value_rows, value_why, sizeof(value_why))
        && locate_fits(at, layout, value_why, sizeof(value_why));
```

`native/srtoybox/locate.cpp` 에서 다음 바로 뒤에:

```cpp
const int MAX_TABLE = STATE_WANTED * STATE_SIGS;    // 한 표의 서명 수의 상한(상태 21개, 값 12개)
```

이것을 더한다:

```cpp
static_assert(VALUE_WANTED <= STATE_WANTED, "vote_table 의 배열은 상태 묶음의 크기로 잡았다 — 더 큰 표를 더하면 MAX_TABLE 을 키운다");
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
    SigRange ranges[32];
```

이렇게 바꾼다:

```cpp
    if (total > MAX_TABLE) {
        snprintf(why, why_size, "서명 표가 너무 큽니다 (%d개)", total);
        return false;
    }
    SigRange ranges[32];                                // 구역은 32개까지 읽는다(parse)
```

`native/srtoybox/locate.cpp` 에서 다음을 찾아:

```cpp
    if (!offset_ok(treasury)) {
        snprintf(why, why_size, "%s: 찾은 자리가 범위 밖입니다", VALUES[1].label);
```

이렇게 바꾼다:

```cpp
    if (world % 8 != 0) {                       // 포인터와 double 은 8 의 배수 자리에, float 는 4 의 배수 자리에 놓인다
        snprintf(why, why_size, "%s: 찾은 주소가 8 의 배수가 아닙니다", VALUES[0].label);
        return false;
    }
    if (!offset_ok(treasury)) {
        snprintf(why, why_size, "%s: 찾은 자리가 범위 밖입니다", VALUES[1].label);
        return false;
    }
    if (treasury % 8 != 0) {
        snprintf(why, why_size, "%s: 찾은 자리가 8 의 배수가 아닙니다", VALUES[1].label);
```

`native/srtoybox/locate.cpp` 에서 다음 바로 뒤에:

```cpp
            snprintf(why, why_size, "%s: 찾은 자리나 간격이 범위 밖입니다", VALUES[w].label);
```

이것을 더한다:

```cpp
            return false;
        }
        if (first % 4 != 0) {
            snprintf(why, why_size, "%s: 찾은 자리가 4 의 배수가 아닙니다", VALUES[w].label);
```

`native/srtoybox/locate.cpp` 에서 다음 바로 앞에:

```cpp
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva)
```

이것을 더한다:

```cpp
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size)
{
    const uint64_t world = values.world_pointer;
    for (int w = 0; w < STATE_WANTED; w++) {
        const uint64_t rva = state.*(STATE[w].field);
        if (world < rva + STATE[w].bytes && rva < world + 8) {
            snprintf(why, why_size, "%s: 찾은 주소가 %s 의 자리와 겹칩니다", VALUES[0].label, STATE[w].label);
            return false;
        }
    }
    snprintf(why, why_size, "%s", "");
    return true;
}

```

`native/srtoybox/locate.h` 에서 다음을 찾아:

```cpp
// 읽어 낸 값이 말이 되는지도 본다: 포인터는 쓸 수 있는 자료 구역 안, 자리는 0 보다 크고 0x100000 보다 작다, 간격은 4 의 배수,
// 국고 칸(8바이트)과 재고 칸들(4바이트 × STOCK_SLOTS)이 겹치지 않는다.
// rows: VALUE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);
```

이렇게 바꾼다:

```cpp
// 읽어 낸 값이 말이 되는지도 본다: 포인터는 쓸 수 있는 자료 구역 안의 8 의 배수 자리, 자리는 0 보다 크고 0x100000 보다 작다,
// 국고 칸은 8 의 배수 · 표의 첫 칸과 간격은 4 의 배수, 국고 칸(8바이트)과 재고 칸들(4바이트 × STOCK_SLOTS)이 겹치지 않는다.
// rows: VALUE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);

// 두 묶음을 함께 본다(둘 다 찾은 뒤에): 세계 자료 포인터가 상태 전역 일곱 가운데 어느 것과도 겹치지 않아야 한다.
// 겹치면 false 와 why(UTF-8) — 값 묶음을 못 찾은 것으로 친다(상태 묶음은 그대로 쓴다).
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size);
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
    lib.srtoybox_function_root.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint]
```

이것을 더한다:

```python
    lib.srtoybox_locate_fits.argtypes = [ctypes.POINTER(GameAddresses), ctypes.POINTER(ValueLayout), ctypes.c_char_p, ctypes.c_int]
```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
def legacy_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str]:
```

이것을 더한다:

```python
def fits(lib: ctypes.CDLL, state: dict[str, int], values: dict[str, int]) -> str:
    """두 묶음의 대조(세계 자료 포인터가 상태 전역과 겹치지 않는가). 맞으면 빈 글, 아니면 까닭."""
    error = ctypes.create_string_buffer(256)
    ok = lib.srtoybox_locate_fits(ctypes.byref(GameAddresses(**state)), ctypes.byref(ValueLayout(**values)), error, len(error)) == 0
    return "" if ok else error.value.decode("utf-8")


```

`src/srkit/toybox.py` 에서 다음 바로 앞에:

```python
    legacy, legacy_why = legacy_of(lib, image)
```

이것을 더한다:

```python
    clash = fits(lib, state, values) if state is not None and values is not None else ""
    if clash:
        values, values_why = None, clash      # 게임 안의 ToyBox 도 이때 값 묶음을 버린다(game_init_from)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_game.py tests/test_toybox_values.py -q 2>&1 | tail -2 && uv run srkit locate | tail -12`

Expected: `빌드 완료: …`, `120 passed`, 그리고 `srkit locate` 의 끝이 계획 (나) 때와 같다 — 값 묶음의 여섯 줄(`0x01af5868  세계 자료 객체의 포인터…` … `0x00000084  그 표의 간격`), 옛 찾기의 세 줄, `모두 찾았습니다. docs/11 의 표와 다르면 게임이 바뀐 것입니다.`

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/locate.h native/srtoybox/locate.cpp native/srtoybox/game.cpp native/srtoybox/exports.cpp src/srkit/toybox.py tests/test_toybox_game.py tests/test_toybox_values.py && git commit -q -F - <<'EOF'
fix: ToyBox 값의 자리 찾기 — 자리의 정렬과 두 묶음의 겹침을 대조한다

- 세계 자료 포인터와 국고 칸은 8 의 배수, 표의 첫 칸은 4 의 배수여야 한다(포인터 · double · float 가 놓이는 자리).
- 세계 자료 포인터가 상태 전역 일곱과 겹치면 둘 가운데 하나는 엉뚱한 것을 읽은 것이다 — 값 묶음을 버린다(locate_fits).
  게임이 뜰 때와 srkit locate 가 같은 대조를 한다.
- 서명 표의 크기를 컴파일할 때와 돌 때 본다(vote_table 의 배열은 상태 묶음의 크기로 잡혀 있다).

계획 (나)의 최종 검토가 남긴 것이다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `315 passed`.

---

### Task 3: 대기열 — 물자의 이름과 "모든 물자"

**브랜치:** `feat/toybox-values-stock`

**Files:**
- Modify: `native/srtoybox/keeper.h`, `native/srtoybox/keeper.cpp`, `native/srtoybox/game.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: Task 1 의 `product_label` · `short_amount`. 계획 (나)의 `keeper_enqueue` · `keeper_tick` · `keeper_last` · `Request`, `game_values()` · `game_write_stock`.
- Produces:
  - `const int ALL_STOCK = -2` — `Request.slot` 에 주면 이번 판에서 쓰는 물자 모두. 대기열을 비울 때 칸마다의 요청으로 풀린다(쓰지 않는 칸에는 닿지 않는다).
  - `keeper_last()` 의 새 글: 물자는 이름과 자원 표시줄의 표기로(`"석유 2.5 M -> 3.5 M"`), "모든 물자" 뒤에는 `"모든 물자 3개"`(고친 물자의 수. 하나도 고치지 않았으면 앞의 글 그대로).
  - 로그: `값 쓰기: 석유 2.5 M -> 3.5 M`, `값 쓰기 실패 (석유) — 값 쓰기를 끕니다`(지금까지는 `재고 칸 3`).
  - 테스트의 `srtoybox_keeper_request(-2, …)`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
TREASURY = -1                                                       # 쓰기의 대상: 국고. 0 … 11 은 그 칸의 재고
```

이렇게 바꾼다:

```python
TREASURY, ALL_STOCK = -1, -2                                        # 쓰기의 대상: 국고 / 쓰는 물자 모두. 0 … 11 은 그 칸의 재고
```

`tests/test_toybox_values.py` 에서 다음을 찾아:

```python
    assert told(lib) == ("재고 칸 0 1.00 K -> 0", "이번 판에서 쓰지 않는 물자입니다.")
```

이렇게 바꾼다:

```python
    assert told(lib) == ("농산물 1.0 K -> 0", "이번 판에서 쓰지 않는 물자입니다.")      # 물자는 이름으로, 자원 표시줄의 표기로


def test_a_request_for_all_products_reaches_every_product_in_use(lib, game, tmp_path):
    """"모든 물자" 줄의 요청은 쓸 때 이번 판에서 쓰는 물자마다의 요청으로 풀린다. 쓰지 않는 칸 · 다른 나라는 그대로다."""
    game.set_stock(141, 3, 777.0)
    assert ask(lib, ALL_STOCK, ADD, 1e6)
    lib.srtoybox_keeper_tick()
    assert [game.stock(176, slot) for slot in range(12)] == [1001000.0, 0, 0, 1002500.0, 0, 0, 0, 1000000.0, 0, 0, 0, 0]
    assert told(lib) == ("모든 물자 3개", "")
    assert ask(lib, ALL_STOCK, SET, 0.0)
    lib.srtoybox_keeper_tick()
    assert [game.stock(176, slot) for slot in (0, 3, 7)] == [0.0, 0.0, 0.0] and told(lib) == ("모든 물자 3개", "")
    assert ask(lib, ALL_STOCK, ADD, -1e8) and ask(lib, 7, ADD, 5.0)
    lib.srtoybox_keeper_tick()
    assert told(lib) == ("전력 0 -> 5", "")                    # 바꿀 것이 없던 "모든 물자"는 마지막으로 쓴 것을 덮지 않는다
    assert game.stock(141, 3) == 777.0 and game.treasury(176) == 14.43e9
    log = (tmp_path / "toybox.log").read_text(encoding="utf-8")
    assert [line.split(" ", 2)[2] for line in log.splitlines()][:3] == ["값 쓰기: 농산물 1.0 K -> 1.0 M", "값 쓰기: 석유 2.5 K -> 1.0 M",
                                                                        "값 쓰기: 전력 0 -> 1.0 M"]
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def test_nothing_is_asked_when_values_cannot_be_written(lib, game):
```

이것을 더한다:

```python
def test_a_failed_stock_write_names_the_product(lib, game, tmp_path):
    game.lock(176)
    game.play(176)
    assert ask(lib, ALL_STOCK, ADD, 1e6)
    lib.srtoybox_keeper_tick()
    assert text(lib.srtoybox_values_off) == FAILED_OFF and told(lib)[0] == ""
    log = (tmp_path / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (농산물) — 값 쓰기를 끕니다") == 1 and "값 쓰기: " not in log   # 첫 칸에서 멈춘다


```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -8`

Expected: `3 failed, 36 passed` — `test_stock_requests_reach_only_products_in_use`(`'재고 칸 0 1.00 K -> 0'` 이 나온다), `test_a_request_for_all_products_reaches_every_product_in_use`(재고가 그대로다 — 칸 −2 는 아직 "쓰지 않는 물자"로 버려진다), `test_a_failed_stock_write_names_the_product`(같은 까닭으로 쓰기를 시도하지 않아 값 쓰기가 꺼지지 않는다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
// 테스트: 값 쓰기 요청(keeper.h). slot 이 -1 이면 국고. change: 0 더하기, 1 이 값으로, 2 바닥. 받았으면 1.
```

이렇게 바꾼다:

```cpp
// 테스트: 값 쓰기 요청(keeper.h). slot 이 -1 이면 국고, -2 면 쓰는 물자 모두. change: 0 더하기, 1 이 값으로, 2 바닥. 받았으면 1.
```

`native/srtoybox/game.cpp` 에서 다음 바로 뒤에:

```cpp
#include "log.h"
```

이것을 더한다:

```cpp
#include "products.h"
```

`native/srtoybox/game.cpp` 에서 다음을 찾아:

```cpp
        if (slot < 0)
            log_line("값 쓰기 실패 (국고) — 값 쓰기를 끕니다");
        else
            log_line("값 쓰기 실패 (재고 칸 %d) — 값 쓰기를 끕니다", slot);
```

이렇게 바꾼다:

```cpp
        log_line("값 쓰기 실패 (%s) — 값 쓰기를 끕니다", slot < 0 ? "국고" : product_label(slot).c_str());
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
#include "runner_win.h"
```

이것을 더한다:

```cpp
#include "products.h"
```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
    return slot == TREASURY ? std::string("국고") : "재고 칸 " + std::to_string(slot);
}

// 요청 하나를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now)
{
```

이렇게 바꾼다:

```cpp
    return slot == TREASURY ? std::string("국고") : product_label(slot);
}

// 국고는 재무 패널의 표기로, 물자는 위쪽 자원 표시줄의 표기로 적는다.
std::string shown(int slot, double value)
{
    return slot == TREASURY ? short_number(value) : short_amount(value);
}

// 요청 하나(국고나 물자 한 칸)를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다.
// 썼으면 *wrote_it 이 true. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now, bool *wrote_it)
{
    *wrote_it = false;
```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
        g_last = target_name(r.slot) + " " + short_number(from) + " -> " + short_number(to);
```

이렇게 바꾼다:

```cpp
        *wrote_it = true;
        g_last = target_name(r.slot) + " " + shown(r.slot, from) + " -> " + shown(r.slot, to);
```

`native/srtoybox/keeper.cpp` 에서 다음 바로 앞에:

```cpp
}  // namespace
```

이것을 더한다:

```cpp
// "모든 물자": 이번 판에서 쓰는 물자마다 같은 일을 한다. 한 칸에 쓰는 것은 다른 칸의 값을 바꾸지 않으므로 now 를 다시 읽지 않는다.
bool apply_all(const Request &r, const GameValues &now)
{
    int count = 0;
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        if (!now.used[slot])
            continue;
        bool wrote_it = false;
        if (!apply({slot, r.change, r.amount}, now, &wrote_it))
            return false;
        count += wrote_it ? 1 : 0;
    }
    if (count > 0)
        g_last = "모든 물자 " + std::to_string(count) + "개";
    return true;
}

```

`native/srtoybox/keeper.cpp` 에서 다음을 찾아:

```cpp
        if (!apply(r, now)) {
```

이렇게 바꾼다:

```cpp
        bool wrote_it = false;
        if (!(r.slot == ALL_STOCK ? apply_all(r, now) : apply(r, now, &wrote_it))) {
```

`native/srtoybox/keeper.h` 에서 다음 바로 뒤에:

```cpp
const int TREASURY = -1;                       // Request.slot: 국고. 0 … STOCK_SLOTS - 1 은 그 칸의 물자 재고
```

이것을 더한다:

```cpp
const int ALL_STOCK = -2;                      // Request.slot: 이번 판에서 쓰는 물자 모두 — 쓸 때 칸마다의 요청으로 풀린다
```

`native/srtoybox/keeper.h` 에서 다음을 찾아:

```cpp
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B". 없으면 빈 글
```

이렇게 바꾼다:

```cpp
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개". 없으면 빈 글
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -2`

Expected: `빌드 완료: …`, `39 passed`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/keeper.h native/srtoybox/keeper.cpp native/srtoybox/game.cpp native/srtoybox/exports.cpp tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox 값 쓰기 요청 — 물자는 이름으로 적고, "모든 물자"는 쓰는 물자마다로 풀린다

- ALL_STOCK: 이번 판에서 쓰는 물자마다 같은 일을 한다. 쓰지 않는 물자의 칸과 다른 나라에는 닿지 않는다.
- 마지막으로 쓴 값과 로그에 물자의 이름과 자원 표시줄의 표기를 쓴다(석유 2.5 M -> 3.5 M).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `317 passed`.

---

### Task 4: 물자 탭 — 물자의 치트 단추를 지운다

**브랜치:** `feat/toybox-values-stock`

**Files:**
- Modify: `native/srtoybox/ui.cpp`, `native/srtoybox/features.cpp`, `src/srkit/cli.py`
- Test: `tests/test_toybox.py`, `tests/toybox_overlay_probe.py`

**Interfaces:**
- Consumes: Task 1 의 `product_label` · `find_product` · `short_amount`, Task 3 의 `ALL_STOCK` 과 `keeper_enqueue({칸, Change, 수량})`, 계획 (나)의 `game_values()` · `game_values_off()` · `money_tab`.
- Produces:
  - 탭의 순서: `돈` · `물자` · `연구` · `인구·여론` · `외교·영토` · `부대` · `화면·진행` · `설정`. 앞의 둘은 전용 화면이 그린다. 기능 표는 19줄(`products` · `branson` · `bezos` 가 없다).
  - 물자 탭이 그리는 것(창이 그린 것의 목록 — 테스트와 Task 5 · 8 이 이 이름을 쓴다): 줄마다 `stock:<칸>`(이름) · `stock:<칸>:now`(재고) · `stock:<칸>:-100m` · `:-1m` · `:zero` · `:+1m` · `:+100m`(단추 `-1억` · `-100만` · `0` · `+100만` · `+1억`). "모든 물자" 줄은 `stock:all` · `stock:all:now`(`-`) · `stock:all:<단추>`. 쓸 수 없으면 `stock:off`(까닭 한 줄)만.
  - 줄이 나오는 물자: 게임 안에서는 이번 판에서 쓰는 물자(`used`), 게임 밖에서는 이름표에 있는 물자(재고는 `-`, 단추는 꺼져 있다).
  - `bool money_tab(…)` · `bool stock_tab(…)` — 그 탭을 쓸 수 있었으면 `true`. `values_ready(game, name, &now)` 가 두 탭의 머리(쓸 수 없는 까닭)를 함께 그린다.
  - 바닥의 안내(`hint`): 돈 · 물자 탭에서는 쓸 수 있을 때 늘 `값은 바로 바뀝니다. …`, 쓸 수 없으면 없다.
  - 창의 첫 크기 720×520.
  - 검사 도구의 mode: `stock` · `stock_menu` · `money_fault` · `money_hint`, 그리고 `money_*` 의 출력에 `hint`(와 꺼진 까닭을 보는 mode 들에 `stock_off` · `stock_rows` · `stock_cheats`).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_toybox.py` 의 기능 표 · 설정의 기대값(22 → 19, `products` 가 없다)과 새 테스트 다섯, 검사 도구의 새 mode 들. 검사 도구의 창 밖 누름 자리(700,100)는 넓어진 창 안이 되므로 (900,100)으로 옮긴다.

<!-- 고칠 곳: test -->
`tests/test_toybox.py` 에서 다음을 찾아:

```python
TABS = ["물자", "연구", "인구·여론", "외교·영토", "부대", "화면·진행"]     # 기능 표의 탭. "돈" 탭은 기능 표가 아니라 전용 화면이 그린다
```

이렇게 바꾼다:

```python
TABS = ["연구", "인구·여론", "외교·영토", "부대", "화면·진행"]     # 기능 표의 탭. "돈" · "물자" 탭은 기능 표가 아니라 전용 화면이 그린다
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert len(fs) == 22
    assert len({f["id"] for f in fs}) == 22 and len({f["command"] for f in fs}) == 22
    assert not {"treasury", "georgew", "georgeww"} & {f["id"] for f in fs}   # 국고는 내장 치트를 거치지 않는다(돈 탭)
```

이렇게 바꾼다:

```python
    assert len(fs) == 19
    assert len({f["id"] for f in fs}) == 19 and len({f["command"] for f in fs}) == 19
    # 국고와 물자는 내장 치트를 거치지 않는다(돈 탭 · 물자 탭)
    assert not {"treasury", "georgew", "georgeww", "products", "branson", "bezos"} & {f["id"] for f in fs}
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert {f["id"] for f in fs if f["has_value"]} == {"products", "technology", "spawnunit"}
```

이렇게 바꾼다:

```python
    assert {f["id"] for f in fs if f["has_value"]} == {"technology", "spawnunit"}
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert dll.srtoybox_feature_info(22, ctypes.create_string_buffer(8), 8) == -1
```

이렇게 바꾼다:

```python
    assert dll.srtoybox_feature_info(19, ctypes.create_string_buffer(8), 8) == -1
```

`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
    assert text(dll.srtoybox_command, b"technology", 1, 0, size=4) is None                     # 버퍼가 작으면 넘치지 않고 -1
```

이것을 더한다:

```python
    assert text(dll.srtoybox_command, b"products", 1, 0) is None                               # 〃 — 물자는 물자 탭이
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\nproducts=100000\ntechnology=120\nspawnunit=2413\n"
```

이렇게 바꾼다:

```python
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\ntechnology=120\nspawnunit=2413\n"
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert norm("money.amount=0\nproducts=999999999999\ntechnology=abc\nspawnunit=12x\n") == DEFAULTS   # 범위 밖·숫자 아님 → 기본값
    assert norm("unknown=5\ngeorgew=7\ndepopulate=1\ntreasury=500\n") == DEFAULTS            # 모르는 키, 값이 없는 기능, 지운 기능
```

이렇게 바꾼다:

```python
    assert norm("money.amount=0\ntechnology=999999999999\nspawnunit=12x\n") == DEFAULTS       # 범위 밖·숫자 아님 → 기본값
    assert norm("technology=abc\n") == DEFAULTS
    assert norm("unknown=5\nfinalexam=7\ndepopulate=1\ntreasury=500\nproducts=5\n") == DEFAULTS   # 모르는 키, 값이 없는 기능, 지운 기능
```

`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
def test_money_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
```

이것을 더한다:

```python
DIRECT_HINT = "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다."


@pytest.mark.parametrize("env", [{}, {"SRTOYBOX_DIRECT": "0"}], ids=["direct", "typing"])
def test_the_hint_on_a_value_tab_never_talks_about_the_typing_route(dll, cfg, tmp_path, env):
    """돈 · 물자 탭은 글쇠 방식과 상관없다. 내장 치트로 도는 기능이 글쇠 방식으로 돌 때(SRTOYBOX_DIRECT=0, 옛 찾기 실패)에도
    이 탭들의 바닥 안내는 "게임의 설정 창이 잠깐 열렸다 닫힙니다"가 아니다."""
    got = json.loads(_probe(cfg, tmp_path, "money_hint", env=env))
    assert got["hint"] == DIRECT_HINT and got["stock_hint"] == DIRECT_HINT
    assert got["cheat_hint"] == (DIRECT_HINT if not env else "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.")


```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
    assert got["off"] == why and got["now"] == "-"
    assert got["buttons"] == [] and got["cheat_buttons"] == []
```

이렇게 바꾼다:

```python
    assert got["off"] == why and got["now"] == "-" and got["hint"] == "-"
    assert got["buttons"] == [] and got["cheat_buttons"] == []
    assert got["stock_off"] == why and got["stock_rows"] == [] and got["stock_cheats"] == []      # 물자 탭도 같다
```

`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
def test_prologue_length_knows_only_plain_function_heads(dll):
```

이것을 더한다:

```python
def test_values_are_not_written_after_the_fault_guard_trips(dll, cfg, tmp_path):
    """직접 실행의 오류 가드가 걸린 뒤에는 값 쓰기도 멈춘다 — 대기열에 먼저 들어와 있던 국고 요청도 버린다."""
    got = json.loads(_probe(cfg, tmp_path, "money_fault"))
    assert got["fault"] == FAULT_WARNING and got["after"] == 14.43e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "값 쓰기: " not in log


STOCK_BUTTONS = ["+100m", "+1m", "-100m", "-1m", "zero"]
PRODUCTS = ["농산물", "고무", "목재", "석유", "석탄", "금속 광석", "우라늄", "전력", "소비재", "산업재", "군수품"]


def test_the_stock_tab_writes_stock_without_any_cheat(dll, cfg, tmp_path):
    """요구 3: 물자 탭도 내장 치트를 거치지 않는다. 이번 판에서 쓰는 물자만 줄로 나오고, "모든 물자" 줄은 그 물자들에만 닿는다.
    쓰는 곳은 플레이어의 재고뿐이다(다른 나라의 재고, 쓰지 않는 물자의 칸은 그대로다)."""
    got = json.loads(_probe(cfg, tmp_path, "stock"))
    assert got["off"] == "-" and got["hint"] == DIRECT_HINT and got["cheat_buttons"] == []
    assert got["rows"] == [["stock:all", "모든 물자", "-"], ["stock:0", "농산물", "1.0 K"], ["stock:3", "석유", "2.5 M"],
                           ["stock:7", "전력", "0"], ["stock:11", "물자 #11", "5"]]     # 열두째 칸은 이름이 없어도 쓰는 판이면 나온다
    assert got["buttons"] == STOCK_BUTTONS
    # 재고의 칸 0 · 3 · 7 · 11 과 쓰지 않는 칸 5. 석유 +100만, -1억, +1억, 0 / 모든 물자 +100만, -1억 / 농산물 +1억
    assert got["steps"] == [[1000.0, 3.5e6, 0.0, 5.0, 0.0], [1000.0, 0.0, 0.0, 5.0, 0.0], [1000.0, 1e8, 0.0, 5.0, 0.0],
                            [1000.0, 0.0, 0.0, 5.0, 0.0], [1001000.0, 1e6, 1e6, 1000005.0, 0.0], [0.0, 0.0, 0.0, 0.0, 0.0],
                            [1e8, 0.0, 0.0, 0.0, 0.0]]
    assert got["wrote_all"] == "모든 물자 4개" and got["wrote"] == "농산물 0 -> 100 M" and got["now_after"] == "100 M"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["poland"] == 777.0
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: 석유") == 6 and log.count("값 쓰기: ") == 13 and "직접 실행" not in log


def test_the_stock_tab_lists_the_named_products_outside_a_game(dll, cfg, tmp_path):
    """메뉴에서는 이름표의 물자 열하나가 재고 없이 나오고 단추가 꺼져 있다."""
    got = json.loads(_probe(cfg, tmp_path, "stock_menu"))
    assert got["rows"] == [["stock:all", "모든 물자", "-"]] + [[f"stock:{slot}", name, "-"] for slot, name in enumerate(PRODUCTS)]
    assert got["buttons"] == STOCK_BUTTONS and got["hint"] == "-"
    assert got["steps"] == [[1000.0, 2.5e6, 0.0, 5.0, 0.0]] and got["lines"] == [] and got["text"] == ""
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
설정 창에 보이는 글 (출력은 JSON 한 줄. 보이지 않는 글은 "-"):
```

이것을 더한다:

```python
    money_fault      옮기지 않은 기능의 직접 실행이 죽는다(오류 가드) — 함께 대기열에 있던 국고 요청을 쓰지 않는다
    money_hint       게임 안에서 돈 · 물자 탭과 내장 치트로 도는 탭의 바닥 안내
물자 탭 — 내장 치트를 거치지 않고 물자 재고를 고친다 (출력은 JSON 한 줄):
    stock            게임 안(물자 0 · 3 · 7 · 11 을 쓰는 판)에서 석유의 단추, "모든 물자"의 단추, 농산물의 단추를 누른다
    stock_menu       메뉴에 있다 — 이름표의 물자가 재고 없이 나오고 단추가 꺼져 있다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
        game.hotkey()
```

이렇게 바꾼다:

```python
        game.open()                                           # 내장 치트로 도는 탭에서 본다(돈 · 물자 탭의 안내는 money_hint 가 본다)
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    fake = box["fake"] = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value, values=mode != "money_notfound")
```

이렇게 바꾼다:

```python
    handler = crash_stub() if mode == "money_fault" else ctypes.cast(game.handler, ctypes.c_void_p).value
    fake = box["fake"] = fake_game(hook, handler, values=mode != "money_notfound")
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    out: dict[str, object] = {"now": game.shown("money:now"), "off": game.shown("money:off")}
```

이렇게 바꾼다:

```python
    out: dict[str, object] = {"now": game.shown("money:now"), "off": game.shown("money:off"), "hint": game.shown("hint")}
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    out["lines"], out["text"], out["options"], out["poland"] = lines, game.text(), fake.peek(OPTIONS, "<I"), fake.treasury(141)
```

이렇게 바꾼다:

```python
    elif mode == "money_fault":
        game.click(CHEAT_TAB)
        game.click(BUTTON)                                    # 옮기지 않은 기능 하나가 대기열에 든다 — 실행되면 죽는다
        game.click(MONEY)
        game.click("money:+10b")                              # 국고 요청도 대기열에 든다
        game.wait(0.5)
        out["after"], out["fault"] = fake.treasury(176), game.shown("fault")
    elif mode == "money_hint":
        game.click(STOCK)
        out["stock_hint"] = game.shown("hint")
        game.click(CHEAT_TAB)
        out["cheat_hint"] = game.shown("hint")
    elif mode in ("money_write_off", "money_notfound", "money_unread", "money_unreadable"):
        game.click(STOCK)                                     # 물자 탭도 같은 까닭 한 줄뿐이어야 한다
        facts = game.facts()
        out["stock_off"] = game.shown("stock:off")
        out["stock_rows"] = sorted(name for name in facts if name.startswith("stock:") and name != "stock:off")
        out["stock_cheats"] = sorted(name for name in facts if name.startswith("run:"))
    out["lines"], out["text"], out["options"], out["poland"] = lines, game.text(), fake.peek(OPTIONS, "<I"), fake.treasury(141)
    print(json.dumps(out, ensure_ascii=False))
    return 0


STOCK = "tab:물자"
STOCK_SLOTS_SEEN = (0, 3, 7, 11, 5)     # run_stock 이 재고를 적어 내는 칸: 쓰는 물자 넷과 쓰지 않는 물자 하나


def run_stock(hook: str, mode: str) -> int:
    """물자 탭: 내장 치트를 거치지 않고 물자 재고를 고친다. 출력은 JSON 한 줄(보이지 않는 글은 "-").

    독일은 물자 0(농산물 1000) · 3(석유 250만) · 7(전력 0) · 11(이름 없는 열두째 칸, 5)을 쓴다. 폴란드의 석유는 777 이다.
    """
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    game.handler = HANDLER(lambda _context, line: lines.append(line.decode()))   # 불리면 안 된다
    fake = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value)
    for slot, amount in ((0, 1000.0), (3, 2.5e6), (7, 0.0), (11, 5.0)):
        fake.use(slot)
        fake.set_stock(176, slot, amount)
    fake.set_stock(141, 3, 777.0)
    if mode != "stock_menu":
        fake.play(176)
    game.hotkey()
    game.click(STOCK)
    game.got.clear()
    facts = game.facts()
    rows = [name for name in facts if name.startswith("stock:") and name.count(":") == 1 and name != "stock:off"]   # 그린 순서대로
    out: dict[str, object] = {"off": game.shown("stock:off"), "hint": game.shown("hint"),
                              "rows": [[name, facts[name][3], facts[name + ":now"][3]] for name in rows],
                              "cheat_buttons": sorted(name for name in facts if name.startswith("run:")),
                              "buttons": sorted(name[len("stock:3:"):] for name in facts
                                                if name.startswith("stock:3:") and name != "stock:3:now")}

    def press(name: str) -> list[float]:
        game.click(name)
        game.wait(0.2)                                        # 쓰는 것은 다음 타이머에서다
        return [fake.stock(176, slot) for slot in STOCK_SLOTS_SEEN]

    if mode == "stock":
        out["steps"] = [press(name) for name in ("stock:3:+1m", "stock:3:-100m", "stock:3:+100m", "stock:3:zero", "stock:all:+1m",
                                                 "stock:all:-100m")]
        out["wrote_all"] = game.shown("wrote")
        out["steps"].append(press("stock:0:+100m"))
        out["wrote"], out["now_after"] = game.shown("wrote"), game.shown("stock:0:now")
    else:
        out["steps"] = [press("stock:3:+1m")]
        out["status"] = game.shown("status")
    out["lines"], out["text"], out["options"], out["poland"] = lines, game.text(), fake.peek(OPTIONS, "<I"), fake.stock(141, 3)
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    out["outside"] = game.click((700, 100))                   # 설정 창 밖 — 게임이 받아야 한다
```

이렇게 바꾼다:

```python
    out["outside"] = game.click((900, 100))                   # 설정 창 밖(창은 40..760 x 60..580 이다) — 게임이 받아야 한다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
    # 설정 창은 그리는 좌표로 40..540 x 60..520 에 있고, 화면(창의 좌표)에는 80..1080 x 120..1040 으로 보인다
```

이렇게 바꾼다:

```python
    # 설정 창은 그리는 좌표로 40..760 x 60..580 에 있고, 화면(창의 좌표)에는 80..1520 x 120..1160 으로 보인다
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    if mode in ("confirm", "confirm_fault", "hints", "leave", "multiplayer", "pick_gone", "pick_become", "pick_again", "ansi_search"):
```

이것을 더한다:

```python
    if mode.startswith("stock"):
        return run_stock(hook, mode)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox.py -q 2>&1 | tail -22`

Expected: `11 failed, 54 passed` — `test_feature_table`(`assert 22 == 19`), `test_command_text`(`cheat products 1` 이 아직 만들어진다), `test_settings_fall_back_to_defaults` · `test_settings_file_round_trip`(기본 설정에 `products=100000` 이 남아 있다), `test_the_hint_on_a_value_tab_never_talks_about_the_typing_route[typing]`(돈 탭의 안내가 "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다."다), `test_the_money_tab_says_why_it_is_off_and_offers_no_cheat` 의 네 줄(물자 탭에 까닭이 없다 — 아직 치트 단추가 있는 탭이다), `test_the_stock_tab_writes_stock_without_any_cheat` · `test_the_stock_tab_lists_the_named_products_outside_a_game`(검사 도구가 `KeyError: 'stock:3:+1m'` 로 끝난다). **`test_values_are_not_written_after_the_fault_guard_trips` 와 `…typing_route[direct]` 는 지금도 통과한다** — 앞의 것은 이미 있는 동작(오류 가드 뒤에는 대기열을 버린다)을 처음으로 밟는 테스트다. 계획을 쓰며 그 가드를 뺀 빌드에서 이 테스트가 실패하는 것을 봤다(국고가 `24430000000.0` 이 된다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/features.cpp` 에서 다음을 찾아:

```cpp
// 국고의 세 줄(treasury · georgew · georgeww)은 3단계 1 에서 지웠다 — 돈 탭이 내장 치트 없이 직접 한다(ui.cpp 의 money_tab).
// 남은 줄은 아직 내장 치트로 돈다. 묶음마다 옮기고 지운다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
    {"products", "물자", "모든 물자 추가", "입력한 수량만큼 모든 물자의 재고가 늘어난다", "cheat products", true, 100000, 1, 100000000, false},
    {"branson", "물자", "모든 물자 +100만", "모든 물자의 재고가 100만씩 늘어난다", "cheat branson", false, 0, 0, 0, false},
    {"bezos", "물자", "모든 물자 +1억", "모든 물자의 재고가 약 1억씩 늘어난다", "cheat bezos", false, 0, 0, 0, false},
```

이렇게 바꾼다:

```cpp
// 국고의 세 줄(treasury · georgew · georgeww)과 물자의 세 줄(products · branson · bezos)은 3단계 1 에서 지웠다 —
// 돈 탭과 물자 탭이 내장 치트 없이 직접 한다(ui.cpp 의 money_tab · stock_tab).
// 남은 줄은 아직 내장 치트로 돈다. 묶음마다 옮기고 지운다(docs/10-toybox.md 의 "다음 단계").
const Feature FEATURES[] = {
```

`native/srtoybox/ui.cpp` 에서 다음 바로 앞에:

```cpp
#include "regions.h"
```

이것을 더한다:

```cpp
#include "products.h"
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
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
    if (game.in_game && !now.ok) {   // 게임 안인데 값을 믿을 수 없다(재고 칸이 수가 아니다, 세계 자료를 읽지 못했다) — 까닭 없이 꺼 두지 않는다
        const char *const why = "게임의 값을 읽을 수 없어 쓸 수 없습니다.";
        ImGui::TextWrapped("%s", why);
        note("money:off", why);
        return;
    }
```

이렇게 바꾼다:

```cpp
// 값을 쓰는 탭(돈 · 물자)의 머리. 쓸 수 없으면 까닭 한 줄만 그리고(name 으로 적는다) false — 내장 치트로 되돌아가지 않는다.
// 쓸 수 있으면 true 와 *now(탭이 보이는 동안 프레임마다 읽는다. 게임 밖이면 ok 가 거짓인 빈 값).
bool values_ready(const GameState &game, const char *name, GameValues *now)
{
    std::string off = game.known ? game_values_off() : std::string("게임 상태를 읽을 수 있을 때만 씁니다.");
    if (off.empty()) {
        *now = game.in_game ? game_values() : GameValues();
        if (game.in_game && !now->ok)   // 게임 안인데 값을 믿을 수 없다(재고 칸이 수가 아니다, 세계 자료를 읽지 못했다) — 까닭 없이 꺼 두지 않는다
            off = "게임의 값을 읽을 수 없어 쓸 수 없습니다.";
    }
    if (off.empty())
        return true;
    ImGui::TextWrapped("%s", off.c_str());
    note(name, off);
    return false;
}

// 돈 탭: 내장 치트를 거치지 않고 플레이어의 국고를 직접 고친다(기능 표가 아니라 여기서 그린다). 쓸 수 있으면 true.
bool money_tab(const GameState &game, bool blocked)
{
    GameValues now;
    if (!values_ready(game, "money:off", &now))
        return false;
```

`native/srtoybox/ui.cpp` 에서 다음 바로 뒤에:

```cpp
    ImGui::TextDisabled("국고는 음수가 될 수 있다. 다른 나라의 국고는 건드리지 않는다");
    ImGui::EndDisabled();
```

이것을 더한다:

```cpp
    return true;
}

// 물자 탭의 한 줄에 놓이는 단추 다섯: 그 칸(또는 ALL_STOCK)의 재고에서 빼고, 0 으로 만들고, 더한다.
void stock_buttons(const std::string &name, int slot)
{
    static const struct {
        const char *label, *id;
        Change change;
        double amount;
    } BUTTONS[] = {
        {"-1억", ":-100m", Change::Add, -1e8}, {"-100만", ":-1m", Change::Add, -1e6}, {"0", ":zero", Change::Set, 0.0},
        {"+100만", ":+1m", Change::Add, 1e6}, {"+1억", ":+100m", Change::Add, 1e8},
    };
    for (size_t i = 0; i < sizeof(BUTTONS) / sizeof(BUTTONS[0]); i++) {
        if (i > 0)
            ImGui::SameLine();
        const bool pressed = ImGui::Button(BUTTONS[i].label);
        note(name + BUTTONS[i].id, BUTTONS[i].label);
        if (pressed)
            g_notice = keeper_enqueue({slot, BUTTONS[i].change, BUTTONS[i].amount}) ? "" : "대기 중인 요청이 많아 받지 못했습니다.";
    }
}

// 물자 탭의 한 줄. slot 이 ALL_STOCK 이면 "모든 물자" 줄이다(재고 표시가 없다).
void stock_row(int slot, const GameValues &now, bool blocked)
{
    const bool all = slot == ALL_STOCK;
    const std::string name = all ? std::string("stock:all") : "stock:" + std::to_string(slot);
    const std::string label = all ? std::string("모든 물자") : product_label(slot);
    const std::string have = all || !now.ok ? std::string("-") : short_amount(now.stock[slot]);
    ImGui::PushID(slot);
    ImGui::TableNextRow();
    ImGui::TableNextColumn();
    ImGui::AlignTextToFramePadding();
    ImGui::TextUnformatted(label.c_str());
    note(name, label);
    ImGui::TableNextColumn();
    ImGui::AlignTextToFramePadding();
    ImGui::TextUnformatted(have.c_str());
    note(name + ":now", have);
    ImGui::TableNextColumn();
    ImGui::BeginDisabled(blocked || !now.ok);
    stock_buttons(name, slot);
    ImGui::EndDisabled();
    ImGui::PopID();
}

// 물자 탭: 내장 치트를 거치지 않고 플레이어의 물자 재고를 직접 고친다. 물자마다 한 줄 —
// 게임 안에서는 이번 판에서 쓰는 물자만, 게임 밖에서는 이름표에 있는 물자가 나온다(단추는 꺼져 있다). 쓸 수 있으면 true.
bool stock_tab(const GameState &game, bool blocked)
{
    GameValues now;
    if (!values_ready(game, "stock:off", &now))
        return false;
    ImGui::TextDisabled("재고는 0 아래로 내려가지 않는다. 다른 나라의 재고는 건드리지 않는다");
    const ImGuiTableFlags flags = ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_RowBg | ImGuiTableFlags_BordersInnerV
        | ImGuiTableFlags_ScrollX | ImGuiTableFlags_ScrollY;   // 창이 좁으면 표가 가로로 구른다
    if (!ImGui::BeginTable("stock", 3, flags))
        return true;
    ImGui::TableSetupScrollFreeze(1, 1);                       // 이름 칸과 머리 줄은 굴려도 남는다
    ImGui::TableSetupColumn("물자");
    ImGui::TableSetupColumn("재고");
    ImGui::TableSetupColumn("빼기 / 더하기");
    ImGui::TableHeadersRow();
    stock_row(ALL_STOCK, now, blocked);
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (now.ok ? now.used[slot] : find_product(slot) != nullptr)
            stock_row(slot, now, blocked);
    ImGui::EndTable();
    return true;
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
    ImGui::SetNextWindowSize(ImVec2(500.0f, 460.0f), ImGuiCond_FirstUseEver);
```

이렇게 바꾼다:

```cpp
    ImGui::SetNextWindowSize(ImVec2(720.0f, 520.0f), ImGuiCond_FirstUseEver);   // 물자 탭의 표가 한눈에 들어오는 크기
```

`native/srtoybox/ui.cpp` 에서 다음 바로 앞에:

```cpp
        if (ImGui::BeginTabBar("tabs")) {
```

이것을 더한다:

```cpp
        bool values_tab = false, values_ok = false;         // 지금 보이는 탭이 값을 직접 쓰는 탭(돈 · 물자)인가, 그 탭을 쓸 수 있는가
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
                if (ImGui::BeginChild("body", body))
                    money_tab(game, blocked);
```

이렇게 바꾼다:

```cpp
                values_tab = true;
                if (ImGui::BeginChild("body", body))
                    values_ok = money_tab(game, blocked);
                ImGui::EndChild();
                ImGui::EndTabItem();
            }
            const bool stock = ImGui::BeginTabItem("물자");   // 둘째 탭. 이것도 기능 표에 없다
            note("tab:물자", "물자");
            if (stock) {
                values_tab = true;
                if (ImGui::BeginChild("body", body))
                    values_ok = stock_tab(game, blocked);
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
        const char *const hint = game.known && blocked ? nullptr
            : game.known && runner_direct() ? "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다."
```

이렇게 바꾼다:

```cpp
        // 값을 직접 쓰는 탭(돈 · 물자)은 글쇠 방식과 상관없다 — 쓸 수 있으면 늘 바로 바뀌고, 쓸 수 없으면 탭의 까닭 한 줄이 전부다.
        const char *const direct = "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다.";
        const char *const hint = game.known && blocked ? nullptr
            : values_tab ? (values_ok ? direct : nullptr)
            : game.known && runner_direct() ? direct
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
        if (!game.known)   // 게임을 읽지 못하면 단추를 끌 수 없다
```

이렇게 바꾼다:

```cpp
        if (!game.known && !values_tab)   // 게임을 읽지 못하면 내장 치트로 도는 단추를 끌 수 없다
```

`src/srkit/cli.py` 에서 다음을 찾아:

```python
        print("ToyBox 의 돈 탭이 이 빌드에서 꺼집니다. uv run srkit sig-mine [--offset] 으로 서명을 다시 뽑습니다(docs/11).")
```

이렇게 바꾼다:

```python
        print("ToyBox 의 돈 · 물자 탭이 이 빌드에서 꺼집니다. uv run srkit sig-mine [--offset] 으로 서명을 다시 뽑습니다(docs/11).")
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox.py -q 2>&1 | tail -2`

Expected: `빌드 완료: …`, `65 passed`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/ui.cpp native/srtoybox/features.cpp src/srkit/cli.py tests/test_toybox.py tests/toybox_overlay_probe.py && git commit -q -F - <<'EOF'
feat: ToyBox 물자 탭 — 물자마다 재고를 내장 치트 없이 직접 고친다

- 물자 탭: 이번 판에서 쓰는 물자마다 한 줄(재고, -1억 · -100만 · 0 · +100만 · +1억)과 "모든 물자" 줄.
  게임 밖에서는 이름표의 물자가 재고 없이 나오고 단추가 꺼져 있다. 쓸 수 없으면 까닭 한 줄만 — 내장 치트로 되돌아가지 않는다.
- 물자의 치트 단추 셋(products · branson · bezos)을 지운다. 내장 치트로 도는 기능은 19개가 남는다.
- 돈 · 물자 탭의 바닥 안내는 글쇠 방식과 상관없다(옛 찾기 실패, SRTOYBOX_DIRECT=0 에서도 "설정 창이 열렸다 닫힙니다"가 아니다).
- 창의 첫 크기 720x520.
- 테스트: 오류 가드가 걸린 뒤에는 대기열의 값 쓰기도 버린다(계획 (나)의 최종 검토가 남긴 것).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `322 passed`.

---

### Task 5: 게임 안 확인 — 칸과 이름, 열두째 칸, 물자 탭 (V5 · V6 · V7)

**브랜치:** `feat/toybox-values-stock` (게임이 떠 있는 동안 바꾸지 않는다)

**Files:**
- 코드는 고치지 않는다. 근거 화면과 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.

**Interfaces:**
- Consumes: Task 4 의 빌드, 계획 (나)의 `gamedrive.py peek`(`stock` 12칸 · `used` 12칸 · `treasury` · `cheats_allowed`).
- Produces: 이 Task 의 결과(`vc-stock.md` — Task 10 이 `docs/10` 에 적는다)와 `develop` 에 머지된 PR.

**이 Task 가 가르는 것**: 물자 이름표가 맞는가. 이름표는 "번역 표의 물자 목록 순서 = 재고 칸의 순서"라는 추정으로 만들었다. 한 줄이라도 다른 물자가 오르면 머지하지 않고 멈춘다.

- [ ] **Step 1: PR 을 올린다 (머지는 게임 안 확인 뒤에)**

스크래치에 `pr-values-stock.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 1 ~ 4 의 커밋 요약), 요구 3 에 대해 자동 테스트가 보는 것(물자 탭이 명령 처리 함수를 부르지 않고 글쇠를 넣지 않고 치트 허용 비트를 건드리지 않는다 · 쓰는 곳은 플레이어의 그 칸뿐이다 · 쓰지 않는 물자의 칸에는 쓰지 않는다), 설계서와 달라진 곳(이 계획의 같은 이름의 절에서 이 PR 에 닿는 것들), "게임 안 확인은 아래 댓글에", "코드의 최종 검토는 다음 PR(최소 유지)을 머지하기 전에 두 PR 을 함께 놓고 받는다", `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-values-stock && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-values-stock --title "feat: ToyBox 물자 탭 — 물자마다 재고를 내장 치트 없이 직접 고친다" --body-file "<스크래치>/pr-values-stock.md"
```

- [ ] **Step 2: 시험용 빌드를 게임 폴더에 바꿔 넣고, 검증 전의 상태를 적어 둔다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-vc && rm -f build/verify/toybox-home-vc/* && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/VC-saves-before.txt && cat build/verify/toybox/VC-saves-before.txt
```

`build/verify/toybox-home-vc` 는 검증용 게임의 ToyBox 설정 폴더다(비어 있으므로 단축키는 기본값 `Ctrl+Shift+T`). 사용자의 `%APPDATA%\SR2030ToyBox` 는 건드리지 않는다.

- [ ] **Step 3: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)의 "물자" 탭을 게임에서 확인한다. 이 작업(VC)만 수행하라.
끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다).
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법)과 E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법" · "확인한 것"의 VB 표(게임에 들어가는 길, 시간을 흘리는 법)를 읽는다.

규칙:
- 게임은 다음으로만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-vc' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|peek|stop> …
- gamedrive.py peek 은 게임의 메모리에서 읽은 값을 JSON 으로 낸다: stock = 플레이어의 재고 열두 칸(칸 0 … 11), used = 그 칸의 물자를 이번 판에서 쓰는가,
  treasury = 국고, cheats_allowed = 치트 허용 비트, in_game. ToyBox 의 창에 보이는 숫자와 따로 본다.
- ToyBox 의 물자 탭: 물자마다 한 줄(이름, 재고, 단추 "-1억" "-100만" "0" "+100만" "+1억"). 맨 위는 "모든 물자" 줄이다.
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간은 6 에서만, 거기 적힌 만큼만 흘린다. 그 밖에는 일시 정지인 채로 둔다.
- cheat resettutorial · cheat depopulate 는 어떤 경우에도 넣지 않는다. "물자" 탭 밖의 ToyBox 단추를 누르지 않는다.
- ToyBox 창은 처음에 화면의 왼쪽 위(40,60)에 720x520 으로 열린다. 게임의 위쪽 자원 표시줄이나 패널을 가리면 창을 닫고(같은 단축키) 본다.
- 화면은 E:\SR2030ToyBox\build\verify\toybox\VC-<번호>-<이름>.png 로 찍는다.
- ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-vc\toybox.log 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다. peek 의 출력은 그대로 옮긴다):
1. 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다(20초쯤. 빈 화면이면 기다렸다 다시 찍는다).
   로그에서 "게임 상태를 읽습니다 (…)", "값을 씁니다 (…)", "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (…)" 세 줄을 그대로 옮겨 적는다(기능의 수는 19 여야 한다).
2. 메인 메뉴에서 key CTRL+SHIFT+T 로 ToyBox 창을 열고 "물자" 탭을 누른다. 탭의 순서(돈, 물자, 연구, …), 물자 탭에 나온 줄의 이름을 위에서부터 모두,
   재고 칸의 글, 단추가 흐린지(꺼져 있는지)를 적는다. "석유" 줄의 "+100만" 을 한 번 누르고 로그에 새 줄이 생겼는지 적는다(생기면 안 된다).
3. 창을 닫고, 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 게임 화면이 뜨면 일시 정지 상태인지 본다.
4. peek 을 찍는다(S0 = stock 열두 칸, used 열두 칸, cheats_allowed 는 0 이어야 한다).
   ToyBox 창을 열어 "물자" 탭의 줄을 위에서부터 모두 적는다: 이름과 재고 칸의 글. 나온 줄의 수와 used 가 true 인 칸의 수가 같은지 적는다.
   창을 닫고 게임의 위쪽 자원 표시줄을 찍는다. 표시줄에 보이는 물자마다(아이콘에 마우스를 올려 move 로 툴팁을 보면 이름이 나온다) 그 숫자가
   ToyBox 의 같은 이름의 줄의 재고 칸과 같은 글인지 적는다(예: 둘 다 "23.7 M"). 표시줄에 없는 물자는 게임의 물자 패널(경제 · 생산 쪽)에서 찾아본다 —
   찾지 못한 물자는 "게임 화면에서 그 물자의 재고를 보지 못했다"고 적는다.
5. 칸과 이름의 대응. ToyBox 의 "물자" 탭에 나온 줄마다(모든 물자 줄은 빼고, 위에서부터 하나씩) 다음을 한다:
   (a) 그 줄의 "+1억" 을 한 번 누른다. (b) peek 을 찍어 stock 의 어느 칸이 1억(100000000) 늘었는지 적는다 — 한 칸만 늘어야 한다.
   (c) ToyBox 창을 닫고 게임 화면에서 그 물자의 재고가 오른 것을 찍는다(자원 표시줄이나 물자 패널. 숫자가 그대로면 패널을 닫았다 다시 열어 본다.
       그래도 그대로면 그대로라고 적는다 — 시간을 흘리지는 않는다). 오른 것이 ToyBox 의 그 줄의 이름과 같은 물자인지 적는다.
   (d) ToyBox 창을 다시 열어 그 줄의 재고 칸의 글과, 창 바닥의 "마지막으로 쓴 값: …" 을 적는다.
   기대: ToyBox 의 줄이 위에서부터 농산물, 고무, 목재, 석유, 석탄, 금속 광석, 우라늄, 전력, 소비재, 산업재, 군수품이고, 그 순서대로 칸 0, 1, …, 10 이 는다.
   cheats_allowed 는 끝까지 0. 게임의 설정 창(빨간 제목의 창)이 한 번이라도 떴는지 적는다(뜨면 안 된다).
   하나라도 기대와 다르면(다른 칸이 늘었다, 게임 화면에서 다른 물자가 올랐다) 그 줄에서 멈추지 말고 끝까지 하되, 다른 것을 빠짐없이 적는다.
6. 열두째 칸. peek 의 used 의 마지막(칸 11)이 true 인지 false 인지, ToyBox 에 "물자 #11" 줄이 있는지 적는다.
7. 한 줄의 단추. "석유" 줄에서 차례로 누르고, 누를 때마다 peek 의 stock[3] 과 ToyBox 의 재고 칸의 글, "마지막으로 쓴 값: …" 을 적는다:
   (a) "0"  (b) "-100만"(0 에서 더 내려가지 않아야 한다. "마지막으로 쓴 값"도 바뀌지 않아야 한다)  (c) "+100만"  (d) "-1억"(0 이 되어야 한다)  (e) "+1억"
8. "모든 물자" 줄. (a) "+100만" 을 누르고 peek 을 찍는다 — used 가 true 인 칸이 모두 정확히 1000000 씩 늘고 false 인 칸은 그대로여야 한다.
   "마지막으로 쓴 값"(기대: "모든 물자 11개")을 적는다. (b) "0" 을 누르고 peek(쓰는 칸이 모두 0) (c) "+1억" 을 눌러 재고를 돌려놓고 peek.
9. 재고가 0 일 때와 시간. "모든 물자"의 "0" 을 한 번 더 눌러 재고를 모두 0 으로 만들고(peek 으로 확인) ToyBox 창을 닫는다.
   게임의 속도를 "매우 느림"으로 실제 10초 흘린 뒤 다시 일시 정지한다(게임 날짜가 하루를 넘기지 않게 — 넘길 것 같으면 더 일찍 멈춘다).
   게임이 살아 있는지(화면이 그려지는지), peek 의 stock(게임이 그 사이에 고쳤을 수 있다 — 본 값을 그대로), 게임의 날짜 · 시각, 화면에 뜬 경고를 적는다.
   그 뒤 ToyBox 창을 열어 "모든 물자"의 "+1억" 으로 재고를 돌려놓는다.
10. 창을 닫고, 게임의 메뉴(ESC) → "게임 종료" → 저장하지 않고 메인 메뉴로 나온다. gamedrive.py stop 으로 게임을 끈다. status 로 꺼진 것을 확인한다.
    로그를 E:\SR2030ToyBox\build\verify\toybox\VC.log 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). 5 는 줄마다 한 줄의 표로(ToyBox 의 이름 / 늘어난 칸 / 게임 화면에서 오른 물자 / 재고 칸의 글).
로그에 "예외" 나 "실패" 가 든 줄이 있으면 그대로 옮긴다. 보지 못한 것은 "보지 못했다"와 까닭.
기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않는다.

- [ ] **Step 4: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "게임 상태를\|값을 \|옛 방식\|직접 실행\|예외\|실패" build/verify/toybox/VC.log; grep -c "값 쓰기: " build/verify/toybox/VC.log; grep -n "값 쓰기: 모든\|값 쓰기: 국고" build/verify/toybox/VC.log | head; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/VC-saves-before.txt && echo "저장 폴더 그대로"
```

Expected:
- `게임 상태를 읽습니다 (서명 21개 가운데 21개, N ms)`, `값을 씁니다 (국고 +0x14B88, 재고 +0x14DA4 간격 0x150 × 12)`, `옛 방식(내장 치트)으로 도는 기능이 19개 남아 있습니다 (명령 처리 함수 +0x522330)` 가 한 줄씩.
- `값 쓰기: <물자 이름> … -> …` 줄이 여럿(5 의 열하나, 7 의 넷, 8 · 9 의 물자마다). `값 쓰기: 국고` 는 없다. `직접 실행` · `예외` · `실패` 가 든 줄이 없다.
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-values-stock` 다. `저장 폴더 그대로`.

Read 도구로 화면을 직접 본다: 게임 안의 물자 탭(4), 5 의 줄 가운데 셋(석유 · 전력 · 군수품)의 앞뒤, 8 의 뒤. 에이전트가 적은 이름 · 숫자와 화면이 같은지 본다.

**이름표가 틀리면 멈춘다**: 5 에서 ToyBox 의 이름과 게임 화면에서 오른 물자가 한 줄이라도 다르면 머지하지 않는다. 본 대응을 그대로 사용자에게 알리고, 이름표를 본 순서로 고치는 일(`toybox.product_rows` 에 칸 → 물자 목록 번호의 표를 두는 것)은 사용자의 확인 뒤에 한다. 게임 화면에서 재고를 보지 못한 물자가 있으면 그 줄은 [확인: 실행](peek 의 칸만 봤다)으로 적고 이어 간다. 게임이 죽었거나 `값 쓰기 실패` 가 나왔어도 멈춘다.

- [ ] **Step 5: 결과를 PR 에 적고 머지한다**

스크래치에 `vc-stock.md` 를 쓴다(Write 도구): 단계마다 한 것 / 본 것 / 근거 화면의 이름, 5 의 표(칸 · ToyBox 의 이름 · 게임 화면에서 오른 물자), peek 의 값 그대로, 로그의 줄 그대로, 재고 칸의 표기와 게임 화면의 표기를 견준 것, 보지 못한 것. `gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/vc-stock.md"` 로 PR 에 단다.

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git push && gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && git switch develop && git pull --ff-only origin develop && git log --oneline -1
```

Expected: `322 passed`, 머지 커밋이 `develop` 의 머리다. 게임 폴더에는 이 브랜치의 빌드가 들어 있다(`uv run srkit deploy toybox` 의 미리보기가 0개 파일).

---

### Task 6: 설정 — 최소 유지의 켜짐과 값

**브랜치:** `feat/toybox-values-keep` (Task 5 의 PR 이 들어간 `develop` 에서 나눈다)

**Files:**
- Modify: `native/srtoybox/settings.h`, `native/srtoybox/settings.cpp`
- Test: `tests/test_toybox.py`

**Interfaces:**
- Consumes: 지금의 `Settings` · `parse_settings` · `format_settings`, `locate.h` 의 `STOCK_SLOTS`(12).
- Produces:
  - `Settings` 의 새 필드: `bool keep_treasury`, `long long keep_treasury_value`(백만 달러), `bool keep_stock[STOCK_SLOTS]`, `long long keep_stock_value[STOCK_SLOTS]`(수량). 기본은 모두 꺼짐 · 0.
  - `const long long KEEP_TREASURY_MAX = 1000000`, `KEEP_STOCK_MAX = 1000000000`.
  - 파일의 줄(설계서의 표 그대로): `keep.treasury=0|1`, `keep.treasury.value=0 … 1000000`, `keep.stock.<칸>=0|1`, `keep.stock.<칸>.value=0 … 1000000000`(`<칸>` = 0 … 11). `format_settings` 는 `money.amount` 다음에 스물여섯 줄을 늘 쓴다. 틀린 줄은 그 줄만 버린다.
  - 테스트의 `KEEP_DEFAULTS` · `DEFAULTS` · `kept(**줄)`(Task 8 의 테스트도 쓴다).

- [ ] **Step 0: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c feat/toybox-values-keep && uv run srkit toybox-build | tail -1 && uv run pytest -q 2>&1 | tail -2
```

Expected: `빌드 완료: …`, `322 passed`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_toybox.py` 에서 다음을 찾아:

```python
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\ntechnology=120\nspawnunit=2413\n"
```

이렇게 바꾼다:

```python
KEEP_DEFAULTS = "keep.treasury=0\nkeep.treasury.value=0\n" + "".join(f"keep.stock.{slot}=0\nkeep.stock.{slot}.value=0\n"
                                                                      for slot in range(12))
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\n" + KEEP_DEFAULTS + "technology=120\nspawnunit=2413\n"


def kept(**lines: int) -> str:
    """DEFAULTS 에서 유지의 줄 몇 개만 바꾼 것. 키의 점은 밑줄 둘로 적는다: kept(keep__stock__3=1)."""
    out = DEFAULTS
    for key, value in lines.items():
        key = key.replace("__", ".")
        assert f"{key}=0\n" in out, key
        out = out.replace(f"{key}=0\n", f"{key}={value}\n")
    return out
```

`tests/test_toybox.py` 에서 다음을 찾아:

```python
def test_settings_file_round_trip(dll, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    assert text(dll.srtoybox_settings_file) == DEFAULTS                                      # 파일이 없으면 기본값
    assert dll.srtoybox_settings_store(b"hotkey_vk=120\nhotkey_mods=4\ntechnology=140\n") == 1
    saved = DEFAULTS.replace("=84", "=120").replace("mods=3", "mods=4").replace("=120\nspawn", "=140\nspawn")
```

이렇게 바꾼다:

```python
def test_keep_settings(dll):
    """최소 유지: 켜짐과 값을 모두 저장한다. 틀린 줄은 그 줄만 버린다(다른 유지는 그대로다)."""
    norm = lambda ini: text(dll.srtoybox_settings_normalize, ini.encode("utf-8"))
    assert norm("keep.treasury=1\nkeep.treasury.value=50000\n") == kept(keep__treasury=1, keep__treasury__value=50000)
    assert norm("keep.stock.3=1\nkeep.stock.3.value=1000000\nkeep.stock.11.value=7\n") == \
        kept(keep__stock__3=1, keep__stock__3__value=1000000, keep__stock__11__value=7)
    assert norm("keep.treasury.value=1000000\nkeep.stock.0.value=1000000000\n") == \
        kept(keep__treasury__value=1000000, keep__stock__0__value=1000000000)                # 한도까지는 된다
    # 범위 밖의 값, 0 / 1 이 아닌 켜짐, 없는 칸, 깨진 키 — 모두 그 줄만 버린다
    assert norm("keep.treasury=2\nkeep.treasury.value=1000001\nkeep.treasury.value=-1\nkeep.stock.3=7\nkeep.stock.3.value=1000000001\n"
                "keep.stock.12=1\nkeep.stock.12.value=5\nkeep.stock.-1=1\nkeep.stock.=1\nkeep.stock.x=1\nkeep.stock.3.amount=5\n"
                "keep.stock.3x=1\nkeep.stock=1\nkeep.stock.123=1\nkeep.stock. 3=1\n") == DEFAULTS
    assert norm("keep.stock.5=1\nkeep.stock.5=x\nkeep.stock.6=1\n") == kept(keep__stock__5=1, keep__stock__6=1)
    assert len(kept(**{f"keep__stock__{slot}__value": 1000000000 for slot in range(12)}, keep__treasury__value=1000000)) < 1024   # 읽는 쪽은 4096 까지 읽는다


def test_settings_file_round_trip(dll, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    assert text(dll.srtoybox_settings_file) == DEFAULTS                                      # 파일이 없으면 기본값
    assert dll.srtoybox_settings_store(b"hotkey_vk=120\nhotkey_mods=4\ntechnology=140\nkeep.stock.7=1\nkeep.stock.7.value=250000\n") == 1
    saved = kept(keep__stock__7=1, keep__stock__7__value=250000).replace("=84", "=120").replace("mods=3", "mods=4") \
        .replace("=120\nspawn", "=140\nspawn")
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox.py -q -k settings 2>&1 | tail -8`

Expected: `3 failed, 63 deselected` — 세 테스트 모두 설정의 글이 다르다(유지의 스물여섯 줄이 없다).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/settings.cpp` 에서 다음 바로 앞에:

```cpp
std::wstring env(const wchar_t *name)
```

이것을 더한다:

```cpp
// "keep.stock.<칸>" 과 "keep.stock.<칸>.value" 의 줄. rest 는 "keep.stock." 뒤의 글이다. 칸이나 값이 틀리면 버린다.
void parse_keep_stock(const std::string &rest, long long n, Settings &s)
{
    const size_t dot = rest.find('.');
    const std::string digits = rest.substr(0, dot);
    if (digits.empty() || digits.size() > 2 || digits.find_first_not_of("0123456789") != std::string::npos)
        return;
    const int slot = atoi(digits.c_str());
    if (slot >= STOCK_SLOTS)
        return;
    if (dot == std::string::npos) {
        if (n == 0 || n == 1)
            s.keep_stock[slot] = n == 1;
    } else if (rest.compare(dot, std::string::npos, ".value") == 0 && n >= 0 && n <= KEEP_STOCK_MAX) {
        s.keep_stock_value[slot] = n;
    }
}

```

`native/srtoybox/settings.cpp` 에서 다음 바로 뒤에:

```cpp
                s.money_amount = n;
```

이것을 더한다:

```cpp
        } else if (key == "keep.treasury") {
            if (n == 0 || n == 1)
                s.keep_treasury = n == 1;
        } else if (key == "keep.treasury.value") {
            if (n >= 0 && n <= KEEP_TREASURY_MAX)
                s.keep_treasury_value = n;
        } else if (key.compare(0, 11, "keep.stock.") == 0) {
            parse_keep_stock(key.substr(11), n, s);
```

`native/srtoybox/settings.cpp` 에서 다음 바로 앞에:

```cpp
    for (int i = 0; i < FEATURE_COUNT; i++) {
```

이것을 더한다:

```cpp
    out += "keep.treasury=" + std::to_string(s.keep_treasury ? 1 : 0) + "\nkeep.treasury.value=" + std::to_string(s.keep_treasury_value)
        + "\n";
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        const std::string key = "keep.stock." + std::to_string(slot);
        out += key + "=" + std::to_string(s.keep_stock[slot] ? 1 : 0) + "\n" + key + ".value=" + std::to_string(s.keep_stock_value[slot])
            + "\n";
    }
```

`native/srtoybox/settings.cpp` 에서 다음을 찾아:

```cpp
            if (ReadFile(f, buf, sizeof(buf), &n, nullptr))   // 설정 파일은 100바이트 남짓이다. 4096 을 넘는 부분은 읽지 않는다
```

이렇게 바꾼다:

```cpp
            if (ReadFile(f, buf, sizeof(buf), &n, nullptr))   // 설정 파일은 1 KB 를 넘지 않는다. 4096 을 넘는 부분은 읽지 않는다
```

`native/srtoybox/settings.h` 에서 다음을 찾아:

```cpp
// 창에서 바꾸는 설정: 여닫는 단축키, 돈 탭의 입력란, 기능마다 마지막에 넣은 값.
```

이렇게 바꾼다:

```cpp
// 창에서 바꾸는 설정: 여닫는 단축키, 돈 탭의 입력란, 국고와 물자의 최소 유지, 기능마다 마지막에 넣은 값.
```

`native/srtoybox/settings.h` 에서 다음을 찾아:

```cpp
const int HOTKEY_CTRL = 1, HOTKEY_SHIFT = 2, HOTKEY_ALT = 4;
const long long MONEY_AMOUNT_MIN = 1, MONEY_AMOUNT_MAX = 1000000, MONEY_AMOUNT_DEFAULT = 10000;   // 돈 탭의 입력란(백만 달러)
```

이렇게 바꾼다:

```cpp
#include "locate.h"

const int HOTKEY_CTRL = 1, HOTKEY_SHIFT = 2, HOTKEY_ALT = 4;
const long long MONEY_AMOUNT_MIN = 1, MONEY_AMOUNT_MAX = 1000000, MONEY_AMOUNT_DEFAULT = 10000;   // 돈 탭의 입력란(백만 달러)
const long long KEEP_TREASURY_MAX = 1000000;       // 유지할 국고(백만 달러): 0 ~ 1,000,000
const long long KEEP_STOCK_MAX = 1000000000;       // 유지할 물자의 수량: 0 ~ 1,000,000,000
```

`native/srtoybox/settings.h` 에서 다음 바로 앞에:

```cpp
    std::map<std::string, long long> values;         // 값이 있는 기능의 id → 값
```

이것을 더한다:

```cpp
    bool keep_treasury = false;                      // 국고의 최소 유지. "keep.treasury"(0 / 1)
    long long keep_treasury_value = 0;               // 그 금액(백만 달러). "keep.treasury.value"
    bool keep_stock[STOCK_SLOTS] = {};               // 물자마다의 최소 유지. "keep.stock.<칸>"(0 / 1)
    long long keep_stock_value[STOCK_SLOTS] = {};    // 그 수량. "keep.stock.<칸>.value"
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox.py -q -k settings 2>&1 | tail -2`

Expected: `빌드 완료: …`, `3 passed, 63 deselected`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/settings.h native/srtoybox/settings.cpp tests/test_toybox.py && git commit -q -F - <<'EOF'
feat: ToyBox 설정 — 국고와 물자의 최소 유지(켜짐과 값)

keep.treasury · keep.treasury.value(백만 달러) · keep.stock.<칸> · keep.stock.<칸>.value. 틀린 줄은 그 줄만 버린다.
아직 아무도 읽지 않는다 — 유지 검사와 창은 다음 커밋들에서.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `323 passed`.

---

### Task 7: 대기열 — 최소 유지

**브랜치:** `feat/toybox-values-keep`

**Files:**
- Modify: `native/srtoybox/keeper.h`, `native/srtoybox/keeper.cpp`(둘 다 통째로), `native/srtoybox/input.cpp`, `native/srtoybox/exports.cpp`
- Test: `tests/test_toybox_values.py`

**Interfaces:**
- Consumes: Task 3 의 `keeper`(요청의 대기열, `ALL_STOCK`), 계획 (나)의 `Change::Floor` · `game_values()` · `game_write_treasury` · `game_write_stock` · `runner_calling()` · `runner_faulted()`, Task 1 의 `product_label` · `short_amount`.
- Produces:
  - `struct Keep { bool treasury; double treasury_floor; bool stock[STOCK_SLOTS]; double stock_floor[STOCK_SLOTS]; }` — 국고의 바닥은 **달러**, 물자는 수량.
  - `void keeper_set_keep(const Keep &keep)`(다음 틱에 바로 본다), `Keep keeper_keep()`, `int keep_count(const Keep &)`.
  - **`void keeper_tick(unsigned long long now_ms)`** — 시계를 받는다(지금까지는 인자가 없었다). 대기열을 비운 뒤, 켜진 유지가 있고 마지막으로 본 지 `KEEP_EVERY_MS`(500) 가 지났으면(또는 설정이 방금 바뀌었으면) 켜진 항목마다 바닥을 댄다. 게임 밖 · 멀티플레이 · 오류 가드 뒤 · 값 쓰기가 꺼진 뒤 · 게임의 함수 안에서 다시 온 틱에서는 쉰다.
  - 유지는 `keeper_last()` 와 `keeper_notice()` 를 바꾸지 않는다. 로그 `유지: 석유 2.5 K -> 5.0 K` 는 항목마다 이번 실행의 첫 번째만(그 항목의 설정이 바뀌면 다시 한 번).
  - `std::string keep_active_text(const Keep &, const bool *used)` → `" · 유지 중: 국고, 석유, 전력"`(넷을 넘으면 `" · 유지 중: 국고 외 5개"`, 없으면 빈 글), `std::string keep_resting_text(const Keep &, const char *why)` → `" · 유지 3개 켜짐(<까닭>)"`(없으면 빈 글).
  - 내보내기: `srtoybox_keeper_tick_at(ms)`, `srtoybox_keeper_keep(slot, on, floor)`(slot −1 = 국고), `srtoybox_keep_text(used, why, out, size)`. `srtoybox_keeper_tick()` 은 지금 시각(`GetTickCount64`)으로 부른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

시계는 테스트가 준다(`srtoybox_keeper_tick_at`) — 0.5초를 기다리지 않는다.

<!-- 고칠 곳: test -->
`tests/test_toybox_values.py` 에서 다음 바로 뒤에:

```python
    lib.srtoybox_keeper_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
```

이것을 더한다:

```python
    lib.srtoybox_keeper_tick_at.argtypes = [ctypes.c_ulonglong]
    lib.srtoybox_keeper_keep.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
    lib.srtoybox_keep_text.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
```

`tests/test_toybox_values.py` 에서 다음 바로 앞에:

```python
def test_nothing_is_asked_when_values_cannot_be_written(lib, game):
```

이것을 더한다:

```python
def keep(lib, slot: int, floor: float, on: bool = True) -> None:
    assert lib.srtoybox_keeper_keep(slot, int(on), floor) == 0


def kept_lines(tmp_path) -> list[str]:
    """로그의 "유지: …" 줄들(때를 뗀 것)."""
    log = tmp_path / "toybox.log"
    lines = [line.split(" ", 2)[2] for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    return [line for line in lines if line.startswith("유지: ")]


def test_keep_raises_what_falls_below_its_floor(lib, game, tmp_path):
    """최소 유지: 켠 다음 틱에 바로 올리고, 그 뒤로는 0.5초마다 본다. 바닥 위의 값은 건드리지 않는다. 창의 "마지막으로 쓴 값"은 그대로다."""
    keep(lib, TREASURY, 20e9)
    keep(lib, 3, 5000.0)
    keep(lib, 0, 500.0)                                        # 농산물은 1000 — 바닥 위다
    assert game.treasury(176) == 14.43e9                       # 켠 것만으로는 쓰지 않는다 — 창 스레드의 틱에서 쓴다
    lib.srtoybox_keeper_tick_at(100_000)
    assert game.treasury(176) == 20e9 and game.stock(176, 3) == 5000.0 and game.stock(176, 0) == 1000.0
    assert told(lib) == ("", "")
    game.set_treasury(176, 1e9)                                # 게임이 그 사이에 썼다
    game.set_stock(176, 3, 100.0)
    lib.srtoybox_keeper_tick_at(100_010)
    lib.srtoybox_keeper_tick_at(100_499)
    assert game.treasury(176) == 1e9 and game.stock(176, 3) == 100.0     # 아직 0.5초가 안 됐다
    lib.srtoybox_keeper_tick_at(100_500)
    assert game.treasury(176) == 20e9 and game.stock(176, 3) == 5000.0
    assert game.treasury(141) == 5e9 and game.peek(OPTIONS, "<I") == 0   # 다른 나라와 치트 허용 비트는 그대로다
    assert kept_lines(tmp_path) == ["유지: 국고 14.43 B -> 20.00 B", "유지: 석유 2.5 K -> 5.0 K"]   # 항목마다 첫 번째만 적는다


def test_keep_leaves_products_this_game_does_not_use(lib, game):
    keep(lib, 5, 1000.0)                                       # 이번 판에서 쓰지 않는 물자(금속 광석)
    keep(lib, 7, 1000.0)
    lib.srtoybox_keeper_tick_at(1000)
    assert game.stock(176, 5) == 0.0 and game.stock(176, 7) == 1000.0
    assert lib.srtoybox_keeper_keep(12, 1, 5.0) == -1 and lib.srtoybox_keeper_keep(-2, 1, 5.0) == -1     # 없는 칸


def test_keep_rests_outside_a_game_and_says_nothing(lib, game, tmp_path):
    """게임 밖 · 멀티플레이에서는 쉰다(알림도 없다 — 0.5초마다 온다). 돌아오면 다시 한다."""
    keep(lib, TREASURY, 20e9)
    game.menu()
    lib.srtoybox_keeper_tick_at(1000)
    game.play(176)
    game.poke(MULTIPLAYER, "<B", 1)
    lib.srtoybox_keeper_tick_at(1500)
    assert game.treasury(176) == 14.43e9 and told(lib) == ("", "") and kept_lines(tmp_path) == []
    game.poke(MULTIPLAYER, "<B", 0)
    lib.srtoybox_keeper_tick_at(1600)                          # 쉰 것도 본 것이다 — 다음은 0.5초 뒤
    assert game.treasury(176) == 14.43e9
    lib.srtoybox_keeper_tick_at(2000)
    assert game.treasury(176) == 20e9


def test_keep_follows_the_country_being_played(lib, game):
    """플레이하는 나라가 바뀌면 그 뒤로는 새 나라의 값을 본다. 앞의 나라는 건드리지 않는다."""
    keep(lib, TREASURY, 20e9)
    lib.srtoybox_keeper_tick_at(1000)
    assert game.treasury(176) == 20e9 and game.treasury(141) == 5e9
    game.set_treasury(176, 1e9)
    game.play(141)                                             # 폴란드로 바꿨다(이 나라로 플레이)
    lib.srtoybox_keeper_tick_at(1500)
    assert game.treasury(141) == 20e9 and game.treasury(176) == 1e9


def test_a_button_and_keep_work_on_the_same_tick(lib, game):
    """단추의 요청을 먼저 쓰고, 때가 됐으면 이어서 유지를 본다 — 방금 내린 값이 바닥 아래면 올린다."""
    keep(lib, TREASURY, 5e9)
    lib.srtoybox_keeper_tick_at(1000)                          # 14.43 B 는 바닥 위다
    assert ask(lib, TREASURY, SET, 0.0)
    lib.srtoybox_keeper_tick_at(1100)
    assert game.treasury(176) == 0.0 and told(lib) == ("국고 14.43 B -> 0", "")   # 아직 때가 아니다
    lib.srtoybox_keeper_tick_at(1500)
    assert game.treasury(176) == 5e9 and told(lib) == ("국고 14.43 B -> 0", "")   # 유지는 "마지막으로 쓴 값"을 덮지 않는다
    assert ask(lib, TREASURY, SET, 1.0)
    lib.srtoybox_keeper_tick_at(2000)                          # 요청과 유지가 같은 틱에
    assert game.treasury(176) == 5e9 and told(lib) == ("국고 5.00 B -> 1", "")


def test_keep_leaves_a_value_that_is_not_a_number(lib, game):
    keep(lib, TREASURY, 5e9)
    game.set_treasury(176, float("nan"))
    lib.srtoybox_keeper_tick_at(1000)
    assert game.treasury(176) != game.treasury(176) and told(lib) == ("", "")      # 아직 NaN 이고, 알리지도 않는다


def test_keep_stops_when_a_write_fails(lib, game, tmp_path):
    game.lock(176)
    game.play(176)
    keep(lib, TREASURY, 20e9)
    keep(lib, 3, 5000.0)
    lib.srtoybox_keeper_tick_at(1000)
    lib.srtoybox_keeper_tick_at(2000)
    assert game.treasury(176) == 14.43e9 and game.stock(176, 3) == 2500.0
    assert text(lib.srtoybox_values_off) == FAILED_OFF
    log = (tmp_path / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패") == 1 and "값 쓰기 실패 (국고) — 값 쓰기를 끕니다" in log     # 한 번 실패하면 더 시도하지 않는다


def test_keep_logs_the_first_raise_again_after_its_setting_changes(lib, game, tmp_path):
    keep(lib, 3, 5000.0)
    lib.srtoybox_keeper_tick_at(1000)
    game.set_stock(176, 3, 0.0)
    lib.srtoybox_keeper_tick_at(1500)
    assert kept_lines(tmp_path) == ["유지: 석유 2.5 K -> 5.0 K"]
    keep(lib, 3, 9000.0)                                       # 바닥을 고쳤다
    lib.srtoybox_keeper_tick_at(1501)                          # 고친 다음 틱에 바로 본다
    assert game.stock(176, 3) == 9000.0
    assert kept_lines(tmp_path) == ["유지: 석유 2.5 K -> 5.0 K", "유지: 석유 5.0 K -> 9.0 K"]
    keep(lib, 3, 9000.0, on=False)
    game.set_stock(176, 3, 0.0)
    lib.srtoybox_keeper_tick_at(5000)
    assert game.stock(176, 3) == 0.0                           # 껐다


def test_the_status_line_says_what_is_being_kept(lib, game):
    """상태 줄의 뒤에 붙는 글. 게임 안에서는 지금 유지되는 것의 이름(넷을 넘으면 첫 이름과 나머지의 수), 쉬는 동안에는 켜진 수와 까닭."""
    active = lambda used: text(lib.srtoybox_keep_text, used.encode(), None)
    resting = lambda why: text(lib.srtoybox_keep_text, None, why.encode("utf-8"))
    assert active("1" * 12) == "" and resting("게임에 들어가면 적용") == ""          # 켠 것이 없다
    keep(lib, 3, 1.0)
    keep(lib, 7, 1.0)
    assert active("1" * 12) == " · 유지 중: 석유, 전력"
    assert active("000100000000") == " · 유지 중: 석유"                              # 이번 판에서 쓰지 않는 물자는 유지되지 않는다
    assert active("0" * 12) == ""
    assert resting("게임에 들어가면 적용") == " · 유지 2개 켜짐(게임에 들어가면 적용)"
    keep(lib, TREASURY, 1.0)
    keep(lib, 0, 1.0)
    assert active("1" * 12) == " · 유지 중: 국고, 농산물, 석유, 전력"                 # 국고가 먼저, 물자는 칸의 순서로
    keep(lib, 11, 1.0)
    keep(lib, 10, 1.0)
    assert active("1" * 12) == " · 유지 중: 국고 외 5개"                             # 넷을 넘으면
    assert active("000100000001") == " · 유지 중: 국고, 석유, 물자 #11"
    assert resting("멀티플레이에서는 쉽니다") == " · 유지 6개 켜짐(멀티플레이에서는 쉽니다)"


```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -6`

Expected: `48 errors` — `tests/test_toybox_values.py` 전부가 고정물에서 오류다(`function 'srtoybox_keeper_tick_at' not found`).

- [ ] **Step 3: 구현한다**

`keeper.h` · `keeper.cpp` 는 통째로 바꾼다(요청 하나의 셈과 쓰기를 `decide` · `write_slot` 으로 떼어 단추의 요청과 유지가 함께 쓴다). `input.cpp` 는 타이머에서 시계를 넘긴다.

<!-- 고칠 곳: code -->
`native/srtoybox/exports.cpp` 에서 다음을 찾아:

```cpp
    keeper_tick();
```

이렇게 바꾼다:

```cpp
    keeper_tick(GetTickCount64());
}

// 테스트: 가짜 시계로 틱(최소 유지는 KEEP_EVERY_MS 마다 본다).
EXPORT void srtoybox_keeper_tick_at(unsigned long long now_ms)
{
    keeper_tick(now_ms);
}

// 테스트: 최소 유지의 한 항목을 켜고 끈다. slot 이 -1 이면 국고(floor 는 달러), 0 … 11 이면 그 칸의 물자(수량). 없는 칸이면 -1.
EXPORT int srtoybox_keeper_keep(int slot, int on, double floor)
{
    Keep keep = keeper_keep();
    if (slot == TREASURY) {
        keep.treasury = on != 0;
        keep.treasury_floor = floor;
    } else if (slot >= 0 && slot < STOCK_SLOTS) {
        keep.stock[slot] = on != 0;
        keep.stock_floor[slot] = floor;
    } else {
        return -1;
    }
    keeper_set_keep(keep);
    return 0;
}

// 테스트: 상태 줄에 붙는 글. used 가 '0' · '1' 열두 글자면 게임 안의 글(그 물자들을 쓰는 판), nullptr 이면 쉬는 동안의 글(까닭 why).
EXPORT int srtoybox_keep_text(const char *used, const char *why, char *out, int size)
{
    const Keep keep = keeper_keep();
    if (used == nullptr)
        return put(keep_resting_text(keep, why == nullptr ? "" : why), out, size);
    bool flags[STOCK_SLOTS] = {};
    for (int slot = 0; slot < STOCK_SLOTS && used[slot] != '\0'; slot++)
        flags[slot] = used[slot] == '1';
    return put(keep_active_text(keep, flags), out, size);
```

`native/srtoybox/input.cpp` 에서 다음을 찾아:

```cpp
        keeper_tick();                                       // 값 쓰기 요청(돈 탭). 게임의 함수 안에서 다시 온 틱이면 스스로 쉰다
```

이렇게 바꾼다:

```cpp
        keeper_tick(GetTickCount64());                       // 값 쓰기 요청과 최소 유지. 게임의 함수 안에서 다시 온 틱이면 스스로 쉰다
```

`native/srtoybox/keeper.cpp` 를 통째로 다음으로 바꾼다:

```cpp
#include "keeper.h"

#include <cstring>
#include <deque>
#include <mutex>

#include "game.h"
#include "log.h"
#include "products.h"
#include "runner_win.h"

namespace {

const size_t MAX_QUEUE = 32;
const char *const LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다.";

std::mutex g_lock;          // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
std::deque<Request> g_queue;
std::string g_last, g_notice;
Keep g_keep;                        // 최소 유지의 설정(창이 넘긴 것)
bool g_keep_due;                    // 설정이 바뀌었다 — 0.5초를 기다리지 않고 다음 틱에 본다
unsigned long long g_keep_at;       // 마지막으로 유지를 본 때
bool g_kept[1 + STOCK_SLOTS];       // 그 항목을 올린 것을 이번 실행의 로그에 적었다([0] 국고, [1 + 칸] 물자)

std::string target_name(int slot)
{
    return slot == TREASURY ? std::string("국고") : product_label(slot);
}

// 국고는 재무 패널의 표기로, 물자는 위쪽 자원 표시줄의 표기로 적는다.
std::string shown(int slot, double value)
{
    return slot == TREASURY ? short_number(value) : short_amount(value);
}

// 한 칸(국고나 물자 하나)에 대한 셈: 지금 값(*from)과 쓸 값(*to).
Verdict decide(int slot, Change change, double amount, const GameValues &now, double *from, double *to)
{
    if (slot == TREASURY) {
        *from = now.treasury;
        return treasury_value(now.treasury, change, amount, to);
    }
    float next = 0;
    *from = now.stock[slot];
    const Verdict verdict = stock_value(now.stock[slot], change, amount, &next);
    *to = next;
    return verdict;
}

Wrote write_slot(int slot, double value)
{
    return slot == TREASURY ? game_write_treasury(value) : game_write_stock(slot, static_cast<float>(value));
}

// 요청 하나(국고나 물자 한 칸)를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다.
// 썼으면 *wrote_it 이 true. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now, bool *wrote_it)
{
    *wrote_it = false;
    if (r.slot != TREASURY && (r.slot < 0 || r.slot >= STOCK_SLOTS || !now.used[r.slot])) {
        g_notice = "이번 판에서 쓰지 않는 물자입니다.";
        return true;
    }
    double from = 0, to = 0;
    const Verdict verdict = decide(r.slot, r.change, r.amount, now, &from, &to);
    if (verdict == Verdict::Refuse)
        g_notice = "지금 값이 수가 아니어서 쓰지 않았습니다.";
    if (verdict != Verdict::Write)
        return true;
    const Wrote wrote = write_slot(r.slot, to);
    if (wrote == Wrote::Done) {
        *wrote_it = true;
        g_last = target_name(r.slot) + " " + shown(r.slot, from) + " -> " + shown(r.slot, to);
        log_line("값 쓰기: %s", g_last.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 탭이 보인다(game_values_off)
    g_notice = LEFT_GAME;                      // 읽은 뒤 쓰기 전에 게임이 바뀌었다
    return true;
}

// "모든 물자": 이번 판에서 쓰는 물자마다 같은 일을 한다. 한 칸에 쓰는 것은 다른 칸의 값을 바꾸지 않으므로 now 를 다시 읽지 않는다.
bool apply_all(const Request &r, const GameValues &now)
{
    int count = 0;
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        if (!now.used[slot])
            continue;
        bool wrote_it = false;
        if (!apply({slot, r.change, r.amount}, now, &wrote_it))
            return false;
        count += wrote_it ? 1 : 0;
    }
    if (count > 0)
        g_last = "모든 물자 " + std::to_string(count) + "개";
    return true;
}

// 대기열을 비운다. 값 쓰기가 꺼졌거나 값을 읽지 못하면 false(남은 요청은 버렸다). g_lock 을 쥔 채로 부른다.
bool drain()
{
    g_notice.clear();
    while (!g_queue.empty()) {
        const Request r = g_queue.front();
        g_queue.pop_front();
        const GameValues now = game_values();  // 요청마다 다시 읽는다 — 앞의 요청이 값을 바꿨다
        if (!now.ok) {
            g_queue.clear();
            g_notice = "게임의 값을 읽을 수 없어 쓰지 않았습니다.";
            return false;
        }
        bool wrote_it = false;
        if (!(r.slot == ALL_STOCK ? apply_all(r, now) : apply(r, now, &wrote_it))) {
            g_queue.clear();
            return false;
        }
    }
    return true;
}

// 유지의 한 항목: 지금 값이 바닥보다 작으면 바닥으로 올린다. 값 쓰기가 꺼졌으면(실패) false.
// 창에 알리지 않는다(0.5초마다 온다). 로그에는 항목마다 이번 실행의 첫 번째만 적는다.
bool hold(int slot, double floor, const GameValues &now)
{
    double from = 0, to = 0;
    if (decide(slot, Change::Floor, floor, now, &from, &to) != Verdict::Write)
        return true;                           // 바닥 위다. 지금 값이 수가 아니면 건드리지 않는다
    const Wrote wrote = write_slot(slot, to);
    if (wrote == Wrote::Done && !g_kept[1 + slot]) {
        g_kept[1 + slot] = true;
        log_line("유지: %s %s -> %s", target_name(slot).c_str(), shown(slot, from).c_str(), shown(slot, to).c_str());
    }
    return wrote != Wrote::Failed && wrote != Wrote::Off;
}

// 유지 검사: 켜진 항목마다 바닥을 댄다. 물자는 이번 판에서 쓰는 것만. g_lock 을 쥔 채로 부른다.
void keep_check()
{
    const GameValues now = game_values();
    if (!now.ok)
        return;
    if (g_keep.treasury && !hold(TREASURY, g_keep.treasury_floor, now))
        return;
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (g_keep.stock[slot] && now.used[slot] && !hold(slot, g_keep.stock_floor[slot], now))
            return;
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
    if (runner_faulted() || !game_values_off().empty()) {
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
    if (due)
        keep_check();                          // 단추의 요청을 쓴 뒤에 본다 — 방금 내린 값도 바닥 아래면 올린다
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

void keeper_set_keep(const Keep &keep)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (keep.treasury != g_keep.treasury || keep.treasury_floor != g_keep.treasury_floor)
        g_kept[0] = false;                     // 바뀐 항목은 다음에 올릴 때 다시 로그에 적는다
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (keep.stock[slot] != g_keep.stock[slot] || keep.stock_floor[slot] != g_keep.stock_floor[slot])
            g_kept[1 + slot] = false;
    g_keep = keep;
    g_keep_due = true;
}

Keep keeper_keep()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_keep;
}

int keep_count(const Keep &keep)
{
    int count = keep.treasury ? 1 : 0;
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        count += keep.stock[slot] ? 1 : 0;
    return count;
}

std::string keep_active_text(const Keep &keep, const bool *used)
{
    std::string first, names;
    int count = 0;
    for (int slot = TREASURY; slot < STOCK_SLOTS; slot++) {
        if (slot == TREASURY ? !keep.treasury : !(keep.stock[slot] && used[slot]))
            continue;
        const std::string name = target_name(slot);
        if (count++ == 0)
            first = name;
        else
            names += ", ";
        names += name;
    }
    if (count == 0)
        return std::string();
    return " · 유지 중: " + (count > 4 ? first + " 외 " + std::to_string(count - 1) + "개" : names);
}

std::string keep_resting_text(const Keep &keep, const char *why)
{
    const int count = keep_count(keep);
    return count == 0 ? std::string() : " · 유지 " + std::to_string(count) + "개 켜짐(" + why + ")";
}

void keeper_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_queue.clear();
    g_last.clear();
    g_notice.clear();
    g_keep = Keep();
    g_keep_due = false;
    g_keep_at = 0;
    memset(g_kept, 0, sizeof(g_kept));
}
```

`native/srtoybox/keeper.h` 를 통째로 다음으로 바꾼다:

```cpp
// 값 쓰기 요청의 대기열과 최소 유지. 창의 단추(그리는 스레드)가 넣고, 게임 창의 타이머(창 스레드)가 비운다.
// 내장 치트를 거치지 않는다 — 지금 값을 읽고(game.h) 쓸 값을 셈해(values.h) 그 칸에 쓴다.
#pragma once

#include <string>

#include "locate.h"
#include "values.h"

const int TREASURY = -1;                       // Request.slot: 국고. 0 … STOCK_SLOTS - 1 은 그 칸의 물자 재고
const int ALL_STOCK = -2;                      // Request.slot: 이번 판에서 쓰는 물자 모두 — 쓸 때 칸마다의 요청으로 풀린다

struct Request {
    int slot;
    Change change;
    double amount;                             // 국고는 달러, 재고는 수량
};

// 최소 유지: 켜진 항목이 바닥보다 작아지면 바닥으로 올린다. KEEP_EVERY_MS 마다 보고, 설정 창이 닫혀 있어도 돈다.
// 플레이하는 나라가 바뀌면 그 뒤로는 새 나라의 값을 본다. 물자는 이번 판에서 쓰는 것만 올린다.
struct Keep {
    bool treasury = false;
    double treasury_floor = 0;                 // 달러
    bool stock[STOCK_SLOTS] = {};
    double stock_floor[STOCK_SLOTS] = {};      // 수량
};

const unsigned long long KEEP_EVERY_MS = 500;

bool keeper_enqueue(const Request &request);   // 받지 못하면 false: 가득 찼다(32개), 값 쓰기가 꺼져 있다
// 대기열을 비우고, 때가 됐으면 유지를 본다. 게임 창을 가진 스레드에서 부른다(now_ms: 흐르는 시계, 밀리초).
// 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고 유지는 쉰다.
// 게임의 명령 처리 함수(옮기지 않은 기능의 직접 실행) 안에서 다시 온 틱이면 아무것도 하지 않는다.
void keeper_tick(unsigned long long now_ms);
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개". 없으면 빈 글
std::string keeper_notice();                   // 쓰지 못한 까닭(창에 보인다). 없으면 빈 글

void keeper_set_keep(const Keep &keep);        // 창이 설정을 읽었거나 고쳤다. 다음 틱에 바로 본다
Keep keeper_keep();
int keep_count(const Keep &keep);              // 켜진 항목의 수
// 상태 줄의 뒤에 붙는 글. used: 이번 판에서 쓰는 물자(STOCK_SLOTS 칸).
// " · 유지 중: 국고, 석유, 전력" — 넷을 넘으면 " · 유지 중: 국고 외 5개". 지금 유지되는 것이 없으면 빈 글.
std::string keep_active_text(const Keep &keep, const bool *used);
// 쉬는 동안의 글: " · 유지 3개 켜짐(<까닭>)". 켜진 것이 없으면 빈 글.
std::string keep_resting_text(const Keep &keep, const char *why);

void keeper_reset_for_test();
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox_values.py -q 2>&1 | tail -2`

Expected: `빌드 완료: …`, `48 passed`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/keeper.h native/srtoybox/keeper.cpp native/srtoybox/input.cpp native/srtoybox/exports.cpp tests/test_toybox_values.py && git commit -q -F - <<'EOF'
feat: ToyBox 최소 유지 — 국고와 물자가 정해 둔 값보다 적어지면 올린다(0.5초마다)

- keeper: 켜진 항목마다 바닥 요청(Change::Floor). 게임 창의 타이머에서 돈다 — 설정 창이 닫혀 있어도.
  게임 밖 · 멀티플레이 · 오류 가드 뒤 · 값 쓰기가 꺼진 뒤에는 쉰다. 플레이하는 나라가 바뀌면 새 나라의 값만 본다.
  이번 판에서 쓰지 않는 물자는 올리지 않는다. 쓰기가 실패하면 그 뒤로 시도하지 않는다.
- 유지는 창의 "마지막으로 쓴 값"과 알림을 건드리지 않는다. 로그에는 항목마다 처음 올린 것만 적는다.
- 상태 줄에 붙일 글(keep_active_text · keep_resting_text).
- 아직 창이 유지를 켜지 않는다 — 다음 커밋에서.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `332 passed`.

---

### Task 8: 창 — 최소 유지의 칸과 상태 줄

**브랜치:** `feat/toybox-values-keep`

**Files:**
- Modify: `native/srtoybox/ui.cpp`, `native/srtoybox/input.cpp`
- Test: `tests/test_toybox.py`, `tests/toybox_overlay_probe.py`

**Interfaces:**
- Consumes: Task 6 의 `Settings::keep_*` · `KEEP_TREASURY_MAX` · `KEEP_STOCK_MAX` · 테스트의 `kept()`, Task 7 의 `Keep` · `keeper_set_keep` · `keep_count` · `keep_active_text` · `keep_resting_text`, Task 4 의 `money_tab` · `stock_row` · `stock_tab`.
- Produces:
  - 돈 탭의 새 줄: `[x] 최소 유지  [ 수량 ] 백만 달러`(창이 그린 것의 목록에 `money:keep` — 글 `"0"` / `"1"`, `money:keepvalue` — 글이 그 수).
  - 물자 탭의 넷째 칸 "최소 유지": 줄마다 `stock:<칸>:keep` · `stock:<칸>:keepvalue`("모든 물자" 줄에는 없다). 유지가 켜진 물자는 쓰지 않는 판에서도 줄이 나온다(재고 칸 `쓰지 않음`, 단추 꺼짐).
  - 유지의 칸은 단추가 꺼져 있을 때(게임 밖 · 멀티플레이)도 고칠 수 있다. 고치면 설정 파일에 적고 `keeper_set_keep` 으로 넘긴다. 수량은 입력을 마쳤을 때 넘어간다.
  - ToyBox 가 뜰 때(`ui_init`) 저장된 유지를 `keeper` 에 넘긴다 — 창을 한 번도 열지 않아도 돈다.
  - 상태 줄(`status`)의 뒤: 게임 안 `· 유지 중: 국고, 석유` / 쉬는 동안 `· 유지 2개 켜짐(게임에 들어가면 적용)` — 까닭은 "설계서와 달라진 곳"의 다섯.
  - 로그: `유지 켬: 석유 5000000` · `유지 켬: 국고 20000 (백만 달러)` · `유지 끔: 석유`.
  - 게임 창에 끼어들 때 `WM_NULL` 을 한 번 부친다(타이머가 입력 없이도 걸린다).
  - 검사 도구의 mode: `keep` · `keep_menu` · `keep_type` · `keep_reenter`. `money` · `stock` mode 의 단추 목록(`buttons`)은 유지의 칸을 세지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

<!-- 고칠 곳: test -->
`tests/test_toybox.py` 에서 다음 바로 앞에:

```python
def test_prologue_length_knows_only_plain_function_heads(dll):
```

이것을 더한다:

```python
KEEP_NOTE = "최소 유지를 켜 두면"


def test_keep_works_with_the_window_closed_and_shows_in_the_status_line(dll, cfg, tmp_path):
    """최소 유지: 저장해 둔 설정이 게임에 들어가자마자, 설정 창을 한 번도 열지 않아도 적용된다. 상태 줄에 무엇이 유지되는지 늘 보이고,
    창에서 켜고 끄면 바로 따른다. 내장 치트는 거치지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "keep"))
    assert got["closed"] == [14.43e9, 5e6, 0.0]                 # 창을 열기 전: 석유만 250만 → 500만(국고의 유지는 꺼져 있다)
    assert got["status"] == "플레이 중: 독일 (1499) · 유지 중: 석유"
    assert got["money"] == ["0", "20000"]                        # 돈 탭의 체크와 입력란(저장해 둔 값)
    assert got["on"] == 20e9 and got["status_on"] == "플레이 중: 독일 (1499) · 유지 중: 국고, 석유"
    assert got["back"] == 20e9                                   # -$10 B 로 내려도 0.5초 안에 돌아온다
    assert got["off"] == 10e9 and got["status_off"] == "플레이 중: 독일 (1499) · 유지 중: 석유"   # 끄면 내린 채로 있다
    # 물자 탭: 유지가 켜진 물자는 이번 판에서 쓰지 않아도 줄이 남는다(끌 수 있게). 단추는 꺼져 있고, 유지되지도 않는다
    assert got["rows"] == [["stock:all", "모든 물자", "-"], ["stock:0", "농산물", "1.0 K"], ["stock:3", "석유", "5.0 M"],
                           ["stock:4", "석탄", "쓰지 않음"], ["stock:7", "전력", "0"]]
    assert got["keeps"] == {"stock:0": ["0", "0"], "stock:3": ["1", "5000000"], "stock:4": ["1", "100"], "stock:7": ["0", "0"]}
    assert got["unused_press"] == 0.0                            # 쓰지 않는 물자의 단추는 꺼져 있다
    assert got["stock_off"] == [0.0, 0.0]                        # 석유의 유지를 끄고 0 으로 만들면 0 인 채로 있다
    assert got["status_end"] == "플레이 중: 독일 (1499)" and got["rows_end"] == ["stock:all", "stock:0", "stock:3", "stock:7"]
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0
    saved = (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")
    assert saved == kept(keep__treasury__value=20000, keep__stock__3__value=5000000, keep__stock__4__value=100)   # 모두 꺼진 채로 저장됐다
    log = [line.split(" ", 2)[2] for line in (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8").splitlines()]
    assert [line for line in log if line.startswith("유지")] == [
        "유지 켬: 석유 5000000", "유지 켬: 석탄 100", "유지: 석유 2.5 M -> 5.0 M", "유지 켬: 국고 20000 (백만 달러)",
        "유지: 국고 14.43 B -> 20.00 B", "유지 끔: 국고", "유지 끔: 석탄", "유지 끔: 석유"]
    assert [line for line in log if line.startswith("값 쓰기")] == ["값 쓰기: 국고 20.00 B -> 10.00 B", "값 쓰기: 국고 20.00 B -> 10.00 B",
                                                                  "값 쓰기: 석유 5.0 M -> 0"]
    assert "직접 실행" not in " ".join(log)


def test_keep_rests_in_the_menu_and_can_be_turned_off_there(dll, cfg, tmp_path):
    """게임 밖에서는 쉬지만 상태 줄에 켜진 수가 보이고, 단추가 꺼진 탭에서도 유지는 끌 수 있다(켜 둔 것을 잊고 새 판을 시작하지 않게)."""
    got = json.loads(_probe(cfg, tmp_path, "keep_menu"))
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다 · 유지 2개 켜짐(게임에 들어가면 적용)"
    assert got["rested"] == [14.43e9, 2.5e6] and got["keeps"]["stock:3"] == ["1", "5000000"]
    assert got["status_off"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다 · 유지 1개 켜짐(게임에 들어가면 적용)"
    assert got["entered"] == [14.43e9, 2.5e6, 100.0]            # 게임에 들어가면 남은 유지(석탄 100)만 적용된다 — 석탄을 쓰는 판이다
    assert "keep.stock.3=0\n" in (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")


def test_keep_does_not_write_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안에는, 유지를 볼 때가 됐어도 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "keep_reenter"))
    assert got["before"] == 20e9                                 # 유지가 돌고 있다
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [1e9]                                # 그 함수 안에서 다시 온 타이머는 바닥 아래가 된 국고를 올리지 않았다
    assert got["after"] == 20e9                                  # 함수가 끝난 뒤에 올린다


def test_a_typed_keep_amount_takes_effect_when_the_typing_is_done(dll, cfg, tmp_path):
    """수량을 치는 동안의 값(7, 70, 700 …)은 쓰이지 않는다. Enter 를 누르거나 다른 곳을 누르면 쓰이고, 치던 채로 창을 닫으면 버려진다."""
    got = json.loads(_probe(cfg, tmp_path, "keep_type"))
    assert got["typing"] == [5e6, "5000000"]                     # 다 쳤지만 아직 입력란 안이다 — 유지는 앞의 수량(500만) 그대로다
    assert got["entered"] == [7e6, "7000000"]                    # Enter
    assert got["clicked_away"] == [9e6, "9000000"]               # 다시 치고 다른 곳을 눌렀다
    assert got["closed"] == [9e6, "9000000"]                     # 또 치다가 창을 닫았다 — 친 것은 버려진다
    assert got["text"] == ""                                     # 친 글자는 게임에 가지 않았다
    assert "keep.stock.3.value=9000000\n" in (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("유지 켬: 석유") == 3                        # 뜰 때의 500만, 고친 700만 · 900만


```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
설정 창에 보이는 글 (출력은 JSON 한 줄. 보이지 않는 글은 "-"):
```

이것을 더한다:

```python
최소 유지 — 국고와 물자가 정해 둔 값보다 적어지면 올린다 (출력은 JSON 한 줄):
    keep             석유(500만)와 석탄(이번 판에서 쓰지 않는다)의 유지를 켜 둔 설정으로 게임에 들어간다. 창을 열어 국고의 유지를 켜고 끈다
    keep_menu        같은 설정으로 메뉴에 있다 — 쉬고, 상태 줄에 켜진 수가 보이고, 거기서 끌 수 있다
    keep_type        석유의 유지를 켠 채 수량을 새로 친다 — 입력을 마쳐야(Enter, 다른 곳을 누름) 쓰인다. 치던 채로 창을 닫으면 버려진다
    keep_reenter     국고의 유지를 켠 채, 옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 온다 — 그 안에서는 올리지 않는다
```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
                            if name.startswith("money:") and name not in ("money:now", "money:off", "money:amount"))
```

이렇게 바꾼다:

```python
                            if name.startswith("money:") and name not in ("money:now", "money:off", "money:amount", "money:keep",
                                                                           "money:keepvalue"))     # 단추만 — 최소 유지의 칸은 따로 본다
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
def run_stock(hook: str, mode: str) -> int:
```

이것을 더한다:

```python
def stock_rows(facts: dict) -> list[str]:
    """물자 탭에 그려진 줄들의 이름("stock:all", "stock:3" …), 그린 순서대로."""
    return [name for name in facts if name.startswith("stock:") and name.count(":") == 1 and name != "stock:off"]


def type_into(game: Game, name: str, digits: str) -> None:
    """그 입력란을 누르고(지금 값이 통째로 골라진다) 숫자를 친다. Enter 는 누르지 않는다."""
    game.click(name)
    game.present(3)
    for char in digits:
        user32.SendMessageW(game.hwnd, WM_CHAR, ord(char), 1)
        game.present()
    game.present(3)


def run_keep(hook: str, mode: str) -> int:
    """최소 유지. 출력은 JSON 한 줄(보이지 않는 글은 "-").

    설정(ToyBox 가 뜰 때 읽는다): 국고의 유지는 꺼져 있고 값이 20000(백만 달러), 석유(3)는 켜져 있고 500만, 석탄(4)은 켜져 있고 100.
    독일은 물자 0(농산물 1000) · 3(석유 250만) · 7(전력 0)을 쓴다 — 석탄은 keep_menu 에서만 쓰는 판이다.
    기다리는 시간(0.8초)은 유지를 보는 간격(0.5초)보다 넉넉히 길다.
    """
    home = os.environ.get("SRTOYBOX_HOME")
    if home:
        ini = "keep.treasury.value=20000\nkeep.stock.3=1\nkeep.stock.3.value=5000000\n"
        ini += {"keep_type": "", "keep_reenter": "keep.treasury=1\n"}.get(mode, "keep.stock.4=1\nkeep.stock.4.value=100\n")
        Path(home, "toybox.ini").write_text(ini, encoding="utf-8")
    game = start_game(hook)
    if game is None:
        return 0
    lines: list[str] = []
    inside: list[float] = []

    def body(_context, line):                                 # keep_reenter 에서만 불린다(옮기지 않은 기능의 직접 실행)
        lines.append(line.decode())
        if line == b"cheat allowcheats":
            fake.poke(OPTIONS, "<I", fake.peek(OPTIONS, "<I") | 0x40)
            return
        fake.set_treasury(176, 1e9)                           # 게임의 함수가 국고를 고치는 중이다(바닥 아래로)
        time.sleep(0.6)                                       # 유지를 볼 때가 지났다
        user32.SendMessageW(game.hwnd, WM_TIMER, TIMER_ID, 0)  # 그 안에서 ToyBox 의 타이머가 다시 온다
        inside.append(fake.treasury(176))

    game.handler = HANDLER(body)                              # 게임이 살아 있는 동안 붙들어 둔다
    fake = fake_game(hook, ctypes.cast(game.handler, ctypes.c_void_p).value)
    for slot, amount in ((0, 1000.0), (3, 2.5e6), (7, 0.0)):
        fake.use(slot)
        fake.set_stock(176, slot, amount)
    out: dict[str, object] = {}
    seen = lambda: [fake.treasury(176), fake.stock(176, 3), fake.stock(176, 4)]
    keeps = lambda facts: {name: [facts[name + ":keep"][3], facts[name + ":keepvalue"][3]] for name in stock_rows(facts)
                           if name != "stock:all"}
    if mode == "keep":
        fake.play(176)
        game.wait(0.8)                                        # 창은 닫혀 있다. 유지는 타이머에서 돈다
        out["closed"] = seen()
        game.hotkey()                                         # 창이 열리면 첫 탭이 "돈"이다
        game.got.clear()
        out["status"] = game.shown("status")
        out["money"] = [game.shown("money:keep"), game.shown("money:keepvalue")]
        game.click("money:keep")                              # 국고의 유지를 켠다
        game.wait(0.8)
        out["on"], out["status_on"] = fake.treasury(176), game.shown("status")
        game.click("money:-10b")                              # 바닥 아래로 내린다 — 다음 검사에서 돌아온다
        game.wait(0.8)
        out["back"] = fake.treasury(176)
        game.click("money:keep")                              # 끈다
        game.click("money:-10b")
        game.wait(0.8)
        out["off"], out["status_off"] = fake.treasury(176), game.shown("status")
        game.click(STOCK)
        facts = game.facts()
        out["rows"] = [[name, facts[name][3], facts[name + ":now"][3]] for name in stock_rows(facts)]
        out["keeps"] = keeps(facts)
        game.click("stock:4:+1m")                             # 쓰지 않는 물자의 단추 — 꺼져 있다
        game.wait(0.2)
        out["unused_press"] = fake.stock(176, 4)
        game.click("stock:4:keep")                            # 석탄의 유지를 끈다 — 줄이 없어진다
        game.click("stock:3:keep")                            # 석유의 유지를 끈다
        game.click("stock:3:zero")
        game.wait(0.8)
        out["stock_off"] = [fake.stock(176, 3), fake.stock(176, 4)]
        out["status_end"], out["rows_end"] = game.shown("status"), stock_rows(game.facts())
    elif mode == "keep_menu":
        fake.use(4)                                           # 석탄을 쓰는 판
        game.wait(0.8)
        game.hotkey()
        game.got.clear()
        out["status"], out["rested"] = game.shown("status"), seen()[:2]
        game.click(STOCK)
        out["keeps"] = keeps(game.facts())
        game.click("stock:3:keep")                            # 메뉴에서 석유의 유지를 끈다
        out["status_off"] = game.shown("status")
        fake.play(176)
        game.wait(0.8)
        out["entered"] = seen()
    elif mode == "keep_reenter":
        fake.play(176)
        game.wait(0.8)
        out["before"] = fake.treasury(176)                    # 유지가 돌고 있다(국고 $20 B)
        game.open()
        game.click(BUTTON)                                    # 옮기지 않은 기능 하나(직접 실행) — 그 안에서 body 가 돈다
        game.wait(1.5)
        out["inside"], out["after"] = inside, fake.treasury(176)
    else:
        fake.play(176)
        game.hotkey()
        game.click(STOCK)
        game.wait(0.8)                                        # 석유가 500만으로 올라온다
        game.got.clear()
        amount = lambda: [fake.stock(176, 3), game.shown("stock:3:keepvalue")]
        type_into(game, "stock:3:keepvalue", "7000000")
        game.wait(0.8)                                        # 치는 동안의 값이 쓰였다면 그사이에 700만이 됐을 것이다
        out["typing"] = amount()
        user32.SendMessageW(game.hwnd, WM_KEYDOWN, 0x0D, 1)   # Enter
        user32.SendMessageW(game.hwnd, WM_KEYUP, 0x0D, 0xC0000001)
        game.wait(0.8)
        out["entered"] = amount()
        type_into(game, "stock:3:keepvalue", "9000000")
        game.click("stock:all")                               # 다른 곳(글)을 누른다
        game.wait(0.8)
        out["clicked_away"] = amount()
        type_into(game, "stock:3:keepvalue", "1234")
        game.hotkey()                                         # 치던 채로 창을 닫는다
        game.wait(0.8)
        game.hotkey()                                         # 다시 연다(물자 탭이 그대로 열려 있다)
        out["closed"] = amount()
    out["lines"], out["text"], out["options"] = lines, game.text(), fake.peek(OPTIONS, "<I")
    print(json.dumps(out, ensure_ascii=False))
    return 0


```

`tests/toybox_overlay_probe.py` 에서 다음을 찾아:

```python
                                                if name.startswith("stock:3:") and name != "stock:3:now")}
```

이렇게 바꾼다:

```python
                                                if name.startswith("stock:3:") and name[len("stock:3:"):] not in ("now", "keep", "keepvalue"))}
```

`tests/toybox_overlay_probe.py` 에서 다음 바로 앞에:

```python
    if mode in ("confirm", "confirm_fault", "hints", "leave", "multiplayer", "pick_gone", "pick_become", "pick_again", "ansi_search"):
```

이것을 더한다:

```python
    if mode.startswith("keep"):
        return run_keep(hook, mode)
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 2: 실패를 본다**

Run: `uv run pytest tests/test_toybox.py -q -k keep 2>&1 | tail -8`

Expected: `4 failed, 4 passed, 62 deselected` — 새 테스트 넷이 실패한다: `test_keep_works_with_the_window_closed_and_shows_in_the_status_line`(검사 도구가 `KeyError: 'money:keep'` 로 끝난다 — 돈 탭에 유지의 칸이 없다), `test_keep_rests_in_the_menu_and_can_be_turned_off_there`(`KeyError: 'stock:0:keep'`), `test_keep_does_not_write_while_the_games_handler_is_running`(`assert 14430000000.0 == 20000000000.0` — 저장된 유지를 아무도 `keeper` 에 넘기지 않아 돌고 있지 않다), `test_a_typed_keep_amount_takes_effect_when_the_typing_is_done`(`KeyError: 'stock:3:keepvalue'`). 통과하는 넷은 이름에 keep 이 든 앞의 테스트들이다(`test_keep_settings` 등).

- [ ] **Step 3: 구현한다**

<!-- 고칠 곳: code -->
`native/srtoybox/input.cpp` 에서 다음 바로 뒤에:

```cpp
        SetWindowLongPtrA(game, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wrapped));
    }
```

이것을 더한다:

```cpp
    // 타이머는 창 스레드에서 걸어야 해서 감싼 프로시저가 처음 불릴 때 건다. 그때까지 기다리지 않게 빈 메시지로 한 번 깨운다 —
    // 최소 유지는 사용자가 아무것도 누르지 않아도 돌아야 한다.
    PostMessageW(game, WM_NULL, 0, 0);
```

`native/srtoybox/ui.cpp` 에서 다음 바로 앞에:

```cpp
#include "overlay.h"
```

이것을 더한다:

```cpp
#include "log.h"
```

`native/srtoybox/ui.cpp` 에서 다음 바로 뒤에:

```cpp
float g_footer;               // 바닥 줄들(알림 · 안내)의 높이 — 지난 프레임에 잰 것
```

이것을 더한다:

```cpp
Keep g_keep_sent;             // keeper 에 마지막으로 넘긴 최소 유지(저장한 설정과 같다)
```

`native/srtoybox/ui.cpp` 에서 다음 바로 앞에:

```cpp
// 돈 탭의 단추 하나: 누르면 국고에 대한 요청을 대기열에 넣는다. 쓰는 것은 게임 창의 타이머에서다(keeper.h).
```

이것을 더한다:

```cpp
// 설정의 최소 유지를 keeper 가 쓰는 꼴로: 국고는 백만 달러 → 달러.
Keep keep_of(const Settings &s)
{
    Keep keep;
    keep.treasury = s.keep_treasury;
    keep.treasury_floor = static_cast<double>(s.keep_treasury_value) * 1e6;
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        keep.stock[slot] = s.keep_stock[slot];
        keep.stock_floor[slot] = static_cast<double>(s.keep_stock_value[slot]);
    }
    return keep;
}

// 창에서 고친 최소 유지를 keeper 에 넘긴다(save 면 설정 파일에도 적는다). 달라진 것이 없으면 아무것도 하지 않는다.
// 로그에는 켠 것 · 끈 것 · 켜진 채로 값이 바뀐 것을 적는다.
void send_keep(bool save)
{
    const Keep want = keep_of(g_settings);
    bool changed = want.treasury != g_keep_sent.treasury || want.treasury_floor != g_keep_sent.treasury_floor;
    if (want.treasury && (!g_keep_sent.treasury || want.treasury_floor != g_keep_sent.treasury_floor))
        log_line("유지 켬: 국고 %lld (백만 달러)", g_settings.keep_treasury_value);
    else if (!want.treasury && g_keep_sent.treasury)
        log_line("유지 끔: 국고");
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        changed = changed || want.stock[slot] != g_keep_sent.stock[slot] || want.stock_floor[slot] != g_keep_sent.stock_floor[slot];
        if (want.stock[slot] && (!g_keep_sent.stock[slot] || want.stock_floor[slot] != g_keep_sent.stock_floor[slot]))
            log_line("유지 켬: %s %lld", product_label(slot).c_str(), g_settings.keep_stock_value[slot]);
        else if (!want.stock[slot] && g_keep_sent.stock[slot])
            log_line("유지 끔: %s", product_label(slot).c_str());
    }
    if (!changed)
        return;
    if (save)
        save_settings(g_settings);
    keeper_set_keep(want);
    g_keep_sent = want;
}

// 최소 유지의 수량 입력란. 치는 동안의 값(5, 50, 500 …)은 쓰이지 않는다 — ImGui 의 InputScalar 는 입력을 마쳤을 때
// (Enter, 다른 곳을 누름)에만 값을 넘겨준다. 치던 채로 창을 닫으면 친 것은 버려진다. 누르면 지금 값이 통째로 골라진다.
void keep_input(const char *id, long long *value, long long high, float width)
{
    ImGui::SetNextItemWidth(width);
    if (ImGui::InputScalar(id, ImGuiDataType_S64, value)) {
        *value = std::min(high, std::max(0LL, *value));
        send_keep(true);
    }
}

// 상태 줄의 뒤에 붙는 글: 최소 유지가 지금 무엇을 하고 있는가. 켜진 것이 없으면 빈 글.
std::string keep_text(const GameState &game)
{
    if (keep_count(g_keep_sent) == 0)
        return std::string();
    if (!game.known)
        return keep_resting_text(g_keep_sent, "게임을 읽을 수 없어 쉽니다");
    if (game.multiplayer)
        return keep_resting_text(g_keep_sent, "멀티플레이에서는 쉽니다");
    if (!game.in_game)
        return keep_resting_text(g_keep_sent, "게임에 들어가면 적용");
    if (!game_values_off().empty())
        return keep_resting_text(g_keep_sent, "값을 쓸 수 없어 쉽니다");
    const GameValues now = game_values();
    return now.ok ? keep_active_text(g_keep_sent, now.used) : keep_resting_text(g_keep_sent, "값을 읽을 수 없어 쉽니다");
}

```

`native/srtoybox/ui.cpp` 에서 다음 바로 뒤에:

```cpp
    ImGui::TextDisabled("국고는 음수가 될 수 있다. 다른 나라의 국고는 건드리지 않는다");
    ImGui::EndDisabled();
```

이것을 더한다:

```cpp
    ImGui::Spacing();

    // 최소 유지는 설정이다 — 게임 밖에서도 켜고 끌 수 있다(쓰는 것은 게임 안에서만이다)
    if (ImGui::Checkbox("최소 유지", &g_settings.keep_treasury))
        send_keep(true);
    note("money:keep", g_settings.keep_treasury ? "1" : "0");
    ImGui::SameLine();
    keep_input("##keepvalue", &g_settings.keep_treasury_value, KEEP_TREASURY_MAX, 150.0f);
    note("money:keepvalue", std::to_string(g_settings.keep_treasury_value));
    ImGui::SameLine();
    ImGui::TextUnformatted("백만 달러");
    ImGui::TextDisabled("켜 두면 국고가 이 금액보다 적어질 때 이 금액으로 올린다(0.5초마다). 창을 닫아도, 새 판에서도 계속된다");
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
// 물자 탭의 한 줄. slot 이 ALL_STOCK 이면 "모든 물자" 줄이다(재고 표시가 없다).
void stock_row(int slot, const GameValues &now, bool blocked)
{
    const bool all = slot == ALL_STOCK;
    const std::string name = all ? std::string("stock:all") : "stock:" + std::to_string(slot);
    const std::string label = all ? std::string("모든 물자") : product_label(slot);
    const std::string have = all || !now.ok ? std::string("-") : short_amount(now.stock[slot]);
```

이렇게 바꾼다:

```cpp
// 물자 탭의 한 줄. slot 이 ALL_STOCK 이면 "모든 물자" 줄이다(재고 표시와 최소 유지가 없다).
// 이번 판에서 쓰지 않는 물자의 줄(최소 유지가 켜져 있어 남은 것)은 단추가 꺼져 있다.
void stock_row(int slot, const GameValues &now, bool blocked)
{
    const bool all = slot == ALL_STOCK;
    const bool unused = !all && now.ok && !now.used[slot];
    const std::string name = all ? std::string("stock:all") : "stock:" + std::to_string(slot);
    const std::string label = all ? std::string("모든 물자") : product_label(slot);
    const std::string have = all || !now.ok ? std::string("-") : unused ? std::string("쓰지 않음") : short_amount(now.stock[slot]);
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
    ImGui::BeginDisabled(blocked || !now.ok);
    stock_buttons(name, slot);
    ImGui::EndDisabled();
```

이렇게 바꾼다:

```cpp
    ImGui::BeginDisabled(blocked || !now.ok || unused);
    stock_buttons(name, slot);
    ImGui::EndDisabled();
    ImGui::TableNextColumn();
    if (!all) {                                  // 최소 유지는 설정이다 — 단추가 꺼져 있을 때도 고칠 수 있다
        if (ImGui::Checkbox("##keep", &g_settings.keep_stock[slot]))
            send_keep(true);
        note(name + ":keep", g_settings.keep_stock[slot] ? "1" : "0");
        ImGui::SameLine();
        keep_input("##keepvalue", &g_settings.keep_stock_value[slot], KEEP_STOCK_MAX, 120.0f);
        note(name + ":keepvalue", std::to_string(g_settings.keep_stock_value[slot]));
    }
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
// 게임 안에서는 이번 판에서 쓰는 물자만, 게임 밖에서는 이름표에 있는 물자가 나온다(단추는 꺼져 있다). 쓸 수 있으면 true.
```

이렇게 바꾼다:

```cpp
// 게임 안에서는 이번 판에서 쓰는 물자만, 게임 밖에서는 이름표에 있는 물자가 나온다(단추는 꺼져 있다).
// 최소 유지가 켜진 물자는 어느 쪽에서든 줄이 남는다(끌 수 있게). 쓸 수 있으면 true.
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
    const ImGuiTableFlags flags = ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_RowBg | ImGuiTableFlags_BordersInnerV
        | ImGuiTableFlags_ScrollX | ImGuiTableFlags_ScrollY;   // 창이 좁으면 표가 가로로 구른다
    if (!ImGui::BeginTable("stock", 3, flags))
```

이렇게 바꾼다:

```cpp
    ImGui::TextDisabled("최소 유지를 켜 두면 재고가 그 수량보다 적어질 때 그 수량으로 올린다(0.5초마다). 창을 닫아도, 새 판에서도 계속된다");
    const ImGuiTableFlags flags = ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_RowBg | ImGuiTableFlags_BordersInnerV
        | ImGuiTableFlags_ScrollX | ImGuiTableFlags_ScrollY;   // 창이 좁으면 표가 가로로 구른다
    if (!ImGui::BeginTable("stock", 4, flags))
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
    ImGui::TableHeadersRow();
    stock_row(ALL_STOCK, now, blocked);
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (now.ok ? now.used[slot] : find_product(slot) != nullptr)
```

이렇게 바꾼다:

```cpp
    ImGui::TableSetupColumn("최소 유지");
    ImGui::TableHeadersRow();
    stock_row(ALL_STOCK, now, blocked);
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if ((now.ok ? now.used[slot] : find_product(slot) != nullptr) || g_settings.keep_stock[slot])
```

`native/srtoybox/ui.cpp` 에서 다음을 찾아:

```cpp
    const std::string text = !game.known ? "게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다"
        : game.multiplayer ? "멀티플레이에서는 동작하지 않습니다"
        : !game.in_game ? "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"
        : "플레이 중: " + region_label(game.player) + " (" + std::to_string(game.player) + ")";
```

이렇게 바꾼다:

```cpp
    const std::string state = !game.known ? "게임 상태를 읽을 수 없습니다 — 글쇠 방식으로 동작합니다"
        : game.multiplayer ? "멀티플레이에서는 동작하지 않습니다"
        : !game.in_game ? "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"
        : "플레이 중: " + region_label(game.player) + " (" + std::to_string(game.player) + ")";
    const std::string text = state + keep_text(game);   // 최소 유지가 켜져 있으면 늘 보인다 — 켜 둔 것을 잊지 않게
```

`native/srtoybox/ui.cpp` 에서 다음 바로 뒤에:

```cpp
    g_settings = load_settings();
```

이것을 더한다:

```cpp
    send_keep(false);             // 저장해 둔 최소 유지를 keeper 에 넘긴다 — 창을 한 번도 열지 않아도 돈다
```
<!-- 고칠 곳 끝 -->

- [ ] **Step 4: 빌드하고 통과를 본다**

Run: `uv run srkit toybox-build | tail -1 && uv run pytest tests/test_toybox.py -q 2>&1 | tail -2`

Expected: `빌드 완료: …`, `70 passed`.

- [ ] **Step 5: 커밋한다**

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add native/srtoybox/ui.cpp native/srtoybox/input.cpp tests/test_toybox.py tests/toybox_overlay_probe.py && git commit -q -F - <<'EOF'
feat: ToyBox 최소 유지를 창에서 켜고 끈다 — 돈 · 물자 탭의 칸, 상태 줄의 "유지 중"

- 돈 탭에 "최소 유지"(백만 달러), 물자 탭에 넷째 칸. 켜짐과 값을 저장하고, ToyBox 가 뜰 때부터 적용한다(창을 열지 않아도).
- 유지의 칸은 게임 밖에서도 고칠 수 있다. 유지가 켜진 물자는 쓰지 않는 판에서도 줄이 남는다(끌 수 있게).
- 수량은 입력을 마쳤을 때 쓰인다(치는 동안의 값이 바닥으로 쓰이지 않는다).
- 상태 줄: 게임 안에서는 유지되는 것의 이름, 쉬는 동안에는 켜진 수와 까닭 — 켜 둔 것을 잊지 않게 늘 보인다.
- 게임 창의 타이머를 빈 메시지로 깨워서 건다(유지는 입력이 없어도 돌아야 한다).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `336 passed`.

---

### Task 9: 게임 안 확인 — 최소 유지 (V1 · V8 ~ V11 · V13), 최종 검토, 머지

**브랜치:** `feat/toybox-values-keep` (게임이 떠 있는 동안 바꾸지 않는다)

**Files:**
- Modify: `scripts/gamedrive.py` (`peek <지역 번호>`)
- 근거 화면과 로그 사본은 `build/verify/toybox/`(git 제외)에 둔다.

**Interfaces:**
- Consumes: Task 8 의 빌드, 계획 (나)의 `gamedrive.py peek`.
- Produces: `uv run python scripts/gamedrive.py peek <지역 번호>` — 국고 · 재고를 플레이어 대신 그 번호의 지역에서 읽는다(결과에 `region`. `player` 는 여전히 플레이하는 나라의 번호다). 그리고 이 Task 의 결과(`vd-keep.md` — Task 10 이 `docs/10` 에 적는다)와 `develop` 에 머지된 PR.

- [ ] **Step 1: `gamedrive.py peek` 에 지역 번호를 줄 수 있게 한다**

<!-- 고칠 곳: code -->
`scripts/gamedrive.py` 에서 다음을 찾아:

```python
    uv run python scripts/gamedrive.py peek                   # 이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다(읽기만, JSON)
```

이렇게 바꾼다:

```python
    uv run python scripts/gamedrive.py peek [지역 번호]       # 이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 값을 읽는다(읽기만, JSON).
                                                              # 번호를 주면 플레이어 대신 그 지역의 국고 · 재고를 읽는다
```

`scripts/gamedrive.py` 에서 다음을 찾아:

```python
def peek_game(cfg: config.Config) -> dict:
    """이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 것을 읽는다(읽기만). 주소는 srkit locate 와 같은 방법(서명)으로 찾는다.

    ToyBox 의 창에 보이는 값이 아니라 게임의 메모리 그 자체다 — ToyBox 가 쓴 값과 치트 허용 비트를 따로 확인하는 데 쓴다.
```

이렇게 바꾼다:

```python
def peek_game(cfg: config.Config, number: int | None = None) -> dict:
    """이 도구가 띄운 게임의 메모리에서 ToyBox 가 보는 것을 읽는다(읽기만). 주소는 srkit locate 와 같은 방법(서명)으로 찾는다.

    ToyBox 의 창에 보이는 값이 아니라 게임의 메모리 그 자체다 — ToyBox 가 쓴 값과 치트 허용 비트를 따로 확인하는 데 쓴다.
    number 를 주면 국고 · 재고를 플레이어 대신 그 번호의 지역 객체에서 읽는다(지역 표에서 찾는다. 결과의 region 이 그 번호다) —
    플레이하는 나라를 바꾼 뒤 앞 나라의 값이 그대로인지 볼 때 쓴다.
```

`scripts/gamedrive.py` 에서 다음을 찾아:

```python
            out["treasury"] = read(player + values["treasury"], "<d")
            out["stock"] = [read(player + values["stock_first"] + values["stock_step"] * i, "<f") for i in range(toybox.STOCK_SLOTS)]
```

이렇게 바꾼다:

```python
            who = player
            if number is not None:                                      # 지역 표(인덱스 1 … 지역 수)에서 그 번호의 객체를 찾는다
                count = min(read(base + state["region_count"], "<i") or 0, 1023)
                table = (read(base + state["region_table"] + 8 * index, "<Q") for index in range(1, count + 1))
                who = next((pointer for pointer in table if pointer and read(pointer + 8, "<H") == number), None)
                if who is None:
                    raise SystemExit(f"그 번호의 지역이 지역 표에 없습니다: {number}")
                out["region"] = number
            out["treasury"] = read(who + values["treasury"], "<d")
            out["stock"] = [read(who + values["stock_first"] + values["stock_step"] * i, "<f") for i in range(toybox.STOCK_SLOTS)]
```

`scripts/gamedrive.py` 에서 다음을 찾아:

```python
        print(json.dumps(peek_game(cfg), ensure_ascii=False))
```

이렇게 바꾼다:

```python
        print(json.dumps(peek_game(cfg, int(args[0]) if args else None), ensure_ascii=False))
```
<!-- 고칠 곳 끝 -->

Run: `uv run python scripts/gamedrive.py peek 1499; echo "exit=$?"`
Expected: 게임이 떠 있지 않으므로 `게임이 떠 있지 않습니다`, `exit=1`. (게임이 뜬 뒤의 동작은 Step 4 에서 본다.)

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git add scripts/gamedrive.py && git commit -q -F - <<'EOF'
chore: gamedrive.py peek <지역 번호> — 플레이어가 아닌 지역의 국고 · 재고도 읽는다(검증용, 읽기만)

플레이하는 나라를 바꾼 뒤 앞 나라의 값이 그대로인지(최소 유지가 플레이어의 나라만 건드리는지) 메모리로 본다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline -1
```

Expected: `336 passed`.

- [ ] **Step 2: PR 을 올린다 (머지는 게임 안 확인과 최종 검토 뒤에)**

스크래치에 `pr-values-keep.md` 를 쓴다(Write 도구): 무엇을 고쳤나(Task 6 ~ 9 의 커밋 요약), 요구 2 · 3 에 대해 자동 테스트가 보는 것(유지가 플레이하는 나라의 값만 본다 · 쓰지 않는 물자와 게임 밖에서는 쓰지 않는다 · 명령 처리 함수를 부르지 않고 글쇠를 넣지 않는다), 설계서와 달라진 곳(이 계획의 같은 이름의 절에서 이 PR 에 닿는 것들), "게임 안 확인과 최종 검토의 결과는 아래 댓글에", `uv run pytest` 의 결과 줄 그대로, 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
cd /e/SR2030ToyBox && git push -u origin feat/toybox-values-keep && gh pr create --repo game-mod-project/SR2030Toybox --base develop --head feat/toybox-values-keep --title "feat: ToyBox 최소 유지 — 국고와 물자가 정해 둔 값보다 적어지면 올린다" --body-file "<스크래치>/pr-values-keep.md"
```

- [ ] **Step 3: 시험용 빌드를 게임 폴더에 바꿔 넣고, 검증용 설정과 검증 전의 상태를 적어 둔다**

Run: `uv run python scripts/gamedrive.py status; uv run srkit deploy toybox`
Expected: 게임이 떠 있지 않다. 미리보기에 `갱신: srtoybox.dll` 한 줄과 `미리보기(--apply 로 실행): 1개 파일 …`. **다른 줄이 있으면 멈춘다.**

Run: `uv run srkit deploy toybox --apply`
Expected: `설치 완료: 1개 파일 → …`

```bash
cd /e/SR2030ToyBox && mkdir -p build/verify/toybox build/verify/toybox-home-vd && rm -f build/verify/toybox-home-vd/*
```

`build/verify/toybox-home-vd/toybox.ini` 를 Write 도구로 쓴다 — 유지의 값만 미리 넣고 켜지는 않는다(국고 $500 B, 석유 9억. 독일의 처음 값보다 크다):

```
keep.treasury.value=500000
keep.stock.3.value=900000000
```

```bash
cd /e/SR2030ToyBox && ls build/verify/toybox-home-vd/ && cat build/verify/toybox-home-vd/toybox.ini && uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" > build/verify/toybox/VD-saves-before.txt && cat build/verify/toybox/VD-saves-before.txt && ls -la --time-style=full-iso "$APPDATA/SR2030ToyBox/toybox.ini" | tee build/verify/toybox/VD-user-ini-before.txt && grep -c "^keep" "$APPDATA/SR2030ToyBox/toybox.ini"
```

Expected: 폴더에 `toybox.ini` 하나. 사용자의 실제 설정 파일에는 `keep` 줄이 없다(`0` — 유지를 아는 빌드가 그 파일을 고쳐 쓴 적이 없다. 0 이 아니면 `grep "^keep.*=1$"` 로 켜진 것이 없는지 보고, 본 것을 적는다).

- [ ] **Step 4: 백그라운드 에이전트에게 게임 안 확인을 맡긴다**

Agent 도구(`general-purpose`, 백그라운드)에 다음 지시문을 그대로 준다:

```
Supreme Ruler 2030 의 ToyBox(게임 안 모드 설정 창)의 "최소 유지"를 게임에서 확인한다. 이 작업(VD)만 수행하라.
끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.
명세에 없는 것을 추측 · 즉흥으로 하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라.
코드와 문서를 고치지 말라. git 명령을 내지 말라(브랜치를 바꾸면 안 된다).
모든 명령에 절대경로를 쓴다. cd 후 상대경로로 후속 명령을 내지 말 것 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다.

먼저 E:\SR2030ToyBox\CLAUDE.md 의 "명령"(gamedrive.py 쓰는 법)과 E:\SR2030ToyBox\docs\10-toybox.md 의 "쓰는 법" · "확인한 것"의 VB 표(게임에 들어가는 길,
시간을 흘리는 법, "외교·영토" 탭에서 나라를 고르는 법)를 읽는다.

최소 유지란: 국고나 물자의 재고가 정해 둔 값보다 적어지면 ToyBox 가 그 값으로 올리는 것이다(0.5초마다). "돈" 탭의 "최소 유지" 체크와 그 옆의 수량(백만 달러),
"물자" 탭의 줄마다 맨 오른쪽 칸의 체크와 수량으로 켠다. 무엇이 유지되는지는 창 맨 위의 상태 줄에 보인다. 설정은 저장된다.

규칙:
- 게임은 다음으로만 띄운다(백그라운드로). 화면 밖에 뜬다. 사용자가 켠 게임이 떠 있으면 아무것도 하지 말고 보고한다.
    SRTOYBOX_HOME='E:\SR2030ToyBox\build\verify\toybox-home-vd' uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py start
  그 뒤의 명령은 uv run --project E:\SR2030ToyBox python E:\SR2030ToyBox\scripts\gamedrive.py <shot|click|move|key|wheel|type|status|peek|stop> …
  SRTOYBOX_HOME 을 빼고 띄우면 안 된다 — 사용자의 실제 설정에 유지가 켜진 채로 남는다.
- gamedrive.py peek 은 게임의 메모리에서 읽은 값을 JSON 으로 낸다: treasury = 플레이어의 국고(달러), stock = 재고 열두 칸(칸 3 이 석유), used, player = 플레이하는
  나라의 번호, cheats_allowed, in_game. "peek 1499" 처럼 지역 번호를 주면 플레이어 대신 그 지역(1499 = 독일)의 국고와 재고를 읽는다.
- 유지는 0.5초마다 본다. 무언가를 누른 뒤에는 2초 기다렸다가 peek 을 찍는다.
- 게임을 저장하지 않는다("저장 후 종료"를 누르지 않는다). 게임의 시간은 6 과 8 에서만, 거기 적힌 만큼만 흘린다. 한 판에서 게임 날짜가 3일을 넘기면 안 된다.
- cheat resettutorial · cheat depopulate 는 어떤 경우에도 넣지 않는다. 8 의 "이 나라로 플레이" 말고는 "돈" · "물자" 탭 밖의 ToyBox 단추를 누르지 않는다.
- ToyBox 창은 화면의 왼쪽 위(40,60)에 720x520 으로 열린다. 게임의 속도 단추나 패널을 가리면 창을 닫고(같은 단축키) 누른다.
- 화면은 E:\SR2030ToyBox\build\verify\toybox\VD-<번호>-<이름>.png 로 찍는다.
- ToyBox 의 로그는 E:\SR2030ToyBox\build\verify\toybox-home-vd\toybox.log, 설정은 같은 폴더의 toybox.ini 다.

할 일(순서대로. 단계마다 화면을 찍고, 본 것을 그대로 적는다. peek 의 출력은 그대로 옮긴다):

첫 실행
1. 게임을 띄우고 메인 메뉴가 그려질 때까지 기다린다. 로그에서 "값을 씁니다 (…)" 와 "옛 방식(내장 치트)으로 도는 기능이 …개 남아 있습니다 (…)" 를 옮겨 적는다.
   key CTRL+SHIFT+T 로 ToyBox 창을 열어 상태 줄을 적는다(유지에 대한 글이 없어야 한다). "돈" 탭의 "최소 유지" 체크가 꺼져 있고 수량이 500000 인지,
   "물자" 탭의 "석유" 줄의 체크가 꺼져 있고 수량이 900000000 인지 적는다. 창을 닫는다.
2. 샌드박스 "2030 - 세계"를 기본 선택(독일)으로 시작한다. 일시 정지 상태인지 본다. peek 을 찍는다(T0 = treasury, S0 = stock[3]).
3. (V8) ToyBox 창을 열어 "물자" 탭의 "석유" 줄의 최소 유지 체크를 켠다. 2초 뒤 peek(기대: stock[3] = 900000000, treasury 는 T0 그대로, cheats_allowed 0).
   상태 줄(기대: "플레이 중: 독일 (1499) · 유지 중: 석유"), "석유" 줄의 재고 칸(기대: "900 M"), 로그의 새 줄(기대: "유지 켬: 석유 900000000" 과 "유지: 석유 … -> 900 M")을 적는다.
4. "돈" 탭의 "최소 유지" 체크를 켠다. 2초 뒤 peek(기대: treasury = 500000000000). 상태 줄(기대: "… · 유지 중: 국고, 석유"), "국고: $ …"(기대: 500.00 B),
   로그의 새 줄(기대: "유지 켬: 국고 500000 (백만 달러)" 와 "유지: 국고 … -> 500.00 B")을 적는다.
5. (V9) "돈" 탭의 "-$100 B" 를 한 번 누르고 2초 뒤 peek(기대: treasury 가 500000000000 으로 돌아와 있다). 로그에 "값 쓰기: 국고 500.00 B -> 400.00 B" 가 한 줄 생겼는지 적는다.
   "물자" 탭의 "석유" 줄의 "0" 을 한 번 누르고 2초 뒤 peek(기대: stock[3] = 900000000). 로그에 "값 쓰기: 석유 900 M -> 0" 이 생겼는지 적는다.
6. (V8 · V13) ToyBox 창을 닫는다. peek 을 찍어 둔다(stock 열두 칸 — 흘리기 전). 게임의 속도를 "매우 느림"으로 실제 25초 흘린 뒤 다시 일시 정지한다
   (게임 날짜가 하루를 넘길 것 같으면 더 일찍 멈추고, 몇 초를 흘렸는지 적는다). 2초 뒤 peek.
   적을 것: 게임이 살아 있는지, 게임의 날짜 · 시각, stock[3](기대: 900000000 — 그 사이에 소비가 있었어도 그 수준이다), treasury(기대: 500000000000 이상),
   유지를 켜지 않은 다른 칸의 재고가 흘리기 전과 달라졌는지(달라졌으면 그 사이에 게임이 재고를 고쳤다는 근거다 — 어느 칸이 얼마나).
7. (수량을 친다) ToyBox 창을 열어 "물자" 탭의 "석유" 줄의 수량 칸을 누른다(글이 통째로 골라진다). type 950000000 으로 치고, **ENTER 를 누르기 전에** peek 을 찍는다
   (기대: stock[3] 은 900000000 그대로 — 치는 동안의 값은 쓰이지 않는다). key ENTER 를 누르고 2초 뒤 peek(기대: stock[3] = 950000000).
   로그의 새 줄(기대: "유지 켬: 석유 950000000" 과 "유지: 석유 900 M -> 950 M")을 적는다. 수량 칸에 950000000 이 남아 있는지 적는다.
8. (V10) "외교·영토" 탭에서 폴란드를 고르고, 맨 아래의 "이 나라로 플레이" 를 누른다(한 번 누르면 "… 한 번 더 누르면 실행합니다"로 바뀐다. 한 번 더 누른다).
   상태 줄(기대: "플레이 중: 폴란드 (1106) · 유지 중: …")을 적는다. 2초 뒤 peek(player 는 1106. treasury 와 stock[3] — 기대: 유지 값보다 작았다면 500000000000 · 950000000 으로
   올라와 있다. 폴란드가 석유를 쓰지 않는 판이면 used[3] 이 false 이고 석유는 유지되지 않는다 — 본 대로)과 peek 1499(독일의 treasury 와 stock[3] — D1)를 찍는다.
   (이 단추는 아직 내장 치트로 돈다 — cheats_allowed 가 1 이 되는 것은 기대대로다.)
   ToyBox 창을 닫고 시간을 "매우 느림"으로 실제 10초 흘린 뒤 일시 정지한다. 2초 뒤 peek 과 peek 1499 를 찍는다.
   적을 것: 폴란드의 treasury · stock[3](기대: 유지 값 그대로), 독일의 treasury · stock[3] 이 D1 과 같은지 달라졌는지
   (독일의 석유가 950000000 보다 줄어 있고 다시 올라오지 않았다면 — 유지가 앞의 나라를 건드리지 않는다는 근거다. D1 그대로면 "그대로였다"고 적는다).
9. (V1) ToyBox 창을 닫고, 게임의 메뉴(ESC) → "게임 종료" → 저장하지 않고 메인 메뉴로 나온다. ToyBox 창을 열어 상태 줄을 적는다
   (기대: "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다 · 유지 2개 켜짐(게임에 들어가면 적용)"). "돈" 탭의 단추가 흐리고 "최소 유지" 체크는 켜져 있는지 적는다.
   10초 기다린 뒤, 메뉴에 있는 동안 로그에 "값 쓰기" 나 "유지: " 줄이 새로 생겼는지 적는다(생기면 안 된다).
10. gamedrive.py stop 으로 게임을 끈다. status 로 꺼진 것을 확인한다. 로그를 E:\SR2030ToyBox\build\verify\toybox\VD-1.log 로,
    toybox.ini 를 E:\SR2030ToyBox\build\verify\toybox\VD-1.ini 로 복사한다.

둘째 실행 (같은 SRTOYBOX_HOME 으로 — 게임을 다시 켜도 유지가 이어지는가)
11. 같은 명령으로 게임을 다시 띄운다. 메인 메뉴에서 로그의 이번 실행 부분에 "유지 켬: 국고 500000 (백만 달러)" 와 "유지 켬: 석유 950000000" 이 있는지 적는다.
    ToyBox 창을 열어 상태 줄을 적고(기대: "… · 유지 2개 켜짐(게임에 들어가면 적용)") 창을 닫는다.
12. (V11) 샌드박스 "2030 - 세계"를 독일로 새로 시작한다. **ToyBox 창을 열지 않은 채로** 게임 화면이 뜨고 3초 뒤 peek 을 찍는다
    (기대: treasury = 500000000000, stock[3] = 950000000 — 새 판에 바로 적용된다). 로그의 새 줄("유지: 국고 … -> 500.00 B", "유지: 석유 … -> 950 M")을 적는다.
    ToyBox 창을 열어 상태 줄을 적는다(기대: "플레이 중: 독일 (1499) · 유지 중: 국고, 석유").
13. (끈다) "돈" 탭의 "최소 유지" 체크를 끄고, "물자" 탭의 "석유" 줄의 체크를 끈다. 상태 줄에 유지에 대한 글이 없어졌는지 적는다.
    "돈" 탭의 "-$100 B" 를 한 번 누르고 3초 뒤 peek(기대: treasury = 400000000000 그대로 — 꺼졌다). 로그의 새 줄("유지 끔: 국고", "유지 끔: 석유")을 적는다.
14. 창을 닫고, 저장하지 않고 메인 메뉴로 나온 뒤 gamedrive.py stop 으로 게임을 끈다. status 로 꺼진 것을 확인한다.
    로그를 E:\SR2030ToyBox\build\verify\toybox\VD-2.log 로, toybox.ini 를 E:\SR2030ToyBox\build\verify\toybox\VD-2.ini 로 복사한다.

보고: 단계마다 (한 것 / 본 것 / 화면 파일). 로그에 "예외" 나 "실패" 가 든 줄이 있으면 그대로 옮긴다. 보지 못한 것은 "보지 못했다"와 까닭.
기대와 다른 것이 있어도 고치려 하지 말고 본 대로 적는다.
```

에이전트가 도는 동안 브랜치를 바꾸지 않는다. Task 10 의 문서 초안은 써도 된다(커밋은 브랜치를 바꿔야 하므로 에이전트가 끝난 뒤에).

- [ ] **Step 5: 에이전트의 보고를 직접 확인한다**

```bash
cd /e/SR2030ToyBox && grep -n "값을 \|옛 방식\|유지\|값 쓰기\|직접 실행\|예외\|실패" build/verify/toybox/VD-2.log | cut -c1-150; echo ---; grep -n "^keep.treasury\|^keep.stock.3" build/verify/toybox/VD-1.ini build/verify/toybox/VD-2.ini; uv run python scripts/gamedrive.py status; git status --short; git branch --show-current; uv run python -c "from srkit import config; import os; d = config.user_save_dir(); print(sorted(os.listdir(d)) if d.is_dir() else '저장 폴더 없음')" | diff - build/verify/toybox/VD-saves-before.txt && echo "저장 폴더 그대로"; ls -la --time-style=full-iso "$APPDATA/SR2030ToyBox/toybox.ini" | diff - build/verify/toybox/VD-user-ini-before.txt && echo "사용자의 설정 파일 그대로"
```

(`VD-2.log` 는 두 실행의 줄을 모두 담고 있다 — 같은 폴더의 로그에 이어 쓴다.)

Expected:
- 첫 실행: `유지 켬: 석유 900000000` → `유지: 석유 … -> 900 M` → `유지 켬: 국고 500000 (백만 달러)` → `유지: 국고 14.43 B -> 500.00 B` → `값 쓰기: 국고 500.00 B -> 400.00 B` → `값 쓰기: 석유 900 M -> 0` → `유지 켬: 석유 950000000` → `유지: 석유 900 M -> 950 M` → `직접 실행: cheat becomeregion 1106`(8 의 단추. 그 앞에 `cheat allowcheats`). 5 의 "돌아왔다"는 로그에 줄이 없다(항목마다 처음 올린 것만 적는다) — peek 이 근거다.
- 둘째 실행: `시작 (프로세스 …)` 뒤에 `유지 켬: 국고 500000 (백만 달러)` · `유지 켬: 석유 950000000`, 게임에 들어간 뒤 `유지: 국고 … -> 500.00 B` · `유지: 석유 … -> 950 M`, 끝에 `유지 끔: 국고` · `유지 끔: 석유` · `값 쓰기: 국고 500.00 B -> 400.00 B`.
- `예외` · `실패` 가 든 줄이 없다.
- `VD-1.ini`: `keep.treasury=1` · `keep.treasury.value=500000` · `keep.stock.3=1` · `keep.stock.3.value=950000000`. `VD-2.ini`: 둘 다 `=0`, 값은 그대로.
- 게임이 떠 있지 않다. 작업 폴더가 깨끗하고 브랜치가 `feat/toybox-values-keep` 다. `저장 폴더 그대로`. `사용자의 설정 파일 그대로`.

Read 도구로 화면을 직접 본다: 유지를 켠 뒤의 물자 탭(3)과 돈 탭(4), 시간을 흘린 뒤(6), 나라를 바꾼 뒤의 상태 줄(8), 메뉴의 상태 줄(9), 창을 열지 않은 새 판(12). 에이전트가 적은 글 · 숫자와 화면이 같은지 본다.

**멈추는 경우**: 유지가 다른 나라의 값을 고쳤다(8 에서 독일의 값이 유지 값으로 올라왔다), 메뉴에서 값을 썼다(9), 게임이 죽었다, `값 쓰기 실패` 가 나왔다, 사용자의 실제 설정 파일이 바뀌었다 — 머지하지 않고 본 것을 그대로 사용자에게 알린다. 그 밖에 기대와 다른 것(시간이 흐르는 동안 재고가 유지 값보다 잠깐 낮게 읽혔다 같은 것)은 본 대로 적고 이어 간다.

- [ ] **Step 6: 최종 검토를 받고 고친다**

**코드의 최종 검토는 여기서 한 번, 두 PR 을 함께 놓고 받는다**: 범위는 이 계획을 시작하기 전의 `develop`(`8991bd1`)부터 이 브랜치의 머리까지다(Task 5 에서 머지된 물자 탭의 커밋 포함). 실행 방식의 최종 검토 절차대로 검토받고(검토자에게 이 문서의 Review Focus 와 "설계서와 달라진 곳"을 함께 준다), Critical · Important 를 고친다 — 고칠 때마다 실패하는 테스트를 먼저 쓴다. 고쳤으면 `uv run srkit toybox-build` → `uv run pytest` → 게임이 꺼진 채로 `uv run srkit deploy toybox` 미리보기(`갱신: srtoybox.dll` 한 줄) → `--apply` 로 최종 빌드를 다시 넣는다. 고친 것이 게임 안의 동작을 바꾸면 Step 4 의 해당 단계만 다시 본다.

- [ ] **Step 7: 결과를 PR 에 적고 머지한다**

스크래치에 `vd-keep.md` 를 쓴다(Write 도구): 단계마다 한 것 / 본 것 / 근거 화면의 이름, peek 의 값 그대로, 로그의 줄 그대로, 보지 못한 것, 최종 검토의 결과(고친 것 · 미룬 것). `gh pr comment <번호> --repo game-mod-project/SR2030Toybox --body-file "<스크래치>/vd-keep.md"` 로 PR 에 단다.

```bash
cd /e/SR2030ToyBox && uv run pytest -q 2>&1 | tail -2 && git push && gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && git switch develop && git pull --ff-only origin develop && git log --oneline -1 && uv run srkit deploy toybox | tail -2
```

Expected: 테스트 통과, 머지 커밋이 `develop` 의 머리다. 게임 폴더에는 이 브랜치의 마지막 빌드가 들어 있다(미리보기가 0개 파일).

---

### Task 10: 문서

**브랜치:** `docs/toybox-values-stock-keep` (Task 9 의 PR 이 들어간 `develop` 에서 나눈다)

**Files:**
- Modify: `docs/10-toybox.md`, `docs/11-game-internals.md`, `docs/05-game-systems.md`, `docs/09-cheat-mod-plan.md`, `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md` ("보완 내역"에 한 절)

**Interfaces:**
- Consumes: Task 5 의 `vc-stock.md`, Task 9 의 `vd-keep.md`(본 것 · 보지 못한 것 · 최종 검토의 결과), 이 계획의 "설계서와 달라진 곳" · "계획을 쓰며 확인한 것".
- Produces: 문서. 게임 안에서 보지 않은 것은 "보지 못했다"로 적는다 — 두 파일에 없는 것을 본 것처럼 쓰지 않는다.

- [ ] **Step 1: 브랜치를 만든다**

```bash
cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git switch -c docs/toybox-values-stock-keep && git log --oneline -1
```

- [ ] **Step 2: `docs/10-toybox.md`**

1. "무엇인가": 3단계 문단에 "물자 탭과 최소 유지도 내장 치트를 거치지 않는다(3단계 1 (다), 2026-10-10). 묶음 1(기반 + 돈 · 물자)이 끝났다. 나머지 19개 기능은 옮길 때까지 내장 치트로 돈다"를 더한다.
2. "쓰는 법":
   - 물자 탭 — 물자마다 한 줄(이름, 재고, `-1억` · `-100만` · `0` · `+100만` · `+1억`), 맨 위의 "모든 물자" 줄(이번 판에서 쓰는 물자 모두에 같은 일). 게임 안에서는 이번 판에서 쓰는 물자만, 게임 밖에서는 이름표의 열하나가 재고 없이 나온다. 재고는 0 아래로 내려가지 않는다.
   - 최소 유지 — 돈 탭의 "최소 유지"(백만 달러, 0 ~ 1,000,000)와 물자 탭의 넷째 칸(수량, 0 ~ 1,000,000,000). 켜 두면 값이 그 수준보다 적어질 때 그 수준으로 올린다(0.5초마다). **설정 창을 닫아도, 게임을 다시 켜도, 새 판을 시작해도 계속된다** — 창 맨 위의 상태 줄에 무엇이 유지되는지 늘 보인다(게임 밖에서는 `유지 N개 켜짐(게임에 들어가면 적용)`). 끄려면 체크를 끈다(게임 밖에서도 된다). 수량은 Enter 를 누르거나 다른 곳을 눌러 입력을 마쳐야 쓰인다 — 치던 채로 창을 닫으면 버려진다.
3. "기능"의 표: 물자의 세 줄(`cheat products N` · `cheat branson` · `cheat bezos`)을 지우고 물자 탭의 줄들과 최소 유지의 줄들로 바꾼다. "게임에 넣는 것" 칸은 "없다 — 재고 칸(float)에 직접 쓴다". 검증 칸은 `vc-stock.md` · `vd-keep.md` 의 단계 번호([확인: VC-5] 등). 표 위의 기능 수(22 → 19 + 돈 · 물자 탭)를 고친다.
4. "한계"에 더한다(본 대로 고쳐 적는다):
   - 최소 유지는 "아래로 내려가면 올린다"뿐이다 — 값을 그 수준에 묶어 두지 않는다(올라가는 것은 막지 않는다). 0.5초 사이에는 그보다 낮을 수 있다.
   - 유지를 켜 둔 것을 잊고 새 판을 시작하면 그 판에도 적용된다(사용자가 고른 동작 — 상태 줄을 본다).
   - 유지가 올린 것은 창 바닥의 `마지막으로 쓴 값` 에 나오지 않는다(로그에 항목마다 처음 한 번).
   - 유지가 켜진 물자를 쓰지 않는 판에서는 그 물자가 유지되지 않는다(줄에 `쓰지 않음`).
   - 물자의 재고는 float 다 — 약 1,677만부터 낱개 단위가 반올림된다. 한 번에 쓰는 한도는 10억이다.
   - 물자 탭만 쓴 판도 게임이 "치트를 쓴 판"으로 표시하지 않는다(`vc-stock.md` 의 5 에서 본 대로).
   - 쓴 뒤 게임 화면의 재고 숫자가 언제 따라오는지(`vc-stock.md` 의 5 (c)에서 본 대로 — 바로인지, 패널을 다시 열어야 하는지).
   - ToyBox 창이 처음 자리(40,60)에서는 게임의 속도 목록을 덮는다. 창을 옮기면 그 자리가 저장된다.
   - 재고가 0 일 때의 게임(`vc-stock.md` 의 9 에서 본 대로), 열두째 칸(본 대로), DLC 의 판에서는 보지 않았다는 것.
   - "물자 탭 · 최소 유지는 아직 없다" · "물자의 세 단추는 아직 내장 치트다"(계획 (나)가 적은 줄)를 지운다.
5. "구조"의 표: `products`(재고 칸 → 물자 이름. 빌드할 때 번역 표에서)를 더하고, `keeper`(요청의 대기열 **과 최소 유지**) · `values`(물자 수량의 표기, 한도 밖의 값) · `locate`(정렬 · 겹침의 대조) · `features`(19줄) · `settings`(`keep.*`) · `ui`(물자 탭, 유지의 칸, 상태 줄) · `input`(타이머를 빈 메시지로 깨운다)의 줄을 고친다. 설정 파일의 줄 표에 `keep.treasury` · `keep.treasury.value` · `keep.stock.<칸>` · `keep.stock.<칸>.value` 를 더한다. 로그의 표에 더한다: `값 쓰기: 석유 2.5 M -> 3.5 M` · `유지 켬: 석유 5000000` · `유지 켬: 국고 20000 (백만 달러)` · `유지 끔: 석유` · `유지: 석유 2.5 M -> 5.0 M`(항목마다 이번 실행의 첫 번째만. 설정을 고치면 다시 한 번) · `값을 쓸 수 없습니다 (세계 자료 포인터: 찾은 주소가 … 의 자리와 겹칩니다)`. `옛 방식 … 22개` 를 `19개` 로.
6. "확인한 것": 새 표 둘 — **"3단계 1 (다) — 물자 탭"**(`vc-stock.md` 에서. 번호 VC-1 … VC-10. 칸과 이름의 대응 표를 그대로 싣는다)과 **"3단계 1 (다) — 최소 유지"**(`vd-keep.md` 에서. 번호 VD-1 … VD-14). 칸은 VB 표와 같다(# · 한 것 · 본 것 · 근거 화면). 설계서의 V 번호와의 대응을 표 아래에 적는다(VC-5 = V5, VC-6 = V6, VC-7 · 8 = V7, VD-3 · 6 = V8, VD-5 = V9, VD-8 = V10, VD-9 · 11 = V1, VD-12 = V11, VD-6 = V13). 보지 못한 것을 따로 적는다. 묶음 1 의 V0 ~ V14 가운데 어느 것을 어디서 봤는지 한 줄씩의 표로 마무리한다(V0 — (가), V1 의 일부 · V2 ~ V4 · V12 · V14 — (나), 나머지 — (다)).
7. "문제가 생기면": "유지를 켠 적이 없는데 값이 올라간다 / 유지를 끄고 싶다" — 상태 줄을 보고, 돈 · 물자 탭에서 체크를 끈다. 창을 열 수 없으면 게임을 끄고 `%APPDATA%\SR2030ToyBox\toybox.ini` 의 `keep.` 줄을 지운다(모르는 줄 · 없는 줄은 꺼짐이다). `SRTOYBOX_WRITE=0` 이면 유지도 쉰다. 돈 · 물자 탭에 `이 게임 판에서는 쓸 수 없습니다 (… 겹칩니다)` 가 보일 때 할 일(`uv run srkit locate` → [11](11-game-internals.md))을 적는다.
8. "다음 단계"의 표: 묶음 1 의 줄을 "(가) · (나) · (다) 완료 — 2026-10-10"로 고치고, 다음이 묶음 2(그 밖의 값 쓰기 — 지식 순위, 세계 시장 여론, 관계 최고 · 중립)임을 적는다.

- [ ] **Step 3: `docs/11-game-internals.md` · `docs/05-game-systems.md`**

`docs/11`:
1. "새 찾기 — 값을 읽고 쓰는 자리" 절에 더한다: 읽어 낸 값의 대조에 정렬(세계 자료 포인터와 국고 칸은 8 의 배수, 표의 첫 칸은 4 의 배수)과 두 묶음의 겹침(`locate_fits` — 세계 자료 포인터가 상태 전역 일곱과 겹치면 값 묶음을 버린다. 게임이 뜰 때와 `srkit locate` 가 같은 대조를 한다). build 21347933 의 값이 그 대조를 지난다는 것.
2. 재고 칸의 표에 **칸과 물자의 대응**을 싣는다: 칸 0 ~ 10 = 농산물 · 고무 · 목재 · 석유 · 석탄 · 금속 광석 · 우라늄 · 전력 · 소비재 · 산업재 · 군수품(`LOCALIZE|productsl|0` ~ `|10` 의 순서). 근거는 `vc-stock.md` 의 5 — 게임 화면에서 오른 것을 본 물자는 [확인: 게임], peek 의 칸만 본 물자는 [확인: 실행]으로 나눠 적는다. 열두째 칸(칸 11)은 본 대로(독일 · 샌드박스 2030 에서 쓰지 않는 칸. 같은 목록의 11 은 "전체"다).
3. "보지 않은 것"에서 이 계획이 본 것을 지우고(재고 칸에 쓴 값, 칸과 이름의 대응, 열두째 칸, 재고가 0 일 때 — 본 만큼만), 남은 것을 적는다: DLC 의 판에서의 물자 구성, 날짜를 넘기는 계산과 쓰기가 겹치는지(본 만큼만), 다른 빌드.

`docs/05`: "물자" 절(82줄 근처)의 물자 이름을 번역 표의 이름으로 맞춘다(광석 → 금속 광석, 공업재 → 산업재 — 다른 곳에 같은 말이 있으면 함께). 그 절에 더한다: "재고는 지역 객체 안에 물자마다 float 한 칸씩, 열두 칸이 있다(build 21347933 — [11](11-game-internals.md)). 앞의 열하나가 위의 물자이고(그 순서) 열두째는 이 게임에서 쓰지 않는다(본 대로). ToyBox 의 물자 탭이 이 칸을 직접 고친다([10](10-toybox.md))." 그리고 "내장 치트: 재고는 치트로 충분하다"(102줄 근처)를 "ToyBox 의 물자 탭이 물자마다 고친다 — 내장 치트 없이"로 고친다.

- [ ] **Step 4: `docs/09` · `README.md` · `CLAUDE.md` · 설계서**

- `docs/09-cheat-mod-plan.md`: 로드맵의 3단계 줄에 묶음 1 의 완료와 날짜. "물자"의 표(`cheat products` · `branson` · `bezos` 가 "그대로 쓴다"인 곳)에 "ToyBox 의 물자 탭은 3단계 1 (다)부터 이 치트를 쓰지 않고 재고 칸에 직접 쓴다([10](10-toybox.md))"를 덧붙인다. 치트 자체의 사실(07 의 검증)은 그대로 둔다.
- `README.md`: 현재 상태의 3단계 줄을 고친다(돈 · 물자 탭과 최소 유지가 내장 치트 없이 동작한다. 남은 기능 19개).
- `CLAUDE.md`:
  - "명령"의 `gamedrive.py peek` 줄에 `peek <지역 번호>`(플레이어가 아닌 지역의 국고 · 재고)를 더한다.
  - 게임 안 확인의 줄들에 더한다: "**ToyBox 의 최소 유지는 저장되는 설정이다.** 검증용 게임은 반드시 `SRTOYBOX_HOME` 을 임시 폴더로 돌려 띄우고, Steam 으로 띄운 게임(실제 설정)에서는 유지를 켜지 않는다 — 켠 채로 남으면 사용자의 판에 적용된다."
  - "지켜야 할 것"의 "ToyBox 가 게임의 메모리에 쓰는 곳은 …" 줄은 그대로 맞다(최소 유지도 같은 칸에 쓴다) — "단추와 최소 유지가 쓴다"를 덧붙인다.
- 설계서(`docs/superpowers/specs/2026-10-09-toybox-stage3-1-design.md`)의 끝에 절 **"보완 내역 (2026-10-10, 계획 (다)를 쓰고 실행하며)"** 를 더한다: 이 계획의 "설계서와 달라진 곳"을 그대로 옮기고, [계획 (다)](../plans/2026-10-10-toybox-stage3-1c-stock-keep.md)를 가리킨다. "아직 보지 않은 것"의 2 · 3 · 4(칸과 이름, 열두째 칸, 재고가 0 일 때)를 본 대로 적는다. 완료 기준 여섯 가지를 하나씩 짚어, 채운 것과 남은 것(보지 못한 V 가 있으면 그것)을 적는다. 최종 검토가 남긴 것(미룬 Minor)이 있으면 적는다.

- [ ] **Step 5: 링크와 사실을 대조하고 커밋 · PR · 머지**

```bash
cd /e/SR2030ToyBox && uv run python "<스크래치>/linkcheck.py" . 2>&1 | tail -5; grep -n "22개\|22 개\|branson\|공업재" docs/10-toybox.md docs/05-game-systems.md README.md CLAUDE.md | head -20; uv run pytest -q 2>&1 | tail -2
```

Expected: 계획 문서 밖의 깨진 상대 링크가 없다(`linkcheck.py` 는 앞 계획에서 쓴 스크래치의 스크립트다 — 없으면 `docs/` · `README.md` · `CLAUDE.md` 의 `](…)` 링크가 가리키는 파일이 있는지 보는 열 줄짜리를 다시 쓴다. 계획 문서 안에 인용된 링크는 세지 않는다). 남은 `22개` · `branson` 은 지난 단계의 기록(확인한 것의 표, 07 을 가리키는 줄)뿐이다. 테스트는 Task 9 의 끝과 같은 수가 통과한다(문서만 바꿨다).

```bash
cd /e/SR2030ToyBox && git add docs README.md CLAUDE.md && git commit -q -F - <<'EOF'
docs: ToyBox 3단계 1 (다) — 물자 탭과 최소 유지(내장 치트 없이), 칸과 물자의 대응, 게임에서 본 것

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push -u origin docs/toybox-values-stock-keep
```

스크래치에 `pr-docs-stock-keep.md` 를 쓰고(무엇을 고쳤나의 표, 게임에서 본 것과 보지 못한 것, `uv run pytest` 결과), PR 을 올려 머지한다:

```bash
gh pr create --repo game-mod-project/SR2030Toybox --base develop --head docs/toybox-values-stock-keep --title "docs: ToyBox 3단계 1 (다) — 물자 탭과 최소 유지" --body-file "<스크래치>/pr-docs-stock-keep.md"
```

```bash
gh pr merge <번호> --repo game-mod-project/SR2030Toybox --merge && cd /e/SR2030ToyBox && git switch develop && git pull --ff-only origin develop && git log --oneline -3
```

---

## 끝난 뒤의 상태

- `develop` 에 PR 넷(이 계획 문서 · 물자 탭 · 최소 유지 · 문서)이 들어가 있다. `uv run pytest` 336개 통과(최종 검토에서 테스트가 더해졌으면 그만큼 더). 게임 폴더에는 최종 빌드의 `srtoybox.dll` 이 있고 그 밖의 게임 파일은 그대로다.
- 사용자의 `%APPDATA%\SR2030ToyBox` 설정은 그대로다 — 최소 유지는 모두 꺼져 있다(줄이 없다 = 꺼짐). 새 빌드가 처음 설정을 저장할 때(사용자가 창에서 무언가를 바꿀 때) `keep.` 스물여섯 줄이 0 으로 생기고 `products=…` 줄이 없어진다.
- **묶음 1(기반 + 돈 · 물자)이 끝난다.** 설계서의 완료 기준 여섯을 Task 10 에서 하나씩 짚는다. 내장 치트로 도는 기능은 19개가 남는다(연구 3, 인구 · 여론 3, 외교 · 영토 8, 부대 3, 화면 · 진행 2).
- **다음**: 묶음 2(그 밖의 값 쓰기 — 지식 순위, 세계 시장 여론, 관계 최고 · 중립)의 설계. 사용자가 처음에 청한 것 가운데 남은 것은 묶음 3(개별 연구 미/완료, 일부 연구가 완료되지 않는 원인), 5(부대 목록에서 골라 생성 · 보급 · 경험), 7(배율 — 국고 세금/지출, 국방비, 물자별 생산 · 소비, 연구 속도)이다.
- **이 계획이 미룬 것**: 계획 (나)의 최종 검토가 남긴 넷(요청을 받지 못한 까닭의 구분, 찾기가 실패했을 때 맞지 않은 서명을 적지 않는 것, `cheat_ranges` 가 `call rel32` 만 세는 것, `마지막으로 쓴 값` 이 판을 넘어 남는 것), 창의 첫 자리, 물자 탭의 재고 칸을 오른쪽으로 맞추는 것.
