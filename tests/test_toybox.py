"""ToyBox DLL(native/srtoybox)을 직접 불러 화면 없는 부분을 확인한다(게임은 띄우지 않는다)."""
import ctypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from srkit import hook, toybox

# 넣지 않는 것: 모든 지역 · AI 에 닿거나, 불리해지거나, 반응이 없었거나, 넣지 않기로 한 것
EXCLUDED = {
    "onedaybuild", "allunit", "gates", "devcheat", "endday", "increaseday", "eventnow", "peace", "worldwar", "darren",
    "democracy", "saddam", "breakground", "depopulate", "trumpme", "sanction", "wmsanction", "shelovesmenot", "saddamme",
    "hate", "liberate", "revolt", "resettutorial", "allowcheats",
}
TABS = ["돈", "물자", "연구", "인구·여론", "외교·영토", "부대", "화면·진행"]
TEXT_CALLS = ["srtoybox_feature_info", "srtoybox_command", "srtoybox_plan", "srtoybox_simulate",
              "srtoybox_settings_normalize", "srtoybox_settings_file", "srtoybox_hotkey_name"]


@pytest.fixture(scope="module")
def dll(cfg):
    path = toybox.output(cfg)
    if not path.is_file():
        pytest.skip("ToyBox DLL 미빌드 (srkit toybox-build)")
    lib = ctypes.CDLL(str(path))
    lib.srtoybox_feature_info.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_command.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
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
        ident, tab, label, command, has_value, default, low, high, confirm, help_, target = \
            text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_,
                    "target": target})
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
    assert len(fs) == 25
    assert len({f["id"] for f in fs}) == 25 and len({f["command"] for f in fs}) == 25
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    for f in fs:
        assert f["command"] == "cheat " + f["id"] and f["label"] and f["help"]
        assert not (f["has_value"] and f["target"] != "none")           # 한 기능의 인자는 하나다
        if f["has_value"]:
            assert f["min"] <= f["default"] <= f["max"]
    assert {f["id"] for f in fs if f["has_value"]} == {"treasury", "products", "technology", "spawnunit"}
    assert {f["id"] for f in fs if f["target"] == "player"} == {"approval"}
    assert {f["id"] for f in fs if f["target"] == "picked"} == {"love", "neutral", "annex", "colonize", "novichok", "fight",
                                                                "becomeregion"}
    # 되돌릴 수 없는 것은 한 번 더 누르게 한다
    assert [f["id"] for f in fs if f["confirm"]] == ["annex", "colonize", "novichok", "fight", "becomeregion", "instantwin"]
    assert {f["id"] for f in fs if f["tab"] == "외교·영토"} == {"love", "neutral", "treaty", "annex", "colonize", "novichok",
                                                              "fight", "becomeregion"}
    assert dll.srtoybox_feature_info(25, ctypes.create_string_buffer(8), 8) == -1


def test_only_cheats_that_were_seen_working_and_reach_what_the_user_chose(dll, cfg):
    """요구: 설정은 플레이어가 플레이 중인 국가에만 적용된다. 게임에서 효과를 확인한 치트만 내놓고,
    플레이어 밖에 닿는 것은 사용자가 창이나 지도에서 고른 나라 하나에만 닿는 것이어야 한다(2026-10-07, 사용자가 범위를 정했다)."""
    rows = documented(cfg)
    for f in features(dll):
        target, verdict = rows[f["id"]]
        assert verdict == "[확인: 효과]", f["id"]
        assert f["id"] not in EXCLUDED
        if f["tab"] == "외교·영토" or f["target"] == "player":
            assert target in ("지정한 지역", "고른 지역", "플레이어"), (f["id"], target)
        else:
            assert target.startswith("플레이어") or target == "고른 부대", (f["id"], target)


def test_command_text(dll):
    assert text(dll.srtoybox_command, b"treasury", 1234, 0) == "cheat treasury 1234"
    assert text(dll.srtoybox_command, b"treasury", 0, 0) == "cheat treasury 1"                 # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"treasury", -5, 0) == "cheat treasury 1"
    assert text(dll.srtoybox_command, b"treasury", 10**12, 0) == "cheat treasury 1000000"
    assert text(dll.srtoybox_command, b"georgew", 999, 1106) == "cheat georgew"                # 값도 대상도 없는 기능은 둘 다 무시한다
    assert text(dll.srtoybox_command, b"e=mc2", 0, 0) == "cheat e=mc2"
    assert text(dll.srtoybox_command, b"approval", 0, 1499) == "cheat approval 1499"           # 대상이 있는 기능은 지역 번호가 붙는다
    assert text(dll.srtoybox_command, b"love", 0, 1106) == "cheat love 1106"
    assert text(dll.srtoybox_command, b"treaty", 0, 1106) == "cheat treaty"                    # 게임이 지도에서 고른 나라를 쓴다
    assert text(dll.srtoybox_command, b"love", 0, 0) is None                                   # 나라를 고르지 않았으면 만들지 않는다
    assert text(dll.srtoybox_command, b"approval", 0, -1) is None
    assert text(dll.srtoybox_command, b"depopulate", 0, 0) is None                             # 표에 없는 것은 만들지 않는다
    assert text(dll.srtoybox_command, b"treasury", 1, 0, size=4) is None                       # 버퍼가 작으면 넘치지 않고 -1


def expected_plan(command: str) -> list[str]:
    """gamedrive.py 가 밖에서 넣는 것과 같은 순서: 설정 창 열기 → cheat allowcheats → 명령 → ESC."""
    out = ["MODS 1", "DOWN 17", "DOWN 16", "DOWN 83", "WAIT 50", "UP 83", "WAIT 100", "UP 16", "UP 17", "WAIT 200", "MODS 0",
           "WAIT 300"]
    for line in ("cheat allowcheats", command):
        for ch in line:
            out += [f"CHAR {ord(ch)}", "WAIT 30"]
        out += ["DOWN 13", "WAIT 50", "UP 13", "WAIT 300"]
    return out + ["DOWN 27", "WAIT 50", "UP 27", "WAIT 300"]


def typed_keys(command: str) -> str:
    """글쇠 방식으로 그 명령을 넣을 때 게임이 받는 것(프로브의 Game.text 와 같은 표기): 글자는 그대로, 누름은 <이름>."""
    keys = {13: "<Enter>", 27: "<Esc>", 83: "<S>", 17: "<Ctrl>", 16: "<Shift>"}
    steps = [step.split() for step in expected_plan(command)]
    return "".join(chr(int(v)) if act == "CHAR" else keys[int(v)] for act, v in steps if act in ("CHAR", "DOWN"))


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


IMGUI_FILES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp", "imgui.h", "imgui_internal.h", "imconfig.h",
               "imstb_rectpack.h", "imstb_textedit.h", "imstb_truetype.h", "backends/imgui_impl_win32.h",
               "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.h", "backends/imgui_impl_dx11.cpp", "LICENSE.txt", "README.md"]


def test_imgui_is_vendored_with_its_license_and_version(cfg):
    """외부 소스는 필요한 파일만, 라이선스와 함께, 버전을 적어 둔다."""
    root = cfg.root / toybox.IMGUI_DIR
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) == sorted(IMGUI_FILES)
    assert "MIT" in (root / "LICENSE.txt").read_text(encoding="utf-8")
    version = re.search(r'#define IMGUI_VERSION\s+"([^"]+)"', (root / "imgui.h").read_text(encoding="utf-8"))[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert f"v{version}" in readme and "github.com/ocornut/imgui" in readme
    assert [s for s in toybox.IMGUI_SOURCES if not (root / s).is_file()] == []


START_PROBE = "import ctypes, sys, time; ctypes.WinDLL(sys.argv[1]); time.sleep(float(sys.argv[2]))"


def test_the_hook_starts_toybox_and_it_writes_a_log(dll, cfg, tmp_path):
    """훅이 불러와 srtoybox_start 를 부르면 로그에 시작 줄이 생긴다. 게임이 아닌 프로세스에서도 죽지 않는다."""
    if not hook.output(cfg).is_file():
        pytest.skip("훅 DLL 미빌드 (srkit hook-build)")
    home = tmp_path / "home"
    home.mkdir()
    shutil.copyfile(hook.output(cfg), tmp_path / "hookcopy.dll")
    shutil.copyfile(toybox.output(cfg), tmp_path / toybox.DLL_NAME)
    run = subprocess.run([sys.executable, "-c", START_PROBE, str(tmp_path / "hookcopy.dll"), "8"], capture_output=True, text=True,
                         env={**os.environ, "SRTOYBOX_HOME": str(home)}, timeout=60)
    assert run.returncode == 0, run.stderr
    log = (home / "toybox.log").read_text(encoding="utf-8")
    assert "시작" in log and ("끼어들었습니다" in log or "끼어들지 못했습니다" in log), log
    assert "게임 상태를 읽을 수 없습니다" in log, log     # 게임이 아닌 프로세스다 — 주소를 못 찾고 글쇠 방식으로 남는다


def _probe(cfg, tmp_path, mode: str, env: dict[str, str] | None = None) -> str:
    """tests/toybox_overlay_probe.py 를 새 프로세스로 돌려 그 출력 한 줄을 받는다. ToyBox 의 로그는 tmp_path/home 에 남는다."""
    if not hook.output(cfg).is_file():
        pytest.skip("훅 DLL 미빌드 (srkit hook-build)")
    home = tmp_path / "home"
    home.mkdir()
    shutil.copyfile(hook.output(cfg), tmp_path / "hookcopy.dll")
    shutil.copyfile(toybox.output(cfg), tmp_path / toybox.DLL_NAME)
    probe = Path(__file__).with_name("toybox_overlay_probe.py")
    run = subprocess.run([sys.executable, str(probe), str(tmp_path / "hookcopy.dll"), mode], capture_output=True, text=True,
                         encoding="utf-8", env={**os.environ, "SRTOYBOX_HOME": str(home), **(env or {})}, timeout=120)
    out = run.stdout.strip()
    if out == "nodevice":
        pytest.skip("Direct3D 장치를 만들 수 없는 환경")
    if out.startswith("skip "):
        pytest.skip(out[5:])
    assert run.returncode == 0 and out, (run.returncode, out, run.stderr[-600:])
    return out


def _fields(out: str) -> dict[str, str]:
    """"이름=값 이름=값 …" 을 사전으로. 마지막 값(text=…)에는 빈칸이 들어 있을 수 있다."""
    head, _, tail = out.partition(" text=")
    return {**dict(pair.split("=", 1) for pair in head.split()), **({"text": tail} if " text=" in out else {})}


def _overlay_probe(cfg, tmp_path, mode: str) -> tuple[int, int]:
    """다른 훅과 함께 돌린 결과: (가짜 훅이 불린 횟수, 마지막 반환값). 반환값은 아무 훅도 없을 때와 같아야 한다."""
    got = _fields(_probe(cfg, tmp_path, mode))
    assert got["hr"] == got["plain"], got
    return int(got["calls"]), int(got["hr"], 16)


def _ok(hr: str) -> bool:
    return int(hr, 16) < 0x80000000                 # 성공(S_OK 또는 가려져 있다는 상태값)


def test_present_passes_through_when_toybox_is_alone(dll, cfg, tmp_path):
    calls, hr = _overlay_probe(cfg, tmp_path, "plain")
    assert calls == 0 and hr < 0x80000000           # 성공(S_OK 또는 가려져 있다는 상태값)


def test_no_ping_pong_with_a_hook_that_was_there_first(dll, cfg, tmp_path):
    """Steam 오버레이처럼 먼저 끼어든 훅이 있을 때: 화면을 세 번 내보내면 그 훅도 세 번만 불린다.

    고치기 전에는 둘이 서로를 원래 함수로 알고 부르며 맴돌아 Steam 으로 띄운 게임이 죽었다.
    """
    calls, hr = _overlay_probe(cfg, tmp_path, "before")
    assert calls == 3 and hr < 0x80000000


def test_no_ping_pong_with_a_hook_placed_on_top_later(dll, cfg, tmp_path):
    calls, hr = _overlay_probe(cfg, tmp_path, "rehook")
    assert calls == 3 and hr < 0x80000000


def test_no_ping_pong_with_a_jump_planted_in_the_real_function(dll, cfg, tmp_path):
    """Steam 오버레이의 방식: 진짜 Present 의 머리에 점프를 심어 두고, 표에서 본 ToyBox 의 함수를 원래 함수로 부른다.

    ToyBox 가 진짜 함수를 부르면 그 점프를 타고 훅으로 되돌아오므로, 되불렸을 때는 점프를 건너뛰는 길로 가야 한다.
    """
    calls, hr = _overlay_probe(cfg, tmp_path, "inline")
    assert calls == 3 and hr < 0x80000000


def test_no_ping_pong_in_the_layout_steam_really_made(dll, cfg, tmp_path):
    """Steam 으로 띄운 게임에서 실제로 탄 길: 오버레이가 진짜 Present 와 ToyBox 함수 양쪽 머리에 점프를 심고,
    ToyBox 함수의 트램펄린을 원래 함수로 부른다. 이때 ToyBox 는 재진입도 아니고 표의 칸도 그대로다 — 자기 함수의 머리가
    바뀐 것을 보고 깨끗한 진입로로 가야 오버레이가 한 화면에 한 번만 돈다."""
    calls, hr = _overlay_probe(cfg, tmp_path, "steam")
    assert calls == 3 and hr < 0x80000000


@pytest.mark.parametrize("mode", ["inline_resize", "inline_present1"])
def test_resize_and_present1_skip_a_planted_jump_too(dll, cfg, tmp_path, mode):
    calls, hr = _overlay_probe(cfg, tmp_path, mode)
    assert calls == 1 and hr < 0x80000000


def test_draws_into_the_back_buffer_and_lets_go_of_it_on_resize(dll, cfg, tmp_path):
    got = _fields(_probe(cfg, tmp_path, "draw_resize"))
    assert got["resize_hooked"] == "1" and _ok(got["visible"])
    assert got["direct_resize"] == "0x887a0001"     # ToyBox 를 거치지 않으면 크기를 못 바꾼다 — 뒷면을 쥐고 있다(= 실제로 그렸다)
    assert got["hooked_resize"] == "0x0"            # ToyBox 를 거치면 놓아 준다
    assert _ok(got["after"]) and _ok(got["present1"]) and got["present1"] == got["present1_plain"]


@pytest.mark.parametrize("mode, reason", [("longpatch", "길게 고쳐"), ("longpatch_resize", "길게 고쳐"), ("stale", "파일과 다릅니다")])
def test_does_not_hook_where_the_clean_entry_cannot_be_trusted(dll, cfg, tmp_path, mode, reason):
    """깨끗한 진입로는 디스크의 dxgi.dll 에서 읽은 첫 14바이트를 실행하고 그 뒤로 뛴다. 그 뒤가 메모리에서 이미 바뀌어 있거나
    (14바이트보다 긴 훅) 디스크의 파일이 올라온 것과 다른 판이면 엉뚱한 자리로 뛰게 된다 — 그때는 끼어들지 않는다.
    크기 바꾸기(ResizeBuffers)에 끼어들 수 없으면 Present 에도 끼어들지 않는다: 그리기만 하면 뒷면을 쥔 채 놓지 못한다."""
    assert _probe(cfg, tmp_path, mode) == "nohook"
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "끼어들지 못했습니다" in log and reason in log, log


def test_keys_and_clicks_reach_only_the_side_they_are_meant_for(dll, cfg, tmp_path):
    got = _fields(_probe(cfg, tmp_path, "input"))
    assert got["hotkey"] == "toybox"                # 단축키는 게임에 가지 않는다
    assert got["button"] == "none"                  # 설정 창 위의 누름도
    assert got["outside"] == "press+release"        # 설정 창 밖의 누름은 게임이 받는다
    assert got["typing"] == "1" and got["done"] == "1", got
    # 게임이 받은 글쇠는 계획 그대로다. 넣는 동안 사용자가 친 9 와 단축키(<0x54>)는 섞이지 않는다
    assert got["text"] == typed_keys("cheat georgew")
    assert got["hotkey_busy"] == "toybox"           # 넣는 동안에도 단축키는 ToyBox 의 것이고
    assert got["title_after"] == "press+release"    # 그래서 창이 닫혔다
    assert got["mods_left"] == "0"                  # Ctrl · Shift 가 눌린 채로 남지 않는다


def test_mouse_follows_the_size_the_game_draws_at(dll, cfg, tmp_path):
    """게임이 창보다 작게 그리면 화면에는 늘어나 보인다. 누른 자리는 보이는 설정 창을 기준으로 가려야 한다."""
    got = _fields(_probe(cfg, tmp_path, "scale"))
    assert got["title"] == "none"                   # 보이는 창의 제목 줄을 눌렀다 — 게임에 새지 않는다
    assert got["beside"] == "press+release"         # 보이는 창의 바깥이다 — 게임이 받는다


def test_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    """ToyBox 가 게임을 읽을 수 있으면, 메뉴에서는 단추를 눌러도 게임에 아무것도 가지 않는다."""
    got = _fields(_probe(cfg, tmp_path, "gate_menu"))
    assert got["button"] == "none" and got["text"] == ""


def test_a_queued_command_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 실행되기 전에 게임에서 나가면, 그 명령을 메뉴에 넣지 않고 버린다."""
    got = _fields(_probe(cfg, tmp_path, "gate_leave"))
    assert got["button"] == "none" and got["text"] == ""


def test_the_typing_route_still_works_in_a_game_toybox_can_read(dll, cfg, tmp_path):
    got = _fields(_probe(cfg, tmp_path, "gate_typing", env={"SRTOYBOX_DIRECT": "0"}))
    assert got["text"] == typed_keys("cheat georgew")


def test_direct_run_calls_the_games_handler(dll, cfg, tmp_path):
    """게임 안에서는 글쇠를 넣지 않고 게임의 명령 처리 함수에 바로 넘긴다.

    치트 허용이 꺼져 있으면 먼저 cheat allowcheats 를 부르고, 켜져 있으면 다시 부르지 않는다
    (메뉴에 나갔다 오면 게임이 꺼 두므로 그때는 다시 부른다).
    """
    got = _fields(_probe(cfg, tmp_path, "direct"))
    assert got["lines"].replace("_", " ").split("|") == ["cheat allowcheats", "cheat georgew", "cheat georgew",
                                                        "cheat allowcheats", "cheat georgew"]
    assert got["text"] == ""                                    # 글쇠는 가지 않는다 — 게임의 설정 창이 뜨지 않는다
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("직접 실행: cheat georgew") == 3


def test_a_fault_in_the_games_handler_is_caught_and_nothing_runs_after(dll, cfg, tmp_path):
    """명령 처리 함수 안에서 예외가 나도 프로세스가 죽지 않는다. 게임의 상태가 어긋났을 수 있으므로 그 뒤로는
    직접으로도 글쇠로도 실행하지 않는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_fault"))
    assert got["lines"] == "" and got["text"] == ""
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("직접 실행 중 예외 0xC0000005") == 1         # 한 번 잡은 뒤로는 다시 부르지 않는다


def test_the_games_handler_is_not_called_outside_a_game(dll, cfg, tmp_path):
    """명령 처리 함수는 게임이 진행 중인지 검사하지 않고 플레이어 포인터를 따라간다 — 게임 밖에서 부르면 죽는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_menu"))
    assert got["lines"] == "" and got["text"] == ""


def test_srtoybox_direct_0_keeps_the_typing_route(dll, cfg, tmp_path):
    """탈출구: SRTOYBOX_DIRECT=0 이면 명령 처리 함수를 부를 수 있어도 글쇠를 넣는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_off", env={"SRTOYBOX_DIRECT": "0"}))
    assert got["lines"] == "" and got["text"] == typed_keys("cheat georgew")


@pytest.mark.parametrize("mode", ["reenter_timer", "reenter_keyup", "reenter_present"])
def test_the_games_handler_may_come_back_into_toybox(dll, cfg, tmp_path, mode):
    """게임의 명령 처리 함수가 일하는 도중에 메시지를 돌리거나 화면을 내보내면 ToyBox 의 타이머 · 입력 · 그리기로 되돌아온다.

    ToyBox 는 그때 아무 잠금도 쥐고 있지 않아야 하고(쥔 채로 되돌아오면 프로세스가 끝난다), 대기열의 다음 명령을
    그 안에서 시작해서도 안 된다(게임의 함수가 겹쳐 불린다).
    """
    got = _fields(_probe(cfg, tmp_path, mode))
    assert got["inside"] == "ok" and got["deepest"] == "1", got
    assert got["lines"].replace("_", " ").split("|") == ["cheat allowcheats"] + ["cheat georgew"] * 3
    assert got["text"] == ""
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "예외" not in log and log.count("직접 실행: cheat georgew") == 3, log


def test_toybox_keeps_drawing_after_an_exception_passes_through_present(dll, cfg, tmp_path):
    """ToyBox 가 부른 다음 함수 안에서 예외가 나고 그것을 위에서 누가 잡으면(게임의 함수를 직접 부르는 ToyBox 자신이 그렇다),
    "지금 훅 안이다"라는 표시가 남아 그 뒤로 영영 그리지 않게 되면 안 된다."""
    got = _fields(_probe(cfg, tmp_path, "present_fault"))
    assert got == {"caught": "1", "drawn": "1"}


def test_prologue_length_knows_only_plain_function_heads(dll):
    """다른 훅이 심은 점프를 건너뛰려면 함수의 원래 첫 명령들을 통째로 옮겨야 한다. 옮겨도 되는 명령만 센다."""
    dll.srtoybox_prologue_length.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    length = lambda text, want=14: dll.srtoybox_prologue_length(bytes.fromhex(text), len(bytes.fromhex(text)), want)
    # 이 PC 의 dxgi.dll (10.0.26100) 에서 읽은 Present · Present1 · ResizeBuffers 의 머리
    assert length("48 89 5c 24 10 48 89 74 24 18 55 57 41 56 48 8d 6c 24 90 48 81 ec 70 01 00 00") == 14
    assert length("48 89 5c 24 10 48 89 74 24 18 55 57 41 54 41 56 41 57 48 8d 6c 24 80 48") == 14
    assert length("48 8b c4 44 89 48 20 44 89 40 18 89 50 10 48 89 48 08 55 53 56 57 41 54") == 14
    assert length("48 89 5c 24 10 48 89 74 24 18 55 57 41 56 48 8d 6c 24 90", want=5) == 5
    assert length("48 83 ec 28 48 81 ec 70 01 00 00 55 53 56") == 14        # sub rsp
    assert length("e9 11 22 33 44 90 90 90 90 90 90 90 90 90 90 90") == 0    # 점프(이미 누가 심은 것) — 옮기지 않는다
    assert length("48 8b 05 11 22 33 44 55 55 55 55 55 55 55 55 55") == 0    # RIP 상대 주소 — 옮기면 주소가 틀어진다
    assert length("e8 11 22 33 44 55 55 55 55 55 55 55 55 55 55 55") == 0    # call
    assert length("48 89 5c 24 10 48 89 74 24") == 0                         # 명령이 중간에 끊겼다
