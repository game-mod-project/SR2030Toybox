"""BattleGoat ``&&SECTION`` 텍스트 데이터(LocalText-*.csv, Variables.ini, LocalText-GUI.csv 등)의 무손실 파서.

줄 단위로 읽고, 각 줄을 큰따옴표 기준으로 나눠 보관한다(짝수 인덱스 = 따옴표 밖, 홀수 = 문자열 내용).
따라서 ``serialize(parse(x)) == x`` 가 항상 성립하고, 번역은 홀수 인덱스 조각만 바꿔 넣으면 된다.

예외가 하나 있다: ``&&REGIONTEXT`` 의 **따옴표 없는 이름**(DLC 의 1940 ~ 1942 시나리오 — ``101,Egypt,"\\42 …"``, ``102,Libya,\\42 ``).
그 이름도 번역 단위(순번 0)로 뽑고, 번역을 넣을 때 따옴표를 둘러 쓴다(``101,"이집트","\\42 …"``). 번역하지 않은 줄은 그대로다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 번역문에서 보존해야 하는 토큰: printf 서식, 줄 맨 앞 코드, 줄바꿈 기호.
# 코드는 백슬래시 + 3바이트다(`\42 ` 는 뒤 공백까지). 공백이 빠지면 엔진이 다음 글자의 바이트를 먹는다.
# printf 의 공백 플래그는 치지 않는다: 본문의 "50% discount", "% condition" 이 서식으로 오인된다.
TOKEN_RE = re.compile(r"%[-+0#]*\d*(?:\.\d+)?[sSdiufcxX%]|\\(?:LEF|CEN|RIG|\d{3}|\d{2} |\d {2})|¶")


BARE = -1   # Unit.part: 따옴표 없는 이름(Line.bare)

# &&REGIONTEXT 의 따옴표 없는 이름: "<번호>,<이름>," — 이름에 글자가 하나는 있어야 하고(빈 칸 · 숫자뿐인 칸이 아니다), 코드(역슬래시)가 아니다
BARE_NAME = re.compile(r"\s*\d+\s*,\s*([^,\\]*[^\W\d_][^,\\]*?)\s*,")


@dataclass
class Line:
    parts: list[str]
    section: str | None = None  # 이 줄이 속한 섹션 (헤더/주석/빈 줄은 None)
    key: str | None = None      # 행 키 (첫 필드, GUITRANS 는 영어 원문)
    bare: tuple[int, int] | None = None   # 따옴표 없는 이름이 parts[0] 안에서 차지하는 자리 [시작, 끝) — REGIONTEXT 만

    @property
    def strings(self) -> list[str]:
        return self.parts[1::2]


@dataclass
class Unit:
    """번역 단위: 한 행의 문자열 필드 하나."""
    key: str      # "섹션|행키|문자열순번" (중복 행은 #n 접미)
    text: str
    line: int     # Document.lines 인덱스
    part: int     # Line.parts 인덱스. 따옴표 없는 이름(Line.bare)이면 BARE


@dataclass
class Document:
    lines: list[Line] = field(default_factory=list)

    def serialize(self) -> str:
        return "\n".join('"'.join(ln.parts) for ln in self.lines)

    def sections(self) -> list[str]:
        seen: list[str] = []
        for ln in self.lines:
            if ln.section and ln.section not in seen:
                seen.append(ln.section)
        return seen

    def units(self, *, include_empty: bool = False) -> list[Unit]:
        out: list[Unit] = []
        counts: dict[tuple[str, str], int] = {}
        for li, ln in enumerate(self.lines):
            if ln.section is None or ln.key is None:
                continue
            n = counts.get((ln.section, ln.key), 0) + 1
            counts[(ln.section, ln.key)] = n
            row = ln.key if n == 1 else f"{ln.key}#{n}"
            first = 0
            if ln.bare is not None:                      # 따옴표 없는 이름이 순번 0 이고, 따옴표 안의 글은 1 부터다
                out.append(Unit(f"{ln.section}|{row}|0", ln.parts[0][ln.bare[0]:ln.bare[1]], li, BARE))
                first = 1
            for si, pi in enumerate(range(1, len(ln.parts), 2)):
                text = ln.parts[pi]
                if text or include_empty:
                    out.append(Unit(f"{ln.section}|{row}|{si + first}", text, li, pi))
        return out

    def apply(self, translations: dict[str, str]) -> int:
        """key → 번역문 을 적용하고 바뀐 개수를 돌려준다."""
        changed = 0
        bare: list[tuple[Unit, str]] = []
        for u in self.units():
            new = translations.get(u.key)
            if new and new != u.text:
                if '"' in new:
                    raise ValueError(f"번역문에 큰따옴표를 쓸 수 없습니다: {u.key}")
                if u.part == BARE:
                    bare.append((u, new))                # 줄의 조각 수가 바뀐다 — 그 줄의 다른 조각을 다 넣은 뒤에
                else:
                    self.lines[u.line].parts[u.part] = new
                changed += 1
        for u, new in bare:                              # 따옴표 없는 이름은 따옴표를 둘러 넣는다
            ln = self.lines[u.line]
            start, end = ln.bare
            head = ln.parts[0]
            ln.parts = [head[:start], new, head[end:]] + ln.parts[1:]
            ln.bare = None
        return changed


def section_name(head: str) -> str | None:
    """``&&이름`` 으로 시작하는 줄이면 섹션 이름(대문자)을, 아니면 None 을 돌려준다. 종료 표시는 "END" 다."""
    if not head.startswith("&&"):
        return None
    return re.split(r"[,\s]", head[2:], maxsplit=1)[0].upper()


def parse(text: str) -> Document:
    doc = Document()
    section: str | None = None
    for raw in text.split("\n"):
        parts = raw.split('"')
        head = parts[0].strip()
        line = Line(parts)
        name = section_name(head)
        if name is not None:
            section = None if name == "END" else name
        elif section and not head.startswith(("//", "#")) and len(parts) % 2 == 1:
            # '#include "파일", "경로"' 같은 지시문은 섹션 안에 있어도 번역 단위가 아니다
            name = BARE_NAME.match(parts[0]) if section == "REGIONTEXT" else None
            if len(parts) >= 3 or name is not None:
                line.section = section
                first = head.split(",", 1)[0].strip()
                line.key = first if first else parts[1]
                if name is not None:
                    line.bare = (name.start(1), name.end(1))
        doc.lines.append(line)
    return doc


def tokens(text: str) -> list[str]:
    """나타나는 순서대로. printf 인자는 위치로 대응되므로 번역문도 같은 순서여야 한다."""
    return TOKEN_RE.findall(text)
