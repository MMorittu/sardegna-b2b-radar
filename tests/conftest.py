from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Return an isolated temporary SQLite database path."""
    return tmp_path / "test_radar.db"
