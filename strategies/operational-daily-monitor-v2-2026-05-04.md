# Operational Daily Monitor

Generated: 2026-05-04T20:31:36.231370+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Stress PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| TRADE | ANKRUSDT | best_strategy | ANKR LONG Best | +3.56% | 1.83 | 3.05% | +2.73% | 1.59 | return +3.56% > 0.00%; PF 1.83 >= 1.08; DD 3.05% <= 18.00%; trades 12 >= 10 | stress passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +25.76% | 2.03 | 6.00% | +5.16% | 1.15 | 30d+60d health | stress passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +7.74% | 5.19 | 1.14% | +5.78% | 3.79 | return +7.74% > 0.00%; PF 5.19 >= 1.05; DD 1.14% <= 15.00%; trades 23 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +29.93% | 1.64 | 3.50% | +3.47% | 1.07 | return +29.93% > 0.00%; PF 1.64 >= 1.05; DD 3.50% <= 18.00%; trades 1314 >= 30 | stress failed: strict_maker: return -0.09% <= 0; PF 1.00 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 10 | +18.24% | 1.75 | 1.41% | +6.26% | 1.25 | return +18.24% > 0.00%; PF 1.75 >= 1.05; DD 1.41% <= 18.00%; trades 1159 >= 20 | stress failed: strict_maker: return -0.77% <= 0; PF 0.97 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +32.33% | 1.55 | 4.93% | -0.02% | 1.00 | return +32.33% > 0.00%; PF 1.55 >= 1.08; DD 4.93% <= 18.00%; trades 1395 >= 30 | stress failed: taker_like: return -0.02% <= 0; PF 1.00 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.43% | 1.78 | 3.06% | +1.21% | 1.38 | return +3.78% > 0.00%; PF 1.68 >= 1.05; DD 3.06% <= 15.00%; trades 23 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +13.50% | 1.32 | 3.62% | +5.22% | 1.13 | return +13.50% > 0.00%; PF 1.32 >= 1.05; DD 3.62% <= 18.00%; trades 926 >= 20 | stress weak: strict_maker: return -12.87% <= 0; PF 0.59 < 1.00 |
| WATCH | SANDUSDT | best_strategy | SAND LONG Best | +0.44% | 1.18 | 2.40% | +0.18% | 1.07 | return +0.25% > 0.00%; PF 1.08 >= 1.05; DD 2.40% <= 12.00%; trades 7 >= 5 | stress weak: strict_maker: return -0.46% <= 0; PF 0.81 < 1.00 |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +2.82% | 1.34 | 6.99% | +1.68% | 1.20 | return +2.82% > 0.00%; PF 1.34 >= 1.08; DD 6.99% <= 16.00%; trades 17 >= 10 | stress failed: strict_maker: return -0.78% <= 0; PF 0.90 < 1.00 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +19.04% | 2.15 | 4.31% | +6.24% | 1.31 | 30d+60d health | stress passed |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +29.24% | 1.52 | 8.38% | +26.18% | 1.47 | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +2.10% | 5.13 | 0.50% | +1.72% | 3.36 | trades 6 < 10 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | 1.18 | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check прошел и stress исполнения не сломал стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически или stress слабый.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
