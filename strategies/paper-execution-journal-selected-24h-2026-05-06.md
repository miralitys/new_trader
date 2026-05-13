# Paper Execution Journal

Generated: 2026-05-06T22:05:21.706105+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 7 | 6 | 85.71% | 4 | +0.11% | 2.32 | +0.03% | take_profit=3;time_stop=1 |
| GALA | Минутка 7.3 | 5 | 4 | 80.00% | 4 | -0.04% | 0.81 | -0.01% | take_profit=3;end_of_data=1 |

## Files

- Journal CSV: `data/paper_execution_journal_selected_24h_2026-05-06.csv`
- Summary CSV: `data/paper_execution_summary_selected_24h_2026-05-06.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
