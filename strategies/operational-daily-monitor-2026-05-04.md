# Operational Daily Monitor

Generated: 2026-05-04T20:21:07.357234+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Trades30 | 60d | PF60 | DD60 | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| TRADE | ANKRUSDT | best_strategy | ANKR LONG Best | +3.56% | 1.83 | 3.05% | 12 | +29.38% | 2.21 | 4.04% | return +3.56% > 0.00%; PF 1.83 >= 1.08; DD 3.05% <= 18.00%; trades 12 >= 10 |
| TRADE | GALAUSDT | best_strategy | Минутка 7.3 | +29.93% | 1.64 | 3.50% | 1314 | +73.64% | 1.64 | 3.50% | return +29.93% > 0.00%; PF 1.64 >= 1.05; DD 3.50% <= 18.00%; trades 1314 >= 30 |
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +18.24% | 1.75 | 1.41% | 1159 | +31.55% | 1.48 | 1.81% | return +18.24% > 0.00%; PF 1.75 >= 1.05; DD 1.41% <= 18.00%; trades 1159 >= 20 |
| TRADE | GALAUSDT | best_strategy | Минутка 11.2 | +32.33% | 1.55 | 4.93% | 1395 | +70.97% | 1.50 | 4.93% | return +32.33% > 0.00%; PF 1.55 >= 1.08; DD 4.93% <= 18.00%; trades 1395 >= 30 |
| TRADE | SPELLUSDT | best_strategy | SPELL SHORT Best | +2.82% | 1.34 | 6.99% | 17 | +3.66% | 1.32 | 7.03% | return +2.82% > 0.00%; PF 1.34 >= 1.08; DD 6.99% <= 16.00%; trades 17 >= 10 |
| TRADE | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% |  | n/a | n/a | n/a% | constituent strategies are TRADE |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +25.76% | 2.03 | 6.00% | 69 | +36.44% | 1.58 | 6.00% | 30d+60d health |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +7.74% | 5.19 | 1.14% | 23 | +14.34% | 3.96 | 1.75% | return +7.74% > 0.00%; PF 5.19 >= 1.05; DD 1.14% <= 15.00%; trades 23 >= 10 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.43% | 1.78 | 3.06% | 13 | +3.78% | 1.68 | 3.06% | return +3.78% > 0.00%; PF 1.68 >= 1.05; DD 3.06% <= 15.00%; trades 23 >= 5 |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +13.50% | 1.32 | 3.62% | 926 | +43.92% | 1.34 | 8.89% | return +13.50% > 0.00%; PF 1.32 >= 1.05; DD 3.62% <= 18.00%; trades 926 >= 20 |
| WATCH | SANDUSDT | best_strategy | SAND LONG Best | +0.44% | 1.18 | 2.40% | 4 | +0.25% | 1.08 | 2.40% | return +0.25% > 0.00%; PF 1.08 >= 1.05; DD 2.40% <= 12.00%; trades 7 >= 5 |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% |  | n/a | n/a | n/a% | constituent strategies are mixed: ['WATCH', 'TRADE'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +19.04% | 2.15 | 4.31% | 119 | +25.22% | 2.16 | 4.31% | 30d+60d health |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +29.24% | 1.52 | 8.38% | 105 | +27.44% | 1.26 | 11.40% | 30d+60d health |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% |  | n/a | n/a | n/a% | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% |  | n/a | n/a | n/a% | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% |  | n/a | n/a | n/a% | requires separate hot/wave trigger; no always-on trade |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +2.10% | 5.13 | 0.50% | 6 | +2.47% | 1.32 | 3.35% | trades 6 < 10 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | 8 | +0.87% | 1.05 | 5.88% | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% |  | n/a | n/a | n/a% | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% |  | n/a | n/a | n/a% | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check прошел, можно продолжать paper/live-small режим.
- WATCH: стратегия интересная, но ее нельзя включать автоматически.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
