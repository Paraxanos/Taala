"""Tests for taala.personal — Script-Independent Personal Info Matcher (N2).

Architecture §3 [4]: Personal info check.
Paper claim: Taala catches Pr1ya@98 even if the user's profile is stored in
Devanagari on the server.
"""
import pytest
from taala.personal import (
    build_context_tokens,
    dob_tokens,
    name_tokens,
    mobile_tokens,
    email_tokens,
)


# ---------------------------------------------------------------------------
# DOB tokens
# ---------------------------------------------------------------------------

class TestDobTokens:
    def test_iso_format(self):
        tokens = dob_tokens("1998-04-02")
        assert "1998" in tokens
        assert "98" in tokens
        assert "04" in tokens
        assert "02" in tokens

    def test_dmy_format(self):
        tokens = dob_tokens("02/04/1998")
        assert "1998" in tokens
        assert "98" in tokens

    def test_ddmm_variant(self):
        tokens = dob_tokens("1998-04-02")
        assert "0204" in tokens  # DDMM

    def test_mmdd_variant(self):
        tokens = dob_tokens("1998-04-02")
        assert "0402" in tokens  # MMDD

    def test_full_variants(self):
        tokens = dob_tokens("1998-04-02")
        assert "02041998" in tokens   # DDMMy4
        assert "04021998" in tokens   # MMDDy4

    def test_year_short(self):
        tokens = dob_tokens("1998-04-02")
        assert "98" in tokens

    def test_no_duplicates(self):
        tokens = dob_tokens("2000-01-01")
        assert len(tokens) == len(set(tokens))


# ---------------------------------------------------------------------------
# Name tokens — Latin
# ---------------------------------------------------------------------------

class TestNameTokensLatin:
    def test_lowercase_included(self):
        tokens = name_tokens("Priya")
        assert "priya" in tokens

    def test_terminal_vowel_alternate(self):
        tokens = name_tokens("Priya")
        # priya → priyaa alternate
        assert "priyaa" in tokens

    def test_split_first_last(self):
        tokens = name_tokens("Priya Sharma")
        assert "priya" in tokens
        assert "sharma" in tokens

    def test_hyphenated_name(self):
        tokens = name_tokens("Ravi-Kumar")
        assert "ravi" in tokens
        assert "kumar" in tokens


# ---------------------------------------------------------------------------
# Name tokens — Devanagari (Script Independence N2)
# ---------------------------------------------------------------------------

class TestNameTokensDevanagari:
    def test_devanagari_name_produces_latin(self):
        """प्रिया must produce 'priya' or close transliteration."""
        tokens = name_tokens("प्रिया")
        # At least one Latin token should be present
        latin_tokens = [t for t in tokens if all(ord(c) < 128 for c in t)]
        assert len(latin_tokens) > 0, f"No Latin tokens from Devanagari name. Got: {tokens}"

    def test_ram_devanagari(self):
        """राम → 'ram' (final inherent 'a' deleted per N2)."""
        tokens = name_tokens("राम")
        assert "ram" in tokens, f"Expected 'ram' in tokens, got: {tokens}"

    def test_devanagari_catches_leetspeak_variant(self):
        """
        Paper claim: Taala catches Pr1ya@98 even if profile stored in Devanagari.
        This test verifies that the Devanagari name प्रिया expands to 'priya',
        which when used as context lets zxcvbn detect 'pr1ya'.
        """
        from taala.estimate import estimate
        tokens = build_context_tokens(name="प्रिया", dob="1998-04-02")
        # 'priya' must be in context so zxcvbn can match 'pr1ya'
        assert "priya" in tokens
        # '98' must be in context so zxcvbn can match the year component
        assert "98" in tokens


# ---------------------------------------------------------------------------
# Mobile tokens
# ---------------------------------------------------------------------------

class TestMobileTokens:
    def test_raw_digits(self):
        tokens = mobile_tokens("9876543210")
        assert "9876543210" in tokens

    def test_strips_country_code_91(self):
        tokens = mobile_tokens("+919876543210")
        assert "9876543210" in tokens

    def test_last_four(self):
        tokens = mobile_tokens("9876543210")
        assert "3210" in tokens

    def test_no_duplicates(self):
        tokens = mobile_tokens("9999999999")
        assert len(tokens) == len(set(tokens))


# ---------------------------------------------------------------------------
# Email tokens
# ---------------------------------------------------------------------------

class TestEmailTokens:
    def test_local_part_extracted(self):
        tokens = email_tokens("priya.sharma@gmail.com")
        assert "priya" in tokens
        assert "sharma" in tokens

    def test_local_part_whole(self):
        tokens = email_tokens("priya.sharma@gmail.com")
        assert "priya.sharma" in tokens

    def test_underscore_split(self):
        tokens = email_tokens("priya_sharma@outlook.com")
        assert "priya" in tokens
        assert "sharma" in tokens


# ---------------------------------------------------------------------------
# build_context_tokens (integration)
# ---------------------------------------------------------------------------

class TestBuildContextTokens:
    def test_combined_profile(self):
        tokens = build_context_tokens(
            name="Priya Sharma",
            dob="1998-04-02",
            mobile="9876543210",
        )
        assert "priya" in tokens
        assert "sharma" in tokens
        assert "98" in tokens
        assert "0402" in tokens
        assert "9876543210" in tokens

    def test_devanagari_profile(self):
        tokens = build_context_tokens(
            name="प्रिया",
            dob="1998-04-02",
        )
        # Latin transliteration must appear
        latin = [t for t in tokens if all(ord(c) < 128 for c in t)]
        assert len(latin) > 0
        assert "98" in tokens

    def test_no_duplicates_in_output(self):
        tokens = build_context_tokens(
            name="Ram Ram",
            dob="2000-01-01",
        )
        assert len(tokens) == len(set(tokens))

    def test_email_integration(self):
        tokens = build_context_tokens(email="priya@example.com")
        assert "priya" in tokens

    def test_extra_tokens(self):
        tokens = build_context_tokens(extra=["fluffy", "tiger"])
        assert "fluffy" in tokens
        assert "tiger" in tokens

    def test_empty_call_returns_empty(self):
        tokens = build_context_tokens()
        assert tokens == []
