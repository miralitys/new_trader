# Paper Execution Journal

Generated: 2026-05-10T15:03:15.278580+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 2 | 2 | 100.00% | 2 | -1.52% | 0.39 | -0.76% | take_profit=1;time_stop=1 |
| GALA | Минутка 10 | 18 | 17 | 94.44% | 17 | +0.13% | 1.31 | +0.01% | take_profit=14;time_stop=3 |
| GALA | Минутка 11.2 | 44 | 39 | 88.64% | 23 | -0.31% | 0.79 | -0.01% | take_profit=20;time_stop=2;stop_loss=1 |
| GALA | Минутка 7.3 | 26 | 22 | 84.62% | 22 | -0.89% | 0.54 | -0.04% | take_profit=18;time_stop=3;stop_loss=1 |
| RIF | RIF Regime Monitor | 86 | 62 | 72.09% | 62 | +28.32% | 2.60 | +0.46% | take_profit=38;time_stop=24 |
| SPELL | SPELL SHORT Best | 1 | 1 | 100.00% | 1 | +0.96% | inf | +0.96% | take_profit=1 |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-10.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-10.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
