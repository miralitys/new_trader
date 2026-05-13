# Operational Daily Monitor

Generated: 2026-05-05T15:08:04.829975+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Stress PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 7.3 | +29.73% | 1.64 | 3.50% | +3.37% | 1.07 | return +29.73% > 0.00%; PF 1.64 >= 1.05; DD 3.50% <= 18.00%; trades 1291 >= 30 | stress passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +30.51% | 2.15 | 6.00% | +6.60% | 1.19 | 30d+60d health | stress passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +8.15% | 4.64 | 1.14% | +5.95% | 3.34 | return +8.15% > 0.00%; PF 4.64 >= 1.05; DD 1.14% <= 15.00%; trades 26 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 10 | +17.58% | 1.75 | 1.41% | +6.18% | 1.25 | return +17.58% > 0.00%; PF 1.75 >= 1.05; DD 1.41% <= 18.00%; trades 1118 >= 20 | stress failed: strict_maker: return -0.82% <= 0; PF 0.96 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +32.61% | 1.56 | 4.93% | -0.12% | 1.00 | return +32.61% > 0.00%; PF 1.56 >= 1.08; DD 4.93% <= 18.00%; trades 1359 >= 30 | stress failed: taker_like: return -0.12% <= 0; PF 1.00 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.90% | 1.93 | 3.06% | +1.61% | 1.50 | return +4.25% > 0.00%; PF 1.77 >= 1.05; DD 3.06% <= 15.00%; trades 24 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +10.35% | 1.26 | 3.62% | +4.49% | 1.12 | return +10.35% > 0.00%; PF 1.26 >= 1.05; DD 3.62% <= 18.00%; trades 858 >= 20 | stress weak: strict_maker: return -11.12% <= 0; PF 0.62 < 1.00 |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +2.82% | 1.34 | 6.99% | +1.68% | 1.20 | return +2.82% > 0.00%; PF 1.34 >= 1.08; DD 6.99% <= 16.00%; trades 17 >= 10 | stress failed: strict_maker: return -0.78% <= 0; PF 0.90 < 1.00 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +16.99% | 1.89 | 4.31% | +4.46% | 1.20 | 30d+60d health | stress passed |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +29.39% | 1.56 | 8.38% | +25.51% | 1.49 | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -2.21% | 0.46 | 3.05% | -2.64% | 0.40 | return -2.21% <= 0.00%; PF 0.46 < 1.08; trades 6 < 10 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | 1.98 | trades 7 < 10 |
| OFF | SANDUSDT | best_strategy | SAND LONG Best | -0.04% | 0.99 | 2.86% | -0.46% | 0.86 | return -0.23% <= 0.00%; PF 0.94 < 1.05 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | 1.18 | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check прошел и stress исполнения не сломал стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически или stress слабый.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
