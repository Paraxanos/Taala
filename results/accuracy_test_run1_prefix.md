# §6.1 accuracy: test half

Weak = guesses_log10 < 6.0. Rates with 95% Wilson intervals.
Proxy: rockyou.txt has no counts: file position is the frequency rank; 'rare' is the second half of the file.
Indian-context passwords found: 16674.

| System | Overrating, all | Overrating, Indian | Strictness, all | Strictness, Indian | Spearman, all | Spearman, Indian |
|---|---|---|---|---|---|---|
| stock_zxcvbn |   8.3% [7.8, 8.9] (n=10000) |  61.0% [60.1, 62.0] (n=10000) |  26.1% [25.2, 27.0] (n=10000) |  24.5% [23.3, 25.7] (n=5000) | 0.273 | 0.343 |
| taala |   6.9% [6.4, 7.4] (n=10000) |  28.3% [27.4, 29.2] (n=10000) |  33.9% [33.0, 34.9] (n=10000) |  63.6% [62.3, 64.9] (n=5000) | 0.253 | 0.422 |
| ablation_no_canon |   7.3% [6.8, 7.9] (n=10000) |  40.0% [39.0, 41.0] (n=10000) |  27.1% [26.2, 28.0] (n=10000) |  49.4% [48.0, 50.7] (n=5000) | 0.276 | 0.369 |
| ablation_no_pack |   7.9% [7.4, 8.4] (n=10000) |  48.9% [47.9, 49.9] (n=10000) |  32.4% [31.5, 33.3] (n=10000) |  37.3% [36.0, 38.7] (n=5000) | 0.252 | 0.346 |
| ablation_learned_rules |   6.6% [6.2, 7.1] (n=10000) |  31.7% [30.8, 32.6] (n=10000) |  34.4% [33.5, 35.3] (n=10000) |  61.0% [59.7, 62.4] (n=5000) | 0.256 | 0.401 |

Overrating: lower is better. Strictness: report beside overrating, not alone.
Spearman: guesses_log10 against file position; higher is better.
