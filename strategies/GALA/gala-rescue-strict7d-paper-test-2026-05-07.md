# GALA Rescue Paper Test

Generated: 2026-05-07T21:51:58.897823+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 91 | 34 | 34 | -0.28% | 0.87 | 91.18% | -0.01% | take_profit=31;time_stop=3 | 0 |
| GALA 7.3R short_score>=50 | 67 | 21 | 21 | -0.96% | 0.50 | 80.95% | -0.05% | take_profit=17;time_stop=4 | 157 |
| GALA 7.3R short_score>=60 | 45 | 15 | 15 | -1.31% | 0.33 | 73.33% | -0.09% | take_profit=11;time_stop=4 | 214 |
| GALA 7.3R short_score>=60 ret7<=5 | 25 | 8 | 8 | -0.46% | 0.43 | 75.00% | -0.06% | take_profit=6;time_stop=2 | 100 |
| GALA 7.3R short_score>=60 fast60 | 50 | 17 | 17 | -0.82% | 0.46 | 70.59% | -0.05% | take_profit=12;time_stop=5 | 214 |
| GALA 7.3R 1h | 13 | 3 | 3 | +0.17% | inf | 100.00% | +0.06% | take_profit=3 | 262 |
| GALA 7.3R 1h score 50-79 | 8 | 1 | 1 | +0.06% | inf | 100.00% | +0.06% | take_profit=1 | 274 |
| GALA 7.3 diagnostic ret7<=25 | 162 | 59 | 59 | -0.68% | 0.82 | 89.83% | -0.01% | take_profit=53;time_stop=5;stop_loss=1 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 115 | 38 | 38 | -1.45% | 0.56 | 84.21% | -0.04% | take_profit=32;time_stop=5;stop_loss=1 | 273 |
| GALA 7.3R ret7<=25 1h score 50-79 | 8 | 1 | 1 | +0.06% | inf | 100.00% | +0.06% | take_profit=1 | 463 |
| GALA 7.3R 1h short_score>=60 | 6 | 1 | 1 | +0.06% | inf | 100.00% | +0.06% | take_profit=1 | 277 |
| GALA 7.3R 1h score 50-79 fast | 8 | 1 | 1 | +0.06% | inf | 100.00% | +0.06% | take_profit=1 | 274 |
| GALA 11.2 base | 153 | 59 | 41 | -0.52% | 0.82 | 90.24% | -0.01% | take_profit=37;time_stop=4 | 0 |
| GALA 11.2R short_score>=50 no x1.5 | 129 | 46 | 31 | -0.45% | 0.72 | 87.10% | -0.01% | take_profit=27;time_stop=4 | 157 |
| GALA 11.2R short_score>=60 no x1.5 | 107 | 40 | 31 | -0.24% | 0.81 | 87.10% | -0.01% | take_profit=27;time_stop=4 | 214 |
| GALA 11.2R short_score>=60 ret7<=5 no x1.5 | 87 | 33 | 29 | +0.07% | 1.08 | 89.66% | +0.00% | take_profit=26;time_stop=3 | 100 |
| GALA 11.2R short_score>=60 keep x1.5 | 107 | 40 | 31 | -0.55% | 0.67 | 87.10% | -0.02% | take_profit=27;time_stop=4 | 214 |
| GALA 11.2R 1h | 19 | 5 | 5 | +0.30% | inf | 100.00% | +0.06% | take_profit=5 | 393 |
| GALA 11.2R 1h no x1.5 | 19 | 5 | 5 | +0.22% | inf | 100.00% | +0.04% | take_profit=5 | 393 |
| GALA 11.2R 1h short score 50-79 | 14 | 3 | 3 | +0.12% | inf | 100.00% | +0.04% | take_profit=3 | 405 |
| GALA 11.2 diagnostic ret7<=25 | 276 | 107 | 72 | +0.74% | 1.23 | 90.28% | +0.01% | take_profit=65;time_stop=7 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 229 | 86 | 60 | +0.26% | 1.13 | 90.00% | +0.00% | take_profit=54;time_stop=6 | 273 |
| GALA 11.2R ret7<=25 1h no x1.5 | 19 | 5 | 5 | +0.22% | inf | 100.00% | +0.04% | take_profit=5 | 676 |

## Files

- Journal CSV: `data/gala_rescue_strict7d_journal_2026-05-07.csv`
- Summary CSV: `data/gala_rescue_strict7d_summary_2026-05-07.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `short_score >= 60` is a defensive short filter: weak short signals are ignored.
- This is a rolling paper-execution check with maker-limit fill validation.
