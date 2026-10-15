"""The variant tables must respect the hold-out and declare where every row came from."""

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "data" / "variants"


def read(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


@pytest.fixture(scope="module")
def words():
    return {r["id"]: r for r in read(ROOT / "survey" / "words.tsv")}


@pytest.fixture(scope="module")
def split():
    return {r["id"]: r["split"] for r in read(ROOT / "survey" / "split.tsv")}


def test_constructed_covers_train_words_only(split):
    """Writing a spelling for a test word contaminates the hold-out irreversibly."""
    rows = read(VARIANTS / "constructed.tsv")
    assert rows, "constructed.tsv is empty"
    for row in rows:
        assert split[row["word_id"]] == "train", f"{row['word_id']} is a test word"


def test_constructed_declares_that_it_is_not_human_data(words):
    for row in read(VARIANTS / "constructed.tsv"):
        assert "model-generated" in row["note"]
        assert row["spelling"] != words[row["word_id"]]["ref_latin"]


def test_spellings_are_plain_lowercase_latin(words):
    for name in ("constructed.tsv", "wild.tsv"):
        for row in read(VARIANTS / name):
            s = row["spelling"]
            assert s.isascii() and s.isalpha() and s.islower(), f"{name}: {s!r}"
            assert 2 <= len(s) <= 24, f"{name}: {s!r}"


def test_no_duplicate_rows_within_a_file():
    for name in ("constructed.tsv", "wild.tsv"):
        rows = read(VARIANTS / name)
        pairs = [(r["word_id"], r["spelling"]) for r in rows]
        assert len(pairs) == len(set(pairs)), name


def test_wild_rows_name_their_source():
    for row in read(VARIANTS / "wild.tsv"):
        assert row["source"] == "wikipedia_redirect"
        assert "->" in row["source_detail"]


def test_wild_holds_no_rejected_spellings():
    """The junk the filter drops must not creep back in on a re-collection."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cw", ROOT / "tools" / "collect_wild.py")
    cw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cw)
    refs = {r["id"]: r["ref_latin"] for r in read(ROOT / "survey" / "words.tsv")}
    for row in read(VARIANTS / "wild.tsv"):
        ref = refs[row["word_id"]]
        assert cw.is_spelling_variant(ref, row["spelling"]), f"{row['spelling']} for {ref}"


def test_enough_pairs_for_d0_3():
    """D0.3's bar: at least 150 usable spellings, at least 60 of them externally attested."""
    wild = read(VARIANTS / "wild.tsv")
    total = len(wild) + len(read(VARIANTS / "constructed.tsv"))
    assert len(wild) >= 60, len(wild)
    assert total >= 150, total
