# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-12T11:50:42.298341+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 12 | +1.49% | $1014.88 | $14.88 | no | +1.91% | 1.59 | +75.00% | period_end | CHZ=12 |
| 7d | cashflow_stop | 12 | +1.49% | $1014.88 | $14.88 | no | +1.91% | 1.59 | +75.00% | period_end | CHZ=12 |
| 30d | continuous | 56 | -27.33% | $726.72 | $0.00 | no | +67.28% | 0.70 | +71.43% | period_end | CHZ=31;SPELL=19;SHIB=6 |
| 30d | cashflow_stop | 13 | +6.75% | $1067.49 | $67.49 | yes | +0.30% | 11.20 | +76.92% | profit_target | CHZ=9;SHIB=3;SPELL=1 |
| 60d | continuous | 87 | -31.26% | $687.40 | $0.00 | no | +71.24% | 0.76 | +63.22% | period_end | CHZ=35;SPELL=30;SHIB=22 |
| 60d | cashflow_stop | 10 | +10.52% | $1105.23 | $105.23 | yes | +6.86% | 2.49 | +50.00% | profit_target | SHIB=6;SPELL=4 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | CHZ | CHZ LONG Best | 16 | 12 | +75.00% | 12 | +1.50% | 1.60 | +75.00% | take_profit=8;time_stop=4 |
| 30d | CHZ | CHZ LONG Best | 40 | 31 | +77.50% | 31 | +6.52% | 2.49 | +77.42% | take_profit=23;time_stop=8 |
| 30d | SHIB | SHIB LONG Best | 11 | 6 | +54.55% | 6 | -0.40% | 0.54 | +33.33% | time_stop=6 |
| 30d | SPELL | SPELL SHORT Best | 22 | 19 | +86.36% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | CHZ | CHZ LONG Best | 47 | 35 | +74.47% | 35 | +7.82% | 2.76 | +77.14% | take_profit=26;time_stop=9 |
| 60d | SHIB | SHIB LONG Best | 36 | 22 | +61.11% | 22 | +0.23% | 1.03 | +45.45% | time_stop=16;take_profit=6 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+6.75%`, а если продолжать торговать без остановки - `-27.33%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+10.52%`, а если продолжать торговать без остановки - `-31.26%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow2_chz_shib_spell_fresh_strict_journal_2026-05-12.csv`
- Portfolio summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_summary_2026-05-12.csv`
- Module summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_modules_2026-05-12.csv`
