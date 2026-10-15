"""Validate survey/words.tsv, generate the frozen train/test split, and hash both.

Usage:
    python tools/freeze_wordlist.py            # create the freeze (refuses to overwrite)
    python tools/freeze_wordlist.py --force    # re-freeze after a deliberate word-list change
    python tools/freeze_wordlist.py --check    # verify current files against FREEZE.json

The split is by word and stratified by category, so both halves cover every category.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "survey" / "words.tsv"
SPLIT = ROOT / "survey" / "split.tsv"
FREEZE = ROOT / "survey" / "FREEZE.json"

SEED = 20261007
N_WORDS = 100

CATEGORIES = {
    "given_name", "surname", "deity_festival", "place",
    "everyday", "film_music", "sports",
}
PHENOMENA = {
    "long_aa", "ee_i", "oo_u", "v_w", "ph_f", "z_j", "sh_s", "final_a",
    "aspirate", "nasal", "cluster", "retroflex", "diphthong", "doubled",
    "vocalic_r", "glide", "plain",
}
DEVANAGARI = range(0x0900, 0x0980)


def read_words():
    with WORDS.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    validate(rows)
    return rows


def validate(rows):
    """Fail loudly on anything that would corrupt the experiment."""
    assert len(rows) == N_WORDS, f"expected {N_WORDS} words, found {len(rows)}"

    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), "duplicate word ids"

    seen_devanagari = set()
    for r in rows:
        wid = r["id"]
        dev = r["devanagari"].strip()
        assert dev, f"{wid}: empty devanagari"
        assert any(ord(ch) in DEVANAGARI for ch in dev), f"{wid}: no Devanagari characters"
        assert dev not in seen_devanagari, f"{wid}: duplicate Devanagari form"
        seen_devanagari.add(dev)

        ref = r["ref_latin"].strip()
        assert ref and ref.isascii() and ref.isalpha() and ref.islower(), (
            f"{wid}: ref_latin must be lowercase a-z, got {ref!r}"
        )

        assert r["category"] in CATEGORIES, f"{wid}: unknown category {r['category']!r}"

        tags = [t for t in r["phenomena"].split(",") if t]
        assert tags, f"{wid}: no phenomena tags"
        unknown = set(tags) - PHENOMENA
        assert not unknown, f"{wid}: unknown phenomena {sorted(unknown)}"


def _split_once(rows, seed):
    """Stratified alternating split: exactly half train, half test."""
    rng = random.Random(seed)
    ordered = []
    for category in sorted(CATEGORIES):
        group = [r["id"] for r in rows if r["category"] == category]
        rng.shuffle(group)
        ordered.extend(group)
    assert len(ordered) == len(rows)
    return {wid: ("train" if i % 2 == 0 else "test") for i, wid in enumerate(ordered)}


def phenomena_balanced(rows, split):
    """Every spelling phenomenon must appear in both halves, or it cannot be tested."""
    halves = {"train": set(), "test": set()}
    for row in rows:
        halves[split[row["id"]]].update(t for t in row["phenomena"].split(",") if t)
    return not (halves["train"] ^ halves["test"])


def build_split(rows, seed=SEED):
    """The first seed at or above `seed` whose split covers every phenomenon twice.

    Stratifying by category alone is not enough: a phenomenon carried by only three
    words (z_j, for instance) can land entirely in one half, which makes it untestable.
    Searching upward from a fixed seed keeps the result deterministic and the choice
    auditable, while leaving the split random within that one constraint.
    """
    for candidate in range(seed, seed + 1000):
        split = _split_once(rows, candidate)
        if phenomena_balanced(rows, split):
            return split, candidate
    raise AssertionError("no seed within 1000 tries balanced the phenomena")


def write_split(split):
    with SPLIT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "split"])
        for wid in sorted(split):
            writer.writerow([wid, split[wid]])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def do_freeze(force):
    if FREEZE.exists() and not force:
        sys.exit("FREEZE.json already exists. Use --force only for a deliberate change.")
    rows = read_words()
    split, used_seed = build_split(rows)
    write_split(split)

    counts = {"train": 0, "test": 0}
    for half in split.values():
        counts[half] += 1
    assert counts["train"] == counts["test"] == N_WORDS // 2, counts

    FREEZE.write_text(json.dumps({
        "seed_start": SEED,
        "seed_used": used_seed,
        "seed_rule": "first seed at or above seed_start whose split puts every phenomenon in both halves",
        "n_words": N_WORDS,
        "frozen_on": dt.date.today().isoformat(),
        "sha256": {"words.tsv": sha256(WORDS), "split.tsv": sha256(SPLIT)},
        "note": "Rules are developed on the train half only. The test half is opened once, in P4.",
    }, indent=2) + "\n", encoding="utf-8")

    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], {"train": 0, "test": 0})[split[r["id"]]] += 1
    print(f"froze {N_WORDS} words: {counts['train']} train / {counts['test']} test")
    for cat in sorted(by_cat):
        print(f"  {cat:16s} train={by_cat[cat]['train']:2d} test={by_cat[cat]['test']:2d}")


def do_check():
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    read_words()  # structural validation still passes
    for name, path in (("words.tsv", WORDS), ("split.tsv", SPLIT)):
        actual = sha256(path)
        expected = frozen["sha256"][name]
        if actual != expected:
            sys.exit(f"{name} changed since the freeze\n  expected {expected}\n  actual   {actual}")
    print("freeze intact")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    do_check() if args.check else do_freeze(args.force)
