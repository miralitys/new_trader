# GALA Rescue 24h Paper Test

Generated: 2026-05-07T21:47:12.440582+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 53 | 53 | 53 | -0.87% | 0.75 | 86.79% | -0.02% | take_profit=46;time_stop=6;stop_loss=1 | 0 |
| GALA 7.3R 1h | 4 | 4 | 4 | -0.22% | 0.44 | 75.00% | -0.05% | take_profit=3;time_stop=1 | 278 |
| GALA 7.3R 1h score 50-79 | 4 | 4 | 4 | -0.22% | 0.44 | 75.00% | -0.05% | take_profit=3;time_stop=1 | 282 |
| GALA 7.3 diagnostic ret7<=25 | 87 | 87 | 87 | -1.71% | 0.71 | 85.06% | -0.02% | take_profit=74;time_stop=11;stop_loss=2 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 72 | 72 | 72 | -1.84% | 0.65 | 83.33% | -0.03% | take_profit=60;time_stop=10;stop_loss=2 | 273 |
| GALA 7.3R ret7<=25 1h score 50-79 | 4 | 4 | 4 | -0.22% | 0.44 | 75.00% | -0.05% | take_profit=3;time_stop=1 | 471 |
| GALA 7.3R 1h score 50-79 fast | 4 | 4 | 4 | +0.01% | 1.07 | 75.00% | +0.00% | take_profit=3;time_stop=1 | 282 |
| GALA 11.2 base | 106 | 106 | 69 | +0.38% | 1.13 | 91.30% | +0.01% | take_profit=63;time_stop=6 | 0 |
| GALA 11.2R 1h | 8 | 8 | 8 | -0.16% | 0.70 | 87.50% | -0.02% | take_profit=7;time_stop=1 | 409 |
| GALA 11.2R 1h no x1.5 | 8 | 8 | 8 | -0.06% | 0.83 | 87.50% | -0.01% | take_profit=7;time_stop=1 | 409 |
| GALA 11.2R 1h short score 50-79 | 8 | 8 | 8 | -0.06% | 0.83 | 87.50% | -0.01% | take_profit=7;time_stop=1 | 413 |
| GALA 11.2 diagnostic ret7<=25 | 183 | 183 | 113 | +0.85% | 1.20 | 90.27% | +0.01% | take_profit=102;time_stop=11 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 168 | 168 | 102 | +0.40% | 1.13 | 89.22% | +0.00% | take_profit=91;time_stop=11 | 273 |
| GALA 11.2R ret7<=25 1h no x1.5 | 8 | 8 | 8 | -0.06% | 0.83 | 87.50% | -0.01% | take_profit=7;time_stop=1 | 692 |

## Files

- Journal CSV: `data/gala_rescue_7d_journal_2026-05-07.csv`
- Summary CSV: `data/gala_rescue_7d_summary_2026-05-07.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `score 50-79` is a defensive short filter: weak short signals are ignored, and extreme 80+ short signals are not chased.
- This is a rolling 24h paper-execution check with maker-limit fill validation.
