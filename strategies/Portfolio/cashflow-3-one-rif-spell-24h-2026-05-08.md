# Cashflow 3 Fresh Strict Check

Generated: `2026-05-09T00:35:53.097410+00:00`

Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.

| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| 1d | continuous | 10 | +2.53% | $1025.26 | $25.26 | no `$100` | +0.84% | 4.00 | +90.00% | period_end | RIF=6;ONE=4 |
| 1d | cashflow_stop | 10 | +2.53% | $1025.26 | $25.26 | no `$100` | +0.84% | 4.00 | +90.00% | period_end | RIF=6;ONE=4 |

## Module Detail

| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1d | ONE | ONE 11.2 | 5 | 4 | +80.00% | 4 | +0.27% | inf | +100.00% | take_profit=4 |
| 1d | RIF | RIF 5m LONG Best | 10 | 6 | +60.00% | 6 | +3.53% | 3.79 | +83.33% | take_profit=5;time_stop=1 |

## Files

- Journal CSV: `data/cashflow3_one_rif_spell_24h_journal_2026-05-08.csv`
- Summary CSV: `data/cashflow3_one_rif_spell_24h_summary_2026-05-08.csv`
- Modules CSV: `data/cashflow3_one_rif_spell_24h_modules_2026-05-08.csv`
