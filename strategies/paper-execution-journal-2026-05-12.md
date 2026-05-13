# Paper Execution Journal

Generated: 2026-05-12T11:48:20.031493+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 2 | 2 | 100.00% | 2 | -1.52% | 0.39 | -0.76% | take_profit=1;time_stop=1 |
| GALA | Минутка 10 | 16 | 15 | 93.75% | 15 | +0.18% | 1.57 | +0.01% | take_profit=13;time_stop=2 |
| GALA | Минутка 11.2 | 37 | 32 | 86.49% | 20 | -0.34% | 0.75 | -0.02% | take_profit=18;time_stop=1;stop_loss=1 |
| GALA | Минутка 7.3 | 21 | 17 | 80.95% | 17 | -0.64% | 0.56 | -0.04% | take_profit=14;time_stop=2;stop_loss=1 |
| RIF | RIF Regime Monitor | 61 | 44 | 72.13% | 44 | +20.29% | 2.42 | +0.46% | take_profit=29;time_stop=15 |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-12.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-12.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
