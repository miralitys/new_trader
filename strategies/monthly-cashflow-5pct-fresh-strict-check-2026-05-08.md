# Fresh Strict Check - Monthly Cashflow 5%

Generated: `2026-05-08T19:28:18.588235+00:00`

Проверка фиксированного кандидата `GALA 20% / SPELL 80%`, scale `6`, через strict maker-fill.

Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.

## Portfolio Result

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 1d | cashflow_stop | 0 | +0.00% | $1000.00 | $0.00 | no | +0.00% | 0.00 | +0.00% | period_end |  |
| 7d | continuous | 41 | -0.64% | $993.55 | $0.00 | no | +1.83% | 0.81 | +90.24% | period_end | GALA=41 |
| 7d | cashflow_stop | 41 | -0.64% | $993.55 | $0.00 | no | +1.83% | 0.81 | +90.24% | period_end | GALA=41 |
| 30d | continuous | 203 | -30.53% | $694.68 | $0.00 | no | +49.71% | 0.72 | +87.68% | period_end | GALA=176;SPELL=27 |
| 30d | cashflow_stop | 42 | +8.22% | $1082.25 | $82.25 | yes | +3.66% | 2.50 | +83.33% | profit_target | GALA=39;SPELL=3 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | GALA | Минутка 11.2 | 153 | 59 | +38.56% | 41 | -0.52% | 0.82 | +90.24% | take_profit=37;time_stop=4 |
| 30d | GALA | Минутка 11.2 | 617 | 235 | +38.09% | 176 | -0.62% | 0.94 | +89.20% | take_profit=157;time_stop=17;stop_loss=2 |
| 30d | SPELL | SPELL SHORT Best | 31 | 27 | +87.10% | 27 | -4.33% | 0.82 | +77.78% | take_profit=20;stop_loss=5;time_stop=2 |

## Человеческий вывод

На `30d` видно главное: с остановкой после цели результат `+8.22%`, а если продолжать торговать без остановки - `-30.53%`. Значит profit-target shutdown является обязательной частью стратегии, а не косметикой.

Кандидат не добрал `$50+` в окнах: 1d, 7d. Это не обязательно ломает месячную идею, но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую.

## Files

- Journal CSV: `data/monthly_cashflow_5pct_fresh_strict_journal_2026-05-08.csv`
- Portfolio summary CSV: `data/monthly_cashflow_5pct_fresh_strict_summary_2026-05-08.csv`
- Module summary CSV: `data/monthly_cashflow_5pct_fresh_strict_modules_2026-05-08.csv`
