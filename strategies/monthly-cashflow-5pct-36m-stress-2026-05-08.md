# Monthly Cashflow 5% 36M Stress

Generated: 2026-05-08T18:21:42.577976+00:00

Strategy: `GALA 40% / SPELL 60%`, scale `6x`, monthly target `$50`, monthly loss stop `30%`.

The base trade pool already includes maker fee `0.02%` per side and zero slippage. Stress scenarios subtract extra cost from the raw trade return before portfolio weights and scale are applied.

## Stress Summary

| Scenario | $50+ Months | Net | MaxDD | PF | Worst Month | Trades | Fill Skips | Funding |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base_fee002_slip0` | 36/36 | $2265.58 | +32.90% | 1.43 | $50.25 | 2092 | 0 | 0.00% |
| `base_plus_funding` | 36/36 | $2268.98 | +32.96% | 1.43 | $50.11 | 2093 | 0 | -2.84% |
| `fee0025_slip0` | 35/36 | $2216.45 | +39.27% | 1.36 | $-341.51 | 2303 | 0 | 0.00% |
| `fee003_slip0` | 32/36 | $1999.80 | +45.09% | 1.21 | $-357.91 | 3569 | 0 | 0.00% |
| `fee004_slip0` | 0/36 | $-998.53 | +99.91% | 0.70 | $-238.16 | 13024 | 0 | 0.00% |
| `fee004_slip0005` | 0/36 | $-999.50 | +99.97% | 0.67 | $-242.41 | 12725 | 0 | 0.00% |
| `fee004_slip001` | 0/36 | $-999.76 | +99.98% | 0.65 | $-246.91 | 12498 | 0 | 0.00% |
| `taker_like_fee004_slip002` | 0/36 | $-999.96 | +100.00% | 0.61 | $-265.92 | 11263 | 0 | 0.00% |
| `fee004_slip001_plus_funding` | 0/36 | $-999.77 | +99.98% | 0.65 | $-246.29 | 12475 | 0 | -2.84% |
| `miss_5pct_winners` | 6/36 | $-588.67 | +98.98% | 0.90 | $-396.63 | 13208 | 682 | 0.00% |
| `miss_10pct_winners` | 0/36 | $-996.07 | +99.86% | 0.73 | $-219.45 | 11968 | 1401 | 0.00% |
| `miss_20pct_winners` | 4/36 | $-793.86 | +99.95% | 0.76 | $-310.98 | 9547 | 2738 | 0.00% |

## Liquidation / Margin Approximation

| Item | Value |
|---|---:|
| SPELL effective exposure | `3.60x` |
| GALA short effective exposure | `0.86x` |
| GALA long effective exposure | `0.43x` |
| SPELL cross-equivalent liquidation distance | `27.28%` |
| Isolated 6x approximate liquidation distance | `16.17%` |

Interpretation: if this is traded as isolated `6x`, a roughly `16%` adverse move can become dangerous before stop execution. If traded cross with effective SPELL exposure around `3.6x`, the rough distance is wider, around `27%`, but the whole account is at risk.

## Monthly For Base Scenario

| Month | PnL | Withdrawal | Stop | Trades | Top Coins |
|---|---:|---:|---|---:|---|
| 2023-05 | $52.99 | $52.99 | cash_target | 25 | `[('GALA', 24), ('SPELL', 1)]` |
| 2023-06 | $50.65 | $50.65 | cash_target | 31 | `[('GALA', 29), ('SPELL', 2)]` |
| 2023-07 | $51.67 | $51.67 | cash_target | 36 | `[('GALA', 30), ('SPELL', 6)]` |
| 2023-08 | $51.75 | $51.75 | cash_target | 15 | `[('GALA', 13), ('SPELL', 2)]` |
| 2023-09 | $76.38 | $76.38 | cash_target | 51 | `[('GALA', 47), ('SPELL', 4)]` |
| 2023-10 | $67.32 | $67.32 | cash_target | 10 | `[('GALA', 8), ('SPELL', 2)]` |
| 2023-11 | $73.29 | $73.29 | cash_target | 33 | `[('GALA', 28), ('SPELL', 5)]` |
| 2023-12 | $56.55 | $56.55 | cash_target | 17 | `[('GALA', 16), ('SPELL', 1)]` |
| 2024-01 | $66.81 | $66.81 | cash_target | 11 | `[('GALA', 8), ('SPELL', 3)]` |
| 2024-02 | $74.69 | $74.69 | cash_target | 28 | `[('GALA', 23), ('SPELL', 5)]` |
| 2024-03 | $51.74 | $51.74 | cash_target | 53 | `[('GALA', 53)]` |
| 2024-04 | $57.96 | $57.96 | cash_target | 4 | `[('GALA', 2), ('SPELL', 2)]` |
| 2024-05 | $50.25 | $50.25 | cash_target | 98 | `[('GALA', 87), ('SPELL', 11)]` |
| 2024-06 | $62.83 | $62.83 | cash_target | 119 | `[('GALA', 91), ('SPELL', 28)]` |
| 2024-07 | $84.84 | $84.84 | cash_target | 15 | `[('GALA', 13), ('SPELL', 2)]` |
| 2024-08 | $55.58 | $55.58 | cash_target | 79 | `[('GALA', 67), ('SPELL', 12)]` |
| 2024-09 | $50.62 | $50.62 | cash_target | 79 | `[('GALA', 66), ('SPELL', 13)]` |
| 2024-10 | $69.81 | $69.81 | cash_target | 51 | `[('GALA', 44), ('SPELL', 7)]` |
| 2024-11 | $66.01 | $66.01 | cash_target | 164 | `[('GALA', 144), ('SPELL', 20)]` |
| 2024-12 | $70.33 | $70.33 | cash_target | 2 | `[('SPELL', 2)]` |
| 2025-01 | $80.81 | $80.81 | cash_target | 36 | `[('GALA', 33), ('SPELL', 3)]` |
| 2025-02 | $78.16 | $78.16 | cash_target | 25 | `[('GALA', 23), ('SPELL', 2)]` |
| 2025-03 | $64.73 | $64.73 | cash_target | 29 | `[('GALA', 24), ('SPELL', 5)]` |
| 2025-04 | $80.62 | $80.62 | cash_target | 99 | `[('GALA', 84), ('SPELL', 15)]` |
| 2025-05 | $50.27 | $50.27 | cash_target | 118 | `[('GALA', 93), ('SPELL', 25)]` |
| 2025-06 | $64.84 | $64.84 | cash_target | 29 | `[('GALA', 23), ('SPELL', 6)]` |
| 2025-07 | $51.52 | $51.52 | cash_target | 8 | `[('GALA', 6), ('SPELL', 2)]` |
| 2025-08 | $57.69 | $57.69 | cash_target | 51 | `[('GALA', 44), ('SPELL', 7)]` |
| 2025-09 | $82.74 | $82.74 | cash_target | 44 | `[('GALA', 41), ('SPELL', 3)]` |
| 2025-10 | $79.47 | $79.47 | cash_target | 52 | `[('GALA', 47), ('SPELL', 5)]` |
| 2025-11 | $52.30 | $52.30 | cash_target | 57 | `[('GALA', 54), ('SPELL', 3)]` |
| 2025-12 | $50.73 | $50.73 | cash_target | 114 | `[('GALA', 112), ('SPELL', 2)]` |
| 2026-01 | $70.88 | $70.88 | cash_target | 90 | `[('GALA', 86), ('SPELL', 4)]` |
| 2026-02 | $55.72 | $55.72 | cash_target | 231 | `[('GALA', 212), ('SPELL', 19)]` |
| 2026-03 | $51.44 | $51.44 | cash_target | 111 | `[('GALA', 111)]` |
| 2026-04 | $51.59 | $51.59 | cash_target | 77 | `[('GALA', 76), ('SPELL', 1)]` |

## Files

- Summary CSV: `data/monthly_cashflow_5pct_36m_highrisk_stress_summary_2026-05-08.csv`
- Monthly CSV: `data/monthly_cashflow_5pct_36m_highrisk_stress_monthly_2026-05-08.csv`
