# Cashflow 3 Fresh Strict Check

Generated: `2026-05-12T12:01:54.459932+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 31 | +10.44% | $1104.36 | $104.36 | yes `$100` | +0.84% | 5.10 | +83.87% | period_end | RIF=24;ONE=7 |
| 7d | cashflow_stop | 29 | +10.46% | $1104.59 | $104.59 | yes `$100` | +0.84% | 6.74 | +86.21% | profit_target | RIF=22;ONE=7 |
| 30d | continuous | 381 | +3.35% | $1033.46 | $33.46 | no `$100` | +38.55% | 1.04 | +74.28% | period_end | ONE=255;RIF=107;SPELL=19 |
| 30d | cashflow_stop | 290 | -38.52% | $614.78 | $0.00 | no `$100` | +38.55% | 0.48 | +72.07% | loss_stop | ONE=229;RIF=52;SPELL=9 |
| 60d | continuous | 1281 | -14.99% | $850.12 | $0.00 | no `$100` | +53.66% | 0.92 | +73.54% | period_end | ONE=974;RIF=277;SPELL=30 |
| 60d | cashflow_stop | 1183 | -44.58% | $554.25 | $0.00 | no `$100` | +49.21% | 0.72 | +72.95% | loss_stop | ONE=948;RIF=218;SPELL=17 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | ONE | ONE 11.2 | 11 | 9 | +81.82% | 7 | -0.04% | 0.92 | +85.71% | take_profit=6;time_stop=1 |
| 7d | RIF | RIF 5m LONG Best | 32 | 24 | +75.00% | 24 | +15.15% | 5.83 | +83.33% | take_profit=19;time_stop=5 |
| 30d | ONE | ONE 11.2 | 1276 | 436 | +34.17% | 255 | -9.52% | 0.55 | +76.08% | take_profit=189;time_stop=63;stop_loss=3 |
| 30d | RIF | RIF 5m LONG Best | 144 | 107 | +74.31% | 107 | +34.42% | 1.99 | +70.09% | take_profit=72;time_stop=35 |
| 30d | SPELL | SPELL SHORT Best | 22 | 19 | +86.36% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | ONE | ONE 11.2 | 5062 | 1700 | +33.58% | 974 | -26.46% | 0.63 | +77.31% | take_profit=731;time_stop=236;stop_loss=7 |
| 60d | RIF | RIF 5m LONG Best | 365 | 277 | +75.89% | 277 | +27.27% | 1.22 | +61.73% | take_profit=153;time_stop=123;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_fresh_strict_journal_2026-05-12.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_fresh_strict_summary_2026-05-12.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_fresh_strict_modules_2026-05-12.csv`
