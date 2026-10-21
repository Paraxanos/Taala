"""The word list and split must not drift after the freeze.

If these fail, either someone edited survey/words.tsv or the split was regenerated. Both
invalidate the train/test separation that every §6.2 result depends on.
"""

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


freeze_wordlist = _load("freeze_wordlist")


def test_hashes_match_freeze():
    frozen = json.loads((ROOT / "survey" / "FREEZE.json").read_text(encoding="utf-8"))
    for name in ("words.tsv", "split.tsv"):
        actual = freeze_wordlist.sha256(ROOT / "survey" / name)
        assert actual == frozen["sha256"][name], f"{name} changed since the freeze"


def test_words_still_valid():
    freeze_wordlist.read_words()  # raises on any structural problem


def test_split_is_half_and_covers_every_word():
    with (ROOT / "survey" / "split.tsv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    halves = [r["split"] for r in rows]
    assert len(rows) == freeze_wordlist.N_WORDS
    assert halves.count("train") == halves.count("test") == freeze_wordlist.N_WORDS // 2

    word_ids = {r["id"] for r in freeze_wordlist.read_words()}
    assert {r["id"] for r in rows} == word_ids


def test_split_is_reproducible_from_the_seed():
    rows = freeze_wordlist.read_words()
    rebuilt, used_seed = freeze_wordlist.build_split(rows)
    with (ROOT / "survey" / "split.tsv").open(encoding="utf-8", newline="") as fh:
        on_disk = {r["id"]: r["split"] for r in csv.DictReader(fh, delimiter="\t")}
    assert rebuilt == on_disk

    frozen = json.loads((ROOT / "survey" / "FREEZE.json").read_text(encoding="utf-8"))
    assert used_seed == frozen["seed_used"]


def test_every_phenomenon_appears_in_both_halves():
    """A phenomenon only in the train half cannot be tested, and vice versa."""
    rows = freeze_wordlist.read_words()
    with (ROOT / "survey" / "split.tsv").open(encoding="utf-8", newline="") as fh:
        split = {r["id"]: r["split"] for r in csv.DictReader(fh, delimiter="\t")}

    halves = {"train": set(), "test": set()}
    for row in rows:
        for tag in row["phenomena"].split(","):
            halves[split[row["id"]]].add(tag)

    missing = halves["train"] ^ halves["test"]
    assert not missing, f"phenomena present in only one half: {sorted(missing)}"


def test_gitattributes_pins_line_endings():
    """Regression: a CRLF checkout on Windows CI changed the bytes and broke the freeze hashes."""
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "eol=lf" in attrs and "*.tsv" in attrs
