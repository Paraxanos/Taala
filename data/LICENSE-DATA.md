# Where the data in this folder comes from

The code in this repository and the data in this folder are **not** under the same terms.
See `OPEN_SOURCE.md` §2 in the project docs for the full reasoning.

## Wikipedia-derived files

| File | Content | Terms |
|---|---|---|
| `data/variants/wild.tsv` | Alternate romanizations taken from English Wikipedia redirect titles. Every row records the page it came from | Derived from Wikipedia, which is **CC BY-SA 4.0**. Attribution: English Wikipedia, retrieved 7 Oct 2026 |
| `locales/hi-latn/words/*.txt` | Word lists built from English Wikipedia category membership | Same: **CC BY-SA 4.0**, English Wikipedia, retrieved 7 Oct 2026 |

**The generated word lists are deliberately not committed.** They are rebuilt with
`python tools/fetch_wordlists.py`, and `locales/hi-latn/pack.toml` records exactly which
categories produced which file, with counts, so a reader can reproduce or audit them.
Keeping a derived corpus out of the repository avoids redistributing it, which is the
simplest way to keep the share-alike terms confined to files that carry them.

`wild.tsv` **is** committed, because the pilot variant set is what every §6.2 result rests
on and the numbers must be reproducible. It is small, it is a list of spellings rather
than prose, and each row names its source page. **It stays under CC BY-SA 4.0**: anyone who
reuses it must credit English Wikipedia and share their derived version under the same
terms. The share-alike term applies to this file and the word lists, not to the code.

## Third-party code

Taala depends on `zxcvbn` (MIT, https://github.com/dwolfhub/zxcvbn-python) and says so
descriptively. It is not affiliated with or endorsed by Dropbox or the port's maintainers.

## Our own files

| File | Terms |
|---|---|
| `survey/words.tsv`, `split.tsv`, `FREEZE.json` (the 100-word list and its frozen split) | Ours; MIT unless a file says otherwise |
| `data/variants/sheets/*`, `observed_authors.tsv` | Ours. **Filled author sheets are published only with each author's written agreement** (see below) |
| `data/variants/constructed.tsv` | Spellings written by a language model. Development use only; never part of a reported result |
| `locales/hi-latn/rules*.tsv`, `script.tsv` | Ours; MIT |

## Never in this repository

Password corpora and anything derived from them, raw survey responses, and usability
pilot recordings. `.gitignore` blocks the paths these would land in.
