# Best Strategies Rescue Matrix

Срез защитных правок по стратегиям из реестра `Лучшие стратегии`.

Проверка сделана на Binance Futures archive, maker-limit вход с откатом `0.05%`, fee `0.02%`, slippage `0`.

| Coin | Strategy | 7d best | 7d | 30d best | 30d | 60d best | 60d | Решение |
|---|---|---|---:|---|---:|---|---:|---|
| ANKR | ANKR LONG Best | base | +0.00% | base | +1.20% | base | +14.12% | кандидат |
| CHZ | CHZ LONG Best | threshold>=60 | +0.48% | base | +4.53% | base | +8.31% | кандидат |
| GALA | GALA Minutka 10 | base | +0.13% | return_7d<=0.05 | +1.46% | 1h long_score>=60 | -2.53% | watchlist |
| GALA | GALA Minutka 11.2 | long only | +0.11% | base | +2.66% | 1h filter | +0.03% | кандидат |
| GALA | GALA Minutka 7.3 | time_stop 60m | +0.10% | time_stop 60m | +0.50% | 1h filter | +3.71% | кандидат |
| JASMY | JASMY SHORT Best | base | +0.00% | time_stop 30m | +1.71% | base | +2.60% | кандидат |
| MANA | MANA LONG Best | base | +0.46% | return_7d<=0.05 | +4.60% | return_7d<=0.05 | +4.65% | кандидат |
| ONE | ONE Minutka 11.2 | 1h filter | +0.13% | 1h short_score>=60 | -5.61% | 1h short_score>=60 | -9.85% | watchlist |
| SAND | SAND LONG Best | threshold>=80 | +0.00% | base | -0.81% | base | -1.26% | не брать сейчас |
| SHIB | SHIB LONG Best | base | +0.00% | threshold>=60 | -0.08% | return_7d<=0.05 | +3.80% | watchlist |
| SPELL | SPELL SHORT Best | base | +0.96% | threshold>=80 | +4.68% | threshold>=80 | +4.62% | кандидат |

## Короткий вывод

- Стабильно полезные правки: GALA 7.3 через `1h/time_stop`, MANA через `return_7d<=0.05`, SPELL через `threshold>=80`.
- CHZ, ANKR, JASMY на 30/60 днях уже плюс: их лучше не ломать, а оставить с мониторингом.
- ONE и SAND пока не удалось честно вывести в плюс на 30/60 днях.
- SHIB оживает на 60 днях через `return_7d<=0.05`, но на 30 днях еще слабая.

## Files

- `data/best_strategy_rescue_best_7d_2026-05-07.csv`
- `data/best_strategy_rescue_best_30d_2026-05-07.csv`
- `data/best_strategy_rescue_best_60d_2026-05-07.csv`
- `data/best_strategy_rescue_summary_7d_2026-05-07.csv`
- `data/best_strategy_rescue_summary_30d_2026-05-07.csv`
- `data/best_strategy_rescue_summary_60d_2026-05-07.csv`
