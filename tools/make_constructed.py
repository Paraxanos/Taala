"""Build data/variants/constructed.tsv from the hand-written list in constructed_spellings.txt.

The spellings in that list were written one at a time by a language model, from knowledge
of how Hindi words get typed in Latin letters. They are not human-authored data and the
note column on every row says so. They were NOT produced by applying a rewrite table: if they had
been, the rule learner would simply rediscover the table it was given and every merge
rate in section 6.2 would be circular.

Two rules this script enforces, because both are easy to break by accident:

  1. Train words only. The 50/50 split in survey/split.tsv was frozen before any
     spelling existed. Writing a spelling for a test word contaminates the hold-out, and
     no later care undoes it.
  2. Development only. These spellings are a stand-in for data we do not have yet. They
     may train a learner; they may never appear in a test table or in a reported number.
     tools/build_variants.py (D1.3) is where that is enforced.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "survey" / "words.tsv"
SPLIT = ROOT / "survey" / "split.tsv"
SOURCE = Path(__file__).with_name("constructed_spellings.txt")
WILD = ROOT / "data" / "variants" / "wild.tsv"
OUT = ROOT / "data" / "variants" / "constructed.tsv"

NOTE = "model-generated (Claude), not written by a human author; development only, never in a test table"
SPELLING = re.compile(r"^[a-z]{2,24}$")


def load_words():
    with WORDS.open(encoding="utf-8", newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh, delimiter="\t")}


def load_train_ids():
    with SPLIT.open(encoding="utf-8", newline="") as fh:
        return {r["id"] for r in csv.DictReader(fh, delimiter="\t") if r["split"] == "train"}


def load_source():
    out = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            out.append((parts[0], parts[1:]))
    return out


def main():
    words, train = load_words(), load_train_ids()
    rows, seen = [], set()

    for word_id, spellings in load_source():
        assert word_id in words, f"unknown word id {word_id}"
        assert word_id in train, f"{word_id} is a TEST word -- the hold-out forbids this"
        ref = words[word_id]["ref_latin"]
        for spelling in spellings:
            assert SPELLING.match(spelling), f"{spelling!r} is not 2-24 lowercase letters"
            assert spelling != ref, f"{spelling} is the reference spelling, not a variant"
            assert (word_id, spelling) not in seen, f"duplicate {word_id} {spelling}"
            seen.add((word_id, spelling))
            rows.append([word_id, words[word_id]["devanagari"], spelling, NOTE])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["word_id", "devanagari", "spelling", "note"])
        writer.writerows(rows)

    print(f"wrote {len(rows)} spellings across {len(load_source())} train words")
    if WILD.exists():
        with WILD.open(encoding="utf-8", newline="") as fh:
            wild = {(r["word_id"], r["spelling"]) for r in csv.DictReader(fh, delimiter="\t")}
        print(f"also present in wild.tsv: {len(seen & wild)} (harmless, D1.3 deduplicates)")


if __name__ == "__main__":
    main()
