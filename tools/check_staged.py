"""Pre-commit guard: refuse to commit password data, secrets or oversized files.

Enable once per clone:   git config core.hooksPath .githooks
Run by hand:             python tools/check_staged.py

It checks the files staged for commit. The rules mirror .gitignore, so they also catch a
file forced in with `git add -f`.
"""
import fnmatch
import subprocess
import sys

MAX_BYTES = 1_000_000

# Paths that must never be committed, matched against the repo-relative path.
BLOCKED = [
    "data/raw/*", "data/private/*", "data/survey_raw/*", "results/private/*",
    "data/splits/*.tsv", "*rockyou*", "*withcount*", "*.env", ".env", "*.log",
    "locales/*/words/*.txt",
]
# Exceptions to the blocked patterns above.
ALLOWED = ["data/splits/MANIFEST.json"]


def violations(files):
    """files: iterable of (path, size_in_bytes). Returns a list of (path, reason)."""
    bad = []
    for path, size in files:
        p = path.replace("\\", "/")
        if p in ALLOWED:
            continue
        if any(fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(p.rsplit("/", 1)[-1], pat) for pat in BLOCKED):
            bad.append((p, "matches a blocked path (password data, private or generated file)"))
        elif size > MAX_BYTES:
            bad.append((p, f"is {size:,} bytes, over the {MAX_BYTES:,}-byte limit"))
    return bad


def staged_files():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    files = []
    for path in filter(None, out.split("\0")):
        size = int(subprocess.run(["git", "cat-file", "-s", f":{path}"],
                                  capture_output=True, check=True).stdout)
        files.append((path, size))
    return files


def main():
    bad = violations(staged_files())
    for path, why in bad:
        print(f"BLOCKED: {path} {why}", file=sys.stderr)
    if bad:
        print("Commit refused. See CONTRIBUTING.md: no password data in commits, ever.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
