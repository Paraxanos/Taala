"""Rank the Hinglish pack words by how often they occur as a whole password base in the
TRAIN half of the corpus (D1.2 / pack ranking). Never reads the test half.

Output: data/private/pack_rank.txt (gitignored: derived from the breach corpus).
Without it, taala.pack falls back to alphabetical order, which is deterministic but unranked.

Usage:  python tools/rank_pack.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from taala.pack import get_words  # noqa: E402

TRAIN = ROOT / "data" / "splits" / "train_counts.tsv"
OUT = ROOT / "data" / "private" / "pack_rank.txt"


def main():
    import argparse
    from taala import pack
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", help="rule file to rank under (default: shipped rules.tsv)")
    ap.add_argument("--out", help="output file (default: data/private/pack_rank.txt)")
    a = ap.parse_args()
    out = Path(a.out) if a.out else OUT
    if a.rules:
        pack.configure(rules_file=Path(a.rules))
    words = get_words()
    counts = Counter()
    from taala.pack import canonical_word
    with TRAIN.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            n, _, pw = line.rstrip("\n").partition("\t")
            base = re.sub(r"[^a-z]", "", pw.lower())
            if len(base) >= 3:
                c = canonical_word(base)
                if c in words:
                    counts[c] += int(n or 1)
    ranked = sorted(words, key=lambda w: (-counts[w], w))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(ranked) + "\n", encoding="utf-8")
    seen = sum(1 for w in words if counts[w])
    print(f"{len(words)} pack words, {seen} seen in the train half; wrote {out}")
    print("top 15:", ", ".join(ranked[:15]))


if __name__ == "__main__":
    main()
