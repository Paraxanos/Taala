"""Tests for taala.policy — NIST SP 800-63B-4 Policy Engine.

Architecture §3 [7]: Policy verdict.
Paper claim: Taala NEVER rejects a password for missing an uppercase letter,
digit, or symbol (direct critique of legacy composition rules).
"""
import pytest
from taala.policy import load_policy, verdict


@pytest.fixture(scope="module")
def policy():
    return load_policy()


# ---------------------------------------------------------------------------
# Core accept / reject paths
# ---------------------------------------------------------------------------

class TestVerdictStructure:
    def test_verdict_has_required_keys(self, policy):
        result = verdict("CorrectHorseBatteryStaple!", policy=policy)
        assert "verdict" in result
        assert "reject_reasons" in result
        assert "composition_rules_enforced" in result
        assert "guesses_log10" in result
        assert "band" in result

    def test_composition_rules_always_false(self, policy):
        """NIST §3.1.1.2: composition rules MUST NOT be enforced."""
        result = verdict("alllowercasepassword", policy=policy)
        assert result["composition_rules_enforced"] is False


class TestLengthGate:
    def test_too_short_rejected(self, policy):
        result = verdict("abc", policy=policy)
        assert result["verdict"] == "reject"
        assert "too_short" in result["reject_reasons"]

    def test_exactly_min_length_not_too_short(self, policy):
        """Exactly 15 chars (single-factor minimum) should not trigger 'too_short'."""
        result = verdict("abcdefghijklmno", policy=policy)
        assert "too_short" not in result["reject_reasons"]

    def test_single_factor_rejects_14(self, policy):
        assert "too_short" in verdict("abcdefghijklmn", policy=policy)["reject_reasons"]

    def test_multi_factor_profile_allows_8(self, policy):
        mfa = {"policy": {**policy["policy"], "length": {"authenticator": "multi_factor"}}}
        assert "too_short" not in verdict("abcdefgh", policy=mfa)["reject_reasons"]
        assert "too_short" in verdict("abcdefg", policy=mfa)["reject_reasons"]

    def test_too_long_rejected(self, policy):
        """Passwords over 128 chars should be rejected."""
        long_pw = "a" * 129
        result = verdict(long_pw, policy=policy)
        assert result["verdict"] == "reject"
        assert "too_long" in result["reject_reasons"]


class TestBlocklistGate:
    def test_common_password_rejected(self, policy):
        result = verdict("password", policy=policy)
        assert result["verdict"] == "reject"
        assert "on_blocklist" in result["reject_reasons"]

    def test_123456_rejected(self, policy):
        result = verdict("123456", policy=policy)
        assert "on_blocklist" in result["reject_reasons"]


class TestPersonalInfoGate:
    def test_name_in_password_rejected(self, policy):
        context = ["priya", "sharma"]
        result = verdict("PriyaPassword1", policy=policy, context=context)
        assert result["verdict"] == "reject"
        assert "personal_info" in result["reject_reasons"]

    def test_no_context_no_personal_reject(self, policy):
        """Without context tokens, personal_info gate must not fire."""
        result = verdict("PriyaPassword1", policy=policy, context=None)
        assert "personal_info" not in result["reject_reasons"]

    def test_short_tokens_not_matched(self, policy):
        """Tokens shorter than 3 chars must not trigger the gate (too many false positives)."""
        context = ["ab"]
        result = verdict("ab" * 10 + "xyz", policy=policy, context=context)
        assert "personal_info" not in result["reject_reasons"]


# ---------------------------------------------------------------------------
# The critical paper claim: composition rules are NEVER enforced
# ---------------------------------------------------------------------------

class TestNISTCompositionCritique:
    """
    Architecture §3 [7] / Paper §4.2:
    Taala issues a verdict of 'accept' for passwords that are long and random
    even if they have no uppercase, no digits, and no symbols.
    """

    def test_password_never_rejected_for_missing_uppercase(self, policy):
        """A long, lowercase-only password must NOT be rejected for missing uppercase."""
        pw = "alllowercaselongpasswordisvalid"
        result = verdict(pw, policy=policy)
        assert "missing_uppercase" not in result["reject_reasons"]
        assert result["composition_rules_enforced"] is False

    def test_password_never_rejected_for_missing_digit(self, policy):
        """A long password with only letters must NOT be rejected for missing a digit."""
        pw = "correcthorsebatterystaple"
        result = verdict(pw, policy=policy)
        assert "missing_digit" not in result["reject_reasons"]
        assert result["composition_rules_enforced"] is False

    def test_password_never_rejected_for_missing_symbol(self, policy):
        """A password without any symbol must NOT be rejected for that reason."""
        pw = "NoSymbolsHereAtAll12345678"
        result = verdict(pw, policy=policy)
        assert "missing_symbol" not in result["reject_reasons"]
        assert result["composition_rules_enforced"] is False

    def test_strong_lowercase_only_accepted(self, policy):
        """A cryptographically strong but lowercase-only passphrase must be accepted."""
        pw = "correct-horse-battery-staple-xyzabc"
        result = verdict(pw, policy=policy)
        # Should be accepted — strong enough, not on blocklist, no composition gate
        assert result["verdict"] == "accept", (
            f"Expected 'accept' for strong lowercase passphrase. Got: {result}"
        )


# ---------------------------------------------------------------------------
# Pre-computed estimate_result shortcircuit
# ---------------------------------------------------------------------------

class TestEstimateResultReuse:
    def test_precomputed_estimate_is_used(self, policy):
        """Passing estimate_result avoids a redundant zxcvbn call."""
        from taala.estimate import estimate as taala_estimate
        pw = "correct-horse-battery-staple"
        est = taala_estimate(pw)
        result = verdict(pw, policy=policy, estimate_result=est)
        assert result["guesses_log10"] == est["guesses_log10"]
        assert result["band"] == est["band"]
