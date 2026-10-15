"""Generate one blank spelling sheet per author, each in a different word order.

Usage:
    python tools/make_collection_sheets.py            # authors A B C D
    python tools/make_collection_sheets.py --authors A B C D E

Each sheet contains only the word id and the Devanagari form. It deliberately omits
ref_latin, category and phenomena, so nobody is primed by a reference spelling or by
knowing which phenomenon a word targets. The order differs per author so that fatigue
does not always hit the same words.
"""

import argparse
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "survey" / "words.tsv"
OUT_DIR = ROOT / "data" / "variants" / "sheets"
SEED = 20261007


def main(authors):
    with WORDS.open(encoding="utf-8", newline="") as fh:
        rows = [(r["id"], r["devanagari"]) for r in csv.DictReader(fh, delimiter="\t")]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for author in authors:
        shuffled = rows[:]
        random.Random(f"{SEED}:{author}").shuffle(shuffled)
        path = OUT_DIR / f"author_{author}.tsv"
        if path.exists():
            print(f"skipped {path.name} (already exists, not overwriting your answers)")
            continue
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
            writer.writerow(["word_id", "devanagari", "spelling", "spelling_alt", "dont_know"])
            for wid, dev in shuffled:
                writer.writerow([wid, dev, "", "", ""])
        print(f"wrote {path.relative_to(ROOT)} ({len(shuffled)} words)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--authors", nargs="+", default=["A", "B", "C", "D"])
    main(parser.parse_args().authors)
