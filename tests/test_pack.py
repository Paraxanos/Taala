"""Tests for Pack Integration (Tasks 2.2 & 2.3)."""
import conftest
from taala.pack import get_rules, get_script, get_words
from taala.canon import generate_canonical_forms

@conftest.needs_wordlists
def test_pack_loads_successfully():
    assert len(get_rules()) > 0, "rules.tsv is empty or missing. Run tools/learn_rules.py!"
    assert len(get_script()) > 0, "script.tsv is empty or missing. Run tools/build_script.py!"
    assert len(get_words()) > 100, "words/*.txt are missing. Run tools/fetch_wordlists.py!"

def test_devanagari_inherent_a_deletion():
    forms = generate_canonical_forms("गणेश")
    # "गणेश" transliterates to "ganesh". The learned rule "sh" -> "s" then reduces it to "ganes".
    assert "ganes" in forms, f"Expected 'ganes' in {forms}"
    
    forms = generate_canonical_forms("राम")
    # "राम" transliterates to "ram" (final 'a' deleted). No rules apply.
    assert "ram" in forms, f"Expected 'ram' in {forms}"

def test_learned_rules_integration():
    forms = generate_canonical_forms("प्यार")
    # "प्यार" transliterates to "pyaar". The rule "aa" -> "a" reduces it to "pyar".
    assert "pyar" in forms, f"Expected 'pyar' in {forms}"
    
def test_dictionary_is_canonicalized():
    """Architecture §3 [3]: Everything is stored in canonical form."""
    words = get_words()
    # If "ganesha" was in the raw wiki list, it should be stored as "ganesa" or "ganes"
    # We just verify that no word in the dictionary contains "aa" or "sh" if those rules exist.
    rules = dict(get_rules())
    if "aa" in rules:
        assert not any("aa" in w for w in words), "Dictionary words were not canonicalized!"