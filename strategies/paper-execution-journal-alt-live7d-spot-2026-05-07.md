# Paper Execution Journal

Generated: 2026-05-07T21:44:05.950912+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 3 | 2 | 66.67% | 2 | -2.91% | 0.00 | -1.46% | time_stop=2 |
| GALA | Минутка 11.2 | 153 | 59 | 38.56% | 41 | -0.52% | 0.82 | -0.01% | take_profit=37;time_stop=4 |
| GALA | Минутка 7.3 | 91 | 34 | 37.36% | 34 | -0.28% | 0.87 | -0.01% | take_profit=31;time_stop=3 |
| RIF | RIF Regime Monitor | 95 | 31 | 32.63% | 31 | +15.64% | 2.42 | +0.50% | take_profit=23;time_stop=7;end_of_data=1 |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_execution_journal_alt_live7d_spot_2026-05-07.csv`
- Summary CSV: `data/paper_execution_summary_alt_live7d_spot_2026-05-07.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
