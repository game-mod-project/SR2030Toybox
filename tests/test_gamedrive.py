"""scripts/gamedrive.py 가 자기가 띄운 게임만 다루는지 확인한다(게임은 띄우지 않는다)."""
import importlib.util
import io
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def gd():
    spec = importlib.util.spec_from_file_location("gamedrive", Path(__file__).parents[1] / "scripts" / "gamedrive.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_only_games_started_by_the_tool_are_touched(gd, cfg, tmp_path, monkeypatch):
    """사용자가 직접 켠 게임에 캡처·입력을 하면 창이 화면 밖으로 옮겨진다. 그런 일이 없어야 한다."""
    fake = replace(cfg, root=tmp_path)
    sleeper = [sys.executable, "-c", "import time; time.sleep(60)"]
    mine, theirs = subprocess.Popen(sleeper), subprocess.Popen(sleeper)     # 게임 프로세스 대역
    try:
        monkeypatch.setattr(gd, "game_pids", lambda: [mine.pid, theirs.pid])
        assert gd.owned_pids(fake) == set()
        gd.record_owned(fake, [mine.pid])
        assert gd.owned_pids(fake) == {mine.pid}

        monkeypatch.setattr(gd, "game_pids", lambda: [theirs.pid])           # 내 게임은 끝나고 사용자의 게임만 남음
        assert gd.owned_pids(fake) == set()
        with pytest.raises(SystemExit, match="띄운 것이 아닙니다"):
            gd.need_window(fake)

        # 프로세스 ID 가 재사용되어도 시작 시각이 다르면 내 것으로 치지 않는다
        (fake.build_dir / gd.OWNED_FILE).write_text(json.dumps({str(theirs.pid): gd.started_at(theirs.pid) - 1}))
        assert gd.owned_pids(fake) == set()

        monkeypatch.setattr(gd, "game_pids", lambda: [])
        with pytest.raises(SystemExit, match="게임 창이 없습니다"):
            gd.need_window(fake)
    finally:
        mine.kill()
        theirs.kill()


def test_key_names_with_modifiers(gd):
    assert gd.parse_key("ENTER") == ([], 0x0D)
    assert gd.parse_key("0x1B") == ([], 0x1B)
    assert gd.parse_key("27") == ([], 27)                    # 숫자는 지금처럼 가상 키 코드다
    assert gd.parse_key("s") == ([], 0x53)
    assert gd.parse_key("CTRL+SHIFT+S") == ([0x11, 0x10], 0x53)
    assert gd.parse_key("ctrl+enter") == ([0x11], 0x0D)
    with pytest.raises(SystemExit, match="모르는 수정키"):
        gd.parse_key("WIN+S")


def test_output_is_utf8_even_when_the_pipe_is_cp949(gd, cfg, monkeypatch):
    """파이프로 받으면 한국어 Windows 의 표준 출력은 CP949 다. shot 이 찍는 "–"(U+2013)는 CP949 에 없어 거기서 죽었다."""
    pipe = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
    monkeypatch.setattr(sys, "stdout", pipe)
    monkeypatch.setattr(gd.config, "load", lambda: cfg)
    monkeypatch.setattr(gd, "game_pids", lambda: [])            # 떠 있는 게임이 있어도 건드리지 않는다
    assert gd.main(["status"]) == 0
    print("밝기 0–255")                                         # shot 의 출력에 들어가는 글자
    pipe.flush()
    out = pipe.buffer.getvalue()
    assert "프로세스: 없음".encode("utf-8") in out
    assert "밝기 0–255".encode("utf-8") in out
