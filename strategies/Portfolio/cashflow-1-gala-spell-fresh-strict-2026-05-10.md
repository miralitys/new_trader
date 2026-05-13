# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-10T15:24:10.167033+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.
Monthly loss stop: `35%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 36 | -1.00% | $989.97 | $0.00 | no | +1.83% | 0.71 | +88.89% | period_end | GALA=36 |
| 7d | cashflow_stop | 36 | -1.00% | $989.97 | $0.00 | no | +1.83% | 0.71 | +88.89% | period_end | GALA=36 |
| 30d | continuous | 196 | -30.03% | $699.68 | $0.00 | no | +49.71% | 0.72 | +88.27% | period_end | GALA=169;SPELL=27 |
| 30d | cashflow_stop | 14 | +5.01% | $1050.12 | $50.12 | yes | +0.26% | 19.22 | +92.86% | profit_target | GALA=13;SPELL=1 |
| 60d | continuous | 346 | -33.82% | $661.82 | $0.00 | no | +57.22% | 0.76 | +86.13% | period_end | GALA=309;SPELL=37 |
| 60d | cashflow_stop | 85 | +8.84% | $1088.36 | $88.36 | yes | +2.14% | 2.44 | +87.06% | profit_target | GALA=82;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | GALA | Минутка 11.2 | 144 | 54 | +37.50% | 36 | -0.82% | 0.71 | +88.89% | take_profit=32;time_stop=4 |
| 30d | GALA | Минутка 11.2 | 591 | 227 | +38.41% | 169 | -0.03% | 1.00 | +89.94% | take_profit=152;time_stop=15;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 31 | 27 | +87.10% | 27 | -4.33% | 0.82 | +77.78% | take_profit=20;stop_loss=5;time_stop=2 |
| 60d | GALA | Минутка 11.2 | 1138 | 404 | +35.50% | 309 | -1.64% | 0.92 | +87.70% | take_profit=271;time_stop=36;stop_loss=2 |
| 60d | SPELL | SPELL SHORT Best | 41 | 37 | +90.24% | 37 | -4.51% | 0.85 | +72.97% | take_profit=25;time_stop=6;stop_loss=6 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+5.01%`, а если продолжать торговать без остановки - `-30.03%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+8.84%`, а если продолжать торговать без остановки - `-33.82%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow1_gala_spell_fresh_strict_journal_2026-05-10.csv`
- Portfolio summary CSV: `data/cashflow1_gala_spell_fresh_strict_summary_2026-05-10.csv`
- Module summary CSV: `data/cashflow1_gala_spell_fresh_strict_modules_2026-05-10.csv`
