"""Tests for the 2^k penalty estimator and mathematical fix (Task 1.2 & 1.3)."""
import math
import pytest
from taala.estimate import (
    estimate, 
    words_to_add_for_strong, 
    get_band, 
    calculate_transformations,
    STRONG_THRESHOLD_LOG10,
    LOG10_7776
)

def test_words_to_add_math():
    """Architecture §3 [8]: ceil( log10(10^10 / G) / log10(7776) )"""
    # If guesses = 10^6 (Weak), gap is 4. 4 / 3.89 = 1.02 -> ceil is 2 words.
    assert words_to_add_for_strong(6.0) == 2
    
    # If guesses = 10^8 (Fair), gap is 2. 2 / 3.89 = 0.51 -> ceil is 1 word.
    assert words_to_add_for_strong(8.0) == 1
    
    # If already Strong (10^10), 0 words needed.
    assert words_to_add_for_strong(10.0) == 0
    assert words_to_add_for_strong(12.5) == 0

def test_bands():
    """Architecture §3 [6]: Weak < 10^6, Fair < 10^10, Strong >= 10^10"""
    assert get_band(3.0) == "Weak"
    assert get_band(5.99) == "Weak"
    assert get_band(6.0) == "Fair"
    assert get_band(9.99) == "Fair"
    assert get_band(10.0) == "Strong"
    assert get_band(15.0) == "Strong"

def test_calculate_transformations():
    """Verify 'k' correctly counts the 5 distinct transformation types."""
    # 1. Script (Devanagari)
    assert calculate_transformations("राम123", "ram") >= 1
    
    # 2. Case
    assert calculate_transformations("Password", "password") >= 1
    
    # 3. Leet
    assert calculate_transformations("p@ssword", "password") >= 1
    
    # 4. Padding
    assert calculate_transformations("password1998", "password") >= 1
    
    # 5. Spelling (aa -> a)
    assert calculate_transformations("pyaar", "pyar") >= 1

def test_estimate_returns_correct_structure():
    """Ensure the Result object matches the contract in Architecture §3 [8]."""
    result = estimate("password123")
    
    assert "guesses_log10" in result
    assert "band" in result
    assert "words_to_add" in result
    assert "recipe" in result
    assert isinstance(result["recipe"], list)
    assert "canonical_forms" in result

def test_zxcvbn_integration():
    """Ensure zxcvbn actually runs and produces logical bands."""
    # A very weak password
    weak_res = estimate("123456")
    assert weak_res["band"] == "Weak"
    assert weak_res["words_to_add"] > 0
    
    # A very strong, long random string
    strong_res = estimate("correct-horse-battery-staple-xy7z!")
    assert strong_res["band"] in ("Fair", "Strong")

def test_stripped_affix_is_charged_not_free():
    """Regression: 'mxpqzr83921' was rated as just 'mxpqzr' (6.6 vs stock 10.4) because the
    padding-stripped canonical form dropped the digits for free."""
    import zxcvbn
    from taala.estimate import estimate
    for pw in ("mxpqzr83921", "zebracorn4927"):
        stock = zxcvbn.zxcvbn(pw)["guesses_log10"]
        assert estimate(pw)["guesses_log10"] >= stock - 0.5, pw


def test_scores_do_not_depend_on_hash_seed():
    """Regression: pack words reached zxcvbn in set order, so scores changed per process."""
    import subprocess, sys
    code = "from taala.estimate import estimate; print(estimate('navratri2024')['guesses_log10'])"
    outs = {
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env={**__import__('os').environ, "PYTHONHASHSEED": str(s)}).stdout.strip()
        for s in (1, 2, 3)
    }
    assert len(outs) == 1, outs
