# RIF/MOVR 5m and 1h Adaptation Summary

Generated: 2026-05-08

Source: Binance Futures archive, ending `2026-05-03`.

Execution: maker limit offset `0.05%`, maker fee `0.02%`, slippage `0`.

## Best Practical Adaptations

| Coin | TF | Direction | Status | Params | 1d | 7d | 30d | 60d | 90d | 180d | 365d | DD365 | PF365 |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RIF | 5m | LONG | good candidate | th40 wide, TP 1.00%, SL 6.00%, T180, weekly kill 2% | +0.63% | +11.65% | +12.24% | +23.62% | +38.81% | +66.86% | +56.03% | 12.05% | 1.26 |
| MOVR | 1h | LONG | cautious candidate | th60 base, TP 5.00%, SL 8.00%, T1440, weekly kill 2% | +0.80% | +0.80% | +5.80% | +3.51% | +3.51% | +9.21% | +9.69% | 6.39% | 1.51 |

## Not Recommended As Direct Adaptations

| Coin | TF | Reason |
|---|---|---|
| RIF | 1h LONG | Too little edge. Best long version is only about +4.69% on 365d. |
| MOVR | 5m LONG | 365d remains negative in the best long variants. |
| MOVR | 5m SHORT | Large 365d return appears, but 7d/30d/60d are negative and DD is too high. |
| MOVR | 1h SHORT | 365d can look strong, but 1d/7d and 180d are weak; not stable enough. |

## Side Findings

- RIF 5m can be adapted, but it needs a lower threshold and wider stop than the 1m version.
- RIF 5m max-return candidate reached +61.59% on 365d, but DD was 24.66%; the cleaner candidate is +56.03% with DD 12.05%.
- MOVR 1h long is modest but clean: low drawdown and PF 1.51, but only 19 trades on 365d, so cashflow may be weak.
- 1h strategies are naturally slower; they should not be judged as daily cashflow strategies yet.

## Next Tests

1. Run stress with fee/slippage and stricter maker fill.
2. Check fresh spot/data-api 24h/7d for these adapted variants.
3. Compare against original 1m RIF/MOVR before promoting either strategy to monitor.

## Files

- Long search: `strategies/rif-interval-adaptation-search-long-2026-05-08.md`
- Short search: `strategies/rif-interval-adaptation-search-short-2026-05-08.md`
- Long best CSV: `data/rif_interval_adaptation_best_long_2026-05-08.csv`
- Short best CSV: `data/rif_interval_adaptation_best_short_2026-05-08.csv`
