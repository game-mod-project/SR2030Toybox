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


class FakeUser32:
    """held() 와 key 명령이 부르는 user32 함수의 대역. 게임에 닿는 호출을 부른 순서대로 적어 둔다."""

    def __init__(self, attach_ok: bool = True):
        self.attach_ok, self.calls = attach_ok, []

    def GetWindowThreadProcessId(self, hwnd, pid):
        return 77

    def AttachThreadInput(self, me, target, on):
        self.calls.append(("attach" if on else "detach",))
        return int(self.attach_ok)

    def GetKeyboardState(self, state):
        return 1

    def SetKeyboardState(self, state):
        self.calls.append(("state", tuple(vk for vk in (0x10, 0x11, 0x12) if state[vk] & 0x80)))
        return 1

    def PostMessageW(self, hwnd, msg, wparam, lparam):
        self.calls.append(({0x100: "down", 0x101: "up"}[msg], wparam))
        return 1


@pytest.fixture
def fake_user32(gd, monkeypatch):
    fake = FakeUser32()
    monkeypatch.setattr(gd, "user32", fake)
    monkeypatch.setattr(gd.time, "sleep", lambda seconds: None)
    return fake


def test_combo_key_holds_the_modifiers_around_the_body(gd, fake_user32):
    with gd.held(1, [0x11, 0x10]):
        fake_user32.calls.append(("body",))
    assert fake_user32.calls == [("attach",), ("down", 0x11), ("down", 0x10), ("state", (0x10, 0x11)), ("body",),
                                 ("up", 0x10), ("up", 0x11), ("state", ()), ("detach",)]


def test_combo_key_is_not_sent_when_the_game_thread_cannot_be_attached(gd, cfg, fake_user32, monkeypatch, capsys):
    """붙지 못하면 수정키 없이 맨 키만 전달된다(CTRL+SHIFT+S 가 S = 보급 지도가 된다). 보내지 않고 실패로 끝낸다."""
    fake_user32.attach_ok = False
    monkeypatch.setattr(gd.config, "load", lambda: cfg)
    monkeypatch.setattr(gd, "need_window", lambda cfg: (1, 0, 0))
    with pytest.raises(SystemExit, match="붙지 못했습니다"):
        gd.main(["key", "CTRL+SHIFT+S"])
    assert [call for call in fake_user32.calls if call[0] in ("down", "up", "state")] == []
    assert "키 CTRL" not in capsys.readouterr().out             # 성공한 것처럼 찍지 않는다


def test_modifiers_are_released_even_when_the_body_fails(gd, fake_user32):
    """본문에서 예외가 나도(Ctrl+C, 시간 초과) 화면 밖 게임에 수정키가 눌린 채 남지 않는다."""
    with pytest.raises(KeyboardInterrupt):
        with gd.held(1, [0x11, 0x10]):
            raise KeyboardInterrupt
    assert fake_user32.calls[-4:] == [("up", 0x10), ("up", 0x11), ("state", ()), ("detach",)]


class FakeDesktop:
    """앞 창을 다루는 user32 함수의 대역. 이 PC 에서 잰 대로 흉내 낸다(docs/04 의 "포커스", 2026-10-10):
    다른 프로세스는 입력을 낸 직후에만 앞 창을 바꿀 수 있다 — 앞 창의 스레드에 입력을 붙이는 것으로는 안 된다."""
    USER, MAIN, VIDEO, SHELL = 0x100, 0x200, 0x300, 0x900     # 쓰던 창, 게임의 본 창, 게임의 인트로 영상 창(더 크다), 바탕 화면
    GAME_PID, USER_PID = 4242, 7

    def __init__(self, foreground: int, movable: bool = True):
        self.foreground, self.movable = foreground, movable
        self.armed, self.calls = False, []

    def GetForegroundWindow(self):
        return self.foreground

    def GetShellWindow(self):
        return self.SHELL

    def IsWindow(self, hwnd):
        return int(hwnd in (self.USER, self.MAIN, self.VIDEO, self.SHELL))

    def GetWindowThreadProcessId(self, hwnd, pid):
        if pid is not None:
            pid._obj.value = self.GAME_PID if hwnd in (self.MAIN, self.VIDEO) else self.USER_PID
        return 77

    def GetSystemMetrics(self, index):
        return 1920 if index == 78 else 0

    def GetWindowRect(self, hwnd, rect):
        rect._obj.left = 5000                                 # 이미 화면 밖이다
        return 1

    def SetWindowPos(self, *args):
        return 1

    def AttachThreadInput(self, me, target, on):
        return 1

    def SendInput(self, count, inputs, size):
        self.calls.append("input")
        self.armed = True
        return count

    def SetForegroundWindow(self, hwnd):
        ok = self.armed and self.movable
        self.armed = False
        self.calls.append(("set", hwnd, ok))
        if ok:
            self.foreground = hwnd
        return int(ok)

    def LockSetForegroundWindow(self, code):
        self.calls.append(("lock", code))
        return 1


def watch(gd, monkeypatch, desk: FakeDesktop, previous: int, largest: int = FakeDesktop.VIDEO) -> None:
    """keep_hidden 을 가짜 바탕 화면에서 잠깐 돌린다. 게임의 가장 큰 창은 largest 다."""
    monkeypatch.setattr(gd, "user32", desk)
    monkeypatch.setattr(gd.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(gd, "game_window", lambda pids=None: (largest, "Supreme Ruler 2030", (1044, 811)))
    gd.keep_hidden(lambda: {desk.GAME_PID}, previous, settle=0.05, watch=0.2)


def test_focus_goes_back_to_the_window_the_user_was_using(gd, monkeypatch, capsys):
    """게임이 뜨면서 포커스를 가져가면 쓰던 창에 돌려준다 — 실제로 넘어갔을 때만 "돌려줌"으로 센다."""
    desk = FakeDesktop(foreground=FakeDesktop.VIDEO)
    watch(gd, monkeypatch, desk, previous=desk.USER)
    assert desk.foreground == desk.USER
    out = capsys.readouterr().out
    assert "포커스 돌려줌 1회" in out and "포커스는 다른 창에 있음" in out and "돌려주지 못함" not in out


def test_focus_is_taken_back_from_any_window_of_the_game(gd, monkeypatch):
    """게임은 창이 둘이다(본 창과 인트로 영상 창). 가장 큰 창이 아닌 쪽이 포커스를 쥐어도 돌려준다 —
    가장 큰 창만 보던 때에는 시도조차 하지 않아 게임이 포커스를 쥔 채로 남았다."""
    desk = FakeDesktop(foreground=FakeDesktop.MAIN)
    watch(gd, monkeypatch, desk, previous=desk.USER, largest=desk.VIDEO)
    assert desk.foreground == desk.USER


def test_focus_goes_to_the_desktop_when_no_window_was_in_front(gd, monkeypatch):
    """시작할 때 앞 창이 없었으면(직전에 포커스를 쥔 게임을 껐다) 바탕 화면에 넘긴다 — 보이지 않는 게임이 키 입력을 받지 않게."""
    desk = FakeDesktop(foreground=FakeDesktop.MAIN)
    watch(gd, monkeypatch, desk, previous=0, largest=desk.MAIN)
    assert desk.foreground == desk.SHELL


def test_a_focus_that_could_not_be_given_back_is_not_counted_as_given(gd, monkeypatch, capsys):
    desk = FakeDesktop(foreground=FakeDesktop.VIDEO, movable=False)
    watch(gd, monkeypatch, desk, previous=desk.USER)
    out = capsys.readouterr().out
    assert desk.foreground == desk.VIDEO
    assert "포커스 돌려줌 0회" in out and "돌려주지 못함" in out and "게임이 포커스를 쥐고 있음" in out


def test_the_foreground_is_locked_before_the_game_is_started(gd, cfg, monkeypatch, capsys):
    """이 도구를 띄운 앱이 앞 창이면 게임이 뜨자마자 포커스를 가져간다. 띄우기 전에 앞 창 잠금을 걸고, 지켜보기가 끝나면 푼다."""
    desk = FakeDesktop(foreground=FakeDesktop.USER)

    class Game:
        pid = FakeDesktop.GAME_PID

        def poll(self):
            return None

    def launch(*args, **kwargs):
        desk.calls.append("launch")
        return Game()

    monkeypatch.setattr(gd, "user32", desk)
    monkeypatch.setattr(gd.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(gd.subprocess, "Popen", launch)
    monkeypatch.setattr(gd, "record_owned", lambda cfg, pids: None)
    monkeypatch.setattr(gd, "game_window", lambda pids=None: (desk.MAIN, "Supreme Ruler 2030", (1024, 768)))
    monkeypatch.setattr(gd, "keep_hidden", lambda pids, previous, **kwargs: desk.calls.append("watch"))
    gd.start_in_background(cfg, cfg.game_dir / gd.EXE, ["-window"])
    assert desk.calls == [("lock", 1), "launch", "watch", ("lock", 2)]
    assert "앞 창 잠금" in capsys.readouterr().out


def test_peek_reads_tech_opinion_and_the_relation_with_one_region(gd):
    """peek 은 더 쓰는 값도 읽는다: 그 지역의 기술 수준 · 여론, 그리고 플레이어가 아닌 지역이면 둘 사이의 관계 여섯 칸.
    못 찾은 묶음(자리 0)의 값은 결과에 없다. 읽기만 한다."""
    import ctypes
    import struct

    from toybox_fake_game import MORE, FakeGame

    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.set_tech(176, 130.0)
    fake.set_tech(141, 128.0)
    fake.set_opinion(176, (0.5, 0.25, 0.75))
    fake.set_relation(176, 141, (0.25, -0.5, 0.75))           # 독일 객체의 표에서 폴란드의 칸
    fake.set_relation(141, 176, (0.125, 0.5, 1.0))            # 폴란드 객체의 표에서 독일의 칸
    before = fake.snapshot(176) + fake.snapshot(141)

    def read(address: int, fmt: str):
        return struct.unpack(fmt, ctypes.string_at(address, struct.calcsize(fmt)))[0]

    germany, poland = fake.where[176], fake.where[141]
    assert gd.peek_more(read, MORE, germany, 176, germany) == {"tech": 130.0, "opinion": [0.5, 0.25, 0.75]}
    assert gd.peek_more(read, MORE, germany, 176, poland) == {
        "tech": 128.0, "opinion": [0.0, 0.0, 0.0], "relations": {"mine": [0.25, -0.5, 0.75], "theirs": [0.125, 0.5, 1.0]}}
    assert gd.peek_more(read, {**MORE, "tech": 0, "relation0": 0}, germany, 176, poland) == {"opinion": [0.0, 0.0, 0.0]}
    assert gd.peek_more(read, dict.fromkeys(MORE, 0), germany, 176, poland) == {}
    assert fake.snapshot(176) + fake.snapshot(141) == before


@pytest.fixture
def lab_game(cfg):
    """독일(176)로 진행 중인 가짜 게임과 그 연구(toybox_fake_game.standard_lab), 표의 꼴(ToyBox 의 DLL 이 아는 것 — locate.h), 읽는 함수."""
    import ctypes

    from srkit import toybox
    from toybox_fake_game import FakeGame, standard_lab

    if not toybox.output(cfg).is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    fake = FakeGame()
    fake.region(141, 1106, alive=3)
    fake.region(176, 1499)
    fake.play(176)
    return fake, standard_lab(fake), toybox.research_shape(toybox.library(cfg)), lambda address, size: ctypes.string_at(address, size)


def test_research_reads_what_a_region_holds_and_the_players_queue(gd, lab_game):
    """research 는 게임의 메모리에서 연구를 읽는다(읽기만): 그 지역이 보유한 기술 · 부대 설계, 쓰는 항목과 묶음이 없는 항목의 수,
    플레이어의 대기열(나중에 건 것이 앞이다), 모든 기술의 연구 기간의 합. ToyBox 가 쓴 것을 창의 숫자가 아니라 이것으로 본다."""
    from toybox_fake_game import RESEARCH

    fake, lab, shape, read = lab_game
    before = lab.everything()
    germany = gd.peek_research(read, RESEARCH, shape, fake.base, 176, 176)
    assert germany == {"index": 176, "techs": [1, 4, 6], "designs": [10, 13, 14], "used": {"techs": 6, "designs": 5},
                       "unhoused": {"techs": 1, "designs": 1}, "days": 600.0,
                       "queue": [[2, 11, "00000001", "60000001"], [1, 2, "00000001", "00000000"]]}
    poland = gd.peek_research(read, RESEARCH, shape, fake.base, 141, 176)
    assert (poland["index"], poland["techs"], poland["designs"]) == (141, [1, 2], [11, 13])
    assert poland["queue"] == germany["queue"] and "effects" not in poland     # 대기열은 플레이어의 것이다. 보정 표는 달라고 할 때만
    assert lab.everything() == before


def test_research_reads_the_effect_tables_of_the_build_it_knows(gd, lab_game, monkeypatch):
    """지역의 보정 표(게임의 "효과를 다시 셈"이 쌓는 것)의 자리는 한 빌드에서만 안다 — 지역 객체의 주소를 줄 때만 읽는다.
    표는 세계 객체 안에 지역마다 있고(첫 자리 + 간격 × 지역 인덱스), 한 칸은 지역 객체 안에 있다."""
    import struct

    from toybox_fake_game import RESEARCH

    fake, _lab, shape, read = lab_game
    world = fake.base + RESEARCH["world"]
    monkeypatch.setattr(gd, "EFFECT_TABLES", {"mul": (0x100000, 0x10, 3), "add": (0x200000, 0x20, 2)})
    monkeypatch.setattr(gd, "EFFECT_CELL", 0x800)
    far = {world + 0x100000 + 0x10 * 176: struct.pack("<3f", 1.0, 1.5, 2.0), world + 0x200000 + 0x20 * 176: struct.pack("<2f", 0.25, 0.5)}
    fake._write(176, 0x800, "<I", 7)
    got = gd.peek_research(lambda address, size: far[address] if address in far else read(address, size), RESEARCH, shape, fake.base,
                           176, 176, region=fake.where[176])
    assert got["effects"] == {"mul": [1.0, 1.5, 2.0], "add": [0.25, 0.5], "cell": 7} and got["techs"] == [1, 4, 6]


def test_research_stops_when_the_game_cannot_be_read(gd, lab_game):
    """표를 읽을 수 없거나 자리 수가 말이 안 되면 반쯤 읽은 것을 내지 않는다."""
    from toybox_fake_game import RESEARCH

    fake, _lab, shape, read = lab_game
    with pytest.raises(SystemExit, match="게임의 메모리를 읽을 수 없습니다"):
        gd.peek_research(lambda address, size: None if size > 64 else read(address, size), RESEARCH, shape, fake.base, 176, 176)
    fake.poke(RESEARCH["tech_count"], "<i", 70000)
    with pytest.raises(SystemExit, match="자리 수가 범위 밖입니다"):
        gd.peek_research(read, RESEARCH, shape, fake.base, 176, 176)
