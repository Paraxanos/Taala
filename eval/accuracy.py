"""Taala §6.1: does Taala judge Indian passwords better than stock zxcvbn?  (N7)

Metrics, all measured against how often each password occurs (Architecture §6.1):
  overrating  share of the 10,000 most common passwords NOT called Weak   (headline)
  strictness  share of rare passwords called Weak                         (not just rejecting everything)
  rank agreement  Spearman correlation of guesses_log10 with frequency rank

IMPORTANT, read before quoting any number:
  * The corpus here is rockyou.txt WITHOUT counts, so every password occurs once.
    The original file is ordered by frequency, and the split keeps that order, so the
    position in the split file is used as the frequency rank. "Rare" means the second
    half of the file. This is a proxy, and the report must say so.
  * Each password lands in exactly one half, so the test half's common passwords are
    never in the train half. Nothing here is a blocklist test.
  * The Indian set is selected with OUR pack, so it favours us (NOVELTY.md N7 weakness).
  * Weak means guesses_log10 < 6.0 for every system, so the comparison is like for like.

Test-half discipline (IMPLEMENTATION_PLAN §2): develop with --split train. The test half
may be scored once; a lock file in results/ blocks a second run unless --allow-rerun is
given, and the rerun is then recorded. No individual password is ever printed or written.

Usage:
    python eval/accuracy.py --split train --quick      # development
    python eval/accuracy.py --split test               # the one real run
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import zxcvbn  # noqa: E402
from zxcvbn.frequency_lists import FREQUENCY_LISTS as FL  # noqa: E402

from taala import pack  # noqa: E402
from taala.estimate import estimate, FAIR_THRESHOLD_LOG10  # noqa: E402

SPLITS = ROOT / "data" / "splits"
RESULTS = ROOT / "results"
SEED = 20261019
LEARNED_RULES = ROOT / "locales" / "hi-latn" / "rules_learned.tsv"
LEARNED_RANK = ROOT / "data" / "private" / "pack_rank_learned.txt"

SYSTEMS = ["stock_zxcvbn", "taala", "ablation_no_canon", "ablation_no_pack", "ablation_learned_rules"]


# ---------------------------------------------------------------------------
# Systems
# ---------------------------------------------------------------------------

def score_stock(pw):
    return zxcvbn.zxcvbn(pw)["guesses_log10"]


def make_scorer(system):
    if system == "stock_zxcvbn":
        return score_stock
    if system == "taala":
        return lambda pw: estimate(pw)["guesses_log10"]
    if system == "ablation_no_canon":
        return lambda pw: estimate(pw, use_canon=False)["guesses_log10"]
    if system == "ablation_no_pack":
        return lambda pw: estimate(pw, use_pack=False)["guesses_log10"]
    if system == "ablation_learned_rules":
        return lambda pw: estimate(pw)["guesses_log10"]  # caller switches the pack
    raise ValueError(system)


# ---------------------------------------------------------------------------
# Indian-context set (Architecture §6.1)
# ---------------------------------------------------------------------------

CURATED_LISTS = ["given_names", "surnames", "deities", "festivals", "places", "common_words"]


class IndianMatcher:
    """A password is Indian-context if its letters-only base canonicalises to a pack word,
    or to two pack words joined, and an English dictionary does not contain it.

    Only the curated Indian lists count (names, deities, festivals, places, common words).
    films_music and sports are left out: they hold English titles and Western names.
    The English dictionary is a union, because zxcvbn removes a word from a later list if an
    earlier one has it (so 'love' is absent from english_wikipedia) and english_wikipedia
    itself contains 'priya' and 'rahul', so its long tail is cut off."""

    def __init__(self):
        words = ROOT / "locales" / "hi-latn" / "words"
        self.pack = {pack.canonical_word(w.strip()) for name in CURATED_LISTS
                     for w in (words / f"{name}.txt").read_text(encoding="utf-8").split() if w.isalpha()}
        self.english = (set(FL["english_wikipedia"][:8000]) | set(FL["us_tv_and_film"][:8000])
                        | set(FL["passwords"][:2000]))
        self.cache = {}

    def _english_like(self, w):
        return w in self.english

    MIN_PART = 4  # shorter pack tokens are mostly Wikipedia fragments (ela, mar, jos)

    def match(self, pw):
        """Return the matched pack token(s) as a tuple, or None.

        Both parts of a join must be absent from the English and name lists. The first
        version allowed one English part and matched 163k passwords, mostly 'love' + noise."""
        base = re.sub(r"[^a-z]", "", pw.lower())
        if not 4 <= len(base) <= 30 or base in self.english:
            return None
        if base in self.cache:
            return self.cache[base]
        c = pack.canonical_word(base)
        hit = None
        if c in self.pack and not self._english_like(base) and not self._english_like(c):
            hit = (c,)
        else:
            for i in range(self.MIN_PART, len(c) - self.MIN_PART + 1):
                a, b = c[:i], c[i:]
                if a in self.pack and b in self.pack and not self._english_like(a) and not self._english_like(b):
                    hit = (a, b)
                    break
        self.cache[base] = hit
        return hit


# ---------------------------------------------------------------------------
# One streaming pass over the split file
# ---------------------------------------------------------------------------

def collect(split, quick):
    path = SPLITS / f"{split}_counts.tsv"
    manifest = json.loads((SPLITS / "MANIFEST.json").read_text(encoding="utf-8"))
    n_total = manifest["counts"][split]
    k = 10 if quick else 1
    top_n, rare_n, rank_n, rank_pool = 10000 // k, 10000 // k, 10000 // k, 100000 // k
    rng = random.Random(SEED)
    rare_pos = set(rng.sample(range(n_total // 2, n_total), rare_n))
    rank_pos = set(rng.sample(range(1, rank_pool + 1), rank_n))

    sets = {"top": [], "rare": [], "rank": []}
    indian = []          # (position, password) for every Indian-context password
    token_counts = Counter()
    matcher = IndianMatcher()
    with path.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for pos, line in enumerate(fh, 1):
            pw = line.rstrip("\n").partition("\t")[2]
            if pos <= top_n:
                sets["top"].append((pos, pw))
            if pos in rare_pos:
                sets["rare"].append((pos, pw))
            if pos in rank_pos:
                sets["rank"].append((pos, pw))
            m = matcher.match(pw)
            if m:
                indian.append((pos, pw))
                token_counts.update(m)
    return sets, indian, token_counts, n_total


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def avg_ranks(xs):
    order = sorted(range(len(xs)), key=xs.__getitem__)
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return float("nan")
    rx, ry = avg_ranks(xs), avg_ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def proportion(flags):
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n if n else float("nan")), "ci95": [lo, hi]}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_system(system, scorer, groups, cache):
    """groups: {name: [(pos, pw), ...]} -> metrics. cache memoises scores per password."""
    def score(pw):
        if pw not in cache:
            cache[pw] = scorer(pw)
        return cache[pw]

    out = {}
    for name, items in groups.items():
        scores = [score(pw) for _, pw in items]
        if name.endswith("_overrating"):
            out[name] = proportion([s >= FAIR_THRESHOLD_LOG10 for s in scores])
        elif name.endswith("_strictness"):
            out[name] = proportion([s < FAIR_THRESHOLD_LOG10 for s in scores])
        elif name.endswith("_rank"):
            out[name] = {"n": len(items), "spearman": spearman(scores, [p for p, _ in items])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "test"], required=True)
    ap.add_argument("--quick", action="store_true", help="1/10 sample sizes (development)")
    ap.add_argument("--allow-rerun", action="store_true", help="score the test half again (recorded)")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    lock = RESULTS / "test_run.lock.json"
    if args.split == "test":
        if args.quick:
            sys.exit("refusing: --quick is for development, and a test run is one-off")
        if lock.exists() and not args.allow_rerun:
            sys.exit(f"The test half was already scored ({lock.name}). A rerun must be justified "
                     f"in the report; pass --allow-rerun to do it and record it.")

    t0 = time.time()
    print(f"[{args.split}] scanning split and selecting sets ...", flush=True)
    sets, indian, tokens, n_total = collect(args.split, args.quick)
    k = 10 if args.quick else 1
    ind_top = indian[: 10000 // k]
    ind_tail = [x for x in indian if x[0] >= n_total // 2]
    ind_tail = random.Random(SEED).sample(ind_tail, min(len(ind_tail), 5000 // k))
    ind_rank = indian[: 10000 // k]
    print(f"  indian-context passwords: {len(indian)} "
          f"(top {len(ind_top)} used; tail sample {len(ind_tail)}); "
          f"distinct pack tokens matched: {len(tokens)}", flush=True)
    print("  most-matched pack tokens:", ", ".join(f"{w}:{c}" for w, c in tokens.most_common(12)), flush=True)

    groups = {
        "all_overrating": sets["top"], "all_strictness": sets["rare"], "all_rank": sets["rank"],
        "indian_overrating": ind_top, "indian_strictness": ind_tail, "indian_rank": ind_rank,
    }
    sizes = {k_: len(v) for k_, v in groups.items()}

    results = {}
    for system in SYSTEMS:
        t1 = time.time()
        if system == "ablation_learned_rules":
            pack.configure(rules_file=LEARNED_RULES, rank_file=LEARNED_RANK)
        else:
            pack.configure()
        results[system] = evaluate_system(system, make_scorer(system), groups, {})
        print(f"  {system}: done in {time.time() - t1:.0f}s", flush=True)
    pack.configure()

    import hashlib
    frozen = ["taala/estimate.py", "taala/canon.py", "taala/pack.py", "taala/feedback.py",
              "locales/hi-latn/rules.tsv", "locales/hi-latn/rules_learned.tsv",
              "locales/hi-latn/script.tsv", "eval/accuracy.py"]
    hashes = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()[:16] for f in frozen}
    meta = {
        "code_sha256_16": hashes,
        "zxcvbn_version": getattr(zxcvbn, "__version__", "unknown"),
        "split": args.split, "quick": args.quick, "seed": SEED, "n_split": n_total,
        "weak_below_log10": FAIR_THRESHOLD_LOG10, "set_sizes": sizes,
        "indian_context_total": len(indian), "distinct_pack_tokens_matched": len(tokens),
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0),
        "proxy_note": "rockyou.txt has no counts: file position is the frequency rank; "
                      "'rare' is the second half of the file.",
    }
    stem = f"accuracy_{args.split}{'_quick' if args.quick else ''}"
    (RESULTS / f"{stem}.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2), encoding="utf-8")
    (RESULTS / f"{stem}.md").write_text(render(meta, results), encoding="utf-8")
    print(render(meta, results))

    if args.split == "test":
        prior = json.loads(lock.read_text(encoding="utf-8")) if lock.exists() else {"runs": []}
        prior["runs"].append({"finished": meta["finished"], "rerun": args.allow_rerun})
        lock.write_text(json.dumps(prior, indent=2), encoding="utf-8")


def fmt_rate(m):
    lo, hi = m["ci95"]
    return f"{m['rate']*100:5.1f}% [{lo*100:.1f}, {hi*100:.1f}] (n={m['n']})"


def render(meta, r):
    rows = [
        f"# §6.1 accuracy: {meta['split']} half{' (QUICK, development only)' if meta['quick'] else ''}",
        "",
        f"Weak = guesses_log10 < {meta['weak_below_log10']}. Rates with 95% Wilson intervals.",
        f"Proxy: {meta['proxy_note']}",
        f"Indian-context passwords found: {meta['indian_context_total']}.",
        "",
        "| System | Overrating, all | Overrating, Indian | Strictness, all | Strictness, Indian | Spearman, all | Spearman, Indian |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in SYSTEMS:
        x = r[s]
        rows.append(f"| {s} | {fmt_rate(x['all_overrating'])} | {fmt_rate(x['indian_overrating'])} | "
                    f"{fmt_rate(x['all_strictness'])} | {fmt_rate(x['indian_strictness'])} | "
                    f"{x['all_rank']['spearman']:.3f} | {x['indian_rank']['spearman']:.3f} |")
    rows += ["", "Overrating: lower is better. Strictness: report beside overrating, not alone.",
             "Spearman: guesses_log10 against file position; higher is better.", ""]
    return "\n".join(rows)


if __name__ == "__main__":
    main()
