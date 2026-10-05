"""디코딩 훅 DLL(native/srhook) 빌드. 게임이 임포트하는 WTSAPI32.dll 의 프록시로 만든다."""
from __future__ import annotations

import os
import struct
import subprocess
from pathlib import Path

from .config import Config

PROXY_NAME = "WTSAPI32.dll"
VSWHERE = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"


def system_dll() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wtsapi32.dll"


def exports(dll: Path) -> list[tuple[int, str]]:
    """PE 내보내기 테이블에서 (서수, 이름) 목록을 읽는다."""
    data = dll.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec, optsize = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    ddir = opt + (112 if struct.unpack_from("<H", data, opt)[0] == 0x20B else 96)
    secs = [struct.unpack_from("<IIII", data, opt + optsize + i * 40 + 8) for i in range(nsec)]

    def off(rva: int) -> int:
        for vsize, va, rsize, raw in secs:
            if va <= rva < va + max(vsize, rsize):
                return rva - va + raw
        raise ValueError(f"RVA {rva:#x} 가 섹션 밖입니다")

    exp = off(struct.unpack_from("<I", data, ddir)[0])
    base, _nfunc, nnames, _funcs, names, ordinals = struct.unpack_from("<6I", data, exp + 16)
    out = []
    for i in range(nnames):
        name_off = off(struct.unpack_from("<I", data, off(names) + i * 4)[0])
        name = data[name_off:data.index(b"\0", name_off)].decode("ascii")
        out.append((base + struct.unpack_from("<H", data, off(ordinals) + i * 2)[0], name))
    return out


def output(cfg: Config) -> Path:
    return cfg.build_dir / "srhook" / PROXY_NAME


def status(cfg: Config) -> str:
    out = output(cfg)
    return f"{out} (빌드됨)" if out.is_file() else "빌드 안 됨 — srkit hook-build"


def _vcvars() -> Path:
    if not VSWHERE.is_file():
        raise RuntimeError("Visual Studio(Build Tools) 를 찾을 수 없습니다: vswhere.exe 없음")
    found = subprocess.run(
        [str(VSWHERE), "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-property", "installationPath"], capture_output=True, text=True, check=True).stdout.strip()
    vcvars = Path(found) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if not found or not vcvars.is_file():
        raise RuntimeError("MSVC x64 도구(C++ 빌드 도구)가 설치되어 있지 않습니다")
    return vcvars


def build(cfg: Config) -> Path:
    src = cfg.root / "native" / "srhook"
    out = output(cfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 원래 WTSAPI32 의 모든 함수를 시스템 DLL 로 전달(forward)한다
    target = str(system_dll().with_suffix("")).replace("\\", "\\\\")
    forwards = out.parent / "exports.c"
    forwards.write_text("".join(f'#pragma comment(linker, "/EXPORT:{name}=\\"{target}.{name}\\",@{ordinal}")\n'
                                for ordinal, name in exports(system_dll()))
                        + "typedef int srhook_forwards_only; /* 빈 번역 단위 경고 방지 */\n", encoding="utf-8")
    script = out.parent / "build.cmd"
    script.write_text(
        "@echo off\r\n"
        f'call "{_vcvars()}" >nul || exit /b 1\r\n'
        f'cl /nologo /utf-8 /O2 /W4 /WX /MT /LD "{src / "srhook.c"}" "{src / "srdecode.c"}" "{forwards}" '
        f'/Fe:"{out}" /link /NOLOGO kernel32.lib advapi32.lib\r\n',
        encoding="mbcs")
    result = subprocess.run(["cmd", "/d", "/c", str(script)], cwd=out.parent, capture_output=True)
    if result.returncode != 0 or not out.is_file():
        raise RuntimeError(f"훅 DLL 빌드 실패:\n{_text(result.stdout)}\n{_text(result.stderr)}")
    return out


def _text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("mbcs", errors="replace")
