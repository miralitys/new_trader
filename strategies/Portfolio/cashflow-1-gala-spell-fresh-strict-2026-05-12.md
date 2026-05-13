# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-12T11:57:47.713605+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.
Monthly loss stop: `35%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 31 | -1.36% | $986.40 | $0.00 | no | +1.83% | 0.60 | +87.10% | period_end | GALA=31 |
| 7d | cashflow_stop | 31 | -1.36% | $986.40 | $0.00 | no | +1.83% | 0.60 | +87.10% | period_end | GALA=31 |
| 30d | continuous | 194 | -33.18% | $668.22 | $0.00 | no | +49.71% | 0.68 | +88.14% | period_end | GALA=168;SPELL=26 |
| 30d | cashflow_stop | 124 | -35.05% | $649.54 | $0.00 | no | +37.61% | 0.44 | +87.90% | loss_stop | GALA=116;SPELL=8 |
| 60d | continuous | 315 | -34.45% | $655.54 | $0.00 | no | +57.22% | 0.75 | +85.40% | period_end | GALA=278;SPELL=37 |
| 60d | cashflow_stop | 54 | +7.80% | $1078.03 | $78.03 | yes | +2.14% | 2.57 | +83.33% | profit_target | GALA=51;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | GALA | Минутка 11.2 | 125 | 49 | +39.20% | 31 | -1.13% | 0.60 | +87.10% | take_profit=27;time_stop=4 |
| 30d | GALA | Минутка 11.2 | 585 | 226 | +38.63% | 168 | -0.11% | 0.99 | +89.88% | take_profit=151;time_stop=15;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 30 | 26 | +86.67% | 26 | -5.29% | 0.78 | +76.92% | take_profit=19;stop_loss=5;time_stop=2 |
| 60d | GALA | Минутка 11.2 | 1016 | 365 | +35.93% | 278 | -2.44% | 0.87 | +87.05% | take_profit=242;time_stop=34;stop_loss=2 |
| 60d | SPELL | SPELL SHORT Best | 41 | 37 | +90.24% | 37 | -4.51% | 0.85 | +72.97% | take_profit=25;time_stop=6;stop_loss=6 |

## Человеческий вывод

На `60d` видно главное: с остановкой после цели результат `+7.80%`, а если продолжать торговать без остановки - `-34.45%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d, 30d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow1_gala_spell_fresh_strict_journal_2026-05-12.csv`
- Portfolio summary CSV: `data/cashflow1_gala_spell_fresh_strict_summary_2026-05-12.csv`
- Module summary CSV: `data/cashflow1_gala_spell_fresh_strict_modules_2026-05-12.csv`
