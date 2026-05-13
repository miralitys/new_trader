# Regime Monitor Batch Fast

Быстрый первичный поиск монет, похожих на RIF: always-on может быть плохим, но rolling 30/60d health включает только рабочие дни.

Важно: это быстрый screen по rolling trade-health. Кандидатов надо потом добивать точным per-day health script.

| Symbol | Direction | Always 730 | Always DD | Gated 730 | Gated DD | Gated PF | Active Days | Weekly Kill 730 | Weekly DD | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `RIFUSDT` | long | -41.82% | 73.90% | +42.76% | 15.48% | 1.33 | 144 | +34.17% | 8.29% | regime_candidate_defensive |
| `REZUSDT` | long | -89.00% | 92.52% | +31.81% | 18.58% | 1.14 | 72 | +23.58% | 5.94% | regime_candidate_defensive |
| `ACHUSDT` | long | -90.19% | 92.58% | +7.82% | 13.96% | 1.16 | 48 | +12.44% | 5.57% | regime_candidate_defensive |
| `ZENUSDT` | long | -75.00% | 86.94% | +2.62% | 18.72% | 1.02 | 72 | +2.87% | 10.40% | reject |
| `BICOUSDT` | short | -90.74% | 92.96% | -6.08% | 9.20% | 0.51 | 8 | -4.28% | 6.09% | reject |
| `CHRUSDT` | long | -97.39% | 97.81% | -7.16% | 12.25% | 0.73 | 9 | +1.09% | 4.04% | reject |
| `APEUSDT` | long | -74.97% | 81.03% | -9.89% | 12.89% | 0.87 | 85 | -3.60% | 12.14% | reject |
| `AXLUSDT` | long | -87.75% | 89.87% | -17.09% | 21.42% | 0.45 | 14 | -12.32% | 12.32% | reject |
| `RLCUSDT` | long | -79.39% | 88.72% | -24.29% | 39.08% | 0.81 | 91 | -0.64% | 13.86% | reject |
| `EDUUSDT` | long | -37.70% | 52.83% | -33.27% | 36.33% | 0.68 | 89 | -20.85% | 24.90% | reject |
