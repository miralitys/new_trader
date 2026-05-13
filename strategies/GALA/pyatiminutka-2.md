# Пятиминутка 2

## Название

GALAUSDT 5m SHORT regime-filtered maker scalp

## Идея

Пятиминутка 2 - это не прямой перенос Минутки 2 на `5m`.

Прямой клон был проверен как контрольный вариант и быстро ослаб:

| Период | Сделок | Return | Win rate | PF | Max DD |
|---|---:|---:|---:|---:|---:|
| 7d | 132 | +0.85% | 81.82% | 1.17 | 1.75% |
| 30d | 513 | -1.08% | 82.85% | 0.95 | 3.81% |
| 90d | 1 697 | -2.88% | 83.50% | 0.96 | 8.52% |

Поэтому рабочая версия пятиминутки сделана отдельно:

- слабее плечо позиции;
- мягче фильтр сигнала;
- шире стоп;
- дольше выход по времени;
- добавлен фильтр рыночного режима;
- добавлен дневной автостоп.

Цель этой версии - проверить, можно ли на `5m` сохранить плюс на 7, 30, 90,
180 и 365 днях без полного развала на длинном окне.

## Основные параметры

| Параметр | Значение |
|---|---:|
| Пара | `GALAUSDT` |
| Таймфрейм | `5m` |
| Направление | `SHORT` |
| Вход | Лимитный у текущей цены |
| Размер позиции | `24%` текущего баланса |
| Комиссия | `0.02%` вход + `0.02%` выход |
| Проскальзывание | `0` |
| Фильтр сигнала | `short_score >= 40` |
| Тейк | `0.25%` |
| Стоп | `3%` |
| Выход по времени | `180 минут` |
| Дневной автостоп | `1%` |

## Фильтр рыночного режима

Сделка разрешена только если на закрытой сигнальной свече выполнены все условия:

| Фильтр | Значение |
|---|---:|
| ATR% | `>= 0.25%` |
| Дистанция close от EMA200 | от `-1.5%` до `+1.5%` |
| Доходность за 7 дней | от `-40%` до `+10%` |

Смысл фильтра: не шортить GALA в любом месте, а брать только участки, где цена
рядом с EMA200, волатильность достаточная, но недельное движение еще не стало
слишком экстремальным.

## Команда

```bash
python3 scripts/gala_mb_backtest.py --market futures_archive --symbol GALAUSDT --interval 5m --days 365 --warmup-days 7 --direction short \
  --entry-mode maker_limit \
  --limit-entry-offset-pct 0 \
  --limit-entry-timeout-min 5 \
  --fee-pct 0.0002 \
  --slippage-pct 0 \
  --position-pct 0.24 \
  --short-threshold 40 \
  --short-tp-pct 0.0025 \
  --short-sl-pct 0.030 \
  --short-time-stop-min 180 \
  --daily-loss-stop-pct 0.01 \
  --filter-atr-min-pct 0.0025 \
  --filter-dist-ema200-min -0.015 \
  --filter-dist-ema200-max 0.015 \
  --filter-return-7d-min -0.40 \
  --filter-return-7d-max 0.10
```

## Результаты

| Период | Сделок | Return | Win rate | PF | Max DD | Expectancy |
|---|---:|---:|---:|---:|---:|---:|
| 7d | 124 | +3.21% | 91.94% | 2.21 | 0.67% | +0.0255% |
| 30d | 502 | +7.92% | 90.24% | 1.51 | 1.10% | +0.0153% |
| 90d | 1 477 | +19.95% | 90.86% | 1.37 | 2.57% | +0.0124% |
| 180d | 2 644 | +23.62% | 89.45% | 1.23 | 3.87% | +0.0081% |
| 365d | 4 481 | +5.29% | 87.95% | 1.03 | 19.16% | +0.0013% |

## Exit reasons, 365 дней

| Причина выхода | Количество |
|---|---:|
| Тейк | 3 935 |
| Выход по времени | 438 |
| Стоп | 108 |

## CSV

Результаты сохранены в:

| Период | Candles | Trades | Equity |
|---|---|---|---|
| 7d | `data/pyatiminutka2_candidate_7d_candles.csv` | `data/pyatiminutka2_candidate_7d_trades.csv` | `data/pyatiminutka2_candidate_7d_equity.csv` |
| 30d | `data/pyatiminutka2_candidate_30d_candles.csv` | `data/pyatiminutka2_candidate_30d_trades.csv` | `data/pyatiminutka2_candidate_30d_equity.csv` |
| 90d | `data/pyatiminutka2_candidate_90d_candles.csv` | `data/pyatiminutka2_candidate_90d_trades.csv` | `data/pyatiminutka2_candidate_90d_equity.csv` |
| 180d | `data/pyatiminutka2_candidate_180d_candles.csv` | `data/pyatiminutka2_candidate_180d_trades.csv` | `data/pyatiminutka2_candidate_180d_equity.csv` |
| 365d | `data/pyatiminutka2_candidate_365d_candles.csv` | `data/pyatiminutka2_candidate_365d_trades.csv` | `data/pyatiminutka2_candidate_365d_equity.csv` |

## Вывод

Пятиминутка 2 заметно лучше прямого 5m-клона: на 7, 30, 90, 180 и 365 днях
результат остается положительным.

Но годовой результат слабый: всего `+5.29%` при максимальной просадке `19.16%`
и PF `1.03`. Это значит, что преимущество на длинном окне почти исчезает.

Практический вывод: Пятиминутку 2 можно сохранить как первый отдельный 5m-кандидат,
но пока нельзя считать ее готовой рабочей стратегией. Следующий шаг - снижать
годовую просадку и делать стресс-тест комиссии/исполнения.
