# Operational Daily Monitor

Generated: 2026-05-09T02:12:14.733147+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +16.73% | 1.81 | 1.41% | +5.74% | n/a | n/a | return +16.73% > 0.00%; PF 1.81 >= 1.05; DD 1.41% <= 18.00%; trades 1010 >= 20 | stress passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +52.08% | 2.19 | 6.00% | +29.36% | +21.23% | 2.01 | 30d+60d health | stress passed | paper passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +7.61% | 2.09 | 3.34% | +4.07% | n/a | n/a | return +7.61% > 0.00%; PF 2.09 >= 1.05; DD 3.34% <= 15.00%; trades 39 >= 10 | stress passed |
| WATCH | DYDXUSDT | best_strategy | DYDX Pullback SHORT x2 Protected | +22.83% | 2.41 | 3.84% | +18.52% | n/a | n/a | return +22.83% > 0.00%; PF 2.41 >= 1.10; DD 3.84% <= 12.00%; trades 44 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +26.08% | 1.60 | 3.50% | +2.56% | -0.89% | 0.54 | return +26.08% > 0.00%; PF 1.60 >= 1.05; DD 3.50% <= 18.00%; trades 1187 >= 30 | stress passed | paper weak: paper return -0.89% <= 0.00%; paper PF 0.54 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +28.46% | 1.53 | 4.93% | -1.31% | -0.31% | 0.79 | return +28.46% > 0.00%; PF 1.53 >= 1.08; DD 4.93% <= 18.00%; trades 1248 >= 30 | stress failed: taker_like: return -1.31% <= 0; PF 0.97 < 1.00 | paper weak: paper return -0.31% <= 0.00%; paper PF 0.79 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.90% | 1.93 | 3.06% | +1.61% | n/a | n/a | return +3.78% > 0.00%; PF 1.69 >= 1.05; DD 3.06% <= 15.00%; trades 23 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +9.02% | 1.28 | 3.62% | +4.31% | n/a | n/a | return +9.02% > 0.00%; PF 1.28 >= 1.05; DD 3.62% <= 18.00%; trades 701 >= 20 | stress weak: strict_maker: return -10.51% <= 0; PF 0.59 < 1.00 |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +5.20% | 1.84 | 6.09% | +4.12% | +0.96% | inf | return +5.20% > 0.00%; PF 1.84 >= 1.08; DD 6.09% <= 16.00%; trades 16 >= 10 | stress passed | paper weak: paper accepted 1 < 5 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +10.99% | 1.37 | 7.13% | -0.75% | n/a | n/a | 30d+60d health | stress weak: taker_like: return -0.75% <= 0; PF 0.97 < 1.00 |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +16.49% | 1.47 | 7.02% | +15.10% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -1.68% | 0.53 | 2.53% | -2.04% | +0.00% | 0.00 | return -1.68% <= 0.00%; PF 0.53 < 1.08; trades 5 < 10 | paper weak: paper accepted 0 < 5; paper return +0.00% <= 0.00%; paper PF 0.00 < 1.00 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | n/a | n/a | trades 7 < 10 |
| OFF | SANDUSDT | best_strategy | SAND LONG Best | -0.04% | 0.99 | 2.86% | -0.46% | n/a | n/a | return -0.59% <= 0.00%; PF 0.83 < 1.05 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | n/a | n/a | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
