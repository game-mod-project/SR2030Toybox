"""BattleGoat ``&&SECTION`` 텍스트 데이터(LocalText-*.csv, Variables.ini, LocalText-GUI.csv 등)의 무손실 파서.

줄 단위로 읽고, 각 줄을 큰따옴표 기준으로 나눠 보관한다(짝수 인덱스 = 따옴표 밖, 홀수 = 문자열 내용).
따라서 ``serialize(parse(x)) == x`` 가 항상 성립하고, 번역은 홀수 인덱스 조각만 바꿔 넣으면 된다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 번역문에서 보존해야 하는 토큰: printf 서식, 줄 맨 앞 코드, 줄바꿈 기호.
# 코드는 백슬래시 + 3바이트다(`\42 ` 는 뒤 공백까지). 공백이 빠지면 엔진이 다음 글자의 바이트를 먹는다.
# printf 의 공백 플래그는 치지 않는다: 본문의 "50% discount", "% condition" 이 서식으로 오인된다.
TOKEN_RE = re.compile(r"%[-+0#]*\d*(?:\.\d+)?[sSdiufcxX%]|\\(?:LEF|CEN|RIG|\d{3}|\d{2} |\d {2})|¶")


@dataclass
class Line:
    parts: list[str]
    section: str | None = None  # 이 줄이 속한 섹션 (헤더/주석/빈 줄은 None)
    key: str | None = None      # 행 키 (첫 필드, GUITRANS 는 영어 원문)

    @property
    def strings(self) -> list[str]:
        return self.parts[1::2]


@dataclass
class Unit:
    """번역 단위: 한 행의 문자열 필드 하나."""
    key: str      # "섹션|행키|문자열순번" (중복 행은 #n 접미)
    text: str
    line: int     # Document.lines 인덱스
    part: int     # Line.parts 인덱스


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
            for si, pi in enumerate(range(1, len(ln.parts), 2)):
                text = ln.parts[pi]
                if text or include_empty:
                    out.append(Unit(f"{ln.section}|{row}|{si}", text, li, pi))
        return out

    def apply(self, translations: dict[str, str]) -> int:
        """key → 번역문 을 적용하고 바뀐 개수를 돌려준다."""
        changed = 0
        for u in self.units():
            new = translations.get(u.key)
            if new and new != u.text:
                if '"' in new:
                    raise ValueError(f"번역문에 큰따옴표를 쓸 수 없습니다: {u.key}")
                self.lines[u.line].parts[u.part] = new
                changed += 1
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
        elif section and not head.startswith(("//", "#")) and len(parts) >= 3 and len(parts) % 2 == 1:
            # '#include "파일", "경로"' 같은 지시문은 섹션 안에 있어도 번역 단위가 아니다
            line.section = section
            first = head.split(",", 1)[0].strip()
            line.key = first if first else parts[1]
        doc.lines.append(line)
    return doc


def tokens(text: str) -> list[str]:
    """나타나는 순서대로. printf 인자는 위치로 대응되므로 번역문도 같은 순서여야 한다."""
    return TOKEN_RE.findall(text)
