"""Smoke test to verify that the compintel package scaffold is importable."""

import pytest

import compintel


@pytest.mark.unit
def test_compintel_package_imports() -> None:
    """Verify that the compintel package imports cleanly."""
    assert compintel is not None
