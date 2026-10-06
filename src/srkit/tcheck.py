"""게임의 번역 검사 로그(-tcheck 옵션, 저장 폴더의 LOG-TRANS-CHECK.log) 읽기.

게임은 시작할 때 화면 정의(HAP)에 나오는 문구마다 GUI 사전에 번역이 있는지 보고 두 가지를 적는다
(로그를 쓴 뒤에는 평소처럼 메인 메뉴로 간다).
    SRLOG: Missing GUI Translation, in <화면>, <문구>
    SRLOG: Incorrect Case Translation, in <화면>, <문구>, (<사전의 키>, <그 번역>)   ← 대소문자만 다른 키가 있음
다른 언어의 사전에 없는 문구(공식 번역에서도 빠진 것)는 이 로그로만 알 수 있다.

화면 표시는 대소문자까지 똑같은 키만 쓴다(게임 화면으로 확인). 똑같은 키가 없으면 Missing 이 적히고 영어로 나온다.
Incorrect Case 는 사전에서 대소문자를 무시하고 처음 걸린 키가 문구와 다르면 적힌다(196종 모두 파일의 앞쪽 키).
똑같은 키가 뒤에 따로 있어도 적히므로, Missing 없이 이 줄만 있으면 화면에는 번역이 제대로 나온다.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from . import srutf8

MISSING = re.compile(r"^SRLOG: Missing GUI Translation, in ([^,]*), (.*)$")
CASE = re.compile(r"^SRLOG: Incorrect Case Translation, in ([^,]*), (.*)$")
EXTRA_KEYS = "gui-keys-extra.csv"   # mods/korean/ 아래: 로그에서 모은 GUI 키 (extract 가 사전 키에 합친다)


@dataclass
class Log:
    missing: dict[str, str]              # 문구 → 처음 나온 화면
    case: dict[str, tuple[str, str]]     # 문구 → (사전의 키, 화면)


def parse(raw: bytes) -> Log:
    log = Log({}, {})
    for line in srutf8.decode(raw).replace("\r", "").split("\n"):
        if m := MISSING.match(line):
            log.missing.setdefault(m.group(2), m.group(1))
        elif m := CASE.match(line):
            rest = m.group(2)
            # "<문구>, (<키>, <번역>)" — 문구와 키는 길이가 같고 대소문자만 다르다(쉼표가 들어 있을 수 있다)
            for at in (i.start() for i in re.finditer(r", \(", rest)):
                text, key = rest[:at], rest[at + 3:at + 3 + at]
                if key.casefold() == text.casefold() and rest[at + 3 + at:at + 5 + at] == ", ":
                    log.case.setdefault(text, (key, m.group(1)))
                    break
    return log


def read_extra_keys(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["key"]: r["seen_in"] for r in csv.DictReader(f)}


def write_extra_keys(path: Path, keys: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["key", "seen_in"])
        w.writerows(sorted(keys.items(), key=lambda kv: (kv[1], kv[0])))
