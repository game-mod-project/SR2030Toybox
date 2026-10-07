# 01. 게임 구성

Supreme Ruler 2030 설치본을 직접 조사한 결과다. 조사 기준: Steam appid `2093410`, build `21347933`
(설치 스크립트의 버전 코드 `S12-00-00`), 64비트 / DirectX 11.

표기: **[확인]** 파일·코드에서 직접 확인, **[추정]** 정황으로 판단(게임 안에서 미검증).

## 설치 폴더

`E:\SteamLibrary\steamapps\common\Supreme Ruler 2030` (약 2.0GB)

| 경로 | 파일 수 | 내용 |
|---|---|---|
| `SupremeRuler2030.exe` | – | 게임 본체. `MapEditor.exe` 는 맵 에디터 |
| `Localize\` | 455 | 언어별 텍스트·글꼴·UI 그림. [03 문서](03-localization-internals.md) 참고 |
| `INI\` | 12 | 엔진 표: UI 설정, 단축키, 명령, 스타일, 비트맵 좌표, AI 매개변수 |
| `HAPS\` | 1,190 | GUI 화면 정의(`.HAPX`, 텍스트 형식) |
| `Maps\` | 432 | 지도와 기본 데이터. `Maps\DATA\DEFAULT.*` 가 게임 전체의 기준 데이터 |
| `Sandbox\` `Scenario\` `Campaign\` `Tutorials\` | 12 / 39 / 16 / 14 | 게임 모드별 시나리오 정의와 전용 데이터 |
| `Common\` | 9 | 여러 시나리오가 공유하는 이벤트 CSV (지도자, NATO, 우크라이나 전쟁 등) |
| `Cache\` | 7 | 시나리오별 미리 계산된 캐시(`.SAV`, 각 약 12MB) |
| `Graphics\` | 6,933 | UI 스킨(`Skin0`, `Skin5`), 3D 모델(`Meshes\*.cmo`), 인물 사진, 국기, 스플래시, 영상 |
| `Sounds\` | 191 | `Military` `Music` `UI` (wav, xwma) |
| `Misc\` | 2 | 기술 트리 도표(PNG, Visio) |

실행 파일이 직접 임포트하는 DLL: `steam_api64`, `discord_game_sdk`(게임 폴더), `WINMM`, `WS2_32`, `WTSAPI32`,
`WININET`, `KERNEL32`, `USER32`, `GDI32`, `ADVAPI32`, `SHELL32`, `ole32`, `d3d11`, `MF`, `MFPlat`. **[확인]**

## 데이터 파일 형식

거의 모든 데이터가 **CP1252 텍스트**이고 같은 문법을 쓴다. **[확인]**

```
// 주석
&&SECTION, 0          ← 섹션 시작 (이름으로 내용 종류가 정해진다)
id, "문자열", 1.000    ← 쉼표로 나눈 행. 문자열은 큰따옴표
&&END
#include "파일", "경로\"   ← 다른 파일 포함. 세 번째 인자 Y 는 "현지화 폴더에서 찾기"
#ifset 0x02 … #endifset  ← 로딩 단계별 조건
```

| 파일 | 섹션 | 역할 |
|---|---|---|
| `*.scenario` | `MAP` `SAV` `GMC` + `#include` | 시나리오 정의: 어떤 데이터를 어떤 단계에 읽을지, 시작 날짜·난이도 등 게임 설정 |
| `Maps\*.MAPX` / `*.OOF` | – / `OOF` | 육각 지도 / 지도 위 개체(도시·시설) |
| `Maps\*.CVP` | `CVP` `GROUPING` `REGIONTECHS` `REGIONUNITDESIGNS` `REGIONPRODUCTS` … | 지역(국가) 데이터 |
| `Maps\*.REGIONINCL` | `REGIONINCL` | 시나리오에 포함할 지역 |
| `Maps\ORBATS\*.OOB` + 지역별 csv | – | 전투서열(부대 배치) |
| `Maps\DATA\DEFAULT.UNIT` | `UNITS` | 장비(유닛·시설) 데이터. 3.8MB |
| `Maps\DATA\DEFAULT.TTRX` | `TTR` | 기술 트리 |
| `Maps\DATA\DEFAULT.TERX` | `TERRAIN` | 지형 |
| `Maps\DATA\DEFAULT.PPLX` | `PEOPLE` | 인물(지도자·각료) |
| `Maps\DATA\DEFAULT.NEWSITEMS` | `NEWSITEMS` | 뉴스·이메일 항목 정의(문구는 `Localize` 에 있음) |
| `Maps\DATA\DEFAULT.NAME` | `NAMESET` | 이름 목록 |
| `Maps\DATA\*.WMDATA` | `WMDATA` `WMPRODDATA` `GOVTYPE` | 세계 시장·정부 형태 |
| `Common\*.csv`, `*_events.csv` | `SEVENTS` | 이벤트 스크립트 |
| `INI\UISettings.csv` | `UISETTINGS` | **언어 목록**(`langdirs`, `langs`), GUI 배율 등 |
| `INI\Styles.csv` / `Bitmaps.csv` / `Menumap.csv` / `hotkeys.csv` / `orders.csv` | `OBSTYLES` / `BITMAPS` / `MENUMAP` / `HOTKEYS` / `ORDERS` | UI 스타일, 스프라이트 좌표, 메뉴, 단축키, 명령 |
| `HAPS\*.HAPX` | `HAPS` `HAPOB` | GUI 화면과 그 안의 개체(위치, 스타일, 툴팁 키) |
| `Graphics\Meshes\DEFAULT.PICNUMS` | `PICNUMS` | 그림 번호 ↔ 3D 모델 연결 |

대부분 파일 머리에 `Created by the Asset Manager` 가 찍혀 있다 — 개발사 도구(Asset Manager)의 산출물이다.

## 시나리오 로딩

`Sandbox\World2030.scenario` 예. `#ifset` 값은 로딩 단계다(파일 머리 주석 그대로): **[확인]**

| 값 | 단계 | 읽는 것 |
|---|---|---|
| `0x01` | CVP 로드 | `W2030.CVP`, `REGIONINCL`, `theatres.csv` |
| `0x02` | 나머지 원본 로드(캐시 생성 시) | `DEFAULT.UNIT/PPLX/TTRX/TERX`, `WMDATA`, 지도, OOB … |
| `0x04` | 캐시 로드 | `&&SAV savfile "W2030"` → `Cache\W2030.SAV`, 공통 이벤트 |
| 조건 없음 | 항상 | 시나리오 지역 설정 csv, `LocalText-Regions.csv`(현지화) |

- `Cache\*.SAV` 는 원본 데이터로 미리 만든 결과다. **원본 데이터(`DEFAULT.UNIT`, `*.CVP`)를 고치는 모드는 캐시를 다시 만들어야 반영된다.**
  로비의 "모드용 캐시 재생성" 옵션으로 만들고, 그때 게임이 `Cache\` 의 파일을 고쳐 쓴다. 시나리오 파일의 `&&GMC` 와 파일 끝에 덧붙인
  `&&CVP` · `&&UNITS` 블록은 캐시와 무관하게 반영된다. [확인: 게임 12.1.1360 / build 21347933 — [06](06-data-reference.md)의 "로딩 단계와 캐시"]
- 언어 추가는 캐시와 무관하다. [확인: 한글화 모드는 `Cache\` 의 파일을 하나도 건드리지 않고 언어를 더했고(설치 내역에 캐시 파일이 없다),
  그 상태로 시작한 게임의 문구와 지역 이름이 한글로 나온다 — [04](04-korean-localization.md)] 현지화 텍스트를 캐시 **뒤에** 읽는다는 순서는
  시나리오 파일의 `#ifset` 구조로 본 것이고 따로 실험하지 않았다. [추정] 캐시에 구워져 언어를 바꿔도 안 바뀌는 글이 있는지도 가리지 않았다.
- `SAMPLE.scenario` 는 같은 이름의 폴더 `SAMPLE\` 를 먼저 뒤진다(시나리오 전용 덮어쓰기). 예: `Scenario\Arena 6A\Localize\LOCALEN\…`.

## 실행 옵션·설정 위치 [확인: 실행 파일 문자열·코드]

- 명령줄: `-window` `-fullscreen` `-logon` `-tcheck`(번역 검사, `LOG-TRANS-CHECK.log` 기록) `-mapedit` `-haps`
  `-host` `-client` `-player` `-port` `-maxplayers` `-mpsynccheck`
- 레지스트리 `Software\BattleGoat\Supreme Ruler 2030`: `HKLM` 을 먼저 읽고 `HKCU` 값으로 덮어쓴다. 쓰기는 `HKCU`.
  값: `Language File`(기본 `LOCALEN`), `Player Name`, `Options File`, `SaveGame Path`, `HAPS Directory` 등.
  게임을 한 번도 실행하지 않은 상태에서는 키가 없다(이 PC 가 그렇다).
- 사용자 폴더: `문서\My Games\Supreme Ruler 2030\Savegame\` — 저장과 로그(`LOG-*.log`). [확인: 실행 중 메모리의 경로]
  이 PC 의 문서 폴더는 `%USERPROFILE%\OneDrive\문서` 이고, Windows "제어된 폴더 액세스"가 게임의 쓰기를 막고 있다
  ([04 문서](04-korean-localization.md)).
- 첫 실행 때 설정 안내 화면이 뜨고(`setupoptionscomplete`), 화면·창 모드 설정도 레지스트리에 저장된다(`UseWindowed`, `Gamerezx/y`).
- Steam Workshop 사용(`STEAMUGC_INTERFACE_VERSION020`), 메인 메뉴에 Workshop 목록(`[MODS] 제목` / `[MAPS] 제목`).
