# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-12T12:32:28.474934+00:00`

Проверка фиксированного кандидата `CHZ 10% / SHIB 10% / SPELL 80%`, scale `10`, через strict maker-fill.
Monthly loss stop: `50%`. Target cash: `$50.00`.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|

## Человеческий вывод

Кандидат не добрал `$50+` в окнах: 1d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/24h_snapshot_cashflow2_chz10_shib10_spell80_journal_2026-05-12.csv`
- Portfolio summary CSV: `data/24h_snapshot_cashflow2_chz10_shib10_spell80_summary_2026-05-12.csv`
- Module summary CSV: `data/24h_snapshot_cashflow2_chz10_shib10_spell80_modules_2026-05-12.csv`
