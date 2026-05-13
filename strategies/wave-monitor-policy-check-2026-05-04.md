# Wave Monitor Policy Check

Проверка сравнивает несколько правил управления wave-включениями.

- `all_events`: брать каждое hot-событие.
- `pause_14d_after_loss`: если включение закрылось в минус, не брать новые события по этой монете 14 дней.
- `pause_30d_after_loss_or_dd15`: пауза 30 дней после минуса или event DD больше 15%.
- `pause_30d_after_loss_or_dd10`: более жесткая версия с DD больше 10%.

## Main Table

| Symbol | Scenario | Forward | Policy | Taken/Skipped | Compounded | Avg Event | Win | Seq DD | Worst Event | Event DD Avg/Worst |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `IRYSUSDT` | strict_maker | 14 | pause_14d_after_loss | 9/1 | +199.08% | +14.87% | 77.78% | 14.18% | -11.44% | 11.72% / 17.91% |
| `B2USDT` | strict_maker | 14 | pause_14d_after_loss | 15/4 | +115.45% | +5.90% | 66.67% | 14.65% | -13.89% | 9.69% / 21.21% |
| `GUAUSDT` | strict_maker | 14 | pause_14d_after_loss | 7/0 | +96.11% | +10.23% | 100.00% | 0.00% | +3.84% | 9.01% / 14.94% |
| `RAVEUSDT` | strict_maker | 14 | pause_14d_after_loss | 5/1 | +58.32% | +10.42% | 60.00% | 6.43% | -6.43% | 10.69% / 20.92% |
| `MEGAUSDT` | strict_maker | 14 | pause_14d_after_loss | 1/0 | +18.32% | +18.32% | 100.00% | 0.00% | +18.32% | 8.68% / 8.68% |
| `RIFUSDT` | strict_maker | 14 | pause_14d_after_loss | 21/8 | -42.01% | -2.21% | 42.86% | 55.07% | -17.89% | 10.55% / 21.15% |
| `IRYSUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 7/3 | +189.29% | +18.36% | 85.71% | 3.10% | -3.10% | 11.02% / 15.21% |
| `IRYSUSDT` | strict_maker | 14 | all_events | 10/0 | +182.35% | +12.82% | 70.00% | 18.99% | -11.44% | 12.06% / 17.91% |
| `B2USDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 11/8 | +104.28% | +7.07% | 81.82% | 11.85% | -11.85% | 7.60% / 19.09% |
| `B2USDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 11/8 | +104.28% | +7.07% | 81.82% | 11.85% | -11.85% | 7.60% / 19.09% |
| `B2USDT` | strict_maker | 14 | all_events | 19/0 | +96.64% | +4.24% | 63.16% | 24.06% | -13.89% | 10.94% / 21.21% |
| `GUAUSDT` | strict_maker | 14 | all_events | 7/0 | +96.11% | +10.23% | 100.00% | 0.00% | +3.84% | 9.01% / 14.94% |
| `GUAUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 7/0 | +96.11% | +10.23% | 100.00% | 0.00% | +3.84% | 9.01% / 14.94% |
| `RAVEUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 4/2 | +69.20% | +14.64% | 75.00% | 0.00% | +0.00% | 8.13% / 16.00% |
| `GUAUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 5/2 | +61.18% | +10.13% | 100.00% | 0.00% | +4.41% | 6.64% / 12.57% |
| `RAVEUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 3/3 | +54.01% | +16.23% | 66.67% | 0.00% | +0.00% | 5.51% / 10.77% |
| `RAVEUSDT` | strict_maker | 14 | all_events | 6/0 | +45.74% | +7.36% | 50.00% | 13.86% | -7.94% | 11.63% / 20.92% |
| `IRYSUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 3/7 | +23.50% | +8.25% | 66.67% | 11.44% | -11.44% | 14.02% / 17.91% |
| `MEGAUSDT` | strict_maker | 14 | all_events | 1/0 | +18.32% | +18.32% | 100.00% | 0.00% | +18.32% | 8.68% / 8.68% |
| `MEGAUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 1/0 | +18.32% | +18.32% | 100.00% | 0.00% | +18.32% | 8.68% / 8.68% |
| `MEGAUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 1/0 | +18.32% | +18.32% | 100.00% | 0.00% | +18.32% | 8.68% / 8.68% |
| `RIFUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd15 | 17/12 | -23.95% | -1.24% | 47.06% | 39.15% | -17.89% | 9.90% / 20.99% |
| `RIFUSDT` | strict_maker | 14 | pause_30d_after_loss_or_dd10 | 16/13 | -33.82% | -2.09% | 50.00% | 47.68% | -17.89% | 9.92% / 20.99% |
| `RIFUSDT` | strict_maker | 14 | all_events | 29/0 | -74.85% | -4.32% | 31.03% | 79.04% | -17.89% | 11.28% / 21.15% |
| `B2USDT` | strict_maker | 30 | pause_14d_after_loss | 14/3 | +322.77% | +12.11% | 71.43% | 20.61% | -16.06% | 16.68% / 30.66% |
| `GUAUSDT` | strict_maker | 30 | pause_14d_after_loss | 5/0 | +231.14% | +27.23% | 100.00% | 0.00% | +19.55% | 9.36% / 14.94% |
| `IRYSUSDT` | strict_maker | 30 | pause_14d_after_loss | 7/1 | +144.87% | +16.14% | 71.43% | 27.14% | -17.29% | 15.18% / 22.24% |
| `B2USDT` | strict_maker | 7 | pause_14d_after_loss | 15/4 | +64.76% | +3.63% | 60.00% | 7.32% | -7.32% | 6.52% / 14.17% |
| `IRYSUSDT` | strict_maker | 7 | pause_14d_after_loss | 9/2 | +47.06% | +5.26% | 55.56% | 24.74% | -12.08% | 9.40% / 15.21% |
| `GUAUSDT` | strict_maker | 7 | pause_14d_after_loss | 7/1 | +26.06% | +3.48% | 71.43% | 1.04% | -1.04% | 6.34% / 14.94% |
| `RAVEUSDT` | strict_maker | 7 | pause_14d_after_loss | 5/2 | +18.99% | +4.40% | 20.00% | 9.96% | -7.67% | 6.51% / 16.00% |
| `MEGAUSDT` | strict_maker | 7 | pause_14d_after_loss | 1/1 | -0.66% | -0.66% | 0.00% | 0.66% | -0.66% | 4.04% / 4.04% |
| `RAVEUSDT` | strict_maker | 30 | pause_14d_after_loss | 3/1 | -7.70% | -2.25% | 33.33% | 15.20% | -12.46% | 22.51% / 26.16% |
| `RIFUSDT` | strict_maker | 7 | pause_14d_after_loss | 24/6 | -26.65% | -1.09% | 54.17% | 32.59% | -13.53% | 6.72% / 15.70% |
| `RIFUSDT` | strict_maker | 30 | pause_14d_after_loss | 20/8 | -66.64% | -4.54% | 40.00% | 80.43% | -27.18% | 15.04% / 28.05% |
| `GUAUSDT` | strict_maker | 30 | all_events | 5/0 | +231.14% | +27.23% | 100.00% | 0.00% | +19.55% | 9.36% / 14.94% |
| `GUAUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd15 | 5/0 | +231.14% | +27.23% | 100.00% | 0.00% | +19.55% | 9.36% / 14.94% |
| `IRYSUSDT` | strict_maker | 30 | all_events | 8/0 | +207.09% | +17.30% | 75.00% | 27.14% | -17.29% | 15.18% / 22.24% |
| `B2USDT` | strict_maker | 30 | pause_30d_after_loss_or_dd15 | 10/7 | +204.64% | +13.11% | 70.00% | 12.52% | -12.52% | 14.71% / 29.21% |
| `B2USDT` | strict_maker | 30 | all_events | 17/0 | +178.54% | +7.71% | 58.82% | 43.94% | -19.27% | 18.51% / 32.84% |
| `B2USDT` | strict_maker | 30 | pause_30d_after_loss_or_dd10 | 9/8 | +169.87% | +13.13% | 66.67% | 12.52% | -12.52% | 14.43% / 29.21% |
| `GUAUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd10 | 4/1 | +147.93% | +25.65% | 100.00% | 0.00% | +19.55% | 7.97% / 14.94% |
| `IRYSUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd15 | 5/3 | +109.01% | +18.38% | 80.00% | 17.29% | -17.29% | 15.34% / 22.24% |
| `IRYSUSDT` | strict_maker | 7 | all_events | 11/0 | +63.25% | +5.30% | 63.64% | 24.18% | -12.08% | 8.72% / 15.21% |
| `B2USDT` | strict_maker | 7 | all_events | 19/0 | +57.60% | +2.73% | 63.16% | 17.99% | -16.07% | 7.33% / 18.44% |
| `RAVEUSDT` | strict_maker | 7 | all_events | 7/0 | +44.11% | +6.12% | 42.86% | 7.67% | -7.67% | 7.07% / 16.00% |
| `GUAUSDT` | strict_maker | 7 | all_events | 8/0 | +41.31% | +4.56% | 75.00% | 1.04% | -1.04% | 6.19% / 14.94% |
| `B2USDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 9/10 | +39.82% | +3.92% | 77.78% | 2.28% | -2.28% | 7.31% / 16.01% |
| `IRYSUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd10 | 3/5 | +37.93% | +12.94% | 66.67% | 11.91% | -11.91% | 14.69% / 19.14% |
| `B2USDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 11/8 | +30.44% | +2.60% | 72.73% | 9.44% | -7.32% | 7.45% / 16.01% |
| `RAVEUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 4/3 | +28.87% | +7.42% | 25.00% | 2.48% | -2.48% | 4.13% / 10.77% |
| `RAVEUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 4/3 | +28.87% | +7.42% | 25.00% | 2.48% | -2.48% | 4.13% / 10.77% |
| `MEGAUSDT` | strict_maker | 7 | all_events | 2/0 | +18.32% | +9.22% | 50.00% | 0.66% | -0.66% | 5.44% / 6.85% |
| `RAVEUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd15 | 1/3 | +8.84% | +8.84% | 100.00% | 0.00% | +8.84% | 20.92% / 20.92% |
| `RAVEUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd10 | 1/3 | +8.84% | +8.84% | 100.00% | 0.00% | +8.84% | 20.92% / 20.92% |
| `GUAUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 5/3 | +8.41% | +1.65% | 60.00% | 1.04% | -1.04% | 6.36% / 14.94% |
| `GUAUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 4/4 | +6.43% | +1.60% | 50.00% | 1.04% | -1.04% | 5.51% / 14.94% |
| `MEGAUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 1/1 | -0.66% | -0.66% | 0.00% | 0.66% | -0.66% | 4.04% / 4.04% |
| `MEGAUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 1/1 | -0.66% | -0.66% | 0.00% | 0.66% | -0.66% | 4.04% / 4.04% |
| `RIFUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 20/10 | -0.98% | +0.12% | 60.00% | 14.87% | -13.53% | 5.97% / 15.70% |
| `IRYSUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 5/6 | -1.31% | +0.03% | 40.00% | 17.39% | -8.65% | 9.55% / 15.21% |
| `IRYSUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd10 | 5/6 | -1.31% | +0.03% | 40.00% | 17.39% | -8.65% | 9.55% / 15.21% |
| `RIFUSDT` | strict_maker | 7 | pause_30d_after_loss_or_dd15 | 20/10 | -7.35% | -0.20% | 60.00% | 16.70% | -13.53% | 6.55% / 15.70% |
| `RAVEUSDT` | strict_maker | 30 | all_events | 4/0 | -21.39% | -5.39% | 25.00% | 27.77% | -14.83% | 23.42% / 26.16% |
| `RIFUSDT` | strict_maker | 7 | all_events | 30/0 | -45.59% | -1.80% | 46.67% | 50.92% | -13.53% | 7.15% / 15.70% |
| `RIFUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd15 | 14/14 | -55.65% | -4.86% | 35.71% | 67.12% | -27.18% | 14.25% / 28.05% |
| `RIFUSDT` | strict_maker | 30 | pause_30d_after_loss_or_dd10 | 14/14 | -55.65% | -4.86% | 35.71% | 67.12% | -27.18% | 14.25% / 28.05% |
| `RIFUSDT` | strict_maker | 30 | all_events | 28/0 | -88.44% | -6.66% | 32.14% | 92.94% | -27.18% | 15.83% / 28.05% |
