"""
Taala Rule Learner (N3 / D2.1), Architecture §4.2.

Learns spelling-normalization rules from the pilot variant set, TRAIN HALF ONLY.

Design choices, each fixing a failure seen in the first version (which wrote rules
such as a->ee, k->ch, s->hh and turned "password" into "peteteteteveord"):

  * Rules are one-directional and always move toward the shorter form (or, for equal
    length, the alphabetically smaller one), so rewriting terminates and rules never
    fight each other. The first version added every rule in both directions.
  * Support is the number of DISTINCT WORDS that show the pattern, not the number of
    times it was seen. One word with 20 spellings cannot carry a rule on its own.
  * Only pairs of spellings that are clearly the same word are aligned
    (SequenceMatcher ratio >= MIN_PAIR_RATIO), so a typo does not teach a rule.
  * Collisions are measured against ~15k common English words and passwords from
    zxcvbn's own frequency lists, not a hand-typed list of 3-letter words.
  * The learner's scoring applies the same pipeline as the engine: rules to a fixed
    point, then repeated-letter collapse (taala/canon.py).
  * Output goes to rules_learned.tsv. The shipped rules.tsv is never overwritten;
    the hand-written set stays as the baseline the learner has to beat.

Usage:
    python tools/learn_rules.py [--min-words 2] [--lambda 5] [--mu 2]
"""
import argparse
import csv
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT_PATH = ROOT / "survey" / "split.tsv"
WORDS_PATH = ROOT / "survey" / "words.tsv"
WILD_PATH = ROOT / "data" / "variants" / "wild.tsv"
CONSTRUCTED_PATH = ROOT / "data" / "variants" / "constructed.tsv"
OBSERVED_PATH = ROOT / "data" / "variants" / "observed_authors.tsv"
OUT_PATH = ROOT / "locales" / "hi-latn" / "rules_learned.tsv"

MIN_PAIR_RATIO = 0.70
MAX_PATTERN_LEN = 3
MAX_RULES = 40
MIN_GAIN = 1e-4


def load_train():
    """Return {word_id: set(spellings)} for TRAIN words only, and the train id set."""
    with open(SPLIT_PATH, encoding="utf-8") as f:
        train = {r["id"] for r in csv.DictReader(f, delimiter="\t") if r["split"] == "train"}
    variants = defaultdict(set)
    with open(WORDS_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["id"] in train:
                variants[r["id"]].add(r["ref_latin"].lower())
    for path in (WILD_PATH, CONSTRUCTED_PATH, OBSERVED_PATH):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                wid, sp = r.get("word_id"), (r.get("spelling") or "").lower()
                if wid in train and sp.isalpha():
                    variants[wid].add(sp)
    return dict(variants), train


def pack_words(exclude):
    """Raw tokens from the Hinglish pack, minus the reference spellings of TEST words."""
    out = set()
    for f in sorted((ROOT / "locales" / "hi-latn" / "words").glob("*.txt")):
        out.update(w.strip().lower() for w in f.read_text(encoding="utf-8").splitlines())
    return sorted(w for w in out if w.isalpha() and w not in exclude)


def test_refs(train):
    with open(WORDS_PATH, encoding="utf-8") as f:
        return {r["ref_latin"].lower() for r in csv.DictReader(f, delimiter="	") if r["id"] not in train}


def english_words():
    from zxcvbn.frequency_lists import FREQUENCY_LISTS as F
    words = set(F["english_wikipedia"][:10000]) | set(F["passwords"][:5000])
    return sorted(w for w in words if w.isalpha() and w.isascii() and len(w) >= 3)


def canon(word, rules):
    """Same order as taala/canon.py: rules to a fixed point, then collapse repeats."""
    prev = None
    for _ in range(10):
        if word == prev:
            break
        prev = word
        for old, new in rules:
            word = word.replace(old, new)
    return re.sub(r"(.)\1+", r"\1", word)


def directed(a, b):
    """Order (a, b) as (from, to): toward shorter, then alphabetically smaller."""
    if len(a) != len(b):
        return (a, b) if len(a) > len(b) else (b, a)
    return (a, b) if a > b else (b, a)


def extract_candidates(variants, min_words):
    """Candidate (old, new) rules, with the set of distinct words that support each."""
    support = defaultdict(set)
    for wid, spellings in variants.items():
        for s1, s2 in ((a, b) for a in spellings for b in spellings if a < b):
            m = difflib.SequenceMatcher(None, s1, s2)
            if m.ratio() < MIN_PAIR_RATIO:
                continue
            for tag, i1, i2, j1, j2 in m.get_opcodes():
                if tag != "replace":
                    continue
                a, b = s1[i1:i2], s2[j1:j2]
                if not (1 <= len(a) <= MAX_PATTERN_LEN and 1 <= len(b) <= MAX_PATTERN_LEN):
                    continue
                old, new = directed(a, b)
                support[(old, new)].add(wid)
    return {k: v for k, v in support.items() if len(v) >= min_words}


class Scorer:
    def __init__(self, variants, english, pack):
        self.variants = variants
        self.english = english
        self.pack = pack
        self.base_pack_merges = self._pack_merges([])
        self.train_spellings = {s for v in variants.values() for s in v}
        self.pairs_total = sum(len(v) * (len(v) - 1) // 2 for v in variants.values())
        self.base_collisions = self._collisions([])

    def _pack_merges(self, rules):
        """Distinct pack tokens lost to merging: a rule set that fuses real words is penalised."""
        return len(self.pack) - len({canon(w, rules) for w in self.pack})

    def _collisions(self, rules):
        hinglish = {canon(s, rules) for s in self.train_spellings}
        return {w for w in self.english if w not in self.train_spellings and canon(w, rules) in hinglish}

    def metrics(self, rules):
        merged, owner = 0, defaultdict(set)
        for wid, sp in self.variants.items():
            counts = defaultdict(int)
            for s in sp:
                c = canon(s, rules)
                counts[c] += 1
                owner[c].add(wid)
            merged += sum(n * (n - 1) // 2 for n in counts.values())
        merge_rate = merged / self.pairs_total if self.pairs_total else 0.0
        train_fm = sum(1 for w in owner.values() if len(w) > 1) / len(self.variants)
        pack_fm = (self._pack_merges(rules) - self.base_pack_merges) / len(self.pack)
        false_merge = train_fm + pack_fm
        new_collisions = self._collisions(rules) - self.base_collisions
        return merge_rate, false_merge, len(new_collisions) / len(self.english)


def greedy(cands, scorer, lam, mu):
    selected, current = [], None
    m, fm, ec = scorer.metrics([])
    current = m - lam * fm - mu * ec
    print(f"baseline (no rules): merge={m:.3f} false_merge={fm:.4f} english_collision={ec:.4f}")
    remaining = list(cands)
    while remaining and len(selected) < MAX_RULES:
        best = None
        for c in remaining:
            m, fm, ec = scorer.metrics(selected + [c])
            gain = (m - lam * fm - mu * ec) - current
            if best is None or gain > best[0]:
                best = (gain, c, (m, fm, ec))
        if best[0] < MIN_GAIN:
            break
        gain, c, (m, fm, ec) = best
        selected.append(c)
        remaining.remove(c)
        current += gain
        print(f"+ {c[0]!r}->{c[1]!r}  words={len(cands[c])}  gain={gain:.4f}  "
              f"merge={m:.3f} false_merge={fm:.4f} english_collision={ec:.4f}")
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-words", type=int, default=2, help="distinct words that must show a rule")
    ap.add_argument("--lambda", dest="lam", type=float, default=5.0)
    ap.add_argument("--mu", type=float, default=2.0)
    args = ap.parse_args()

    variants, train = load_train()
    multi = {k: v for k, v in variants.items() if len(v) >= 2}
    print(f"train words: {len(train)}, with 2+ spellings: {len(multi)}, "
          f"spellings: {sum(len(v) for v in variants.values())}")
    cands = extract_candidates(multi, args.min_words)
    print(f"candidates supported by >= {args.min_words} words: {len(cands)}")
    scorer = Scorer(multi, english_words(), pack_words(test_refs(train)))
    selected = greedy(cands, scorer, args.lam, args.mu)

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["pattern", "replacement", "support_words"])
        for c in selected:
            w.writerow([c[0], c[1], len(cands[c])])
    print(f"wrote {len(selected)} rules to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
