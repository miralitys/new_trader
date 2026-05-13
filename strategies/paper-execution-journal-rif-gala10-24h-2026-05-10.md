# Paper Execution Journal

Generated: 2026-05-10T15:39:29.654794+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| GALA | Минутка 10 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| RIF | RIF Regime Monitor | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_execution_journal_rif_gala10_24h_2026-05-10.csv`
- Summary CSV: `data/paper_execution_summary_rif_gala10_24h_2026-05-10.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
