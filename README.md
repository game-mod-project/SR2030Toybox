# SR2030 ToyBox

Supreme Ruler 2030 모드 제작 작업 공간. 첫 과제는 **한글화 모드**다.

- 게임: `E:\SteamLibrary\steamapps\common\Supreme Ruler 2030` (Steam appid 2093410) — `srkit.toml` 에서 바꾼다
- 도구: `srkit` (Python, [uv](https://docs.astral.sh/uv/) 로 실행) + 디코딩 훅 DLL (C, MSVC Build Tools)

## 현재 상태

한글화 도구 체인이 갖춰졌고, **게임 안에서 한글 표시·줄바꿈·언어 등록이 동작하는 것을 확인했다**(2026-10-06, 게임 12.1.1360).
모드 파일은 게임 폴더에 설치되어 있고 게임 언어도 한국어로 바꿔 두었다(2026-10-06. Steam 으로 띄운 게임의 메뉴·옵션 화면이
한글로 나오는 것까지 확인). 영어로 되돌리려면 게임 옵션 → 파일 → 게임 언어 → `English`.
다른 PC 에 설치할 때는 파일을 넣은 뒤 옵션 → FILES → Game Language → `Korean` 을 한 번 골라야 한다([docs/04](docs/04-korean-localization.md)).
번역은 기계 번역 초안 32,869 / 33,412 단위(98.4%, 지도의 도시 이름 9,999개 포함)이고 사람 검수는 아직 0 이다.
남은 일과 확인하지 못한 항목은 [docs/04](docs/04-korean-localization.md).

둘째 과제인 **치트·모드 조사**도 마쳤다(2026-10-06, 게임 12.1.1360). 게임에 든 내장 치트 89개를 게임에서 넣어 봤고(효과 45개),
돈·자원·연구·국가 관계·부대·생산·인구는 내장 치트로 된다는 것을 확인했다 — 넣는 법과 결과는 [docs/07](docs/07-cheats.md).
내장 치트가 없는 GDP 와 장비 수치는 시나리오 파일 끝에 블록을 덧붙이는 방법으로 바뀌는 것을 확인했고(장비는 비용 열 하나로 확인했다. 공격·방어 같은 다른 열은 아직 추정이다), 그 방법을 쓰는 모드는 아직 만들지 않았다.
무엇을 만들고 무엇을 만들지 않는지, 게임 업데이트로 치트가 사라질 때의 대비는 [docs/09](docs/09-cheat-mod-plan.md).

셋째로 **ToyBox**(게임 안 모드 설정 창)를 2단계까지 만들었다(2026-10-07). `Ctrl+Shift+T` 로 여는 창에서 내장 치트를 실행한다(2단계에서 25개. 지금은 13개 — 국고 · 물자, 값만 고치는 단추 넷, 연구 탭의 단추 둘은 3단계에서 내장 치트를 떠났다) —
플레이어 국가에만 닿는 것과, 창이나 지도에서 고른 나라 하나에 닿는 9개(지지율 · 관계 · 동맹 · 병합 등). ToyBox 가 게임의 상태를 읽어
게임 밖에서는 단추를 끄고, 치트는 게임의 명령 처리 함수에 직접 넘긴다. 한글화 모드가 설치되어 있어야 동작한다 — 쓰는 법과 한계는
[docs/10](docs/10-toybox.md), 게임의 안쪽은 [docs/11](docs/11-game-internals.md).
3단계(진행 중, 2026-10-09 ~)에서는 모든 기능을 게임의 내장 치트에서 떼어 낸다 — 게임 상태 읽기가 치트와 무관한 코드의 서명으로 주소를 찾고, 돈 탭이 내장 치트 없이 국고를 직접 고친다(더하기 · 빼기 · 이 값으로). 물자 탭이 물자마다 재고를 고치고(−1억 · −100만 · 0 · +100만 · +1억, "모든 물자"),
국고와 물자마다 **최소 유지**(정해 둔 값보다 적어지면 올린다 — 창을 닫아도, 게임을 다시 켜도 계속된다)를 걸 수 있다. 첫 묶음(기반 + 돈 · 물자)이 끝났고(2026-10-10),
둘째 묶음(그 밖의 값 쓰기)도 끝났다(2026-10-10): "지식 순위 올리기" · "세계 시장 여론 최고" · "관계 최고" · "관계 중립"이 내장 치트 없이 그 칸에 직접 쓴다.
셋째 묶음(연구)은 (가)가 끝났다(2026-10-10): 연구 탭의 "대기열의 연구 즉시 완료" · "기술 수준 N 이하 전부 보유"가 내장 치트 없이 기술 · 부대 설계의 보유를 직접 쓴다 —
**대기열에 건 부대 설계도 끝나고**(내장 치트는 기술만 끝냈다), 모든 나라가 함께 쓰는 연구 기간을 건드리지 않는다. (나) — 연구의 목록(기술 · 부대 설계를 걸러 보고 골라서 완료 · 미완료로) — 도 끝났다(게임에서 R6 ~ R11 을 봤다).
넷째 묶음은 첫 조각(2026-10-10): "인구 +100만" · "내 나라 지지율 100%"가 내장 치트 없이 값을 직접 쓴다(내장 치트의 인구는 첫 자정에 되돌아갔다 — ToyBox 는 인구의 풀 칸에도 써서 남게 한다).
"식민지화"는 게임 자신의 함수를 직접 부른다(게임에서 봤다). "전쟁 붙이기"도 그렇게 옮겼다(게임에서 봤다 — 지도에서 고른 나라가 선포하는 쪽이다). 나머지 9개 기능(외교 · 영토 · 부대 · 화면)은 옮길 때까지 내장 치트로 돈다.

## 빠른 시작

```
uv run srkit info                    # 설정과 게임 설치 상태
uv run pytest                        # 테스트
uv run srkit extract                 # 영문 원문 → 번역 테이블 (기존 번역 유지)
uv run srkit stats                   # 번역 진행률
uv run srkit check                   # 번역문 검증
uv run srkit mt-export <테이블>      # 기계 번역용 청크 내보내기 → mt-check → mt-import
uv run srkit hook-build              # 디코딩 훅 DLL 빌드
uv run srkit toybox-build            # ToyBox DLL(게임 안 모드 설정 창) 빌드 → build/toybox/
uv run srkit locate                  # 설치된 게임에서 ToyBox 가 쓰는 주소를 찾아 보고(게임 업데이트 뒤 점검)
uv run srkit sig-mine <RVA>          # (개발용) ToyBox 가 주소를 찾는 서명의 후보 뽑기 — 치트 함수 밖의 코드에서
uv run srkit build                   # build/korean/ 에 한글화 모드 생성
uv run srkit deploy korean           # 설치 미리보기 (--apply 로 실제 설치)
uv run srkit undeploy korean         # 제거 미리보기 (--apply 로 실제 제거·복원)
uv run srkit font-preview <spritefont> "<문자열>" <out.png>
uv run srkit tcheck-import           # 게임의 번역 검사 로그에서 빠진 GUI 문구를 번역 테이블에 추가
uv run srkit inventory               # 게임 데이터의 섹션·키·열 목록 → build/inventory/*.csv (치트·모드 조사용)
uv run srkit probe <이름> <파일> <바꿀 문자열> <새 문자열>   # 값 한 곳만 바꾼 시험 모드 → build/probe-<이름>/
uv run srkit cheats-check            # 게임의 내장 치트가 docs/07 과 같은지 대조 (게임 업데이트 뒤에 돌린다)
uv run python scripts/gamedrive.py start|steam|status|shot|click|move|key|show|stop   # 게임 실행(화면 밖에서)·창 캡처·입력 (검증용)
```

## 구조

```
docs/            리서치와 설계
  01-game-structure.md          게임 구성
  02-modding-system.md          모드 구성 방식 (MAPS/MODS, 로드 순서, Workshop)
  03-localization-internals.md  현지화 내부 구조 (파일 형식, 글꼴, 렌더 경로)
  04-korean-localization.md     한글화 설계, 검증 현황, 다음 단계
  05-game-systems.md            게임 구조: 12개 영역과 데이터의 대응
  06-data-reference.md          데이터 참조: 섹션·키·열, 캐시와 데이터 수정 (srkit inventory 산출물 기준)
  07-cheats.md                  내장 치트표 (게임에서 넣어 본 결과)
  08-workshop-survey.md         Workshop 기존 모드 조사
  09-cheat-mod-plan.md          치트/모드 제작 계획, 게임 업데이트 대비
  10-toybox.md                  ToyBox — 게임 안 모드 설정 창
  11-game-internals.md          게임의 안쪽 — ToyBox 가 읽고 부르는 것(주소 · 전역 · 찾는 법)
mods/
  _template/     새 모드 골격
  korean/        한글화 모드 원본 (번역 테이블, STYLE.md 번역 규칙, glossary.csv 용어집, sprites.toml 그림 글자)
  toybox/        ToyBox 설명 (모드의 파일은 DLL 하나다)
src/srkit/       도구
  srtext.py      게임 텍스트 형식의 무손실 파서
  srutf8.py      SR-UTF8 인코딩 (게임 엔진과 충돌하지 않는 UTF-8 변형)
  spritefont.py  DirectXTK spritefont 읽기·쓰기·글리프 추가
  korean.py      추출 / 검증 / 빌드
  mt.py          기계 번역 청크 내보내기·검증·병합
  sprites.py     그림 글자(메뉴·제목·버튼 스프라이트) 한글로 다시 그리기
  hook.py        훅 DLL 빌드
  deploy.py      게임 폴더 설치·제거
  inventory.py   게임 데이터의 섹션·키·열 목록 (읽기 전용)
  probe.py       값 한 곳만 바꾼 시험 모드 만들기 (데이터 수정이 게임에 반영되는지 확인용)
  cheats.py      내장 치트 목록을 문서와 대조 (게임 업데이트로 치트가 사라졌는지 감지)
  toybox.py      ToyBox DLL 빌드
  sigmine.py     ToyBox 의 서명 후보 뽑기 (개발용. 디스어셈블러 capstone)
native/srhook/   디코딩 훅 DLL 소스
native/srtoybox/ ToyBox DLL 소스 (C++)
native/third_party/imgui/  Dear ImGui (MIT)
scripts/         gamedrive.py — 게임 실행·창 캡처·입력 (게임 안 검증용)
tests/           자동 테스트 (일부는 게임 설치본·빌드된 DLL 이 있을 때만 실행)
build/           산출물 (git 제외)
```

## 주의

- `build/` 와 번역 테이블에는 게임 원문에서 나온 내용이 들어 있다. 저장소를 공개하기 전에 [docs/04](docs/04-korean-localization.md)의 "결정이 필요한 사항" 참고.
- `deploy --apply` 는 게임 설치 폴더를 바꾼다(추가한 파일·백업 내역은 `build/.deploy/` 에 기록).
- 한 게임 파일은 한 모드만 바꿀 수 있다. 설치된 다른 모드가 쥐고 있는 파일이 있으면 `deploy` 는 아무것도 설치하지 않고(미리보기에 "겹침"으로 나온다),
  `probe` 도 설치된 모드가 바꾼 파일로는 시험 모드를 만들지 않는다. 먼저 그 모드를 `undeploy --apply` 한다.
