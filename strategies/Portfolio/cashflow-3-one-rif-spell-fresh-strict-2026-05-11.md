# Cashflow 3 Fresh Strict Check

Generated: `2026-05-11T15:26:05.610310+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 42 | +11.60% | $1115.99 | $115.99 | yes `$100` | +1.47% | 3.43 | +78.57% | period_end | RIF=32;ONE=10 |
| 7d | cashflow_stop | 36 | +10.14% | $1101.40 | $101.40 | yes `$100` | +1.47% | 3.50 | +77.78% | profit_target | RIF=28;ONE=8 |
| 30d | continuous | 398 | +3.20% | $1032.03 | $32.03 | no `$100` | +38.63% | 1.04 | +73.62% | period_end | ONE=271;RIF=108;SPELL=19 |
| 30d | cashflow_stop | 307 | -38.61% | $613.93 | $0.00 | no `$100` | +38.63% | 0.49 | +71.34% | loss_stop | ONE=245;RIF=53;SPELL=9 |
| 60d | continuous | 1307 | -15.36% | $846.37 | $0.00 | no `$100` | +53.66% | 0.91 | +73.30% | period_end | ONE=996;RIF=281;SPELL=30 |
| 60d | cashflow_stop | 1209 | -44.82% | $551.80 | $0.00 | no `$100` | +49.21% | 0.72 | +72.70% | loss_stop | ONE=970;RIF=222;SPELL=17 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | ONE | ONE 11.2 | 14 | 12 | +85.71% | 10 | +0.09% | 1.19 | +80.00% | take_profit=8;time_stop=2 |
| 7d | RIF | RIF 5m LONG Best | 43 | 32 | +74.42% | 32 | +16.63% | 3.58 | +78.12% | take_profit=24;time_stop=8 |
| 30d | ONE | ONE 11.2 | 1391 | 471 | +33.86% | 271 | -10.68% | 0.53 | +74.91% | take_profit=197;time_stop=71;stop_loss=3 |
| 30d | RIF | RIF 5m LONG Best | 145 | 108 | +74.48% | 108 | +35.38% | 2.02 | +70.37% | take_profit=73;time_stop=35 |
| 30d | SPELL | SPELL SHORT Best | 23 | 19 | +82.61% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | ONE | ONE 11.2 | 5186 | 1744 | +33.63% | 996 | -27.37% | 0.63 | +77.01% | take_profit=744;time_stop=245;stop_loss=7 |
| 60d | RIF | RIF 5m LONG Best | 369 | 281 | +76.15% | 281 | +27.52% | 1.22 | +61.57% | take_profit=155;time_stop=125;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_fresh_strict_journal_2026-05-11.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_fresh_strict_summary_2026-05-11.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_fresh_strict_modules_2026-05-11.csv`
