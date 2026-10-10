"""ToyBox DLL(native/srtoybox)을 직접 불러 화면 없는 부분을 확인한다(게임은 띄우지 않는다)."""
import ctypes
import json
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
TABS = ["연구", "인구·여론", "외교·영토", "부대", "화면·진행"]     # 기능 표의 탭. "돈" · "물자" 탭은 기능 표가 아니라 전용 화면이 그린다
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
        ident, tab, label, command, has_value, default, low, high, confirm, help_, target, how = \
            text(dll.srtoybox_feature_info, i).split("\t")
        out.append({"id": ident, "tab": tab, "label": label, "command": command, "has_value": has_value == "1",
                    "default": int(default), "min": int(low), "max": int(high), "confirm": confirm == "1", "help": help_,
                    "target": target, "how": how})
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
    assert len(fs) == 19 and len({f["id"] for f in fs}) == 19
    # 국고와 물자는 내장 치트를 거치지 않는다(돈 탭 · 물자 탭)
    assert not {"treasury", "georgew", "georgeww", "products", "branson", "bezos"} & {f["id"] for f in fs}
    assert [t for i, t in enumerate(f["tab"] for f in fs) if i == 0 or fs[i - 1]["tab"] != t] == TABS   # 탭끼리 모여 있고 이 순서다
    # 여섯 줄은 ToyBox 가 직접 쓴다(3단계 2 의 넷, 3단계 3 의 연구 둘) — 자리와 이름은 그대로이고 게임에 넣는 글이 없다.
    # 나머지 열셋이 내장 치트로 돈다
    assert {f["id"]: f["how"] for f in fs if f["how"] != "cheat"} == {
        "technology": "tech_level", "e=mc2": "queue_done", "finalexam": "tech_up", "shelovesme": "opinion_best",
        "love": "relation_best", "neutral": "relation_neutral"}
    cheats = [f for f in fs if f["how"] == "cheat"]
    assert len(cheats) == 13 == dll.srtoybox_cheat_feature_count() and len({f["command"] for f in cheats}) == 13
    assert [f["id"] for f in fs][:3] == ["technology", "e=mc2", "finalexam"]            # 줄의 자리는 옮기기 전과 같다
    assert [(f["label"], f["default"], f["min"], f["max"]) for f in fs[:2]] == [("기술 수준 N 이하 전부 보유", 120, 1, 255),
                                                                              ("대기열의 연구 즉시 완료", 0, 0, 0)]
    for f in fs:
        assert f["label"] and f["help"]
        if f["how"] == "cheat":
            assert f["command"] == "cheat " + f["id"]
        else:
            assert f["command"] == "" and not f["confirm"]
        assert not (f["has_value"] and f["target"] != "none")           # 한 기능의 인자는 하나다
        if f["has_value"]:
            assert f["min"] <= f["default"] <= f["max"]
    assert {f["id"] for f in fs if f["has_value"]} == {"technology", "spawnunit"}
    assert {f["id"] for f in fs if f["target"] == "player"} == {"approval"}
    assert {f["id"] for f in fs if f["target"] == "picked"} == {"love", "neutral", "annex", "colonize", "novichok", "fight",
                                                                "becomeregion"}
    # 되돌릴 수 없는 것은 한 번 더 누르게 한다
    assert [f["id"] for f in fs if f["confirm"]] == ["annex", "colonize", "novichok", "fight", "becomeregion", "instantwin"]
    assert {f["id"] for f in fs if f["tab"] == "외교·영토"} == {"love", "neutral", "treaty", "annex", "colonize", "novichok",
                                                              "fight", "becomeregion"}
    assert dll.srtoybox_feature_info(19, ctypes.create_string_buffer(8), 8) == -1


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
    assert text(dll.srtoybox_command, b"spawnunit", 140, 0) == "cheat spawnunit 140"
    assert text(dll.srtoybox_command, b"spawnunit", 0, 0) == "cheat spawnunit 1"               # 범위로 잘라 맞춘다
    assert text(dll.srtoybox_command, b"spawnunit", -5, 0) == "cheat spawnunit 1"
    assert text(dll.srtoybox_command, b"spawnunit", 10**12, 0) == "cheat spawnunit 99999"
    assert text(dll.srtoybox_command, b"populate", 999, 1106) == "cheat populate"              # 값도 대상도 없는 기능은 둘 다 무시한다
    assert text(dll.srtoybox_command, b"approval", 0, 1499) == "cheat approval 1499"           # 대상이 있는 기능은 지역 번호가 붙는다
    assert text(dll.srtoybox_command, b"annex", 0, 1106) == "cheat annex 1106"
    assert text(dll.srtoybox_command, b"treaty", 0, 1106) == "cheat treaty"                    # 게임이 지도에서 고른 나라를 쓴다
    assert text(dll.srtoybox_command, b"annex", 0, 0) is None                                  # 나라를 고르지 않았으면 만들지 않는다
    for moved in (b"technology", b"e=mc2", b"finalexam", b"shelovesme", b"love", b"neutral"):   # 직접 쓰는 줄은 게임에 넣을 글이 없다
        assert text(dll.srtoybox_command, moved, 120, 1106) is None
    assert text(dll.srtoybox_command, b"approval", 0, -1) is None
    assert text(dll.srtoybox_command, b"depopulate", 0, 0) is None                             # 표에 없는 것은 만들지 않는다
    assert text(dll.srtoybox_command, b"treasury", 1, 0) is None                               # 지운 기능 — 국고는 돈 탭이 직접 한다
    assert text(dll.srtoybox_command, b"products", 1, 0) is None                               # 〃 — 물자는 물자 탭이
    assert text(dll.srtoybox_command, b"spawnunit", 1, 0, size=4) is None                      # 버퍼가 작으면 넘치지 않고 -1


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


KEEP_DEFAULTS = "keep.treasury=0\nkeep.treasury.value=0\n" + "".join(f"keep.stock.{slot}=0\nkeep.stock.{slot}.value=0\n"
                                                                      for slot in range(12))
DEFAULTS = "hotkey_vk=84\nhotkey_mods=3\nmoney.amount=10000\n" + KEEP_DEFAULTS + "technology=120\nspawnunit=2413\n"


def kept(**lines: int) -> str:
    """DEFAULTS 에서 유지의 줄 몇 개만 바꾼 것. 키의 점은 밑줄 둘로 적는다: kept(keep__stock__3=1)."""
    out = DEFAULTS
    for key, value in lines.items():
        key = key.replace("__", ".")
        assert f"{key}=0\n" in out, key
        out = out.replace(f"{key}=0\n", f"{key}={value}\n")
    return out


def test_settings_fall_back_to_defaults(dll):
    norm = lambda ini: text(dll.srtoybox_settings_normalize, ini.encode("utf-8"))
    assert norm("") == DEFAULTS
    assert norm("\xff garbage\n===\n[x]\nhotkey_vk\n=5\n") == DEFAULTS                      # 깨진 파일
    assert norm("money.amount=0\ntechnology=0\nspawnunit=12x\n") == DEFAULTS                  # 범위 밖·숫자 아님 → 기본값
    assert norm("technology=999\n") == DEFAULTS.replace("technology=120", "technology=255")   # 기능 값이 범위보다 크면 끝으로 자른다
    assert norm("technology=abc\n") == DEFAULTS
    assert norm("unknown=5\nfinalexam=7\ndepopulate=1\ntreasury=500\nproducts=5\n") == DEFAULTS   # 모르는 키, 값이 없는 기능, 지운 기능
    assert norm("hotkey_vk=16\nhotkey_mods=1\n") == DEFAULTS                                 # 수정키만으로는 단축키가 못 된다
    assert norm("hotkey_vk=27\nhotkey_mods=0\n") == DEFAULTS                                 # ESC 만은 취소다
    assert norm("hotkey_vk=84\nhotkey_mods=9\n") == DEFAULTS
    assert norm(" hotkey_vk = 123 \r\nhotkey_mods=0\r\nmoney.amount= 500 \r\n") == DEFAULTS.replace("=84", "=123").replace("mods=3", "mods=0").replace("amount=10000", "amount=500")
    assert norm("money.amount=1000001\n") == DEFAULTS and norm("money.amount=1000000\n") == DEFAULTS.replace("=10000\n", "=1000000\n")


def test_keep_settings(dll):
    """최소 유지: 켜짐과 값을 모두 저장한다. 틀린 줄은 그 줄만 버린다(다른 유지는 그대로다)."""
    norm = lambda ini: text(dll.srtoybox_settings_normalize, ini.encode("utf-8"))
    assert norm("keep.treasury=1\nkeep.treasury.value=50000\n") == kept(keep__treasury=1, keep__treasury__value=50000)
    assert norm("keep.stock.3=1\nkeep.stock.3.value=1000000\nkeep.stock.11.value=7\n") == \
        kept(keep__stock__3=1, keep__stock__3__value=1000000, keep__stock__11__value=7)
    assert norm("keep.treasury.value=1000000\nkeep.stock.0.value=1000000000\n") == \
        kept(keep__treasury__value=1000000, keep__stock__0__value=1000000000)                # 한도까지는 된다
    # 범위 밖의 값, 0 / 1 이 아닌 켜짐, 없는 칸, 깨진 키 — 모두 그 줄만 버린다
    assert norm("keep.treasury=2\nkeep.treasury.value=1000001\nkeep.treasury.value=-1\nkeep.stock.3=7\nkeep.stock.3.value=1000000001\n"
                "keep.stock.12=1\nkeep.stock.12.value=5\nkeep.stock.-1=1\nkeep.stock.=1\nkeep.stock.x=1\nkeep.stock.3.amount=5\n"
                "keep.stock.3x=1\nkeep.stock=1\nkeep.stock.123=1\nkeep.stock. 3=1\n") == DEFAULTS
    assert norm("keep.stock.5=1\nkeep.stock.5=x\nkeep.stock.6=1\n") == kept(keep__stock__5=1, keep__stock__6=1)
    assert len(kept(**{f"keep__stock__{slot}__value": 1000000000 for slot in range(12)}, keep__treasury__value=1000000)) < 1024   # 읽는 쪽은 4096 까지 읽는다


def test_settings_file_round_trip(dll, tmp_path, monkeypatch):
    monkeypatch.setenv("SRTOYBOX_HOME", str(tmp_path))
    assert text(dll.srtoybox_settings_file) == DEFAULTS                                      # 파일이 없으면 기본값
    assert dll.srtoybox_settings_store(b"hotkey_vk=120\nhotkey_mods=4\ntechnology=140\nkeep.stock.7=1\nkeep.stock.7.value=250000\n") == 1
    saved = kept(keep__stock__7=1, keep__stock__7__value=250000).replace("=84", "=120").replace("mods=3", "mods=4") \
        .replace("=120\nspawn", "=140\nspawn")
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
                         encoding="utf-8", errors="replace", env={**os.environ, "SRTOYBOX_HOME": str(home), **(env or {})}, timeout=120)
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
    assert got["text"] == typed_keys("cheat fullmapshow")
    assert got["hotkey_busy"] == "toybox"           # 넣는 동안에도 단축키는 ToyBox 의 것이고
    assert got["title_after"] == "press+release"    # 그래서 창이 닫혔다
    assert got["mods_left"] == "0"                  # (넣는 중의 단축키가 수정키를 떼므로, 남기는지는 아래 테스트가 가린다)


def test_typing_does_not_leave_the_modifiers_down(dll, cfg, tmp_path):
    """글쇠를 다 넣은 뒤 Ctrl · Shift 가 눌린 채로 남지 않는다. 사용자가 실제로 쥐고 있는 수정키는 남은 것으로 치지 않는다."""
    got = _fields(_probe(cfg, tmp_path, "input_quiet"))
    assert got["typing"] == "1" and got["done"] == "1", got
    assert got["text"] == typed_keys("cheat fullmapshow")
    assert got["mods_left"] == "0"


def test_modifiers_held_before_typing_are_left_as_they_were(dll, cfg, tmp_path):
    """넣기 전부터 눌려 있던 Ctrl · Shift(사용자가 쥐고 있다)는 넣은 뒤에도 눌린 채다 — 그것은 "남은 것"이 아니다.
    테스트가 도는 동안 사용자가 같은 PC 에서 수정키를 쓰면 이 스레드의 키 상태표에 그것이 들어온다."""
    got = _fields(_probe(cfg, tmp_path, "input_held"))
    assert got["typing"] == "1" and got["done"] == "1", got
    assert got["text"] == typed_keys("cheat fullmapshow")
    assert got["mods_before"] == "1" and got["mods_now"] == "1"    # 넣기 전의 상태로 되돌렸다
    assert got["mods_left"] == "0"                                  # 그러니 넣기가 남긴 것은 없다


def test_mouse_follows_the_size_the_game_draws_at(dll, cfg, tmp_path):
    """게임이 창보다 작게 그리면 화면에는 늘어나 보인다. 누른 자리는 보이는 설정 창을 기준으로 가려야 한다."""
    got = _fields(_probe(cfg, tmp_path, "scale"))
    assert got["title"] == "none"                   # 보이는 창의 제목 줄을 눌렀다 — 게임에 새지 않는다
    assert got["beside"] == "press+release"         # 보이는 창의 바깥이다 — 게임이 받는다


def test_the_probe_hotkey_survives_a_real_modifier_key_pressed_elsewhere(dll, cfg, tmp_path):
    """검사 도구의 단축키는 가짜 수정키다: 이 스레드의 키 상태표에 Ctrl · Shift 를 눌린 것으로 적고 T 를 보낸다.
    다른 곳에서 실제 수정키가 눌렸다 떼이면(사용자가 다른 창에서 글을 친다) 그 변화가 이 스레드에 밀려 있다가 다음 GetKeyState 에서
    상태표를 덮는다 — 적어 둔 Ctrl 이 지워져 단축키가 맨 T 로 게임에 새고 창이 열리지 않는다. 화면 검사 테스트가 드물게 아무것이나
    하나씩 실패하던 까닭이다(2026-10-09). 도구가 밀린 변화를 먼저 받아 두어야 한다.

    이 테스트는 시스템에 실제 키 입력을 넣는다(오른쪽 Ctrl 을 눌렀다 뗌, 두 번. 혼자서는 아무 일도 하지 않는 입력이다)."""
    got = _fields(_probe(cfg, tmp_path, "real_key"))
    assert got == {"first": "toybox", "shown": "1", "second": "toybox", "hidden": "1"}


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
    assert got["text"] == typed_keys("cheat fullmapshow")


def test_direct_run_calls_the_games_handler(dll, cfg, tmp_path):
    """게임 안에서는 글쇠를 넣지 않고 게임의 명령 처리 함수에 바로 넘긴다.

    치트 허용이 꺼져 있으면 먼저 cheat allowcheats 를 부르고, 켜져 있으면 다시 부르지 않는다
    (메뉴에 나갔다 오면 게임이 꺼 두므로 그때는 다시 부른다).
    """
    got = _fields(_probe(cfg, tmp_path, "direct"))
    assert got["lines"].replace("_", " ").split("|") == ["cheat allowcheats", "cheat fullmapshow", "cheat fullmapshow",
                                                        "cheat allowcheats", "cheat fullmapshow"]
    assert got["text"] == ""                                    # 글쇠는 가지 않는다 — 게임의 설정 창이 뜨지 않는다
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("직접 실행: cheat fullmapshow") == 3


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
    assert got["lines"] == "" and got["text"] == typed_keys("cheat fullmapshow")


@pytest.mark.parametrize("mode", ["reenter_timer", "reenter_keyup", "reenter_present"])
def test_the_games_handler_may_come_back_into_toybox(dll, cfg, tmp_path, mode):
    """게임의 명령 처리 함수가 일하는 도중에 메시지를 돌리거나 화면을 내보내면 ToyBox 의 타이머 · 입력 · 그리기로 되돌아온다.

    ToyBox 는 그때 아무 잠금도 쥐고 있지 않아야 하고(쥔 채로 되돌아오면 프로세스가 끝난다), 대기열의 다음 명령을
    그 안에서 시작해서도 안 된다(게임의 함수가 겹쳐 불린다).
    """
    got = _fields(_probe(cfg, tmp_path, mode))
    assert got["inside"] == "ok" and got["deepest"] == "1", got
    assert got["lines"].replace("_", " ").split("|") == ["cheat allowcheats"] + ["cheat fullmapshow"] * 3
    assert got["text"] == ""
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "예외" not in log and log.count("직접 실행: cheat fullmapshow") == 3, log


def test_toybox_keeps_drawing_after_an_exception_passes_through_present(dll, cfg, tmp_path):
    """ToyBox 가 부른 다음 함수 안에서 예외가 나고 그것을 위에서 누가 잡으면(게임의 함수를 직접 부르는 ToyBox 자신이 그렇다),
    "지금 훅 안이다"라는 표시가 남아 그 뒤로 영영 그리지 않게 되면 안 된다."""
    got = _fields(_probe(cfg, tmp_path, "present_fault"))
    assert got == {"caught": "1", "drawn": "1"}


def test_srtoybox_read_0_turns_the_game_reading_off(dll, cfg, tmp_path):
    """탈출구: ToyBox 가 게임 안인데도 "게임 밖"으로 잘못 알면(다른 빌드, 보지 못한 화면) 모든 단추가 꺼진 채 풀 길이 없다.
    SRTOYBOX_READ=0 이면 게임을 읽지 않는다 — 1단계처럼 단추가 늘 켜져 있고 글쇠를 넣는다."""
    got = _fields(_probe(cfg, tmp_path, "direct_read_off", env={"SRTOYBOX_READ": "0"}))
    assert got["lines"] == "" and got["text"] == typed_keys("cheat fullmapshow")
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "게임 상태를 읽지 않습니다 (SRTOYBOX_READ=0)" in log, log


FAULT_WARNING = "직접 실행 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오."


def test_an_irreversible_button_says_what_and_to_whom_before_the_second_press(dll, cfg, tmp_path):
    """되돌릴 수 없는 단추는 두 번 눌러야 실행된다. 둘째 누름을 기다리는 단추에는 무엇을 어느 나라에 하는지가 적혀 있고,
    지금 플레이하는 나라와 고른 나라는 탭의 내용을 아래로 내려도 창에 남아 있다."""
    got = json.loads(_probe(cfg, tmp_path, "confirm"))
    assert got["hidden"] == "-" and got["scrolled"] is True     # 그 단추는 탭의 내용을 아래로 내려야 보인다
    assert got["after_first"] == []                             # 처음 누름은 묻기만 한다
    assert got["armed"] == "이 나라로 플레이: 폴란드 (1106) — 한 번 더 누르면 실행합니다"
    assert got["status"] == "플레이 중: 독일 (1499)" and got["picked"] == "고른 나라: 폴란드 (1106)"
    assert got["lines"] == ["cheat allowcheats", "cheat becomeregion 1106"]


def test_the_fault_warning_stays_in_sight(dll, cfg, tmp_path):
    """직접 실행이 죽은 뒤의 경고("저장하지 말고…")는 어느 탭의 어디를 보고 있어도 보여야 한다."""
    got = json.loads(_probe(cfg, tmp_path, "confirm_fault"))
    assert got["at_top"] == FAULT_WARNING
    assert got["scrolled"] is True and got["scrolled_down"] == FAULT_WARNING


@pytest.mark.parametrize("env, in_game", [({}, "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다."),
                                          ({"SRTOYBOX_DIRECT": "0"}, "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.")],
                         ids=["direct", "typing"])
def test_the_hint_is_about_the_game_only_while_in_a_game(dll, cfg, tmp_path, env, in_game):
    """바닥의 안내는 게임 화면에 무슨 일이 생기는지를 말한다. 메뉴에서는 단추가 꺼져 있으므로 띄우지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "hints", env=env))
    assert got == {"menu": "-", "game": in_game}


@pytest.mark.parametrize("mode, status", [("leave", "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"),
                                          ("multiplayer", "멀티플레이에서는 동작하지 않습니다")], ids=["leave", "multiplayer"])
def test_direct_run_is_dropped_when_the_game_stops_being_playable_first(dll, cfg, tmp_path, mode, status):
    """직접 실행의 길에서도: 단추를 누른 뒤 실행되기 전에 게임에서 나가거나 멀티플레이가 되면 게임의 함수를 부르지 않는다
    (그 함수는 게임이 진행 중인지 검사하지 않는다). 그동안 단추는 꺼져 있고, 돌아오면 다시 된다."""
    got = json.loads(_probe(cfg, tmp_path, mode))
    assert got["dropped"] == [] and got["trouble"] == "게임이 진행 중이 아니어서 실행하지 않았습니다."
    assert got["status"] == status and got["while_off"] == []
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]


@pytest.mark.parametrize("mode, status", [("pick_gone", "플레이 중: 독일 (1499)"), ("pick_become", "플레이 중: 폴란드 (1106)")],
                         ids=["gone", "become"])
def test_the_pick_is_dropped_when_that_country_can_no_longer_be_a_target(dll, cfg, tmp_path, mode, status):
    """고른 나라가 이번 판에서 없어지거나(다른 판을 불러왔다) 플레이하는 나라가 그 나라가 되면, 고른 것이 풀리고
    나라를 고르는 단추는 다시 고를 때까지 꺼진다."""
    got = json.loads(_probe(cfg, tmp_path, mode))
    assert got["first"] == [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]   # 고른 동안에는 "관계 최고"가 폴란드와의 관계를 쓴다(양쪽에)
    assert got["status"] == status and got["row"] == "-"
    assert got["picked"] == "고른 나라: 없음 — 아래 목록에서 고르십시오"
    assert got["later"] == [[0.25, -0.5, 0.75], [0.125, 0.5, 1.0]] and got["unwritten"] == "-"   # 풀린 뒤의 누름은 아무것도 쓰지 않는다
    assert got["lines"] == []                                   # 이 단추는 게임의 함수를 부르지 않는다


def test_picking_another_country_starts_the_confirmation_over(dll, cfg, tmp_path):
    """"한 번 더 누르면 실행합니다"를 기다리는 중에 다른 나라를 고르면, 다음 누름이 새 나라에 곧바로 실행되면 안 된다."""
    got = json.loads(_probe(cfg, tmp_path, "pick_again"))
    assert got["asked"] == "이 나라로 플레이: 폴란드 (1106) — 한 번 더 누르면 실행합니다"
    assert got["after_repick"] == "이 나라로 플레이" and got["after_one_press"] == []
    assert got["asked_again"] == "이 나라로 플레이: 덴마크 (1201) — 한 번 더 누르면 실행합니다"
    assert got["lines"] == ["cheat allowcheats", "cheat becomeregion 1201"]


def test_hangul_typed_into_an_ansi_game_window_reaches_the_search_box_whole(dll, cfg, tmp_path):
    """ANSI 창에는 한글 한 글자가 글자 메시지 두 번(코드 페이지의 앞 · 뒤 바이트)으로 온다. 설정 창이 둘을 합쳐 받아야 한다."""
    got = json.loads(_probe(cfg, tmp_path, "ansi_search"))
    assert got["ansi"] == 1
    assert got["search"] == "폴" and got["rows"] == ["row:1106"]   # 폴란드만 남는다


MONEY_BUTTONS = ["money:+100b", "money:+10b", "money:-100b", "money:-10b", "money:add", "money:set", "money:sub", "money:zero"]
VALUES_FAILED = "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다."


def test_the_money_tab_writes_the_treasury_without_any_cheat(dll, cfg, tmp_path):
    """요구 3: 돈 탭은 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고, 글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다.
    쓰는 곳은 플레이어의 국고뿐이다(다른 나라의 국고는 그대로다)."""
    got = json.loads(_probe(cfg, tmp_path, "money"))
    assert got["now"] == "국고: $ 14.43 B" and got["off"] == "-"
    assert got["buttons"] == MONEY_BUTTONS and got["cheat_buttons"] == []
    # +$10 B, +$100 B, -$10 B, -$100 B, $0, 더하기 × 2, 빼기, +$10 B, 이 값으로 (입력란은 1234 백만 달러)
    assert got["steps"] == [24.43e9, 124.43e9, 114.43e9, 14.43e9, 0.0, 1.234e9, 2.468e9, 1.234e9, 11.234e9, 1.234e9]
    assert got["amount"] == "1234" and got["now_after"] == "국고: $ 1.23 B" and got["wrote"] == "국고 11.23 B -> 1.23 B"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["poland"] == 5e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: 국고") == 10 and "직접 실행" not in log


DIRECT_HINT = "값은 바로 바뀝니다. 게임 화면의 숫자는 그 패널을 누르거나 다시 열 때 따라옵니다."


@pytest.mark.parametrize("env", [{}, {"SRTOYBOX_DIRECT": "0"}], ids=["direct", "typing"])
def test_the_hint_on_a_value_tab_never_talks_about_the_typing_route(dll, cfg, tmp_path, env):
    """돈 · 물자 탭은 글쇠 방식과 상관없다. 내장 치트로 도는 기능이 글쇠 방식으로 돌 때(SRTOYBOX_DIRECT=0, 옛 찾기 실패)에도
    이 탭들의 바닥 안내는 "게임의 설정 창이 잠깐 열렸다 닫힙니다"가 아니다."""
    got = json.loads(_probe(cfg, tmp_path, "money_hint", env=env))
    assert got["hint"] == DIRECT_HINT and got["stock_hint"] == DIRECT_HINT
    assert got["cheat_hint"] == (DIRECT_HINT if not env else "단추를 누르면 게임의 설정 창이 잠깐 열렸다 닫힙니다.")


def test_money_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "money_menu"))
    assert got["now"] == "국고: -" and got["buttons"] == MONEY_BUTTONS       # 단추는 보이지만 꺼져 있다
    assert got["steps"] == [14.43e9] and got["lines"] == [] and got["text"] == ""
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_money_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "money_leave"))
    assert got["dropped"] == 14.43e9 and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["steps"] == [24.43e9] and got["unwritten_after"] == "-"


@pytest.mark.parametrize("mode, env, why", [
    ("money_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)"),
    ("money_notfound", {}, "이 게임 판에서는 쓸 수 없습니다 (값의 자리를 주지 않았습니다)"),
    ("money_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다."),
    ("money_unreadable", {}, "게임의 값을 읽을 수 없어 쓸 수 없습니다."),
], ids=["write-off", "not-found", "unread", "unreadable"])
def test_the_money_tab_says_why_it_is_off_and_offers_no_cheat(dll, cfg, tmp_path, mode, env, why):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 까닭 한 줄만 보이고 단추가 없다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert got["off"] == why and got["now"] == "-" and got["hint"] == "-"
    assert got["buttons"] == [] and got["cheat_buttons"] == []
    assert got["stock_off"] == why and got["stock_rows"] == [] and got["stock_cheats"] == []      # 물자 탭도 같다
    assert got["lines"] == [] and got["text"] == ""


def test_a_failed_write_turns_the_money_tab_off_and_says_why(dll, cfg, tmp_path):
    """쓸 수 없는 곳을 만나면 죽지 않고, 이번 실행에서 값 쓰기를 끄고 까닭을 보인다."""
    got = json.loads(_probe(cfg, tmp_path, "money_fail"))
    assert got["now"] == "국고: $ 14.43 B" and got["steps"] == [14.43e9]
    assert got["off_after"] == VALUES_FAILED and got["buttons_after"] == []
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (국고) — 값 쓰기를 끕니다") == 1


def test_money_is_not_written_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 와도, 그 안에서는 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "money_reenter"))
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [14.43e9, 14.43e9]                  # 그 함수 안에서 다시 온 타이머의 앞뒤
    assert got["after"] == 24.43e9                              # 함수가 끝난 뒤에 쓴다


def test_values_are_not_written_after_the_fault_guard_trips(dll, cfg, tmp_path):
    """직접 실행의 오류 가드가 걸린 뒤에는 값 쓰기도 멈춘다 — 대기열에 먼저 들어와 있던 국고 요청도 버린다."""
    got = json.loads(_probe(cfg, tmp_path, "money_fault"))
    assert got["fault"] == FAULT_WARNING and got["after"] == 14.43e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "값 쓰기: " not in log


STOCK_BUTTONS = ["+100m", "+1m", "-100m", "-1m", "zero"]
PRODUCTS = ["농산물", "고무", "목재", "석유", "석탄", "금속 광석", "우라늄", "전력", "소비재", "산업재", "군수품"]


def test_the_stock_tab_writes_stock_without_any_cheat(dll, cfg, tmp_path):
    """요구 3: 물자 탭도 내장 치트를 거치지 않는다. 이번 판에서 쓰는 물자만 줄로 나오고, "모든 물자" 줄은 그 물자들에만 닿는다.
    쓰는 곳은 플레이어의 재고뿐이다(다른 나라의 재고, 쓰지 않는 물자의 칸은 그대로다)."""
    got = json.loads(_probe(cfg, tmp_path, "stock"))
    assert got["off"] == "-" and got["hint"] == DIRECT_HINT and got["cheat_buttons"] == []
    assert got["rows"] == [["stock:all", "모든 물자", "-"], ["stock:0", "농산물", "1.0 K"], ["stock:3", "석유", "2.5 M"],
                           ["stock:7", "전력", "0"], ["stock:11", "물자 #11", "5"]]     # 열두째 칸은 이름이 없어도 쓰는 판이면 나온다
    assert got["buttons"] == STOCK_BUTTONS
    # 재고의 칸 0 · 3 · 7 · 11 과 쓰지 않는 칸 5. 석유 +100만, -1억, +1억, 0 / 모든 물자 +100만, -1억 / 농산물 +1억
    assert got["steps"] == [[1000.0, 3.5e6, 0.0, 5.0, 0.0], [1000.0, 0.0, 0.0, 5.0, 0.0], [1000.0, 1e8, 0.0, 5.0, 0.0],
                            [1000.0, 0.0, 0.0, 5.0, 0.0], [1001000.0, 1e6, 1e6, 1000005.0, 0.0], [0.0, 0.0, 0.0, 0.0, 0.0],
                            [1e8, 0.0, 0.0, 0.0, 0.0]]
    assert got["wrote_all"] == "모든 물자 4개" and got["wrote"] == "농산물 0 -> 100 M" and got["now_after"] == "100 M"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["poland"] == 777.0
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: 석유") == 6 and log.count("값 쓰기: ") == 13 and "직접 실행" not in log


def test_the_stock_tab_lists_the_named_products_outside_a_game(dll, cfg, tmp_path):
    """메뉴에서는 이름표의 물자 열하나가 재고 없이 나오고 단추가 꺼져 있다."""
    got = json.loads(_probe(cfg, tmp_path, "stock_menu"))
    assert got["rows"] == [["stock:all", "모든 물자", "-"]] + [[f"stock:{slot}", name, "-"] for slot, name in enumerate(PRODUCTS)]
    assert got["buttons"] == STOCK_BUTTONS and got["hint"] == "-"
    assert got["steps"] == [[1000.0, 2.5e6, 0.0, 5.0, 0.0]] and got["lines"] == [] and got["text"] == ""
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


KEEP_NOTE = "최소 유지를 켜 두면"


def test_keep_works_with_the_window_closed_and_shows_in_the_status_line(dll, cfg, tmp_path):
    """최소 유지: 저장해 둔 설정이 게임에 들어가자마자, 설정 창을 한 번도 열지 않아도 적용된다. 상태 줄에 무엇이 유지되는지 늘 보이고,
    창에서 켜고 끄면 바로 따른다. 내장 치트는 거치지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "keep"))
    assert got["closed"] == [14.43e9, 5e6, 0.0]                 # 창을 열기 전: 석유만 250만 → 500만(국고의 유지는 꺼져 있다)
    assert got["status"] == "플레이 중: 독일 (1499) · 유지 중: 석유"
    assert got["money"] == ["0", "20000"]                        # 돈 탭의 체크와 입력란(저장해 둔 값)
    assert got["on"] == 20e9 and got["status_on"] == "플레이 중: 독일 (1499) · 유지 중: 국고, 석유"
    assert got["back"] == 20e9                                   # -$10 B 로 내려도 0.5초 안에 돌아온다
    assert got["off"] == 10e9 and got["status_off"] == "플레이 중: 독일 (1499) · 유지 중: 석유"   # 끄면 내린 채로 있다
    # 물자 탭: 유지가 켜진 물자는 이번 판에서 쓰지 않아도 줄이 남는다(끌 수 있게). 단추는 꺼져 있고, 유지되지도 않는다
    assert got["rows"] == [["stock:all", "모든 물자", "-"], ["stock:0", "농산물", "1.0 K"], ["stock:3", "석유", "5.0 M"],
                           ["stock:4", "석탄", "쓰지 않음"], ["stock:7", "전력", "0"]]
    assert got["keeps"] == {"stock:0": ["0", "0"], "stock:3": ["1", "5000000"], "stock:4": ["1", "100"], "stock:7": ["0", "0"]}
    assert got["unused_press"] == 0.0                            # 쓰지 않는 물자의 단추는 꺼져 있다
    assert got["stock_off"] == [0.0, 0.0]                        # 석유의 유지를 끄고 0 으로 만들면 0 인 채로 있다
    assert got["status_end"] == "플레이 중: 독일 (1499)" and got["rows_end"] == ["stock:all", "stock:0", "stock:3", "stock:7"]
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0
    saved = (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")
    assert saved == kept(keep__treasury__value=20000, keep__stock__3__value=5000000, keep__stock__4__value=100)   # 모두 꺼진 채로 저장됐다
    log = [line.split(" ", 2)[2] for line in (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8").splitlines()]
    assert [line for line in log if line.startswith("유지")] == [
        "유지 켬: 석유 5000000", "유지 켬: 석탄 100", "유지: 석유 2.5 M -> 5.0 M", "유지 켬: 국고 20000 (백만 달러)",
        "유지: 국고 14.43 B -> 20.00 B", "유지 끔: 국고", "유지 끔: 석탄", "유지 끔: 석유"]
    assert [line for line in log if line.startswith("값 쓰기")] == ["값 쓰기: 국고 20.00 B -> 10.00 B", "값 쓰기: 국고 20.00 B -> 10.00 B",
                                                                  "값 쓰기: 석유 5.0 M -> 0"]
    assert "직접 실행" not in " ".join(log)


def test_keep_rests_in_the_menu_and_can_be_turned_off_there(dll, cfg, tmp_path):
    """게임 밖에서는 쉬지만 상태 줄에 켜진 수가 보이고, 단추가 꺼진 탭에서도 유지는 끌 수 있다(켜 둔 것을 잊고 새 판을 시작하지 않게)."""
    got = json.loads(_probe(cfg, tmp_path, "keep_menu"))
    assert got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다 · 유지 2개 켜짐(게임에 들어가면 적용)"
    assert got["rested"] == [14.43e9, 2.5e6] and got["keeps"]["stock:3"] == ["1", "5000000"]
    assert got["status_off"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다 · 유지 1개 켜짐(게임에 들어가면 적용)"
    assert got["entered"] == [14.43e9, 2.5e6, 100.0]            # 게임에 들어가면 남은 유지(석탄 100)만 적용된다 — 석탄을 쓰는 판이다
    assert "keep.stock.3=0\n" in (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")


def test_keep_does_not_write_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안에는, 유지를 볼 때가 됐어도 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "keep_reenter"))
    assert got["before"] == 20e9                                 # 유지가 돌고 있다
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [1e9]                                # 그 함수 안에서 다시 온 타이머는 바닥 아래가 된 국고를 올리지 않았다
    assert got["after"] == 20e9                                  # 함수가 끝난 뒤에 올린다


def test_the_status_line_does_not_promise_a_keep_that_cannot_run(dll, cfg, tmp_path):
    """값 쓰기가 꺼져 있으면(SRTOYBOX_WRITE=0, 값의 자리를 못 찾았다, 쓰기가 실패했다) 유지는 게임에 들어가도 돌지 않는다.
    메뉴의 상태 줄이 "게임에 들어가면 적용"이라고 하면 안 된다 — 유지 검사(keeper)와 같은 순서로 까닭을 고른다."""
    got = json.loads(_probe(cfg, tmp_path, "keep_write_off", env={"SRTOYBOX_WRITE": "0"}))
    resting = " · 유지 2개 켜짐(값을 쓸 수 없어 쉽니다)"
    assert got["status_menu"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다" + resting
    assert got["status_game"] == "플레이 중: 독일 (1499)" + resting
    assert got["rested"] == [14.43e9, 2.5e6, 0.0]                # 게임에 들어가도 쓰지 않는다


def test_every_product_row_shows_in_a_window_opened_for_the_first_time(dll, cfg, tmp_path):
    """처음 여는 창에서 "모든 물자"와 물자 열하나의 줄이 굴리지 않아도 모두 보인다 — 바닥에 "마지막으로 쓴 값" 줄이 있어도."""
    got = json.loads(_probe(cfg, tmp_path, "layout_full"))
    assert got["wrote"] == "농산물 1.0 K -> 1.0 M" and got["rows"] == 12
    assert got["hidden"] == []


def test_the_keep_help_stays_inside_a_narrow_window(dll, cfg, tmp_path):
    """이미 써 본 사용자의 창은 저장된 크기(500x460) 그대로다. 최소 유지의 긴 안내 글이 창 밖으로 잘리지 않는다(줄을 바꾼다)."""
    got = json.loads(_probe(cfg, tmp_path, "layout_saved"))
    assert got["money_help_right"] != "-" and int(got["money_help_right"]) <= 540      # 창은 x = 40 … 540
    assert got["help_right"] != "-" and int(got["help_right"]) <= 540


def test_a_typed_keep_amount_takes_effect_when_the_typing_is_done(dll, cfg, tmp_path):
    """수량을 치는 동안의 값(7, 70, 700 …)은 쓰이지 않는다. Enter 를 누르거나 다른 곳을 누르면 쓰이고, 치던 채로 창을 닫으면 버려진다."""
    got = json.loads(_probe(cfg, tmp_path, "keep_type"))
    assert got["typing"] == [5e6, "5000000"]                     # 다 쳤지만 아직 입력란 안이다 — 유지는 앞의 수량(500만) 그대로다
    assert got["entered"] == [7e6, "7000000"]                    # Enter
    assert got["clicked_away"] == [9e6, "9000000"]               # 다시 치고 다른 곳을 눌렀다
    assert got["closed"] == [9e6, "9000000"]                     # 또 치다가 창을 닫았다 — 친 것은 버려진다
    assert got["text"] == ""                                     # 친 글자는 게임에 가지 않았다
    assert "keep.stock.3.value=9000000\n" in (tmp_path / "home" / "toybox.ini").read_text(encoding="utf-8")
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("유지 켬: 석유") == 3                        # 뜰 때의 500만, 고친 700만 · 900만


MORE_START = {"tech": 130.0, "opinion": [0.5, 0.25, 0.75], "poland": [[0.25, -0.5, 0.75], [0.125, 0.5, 1.0]],
              "denmark": [[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]]}
MORE_DONE = {"tech": 132.0, "opinion": [1.0, 1.0, 1.0], "poland": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], "denmark": MORE_START["denmark"]}
RESEARCH_ROWS = ["run:technology", "run:e=mc2", "run:finalexam"]
PEOPLE_ROWS = ["run:populate", "run:shelovesme", "run:approval"]
DIPLOMACY_ROWS = ["run:love", "run:neutral", "run:treaty", "run:annex", "run:colonize", "run:novichok", "run:fight", "run:becomeregion"]


@pytest.mark.parametrize("mode", ["more", "more_alone"], ids=["with-money-and-stock", "alone"])
def test_the_four_moved_buttons_write_without_any_cheat(dll, cfg, tmp_path, mode):
    """요구 3: 지식 순위 · 세계 시장 여론 · 관계 최고 · 관계 중립은 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고,
    글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다. 단추의 이름과 자리는 그대로다. 쓰는 곳은 플레이어의 칸과,
    관계라면 고른 나라의 "플레이어" 칸뿐이다(덴마크와의 관계는 그대로다). 국고 · 재고의 자리를 못 찾은 게임에서도 된다."""
    got = json.loads(_probe(cfg, tmp_path, mode))
    assert list(got["research"]) == RESEARCH_ROWS and got["research"]["run:finalexam"] == "지식 순위 올리기"
    assert list(got["people"]) == PEOPLE_ROWS and got["people"]["run:shelovesme"] == "세계 시장 여론 최고"
    assert list(got["diplomacy"]) == DIPLOMACY_ROWS
    assert (got["diplomacy"]["run:love"], got["diplomacy"]["run:neutral"]) == ("관계 최고", "관계 중립")
    assert got["wrote_tech"] == "기술 수준 131 -> 132" and got["wrote_opinion"] == "세계 시장 여론 최고"
    assert got["unpicked"] == {**MORE_START, "tech": 132.0, "opinion": [1.0, 1.0, 1.0]}       # 나라를 고르기 전의 누름은 쓰지 않는다
    assert got["after_love"] == {**got["unpicked"], "poland": [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]}
    assert got["wrote_love"] == "관계 최고 — 폴란드 (1106)" and got["wrote_neutral"] == "관계 중립 — 폴란드 (1106)"
    assert got["state"] == MORE_DONE and got["status"] == "플레이 중: 독일 (1499)"
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0 and got["treasury"] == 14.43e9
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기: ") == 5 and "직접 실행" not in log and "값 쓰기 실패" not in log


def test_the_moved_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "more_menu"))
    assert list(got["research"]) == RESEARCH_ROWS and list(got["people"]) == PEOPLE_ROWS    # 단추는 보이지만 꺼져 있다
    assert got["state"] == MORE_START and got["wrote_neutral"] == "-"
    assert got["lines"] == [] and got["text"] == "" and got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_moved_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "more_leave"))
    assert got["dropped"] == 130.0 and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["state"]["tech"] == 131.0 and got["unwritten_after"] == "-"


def test_a_relation_is_written_with_the_country_picked_when_the_button_was_pressed(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰이기 전(다음 타이머 전)에 다른 나라를 골라도, 쓰는 것은 누른 때에 골라 둔 나라와의 관계다."""
    got = json.loads(_probe(cfg, tmp_path, "more_repick"))
    assert got["picked"] == "고른 나라: 덴마크 (1201)" and got["wrote"] == "관계 최고 — 폴란드 (1106)"
    assert got["state"] == {**MORE_START, "poland": [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]]}     # 덴마크와의 관계는 그대로다
    assert got["lines"] == []


def test_a_group_that_was_not_found_turns_off_only_its_own_button(dll, cfg, tmp_path):
    """묶음마다 따로 꺼진다: 기술 수준의 자리만 못 찾은 게임에서는 "지식 순위 올리기"의 자리에 까닭 한 줄만 보이고,
    같은 탭의 다른 줄과 나머지 직접 쓰는 줄은 그대로 동작한다. 내장 치트로 되돌아가지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_notfound"))
    assert list(got["research"]) == ["run:technology", "run:e=mc2", "off:finalexam"]
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — 이 게임 판에서는 쓸 수 없습니다 (값의 자리를 주지 않았습니다)"
    assert list(got["people"]) == PEOPLE_ROWS and list(got["diplomacy"]) == DIPLOMACY_ROWS
    assert got["state"] == {**MORE_DONE, "tech": 130.0}
    assert got["lines"] == [] and got["text"] == ""


@pytest.mark.parametrize("mode, env, why", [
    ("more_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)"),
    ("more_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다."),
], ids=["write-off", "unread"])
def test_the_moved_buttons_say_why_they_are_off_and_offer_no_cheat(dll, cfg, tmp_path, mode, env, why):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 그 줄의 단추 자리에 까닭 한 줄만 보인다. 내장 치트로 도는 줄은 그대로다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    assert list(got["research"]) == ["off:technology", "off:e=mc2", "off:finalexam"]          # 연구 탭의 세 줄은 모두 직접 쓰는 줄이다
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — " + why
    assert list(got["people"]) == ["run:populate", "off:shelovesme", "run:approval"]
    assert got["people"]["off:shelovesme"] == "세계 시장 여론 최고 — " + why
    if mode == "more_unread":
        assert got["diplomacy"] == {}                           # 게임을 읽지 못하면 이 탭은 통째로 쓸 수 없다(나라 목록이 없다)
    else:
        assert list(got["diplomacy"]) == ["off:love", "off:neutral"] + DIPLOMACY_ROWS[2:]
        assert got["diplomacy"]["off:love"] == "관계 최고 — " + why and got["diplomacy"]["off:neutral"] == "관계 중립 — " + why
    assert got["state"] == MORE_START and got["lines"] == [] and got["text"] == ""


def test_a_failed_write_of_a_moved_button_turns_value_writing_off_and_says_why(dll, cfg, tmp_path):
    """쓸 수 없는 곳을 만나면 죽지 않고, 이번 실행에서 값 쓰기 전체를 끄고 까닭을 보인다. 반쪽만 쓴 관계는 남지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_fail"))
    assert got["state"] == MORE_START
    assert got["diplomacy"]["off:love"] == "관계 최고 — " + VALUES_FAILED and "run:love" not in got["diplomacy"]
    assert got["research"]["off:finalexam"] == "지식 순위 올리기 — " + VALUES_FAILED and got["money_off"] == VALUES_FAILED
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert log.count("값 쓰기 실패 (관계 — 폴란드 (1106)) — 값 쓰기를 끕니다") == 1 and "값 쓰기: " not in log


def test_a_moved_button_does_not_write_while_the_games_handler_is_running(dll, cfg, tmp_path):
    """옮기지 않은 기능의 직접 실행이 게임의 함수 안에 있는 동안 타이머가 다시 와도, 그 안에서는 게임의 메모리에 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "more_reenter"))
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow"]
    assert got["inside"] == [130.0, 130.0]                      # 그 함수 안에서 다시 온 타이머의 앞뒤
    assert got["state"]["tech"] == 131.0                        # 함수가 끝난 뒤에 쓴다


def test_moved_buttons_do_not_write_after_the_fault_guard_trips(dll, cfg, tmp_path):
    """직접 실행의 오류 가드가 걸린 뒤에는 값 쓰기도 멈춘다 — 대기열에 먼저 들어와 있던 요청도 버린다."""
    got = json.loads(_probe(cfg, tmp_path, "more_fault"))
    assert got["fault"] == FAULT_WARNING and got["state"] == MORE_START
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "값 쓰기: " not in log


# 연구의 판(toybox_fake_game.standard_lab)에서 [독일의 기술, 독일의 부대 설계, 폴란드의 기술, 폴란드의 부대 설계]
HELD_START = [[1, 4, 6], [10, 13, 14], [1, 2], [11, 13]]
HELD_QUEUE = [[1, 2, 3, 4, 6], [10, 11, 13, 14], [1, 2], [11, 13]]          # 대기열의 기술 2(+ 선행은 이미 보유) · 부대 설계 11(+ 선행 3)
HELD_LEVEL = [[1, 2, 3, 4, 6, 7], [10, 11, 13, 14], [1, 2], [11, 13]]       # 거기에 수준 120 이하의 남은 기술 7
RESEARCH_BUTTONS = {"value:technology": "120", "run:technology": "기술 수준 N 이하 전부 보유", "run:e=mc2": "대기열의 연구 즉시 완료",
                    "run:finalexam": "지식 순위 올리기"}
RESEARCH_FAULT = "효과를 다시 셈하는 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오."


@pytest.mark.parametrize("env", [{}, {"SRTOYBOX_DIRECT": "0"}], ids=["direct", "typing"])
def test_the_two_research_buttons_write_without_any_cheat(dll, cfg, tmp_path, env):
    """요구 3: "대기열의 연구 즉시 완료"와 "기술 수준 N 이하 전부 보유"는 내장 치트를 거치지 않는다 — 명령 처리 함수를 부르지 않고,
    글쇠를 넣지 않고, 치트 허용 비트를 건드리지 않는다. 단추의 이름과 자리는 그대로다.
    사용자가 알린 문제: 내장 치트는 대기열의 부대 설계를 끝내지 않았다 — 이제 설계 11 도 끝난다.
    내장 치트는 모든 기술의 연구 기간을 1일로 바꿨다(모든 나라의 표) — 이제 그대로다. 다른 나라의 보유도 그대로다.
    게임의 함수는 "효과를 다시 셈" 하나만, 플레이어의 지역 인덱스로만 부른다. 내장 치트가 글쇠 방식이어도 이 탭은 상관없다."""
    got = json.loads(_probe(cfg, tmp_path, "research", env=env))
    assert got["rows"] == RESEARCH_BUTTONS and list(got["rows"]) == list(RESEARCH_BUTTONS)
    assert got["after_queue"] == HELD_QUEUE and got["wrote_queue"] == "기술 2개(선행 1개 포함) · 부대 설계 1개를 완료로 — 대기열"
    assert got["held"] == HELD_LEVEL and got["wrote_level"] == "기술 1개를 완료로 — 기술 수준 120 이하"
    assert got["unwritten"] == "바꿀 것이 없습니다 — 대기열"                 # 세 번째 누름: 대기열이 비었다
    assert got["days"] == [100.0] and got["recomputed"] == [176, 176]
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0
    assert got["hint"] == DIRECT_HINT and got["status"] == "플레이 중: 독일 (1499)"
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "연구 완료 (대기열): 기술 2개(선행 1개 포함) · 부대 설계 1개 · 대기열에서 2개 · 새 묶음 1개" in log
    assert "연구 완료 (기술 수준 120 이하): 기술 1개" in log and "연구 완료 (대기열): 바꿀 것이 없습니다" in log
    assert "직접 실행" not in log and "실패" not in log


def test_the_research_buttons_are_off_outside_a_game(dll, cfg, tmp_path):
    got = json.loads(_probe(cfg, tmp_path, "research_menu"))
    assert got["rows"] == RESEARCH_BUTTONS                      # 단추는 보이지만 꺼져 있다
    assert got["held"] == HELD_START and got["wrote_level"] == "-" and got["recomputed"] == []
    assert got["lines"] == [] and got["text"] == "" and got["status"] == "게임을 진행 중이 아닙니다 — 단추가 꺼져 있습니다"


def test_a_research_request_is_dropped_when_the_game_ends_first(dll, cfg, tmp_path):
    """단추를 누른 뒤 쓰기 전에 게임에서 나가면 쓰지 않고 버린다. 돌아온 뒤에 뒤늦게 쓰이지 않고, 새로 누르면 된다."""
    got = json.loads(_probe(cfg, tmp_path, "research_leave"))
    assert got["dropped"] == HELD_START and got["unwritten"] == "게임이 진행 중이 아니어서 쓰지 않았습니다."
    assert got["held"] == HELD_QUEUE and got["unwritten_after"] == "-" and got["recomputed"] == [176]


@pytest.mark.parametrize("mode, env, why, third", [
    ("research_notfound", {}, "이 게임 판에서는 쓸 수 없습니다 (연구의 자리를 주지 않았습니다)", None),
    ("research_write_off", {"SRTOYBOX_WRITE": "0"}, "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)", "off"),
    ("research_unread", {"SRTOYBOX_READ": "0"}, "게임 상태를 읽을 수 있을 때만 씁니다.", "off"),
], ids=["not-found", "write-off", "unread"])
def test_the_research_buttons_say_why_they_are_off_and_offer_no_cheat(dll, cfg, tmp_path, mode, env, why, third):
    """쓸 수 없을 때 내장 치트로 되돌아가지 않는다 — 단추 자리에 까닭 한 줄만 보인다(입력란도 없다).
    연구의 자리만 못 찾은 게임에서는 두 줄만 꺼지고 "지식 순위 올리기"는 제 묶음대로 남는다."""
    got = json.loads(_probe(cfg, tmp_path, mode, env=env))
    rows = got["rows"]
    assert list(rows) == ["off:technology", "off:e=mc2", "run:finalexam" if third is None else "off:finalexam"]
    assert rows["off:technology"] == "기술 수준 N 이하 전부 보유 — " + why and rows["off:e=mc2"] == "대기열의 연구 즉시 완료 — " + why
    assert got["lines"] == [] and got["text"] == "" and got["recomputed"] == []
    if mode != "research_notfound":
        assert got["held"] == HELD_START and got["hint"] == "-"      # 쓸 수 있는 줄이 없다 — 바닥의 안내도 없다


def test_a_fault_while_recomputing_stops_toybox_and_says_so(dll, cfg, tmp_path):
    """게임의 "효과를 다시 셈"에서 예외가 나면 ToyBox 가 잡는다: 게임은 죽지 않고, 빨간 경고가 뜨고, 그 뒤로는 아무것도 쓰지 않는다."""
    got = json.loads(_probe(cfg, tmp_path, "research_fault"))
    assert got["fault"] == RESEARCH_FAULT
    assert got["after_fault"] == HELD_QUEUE == got["held"]      # 비트는 예외 전에 썼다. 그 뒤의 "기술 수준" 단추는 듣지 않는다
    log = (tmp_path / "home" / "toybox.log").read_text(encoding="utf-8")
    assert "효과를 다시 셈하는 중 예외 0xC0000005 — ToyBox 를 멈춥니다" in log and "기술 수준 120 이하" not in log


def test_no_cheat_starts_while_the_game_is_recomputing(dll, cfg, tmp_path):
    """"효과를 다시 셈" 안에서 타이머가 다시 와도 그 안에서는 대기열의 내장 치트를 시작하지 않는다 — 직접 실행과 한 쌍의 깃발을 쓴다."""
    got = json.loads(_probe(cfg, tmp_path, "research_reenter"))
    assert len(got["inside"]) == 2 and got["inside"][0] == got["inside"][1]      # 그 안에서 다시 온 타이머의 앞뒤로 명령 처리 함수가 불린 수
    assert got["lines"] == ["cheat allowcheats", "cheat fullmapshow", "cheat fullmapshow"]      # 둘째 치트는 그 뒤에 돈다
    assert got["held"] == HELD_QUEUE and got["recomputed"] == [176]


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


# ---- 연구의 목록(3단계 3 (나)) ----

LIST_TABLES = """slots 16 16
t 1 1 10 0 0 1 1 1 1
t 2 3 20 1 0 0 1 1 1
t 3 3 30 2 0 0 0 0 0
t 49 5 20 0 0 0 1 2 0
d 10 1 0 1 1 1 0 0 0 0 0 0 50 Leopard_2A4
d 11 1 0 0 1 0 0 0 0 1 1 2 95 Panther
d 12 1 0 0 0 0 0 0 0 0 0 14 60
q 1 2 1 0
"""


def test_research_list_rows_follow_the_view(dll):
    """목록의 줄: 보기 여섯 · 분류 · 찾기로 거르고, 수준(연도) · 번호의 순서로 놓는다. 상태는 보유 > 연구 중 > 미보유."""
    dll.srtoybox_research_rows.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    rows = lambda designs, show, kind=-1, find="": text(dll.srtoybox_research_rows, LIST_TABLES.encode(), designs, show, kind,
                                                        find.encode("utf-8")).splitlines()
    ids = lambda *a, **k: [int(line.split("|")[0]) for line in rows(*a, **k)]
    assert rows(0, 0) == ["1|고효율 핵융합 발전|전쟁|10|보유|1|1", "2|개량 폐기물 소각|과학|20|연구 중|1|1", "49|비생식 복제|의료|20|미보유|2|0",
                          "3|물 절약|과학|30|미보유|0|0"]                    # 전체: 수준 · 번호의 순서
    assert ids(0, 1) == [1] and ids(0, 2) == [2, 49, 3]                     # 자국 보유 / 자국 미보유
    assert ids(0, 3) == [2, 49]                                             # 타국만 보유
    assert ids(0, 4) == [1, 2] and ids(0, 5) == [2]                         # 고른 나라의 보유 / 고른 나라에서 가져올 것
    assert ids(0, 0, kind=3) == [2, 3] and ids(0, 2, kind=5) == [49]        # 분류
    assert ids(0, 0, find="복제") == [49] and ids(0, 0, find="CLONING") == [49] and ids(0, 0, find="4") == [49]   # 이름(한글 · 영문) · 번호
    assert rows(1, 0) == ["10|Leopard_2A4|보병|1950|보유|0|0", "12|#12|공중 수송|1960|미보유|0|0", "11|Panther|전차|1995|미보유|1|1"]
    assert ids(1, 0, kind=2) == [11] and ids(1, 0, find="pan") == [11] and ids(1, 5) == [11]


def test_research_names(dll):
    """기술의 이름은 번역 표에서(없으면 #번호), 분류 · 병과의 이름은 ToyBox 의 표에서. 부대 설계의 이름은 CP1252 로 풀어 UTF-8 로."""
    dll.srtoybox_tech_names.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    names = lambda *a: text(dll.srtoybox_tech_names, *a).split("\n")
    assert names(49, 1, 0, b"T-72B") == ["비생식 복제", "전쟁", "보병", "T-72B"]
    assert names(60000, 6, 21, "Škoda Mörser €".encode("cp1252")) == ["#60000", "사회", "시설", "Škoda Mörser €"]
    assert names(1, 0, 22, b"\x81")[1:] == ["0", "22", "?"]               # 표에 없는 번호는 번호로, 정해지지 않은 바이트는 ?
    assert names(1, 1, 6, b"")[2] == "수송" and names(1, 1, 14, b"")[2] == "공중 수송" and names(1, 1, 20, b"")[2] == "해상 수송"


LIST_DONE = [[1, 2, 3, 4, 6, 7], [10, 13, 14], [1, 2], [11, 13]]      # 기술 3(+ 선행 2) · 7 을 완료로


def test_the_research_list_completes_and_revokes_what_is_picked(dll, cfg, tmp_path):
    """연구 탭의 목록: 처음에는 자국 미보유의 기술이 보인다. 고른 것을 완료로 바꾸면 선행도 딸려 오고 목록이 바로 따라온다.
    "고른 것"은 거르개로 가려져도 남고, 목록(기술 ↔ 부대 설계)을 바꾸면 풀린다. "보이는 것 전부 미완료"는 한 번 더 눌러야 실행된다.
    내장 치트는 거치지 않는다. 다른 나라의 보유는 그대로다."""
    got = json.loads(_probe(cfg, tmp_path, "research_list"))
    assert got["rows"] == RESEARCH_BUTTONS                                  # 위의 단추 셋은 그대로다
    assert got["picked"] == "고른 나라: 없음 — 외교·영토 탭에서 고릅니다"
    assert got["first"] == {"2": "0|개량 폐기물 소각|전쟁|20|연구 중|1", "3": "0|물 절약|전쟁|30|미보유|0", "7": "0|미사일 발사 사일로|전쟁|70|미보유|1"}
    assert got["count"] == "보이는 것 3개 · 고른 것 0개" and got["count_chosen"] == "보이는 것 3개 · 고른 것 2개"
    assert got["after_done"] == LIST_DONE and got["wrote_done"] == "기술 3개(선행 1개 포함)를 완료로 — 고른 것"
    assert got["left"] == {} and got["count_left"] == "보이는 것 0개 · 고른 것 2개(보이지 않는 것 2개)"
    assert list(got["mine"]) == ["1", "2", "3", "4", "6", "7"] and got["mine"]["3"] == "1|물 절약|전쟁|30|보유|0"
    assert got["designs"] == {"10": "0|Unit|보병|1950|보유|0", "13": "0|Unit|보병|1950|보유|1", "14": "0|Unit|보병|1950|보유|0"}
    assert got["count_designs"] == "보이는 것 3개 · 고른 것 0개"
    assert got["asking"] == "보이는 것 전부 미완료 — 한 번 더 누르면 실행합니다" and got["held_asking"] == LIST_DONE   # 첫 누름은 쓰지 않는다
    assert got["wrote_undo"] == "부대 설계 3개를 미완료로 — 보이는 것" and got["designs_after"] == {}
    assert got["held"] == [[1, 2, 3, 4, 6, 7], [], [1, 2], [11, 13]]        # 폴란드의 보유는 그대로다
    assert got["days"] == [100.0] and got["recomputed"] == [176]            # 다시 셈은 기술을 바꿨을 때만, 플레이어로만
    assert got["lines"] == [] and got["text"] == "" and got["options"] == 0
