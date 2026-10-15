"""Pack loader for Taala. Reads rules, script, and wordlists from locales/hi-latn/"""
import csv
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set

PACK_DIR = Path(__file__).resolve().parent.parent / "locales" / "hi-latn"

def load_rules() -> List[Tuple[str, str]]:
    """Load learned spelling rules from rules.tsv."""
    rules_path = PACK_DIR / "rules.tsv"
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
_RULES_CACHE = _SCRIPT_CACHE = _WORDS_CACHE = None

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