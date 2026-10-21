"""Taala strength estimator (N1 / E1.2 / E1.3)."""
import math
from typing import List, Optional, Dict, Any

try:
    import zxcvbn
    HAS_ZXCVBN = True
except ImportError:
    HAS_ZXCVBN = False

import re
import unicodedata

from .canon import generate_canonical_forms, has_devanagari, transliterate_devanagari
from .pack import get_script
from .pack import get_words, get_ranked_words
from .feedback import build_recipe

STRONG_THRESHOLD_LOG10 = 10.0
FAIR_THRESHOLD_LOG10 = 6.0
LOG10_7776 = math.log10(7776)
LOG10_2 = math.log10(2)

def get_band(guesses_log10: float) -> str:
    if guesses_log10 < FAIR_THRESHOLD_LOG10: return "Weak"
    elif guesses_log10 < STRONG_THRESHOLD_LOG10: return "Fair"
    return "Strong"

def words_to_add_for_strong(guesses_log10: float) -> int:
    if guesses_log10 >= STRONG_THRESHOLD_LOG10: return 0
    gap = STRONG_THRESHOLD_LOG10 - guesses_log10
    return max(1, math.ceil(gap / LOG10_7776))

def split_affixes(password: str):
    """Split the lowercased, transliterated password into (prefix, base, suffix) at the
    first and last letter. Prefix and suffix hold the digits and symbols a canonical form
    discards, so an estimate that uses the stripped base must still pay for them."""
    text = unicodedata.normalize("NFKC", password)
    if has_devanagari(text):
        text = transliterate_devanagari(text, get_script())
    m = re.match(r"^([^a-z]*)(.*?)([^a-z]*)$", text.lower(), re.S)
    return m.group(1), m.group(2), m.group(3)


def calculate_transformations(original: str, canonical: str, affix_charged: bool = False) -> int:
    k = 0
    if not original or not canonical: return 1
    if any('\u0900' <= c <= '\u097F' for c in original): k += 1
    if any(c.isupper() for c in original): k += 1
    leet_chars = set("@013$574")
    if any(c in leet_chars for c in original): k += 1
    if not affix_charged and (not original[0].isalpha() or not original[-1].isalpha()): k += 1
    if canonical not in original.lower(): k += 1
    return max(1, k)

def estimate(password: str, context: Optional[List[str]] = None,
             use_canon: bool = True, use_pack: bool = True) -> Dict[str, Any]:
    # use_canon / use_pack exist only for the ablations in eval/accuracy.py
    if not HAS_ZXCVBN:
        raise RuntimeError("zxcvbn library is required for Taala estimation.")

    pack_words = get_words()
    user_inputs = (context or []) + (get_ranked_words() if use_pack else [])
    
    orig_result = zxcvbn.zxcvbn(password, user_inputs=user_inputs)
    min_guesses_log10 = orig_result.get('guesses_log10', 0.0)
    best_sequence = orig_result.get('sequence', [])
    best_guesses_raw = orig_result.get('guesses', 1)
    
    forms = generate_canonical_forms(password) if use_canon else []

    # A canonical form built from the stripped base scores only the letters. Charge for the
    # prefix/suffix it threw away, or "mxpqzr83921" would be rated as just "mxpqzr".
    prefix, base, suffix = split_affixes(password)
    stripped = set(generate_canonical_forms(base)) if (use_canon and base and (prefix or suffix)) else set()
    affix_log10 = sum(
        zxcvbn.zxcvbn(a, user_inputs=user_inputs).get('guesses_log10', 0.0) for a in (prefix, suffix) if a
    )

    for form in forms:
        if form == password or form == password.lower(): continue

        charged = form in stripped
        k = calculate_transformations(password, form, affix_charged=charged)
        form_result = zxcvbn.zxcvbn(form, user_inputs=user_inputs)
        form_log10 = form_result.get('guesses_log10', 0.0)

        penalized_log10 = form_log10 + (k * LOG10_2) + (affix_log10 if charged else 0.0)
        
        if penalized_log10 < min_guesses_log10:
            min_guesses_log10 = penalized_log10
            best_sequence = form_result.get('sequence', [])
            best_guesses_raw = 10 ** penalized_log10

    band = get_band(min_guesses_log10)
    words_to_add = words_to_add_for_strong(min_guesses_log10)
    
    # Generate the leak-safe attack recipe
    recipe = build_recipe(best_sequence, pack_words)
    
    reasons = []
    if min_guesses_log10 < FAIR_THRESHOLD_LOG10: reasons.append("too_weak")
    if any(step['step'] == 'common_indian_word_or_name' for step in recipe): 
        reasons.append("common_word_variant")
        
    return {
        "guesses_log10": round(min_guesses_log10, 2),
        "guesses": int(best_guesses_raw),
        "band": band,
        "words_to_add": words_to_add,
        "reasons": reasons,
        "recipe": recipe,
        "canonical_forms": forms 
    }