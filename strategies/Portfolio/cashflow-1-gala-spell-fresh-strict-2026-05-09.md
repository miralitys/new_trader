# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-09T15:23:48.745841+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.
Monthly loss stop: `35%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 41 | -0.64% | $993.55 | $0.00 | no | +1.83% | 0.81 | +90.24% | period_end | GALA=41 |
| 7d | cashflow_stop | 41 | -0.64% | $993.55 | $0.00 | no | +1.83% | 0.81 | +90.24% | period_end | GALA=41 |
| 30d | continuous | 201 | -29.82% | $701.84 | $0.00 | no | +49.71% | 0.73 | +88.56% | period_end | GALA=174;SPELL=27 |
| 30d | cashflow_stop | 7 | +5.03% | $1050.31 | $50.31 | yes | +0.00% | inf | +100.00% | profit_target | GALA=6;SPELL=1 |
| 60d | continuous | 360 | -34.19% | $658.07 | $0.00 | no | +57.22% | 0.76 | +85.83% | period_end | GALA=323;SPELL=37 |
| 60d | cashflow_stop | 99 | +8.22% | $1082.19 | $82.19 | yes | +2.14% | 2.16 | +85.86% | profit_target | GALA=96;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | GALA | Минутка 11.2 | 153 | 59 | +38.56% | 41 | -0.52% | 0.82 | +90.24% | take_profit=37;time_stop=4 |
| 30d | GALA | Минутка 11.2 | 605 | 233 | +38.51% | 174 | +0.23% | 1.02 | +90.23% | take_profit=157;time_stop=15;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 31 | 27 | +87.10% | 27 | -4.33% | 0.82 | +77.78% | take_profit=20;stop_loss=5;time_stop=2 |
| 60d | GALA | Минутка 11.2 | 1198 | 425 | +35.48% | 323 | -2.11% | 0.90 | +87.31% | take_profit=282;time_stop=39;stop_loss=2 |
| 60d | SPELL | SPELL SHORT Best | 41 | 37 | +90.24% | 37 | -4.51% | 0.85 | +72.97% | take_profit=25;time_stop=6;stop_loss=6 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+5.03%`, а если продолжать торговать без остановки - `-29.82%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+8.22%`, а если продолжать торговать без остановки - `-34.19%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow1_gala_spell_fresh_strict_journal_2026-05-09.csv`
- Portfolio summary CSV: `data/cashflow1_gala_spell_fresh_strict_summary_2026-05-09.csv`
- Module summary CSV: `data/cashflow1_gala_spell_fresh_strict_modules_2026-05-09.csv`
