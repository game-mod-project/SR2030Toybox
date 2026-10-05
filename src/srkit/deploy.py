"""빌드한 모드(build/<모드>/, 게임 루트 구조)를 게임 폴더에 설치·제거한다.

덮어쓰는 원본은 build/.deploy/<모드>/backup 에 보관하고, 설치 내역(manifest.json)으로 깨끗이 되돌린다.
apply=False 면 무엇을 할지만 알려 준다.
"""
from __future__ import annotations

import filecmp
import json
import shutil
from pathlib import Path

from .config import Config

GAME_EXE = "SupremeRuler2030.exe"


def _state_dir(cfg: Config, mod: str) -> Path:
    return cfg.build_dir / ".deploy" / mod


def _check_game(cfg: Config) -> None:
    if not (cfg.game_dir / GAME_EXE).is_file():
        raise RuntimeError(f"게임 폴더가 아닙니다({GAME_EXE} 없음): {cfg.game_dir}")


def deploy(cfg: Config, mod: str, *, apply: bool = False) -> list[str]:
    _check_game(cfg)
    src = cfg.build_dir / mod
    if not src.is_dir():
        raise RuntimeError(f"빌드 산출물이 없습니다: {src}")
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
