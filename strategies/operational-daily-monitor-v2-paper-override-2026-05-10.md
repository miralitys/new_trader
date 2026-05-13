# Operational Daily Monitor

Generated: 2026-05-10T15:09:56.105763+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +14.26% | 1.77 | 1.41% | +5.51% | +0.13% | 1.31 | return +14.26% > 0.00%; PF 1.77 >= 1.05; DD 1.41% <= 18.00%; trades 898 >= 20 | stress passed | paper passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +60.55% | 2.30 | 6.00% | +39.32% | +28.32% | 2.60 | 30d+60d health | stress passed | paper passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +7.61% | 2.10 | 3.34% | +4.07% | n/a | n/a | return +7.61% > 0.00%; PF 2.10 >= 1.05; DD 3.34% <= 15.00%; trades 39 >= 10 | stress passed |
| WATCH | DYDXUSDT | best_strategy | DYDX Pullback SHORT x2 Protected | +22.71% | 3.86 | 2.87% | +19.32% | n/a | n/a | return +22.71% > 0.00%; PF 3.86 >= 1.10; DD 2.87% <= 12.00%; trades 34 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +22.20% | 1.57 | 3.50% | +1.18% | -0.89% | 0.54 | return +22.20% > 0.00%; PF 1.57 >= 1.05; DD 3.50% <= 18.00%; trades 1064 >= 30 | stress passed | paper weak: paper return -0.89% <= 0.00%; paper PF 0.54 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +24.22% | 1.51 | 4.93% | -2.31% | -0.31% | 0.79 | return +24.22% > 0.00%; PF 1.51 >= 1.08; DD 4.93% <= 18.00%; trades 1104 >= 30 | stress failed: taker_like: return -2.31% <= 0; PF 0.95 < 1.00 | paper weak: paper return -0.31% <= 0.00%; paper PF 0.79 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +1.96% | 1.63 | 3.06% | +0.81% | n/a | n/a | return +4.35% > 0.00%; PF 2.07 >= 1.05; DD 3.06% <= 15.00%; trades 20 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +6.50% | 1.24 | 3.62% | +2.38% | n/a | n/a | return +6.50% > 0.00%; PF 1.24 >= 1.05; DD 3.62% <= 18.00%; trades 597 >= 20 | stress weak: strict_maker: return -10.16% <= 0; PF 0.55 < 1.00 |
| WATCH | SANDUSDT | best_strategy | SAND LONG Best | +0.92% | 1.31 | 2.86% | +0.44% | n/a | n/a | return +0.92% > 0.00%; PF 1.31 >= 1.05; DD 2.86% <= 12.00%; trades 7 >= 5 | stress passed |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +5.20% | 1.84 | 6.09% | +4.12% | +0.96% | inf | return +5.20% > 0.00%; PF 1.84 >= 1.08; DD 6.09% <= 16.00%; trades 16 >= 10 | stress passed | paper weak: paper accepted 1 < 5 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +9.35% | 1.27 | 8.50% | -0.38% | n/a | n/a | 30d+60d health | stress weak: taker_like: return -0.38% <= 0; PF 0.99 < 1.00 |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +18.56% | 1.62 | 5.56% | +15.10% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -1.68% | 0.53 | 2.53% | -2.04% | -1.52% | 0.39 | return -1.68% <= 0.00%; PF 0.53 < 1.08; trades 5 < 10 | paper weak: paper accepted 2 < 5; paper return -1.52% <= 0.00%; paper PF 0.39 < 1.00 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | n/a | n/a | trades 7 < 10 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | n/a | n/a | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
