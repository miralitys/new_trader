# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-08T19:36:07.973845+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 6 | +0.62% | $1006.19 | $6.19 | no | +0.95% | 1.51 | +66.67% | period_end | CHZ=6 |
| 1d | cashflow_stop | 6 | +0.62% | $1006.19 | $6.19 | no | +0.95% | 1.51 | +66.67% | period_end | CHZ=6 |
| 7d | continuous | 14 | +8.94% | $1089.42 | $89.42 | yes | +1.91% | 3.93 | +71.43% | period_end | CHZ=13;SPELL=1 |
| 7d | cashflow_stop | 1 | +7.68% | $1076.82 | $76.82 | yes | +0.00% | inf | +100.00% | profit_target | SPELL=1 |
| 30d | continuous | 55 | -27.66% | $723.39 | $0.00 | no | +67.28% | 0.69 | +70.91% | period_end | CHZ=30;SPELL=19;SHIB=6 |
| 30d | cashflow_stop | 14 | +7.24% | $1072.40 | $72.40 | yes | +0.30% | 11.89 | +78.57% | profit_target | CHZ=10;SHIB=3;SPELL=1 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | CHZ | CHZ LONG Best | 8 | 6 | +75.00% | 6 | +0.63% | 1.52 | +66.67% | take_profit=4;time_stop=2 |
| 7d | CHZ | CHZ LONG Best | 17 | 13 | +76.47% | 13 | +1.19% | 1.42 | +69.23% | take_profit=8;time_stop=5 |
| 7d | SPELL | SPELL SHORT Best | 1 | 1 | +100.00% | 1 | +0.96% | inf | +100.00% | take_profit=1 |
| 30d | CHZ | CHZ LONG Best | 40 | 30 | +75.00% | 30 | +6.06% | 2.39 | +76.67% | take_profit=22;time_stop=8 |
| 30d | SHIB | SHIB LONG Best | 11 | 6 | +54.55% | 6 | -0.40% | 0.54 | +33.33% | time_stop=6 |
| 30d | SPELL | SPELL SHORT Best | 23 | 19 | +82.61% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+7.24%`, а если продолжать торговать без остановки - `-27.66%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/monthly_cashflow_5pct_chz_shib_spell_fresh_strict_journal_2026-05-08.csv`
- Portfolio summary CSV: `data/monthly_cashflow_5pct_chz_shib_spell_fresh_strict_summary_2026-05-08.csv`
- Module summary CSV: `data/monthly_cashflow_5pct_chz_shib_spell_fresh_strict_modules_2026-05-08.csv`
