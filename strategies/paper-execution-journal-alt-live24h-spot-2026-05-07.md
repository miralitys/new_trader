# Paper Execution Journal

Generated: 2026-05-07T21:40:50.277612+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 2 | 2 | 100.00% | 2 | -2.91% | 0.00 | -1.46% | time_stop=2 |
| GALA | Минутка 11.2 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 7.3 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| RIF | RIF Regime Monitor | 17 | 6 | 35.29% | 6 | +3.94% | 6.52 | +0.66% | take_profit=4;time_stop=1;end_of_data=1 |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_execution_journal_alt_live24h_spot_2026-05-07.csv`
- Summary CSV: `data/paper_execution_summary_alt_live24h_spot_2026-05-07.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
