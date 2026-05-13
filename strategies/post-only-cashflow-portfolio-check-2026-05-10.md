# Post-Only Cashflow Portfolio Check

Generated: 2026-05-10T15:29:39.984116+00:00

Проверка только по нужным cashflow-связкам.

Важно: входной trade-pool уже содержит только сделки, которые были исполнены как maker-limit/post-only rows. Поэтому `candidate_post_only_rows` - это не все сигналы, а уже реально заполненные исторические лимитные входы в пуле.

| Portfolio | Scenario | Scale | Loss stop | Post-only rows | Accepted trades | Hits | Net | MaxDD | PF | Worst month |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ONE/RIF/SPELL 10% v2 max50 | `base_fee002_slip0` | 10.00 | 50% | 13633 | 4156 | 24/24 | $3,238.86 | 52.21% | 1.33 | $100.04 |
| ONE/RIF/SPELL 10% v2 max50 | `fee003_slip0` | 10.00 | 50% | 13633 | 4782 | 23/24 | $3,204.92 | 55.91% | 1.30 | $16.32 |
| ONE/RIF/SPELL 10% v2 max50 | `fee003_slip0005` | 10.00 | 50% | 13633 | 4795 | 22/24 | $2,910.58 | 58.97% | 1.27 | $-40.61 |
| ONE/RIF/SPELL 10% v2 max50 | `fee004_slip0` | 10.00 | 50% | 13633 | 9619 | 11/24 | $684.65 | 94.04% | 1.05 | $-536.00 |
| ONE/RIF/SPELL 10% v2 max100 | `base_fee002_slip0` | 10.00 | 50% | 13633 | 4537 | 24/24 | $3,219.18 | 51.04% | 1.32 | $100.79 |
| ONE/RIF/SPELL 10% v2 max100 | `fee003_slip0` | 10.00 | 50% | 13633 | 5176 | 23/24 | $3,221.22 | 55.05% | 1.30 | $21.59 |
| ONE/RIF/SPELL 10% v2 max100 | `fee003_slip0005` | 10.00 | 50% | 13633 | 5189 | 22/24 | $2,913.17 | 58.31% | 1.27 | $-41.66 |
| ONE/RIF/SPELL 10% v2 max100 | `fee004_slip0` | 10.00 | 50% | 13633 | 10381 | 11/24 | $688.86 | 94.17% | 1.05 | $-536.00 |
| CHZ/MANA/RIF/SPELL 4% v2 exact-best | `base_fee002_slip0` | 8.00 | 50% | 3617 | 946 | 20/24 | $1,082.93 | 58.34% | 1.14 | $-300.19 |
| CHZ/MANA/RIF/SPELL 4% v2 exact-best | `fee003_slip0` | 8.00 | 50% | 3617 | 925 | 20/24 | $991.47 | 62.10% | 1.13 | $-327.28 |
| CHZ/MANA/RIF/SPELL 4% v2 exact-best | `fee003_slip0005` | 8.00 | 50% | 3617 | 971 | 20/24 | $975.34 | 63.85% | 1.13 | $-340.44 |
| CHZ/MANA/RIF/SPELL 4% v2 exact-best | `fee004_slip0` | 8.00 | 50% | 3617 | 2616 | 3/24 | $-618.54 | 95.81% | 0.93 | $-353.35 |

## Files

- Summary CSV: `data/post_only_cashflow_portfolio_check_2026-05-10.csv`
- Monthly CSV: `data/post_only_cashflow_portfolio_check_monthly_2026-05-10.csv`
