"""Taala strength estimator (N1 / E1.2 / E1.3)."""
import math
from typing import List, Optional, Dict, Any

try:
    import zxcvbn
    HAS_ZXCVBN = True
except ImportError:
    HAS_ZXCVBN = False

from .canon import generate_canonical_forms
from .pack import get_words
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

def calculate_transformations(original: str, canonical: str) -> int:
    k = 0
    if not original or not canonical: return 1
    if any('\u0900' <= c <= '\u097F' for c in original): k += 1
    if any(c.isupper() for c in original): k += 1
    leet_chars = set("@013$574")
    if any(c in leet_chars for c in original): k += 1
    if not original[0].isalpha() or not original[-1].isalpha(): k += 1
    if canonical not in original.lower(): k += 1
    return max(1, k)

def estimate(password: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
    if not HAS_ZXCVBN:
        raise RuntimeError("zxcvbn library is required for Taala estimation.")

    pack_words = get_words()
    user_inputs = (context or []) + list(pack_words)
    
    orig_result = zxcvbn.zxcvbn(password, user_inputs=user_inputs)
    min_guesses_log10 = orig_result.get('guesses_log10', 0.0)
    best_sequence = orig_result.get('sequence', [])
    best_guesses_raw = orig_result.get('guesses', 1)
    
    forms = generate_canonical_forms(password)
    for form in forms:
        if form == password or form == password.lower(): continue
            
        k = calculate_transformations(password, form)
        form_result = zxcvbn.zxcvbn(form, user_inputs=user_inputs)
        form_log10 = form_result.get('guesses_log10', 0.0)
        
        penalized_log10 = form_log10 + (k * LOG10_2)
        
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