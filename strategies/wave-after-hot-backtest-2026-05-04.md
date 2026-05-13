# Wave After Hot Backtest

Это проверка не по принципу `торговать весь год`, а по принципу `scanner увидел hot-режим, что было дальше`.

В каждом историческом дне scanner видел только прошлые свечи. После hot-сигнала стратегия включалась на будущие 7/14/30/60 дней.

## Status Counts

| Status | Count |
|---|---:|
| wave_candidate | 3 |
| fresh_wave_watch | 2 |
| maker_only_wave | 10 |
| weak_wave | 36 |

## Data Counts

| Status | Count |
|---|---:|
| ok | 51 |

## Symbol Summary

| Symbol | Decision | Events | Direction | Strict 14d avg | Strict 14d win | Strict 30d avg | Strict 30d worst | Taker 7d avg |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `MEGAUSDT` | fresh_wave_watch | 2 | long | +18.32% | 100.00% | n/a | n/a | +11.00% |
| `IRYSUSDT` | wave_candidate | 11 | long | +12.82% | 70.00% | +17.30% | -17.29% | +0.91% |
| `GUAUSDT` | wave_candidate | 8 | long | +10.23% | 100.00% | +27.23% | +19.55% | +4.47% |
| `RAVEUSDT` | fresh_wave_watch | 7 | short | +7.36% | 50.00% | -5.39% | -14.83% | +4.58% |
| `B2USDT` | wave_candidate | 19 | long | +4.24% | 63.16% | +7.71% | -19.27% | +1.06% |
| `IRUSDT` | maker_only_wave | 10 | short | +9.44% | 55.56% | +15.30% | -22.55% | -2.29% |
| `UBUSDT` | maker_only_wave | 16 | long | +1.82% | 46.67% | -1.44% | -34.25% | -0.76% |
| `OPENUSDT` | maker_only_wave | 9 | long | +1.80% | 66.67% | +1.19% | -18.21% | -0.22% |
| `MERLUSDT` | maker_only_wave | 24 | long | +1.62% | 52.17% | +0.46% | -10.76% | -0.46% |
| `SPACEUSDT` | maker_only_wave | 3 | long | +1.55% | 50.00% | n/a | n/a | -0.62% |
| `XNYUSDT` | maker_only_wave | 23 | long | +1.22% | 45.45% | +0.05% | -41.53% | -1.00% |
| `TURTLEUSDT` | maker_only_wave | 4 | long | +1.21% | 50.00% | +2.87% | -6.01% | -0.89% |
| `BLUAIUSDT` | maker_only_wave | 14 | long | +0.89% | 38.46% | +9.32% | -30.06% | -2.58% |
| `USUSDT` | maker_only_wave | 9 | long | +0.56% | 66.67% | -1.03% | -8.36% | -1.73% |
| `APEUSDT` | maker_only_wave | 33 | long | +0.09% | 46.88% | -6.17% | -27.53% | -1.88% |
| `EDUUSDT` | weak_wave | 45 | long | -0.13% | 40.91% | -1.00% | -27.47% | -0.73% |
| `MITOUSDT` | weak_wave | 9 | long | -0.41% | 55.56% | -0.40% | -26.13% | -3.41% |
| `PIEVERSEUSDT` | weak_wave | 10 | long | -0.69% | 44.44% | -8.67% | -17.62% | +0.09% |
| `TRADOORUSDT` | weak_wave | 18 | long | -0.89% | 52.94% | -2.38% | -34.76% | -2.31% |
| `DUSDT` | weak_wave | 24 | long | -1.00% | 47.83% | -4.25% | -38.51% | -2.29% |
| `DEXEUSDT` | weak_wave | 26 | short | -1.38% | 40.00% | -2.82% | -17.22% | -2.30% |
| `SHELLUSDT` | weak_wave | 28 | long | -1.60% | 39.29% | +0.89% | -28.60% | -3.29% |
| `GWEIUSDT` | weak_wave | 6 | short | -1.65% | 20.00% | -14.52% | -30.02% | -4.24% |
| `AIOUSDT` | weak_wave | 16 | long | -1.74% | 40.00% | -8.98% | -24.15% | -2.16% |
| `FIGHTUSDT` | weak_wave | 6 | long | -2.04% | 60.00% | +3.56% | -9.32% | -4.96% |
| `PARTIUSDT` | weak_wave | 26 | long | -2.51% | 46.15% | -7.12% | -34.23% | -3.89% |
| `RLCUSDT` | weak_wave | 32 | long | -2.62% | 40.62% | -5.12% | -22.28% | -2.53% |
| `4USDT` | weak_wave | 17 | long | -2.67% | 35.29% | -4.80% | -34.86% | -2.62% |
| `SPORTFUNUSDT` | weak_wave | 5 | long | -2.72% | 50.00% | -3.67% | -12.86% | -3.13% |
| `ZEREBROUSDT` | weak_wave | 38 | long | -2.94% | 37.84% | -11.70% | -33.08% | -1.10% |
| `AXLUSDT` | weak_wave | 42 | long | -3.06% | 41.46% | -8.08% | -31.00% | -2.73% |
| `BABYUSDT` | weak_wave | 20 | long | -3.21% | 40.00% | -8.95% | -24.79% | -3.68% |
| `BIOUSDT` | weak_wave | 37 | long | -3.25% | 30.56% | -6.99% | -37.01% | -4.62% |
| `VICUSDT` | weak_wave | 19 | long | -3.61% | 33.33% | -2.26% | -13.35% | -3.83% |
| `NOTUSDT` | weak_wave | 35 | short | -3.86% | 40.00% | -5.26% | -47.29% | -4.56% |
| `BBUSDT` | weak_wave | 52 | long | -3.91% | 31.37% | -10.15% | -28.78% | -3.70% |
| `AKEUSDT` | weak_wave | 18 | long | -4.23% | 35.29% | -5.59% | -31.54% | -3.98% |
| `RIFUSDT` | weak_wave | 30 | long | -4.32% | 31.03% | -6.66% | -27.18% | -2.64% |
| `ZENUSDT` | weak_wave | 45 | long | -4.34% | 26.67% | -10.30% | -52.29% | -3.11% |
| `ALCHUSDT` | weak_wave | 36 | long | -4.81% | 22.86% | -13.49% | -34.21% | -3.81% |
| `BICOUSDT` | weak_wave | 44 | short | -4.85% | 30.23% | -9.09% | -30.90% | -3.28% |
| `FHEUSDT` | weak_wave | 32 | long | -5.08% | 28.12% | -10.86% | -41.85% | -5.00% |
| `WLFIUSDT` | weak_wave | 11 | short | -5.12% | 27.27% | -5.54% | -20.05% | -7.35% |
| `LUMIAUSDT` | weak_wave | 27 | long | -5.25% | 15.38% | -10.95% | -25.04% | -5.27% |
| `REZUSDT` | weak_wave | 44 | long | -6.03% | 36.36% | -11.87% | -41.95% | -5.70% |
| `TAGUSDT` | weak_wave | 21 | short | -6.39% | 19.05% | -13.90% | -31.53% | -4.46% |
| `AKTUSDT` | weak_wave | 26 | long | -6.62% | 19.23% | -15.41% | -35.35% | -5.20% |
| `ACHUSDT` | weak_wave | 32 | long | -7.09% | 15.62% | -13.57% | -32.44% | -5.26% |
| `CHRUSDT` | weak_wave | 38 | long | -7.69% | 13.16% | -14.45% | -43.83% | -4.87% |
| `ZKJUSDT` | weak_wave | 22 | long | -8.57% | 23.81% | -17.80% | -39.63% | -4.65% |
| `TRIAUSDT` | weak_wave | 5 | long | -9.91% | 25.00% | -16.04% | -21.81% | -6.47% |

## Best Wave Candidates

| Symbol | Events | Strict 7d avg | Strict 14d avg | Strict 30d avg | Strict 30d DD avg/worst | Taker 7d avg |
|---|---:|---:|---:|---:|---:|---:|
| `MEGAUSDT` | 2 | +9.22% | +18.32% | n/a | n/a% / n/a% | +11.00% |
| `IRYSUSDT` | 11 | +5.30% | +12.82% | +17.30% | 15.18% / 22.24% | +0.91% |
| `GUAUSDT` | 8 | +4.56% | +10.23% | +27.23% | 9.36% / 14.94% | +4.47% |
| `RAVEUSDT` | 7 | +6.12% | +7.36% | -5.39% | 23.42% / 26.16% | +4.58% |
| `B2USDT` | 19 | +2.73% | +4.24% | +7.71% | 18.51% / 32.84% | +1.06% |

## Latest Hot Events

| Event Time | Symbol | Hot Score | Reasons | Scenario | Forward | Return | PF | DD | Trades |
|---|---|---:|---|---|---:|---:|---:|---:|---:|
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 7 | +10.07% | 3.79 | 2.26% | 21 |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 7 | +2.86% | 1.34 | 5.37% | 20 |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `SPORTFUNUSDT` | 89.22 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | strict_maker | 7 | +22.23% | 2.72 | 2.66% | 44 |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | taker_like | 7 | +8.12% | 1.41 | 3.50% | 46 |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | strict_maker | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `PIEVERSEUSDT` | 100.00 | 3d move;7d move;7d range;volume spike | taker_like | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | strict_maker | 7 | +11.64% | 1.85 | 4.59% | 30 |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | taker_like | 7 | +7.94% | 1.45 | 4.83% | 39 |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | strict_maker | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `AIOUSDT` | 53.33 | 3d range | taker_like | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 7 | +34.71% | 2.22 | 7.03% | 69 |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 7 | +18.47% | 2.17 | 6.37% | 42 |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `IRUSDT` | 94.91 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | strict_maker | 7 | +8.48% | 3.81 | 0.93% | 18 |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | taker_like | 7 | +5.30% | 2.28 | 1.61% | 19 |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | strict_maker | 60 | n/a | n/a | n/a% |  |
| 2026-04-26 | `BICOUSDT` | 66.13 | 7d move;volume spike | taker_like | 60 | n/a | n/a | n/a% |  |
