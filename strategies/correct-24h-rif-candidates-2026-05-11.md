# RIF-like Candidates 24h Check

Generated: 2026-05-11T17:33:14.183875+00:00

Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker offset `0.05%`, maker fee `0.02%`, slippage `0`.

Источник: свежие Binance `data_api_spot` свечи. `1000XECUSDT` посчитан через `XECUSDT` как spot-proxy, потому что spot data-api не имеет `1000XECUSDT`.

## Main: Health 30/60

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | health30_60 | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `ACHUSDT` | health30_60 | 2/2 | 1 | 1 | 1 | -0.83% | 0.83% | 0.00 | -0.83% | time_stop=1 |
| `REZUSDT` | health30_60 | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Defensive: Health 30/60 + Weekly Kill

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | health30_60_weekly_kill | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `ACHUSDT` | health30_60_weekly_kill | 2/2 | 1 | 1 | 1 | -0.83% | 0.83% | 0.00 | -0.83% | time_stop=1 |
| `REZUSDT` | health30_60_weekly_kill | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Raw Always-On Reference

| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | raw_always_on | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |
| `ACHUSDT` | raw_always_on | 2/2 | 1 | 1 | 1 | -0.83% | 0.83% | 0.00 | -0.83% | time_stop=1 |
| `REZUSDT` | raw_always_on | 2/2 | 0 | 0 | 0 | +0.00% | 0.00% | 0.00 | +0.00% |  |

## Files

- Summary CSV: `data/correct_24h_rif_candidates_summary_2026-05-11.csv`
- Journal CSV: `data/correct_24h_rif_candidates_journal_2026-05-11.csv`
