# Operational Daily Monitor

Generated: 2026-05-07T15:02:29.415484+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +18.59% | 1.87 | 1.41% | +6.97% | n/a | n/a | return +18.59% > 0.00%; PF 1.87 >= 1.05; DD 1.41% <= 18.00%; trades 1067 >= 20 | stress passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +41.44% | 1.99 | 6.00% | +18.69% | +21.23% | 2.01 | 30d+60d health | stress passed | paper passed |
| WATCH | CHZUSDT | best_strategy | Минутка 10 CHZ Best | +5.12% | 1.82 | 3.25% | +2.61% | n/a | n/a | return +5.12% > 0.00%; PF 1.82 >= 1.05; DD 3.25% <= 15.00%; trades 31 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +27.52% | 1.61 | 3.50% | +2.34% | -0.89% | 0.54 | return +27.52% > 0.00%; PF 1.61 >= 1.05; DD 3.50% <= 18.00%; trades 1226 >= 30 | stress passed | paper weak: paper return -0.89% <= 0.00%; paper PF 0.54 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +30.76% | 1.55 | 4.93% | -1.52% | -0.31% | 0.79 | return +30.76% > 0.00%; PF 1.55 >= 1.08; DD 4.93% <= 18.00%; trades 1294 >= 30 | stress failed: taker_like: return -1.52% <= 0; PF 0.97 < 1.00 | paper weak: paper return -0.31% <= 0.00%; paper PF 0.79 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.90% | 1.93 | 3.06% | +1.61% | n/a | n/a | return +4.25% > 0.00%; PF 1.77 >= 1.05; DD 3.06% <= 15.00%; trades 24 >= 5 | stress passed |
| WATCH | ONEUSDT | best_strategy | Минутка 11.2 | +8.60% | 1.25 | 3.62% | +3.65% | n/a | n/a | return +8.60% > 0.00%; PF 1.25 >= 1.05; DD 3.62% <= 18.00%; trades 750 >= 20 | stress weak: strict_maker: return -11.74% <= 0; PF 0.58 < 1.00 |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +5.20% | 1.84 | 6.09% | +4.12% | +0.96% | inf | return +5.20% > 0.00%; PF 1.84 >= 1.08; DD 6.09% <= 16.00%; trades 16 >= 10 | stress passed | paper weak: paper accepted 1 < 5 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +15.03% | 1.58 | 4.31% | +2.63% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +12.34% | 1.29 | 12.08% | +10.60% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | +0.87% | 1.83 | 0.77% | +0.59% | +0.00% | 0.00 | trades 4 < 10 | paper weak: paper accepted 0 < 5; paper return +0.00% <= 0.00%; paper PF 0.00 < 1.00 |
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
