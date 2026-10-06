"""빌드한 모드(build/<모드>/, 게임 루트 구조)를 게임 폴더에 설치·제거한다.

덮어쓰는 원본은 build/.deploy/<모드>/backup 에 보관하고, 설치 내역(manifest.json)으로 깨끗이 되돌린다.
apply=False 면 무엇을 할지만 알려 준다.
"""
from __future__ import annotations

import ctypes
import filecmp
import json
import shutil
import subprocess
from pathlib import Path

from .config import Config

GAME_EXE = "SupremeRuler2030.exe"


def _state_dir(cfg: Config, mod: str) -> Path:
    return cfg.build_dir / ".deploy" / mod


def _check_game(cfg: Config) -> None:
    if not (cfg.game_dir / GAME_EXE).is_file():
        raise RuntimeError(f"게임 폴더가 아닙니다({GAME_EXE} 없음): {cfg.game_dir}")


def game_running(cfg: Config) -> bool:
    """이 게임 폴더의 게임이 실행 중인가. 실행 파일 경로를 알 수 없는 게임 프로세스는 실행 중으로 친다."""
    exe = (cfg.game_dir / GAME_EXE).resolve()
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p,
                                                    ctypes.POINTER(ctypes.c_uint)]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    for line in out.splitlines():
        if not line.startswith(f'"{GAME_EXE}"'):
            continue
        handle = kernel32.OpenProcess(0x1000, False, int(line.split('","')[1]))   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return True
        buf, size = ctypes.create_unicode_buffer(1024), ctypes.c_uint(1024)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(handle)
        if not ok or Path(buf.value).resolve() == exe:
            return True
    return False


def _check_not_running(cfg: Config) -> None:
    # 텍스트 파일과 훅 DLL 은 짝이 맞아야 한다. 실행 중에는 DLL 이 잠겨 있어 텍스트만 바뀌면 다음 화면부터 글자가 깨진다
    if game_running(cfg):
        raise RuntimeError("게임이 실행 중입니다. 게임을 끈 뒤 다시 실행하세요 (실행 중에는 파일을 바꾸지 않습니다).")


def deploy(cfg: Config, mod: str, *, apply: bool = False) -> list[str]:
    _check_game(cfg)
    src = cfg.build_dir / mod
    if not src.is_dir():
        raise RuntimeError(f"빌드 산출물이 없습니다: {src}")
    if apply:
        _check_not_running(cfg)
    state = _state_dir(cfg, mod)
    manifest_path = state / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() \
        else {"added": [], "replaced": []}
    log = []
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src).as_posix()
        dest = cfg.game_dir / rel
        if dest.is_file() and filecmp.cmp(path, dest, shallow=False):
            continue
        known = rel in manifest["added"] or rel in manifest["replaced"]
        action = "갱신" if known else ("교체(원본 백업)" if dest.exists() else "추가")
        log.append(f"{action}: {rel}")
        if not apply:
            continue
        if not known:
            if dest.exists():
                backup = state / "backup" / rel
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup)
                manifest["replaced"].append(rel)
            else:
                manifest["added"].append(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    if apply:
        state.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    log.append(f"{'설치 완료' if apply else '미리보기(--apply 로 실행)'}: {len(log)}개 파일 → {cfg.game_dir}")
    return log


def undeploy(cfg: Config, mod: str, *, apply: bool = False) -> list[str]:
    _check_game(cfg)
    state = _state_dir(cfg, mod)
    manifest_path = state / "manifest.json"
    if not manifest_path.is_file():
        return [f"설치 내역이 없습니다: {mod}"]
    if apply:
        _check_not_running(cfg)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    log = []
    for rel in manifest["replaced"]:
        log.append(f"복원: {rel}")
        if apply:
            shutil.copy2(state / "backup" / rel, cfg.game_dir / rel)
    for rel in manifest["added"]:
        dest = cfg.game_dir / rel
        log.append(f"삭제: {rel}")
        if apply and dest.is_file():
            dest.unlink()
            parent = dest.parent
            while parent != cfg.game_dir and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    if apply:
        shutil.rmtree(state)
    log.append(f"{'제거 완료' if apply else '미리보기(--apply 로 실행)'}: {len(log)}개 파일")
    return log
