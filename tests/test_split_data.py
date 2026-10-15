"""The occurrence split must lose nothing and be reproducible from its seed.

These run on a small synthetic corpus, so they need no password data. The real corpus is
never in the repository.
"""

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SYNTHETIC = [
    "  100 password",
    "   50 letmein",
    "   10 correct horse",      # passwords may contain spaces
    "    1 x",                  # single occurrence, single character
    "not-a-count whatever",     # skipped: count is not a number
    "",                         # skipped: blank
    f"    3 {'a' * 80}",        # skipped: longer than MAX_LEN
]


def load_module():
    spec = importlib.util.spec_from_file_location("split_data", ROOT / "tools" / "split_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(tmp_path, lines=SYNTHETIC, seed=1234, has_counts=True):
    module = load_module()
    tmp_path.mkdir(parents=True, exist_ok=True)  # callers may pass a nested path
    module.OUT_DIR = tmp_path / "splits"
    src = tmp_path / "corpus.txt"
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")
    module.main(str(src), has_counts, seed)
    manifest = json.loads((module.OUT_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    return module, manifest


def read_counts(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["password"]: int(r["count"]) for r in csv.DictReader(fh, delimiter="\t")}


def test_no_occurrence_is_lost_or_duplicated(tmp_path):
    module, manifest = run(tmp_path)
    counts = manifest["counts"]
    assert counts["train"] + counts["test"] == counts["occurrences"]

    train = read_counts(module.OUT_DIR / "train_counts.tsv")
    test = read_counts(module.OUT_DIR / "test_counts.tsv")
    for password, total in (("password", 100), ("letmein", 50), ("correct horse", 10), ("x", 1)):
        assert train.get(password, 0) + test.get(password, 0) == total, password


def test_bad_lines_are_skipped_and_counted(tmp_path):
    _, manifest = run(tmp_path)
    assert manifest["counts"]["unique"] == 4
    assert manifest["counts"]["skipped"] == 3  # bad count, blank, over-length
    assert manifest["counts"]["occurrences"] == 161


def test_passwords_with_spaces_survive(tmp_path):
    module, _ = run(tmp_path)
    train = read_counts(module.OUT_DIR / "train_counts.tsv")
    test = read_counts(module.OUT_DIR / "test_counts.tsv")
    assert "correct horse" in (train | test)


def test_same_seed_reproduces_the_split(tmp_path):
    first, _ = run(tmp_path / "a", seed=777)
    second, _ = run(tmp_path / "b", seed=777)
    for name in ("train_counts.tsv", "test_counts.tsv"):
        assert (first.OUT_DIR / name).read_text(encoding="utf-8") == \
               (second.OUT_DIR / name).read_text(encoding="utf-8")


def test_different_seed_changes_the_split(tmp_path):
    """With 100 occurrences of one password, two seeds agreeing exactly would be a bug."""
    first, _ = run(tmp_path / "a", seed=1)
    second, _ = run(tmp_path / "b", seed=2)
    assert (first.OUT_DIR / "train_counts.tsv").read_text(encoding="utf-8") != \
           (second.OUT_DIR / "train_counts.tsv").read_text(encoding="utf-8")


def test_split_is_roughly_even(tmp_path):
    """A 50/50 coin flip over 161 occurrences should not land wildly off centre."""
    _, manifest = run(tmp_path)
    counts = manifest["counts"]
    share = counts["train"] / counts["occurrences"]
    assert 0.30 < share < 0.70, share


def test_no_counts_mode_treats_each_line_as_one(tmp_path):
    _, manifest = run(tmp_path, lines=["alpha", "beta", "gamma"], has_counts=False)
    assert manifest["counts"]["unique"] == 3
    assert manifest["counts"]["occurrences"] == 3


def test_manifest_records_provenance(tmp_path):
    _, manifest = run(tmp_path)
    assert manifest["seed"] == 1234
    assert len(manifest["input"]["sha256"]) == 64
    assert manifest["input"]["has_counts"] is True
    assert set(manifest["outputs"]) == {"train_counts.tsv", "test_counts.tsv"}
    assert manifest["filters"]["max_password_length"] == 64
