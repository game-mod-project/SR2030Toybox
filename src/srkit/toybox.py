"""ToyBox DLL(native/srtoybox) 빌드. 게임 안 모드 설정 창이다 — 한글화 훅(WTSAPI32.dll)이 게임 폴더에서 불러온다."""
from __future__ import annotations

import csv
import ctypes
import re
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import hook
from .config import Config

DLL_NAME = "srtoybox.dll"
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "sigs.cpp", "locate.cpp", "values.cpp", "game.cpp", "keeper.cpp", "regions.cpp",
           "overlay.cpp"]
LIBS = ["kernel32.lib", "user32.lib", "gdi32.lib", "imm32.lib", "dwmapi.lib", "d3d11.lib", "dxgi.lib", "d3dcompiler.lib"]
FLAGS = "/nologo /c /utf-8 /std:c++17 /O2 /MT /EHsc /DNDEBUG /DNOMINMAX"   # NDEBUG: 게임 안에서 assert 로 죽지 않게. NOMINMAX: windows.h 의 min · max 매크로를 끈다
IMGUI_DIR = "native/third_party/imgui"
IMGUI_SOURCES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp",
                 "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.cpp"]
IMGUI_DEFINES = "/DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD"    # 게임패드는 쓰지 않는다(XInput 을 불러오지 않게)
EXE_NAME = "SupremeRuler2030.exe"
# REGIONTEXT|<지역 번호>|0 행이 지역의 이름이다. 뒤의 표(게임의 표에 없어 덧붙인 지역)가 앞의 것을 덮는다
REGION_TABLES = ["mods/korean/translation/localtext-regions.csv", "mods/korean/translation/localtext-regions.extra.csv"]
# native/srtoybox/locate.h 의 GameAddresses 와 같은 순서다
ADDRESS_FIELDS = ["handler", "context", "multiplayer", "options", "program_state", "mode_state", "player_index",
                  "player_pointer", "region_table", "region_count"]
ADDRESS_NAMES = {"handler": "명령 처리 함수", "context": "그 함수의 첫 인자(전역 객체)", "multiplayer": "멀티플레이 표시(byte)",
                 "options": "옵션 묶음(dword, 0x40 = 치트 허용)", "program_state": "프로그램 상태(dword)",
                 "mode_state": "모드 상태(dword)", "player_index": "플레이어 지역의 인덱스(dword)",
                 "player_pointer": "플레이어 지역 객체의 포인터(qword)", "region_table": "지역 포인터 표(qword × 1024)",
                 "region_count": "지역 수(dword)"}
# 새 찾기(서명)가 채우는 일곱 — native/srtoybox/locate.cpp 의 표 STATE 와 같은 순서다
STATE_FIELDS = ["multiplayer", "program_state", "mode_state", "player_index", "player_pointer", "region_table", "region_count"]
# 옛 찾기(치트 닻)가 채우는 셋 — 아직 내장 치트로 도는 기능이 쓴다(전환 기간에만)
LEGACY_FIELDS = ["handler", "context", "options"]
# 새 찾기(서명)가 채우는 값 묶음 — native/srtoybox/locate.h 의 ValueLayout 과 같은 순서다
VALUE_FIELDS = ["world_pointer", "treasury", "stock_first", "stock_step", "used_first", "used_step"]
VALUE_NAMES = {"world_pointer": "세계 자료 객체의 포인터(qword. 이것만 RVA 다)", "treasury": "국고 칸 — 지역 객체 안의 자리(double, 달러)",
               "stock_first": "재고의 첫 칸 — 지역 객체 안의 자리(float)", "stock_step": "재고 칸의 간격",
               "used_first": "\"쓰는 물자\" 표의 첫 칸 — 세계 자료 객체 안의 자리(float. 0 보다 크면 쓴다)", "used_step": "그 표의 간격"}
STOCK_SLOTS = 12        # 재고의 칸 수(native/srtoybox/locate.h 의 STOCK_SLOTS)


@dataclass
class SigRow:
    """서명 하나의 결과."""
    name: str       # 찾을 것(GameAddresses 의 필드 이름)
    text: str       # 서명 글
    count: int      # 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    at: int         # 처음 맞은 자리
    value: int      # 거기서 읽어 낸 주소나 상수(둘을 읽는 서명이면 간격)
    value2: int = 0  # 둘째로 읽어 낸 상수(재고 · "쓰는 물자" 표의 첫 칸). 없으면 0


@dataclass
class Located:
    """설치된 게임의 실행 파일에서 찾은 것."""
    state: dict[str, int] | None     # 새 찾기(서명): 상태 전역 일곱. 못 찾았으면 None
    state_why: str
    rows: list[SigRow]               # 서명마다의 결과
    ms: float                        # 새 찾기에 걸린 시간
    values: dict[str, int] | None    # 새 찾기(서명): 값 묶음. 못 찾았으면 None
    values_why: str
    value_rows: list[SigRow]
    legacy: dict[str, int] | None    # 옛 찾기(치트 닻): 명령 처리 함수 · this · 옵션 묶음. 못 찾았으면 None
    legacy_why: str


class GameAddresses(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ADDRESS_FIELDS]


class ValueLayout(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in VALUE_FIELDS]


def output(cfg: Config) -> Path:
    """모드 폴더(build/toybox, 게임 루트 구조) 안의 DLL. 이 폴더에는 DLL 만 둔다 — deploy 가 통째로 복사한다."""
    return cfg.build_dir / "toybox" / DLL_NAME


def status(cfg: Config) -> str:
    out = output(cfg)
    return f"{out} (빌드됨)" if out.is_file() else "빌드 안 됨 — srkit toybox-build"


def _quoted(paths) -> str:
    return " ".join(f'"{p}"' for p in paths)


def region_rows(cfg: Config) -> list[tuple[int, str, str]]:
    """번역 테이블에서 (지역 번호, 한글 이름, 영문 이름)을 번호순으로. 번역이 빈 행은 영문 이름을 쓴다."""
    rows: dict[int, tuple[str, str]] = {}
    for table in REGION_TABLES:
        with (cfg.root / table).open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                m = re.fullmatch(r"REGIONTEXT\|(\d+)\|0", row["key"])
                en = row["en"].strip()
                if m and en:
                    rows[int(m[1])] = (row["ko"].strip() or en, en)
    return [(number, *rows[number]) for number in sorted(rows)]


def c_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def regions_inc(rows: list[tuple[int, str, str]]) -> str:
    """native/srtoybox/regions.cpp 가 끼워 넣는 초기화 목록(한 줄에 지역 하나)."""
    return "".join(f"{{{number}, {c_string(ko)}, {c_string(en)}}},\n" for number, ko, en in rows)


def build(cfg: Config) -> Path:
    src = cfg.root / "native" / "srtoybox"
    out, obj = output(cfg), cfg.build_dir / "toybox-obj"      # 중간 산출물(.obj .lib .exp)은 모드 폴더 밖에 둔다
    out.parent.mkdir(parents=True, exist_ok=True)
    obj.mkdir(parents=True, exist_ok=True)
    imgui = cfg.root / IMGUI_DIR
    ours = [src / name for name in SOURCES]
    theirs = [imgui / name for name in IMGUI_SOURCES]
    objs = [obj / (p.stem + ".obj") for p in ours + theirs]
    (obj / "regions_table.inc").write_text(regions_inc(region_rows(cfg)), encoding="utf-8", newline="\n")
    include = f'/I"{imgui}" /I"{imgui / "backends"}" /I"{obj}" {IMGUI_DEFINES}'
    script = obj / "build.cmd"
    script.write_text(
        "@echo off\r\n"
        f'call "{hook.vcvars()}" >nul || exit /b 1\r\n'
        f'cl {FLAGS} /W3 {include} /Fo"{obj}\\\\" {_quoted(theirs)} || exit /b 1\r\n'          # 외부 소스: 경고를 오류로 치지 않는다
        f'cl {FLAGS} /W4 /WX {include} /Fo"{obj}\\\\" {_quoted(ours)} || exit /b 1\r\n'
        f'link /NOLOGO /DLL /OUT:"{out}" /IMPLIB:"{obj / "srtoybox.lib"}" /MAP:"{obj / "srtoybox.map"}" '   # map: 충돌 주소 → 함수
        f'{_quoted(objs)} {" ".join(LIBS)} || exit /b 1\r\n',
        encoding="mbcs")
    result = subprocess.run(["cmd", "/d", "/c", str(script)], cwd=obj, capture_output=True)
    if result.returncode != 0 or not out.is_file():
        raise RuntimeError(f"ToyBox DLL 빌드 실패:\n{hook.output_text(result.stdout)}\n{hook.output_text(result.stderr)}")
    return out


def library(cfg: Config) -> ctypes.CDLL:
    """빌드한 DLL 을 불러 주소 찾기 함수의 인자 형을 적어 둔다(srkit locate 와 테스트가 쓴다)."""
    lib = ctypes.CDLL(str(output(cfg)))
    lib.srtoybox_locate_legacy.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p,
                                           ctypes.c_int]
    lib.srtoybox_locate_state.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p,
                                          ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_locate_values.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(ValueLayout), ctypes.c_char_p,
                                           ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.srtoybox_function_root.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_uint]
    lib.srtoybox_function_root.restype = ctypes.c_uint
    return lib


def image_of(exe: bytes) -> bytes:
    """실행 파일을 RVA 대로 펼친다 — 게임이 메모리에 올린 모양이다. 파일에 없는(초기화되지 않은) 자리는 0."""
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    sections, optional = struct.unpack_from("<H", exe, pe + 6)[0], struct.unpack_from("<H", exe, pe + 20)[0]
    size, headers = struct.unpack_from("<II", exe, pe + 24 + 56)
    image = bytearray(size)
    image[:headers] = exe[:headers]
    for i in range(sections):
        _name, virtual_size, rva, raw_size, raw = struct.unpack_from("<8sIIII", exe, pe + 24 + optional + 40 * i)
        n = min(virtual_size, raw_size)
        image[rva:rva + n] = exe[raw:raw + n]
    return bytes(image)


def _sig_rows(text: bytes) -> list[SigRow]:
    """DLL 이 내는 서명마다의 결과(한 줄에 "이름\\t서명\\t횟수\\t자리\\t값\\t둘째 값", 뒤의 넷은 16진수)."""
    return [SigRow(name, sig, int(count, 16), int(at, 16), int(value, 16), int(value2, 16))
            for name, sig, count, at, value, value2 in (line.split("\t") for line in text.decode("utf-8").splitlines())]


def state_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(상태 묶음)를 그 이미지에 돌린다: (이름 → RVA 또는 None, 까닭, 서명마다의 결과)."""
    found, error, rows = GameAddresses(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_state(image, len(image), ctypes.byref(found), error, len(error), rows, len(rows)) == 0
    return ({name: getattr(found, name) for name in STATE_FIELDS} if ok else None), error.value.decode("utf-8"), _sig_rows(rows.value)


def values_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str, list[SigRow]]:
    """새 찾기(값 묶음)를 그 이미지에 돌린다: (이름 → 값 또는 None, 까닭, 서명마다의 결과)."""
    found, error, rows = ValueLayout(), ctypes.create_string_buffer(256), ctypes.create_string_buffer(8192)
    ok = lib.srtoybox_locate_values(image, len(image), ctypes.byref(found), error, len(error), rows, len(rows)) == 0
    return ({name: getattr(found, name) for name in VALUE_FIELDS} if ok else None), error.value.decode("utf-8"), _sig_rows(rows.value)


def legacy_of(lib: ctypes.CDLL, image: bytes) -> tuple[dict[str, int] | None, str]:
    """옛 찾기(치트 닻)를 그 이미지에 돌린다: (이름 → RVA, "") 또는 (None, 까닭)."""
    found, error = GameAddresses(), ctypes.create_string_buffer(256)
    if lib.srtoybox_locate_legacy(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in LEGACY_FIELDS}, ""


def locate(cfg: Config) -> Located:
    """설치된 게임의 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 게임 안에서 도는 것과 같은 코드(DLL)를 쓴다. 파일을 읽기만 한다.

    DLL 이 빌드되어 있어야 한다(srkit toybox-build).
    """
    lib = library(cfg)
    image = image_of((cfg.game_dir / EXE_NAME).read_bytes())
    started = time.perf_counter()
    state, state_why, rows = state_of(lib, image)
    ms = (time.perf_counter() - started) * 1000
    values, values_why, value_rows = values_of(lib, image)
    legacy, legacy_why = legacy_of(lib, image)
    return Located(state, state_why, rows, ms, values, values_why, value_rows, legacy, legacy_why)
