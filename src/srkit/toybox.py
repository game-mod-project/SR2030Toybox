"""ToyBox DLL(native/srtoybox) 빌드. 게임 안 모드 설정 창이다 — 한글화 훅(WTSAPI32.dll)이 게임 폴더에서 불러온다."""
from __future__ import annotations

import csv
import ctypes
import re
import struct
import subprocess
from pathlib import Path

from . import hook
from .config import Config

DLL_NAME = "srtoybox.dll"
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "locate.cpp", "game.cpp", "regions.cpp", "overlay.cpp"]
LIBS = ["kernel32.lib", "user32.lib", "gdi32.lib", "imm32.lib", "dwmapi.lib", "d3d11.lib", "dxgi.lib", "d3dcompiler.lib"]
FLAGS = "/nologo /c /utf-8 /std:c++17 /O2 /MT /EHsc /DNDEBUG /DNOMINMAX"   # NDEBUG: 게임 안에서 assert 로 죽지 않게. NOMINMAX: windows.h 의 min · max 매크로를 끈다
IMGUI_DIR = "native/third_party/imgui"
IMGUI_SOURCES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp",
                 "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.cpp"]
IMGUI_DEFINES = "/DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD"    # 게임패드는 쓰지 않는다(XInput 을 불러오지 않게)
EXE_NAME = "SupremeRuler2030.exe"
REGION_TABLE = "mods/korean/translation/localtext-regions.csv"   # REGIONTEXT|<지역 번호>|0 행이 지역의 이름이다
# native/srtoybox/locate.h 의 GameAddresses 와 같은 순서다
ADDRESS_FIELDS = ["handler", "context", "multiplayer", "options", "program_state", "mode_state", "player_index",
                  "player_pointer", "region_table", "region_count"]
ADDRESS_NAMES = {"handler": "명령 처리 함수", "context": "그 함수의 첫 인자(전역 객체)", "multiplayer": "멀티플레이 표시(byte)",
                 "options": "옵션 묶음(dword, 0x40 = 치트 허용)", "program_state": "프로그램 상태(dword)",
                 "mode_state": "모드 상태(dword)", "player_index": "플레이어 지역의 인덱스(dword)",
                 "player_pointer": "플레이어 지역 객체의 포인터(qword)", "region_table": "지역 포인터 표(qword × 1024)",
                 "region_count": "지역 수(dword)"}


class GameAddresses(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ADDRESS_FIELDS]


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
    with (cfg.root / REGION_TABLE).open(encoding="utf-8-sig", newline="") as f:
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
    lib.srtoybox_locate.argtypes = [ctypes.c_char_p, ctypes.c_ulonglong, ctypes.POINTER(GameAddresses), ctypes.c_char_p, ctypes.c_int]
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


def locate(cfg: Config) -> tuple[dict[str, int] | None, str]:
    """설치된 게임의 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다: (이름 → RVA, "") 또는 (None, 까닭).

    게임 안에서 ToyBox 가 도는 것과 같은 코드(DLL 의 locate)를 쓴다. 파일을 읽기만 한다.
    """
    if not output(cfg).is_file():
        return None, "ToyBox DLL 이 없습니다 — srkit toybox-build"
    image = image_of((cfg.game_dir / EXE_NAME).read_bytes())
    found, error = GameAddresses(), ctypes.create_string_buffer(256)
    if library(cfg).srtoybox_locate(image, len(image), ctypes.byref(found), error, len(error)) != 0:
        return None, error.value.decode("utf-8")
    return {name: getattr(found, name) for name in ADDRESS_FIELDS}, ""
