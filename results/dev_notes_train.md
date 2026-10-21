# Development notes (TRAIN half only; the sealed test half was not touched)

> **Corrected 21 Oct 2026.** The first version of these notes was produced while
> `pack.canonical_word` had a bug (the repeat-collapse backreference was a literal control
> character, so the step did nothing). That made the Indian-context matcher and the pack
> ranking weaker than documented. Tables below are re-run with the fix. The old figures were:
> Taala 1.7%, 12.8%, 35.9% and stock 18.8%, 41.9%, 71.1% for the three rank bands, and 273
> overrated in the top 3,000 (71% name plus digits). The Indian-context set had 16,896
> passwords before the fix and 20,165 after.

Aggregates only. Produced 21 Oct 2026 while investigating why the `--quick` dev run
(stock 18.8%, Taala 1.7% overrating) disagreed with the one-off test run (61.0%, 28.3%).

## 1. The two runs answer different questions

`--quick` scores only the first 1,000 Indian-context passwords by file position, the test run
the first 10,000. Overrating grows steeply with rank. Same train half, same code:

| Indian-context rank | n | stock zxcvbn overrates | Taala overrates |
|---|---|---|---|
| 1 to 1,000 | 1,000 | 17.6% | 1.5% |
| 1,001 to 3,000 | 2,000 | 39.6% | 11.2% |
| 3,001 to 10,000 (random sample) | 2,000 | 66.5% | 30.2% |

The `--quick` run covers only the first slice, so its figures must not be quoted as the headline.

## 2. What Taala still overrates (train, Indian-context ranks 1 to 3,000)

238 of 3,000 (7.9%) are scored Fair or higher.

| Pattern | Count | Share |
|---|---|---|
| one pack word plus digits (`rahul2803`, `seth0120`) | 161 | 68% |
| two pack words joined, no digits (`premnath`, `kalicharan`) | 63 | 26% |
| two pack words plus digits | 11 | 5% |
| other | 3 | 1% |

Name plus digits lands at about 10^6.3 to 10^7.5, while these passwords sit at file positions
of a few hundred thousand, so the true cost for a RockYou-trained attacker is under 10^6.
The digit-suffix cost comes from zxcvbn and treats digit strings as more random than people's
real choices (dates, repeats). This is a zxcvbn limitation, not a Hinglish-specific one.

## 3. The two compound examples

| Password | stock | Taala | Why |
|---|---|---|---|
| `jaishreeram` | 10.52 | 6.42 (Fair) | canonicalises to `jaisriram`, matched as two pack words; just above the Weak line |
| `navratri2024` | 11.00 | 10.63 (Strong) | `navratri` is not in the pack (only `navaratri` is), and no rule maps one to the other |
