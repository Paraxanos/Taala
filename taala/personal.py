"""Taala personal info matcher — Script Independence for profile data (N2).

Converts a user's profile (name, DOB, mobile, email) into a comprehensive list
of context tokens in *both* scripts, so that zxcvbn can flag passwords that are
derived from personal information even when the profile is stored in Devanagari.

Architecture §3 [4]: Personal info check.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Sequence

from .canon import transliterate_devanagari, generate_canonical_forms
from .pack import get_script


# ---------------------------------------------------------------------------
# DOB variant generation
# ---------------------------------------------------------------------------

def _parse_dob(dob: str) -> Optional[Dict[str, str]]:
    """Parse a date string in common formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY."""
    dob = dob.strip()
    patterns = [
        r'^(?P<y>\d{4})[.\-/](?P<m>\d{1,2})[.\-/](?P<d>\d{1,2})$',  # YYYY-MM-DD
        r'^(?P<d>\d{1,2})[.\-/](?P<m>\d{1,2})[.\-/](?P<y>\d{4})$',  # DD/MM/YYYY
    ]
    for pat in patterns:
        m = re.match(pat, dob)
        if m:
            return m.groupdict()
    return None


def dob_tokens(dob: str) -> List[str]:
    """Generate common password-relevant substrings from a date of birth."""
    parts = _parse_dob(dob)
    if not parts:
        # Fallback: just strip punctuation and return raw substrings
        digits = re.sub(r'\D', '', dob)
        tokens: List[str] = [digits]
        for length in (2, 4):
            for start in range(len(digits) - length + 1):
                tokens.append(digits[start:start + length])
        return list(dict.fromkeys(t for t in tokens if t))

    y, m, d = parts['y'], parts['m'].zfill(2), parts['d'].zfill(2)
    yy = y[2:]  # last two digits of year

    tokens = [
        y, yy,                   # full year, short year: 1998, 98
        m, d,                    # zero-padded month/day: 04, 02
        m.lstrip('0') or '0',    # unpadded month: 4
        d.lstrip('0') or '0',    # unpadded day: 2
        d + m,                   # DDMM: 0204
        m + d,                   # MMDD: 0402
        d + m + yy,              # DDMMy2: 020498
        m + d + yy,              # MMDDy2: 040298
        d + m + y,               # DDMMy4: 02041998
        m + d + y,               # MMDDy4: 04021998
        y + m + d,               # YYYYMMdd: 19980402
        yy + m + d,              # yyMMDD: 980402
    ]
    return list(dict.fromkeys(t for t in tokens if t))


# ---------------------------------------------------------------------------
# Name variant generation
# ---------------------------------------------------------------------------

def _devanagari_to_latin(text: str) -> str:
    """Transliterate Devanagari text to Latin using the loaded script map."""
    script_map = get_script()
    return transliterate_devanagari(text, script_map)


# Common transliteration alternates for terminal vowel sounds used in Hindi names
_TERMINAL_ALTERNATES = {
    "aa": "a", "a": "aa",
    "ee": "i", "i": "ee",
    "oo": "u", "u": "oo",
    "ia": "ya", "ya": "ia",
    "sha": "sha", "shri": "sri",
}


def name_tokens(name: str) -> List[str]:
    """Generate canonical password-relevant tokens from a name.

    Handles Devanagari → Latin transliteration, common spelling alternates,
    and all canonical forms that ``generate_canonical_forms`` would produce.
    """
    name = name.strip()
    seeds: List[str] = [name]

    # If Devanagari, also generate Latin form
    if any('\u0900' <= c <= '\u097F' for c in name):
        seeds.append(_devanagari_to_latin(name))

    tokens: List[str] = []
    for seed in seeds:
        # Expand canonical forms (handles leet, padding, locale rules)
        for form in generate_canonical_forms(seed):
            tokens.append(form)

        # Also add lowercased original so zxcvbn context matching is wider
        tokens.append(seed.lower())

        # Split on spaces / hyphens to get first/last name parts individually
        for part in re.split(r'[\s\-]+', seed):
            part_lower = part.lower()
            if part_lower:
                tokens.append(part_lower)
                for form in generate_canonical_forms(part):
                    tokens.append(form)

    # Add simple terminal-vowel alternates (e.g. priya → priyaa, ram → rama)
    extra: List[str] = []
    for token in tokens:
        for suffix, alt_suffix in _TERMINAL_ALTERNATES.items():
            if token.endswith(suffix):
                extra.append(token[: -len(suffix)] + alt_suffix)
    tokens.extend(extra)

    return list(dict.fromkeys(t for t in tokens if len(t) >= 2))


# ---------------------------------------------------------------------------
# Mobile / phone number variants
# ---------------------------------------------------------------------------

def mobile_tokens(mobile: str) -> List[str]:
    """Generate password substrings from a mobile number."""
    digits = re.sub(r'\D', '', mobile)
    tokens: List[str] = [digits]

    # Strip common country-code prefixes
    for prefix in ('91', '0', '1'):
        if digits.startswith(prefix) and len(digits) > len(prefix) + 6:
            stripped = digits[len(prefix):]
            tokens.append(stripped)
            digits = stripped  # use stripped as base for substrings
            break

    # Common sub-sequences attackers try: last 4, last 6, first 4
    for start, end in [(0, 4), (0, 6), (-4, None), (-6, None)]:
        chunk = digits[start:end]
        if chunk:
            tokens.append(chunk)

    return list(dict.fromkeys(t for t in tokens if t))


# ---------------------------------------------------------------------------
# Email variants
# ---------------------------------------------------------------------------

def email_tokens(email: str) -> List[str]:
    """Extract the local-part of an email and generate its canonical forms."""
    email = email.strip().lower()
    local = email.split('@')[0]
    tokens: List[str] = [local]
    # Split on common separators used in email local-parts
    for part in re.split(r'[.\-_]+', local):
        if part:
            tokens.append(part)
            for form in generate_canonical_forms(part):
                tokens.append(form)
    return list(dict.fromkeys(t for t in tokens if len(t) >= 2))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_context_tokens(
    *,
    name: Optional[str] = None,
    dob: Optional[str] = None,
    mobile: Optional[str] = None,
    email: Optional[str] = None,
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """Build a deduplicated list of context tokens from a user's profile.

    Pass any subset of the keyword arguments. All tokens are suitable for
    passing directly as ``user_inputs`` to ``zxcvbn``.

    Args:
        name:   Full name (Latin or Devanagari). E.g. ``"प्रिया"`` or ``"Priya Sharma"``.
        dob:    Date of birth. Supported formats: ``YYYY-MM-DD``, ``DD/MM/YYYY``.
        mobile: Mobile number with or without country code. Digits and hyphens OK.
        email:  Email address; local-part is tokenized.
        extra:  Any additional raw strings (e.g. username, pet name).

    Returns:
        Deduplicated list of lowercase string tokens.

    Example::

        from taala.personal import build_context_tokens
        tokens = build_context_tokens(
            name="प्रिया",
            dob="1998-04-02",
            mobile="9876543210",
        )
        # tokens includes: "priya", "priyaa", "98", "0402", "9876543210", ...
    """
    tokens: List[str] = []

    if name:
        tokens.extend(name_tokens(name))
    if dob:
        tokens.extend(dob_tokens(dob))
    if mobile:
        tokens.extend(mobile_tokens(mobile))
    if email:
        tokens.extend(email_tokens(email))
    if extra:
        for item in extra:
            if item:
                tokens.append(item.lower())
                for form in generate_canonical_forms(item):
                    tokens.append(form)

    # Return deduplicated, non-empty, lowercase tokens
    seen: Dict[str, None] = {}
    result: List[str] = []
    for t in tokens:
        t = t.lower()
        if t and t not in seen:
            seen[t] = None
            result.append(t)
    return result
