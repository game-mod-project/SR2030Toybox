# 05. 게임 구조 — 12개 영역

조사 기준: Steam appid `2093410`, build `21347933`, 2026-10-06.

표기: **[확인]** 파일·실행 파일·게임 안에서 직접 확인, **[추정]** 정황으로 판단, **[위키]** 공식 위키에 있으나 이 빌드에서 미확인.

Supreme Ruler 2030 을 열두 영역으로 나눠, 영역마다 게임에서 무엇이고 · 데이터의 어디에 들어 있고 · 어떤 내장 치트가 닿고 ·
무엇으로 바꿀 수 있는지를 적는다. 섹션·키·열의 전체 목록과 뜻은 [06 데이터 참조](06-data-reference.md), 치트의 전체 목록은
[07 내장 치트](07-cheats.md)에 있다. 이 문서는 그 둘을 영역별로 다시 묶은 길잡이다.

수단은 세 가지를 본다(나머지는 [09](09-cheat-mod-plan.md)).

| 수단 | 언제 적용되나 | 누구에게 |
|---|---|---|
| 내장 치트 (`cheat …`) | 진행 중인 게임 | 대부분 플레이어, 일부는 모든 지역 |
| 시나리오 설정 (`*.scenario` 의 `&&GMC`, 그리고 파일 끝에 덧붙이는 `&&CVP` · `&&UNITS`) | 새 게임. 캐시를 다시 만들지 않아도 된다고 한다 [위키] | 설정에 따라 |
| 데이터 표 (`Maps\*.CVP`, `Maps\DATA\DEFAULT.*`, `INI\*.csv`) | 새 게임. 대부분 캐시를 다시 만들어야 한다 [위키] | 모든 지역 또는 지정한 지역 |

치트의 효과는 이 문서에서 모두 [위키]다. 게임에서 확인한 결과는 [07](07-cheats.md)의 "검증" 열에 있다.

## 국가

**게임에서 무엇인가** — 지도 위의 지역(region) 하나하나가 나라다. 이름, 국기, 수도, 인구, 종주국·식민지 관계, 플레이할 수 있는지가
정해져 있다. 여러 지역을 묶은 그룹(독일 = 1499)이 실제로 플레이하는 단위다.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\W2030.CVP` · `CVP` | `regionname` `flagnum` `regioncolor` `capitalx` `capitaly` | 이름, 국기, 색, 수도 위치 | [위키] |
| 〃 | `refpopulation` `birthratebase` `deathratebase` `lifeexp` `literacy` | 인구와 그 변화 | [위키] |
| 〃 | `parentregion` `federalregion` `keepregion` `nonplayable` `masterdata` | 종주국, 연방, 플레이 가능 여부, 그룹 값 처리 | [위키] |
| 〃 · `GROUPING` | 지역 번호 | 어느 지역들이 한 나라로 묶이는가(최대 32개) | [위키] |
| `Maps\W2030.REGIONINCL` · `REGIONINCL` | 지역 번호 | 시나리오에 나오는 지역 | [확인: 파일] |
| `Sandbox\World2030\World 2030 Regions.csv` · `REGIONSCEN` | `inscenario` `nonplayable` `spawncmdunit` | 시나리오별 포함·플레이 여부 | [추정] |

**내장 치트** — `cheat becomeregion`(다른 지역으로 갈아탄다), `cheat annex`(병합), `cheat colonize`(식민지로), `cheat liberate`(종주국에서 해방),
`cheat revolt`(파르티잔 발생), `cheat reviveall`(세계를 쪼갠다), `cheat populate` · `cheat depopulate`(인구·예비군·현역 ±100만).

**바꿀 수 있는 수단**

- 내장 치트: 진행 중에 영토와 인구를 바꾼다.
- 시나리오 설정: 시나리오 파일 끝에 `&&CVP <지역>` 블록으로 인구·수도 같은 값을 덮어쓴다 [위키].
- 데이터 표: `*.CVP` 를 직접 고친다. 그룹과 하위 지역의 값이 합쳐지는 방식(`masterdata`)을 알아야 한다 [위키].

**모르는 것** — 인구 증감의 계산식(실행 파일 안). `refpopulation` 이 그룹과 하위 지역에서 어떻게 합쳐지는지는 게임에서 확인하지 않았다.

## 경제

**게임에서 무엇인가** — 국고, 1인당 GDP, 국가 부채, 물가, 실업, 신용 등급. 재무 화면에서 세율과 지출을 정한다.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\W2030.CVP` · `CVP` | `treasury` | 시작 국고에 더하는 금액(백만 달러). 기본은 GDP/50 | [위키] |
| 〃 | `gdpc` | 1인당 GDP | [위키] |
| 〃 | `nationaldebtgdp` `creditrating` `inflation` `unemployment` | 시작 부채, 신용 등급, 물가, 실업 | [위키] |
| 〃 | `domsubsidyrating` `tourismrating` `prodefficiency` | 보조금 등급, 관광, 생산 효율 | [위키] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `gdpcbase` `primerate` | 세계 기준 GDP/c, 기준 금리 | [위키] |
| `*.scenario` · `GMC` | `initialfunds` | 초기 자금 0~4 (로비 옵션의 기본값) | [위키] |
| 〃 | `debtfree` | 1 = 부채 없이 시작 | [위키] |
| 〃 | `difficulty` 의 둘째 값 | 경제 난이도 | [위키] |

**내장 치트** — `cheat treasury N`(국고 +N 백만), `cheat georgew`(+100억), `cheat georgeww`(+1000억), `cheat trumpme`(±1조).
GDP 를 직접 바꾸는 치트는 없다.

**바꿀 수 있는 수단**

- 내장 치트: 돈은 치트로 충분하다.
- 시나리오 설정: `initialfunds` `debtfree`. GDP 는 시나리오 파일 끝의 `&&CVP <지역>` 에 `gdpc` 를 적는 방법이 유력하다 [위키].
- 데이터 표: `*.CVP` 의 `gdpc` `treasury`. 캐시 재생성이 필요하다 [위키].

**모르는 것** — `gdpc` 가 진행 중에 어떻게 변하는지(사회 지출·교육과 묶여 있다는 것만 게임 문구에 있다). 시작 뒤에 GDP 를 올리는 수단은 찾지 못했다.

## 자원

**게임에서 무엇인가** — 물자 열한 가지: 농산물, 고무, 목재, 석유, 석탄, 광석, 우라늄, 전력, 소비재, 공업재, 군수품. 생산·소비·비축·세계 시장 거래.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\DATA\_W2030.WMDATA` · `WMPRODDATA` | `wmbasecost` `wmfullcost` `wmmargin` | 물자별 기준 단가와 이윤 | [위키] |
| 〃 | `wmnodeproduction` `wmurbanproduction` `bwmterrain` | 육각·도시의 생산량 | [위키] |
| 〃 | `wmprodperpersonmax` `wmprodperpersonmin` | 1인당 소비 | [위키] |
| 〃 | `producefrom` | 만드는 데 드는 다른 물자 | [위키] |
| 〃 · `WMDATA` | `hexresmults` | 육각 자원 등급별 배수 | [위키] |
| `Maps\DATA\DEFAULT.UNIT` · `RAWPROD` | 시설별 물자 계수 | 어느 시설이 무엇을 얼마나 만드나 | [추정] |
| `Maps\W2030.CVP` · `REGIONPRODUCTS` | – | 지역의 물자 설정(열의 뜻 모름) | [추정] |
| `*.scenario` · `GMC` | `resources` | 자원 설정 0~4 (로비 옵션의 기본값) | [위키] |

**내장 치트** — `cheat products N`(모든 물자 재고 +N), `cheat branson`(+10만), `cheat bezos`(+100만), `cheat gates`(모든 플레이어 +10만).

**바꿀 수 있는 수단**

- 내장 치트: 재고는 치트로 충분하다.
- 시나리오 설정: `resources`. 위키는 `&&CVP` 에 `stockdays` · `stockadd`(시작 비축) 키가 있다고 하나 이 빌드의 파일에는 쓰이지 않는다.
- 데이터 표: `WMPRODDATA` 로 생산량·소비량을 바꾸면 모든 지역에 적용된다.

**모르는 것** — 실행 파일에만 있는 `magicresupply`(부대 보급에 플레이어의 재고를 쓴다 [위키]), `noelecstock`(전력 비축 금지)의 실제 동작.

## 산업

**게임에서 무엇인가** — 시설(공장, 발전소, 광산, 농장)을 지어 물자를 만든다. 시설은 장비와 같은 표에 있고, 짓는 데 날짜와 공업재가 든다.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\DATA\DEFAULT.UNIT` · `UNITS` | `UPGRADEUnit` `uIndustry` `uUrban` `HasProduction` | 그 행이 시설인지, 어떤 시설인지 | [추정] |
| 〃 | `DaysToBuild` `Cost` `IGCost` | 짓는 날짜, 비용, 공업재 | [추정] |
| 〃 | `uProdTech` `uBuildCap` `uStoreType` `uStoreCap` | 생산에 걸리는 기술 효과, 건설 용량, 저장 | [추정] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `upgradenums` | AI 가 짓는 시설 번호(도로, 철도, 공장 …) | [위키] |
| `Maps\DATA\DEFAULT.TTRX` · `TTR` | 효과 16, 18, 36~55, 72~95 | 시설 건설 속도, 시설 효율, 물자별 생산량·효율 | [위키] |
| `Maps\W2030.CVP` · `CVP` | `prodefficiency` | 지역의 기준 생산 효율 | [위키] |

**내장 치트** — `cheat breakground`(시설이 하루 만에 완성. 하루치 비용과 공업재는 든다. 도로에는 안 된다).

**바꿀 수 있는 수단**

- 내장 치트: 시설 건설은 `breakground`.
- 데이터 표: `UNITS` 의 시설 행에서 `DaysToBuild` · `Cost` 를 고친다(캐시 재생성 필요 [위키]). 또는 `TTR` 에 건설 속도 효과(16)가 큰 기술을 둔다.
- 시나리오 설정: `GMC` 의 `fastbuild` 는 쓰이지 않는다 [위키].

**모르는 것** — `breakground` 가 AI 에게도 적용되는지.

## 연구

**게임에서 무엇인가** — 기술 트리. 기술마다 선행 기술, 연구 일수, 비용, 효과(최대 네 개)가 있다. 지역의 기술 수준이 시작 기술을 정한다.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\DATA\DEFAULT.TTRX` · `TTR` | `Time to Res` `Cost` | 연구 일수와 비용 | [위키] |
| 〃 | `Prereq 1` `Prereq 2` `SR6 Tech Level` | 선행 기술, 기술 수준 | [위키] |
| 〃 | `Effect 1`~`Effect 4`, `Effect Value 1`~`4` | 효과 번호와 크기 | [위키] |
| 〃 | `Set by Default` `StartExclude` `Tradeable?` | 기본 보유, 시작 기술 제외, 거래 가능 | [위키] |
| `Maps\W2030.CVP` · `CVP` | `techlevel` | 지역 기술 수준 0~120 | [위키] |
| 〃 · `REGIONTECHS` | 기술 번호 | 지역이 갖고 시작하는 기술(선행 기술 포함) | [위키] |
| `*.scenario` · `GMC` | `groupresearchmerge` `victorytech` | 묶을 때 연구 합치기, 승리 조건 기술 | [위키] |

**내장 치트** — `cheat technology N`(기술 수준 N 이하를 전부 연구된 것으로), `cheat e=mc2`(모든 연구가 하루에 끝난다. 비용은 청구된다),
`cheat finalexam`(기술 수준 +1), `cheat allunit`(연구하지 않은 부대도 만들 수 있다 — AI 도 그렇다).

**바꿀 수 있는 수단**

- 내장 치트: 연구는 치트로 충분하다.
- 시나리오 설정: 시나리오 파일 끝의 `&&CVP <지역>` 에 `techlevel` 을 적는다(위키의 예가 바로 이것이다).
- 데이터 표: `TTR` 의 일수·비용, `REGIONTECHS` 에 기술 추가.

**모르는 것** — `e=mc2` 가 진행 중인 연구만 끝내는지 대기열 전체를 끝내는지.

## 정치

**게임에서 무엇인가** — 정부 형태, 지도자와 각료, 국민·군부 지지율, 선거, 사회 지출, 종교.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\W2030.CVP` · `CVP` | `govtype` `politic` `govtitle` | 정부 형태, 성향, 원수 칭호 | [위키] |
| 〃 | `civapproval` `milapproval` | 국민·군부 지지율 | [위키] |
| 〃 | `electiondate` `electionterm` `polpartin` `leadernum` `oppositionnum` | 선거와 정당, 지도자 | [위키] |
| 〃 | `couppossibility` `revoltpossibility` `fanaticism` | 쿠데타·봉기 가능성, 광신도 | [위키] |
| 〃 · `REGIONSOCIALS` `REGIONRELIGIONS` | 항목·값 | 사회 지출 시작값, 종교 분포 | [위키] |
| `Maps\DATA\_W2030.WMDATA` · `GOVTYPE` | 정부 형태별 배수 60여 열 | 정부 형태가 주는 보정(열의 뜻 모름) | [추정] |
| `Maps\DATA\DEFAULT.PPLX` · `PEOPLE` | – | 인물 | [확인: 파일] |
| `INI\deptprior.csv` · `CABPRIORITIES` | – | 각료의 우선순위 | [추정] |
| `*.scenario` · `GMC` | `govchoice` `approvaleff` | 정부 형태 선택, 지지율 효과 0~4 | [위키] |

**내장 치트** — `cheat approval`(국민·군부 지지율을 0% 와 100% 사이에서 뒤집는다), `cheat democracy`(민주 AI 지역의 선거를 당일로 당기고 집권자가 진다),
`cheat novichok`(지정한 지역의 지도자 사망).

**바꿀 수 있는 수단**

- 내장 치트: 지지율은 `approval`.
- 시나리오 설정: `approvaleff`. 실행 파일에만 있는 `bnoapprovaleff`(지지율 효과 없음 [위키])도 후보다.
- 데이터 표: `CVP` 의 지지율·정부 형태, `GOVTYPE` 의 배수.

**모르는 것** — `GOVTYPE` 의 열. 지지율이 진행 중에 변하는 식.

## 외교

**게임에서 무엇인가** — 지역 사이의 관계(외교·국민·개전 명분), 조약, 세계 시장(UN) 회원 자격과 제재, 세력권.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Sandbox\World2030\World 2030 Regions.csv` · `CVPREL` | `Treatynum` `DipRel` `CivRel` `BelliRel` | 두 지역 사이의 시작 조약과 관계 | [확인: 파일] |
| `Maps\DATA\rtreaties.csv` · `RTREATIES` | 조약 번호, 이름 | 조약의 종류 | [확인: 파일] |
| `Maps\W2030.CVP` · `CVP` | `sphere` `civiliansphere` `influence` `influenceval` | 세력권과 영향 요인 | [위키] |
| 〃 | `worldintegrity` `treatyintegrity` `bwmmember` | UN 승인도, 조약 신뢰도, 회원 여부 | [위키] |
| `Common\*.csv` 등 · `SEVENTS` | `eventid` 2, 3, 4, 5, 6, 7 | 선전포고, 중립, 동맹, 조약, 외교 제안을 일으키는 이벤트 | [위키] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `wmsanctionapproval` `wmsanctionpercentage` `wmrelrate` | 세계 시장 제재 | [추정] |
| `*.scenario` · `GMC` | `relationseffect` `wminvolve` `nosphere` `regionallies` `regionaxis` | 관계 변동성, UN 관여, 세력권, 진영 | [위키] |

**내장 치트** — `cheat love` · `cheat hate` · `cheat neutral`(지정한 지역과의 관계를 최고·최저·0 으로), `cheat treaty`(고른 지역과 동맹, 번호를 주면 그 조약),
`cheat peace`(모두 평화), `cheat worldwar`(모두 전쟁), `cheat fight`(두 지역을 전쟁으로), `cheat saddam` · `cheat saddamme`(무작위 선전포고),
`cheat shelovesmenot`(UN 관계 0%), `cheat moreoffers`(거래 제안이 잦아진다). 실행 파일에만 있는 것: `cheat mutualdef` `cheat dipaccept` `cheat sanction` `cheat wmsanction` `cheat shelovesme`.

**바꿀 수 있는 수단**

- 내장 치트: 관계와 조약은 치트로 충분하다.
- 시나리오 설정: `* Regions.csv` 의 `CVPREL`(캐시 뒤에 읽는다 [확인: 시나리오 파일]), 이벤트 5(조약 설정).
- 데이터 표: `CVP` 의 세력권.

**모르는 것** — 실행 파일에만 있는 다섯 치트의 효과.

## 군사

**게임에서 무엇인가** — 병력(현역·예비군), 징병, 군사 지출, 데프콘, 첩보와 위성.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\W2030.CVP` · `CVP` | `poptotalarmy` `popminreserve` `bconscript` | 총 병력, 최소 예비군, 징병 | [위키] |
| 〃 | `defcon` `alertlevel` | 데프콘, 경계 수준 | [위키] |
| 〃 | `milspendsalary` `milspendmaint` `milspendintel` `milspendresearch` | 군사 지출의 시작 수준 | [추정] |
| `Maps\DATA\training.csv` · `TRAINING` | 임무 번호, 비용 | 첩보 임무 | [추정] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `battstrdefault` | 병과별 기본 대대 병력 | [위키] |
| `Maps\DATA\DEFAULT.TTRX` · `TTR` | 효과 6, 7, 8, 116~127 | 방첩·첩보·군사 효율, **그 지역 모든 부대의 공격·방어** | [위키] |

**내장 치트** — `cheat 007`(첩보 임무가 전부 성공), `cheat maxsat` · `cheat satellite`(위성을 만들지 않고 띄운다), `cheat populate`(예비군·현역 포함 +100만).

**바꿀 수 있는 수단**

- 내장 치트: 병력 수와 첩보.
- 데이터 표: `TTR` 의 효과 116~127 로 한 지역의 모든 부대 수치를 올릴 수 있다고 한다 [위키] — 기술 하나를 고치거나 더해 "부대 스탯"을 바꾸는 길이다.
- 시나리오 설정: 시나리오 파일 끝의 `&&CVP <지역>` 에 `poptotalarmy`.

**모르는 것** — 효과 116~127 의 정확한 번호별 뜻은 위키 목록의 뒷부분에 있다(이 문서에 옮기지 않았다). 게임에서 확인하지 않았다.

## 부대

**게임에서 무엇인가** — 지도 위의 대대들. 시작 배치(전투서열), 전투단, 수비대·파르티잔 같은 자동 생성 부대.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\ORBATS\*.OOB`, `ORBATS20xx\<지역>.csv` · `OOB` | 장비 번호, 위치, 수량, 상태, 효율, 경험, 병력 | 시작 부대의 종류와 수, 배치 | [확인: 파일 주석] |
| `Common\*.csv` 등 · `SEVENTS` | `eventid` 10 | 부대를 만들어 주는 이벤트(수량, 배치 상태, 위치) | [위키] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `unitgarrison` `unitguerrilla` `unitpartisan` `commandunit` | 자동으로 생기는 부대의 장비 번호 | [위키] |
| 〃 | `createbattlegroupsize` | 전투단 크기 | [추정] |
| `Maps\theatres.csv` · `THEATRES` `THEATRETRANSF` `NAVALTRANSIT` | – | 전구와 전구 사이 이동 | [확인: 파일] |

**내장 치트** — `cheat damage N`(고른 부대에 피해), `cheat stranded`(고른 부대의 탄약·보급을 채우거나 비운다), `cheat nomove`(부대가 명령을 받지 않는다),
`cheat darran`(각 병과 최강 부대 한 묶음을 받고 적 부대의 4분의 1쯤이 사라진다), `cheat darren`(AI 가 받고 모두 선전포고), `cheat selloffunits`(AI 가 부대를 판다).
실행 파일에만 있는 것: `cheat spawnunit`(이름으로는 부대 생성), `cheat launchattack`.

**바꿀 수 있는 수단**

- 내장 치트: `darran` 은 종류를 고를 수 없다. 원하는 부대를 골라 받는 수단은 `spawnunit` 의 동작에 달려 있다(모름).
- 시나리오 설정: 이벤트 10 으로 시작 직후 원하는 부대를 받는다 [위키]. 실행 파일에만 있는 `nounits`(부대 없이 시작 [위키]).
- 데이터 표: `OOB` 의 수량. 전투서열은 캐시에 구워지고 캐시 생성 시간의 대부분을 차지한다 [위키].

**모르는 것** — `spawnunit` 의 인자.

## 장비

**게임에서 무엇인가** — 부대의 종류(전차, 전투기, 함정, 미사일)마다의 수치: 비용, 건조 일수, 공격·방어, 사거리, 속도, 필요 기술.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\DATA\DEFAULT.UNIT` · `UNITS` | `DaysToBuild` `Cost` `IGCost` `URCost` | 건조 일수와 비용 | [추정] |
| 〃 | `SoftAttack` `HardAttack` `FortAttack` `LowAirAttack` `MidAirAttack` `HighAirAttack` `NavalSurfaceAttack` `NavalSubAttack` `CloseCombatAttack` | 공격 수치 | [추정] |
| 〃 | `GroundDefense` `TacAirDefense` `IndirectDefense` `CloseDefense` | 방어 수치 | [추정] |
| 〃 | `GroundAttRange` `AirAttRange` `SurfaceAttRange` `SubAttRange` `Speed` `MoveRange` `FuelCap` `SupplyCap` | 사거리, 속도, 항속, 연료, 보급 | [추정] |
| 〃 | `TechReq1` `TechReq2` `Regions` `(YearAvail - 1900)` `NoBuild` `NoResearch` | 만들 수 있는 조건 | [추정] |
| `Maps\W2030.CVP` · `REGIONUNITDESIGNS` | 장비 번호 | 지역이 갖고 시작하는 설계 | [위키] |
| 〃 · `CVP` | `worldavail` `armsavail` | 만들 수 있는 장비의 지역 코드 | [위키] |

**내장 치트** — `cheat allunit`(연구 없이 모든 부대 생산. AI 도 그렇다), `cheat unitdesign N`(그 설계를 가진 것으로), `cheat onedaybuild`(주문한 부대가 다음 날 완성. AI 도 그렇다).
장비의 수치를 바꾸는 치트는 없다.

**바꿀 수 있는 수단**

- 내장 치트: 생산 조건과 속도. 다만 `allunit` 과 `onedaybuild` 는 AI 도 함께 혜택을 본다.
- 시나리오 설정: 시나리오 파일 끝에 `&&UNITS` 행을 덧붙여 장비의 수치를 덮어쓴다고 한다 [위키] — 캐시를 다시 만들지 않는 길이다.
- 데이터 표: `DEFAULT.UNIT` 을 고친다(캐시 재생성 필요 [위키]). Workshop 의 장비 모드들이 쓰는 방법이다([08](08-workshop-survey.md)).

**모르는 것** — 플레이어만 빠르게 만드는 수단. 수치가 전투 계산에 들어가는 식.

## 전쟁

**게임에서 무엇인가** — 전투와 그 환경: 지형, 날씨, 탐지, 보급, 핵, 승리 조건.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `Maps\DATA\DEFAULT.TERX` · `TERRAIN` | `M0`~`M15`, `D0`~`D3`, `Entrench` | 지형별 이동 비용, 방어 배수, 참호 | [추정] |
| `INI\Spotting.csv` · `SPOTTING` | 탐지 유형별 강도·거리 | 탐지 | [추정] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `lutsupcost` `weatheryear` `weatherspeed` | 보급 부족 비용, 날씨 | [위키] |
| 〃 (파일에 안 쓰임) | `maxstacksize` `attackrangemod` `spottingrangemod` `lossdivconstant` `resupfuelmult` | 전투 엔진의 내부 값. 바꾸면 게임이 깨질 수 있다고 한다 | [위키] |
| `*.scenario` · `GMC` | `wmduse` `wmdeff` | 핵 사용 허용, 핵이 관계에 주는 영향 | [위키] |
| 〃 | `alliedvictory` `victoryhex` `victorytech` `gamelength` `difficulty` 의 첫 값 | 승리 조건, 군사 난이도 | [위키] |
| `INI\orders.csv` · `ORDERS` | – | 부대 명령 | [확인: 파일] |

**내장 치트** — `cheat worldwar` · `cheat peace` · `cheat fight`(외교 참조), `cheat instantwin`(승리. 이어서 할 수 있다), `cheat blueskies`(날씨와 지면 상태 초기화),
`cheat endday`(부대의 계산을 꺼서 하루가 1초에 지나간다. 부대는 멈춘다). 실행 파일에만 있는 것: `cheat killeveryone`.

**바꿀 수 있는 수단**

- 내장 치트: 전쟁의 시작과 끝, 승리.
- 시나리오 설정: 핵, 승리 조건. 실행 파일에만 있는 `fogofwar` `advfogofwar` `norangemult` `nospotrangemult` 는 전장의 안개와 탐지 설정으로 보인다.
- 데이터 표: `TERRAIN` 은 `INI\AllLoad.ini` 가 매번 다시 읽으므로 캐시와 무관하게 반영될 가능성이 크다 [추정].

**모르는 것** — 전투 계산식. 전장의 안개를 끄는 수단(치트 `fullmapshow` 는 GUI 를 숨기는 것이지 안개를 걷는 것이 아니다 [위키]).

## AI

**게임에서 무엇인가** — 컴퓨터 지역의 태세와 행동: 무엇을 짓고, 누구와 싸우고, 플레이어의 각료가 무엇을 대신하는가.

**어디에 들어 있나**

| 파일 · 섹션 | 키 · 열 | 무엇을 정하나 | 근거 |
|---|---|---|---|
| `INI\AIParams.csv` · `AIPARAMS` | `aibuildarray` `aiforcesize` `aiprireqtype` `autobuildbypopmax` `autobuildbypopmin` | AI 의 건설·전력 규모·요청 우선순위 | [추정] |
| 〃 · `BUILDSEQUENCE2` `BUILDSEQUENCE3` | 병과별 비율, 선호 | AI 가 만드는 부대의 구성 | [추정] |
| 〃 · `UNITWEIGHTING` `MISSILEWEIGHTING` | 수치 항목별 가중치 | AI 가 장비를 평가하는 기준 | [추정] |
| 〃 · `AIREQRESPONSE` | – | AI 요청에 응하는 병과 | [추정] |
| `Maps\W2030.CVP` · `CVP` | `playeraistance` `playeragenda` | 지역의 AI 태세(0 보통 ~ 4 예측 불가)와 의제 | [위키] |
| `Maps\DATA\_W2030.WMDATA` · `WMDATA` | `aiplayrich` `aiunitbuildmilgoods` `aiunitbuildpetrol` `aiunitbuildreserve` | AI 가 부대를 만들 때의 자원 기준 | [추정] |
| `*.scenario` · `GMC` | `aistance` `difficulty` | 전체 AI 태세, 난이도 | [위키] |

**내장 치트** — `cheat airequest`(AI 가 내부 요청을 할 때마다 알림), `cheat nomove`(부대가 명령을 받지 않는다). 실행 파일에만 있는 것: `cheat noaiinit` `cheat fullaiinit`.

**바꿀 수 있는 수단**

- 시나리오 설정: `aistance`, `difficulty`.
- 데이터 표: `INI\AIParams.csv` 는 `INI\AllLoad.ini` 가 매번 다시 읽는다 — 캐시와 저장 게임에 들어가지 않으므로 고치면 진행 중인 게임에도 반영될 것이다 [추정: 파일 주석].
- 내장 치트: AI 를 직접 약하게 하는 치트는 없다.

**모르는 것** — AI 매개변수 각 칸의 뜻. 위키에 "AI Params file" 문서가 있다(읽지 않았다).

## 출처

- [06 데이터 참조](06-data-reference.md) — 섹션·키·열과 그 근거
- [Cheats — Official Supreme Ruler Wiki](https://supremeruler.fandom.com/wiki/Cheats) — 치트의 효과
- [Regional Data](https://supremeruler.fandom.com/wiki/Regional_Data), [Scenario Files](https://supremeruler.fandom.com/wiki/Scenario_Files),
  [WMData](https://supremeruler.fandom.com/wiki/WMData), [Tech Tree](https://supremeruler.fandom.com/wiki/Tech_Tree),
  [Events](https://supremeruler.fandom.com/wiki/Events), [Creating a Cache](https://supremeruler.fandom.com/wiki/Creating_a_Cache) — 2026-10-06 열람
