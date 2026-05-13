# GALA Rescue 24h Paper Test

Generated: 2026-05-07T21:25:54.579072+00:00

| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| GALA 7.3 base | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3R 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 7.3 diagnostic ret7<=25 | 22 | 22 | 22 | -1.53% | 0.38 | 72.73% | -0.07% | take_profit=16;time_stop=5;stop_loss=1 | 0 |
| GALA 7.3 diagnostic ret7<=25 score 50-79 | 17 | 17 | 17 | -1.16% | 0.37 | 70.59% | -0.07% | take_profit=12;stop_loss=1;time_stop=4 | 85 |
| GALA 7.3R ret7<=25 1h score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 133 |
| GALA 7.3R 1h score 50-79 fast | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2 base | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2R 1h short score 50-79 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 0 |
| GALA 11.2 diagnostic ret7<=25 | 49 | 49 | 26 | -0.38% | 0.76 | 80.77% | -0.01% | take_profit=21;time_stop=5 | 0 |
| GALA 11.2 diagnostic ret7<=25 short score 50-79 | 44 | 44 | 21 | -0.44% | 0.59 | 76.19% | -0.02% | take_profit=16;time_stop=5 | 85 |
| GALA 11.2R ret7<=25 1h no x1.5 | 0 | 0 | 0 | +0.00% | 0.00 | 0.00% | +0.00% |  | 195 |

## Files

- Journal CSV: `data/gala_rescue_24h_journal_2026-05-07.csv`
- Summary CSV: `data/gala_rescue_24h_summary_2026-05-07.csv`

## Notes

- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.
- `score 50-79` is a defensive short filter: weak short signals are ignored, and extreme 80+ short signals are not chased.
- This is a rolling 24h paper-execution check with maker-limit fill validation.
