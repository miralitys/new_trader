# Paper Execution Journal

Generated: 2026-05-08T20:27:08.452346+00:00
Window: last 7 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 3 | 2 | 66.67% | 2 | -2.91% | 0.00 | -1.46% | time_stop=2 |
| GALA | Минутка 11.2 | 153 | 59 | 38.56% | 41 | -0.52% | 0.82 | -0.01% | take_profit=37;time_stop=4 |
| GALA | Минутка 7.3 | 91 | 34 | 37.36% | 34 | -0.28% | 0.87 | -0.01% | take_profit=31;time_stop=3 |
| RIF | RIF Regime Monitor | 95 | 29 | 30.53% | 29 | +12.69% | 2.09 | +0.44% | take_profit=21;time_stop=8 |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/post_only_market_limit_journal_7d_2026-05-08.csv`
- Summary CSV: `data/post_only_market_limit_summary_7d_2026-05-08.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
