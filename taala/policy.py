"""Taala NIST SP 800-63B-4 policy engine — formal Accept/Reject verdict.

Architecture §3 [7]: Policy verdict.

The engine reads ``policy.toml`` (co-located with this file) and issues a
structured verdict for any password.  It deliberately does NOT reject passwords
for missing an uppercase letter, digit, or symbol — which is a direct critique
of legacy composition rules and a core claim of the Taala paper.

Usage::

    from taala.policy import load_policy, verdict

    policy = load_policy()
    result = verdict("MyPass1234", policy=policy)
    # result["verdict"] == "accept" | "reject"
    # result["reject_reasons"] == []  |  ["too_short", "on_blocklist", ...]
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-reuse-attr]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from .blocklist import check as blocklist_check
from .estimate import estimate, FAIR_THRESHOLD_LOG10

_POLICY_TOML = pathlib.Path(__file__).parent / "policy.toml"


# ---------------------------------------------------------------------------
# Policy loading
# ---------------------------------------------------------------------------

def load_policy(path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """Load and return the policy configuration from ``policy.toml``.

    Args:
        path: Override path to a TOML policy file. Defaults to the bundled
              ``taala/policy.toml``.

    Returns:
        Parsed policy dict (mirrors the TOML structure).

    Raises:
        RuntimeError: If neither ``tomllib`` nor ``tomli`` is available.
        FileNotFoundError: If the TOML file does not exist.
    """
    if tomllib is None:
        raise RuntimeError(
            "A TOML parser is required: install 'tomli' (pip install tomli) "
            "or use Python 3.11+."
        )
    target = path or _POLICY_TOML
    with open(target, "rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# Core verdict logic
# ---------------------------------------------------------------------------

def verdict(
    password: str,
    *,
    policy: Optional[Dict[str, Any]] = None,
    context: Optional[List[str]] = None,
    estimate_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Issue a formal NIST SP 800-63B-4 Accept/Reject verdict.

    Args:
        password:        The candidate password (plaintext).
        policy:          Parsed policy dict from :func:`load_policy`. If *None*,
                         the bundled ``policy.toml`` is loaded automatically.
        context:         Optional list of personal-info tokens (from
                         ``taala.personal.build_context_tokens``).  Used only
                         when ``policy.personal_info.enabled`` is true.
        estimate_result: Pre-computed result from ``taala.estimate.estimate()``.
                         Pass this to avoid a redundant estimation call if you
                         have already called ``estimate()`` for the same password
                         and context.

    Returns:
        Dict with keys:

        - ``verdict``:         ``"accept"`` or ``"reject"``
        - ``reject_reasons``:  List of strings (empty on accept), chosen from:
            - ``"too_short"``       — below the minimum (15 single-factor, 8 multi-factor)
            - ``"too_long"``        — above ``policy.length.max_chars``
            - ``"on_blocklist"``    — canonical form is a known weak password
            - ``"personal_info"``   — password matches a user-profile token
            - ``"too_weak"``        — below ``policy.strength.min_guesses_log10``
        - ``composition_rules_enforced``:  Always ``False`` (NIST §3.1.1.2).
        - ``guesses_log10``:   From the estimator (for informational display).
        - ``band``:            ``"Weak"`` / ``"Fair"`` / ``"Strong"``.

    Notes:
        NIST §3.1.1.2 explicitly states verifiers SHOULD NOT impose composition
        rules.  This engine therefore **never** rejects a password solely for
        missing an uppercase letter, digit, or symbol.
    """
    if policy is None:
        policy = load_policy()

    p = policy["policy"]
    length_cfg   = p.get("length", {})
    blocklist_cfg = p.get("blocklist", {})
    personal_cfg = p.get("personal_info", {})
    strength_cfg = p.get("strength", {})

    if "min_chars" in length_cfg:
        min_chars = length_cfg["min_chars"]
    elif length_cfg.get("authenticator", "single_factor") == "multi_factor":
        min_chars = length_cfg.get("min_chars_multi_factor", 8)
    else:
        min_chars = length_cfg.get("min_chars_single_factor", 15)
    max_chars = length_cfg.get("max_chars", 128)

    # zxcvbn has its own hard cap of 72 characters; cap our policy max accordingly
    # so that the length gate fires *before* the estimator raises ValueError.
    _ZXCVBN_MAX = 72

    reject_reasons: List[str] = []

    # --- Gate 1: Length (NIST §3.1.1.2 requirement) ---------------------
    char_count = len(password)
    if char_count < min_chars:
        reject_reasons.append("too_short")
    if char_count > max_chars:
        reject_reasons.append("too_long")

    # If the password is already rejected for being too long, skip estimation
    # (also handles zxcvbn's own 72-char cap gracefully).
    _skip_estimate = char_count > min(max_chars, _ZXCVBN_MAX)

    # --- Gate 2: Blocklist (NIST §3.1.1.2) ----------------------------
    if blocklist_cfg.get("enabled", True) and not _skip_estimate:
        hits = blocklist_check(password)
        if hits:
            reject_reasons.append("on_blocklist")

    # --- Gate 3: Personal info (NIST §3.1.1.2) ------------------------
    if personal_cfg.get("enabled", True) and context:
        password_lower = password.lower()
        for token in context:
            token_lower = token.lower()
            if len(token_lower) >= 3 and token_lower in password_lower:
                reject_reasons.append("personal_info")
                break

    # --- Gate 4: Strength estimate -----------------------------------------
    min_log10 = strength_cfg.get("min_guesses_log10", FAIR_THRESHOLD_LOG10)
    guesses_log10 = 0.0
    band = "Weak"
    if not _skip_estimate:
        if estimate_result is None:
            estimate_result = estimate(password, context=context)
        guesses_log10 = estimate_result.get("guesses_log10", 0.0)
        band = estimate_result.get("band", "Weak")
        if guesses_log10 < min_log10:
            reject_reasons.append("too_weak")


    return {
        "verdict": "reject" if reject_reasons else "accept",
        "reject_reasons": reject_reasons,
        "composition_rules_enforced": False,  # Always False — NIST §3.1.1.2
        "guesses_log10": guesses_log10,
        "band": band,
    }
