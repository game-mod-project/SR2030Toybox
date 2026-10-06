from dataclasses import replace

import pytest

from srkit import probe

# CRLF 와 CP1252 바이트(é = 0xE9)가 든 지역 데이터 대역
CVP = (b"&&CVP 1499\r\nregionname \"Allemagn\xe9\"\r\ngdpc 51203\r\n\r\n"
       b"&&CVP 1500\r\nregionname \"Other\"\r\ngdpc 51203\r\ntechlevel 110\r\n")


@pytest.fixture
def fake(cfg, tmp_path):
    game = tmp_path / "game"
    (game / "Maps").mkdir(parents=True)
    (game / "Maps" / "W2030.CVP").write_bytes(CVP)
    return replace(cfg, root=tmp_path / "proj", game_dir=game)


def test_changes_one_place_and_keeps_every_other_byte(fake):
    out = probe.make(fake, "cvp", "Maps/W2030.CVP", "gdpc 51203", "gdpc 99999", after="&&CVP 1500")
    assert out == fake.build_dir / "probe-cvp" / "Maps" / "W2030.CVP"
    assert out.read_bytes() == CVP[:CVP.rindex(b"gdpc 51203")] + b"gdpc 99999" + b"\r\ntechlevel 110\r\n"
    assert (fake.game_dir / "Maps" / "W2030.CVP").read_bytes() == CVP          # 게임 폴더는 그대로


def test_without_an_anchor_the_text_must_be_unique(fake):
    out = probe.make(fake, "tech", "Maps/W2030.CVP", "techlevel 110", "techlevel 140")
    assert b"techlevel 140" in out.read_bytes()
    with pytest.raises(RuntimeError, match="2번 나옵니다"):
        probe.make(fake, "dup", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1")
    with pytest.raises(RuntimeError, match="0번 나옵니다"):
        probe.make(fake, "none", "Maps/W2030.CVP", "gdpc 7", "gdpc 1")
    assert not (fake.build_dir / "probe-dup").exists() and not (fake.build_dir / "probe-none").exists()


def test_anchor_must_be_unique_and_close(fake, monkeypatch):
    with pytest.raises(RuntimeError, match="기준 문자열이 2번"):
        probe.make(fake, "x", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1", after="&&CVP 1")
    with pytest.raises(RuntimeError, match="기준 문자열이 0번"):
        probe.make(fake, "x", "Maps/W2030.CVP", "gdpc 51203", "gdpc 1", after="&&CVP 777")
    monkeypatch.setattr(probe, "NEAR", 20)      # 기준 블록에 값이 없으면 다음 블록의 값을 바꾸지 않는다
    with pytest.raises(RuntimeError, match="안에 바꿀 문자열이 없습니다"):
        probe.make(fake, "x", "Maps/W2030.CVP", "techlevel 110", "techlevel 1", after="&&CVP 1499")
    assert not (fake.build_dir / "probe-x").exists()


def test_missing_game_file_is_refused(fake):
    with pytest.raises(RuntimeError, match="게임 폴더에 없는 파일"):
        probe.make(fake, "x", "Maps/NOPE.CVP", "a", "b")
