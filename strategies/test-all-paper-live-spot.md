# Paper Execution Journal

Generated: 2026-05-13T16:05:31.898284+00:00
Window: last 1 days

| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ANKR | ANKR LONG Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| DYDX | DYDX Pullback SHORT x2 Protected | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 10 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| GALA | Минутка 11.2 | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| RIF | RIF Regime Monitor | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |
| SPELL | SPELL SHORT Best | 0 | 0 | 0.00% | 0 | +0.00% | 0.00 | +0.00% |  |

## Files

- Journal CSV: `data/paper_live/test_all_spot_journal.csv`
- Summary CSV: `data/paper_live/test_all_spot_summary.csv`

## How To Use

- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.
- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.
- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.
- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.
