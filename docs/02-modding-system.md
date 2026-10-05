# 02. 모드 구성 방식

출처는 공식 위키(아래 링크)와 설치본 조사다. 위키는 Supreme Ruler Ultimate 기준으로 쓰였고 2030 도
같은 구조를 쓴다(2030 Workshop 에 `Mods` 태그 항목 다수, 실행 파일에 `MODS`/`MAPS` 표시 코드 존재).

## 두 가지 모드 유형

| | MAPS | MODS |
|---|---|---|
| 용도 | 새 시나리오 | 기존 게임 요소의 교체·추가 |
| 구성 | `이름.scenario` + 같은 이름의 폴더 `이름\` | 게임 설치 폴더와 **같은 폴더 구조** |
| 넣을 수 있는 것 | 시나리오 전용 데이터, `Maps\` `Graphics\` 등 덮어쓰기 | 무엇이든: `Localize\` `INI\` `Graphics\` `Sounds\` `HAPS\` `Maps\` `Sandbox\…` `Common\` |
| 적용 시점 | 그 시나리오를 시작할 때 | 구독하면 항상(켜고 끄면 게임 재시작) |
| 제약 | 멀티플레이 불가, 글꼴·커서 같은 엔진 자원은 바꿀 수 없음 | 다른 모드와 파일이 겹치면 충돌 |

**한글화는 MODS 유형이다**(`Localize\`, `INI\` 를 바꾼다).

## 파일 로드 순서 (먼저 찾은 것 사용)

1. MAPS 시나리오면: 그 MAPS 의 Workshop 경로
2. 아니면: 구독한 각 MODS 경로에서 시나리오 전용 경로
3. 기본 설치본의 시나리오 전용 경로
4. 기본 설치본

예) Sandbox `SR1940` 이 `Default.WMData` 를 찾을 때:
`<모드>\Sandbox\SR1940\MAPS\Default.WMData` → `Sandbox\SR1940\MAPS\Default.WMData` → `MAPS\Default.WMData`

Workshop 항목은 Steam 이 `steamapps\workshop\content\2093410\<항목ID>\` 에 내려받는다(이 PC 에는 아직 구독 항목이 없다).
스플래시 화면은 Workshop 데이터가 오기 전에 뜨므로 모드로 바꿀 수 없다.

## 공식 도구

Steam 라이브러리의 **도구** 항목에서 설치한다: Map Editor, Scenario Creator, Asset Manager, **Workshop Uploader**.

업로드 절차(Workshop Uploader): 유형(MAPS/MODS) 선택 → MAPS 는 `.scenario` 파일, MODS 는 **루트 폴더** 지정 →
제목·공개 범위·설명·미리보기 그림(1MB 미만)·태그·언어 입력 → 업로드. 갱신은 구독한 항목 폴더를 다시 가져오면
`ModInfo.meta` 를 인식한다.

## 이 저장소에서의 작업 방식

```
mods/<모드>/        모드 원본(사람이 고치는 것)
build/<모드>/       게임 루트 구조로 조립한 산출물 = Workshop Uploader 에 지정할 MODS 루트 폴더
```

- 손으로 만든 파일만으로 된 단순 모드는 `mods/_template` 를 복사해 `files\` 아래에 게임 루트 구조로 넣는다.
- 로컬 시험: `uv run srkit deploy <모드> --apply` 가 `build/<모드>` 를 게임 폴더에 복사한다. 덮어쓴 원본은
  `build/.deploy/<모드>/backup` 에 보관하고 `undeploy` 로 되돌린다. (Workshop 을 거치지 않는 직접 설치)
- **DLL 과 실행 파일은 게임의 파일 로더를 거치지 않으므로 Workshop 으로 배포할 수 없다.**
  한글화의 디코딩 훅 DLL 은 사용자가 게임 폴더에 직접 넣어야 한다([04 문서](04-korean-localization.md)).

## 출처

- [Steam Workshop — Official Supreme Ruler Wiki](https://supremeruler.fandom.com/wiki/Steam_Workshop)
- [Workshop Uploader — Official Supreme Ruler Wiki](https://supremeruler.fandom.com/wiki/Workshop_Uploader)
- [Modding Supreme Ruler — Official Supreme Ruler Wiki](https://supremeruler.fandom.com/wiki/Modding_Supreme_Ruler)
- [Special Characters — Official Supreme Ruler Wiki](https://supremeruler.fandom.com/wiki/Special_Characters)
- [Supreme Ruler 2030 Steam Workshop](https://steamcommunity.com/app/2093410/workshop/)
