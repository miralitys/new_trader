# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-13T15:25:48.428132+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.
Monthly loss stop: `35%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 25 | +0.91% | $1009.13 | $9.13 | no | +0.47% | 2.39 | +92.00% | period_end | GALA=25 |
| 1d | cashflow_stop | 25 | +0.91% | $1009.13 | $9.13 | no | +0.47% | 2.39 | +92.00% | period_end | GALA=25 |
| 7d | continuous | 26 | +1.02% | $1010.24 | $10.24 | no | +0.47% | 2.55 | +92.31% | period_end | GALA=26 |
| 7d | cashflow_stop | 26 | +1.02% | $1010.24 | $10.24 | no | +0.47% | 2.55 | +92.31% | period_end | GALA=26 |
| 30d | continuous | 220 | -32.50% | $674.96 | $0.00 | no | +49.71% | 0.69 | +88.64% | period_end | GALA=194;SPELL=26 |
| 30d | cashflow_stop | 124 | -35.05% | $649.54 | $0.00 | no | +37.61% | 0.44 | +87.90% | loss_stop | GALA=116;SPELL=8 |
| 60d | continuous | 321 | -33.57% | $664.30 | $0.00 | no | +57.22% | 0.76 | +85.98% | period_end | GALA=284;SPELL=37 |
| 60d | cashflow_stop | 34 | +8.15% | $1081.53 | $81.53 | yes | +1.30% | 3.54 | +82.35% | profit_target | GALA=31;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | GALA | Минутка 11.2 | 84 | 34 | +40.48% | 25 | +0.76% | 2.38 | +92.00% | take_profit=23;time_stop=2 |
| 7d | GALA | Минутка 11.2 | 85 | 35 | +41.18% | 26 | +0.85% | 2.55 | +92.31% | take_profit=23;time_stop=2;end_of_data=1 |
| 30d | GALA | Минутка 11.2 | 670 | 261 | +38.96% | 194 | +0.73% | 1.07 | +90.21% | take_profit=175;time_stop=17;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 30 | 26 | +86.67% | 26 | -5.29% | 0.78 | +76.92% | take_profit=19;stop_loss=5;time_stop=2 |
| 60d | GALA | Минутка 11.2 | 1021 | 369 | +36.14% | 284 | -1.34% | 0.92 | +87.68% | take_profit=249;time_stop=33;stop_loss=2 |
| 60d | SPELL | SPELL SHORT Best | 41 | 37 | +90.24% | 37 | -4.51% | 0.85 | +72.97% | take_profit=25;time_stop=6;stop_loss=6 |

## Человеческий вывод

На `60d` видно главное: с остановкой после цели результат `+8.15%`, а если продолжать торговать без остановки - `-33.57%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d, 30d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow1_gala_spell_fresh_strict_journal_2026-05-13.csv`
- Portfolio summary CSV: `data/cashflow1_gala_spell_fresh_strict_summary_2026-05-13.csv`
- Module summary CSV: `data/cashflow1_gala_spell_fresh_strict_modules_2026-05-13.csv`
