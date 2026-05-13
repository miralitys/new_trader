# Cashflow 3 Fresh Strict Check

Generated: `2026-05-09T15:27:24.805285+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no `$100` | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 51 | +13.84% | $1138.42 | $138.42 | yes `$100` | +2.13% | 2.40 | +76.47% | period_end | RIF=40;ONE=10;SPELL=1 |
| 7d | cashflow_stop | 40 | +10.34% | $1103.38 | $103.38 | yes `$100` | +2.13% | 2.15 | +72.50% | profit_target | RIF=33;ONE=6;SPELL=1 |
| 30d | continuous | 450 | +1.65% | $1016.55 | $16.55 | no `$100` | +39.66% | 1.02 | +74.22% | period_end | ONE=322;RIF=109;SPELL=19 |
| 30d | cashflow_stop | 362 | -39.16% | $608.42 | $0.00 | no `$100` | +39.66% | 0.50 | +72.38% | loss_stop | ONE=296;RIF=57;SPELL=9 |
| 60d | continuous | 1370 | -16.28% | $837.16 | $0.00 | no `$100` | +53.66% | 0.91 | +73.28% | period_end | ONE=1046;RIF=294;SPELL=30 |
| 60d | cashflow_stop | 1275 | -45.09% | $549.15 | $0.00 | no `$100` | +49.21% | 0.73 | +72.71% | loss_stop | ONE=1020;RIF=238;SPELL=17 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | ONE | ONE 11.2 | 14 | 12 | +85.71% | 10 | +0.09% | 1.19 | +80.00% | take_profit=8;time_stop=2 |
| 7d | RIF | RIF 5m LONG Best | 55 | 40 | +72.73% | 40 | +13.84% | 1.99 | +75.00% | take_profit=29;time_stop=11 |
| 7d | SPELL | SPELL SHORT Best | 1 | 1 | +100.00% | 1 | +0.96% | inf | +100.00% | take_profit=1 |
| 30d | ONE | ONE 11.2 | 1616 | 554 | +34.28% | 322 | -11.71% | 0.55 | +75.78% | take_profit=236;time_stop=83;stop_loss=3 |
| 30d | RIF | RIF 5m LONG Best | 147 | 109 | +74.15% | 109 | +34.14% | 1.95 | +69.72% | take_profit=73;time_stop=36 |
| 30d | SPELL | SPELL SHORT Best | 23 | 19 | +82.61% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | ONE | ONE 11.2 | 5420 | 1839 | +33.93% | 1046 | -28.87% | 0.63 | +77.06% | take_profit=782;time_stop=256;stop_loss=8 |
| 60d | RIF | RIF 5m LONG Best | 387 | 294 | +75.97% | 294 | +27.44% | 1.21 | +61.22% | take_profit=162;time_stop=131;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_fresh_strict_journal_2026-05-09.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_fresh_strict_summary_2026-05-09.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_fresh_strict_modules_2026-05-09.csv`
