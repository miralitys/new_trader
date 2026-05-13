# Cashflow Legacy Tuning Summary

Дата: 2026-05-08

Цель: проверить, можно ли докрутить две старые cashflow-ветки:

- `Monthly Cashflow 10% 24M High Risk`: ONE 20% / SPELL 80%;
- `MOVR / CHZ / MANA Monthly 4%`: MOVR 50% / CHZ 25% / MANA 25%;
- отдельно проверить, помогает ли RIF как добавка к этим портфелям.

Важно: `SIFUSDT` в локальном Binance Futures inventory не найден. В проекте хорошо себя показывал именно `RIFUSDT`, поэтому в тесты добавлялся RIF.

## Короткий вывод

ONE / SPELL 10% остается только агрессивной recent-window идеей. На последних 24 месяцах база держит `24/24`, но на 36 месяцах разваливается полностью. Добавление RIF немного улучшает стресс на 24 месяцах, но не чинит 36 месяцев.

MOVR / CHZ / MANA не удалось превратить в стабильную 36-месячную cashflow-стратегию. На свежем участке лучше всего себя показала версия `CHZ 60% / MANA 40%`, но это recent-window кандидат, а не доказанная долгосрочная система.

RIF сильный как regime-модуль, но не как универсальная добавка для ежемесячной кассы. В cashflow-режиме он помогает отдельным окнам, но не дает стабильные `36/36` месяцев.

## ONE / SPELL 10%

Цель: `$100` в месяц с капитала `$1000`.

| Вариант | Окно | Base | Stress fee 0.03% | Stress fee 0.03% + slip 0.005% | Вывод |
|---|---:|---:|---:|---:|---|
| ONE 20% / SPELL 80%, scale 6 | 24M | `24/24`, DD `36.6%`, PF `1.41` | `17/24`, DD `72.1%`, PF `1.19` | `15/24`, DD `71.0%`, PF `1.13` | База красивая, стресс слабый |
| ONE 10% / RIF 10% / SPELL 80%, scale 7 | 24M | `24/24`, DD `39.8%`, PF `1.42` | `23/24`, DD `43.2%`, PF `1.38` | `17/24`, DD `75.5%`, PF `1.17` | RIF помогает stress fee, но просадка выше |
| ONE 20% / SPELL 80%, scale 6 | 36M | `0/36`, DD `98.8%`, PF `0.89` | `0/36`, DD `99.5%`, PF `0.83` | `0/36`, DD `99.7%`, PF `0.80` | Не проходит длинную историю |
| ONE 10% / RIF 10% / SPELL 80%, scale 7 | 36M | `0/36`, DD `99.6%`, PF `0.85` | `0/36`, DD `99.9%`, PF `0.77` | `0/36`, DD `99.9%`, PF `0.75` | RIF не спасает |

Вывод: 10% cashflow можно было красиво видеть на последних 24 месяцах, но как долгосрочная стратегия это слишком опасно. RIF-версия лучше переносит fee-only stress на 24M, но не проходит 36M и увеличивает риск.

## MOVR / CHZ / MANA 4%

Цель: `$40` в месяц с капитала `$1000`.

| Вариант | Окно | Base | Stress fee 0.03% | Stress fee 0.03% + slip 0.005% | Вывод |
|---|---:|---:|---:|---:|---|
| MOVR 50% / CHZ 25% / MANA 25%, scale 2.5 | 36M | `5/36`, DD `36.0%`, PF `1.10` | `6/36`, DD `30.7%`, PF `1.18` | `5/36`, DD `32.8%`, PF `1.13` | Не cashflow на длинной истории |
| MANA 20% / RIF 80%, scale 6 | 36M | `15/36`, DD `28.8%`, PF `1.43` | `15/36`, DD `30.0%`, PF `1.46` | `15/36`, DD `30.1%`, PF `1.42` | Лучше, но далеко от 36/36 |
| CHZ 60% / MANA 40%, scale 5 | 11M | `11/11`, DD `8.7%`, PF `4.18` | `11/11`, DD `8.9%`, PF `3.96` | `11/11`, DD `8.7%`, PF `3.95` | Лучший свежий вариант |
| CHZ 60% / MANA 40%, scale 5 | 36M | `2/36`, DD `72.4%`, PF `1.02` | `0/36`, DD `73.2%`, PF `0.98` | `0/36`, DD `69.8%`, PF `0.97` | Только recent-window, не core |

Вывод: если смотреть только свежий участок `2025-06` - `2026-04`, лучшая докрутка - `CHZ 60% / MANA 40%`, scale `5`, target `$40`, loss stop `5%`. Но на 36 месяцах она не работает, поэтому ее нельзя ставить рядом с главными cashflow-стратегиями.

## Что делать дальше

Не повышать статус этих двух веток до основных.

Оставить:

- ONE / SPELL 10% как high-risk recent-window archive;
- CHZ 60% / MANA 40% как свежий watchlist-кандидат;
- RIF отдельно как regime-monitor, а не как cashflow-стабилизатор.

Главные cashflow-стратегии пока не меняются:

- `Минутка Cashflow 1`: GALA / SPELL;
- `Минутка Cashflow 2`: CHZ / SHIB / SPELL.

## Файлы

- `data/cashflow_tune_one_spell_rif_10pct_summary_2026-05-08.csv`
- `data/cashflow_tune_one_spell_rif_10pct_24m_summary_2026-05-08.csv`
- `data/cashflow_tune_movr_chz_mana_rif_4pct_summary_2026-05-08.csv`
- `data/cashflow_tune_movr_chz_mana_rif_4pct_11m_summary_2026-05-08.csv`
- `data/cashflow_legacy_tune_comparison_2026-05-08.csv`
- `strategies/cashflow-tune-one-spell-rif-10pct-2026-05-08.md`
- `strategies/cashflow-tune-one-spell-rif-10pct-24m-2026-05-08.md`
- `strategies/cashflow-tune-movr-chz-mana-rif-4pct-2026-05-08.md`
- `strategies/cashflow-tune-movr-chz-mana-rif-4pct-11m-2026-05-08.md`
