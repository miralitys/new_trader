# Cashflow + ALICE / 1000SATS Portfolio Test

Generated UTC: `2026-05-09T01:23:16.742137+00:00`.

Проверка: добавляют ли новые rescue-кандидаты `ALICE SHORT` и `1000SATS SHORT` пользу к текущим cashflow-портфелям.

| Portfolio | Scenario | Cash Hits | Positive Months | Net | Max DD | Max Month DD | PF | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Cashflow 1 old - GALA20/SPELL80 | base | 36/36 | 36/36 | $2487.41 | +35.31% | +29.31% | 1.52 | 1951 |
| Cashflow 1 old - GALA20/SPELL80 | stress_0.03_fee_0.005_slip | 35/36 | 35/36 | $2484.88 | +45.03% | +39.80% | 1.39 | 3191 |
| Cashflow 1 old - GALA20/SPELL80 | stress_0.04_fee_0.02_slip | 0/36 | 7/36 | $-999.87 | +99.99% | +63.47% | 0.62 | 12483 |
| Cashflow 1 + ALICE/1000SATS | base | 9/36 | 22/36 | $493.57 | +97.12% | +52.71% | 1.04 | 18884 |
| Cashflow 1 + ALICE/1000SATS | stress_0.03_fee_0.005_slip | 2/36 | 12/36 | $101.79 | +99.89% | +55.59% | 1.02 | 25561 |
| Cashflow 1 + ALICE/1000SATS | stress_0.04_fee_0.02_slip | 0/36 | 8/36 | $-997.63 | +100.00% | +53.44% | 0.62 | 25206 |
| Cashflow 1 + small ALICE/1000SATS | base | 36/36 | 36/36 | $2369.37 | +29.60% | +23.83% | 1.42 | 4120 |
| Cashflow 1 + small ALICE/1000SATS | stress_0.03_fee_0.005_slip | 0/36 | 14/36 | $-850.34 | +99.80% | +58.04% | 0.79 | 27816 |
| Cashflow 1 + small ALICE/1000SATS | stress_0.04_fee_0.02_slip | 0/36 | 8/36 | $-999.53 | +99.99% | +50.53% | 0.61 | 25900 |
| Cashflow 2 old - CHZ10/SHIB10/SPELL80 | base | 36/36 | 36/36 | $2491.36 | +42.20% | +37.10% | 1.41 | 781 |
| Cashflow 2 old - CHZ10/SHIB10/SPELL80 | stress_0.03_fee_0.005_slip | 0/36 | 14/36 | $-999.51 | +99.99% | +76.59% | 0.68 | 4099 |
| Cashflow 2 old - CHZ10/SHIB10/SPELL80 | stress_0.04_fee_0.02_slip | 0/36 | 10/36 | $-999.99 | +100.00% | +75.87% | 0.60 | 3945 |
| Cashflow 2 + ALICE/1000SATS | base | 11/36 | 22/36 | $594.55 | +99.62% | +69.78% | 1.06 | 13094 |
| Cashflow 2 + ALICE/1000SATS | stress_0.03_fee_0.005_slip | 1/36 | 12/36 | $61.07 | +99.99% | +67.72% | 1.01 | 18669 |
| Cashflow 2 + ALICE/1000SATS | stress_0.04_fee_0.02_slip | 0/36 | 9/36 | $-999.73 | +100.00% | +73.07% | 0.61 | 18317 |
| ALICE/1000SATS only | base | 8/36 | 18/36 | $422.45 | +90.70% | +39.73% | 1.03 | 10813 |
| ALICE/1000SATS only | stress_0.03_fee_0.005_slip | 4/36 | 13/36 | $212.71 | +98.94% | +39.87% | 1.04 | 12838 |
| ALICE/1000SATS only | stress_0.04_fee_0.02_slip | 0/36 | 9/36 | $-643.20 | +99.96% | +38.24% | 0.82 | 15039 |

## Вывод

Если новая версия дает меньше cash hits или выше просадку, ALICE/1000SATS не добавляем в основной cashflow, даже если отдельно они выглядят красиво.