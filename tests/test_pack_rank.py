"""The rank file is private; a clone without it must still work and say so."""
from pathlib import Path

import conftest
from taala import pack
from taala.estimate import estimate


def test_missing_rank_file_falls_back_deterministically():
    try:
        pack.configure(rank_file=Path("does_not_exist.txt"))
        assert not pack.has_rank_file()
        first = estimate("rahul2803")["guesses_log10"]
        pack.configure(rank_file=Path("does_not_exist.txt"))
        assert estimate("rahul2803")["guesses_log10"] == first
        assert pack.get_ranked_words() == sorted(pack.get_words())
    finally:
        pack.configure()


@conftest.needs_wordlists
def test_rank_file_orders_words_first(tmp_path):
    words = sorted(pack.get_words())
    f = tmp_path / "rank.txt"
    f.write_text(words[-1] + chr(10) + words[-2] + chr(10), encoding="utf-8")
    try:
        pack.configure(rank_file=f)
        assert pack.has_rank_file()
        assert pack.get_ranked_words()[:2] == [words[-1], words[-2]]
    finally:
        pack.configure()


def test_canonical_word_collapses_repeated_letters():
    # Regression: the backreference was once written as a literal control character,
    # which silently turned the collapse step into a no-op.
    pack.configure()
    assert pack.canonical_word("helllo") == pack.canonical_word("hello") == "helo"
    assert pack.canonical_word("mummmy") == "mumy"
    src = open(pack.__file__, "rb").read()
    assert bytes([1]) not in src  # no stray control characters in the source
