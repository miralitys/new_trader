# Monthly Cashflow Target Ceiling

Generated: `2026-05-08T19:39:47.764200+00:00`

Цель: найти максимальную месячную цель, которую фиксированная стратегия выполняет во всех 36 месяцах.

Период: `2023-05` - `2026-04`.
Trade pool: `data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv`.

## Ceiling Summary

| Strategy | Scenario | Max Stable % / $ | Next Target | Cash Hits | MaxDD | PF | Worst Month | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GALA 20% / SPELL 80% | `base_fee002_slip0` | 5.73% / $57.30 | $57.40 (0/36 months) | 36/36 | +37.95% | 1.51 | $57.36 | 2856 |

## Human Read

- `GALA 20% / SPELL 80%`: исторический потолок в базе - примерно `5.73%` в месяц. Следующий шаг `$57.40` уже не проходит все 36 месяцев (0/36).

Важно: это потолок по истории. Его нельзя автоматически ставить в live. Чем ближе цель к потолку, тем меньше запас на исполнение, slippage, пропущенные fill и изменение режима рынка.

## Files

- Summary CSV: `data/_smoke_ceiling_summary.csv`
- Monthly CSV: `data/_smoke_ceiling_monthly.csv`
