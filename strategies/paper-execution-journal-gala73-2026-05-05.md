# Paper Execution Journal

Generated: 2026-05-05T15:16:08.317684+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| GALA | Минутка 7.3 | 95 | 49 | 51.58% | 49 | -0.06% | 0.98 | -0.00% | take_profit=40;time_stop=9 |

## Files

- Journal CSV: `data/paper_execution_journal_gala73_2026-05-05.csv`
- Summary CSV: `data/paper_execution_summary_gala73_2026-05-05.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
