# DYDX Pullback SHORT Aggressive Leverage Test

Generated UTC: `2026-05-09T02:01:12.657108+00:00`.

Base position: `65%` of equity. Leverage changes notional only; signal rules are unchanged.

## Stress Windows

| Lev | Notional | 1d | 7d | 30d | 60d | 90d | 180d | 365d | 730d | DD730 | PF730 | Worst trade |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| x1 | 65% | +0.00% | +0.00% | +8.97% | +33.05% | +155.79% | +296.15% | +291.04% | +359.57% | 21.43% | 1.27 | -1.96% |
| x2 | 130% | +0.00% | +0.00% | +18.52% | +75.92% | +538.39% | +1381.95% | +1305.49% | +1758.62% | 39.71% | 1.27 | -3.92% |
| x3 | 195% | +0.00% | +0.00% | +28.64% | +131.13% | +1453.80% | +5128.37% | +4534.11% | +6493.79% | 54.85% | 1.27 | -5.87% |
| x6 | 390% | +0.00% | +0.00% | +62.49% | +404.02% | +19063.39% | +159184.81% | +96790.61% | +129409.89% | 86.09% | 1.27 | -11.75% |
| x10 | 650% | +0.00% | +0.00% | +115.22% | +1192.84% | +369793.12% | +6071758.77% | +1445307.52% | +866517.17% | 99.06% | 1.27 | -19.58% |

## Monthly Stress Summary

| Lev | Positive months | Negative months | Worst month | Best month | Avg month |
|---:|---:|---:|---:|---:|---:|
| x1 | 17/24 | 7/24 | -7.66% | +67.86% | +7.58% |
| x2 | 17/24 | 7/24 | -15.13% | +176.28% | +17.66% |
| x3 | 17/24 | 7/24 | -22.36% | +345.65% | +31.33% |
| x6 | 17/24 | 7/24 | -42.31% | +1548.67% | +111.29% |
| x10 | 14/24 | 10/24 | -64.06% | +6774.20% | +417.26% |

## Human Conclusion

Leverage improves return only when the strategy has trades. The last 1d and 7d had zero trades, so leverage produced zero result there.

x2 and x3 are the practical stress-test zone. x6 and x10 produce very large historical returns, but single stop losses become large enough to damage the account quickly; they require hard kill-switches, margin buffer, funding checks, and paper execution before any live use.