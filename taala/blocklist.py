"""Taala blocklist lookup (N1 / E1.3)."""
import re
from typing import List, Set, Optional
from .pack import get_words, get_rules

_BLOCKLIST: Set[str] = {
    "password", "123456", "123456789", "guest", "admin", "root",
    "qwerty", "login", "welcome", "monkey", "letmein",
    "princess", "football", "hello", "charlie", "12345678",
    "1234", "12345", "123", "1111", "dragon", "master",
    "qwertyuiop", "baseball", "abc123", "trustno1", "sunshine",
}

def _canonicalize_word(w: str, rules: list) -> str:
    """Apply rules and collapse repeats to a single word."""
    curr = w.lower()
    prev = None
    while prev != curr:
        prev = curr
        for old, new in rules:
            curr = curr.replace(old, new)
    return re.sub(r'(.)\1+', r'\1', curr)

_CACHE = None  # (rules, words, blocklist); rebuilt when pack.configure() swaps either


def get_full_blocklist() -> Set[str]:
    """Combines the hardcoded weak passwords with the canonicalized pack words.

    Built once per loaded pack. Callers must not mutate the returned set.
    """
    global _CACHE
    rules, words = get_rules(), get_words()
    if _CACHE is not None and _CACHE[0] is rules and _CACHE[1] is words:
        return _CACHE[2]
    # Canonicalize the hardcoded weak passwords
    bl = {_canonicalize_word(w, rules) for w in _BLOCKLIST}
    # Add the already-canonicalized pack words
    bl.update(words)
    _CACHE = (rules, words, bl)
    return bl

def check(password: str, blocklist: Optional[Set[str]] = None) -> List[str]:
    from .canon import generate_canonical_forms
    forms = generate_canonical_forms(password)
    bl = get_full_blocklist() if blocklist is None else blocklist
    hits = [f for f in forms if f in bl]
    return hits