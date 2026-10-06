from dataclasses import replace

import pytest

from srkit import cheats

DOC = (
    "# 07. 내장 치트\n\n"
    "조사 기준: Steam appid `2093410`, build `21347933`, 2026-10-06.\n\n"
    "게임에는 `cheat <이름>` 꼴의 명령이 들어 있다.\n\n"       # 일반 표기는 명령이 아니다
    "2. 입력란에 `cheat allowcheats` 를 넣는다.\n\n"
    "| 명령 | 인자 | 효과 |\n|---|---|---|\n"
    "| `cheat treasury` | 금액 | 국고 |\n"
    "| `cheat e=mc2` | – | 연구 |\n"
    "| `cheat charge!` | – | 충전 |\n"
    "\n`cheat devcheat` 는 `allowcheats` `q` 를 한꺼번에 켠다.\n"
)
HOTKEYS = (b"// Key Code,Stage,Modifier,Action Val\r\n&&HOTKEYS,,,\r\n"
           b"0x53,0,2,1181,,,,43,Save Player Settings,<Shift> + <S>\r\n"
           b"0x53,0,4,1115,,,,,Game Settings,<Ctrl> + <Shift> + <S>,,,S\r\n")


def fake(cfg, tmp_path, exe: bytes, hotkeys: bytes = HOTKEYS, buildid: str | None = "21347933"):
    steamapps = tmp_path / "lib" / "steamapps"
    game = steamapps / "common" / "Supreme Ruler 2030"
    (game / "INI").mkdir(parents=True)
    (game / "SupremeRuler2030.exe").write_bytes(exe)
    (game / "INI" / "hotkeys.csv").write_bytes(hotkeys)
    (game / "steam_appid.txt").write_text("2093410")
    if buildid:
        (steamapps / "appmanifest_2093410.acf").write_text(f'"AppState"\n{{\n\t"appid"\t\t"2093410"\n\t"buildid"\t\t"{buildid}"\n}}\n')
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "07-cheats.md").write_text(DOC, encoding="utf-8")
    return replace(cfg, root=root, game_dir=game)


def exe_with(*names: str) -> bytes:
    return b"\0junk\0" + b"\0".join(b"cheat " + n.encode("ascii") for n in names) + b"\0more junk cheater\0"


def test_names_come_from_the_executable_strings():
    assert cheats.names_in(exe_with("treasury", "e=mc2", "charge!", "treasury")) == ["charge!", "e=mc2", "treasury"]
    assert cheats.names_in(b"no commands here") == []


def test_documented_names_are_the_backticked_commands():
    assert cheats.documented(DOC) == {"allowcheats", "treasury", "e=mc2", "charge!", "devcheat"}
    assert cheats.documented_build(DOC) == "21347933"


def test_nothing_to_report_when_the_game_matches_the_document(cfg, tmp_path):
    r = cheats.check(fake(cfg, tmp_path, exe_with("allowcheats", "treasury", "e=mc2", "charge!", "devcheat")))
    assert r.removed == [] and r.added == [] and r.settings_hotkey and r.build == r.doc_build == "21347933"
    assert r.ok


def test_removed_and_added_commands_are_reported(cfg, tmp_path):
    """게임이 업데이트되어 치트가 사라지거나 새로 생긴 경우."""
    r = cheats.check(fake(cfg, tmp_path, exe_with("allowcheats", "treasury", "newcheat"), buildid="22000000"))
    assert r.removed == ["charge!", "devcheat", "e=mc2"]
    assert r.added == ["newcheat"]
    assert r.build == "22000000" and r.doc_build == "21347933"
    assert not r.ok


def test_missing_settings_hotkey_is_reported(cfg, tmp_path):
    """치트 입력란이 있는 Game Settings 창의 단축키 행이 사라진 경우."""
    r = cheats.check(fake(cfg, tmp_path, exe_with("allowcheats", "treasury", "e=mc2", "charge!", "devcheat"),
                          hotkeys=b"&&HOTKEYS,,,\r\n0x53,0,2,1181,,,,43,Save Player Settings,<Shift> + <S>\r\n"))
    assert r.removed == [] and not r.settings_hotkey and not r.ok


def test_build_change_alone_is_not_a_failure(cfg, tmp_path):
    """빌드만 바뀌고 목록이 같으면 알려 주기만 한다. 설치 정보가 없어도 죽지 않는다."""
    same = exe_with("allowcheats", "treasury", "e=mc2", "charge!", "devcheat")
    assert cheats.check(fake(cfg, tmp_path / "a", same, buildid="22000000")).ok
    r = cheats.check(fake(cfg, tmp_path / "b", same, buildid=None))
    assert r.build is None and r.ok


def test_refuses_a_folder_without_the_game(cfg, tmp_path):
    with pytest.raises(RuntimeError, match="게임 폴더가 아닙니다"):
        cheats.check(replace(cfg, root=tmp_path, game_dir=tmp_path / "nowhere"))


def test_installed_game_still_has_every_documented_cheat(game_dir, cfg):
    """설치된 게임과 docs/07 의 치트 목록이 같은가. 게임이 업데이트되어 치트가 바뀌면 여기서 걸린다."""
    r = cheats.check(cfg)
    assert r.ok, ("게임의 내장 치트가 문서와 달라졌다(게임 업데이트?). "
                  f"사라진 것 {r.removed}, 새로 생긴 것 {r.added}, 설정 창 단축키 {r.settings_hotkey}, "
                  f"빌드 {r.build} (문서 {r.doc_build}). docs/09 의 '게임 업데이트 대비'를 보라")
