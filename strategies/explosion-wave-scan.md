# Explosion Wave Scan

Идея: найти месяцы, когда монета резко оживала, и проверить, могла ли наша семья 1m LONG/SHORT стратегий поймать этот режим.

Взрывной месяц считается так: `abs(price return) >= 35%` или `месячный range >= 75%` или `объем/день >= 2.5x` к предыдущим ~90 дням.

Важно: `paper_only` значит, что базовый maker-тест поймал волну, но strict maker-fill уже не подтвердил реалистичность.

## Status Breakdown

| Status | Count |
|---|---:|
| caught_realistic | 38 |
| paper_only | 8 |
| weak_catch | 113 |
| not_caught | 2 |

## Top Strategy Catches

| Symbol | Month | Market move | Range | Volume x | Best setup | Base return | Strict return | Taker-like | Status |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| DENTUSDT | 2025-12 | -40.88% | 76.29% | 2.85x | short th50 wide TP 0.35% T60 | +1495.28% | -37.05% | +862.66% | paper_only |
| CHRUSDT | 2026-03 | -14.61% | 52.31% | 2.96x | long th50 base TP 0.50% T90 | +337.11% | -43.57% | +199.66% | paper_only |
| DENTUSDT | 2026-03 | -32.05% | 121.39% | 2.07x | short th40 wide TP 0.35% T60 | +277.37% | -34.40% | +69.45% | paper_only |
| DENTUSDT | 2026-02 | +59.26% | 266.67% | 12.67x | long th50 base TP 0.50% T90 | +258.80% | -32.39% | +89.69% | paper_only |
| CHRUSDT | 2026-02 | -42.02% | 96.32% | 2.36x | short th40 wide TP 0.35% T60 | +235.04% | -16.77% | +31.49% | paper_only |
| DENTUSDT | 2026-04 | -32.61% | 179.07% | 0.27x | long th50 base TP 0.50% T90 | +142.09% | -13.79% | +75.05% | paper_only |
| HIFIUSDT | 2025-05 | -66.92% | 304.73% | 0.00x | short th40 wide TP 1.00% T90 | +81.54% | +68.54% | +46.13% | caught_realistic |
| CHRUSDT | 2026-04 | +59.93% | 88.92% | 3.23x | long th50 base TP 0.50% T90 | +70.16% | +13.75% | +58.87% | caught_realistic |
| 1000PEPEUSDT | 2025-05 | +42.42% | 115.63% | 0.00x | long th50 base TP 0.70% T180 | +54.75% | +40.27% | +37.18% | caught_realistic |
| AXLUSDT | 2025-12 | -42.64% | 144.16% | 5.98x | short th50 wide TP 1.20% T180 | +48.48% | +28.03% | +36.77% | caught_realistic |
| BAKEUSDT | 2025-09 | -51.41% | 558.68% | 18.18x | short th60 wide TP 0.70% T180 | +48.39% | +35.36% | +22.72% | caught_realistic |
| HIFIUSDT | 2025-09 | +14.47% | 1798.88% | 6.92x | short th50 base TP 1.00% T60 | +45.26% | +34.57% | +24.29% | caught_realistic |
| BBUSDT | 2025-09 | +36.56% | 98.66% | 1.61x | long th50 wide TP 0.70% T120 | +45.11% | +28.39% | +12.82% | caught_realistic |
| XVGUSDT | 2025-11 | +12.31% | 64.22% | 2.68x | long th50 wide TP 1.20% T120 | +43.92% | +32.93% | +27.53% | caught_realistic |
| LEVERUSDT | 2025-08 | -8.69% | 152.18% | 1.00x | long th50 wide TP 1.00% T90 | +41.74% | +28.42% | +12.40% | caught_realistic |
| ANKRUSDT | 2026-02 | -14.64% | 58.09% | 3.52x | short th60 base TP 0.70% T180 | +41.57% | +36.35% | +25.51% | caught_realistic |
| REZUSDT | 2026-04 | +38.86% | 45.27% | 0.90x | long th50 base TP 1.20% T120 | +41.01% | +31.32% | +34.30% | caught_realistic |
| NTRNUSDT | 2025-05 | -24.34% | 86.80% | 0.00x | short th40 base TP 1.20% T90 | +38.73% | +30.77% | +25.05% | caught_realistic |
| LEVERUSDT | 2025-07 | -50.01% | 163.48% | 3.02x | short th60 base TP 1.20% T60 | +37.79% | +32.18% | -3.64% | caught_realistic |
| XVGUSDT | 2025-05 | +31.40% | 99.76% | 0.00x | long th60 base TP 1.20% T180 | +36.84% | +26.32% | +18.23% | caught_realistic |
| ALPINEUSDT | 2025-10 | -88.79% | 3236.06% | 1.29x | short th50 wide TP 1.20% T120 | +36.68% | +13.04% | +2.56% | caught_realistic |
| LEVERUSDT | 2025-06 | -25.85% | 102.45% | 1.71x | short th60 base TP 1.00% T180 | +35.54% | +24.14% | +30.39% | caught_realistic |
| ONEUSDT | 2025-10 | -38.59% | 499.44% | 1.22x | short th50 wide TP 1.20% T120 | +34.25% | -0.81% | +19.91% | paper_only |
| RDNTUSDT | 2025-12 | -7.27% | 64.66% | 2.71x | short th40 wide TP 1.00% T90 | +34.20% | +14.77% | +20.42% | caught_realistic |
| RDNTUSDT | 2025-10 | -22.85% | 1092.72% | 4.60x | short th40 base TP 1.20% T90 | +33.03% | +23.16% | +22.01% | caught_realistic |
| BBUSDT | 2025-05 | +0.86% | 93.55% | 0.00x | long th50 wide TP 1.00% T90 | +32.40% | +19.93% | +13.58% | caught_realistic |
| BATUSDT | 2025-11 | +69.20% | 83.93% | 2.29x | long th50 wide TP 1.20% T120 | +32.40% | +6.14% | +6.70% | caught_realistic |
| HIFIUSDT | 2025-06 | +55.56% | 123.39% | 1.25x | long th70 base TP 1.20% T180 | +32.17% | +9.88% | +26.19% | caught_realistic |
| NTRNUSDT | 2026-03 | -56.54% | 172.46% | 2.72x | short th60 wide TP 1.20% T90 | +31.88% | +19.35% | +32.94% | caught_realistic |
| XVGUSDT | 2025-10 | +20.97% | 222.31% | 4.07x | long th60 base TP 1.20% T120 | +31.50% | +34.34% | +20.34% | caught_realistic |
| XVGUSDT | 2025-07 | +15.70% | 75.96% | 0.90x | long th50 wide TP 1.20% T90 | +31.04% | +13.47% | +16.39% | caught_realistic |
| SANDUSDT | 2026-01 | -6.22% | 89.50% | 4.03x | long th50 wide TP 0.70% T120 | +31.00% | +20.51% | +15.99% | caught_realistic |
| GALAUSDT | 2025-10 | -30.21% | 543.63% | 1.17x | long th50 base TP 1.00% T120 | +30.22% | +28.93% | +18.09% | caught_realistic |
| MAVUSDT | 2025-10 | -44.92% | 499.81% | 0.35x | long th50 base TP 1.20% T120 | +28.05% | +24.07% | +14.26% | caught_realistic |
| 1000FLOKIUSDT | 2025-10 | -14.05% | 667.31% | 1.46x | short th50 base TP 1.20% T60 | +27.86% | +13.96% | +13.47% | caught_realistic |
| NFPUSDT | 2025-10 | -34.26% | 176.43% | 1.30x | long th60 base TP 1.20% T180 | +27.53% | +21.02% | +18.19% | caught_realistic |
| MOVRUSDT | 2026-04 | +92.75% | 295.33% | 20.56x | long th50 wide TP 1.20% T90 | +26.65% | +17.22% | +15.20% | caught_realistic |
| BATUSDT | 2025-10 | +15.96% | 93.36% | 2.76x | long th50 base TP 1.00% T180 | +26.61% | +33.08% | +17.73% | caught_realistic |
| MAVUSDT | 2025-11 | -8.77% | 117.93% | 1.43x | long th50 wide TP 1.00% T90 | +26.52% | -6.95% | +7.49% | paper_only |
| ORDIUSDT | 2025-05 | +13.73% | 104.98% | 0.00x | long th50 base TP 1.00% T180 | +26.25% | +21.93% | +17.30% | caught_realistic |

## Top Market Explosions

| Symbol | Month | Market move | Range | Volume x | Score | Caught? |
|---|---|---:|---:|---:|---:|---|
| ALPINEUSDT | 2025-10 | -88.79% | 3236.06% | 1.29x | 43.15 | caught_realistic |
| IOTXUSDT | 2025-10 | -51.45% | 2005.04% | 1.33x | 26.73 | weak_catch |
| HIFIUSDT | 2025-09 | +14.47% | 1798.88% | 6.92x | 23.99 | caught_realistic |
| RDNTUSDT | 2025-10 | -22.85% | 1092.72% | 4.60x | 14.57 | caught_realistic |
| ALPINEUSDT | 2025-09 | +254.77% | 932.53% | 1.35x | 12.43 | weak_catch |
| ORDIUSDT | 2025-10 | -41.51% | 898.66% | 1.18x | 11.98 | weak_catch |
| HOOKUSDT | 2025-10 | -35.58% | 871.87% | 1.36x | 11.62 | weak_catch |
| LITUSDT | 2025-12 | +322.47% | 641.39% | 0.00x | 9.21 | weak_catch |
| 1000FLOKIUSDT | 2025-10 | -14.05% | 667.31% | 1.46x | 8.90 | caught_realistic |
| 1000LUNCUSDT | 2025-12 | +54.78% | 228.96% | 21.20x | 8.48 | weak_catch |
| MOVRUSDT | 2026-04 | +92.75% | 295.33% | 20.56x | 8.22 | caught_realistic |
| KNCUSDT | 2025-07 | +48.24% | 166.67% | 20.10x | 8.04 | weak_catch |
| BAKEUSDT | 2025-09 | -51.41% | 558.68% | 18.18x | 7.45 | caught_realistic |
| GALAUSDT | 2025-10 | -30.21% | 543.63% | 1.17x | 7.25 | caught_realistic |
| MAVUSDT | 2025-10 | -44.92% | 499.81% | 0.35x | 6.66 | caught_realistic |
| ONEUSDT | 2025-10 | -38.59% | 499.44% | 1.22x | 6.66 | paper_only |
| ZILUSDT | 2026-02 | +2.20% | 135.95% | 15.78x | 6.31 | weak_catch |
| 1000BONKUSDT | 2025-10 | -27.12% | 462.99% | 0.66x | 6.17 | weak_catch |
| ENJUSDT | 2026-04 | +180.32% | 446.17% | 6.32x | 5.95 | weak_catch |
| USTCUSDT | 2025-12 | +4.96% | 155.95% | 14.68x | 5.87 | weak_catch |
| MAVUSDT | 2025-07 | -6.04% | 113.64% | 14.36x | 5.74 | weak_catch |
| AIUSDT | 2025-10 | -39.08% | 413.35% | 1.22x | 5.51 | weak_catch |
| ORDIUSDT | 2026-04 | +88.48% | 393.80% | 7.05x | 5.25 | weak_catch |
| TRUUSDT | 2026-04 | +13.21% | 249.33% | 12.91x | 5.16 | weak_catch |
| DENTUSDT | 2026-02 | +59.26% | 266.67% | 12.67x | 5.07 | paper_only |
| BBUSDT | 2025-10 | -43.62% | 363.84% | 0.67x | 4.85 | weak_catch |
| AXLUSDT | 2025-10 | -42.11% | 361.16% | 1.24x | 4.82 | weak_catch |
| AXLUSDT | 2025-06 | +4.28% | 94.79% | 11.59x | 4.63 | weak_catch |
| TRUUSDT | 2025-10 | -33.65% | 342.48% | 1.92x | 4.57 | weak_catch |
| NTRNUSDT | 2025-10 | -43.56% | 306.00% | 0.57x | 4.08 | weak_catch |
| HIFIUSDT | 2025-05 | -66.92% | 304.73% | 0.00x | 4.06 | caught_realistic |
| APEUSDT | 2025-10 | -25.40% | 294.08% | 1.73x | 3.92 | weak_catch |
| KNCUSDT | 2026-03 | +1.16% | 58.59% | 9.57x | 3.83 | weak_catch |
| 1000PEPEUSDT | 2025-10 | -29.61% | 274.57% | 0.89x | 3.66 | weak_catch |
| 1000LUNCUSDT | 2025-10 | -19.75% | 274.50% | 1.56x | 3.66 | weak_catch |
| LITUSDT | 2026-01 | -37.27% | 142.64% | 9.07x | 3.63 | weak_catch |
| ENJUSDT | 2026-03 | +1.87% | 71.93% | 8.80x | 3.52 | weak_catch |
| API3USDT | 2025-08 | +59.12% | 175.24% | 8.15x | 3.26 | weak_catch |
| APEUSDT | 2026-04 | +85.03% | 242.00% | 7.69x | 3.23 | weak_catch |
| ALPINEUSDT | 2025-08 | +112.67% | 211.49% | 2.95x | 3.22 | weak_catch |
| SANDUSDT | 2025-10 | -23.82% | 238.46% | 1.15x | 3.18 | weak_catch |
| DENTUSDT | 2025-10 | -33.55% | 231.92% | 1.66x | 3.09 | weak_catch |
| ANKRUSDT | 2026-03 | +15.62% | 54.54% | 7.57x | 3.03 | weak_catch |
| JASMYUSDT | 2025-10 | -19.79% | 224.09% | 1.25x | 2.99 | weak_catch |
| DOGEUSDT | 2025-10 | -19.96% | 222.47% | 1.20x | 2.97 | weak_catch |
| XVGUSDT | 2025-10 | +20.97% | 222.31% | 4.07x | 2.96 | caught_realistic |
| CHZUSDT | 2025-10 | -23.71% | 216.35% | 1.19x | 2.88 | weak_catch |
| ZENUSDT | 2025-10 | +88.20% | 201.61% | 7.20x | 2.88 | weak_catch |
| 1000LUNCUSDT | 2026-04 | +100.51% | 117.05% | 1.34x | 2.87 | weak_catch |
| REZUSDT | 2025-10 | -25.18% | 213.30% | 0.72x | 2.84 | weak_catch |
| 1000BONKUSDT | 2025-07 | +79.54% | 202.03% | 4.18x | 2.69 | weak_catch |
| USTCUSDT | 2025-10 | -28.62% | 201.41% | 1.03x | 2.69 | weak_catch |
| MANAUSDT | 2025-10 | -21.54% | 198.67% | 1.28x | 2.65 | weak_catch |
| ENJUSDT | 2025-10 | -32.20% | 194.62% | 1.27x | 2.59 | weak_catch |
| CHRUSDT | 2025-10 | -7.27% | 191.19% | 1.39x | 2.55 | weak_catch |
| SPELLUSDT | 2025-10 | -26.54% | 187.02% | 0.66x | 2.49 | weak_catch |
| COTIUSDT | 2025-10 | -27.34% | 185.79% | 1.33x | 2.48 | weak_catch |
| LRCUSDT | 2025-12 | -6.43% | 48.29% | 6.08x | 2.43 | weak_catch |
| AXLUSDT | 2025-12 | -42.64% | 144.16% | 5.98x | 2.39 | caught_realistic |
| DENTUSDT | 2026-04 | -32.61% | 179.07% | 0.27x | 2.39 | paper_only |
