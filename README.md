# Taala: a password strength checker for Hinglish passwords

Taala estimates how hard a password is to guess when it is built from Indian words and
names written in Latin letters ("Hinglish"), in any spelling, or in Devanagari. Stock
[zxcvbn](https://github.com/dropbox/python-zxcvbn) knows English words; it does not know
that `priyanka`, `priyankaa` and `प्रियंका` are the same name, or that `py@r` is `pyar`.

**Status: early beta, measured on a proxy, not security-reviewed.** Read
[Results](#results) and [Limitations](#limitations) before relying on it.

> **Do not type real passwords into any copy of this tool that you did not run yourself.**
> The web page is meant for localhost only. It binds to 127.0.0.1 and sends the password
> in a POST body, never in a URL, but nobody has audited it.

## What it does

- **Canonicalization:** spelling variants, leetspeak and padding are reduced to at most
  8 canonical forms before any lookup (`jaishreeram` becomes `jaisriram`).
- **Script independence:** Devanagari and Latin reach the same form
  (राम and `ram`, not `rama`).
- **Estimate:** the lowest of stock zxcvbn's score and the scores of the canonical forms,
  with a small penalty per transformation. Bands: Weak below 10^6 guesses, Fair below
  10^10, Strong above.
- **Attack-recipe feedback:** step-by-step guess counts, and the number of random words
  to add to reach Strong. The recipe lists only categories and guess counts, never the password's own tokens.
- **Policy verdict** (`taala/policy.py`, `policy.toml`): accept or reject following the
  password-verifier rules in NIST SP 800-63B-4 §3.1.1.2, as we read them (minimum 15 characters for a
  single-factor password, 8 if only used with multi-factor, no composition rules,
  blocklist check). It checks length, blocklist and personal info; it does not do rate
  limiting or the other parts of the standard. It is not NIST-certified; NIST does not
  certify libraries.

## Quick start

Requires Python 3.11 or newer. Taala is not on PyPI yet; install from a clone:

```bash
git clone https://github.com/Paraxanos/Taala && cd Taala
pip install -e .
python tools/fetch_wordlists.py   # builds the word lists from Wikipedia, about 3 minutes

taala jaishreeram                 # CLI (same as: python -m taala.cli jaishreeram)
python -m taala.web               # then open http://127.0.0.1:8080
```

Without `fetch_wordlists.py`, Taala still runs but only applies spelling rules on top of
stock zxcvbn, and the CLI says so. The word lists are Wikipedia-derived (CC BY-SA 4.0) and
are not committed. To run the tests: `pip install -e ".[dev]" && python -m pytest`
(tests that need the word lists skip when they are missing).

## Results

Measured on a held-out half of the RockYou leak, with learning done only on the other half.
RockYou has no counts in our copy, so **file position stands in for frequency**. Weak means
fewer than 10^6 guesses. "Overrating" is the share of the 10,000 most common Indian-context
passwords that a system does not call Weak. Intervals are 95% Wilson.

**The test half was scored twice, and both runs are reported.** The first run (19 Oct 2026)
used a harness with a bug: the Indian-context matcher did not collapse repeated letters
(found by code inspection on 21 Oct, not from the results). The fixed code re-scored the
test half once more (21 Oct), and the table below is that second run. The first run gave
stock 61.0%, Taala 28.3% and learned rules 31.7% overrating on the Indian-context set; it is
kept in `results/accuracy_test_run1_prefix.md`. Between the two runs the estimator and
the evaluation script were not changed except for that fix (and the pack rank files, rebuilt
with it); the other changes were to the web page, CLI, policy module and packaging.

| System | Overrating, Indian-context | Overrating, all passwords | Rare Indian passwords called Weak |
|---|---|---|---|
| stock zxcvbn | 59.3% [58.4, 60.3] | 8.3% | 25.0% |
| **Taala** | **24.3% [23.5, 25.2]** | 6.8% | 66.3% |
| Taala without canonicalization | 39.8% | 7.3% | 47.9% |
| Taala without the word pack | 44.3% | 7.9% | 40.2% |
| Taala with machine-learned rules | 27.4% | 6.6% | 63.5% |

Full table with intervals and rank agreement: [`results/accuracy_test.md`](results/accuracy_test.md).

How to read this:

- Both parts help. Removing either canonicalization or the word pack raises overrating
  by a wide margin.
- **Taala is stricter, and that explains part of the gain.** It calls 66.3% of rare Indian
  passwords Weak against 25.0% for stock. A stricter checker overrates less by
  construction, so the two columns must be read together.
- **The Indian-context set is chosen with Taala's own word pack, so the comparison is
  partly circular.** A set not built from our pack would be a fairer test.
- **Outside the Indian-context set the gain is small** (8.3% against 6.8%), and rank
  agreement with frequency is weak for every system, Taala included (Spearman 0.25 on
  all passwords against 0.27 for stock).
- Overrating depends strongly on how far down the list you look. On the train half, Taala
  overrates 1.5% of the top 1,000 Indian-context passwords, 11.2% of ranks 1,001 to 3,000
  and 30.2% of ranks 3,001 to 10,000 (stock: 17.6%, 39.6%, 66.5%).
  See [`results/dev_notes_train.md`](results/dev_notes_train.md).
- The machine-learned spelling rules did **not** beat the 6 hand-written ones (27.4% against
  24.3% overrating). They were
  learned from only 50 words, so this says little about what a larger survey would give.

An independent check, a survey of how real people spell common words, is planned and has
not been run yet.

## Reproducing the results

The published numbers need password data that this repository does not distribute:

1. `data/splits/*_counts.tsv`: the RockYou train and test halves, made by `tools/split_data.py`
   (only `data/splits/MANIFEST.json`, with hashes and counts, is committed).
2. `data/private/pack_rank.txt`: pack words ordered by train-half frequency, made by
   `tools/rank_pack.py`. **This file is kept private on purpose** because it is derived from
   breach data.

Without them, Taala still runs, but pack words are ranked alphabetically and scores are
less strict than reported, so the results table cannot be reproduced from a bare clone. If
you have your own copy of RockYou, you can rebuild both files and then run
`python eval/accuracy.py --split train`. The test half is meant to be scored once; the
script refuses a second run unless you pass `--allow-rerun`.

## Limitations

- **A clone will not reproduce the table above** (see [Reproducing the results](#reproducing-the-results)).
  The pack words are ranked by how often they appear in the RockYou train half, and that rank
  file is deliberately kept private. Without it the words are ranked alphabetically, which
  makes scores 0 to 1.1 log10 higher (less strict) on the examples I tried. The CLI prints a
  note when the file is missing.
- **Name plus digits is still overrated.** About 68% of what Taala still gets wrong in the
  top 3,000 Indian-context passwords is a pack word followed by digits (`rahul2803`,
  `seth0120`). The digit cost comes from zxcvbn and treats digits as more random than
  people's real choices. Compounds with no digits make up another 26%.
- **Word-pack coverage is incomplete.** The lists come from Wikipedia categories. For
  example `navaratri` is in the pack but `navratri` is not, so `navratri2024` scores
  10.6 (Strong); `jaishreeram` scores 6.4, just above the Weak line.
- **Short pack words can match by accident** (`taki`, `fase`, `sang` inside longer strings).
- The spelling rules cover common Hindi patterns only; there are no rules for dropped
  vowels like `navaratri` and `navratri`.
- The proxy (file position for frequency, one leak) is not the same as what an attacker
  would try, and RockYou is an old English-leaning leak.
- Not security-reviewed. The policy engine implements only part of NIST SP 800-63B-4.

## Repository layout

`taala/` engine, CLI and web page. `locales/hi-latn/` rules, script map and pack metadata.
`tools/` word-list builder and rule learner. `eval/` the accuracy and performance scripts.
`tests/` the test suite (`python -m pytest`). `survey/` the frozen 100-word list and its train/test split (no survey has been run) and
`data/variants/` the spelling data used to learn and test the rules. Raw password data is never committed.

## License

Code: MIT (see `LICENSE`). Word lists derived from Wikipedia are CC BY-SA 4.0 and are
built locally, not committed. See `data/LICENSE-DATA.md`.
