from dataclasses import replace
from pathlib import Path

import pytest

from srkit import deploy, korean, srtext, srutf8


def test_table_name():
    assert korean.table_name(Path("LocalText-Game.csv")) == "localtext-game.csv"
    assert korean.table_name(Path("CUSTOM/DEFAULT.GMT")) == "custom.default.csv"
    assert korean.scenario_table(Path("Scenario/Arena 6A/Localize/LOCALEN/Arena_localTTRX.csv")) \
        == "scen.arena-6a.arena_localttrx.csv"
    assert korean.scenario_table(Path("Scenario/Battle of Russia 2030/Localize/LOCALEN/Battle of Russia-Text.csv")) \
        == "scen.battle-of-russia-2030.battle-of-russia-text.csv"


def test_tm_fill_uses_unambiguous_translations_only(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path)
    Row = korean.Row
    korean.write_table(fake.translation_dir / "localtext-ttr.csv", {
        "TTRTEXT|37|0": Row("Cold Fusion", "상온 핵융합", "mt"),
        "TTRTEXT|1|0": Row("Patrol", "순찰", "mt"),
        "TTRTEXT|2|0": Row("Patrol", "초계", "mt"),
    })
    scen = fake.translation_dir / "scen.arena-6a.arena_localttrx.csv"
    korean.write_table(scen, {"TTRTEXT|37|0": Row("Cold Fusion"), "TTRTEXT|9|0": Row("Patrol"), "TTRTEXT|8|0": Row("New")})
    assert korean.tm_fill(fake) == 1
    rows = korean.read_table(scen)
    assert rows["TTRTEXT|37|0"] == Row("Cold Fusion", "상온 핵융합", "mt")
    assert rows["TTRTEXT|9|0"].ko == "" and rows["TTRTEXT|8|0"].ko == ""    # 번역이 갈리는 말, 없는 말은 그대로


def test_extra_region_names_cover_sandbox_regions_missing_from_localization(cfg, game_dir):
    extras = dict(korean.extra_region_names(cfg, known=set()))
    assert extras["REGIONTEXT|2314|0"] == "Falklands"
    assert "REGIONTEXT|2314|0" not in dict(korean.extra_region_names(cfg, known={"2314"}))


def test_patch_uisettings_puts_language_second():
    """옵션 화면이 앞의 6개 언어만 보여 주므로 영어 바로 다음에 넣는다. 끝에 들어 있던 것은 옮긴다."""
    text = 'langdirs, "LOCALEN", "LOCALPT", ""\r\nlangs, "English", "Portuguese", ""\r\nother, 1'
    want = 'langdirs, "LOCALEN", "LOCALKO", "LOCALPT", ""\r\nlangs, "English", "Korean", "Portuguese", ""\r\nother, 1'
    out = korean.patch_uisettings(text, "LOCALKO", "Korean")
    assert out == want
    assert korean.patch_uisettings(out, "LOCALKO", "Korean") == out
    appended = 'langdirs, "LOCALEN", "LOCALPT", "LOCALKO", ""\r\nlangs, "English", "Portuguese", "Korean", ""\r\nother, 1'
    assert korean.patch_uisettings(appended, "LOCALKO", "Korean") == want


def test_table_roundtrip_keeps_translations(tmp_path):
    Row = korean.Row
    path = tmp_path / "t.csv"
    korean.write_table(path, {"A|1|0": Row('He said, "hi"¶next', "안녕", "ok"), "A|2|0": Row("x")})
    assert korean.read_table(path) == {"A|1|0": Row('He said, "hi"¶next', "안녕", "ok"), "A|2|0": Row("x")}
    report = korean._merge(path, [("A|1|0", "changed source", ), ("A|3|0", "new")])
    assert report.changed == ["A|1|0"] and report.removed == ["A|2|0"]
    assert (report.translated, report.reviewed) == (1, 0)
    # 원문이 바뀌면 번역은 남기되 다시 검수 대상(mt)으로 돌린다
    assert korean.read_table(path)["A|1|0"] == Row("changed source", "안녕", "mt")


def test_old_three_column_table_reads_as_draft(tmp_path):
    path = tmp_path / "old.csv"
    path.write_text("key,en,ko\nA|1|0,Hello,안녕\nA|2|0,Bye,\n", encoding="utf-8-sig")
    assert korean.read_table(path) == {"A|1|0": korean.Row("Hello", "안녕", "mt"), "A|2|0": korean.Row("Bye")}


def test_inconsistencies_ignore_case_and_group_by_translation(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path)
    korean.write_table(fake.translation_dir / "a.csv", {
        "G|ACTIVATE": korean.Row("ACTIVATE", "활성화", "mt"),
        "G|Activate": korean.Row("Activate ", "켜기", "mt"),
        "G|Cancel": korean.Row("Cancel", "취소", "mt"),
        "G|CANCEL": korean.Row("CANCEL", "취소", "mt"),
    })
    assert korean.inconsistencies(fake) == [("activate", {"활성화": ["a:G|ACTIVATE"], "켜기": ["a:G|Activate"]})]


def test_notranslate_keys_are_skipped_and_reported(cfg, tmp_path):
    fake = replace(cfg, root=tmp_path)
    table = fake.translation_dir / "variables.csv"
    korean.write_table(table, {
        "LOCALIZE|monthsinyearsh|6": korean.Row("Jul", "7월", "mt"),
        "LOCALIZE|monthsinyearl|6": korean.Row("July", "7월", "mt"),
    })
    assert korean.notranslate(fake) is None and korean.check(fake) == []
    (fake.korean_mod_dir / "notranslate.txt").write_text(
        "# 설명 줄\n\n^LOCALIZE\\|monthsinyearsh\\|   # 3바이트로 잘림\n", encoding="utf-8")
    skip = korean.notranslate(fake)
    assert korean._translations(table, skip) == {"LOCALIZE|monthsinyearl|6": "7월"}
    assert korean.check(fake) == ["variables.csv: LOCALIZE|monthsinyearsh|6: 번역 금지 키(notranslate.txt)"]


def test_problem_detects_what_breaks_in_game():
    assert korean.problem("%s attacks %s", "%s이(가) %s 공격") is None
    assert korean.problem("Say %s", '"%s" 라고 말함')                     # 큰따옴표
    assert korean.problem("%d of %s", "%s 중 %d")                         # 서식 순서 바뀜
    assert korean.problem("Line one¶Line two", "한 줄로 합침")            # 줄바꿈 기호 누락
    assert korean.problem("\\42 Germany is", "\\42독일은")                # 코드 뒤 공백 누락
    assert korean.problem("\\42 Germany is", "\\42 독일은") is None
    # 지역 이름은 30바이트(한글 10자)까지만 화면에 나온다. 설명문(|1)에는 제한이 없다
    long_name = "프린스에드워드아일랜드"
    assert korean.problem("Prince Edward Island", long_name, "localtext-regions.csv|REGIONTEXT|2410|0")
    assert korean.problem("Prince Edward Island", "프린스에드워드섬", "localtext-regions.csv|REGIONTEXT|2410|0") is None
    assert korean.problem("Prince Edward Island", long_name, "localtext-regions.csv|REGIONTEXT|2410|1") is None
    # 시나리오 전용 파일의 같은 키는 소개문이다(이름 칸이 비어 있음)
    assert korean.problem("Briefing", long_name, "scen.x.y.csv|REGIONTEXT|801|0") is None
    # 인코딩이 담지 못하는 문자(한자 일부)
    assert "聖" in korean.problem("the holy day", "성일(聖日)")
    assert korean.problem("the holy day", "성일") is None


def test_build_text_applies_translation_in_sr_utf8(cfg, game_dir, tmp_path):
    tr = tmp_path / "translation"
    korean.write_table(tr / "localtext-game.csv", {"ORDERSTEXT|1|0": korean.Row("MOVE TO", "이동 — 북부", "mt")})
    korean.write_table(tr / korean.GUI_TABLE, {"GUITRANS|Accept": korean.Row("Accept", "수락", "mt")})
    korean.write_table(tr / korean.EXTRA_REGIONS_TABLE,
                       {"REGIONTEXT|2314|0": korean.Row("Falklands", "포클랜드 제도", "mt")})
    korean.write_table(tr / "scen.arena-6a.arena_localttrx.csv",
                       {"TTRTEXT|37|0": korean.Row("Cold Fusion", "상온 핵융합", "mt")})
    fake = replace(cfg, root=tmp_path)  # translation_dir = tmp/mods/korean/translation
    (tmp_path / "mods" / "korean").mkdir(parents=True)
    tr.rename(fake.translation_dir)
    root = tmp_path / "out"
    out = root / "Localize" / "LOCALKO"
    applied, used = korean.build_text(fake, root)
    assert applied == 4 and "북" in used
    # 영어판에 없는 지역 이름은 REGIONTEXT 섹션 끝(&&END 앞)에 행으로 더해진다
    regions = srutf8.decode((out / "LocalText-Regions.csv").read_bytes()).split("\n")
    at = regions.index('2314, "포클랜드 제도"')
    assert regions[at + 1].startswith("&&END") and regions[at - 1][0].isdigit()
    # 시나리오 폴더 안의 현지화 파일은 같은 자리의 대상 언어 폴더로 나온다
    arena = root / "Scenario" / "Arena 6A" / "Localize" / "LOCALKO" / "Arena_localTTRX.csv"
    assert '37, "상온 핵융합", "",' in srutf8.decode(arena.read_bytes())
    game = (out / "LocalText-Game.csv").read_bytes()
    assert 0xB6 not in srutf8.encode("북")           # 인코딩이 줄바꿈 바이트를 피한다
    text = srutf8.decode(game)
    assert '1, "이동 - 북부"' in text                  # 문장부호 정규화 포함
    assert srtext.parse(text).sections()[0] == "ORDERSTEXT"
    assert srutf8.decode((out / korean.GUI_NAME).read_bytes()).splitlines()[2] == '"Accept", "수락", '
    # 번역하지 않은 파일은 원문 그대로(줄바꿈 기호는 단일 바이트 유지)
    news = (out / "LocalText-NEWSITEMS.csv").read_bytes()
    assert news.count(b"\xb6") > 1000 and b"\xc2\xb6" not in news


def test_deploy_and_undeploy_restore_game_folder(cfg, tmp_path):
    game, root = tmp_path / "game", tmp_path / "proj"
    (game / "INI").mkdir(parents=True)
    (game / deploy.GAME_EXE).write_bytes(b"exe")
    (game / "INI" / "UISettings.csv").write_text("orig")
    mod = root / "build" / "korean"
    (mod / "INI").mkdir(parents=True)
    (mod / "Localize" / "LOCALKO").mkdir(parents=True)
    (mod / "INI" / "UISettings.csv").write_text("patched")
    (mod / "Localize" / "LOCALKO" / "a.csv").write_text("ko")
    fake = replace(cfg, root=root, game_dir=game)

    deploy.deploy(fake, "korean")                      # 미리보기는 아무것도 바꾸지 않는다
    assert (game / "INI" / "UISettings.csv").read_text() == "orig"
    assert not (game / "Localize").exists()

    deploy.deploy(fake, "korean", apply=True)
    assert (game / "INI" / "UISettings.csv").read_text() == "patched"
    assert (game / "Localize" / "LOCALKO" / "a.csv").read_text() == "ko"
    (mod / "INI" / "UISettings.csv").write_text("patched2")
    deploy.deploy(fake, "korean", apply=True)          # 재설치해도 백업은 최초 원본을 유지
    assert (game / "INI" / "UISettings.csv").read_text() == "patched2"

    deploy.undeploy(fake, "korean", apply=True)
    assert (game / "INI" / "UISettings.csv").read_text() == "orig"
    assert not (game / "Localize").exists()
    assert sorted(p.name for p in game.iterdir()) == ["INI", deploy.GAME_EXE]


def test_deploy_refuses_while_the_game_is_running(cfg, tmp_path, monkeypatch):
    """실행 중에는 훅 DLL 이 잠겨 있다. 텍스트만 바뀌면 DLL 과 짝이 안 맞아 글자가 깨지므로 아무것도 바꾸지 않는다."""
    game, root = tmp_path / "game", tmp_path / "proj"
    (game / "INI").mkdir(parents=True)
    (game / deploy.GAME_EXE).write_bytes(b"exe")
    (game / "INI" / "UISettings.csv").write_text("orig")
    (root / "build" / "korean" / "INI").mkdir(parents=True)
    (root / "build" / "korean" / "INI" / "UISettings.csv").write_text("patched")
    fake = replace(cfg, root=root, game_dir=game)
    assert not deploy.game_running(fake)               # 다른 폴더의 게임이 떠 있어도 이 폴더의 게임은 아니다

    monkeypatch.setattr(deploy, "game_running", lambda _cfg: True)
    assert deploy.deploy(fake, "korean")[0] == "교체(원본 백업): INI/UISettings.csv"     # 미리보기는 된다
    with pytest.raises(RuntimeError, match="실행 중"):
        deploy.deploy(fake, "korean", apply=True)
    assert (game / "INI" / "UISettings.csv").read_text() == "orig"
    monkeypatch.setattr(deploy, "game_running", lambda _cfg: False)
    deploy.deploy(fake, "korean", apply=True)
    monkeypatch.setattr(deploy, "game_running", lambda _cfg: True)
    with pytest.raises(RuntimeError, match="실행 중"):
        deploy.undeploy(fake, "korean", apply=True)
    assert (game / "INI" / "UISettings.csv").read_text() == "patched"
