"""Tests for the set-based canonicalizer (Task 1.1)."""
import pytest
from taala.canon import generate_canonical_forms

def test_spelling_variants_merge():
    """Architecture §3 [2] / G2: spelling variants must collapse to a shared form."""
    forms1 = generate_canonical_forms("pyaar4ever")
    forms2 = generate_canonical_forms("Pyar4ever")
    forms3 = generate_canonical_forms("pyaaar4ever")
    
    # They should all share at least one canonical form (e.g., "pyar4ever")
    shared = set(forms1) & set(forms2) & set(forms3)
    assert len(shared) > 0, f"No shared form between {forms1}, {forms2}, {forms3}"

def test_leetspeak_branching():
    """Leetspeak should branch but respect the 8-form cap and collapse repeats."""
    forms = generate_canonical_forms("p@ssw0rd")
    # "password" becomes "pasword" after step 6 (collapse_repeats)
    assert "pasword" in forms, f"Expected 'pasword' in {forms}"
    assert len(forms) <= 8, f"Exceeded 8-form cap: {forms}"

def test_padding_split():
    """Padding should be peeled to reveal the base word."""
    forms = generate_canonical_forms("priyanka@1998")
    # The base word "priyanka" should be isolated
    assert "priyanka" in forms, f"Expected 'priyanka' in {forms}"

def test_devanagari_transliteration():
    """Devanagari should map to Latin and drop final inherent 'a'."""
    forms = generate_canonical_forms("राम")
    assert "ram" in forms, f"Expected 'ram' in {forms}"
    
def test_max_forms_cap():
    """The pipeline must never return more than 8 forms."""
    # A string with many leetspeak options (1 can be i or l)
    forms = generate_canonical_forms("1111111111")
    assert len(forms) <= 8, f"Exceeded 8-form cap: {forms}"

def test_nfk_normalization():
    """NFKC normalization should handle full-width characters."""
    # Full-width 'ｐａｓｓｗｏｒｄ' -> 'password' -> 'pasword' (due to repeat collapse)
    forms = generate_canonical_forms("ｐａｓｓｗｏｒｄ")
    assert "pasword" in forms, f"Expected 'pasword' in {forms}"

def test_repeated_letter_collapse():
    """Repeated letters should be collapsed."""
    # Note: We use 'passsword' instead of 'bookkeeper'. 
    # 'bookkeeper' contains 'oo' and 'ee', which the Hinglish locale rules 
    # rewrite to 'u' and 'i' (resulting in 'bukiper'). This is a known 
    # "English collision" that Architecture §4.2 explicitly measures!
    forms = generate_canonical_forms("passsword")
    assert "pasword" in forms, f"Expected 'pasword' in {forms}"

def test_locale_rules_application():
    """Locale rules should be applied iteratively."""
    # Assuming 'aa' -> 'a' is in the default LOCALE_RULES
    forms = generate_canonical_forms("pyaar")
    assert "pyar" in forms, f"Expected 'pyar' in {forms}"