# Paper Execution Journal

Generated: 2026-05-11T17:39:12.490363+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| DYDX | DYDX Pullback SHORT x2 Protected | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 10 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 7.3 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| RIF | RIF Regime Monitor | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/correct_24h_core_spot_journal_2026-05-11.csv`
- Summary CSV: `data/correct_24h_core_spot_summary_2026-05-11.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
