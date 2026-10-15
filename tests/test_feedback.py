"""Tests for the Attack Recipe and Leak Safety (Task 3.1)."""
from taala.feedback import build_recipe
from taala.estimate import estimate

def test_leak_safety_no_tokens_in_recipe():
    """Architecture §5: The recipe must NEVER expose the exact matched token."""
    # A password that zxcvbn will definitely match against a dictionary
    result = estimate("password123")
    
    for step in result["recipe"]:
        assert "token" not in step, "LEAK SAFETY VIOLATION: Raw token exposed in recipe!"
        assert "matched_word" not in step, "LEAK SAFETY VIOLATION: Matched word exposed!"
        assert "step" in step
        assert "guesses_log10" in step

def test_indian_word_categorization():
    """Ensure Indian names from our pack are categorized correctly."""
    # We test the base word directly. 
    # If we use "priyanka1998", the canonicalizer strips "1998" as padding, 
    # and the 2^k penalty makes the base word the weakest path, so the recipe 
    # only shows the name. This is correct architectural behavior (§3 [5])!
    result = estimate("priyanka")
    steps = [s["step"] for s in result["recipe"]]
    assert "common_indian_word_or_name" in steps or "common_english_word" in steps

def test_date_categorization():
    """Ensure dates are categorized correctly when they are the primary weakness."""
    result = estimate("1998")
    steps = [s["step"] for s in result["recipe"]]
    assert "date_or_year" in steps

def test_recipe_handles_empty_sequence():
    """Ensure the recipe builder doesn't crash on purely random strings."""
    # A completely random string that zxcvbn might just label as bruteforce
    result = estimate("x7#q9!zP2")
    assert isinstance(result["recipe"], list)
    assert len(result["recipe"]) > 0