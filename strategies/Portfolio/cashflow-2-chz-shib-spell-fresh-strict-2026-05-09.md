# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-09T15:12:37.588514+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 2 | +0.92% | $1009.22 | $9.22 | no | +0.00% | inf | +100.00% | period_end | CHZ=2 |
| 1d | cashflow_stop | 2 | +0.92% | $1009.22 | $9.22 | no | +0.00% | inf | +100.00% | period_end | CHZ=2 |
| 7d | continuous | 16 | +9.95% | $1099.47 | $99.47 | yes | +1.91% | 4.26 | +75.00% | period_end | CHZ=15;SPELL=1 |
| 7d | cashflow_stop | 1 | +7.68% | $1076.82 | $76.82 | yes | +0.00% | inf | +100.00% | profit_target | SPELL=1 |
| 30d | continuous | 56 | -27.33% | $726.72 | $0.00 | no | +67.28% | 0.70 | +71.43% | period_end | CHZ=31;SPELL=19;SHIB=6 |
| 30d | cashflow_stop | 13 | +6.75% | $1067.49 | $67.49 | yes | +0.30% | 11.20 | +76.92% | profit_target | CHZ=9;SHIB=3;SPELL=1 |
| 60d | continuous | 98 | -31.19% | $688.07 | $0.00 | no | +71.24% | 0.77 | +63.27% | period_end | CHZ=36;SHIB=32;SPELL=30 |
| 60d | cashflow_stop | 21 | +10.63% | $1106.31 | $106.31 | yes | +7.19% | 1.80 | +57.14% | profit_target | SHIB=16;SPELL=4;CHZ=1 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | CHZ | CHZ LONG Best | 2 | 2 | +100.00% | 2 | +0.92% | inf | +100.00% | take_profit=2 |
| 7d | CHZ | CHZ LONG Best | 19 | 15 | +78.95% | 15 | +2.11% | 1.75 | +73.33% | take_profit=10;time_stop=5 |
| 7d | SPELL | SPELL SHORT Best | 1 | 1 | +100.00% | 1 | +0.96% | inf | +100.00% | take_profit=1 |
| 30d | CHZ | CHZ LONG Best | 41 | 31 | +75.61% | 31 | +6.52% | 2.49 | +77.42% | take_profit=23;time_stop=8 |
| 30d | SHIB | SHIB LONG Best | 11 | 6 | +54.55% | 6 | -0.40% | 0.54 | +33.33% | time_stop=6 |
| 30d | SPELL | SPELL SHORT Best | 23 | 19 | +82.61% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | CHZ | CHZ LONG Best | 48 | 36 | +75.00% | 36 | +7.08% | 2.37 | +75.00% | take_profit=26;time_stop=10 |
| 60d | SHIB | SHIB LONG Best | 49 | 32 | +65.31% | 32 | +1.20% | 1.09 | +53.12% | time_stop=20;take_profit=11;stop_loss=1 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+6.75%`, а если продолжать торговать без остановки - `-27.33%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+10.63%`, а если продолжать торговать без остановки - `-31.19%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow2_chz_shib_spell_fresh_strict_journal_2026-05-09.csv`
- Portfolio summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_summary_2026-05-09.csv`
- Module summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_modules_2026-05-09.csv`
