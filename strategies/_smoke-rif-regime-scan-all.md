# RIF Regime Scan All Binance

Generated: 2026-05-08T01:31:48.387511+00:00

Проверка применяет фиксированную механику `RIF Regime Monitor` ко всем активным Binance USD-M USDT futures из inventory.

Фиксированная стратегия: `LONG th50 wide TP 1.2% SL 4% time-stop 90m`, strict maker `0.05%`, fee `0.02%`, slippage `0`.
Gate: торговать только если прошлые 30d и 60d проходят health-check. Defensive версия добавляет weekly kill `2%`.

## Counts

| Decision | Count |
|---|---:|
| regime_candidate_defensive | 2 |
| reject | 3 |

## Top Candidates

| Symbol | Decision | Active Days 730 | Always 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `RIFUSDT` | regime_candidate_defensive | 144 | -41.82% | +42.76% | 15.48% | 1.33 | +34.17% | 8.29% | 1.56 |
| `REZUSDT` | regime_candidate_defensive | 72 | -89.00% | +31.81% | 18.58% | 1.14 | +23.58% | 5.94% | 1.44 |

## Strong Rejected By Risk Filter

| Symbol | Active Days 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ACHUSDT` | 60 | +8.15% | 20.64% | 1.06 | +4.98% | 8.40% | 1.11 |
| `CHZUSDT` | 208 | -6.56% | 19.55% | 0.97 | +4.92% | 18.75% | 1.05 |
| `GALAUSDT` | 67 | -30.64% | 37.77% | 0.82 | -8.43% | 12.55% | 0.82 |

## Files

- Summary CSV: `data/_smoke_rif_regime_scan_all.csv`
