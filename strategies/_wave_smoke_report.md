# Wave After Hot Backtest

Это проверка не по принципу `торговать весь год`, а по принципу `scanner увидел hot-режим, что было дальше`.

В каждом историческом дне scanner видел только прошлые свечи. После hot-сигнала стратегия включалась на будущие 7/14/30/60 дней.

## Status Counts

| Status | Count |
|---|---:|
| wave_candidate | 0 |
| fresh_wave_watch | 0 |
| maker_only_wave | 1 |
| weak_wave | 0 |

## Data Counts

| Status | Count |
|---|---:|
| ok | 1 |

## Symbol Summary

| Symbol | Decision | Events | Direction | Strict 14d avg | Strict 14d win | Strict 30d avg | Strict 30d worst | Taker 7d avg |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `UBUSDT` | maker_only_wave | 16 | long | +1.82% | 46.67% | -1.44% | -34.25% | -0.76% |

## Best Wave Candidates

| Symbol | Events | Strict 7d avg | Strict 14d avg | Strict 30d avg | Strict 30d DD avg/worst | Taker 7d avg |
|---|---:|---:|---:|---:|---:|---:|

## Latest Hot Events

| Event Time | Symbol | Hot Score | Reasons | Scenario | Forward | Return | PF | DD | Trades |
|---|---|---:|---|---|---:|---:|---:|---:|---:|
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 7 | +27.25% | 1.89 | 7.92% | 66 |
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 7 | +9.36% | 1.35 | 12.99% | 50 |
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 14 | n/a | n/a | n/a% |  |
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 14 | n/a | n/a | n/a% |  |
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-23 | `UBUSDT` | 100.00 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | strict_maker | 7 | +0.00% | 0.00 | 0.00% | 0 |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | taker_like | 7 | +0.00% | 0.00 | 0.00% | 0 |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | strict_maker | 14 | +27.25% | 1.89 | 7.92% | 66 |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | taker_like | 14 | +9.36% | 1.35 | 12.99% | 50 |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-16 | `UBUSDT` | 86.27 | 3d move;7d move;3d range;7d range | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | strict_maker | 7 | +32.41% | 1.88 | 4.86% | 81 |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | taker_like | 7 | +39.35% | 1.99 | 5.49% | 94 |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | strict_maker | 14 | +32.41% | 1.88 | 4.86% | 81 |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | taker_like | 14 | +39.35% | 1.99 | 5.49% | 94 |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | strict_maker | 30 | n/a | n/a | n/a% |  |
| 2026-04-09 | `UBUSDT` | 68.16 | 3d range | taker_like | 30 | n/a | n/a | n/a% |  |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 7 | +8.12% | 1.14 | 11.21% | 93 |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 7 | +5.96% | 1.10 | 11.48% | 95 |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 14 | +43.15% | 1.44 | 11.21% | 174 |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 14 | +47.66% | 1.47 | 11.48% | 189 |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | strict_maker | 30 | +82.16% | 1.58 | 11.21% | 240 |
| 2026-04-02 | `UBUSDT` | 78.39 | 3d move;7d move;3d range;7d range;volume spike | taker_like | 30 | +61.49% | 1.43 | 13.56% | 239 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | strict_maker | 7 | -7.08% | 0.85 | 11.08% | 62 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | taker_like | 7 | -0.59% | 0.99 | 11.00% | 79 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | strict_maker | 14 | +0.47% | 1.00 | 11.97% | 155 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | taker_like | 14 | +5.34% | 1.05 | 11.48% | 174 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | strict_maker | 30 | +33.30% | 1.23 | 11.97% | 248 |
| 2026-03-26 | `UBUSDT` | 63.85 | 3d range;7d range | taker_like | 30 | +46.32% | 1.29 | 11.48% | 280 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | strict_maker | 7 | -7.46% | 0.67 | 9.45% | 35 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | taker_like | 7 | -7.15% | 0.71 | 8.92% | 40 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | strict_maker | 14 | -11.93% | 0.70 | 17.41% | 59 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | taker_like | 14 | -11.21% | 0.73 | 15.91% | 66 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | strict_maker | 30 | -11.24% | 0.90 | 17.41% | 195 |
| 2026-03-06 | `UBUSDT` | 61.83 | 3d move;3d range | taker_like | 30 | -9.72% | 0.92 | 18.75% | 216 |
| 2026-02-27 | `UBUSDT` | 65.17 | 3d move;3d range;7d range | strict_maker | 7 | -5.74% | 0.87 | 15.56% | 61 |
| 2026-02-27 | `UBUSDT` | 65.17 | 3d move;3d range;7d range | taker_like | 7 | -5.17% | 0.88 | 15.77% | 65 |
| 2026-02-27 | `UBUSDT` | 65.17 | 3d move;3d range;7d range | strict_maker | 14 | -12.77% | 0.80 | 18.23% | 96 |
| 2026-02-27 | `UBUSDT` | 65.17 | 3d move;3d range;7d range | taker_like | 14 | -11.95% | 0.82 | 17.11% | 105 |
