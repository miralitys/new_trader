# Monthly Cashflow 5% Robust Search

Generated: `2026-05-08T18:59:07.350078+00:00`

Цель: найти смесь стратегий, которая дает `$50+` в месяц на стартовом балансе `$1000` за 36 месяцев и не разваливается от ухудшения комиссии/исполнения.

Важно: это поиск по уже готовому пулу сделок. База уже содержит maker fee `0.02%` за сторону и `0` slippage; стресс добавляет extra-cost поверх базы.

## Поисковая настройка

- Trade pool: `data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv`
- Period: `2023-05` - `2026-04`
- Search stress: `fee003_slip0`
- Target: `$50.00` per month

## Лучшие кандидаты в поисковом stress-сценарии

| # | Name | Weights | Scale | Loss Stop | $50+ Months | Net | MaxDD | PF | Worst Month | Trades |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `ANKR10_GALA10_SPELL80` | `ANKR:0.10;GALA:0.10;SPELL:0.80` | 6.00 | 0.30 | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| 2 | `ANKR10_GALA10_SPELL80` | `ANKR:0.10;GALA:0.10;SPELL:0.80` | 6.00 | 0.35 | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| 3 | `ANKR10_GALA10_SPELL80` | `ANKR:0.10;GALA:0.10;SPELL:0.80` | 6.00 | 0.40 | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| 4 | `ANKR10_GALA10_SPELL80` | `ANKR:0.10;GALA:0.10;SPELL:0.80` | 6.00 | 0.50 | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| 5 | `CHZ10_GALA10_SPELL80` | `CHZ:0.10;GALA:0.10;SPELL:0.80` | 10.00 | 0.50 | 36/36 | $2863.45 | +52.90% | 1.48 | $50.01 | 1859 |
| 6 | `GALA30_SPELL70` | `GALA:0.30;SPELL:0.70` | 6.00 | 0.35 | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| 7 | `GALA30_SPELL70` | `GALA:0.30;SPELL:0.70` | 6.00 | 0.40 | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| 8 | `GALA30_SPELL70` | `GALA:0.30;SPELL:0.70` | 6.00 | 0.50 | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| 9 | `ANKR10_CHZ10_SPELL80` | `ANKR:0.10;CHZ:0.10;SPELL:0.80` | 8.00 | 0.40 | 36/36 | $2540.78 | +42.77% | 1.44 | $50.74 | 621 |
| 10 | `ANKR10_CHZ10_SPELL80` | `ANKR:0.10;CHZ:0.10;SPELL:0.80` | 8.00 | 0.50 | 36/36 | $2540.78 | +42.77% | 1.44 | $50.74 | 621 |
| 11 | `GALA15_SAND15_SPELL70` | `GALA:0.15;SAND:0.15;SPELL:0.70` | 6.00 | 0.30 | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| 12 | `GALA15_SAND15_SPELL70` | `GALA:0.15;SAND:0.15;SPELL:0.70` | 6.00 | 0.35 | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| 13 | `GALA15_SAND15_SPELL70` | `GALA:0.15;SAND:0.15;SPELL:0.70` | 6.00 | 0.40 | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| 14 | `GALA15_SAND15_SPELL70` | `GALA:0.15;SAND:0.15;SPELL:0.70` | 6.00 | 0.50 | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| 15 | `GALA20_SPELL80` | `GALA:0.20;SPELL:0.80` | 6.00 | 0.35 | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| 16 | `GALA20_SPELL80` | `GALA:0.20;SPELL:0.80` | 6.00 | 0.40 | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| 17 | `GALA20_SPELL80` | `GALA:0.20;SPELL:0.80` | 6.00 | 0.50 | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| 18 | `GALA20_SPELL80` | `GALA:0.20;SPELL:0.80` | 8.00 | 0.50 | 36/36 | $2648.83 | +47.93% | 1.42 | $50.58 | 2025 |
| 19 | `GALA20_MANA20_SPELL60` | `GALA:0.20;MANA:0.20;SPELL:0.60` | 8.00 | 0.40 | 36/36 | $2503.31 | +42.20% | 1.41 | $50.15 | 2231 |
| 20 | `GALA20_MANA20_SPELL60` | `GALA:0.20;MANA:0.20;SPELL:0.60` | 8.00 | 0.50 | 36/36 | $2503.31 | +42.20% | 1.41 | $50.15 | 2231 |

## Проверка топ-кандидатов по сценариям

| Candidate | Scenario | $50+ Months | Net | MaxDD | PF | Worst Month | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `base_fee002_slip0` | 36/36 | $2508.23 | +34.48% | 1.48 | $50.12 | 3071 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `fee0025_slip0` | 36/36 | $2605.27 | +34.90% | 1.49 | $50.03 | 3106 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `fee003_slip0` | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `fee003_slip0005` | 32/36 | $2342.52 | +61.48% | 1.30 | $-302.00 | 4709 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `fee004_slip0` | 30/36 | $2137.34 | +64.23% | 1.25 | $-338.89 | 5096 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.30 | `miss_5pct_winners` | 32/36 | $2427.69 | +62.47% | 1.34 | $-310.48 | 4000 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `base_fee002_slip0` | 36/36 | $2508.23 | +34.48% | 1.48 | $50.12 | 3071 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `fee0025_slip0` | 36/36 | $2605.27 | +34.90% | 1.49 | $50.03 | 3106 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `fee003_slip0` | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `fee003_slip0005` | 32/36 | $2310.47 | +64.22% | 1.29 | $-351.69 | 4778 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `fee004_slip0` | 29/36 | $2079.53 | +66.96% | 1.24 | $-365.96 | 5181 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.35 | `miss_5pct_winners` | 32/36 | $2410.11 | +64.71% | 1.33 | $-351.73 | 4069 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2508.23 | +34.48% | 1.48 | $50.12 | 3071 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2605.27 | +34.90% | 1.49 | $50.03 | 3106 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `fee003_slip0` | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `fee003_slip0005` | 31/36 | $2225.48 | +68.70% | 1.28 | $-432.96 | 4820 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `fee004_slip0` | 29/36 | $2096.91 | +71.15% | 1.22 | $-451.70 | 5515 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.40 | `miss_5pct_winners` | 31/36 | $2344.09 | +70.24% | 1.33 | $-453.24 | 4111 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2508.23 | +34.48% | 1.48 | $50.12 | 3071 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2605.27 | +34.90% | 1.49 | $50.03 | 3106 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `fee003_slip0` | 36/36 | $2693.93 | +35.28% | 1.48 | $50.42 | 3185 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `fee003_slip0005` | 31/36 | $2257.79 | +73.95% | 1.30 | $-527.98 | 4853 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `fee004_slip0` | 22/36 | $1375.51 | +76.00% | 1.10 | $-537.08 | 10670 |
| `ANKR10_GALA10_SPELL80` scale 6.00 loss 0.50 | `miss_5pct_winners` | 31/36 | $2310.76 | +75.17% | 1.33 | $-543.90 | 4138 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2758.38 | +51.58% | 1.47 | $50.15 | 1763 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2656.16 | +52.05% | 1.45 | $50.26 | 1804 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0` | 36/36 | $2863.45 | +52.90% | 1.48 | $50.01 | 1859 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0005` | 35/36 | $2758.20 | +53.37% | 1.34 | $27.83 | 3734 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `fee004_slip0` | 0/36 | $-999.99 | +100.00% | 0.65 | $-393.41 | 15371 |
| `CHZ10_GALA10_SPELL80` scale 10.00 loss 0.50 | `miss_5pct_winners` | 36/36 | $2722.16 | +51.32% | 1.42 | $50.34 | 2005 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `base_fee002_slip0` | 36/36 | $2355.36 | +35.21% | 1.45 | $50.06 | 2127 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `fee0025_slip0` | 36/36 | $2457.45 | +35.89% | 1.47 | $50.26 | 2171 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `fee003_slip0` | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `fee003_slip0005` | 35/36 | $2346.38 | +45.46% | 1.30 | $-405.57 | 3460 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `fee004_slip0` | 0/36 | $-998.22 | +99.93% | 0.69 | $-232.00 | 14253 |
| `GALA30_SPELL70` scale 6.00 loss 0.35 | `miss_5pct_winners` | 31/36 | $2077.86 | +68.05% | 1.28 | $-398.20 | 3190 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2355.36 | +35.21% | 1.45 | $50.06 | 2127 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2457.45 | +35.89% | 1.47 | $50.26 | 2171 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `fee003_slip0` | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `fee003_slip0005` | 35/36 | $2346.38 | +45.46% | 1.30 | $-405.57 | 3460 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `fee004_slip0` | 0/36 | $-999.32 | +99.97% | 0.70 | $-232.00 | 14638 |
| `GALA30_SPELL70` scale 6.00 loss 0.40 | `miss_5pct_winners` | 24/36 | $1608.81 | +75.13% | 1.14 | $-483.97 | 7851 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2355.36 | +35.21% | 1.45 | $50.06 | 2127 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2457.45 | +35.89% | 1.47 | $50.26 | 2171 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `fee003_slip0` | 36/36 | $2375.47 | +36.42% | 1.45 | $50.12 | 2206 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `fee003_slip0005` | 35/36 | $2333.15 | +56.38% | 1.30 | $-524.58 | 3498 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `fee004_slip0` | 0/36 | $-999.65 | +99.99% | 0.71 | $-232.00 | 15547 |
| `GALA30_SPELL70` scale 6.00 loss 0.50 | `miss_5pct_winners` | 25/36 | $1667.74 | +74.07% | 1.14 | $-511.59 | 8050 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2570.49 | +41.59% | 1.46 | $50.06 | 611 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2646.93 | +41.72% | 1.46 | $51.61 | 620 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `fee003_slip0` | 36/36 | $2540.78 | +42.77% | 1.44 | $50.74 | 621 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `fee003_slip0005` | 36/36 | $2518.95 | +43.25% | 1.43 | $50.49 | 637 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `fee004_slip0` | 31/36 | $2231.12 | +78.49% | 1.25 | $-490.17 | 1010 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.40 | `miss_5pct_winners` | 28/36 | $1870.42 | +77.03% | 1.19 | $-474.45 | 1100 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2570.49 | +41.59% | 1.46 | $50.06 | 611 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2646.93 | +41.72% | 1.46 | $51.61 | 620 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `fee003_slip0` | 36/36 | $2540.78 | +42.77% | 1.44 | $50.74 | 621 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2518.95 | +43.25% | 1.43 | $50.49 | 637 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `fee004_slip0` | 31/36 | $2269.63 | +82.12% | 1.26 | $-576.23 | 1021 |
| `ANKR10_CHZ10_SPELL80` scale 8.00 loss 0.50 | `miss_5pct_winners` | 15/36 | $38.07 | +99.30% | 1.01 | $-592.81 | 2266 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `base_fee002_slip0` | 36/36 | $2395.97 | +31.20% | 1.44 | $50.02 | 3075 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `fee0025_slip0` | 36/36 | $2459.95 | +32.00% | 1.45 | $50.05 | 3124 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `fee003_slip0` | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `fee003_slip0005` | 35/36 | $2315.18 | +32.91% | 1.38 | $12.09 | 4025 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `fee004_slip0` | 4/36 | $-739.32 | +99.55% | 0.86 | $-317.75 | 14239 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.30 | `miss_5pct_winners` | 36/36 | $2409.50 | +31.53% | 1.41 | $50.19 | 3293 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `base_fee002_slip0` | 36/36 | $2395.97 | +31.20% | 1.44 | $50.02 | 3075 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `fee0025_slip0` | 36/36 | $2459.95 | +32.00% | 1.45 | $50.05 | 3124 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `fee003_slip0` | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `fee003_slip0005` | 35/36 | $2315.18 | +32.91% | 1.38 | $12.09 | 4025 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `fee004_slip0` | 4/36 | $-745.76 | +99.74% | 0.84 | $-433.93 | 14573 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.35 | `miss_5pct_winners` | 36/36 | $2409.50 | +31.53% | 1.41 | $50.19 | 3293 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2395.97 | +31.20% | 1.44 | $50.02 | 3075 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2459.95 | +32.00% | 1.45 | $50.05 | 3124 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `fee003_slip0` | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `fee003_slip0005` | 35/36 | $2315.18 | +32.91% | 1.38 | $12.09 | 4025 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `fee004_slip0` | 4/36 | $-747.26 | +99.81% | 0.84 | $-433.93 | 14932 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.40 | `miss_5pct_winners` | 36/36 | $2409.50 | +31.53% | 1.41 | $50.19 | 3293 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2395.97 | +31.20% | 1.44 | $50.02 | 3075 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2459.95 | +32.00% | 1.45 | $50.05 | 3124 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `fee003_slip0` | 36/36 | $2439.57 | +32.23% | 1.44 | $50.04 | 3237 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `fee003_slip0005` | 35/36 | $2315.18 | +32.91% | 1.38 | $12.09 | 4025 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `fee004_slip0` | 4/36 | $-751.03 | +99.93% | 0.85 | $-457.97 | 15811 |
| `GALA15_SAND15_SPELL70` scale 6.00 loss 0.50 | `miss_5pct_winners` | 36/36 | $2409.50 | +31.53% | 1.41 | $50.19 | 3293 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `base_fee002_slip0` | 36/36 | $2525.94 | +37.63% | 1.50 | $50.00 | 2086 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `fee0025_slip0` | 36/36 | $2498.68 | +38.01% | 1.44 | $50.09 | 2921 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `fee003_slip0` | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `fee003_slip0005` | 36/36 | $2598.46 | +38.98% | 1.44 | $50.03 | 3283 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `fee004_slip0` | 34/36 | $2529.81 | +42.04% | 1.32 | $-364.94 | 5317 |
| `GALA20_SPELL80` scale 6.00 loss 0.35 | `miss_5pct_winners` | 36/36 | $2538.41 | +37.77% | 1.42 | $50.00 | 3057 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2525.94 | +37.63% | 1.50 | $50.00 | 2086 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2498.68 | +38.01% | 1.44 | $50.09 | 2921 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `fee003_slip0` | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `fee003_slip0005` | 36/36 | $2598.46 | +38.98% | 1.44 | $50.03 | 3283 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `fee004_slip0` | 34/36 | $2546.43 | +49.88% | 1.28 | $-450.82 | 5596 |
| `GALA20_SPELL80` scale 6.00 loss 0.40 | `miss_5pct_winners` | 36/36 | $2538.41 | +37.77% | 1.42 | $50.00 | 3057 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2525.94 | +37.63% | 1.50 | $50.00 | 2086 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2498.68 | +38.01% | 1.44 | $50.09 | 2921 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `fee003_slip0` | 36/36 | $2445.93 | +38.40% | 1.43 | $50.00 | 2972 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2598.46 | +38.98% | 1.44 | $50.03 | 3283 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `fee004_slip0` | 34/36 | $2560.10 | +57.51% | 1.29 | $-534.40 | 5621 |
| `GALA20_SPELL80` scale 6.00 loss 0.50 | `miss_5pct_winners` | 36/36 | $2538.41 | +37.77% | 1.42 | $50.00 | 3057 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2572.66 | +46.57% | 1.41 | $50.11 | 1930 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2516.44 | +47.19% | 1.40 | $50.24 | 1967 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `fee003_slip0` | 36/36 | $2648.83 | +47.93% | 1.42 | $50.58 | 2025 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2550.14 | +48.18% | 1.35 | $50.32 | 3071 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `fee004_slip0` | 35/36 | $2429.65 | +48.89% | 1.27 | $-49.05 | 5025 |
| `GALA20_SPELL80` scale 8.00 loss 0.50 | `miss_5pct_winners` | 36/36 | $2539.52 | +46.79% | 1.37 | $50.19 | 2129 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2409.01 | +41.00% | 1.41 | $50.11 | 2116 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2546.66 | +41.67% | 1.42 | $50.15 | 2183 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `fee003_slip0` | 36/36 | $2503.31 | +42.20% | 1.41 | $50.15 | 2231 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `fee003_slip0005` | 36/36 | $2488.66 | +42.77% | 1.37 | $50.00 | 3080 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `fee004_slip0` | 15/36 | $43.27 | +97.66% | 1.01 | $-467.10 | 12137 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.40 | `miss_5pct_winners` | 15/36 | $306.76 | +96.77% | 1.04 | $-472.75 | 11606 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2409.01 | +41.00% | 1.41 | $50.11 | 2116 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2546.66 | +41.67% | 1.42 | $50.15 | 2183 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `fee003_slip0` | 36/36 | $2503.31 | +42.20% | 1.41 | $50.15 | 2231 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2488.66 | +42.77% | 1.37 | $50.00 | 3080 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `fee004_slip0` | 15/36 | $8.81 | +98.89% | 1.00 | $-518.41 | 12537 |
| `GALA20_MANA20_SPELL60` scale 8.00 loss 0.50 | `miss_5pct_winners` | 15/36 | $185.37 | +98.35% | 1.02 | $-505.28 | 12124 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `base_fee002_slip0` | 36/36 | $2481.22 | +37.84% | 1.42 | $50.20 | 2188 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `fee0025_slip0` | 36/36 | $2452.29 | +38.55% | 1.41 | $50.14 | 2249 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `fee003_slip0` | 36/36 | $2445.38 | +39.13% | 1.40 | $50.30 | 2352 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `fee003_slip0005` | 36/36 | $2500.00 | +39.72% | 1.36 | $50.00 | 3221 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `fee004_slip0` | 15/36 | $30.05 | +97.20% | 1.00 | $-364.56 | 12360 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.35 | `miss_5pct_winners` | 32/36 | $2137.62 | +66.34% | 1.24 | $-355.28 | 3343 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `base_fee002_slip0` | 36/36 | $2481.22 | +37.84% | 1.42 | $50.20 | 2188 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `fee0025_slip0` | 36/36 | $2452.29 | +38.55% | 1.41 | $50.14 | 2249 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `fee003_slip0` | 36/36 | $2445.38 | +39.13% | 1.40 | $50.30 | 2352 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `fee003_slip0005` | 36/36 | $2500.00 | +39.72% | 1.36 | $50.00 | 3221 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `fee004_slip0` | 15/36 | $-3.26 | +98.23% | 1.00 | $-469.85 | 12553 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.40 | `miss_5pct_winners` | 15/36 | $275.43 | +96.80% | 1.03 | $-478.99 | 11987 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2481.22 | +37.84% | 1.42 | $50.20 | 2188 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2452.29 | +38.55% | 1.41 | $50.14 | 2249 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `fee003_slip0` | 36/36 | $2445.38 | +39.13% | 1.40 | $50.30 | 2352 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2500.00 | +39.72% | 1.36 | $50.00 | 3221 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `fee004_slip0` | 15/36 | $-31.45 | +99.10% | 1.00 | $-512.86 | 12928 |
| `GALA20_MANA10_SAND10_SPELL60` scale 8.00 loss 0.50 | `miss_5pct_winners` | 15/36 | $143.24 | +98.51% | 1.02 | $-502.95 | 12517 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2867.02 | +49.40% | 1.41 | $51.39 | 602 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2704.29 | +50.04% | 1.39 | $50.62 | 605 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0` | 36/36 | $2754.82 | +50.92% | 1.39 | $50.45 | 610 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2720.73 | +51.34% | 1.38 | $50.03 | 630 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `fee004_slip0` | 31/36 | $2333.00 | +88.30% | 1.26 | $-602.95 | 902 |
| `ANKR10_CHZ10_SPELL80` scale 10.00 loss 0.50 | `miss_5pct_winners` | 15/36 | $253.48 | +99.70% | 1.03 | $-552.94 | 2190 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `base_fee002_slip0` | 36/36 | $2690.47 | +50.01% | 1.37 | $50.13 | 702 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `fee0025_slip0` | 36/36 | $2792.51 | +50.61% | 1.39 | $51.11 | 723 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0` | 36/36 | $2821.92 | +51.22% | 1.39 | $51.23 | 734 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `fee003_slip0005` | 36/36 | $2820.75 | +51.81% | 1.39 | $50.05 | 740 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `fee004_slip0` | 36/36 | $2741.28 | +52.42% | 1.32 | $50.15 | 900 |
| `CHZ10_SHIB10_SPELL80` scale 10.00 loss 0.50 | `miss_5pct_winners` | 36/36 | $2777.53 | +49.78% | 1.35 | $50.13 | 765 |

## Вывод

Найден кандидат, который держит `36/36` месяцев даже в stress-сценарии `fee003_slip0`:

- `GALA15_SAND15_SPELL70`
- веса: `GALA:0.15;SAND:0.15;SPELL:0.70`
- scale: `6.00`
- monthly loss stop: `0.30`
- MaxDD в stress: `+32.23%`
- PF в stress: `1.44`

Но перед live его все равно надо отдельно проверить на свежих 24h/7d и strict maker-fill.

## Files

- Search summary CSV: `data/monthly_cashflow_5pct_36m_robust_quad_summary_2026-05-08.csv`
- Scenario summary CSV: `data/monthly_cashflow_5pct_36m_robust_quad_eval_summary_2026-05-08.csv`
- Scenario monthly CSV: `data/monthly_cashflow_5pct_36m_robust_quad_eval_monthly_2026-05-08.csv`
