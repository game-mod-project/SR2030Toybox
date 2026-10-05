# SR2030 ToyBox — 작업 규칙

Supreme Ruler 2030 모드 제작 저장소. 개요는 [README.md](README.md), 배경 지식은 `docs/` 를 먼저 읽는다.

## 명령

- 테스트: `uv run pytest` — 코드를 고치면 항상 실행한다. 게임 설치본이 없으면 일부가 건너뛰어진다.
- 한글화 빌드: `uv run srkit build` (글꼴 포함 약 14초). 훅 DLL 을 고쳤으면 `uv run srkit hook-build` 먼저.
- Python 은 시스템에 설치되어 있지 않다. 항상 `uv run` 으로 실행한다.
- 게임 안 확인: `uv run python scripts/gamedrive.py start` → `shot <png>` → `click X Y` → `stop`.
  게임 창만 캡처하고 게임 창에만 입력을 보낸다. `-window` 로 띄우면 창 모드·해상도가 레지스트리(`HKCU\Software\BattleGoat\Supreme Ruler 2030`)에 저장되므로 사용자의 설정을 바꾸지 않도록 끝나면 되돌린다.
- **게임 실행은 백그라운드로 한다**(사용자 지시): 게임을 띄우는 명령은 백그라운드 작업으로 돌리고 그동안 다른 일을 한다.
  `start` 는 창을 활성화하지 않고 다른 창 뒤에 띄운다(캡처·입력은 가려진 창에도 된다). 사용자에게 창을 앞으로 가져와 달라고 하지 않는다.
- 빠진 GUI 문구 찾기: `gamedrive.py start -window -tcheck` → (메인 메뉴가 뜨면) `uv run srkit tcheck-import` → `gamedrive.py stop`.
  게임은 시작할 때 검사 로그를 쓰고 평소처럼 계속 실행된다.

## 지켜야 할 것

- **게임 설치 폴더는 읽기 전용으로 다룬다.** 바꾸는 경로는 `srkit deploy/undeploy --apply` 뿐이고, 사용자가 요청했을 때만 실행한다.
- 게임 파일을 저장소에 복사해 커밋하지 않는다. 파생물은 `build/` (git 제외)에만 둔다.
- 게임 텍스트는 CP1252 다. 원본을 읽을 때 UTF-8 로 열지 않는다(`korean.decode_cp1252`).
- `srutf8.py` 와 `native/srhook/srdecode.c` 는 같은 규칙의 두 구현이다. 한쪽을 고치면 다른 쪽도 고치고 `tests/test_hook.py` 로 일치를 확인한다.
- 번역 테이블(`mods/korean/translation/*.csv`)은 UTF-8 BOM + LF. 손으로 고칠 때 `key`, `en` 열은 건드리지 않는다.
- 실행 파일 주소(RVA)는 게임 빌드마다 달라진다. 문서에 적을 때는 빌드 번호를 함께 적는다.
- 게임 안에서 확인하지 않은 동작을 "된다"고 쓰지 않는다. `docs/04` 의 검증 현황에 구분해 둔다.

## Git 브랜치 전략

`main` 은 보호 브랜치다. 직접 커밋·푸시하지 않는다.

1. `develop` 에서 `feat/*` · `fix/*` · `chore/*` · `docs/*` 브랜치를 만든다.
2. 작업 브랜치 → `develop` PR, CI 통과 후 merge commit 으로 머지.
3. 릴리스 때만 `develop` → `main` PR.

현재: 원격 저장소 없이 **로컬 커밋만** 한다(사용자 결정, 2026-10-06). PR 을 올릴 곳이 없으므로 작업 브랜치를 `develop` 에
`git merge --no-ff` 로 합치는 것이 PR 머지를 대신하고, 합치기 전에 `uv run pytest` 통과를 확인한다(CI 대신).
`main` 은 빈 초기 커밋에 머물며 릴리스 때만 `develop` 을 합친다. 원격 저장소를 만들지는 사용자가 정한다
(번역 테이블에 게임 원문이 들어 있어 공개 저장소는 피한다).
