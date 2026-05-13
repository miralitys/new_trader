# Paper Execution Journal

Generated: 2026-05-13T15:01:43.636692+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 2 | 2 | 100.00% | 2 | -1.52% | 0.39 | -0.76% | take_profit=1;time_stop=1 |
| GALA | Минутка 10 | 14 | 13 | 92.86% | 13 | +0.23% | 2.04 | +0.02% | take_profit=12;time_stop=1 |
| GALA | Минутка 11.2 | 33 | 28 | 84.85% | 16 | -0.45% | 0.66 | -0.03% | take_profit=15;stop_loss=1 |
| GALA | Минутка 7.3 | 19 | 15 | 78.95% | 15 | -0.55% | 0.58 | -0.04% | take_profit=13;stop_loss=1;time_stop=1 |
| RIF | RIF Regime Monitor | 50 | 36 | 72.00% | 36 | +20.41% | 3.04 | +0.57% | take_profit=26;time_stop=10 |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_execution_journal_2026-05-13.csv`
- Summary CSV: `data/paper_execution_summary_2026-05-13.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
