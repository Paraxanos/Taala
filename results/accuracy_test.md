# §6.1 accuracy: test half

Weak = guesses_log10 < 6.0. Rates with 95% Wilson intervals.
Proxy: rockyou.txt has no counts: file position is the frequency rank; 'rare' is the second half of the file.
Indian-context passwords found: 19820.

| System | Overrating, all | Overrating, Indian | Strictness, all | Strictness, Indian | Spearman, all | Spearman, Indian |
|---|---|---|---|---|---|---|
| stock_zxcvbn |   8.3% [7.8, 8.9] (n=10000) |  59.3% [58.4, 60.3] (n=10000) |  26.1% [25.2, 27.0] (n=10000) |  25.0% [23.8, 26.2] (n=5000) | 0.273 | 0.394 |
| taala |   6.8% [6.3, 7.3] (n=10000) |  24.3% [23.5, 25.2] (n=10000) |  33.9% [33.0, 34.9] (n=10000) |  66.3% [65.0, 67.6] (n=5000) | 0.254 | 0.424 |
| ablation_no_canon |   7.3% [6.8, 7.8] (n=10000) |  39.8% [38.9, 40.8] (n=10000) |  27.1% [26.2, 28.0] (n=10000) |  47.9% [46.6, 49.3] (n=5000) | 0.276 | 0.412 |
| ablation_no_pack |   7.9% [7.4, 8.4] (n=10000) |  44.3% [43.3, 45.3] (n=10000) |  32.4% [31.5, 33.3] (n=10000) |  40.2% [38.9, 41.6] (n=5000) | 0.252 | 0.371 |
| ablation_learned_rules |   6.6% [6.1, 7.1] (n=10000) |  27.4% [26.5, 28.3] (n=10000) |  34.5% [33.5, 35.4] (n=10000) |  63.5% [62.2, 64.8] (n=5000) | 0.256 | 0.419 |

Overrating: lower is better. Strictness: report beside overrating, not alone.
Spearman: guesses_log10 against file position; higher is better.
