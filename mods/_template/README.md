# 모드 골격

새 모드를 시작할 때 이 폴더를 `mods/<모드이름>/` 으로 복사한다. 모드 유형과 로드 순서는 [docs/02](../../docs/02-modding-system.md).

```
mods/<모드이름>/
  README.md      무엇을 바꾸는 모드인지, 대상 게임 빌드
  files/         게임 설치 폴더와 같은 구조로 파일을 둔다 (MODS 유형)
    INI/…
    Localize/LOCALEN/…
    Graphics/…
    Sandbox/<시나리오>/…     특정 시나리오에만 적용할 덮어쓰기
```

## 시험과 배포

1. `files/` 의 내용을 `build/<모드이름>/` 으로 복사한다(가공이 필요 없으면 그대로).
2. `uv run srkit deploy <모드이름>` 으로 무엇이 추가·교체되는지 보고, `--apply` 로 게임 폴더에 설치한다.
3. 게임에서 확인한 뒤 `uv run srkit undeploy <모드이름> --apply` 로 되돌린다.
4. 배포는 Steam 도구의 Workshop Uploader 에서 유형 MODS, 루트 폴더로 `build/<모드이름>` 을 지정한다.

## 알아 둘 것

- 게임 데이터는 CP1252 텍스트다. 편집기가 UTF-8 로 저장하지 않게 한다.
- `Maps\DATA\DEFAULT.*` 같은 원본 데이터를 바꾸면 `Cache\*.SAV` 와 어긋날 수 있다(캐시 재생성 필요 여부는 게임에서 확인).
- 새 시나리오는 MODS 가 아니라 MAPS 유형이다: `<이름>.scenario` + `<이름>\` 폴더.
- DLL·실행 파일은 Workshop 으로 배포되지 않는다.
