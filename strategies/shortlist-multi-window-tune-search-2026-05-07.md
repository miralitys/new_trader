# Shortlist Multi-Window Tune Search

Generated: 2026-05-07T23:55:19.211679+00:00

Ищем одну и ту же настройку, которая одновременно дает плюс на 1d / 7d / 30d / 60d.
Это не доказательство будущей прибыли, а фильтр против грубой подгонки под одни сутки.

## Best Per Strategy

| Coin | Strategy | Verdict | Variant | 1d Return / PF / Trades | 7d Return / PF / Trades | 30d Return / PF / Trades | 60d Return / PF / Trades |
|---|---|---|---|---:|---:|---:|---:|
| CHZ | CHZ LONG Best | passed_all_windows | thr60 atr>=0.0025 dist<=0.025 ret7 -0.40..0.10 tp0.0050 T90 off0.0005 | +0.46% / inf / 1 | +0.88% / 1.77 / 7 | +5.02% / 5.40 / 16 | +9.62% / 9.44 / 26 |
| ANKR | ANKR LONG Best | passed_all_windows | thr50 atr>=0.0000 dist<=0.025 ret7 -0.20..0.05 tp0.0100 T60 off0.0005 | +0.01% / inf / 1 | +2.00% / 1.68 / 15 | +2.18% / 1.10 / 85 | +5.30% / 1.07 / 220 |
| MANA | MANA LONG Best | no_candidates |  | n/a / n/a /  | n/a / n/a /  | n/a / n/a /  | n/a / n/a /  |
| SPELL | SPELL SHORT Best | no_candidates |  | n/a / n/a /  | n/a / n/a /  | n/a / n/a /  | n/a / n/a /  |
| GALA | GALA 7.3 protected | passed_all_windows | thr40 atr>=0.0000 dist<=any ret7 0.00..0.25 tp0.0025 T120 off0.0000 | +0.59% / 1.26 / 63 | +0.69% / 1.11 / 154 | +6.00% / 1.15 / 1021 | +13.52% / 1.27 / 1403 |
| GALA | GALA 11.2 watchlist | passed_all_windows | S80 L50 ret7 -0.50..0.25 tpS0.0028 tpL0.0050 T90 wS1.35 wL0.90 off0.0000 | +0.46% / 1.57 / 22 | +2.08% / 1.75 / 78 | +5.52% / 1.53 / 262 | +8.07% / 1.48 / 425 |

## Survivors

Найдено устойчивых кандидатов: 140.

## Diagnostics

| Symbol | Status | Candles | Start | End | Error |
|---|---:|---:|---|---|---|
| CHZUSDT | ok | 86400 | 2026-03-08T23:38:00+00:00 | 2026-05-07T23:37:59.999000+00:00 |  |
| ANKRUSDT | ok | 86400 | 2026-03-08T23:42:00+00:00 | 2026-05-07T23:41:59.999000+00:00 |  |
| MANAUSDT | ok | 86400 | 2026-03-08T23:44:00+00:00 | 2026-05-07T23:43:59.999000+00:00 |  |
| SPELLUSDT | ok | 86400 | 2026-03-08T23:47:00+00:00 | 2026-05-07T23:46:59.999000+00:00 |  |
| GALAUSDT | ok | 86400 | 2026-03-08T23:50:00+00:00 | 2026-05-07T23:49:59.999000+00:00 |  |

## Files

- Best CSV: `data/shortlist_multi_window_tune_best_2026-05-07.csv`
- Passing CSV: `data/shortlist_multi_window_tune_passing_2026-05-07.csv`
