"""게임 텍스트 데이터의 섹션·키·열 목록을 뽑는다(읽기 전용). 산출물은 build/inventory/ 의 CSV 다.

데이터 줄은 두 가지로 읽는다: 이름으로 시작하는 줄(``키 값`` · ``키: 값`` · ``키, 값, …``)과 쉼표 행.
섹션이 "키 섹션"인지 "표"인지는 데이터로 정한다 — 행의 90% 이상이 소문자로 시작하는 이름으로 시작하면 키 섹션이다
(빌드 21347933 에서 CVP · GMC · MAP · SAV · WMDATA · WMPRODDATA · UISETTINGS · AIPARAMS).
"""
from __future__ import annotations

import re

KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::|,|\s|$)")


def strip_comment(line: str) -> str:
    """큰따옴표 밖의 ``//`` 부터 줄 끝까지를 버린다."""
    parts = line.split('"')
    for i in range(0, len(parts), 2):
        cut = parts[i].find("//")
        if cut >= 0:
            return '"'.join(parts[:i] + [parts[i][:cut]])
    return line


def fields_of(line: str) -> list[str]:
    """쉼표로 나눈 필드(앞뒤 공백 제거). 큰따옴표 안의 쉼표는 나누지 않고, 따옴표 밖의 주석은 버린다."""
    out, cur = [], ""
    for i, part in enumerate(strip_comment(line).split('"')):
        if i % 2:
            cur += part
            continue
        pieces = part.split(",")
        cur += pieces[0]
        for piece in pieces[1:]:
            out.append(cur.strip())
            cur = piece
    out.append(cur.strip())
    return out


def key_value(line: str) -> tuple[str, str] | None:
    """이름으로 시작하는 줄이면 (키, 값)을 돌려준다. 구분은 공백 · ``:`` · ``,`` 어느 것이든 된다."""
    body = strip_comment(line).strip()
    m = KEY_RE.match(body)
    if not m:
        return None
    return m.group(1), body[m.end(1):].lstrip(":, \t").strip()


def header_names(comments: list[str]) -> list[str]:
    """섹션 머리 바로 위 주석들 가운데 열 이름 줄을 고른다: 쉼표로 나눈 이름이 가장 많은 줄(둘 이상일 때만)."""
    best: list[str] = []
    for comment in comments:
        names = [n.strip().lstrip("/").strip() for n in comment.lstrip("/").split(",")]
        if sum(map(bool, names)) > sum(map(bool, best)):
            best = names
    return best if sum(map(bool, best)) >= 2 else []
