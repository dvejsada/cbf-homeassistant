"""Fixtures for CBF tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TEAM_ID = 7817  # TJ ÚVN
PHASE_ID = 10469  # 2.třída B 2026/27


def load(name: str) -> bytes:
    """Load a fixture file."""
    return (FIXTURES / name).read_bytes()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    return
