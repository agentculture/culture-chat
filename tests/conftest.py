"""Pytest fixtures shared across test modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.smoke_support import build_fixture


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A faithful fixture clone of the files the smoke check's config stage reads."""
    return build_fixture(tmp_path / "clone")


@pytest.fixture
def on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty PATH containing only the fake tools a test plants."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir
