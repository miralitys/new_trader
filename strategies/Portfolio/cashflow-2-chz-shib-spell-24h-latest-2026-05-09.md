# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-09T19:15:10.448095+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 2 | +0.92% | $1009.22 | $9.22 | no | +0.00% | inf | +100.00% | period_end | CHZ=2 |
| 1d | cashflow_stop | 2 | +0.92% | $1009.22 | $9.22 | no | +0.00% | inf | +100.00% | period_end | CHZ=2 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | CHZ | CHZ LONG Best | 2 | 2 | +100.00% | 2 | +0.92% | inf | +100.00% | take_profit=2 |

## Человеческий вывод

Кандидат не добрал `$50+` в окнах: 1d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/cashflow2_chz_shib_spell_24h_latest_journal_2026-05-09.csv`
- Portfolio summary CSV: `data/cashflow2_chz_shib_spell_24h_latest_summary_2026-05-09.csv`
- Module summary CSV: `data/cashflow2_chz_shib_spell_24h_latest_modules_2026-05-09.csv`
