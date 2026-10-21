"""Split a password frequency list into train and test halves, by occurrence (D0.5).

The input is a list of passwords with counts, as a breach corpus such as RockYou is
usually distributed. Each *occurrence* is assigned to train or test independently, so a
password seen 100 times lands roughly 50/50 in both halves. That mirrors reality, where
common passwords appear across many sites.

Usage:
    python tools/split_data.py --input path/to/rockyou-withcount.txt
    python tools/split_data.py --input path/to/plain-list.txt --no-counts

The password data never enters git. Only data/splits/MANIFEST.json is committed, which
records the hashes and totals so a reviewer can confirm the split is reproducible.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "splits"
SEED = 20261007
MAX_LEN = 64


def parse_line(line, has_counts):
    """'   12 password' -> ('password', 12). Returns None for unusable lines."""
    line = line.rstrip("\n").rstrip("\r")
    if not line.strip():
        return None
    if not has_counts:
        pw = line
        count = 1
    else:
        stripped = line.lstrip()
        head, sep, rest = stripped.partition(" ")
        if not sep or not head.isdigit():
            return None
        pw, count = rest, int(head)
    if not pw or len(pw) > MAX_LEN or count < 1:
        return None
    return pw, count


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(input_path, has_counts, seed):
    # random.Random.binomialvariate arrived in Python 3.12. The committed split (see
    # data/splits/MANIFEST.json) was drawn with its random stream, and a substitute would
    # silently give a different split, so older versions are refused rather than approximated.
    if not hasattr(random.Random, "binomialvariate"):
        raise SystemExit("tools/split_data.py needs Python 3.12 or newer (random.binomialvariate), "
                         "so that the split reproduces the one recorded in data/splits/MANIFEST.json.")
    input_path = Path(input_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    train_path = OUT_DIR / "train_counts.tsv"
    test_path = OUT_DIR / "test_counts.tsv"
    stats = {"unique": 0, "skipped": 0, "occurrences": 0, "train": 0, "test": 0,
             "train_unique": 0, "test_unique": 0}

    with input_path.open(encoding="utf-8", errors="replace") as src, \
            train_path.open("w", encoding="utf-8", newline="") as tr, \
            test_path.open("w", encoding="utf-8", newline="") as te:
        train_w = csv.writer(tr, delimiter="\t", lineterminator="\n")
        test_w = csv.writer(te, delimiter="\t", lineterminator="\n")
        train_w.writerow(["count", "password"])
        test_w.writerow(["count", "password"])

        for line in src:
            parsed = parse_line(line, has_counts)
            if parsed is None:
                stats["skipped"] += 1
                continue
            pw, count = parsed
            n_train = rng.binomialvariate(count, 0.5)
            n_test = count - n_train
            assert n_train + n_test == count  # no occurrence is lost or duplicated

            stats["unique"] += 1
            stats["occurrences"] += count
            stats["train"] += n_train
            stats["test"] += n_test
            if n_train:
                train_w.writerow([n_train, pw])
                stats["train_unique"] += 1
            if n_test:
                test_w.writerow([n_test, pw])
                stats["test_unique"] += 1

    assert stats["train"] + stats["test"] == stats["occurrences"]

    (OUT_DIR / "MANIFEST.json").write_text(json.dumps({
        "created": dt.date.today().isoformat(),
        "seed": seed,
        "input": {"name": input_path.name, "sha256": sha256_file(input_path),
                  "has_counts": has_counts},
        "filters": {"max_password_length": MAX_LEN},
        "counts": stats,
        "outputs": {"train_counts.tsv": sha256_file(train_path),
                    "test_counts.tsv": sha256_file(test_path)},
        "note": "Outputs are gitignored. Rerunning with the same seed and input reproduces them.",
    }, indent=2) + "\n", encoding="utf-8")

    print(f"unique passwords: {stats['unique']:,}   skipped lines: {stats['skipped']:,}")
    print(f"occurrences: {stats['occurrences']:,}"
          f"  -> train {stats['train']:,} / test {stats['test']:,}")
    print(f"wrote {train_path.name}, {test_path.name}, MANIFEST.json in data/splits/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="password list, kept outside git")
    parser.add_argument("--no-counts", action="store_true",
                        help="input is one password per line, without counts")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    main(args.input, not args.no_counts, args.seed)
