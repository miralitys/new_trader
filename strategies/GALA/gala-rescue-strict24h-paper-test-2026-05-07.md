# GALA Rescue Paper Test

Generated: 2026-05-07T21:52:32.666815+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=50 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 ret7<=5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 fast60 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3 diagnostic ret7<=25 | 51 | 16 | 16 | -0.92% | 0.45 | 81.25% | -0.06% | take_profit=13;stop_loss=1;time_stop=2 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 32 | 11 | 11 | -0.83% | 0.38 | 81.82% | -0.08% | take_profit=9;stop_loss=1;time_stop=1 | 85 |
| GALA 7.3R ret7<=25 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 133 |
| GALA 7.3R 1h short_score>=60 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h score 50-79 fast | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2 base | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R short_score>=50 no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R short_score>=60 no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R short_score>=60 ret7<=5 no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R short_score>=60 keep x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h short score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2 diagnostic ret7<=25 | 85 | 32 | 18 | -0.51% | 0.62 | 77.78% | -0.03% | take_profit=14;time_stop=4 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 66 | 27 | 18 | -0.15% | 0.79 | 83.33% | -0.01% | take_profit=15;time_stop=3 | 85 |
| GALA 11.2R ret7<=25 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 195 |

## Files

- Journal CSV: `data/gala_rescue_strict24h_journal_2026-05-07.csv`
- Summary CSV: `data/gala_rescue_strict24h_summary_2026-05-07.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `short_score >= 60` is a defensive short filter: weak short signals are ignored.
- This is a rolling paper-execution check with maker-limit fill validation.
