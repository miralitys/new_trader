# Selected 4 Portfolio Final Validation

Generated UTC: `2026-05-09T12:42:32.245436+00:00`.

Portfolios:

- `selected4_income_A50_D20_R10_T20`: ALICE 50%, DYDX 20%, REZ 10%, TAO 20%.
- `selected4_defensive_A30_D20_R20_T30`: ALICE 30%, DYDX 20%, REZ 20%, TAO 30%.

## Window Results

| Portfolio | Scenario | 30d | 90d | 365d | 730d | DD365 | DD730 |
|---|---|---:|---:|---:|---:|---:|---:|
| `selected4_defensive_A30_D20_R20_T30` | `base_maker` | +1.59% | +138.94% | +777.42% | +1172.06% | 5.38% | 7.42% |
| `selected4_defensive_A30_D20_R20_T30` | `harsh` | +0.10% | +27.54% | +8.62% | -14.65% | 21.44% | 34.77% |
| `selected4_defensive_A30_D20_R20_T30` | `stress` | +0.83% | +88.31% | +180.20% | +164.16% | 7.40% | 14.51% |
| `selected4_defensive_A30_D20_R20_T30` | `taker_like` | -0.13% | +22.20% | -5.72% | -26.41% | 24.66% | 37.81% |
| `selected4_income_A50_D20_R10_T20` | `base_maker` | +2.02% | +225.83% | +1016.77% | +1482.74% | 5.59% | 10.95% |
| `selected4_income_A50_D20_R10_T20` | `harsh` | +0.32% | +46.79% | +8.70% | -23.09% | 30.46% | 48.53% |
| `selected4_income_A50_D20_R10_T20` | `stress` | +1.13% | +145.28% | +247.46% | +219.00% | 9.93% | 20.60% |
| `selected4_income_A50_D20_R10_T20` | `taker_like` | +0.04% | +38.80% | -9.97% | -37.80% | 34.53% | 52.26% |

## Monthly Check

| Portfolio | Scenario | Months + | Months >= 4% | Worst | Best | Avg |
|---|---|---:|---:|---:|---:|---:|
| `selected4_defensive_A30_D20_R20_T30` | `base_maker` | 22/26 | 8/26 | -2.76% | +57.60% | +8.91% |
| `selected4_defensive_A30_D20_R20_T30` | `harsh` | 9/26 | 4/26 | -7.43% | +15.62% | -0.41% |
| `selected4_defensive_A30_D20_R20_T30` | `stress` | 15/26 | 5/26 | -3.60% | +44.55% | +4.06% |
| `selected4_defensive_A30_D20_R20_T30` | `taker_like` | 6/26 | 4/26 | -8.36% | +13.49% | -1.21% |
| `selected4_income_A50_D20_R10_T20` | `base_maker` | 22/26 | 10/26 | -3.23% | +92.32% | +11.91% |
| `selected4_income_A50_D20_R10_T20` | `harsh` | 8/26 | 4/26 | -10.58% | +24.99% | -0.66% |
| `selected4_income_A50_D20_R10_T20` | `stress` | 18/26 | 6/26 | -5.46% | +72.01% | +5.58% |
| `selected4_income_A50_D20_R10_T20` | `taker_like` | 7/26 | 3/26 | -11.81% | +21.84% | -1.72% |
