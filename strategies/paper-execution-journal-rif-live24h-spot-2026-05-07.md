# Paper Execution Journal

Generated: 2026-05-07T21:15:52.163595+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RIF | RIF Regime Monitor | 15 | 5 | 33.33% | 5 | +3.93% | 6.50 | +0.79% | take_profit=4;time_stop=1 |

## Files

- Journal CSV: `data/paper_execution_journal_rif_live24h_spot_2026-05-07.csv`
- Summary CSV: `data/paper_execution_summary_rif_live24h_spot_2026-05-07.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
