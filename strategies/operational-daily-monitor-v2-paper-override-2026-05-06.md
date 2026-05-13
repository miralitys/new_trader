# Operational Daily Monitor

Generated: 2026-05-06T15:07:22.780594+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +30.54% | 1.95 | 6.00% | +7.50% | +13.06% | 1.93 | 30d+60d health | stress passed | paper passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +6.73% | 2.62 | 1.77% | +4.41% | n/a | n/a | return +6.73% > 0.00%; PF 2.62 >= 1.05; DD 1.77% <= 15.00%; trades 28 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +29.77% | 1.67 | 3.50% | +4.01% | -0.33% | 0.72 | return +29.77% > 0.00%; PF 1.67 >= 1.05; DD 3.50% <= 18.00%; trades 1257 >= 30 | stress passed | paper weak: paper return -0.33% <= 0.00%; paper PF 0.72 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 10 | +17.73% | 1.79 | 1.41% | +6.00% | n/a | n/a | return +17.73% > 0.00%; PF 1.79 >= 1.05; DD 1.41% <= 18.00%; trades 1083 >= 20 | stress failed: strict_maker: return -0.41% <= 0; PF 0.98 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +33.03% | 1.59 | 4.93% | -0.30% | -0.22% | 0.74 | return +33.03% > 0.00%; PF 1.59 >= 1.08; DD 4.93% <= 18.00%; trades 1327 >= 30 | stress failed: taker_like: return -0.30% <= 0; PF 0.99 < 1.00 | paper weak: paper return -0.22% <= 0.00%; paper PF 0.74 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.90% | 1.93 | 3.06% | +1.61% | n/a | n/a | return +4.25% > 0.00%; PF 1.77 >= 1.05; DD 3.06% <= 15.00%; trades 24 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +11.49% | 1.31 | 3.62% | +7.03% | n/a | n/a | return +11.49% > 0.00%; PF 1.31 >= 1.05; DD 3.62% <= 18.00%; trades 816 >= 20 | stress weak: strict_maker: return -10.33% <= 0; PF 0.63 < 1.00 |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +5.20% | 1.84 | 6.09% | +4.12% | +1.92% | inf | return +5.20% > 0.00%; PF 1.84 >= 1.08; DD 6.09% <= 16.00%; trades 16 >= 10 | stress passed | paper weak: paper accepted 2 < 5 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +14.68% | 1.56 | 4.31% | +2.37% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +17.06% | 1.43 | 8.38% | +16.67% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -1.34% | 0.58 | 2.19% | -1.69% | +0.00% | 0.00 | return -1.34% <= 0.00%; PF 0.58 < 1.08; trades 5 < 10 | paper weak: paper accepted 0 < 5; paper return +0.00% <= 0.00%; paper PF 0.00 < 1.00 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | n/a | n/a | trades 7 < 10 |
| OFF | SANDUSDT | best_strategy | SAND LONG Best | -0.04% | 0.99 | 2.86% | -0.46% | n/a | n/a | return -0.23% <= 0.00%; PF 0.94 < 1.05 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | n/a | n/a | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
