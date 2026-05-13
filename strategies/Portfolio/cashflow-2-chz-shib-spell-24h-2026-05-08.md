# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-09T00:32:40.796096+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 6 | +0.62% | $1006.19 | $6.19 | no | +0.95% | 1.51 | +66.67% | period_end | CHZ=6 |
| 1d | cashflow_stop | 6 | +0.62% | $1006.19 | $6.19 | no | +0.95% | 1.51 | +66.67% | period_end | CHZ=6 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | CHZ | CHZ LONG Best | 8 | 6 | +75.00% | 6 | +0.63% | 1.52 | +66.67% | take_profit=4;time_stop=2 |

## Человеческий вывод

Кандидат не добрал `$50+` в окнах: 1d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow2_chz_shib_spell_24h_journal_2026-05-08.csv`
- Portfolio summary CSV: `data/cashflow2_chz_shib_spell_24h_summary_2026-05-08.csv`
- Module summary CSV: `data/cashflow2_chz_shib_spell_24h_modules_2026-05-08.csv`
