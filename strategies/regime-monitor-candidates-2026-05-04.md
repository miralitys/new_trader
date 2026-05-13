# Regime Monitor Candidates

Проверка монет, похожих на RIF: базовая стратегия может быть плохой на 730 дней, но бот торгует только когда прошлые 30/60 дней показывали здоровый режим.

## Exact Results

| Монета | Режим | 730d Return | MaxDD | PF | Active Days | Вывод |
|---|---|---:|---:|---:|---:|---|
| RIFUSDT | health30_60 | +48.19% | 15.48% | 1.37 | 138 / 730 | Основной regime-кандидат |
| RIFUSDT | health30_60 + weekly kill 2% | +39.27% | 8.29% | 1.67 | 138 / 730 | Самая аккуратная версия |
| ACHUSDT | health30_60 | +3.61% | 14.99% | 1.07 | 45 / 730 | Слабый кандидат |
| ACHUSDT | health30_60 + weekly kill 2% | +8.06% | 6.76% | 1.25 | 45 / 730 | Можно поставить в monitor-watchlist |
| REZUSDT | health30_60 | +15.58% | 19.62% | 1.08 | 59 / 730 | Слабый кандидат, DD выше |
| REZUSDT | health30_60 + weekly kill 2% | +5.30% | 8.81% | 1.14 | 59 / 730 | Можно поставить в monitor-watchlist |

## Decision

- RIFUSDT остается главным кандидатом для regime-monitor.
- ACHUSDT можно добавить в тот же монитор, но только как защитный watchlist: доходность маленькая, зато DD низкий и PF в weekly-kill версии нормальный.
- REZUSDT тоже можно добавить, но осторожно: без weekly kill просадка почти 20%, а с weekly kill доходность падает до +5.30% за 730 дней.
- ZENUSDT, BICOUSDT, CHRUSDT, APEUSDT, AXLUSDT, RLCUSDT, EDUUSDT по точному/быстрому фильтру не проходят как рабочие аналоги RIF.

## Practical Monitor List

В один режимный монитор сейчас логично поставить:

| Уровень | Монеты |
|---|---|
| Core | RIFUSDT |
| Watchlist | ACHUSDT, REZUSDT |
| Отдельный wave-monitor | GUAUSDT, IRYSUSDT, B2USDT |

Главная идея: RIF торгуем как рабочий regime-кандидат, ACH и REZ пока только наблюдаем тем же алгоритмом включения/выключения.
