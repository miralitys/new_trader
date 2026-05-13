# RIF Regime Scan All Binance

Generated: 2026-05-08T04:30:38.725773+00:00

Проверка применяет фиксированную механику `RIF Regime Monitor` ко всем активным Binance USD-M USDT futures из inventory.

Фиксированная стратегия: `LONG th50 wide TP 1.2% SL 4% time-stop 90m`, strict maker `0.05%`, fee `0.02%`, slippage `0`.
Gate: торговать только если прошлые 30d и 60d проходят health-check. Defensive версия добавляет weekly kill `2%`.

## Counts

| Decision | Count |
|---|---:|
| insufficient_history | 3 |
| regime_candidate | 6 |
| regime_candidate_defensive | 21 |
| reject | 243 |

## Top Candidates

| Symbol | Decision | Active Days 730 | Always 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `API3USDT` | regime_candidate_defensive | 102 | -81.51% | +14.30% | 26.90% | 1.06 | +44.19% | 11.60% | 1.57 |
| `GASUSDT` | regime_candidate_defensive | 180 | -48.87% | +4.72% | 25.51% | 1.02 | +36.75% | 10.88% | 1.34 |
| `RIFUSDT` | regime_candidate_defensive | 144 | -41.82% | +42.76% | 15.48% | 1.33 | +34.17% | 8.29% | 1.56 |
| `ENAUSDT` | regime_candidate_defensive | 105 | -77.98% | +39.05% | 23.17% | 1.13 | +33.11% | 7.92% | 1.48 |
| `MOVRUSDT` | regime_candidate_defensive | 156 | -65.16% | +33.59% | 24.96% | 1.11 | +31.18% | 13.69% | 1.31 |
| `REZUSDT` | regime_candidate_defensive | 72 | -89.00% | +31.81% | 18.58% | 1.14 | +23.58% | 5.94% | 1.44 |
| `MANAUSDT` | regime_candidate_defensive | 167 | -53.17% | +10.85% | 20.25% | 1.04 | +21.70% | 11.39% | 1.22 |
| `UMAUSDT` | regime_candidate_defensive | 39 | -88.49% | +10.07% | 13.42% | 1.21 | +20.45% | 5.22% | 1.74 |
| `SANDUSDT` | regime_candidate_defensive | 109 | -77.19% | -12.54% | 20.46% | 0.90 | +15.84% | 10.07% | 1.27 |
| `COMPUSDT` | regime_candidate_defensive | 72 | -57.56% | -0.26% | 18.96% | 1.00 | +15.52% | 6.38% | 1.41 |
| `VETUSDT` | regime_candidate_defensive | 64 | -82.10% | -7.40% | 18.61% | 0.93 | +13.54% | 8.47% | 1.28 |
| `TIAUSDT` | regime_candidate_defensive | 36 | -94.10% | -7.26% | 13.91% | 0.88 | +13.29% | 5.32% | 1.60 |
| `KAVAUSDT` | regime_candidate_defensive | 120 | -34.45% | +18.75% | 16.59% | 1.14 | +13.25% | 8.26% | 1.26 |
| `ADAUSDT` | regime_candidate_defensive | 83 | -58.99% | -14.68% | 22.77% | 0.87 | +13.00% | 8.67% | 1.21 |
| `ANKRUSDT` | regime_candidate_defensive | 108 | -47.75% | +40.47% | 17.67% | 1.24 | +12.94% | 9.73% | 1.27 |
| `THETAUSDT` | regime_candidate_defensive | 72 | -77.75% | +11.36% | 12.16% | 1.08 | +10.92% | 10.76% | 1.30 |
| `STRKUSDT` | regime_candidate_defensive | 36 | -86.17% | -20.00% | 28.69% | 0.80 | +9.38% | 6.17% | 1.42 |
| `BNXUSDT` | regime_candidate_defensive | 52 | -43.04% | +10.85% | 16.87% | 1.08 | +8.59% | 12.35% | 1.22 |
| `ONGUSDT` | regime_candidate_defensive | 52 | -68.66% | -2.14% | 12.46% | 0.96 | +8.10% | 5.36% | 1.27 |
| `ETCUSDT` | regime_candidate_defensive | 44 | -50.25% | +8.64% | 3.50% | 1.50 | +7.39% | 3.50% | 1.43 |
| `MASKUSDT` | regime_candidate_defensive | 27 | -87.65% | -23.69% | 32.51% | 0.69 | +6.71% | 7.64% | 1.24 |
| `AGLDUSDT` | regime_candidate | 101 | -84.15% | +16.81% | 18.77% | 1.10 | +9.43% | 10.39% | 1.18 |
| `CVCUSDT` | regime_candidate | 59 | -26.23% | +10.35% | 14.19% | 1.23 | +9.06% | 8.50% | 1.60 |
| `1000XECUSDT` | regime_candidate | 46 | -75.33% | +7.43% | 4.37% | 1.44 | +8.12% | 2.87% | 1.60 |
| `SFPUSDT` | regime_candidate | 68 | -18.11% | +18.75% | 10.23% | 1.37 | +0.22% | 10.89% | 1.01 |
| `AVAXUSDT` | regime_candidate | 111 | -73.19% | +18.59% | 16.50% | 1.12 | -3.31% | 10.51% | 0.94 |
| `ARKUSDT` | regime_candidate | 141 | +6.75% | +30.06% | 14.00% | 1.17 | -13.37% | 19.44% | 0.79 |

## Strong Rejected By Risk Filter

| Symbol | Active Days 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `MINAUSDT` | 119 | +17.77% | 13.23% | 1.10 | +0.41% | 11.54% | 1.01 |
| `ONDOUSDT` | 96 | +15.98% | 21.87% | 1.05 | +5.51% | 14.69% | 1.07 |
| `CKBUSDT` | 74 | +12.23% | 16.60% | 1.07 | -1.53% | 15.01% | 0.96 |
| `PEOPLEUSDT` | 123 | +9.50% | 19.61% | 1.04 | +1.59% | 11.42% | 1.02 |
| `OMUSDT` | 73 | +9.13% | 11.03% | 1.07 | -4.85% | 14.45% | 0.88 |
| `ACHUSDT` | 60 | +8.15% | 20.64% | 1.06 | +4.98% | 8.40% | 1.11 |
| `WAXPUSDT` | 108 | +7.07% | 23.85% | 1.06 | -2.65% | 14.02% | 0.93 |
| `XTZUSDT` | 90 | +4.77% | 19.07% | 1.03 | +9.46% | 8.22% | 1.18 |
| `XLMUSDT` | 35 | +3.87% | 9.35% | 1.09 | -6.31% | 11.56% | 0.66 |
| `HBARUSDT` | 135 | +3.55% | 26.98% | 1.01 | -4.53% | 13.88% | 0.95 |
| `DASHUSDT` | 47 | +2.64% | 15.62% | 1.03 | +1.31% | 8.11% | 1.05 |
| `LOOMUSDT` | 25 | +2.62% | 0.65% | 4.12 | +2.62% | 0.65% | 4.12 |
| `HFTUSDT` | 56 | +2.61% | 13.50% | 1.03 | +0.87% | 14.24% | 1.02 |
| `SLPUSDT` | 56 | +2.22% | 11.58% | 1.03 | -1.61% | 8.41% | 0.95 |
| `QTUMUSDT` | 190 | +1.77% | 13.36% | 1.01 | +5.30% | 9.44% | 1.07 |
| `ORDIUSDT` | 4 | +1.47% | 2.75% | 1.13 | -0.61% | 2.44% | 0.79 |
| `QNTUSDT` | 97 | +1.29% | 14.83% | 1.01 | +0.06% | 9.63% | 1.00 |
| `PORTALUSDT` | 31 | +1.08% | 18.33% | 1.01 | +0.68% | 7.65% | 1.03 |
| `PERPUSDT` | 5 | +0.93% | 1.60% | 1.57 | +0.93% | 1.60% | 1.57 |
| `ZECUSDT` | 79 | +0.72% | 19.63% | 1.00 | -1.60% | 13.97% | 0.97 |

## Files

- Summary CSV: `data/rif_regime_scan_all_binance_overnight_2026-05-08.csv`
