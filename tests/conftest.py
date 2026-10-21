"""Shared test setup.

The Hinglish word lists are built locally (python tools/fetch_wordlists.py) and are not
committed, so a fresh clone does not have them. Tests that need them are skipped, not failed.
"""
import pytest

from taala import pack

needs_wordlists = pytest.mark.skipif(
    not any((pack.PACK_DIR / "words").glob("*.txt")),
    reason="word lists not built: run python tools/fetch_wordlists.py",
)
