"""Pack loader for Taala. Reads rules, script, and wordlists from locales/hi-latn/"""
import csv
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set

PACK_DIR = Path(__file__).resolve().parent.parent / "locales" / "hi-latn"

_RULES_FILE = None  # override for ablations, see configure()
_RANK_FILE = None


def load_rules() -> List[Tuple[str, str]]:
    """Load spelling rules from rules.tsv (or the file given to configure())."""
    rules_path = _RULES_FILE or PACK_DIR / "rules.tsv"
    if not rules_path.exists(): return []
    rules = []
    with open(rules_path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            pattern = row.get("pattern")
            replacement = row.get("replacement")
            if pattern and replacement is not None:
                rules.append((pattern, replacement))
    return rules

def load_script() -> Dict[str, str]:
    """Load Devanagari -> Latin character map from script.tsv."""
    script_path = PACK_DIR / "script.tsv"
    if not script_path.exists(): return {}
    script = {}
    with open(script_path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            script[row["devanagari"]] = row["latin"]
    return script

def canonical_word(w: str) -> str:
    """Apply the locale rules to a fixed point, then collapse repeats (Architecture §3 [3])."""
    prev, curr = None, w.lower()
    while prev != curr:
        prev = curr
        for old, new in get_rules():
            curr = curr.replace(old, new)
    return re.sub(r'(.)\1+', r'\1', curr)


def load_words() -> Set[str]:
    """
    Load all pack words into a single set, applying locale rules and repeat collapse 
    so they match the canonicalized passwords (Architecture §3 [3]).
    """
    words_dir = PACK_DIR / "words"
    if not words_dir.exists(): return set()
    
    rules = get_rules()
    words = set()
    
    for txt_file in words_dir.glob("*.txt"):
        with open(txt_file, encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w and w.isalpha(): 
                    # Apply locale rules iteratively
                    prev = None
                    curr = w
                    while prev != curr:
                        prev = curr
                        for old, new in rules:
                            curr = curr.replace(old, new)
                    # Collapse repeats
                    curr = re.sub(r'(.)\1+', r'\1', curr)
                    words.add(curr)
    return words

# Module-level caching
_RULES_CACHE = _SCRIPT_CACHE = _WORDS_CACHE = _RANKED_CACHE = None

def configure(rules_file=None, rank_file=None):
    """Swap the rule file and/or rank file (evaluation ablations) and drop every cache."""
    global _RULES_FILE, _RANK_FILE, _RULES_CACHE, _SCRIPT_CACHE, _WORDS_CACHE, _RANKED_CACHE
    _RULES_FILE, _RANK_FILE = rules_file, rank_file
    _RULES_CACHE = _SCRIPT_CACHE = _WORDS_CACHE = _RANKED_CACHE = None


def get_rules():
    global _RULES_CACHE
    if _RULES_CACHE is None: _RULES_CACHE = load_rules()
    return _RULES_CACHE

def get_script():
    global _SCRIPT_CACHE
    if _SCRIPT_CACHE is None: _SCRIPT_CACHE = load_script()
    return _SCRIPT_CACHE

def get_words():
    global _WORDS_CACHE
    if _WORDS_CACHE is None: _WORDS_CACHE = load_words()
    return _WORDS_CACHE


def has_word_lists() -> bool:
    """False on a fresh clone: the lists are built locally by tools/fetch_wordlists.py."""
    return any((PACK_DIR / "words").glob("*.txt"))


def rank_file_path():
    return _RANK_FILE or PACK_DIR.parent.parent / "data" / "private" / "pack_rank.txt"


def has_rank_file() -> bool:
    """False on a fresh clone: the rank file is built from breach data and is not distributed."""
    return rank_file_path().exists()


def get_ranked_words() -> List[str]:
    """Pack words in a DETERMINISTIC order, most common first.

    zxcvbn turns list position into a guess count, so a set's iteration order (which changes
    with PYTHONHASHSEED) made scores differ between runs. Order comes from
    data/private/pack_rank.txt (tools/rank_pack.py, train half only) when present, and is
    alphabetical otherwise. Words missing from the rank file follow it, alphabetically.
    """
    global _RANKED_CACHE
    if _RANKED_CACHE is None:
        words = get_words()
        rank_file = rank_file_path()
        ranked: List[str] = []
        if rank_file.exists():
            ranked = [w for w in rank_file.read_text(encoding="utf-8").split() if w in words]
        listed = set(ranked)
        _RANKED_CACHE = ranked + sorted(words - listed)
    return _RANKED_CACHE
