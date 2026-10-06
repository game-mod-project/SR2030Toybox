"""ToyBox DLL(native/srtoybox) 빌드. 게임 안 모드 설정 창이다 — 한글화 훅(WTSAPI32.dll)이 게임 폴더에서 불러온다."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import hook
from .config import Config

DLL_NAME = "srtoybox.dll"
SOURCES = ["features.cpp", "command.cpp", "runner.cpp", "settings.cpp", "exports.cpp",
           "log.cpp", "runner_win.cpp", "ui.cpp", "input.cpp", "prologue.cpp", "overlay.cpp"]
LIBS = ["kernel32.lib", "user32.lib", "gdi32.lib", "imm32.lib", "dwmapi.lib", "d3d11.lib", "dxgi.lib", "d3dcompiler.lib"]
FLAGS = "/nologo /c /utf-8 /std:c++17 /O2 /MT /EHsc /DNDEBUG /DNOMINMAX"   # NDEBUG: 게임 안에서 assert 로 죽지 않게. NOMINMAX: windows.h 의 min · max 매크로를 끈다
IMGUI_DIR = "native/third_party/imgui"
IMGUI_SOURCES = ["imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp", "imgui_widgets.cpp",
                 "backends/imgui_impl_win32.cpp", "backends/imgui_impl_dx11.cpp"]
IMGUI_DEFINES = "/DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD"    # 게임패드는 쓰지 않는다(XInput 을 불러오지 않게)


def output(cfg: Config) -> Path:
    """모드 폴더(build/toybox, 게임 루트 구조) 안의 DLL. 이 폴더에는 DLL 만 둔다 — deploy 가 통째로 복사한다."""
    return cfg.build_dir / "toybox" / DLL_NAME


def status(cfg: Config) -> str:
    out = output(cfg)
    return f"{out} (빌드됨)" if out.is_file() else "빌드 안 됨 — srkit toybox-build"


def _quoted(paths) -> str:
    return " ".join(f'"{p}"' for p in paths)


def build(cfg: Config) -> Path:
    src = cfg.root / "native" / "srtoybox"
    out, obj = output(cfg), cfg.build_dir / "toybox-obj"      # 중간 산출물(.obj .lib .exp)은 모드 폴더 밖에 둔다
    out.parent.mkdir(parents=True, exist_ok=True)
    obj.mkdir(parents=True, exist_ok=True)
    imgui = cfg.root / IMGUI_DIR
    ours = [src / name for name in SOURCES]
    theirs = [imgui / name for name in IMGUI_SOURCES]
    objs = [obj / (p.stem + ".obj") for p in ours + theirs]
    include = f'/I"{imgui}" /I"{imgui / "backends"}" {IMGUI_DEFINES}'
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
