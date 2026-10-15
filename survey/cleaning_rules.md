# Pre-registered cleaning rules

**Fixed on 7 Oct 2026, before any spelling was collected.** These rules are frozen for the same reason the word list is: deciding how to clean data after seeing it lets you pick the version that flatters your results.

They apply to the pilot variant set now, and to the class survey later, unchanged.

## Per spelling

Applied in this order:

1. Strip leading and trailing whitespace.
2. Lowercase.
3. Remove internal spaces and hyphens (`sri nagar` → `srinagar`).
4. **Discard** the spelling if, after steps 1–3, it contains anything other than `a`–`z`. This drops digits, punctuation, emoji, and anything left in Devanagari.
5. **Discard** if shorter than 2 characters or longer than 24.
6. Keep at most two spellings per participant per word: the primary one, and the alternative if it differs from the primary after cleaning.

## Per participant

7. **Discard the whole response** if fewer than 80% of words were answered, counting "don't know" as answered.
8. **Discard the whole response** if more than 20% of the kept spellings are identical to the Devanagari input, which indicates a copy-paste rather than a romanization.
9. A `plain` control word spelled in more than 3 distinct ways across all participants is reported as a warning. It may mean the instructions were misread.

## Per word

10. A word with **fewer than 2 distinct spellings** across all participants yields no pairs, so it contributes nothing to the learner. It is still counted and reported.
11. "Don't know" answers are counted and reported per word, and are otherwise ignored.

## Team members' own data

12. Spellings written by the four authors live in their own file and are **never used in the test-half evaluation**. They may be used for development, on the train half only.
13. In the later class survey, anyone answering "yes" to the team-membership screening question is handled the same way.

## What gets reported alongside every result

- number of participants, after rule 7
- number of words with at least 2 distinct spellings, after rule 10
- number of spelling pairs, broken down by source (authors / constructed / wild / survey)
- number of spellings discarded, by which rule discarded them
- "don't know" counts

## Changing these rules

If a rule turns out to be wrong, change it, but record in the commit message what changed, why, and what the numbers were before and after. A silent change to a cleaning rule after seeing results is the single easiest way to make an honest project look dishonest.
