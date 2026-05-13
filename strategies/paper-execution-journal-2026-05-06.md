# Paper Execution Journal

Generated: 2026-05-06T15:07:14.881369+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 49 | 36 | 73.47% | 19 | -0.22% | 0.74 | -0.01% | take_profit=14;time_stop=5 |
| GALA | Минутка 7.3 | 31 | 19 | 61.29% | 19 | -0.33% | 0.72 | -0.02% | take_profit=15;time_stop=3;end_of_data=1 |
| RIF | RIF Regime Monitor | 62 | 44 | 70.97% | 44 | +13.06% | 1.93 | +0.30% | time_stop=22;take_profit=21;end_of_data=1 |
| SPELL | SPELL SHORT Best | 2 | 2 | 100.00% | 2 | +1.92% | inf | +0.96% | take_profit=2 |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-06.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-06.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
