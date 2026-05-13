# Operational Daily Monitor

Generated: 2026-05-13T15:09:32.687640+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +14.11% | 1.99 | 1.41% | +7.36% | +0.23% | 2.04 | return +14.11% > 0.00%; PF 1.99 >= 1.05; DD 1.41% <= 18.00%; trades 764 >= 20 | stress passed | paper passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +60.55% | 2.30 | 6.00% | +39.32% | +20.41% | 3.04 | 30d+60d health | stress passed | paper passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +6.95% | 1.86 | 3.34% | +3.22% | n/a | n/a | return +6.95% > 0.00%; PF 1.86 >= 1.05; DD 3.34% <= 15.00%; trades 42 >= 10 | stress passed |
| WATCH | DYDXUSDT | best_strategy | DYDX Pullback SHORT x2 Protected | +20.20% | 14.03 | 1.42% | +18.23% | n/a | n/a | return +20.20% > 0.00%; PF 14.03 >= 1.10; DD 1.42% <= 12.00%; trades 21 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +17.16% | 1.53 | 3.50% | -1.27% | -0.55% | 0.58 | return +17.16% > 0.00%; PF 1.53 >= 1.05; DD 3.50% <= 18.00%; trades 894 >= 30 | stress failed: strict_maker: return -1.28% <= 0; PF 0.95 < 1.00 | taker_like: return -1.27% <= 0; PF 0.96 < 1.00 | paper weak: paper return -0.55% <= 0.00%; paper PF 0.58 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +19.54% | 1.49 | 4.93% | -3.85% | -0.45% | 0.66 | return +19.54% > 0.00%; PF 1.49 >= 1.08; DD 4.93% <= 18.00%; trades 943 >= 30 | stress failed: taker_like: return -3.85% <= 0; PF 0.90 < 1.00 | paper weak: paper return -0.45% <= 0.00%; paper PF 0.66 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +1.96% | 1.63 | 3.06% | +0.81% | n/a | n/a | return +5.29% > 0.00%; PF 2.65 >= 1.05; DD 3.06% <= 15.00%; trades 19 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +4.36% | 1.20 | 3.33% | +3.05% | n/a | n/a | return +4.36% > 0.00%; PF 1.20 >= 1.05; DD 3.33% <= 18.00%; trades 473 >= 20 | stress weak: strict_maker: return -7.60% <= 0; PF 0.57 < 1.00 |
| WATCH | SANDUSDT | best_strategy | SAND LONG Best | +0.92% | 1.31 | 2.86% | +0.44% | n/a | n/a | return +0.92% > 0.00%; PF 1.31 >= 1.05; DD 2.86% <= 12.00%; trades 7 >= 5 | stress passed |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +4.20% | 1.69 | 6.09% | +3.19% | +0.00% | 0.00 | return +4.20% > 0.00%; PF 1.69 >= 1.08; DD 6.09% <= 16.00%; trades 15 >= 10 | stress passed | paper weak: paper accepted 0 < 5; paper return +0.00% <= 0.00%; paper PF 0.00 < 1.00 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +5.37% | 1.14 | 11.81% | -4.42% | n/a | n/a | 30d+60d health | stress weak: taker_like: return -4.42% <= 0; PF 0.86 < 1.00 |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +20.03% | 1.82 | 5.05% | +17.72% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -0.92% | 0.68 | 2.53% | -1.20% | -1.52% | 0.39 | return -0.92% <= 0.00%; PF 0.68 < 1.08; trades 4 < 10 | paper weak: paper accepted 2 < 5; paper return -1.52% <= 0.00%; paper PF 0.39 < 1.00 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | n/a | n/a | trades 7 < 10 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | n/a | n/a | trades 8 < 10 |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |

## How To Read

- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
