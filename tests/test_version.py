from __future__ import annotations

from sardegna_radar import __version__


def test_package_version() -> None:
    assert __version__ == "1.1.0"
