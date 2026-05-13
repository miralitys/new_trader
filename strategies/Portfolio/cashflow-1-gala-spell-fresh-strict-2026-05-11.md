# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-11T15:20:41.141245+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.
Monthly loss stop: `35%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 34 | -1.19% | $988.12 | $0.00 | no | +1.83% | 0.65 | +88.24% | period_end | GALA=34 |
| 7d | cashflow_stop | 34 | -1.19% | $988.12 | $0.00 | no | +1.83% | 0.65 | +88.24% | period_end | GALA=34 |
| 30d | continuous | 196 | -30.03% | $699.68 | $0.00 | no | +49.71% | 0.72 | +88.27% | period_end | GALA=169;SPELL=27 |
| 30d | cashflow_stop | 14 | +5.01% | $1050.12 | $50.12 | yes | +0.26% | 19.22 | +92.86% | profit_target | GALA=13;SPELL=1 |
| 60d | continuous | 329 | -33.86% | $661.44 | $0.00 | no | +57.22% | 0.76 | +86.02% | period_end | GALA=292;SPELL=37 |
| 60d | cashflow_stop | 68 | +8.77% | $1087.73 | $87.73 | yes | +2.14% | 2.82 | +86.76% | profit_target | GALA=65;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | GALA | Минутка 11.2 | 140 | 52 | +37.14% | 34 | -0.98% | 0.65 | +88.24% | take_profit=30;time_stop=4 |
| 30d | GALA | Минутка 11.2 | 589 | 227 | +38.54% | 169 | -0.03% | 1.00 | +89.94% | take_profit=152;time_stop=15;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 31 | 27 | +87.10% | 27 | -4.33% | 0.82 | +77.78% | take_profit=20;stop_loss=5;time_stop=2 |
| 60d | GALA | Минутка 11.2 | 1086 | 381 | +35.08% | 292 | -1.69% | 0.91 | +87.67% | take_profit=256;time_stop=34;stop_loss=2 |
| 60d | SPELL | SPELL SHORT Best | 41 | 37 | +90.24% | 37 | -4.51% | 0.85 | +72.97% | take_profit=25;time_stop=6;stop_loss=6 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+5.01%`, а если продолжать торговать без остановки - `-30.03%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+8.77%`, а если продолжать торговать без остановки - `-33.86%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow1_gala_spell_fresh_strict_journal_2026-05-11.csv`
- Portfolio summary CSV: `data/cashflow1_gala_spell_fresh_strict_summary_2026-05-11.csv`
- Module summary CSV: `data/cashflow1_gala_spell_fresh_strict_modules_2026-05-11.csv`
