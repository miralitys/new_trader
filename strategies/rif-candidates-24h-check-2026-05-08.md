# RIF-like Candidates 24h Check

Generated: 2026-05-08T15:32:49.046470+00:00

Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker offset `0.05%`, maker fee `0.02%`, slippage `0`.

Источник: свежие Binance `data_api_spot` свечи. `1000XECUSDT` посчитан через `XECUSDT` как spot-proxy, потому что spot data-api не имеет `1000XECUSDT`.

## Main: Health 30/60

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | health30_60 | 2/2 | 22 | 7 | 7 | +6.15% | 0.95% | 7.07 | +0.86% | take_profit=6;time_stop=1 |
| `ENAUSDT` | health30_60 | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `MOVRUSDT` | health30_60 | 2/2 | 33 | 23 | 23 | +14.94% | 4.04% | 2.71 | +0.62% | take_profit=19;time_stop=2;stop_loss=1;end_of_data=1 |
| `UMAUSDT` | health30_60 | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `COMPUSDT` | health30_60 | 2/2 | 2 | 2 | 1 | -3.14% | 3.14% | 0.00 | -3.14% | time_stop=2 |
| `CVCUSDT` | health30_60 | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `1000XECUSDT` | health30_60 | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Defensive: Health 30/60 + Weekly Kill

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | health30_60_weekly_kill | 2/2 | 22 | 7 | 7 | +6.15% | 0.95% | 7.07 | +0.86% | take_profit=6;time_stop=1 |
| `ENAUSDT` | health30_60_weekly_kill | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `MOVRUSDT` | health30_60_weekly_kill | 2/2 | 33 | 23 | 13 | +7.72% | 4.04% | 2.37 | +0.58% | take_profit=19;time_stop=2;stop_loss=1;end_of_data=1 |
| `UMAUSDT` | health30_60_weekly_kill | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `COMPUSDT` | health30_60_weekly_kill | 2/2 | 2 | 2 | 1 | -3.14% | 3.14% | 0.00 | -3.14% | time_stop=2 |
| `CVCUSDT` | health30_60_weekly_kill | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `1000XECUSDT` | health30_60_weekly_kill | 0/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Raw Always-On Reference

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | raw_always_on | 2/2 | 22 | 7 | 7 | +6.15% | 0.95% | 7.07 | +0.86% | take_profit=6;time_stop=1 |
| `ENAUSDT` | raw_always_on | 2/2 | 14 | 8 | 8 | +2.40% | 1.59% | 1.91 | +0.30% | take_profit=4;time_stop=3;end_of_data=1 |
| `MOVRUSDT` | raw_always_on | 2/2 | 33 | 23 | 23 | +14.94% | 4.04% | 2.71 | +0.62% | take_profit=19;time_stop=2;stop_loss=1;end_of_data=1 |
| `UMAUSDT` | raw_always_on | 2/2 | 2 | 2 | 2 | -0.65% | 1.79% | 0.64 | -0.31% | take_profit=1;time_stop=1 |
| `COMPUSDT` | raw_always_on | 2/2 | 2 | 2 | 1 | -3.14% | 3.14% | 0.00 | -3.14% | time_stop=2 |
| `CVCUSDT` | raw_always_on | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `1000XECUSDT` | raw_always_on | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Files

- Summary CSV: `data/rif_candidates_24h_summary_2026-05-08.csv`
- Journal CSV: `data/rif_candidates_24h_journal_2026-05-08.csv`
