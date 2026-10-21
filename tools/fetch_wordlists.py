"""Build the Hinglish pack's word lists from public reference sources (D0.4).

Words come from English Wikipedia category membership, not from our own memory, so every
list has a source that someone else can check. `pack.toml` records which categories fed
which file and when.

Usage:
    python tools/fetch_wordlists.py --list given_names     # one list
    python tools/fetch_wordlists.py                       # all of them (~3 minutes)
    python tools/fetch_wordlists.py --self-check           # token cleaning only, no network

Ranking comes later: the architecture ranks each list by how often its entries appear in
the training corpus, which needs D1.2, which needs the D0.1 sign-off. Until then the
lists are alphabetical and `pack.toml` says so.
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "locales" / "hi-latn"
WORDS_DIR = PACK / "words"
SURVEY_WORDS = ROOT / "survey" / "words.tsv"

API = "https://en.wikipedia.org/w/api.php"
UA = "Taala-research/0.1 (student project on password strength; contact via repo)"
PAUSE_SECONDS = 1.2
BACKOFF_SECONDS = (5, 15, 30)

# 3, not 4: "ram", "jai", "dev" and "raj" are exactly the short words people build
# passwords from. Short English noise also gets in, which is what the pack builder's
# English-collision guard (D2.2) is for. Safe because the blocklist only matches whole
# canonical forms, so "ram" in the list never blocks "programmer".
MIN_TOKEN = 3
MAX_TOKEN = 20
MAX_PER_LIST = 4000
MAX_REQUESTS_PER_LIST = 120
SAMPLE_SEED = 20261007

# Words that describe Wikipedia's own structure rather than naming anything.
STOPWORDS = {
    "list", "lists", "index", "outline", "category", "name", "names", "surname",
    "surnames", "india", "indian", "indians", "film", "films", "movie", "language",
    "district", "districts", "city", "cities", "town", "towns", "village", "villages",
    "state", "states", "union", "territory", "hindu", "hinduism", "goddess", "goddesses",
    "cricketer", "cricketers", "cricket", "people", "disambiguation", "given", "family",
    "origin", "south", "north", "east", "west", "national", "team", "test", "first",
    "and", "the", "of", "in", "by", "at", "on", "for", "from", "with",
}
SKIP_TITLE_PREFIXES = ("list of", "lists of", "index of", "outline of", "glossary of")

# list name -> (kind, [(category, subcategory depth)])
SOURCES = {
    "given_names": ("person", [
        ("Indian masculine given names", 0),
        ("Indian feminine given names", 0),
        ("Indian given names", 0),
    ]),
    "surnames": ("person", [("Surnames of Indian origin", 0)]),
    "deities": ("person", [("Hindu gods", 0), ("Hindu goddesses", 0)]),
    "festivals": ("title", [("Hindu festivals", 0)]),
    "sports": ("person", [("Indian cricketers", 0)]),
    # Two parents are needed: "Cities and towns in ..." holds smaller towns, while the
    # big cities (Pune, Varanasi, Ahmedabad) sit under "Cities in ...".
    "places": ("title", [
        ("Cities and towns in India by state or union territory", 1),
        ("Cities in India by state or union territory", 1),
    ]),
    "films_music": ("title", [
        ("2020s Hindi-language films", 1),
        ("2010s Hindi-language films", 1),
        ("2000s Hindi-language films", 1),
        ("1990s Hindi-language films", 1),
    ]),
}


def api_get(params):
    url = f"{API}?{urllib.parse.urlencode({**params, 'action': 'query', 'format': 'json', 'formatversion': '2'})}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for wait in (*BACKOFF_SECONDS, None):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or wait is None:
                raise
            print(f"    rate limited, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)


def category_members(category, member_type, budget):
    """All page or subcategory titles in a category, following continuations."""
    titles, cont = [], None
    while budget[0] > 0:
        params = {"list": "categorymembers", "cmtitle": f"Category:{category}",
                  "cmlimit": "500", "cmtype": member_type}
        if cont:
            params["cmcontinue"] = cont
        data = api_get(params)
        budget[0] -= 1
        time.sleep(PAUSE_SECONDS)
        titles += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return titles


def collect_titles(categories):
    """Page titles from each category, descending `depth` levels of subcategories."""
    budget = [MAX_REQUESTS_PER_LIST]
    titles, used = [], []
    for category, depth in categories:
        frontier = [category]
        for level in range(depth + 1):
            next_frontier = []
            for cat in frontier:
                if budget[0] <= 0:
                    print(f"    request budget spent, stopping at {cat!r}")
                    break
                titles += category_members(cat, "page", budget)
                used.append(cat)
                if level < depth:
                    next_frontier += [
                        t.removeprefix("Category:")
                        for t in category_members(cat, "subcat", budget)
                    ]
            frontier = next_frontier
    return titles, used


def tokens_from_title(title, kind):
    """A Wikipedia title becomes zero or more candidate word-list entries."""
    if title.lower().startswith(SKIP_TITLE_PREFIXES):
        return []
    cleaned = re.sub(r"\(.*?\)", " ", title)          # drop "(cricketer)", "(1998 film)"
    cleaned = re.sub(r"[^A-Za-z\s-]", " ", cleaned)   # drop digits and punctuation
    parts = [p.lower() for p in re.split(r"[\s-]+", cleaned) if p]
    parts = [p for p in parts if p not in STOPWORDS]

    out = [p for p in parts if MIN_TOKEN <= len(p) <= MAX_TOKEN]
    # Films and places are also typed as one run-together word: "Navi Mumbai" -> navimumbai.
    # Filler words are already gone from `parts`, so joining them cannot smuggle any back.
    if kind == "title" and len(parts) > 1:
        joined = "".join(parts)
        if MIN_TOKEN <= len(joined) <= MAX_TOKEN:
            out.append(joined)
    return out


def write_list(name, tokens):
    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    path = WORDS_DIR / f"{name}.txt"
    path.write_text("\n".join(tokens) + "\n", encoding="utf-8")
    return path


def common_words_from_survey():
    """Everyday Hindi words we already chose for the survey; expanded in P2."""
    with SURVEY_WORDS.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    return sorted({r["ref_latin"] for r in rows if r["category"] == "everyday"})


def cap(tokens):
    """Keep at most MAX_PER_LIST tokens, sampling rather than slicing.

    Slicing a sorted list throws away everything after one letter of the alphabet, which
    is how an earlier run produced a film list ending at "maximum". Sampling with a fixed
    seed keeps coverage across the alphabet and stays reproducible.
    """
    import random
    if len(tokens) <= MAX_PER_LIST:
        return sorted(tokens), False
    sampled = random.Random(SAMPLE_SEED).sample(sorted(tokens), MAX_PER_LIST)
    return sorted(sampled), True


def build(selected):
    manifest = {}
    for name, (kind, categories) in SOURCES.items():
        if selected and name not in selected:
            continue
        print(f"{name}: fetching")
        titles, used = collect_titles(categories)
        tokens, sampled = cap({t for title in titles for t in tokens_from_title(title, kind)})
        write_list(name, tokens)
        manifest[name] = {"kind": kind, "count": len(tokens), "sampled": sampled,
                          "categories": [c for c, _ in categories],
                          "categories_traversed": len(used), "titles_seen": len(titles)}
        print(f"  {len(titles)} titles -> {len(tokens)} tokens"
              + (f" (sampled down from more; cap {MAX_PER_LIST})" if sampled else ""))

    if not selected or "common_words" in selected:
        tokens = common_words_from_survey()
        write_list("common_words", tokens)
        manifest["common_words"] = {"kind": "seed", "count": len(tokens), "sampled": False,
                                    "categories": [], "titles_seen": 0}
        print(f"common_words: {len(tokens)} tokens (seed from our survey word list)")
    return manifest


def write_pack_toml(manifest):
    today = dt.date.today().isoformat()
    lines = [
        "# Generated by tools/fetch_wordlists.py. Edit the script, not this file.",
        "",
        "[pack]",
        'name = "hi-latn"',
        'description = "Romanized Hindi (Hinglish) word lists and spelling rules"',
        'version = "0.1.0"',
        f'created = "{today}"',
        'ranking = "unranked (v0). Ranks by training-corpus frequency are added in P1, after D1.2."',
        'rules = "rules.tsv is produced by tools/learn_rules.py in P2 (D2.1)."',
        'known_gaps = "places: Wikipedia files Indian towns under per-state and '
        'per-district categories, so coverage is partial even after traversing both city '
        "parents. Ahmedabad is a known miss (only ahmednagar is present), so a "
        '\'largest cities\' source is still needed. films_music: sampled down to the cap. '
        'common_words: only 20 entries, seeded from our own survey words, because no clean '
        'public list of romanized everyday Hindi exists. All three are revisited in P3 '
        '(D3.2, word lists v2)."',
        "",
        "[gates]",
        "# Thresholds are set in P3 (S2.1) from measured values. Placeholders until then.",
        "merge_rate_min = 0.0",
        "false_merge_rate_max = 1.0",
        "english_collision_rate_max = 1.0",
        "cross_script_merge_rate_min = 0.0",
        "",
    ]
    for name in sorted(manifest):
        info = manifest[name]
        cats = ", ".join(f'"{c}"' for c in info["categories"])
        source = ("our own survey word list (survey/words.tsv, everyday words)"
                  if info["kind"] == "seed" else "English Wikipedia category membership")
        licence = ("ours" if info["kind"] == "seed"
                   else "CC BY-SA 4.0 (English Wikipedia). Built locally by tools/fetch_wordlists.py, not committed.")
        lines += [
            "[[lists]]",
            f'file = "words/{name}.txt"',
            f'kind = "{info["kind"]}"',
            f'count = {info["count"]}',
            f'sampled = {str(info.get("sampled", False)).lower()}',
            f'source = "{source}"',
            f"categories = [{cats}]",
            f'categories_traversed = {info.get("categories_traversed", len(info["categories"]))}',
            f'fetched = "{today}"',
            f'license = "{licence}"',
            "",
        ]
    (PACK / "pack.toml").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {(PACK / 'pack.toml').relative_to(ROOT)}")


def manifest_from_disk():
    """Rebuild pack.toml from the lists already on disk, without touching the network."""
    manifest = {}
    for path in sorted(WORDS_DIR.glob("*.txt")):
        name = path.stem
        kind, categories = SOURCES.get(name, ("seed", []))
        count = len(path.read_text(encoding="utf-8").split())
        manifest[name] = {
            "kind": kind if name != "common_words" else "seed",
            "count": count,
            "sampled": count >= MAX_PER_LIST,
            "categories": [c for c, _ in categories],
            "categories_traversed": 0,
            "titles_seen": 0,
        }
    return manifest


def _self_check():
    assert tokens_from_title("Virat Kohli (cricketer)", "person") == ["virat", "kohli"]
    assert tokens_from_title("List of Hindu festivals", "title") == []
    assert tokens_from_title("Dhoom 2 (2006 film)", "title") == ["dhoom"]
    assert tokens_from_title("Navi Mumbai", "title") == ["navi", "mumbai", "navimumbai"]
    # Filler words must not survive, not even glued inside the joined form.
    assert tokens_from_title("Cities and towns in Kerala", "title") == ["kerala"]
    assert tokens_from_title("Jai Shri Ram", "title") == ["jai", "shri", "ram", "jaishriram"]
    assert all(t.isalpha() and t.islower() for t in tokens_from_title("Aamir Khan", "person"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="append", dest="lists",
                        help="only this list; repeatable")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--pack-only", action="store_true",
                        help="rebuild pack.toml from the lists on disk, no network")
    args = parser.parse_args()
    _self_check()
    if args.self_check:
        print("token cleaning self-check passed")
    elif args.pack_only:
        write_pack_toml(manifest_from_disk())
    else:
        write_pack_toml(build(set(args.lists or [])))
