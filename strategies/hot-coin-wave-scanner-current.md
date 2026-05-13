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
| ready | 10 |
| hot_watch | 1 |
| watch | 3 |
| paper_trap | 0 |
| skip | 1 |
| cold | 0 |

## Action List

| Symbol | Decision | Hot score | Reasons | 7d move | 7d range | Vol x | Setup | Strict 7d | Strict 14d | Strict 30d | Base 7d | Taker 7d |
|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| NFPUSDT | ready | 81.2 | 3d move;3d range;7d range;volume spike | -11.61% | 82.52% | 22.06x | short th60 wide TP 0.70% T180 | +25.21% / PF 1.92 | +20.70% | +19.71% | +21.18% | -1.82% |
| SPELLUSDT | ready | 39.1 | volume spike | +1.15% | 16.35% | 5.50x | long th50 wide TP 1.20% T90 | +21.60% / PF 2.71 | +19.33% | +19.00% | +16.43% | +16.44% |
| CHRUSDT | ready | 57.2 | 7d move;3d range | +20.75% | 41.62% | 1.08x | long th50 wide TP 0.35% T90 | +16.23% / PF 2.05 | +14.81% | +5.26% | +19.80% | +10.43% |
| BBUSDT | ready | 72.8 | 3d move;7d move;3d range;volume spike | +22.32% | 39.13% | 2.00x | long th50 wide TP 1.00% T90 | +15.78% / PF 1.44 | +10.50% | +17.43% | +19.66% | +14.90% |
| ZENUSDT | ready | 60.6 | 3d move;3d range | +16.08% | 32.03% | 1.13x | long th50 wide TP 1.20% T120 | +13.52% / PF 4.58 | +15.40% | +33.79% | +13.29% | +12.06% |
| RLCUSDT | ready | 56.4 | 3d move | +6.80% | 23.51% | 1.68x | long th50 wide TP 1.20% T90 | +12.47% / PF 2.42 | +18.63% | +6.50% | +14.65% | +13.60% |
| AXLUSDT | ready | 66.1 | 3d move;7d move;3d range;7d range | +25.87% | 53.78% | 1.62x | long th50 base TP 1.00% T180 | +11.08% / PF 2.41 | +9.64% | +11.15% | +8.19% | +6.19% |
| XVGUSDT | ready | 58.5 | 3d move;3d range | +3.27% | 30.51% | 1.47x | short th40 base TP 1.20% T90 | +7.43% / PF 1.68 | +6.78% | -3.78% | +2.97% | +1.19% |
| APEUSDT | ready | 100.0 | volume spike | +14.48% | 38.97% | 1.31x | long th50 wide TP 1.20% T90 | +7.17% / PF 1.95 | +14.55% | +22.83% | +6.79% | +3.28% |
| REZUSDT | ready | 71.0 | 3d move;7d move;3d range;7d range | +30.24% | 49.79% | 1.80x | long th50 wide TP 1.20% T90 | +6.05% / PF 1.47 | +14.65% | +29.24% | +14.22% | +8.08% |
| USTCUSDT | hot_watch | 74.1 | 7d move;3d range;volume spike | +20.67% | 42.35% | 4.48x | short th60 base TP 1.20% T60 | +7.94% / PF 2.85 | -0.98% | -5.75% | +4.80% | +3.05% |
| API3USDT | watch | 59.1 | volume spike | +10.64% | 30.98% | 1.57x | long th50 base TP 1.00% T180 | +2.80% / PF 1.68 | -1.65% | -2.27% | +1.93% | +0.98% |
| ORDIUSDT | watch | 73.9 | 3d move;3d range;7d range | +17.47% | 56.59% | 0.53x | long th50 base TP 0.35% T90 | +1.83% / PF 1.42 | -1.62% | -4.38% | +3.62% | +1.65% |
| KNCUSDT | watch | 87.2 | 3d move;3d range;volume spike | +13.44% | 42.24% | 8.38x | long th50 base TP 1.20% T120 | +1.16% / PF inf | -1.63% | -4.11% | +2.33% | +2.21% |
| 1000LUNCUSDT | skip | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +37.04% | 70.50% | 11.97x | short th40 base TP 1.20% T90 | +0.00% / PF 0.00 | +1.94% | -1.50% | +0.00% | +0.00% |

## Hot Market Only

| Symbol | Hot score | Reasons | 3d move | 7d move | 7d range | Vol x | Avg quote volume 7d |
|---|---:|---|---:|---:|---:|---:|---:|
| APEUSDT | 100.0 | volume spike | +4.01% | +14.48% | 38.97% | 1.31x | $98,985,509 |
| 1000LUNCUSDT | 100.0 | 3d move;7d move;3d range;7d range;volume spike | +14.52% | +37.04% | 70.50% | 11.97x | $98,394,800 |
| KNCUSDT | 87.2 | 3d move;3d range;volume spike | +21.88% | +13.44% | 42.24% | 8.38x | $29,010,245 |
| NFPUSDT | 81.2 | 3d move;3d range;7d range;volume spike | +12.17% | -11.61% | 82.52% | 22.06x | $37,274,946 |
| USTCUSDT | 74.1 | 7d move;3d range;volume spike | +5.13% | +20.67% | 42.35% | 4.48x | $9,816,908 |
| ORDIUSDT | 73.9 | 3d move;3d range;7d range | +23.36% | +17.47% | 56.59% | 0.53x | $87,115,241 |
| BBUSDT | 72.8 | 3d move;7d move;3d range;volume spike | +17.44% | +22.32% | 39.13% | 2.00x | $10,625,273 |
| REZUSDT | 71.0 | 3d move;7d move;3d range;7d range | +14.17% | +30.24% | 49.79% | 1.80x | $9,178,121 |
| AXLUSDT | 66.1 | 3d move;7d move;3d range;7d range | +16.79% | +25.87% | 53.78% | 1.62x | $20,654,594 |
| ZENUSDT | 60.6 | 3d move;3d range | +21.88% | +16.08% | 32.03% | 1.13x | $16,043,268 |
| API3USDT | 59.1 | volume spike | +3.16% | +10.64% | 30.98% | 1.57x | $30,370,908 |
| XVGUSDT | 58.5 | 3d move;3d range | +15.46% | +3.27% | 30.51% | 1.47x | $6,049,206 |
| CHRUSDT | 57.2 | 7d move;3d range | +8.65% | +20.75% | 41.62% | 1.08x | $6,230,355 |
| RLCUSDT | 56.4 | 3d move | +14.73% | +6.80% | 23.51% | 1.68x | $2,471,373 |
| SPELLUSDT | 39.1 | volume spike | +1.09% | +1.15% | 16.35% | 5.50x | $7,958,357 |

## Data Errors

| Symbol | Error |
|---|---|
| AMPUSDT | No recent futures archive files found for AMPUSDT |
