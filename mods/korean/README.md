# 한글화 모드 (korean)

게임에 `Localize\LOCALKO` 를 추가하는 MODS 유형 모드. 설계는 [docs/04](../../docs/04-korean-localization.md).

## 번역 테이블

`translation/*.csv` — 열은 `key,en,ko,status`. `ko` 를 비워 두면 게임에서 영어로 나온다.
`status` 는 `mt`(기계 번역 초안) 또는 `ok`(사람이 확인함)다. **검수할 때는 `mt` 행을 보고, 고치든 그대로 두든 `ok` 로 바꾼다.**
Excel 에서 열어 `status` 로 필터하면 된다(UTF-8 BOM 으로 저장되어 있다. 저장할 때 CSV UTF-8 형식을 유지할 것).

번역 규칙은 [STYLE.md](STYLE.md), 용어는 [glossary.csv](glossary.csv). 용어를 바꾸려면 용어집부터 고친다.

| 파일 | 내용 |
|---|---|
| `localtext-gui.csv` | 버튼·라벨 등 화면 문구. 키가 영어 원문이고 대소문자별로 행이 따로 있다 |
| `variables.csv` | 선택지·상태 이름 같은 목록형 문구 |
| `localtext-game.csv` | 명령, 조약, 훈련, 지형, 유닛 분류 |
| `localtext-start.csv` `localtext-tips.csv` | 시나리오 소개, 툴팁 |
| `localtext-ttr.csv` | 기술 이름·설명 |
| `localtext-regions.csv` | 지역 이름·소개 |
| `localtext-newsitems.csv` | 뉴스·이메일·보고 (가장 많다) |
| `custom.default.csv` | 사용자 시나리오 기본 문구 |
| `localtext-regions.extra.csv` | 영어판 현지화 파일에 없는 지역 이름. 한국어판에만 행으로 추가된다 |
| `scen.<시나리오>.<파일>.csv` | 시나리오 폴더 안의 전용 문구(Arena 6A 기술 이름, Battle of Russia 브리핑) |

지역 이름(`localtext-regions*.csv` 의 `…|0` 행)은 **한글 10자(30바이트)까지**만 화면에 나온다. `srkit check` 가 검사한다.
`uv run srkit tm-fill` 은 시나리오 테이블의 빈 행을 다른 테이블의 같은 원문 번역으로 채운다.

`uv run srkit extract` 를 다시 돌리면 게임 갱신으로 바뀐 원문을 반영하고, 기존 번역은 키 기준으로 유지한다.

## 화면에 영어로 남는 GUI 문구 찾기

GUI 사전의 키 목록은 공식 번역 5개 언어의 합집합이라, 공식 번역에서도 빠진 문구는 들어 있지 않다.
게임의 번역 검사로 찾는다(게임이 시작할 때 화면 정의의 문구를 모두 사전에 대 보고 로그를 쓴다).

```
uv run python scripts/gamedrive.py start -window -tcheck    # 메인 메뉴가 뜨면 로그는 이미 쓰여 있다
uv run srkit tcheck-import        # 저장 폴더의 LOG-TRANS-CHECK.log 를 읽는다 (경로를 줄 수도 있다)
uv run python scripts/gamedrive.py stop
```

`tcheck-import` 는 사전에 없는 문구를 [gui-keys-extra.csv](gui-keys-extra.csv)(문구, 처음 나온 화면)에 모으고
`localtext-gui.csv` 에 빈 행으로 넣는다. 대소문자만 다른 키가 이미 번역돼 있으면 그 번역으로 채운다.
그다음은 여느 미번역 행처럼 `mt-export` 로 번역한다. 번역하고 다시 설치한 뒤 한 번 더 돌려
"번역이 있는데 게임이 찾지 못한 문구"가 나오지 않으면 된 것이다.
개발용 화면(`BUILDERX`, `FONTTEST`)의 문구는 모으지 않는다. 로그 줄의 뜻은 [docs/03](../../docs/03-localization-internals.md).

## 기계 번역 초안 만들기

```
uv run srkit mt-export <테이블>          # 미번역 행 → build/mt/<테이블>~NNN.in.jsonl
(각 청크를 번역해 같은 이름의 .out.jsonl 로 저장: 한 줄에 {"key": ..., "ko": ...})
uv run srkit mt-check <청크.in.jsonl>    # 서식 토큰·금지 문자·빠진 행 검사
uv run srkit mt-import                   # 검사를 통과한 행만 테이블에 반영 (status=mt)
```

`ko` 가 빈 문자열인 행은 "일부러 번역하지 않음"이다(형식 코드, 약어 등). 이미 번역이 있는 행은 `--overwrite` 없이는 바뀌지 않는다.
청크를 번역하는 쪽(사람이든 에이전트든)이 따를 방법은 [MT-INSTRUCTIONS.md](MT-INSTRUCTIONS.md)에 있다.
게임이 갱신되어 원문이 늘면 `extract` → `mt-export` 로 새 행만 다시 뽑아 같은 절차를 밟는다.

검증: `uv run srkit check` (테이블 전체), 진행률: `uv run srkit stats`

## 검수할 때

- `uv run srkit consistency` — 같은 영어 원문이 서로 다르게 번역된 곳. 문맥이 달라 맞는 것도 있으니 하나씩 판단한다.
- 게임에서 글자가 깨져 보이는 자리(글자 수가 고정된 칸 등)는 키를 [notranslate.txt](notranslate.txt)에 추가한다. 그 키는 영어로 나온다.
- 고친 뒤: `uv run srkit check` → `uv run srkit build` → `uv run srkit deploy korean --apply` → 게임 재시작.
