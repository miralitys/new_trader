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
| ready | 1 |
| hot_watch | 0 |
| watch | 1 |
| paper_trap | 0 |
| skip | 1 |
| cold | 0 |

## Action List

| Symbol | Decision | Hot score | Reasons | 7d move | 7d range | Vol x | Setup | Strict 7d | Strict 14d | Strict 30d | Base 7d | Taker 7d |
|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| NOTUSDT | ready | 69.0 | 7d range;volume spike | -4.06% | 78.04% | 2.55x | short th50 wide TP 1.20% T180 | +5.56% / PF 2.36 | +6.30% | +6.95% | +5.67% | +4.75% |
| RUNEUSDT | watch | 52.6 | volume spike | +0.88% | 11.68% | 1.09x | short th40 wide TP 0.70% T60 | +1.99% / PF inf | -3.49% | -3.24% | -2.33% | -2.41% |
| AXSUSDT | skip | 59.5 | volume spike | -6.70% | 18.61% | 0.82x | short th40 base TP 1.20% T90 | +0.00% / PF 0.00 | -0.26% | +3.48% | +0.00% | +0.00% |

## Hot Market Only

| Symbol | Hot score | Reasons | 3d move | 7d move | 7d range | Vol x | Avg quote volume 7d |
|---|---:|---|---:|---:|---:|---:|---:|
| NOTUSDT | 69.0 | 7d range;volume spike | +5.81% | -4.06% | 78.04% | 2.55x | $9,534,902 |
| AXSUSDT | 59.5 | volume spike | -3.36% | -6.70% | 18.61% | 0.82x | $39,001,116 |
| RUNEUSDT | 52.6 | volume spike | +3.38% | +0.88% | 11.68% | 1.09x | $6,901,906 |
