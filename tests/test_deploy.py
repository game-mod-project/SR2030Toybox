"""겹치는 모드: 한 게임 파일은 한 모드만 쥔다. 임시 폴더만 쓴다(실제 게임 폴더에는 설치하지 않는다)."""
import json
from dataclasses import replace

import pytest

from srkit import deploy, probe

ORIG = b"gdpc 51203\r\n"
X = "Maps/W2030.CVP"


@pytest.fixture
def fake(cfg, tmp_path):
    game = tmp_path / "game"
    (game / "Maps").mkdir(parents=True)
    (game / deploy.GAME_EXE).write_bytes(b"exe")
    (game / X).write_bytes(ORIG)
    return replace(cfg, root=tmp_path / "proj", game_dir=game)


def build(cfg, mod: str, files: dict[str, bytes]) -> None:
    for rel, data in files.items():
        path = cfg.build_dir / mod / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_a_second_mod_cannot_take_a_file_another_mod_holds(fake):
    """A 설치 → B 설치 → A 제거 → B 제거 순서로 게임 폴더에 A 의 파일이 남던 문제. B 의 설치를 거부한다."""
    build(fake, "a", {X: b"A\r\n", "Maps/a-only.txt": b"a"})
    build(fake, "b", {X: b"B\r\n", "Maps/b-only.txt": b"b"})
    deploy.deploy(fake, "a", apply=True)
    with pytest.raises(RuntimeError, match=r"Maps/W2030\.CVP \(모드 a\)"):       # 어떤 파일이 어떤 모드와 겹치는지 알려 준다
        deploy.deploy(fake, "b", apply=True)
    assert (fake.game_dir / X).read_bytes() == b"A\r\n"
    assert not (fake.game_dir / "Maps" / "b-only.txt").exists()            # 겹치지 않는 파일도 설치하지 않는다
    assert not (fake.build_dir / ".deploy" / "b").exists()

    deploy.undeploy(fake, "a", apply=True)
    assert (fake.game_dir / X).read_bytes() == ORIG
    deploy.deploy(fake, "b", apply=True)                                   # A 를 제거한 뒤에는 된다
    assert (fake.game_dir / X).read_bytes() == b"B\r\n"
    deploy.undeploy(fake, "b", apply=True)
    assert (fake.game_dir / X).read_bytes() == ORIG
    assert sorted(p.name for p in (fake.game_dir / "Maps").iterdir()) == ["W2030.CVP"]


def test_preview_shows_the_overlap_and_changes_nothing(fake):
    build(fake, "a", {X: b"A\r\n"})
    build(fake, "b", {"maps/w2030.cvp": b"B\r\n", "maps/b-only.txt": b"b"})    # 대소문자가 달라도 같은 파일이다
    deploy.deploy(fake, "a", apply=True)
    log = deploy.deploy(fake, "b")
    assert "겹침: maps/w2030.cvp — 설치된 모드 a 가 쥐고 있는 파일" in log
    assert "추가: maps/b-only.txt" in log
    assert "설치할 수 없습니다" in log[-1] and "srkit undeploy a --apply" in log[-1]
    assert (fake.game_dir / X).read_bytes() == b"A\r\n"


def test_the_same_content_is_still_an_overlap(fake):
    """내용이 같아 지금은 바꿀 것이 없어도, 한쪽을 제거하면 다른 쪽이 설치한 줄 아는 파일이 원본으로 돌아간다."""
    build(fake, "a", {X: b"A\r\n"})
    build(fake, "b", {X: b"A\r\n"})
    deploy.deploy(fake, "a", apply=True)
    with pytest.raises(RuntimeError, match="한 파일은 한 모드만"):
        deploy.deploy(fake, "b", apply=True)


def test_reinstalling_the_same_mod_is_not_an_overlap(fake):
    build(fake, "a", {X: b"A\r\n"})
    deploy.deploy(fake, "a", apply=True)
    build(fake, "a", {X: b"A2\r\n"})
    assert deploy.deploy(fake, "a", apply=True)[0] == f"갱신: {X}"
    deploy.undeploy(fake, "a", apply=True)
    assert (fake.game_dir / X).read_bytes() == ORIG


def test_undeploy_refuses_when_two_install_records_share_a_file(fake):
    """겹침 검사가 생기기 전에 겹쳐 설치된 상태. 어느 쪽의 백업이 원본인지 알 수 없으므로 어느 쪽도 되돌리지 않는다."""
    build(fake, "a", {X: b"A\r\n"})
    deploy.deploy(fake, "a", apply=True)
    state = fake.build_dir / ".deploy" / "b"                # 예전 도구가 남겼을 내역: b 가 a 의 파일을 백업하고 교체했다
    (state / "backup" / "Maps").mkdir(parents=True)
    (state / "backup" / X).write_bytes(b"A\r\n")
    (state / "manifest.json").write_text(json.dumps({"added": [], "replaced": [X]}), encoding="utf-8")
    (fake.game_dir / X).write_bytes(b"B\r\n")

    for mod, other in (("a", "b"), ("b", "a")):
        log = deploy.undeploy(fake, mod)
        assert log[0] == f"겹침: {X} — 설치된 모드 {other} 도 쥐고 있는 파일" and "제거할 수 없습니다" in log[-1]
        with pytest.raises(RuntimeError, match="어느 쪽의 백업이 원본인지"):
            deploy.undeploy(fake, mod, apply=True)
    assert (fake.game_dir / X).read_bytes() == b"B\r\n"
    assert (fake.build_dir / ".deploy" / "a" / "manifest.json").is_file() and (state / "manifest.json").is_file()


def test_probe_refuses_a_file_an_installed_mod_holds(fake):
    """설치된 모드가 바꾼 파일은 원본이 아니다. 그것을 읽어 시험 모드를 만들면 변경이 겹친다."""
    build(fake, "a", {X: b"gdpc 7\r\n"})
    deploy.deploy(fake, "a", apply=True)
    with pytest.raises(RuntimeError, match="설치된 모드 a"):
        probe.make(fake, "x", "maps/w2030.cvp", "gdpc 7", "gdpc 8")
    assert not (fake.build_dir / "probe-x").exists()
    deploy.undeploy(fake, "a", apply=True)
    out = probe.make(fake, "x", X, "gdpc 51203", "gdpc 8")
    assert out.read_bytes() == b"gdpc 8\r\n"
