"""The commit guard blocks password data and big files, and lets normal files through."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_staged", ROOT / "tools" / "check_staged.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def blocked(path, size=10):
    return [p for p, _ in guard.violations([(path, size)])]


def test_blocks_password_data_and_private_files():
    for path in ["data/raw/rockyou.txt", "data/private/pack_rank.txt", "data/splits/train_counts.tsv",
                 "stuff/rockyou-withcount.txt", "results/test_run.log", ".env",
                 "locales/hi-latn/words/given_names.txt", "data" + chr(92) + "private" + chr(92) + "x.txt"]:
        assert blocked(path), path


def test_blocks_oversized_files():
    assert blocked("tools/big.bin", size=2_000_000)


def test_allows_normal_files_and_the_manifest():
    for path in ["taala/estimate.py", "README.md", "results/accuracy_test.json",
                 "data/splits/MANIFEST.json", "locales/hi-latn/rules.tsv"]:
        assert not blocked(path), path
