# RIF Regime Scan All Binance

Generated: 2026-05-08T01:48:30.256376+00:00

Проверка применяет фиксированную механику `RIF Regime Monitor` ко всем активным Binance USD-M USDT futures из inventory.

Фиксированная стратегия: `LONG th50 wide TP 1.2% SL 4% time-stop 90m`, strict maker `0.05%`, fee `0.02%`, slippage `0`.
Gate: торговать только если прошлые 30d и 60d проходят health-check. Defensive версия добавляет weekly kill `2%`.

## Counts

| Decision | Count |
|---|---:|
| regime_candidate | 1 |
| reject | 9 |

## Top Candidates

| Symbol | Decision | Active Days 730 | Always 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `1000XECUSDT` | regime_candidate | 46 | -75.33% | +7.43% | 4.37% | 1.44 | +8.12% | 2.87% | 1.60 |

## Strong Rejected By Risk Filter

| Symbol | Active Days 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `1000SATSUSDT` | 0 | +0.00% | 0.00% | 0.00 | +0.00% | 0.00% | 0.00 |
| `1000RATSUSDT` | 3 | -0.24% | 8.60% | 0.99 | +0.50% | 2.24% | 1.17 |
| `1000LUNCUSDT` | 32 | -3.20% | 5.58% | 0.79 | -3.20% | 5.58% | 0.79 |
| `AGIXUSDT` | 14 | -6.03% | 12.40% | 0.86 | +1.33% | 6.61% | 1.09 |
| `1INCHUSDT` | 89 | -7.52% | 17.18% | 0.93 | -2.99% | 7.63% | 0.93 |
| `1000PEPEUSDT` | 21 | -13.63% | 14.83% | 0.69 | -2.59% | 7.48% | 0.89 |
| `1000FLOKIUSDT` | 50 | -19.42% | 30.22% | 0.84 | -7.95% | 19.37% | 0.83 |
| `1000SHIBUSDT` | 66 | -22.82% | 22.82% | 0.68 | -16.57% | 16.57% | 0.58 |
| `1000BONKUSDT` | 53 | -32.61% | 32.61% | 0.75 | -17.51% | 17.51% | 0.62 |

## Files

- Summary CSV: `data/rif_regime_scan_all_binance_2026-05-08.csv`
