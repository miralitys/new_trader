# Paper Execution Journal

Generated: 2026-05-04T20:42:39.644976+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 306 | 162 | 52.94% | 83 | -0.33% | 0.93 | -0.00% | take_profit=66;time_stop=17 |
| RIF | RIF Regime Monitor | 62 | 43 | 69.35% | 43 | +16.38% | 2.54 | +0.38% | time_stop=22;take_profit=21 |
| SPELL | SPELL SHORT Best | 17 | 15 | 88.24% | 15 | -1.04% | 0.91 | -0.07% | take_profit=11;stop_loss=3;time_stop=1 |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-04.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-04.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
