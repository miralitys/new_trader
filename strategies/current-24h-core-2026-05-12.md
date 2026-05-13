# Paper Execution Journal

Generated: 2026-05-13T02:36:37.659506+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| GALA | Минутка 10 | 13 | 5 | 38.46% | 5 | +0.11% | 3.33 | +0.02% | take_profit=4;end_of_data=1 |
| GALA | Минутка 11.2 | 17 | 6 | 35.29% | 5 | +0.10% | 3.33 | +0.02% | take_profit=4;end_of_data=1 |
| RIF | RIF Regime Monitor | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/current_24h_core_journal_2026-05-12.csv`
- Summary CSV: `data/current_24h_core_summary_2026-05-12.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
