# 08. Workshop 조사

조사일: 2026-10-06. 대상: Supreme Ruler 2030 Workshop 의 항목 53개 전부(Steam appid `2093410`). 항목을 구독하지 않고 Workshop 페이지의 제목·설명·태그만 읽었다 — **파일 내용은 보지 않았다.** 목록은 시간이 지나면 바뀐다.

표기: "근거"가 `설명`이면 항목 설명에 그렇게 적혀 있다는 뜻이고, `설명 부족`이면 제목과 태그로만 판단했다는 뜻이다. 어느 쪽도 게임에서 확인한 것이 아니다. 요약은 설명을 우리말로 줄인 것이다.

읽은 방법: 구독자 순 목록 두 쪽에 실린 항목 자료(제목, 짧은 설명, 태그, 날짜, 크기)를 53개 모두에 썼고, 항목 페이지는 39개를 열어 긴 설명과 필요 DLC 를 봤다. 나머지 14개는 Steam 이 요청을 막아 페이지를 열지 못했다 — 그 항목의 필요 DLC 는 `미확인`이다.

## 요약

| 분류 | 항목 수 |
|---|---|
| 치트 · 도구 | 5 |
| 밸런스 | 3 |
| 경제 | 1 |
| 군사 · 장비 | 4 |
| 국가 · 시나리오 | 32 |
| 지도 | 3 |
| 그래픽 · 소리 · UI | 5 |

- **대부분은 시나리오다.** 32개가 새 시나리오이거나 기존 시나리오의 변형이고, 그중 여덟 개는 시작 기술을 1차대전 수준으로 낮춘 같은 제작자의 변형이다.
- **"치트"라고 부를 만한 것은 게임 밖 프로그램 둘뿐이다.** `Unofficial External Trainer` 는 실행 중인 게임의 메모리를, `SR2030 Save Editor` 는 저장 파일을 고친다. 둘 다 Workshop 으로 배포되지만 게임이 읽는 모드 파일이 아니라 따로 실행하는 프로그램이다. 이 저장소에서는 내려받거나 실행해 보지 않았다.
- **플레이어만 유리하게 하는 데이터 모드는 없다.** 수치를 바꾸는 모드(전투 3배, 잠수함 약화, 장비 개편, 경제 개편)는 모두 모든 지역에 똑같이 적용되는 균형 조정이다.
- **모드 제작에 참고할 만한 단서가 설명에 있다.** `Submarine Balance Mod` 와 `Intermarium2030 (Assets)` 는 장비·인물 파일을 바꾼 뒤 캐시를 다시 만들라고 적었고, `Communist Michigan` 은 시나리오 파일에 두 줄을 더하는 것만으로 한 지역의 값을 바꿨다고 적었다([06](06-data-reference.md)의 "로딩 단계와 캐시").

## 분류별 표

"유형"은 태그의 `Mods`(게임 요소 교체) · `Maps`(새 시나리오)다([02](02-modding-system.md)). "겹치는 기능"은 [05](05-game-systems.md)의 영역 이름으로 적었다.

### 치트 · 도구

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [Unofficial External Trainer (v.00)](https://steamcommunity.com/sharedfiles/filedetails/?id=3625246338) | Mooninnng | MODS | – | 2025-12-16 | 9 MB | 게임 밖 실행 파일. 실행 중인 게임의 메모리를 고쳐 나라의 수치와 자원을 실시간으로 바꾼다. 싱글플레이 전용이라고 적혀 있다 | 경제 — 돈, 자원 | 설명 |
| [SR2030 Save Editor v 108](https://steamcommunity.com/sharedfiles/filedetails/?id=3704887722) | Mooninnng | MODS | – | 2026-06-28 | 11 MB | 게임 밖 저장 파일(.SAV) 편집기. 나라, 정부, 지도자, AI 행동, 외교 관계, 조약, 전투단, 이벤트를 고친다 | 외교 — 국가 관계 / 정치 / AI | 설명 |
| [SR2030 Intelligence Suite - Unit Comparison & Tech Analyzer V01](https://steamcommunity.com/sharedfiles/filedetails/?id=3620254489) | Mooninnng | MODS | – | 2025-12-08 | 211 MB | 게임 밖 도구. 메모리를 읽어 부대 비교, 기술 영향 분석, 기술 트리, 경제 기록을 겹쳐 보여 준다(읽기) | 없음(값을 바꾸지 않는다) | 설명 |
| [SR2030 Logger](https://steamcommunity.com/sharedfiles/filedetails/?id=3603000429) | Mooninnng | MODS | 미확인 | 2025-11-09 | 102 MB | 게임 밖 도구. 메모리를 읽기 전용으로 읽어 경제·자원·인구·지지율·국고를 기록한다 | 없음(값을 바꾸지 않는다) | 설명 |
| [SR Planner — In-Game Battle Planner](https://steamcommunity.com/sharedfiles/filedetails/?id=3762611464) | Mooninnng | MODS | 미확인 | 2026-07-11 | 53 MB | 지도 위에 화살표·전선·NATO 기호로 작전 계획을 그리는 도구 | 없음 | 설명 |

### 밸런스

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [World 2024 Rework](https://steamcommunity.com/sharedfiles/filedetails/?id=3151451050) | GODOFGOLD808 | MODS | – | 2024-08-02 | 72 MB | 2024년 1월 기준으로 일부 구조를 고치고 균형을 다시 잡은 바닐라 보강판 | 장비 / 국가 | 설명 |
| [Submarine Balance Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=3180751071) | Penny Tration | MODS | – | 2024-03-12 | 4 MB | 잠수함의 속도·사거리·공격·방어를 15% 낮춘다. 새 게임에서 Force Recache 를 켜라고 적혀 있다 | 장비 — 부대 스탯(잠수함만) | 설명 |
| [World 2030 Battle Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=3502640953) | Evidential | MODS | – | 2025-09-03 | 8 MB | 모든 장비의 방어와 인원을 3배로 해 전투를 길게 한다. 거의 모든 나라의 전투서열을 늘렸다 | 장비 — 부대 스탯(모든 지역) / 부대 — 군사력 | 설명 |

### 경제

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [Economic Overhaul](https://steamcommunity.com/sharedfiles/filedetails/?id=3248085183) | DigitalGeneral | MODS | – | 2024-05-17 | 34 MB | 자원의 투입과 산출을 현실에 가깝게. 거의 모든 시설이 석유와 전력을 쓰고 석유 채굴량을 줄였다 | 자원 / 산업 | 설명 |

### 군사 · 장비

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [GCR + Unit Overhaul 5.1.3 for SR2030](https://steamcommunity.com/sharedfiles/filedetails/?id=3754538686) | Tnarg | MODS | Expansion Pass | 2026-09-21 | 2407 MB | 장비 수천 개와 기술 트리, 모델, 지도·지역·전투서열을 고친 대형 개편에 Global Crisis 재조정을 더했다 | 장비 — 부대 스탯(전면 개편) / 연구 | 설명 |
| [SR2030 : SPECIAL FORCES MOD (Includes Terrorists that multiply and Military Contractors!) UPDATED 24 MARCH](https://steamcommunity.com/sharedfiles/filedetails/?id=3451253117) | DigitalGeneral | MODS | – | 2025-03-24 | 130 MB | 민간 군사 기업, 특수부대 개편, 불어나는 테러리스트 부대, 건물 추가. 민간 군사 기업은 하루 만에 만들어진다 | 장비 / 장비 생산(그 부대만) | 설명 |
| [Unit Overhaul WWII 2.6 for SR2030](https://steamcommunity.com/sharedfiles/filedetails/?id=3754500870) | Tnarg | MODS | Expansion Pass | 2026-08-30 | 2098 MB | 2차대전기 장비 대형 개편 | 장비 — 부대 스탯(전면 개편) | 설명 |
| [Demonius' Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=3634810731) | Demonius | MODS | 미확인 | 2026-01-03 | 57 MB | 일부 장비를 고치고 새 장비를 더했다. 2025년 세계 샌드박스 포함 | 장비 | 설명 부족 |

### 국가 · 시나리오

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [Regions and Facilities](https://steamcommunity.com/sharedfiles/filedetails/?id=3033304256) | Snelg | MODS | – | 2026-10-01 | 96 MB | 세계 곳곳에 지역과 시설(주로 정착지)을 더한 새 Shattered World 시나리오. 캐시를 함께 싣는다 | 국가 | 설명 |
| [Shattered Jewel](https://steamcommunity.com/sharedfiles/filedetails/?id=3072826861) | Tokyo Dreamin’ | MODS | – | 2023-11-08 | 35 MB | 대체 역사 시나리오(1948년에야 끝난 태평양 전쟁 이후) | 국가 | 설명 |
| [SR:"Fallout" ALPHA](https://steamcommunity.com/sharedfiles/filedetails/?id=3111481857) | Sanguinius | MODS | – | 2023-12-11 | 1076 MB | 폴아웃 세계관의 전면 개조(알파). 미국 서부 중심 | 국가 / 장비 | 설명 |
| [Shattered World 2030 WW2 starting tech](https://steamcommunity.com/sharedfiles/filedetails/?id=3310351487) | Franklin24 | MAPS | – | 2024-12-23 | 1 MB | Shattered World 를 1940년 기술로. 나라마다 시작 기술을 바꾸고 기술 수준을 40 으로 했다 | 연구 — 시작 기술(낮춤) | 설명 |
| [New World Order](https://steamcommunity.com/sharedfiles/filedetails/?id=3415445922) | Superman 12 in 3D | MODS | – | 2025-04-23 | 22 MB | 설명이 한 줄뿐이라 내용을 알 수 없다 | 모름 | 설명 부족 |
| [Battle of Italy 2030 - No Events](https://steamcommunity.com/sharedfiles/filedetails/?id=3012856682) | ScaryHug | MAPS | – | 2023-07-31 | 793 KB | Battle of Italy 2030 을 이벤트 없이 | 국가 | 설명 |
| [1984 - The Perpentual War](https://steamcommunity.com/sharedfiles/filedetails/?id=3385548585) | Zahav | MODS | – | 2024-12-16 | 21 MB | 소설 1984 의 세 초강대국 세계 | 국가 | 설명 |
| [IronPeace:1965](https://steamcommunity.com/sharedfiles/filedetails/?id=3737107927) | Sanguinius | MODS | – | 2026-06-06 | 38 MB | 추축국에 유리하게 끝난 2차대전 뒤의 1965년 냉전 | 국가 | 설명 |
| [Shattered World but with WW1 techs](https://steamcommunity.com/sharedfiles/filedetails/?id=3405298903) | [EVO] Dan | MAPS | – | 2025-10-27 | 11 MB | Shattered World 를 1차대전 기술로, 시작 부대 없이 | 연구 — 시작 기술(낮춤) / 부대 | 설명 |
| [World 2023 but with WW1 Techs](https://steamcommunity.com/sharedfiles/filedetails/?id=3391502075) | [EVO] Dan | MAPS | – | 2025-10-27 | 11 MB | World 2023 을 1차대전 기술로, 시작 부대 없이 | 연구 — 시작 기술(낮춤) / 부대 | 설명 |
| [The Falklands Crisis](https://steamcommunity.com/sharedfiles/filedetails/?id=3228021937) | [EVO] Dan | MAPS | – | 2024-08-02 | 8 MB | 1982년 포클랜드 전쟁. 전투서열을 새로 짜고 GDP/c·기술·설계를 맞췄다 | 국가 | 설명 |
| [SR: Korea](https://steamcommunity.com/sharedfiles/filedetails/?id=3475015281) | [EVO] Dan | MAPS | – | 2025-05-03 | 12 MB | 1948년에 시작하는 한국전쟁. 남과 북만 플레이 | 국가 | 설명 |
| [Shattered World ZOMBIES + ANIMALS Future Extended](https://steamcommunity.com/sharedfiles/filedetails/?id=3640045547) | SONOFPOLLUX | MAPS | Global Outbreak | 2026-01-31 | 28 MB | 좀비와 동물이 나오는 Shattered World 확장 | 국가 | 설명 |
| [Shattered World Crisis](https://steamcommunity.com/sharedfiles/filedetails/?id=3416524831) | [EVO] Dan | MAPS | – | 2025-01-28 | 13 MB | 나라 사이 긴장을 높여 전쟁이 잦은 Shattered World | 외교 — 국가 관계(모든 지역) | 설명 |
| [SEA Crisis](https://steamcommunity.com/sharedfiles/filedetails/?id=3188069462) | Penny Tration | MODS | – | 2024-03-17 | 7 MB | 남중국해의 분쟁 도서를 더한 시나리오 | 국가 | 설명 |
| [World 2023 but with WW1 techs and no starting unit production](https://steamcommunity.com/sharedfiles/filedetails/?id=3588556236) | [EVO] Dan | MAPS | – | 2025-10-27 | 17 MB | World 2023 을 1차대전 기술로, 시작 부대와 부대 생산 시설 없이 | 연구 — 시작 기술(낮춤) / 산업 | 설명 |
| [World2030 but with WW1 starting techs](https://steamcommunity.com/sharedfiles/filedetails/?id=3393947251) | [EVO] Dan | MAPS | – | 2025-10-27 | 11 MB | World 2030 을 1914년 기술로, 현대 부대 없이 | 연구 — 시작 기술(낮춤) / 부대 | 설명 |
| [SupremeKaiser](https://steamcommunity.com/sharedfiles/filedetails/?id=3460684720) | Sanguinius | MODS | – | 2025-04-24 | 20 MB | Kaiserreich 세계관의 시험 시나리오 | 국가 | 설명 부족 |
| [SR:Battle For Terra v0.3.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3409429021) | Sanguinius | MODS | – | 2025-01-22 | 241 MB | 워해머 풍의 전투 전용 시나리오. 모델과 장비 포함 | 국가 / 장비 | 설명 |
| [WackyWorld-0.2.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3435958375) | Sanguinius | MODS | – | 2025-03-04 | 27 MB | 현대에 머문 봉건 세계. 멀티플레이용 | 국가 | 설명 |
| [Intermarium2030 Scenario](https://steamcommunity.com/sharedfiles/filedetails/?id=3379337576) | Zahav | MAPS | – | 2025-01-03 | 15 MB | 제작자의 Intermarium 세계관 시나리오 | 국가 | 설명 |
| [Taiwan Strait Crisis 2030](https://steamcommunity.com/sharedfiles/filedetails/?id=3422754016) | [EVO] Dan | MAPS | – | 2025-04-03 | 12 MB | 2030년 대만 해협 위기(중국 대 일본 주도 연합) | 국가 | 설명 |
| [Operation Corporate II](https://steamcommunity.com/sharedfiles/filedetails/?id=3171135521) | [EVO] Dan | MAPS | – | 2024-03-04 | 467 KB | 지금의 군대로 다시 치르는 포클랜드(영국 대 아르헨티나, 1년) | 국가 | 설명 |
| [Shattered World but with WW1 techs and no starting unit production](https://steamcommunity.com/sharedfiles/filedetails/?id=3588549046) | [EVO] Dan | MAPS | 미확인 | 2025-10-27 | 17 MB | Shattered World 를 1차대전 기술로, 시작 부대와 부대 생산 시설 없이 | 연구 — 시작 기술(낮춤) / 산업 | 설명 |
| [Global Crisis but with WW1 techs](https://steamcommunity.com/sharedfiles/filedetails/?id=3405300799) | [EVO] Dan | MAPS | 미확인 | 2025-10-27 | 10 MB | Global Crisis 를 1차대전 기술로, 시작 부대 없이 | 연구 — 시작 기술(낮춤) / 부대 | 설명 |
| [Fractured Earth 2026](https://steamcommunity.com/sharedfiles/filedetails/?id=3798319251) | saarud | MODS | 미확인 | 2026-09-09 | 27 MB | 현대 국가들이 수백 개 나라로 쪼개진 대체 세계 | 국가 | 설명 |
| [World 2030 but with WW1 techs and no starting unit production](https://steamcommunity.com/sharedfiles/filedetails/?id=3588553785) | [EVO] Dan | MAPS | 미확인 | 2025-10-27 | 17 MB | World 2030 을 1차대전 기술로, 시작 부대와 부대 생산 시설 없이 | 연구 — 시작 기술(낮춤) / 산업 | 설명 |
| [Merowe Crisis](https://steamcommunity.com/sharedfiles/filedetails/?id=3173788086) | [EVO] Dan | MAPS | 미확인 | 2024-03-05 | 396 KB | 나일강 댐을 둘러싼 수단과 이집트의 가상 분쟁(1년) | 국가 | 설명 |
| [Communist Michigan](https://steamcommunity.com/sharedfiles/filedetails/?id=3124222601) | Michigan Mayor | MAPS | 미확인 | 2023-12-27 | 1 MB | Shattered World 의 시나리오 파일에 두 줄을 더해 미시간의 정부 형태를 공산주의(3)로 바꿨다 | 정치 — 정부 형태(한 지역) | 설명 |
| [Global Crisis but with WW1 techs and no starting unit production](https://steamcommunity.com/sharedfiles/filedetails/?id=3588148329) | [EVO] Dan | MAPS | 미확인 | 2025-10-27 | 17 MB | Global Crisis 를 1차대전 기술로, 시작 부대와 부대 생산 시설 없이 | 연구 — 시작 기술(낮춤) / 산업 | 설명 |
| [Divided Republics 1914](https://steamcommunity.com/sharedfiles/filedetails/?id=3804611700) | Darkens999 | MODS | 미확인 | 2026-09-19 | 6 MB | 1914년, 남북으로 갈린 미국에서 시작하는 대체 역사 샌드박스 | 국가 | 설명 |
| [Downfall?](https://steamcommunity.com/sharedfiles/filedetails/?id=3806591509) | Darkens999 | MODS | 미확인 | 2026-09-23 | 16 MB | 1944년 12월에 시작. 독일이 마우스 전차 12대를 배치한 채 시작하고 Ho 229 를 만들 수 있다 | 국가 / 부대 | 설명 |

### 지도

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [Vintage Map Mod V 4.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3463552278) | Mooninnng | MODS | – | 2025-08-23 | 596 MB | 지도 그림을 옛 군용 지도 풍으로. 바다 이름 포함 | 없음 | 설명 |
| [Prime Atlas V.2.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3487630822) | Mooninnng | MODS | – | 2025-08-23 | 285 MB | 지형 색과 질감을 다듬은 지도 그림 | 없음 | 설명 |
| [SR GEO - Vanilla - Dark blue SEA V1.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3549376580) | Mooninnng | MODS | 미확인 | 2025-08-23 | 19 MB | 바다와 대양의 이름을 지도에 표시(짙은 파란 바다용) | 없음 | 설명 |

### 그래픽 · 소리 · UI

| 항목 | 제작자 | 유형 | 필요 DLC | 고친 날 | 크기 | 무엇을 바꾸나 | 겹치는 기능 | 근거 |
|---|---|---|---|---|---|---|---|---|
| [Real Unit Stats](https://steamcommunity.com/sharedfiles/filedetails/?id=3114596967) | D-Bassett | MODS | – | 2023-12-15 | 173 KB | 장비 수치를 소수 둘째 자리까지 보여 준다. 수치를 바꾸는 모드가 아니다 | 없음(표시만) | 설명 |
| [Fixed Models (V1)](https://steamcommunity.com/sharedfiles/filedetails/?id=3029643495) | Cockitchy gaming | MODS | – | 2023-09-03 | 262 MB | 잘못된 3D 모델을 고치고 방공 체계 둘을 더했다 | 장비(모델) | 설명 |
| [Nato Style Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=3289865365) | Mooninnng | MODS | – | 2024-07-22 | 47 MB | 부대 모델을 NATO 식 기호로(1차대전기 42종). 전용 샌드박스 둘 | 없음 | 설명 |
| [Intermarium2030 (Assets)](https://steamcommunity.com/sharedfiles/filedetails/?id=3379316522) | Zahav | MODS | – | 2025-01-03 | 2 MB | Intermarium 시나리오용 국기와 지도자 그림·이름. 인물 파일을 넣은 뒤 캐시를 다시 만들라고 적혀 있다 | 없음 | 설명 |
| [Nostalgic ruler](https://steamcommunity.com/sharedfiles/filedetails/?id=3720562663) | Mooninnng | MODS | 미확인 | 2026-06-15 | 37 MB | 게임 창의 스킨을 옛 느낌으로 | 없음 | 설명 |

## 이미 있는 기능과 없는 기능

원안이 든 예시 아홉 개마다, 그 기능을 주는 Workshop 항목이 있는지 본다. 내장 치트로 되는지는 [07](07-cheats.md)에 있다.

| 원하는 것 | Workshop 항목 | 비고 |
|---|---|---|
| 돈 | `Unofficial External Trainer` | 게임 밖 프로그램. 설명은 "나라의 수치와 자원"이라고만 한다 |
| 자원 | `Unofficial External Trainer` | 위와 같음 |
| 연구 | 없음 | 시작 기술을 **낮추는** 시나리오만 있다. 연구를 바로 끝내는 모드는 없다 |
| 국가 관계 | `SR2030 Save Editor` | 게임 밖 프로그램. 저장 파일의 외교 관계와 조약을 고친다 |
| 군사력 | `World 2030 Battle Mod` | 전투서열을 늘렸지만 모든 나라가 대상이다 |
| 장비 생산 | 없음 | 생산 속도를 올리는 모드는 없다(`SPECIAL FORCES MOD` 의 한 부대만 하루) |
| 부대 스탯 | `World 2030 Battle Mod`, `Submarine Balance Mod`, `GCR + Unit Overhaul`, `Unit Overhaul WWII` | 모두 모든 지역에 적용되는 균형 조정이다. 플레이어의 부대만 강하게 하는 것은 없다 |
| 인구 | 없음 | – |
| GDP | 없음 | `Unofficial External Trainer` 가 바꿀 수 있을지는 설명만으로 알 수 없다 |

정리하면, **내 플레이용 치트를 데이터 모드로 낸 사람은 아직 없다.** 진행 중인 게임의 값을 바꾸고 싶으면 내장 치트나 게임 밖 프로그램 둘이 있고, 새 게임의 시작 조건을 내게만 유리하게 바꾸는 모드(시작 국고, GDP, 내 장비의 수치)는 직접 만들어야 한다.

## 출처

- [Supreme Ruler 2030 Steam Workshop](https://steamcommunity.com/app/2093410/workshop/) — 구독자 순 목록, 2026-10-06
- 각 항목의 Workshop 페이지(표의 링크)
