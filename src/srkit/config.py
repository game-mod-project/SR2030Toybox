"""프로젝트 루트와 srkit.toml 설정 로딩."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = "srkit.toml"


@dataclass(frozen=True)
class Config:
    root: Path
    game_dir: Path
    source_lang: str
    target_lang: str
    display_name: str
    hangul_font: Path
    hangul_weight_regular: int
    hangul_weight_bold: int

    @property
    def localize_dir(self) -> Path:
        return self.game_dir / "Localize"

    @property
    def source_dir(self) -> Path:
        return self.localize_dir / self.source_lang

    @property
    def korean_mod_dir(self) -> Path:
        return self.root / "mods" / "korean"

    @property
    def translation_dir(self) -> Path:
        return self.korean_mod_dir / "translation"

    @property
    def build_dir(self) -> Path:
        return self.root / "build"


def user_save_dir() -> Path:
    """게임이 저장·로그를 쓰는 폴더: <문서>\\My Games\\Supreme Ruler 2030\\Savegame (문서 폴더는 리디렉션될 수 있다)."""
    import ctypes

    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL
    return Path(buf.value) / "My Games" / "Supreme Ruler 2030" / "Savegame"


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if (p / CONFIG_NAME).is_file():
            return p
    raise FileNotFoundError(f"{CONFIG_NAME} 을(를) 찾을 수 없습니다 (시작 위치: {here})")


def load(start: Path | None = None) -> Config:
    root = find_root(start)
    data = tomllib.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
    ko = data.get("korean", {})
    game_dir = Path(os.environ.get("SR2030_GAME_DIR") or data["game_dir"])
    return Config(
        root=root,
        game_dir=game_dir,
        source_lang=ko.get("source_lang", "LOCALEN"),
        target_lang=ko.get("target_lang", "LOCALKO"),
        display_name=ko.get("display_name", "Korean"),
        hangul_font=Path(ko.get("hangul_font", r"C:\Windows\Fonts\malgun.ttf")),
        hangul_weight_regular=int(ko.get("hangul_weight_regular", 400)),
        hangul_weight_bold=int(ko.get("hangul_weight_bold", 700)),
    )
