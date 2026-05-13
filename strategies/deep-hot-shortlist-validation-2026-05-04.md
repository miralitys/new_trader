# Deep Validation: Binance Hot Shortlist

Проверка берет **ровно тот setup**, который нашел быстрый Binance-wide hot-scan, и гонит его на больших окнах.

Сценарии:

- `base_maker`: maker 0.02%, лимит у текущей цены.
- `strict_maker`: maker 0.02%, лимитка засчитывается только после возврата цены на 0.05%.
- `taker_like`: fee 0.04% + slippage 0.02%, вход по следующему open.

## Status Counts

| Status | Count |
|---|---:|
| deep_pass_730 | 0 |
| deep_pass_365 | 1 |
| fresh_watch | 28 |
| maker_only_watch | 5 |
| reject_or_too_early | 17 |

## Data Counts

| Status | Count |
|---|---:|
| ok | 51 |

## Per-Symbol Summary

| Symbol | Class | Strict 30d | Strict 90d | Strict 180d | Strict 365d | Strict 730d | Taker 30d |
|---|---|---:|---:|---:|---:|---:|---:|
| `UBUSDT` | fresh_watch | +73.14% / PF 1.59 | +76.97% / PF 1.19 | +13.55% / PF 1.03 | n/a | n/a | +49.88% |
| `GUAUSDT` | fresh_watch | +70.80% / PF 1.44 | +108.63% / PF 1.37 | n/a | n/a | n/a | +68.75% |
| `IRYSUSDT` | fresh_watch | +63.28% / PF 1.51 | +108.01% / PF 1.27 | n/a | n/a | n/a | +19.71% |
| `RAVEUSDT` | fresh_watch | +57.14% / PF 1.82 | +66.30% / PF 1.22 | n/a | n/a | n/a | +23.85% |
| `FIGHTUSDT` | reject_or_too_early | +56.04% / PF 1.32 | -8.79% / PF 0.98 | n/a | n/a | n/a | +42.24% |
| `B2USDT` | fresh_watch | +54.45% / PF 1.62 | +53.59% / PF 1.31 | +76.30% / PF 1.16 | n/a | n/a | +30.87% |
| `ZEREBROUSDT` | fresh_watch | +52.82% / PF 2.39 | +23.83% / PF 1.13 | -14.22% / PF 0.96 | -62.36% / PF 0.89 | n/a | +48.55% |
| `BLUAIUSDT` | fresh_watch | +51.65% / PF 1.51 | +67.17% / PF 1.15 | +8.16% / PF 1.01 | n/a | n/a | +15.07% |
| `SPORTFUNUSDT` | fresh_watch | +44.71% / PF 1.80 | +25.54% / PF 1.14 | n/a | n/a | n/a | +34.97% |
| `FHEUSDT` | fresh_watch | +43.31% / PF 1.32 | +35.06% / PF 1.09 | -27.74% / PF 0.94 | -47.27% / PF 0.95 | n/a | +13.38% |
| `ALCHUSDT` | fresh_watch | +40.64% / PF 2.03 | +34.32% / PF 1.25 | -15.89% / PF 0.94 | -60.13% / PF 0.86 | n/a | +28.23% |
| `ZENUSDT` | fresh_watch | +33.79% / PF 2.29 | +25.68% / PF 1.29 | +1.64% / PF 1.01 | -38.00% / PF 0.91 | -75.00% / PF 0.90 | +22.93% |
| `TRADOORUSDT` | fresh_watch | +31.13% / PF 2.33 | +77.68% / PF 1.49 | +12.55% / PF 1.03 | n/a | n/a | +25.51% |
| `REZUSDT` | fresh_watch | +29.24% / PF 1.52 | +26.34% / PF 1.19 | -4.88% / PF 0.98 | -9.56% / PF 0.99 | -89.00% / PF 0.86 | +26.18% |
| `SHELLUSDT` | fresh_watch | +28.37% / PF 1.45 | +31.60% / PF 1.21 | +16.46% / PF 1.05 | +45.85% / PF 1.05 | n/a | +23.21% |
| `PIEVERSEUSDT` | fresh_watch | +28.26% / PF 1.91 | +14.78% / PF 1.18 | n/a | n/a | n/a | +17.16% |
| `BIOUSDT` | reject_or_too_early | +27.76% / PF 1.43 | -13.69% / PF 0.91 | -45.51% / PF 0.82 | -53.49% / PF 0.94 | n/a | +6.67% |
| `RIFUSDT` | deep_pass_365 | +25.76% / PF 2.03 | +58.12% / PF 1.42 | +72.93% / PF 1.34 | +115.43% / PF 1.34 | -41.82% / PF 0.89 | +5.16% |
| `MERLUSDT` | fresh_watch | +25.22% / PF 2.51 | +5.45% / PF 1.08 | +7.68% / PF 1.04 | n/a | n/a | +30.70% |
| `PARTIUSDT` | reject_or_too_early | +24.80% / PF 1.45 | -3.45% / PF 0.97 | -35.66% / PF 0.87 | -41.73% / PF 0.93 | n/a | +15.79% |
| `XNYUSDT` | fresh_watch | +23.71% / PF 1.68 | +2.15% / PF 1.01 | -0.78% / PF 1.00 | n/a | n/a | +14.75% |
| `4USDT` | fresh_watch | +22.94% / PF 1.30 | +12.03% / PF 1.07 | +23.02% / PF 1.04 | n/a | n/a | +9.01% |
| `APEUSDT` | fresh_watch | +22.83% / PF 1.79 | +1.86% / PF 1.02 | -6.30% / PF 0.97 | -16.22% / PF 0.95 | -74.97% / PF 0.86 | +13.53% |
| `AIOUSDT` | maker_only_watch | +20.55% / PF 1.17 | +4.63% / PF 1.02 | -28.92% / PF 0.92 | n/a | n/a | -11.34% |
| `ACHUSDT` | fresh_watch | +19.04% / PF 2.15 | +13.68% / PF 1.28 | -28.15% / PF 0.82 | -42.38% / PF 0.85 | -90.19% / PF 0.75 | +6.24% |
| `GWEIUSDT` | reject_or_too_early | +17.83% / PF 1.13 | -44.57% / PF 0.84 | n/a | n/a | n/a | -11.36% |
| `BBUSDT` | reject_or_too_early | +17.43% / PF 1.18 | -11.69% / PF 0.93 | -18.88% / PF 0.95 | -25.45% / PF 0.97 | n/a | +7.07% |
| `TURTLEUSDT` | fresh_watch | +17.31% / PF 1.41 | +23.58% / PF 1.21 | +4.70% / PF 1.01 | n/a | n/a | +7.35% |
| `IRUSDT` | fresh_watch | +16.44% / PF 1.21 | +64.56% / PF 1.17 | n/a | n/a | n/a | +1.20% |
| `MEGAUSDT` | fresh_watch | +16.24% / PF 1.29 | +13.67% / PF 1.13 | n/a | n/a | n/a | +20.21% |
| `TRIAUSDT` | reject_or_too_early | +15.57% / PF 1.11 | n/a | n/a | n/a | n/a | +21.35% |
| `WLFIUSDT` | maker_only_watch | +14.57% / PF 1.19 | +6.29% / PF 1.02 | -21.70% / PF 0.95 | n/a | n/a | -4.23% |
| `AKEUSDT` | reject_or_too_early | +13.59% / PF 1.15 | -8.30% / PF 0.96 | -36.21% / PF 0.89 | n/a | n/a | -3.87% |
| `EDUUSDT` | fresh_watch | +12.13% / PF 1.15 | +3.56% / PF 1.02 | -5.61% / PF 0.98 | -14.32% / PF 0.97 | -37.70% / PF 0.95 | +8.35% |
| `OPENUSDT` | fresh_watch | +11.93% / PF 5.92 | +25.09% / PF 1.88 | +36.45% / PF 1.42 | n/a | n/a | +15.40% |
| `VICUSDT` | fresh_watch | +11.73% / PF 1.25 | +2.02% / PF 1.02 | -8.79% / PF 0.97 | -11.48% / PF 0.98 | n/a | +11.40% |
| `MITOUSDT` | reject_or_too_early | +11.17% / PF 1.23 | -17.22% / PF 0.87 | +17.27% / PF 1.04 | n/a | n/a | +8.13% |
| `AXLUSDT` | reject_or_too_early | +11.15% / PF 1.59 | -5.54% / PF 0.94 | -27.76% / PF 0.87 | -54.07% / PF 0.80 | -87.75% / PF 0.79 | +4.04% |
| `DUSDT` | reject_or_too_early | +10.01% / PF 1.17 | -19.52% / PF 0.84 | -31.78% / PF 0.86 | -38.71% / PF 0.89 | n/a | -2.69% |
| `DEXEUSDT` | reject_or_too_early | +9.46% / PF 1.11 | -8.90% / PF 0.95 | -38.66% / PF 0.85 | -25.83% / PF 0.95 | n/a | +6.22% |
| `USUSDT` | fresh_watch | +8.75% / PF 1.11 | +6.91% / PF 1.03 | n/a | n/a | n/a | +5.97% |
| `LUMIAUSDT` | reject_or_too_early | +8.67% / PF 1.87 | -19.53% / PF 0.69 | -32.29% / PF 0.79 | -58.05% / PF 0.81 | n/a | +4.64% |
| `NOTUSDT` | maker_only_watch | +6.95% / PF 1.24 | +11.22% / PF 1.09 | -41.84% / PF 0.81 | -46.31% / PF 0.91 | n/a | -4.50% |
| `RLCUSDT` | fresh_watch | +6.50% / PF 1.20 | +23.82% / PF 1.27 | -16.66% / PF 0.89 | -27.05% / PF 0.93 | -79.39% / PF 0.84 | +7.24% |
| `BICOUSDT` | reject_or_too_early | +6.28% / PF 1.12 | -10.82% / PF 0.93 | -37.42% / PF 0.83 | -64.13% / PF 0.84 | -90.74% / PF 0.85 | +1.18% |
| `AKTUSDT` | reject_or_too_early | +5.85% / PF 1.21 | -24.46% / PF 0.79 | -44.07% / PF 0.79 | -55.76% / PF 0.84 | n/a | -0.35% |
| `SPACEUSDT` | maker_only_watch | +5.46% / PF 1.06 | +10.42% / PF 1.03 | n/a | n/a | n/a | -3.98% |
| `CHRUSDT` | reject_or_too_early | +5.26% / PF 1.07 | -65.76% / PF 0.66 | -80.04% / PF 0.74 | -88.33% / PF 0.77 | -97.39% / PF 0.74 | +4.91% |
| `BABYUSDT` | maker_only_watch | +3.00% / PF 1.05 | +6.80% / PF 1.04 | -9.57% / PF 0.96 | -37.17% / PF 0.93 | n/a | -7.79% |
| `TAGUSDT` | reject_or_too_early | +2.24% / PF 1.02 | -34.13% / PF 0.85 | -71.32% / PF 0.77 | n/a | n/a | -16.67% |
| `ZKJUSDT` | reject_or_too_early | +0.12% / PF 1.00 | -22.96% / PF 0.85 | -55.08% / PF 0.82 | n/a | n/a | -10.88% |

## Top Strict 30d

| Symbol | Direction | Period | Return | PF | DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| `UBUSDT` | long | 30 | +73.14% | 1.59 | 11.21% | 218 |
| `GUAUSDT` | long | 30 | +70.80% | 1.44 | 14.94% | 223 |
| `IRYSUSDT` | long | 30 | +63.28% | 1.51 | 9.57% | 190 |
| `RAVEUSDT` | short | 30 | +57.14% | 1.82 | 7.31% | 111 |
| `FIGHTUSDT` | long | 30 | +56.04% | 1.32 | 16.92% | 221 |
| `B2USDT` | long | 30 | +54.45% | 1.62 | 6.67% | 200 |
| `ZEREBROUSDT` | long | 30 | +52.82% | 2.39 | 4.66% | 102 |
| `BLUAIUSDT` | long | 30 | +51.65% | 1.51 | 10.39% | 171 |
| `SPORTFUNUSDT` | long | 30 | +44.71% | 1.80 | 11.59% | 112 |
| `FHEUSDT` | long | 30 | +43.31% | 1.32 | 11.24% | 235 |
| `ALCHUSDT` | long | 30 | +40.64% | 2.03 | 4.22% | 93 |
| `ZENUSDT` | long | 30 | +33.79% | 2.29 | 4.36% | 61 |
| `TRADOORUSDT` | long | 30 | +31.13% | 2.33 | 4.04% | 59 |
| `REZUSDT` | long | 30 | +29.24% | 1.52 | 8.38% | 105 |
| `SHELLUSDT` | long | 30 | +28.37% | 1.45 | 6.71% | 160 |
| `PIEVERSEUSDT` | long | 30 | +28.26% | 1.91 | 9.80% | 82 |
| `BIOUSDT` | long | 30 | +27.76% | 1.43 | 13.29% | 106 |
| `RIFUSDT` | long | 30 | +25.76% | 2.03 | 6.00% | 69 |
| `MERLUSDT` | long | 30 | +25.22% | 2.51 | 5.85% | 42 |
| `PARTIUSDT` | long | 30 | +24.80% | 1.45 | 9.15% | 146 |
| `XNYUSDT` | long | 30 | +23.71% | 1.68 | 19.31% | 65 |
| `4USDT` | long | 30 | +22.94% | 1.30 | 19.40% | 177 |
| `APEUSDT` | long | 30 | +22.83% | 1.79 | 3.84% | 71 |
| `AIOUSDT` | long | 30 | +20.55% | 1.17 | 13.10% | 202 |
| `ACHUSDT` | long | 30 | +19.04% | 2.15 | 4.31% | 119 |

## Top Strict 365d

| Symbol | Direction | Period | Return | PF | DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| `RIFUSDT` | long | 365 | +115.43% | 1.34 | 16.24% | 524 |
| `SHELLUSDT` | long | 365 | +45.85% | 1.05 | 39.00% | 1785 |
| `REZUSDT` | long | 365 | -9.56% | 0.99 | 58.71% | 1497 |
| `VICUSDT` | long | 365 | -11.48% | 0.98 | 42.30% | 1118 |
| `EDUUSDT` | long | 365 | -14.32% | 0.97 | 38.39% | 908 |
| `APEUSDT` | long | 365 | -16.22% | 0.95 | 47.22% | 663 |
| `BBUSDT` | long | 365 | -25.45% | 0.97 | 56.79% | 1467 |
| `DEXEUSDT` | short | 365 | -25.83% | 0.95 | 58.71% | 1210 |
| `RLCUSDT` | long | 365 | -27.05% | 0.93 | 57.48% | 759 |
| `BABYUSDT` | long | 365 | -37.17% | 0.93 | 59.01% | 1069 |
| `ZENUSDT` | long | 365 | -38.00% | 0.91 | 59.13% | 959 |
| `DUSDT` | long | 365 | -38.71% | 0.89 | 58.02% | 638 |
| `PARTIUSDT` | long | 365 | -41.73% | 0.93 | 65.69% | 1571 |
| `ACHUSDT` | long | 365 | -42.38% | 0.85 | 58.22% | 1237 |
| `NOTUSDT` | short | 365 | -46.31% | 0.91 | 60.03% | 917 |
| `FHEUSDT` | long | 365 | -47.27% | 0.95 | 77.84% | 2232 |
| `BIOUSDT` | long | 365 | -53.49% | 0.94 | 79.50% | 1367 |
| `AXLUSDT` | long | 365 | -54.07% | 0.80 | 60.70% | 591 |
| `AKTUSDT` | long | 365 | -55.76% | 0.84 | 64.41% | 898 |
| `LUMIAUSDT` | long | 365 | -58.05% | 0.81 | 65.41% | 1339 |
| `ALCHUSDT` | long | 365 | -60.13% | 0.86 | 75.05% | 1147 |
| `ZEREBROUSDT` | long | 365 | -62.36% | 0.89 | 82.62% | 1822 |
| `BICOUSDT` | short | 365 | -64.13% | 0.84 | 71.77% | 1104 |
| `CHRUSDT` | long | 365 | -88.33% | 0.77 | 90.87% | 2647 |
