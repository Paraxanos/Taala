"""The pack's word lists must be clean enough for the blocklist to use directly.

These run only if the lists have been fetched (`python tools/fetch_wordlists.py`), since
the generated lists are not committed. pack.toml is committed, so the provenance checks
always run.
"""

import importlib.util
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "locales" / "hi-latn"
PACK_TOML = PACK / "pack.toml"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = _load("fetch_wordlists")

pytestmark = pytest.mark.skipif(not PACK_TOML.exists(), reason="run tools/fetch_wordlists.py first")


def pack():
    return tomllib.loads(PACK_TOML.read_text(encoding="utf-8"))


def entries():
    return pack()["lists"]


def test_pack_metadata_is_present():
    meta = pack()["pack"]
    assert meta["name"] == "hi-latn"
    assert meta["ranking"]  # must say whether the lists are ranked yet


def test_every_list_records_its_provenance():
    for entry in entries():
        assert entry["source"], entry["file"]
        assert entry["fetched"], entry["file"]
        assert entry["license"], entry["file"]
        if entry["kind"] != "seed":
            assert entry["categories"], f"{entry['file']} has no source categories"


def test_tokens_are_clean():
    for entry in entries():
        path = PACK / entry["file"]
        if not path.exists():
            pytest.skip(f"{entry['file']} not fetched")
        tokens = path.read_text(encoding="utf-8").split()
        assert tokens, entry["file"]
        for token in tokens:
            assert token.isalpha() and token.isascii(), f"{entry['file']}: {token!r}"
            assert token.islower(), f"{entry['file']}: {token!r}"
            assert fetch.MIN_TOKEN <= len(token) <= fetch.MAX_TOKEN, f"{entry['file']}: {token!r}"
            assert token not in fetch.STOPWORDS, f"{entry['file']}: {token!r} is a filler word"


def test_tokens_are_unique_and_sorted():
    for entry in entries():
        path = PACK / entry["file"]
        if not path.exists():
            pytest.skip(f"{entry['file']} not fetched")
        tokens = path.read_text(encoding="utf-8").split()
        assert len(set(tokens)) == len(tokens), f"{entry['file']} has duplicates"
        assert tokens == sorted(tokens), f"{entry['file']} is not sorted"


def test_counts_match_the_files():
    for entry in entries():
        path = PACK / entry["file"]
        if not path.exists():
            pytest.skip(f"{entry['file']} not fetched")
        actual = len(path.read_text(encoding="utf-8").split())
        assert actual == entry["count"], (
            f"{entry['file']}: pack.toml says {entry['count']}, file has {actual}. "
            "Re-run tools/fetch_wordlists.py."
        )


def test_survey_words_are_covered_by_the_pack():
    """Sanity: the Hindi words we chose for the survey should mostly be in the lists.

    Not all of them will be — everyday words come from the seed list, and some names are
    spelled differently on Wikipedia. A very low overlap means the lists are off-target.
    """
    import csv

    present = set()
    for entry in entries():
        path = PACK / entry["file"]
        if path.exists():
            present.update(path.read_text(encoding="utf-8").split())
    if not present:
        pytest.skip("no lists fetched")

    with (ROOT / "survey" / "words.tsv").open(encoding="utf-8", newline="") as fh:
        refs = [r["ref_latin"] for r in csv.DictReader(fh, delimiter="\t")]
    hits = sum(1 for r in refs if r in present)
    assert hits >= len(refs) * 0.30, f"only {hits}/{len(refs)} survey words are in the pack"
