"""Collect alternate romanizations from Wikipedia redirects.

These are *observed* spellings: someone other than us wrote them, and each row records
where it came from. That makes them better evidence than spellings we invent ourselves.

Usage:
    python tools/collect_wild.py --limit 5     # try a few words first
    python tools/collect_wild.py               # all words that have a wiki_title

Method: for each word with a `wiki_title`, ask the English Wikipedia API for that page's
redirects. A redirect like "Laxmi" -> "Lakshmi" is a romanization someone attested. We
keep a redirect only if, after normalising, it is a single a-z token similar enough to
the reference spelling to be the same name rather than a different phrase.
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "survey" / "words.tsv"
OUT = ROOT / "data" / "variants" / "wild.tsv"

API = "https://en.wikipedia.org/w/api.php"
UA = "Taala-research/0.1 (student project on password strength; contact via repo)"
MIN_SIMILARITY = 0.70
MAX_LEN_DIFF = 3
MAX_INSERT = 3          # a run of this many new characters is another word, not a respelling

# Two redirects survive every structural rule above because the difference is semantic,
# not shaped like one. Curated by hand, listed here so the decision is auditable and the
# next run reproduces it. Keep this list tiny: if it grows, the rules above are wrong.
REJECTED = {
    ("chaudhary", "chaudhrani"): "feminine title (Chaudhrani), a different word",
    ("bhopal", "bhojpal"): "Bhojpal is a historical name for the city, not a spelling of Bhopal",
}
PAUSE_SECONDS = 1.0
BACKOFF_SECONDS = (5, 15, 30)


def normalise(title):
    """'Laxmi (goddess)' -> 'laxmi'. Returns '' if nothing usable is left."""
    title = re.sub(r"\(.*?\)", " ", title)
    title = title.replace("-", "").replace("'", "").replace(".", "")
    collapsed = re.sub(r"\s+", "", title).lower()
    return collapsed if collapsed.isascii() and collapsed.isalpha() else ""


def fetch_redirects(title):
    """Return (canonical_title, [redirect titles]). Follows the page's own redirect."""
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "redirects", "rdlimit": "max", "redirects": "1", "titles": title,
    }
    req = urllib.request.Request(
        f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA}
    )
    for attempt, wait in enumerate((*BACKOFF_SECONDS, None)):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or wait is None:
                raise
            print(f"  rate limited, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)

    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None, []
    page = pages[0]
    return page["title"], [r["title"] for r in page.get("redirects", [])]


def is_spelling_variant(ref, cand):
    """True if `cand` spells the same word differently, rather than being another name.

    Wikipedia redirects mix two things together. 'laksmi' is a spelling of 'lakshmi';
    'mahalakshmi' and 'lakshmidevi' are different names that merely contain it. Two
    cheap rules separate them: a spelling variant stays about the same length, and
    neither form contains the other whole.
    """
    if not (2 <= len(cand) <= 24) or cand == ref:
        return False
    if abs(len(cand) - len(ref)) > MAX_LEN_DIFF:
        return False
    if ref in cand or cand in ref:
        return False
    if REJECTED.get((ref, cand)):
        return False
    if longest_insertion(ref, cand) >= MAX_INSERT:
        return False
    return SequenceMatcher(None, ref, cand).ratio() >= MIN_SIMILARITY


def longest_insertion(ref, cand):
    """Longest run of characters `cand` adds that `ref` has nothing to match.

    'laksmidevi' adds 'devi' to 'laksmi' and 'chetnavrati' adds 'chet' to 'navratri':
    whole extra words. A respelling only ever swaps or doubles a letter or two, so the
    runs it adds are short. Deletions do not count -- 'amdavad' for 'ahmedabad' drops
    letters but is still the same name.
    """
    worst = 0
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, ref, cand).get_opcodes():
        if tag in ("insert", "replace"):
            worst = max(worst, (j2 - j1) - (i2 - i1))
    return worst


def candidates(ref, canonical, redirects):
    """Normalised spellings that plausibly spell the same word as `ref`."""
    out = {}
    for raw in ([canonical] if canonical else []) + redirects:
        cand = normalise(raw)
        if cand and is_spelling_variant(ref, cand):
            out.setdefault(cand, raw)
    return out


def _self_check():
    """The filter must keep real variants and drop other names."""
    for good in ("laksmi", "laxshmi", "lakshami", "laskhmi"):
        assert is_spelling_variant("lakshmi", good), good
    for bad in ("mahalakshmi", "lakshmidevi", "godesslakshmi", "dhanalakshmi", "lakshmi"):
        assert not is_spelling_variant("lakshmi", bad), bad
    assert is_spelling_variant("gurunanak", "gurunank")
    assert not is_spelling_variant("gurunanak", "nanak")
    assert not is_spelling_variant("varanasi", "varanasicity")
    assert is_spelling_variant("varanasi", "baranasi")
    # whole extra words, caught by the insertion rule
    for bad in ("laksmidevi", "mahalaksmi"):
        assert not is_spelling_variant("lakshmi", bad), bad
    assert not is_spelling_variant("phoolan", "poolandevi")
    assert not is_spelling_variant("navratri", "chetnavrati")
    assert not is_spelling_variant("chennai", "chennapuri")
    # curated rejections
    assert not is_spelling_variant("chaudhary", "chaudhrani")
    assert not is_spelling_variant("bhopal", "bhojpal")
    # respellings the insertion rule must not touch
    assert is_spelling_variant("diwali", "deepwali")
    assert is_spelling_variant("ahmedabad", "amdavad")
    assert is_spelling_variant("dhoom", "dhooom")
    assert is_spelling_variant("jaishreeram", "jayashreerama")
    assert is_spelling_variant("bengaluru", "bangalooru")


def clean_existing():
    """Re-apply the filter to wild.tsv without touching the network.

    The rows were collected under a looser filter. Re-running the collector would work
    but costs ten minutes of API calls for a result that depends only on the filter, so
    rows are re-tested in place instead.
    """
    with WORDS.open(encoding="utf-8", newline="") as fh:
        ref_of = {r["id"]: r["ref_latin"] for r in csv.DictReader(fh, delimiter="\t")}
    with OUT.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    keep, drop = [], []
    for row in rows:
        ref = ref_of[row["word_id"]]
        (keep if is_spelling_variant(ref, row["spelling"]) else drop).append((ref, row))

    for ref, row in drop:
        why = REJECTED.get((ref, row["spelling"])) or               f"adds {longest_insertion(ref, row['spelling'])} characters in a row"
        print(f"  dropped {row['spelling']} (for {ref}): {why}")

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(row for _, row in keep)
    print(f"kept {len(keep)} spellings, dropped {len(drop)}")


def main(limit):
    with WORDS.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh, delimiter="\t") if r["wiki_title"].strip()]
    if limit:
        rows = rows[:limit]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    found = kept = 0
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["word_id", "devanagari", "spelling", "source", "source_detail"])
        for row in rows:
            ref = row["ref_latin"]
            try:
                canonical, redirects = fetch_redirects(row["wiki_title"])
            except Exception as exc:  # network and API hiccups should not lose earlier rows
                print(f"  {row['id']}: lookup failed ({exc})", file=sys.stderr)
                continue
            if canonical is None:
                print(f"  {row['id']}: no such page {row['wiki_title']!r}")
                continue
            found += 1
            for spelling, raw in sorted(candidates(ref, canonical, redirects).items()):
                writer.writerow([
                    row["id"], row["devanagari"], spelling,
                    "wikipedia_redirect", f"{row['wiki_title']} -> {raw}",
                ])
                kept += 1
            time.sleep(PAUSE_SECONDS)

    print(f"queried {len(rows)} titles, {found} pages existed, kept {kept} spellings")
    print(f"wrote {OUT.relative_to(ROOT)}")
    if kept < 60 and not limit:
        print("NOTE: under the 60-spelling target in D0.3. Add titles to words.tsv's "
              "wiki_title column, or collect by hand from film and cricket sites.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="only the first N titles")
    parser.add_argument("--self-check", action="store_true", help="test the filter, no network")
    parser.add_argument("--clean-existing", action="store_true",
                        help="re-filter the rows already in wild.tsv, no network")
    args = parser.parse_args()
    _self_check()
    if args.self_check:
        print("filter self-check passed")
    elif args.clean_existing:
        clean_existing()
    else:
        main(args.limit)
