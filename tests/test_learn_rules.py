"""The rule learner must stay train-only, directed and unable to mangle ordinary words."""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lr", ROOT / "tools" / "learn_rules.py")
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)


def test_learner_sees_train_words_only():
    variants, train = lr.load_train()
    with open(ROOT / "survey" / "split.tsv", encoding="utf-8") as f:
        test = {r["id"] for r in csv.DictReader(f, delimiter="\t") if r["split"] == "test"}
    assert set(variants) <= train and not (set(variants) & test)


def test_rules_are_directed_toward_the_shorter_form():
    assert lr.directed("ee", "i") == ("ee", "i")
    assert lr.directed("i", "ee") == ("ee", "i")
    assert lr.directed("w", "v") == lr.directed("v", "w")


def test_support_counts_distinct_words_not_occurrences():
    # one word with many spellings must not satisfy min_words=2 by itself
    v = {"w1": {"chaudhary", "choudhary", "chowdhary", "chaudhari"}}
    assert lr.extract_candidates(v, min_words=2) == {}


def test_canon_is_stable_and_terminates():
    rules = [("va", "w"), ("w", "v")]
    once = lr.canon("wawa", rules)
    assert lr.canon(once, rules) == once


def test_shipped_rules_do_not_mangle_english():
    from taala.canon import generate_canonical_forms
    for pw in ("password", "football", "welcome"):
        # the old broken rules turned "password" into "peteteteteveord" (similarity under 0.5)
        best = max(lr.difflib.SequenceMatcher(None, pw, f).ratio() for f in generate_canonical_forms(pw))
        assert best >= 0.65, (pw, generate_canonical_forms(pw))


def test_learned_output_does_not_replace_shipped_rules():
    assert lr.OUT_PATH.name == "rules_learned.tsv"
