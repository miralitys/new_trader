# Paper Execution Journal

Generated: 2026-05-07T15:16:20.676290+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RIF | RIF Regime Monitor | 21 | 16 | 76.19% | 16 | +7.06% | 2.03 | +0.44% | take_profit=12;time_stop=4 |

## Files

- Journal CSV: `data/paper_execution_journal_rif_24h_2026-05-07.csv`
- Summary CSV: `data/paper_execution_summary_rif_24h_2026-05-07.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
