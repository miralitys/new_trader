# Overnight Research Human Shortlist

Дата: 2026-05-09.

Проверка была сделана по 669 локальным Binance Futures USDT-инструментам на 1m-данных. Семейства стратегий были разноплановые: trend pullback, breakout continuation, exhaustion reversal, volatility expansion.

## Главное

- Самая практичная новая ветка: `exhaustion_reversal`, особенно SHORT после перегрева.
- Самая доходная ветка: `trend_pullback SHORT`, но она часто дает большую просадку и свежие 1d/7d иногда пустые или минусовые.
- Лучший спокойный кандидат ночи: `REZUSDT exhaustion_reversal SHORT`.
- Хорошие кандидаты на отдельное добивание: `NFPUSDT`, `TAOUSDT`, `HIGHUSDT`, `SANTOSUSDT`, `CHILLGUYUSDT`.
- Очень доходные, но рискованные кандидаты: `CELOUSDT`, `ALICEUSDT`, `DYDXUSDT`.

## Короткий shortlist

| Монета | Семья | Сторона | Вариант | Win windows | 1d | 7d | 30d | 365d | 730d | PF365 | DD365 | Месяцы + | Худший месяц | Статус |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `REZUSDT` | exhaustion_reversal | short | `exhaustion_short_ret0.08_tp0.006_sl0.025_t150_pos0.25` | 8/8 | +0.63% | +1.00% | +1.00% | +4.54% | +1.95% | 1.33 | 2.73% | 14/26 | -2.06% | рабочий кандидат на full tune |
| `HIGHUSDT` | exhaustion_reversal | long | `exhaustion_long_ret0.08_tp0.004_sl0.018_t90_pos0.25` | 7/8 | +0.00% | +0.23% | +0.40% | +1.33% | +0.26% | 1.70 | 0.65% | n/a | n/a | рабочий кандидат на full tune |
| `NFPUSDT` | exhaustion_reversal | short | `exhaustion_short_ret0.08_tp0.006_sl0.025_t150_pos0.25` | 7/8 | +0.00% | +0.50% | +1.13% | +2.25% | +2.34% | 1.61 | 1.09% | n/a | n/a | рабочий кандидат на full tune |
| `SANTOSUSDT` | exhaustion_reversal | short | `exhaustion_short_ret0.05_tp0.006_sl0.025_t150_pos0.25` | 7/7 | +0.25% | +0.25% | +1.01% | +3.03% | n/a | 1.31 | 1.93% | n/a | n/a | watchlist, мало истории или нужна проверка |
| `TAOUSDT` | exhaustion_reversal | short | `exhaustion_short_ret0.08_tp0.006_sl0.025_t150_pos0.25` | 7/8 | +0.00% | +0.50% | +0.63% | +1.54% | +2.82% | 1.18 | 2.56% | n/a | n/a | рабочий кандидат на full tune |
| `CHILLGUYUSDT` | exhaustion_reversal | long | `exhaustion_long_ret0.05_tp0.006_sl0.025_t150_pos0.25` | 7/7 | +0.25% | +0.50% | +1.64% | +2.66% | n/a | 1.10 | 4.43% | n/a | n/a | watchlist, мало истории или нужна проверка |
| `CELOUSDT` | trend_pullback | short | `trend_pullback_short_rsi38-52_tp0.008_sl0.03_t180_pos0.5` | 6/8 | +0.00% | +0.00% | +0.71% | +335.28% | +229.33% | 1.40 | 22.17% | n/a | n/a | high-return watchlist, нужна защита DD |
| `ALICEUSDT` | trend_pullback | short | `trend_pullback_short_rsi48-62_tp0.008_sl0.03_t180` | 6/8 | +0.00% | +0.00% | +2.28% | +361.76% | +203.20% | 1.31 | 27.55% | n/a | n/a | high-return watchlist, нужна защита DD |
| `DYDXUSDT` | trend_pullback | short | `trend_pullback_short_rsi48-62_tp0.008_sl0.03_t180_pos0.75` | 6/8 | +0.00% | +0.00% | +9.23% | +271.47% | +260.48% | 1.26 | 31.67% | n/a | n/a | high-return watchlist, нужна защита DD |

## Что брать в следующий этап

1. `REZUSDT exhaustion_reversal SHORT` — первый кандидат на полное сохранение и tuning.
2. `NFPUSDT exhaustion_reversal SHORT` — меньше доходность, но хороший PF и положительный 730d.
3. `TAOUSDT exhaustion_reversal SHORT` — интересный 730d, но надо снизить DD.
4. `HIGHUSDT exhaustion_reversal LONG` — низкая доходность, зато хороший PF; можно попробовать поднять позицию/TP.
5. `CELO/ALICE trend_pullback SHORT` — высокий потенциал, но только после защиты от просадки, как делали с DYDX.

## Файлы

- Полный отчет: `strategies/overnight-new-strategy-research-2026-05-09.md`
- Shortlist CSV: `data/overnight_strategy_human_shortlist_2026-05-09.csv`
- Deep CSV: `data/overnight_strategy_deep_2026-05-09.csv`
- Monthly CSV: `data/overnight_strategy_monthly_2026-05-09.csv`

## Дополнительная месячная проверка shortlist

| Монета | Семья | Месяцев | Плюс | Минус | Ноль | Худший месяц | Лучший месяц | Средний месяц |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `NFPUSDT` | exhaustion_reversal SHORT | 30 | 19 | 8 | 3 | -0.89% | +2.81% | +0.18% |
| `DYDXUSDT` | trend_pullback SHORT | 36 | 16 | 18 | 2 | -21.05% | +85.03% | +4.02% |
| `HIGHUSDT` | exhaustion_reversal LONG | 36 | 15 | 12 | 9 | -2.67% | +0.98% | -0.08% |
| `TAOUSDT` | exhaustion_reversal SHORT | 26 | 14 | 10 | 2 | -1.40% | +2.01% | +0.09% |
| `REZUSDT` | exhaustion_reversal SHORT | 26 | 14 | 11 | 1 | -2.06% | +2.18% | +0.05% |
| `ALICEUSDT` | trend_pullback SHORT | 36 | 13 | 22 | 1 | -13.88% | +135.02% | +3.92% |
| `SANTOSUSDT` | exhaustion_reversal SHORT | 20 | 13 | 4 | 3 | -2.91% | +1.13% | +0.12% |
| `CELOUSDT` | trend_pullback SHORT | 36 | 11 | 24 | 1 | -10.96% | +80.48% | +2.93% |
| `CHILLGUYUSDT` | exhaustion_reversal LONG | 19 | 11 | 8 | 0 | -5.54% | +1.38% | -0.41% |

Вывод по месяцам: самый ровный кандидат из ночного поиска — `NFPUSDT exhaustion_reversal SHORT`. Самые доходные `CELO/ALICE/DYDX` держатся на редких мощных месяцах, но месячная стабильность слабая, поэтому их нельзя брать без отдельной защиты просадки.
