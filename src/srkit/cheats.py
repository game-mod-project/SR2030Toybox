"""게임의 내장 치트가 문서(docs/07-cheats.md)와 같은지 대조한다 — 게임 업데이트로 치트가 사라졌는지 알아채는 용도.

실행 파일의 ``cheat <이름>`` 문자열과 문서에 적힌 명령을 비교하고, 치트 입력란이 있는 Game Settings 창의
단축키 행(INI/hotkeys.csv)이 남아 있는지 본다. 게임 폴더는 읽기만 한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import Config
from .deploy import GAME_EXE

CHEAT_RE = re.compile(rb"cheat ([!-~]{1,20})")
DOC_RE = re.compile(r"`cheat ([a-z0-9=!]+)`")      # `cheat <이름>` 같은 일반 표기는 명령이 아니다
DOC_BUILD_RE = re.compile(r"build `(\d+)`")
HOTKEY_RE = re.compile(rb"^0x53,0,4,[^\r\n]*Game Settings", re.M)     # <Ctrl> + <Shift> + <S>
DOC = "docs/07-cheats.md"


@dataclass
class Report:
    build: str | None                 # 설치된 게임의 Steam 빌드 번호 (알 수 없으면 None)
    doc_build: str | None             # 문서가 조사한 빌드 번호
    removed: list[str] = field(default_factory=list)    # 문서에는 있는데 게임에서 사라진 명령
    added: list[str] = field(default_factory=list)      # 게임에 새로 생긴 명령
    settings_hotkey: bool = True      # Game Settings 창을 여는 단축키 행이 있는가

    @property
    def ok(self) -> bool:
        return not self.removed and not self.added and self.settings_hotkey


def names_in(exe: bytes) -> list[str]:
    """실행 파일에 든 내장 치트 명령의 이름."""
    return sorted({m.decode("ascii") for m in CHEAT_RE.findall(exe)})


def documented(doc: str) -> set[str]:
    return set(DOC_RE.findall(doc))


def documented_build(doc: str) -> str | None:
    m = DOC_BUILD_RE.search(doc)
    return m.group(1) if m else None


def installed_build(cfg: Config) -> str | None:
    """Steam 이 적어 둔 빌드 번호(steamapps/appmanifest_<appid>.acf). 없으면 None."""
    appid = cfg.game_dir / "steam_appid.txt"
    if not appid.is_file():
        return None
    manifest = cfg.game_dir.parent.parent / f"appmanifest_{appid.read_text().strip()}.acf"
    if not manifest.is_file():
        return None
    m = re.search(r'"buildid"\s+"(\d+)"', manifest.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def check(cfg: Config) -> Report:
    exe = cfg.game_dir / GAME_EXE
    if not exe.is_file():
        raise RuntimeError(f"게임 폴더가 아닙니다({GAME_EXE} 없음): {cfg.game_dir}")
    doc = (cfg.root / DOC).read_text(encoding="utf-8")
    in_game, in_doc = set(names_in(exe.read_bytes())), documented(doc)
    hotkeys = cfg.game_dir / "INI" / "hotkeys.csv"
    return Report(build=installed_build(cfg), doc_build=documented_build(doc),
                  removed=sorted(in_doc - in_game), added=sorted(in_game - in_doc),
                  settings_hotkey=hotkeys.is_file() and bool(HOTKEY_RE.search(hotkeys.read_bytes())))
