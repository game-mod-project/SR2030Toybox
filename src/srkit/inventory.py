"""게임 텍스트 데이터의 섹션·키·열 목록을 뽑는다(읽기 전용). 산출물은 build/inventory/ 의 CSV 다.

데이터 줄은 두 가지로 읽는다: 이름으로 시작하는 줄(``키 값`` · ``키: 값`` · ``키, 값, …``)과 쉼표 행.
섹션이 "키 섹션"인지 "표"인지는 데이터로 정한다 — 행의 90% 이상이 소문자로 시작하는 이름으로 시작하면 키 섹션이다
(빌드 21347933 에서 CVP · GMC · MAP · SAV · WMDATA · WMPRODDATA · UISETTINGS · AIPARAMS).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import srtext
from .korean import decode_cp1252

SCAN_DIRS = ("INI", "Maps", "Sandbox", "Scenario", "Campaign", "Tutorials", "Common")
KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::|,|\s|$)")
KEYED_SHARE = 0.9       # 행의 이만큼이 소문자 이름으로 시작하면 키 섹션으로 본다
EXAMPLE_MAX = 60
STRING_RE = re.compile(rb"[\x20-\x7e]{3,}")
WORD_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{2,31}:?\Z")
RUN_GAP = 16            # 실행 파일에서 문자열 사이가 이보다 벌어지면 다른 표로 본다


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


@dataclass
class Table:
    """한 파일 안의 한 섹션을 표로 읽은 결과."""
    names: list[str] = field(default_factory=list)
    filled: Counter = field(default_factory=Counter)        # 열 번호 → 값이 있는 행 수
    example: dict[int, str] = field(default_factory=dict)
    width: int = 0


@dataclass
class Section:
    blocks: Counter = field(default_factory=Counter)        # 파일 → 블록 수
    rows: Counter = field(default_factory=Counter)          # 파일 → 행 수
    lower_first: int = 0                                    # 소문자 이름으로 시작하는 행 수
    keys: Counter = field(default_factory=Counter)          # 키 → 등장 횟수 (처음 나온 순서)
    key_files: dict[str, set[str]] = field(default_factory=dict)
    key_example: dict[str, str] = field(default_factory=dict)
    tables: dict[str, Table] = field(default_factory=dict)  # 파일 → 표

    @property
    def keyed(self) -> bool:
        total = sum(self.rows.values())
        return total > 0 and self.lower_first / total >= KEYED_SHARE


@dataclass
class Inventory:
    sections: dict[str, Section] = field(default_factory=dict)
    skipped: list[tuple[str, str]] = field(default_factory=list)   # (파일, 이유)


@dataclass(frozen=True)
class Candidate:
    string: str
    near: str        # 같은 표에서 가장 가까운 알려진 이름
    distance: int    # 그 이름과 몇 칸 떨어져 있는가
    colon: bool      # 실행 파일에 "이름:" 꼴로 들어 있는가 (GMC 형식 키의 표지)


def scan_text(rel: str, text: str, sections: dict[str, Section]) -> None:
    current: Section | None = None
    table = Table()
    comments: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//"):
            comments.append(line)
            continue
        name = srtext.section_name(line)
        if name is not None:
            current = None if name == "END" else sections.setdefault(name, Section())
            if current is not None:
                current.blocks[rel] += 1
                table = current.tables.setdefault(rel, Table())
                if not table.names:
                    table.names = header_names(comments)
            comments = []
            continue
        comments = []
        if current is None or line.startswith("#"):     # 섹션 밖의 줄, #include · #ifset 지시문
            continue
        current.rows[rel] += 1
        kv = key_value(line)
        if kv:
            key, value = kv
            current.lower_first += key[0].islower()
            current.keys[key] += 1
            current.key_files.setdefault(key, set()).add(rel)
            if value:
                current.key_example.setdefault(key, value[:EXAMPLE_MAX])
        fields = fields_of(line)
        table.width = max(table.width, len(fields))
        for i, value in enumerate(fields):
            if value:
                table.filled[i] += 1
                table.example.setdefault(i, value[:EXAMPLE_MAX])


def is_binary(data: bytes) -> bool:
    """끝에 붙은 NUL(*.OOF 에 하나 있다)은 떼고, 그 밖에 NUL 이 있으면 이진 파일로 본다."""
    return b"\0" in data.rstrip(b"\0")


def scan(game_dir: Path) -> Inventory:
    inv = Inventory()
    for top in SCAN_DIRS:
        for path in sorted((game_dir / top).rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(game_dir).as_posix()
            try:
                data = path.read_bytes()
            except OSError as e:
                inv.skipped.append((rel, f"읽지 못함: {e.strerror}"))
                continue
            if is_binary(data):
                inv.skipped.append((rel, "이진"))
                continue
            scan_text(rel, decode_cp1252(data.rstrip(b"\0")), inv.sections)
    return inv


def exe_candidates(data: bytes, known: set[str]) -> list[Candidate]:
    """실행 파일의 이름 표에서, 알려진 이름과 같은 표에 있으면서 어느 파일에도 쓰이지 않은 이름을 찾는다.

    컴파일러는 한 소스의 문자열 상수를 이어서 놓는다. 이름 꼴 문자열이 붙어 있는 구간을 표 하나로 보고,
    알려진 이름(파일에 쓰인 키·섹션)이 둘 이상 든 표의 나머지를 후보로 낸다. 같은 표에 GUI·글꼴 키도
    섞여 있으므로 후보는 추정일 뿐이다 — distance 가 작고 colon 이 맞는 것부터 본다.
    """
    runs: list[list[str]] = []
    run: list[str] = []
    prev_end = -RUN_GAP - 1
    for m in STRING_RE.finditer(data):
        if WORD_RE.match(m.group()):
            if run and m.start() - prev_end > RUN_GAP:
                runs.append(run)
                run = []
            run.append(m.group().decode("ascii"))
        elif run:
            runs.append(run)
            run = []
        prev_end = m.end()
    if run:
        runs.append(run)
    found: dict[str, Candidate] = {}
    for run in runs:
        names = [s.rstrip(":") for s in run]
        hits = [i for i, name in enumerate(names) if name in known]
        if len(hits) < 2:
            continue
        for i, name in enumerate(names):
            if name in known or name in found:
                continue
            j = min(hits, key=lambda h: abs(h - i))
            found[name] = Candidate(name, names[j], abs(j - i), run[i].endswith(":"))
    return list(found.values())
