# GALA Rescue 24h Paper Test

Generated: 2026-05-07T21:26:15.631587+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 15 | 15 | 15 | -0.56% | 0.57 | 86.67% | -0.04% | take_profit=13;stop_loss=1;time_stop=1 | 0 |
| GALA 7.3R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 90 |
| GALA 7.3R 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 90 |
| GALA 7.3 diagnostic ret7<=25 | 33 | 33 | 33 | +0.01% | 1.00 | 90.91% | +0.00% | take_profit=30;stop_loss=1;time_stop=1;end_of_data=1 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 27 | 27 | 27 | -0.29% | 0.83 | 88.89% | -0.01% | take_profit=24;stop_loss=1;time_stop=1;end_of_data=1 | 109 |
| GALA 7.3R ret7<=25 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 161 |
| GALA 7.3R 1h score 50-79 fast | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 90 |
| GALA 11.2 base | 28 | 28 | 15 | -0.53% | 0.60 | 93.33% | -0.04% | stop_loss=1;take_profit=14 | 0 |
| GALA 11.2R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 139 |
| GALA 11.2R 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 139 |
| GALA 11.2R 1h short score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 139 |
| GALA 11.2 diagnostic ret7<=25 | 61 | 61 | 38 | +0.08% | 1.05 | 92.11% | +0.00% | stop_loss=1;take_profit=35;time_stop=2 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 55 | 55 | 34 | -0.36% | 0.77 | 88.24% | -0.01% | stop_loss=1;take_profit=30;time_stop=3 | 109 |
| GALA 11.2R ret7<=25 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 242 |

## Files

- Journal CSV: `data/gala_rescue_archive24h_journal_2026-05-07.csv`
- Summary CSV: `data/gala_rescue_archive24h_summary_2026-05-07.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `score 50-79` is a defensive short filter: weak short signals are ignored, and extreme 80+ short signals are not chased.
- This is a rolling 24h paper-execution check with maker-limit fill validation.
