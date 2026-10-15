# Pilot variant set (D0.3)

Spelling variants are the ground truth for everything the rule learner does. This folder
holds the **pilot** set used until the class survey runs after the presentation.

## Three sources, kept apart forever

| File | What it is | Rows | Strength as evidence |
|---|---|---|---|
| `wild.tsv` | Alternate romanizations attested on Wikipedia, with the source of every row | **166** | **Strongest source we have.** Someone outside the team wrote each one |
| `constructed.tsv` | Plausible spellings written one at a time by a language model | **127** | Not evidence at all. **Development only** — may train a learner, may never appear in a test table or a reported number |
| `sheets/author_*.tsv` → `observed_authors.tsv` | How each of the four of us naturally writes each word, written independently | **0 — not collected** | Would be weak but honest: four people, one college, and we also write the rules |

Never merge these into one undifferentiated file. Every result that uses them reports the
mix (`cleaning_rules.md`, "what gets reported").

### Why `observed_authors.tsv` is empty

Dropped on 10 Oct 2026 for time. It was **not** replaced with generated spellings, because
the file's only value is that four separate humans produced four independent spellings. One
model writing four columns produces four correlated guesses with a human label on them, and
reporting that as observed data would be fabrication — the kind a reviewer is entitled to
treat as misconduct, not as a shortcut.

What this costs: §6.2 now rests entirely on `wild.tsv` for its reported numbers. That is
externally attested and citable, so the result still stands, but it is narrower — Wikipedia
redirect spellings skew toward names and places and away from everyday words. The class
survey after the presentation restores the human-observed half properly. Say so plainly in
the limitations section rather than leaving the reader to notice.

## `wild.tsv` — collected 7 Oct 2026, filtered 10 Oct 2026

173 spellings collected across 43 of the 100 words; **7 dropped, 166 kept.** Only words with
a `wiki_title` can be collected this way, which is why everyday words like प्यार are absent.

The drop was done by rule rather than by eye, so a re-collection reproduces it. Wikipedia
redirects mix respellings together with different names that merely look similar, and
`tools/collect_wild.py` separates them on four tests: length difference ≤ 3, neither form
contains the other whole, similarity ≥ 0.70, and **no run of 3+ characters that the
candidate adds out of nowhere** (`longest_insertion`). That last one is what catches whole
extra words:

| Dropped | Why |
|---|---|
| `lakshmi → laksmidevi`, `lakshmi → mahalaksmi`, `phoolan → poolandevi` | adds a whole word (`devi`, `maha`) |
| `navratri → chetnavrati`, `chennai → chennapuri` | adds `chet`, `puri` — a different festival, an older city name |
| `chaudhary → chaudhrani` | feminine title, a different word — **curated by hand** |
| `bhopal → bhojpal` | historical name for the city — **curated by hand** |

The last two are semantic, not structural, so no honest rule catches them. They sit in a
`REJECTED` table in the tool with a reason each. **If that table grows past a handful, the
rules above are wrong and should be fixed instead.**

Kept, correctly: `dussehra → dasehra`, `diwali → divali`, `yadav → jadav`, `sunil → suneel`,
`ahmedabad → amdavad`, `krishn → kirushna`. The test for "is this the same word?" is whether
a person typing fast could produce it for that word.

## Two rules that make or break the results

**1. The hold-out rule.** The 50/50 train/test split in `survey/split.tsv` was frozen before
any spelling was written. Rules are developed on **train** words only; the test half is
opened once, in P4. `constructed.tsv` therefore covers **train words only**, and
`tests/test_variants.py` fails if a test word ever appears in it. `wild.tsv` spans both
halves because it was collected from an outside source, not written by us — D1.3 is what
separates it.

**2. Never generate `constructed.tsv` from the rule table.** It is tempting to read the rules
(`aa → a`, `ee → i`) and write variants that exercise them. That makes the evaluation
circular: the learner recovers the rules used to invent the data and the merge rate means
nothing. The 127 rows here were written word by word without consulting any rule file, which
is the only reason they are usable even for development.

## How to fill your sheet (if the team finds time after all)

**Easiest way: open `sheets/author_<your letter>.xlsx` in Excel.** One workbook per author,
never one workbook with four tabs — a shared file lets the second author read the first
one's answers, and independence is the only thing this file measures. Fill the three cream
columns on the *Spellings* tab; the grey ones are given. The *Instructions* tab repeats the
rules and counts how many you have done. The `.tsv` beside it is the same sheet if you would
rather type into a text editor; `tools/import_sheets.py` reads whichever one you filled.

Excel's own validation only checks the shape (length, lowercase, no spaces). The real rules
are enforced by the importer, which prints every cell it rejects instead of dropping it
quietly — so re-run it and fix what it names.

1. Open `sheets/author_<your letter>.tsv`. Every author's sheet has the words in a different order.
2. For each row, type how you would normally write that word in English letters.
3. `spelling` is your natural spelling. `spelling_alt` is optional: fill it only if a second spelling feels equally natural. Put `1` in `dont_know` if you don't know the word.
4. Lowercase a–z only. No spaces, digits or punctuation. One word per cell.
5. **Work alone.** If two of us agree a spelling first, we lose the variation we are measuring.
6. **Do not open `survey/words.tsv` while filling your sheet.** Its `ref_latin` column would anchor your spelling to that one.

The sheets already exist, so re-running `tools/make_collection_sheets.py` will not overwrite
answers. Even a partial return is worth having: two authors is better than zero.

## Known weakness, to state in the paper

Every spelling now in this folder was either scraped by us or generated by a model, and we
also tune the rules. The hold-out rule and the `wild.tsv`-only test set limit the damage;
they do not remove it. This is exactly why the class survey replaces this set as the real
evaluation later.

## Commands

```
python tools/make_constructed.py              # rebuild constructed.tsv from the hand-written list
python tools/collect_wild.py --self-check     # test the Wikipedia filter, no network
python tools/collect_wild.py --clean-existing # re-filter wild.tsv in place, no network
python tools/collect_wild.py                  # rebuild wild.tsv from scratch (~10 min of API calls)
python tools/make_collection_sheets.py        # create blank author sheets as TSV (won't overwrite)
python tools/make_sheets_xlsx.py              # rebuild the four Excel workbooks from those TSVs
python tools/import_sheets.py                 # read filled sheets -> observed_authors.tsv
python tools/build_variants.py                # P1 (D1.3): consolidate and seal the test half
```
