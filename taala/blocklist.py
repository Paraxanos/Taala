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

def get_full_blocklist() -> Set[str]:
    """Combines the hardcoded weak passwords with the canonicalized pack words."""
    rules = get_rules()
    # Canonicalize the hardcoded weak passwords
    bl = {_canonicalize_word(w, rules) for w in _BLOCKLIST}
    # Add the already-canonicalized pack words
    bl.update(get_words()) 
    return bl

def check(password: str, blocklist: Optional[Set[str]] = None) -> List[str]:
    from .canon import generate_canonical_forms
    forms = generate_canonical_forms(password)
    bl = blocklist or get_full_blocklist()
    hits = [f for f in forms if f in bl]
    return hits