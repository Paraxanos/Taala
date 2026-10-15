"""
Taala Attack Recipe Generator (N5).
Translates zxcvbn's internal sequence into user-friendly, leak-safe categories.
Architecture §3 [8] & §5: NEVER expose the matched token to the user.
"""
import math
from typing import List, Dict, Any, Set
from .pack import get_words

def build_recipe(sequence: List[Dict], pack_words: Set[str] = None) -> List[Dict[str, Any]]:
    """
    Turns zxcvbn's sequence into Taala's attack recipe.
    Returns a list of steps with 'step' (category) and 'guesses_log10'.
    """
    if pack_words is None:
        pack_words = get_words()
        
    recipe = []
    
    # Fallback if zxcvbn found no patterns (e.g., purely random short string)
    if not sequence:
        return [{"step": "brute_force_segment", "guesses_log10": 0.0}]

    for match in sequence:
        pattern = match.get("pattern", "unknown")
        token = match.get("token", "").lower()
        guesses = match.get("guesses", 1)
        guesses_log10 = math.log10(max(1, guesses))
        
        # --- Map zxcvbn patterns to Taala categories ---
        if pattern == "dictionary":
            # Check if it's in our Hinglish pack vs standard English
            if token in pack_words:
                category = "common_indian_word_or_name"
            else:
                category = "common_english_word"
        elif pattern == "date":
            category = "date_or_year"
        elif pattern == "regex" and match.get("regex_name") == "recent_year":
            # zxcvbn categorizes standalone 4-digit years (1900-2019) as regex matches
            category = "date_or_year"
        elif pattern in ("sequence", "repeat", "spatial"):
            category = "keyboard_pattern_or_repeat"
        elif pattern == "bruteforce":
            category = "brute_force_segment"
        else:
            category = "unknown_pattern"
            
        recipe.append({
            "step": category,
            "guesses_log10": round(guesses_log10, 2),
            # LEAK SAFETY: We deliberately DO NOT include 'token' in this dictionary.
            # The UI/CLI must only ever see the category and the guess count.
        })
        
    return recipe

def format_recipe_for_cli(recipe: List[Dict]) -> str:
    """Formats the recipe into a readable string for the terminal."""
    lines = []
    for i, step in enumerate(recipe, 1):
        lines.append(f"  {i}. {step['step'].replace('_', ' ').title()} (~10^{step['guesses_log10']:.1f} guesses)")
    return "\n".join(lines)