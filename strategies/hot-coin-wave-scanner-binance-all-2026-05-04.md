# Hot Coin Wave Scanner

Назначение: найти монеты, которые ожили прямо сейчас, и проверить, дает ли наша минутная семья стратегий плюс с realistic maker-fill.

Решения:

- `ready` — монета горячая, strict maker на 7d дает хороший плюс, 14d/30d не разваливаются.
- `hot_watch` — текущий импульс есть, 7d выглядит хорошо, но старшие короткие окна слабее.
- `watch` — strict maker в плюсе, но сигнал пока слабый.
- `paper_trap` — база красивая, strict maker ломается.
- `skip` — монета горячая, но стратегия не показывает edge.

## Decision Counts

| Decision | Count |
|---|---:|
| ready | 59 |
| hot_watch | 13 |
| watch | 23 |
| paper_trap | 0 |
| skip | 5 |
| cold | 0 |

## Action List

| Symbol | Decision | Hot score | Reasons | 7d move | 7d range | Vol x | Setup | Strict 7d | Strict 14d | Strict 30d | Base 7d | Taker 7d |
|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| RAVEUSDT | ready | 66.5 | 3d move;7d move;7d range | -31.54% | 52.42% | 0.07x | short th50 wide TP 1.20% T180 | +48.69% / PF 1.95 | +66.58% | +57.14% | +36.67% | +24.57% |
| ZEREBROUSDT | ready | 100.0 | 7d move;3d range;7d range;volume spike | +71.52% | 177.43% | 13.28x | long th50 wide TP 1.00% T90 | +37.75% / PF 3.10 | +45.19% | +52.82% | +40.35% | +30.87% |
| IRUSDT | ready | 97.6 | 7d move;7d range;volume spike | -25.32% | 151.41% | 2.77x | short th40 wide TP 1.00% T90 | +34.71% / PF 2.22 | +35.37% | +16.44% | +36.54% | +18.47% |
| GUAUSDT | ready | 55.6 | 3d range;7d range | +0.99% | 56.67% | 1.18x | long th50 wide TP 1.20% T120 | +34.55% / PF 1.55 | +44.10% | +70.80% | +36.76% | +26.69% |
| DEXEUSDT | ready | 57.8 | 7d move;7d range | -25.47% | 53.59% | 0.80x | short th50 wide TP 0.70% T90 | +34.13% / PF 1.93 | +15.86% | +9.46% | +46.67% | +40.04% |
| B2USDT | ready | 77.3 | 3d move;3d range;7d range;volume spike | -3.98% | 72.87% | 9.06x | long th50 wide TP 1.00% T90 | +32.88% / PF 1.93 | +37.24% | +54.45% | +34.08% | +24.51% |
| FIGHTUSDT | ready | 69.9 | 3d move;3d range;7d range | +12.98% | 46.98% | 0.96x | long th50 wide TP 1.20% T120 | +32.77% / PF 1.57 | +37.13% | +56.04% | +38.65% | +31.28% |
| UBUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +137.97% | 301.94% | 13.75x | long th50 wide TP 1.00% T90 | +32.33% / PF 2.64 | +27.25% | +73.14% | +17.02% | +14.40% |
| AKEUSDT | ready | 57.1 | 7d range | +8.78% | 53.21% | 0.41x | long th50 base TP 0.70% T180 | +28.92% / PF 1.86 | +15.71% | +13.59% | +27.77% | +20.82% |
| GWEIUSDT | ready | 54.0 | 7d range | -10.66% | 59.87% | 1.13x | short th40 wide TP 0.70% T60 | +28.63% / PF 1.33 | +42.80% | +17.83% | +22.92% | +7.76% |
| WLFIUSDT | ready | 59.4 | 7d move;7d range | -22.03% | 47.55% | 1.90x | short th40 wide TP 1.00% T90 | +26.55% / PF 1.80 | +25.84% | +14.57% | +16.03% | +14.17% |
| NFPUSDT | ready | 81.2 | 3d move;3d range;7d range;volume spike | -11.61% | 82.52% | 22.06x | short th60 wide TP 0.70% T180 | +25.21% / PF 1.92 | +20.70% | +19.71% | +21.18% | -1.82% |
| IRYSUSDT | ready | 55.9 | 3d range | +10.56% | 42.42% | 0.98x | long th50 wide TP 1.20% T90 | +23.69% / PF 1.62 | +43.95% | +63.28% | +20.41% | +14.86% |
| 4USDT | ready | 63.9 | 3d move;3d range | +17.94% | 38.23% | 0.29x | long th60 base TP 0.70% T180 | +23.53% / PF 2.96 | +34.04% | +22.94% | +12.88% | +1.86% |
| BIOUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +101.63% | 141.67% | 4.08x | long th50 wide TP 1.20% T90 | +22.69% / PF 2.40 | +11.27% | +27.76% | +20.03% | +11.44% |
| PIEVERSEUSDT | ready | 88.2 | 3d range;volume spike | -6.98% | 29.41% | 0.19x | long th60 base TP 1.00% T90 | +22.23% / PF 2.72 | +25.78% | +28.26% | +16.35% | +8.12% |
| BLUAIUSDT | ready | 56.8 | 3d range | +17.05% | 35.57% | 0.74x | long th50 wide TP 1.20% T90 | +21.18% / PF 1.95 | +34.83% | +51.65% | +16.38% | +13.98% |
| TRIAUSDT | ready | 65.0 | 3d range | +9.47% | 43.21% | 0.79x | long th50 wide TP 1.20% T120 | +20.50% / PF 1.66 | +46.67% | +15.57% | +25.28% | +20.97% |
| BABYUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +27.67% | 120.10% | 25.46x | long th50 wide TP 1.20% T90 | +19.97% / PF 2.43 | +15.77% | +3.00% | +21.25% | +18.56% |
| ACHUSDT | ready | 62.9 | 7d move;volume spike | +23.21% | 32.94% | 4.47x | long th50 wide TP 0.35% T90 | +18.14% / PF 3.08 | +18.34% | +19.04% | +11.12% | +6.39% |
| ALCHUSDT | ready | 53.0 | 3d move;7d move;3d range | +20.46% | 36.16% | 0.68x | long th50 wide TP 1.20% T90 | +18.13% / PF 2.36 | +39.28% | +40.64% | +15.18% | +12.06% |
| FHEUSDT | ready | 98.1 | 3d move;7d move;3d range;7d range;volume spike | +27.03% | 58.06% | 2.34x | long th50 wide TP 1.00% T90 | +17.46% / PF 1.83 | +18.31% | +43.31% | +18.26% | +10.46% |
| PARTIUSDT | ready | 65.1 | 3d move;7d move;3d range | +22.45% | 33.53% | 1.17x | long th50 wide TP 0.70% T120 | +17.25% / PF 5.35 | +22.27% | +24.80% | +17.91% | +15.32% |
| CHRUSDT | ready | 57.2 | 7d move;3d range | +20.75% | 41.62% | 1.08x | long th50 wide TP 0.35% T90 | +16.23% / PF 2.05 | +14.81% | +5.26% | +19.80% | +10.43% |
| BBUSDT | ready | 72.8 | 3d move;7d move;3d range;volume spike | +22.32% | 39.13% | 2.00x | long th50 wide TP 1.00% T90 | +15.78% / PF 1.44 | +10.50% | +17.43% | +19.66% | +14.90% |
| XNYUSDT | ready | 79.7 | 3d move;3d range;7d range | +3.56% | 73.27% | 1.52x | long th60 base TP 1.20% T180 | +15.75% / PF 3.10 | +49.17% | +23.71% | +6.52% | +3.78% |
| MEGAUSDT | ready | 94.0 | 3d move;7d move;3d range;7d range;volume spike | -26.24% | 74.68% | 39.36x | long th50 wide TP 1.20% T120 | +15.71% / PF 1.37 | +10.20% | +16.24% | +28.03% | +24.38% |
| RIFUSDT | ready | 57.3 | 3d move | +4.26% | 25.42% | 1.96x | long th50 wide TP 1.20% T90 | +15.29% / PF 2.50 | +11.93% | +25.76% | +8.45% | +5.24% |
| ZKJUSDT | ready | 89.6 | 7d move;7d range;volume spike | +30.81% | 365.12% | 67.23x | long th50 wide TP 1.20% T90 | +14.59% / PF 11.01 | +6.41% | +0.12% | +14.47% | +13.40% |
| BUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +214.23% | 368.76% | 49.71x | long th50 wide TP 1.20% T90 | +14.20% / PF 24.35 | +8.44% | -1.40% | +14.15% | +13.24% |
| TRADOORUSDT | ready | 90.0 | 3d move;3d range | +3.80% | 30.83% | 0.45x | long th50 wide TP 1.20% T120 | +13.97% / PF 2.57 | +28.46% | +31.13% | +14.95% | +13.03% |
| EDUUSDT | ready | 67.6 | volume spike | +2.65% | 27.78% | 0.49x | long th50 base TP 1.00% T120 | +13.91% / PF 1.68 | +6.27% | +12.13% | +7.44% | +4.23% |
| ZENUSDT | ready | 60.6 | 3d move;3d range | +16.08% | 32.03% | 1.13x | long th50 wide TP 1.20% T120 | +13.52% / PF 4.58 | +15.40% | +33.79% | +13.29% | +12.06% |
| USUSDT | ready | 64.1 | 3d move;7d move;3d range | +25.72% | 34.30% | 0.75x | long th50 wide TP 1.20% T90 | +12.63% / PF 1.67 | +13.49% | +8.75% | +14.27% | +10.54% |
| RLCUSDT | ready | 56.4 | 3d move | +6.80% | 23.51% | 1.68x | long th50 wide TP 1.20% T90 | +12.47% / PF 2.42 | +18.63% | +6.50% | +14.65% | +13.60% |
| MITOUSDT | ready | 70.2 | 7d move;3d range;volume spike | +23.69% | 43.14% | 2.93x | long th50 wide TP 1.20% T120 | +12.35% / PF 1.90 | +24.21% | +11.17% | +12.74% | +9.92% |
| DUSDT | ready | 58.2 | 3d range | -7.73% | 39.64% | 0.21x | long th60 base TP 1.20% T120 | +11.75% / PF 5.55 | +10.14% | +10.01% | +8.39% | +7.46% |
| AIOUSDT | ready | 62.2 | 7d move | +32.21% | 42.77% | 1.25x | long th50 wide TP 1.20% T90 | +11.64% / PF 1.85 | +17.67% | +20.55% | +10.82% | +7.94% |
| MERLUSDT | ready | 66.1 | 3d move;3d range | -5.12% | 39.29% | 0.58x | long th70 base TP 1.20% T180 | +11.23% / PF 3.53 | +22.47% | +25.22% | +17.65% | +15.62% |
| AXLUSDT | ready | 66.1 | 3d move;7d move;3d range;7d range | +25.87% | 53.78% | 1.62x | long th50 base TP 1.00% T180 | +11.08% / PF 2.41 | +9.64% | +11.15% | +8.19% | +6.19% |
| TAGUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +123.61% | 292.62% | 14.05x | short th40 wide TP 1.20% T90 | +10.34% / PF 1.23 | +16.00% | +2.24% | +9.02% | +4.84% |
| SPORTFUNUSDT | ready | 73.9 | volume spike | +5.94% | 21.90% | 1.19x | long th50 base TP 1.20% T120 | +10.07% / PF 3.79 | +15.56% | +44.71% | +4.33% | +2.86% |
| AKTUSDT | ready | 83.5 | 3d move;7d move;3d range;7d range;volume spike | +28.09% | 46.35% | 4.50x | long th50 wide TP 0.70% T120 | +10.01% / PF 2.53 | +12.59% | +5.85% | +8.74% | +4.38% |
| BRUSDT | ready | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +71.97% | 175.00% | 3.77x | short th50 base TP 1.00% T60 | +9.03% / PF 2.46 | +2.83% | +3.09% | -0.10% | -2.47% |
| ONUSDT | ready | 61.5 | 3d move;3d range | +9.21% | 44.67% | 0.21x | long th60 base TP 0.70% T90 | +8.89% / PF 1.43 | +18.24% | +17.57% | +1.67% | -2.86% |
| SHELLUSDT | ready | 54.3 | 3d move;3d range | +15.82% | 35.64% | 1.26x | long th50 wide TP 0.70% T120 | +8.83% / PF 1.39 | +18.52% | +28.37% | +10.34% | +7.14% |
| VICUSDT | ready | 60.9 | 7d move;3d range;volume spike | -20.46% | 40.81% | 2.16x | long th50 wide TP 0.70% T120 | +8.56% / PF 1.38 | +6.61% | +11.73% | +12.07% | +8.05% |
| BICOUSDT | ready | 59.2 | volume spike | -18.10% | 36.83% | 2.47x | short th40 wide TP 1.00% T90 | +8.48% / PF 3.81 | +8.81% | +6.28% | +7.66% | +5.30% |
| LUMIAUSDT | ready | 79.8 | 3d range;7d range;volume spike | +2.63% | 55.03% | 10.37x | long th60 wide TP 0.35% T90 | +8.38% / PF inf | +5.72% | +8.67% | +5.97% | +4.16% |
| TURTLEUSDT | ready | 57.6 | volume spike | +3.90% | 39.63% | 5.96x | long th50 wide TP 1.00% T90 | +8.16% / PF 1.44 | +12.04% | +17.31% | +8.85% | +5.65% |
| KAVAUSDT | ready | 57.1 | volume spike | +0.48% | 17.11% | 2.58x | short th50 wide TP 0.35% T60 | +8.15% / PF 1.96 | +5.66% | +11.97% | -0.71% | -4.69% |
| XVGUSDT | ready | 58.5 | 3d move;3d range | +3.27% | 30.51% | 1.47x | short th40 base TP 1.20% T90 | +7.43% / PF 1.68 | +6.78% | -3.78% | +2.97% | +1.19% |
| SPACEUSDT | ready | 82.6 | 3d move;3d range;7d range;volume spike | +5.05% | 81.88% | 3.43x | long th50 wide TP 1.20% T120 | +7.24% / PF 1.28 | +14.71% | +5.46% | +8.66% | +3.79% |
| APEUSDT | ready | 100.0 | volume spike | +14.48% | 38.97% | 1.31x | long th50 wide TP 1.20% T90 | +7.17% / PF 1.95 | +14.55% | +22.83% | +6.79% | +3.28% |
| OPENUSDT | ready | 75.8 | 3d move;3d range;volume spike | -12.86% | 36.19% | 3.57x | long th70 base TP 1.20% T60 | +6.37% / PF 3.82 | +9.69% | +11.93% | +10.81% | +9.65% |
| REZUSDT | ready | 71.0 | 3d move;7d move;3d range;7d range | +30.24% | 49.79% | 1.80x | long th50 wide TP 1.20% T90 | +6.05% / PF 1.47 | +14.65% | +29.24% | +14.22% | +8.08% |
| AGTUSDT | ready | 89.8 | 7d move;7d range;volume spike | -30.97% | 99.85% | 2.17x | short th40 base TP 1.20% T120 | +5.71% / PF 5.64 | +17.34% | +3.22% | +0.43% | -0.35% |
| SPKUSDT | ready | 90.9 | volume spike | -5.16% | 21.53% | 0.43x | short th40 wide TP 0.35% T60 | +5.67% / PF 2.59 | +4.51% | -3.69% | +0.92% | -1.13% |
| NOTUSDT | ready | 69.0 | 7d range;volume spike | -4.06% | 78.04% | 2.55x | short th50 wide TP 1.20% T180 | +5.56% / PF 2.36 | +6.30% | +6.95% | +5.67% | +4.75% |
| DAMUSDT | hot_watch | 81.8 | 7d move;7d range;volume spike | +21.05% | 475.99% | 31.78x | short th50 wide TP 1.00% T90 | +16.78% / PF 2.71 | -2.60% | +4.93% | +7.50% | +5.73% |

## Hot Market Only

| Symbol | Hot score | Reasons | 3d move | 7d move | 7d range | Vol x | Avg quote volume 7d |
|---|---:|---|---:|---:|---:|---:|---:|
| 1000000BOBUSDT | 100.0 | 3d move;3d range;7d range;volume spike | +40.55% | +19.77% | 92.44% | 17.00x | $12,155,466 |
| 1000LUNCUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +14.52% | +37.04% | 70.50% | 11.97x | $98,394,800 |
| APEUSDT | 100.0 | volume spike | +4.01% | +14.48% | 38.97% | 1.31x | $98,985,509 |
| BABYUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +35.30% | +27.67% | 120.10% | 25.46x | $82,154,214 |
| BASUSDT | 100.0 | 3d move;3d range;7d range;volume spike | +13.08% | +19.20% | 63.51% | 0.70x | $17,644,095 |
| BIOUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +46.52% | +101.63% | 141.67% | 4.08x | $233,659,075 |
| BRUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +15.32% | +71.97% | 175.00% | 3.77x | $99,251,594 |
| BUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +225.58% | +214.23% | 368.76% | 49.71x | $209,698,204 |
| LABUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +201.26% | +171.03% | 600.97% | 19.99x | $880,156,321 |
| NAORISUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | -12.59% | +46.94% | 110.93% | 11.75x | $100,474,437 |
| ORCAUSDT | 100.0 | 7d move;3d range;7d range;volume spike | -5.77% | +49.70% | 103.75% | 7.22x | $321,965,946 |
| PUMPBTCUSDT | 100.0 | 7d move;7d range;volume spike | -4.81% | -47.47% | 109.37% | 1.12x | $4,609,193 |
| SKYAIUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +32.39% | +144.19% | 245.80% | 9.25x | $391,821,950 |
| TAGUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +131.61% | +123.61% | 292.62% | 14.05x | $67,341,300 |
| TACUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +34.95% | +178.61% | 228.98% | 19.21x | $69,732,714 |
| TSTUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +43.00% | +34.85% | 72.24% | 3.30x | $26,813,780 |
| UBUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +71.10% | +137.97% | 301.94% | 13.75x | $241,732,007 |
| ZBTUSDT | 100.0 | volume spike | +3.50% | -13.64% | 42.65% | 3.49x | $160,239,283 |
| ZEREBROUSDT | 100.0 | 7d move;3d range;7d range;volume spike | -0.15% | +71.52% | 177.43% | 13.28x | $82,162,626 |
| FHEUSDT | 98.1 | 3d move;7d move;3d range;7d range;volume spike | +30.85% | +27.03% | 58.06% | 2.34x | $9,602,335 |
| IRUSDT | 97.6 | 7d move;7d range;volume spike | +0.00% | -25.32% | 151.41% | 2.77x | $9,791,397 |
| HUSDT | 96.3 | 3d move;7d move;7d range;volume spike | +13.60% | +35.50% | 66.30% | 2.39x | $44,540,679 |
| AIOTUSDT | 95.8 | 3d move;7d move;3d range;7d range;volume spike | -21.18% | +37.59% | 141.77% | 2.15x | $169,012,822 |
| MEGAUSDT | 94.0 | 3d move;7d move;3d range;7d range;volume spike | -25.58% | -26.24% | 74.68% | 39.36x | $85,919,854 |
| SPKUSDT | 90.9 | volume spike | +0.31% | -5.16% | 21.53% | 0.43x | $22,136,755 |
| TRADOORUSDT | 90.0 | 3d move;3d range | +14.71% | +3.80% | 30.83% | 0.45x | $27,031,065 |
| AGTUSDT | 89.8 | 7d move;7d range;volume spike | +1.31% | -30.97% | 99.85% | 2.17x | $31,889,990 |
| ZKJUSDT | 89.6 | 7d move;7d range;volume spike | +0.00% | +30.81% | 365.12% | 67.23x | $101,086,226 |
| PIEVERSEUSDT | 88.2 | 3d range;volume spike | +4.27% | -6.98% | 29.41% | 0.19x | $17,706,917 |
| SWARMSUSDT | 87.8 | 7d move;7d range;volume spike | +0.39% | +42.47% | 59.47% | 3.61x | $63,556,111 |
| CHILLGUYUSDT | 87.3 | 3d move;3d range;7d range | +26.20% | +18.67% | 56.48% | 1.45x | $6,603,236 |
| KNCUSDT | 87.2 | 3d move;3d range;volume spike | +21.88% | +13.44% | 42.24% | 8.38x | $29,010,245 |
| AKTUSDT | 83.5 | 3d move;7d move;3d range;7d range;volume spike | +22.39% | +28.09% | 46.35% | 4.50x | $11,222,003 |
| KATUSDT | 83.3 | 7d move;volume spike | -11.83% | -22.84% | 39.52% | 0.43x | $37,609,193 |
| SPACEUSDT | 82.6 | 3d move;3d range;7d range;volume spike | +12.04% | +5.05% | 81.88% | 3.43x | $20,950,282 |
| DAMUSDT | 81.8 | 7d move;7d range;volume spike | +0.00% | +21.05% | 475.99% | 31.78x | $91,731,086 |
| NFPUSDT | 81.2 | 3d move;3d range;7d range;volume spike | +12.17% | -11.61% | 82.52% | 22.06x | $37,274,946 |
| GUNUSDT | 81.0 | volume spike | -0.88% | -1.01% | 16.34% | 0.33x | $9,038,344 |
| LUMIAUSDT | 79.8 | 3d range;7d range;volume spike | +6.53% | +2.63% | 55.03% | 10.37x | $26,168,960 |
| XNYUSDT | 79.7 | 3d move;3d range;7d range | +19.84% | +3.56% | 73.27% | 1.52x | $7,811,222 |
| B2USDT | 77.3 | 3d move;3d range;7d range;volume spike | +13.63% | -3.98% | 72.87% | 9.06x | $10,009,131 |
| VELVETUSDT | 75.9 | 3d move;3d range;7d range;volume spike | -15.41% | -9.34% | 49.21% | 2.15x | $9,543,214 |
| OPENUSDT | 75.8 | 3d move;3d range;volume spike | -19.04% | -12.86% | 36.19% | 3.57x | $21,436,309 |
| AINUSDT | 74.3 | 7d move | +4.64% | +23.40% | 33.54% | 1.26x | $7,968,565 |
| USTCUSDT | 74.1 | 7d move;3d range;volume spike | +5.13% | +20.67% | 42.35% | 4.48x | $9,816,908 |
| ORDIUSDT | 73.9 | 3d move;3d range;7d range | +23.36% | +17.47% | 56.59% | 0.53x | $87,115,241 |
| SPORTFUNUSDT | 73.9 | volume spike | +9.68% | +5.94% | 21.90% | 1.19x | $2,623,033 |
| BBUSDT | 72.8 | 3d move;7d move;3d range;volume spike | +17.44% | +22.32% | 39.13% | 2.00x | $10,625,273 |
| HYPERUSDT | 71.1 | volume spike | -3.65% | -5.06% | 26.19% | 0.60x | $18,434,684 |
| REZUSDT | 71.0 | 3d move;7d move;3d range;7d range | +14.17% | +30.24% | 49.79% | 1.80x | $9,178,121 |
| MITOUSDT | 70.2 | 7d move;3d range;volume spike | +11.06% | +23.69% | 43.14% | 2.93x | $3,659,686 |
| FIGHTUSDT | 69.9 | 3d move;3d range;7d range | +16.66% | +12.98% | 46.98% | 0.96x | $6,305,667 |
| NOTUSDT | 69.0 | 7d range;volume spike | +5.81% | -4.06% | 78.04% | 2.55x | $9,534,902 |
| PENGUUSDT | 68.2 | volume spike | -0.85% | +10.42% | 19.08% | 3.32x | $172,595,324 |
| EDUUSDT | 67.6 | volume spike | -2.07% | +2.65% | 27.78% | 0.49x | $10,133,516 |
| BROCCOLI714USDT | 66.6 | 7d range;volume spike | +0.00% | +7.55% | 48.98% | 2.93x | $17,366,021 |
| RAVEUSDT | 66.5 | 3d move;7d move;7d range | -12.08% | -31.54% | 52.42% | 0.07x | $75,442,599 |
| AXLUSDT | 66.1 | 3d move;7d move;3d range;7d range | +16.79% | +25.87% | 53.78% | 1.62x | $20,654,594 |
| MERLUSDT | 66.1 | 3d move;3d range | +18.81% | -5.12% | 39.29% | 0.58x | $5,852,726 |
| INTCUSDT | 65.1 | 7d move | +7.49% | +21.76% | 26.77% | 1.58x | $40,252,084 |
| PARTIUSDT | 65.1 | 3d move;7d move;3d range | +23.36% | +22.45% | 33.53% | 1.17x | $11,648,783 |
| CGPTUSDT | 65.1 | volume spike | +2.27% | +15.63% | 25.39% | 3.88x | $4,723,547 |
| TRIAUSDT | 65.0 | 3d range | +4.48% | +9.47% | 43.21% | 0.79x | $11,333,404 |
| USUSDT | 64.1 | 3d move;7d move;3d range | +25.83% | +25.72% | 34.30% | 0.75x | $2,010,284 |
| 4USDT | 63.9 | 3d move;3d range | +26.95% | +17.94% | 38.23% | 0.29x | $5,517,264 |
| ACHUSDT | 62.9 | 7d move;volume spike | +8.52% | +23.21% | 32.94% | 4.47x | $11,626,613 |
| AIOUSDT | 62.2 | 7d move | +6.36% | +32.21% | 42.77% | 1.25x | $5,686,390 |
| ONUSDT | 61.5 | 3d move;3d range | +21.88% | +9.21% | 44.67% | 0.21x | $7,230,805 |
| VICUSDT | 60.9 | 7d move;3d range;volume spike | +6.19% | -20.46% | 40.81% | 2.16x | $5,645,920 |
| LYNUSDT | 60.8 | 7d range | -3.76% | +2.23% | 51.54% | 1.65x | $23,991,565 |
| MUSDT | 60.7 | 7d move;7d range | -5.49% | -31.29% | 55.45% | 0.76x | $31,253,828 |
| ZENUSDT | 60.6 | 3d move;3d range | +21.88% | +16.08% | 32.03% | 1.13x | $16,043,268 |
| AXSUSDT | 59.5 | volume spike | -3.36% | -6.70% | 18.61% | 0.82x | $39,001,116 |
| WLFIUSDT | 59.4 | 7d move;7d range | -3.95% | -22.03% | 47.55% | 1.90x | $76,644,369 |
| BICOUSDT | 59.2 | volume spike | -1.84% | -18.10% | 36.83% | 2.47x | $4,138,955 |
| API3USDT | 59.1 | volume spike | +3.16% | +10.64% | 30.98% | 1.57x | $30,370,908 |
| ZKPUSDT | 59.0 | volume spike | +2.93% | -5.65% | 39.99% | 5.47x | $19,140,430 |
| PENDLEUSDT | 58.9 | volume spike | +11.34% | +18.75% | 32.02% | 2.72x | $33,352,669 |
| XVGUSDT | 58.5 | 3d move;3d range | +15.46% | +3.27% | 30.51% | 1.47x | $6,049,206 |
| METUSDT | 58.4 | volume spike | +4.72% | +0.06% | 18.95% | 0.25x | $3,558,344 |

## Data Errors

| Symbol | Error |
|---|---|
| AAPLUSDT | not enough candles: 39490 |
| AIGENSYNUSDT | not enough candles: 6345 |
| AVGOUSDT | not enough candles: 19340 |
| BABAUSDT | not enough candles: 19330 |
| BASEDUSDT | not enough candles: 49800 |
| BSBUSDT | not enough candles: 56895 |
| BZUSDT | not enough candles: 46970 |
| CHIPUSDT | not enough candles: 25485 |
| CLUSDT | not enough candles: 46980 |
| GENIUSUSDT | not enough candles: 25710 |
| GOOGLUSDT | not enough candles: 55270 |
| METAUSDT | not enough candles: 55290 |
| MSFTUSDT | not enough candles: 19350 |
| MUUSDT | not enough candles: 38071 |
| NATGASUSDT | not enough candles: 46960 |
| NVDAUSDT | not enough candles: 55280 |
| OPGUSDT | not enough candles: 16350 |
| PAYPUSDT | not enough candles: 59610 |
| PRLUSDT | not enough candles: 46890 |
| QQQUSDT | not enough candles: 39510 |
| SNDKUSDT | not enough candles: 38060 |
| SPYUSDT | not enough candles: 39500 |
| TSMUSDT | not enough candles: 39480 |
| XAUTUSDT | not enough candles: 55320 |
