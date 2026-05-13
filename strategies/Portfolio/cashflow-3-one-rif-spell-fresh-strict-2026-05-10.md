# Cashflow 3 Fresh Strict Check

Generated: `2026-05-10T15:29:30.504837+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 3 | +0.61% | $1006.13 | $6.13 | no `$100` | +0.65% | 1.93 | +66.67% | period_end | RIF=3 |
| 1d | cashflow_stop | 3 | +0.61% | $1006.13 | $6.13 | no `$100` | +0.65% | 1.93 | +66.67% | period_end | RIF=3 |
| 7d | continuous | 52 | +15.52% | $1155.22 | $155.22 | yes `$100` | +2.13% | 2.68 | +76.92% | period_end | RIF=41;ONE=10;SPELL=1 |
| 7d | cashflow_stop | 34 | +10.19% | $1101.87 | $101.87 | yes `$100` | +2.13% | 2.41 | +73.53% | profit_target | RIF=28;ONE=5;SPELL=1 |
| 30d | continuous | 426 | +2.06% | $1020.59 | $20.59 | no `$100` | +39.41% | 1.02 | +73.71% | period_end | ONE=298;RIF=109;SPELL=19 |
| 30d | cashflow_stop | 335 | -39.29% | $607.12 | $0.00 | no `$100` | +39.41% | 0.49 | +71.64% | loss_stop | ONE=272;RIF=54;SPELL=9 |
| 60d | continuous | 1343 | -15.95% | $840.52 | $0.00 | no `$100` | +53.66% | 0.91 | +73.19% | period_end | ONE=1023;RIF=290;SPELL=30 |
| 60d | cashflow_stop | 1245 | -45.20% | $547.99 | $0.00 | no `$100` | +49.21% | 0.72 | +72.61% | loss_stop | ONE=997;RIF=231;SPELL=17 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | RIF | RIF 5m LONG Best | 3 | 3 | +100.00% | 3 | +0.94% | 1.95 | +66.67% | take_profit=2;time_stop=1 |
| 7d | ONE | ONE 11.2 | 14 | 12 | +85.71% | 10 | +0.09% | 1.19 | +80.00% | take_profit=8;time_stop=2 |
| 7d | RIF | RIF 5m LONG Best | 56 | 41 | +73.21% | 41 | +16.05% | 2.25 | +75.61% | take_profit=30;time_stop=11 |
| 7d | SPELL | SPELL SHORT Best | 1 | 1 | +100.00% | 1 | +0.96% | inf | +100.00% | take_profit=1 |
| 30d | ONE | ONE 11.2 | 1506 | 514 | +34.13% | 298 | -11.16% | 0.54 | +75.17% | take_profit=217;time_stop=78;stop_loss=3 |
| 30d | RIF | RIF 5m LONG Best | 147 | 109 | +74.15% | 109 | +34.18% | 1.95 | +69.72% | take_profit=73;time_stop=36 |
| 30d | SPELL | SPELL SHORT Best | 23 | 19 | +82.61% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | ONE | ONE 11.2 | 5325 | 1804 | +33.88% | 1023 | -29.21% | 0.62 | +76.83% | take_profit=762;time_stop=253;stop_loss=8 |
| 60d | RIF | RIF 5m LONG Best | 380 | 290 | +76.32% | 290 | +28.38% | 1.22 | +61.72% | take_profit=161;time_stop=128;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_fresh_strict_journal_2026-05-10.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_fresh_strict_summary_2026-05-10.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_fresh_strict_modules_2026-05-10.csv`
