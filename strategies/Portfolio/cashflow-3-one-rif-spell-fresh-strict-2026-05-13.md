# Cashflow 3 Fresh Strict Check

Generated: `2026-05-13T15:30:26.039376+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 2 | +0.10% | $1001.03 | $1.03 | no `$100` | +0.00% | inf | +100.00% | period_end | ONE=2 |
| 1d | cashflow_stop | 2 | +0.10% | $1001.03 | $1.03 | no `$100` | +0.00% | inf | +100.00% | period_end | ONE=2 |
| 7d | continuous | 21 | +5.61% | $1056.14 | $56.14 | no `$100` | +0.84% | 4.02 | +85.71% | period_end | RIF=14;ONE=7 |
| 7d | cashflow_stop | 21 | +5.61% | $1056.14 | $56.14 | no `$100` | +0.84% | 4.02 | +85.71% | period_end | RIF=14;ONE=7 |
| 30d | continuous | 359 | +5.84% | $1058.42 | $58.42 | no `$100` | +38.38% | 1.07 | +75.49% | period_end | ONE=236;RIF=104;SPELL=19 |
| 30d | cashflow_stop | 266 | -37.10% | $628.98 | $0.00 | no `$100` | +38.38% | 0.49 | +73.31% | loss_stop | ONE=208;RIF=49;SPELL=9 |
| 60d | continuous | 1253 | -13.32% | $866.83 | $0.00 | no `$100` | +53.66% | 0.92 | +73.82% | period_end | ONE=953;RIF=270;SPELL=30 |
| 60d | cashflow_stop | 136 | +10.21% | $1102.12 | $102.12 | yes `$100` | +3.15% | 1.94 | +77.94% | profit_target | ONE=106;RIF=26;SPELL=4 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | ONE | ONE 11.2 | 5 | 2 | +40.00% | 2 | +0.16% | inf | +100.00% | take_profit=2 |
| 7d | ONE | ONE 11.2 | 13 | 8 | +61.54% | 7 | -0.04% | 0.92 | +85.71% | take_profit=6;time_stop=1 |
| 7d | RIF | RIF 5m LONG Best | 19 | 14 | +73.68% | 14 | +8.36% | 4.71 | +85.71% | take_profit=11;time_stop=3 |
| 30d | ONE | ONE 11.2 | 1185 | 403 | +34.01% | 236 | -8.56% | 0.56 | +77.12% | take_profit=177;time_stop=56;stop_loss=3 |
| 30d | RIF | RIF 5m LONG Best | 141 | 104 | +73.76% | 104 | +37.07% | 2.15 | +72.12% | take_profit=72;time_stop=32 |
| 30d | SPELL | SPELL SHORT Best | 22 | 19 | +86.36% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | ONE | ONE 11.2 | 4962 | 1652 | +33.29% | 953 | -24.48% | 0.64 | +77.54% | take_profit=717;time_stop=229;stop_loss=7 |
| 60d | RIF | RIF 5m LONG Best | 358 | 270 | +75.42% | 270 | +28.21% | 1.24 | +62.22% | take_profit=150;time_stop=119;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_fresh_strict_journal_2026-05-13.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_fresh_strict_summary_2026-05-13.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_fresh_strict_modules_2026-05-13.csv`
