"""eval/accuracy.py: the statistics are right and the test half can only be scored once."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

import conftest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("acc", ROOT / "eval" / "accuracy.py")
acc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acc)


def test_spearman_perfect_reversed_and_ties():
    assert acc.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert acc.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert acc.spearman([1, 1, 2, 2], [1, 2, 3, 4]) == pytest.approx(0.8944, abs=1e-3)


def test_wilson_interval_brackets_the_rate():
    lo, hi = acc.wilson(5, 100)
    assert lo < 0.05 < hi and 0 <= lo and hi <= 1
    assert acc.wilson(0, 0)[0] != acc.wilson(0, 0)[0]  # NaN when there is no data


@conftest.needs_wordlists
def test_indian_matcher_rejects_english_and_accepts_curated_names():
    m = acc.IndianMatcher()
    assert m.match("lovee123") is None        # canonical 'love' is English
    assert m.match("iloveyou") is None
    assert m.match("sanjay1998") == ("sanjay",)
    assert m.match("sanjayrahul9") is not None  # two curated tokens joined


def test_second_test_run_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(acc, "RESULTS", tmp_path)
    (tmp_path / "test_run.lock.json").write_text(json.dumps({"runs": [{"rerun": False}]}))
    monkeypatch.setattr(sys, "argv", ["accuracy.py", "--split", "test"])
    with pytest.raises(SystemExit) as e:
        acc.main()
    assert "already scored" in str(e.value)


def test_quick_is_refused_on_the_test_half(tmp_path, monkeypatch):
    monkeypatch.setattr(acc, "RESULTS", tmp_path)
    monkeypatch.setattr(sys, "argv", ["accuracy.py", "--split", "test", "--quick"])
    with pytest.raises(SystemExit):
        acc.main()
