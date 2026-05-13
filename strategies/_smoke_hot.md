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
| watch | 0 |
| paper_trap | 0 |
| skip | 0 |
| cold | 0 |

## Action List

| Symbol | Decision | Hot score | Reasons | 7d move | 7d range | Vol x | Setup | Strict 7d | Strict 14d | Strict 30d | Base 7d | Taker 7d |
|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| NOTUSDT | ready | 69.0 | 7d range;volume spike | -4.06% | 78.04% | 2.55x | short th50 wide TP 1.20% T180 | +5.56% / PF 2.36 | +6.30% | +6.95% | +5.67% | +4.75% |

## Hot Market Only

| Symbol | Hot score | Reasons | 3d move | 7d move | 7d range | Vol x | Avg quote volume 7d |
|---|---:|---|---:|---:|---:|---:|---:|
| NOTUSDT | 69.0 | 7d range;volume spike | +5.81% | -4.06% | 78.04% | 2.55x | $9,534,902 |
