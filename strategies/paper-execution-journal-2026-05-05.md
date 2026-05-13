# Paper Execution Journal

Generated: 2026-05-05T15:10:27.041588+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 180 | 103 | 57.22% | 49 | -0.41% | 0.85 | -0.01% | take_profit=38;time_stop=11 |
| RIF | RIF Regime Monitor | 60 | 41 | 68.33% | 41 | +15.05% | 2.43 | +0.37% | take_profit=20;time_stop=20;end_of_data=1 |
| SPELL | SPELL SHORT Best | 9 | 8 | 88.89% | 8 | +7.25% | inf | +0.91% | take_profit=7;time_stop=1 |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-05.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-05.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
