"""Pack Quality Gates — automated CI gate for locale pack degradation (N4).

Architecture §4.3: Quality gates.
Paper Novelty N4: Tested locale packs — a bad pack cannot ship.

This suite reads the numeric thresholds defined in ``locales/hi-latn/pack.toml``
under the ``[gates]`` section and validates them against the **sealed test half**
of the variant dataset (``data/variants/``).  If a future code change drops the
merge rate below the declared minimum, this test fails the build.

Gate definitions (from pack.toml [gates]):
  merge_rate_min             — Fraction of same-word spelling pairs collapsed to
                               the same canonical form (higher is better).
  false_merge_rate_max       — Fraction of different words that collide onto the
                               same canonical form (lower is better).
  english_collision_rate_max — Fraction of English words that collide with a
                               Hinglish canonical form (lower is better).
  cross_script_merge_rate_min — Fraction of (Devanagari, Latin) pairs for the
                               same word that are merged (higher is better).

The thresholds in pack.toml are currently placeholder values (0.0/1.0).
This test still validates the *structure* of the measurement pipeline and will
fail immediately if any threshold is violated once real values are set in P3.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Set

import pytest

ROOT = Path(__file__).resolve().parents[1]
VARIANTS_DIR  = ROOT / "data" / "variants"
SURVEY_DIR    = ROOT / "survey"
PACK_TOML     = ROOT / "locales" / "hi-latn" / "pack.toml"
RULES_TSV     = ROOT / "locales" / "hi-latn" / "rules.tsv"
SCRIPT_TSV    = ROOT / "locales" / "hi-latn" / "script.tsv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _load_gates() -> Dict[str, float]:
    """Read [gates] thresholds from pack.toml without a full TOML parser."""
    text = PACK_TOML.read_text(encoding="utf-8")
    gates: Dict[str, float] = {}
    in_gates = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[gates]":
            in_gates = True
            continue
        if in_gates:
            if stripped.startswith("["):
                break  # moved to a new section
            m = re.match(r'^(\w+)\s*=\s*([\d.]+)', stripped)
            if m:
                gates[m.group(1)] = float(m.group(2))
    return gates


def _load_rules() -> List[Tuple[str, str]]:
    if not RULES_TSV.exists():
        return []
    rows = _read_tsv(RULES_TSV)
    return [(r["pattern"], r["replacement"]) for r in rows
            if r.get("pattern") and r.get("replacement") is not None]


def _apply_rules(s: str, rules: List[Tuple[str, str]]) -> str:
    prev = None
    curr = s.lower()
    while prev != curr:
        prev = curr
        for old, new in rules:
            curr = curr.replace(old, new)
    return re.sub(r'(.)\1+', r'\1', curr)


def _load_script_map() -> Dict[str, str]:
    if not SCRIPT_TSV.exists():
        return {}
    script = {}
    for row in _read_tsv(SCRIPT_TSV):
        script[row["devanagari"]] = row["latin"]
    return script


def _transliterate(text: str, script_map: Dict[str, str]) -> str:
    from taala.canon import transliterate_devanagari
    return transliterate_devanagari(text, script_map)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gates() -> Dict[str, float]:
    return _load_gates()


@pytest.fixture(scope="module")
def rules() -> List[Tuple[str, str]]:
    return _load_rules()


@pytest.fixture(scope="module")
def script_map() -> Dict[str, str]:
    return _load_script_map()


@pytest.fixture(scope="module")
def test_split_ids() -> Set[str]:
    """IDs of words assigned to the test half of the survey split."""
    split_path = SURVEY_DIR / "split.tsv"
    if not split_path.exists():
        pytest.skip("survey/split.tsv not found — run tools/freeze_wordlist.py first")
    rows = _read_tsv(split_path)
    return {r["id"] for r in rows if r["split"] == "test"}


@pytest.fixture(scope="module")
def test_variants(test_split_ids: Set[str]) -> Dict[str, List[str]]:
    """Mapping word_id → [spellings] restricted to the test half."""
    variants: Dict[str, List[str]] = defaultdict(list)
    for filename in ("constructed.tsv", "wild.tsv"):
        path = VARIANTS_DIR / filename
        if not path.exists():
            continue
        for row in _read_tsv(path):
            wid = row["word_id"]
            if wid in test_split_ids:
                variants[wid].append(row["spelling"])
    if not variants:
        pytest.skip("No test-split variant data found — run data collection first")
    return dict(variants)


@pytest.fixture(scope="module")
def ref_latin_map() -> Dict[str, str]:
    """word_id → ref_latin from words.tsv."""
    words_path = SURVEY_DIR / "words.tsv"
    if not words_path.exists():
        pytest.skip("survey/words.tsv not found")
    return {r["id"]: r["ref_latin"] for r in _read_tsv(words_path)}


@pytest.fixture(scope="module")
def ref_devanagari_map() -> Dict[str, str]:
    """word_id → ref_devanagari from words.tsv (may be empty if column absent)."""
    words_path = SURVEY_DIR / "words.tsv"
    if not words_path.exists():
        pytest.skip("survey/words.tsv not found")
    rows = _read_tsv(words_path)
    return {r["id"]: r.get("ref_devanagari", "") for r in rows}


# ---------------------------------------------------------------------------
# Gate 1: Merge Rate
# ---------------------------------------------------------------------------

def _compute_merge_rate(
    variants: Dict[str, List[str]], rules: List[Tuple[str, str]]
) -> float:
    """Fraction of same-word spelling pairs that canonicalize to the same form."""
    total_pairs = 0
    merged_pairs = 0
    for spellings in variants.values():
        n = len(spellings)
        if n < 2:
            continue
        total_pairs += n * (n - 1) // 2
        counts: Dict[str, int] = defaultdict(int)
        for s in spellings:
            counts[_apply_rules(s, rules)] += 1
        merged_pairs += sum(c * (c - 1) // 2 for c in counts.values())
    return merged_pairs / total_pairs if total_pairs > 0 else 0.0


class TestMergeRateGate:
    """N4: A pack that cannot merge spelling variants cannot ship."""

    def test_merge_rate_above_minimum(self, gates, test_variants, rules):
        """
        Architecture §4.3 (N4): merge_rate_min gate.
        This test will fail the build if canonicalization degrades.
        """
        min_rate = gates.get("merge_rate_min", 0.0)
        actual = _compute_merge_rate(test_variants, rules)
        assert actual >= min_rate, (
            f"Pack merge rate {actual:.3f} is below the declared minimum "
            f"{min_rate:.3f}. A code change degraded canonicalization. "
            f"Fix the rules in locales/hi-latn/rules.tsv or update the threshold."
        )

    def test_merge_rate_is_measurable(self, test_variants, rules):
        """Basic sanity: we must have pairs to measure against."""
        pairs = sum(
            len(spellings) * (len(spellings) - 1) // 2
            for spellings in test_variants.values()
            if len(spellings) >= 2
        )
        assert pairs > 0, (
            "No multi-spelling words found in the test half. "
            "The variant dataset may be empty or improperly split."
        )


# ---------------------------------------------------------------------------
# Gate 2: False Merge Rate
# ---------------------------------------------------------------------------

def _compute_false_merge_rate(
    variants: Dict[str, List[str]], rules: List[Tuple[str, str]]
) -> float:
    """Fraction of different words that collide onto the same canonical form."""
    canon_to_words: Dict[str, Set[str]] = defaultdict(set)
    for wid, spellings in variants.items():
        for s in spellings:
            canon_to_words[_apply_rules(s, rules)].add(wid)
    false_merges = sum(1 for wids in canon_to_words.values() if len(wids) > 1)
    return false_merges / len(variants) if variants else 0.0


class TestFalseMergeRateGate:
    """N4: A pack with too many false merges cannot ship."""

    def test_false_merge_rate_below_maximum(self, gates, test_variants, rules):
        """
        Architecture §4.3 (N4): false_merge_rate_max gate.
        This test will fail if the canonicalizer starts collapsing unrelated words.
        """
        max_rate = gates.get("false_merge_rate_max", 1.0)
        actual = _compute_false_merge_rate(test_variants, rules)
        assert actual <= max_rate, (
            f"Pack false merge rate {actual:.3f} exceeds the declared maximum "
            f"{max_rate:.3f}. Too many different words share a canonical form."
        )


# ---------------------------------------------------------------------------
# Gate 3: English Collision Rate
# ---------------------------------------------------------------------------

def _load_english_words() -> List[str]:
    """Load a minimal set of common English words to probe for collisions."""
    # We use Python's built-in set here; a real deployment would use a corpus.
    # These are the top English words most likely to appear in Indian passwords.
    return [
        "the", "and", "for", "are", "but", "not", "you", "all", "any",
        "can", "had", "her", "was", "one", "our", "out", "day", "get",
        "has", "him", "his", "how", "its", "let", "man", "new", "now",
        "old", "see", "two", "way", "who", "did", "got", "may", "put",
        "say", "she", "too", "use", "love", "life", "time", "work",
        "year", "good", "know", "long", "make", "many", "more", "only",
        "over", "such", "take", "than", "then", "them", "well", "were",
        "what", "your", "come", "give", "here", "just", "look", "most",
        "name", "need", "same", "tell", "very", "also", "back", "call",
        "come", "come", "each", "even", "find", "from", "give", "hand",
        "high", "keep", "kind", "last", "left", "live", "move", "much",
        "must", "next", "open", "part", "play", "point", "read", "real",
        "room", "said", "seem", "show", "side", "some", "soon", "stop",
        "sure", "talk", "tell", "text", "that", "this", "turn", "want",
        "week", "when", "word", "zero",
    ]


def _compute_english_collision_rate(
    variants: Dict[str, List[str]], rules: List[Tuple[str, str]], english: List[str]
) -> float:
    """Fraction of English words that collide with any Hinglish canonical form."""
    hinglish_canons: Set[str] = set()
    for spellings in variants.values():
        for s in spellings:
            hinglish_canons.add(_apply_rules(s, rules))
    collisions = sum(
        1 for w in english if _apply_rules(w, rules) in hinglish_canons
    )
    return collisions / len(english) if english else 0.0


class TestEnglishCollisionRateGate:
    """N4: A pack that conflates English words with Hinglish cannot ship."""

    def test_english_collision_rate_below_maximum(self, gates, test_variants, rules):
        """
        Architecture §4.3 (N4): english_collision_rate_max gate.
        This test will fail if the rules start over-canonicalizing English.
        """
        max_rate = gates.get("english_collision_rate_max", 1.0)
        english = _load_english_words()
        actual = _compute_english_collision_rate(test_variants, rules, english)
        assert actual <= max_rate, (
            f"English collision rate {actual:.3f} exceeds declared maximum "
            f"{max_rate:.3f}. The canonicalization rules are too aggressive."
        )


# ---------------------------------------------------------------------------
# Gate 4: Cross-Script Merge Rate (N2 validation)
# ---------------------------------------------------------------------------

class TestCrossScriptMergeRateGate:
    """N2: Script Independence — Devanagari and Latin forms must merge."""

    def test_cross_script_merge_rate_above_minimum(
        self, gates, ref_latin_map, ref_devanagari_map, rules, script_map
    ):
        """
        Architecture §4.3 (N2 + N4): cross_script_merge_rate_min gate.
        For each word that has both a Devanagari and a Latin reference form,
        the canonicalizer must produce the same canonical form for both.
        """
        min_rate = gates.get("cross_script_merge_rate_min", 0.0)

        pairs_total = 0
        pairs_merged = 0
        for wid, latin in ref_latin_map.items():
            deva = ref_devanagari_map.get(wid, "")
            if not deva or not latin:
                continue
            pairs_total += 1
            canon_latin = _apply_rules(latin, rules)
            try:
                transliterated = _transliterate(deva, script_map)
                canon_deva = _apply_rules(transliterated, rules)
            except Exception:
                continue
            if canon_latin == canon_deva:
                pairs_merged += 1

        if pairs_total == 0:
            pytest.skip(
                "No (Devanagari, Latin) pairs found in survey/words.tsv — "
                "add a ref_devanagari column to enable this gate."
            )

        actual = pairs_merged / pairs_total
        assert actual >= min_rate, (
            f"Cross-script merge rate {actual:.3f} ({pairs_merged}/{pairs_total}) "
            f"is below the declared minimum {min_rate:.3f}. "
            f"Script independence (N2) is degraded."
        )


# ---------------------------------------------------------------------------
# Structural gate: pack.toml must declare all required threshold keys
# ---------------------------------------------------------------------------

class TestPackTomlStructure:
    """The TOML file must declare all gates; missing keys are a build error."""

    REQUIRED_GATE_KEYS = {
        "merge_rate_min",
        "false_merge_rate_max",
        "english_collision_rate_max",
        "cross_script_merge_rate_min",
    }

    def test_all_gate_keys_present(self, gates):
        missing = self.REQUIRED_GATE_KEYS - gates.keys()
        assert not missing, (
            f"pack.toml [gates] section is missing required keys: {sorted(missing)}"
        )

    def test_gate_values_are_in_range(self, gates):
        for key, val in gates.items():
            assert 0.0 <= val <= 1.0, (
                f"Gate '{key}' value {val} is outside [0.0, 1.0]."
            )
