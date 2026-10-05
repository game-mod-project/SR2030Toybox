# SR2030 ToyBox

Supreme Ruler 2030 모드 제작 작업 공간. 첫 과제는 **한글화 모드**다.

- 게임: `E:\SteamLibrary\steamapps\common\Supreme Ruler 2030` (Steam appid 2093410) — `srkit.toml` 에서 바꾼다
- 도구: `srkit` (Python, [uv](https://docs.astral.sh/uv/) 로 실행) + 디코딩 훅 DLL (C, MSVC Build Tools)

## 현재 상태

한글화 도구 체인이 갖춰졌고, **게임 안에서 한글 표시·줄바꿈·언어 등록이 동작하는 것을 확인했다**(2026-10-06, 게임 12.1.1360).
모드는 게임 폴더에 설치되어 있고 언어는 `LOCALKO` 로 지정되어 있다. 번역은 기계 번역 초안 22,865 / 23,413 단위(97.7%)이고
사람 검수는 아직 0 이다.
남은 일과 확인하지 못한 항목은 [docs/04](docs/04-korean-localization.md).

## 빠른 시작

```
uv run srkit info                    # 설정과 게임 설치 상태
uv run pytest                        # 테스트
uv run srkit extract                 # 영문 원문 → 번역 테이블 (기존 번역 유지)
uv run srkit stats                   # 번역 진행률
uv run srkit check                   # 번역문 검증
uv run srkit mt-export <테이블>      # 기계 번역용 청크 내보내기 → mt-check → mt-import
uv run srkit hook-build              # 디코딩 훅 DLL 빌드
uv run srkit build                   # build/korean/ 에 한글화 모드 생성
uv run srkit deploy korean           # 설치 미리보기 (--apply 로 실제 설치)
uv run srkit undeploy korean         # 제거 미리보기 (--apply 로 실제 제거·복원)
uv run srkit font-preview <spritefont> "<문자열>" <out.png>
uv run srkit tcheck-import           # 게임의 번역 검사 로그에서 빠진 GUI 문구를 번역 테이블에 추가
uv run python scripts/gamedrive.py start|status|shot|click|move|key|show|stop   # 게임 실행(화면 밖에서)·창 캡처·입력 (검증용)
```

## 구조

```
docs/            리서치와 설계
  01-game-structure.md          게임 구성
  02-modding-system.md          모드 구성 방식 (MAPS/MODS, 로드 순서, Workshop)
  03-localization-internals.md  현지화 내부 구조 (파일 형식, 글꼴, 렌더 경로)
  04-korean-localization.md     한글화 설계, 검증 현황, 다음 단계
mods/
  _template/     새 모드 골격
  korean/        한글화 모드 원본 (번역 테이블, STYLE.md 번역 규칙, glossary.csv 용어집, sprites.toml 그림 글자)
src/srkit/       도구
  srtext.py      게임 텍스트 형식의 무손실 파서
  srutf8.py      SR-UTF8 인코딩 (게임 엔진과 충돌하지 않는 UTF-8 변형)
  spritefont.py  DirectXTK spritefont 읽기·쓰기·글리프 추가
  korean.py      추출 / 검증 / 빌드
  mt.py          기계 번역 청크 내보내기·검증·병합
  sprites.py     그림 글자(메뉴·제목·버튼 스프라이트) 한글로 다시 그리기
  hook.py        훅 DLL 빌드
  deploy.py      게임 폴더 설치·제거
native/srhook/   디코딩 훅 DLL 소스
scripts/         gamedrive.py — 게임 실행·창 캡처·입력 (게임 안 검증용)
tests/           자동 테스트 (일부는 게임 설치본·빌드된 DLL 이 있을 때만 실행)
build/           산출물 (git 제외)
```

## 주의

- `build/` 와 번역 테이블에는 게임 원문에서 나온 내용이 들어 있다. 저장소를 공개하기 전에 [docs/04](docs/04-korean-localization.md)의 "결정이 필요한 사항" 참고.
- `deploy --apply` 는 게임 설치 폴더를 바꾼다(추가한 파일·백업 내역은 `build/.deploy/` 에 기록).
