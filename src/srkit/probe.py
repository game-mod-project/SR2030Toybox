"""실험용 모드(build/probe-<이름>/) 만들기: 설치본의 파일 하나에서 값 한 곳만 바꾼 사본.

게임 파일의 사본이므로 저장소에 넣지 않는다(build/ 는 git 제외). 바이트를 그대로 다뤄 인코딩과 줄 끝을 건드리지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from .config import Config

NEAR = 4096     # --after 로 정한 기준에서 이 바이트 안에 있어야 한다 (다른 블록의 같은 값을 잘못 바꾸지 않게)


def make(cfg: Config, name: str, rel: str, old: str, new: str, *, after: str | None = None) -> Path:
    src = cfg.game_dir / rel
    if not src.is_file():
        raise RuntimeError(f"게임 폴더에 없는 파일입니다: {rel}")
    data = src.read_bytes()
    old_b, new_b = old.encode("cp1252"), new.encode("cp1252")
    if after is None:
        if data.count(old_b) != 1:
            raise RuntimeError(f"바꿀 문자열이 {data.count(old_b)}번 나옵니다(한 번이어야 합니다. --after 로 위치를 정하세요): {old!r}")
        pos = data.index(old_b)
    else:
        anchor = after.encode("cp1252")
        if data.count(anchor) != 1:
            raise RuntimeError(f"기준 문자열이 {data.count(anchor)}번 나옵니다(한 번이어야 합니다): {after!r}")
        start = data.index(anchor) + len(anchor)
        pos = data.find(old_b, start, start + NEAR)
        if pos < 0:
            raise RuntimeError(f"기준 뒤 {NEAR}바이트 안에 바꿀 문자열이 없습니다: {old!r}")
    out = cfg.build_dir / f"probe-{name}" / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data[:pos] + new_b + data[pos + len(old_b):])
    return out
