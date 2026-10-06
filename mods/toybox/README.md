# ToyBox — 게임 안 모드 설정 창

Supreme Ruler 2030 의 싱글플레이에서 쓰는 치트 창이다. 게임 화면 위에 창을 띄우고, 창의 단추가 게임의 내장 치트를 대신 넣는다.
설정은 플레이어가 지금 플레이 중인 국가에만 적용된다(게임이 플레이어에게만 적용하는 치트만 넣었다).

- 소스: `native/srtoybox/` (C++, Dear ImGui). 이 폴더에는 설명만 있다 — 모드의 파일은 DLL 하나다.
- 빌드: `uv run srkit toybox-build` → `build/toybox/srtoybox.dll`
- 설치: `uv run srkit deploy toybox --apply` (게임 폴더에 `srtoybox.dll` 한 개를 추가한다). 제거는 `undeploy`.
- **한글화 모드가 설치되어 있어야 동작한다.** 한글화의 훅(`WTSAPI32.dll`)이 이 DLL 을 불러온다.
- Workshop 으로는 배포할 수 없다(DLL 은 게임의 파일 로더를 거치지 않는다).

쓰는 법, 기능 목록, 한계는 [docs/10-toybox.md](../../docs/10-toybox.md).
