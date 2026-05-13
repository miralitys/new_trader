# RIF Live Readiness

RIFUSDT сейчас главный кандидат на paper-live наблюдение. Это не “включаем на весь депозит”, а отдельный режим проверки перед маленьким live-размером.

## Почему RIF

| Проверка | Результат |
|---|---:|
| Daily monitor 30d | +30.51% |
| PF 30d | 2.15 |
| MaxDD 30d | 6.00% |
| Stress taker 30d | +6.60% |
| Paper execution 7d | +15.05% |
| Paper PF 7d | 2.43 |
| Paper fill rate | 68.33% |

RIF прошел три слоя: свежий health-check, stress исполнения и paper execution journal.

## Рабочая Логика

- symbol: RIFUSDT
- direction: LONG
- setup: th50 wide
- TP: 1.2%
- SL: 4%
- time stop: 90 минут
- entry: maker limit
- fee: 0.02% за сторону
- base protection: daily loss stop 2%
- defensive режим: weekly kill 2%

## Когда Торговать

RIF можно оставлять в `TRADE`, только если:

- 30d return > 0;
- 30d PF >= 1.10;
- 30d MaxDD <= 15%;
- 30d trades >= 20;
- 60d return > 0;
- 60d PF >= 1.05;
- 60d MaxDD <= 20%;
- 60d trades >= 40;
- paper execution за 7 дней не отрицательный;
- paper PF >= 1.0;
- accepted paper trades >= 5.

## Когда Выключать

Перевести RIF в `WATCH/OFF`, если:

- paper execution 7d ушел в минус;
- paper PF < 1.0;
- fill rate резко упал;
- 30d или 60d health перестал проходить;
- DD за неделю приблизился к 2%;
- начали часто появляться time-stop выходы с минусом.

## Текущий Вывод

На 2026-05-05 RIF является самым подтвержденным кандидатом проекта.

Следующий режим: 7-14 дней paper-live наблюдения с ежедневным отчетом в чат. Если RIF продолжит держать paper plus, PF выше 1.2 и нормальное исполнение лимиток, можно будет обсуждать маленький live-size.
