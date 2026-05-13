# Operational Daily Monitor

Generated: 2026-05-09T15:09:09.363347+00:00

| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| TRADE | GALAUSDT | best_strategy | Минутка 10 | +16.22% | 1.84 | 1.41% | +5.42% | +0.13% | 1.31 | return +16.22% > 0.00%; PF 1.84 >= 1.05; DD 1.41% <= 18.00%; trades 959 >= 20 | stress passed | paper passed |
| TRADE | RIFUSDT | regime_monitor | RIF Regime Monitor | +62.54% | 2.41 | 6.00% | +41.23% | +28.70% | 2.25 | 30d+60d health | stress passed | paper passed |
| WATCH | DYDXUSDT | best_strategy | DYDX Pullback SHORT x2 Protected | +22.71% | 3.86 | 2.87% | +19.32% | n/a | n/a | return +22.71% > 0.00%; PF 3.86 >= 1.10; DD 2.87% <= 12.00%; trades 34 >= 10 | stress passed |
| WATCH | GALAUSDT | best_strategy | Минутка 7.3 | +23.03% | 1.56 | 3.50% | +1.48% | -0.89% | 0.54 | return +23.03% > 0.00%; PF 1.56 >= 1.05; DD 3.50% <= 18.00%; trades 1119 >= 30 | stress failed: strict_maker: return -0.34% <= 0; PF 0.99 < 1.00 | paper weak: paper return -0.89% <= 0.00%; paper PF 0.54 < 1.00 |
| WATCH | GALAUSDT | best_strategy | Минутка 11.2 | +26.52% | 1.52 | 4.93% | -1.05% | -0.31% | 0.79 | return +26.52% > 0.00%; PF 1.52 >= 1.08; DD 4.93% <= 18.00%; trades 1177 >= 30 | stress failed: taker_like: return -1.05% <= 0; PF 0.98 < 1.00 | paper weak: paper return -0.31% <= 0.00%; paper PF 0.79 < 1.00 |
| WATCH | MANAUSDT | best_strategy | MANA LONG Best | +2.90% | 1.93 | 3.06% | +1.61% | n/a | n/a | return +4.83% > 0.00%; PF 2.18 >= 1.05; DD 3.06% <= 15.00%; trades 21 >= 5 | stress passed |
| WATCH | SANDUSDT | best_strategy | SAND LONG Best | +0.92% | 1.31 | 2.86% | +0.44% | n/a | n/a | return +0.92% > 0.00%; PF 1.31 >= 1.05; DD 2.86% <= 12.00%; trades 7 >= 5 | stress passed |
| WATCH | SPELLUSDT | best_strategy | SPELL SHORT Best | +5.20% | 1.84 | 6.09% | +4.12% | +0.96% | inf | return +5.20% > 0.00%; PF 1.84 >= 1.08; DD 6.09% <= 16.00%; trades 16 >= 10 | stress passed | paper weak: paper accepted 1 < 5 |
| WATCH | GALAUSDT+SPELLUSDT | cashflow | Monthly Cashflow 4% 24M | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are mixed: ['WATCH', 'WATCH'] |
| WATCH | ACHUSDT | regime_monitor | ACH Regime Monitor | +12.10% | 1.38 | 7.13% | +2.27% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | REZUSDT | regime_monitor | REZ Regime Monitor | +16.62% | 1.53 | 5.56% | +14.24% | n/a | n/a | 30d+60d health | stress passed |
| WATCH | B2USDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | GUAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| WATCH | IRYSUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | ANKRUSDT | best_strategy | ANKR LONG Best | -1.68% | 0.53 | 2.53% | -2.04% | -1.52% | 0.39 | return -1.68% <= 0.00%; PF 0.53 < 1.08; trades 5 < 10 | paper weak: paper accepted 2 < 5; paper return -1.52% <= 0.00%; paper PF 0.39 < 1.00 |
| OFF | JASMYUSDT | best_strategy | JASMY SHORT Best | +1.67% | 2.77 | 0.50% | +1.21% | n/a | n/a | trades 7 < 10 |
| OFF | 1000SHIBUSDT | best_strategy | SHIB LONG Best | +0.95% | 1.66 | 0.79% | +0.32% | n/a | n/a | trades 8 < 10 |
| OFF | ONEUSDT+SPELLUSDT | cashflow | Monthly Cashflow 10% 24M High Risk | n/a | n/a | n/a% | n/a | n/a | n/a | constituent strategies are not healthy: ['ERROR', 'WATCH'] |
| OFF | MEGAUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| OFF | RAVEUSDT | wave_monitor | Wave Monitor | n/a | n/a | n/a% | n/a | n/a | n/a | requires separate hot/wave trigger; no always-on trade |
| ERROR | CHZUSDT | best_strategy | Минутка 10 CHZ Best | n/a | n/a | n/a% | n/a | n/a | n/a | Failed to fetch https://data.binance.vision/data/futures/um/daily/klines/CHZUSDT/1m/CHZUSDT-1m-2026-05-09.zip: <urlopen error [Errno 60] Operation timed out> |
| ERROR | ONEUSDT | best_strategy | Минутка 11.2 | n/a | n/a | n/a% | n/a | n/a | n/a | Failed to fetch https://data.binance.vision/data/futures/um/daily/klines/ONEUSDT/1m/ONEUSDT-1m-2026-05-09.zip: <urlopen error [Errno 60] Operation timed out> |

## How To Read

- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.
- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.
- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.

Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.
