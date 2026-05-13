# GALA Rescue Paper Test

Generated: 2026-05-11T18:06:18.553271+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=50 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 ret7<=5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R short_score>=60 fast60 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3 diagnostic ret7<=25 | 25 | 14 | 14 | -0.33% | 0.66 | 78.57% | -0.02% | take_profit=11;time_stop=3 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 39 | 14 | 14 | +0.09% | 1.17 | 78.57% | +0.01% | take_profit=11;time_stop=2;end_of_data=1 | 89 |
| GALA 7.3R ret7<=25 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 193 |
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
| GALA 11.2 diagnostic ret7<=25 | 37 | 21 | 15 | -0.42% | 0.68 | 80.00% | -0.03% | take_profit=12;time_stop=3 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 51 | 21 | 16 | +0.15% | 1.31 | 81.25% | +0.01% | take_profit=13;time_stop=2;end_of_data=1 | 89 |
| GALA 11.2R ret7<=25 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 211 |

## Files

- Journal CSV: `data/24h_snapshot_gala_diagnostic_journal_2026-05-11.csv`
- Summary CSV: `data/24h_snapshot_gala_diagnostic_summary_2026-05-11.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `short_score >= 60` is a defensive short filter: weak short signals are ignored.
- This is a rolling paper-execution check with maker-limit fill validation.
