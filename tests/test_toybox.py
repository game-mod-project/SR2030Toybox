"""ToyBox DLL(native/srtoybox)을 직접 불러 화면 없는 부분을 확인한다(게임은 띄우지 않는다)."""
import ctypes
import re

import pytest

from srkit import toybox

# 설계서의 "넣지 않는 것": 모든 지역·AI 에 닿거나, 불리해지거나, 지역 번호가 필요하거나, 넣지 않기로 한 것
EXCLUDED = {
    "onedaybuild", "allunit", "gates", "devcheat", "endday", "increaseday", "eventnow", "peace", "worldwar", "darren",
    "democracy", "saddam", "breakground", "depopulate", "trumpme", "sanction", "wmsanction", "shelovesmenot", "saddamme",
    "approval", "love", "hate", "neutral", "annex", "colonize", "novichok", "fight", "treaty", "becomeregion",
    "resettutorial", "allowcheats",
}
TABS = ["돈", "물자", "연구", "인구·여론", "부대", "화면·진행"]
TEXT_CALLS = ["srtoybox_feature_info", "srtoybox_command", "srtoybox_plan", "srtoybox_simulate",
              "srtoybox_settings_normalize", "srtoybox_settings_file", "srtoybox_hotkey_name"]


@pytest.fixture(scope="module")
def dll(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_feature_info.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_command.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_plan.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_simulate.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_settings_normalize.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_settings_store.argtypes = [ctypes.c_char_p]
    lib.srtoybox_settings_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_hotkey_name.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return lib


def text(call, *args, size: int = 1 << 17) -> str | None:
    """글을 돌려주는 내보내기 함수를 부른다. 함수가 -1 을 주면 None."""
    buf = ctypes.create_string_buffer(size)
    n = call(*args, buf, size)
    return None if n < 0 else buf.raw[:n].decode("utf-8")


def features(dll) -> list[dict]:
    out = []
    for i in range(dll.srtoybox_feature_count()):
        ident, tab, label, command, has_value, default, low, high, confirm, help_ = text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_})
    return out


def documented(cfg) -> dict[str, tuple[str, str]]:
    """docs/07 의 치트표: 이름 → (대상, 검증)."""
    rows = {}
    for line in (cfg.root / "docs" / "07-cheats.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        m = re.fullmatch(r"`cheat ([^` ]+)`", cells[0]) if len(cells) == 6 else None
        if m:
            rows[m[1]] = (cells[3], cells[5])
    return rows


def test_feature_table(dll):
    fs = features(dll)
    assert len(fs) == 16
    assert len({f["id"] for f in fs}) == 16 and len({f["command"] for f in fs}) == 16
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    for f in fs:
        assert f["command"] == "cheat " + f["id"] and f["label"] and f["help"]
        if f["has_value"]:
            assert f["min"] <= f["default"] <= f["max"]
    assert {f["id"] for f in fs if f["has_value"]} == {"treasury", "products", "technology", "spawnunit"}
    assert [f["id"] for f in fs if f["confirm"]] == ["instantwin"]
    assert dll.srtoybox_feature_info(16, ctypes.create_string_buffer(8), 8) == -1


def test_only_player_cheats_that_were_seen_working(dll, cfg):
    """요구: 설정은 플레이어가 플레이 중인 국가에만 적용된다. 게임이 플레이어에게만 적용하는 것으로 확인된 치트만 내놓는다."""
    rows = documented(cfg)
    for f in features(dll):
        target, verdict = rows[f["id"]]
        assert verdict == "[확인: 효과]", f["id"]
        assert target.startswith("플레이어") or target == "고른 부대", (f["id"], target)
        assert f["id"] not in EXCLUDED


def test_command_text(dll):
    assert text(dll.srtoybox_command, b"treasury", 1234) == "cheat treasury 1234"
    assert text(dll.srtoybox_command, b"treasury", 0) == "cheat treasury 1"                    # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"treasury", -5) == "cheat treasury 1"
    assert text(dll.srtoybox_command, b"treasury", 10**12) == "cheat treasury 1000000"
    assert text(dll.srtoybox_command, b"georgew", 999) == "cheat georgew"                      # 값이 없는 기능은 값을 무시한다
    assert text(dll.srtoybox_command, b"e=mc2", 0) == "cheat e=mc2"
    assert text(dll.srtoybox_command, b"depopulate", 0) is None                                # 표에 없는 것은 만들지 않는다
    assert text(dll.srtoybox_command, b"treasury", 1, size=4) is None                          # 버퍼가 작으면 넘치지 않고 -1


def expected_plan(command: str) -> list[str]:
    """gamedrive.py 가 밖에서 넣는 것과 같은 순서: 설정 창 열기 → cheat allowcheats → 명령 → ESC."""
    out = ["MODS 1", "DOWN 17", "DOWN 16", "DOWN 83", "WAIT 50", "UP 83", "WAIT 100", "UP 16", "UP 17", "WAIT 200", "MODS 0",
           "WAIT 300"]
    for line in ("cheat allowcheats", command):
        for ch in line:
            out += [f"CHAR {ord(ch)}", "WAIT 30"]
        out += ["DOWN 13", "WAIT 50", "UP 13", "WAIT 300"]
    return out + ["DOWN 27", "WAIT 50", "UP 27", "WAIT 300"]


def test_plan_follows_the_route_checked_in_game(dll):
    plan = text(dll.srtoybox_plan, b"cheat treasury 1234").splitlines()
    assert plan == expected_plan("cheat treasury 1234")
    assert plan.index("MODS 0") < min(i for i, step in enumerate(plan) if step.startswith("CHAR"))   # 수정키를 뗀 뒤에 글자를 넣는다


def test_plan_refuses_text_the_game_input_cannot_take(dll):
    for bad in (b"", "cheat 한글".encode("utf-8"), b"cheat a\nb", b"cheat a\tb", b"x" * 65, b"cheat \x7f"):
        assert text(dll.srtoybox_plan, bad) is None, bad
    assert text(dll.srtoybox_plan, b"x" * 64) is not None


def events(log: str) -> list[tuple[int, str]]:
    return [(int(t), f"{act} {value}") for t, act, value in (line.split() for line in log.splitlines() if not line.startswith("REJECT"))]


def assert_gaps_kept(evs: list[tuple[int, str]], plan: list[str]) -> None:
    """계획의 WAIT 만큼은 반드시 벌어져 있어야 한다(프레임이 빨라도 게임이 읽을 시간을 준다)."""
    assert [step for _, step in evs] == [step for step in plan if not step.startswith("WAIT")]
    at, owed, last = 0, 0, None
    for step in plan:
        if step.startswith("WAIT"):
            owed += int(step.split()[1])
            continue
        t = evs[at][0]
        if last is not None:
            assert t - last >= owed, (step, t - last, owed)
        at, owed, last = at + 1, 0, t


def test_runner_keeps_the_gaps_however_fast_it_is_ticked(dll):
    for tick_ms in (1, 10, 16, 40):
        evs = events(text(dll.srtoybox_simulate, b"cheat georgew", tick_ms))
        assert_gaps_kept(evs, expected_plan("cheat georgew"))


def test_runner_runs_commands_in_order(dll):
    evs = events(text(dll.srtoybox_simulate, b"cheat georgew\ncheat populate", 10))
    first, second = expected_plan("cheat georgew"), expected_plan("cheat populate")
    assert_gaps_kept(evs, first + second)                       # 첫 명령의 마지막 WAIT 가 둘째 명령 앞의 간격이 된다


def test_runner_takes_eight_and_rejects_the_rest(dll):
    """단추를 연달아 눌러도 8개까지만 받는다. 받은 것은 순서대로 끝까지 들어간다."""
    commands = [f"cheat treasury {n}" for n in range(1, 11)]
    log = text(dll.srtoybox_simulate, "\n".join(commands).encode(), 10)
    assert [line for line in log.splitlines() if line.startswith("REJECT")] == ["REJECT cheat treasury 9", "REJECT cheat treasury 10"]
    assert_gaps_kept(events(log), [step for c in commands[:8] for step in expected_plan(c)])
    assert text(dll.srtoybox_simulate, "cheat 한글".encode("utf-8"), 10) == "REJECT cheat 한글\n"   # 넣을 수 없는 글은 받지 않는다


DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\ntreasury=10000\nproducts=100000\ntechnology=120\nspawnunit=2413\n"


def test_settings_fall_back_to_defaults(dll):
    norm = lambda ini: text(dll.srtoybox_settings_normalize, ini.encode("utf-8"))
    assert norm("") == DEFAULTS
    assert norm("\xff garbage\n===\n[x]\nhotkey_vk\n=5\n") == DEFAULTS                      # 깨진 파일
    assert norm("treasury=0\nproducts=999999999999\ntechnology=abc\nspawnunit=12x\n") == DEFAULTS   # 범위 밖·숫자 아님 → 기본값
    assert norm("unknown=5\ngeorgew=7\ndepopulate=1\n") == DEFAULTS                          # 모르는 키, 값이 없는 기능
    assert norm("hotkey_vk=16\nhotkey_mods=1\n") == DEFAULTS                                 # 수정키만으로는 단축키가 못 된다
    assert norm("hotkey_vk=27\nhotkey_mods=0\n") == DEFAULTS                                 # ESC 만은 취소다
    assert norm("hotkey_vk=84\nhotkey_mods=9\n") == DEFAULTS
    assert norm(" hotkey_vk = 123 \r\nhotkey_mods=0\r\ntreasury= 500 \r\n") == DEFAULTS.replace("=84", "=123").replace("mods=3", "mods=0").replace("treasury=10000", "treasury=500")


def test_settings_file_round_trip(dll, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    assert text(dll.srtoybox_settings_file) == DEFAULTS                                      # 파일이 없으면 기본값
    assert dll.srtoybox_settings_store(b"hotkey_vk=120\nhotkey_mods=4\ntechnology=140\n") == 1
    saved = DEFAULTS.replace("=84", "=120").replace("mods=3", "mods=4").replace("=120\nspawn", "=140\nspawn")
    assert (tmp_path / "toybox.ini").read_text(encoding="utf-8") == saved
    assert text(dll.srtoybox_settings_file) == saved
    (tmp_path / "toybox.ini").write_bytes(b"\xff\xfe\x00broken")
    assert text(dll.srtoybox_settings_file) == DEFAULTS


def test_hotkey_names(dll):
    name = lambda vk, mods: text(dll.srtoybox_hotkey_name, vk, mods)
    assert name(84, 3) == "Ctrl+Shift+T"
    assert name(0x7B, 0) == "F12"
    assert name(0x31, 4) == "Alt+1"
    assert name(0xC0, 7) == "Ctrl+Shift+Alt+0xC0"


def test_mod_folder_holds_only_the_dll(dll, cfg):
    """build/toybox 는 게임 루트 구조의 모드 폴더다. deploy 가 통째로 복사하므로 DLL 말고는 없어야 한다."""
    assert sorted(p.name for p in toybox.output(cfg).parent.iterdir()) == [toybox.DLL_NAME]
