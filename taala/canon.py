"""Taala canonicalizer — spelling-independent checking (N1)."""
import unicodedata
import re
import itertools
from typing import List, Set, Dict
from .pack import get_rules, get_script

def transliterate_devanagari(text: str, script_map: Dict[str, str]) -> str:
    """Transliterates Devanagari to Latin, handling inherent final 'a' deletion."""
    text = unicodedata.normalize("NFC", text)
    res = []
    i = 0
    while i < len(text):
        char = text[i]
        mapped = script_map.get(char, char)
        is_consonant = ('\u0915' <= char <= '\u0939') or char in ('क़', 'ख़', 'ग़', 'ज़', 'ड़', 'ढ़', 'फ़')
        
        if is_consonant:
            res.append(mapped)
            if i + 1 < len(text):
                next_char = text[i+1]
                is_vowel_sign = ('\u093E' <= next_char <= '\u094C') or next_char in ('ृ', 'ॄ')
                is_virama = next_char == '्'
                if not (is_vowel_sign or is_virama):
                    res.append('a')
        else:
            res.append(mapped)
        i += 1
    return "".join(res)

def has_devanagari(text: str) -> bool:
    return any('\u0900' <= c <= '\u097F' for c in text)

def split_padding(forms: Set[str]) -> Set[str]:
    new_forms = set()
    for s in forms:
        new_forms.add(s)
        match = re.match(r'^([^a-z]*)(.*?)([^a-z]*)$', s)
        if match:
            base = match.group(2)
            if base and base != s: new_forms.add(base)
    return new_forms

LEET_MAP = {
    '@': ['a'], '0': ['o'], '1': ['i', 'l'], '3': ['e'], 
    '$': ['s'], '5': ['s'], '7': ['t'], '4': ['a']
}

def expand_leet(forms: Set[str], cap: int) -> Set[str]:
    new_forms = set()
    for s in forms:
        options = [LEET_MAP.get(c, [c]) for c in s]
        for combo in itertools.product(*options):
            new_forms.add("".join(combo))
            if len(forms) + len(new_forms) >= cap:
                return forms.union(new_forms)
    return forms.union(new_forms)

def apply_locale_rules(s: str, rules: List[tuple]) -> str:
    prev = None
    current = s
    while prev != current:
        prev = current
        for old, new in rules:
            current = current.replace(old, new)
    return current

def collapse_repeats(s: str) -> str:
    return re.sub(r'(.)\1+', r'\1', s)

def generate_canonical_forms(password: str, max_forms: int = 8) -> List[str]:
    script_map = get_script()
    rules = get_rules()
    
    norm = unicodedata.normalize("NFKC", password)
    forms = {norm}
    
    new_forms = set()
    for f in forms:
        new_forms.add(f)
        if has_devanagari(f):
            new_forms.add(transliterate_devanagari(f, script_map))
    forms = new_forms
    
    forms = {f.lower() for f in forms}
    forms = split_padding(forms)
    forms = expand_leet(forms, max_forms)
    
    final_forms = set()
    for f in forms:
        f = apply_locale_rules(f, rules)
        f = collapse_repeats(f)
        if f: final_forms.add(f)
        
    return sorted(list(final_forms))[:max_forms]

def analyze(password: str) -> dict:
    forms = generate_canonical_forms(password)
    from .blocklist import check as _bl_check
    blocklist_hits = _bl_check(password)
    
    reason_parts = []
    if len(password) < 4: reason_parts.append("too_short")
    if any(c.isdigit() for c in password): reason_parts.append("has_digits")
    if any(c in "!@#$%^&*()" for c in password): reason_parts.append("has_special")
        
    return {
        "forms": forms,
        "blocklist_hit": bool(blocklist_hits),
        "structure_reason": "+".join(reason_parts) if reason_parts else "normal",
        "band": "Weak" if len(password) <= 4 else ("Fair" if len(password) <= 7 else "Strong"),
    }