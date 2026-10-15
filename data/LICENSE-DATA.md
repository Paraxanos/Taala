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
simplest way to stay clear of the share-alike question while the project is private.

`wild.tsv` **is** committed, because the pilot variant set is what every §6.2 result rests
on and the numbers must be reproducible. It is small, it is a list of spellings rather
than prose, and each row names its source page.

## Our own files

| File | Terms |
|---|---|
| `survey/*` (word list, split, consent, instructions, cleaning rules) | Ours |
| `data/variants/sheets/*`, `observed_authors.tsv`, `constructed.tsv` | Ours |
| `locales/hi-latn/rules.tsv`, `script.tsv` | Ours |

## Never in this repository

Password corpora and anything derived from them, raw survey responses, and usability
pilot recordings. `.gitignore` blocks the paths these would land in.
