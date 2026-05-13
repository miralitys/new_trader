# RIF-like Candidates Windows Check

Generated: 2026-05-08

Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker `0.05%`, fee `0.02%`, slippage `0`.

Источник: Binance Futures archive. Последняя доступная архивная дата в этом прогоне: `2026-05-03`.

## Main: health30_60

| Symbol | 1d | 7d | 30d | 60d | 90d | 180d | 365d | DD 365d | PF 365d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `RIFUSDT` | +3.88% | +15.29% | +25.76% | +36.12% | +37.67% | +30.15% | +48.19% | 15.48% | 1.37 |
| `ENAUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +28.11% | 14.69% | 1.13 |
| `MOVRUSDT` | -0.17% | +0.64% | +26.78% | +26.78% | +26.78% | +26.78% | +18.83% | 14.54% | 1.18 |
| `UMAUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +10.07% | 13.42% | 1.21 |
| `COMPUSDT` | +0.00% | +2.22% | +15.14% | +15.10% | +15.10% | +17.01% | +12.59% | 12.74% | 1.36 |
| `CVCUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +2.67% | +12.34% | 11.62% | 1.30 |
| `1000XECUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +7.30% | 4.37% | 1.54 |

## Defensive: health30_60_weekly_kill

| Symbol | 1d | 7d | 30d | 60d | 90d | 180d | 365d | DD 365d | PF 365d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `RIFUSDT` | +3.88% | +13.47% | +23.26% | +24.48% | +18.58% | +22.32% | +39.27% | 8.29% | 1.67 |
| `ENAUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +26.80% | 7.92% | 1.48 |
| `MOVRUSDT` | +0.16% | -2.01% | +20.08% | +20.08% | +20.08% | +20.08% | +21.43% | 7.61% | 1.61 |
| `UMAUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +20.45% | 5.22% | 1.74 |
| `COMPUSDT` | +0.00% | +2.22% | +10.53% | +10.50% | +10.50% | +12.33% | +18.86% | 4.04% | 1.97 |
| `CVCUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | -1.48% | +7.81% | 8.50% | 1.52 |
| `1000XECUSDT` | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | +10.51% | 2.87% | 2.00 |

## Raw always-on reference

| Symbol | 1d | 7d | 30d | 60d | 90d | 180d | 365d | DD 365d | PF 365d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `RIFUSDT` | +3.88% | +15.29% | +25.76% | +36.44% | +58.12% | +72.93% | +115.43% | 16.24% | 1.34 |
| `ENAUSDT` | +0.00% | -3.22% | +10.67% | +4.61% | -15.47% | -1.77% | +16.41% | 48.22% | 1.01 |
| `MOVRUSDT` | -0.17% | +0.64% | +28.25% | +35.65% | +27.35% | -11.45% | -27.98% | 59.29% | 0.93 |
| `UMAUSDT` | +0.00% | +1.29% | -0.03% | -8.79% | -27.30% | -36.42% | -40.15% | 53.45% | 0.90 |
| `COMPUSDT` | +0.00% | +2.22% | +13.22% | +25.88% | +32.55% | +10.74% | +10.43% | 39.28% | 1.04 |
| `CVCUSDT` | +0.00% | +0.00% | +0.74% | +2.79% | -5.30% | -29.42% | -26.23% | 45.60% | 0.91 |
| `1000XECUSDT` | +0.00% | +0.15% | -3.52% | -5.05% | -15.11% | -26.61% | -27.85% | 34.73% | 0.85 |

## Interpretation

- `RIFUSDT` is the cleanest candidate: positive on every checked window in `health30_60`.
- `COMPUSDT` is also strong on short and medium windows, and defensive mode improves the 365d risk profile.
- `MOVRUSDT` is powerful on 30-180d, but it is noisy on 1d/7d and raw always-on breaks over 365d.
- `ENAUSDT`, `UMAUSDT`, `CVCUSDT`, and `1000XECUSDT` are mostly regime/wait candidates: the filter keeps them off on recent short windows, while 365d remains positive.
- Raw always-on is clearly dangerous for most coins; the health filter is doing real work.

## Files

- Detail CSV: `data/rif_candidates_windows_detail_2026-05-08.csv`
- Summary CSV: `data/rif_candidates_windows_summary_2026-05-08.csv`
