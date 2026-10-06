# 03. 현지화 내부 구조

설치본 파일과 실행 파일 역분석으로 확인한 내용이다. 주소(RVA)는 build `21347933` 의 `SupremeRuler2030.exe` 기준이며
게임이 갱신되면 달라진다.

## 언어 선택

- 언어 = `Localize\` 아래 폴더 이름. 기본 제공: `LOCALEN` `LOCALDE` `LOCALES` `LOCALFR` `LOCALIT` `LOCALPT`.
- 현재 언어는 레지스트리 값 `Language File` (→ [01 문서](01-game-structure.md)). 게임은 `Localize\<값>\<파일>` 을 읽는다.
- 옵션 화면의 언어 목록은 `INI\UISettings.csv`:
  ```
  langdirs, "LOCALEN", "LOCALDE", "LOCALES", "LOCALFR", "LOCALIT", "LOCALPT", ""
  langs, "English", "Deutsch", "Español", "Français", "Italiano", "Portuguese", ""
  ```
  **목록은 앞의 6개만 보여 준다.** 7번째로 붙인 언어는 목록에 나오지 않아 고를 수 없다(그 언어가 현재 값일 때 항목 옆에
  이름이 표시될 뿐이다). 한국어판은 영어 다음(2번째)에 넣고, 포르투갈어가 목록에서 밀려난다. **[게임 안에서 확인]**
- 목록에서 언어를 고르면 **재시작 없이 바로** 그 언어로 바뀌고 `Language File` 이 저장된다. **[게임 안에서 확인]**
- 게임은 시작할 때 `HKLM\Software\BattleGoat\Supreme Ruler 2030`(64비트 보기, 없음)을 열어 보고 `HKCU\…` 에서 설정 65개를 읽은 뒤,
  읽은 값을 그대로 다시 쓴다. Steam 의 설치 스크립트(`installscript.vdf`)는 Steam 의 게임 언어에 맞춰
  `HKLM\Software\WOW6432Node\…\language file` 을 쓰지만(english → `LOCALEN` 등 4개 언어) 게임은 그 값을 읽지 않는다.
  **[확인: 진단용 훅 빌드의 레지스트리 접근 로그]**
- 해상도를 바꾸고 옵션을 나가면 게임이 Steam 을 거쳐 스스로 다시 시작한다(부모 프로세스가 `steam.exe`). 명령줄 `-window` 는
  창 크기를 1024x768 로 되돌려 저장한다. 인자 없이 띄우면 저장된 크기·창 모드를 쓴다. **[게임 안에서 확인]**

## 언어 폴더 구성 (`Localize\LOCALEN`)

| 파일 | 섹션 | 번역 단위 | 내용 |
|---|---|---|---|
| `LOCALTEXT.csv` | – | – | 색인: TTR·NEWSITEMS·GAME·START·TIPS 를 `#include` |
| `LocalText-NEWSITEMS.csv` | `NEWSITEMSTEXT` | 10,489 | 뉴스·이메일·보고 문구 (전체의 약 65%) |
| `LocalText-TTR.csv` | `TTRTEXT` | 3,248 | 기술 이름·설명 |
| `Variables.ini` | `LOCALIZE` | 2,687 | 목록형 UI 문구(선택지, 상태 이름, 날짜 형식) |
| `LocalText-Game.csv` | `ORDERSTEXT` `CABPRIORITIESTEXT` `RTREATIESTEXT` `TRAININGTEXT` `MENUMAPTEXT` `TECHEFFECTSTEXT` `TERRAINTEXT` `UNITSTEXT` | 1,589 | 명령, 내각 우선순위, 조약, 훈련, 메뉴, 기술 효과, 지형, 유닛 |
| `LocalText-Regions.csv` | `REGIONTEXT` | 760 | 지역 이름·소개(시나리오가 포함) |
| `LocalText-TIPS.csv` | `TIPOFDAYTEXT` | 127 | 툴팁·도움말 |
| `LocalText-START.csv` | `CONTINENTS` `FILETEXT` `THEATRESTEXT` | 118 | 대륙, 시나리오 제목·소개, 전구 |
| `CUSTOM\DEFAULT.GMT` | `SCENNAME` 외 | 9 | 사용자 시나리오 기본 문구 |
| `LocalText-GUI.csv` | `GUITRANS` | 4,099 | **영어 원문 → 번역문** 사전. 영어 폴더에는 없다 |
| `Fonts\` | | | `FONT1…39.spritefont`, `fontinfo.font`, `MakeSpriteFont.exe`, `ttf\` |
| `Graphics\Skin0\SRBITS5.png`, `Skin5\SRBITS5.png` | | | 글자가 그려진 UI 스프라이트(언어별) |

합계 약 **23,126 단위 / 154만 자 / 24만 단어**. `TipofDay.csv` 는 옛 형식으로 일부 언어에만 있어 번역 대상에서 뺐다.

시나리오 전용 문구는 시나리오 폴더 안에 따로 있다: `Scenario\<이름>\Localize\LOCALEN\*.csv`.

### 형식

- 인코딩 **CP1252**, 줄 끝 LF. 파일 머리에 `\n\r\n\r\n` 이 붙어 있다(그대로 보존해야 안전).
- 행: `키, "문자열", "문자열", 300.000, …` — 번역 대상은 큰따옴표 안. **문자열 안에 큰따옴표를 쓸 수 없다**(이스케이프 없음).
- `GUITRANS` 행: `"English", "Deutsch", ` — 키가 영어 원문 자체이고 대소문자를 구분한다(`"ACTIVATE"` 와 `"Activate"` 가 별개 행).
  화면 정의(`HAPS\*.HAPX`)·메뉴·단축키 등 코드와 데이터에 박힌 영어 문구가 이 사전을 거쳐 표시된다.
- `-tcheck` 옵션으로 실행하면 시작할 때 화면 정의에 나오는 문구를 모두 사전에 대 보고 결과를 저장 폴더의
  `LOG-TRANS-CHECK.log` 에 적는다. 그 뒤에는 평소처럼 메인 메뉴로 간다 [확인: 게임 실행]. 줄은 두 가지다.
  - `SRLOG: Missing GUI Translation, in <화면>, <문구>` — 대소문자까지 똑같은 키가 없다. **이 문구는 화면에 영어로 나온다.**
  - `SRLOG: Incorrect Case Translation, in <화면>, <문구>, (<사전의 키>, <번역>)` — 대소문자를 무시하고 찾았을 때 처음 걸린 키가
    문구와 다르다. 똑같은 키가 뒤에 따로 있어도 적히므로 **이 줄만 있으면 화면에는 번역이 제대로 나온다**
    (예: 사전에 `Run Game In Windowed Mode` 가 먼저, `Run Game in Windowed Mode` 가 나중에 있으면 이 줄이 적히지만 화면은 번역됨).
    똑같은 키가 없으면 Missing 과 함께 적히고 영어로 나온다(예: `Force Recache for Modding`).
  - 화면 이름 `BUILDERX`(화면 편집기)·`FONTTEST` 는 개발용이라 게임에 나오지 않는다.

### 문자열 안의 특수 토큰 (번역문에 그대로 남겨야 함)

| 토큰 | 뜻 |
|---|---|
| `¶` (0xB6) | 줄바꿈. 영어 텍스트에 2,600회 |
| `%s` `%d` `%.1f` … | printf 서식. 개수와 순서 유지 |
| `\LEF` `\CEN` `\RIG` | 정렬. **줄 맨 앞**에서만 인식 |
| `\NNN` (예: `\42 `) | 스타일(글꼴) 번호 전환. 백슬래시 뒤 3글자를 숫자로 읽으므로 뒤 공백도 토큰의 일부. 줄 맨 앞에서만 인식 **[추정: 번호의 의미]** |

`srkit check` 가 원문과 번역문의 토큰 구성이 같은지 검사한다.

## 글꼴

- 형식은 **DirectXTK SpriteFont** (`DXTKfont`). 글리프 표(문자, 텍스처 사각형, XOffset/YOffset/XAdvance) + 텍스처 한 장.
- 텍스처는 BC2 "CompressedMono"(픽셀당 4비트 알파). `srkit` 이 읽고 쓰며, 원본을 다시 쓰면 바이트가 일치한다(테스트로 확인).
- 글리프 225개: U+0020–U+00FF 와 U+FFFD. 기본 문자 `*`. **한글 없음.**
- `fontinfo.font` 가 슬롯 1–39 를 파일에 연결한다: `fontimage,FONT11,//,Manrope,11,0,11 M R` (이름, 원본 글꼴, 크기 pt, 스타일 0 보통/1 굵게/2 기울임).
- 실제 래스터 크기는 표기의 2배(예: 9pt → em 24px, 줄 간격 28.8). 게임이 GUI 배율에 맞춰 축소해 그린다.
- 원본 글리프는 모두 XOffset 에 약 em/6 의 왼쪽 여백이 더해져 있다(GDI+ 렌더링의 흔적). 새 글리프도 같은 만큼 밀어야 간격이 맞는다.
- 6개 언어의 글꼴 파일은 서로 같은 파일이다(해시 일치).

## 텍스트가 화면에 나오기까지 [확인: 디스어셈블]

```
파일(CP1252 바이트) ──▶ 메모리(char*) ──┬─▶ 줄바꿈 계산 ──▶ 그리기
                                        └─▶ 폭 측정
```

| 단계 | 위치 | 동작 |
|---|---|---|
| 그리기 | `0x6c570` → `SpriteFont::DrawString(wchar_t*)` `0x64ba0` | `MultiByteToWideChar(**1252**, …)` 로 변환. 버퍼 크기를 `strlen` 으로 넘기고 널은 스스로 붙인다 |
| 폭 측정 | `0x52f90` 등 → `SpriteFont::MeasureDrawBounds(char*)` `0x65430` → `0x65dd0` | `MultiByteToWideChar(**CP_UTF8**, …)`. 그리기와 코드페이지가 다르다 |
| 줄바꿈 계산 | `0xc0e706`, `0xc0eb97`, `0xc0efac` | **바이트 단위.** 한 바이트씩 폭을 재서 더하고, `0x0A` 또는 `0xB6` 이면 줄을 끊고, `0x20` 이하에서만 자동 줄바꿈 |
| 글리프 순회 | `0x64e21`, `0x65f30`, `0x6617a` (DirectXTK `ForEachGlyph` 개조판) | `wchar` 가 `\n` 또는 U+00B6 이면 줄바꿈 |

원본 게임에서도 악센트 문자는 측정(UTF-8 로는 잘못된 바이트 → U+FFFD 폭)과 그리기(CP1252)가 어긋난다. 글꼴에 U+FFFD 가 들어 있는 이유다.

### 한글에 대한 함의

1. **그리기가 CP1252 고정**이라 UTF-8·CP949 어느 쪽 파일을 넣어도 한 바이트가 한 글자로 풀린다 → 디코딩에 개입해야 한다.
2. **줄바꿈 계산이 바이트 0xB6 을 직접 본다.** 표준 UTF-8 에서는 `부 북 분 불 추 출 충 권 삶 싶` 등이, CP949 에서는
   첫 바이트가 0xB6 인 94자(`때 또` 등)와 둘째 바이트가 0xB6 인 글자(`마 조 독 철 섬` 등)가 걸린다
   → 표준 인코딩을 그대로 쓰면 그 글자에서 줄이 끊기고 글자가 깨진다.
3. **폭을 한 바이트씩 잰다.** 멀티바이트 글자의 각 바이트가 따로 측정되므로, 리드 바이트는 한 칸 폭·나머지는 폭 0 으로
   답해야 줄바꿈 위치가 맞고 글자 중간에서 줄이 끊기지 않는다.
4. 글꼴에 한글 글리프가 없다 → spritefont 를 다시 만들어야 한다.

이 네 가지에 대한 해법이 [04 문서](04-korean-localization.md)의 설계다.
