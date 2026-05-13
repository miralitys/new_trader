# Paper Execution Journal

Generated: 2026-05-06T22:04:01.088366+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RIF | RIF Regime Monitor | 11 | 8 | 72.73% | 8 | -1.23% | 0.71 | -0.15% | time_stop=5;take_profit=2;end_of_data=1 |

## Files

- Journal CSV: `data/paper_execution_journal_rif_24h_2026-05-06.csv`
- Summary CSV: `data/paper_execution_summary_rif_24h_2026-05-06.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
