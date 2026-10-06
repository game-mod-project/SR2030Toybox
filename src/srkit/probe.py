"""실험용 모드(build/probe-<이름>/) 만들기: 설치본의 파일 하나에서 값 한 곳만 바꾼 사본.

게임 파일의 사본이므로 저장소에 넣지 않는다(build/ 는 git 제외). 바이트를 그대로 다뤄 인코딩과 줄 끝을 건드리지 않는다.
쓰는 곳은 build/probe-<이름>/ 아래뿐이다 — 이름과 경로가 그 밖을 가리키면 읽기 전에 거부한다.
"""
from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

from .config import Config

NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
NEAR = 4096     # --after 로 정한 기준에서 이 바이트 안에 있어야 한다
BLOCK = b"\n&&"  # 다음 섹션의 머리. 기준 뒤의 탐색은 여기서 멈춘다 (다음 블록의 같은 값을 잘못 바꾸지 않게)


def make(cfg: Config, name: str, rel: str, old: str, new: str, *, after: str | None = None) -> Path:
    if not NAME_RE.fullmatch(name):
        raise RuntimeError(f"시험 이름은 영문자·숫자·-·_ 만 씁니다(폴더 이름 하나가 된다): {name!r}")
    path = PureWindowsPath(rel)     # 게임은 Windows 전용이다. / 와 \ 를 모두 구분자로 본다
    if path.anchor or ".." in path.parts or not path.parts:
        # 절대 경로를 받으면 읽는 곳과 쓰는 곳이 같은 파일이 되어 게임 파일을 덮어쓴다
        raise RuntimeError(f"게임 폴더 기준 상대 경로여야 합니다(예: Maps/W2030.CVP): {rel}")
    src = cfg.game_dir / path
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
        block_end = data.find(BLOCK, start)
        end = min(start + NEAR, len(data) if block_end < 0 else block_end)
        pos = data.find(old_b, start, end)
        if pos < 0:
            raise RuntimeError(f"기준 뒤 같은 블록({end - start}바이트) 안에 바꿀 문자열이 없습니다: {old!r}")
    out = cfg.build_dir / f"probe-{name}" / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data[:pos] + new_b + data[pos + len(old_b):])
    return out
