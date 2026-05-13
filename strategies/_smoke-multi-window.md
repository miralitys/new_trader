# Shortlist Multi-Window Tune Search

Generated: 2026-05-07T23:38:42.170652+00:00

Ищем одну и ту же настройку, которая одновременно дает плюс на 1d / 7d / 30d / 60d.
Это не доказательство будущей прибыли, а фильтр против грубой подгонки под одни сутки.

## Best Per Strategy

| Coin | Strategy | Verdict | Variant | 1d Return / PF / Trades |
|---|---|---|---|---:|
| CHZ | CHZ LONG Best | no_full_pass_best_near_miss | thr50 atr>=0.0000 dist<=0.025 ret7 -0.50..0.25 tp0.0025 T30 off0.0000 | -0.31% / 0.97 / 59 |
| ANKR | ANKR LONG Best | no_full_pass_best_near_miss | thr50 atr>=0.0000 dist<=0.025 ret7 -0.50..0.25 tp0.0025 T30 off0.0000 | -2.15% / 0.71 / 35 |
| MANA | MANA LONG Best | no_full_pass_best_near_miss | thr50 atr>=0.0000 dist<=0.025 ret7 -0.50..0.25 tp0.0025 T30 off0.0000 | -2.18% / 0.47 / 21 |
| SPELL | SPELL SHORT Best | no_full_pass_best_near_miss | thr50 atr>=0.0000 dist<=0.025 ret7 -0.50..0.25 tp0.0025 T30 off0.0000 | -2.32% / 0.46 / 25 |
| GALA | GALA 7.3 protected | no_full_pass_best_near_miss | thr40 atr>=0.0000 dist<=0.025 ret7 -0.50..0.25 tp0.0025 T30 off0.0000 | -0.41% / 0.91 / 96 |
| GALA | GALA 11.2 watchlist | no_full_pass_best_near_miss | S40 L50 ret7 -0.50..0.25 tpS0.0028 tpL0.0025 T30 wS0.00 wL0.90 off0.0000 | -0.04% / 0.93 / 41 |

## Survivors

Устойчивых кандидатов, которые прошли все окна, не найдено.

## Diagnostics

| Symbol | Status | Candles | Start | End | Error |
|---|---:|---:|---|---|---|
| CHZUSDT | ok | 1440 | 2026-05-06T23:36:00+00:00 | 2026-05-07T23:35:59.999000+00:00 |  |
| ANKRUSDT | ok | 1440 | 2026-05-06T23:37:00+00:00 | 2026-05-07T23:36:59.999000+00:00 |  |
| MANAUSDT | ok | 1440 | 2026-05-06T23:37:00+00:00 | 2026-05-07T23:36:59.999000+00:00 |  |
| SPELLUSDT | ok | 1440 | 2026-05-06T23:37:00+00:00 | 2026-05-07T23:36:59.999000+00:00 |  |
| GALAUSDT | ok | 1440 | 2026-05-06T23:38:00+00:00 | 2026-05-07T23:37:59.999000+00:00 |  |

## Files

- Best CSV: `data/_smoke_multi_window_best.csv`
- Passing CSV: `data/_smoke_multi_window_passing.csv`
