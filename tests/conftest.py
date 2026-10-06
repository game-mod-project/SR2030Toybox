from pathlib import Path

import pytest

from srkit import config


@pytest.fixture(scope="session")
def cfg() -> config.Config:
    return config.load(Path(__file__).parent)


@pytest.fixture(scope="session")
def game_dir(cfg) -> Path:
    """실제 게임 설치본이 필요한 테스트용. 없으면 건너뛴다."""
    if not (cfg.game_dir / "Localize" / "LOCALEN").is_dir():
        pytest.skip(f"게임 설치본 없음: {cfg.game_dir}")
    return cfg.game_dir
