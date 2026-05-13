# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-13T15:27:32.468891+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 3 | -0.86% | $991.45 | $0.00 | no | +1.11% | 0.35 | +33.33% | period_end | CHZ=3 |
| 1d | cashflow_stop | 3 | -0.86% | $991.45 | $0.00 | no | +1.11% | 0.35 | +33.33% | period_end | CHZ=3 |
| 7d | continuous | 14 | +0.16% | $1001.60 | $1.60 | no | +1.91% | 1.04 | +64.29% | period_end | CHZ=14 |
| 7d | cashflow_stop | 14 | +0.16% | $1001.60 | $1.60 | no | +1.91% | 1.04 | +64.29% | period_end | CHZ=14 |
| 30d | continuous | 59 | -27.95% | $720.50 | $0.00 | no | +67.28% | 0.69 | +69.49% | period_end | CHZ=34;SPELL=19;SHIB=6 |
| 30d | cashflow_stop | 13 | +6.75% | $1067.49 | $67.49 | yes | +0.30% | 11.20 | +76.92% | profit_target | CHZ=9;SHIB=3;SPELL=1 |
| 60d | continuous | 87 | -32.86% | $671.40 | $0.00 | no | +71.24% | 0.74 | +62.07% | period_end | CHZ=38;SPELL=30;SHIB=19 |
| 60d | cashflow_stop | 7 | +8.88% | $1088.82 | $88.82 | yes | +6.10% | 2.45 | +42.86% | profit_target | SPELL=4;SHIB=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | CHZ | CHZ LONG Best | 3 | 3 | +100.00% | 3 | -0.85% | 0.35 | +33.33% | time_stop=2;take_profit=1 |
| 7d | CHZ | CHZ LONG Best | 17 | 14 | +82.35% | 14 | +0.19% | 1.05 | +64.29% | take_profit=8;time_stop=6 |
| 30d | CHZ | CHZ LONG Best | 43 | 34 | +79.07% | 34 | +5.67% | 2.00 | +73.53% | take_profit=24;time_stop=10 |
| 30d | SHIB | SHIB LONG Best | 11 | 6 | +54.55% | 6 | -0.40% | 0.54 | +33.33% | time_stop=6 |
| 30d | SPELL | SPELL SHORT Best | 22 | 19 | +86.36% | 19 | -1.70% | 0.88 | +73.68% | take_profit=12;time_stop=4;stop_loss=3 |
| 60d | CHZ | CHZ LONG Best | 50 | 38 | +76.00% | 38 | +6.97% | 2.21 | +73.68% | take_profit=27;time_stop=11 |
| 60d | SHIB | SHIB LONG Best | 32 | 19 | +59.38% | 19 | -1.28% | 0.81 | +42.11% | time_stop=15;take_profit=4 |
| 60d | SPELL | SPELL SHORT Best | 35 | 30 | +85.71% | 30 | -2.22% | 0.88 | +60.00% | take_profit=16;time_stop=11;stop_loss=3 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+6.75%`, а если продолжать торговать без остановки - `-27.95%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

На `60d` видно главное: с остановкой после цели результат `+8.88%`, а если продолжать торговать без остановки - `-32.86%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow2_chz_shib_spell_fresh_strict_journal_2026-05-13.csv`
- Portfolio summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_summary_2026-05-13.csv`
- Module summary CSV: `data/cashflow2_chz_shib_spell_fresh_strict_modules_2026-05-13.csv`
