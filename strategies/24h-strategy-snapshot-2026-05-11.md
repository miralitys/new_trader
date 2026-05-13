# 24h Strategy Snapshot

Generated: 2026-05-11T18:00:25.096727+00:00

Этот отчет специально разделяет разные смыслы `24 часа`: обычный backtest, maker-fill paper, strict-варианты и cashflow-обертки.

Status counts: `{'OK': 25, 'WATCH': 4, 'DIAGNOSTIC': 6}`

| Layer | Fixed | Asset | Strategy | Mode | Market | Data start | Data end | Signals | Filled | Trades | Return | PF | DD | Note |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| operational_backtest | yes | ACH | ACH Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 2 | -1.64% | 0.16 | +1.94% |  |
| operational_backtest | yes | ANKR | ANKR LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | CHZ | Минутка 10 CHZ Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | DYDX | DYDX Pullback SHORT x2 Protected | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 10 | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 11.2 | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | inf | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 7.3 | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | JASMY | JASMY SHORT Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | MANA | MANA LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | ONE | Минутка 11.2 | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | inf | +0.00% |  |
| operational_backtest | yes | REZ | REZ Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | RIF | RIF Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SAND | SAND LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SHIB | SHIB LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SPELL | SPELL SHORT Best | theoretical_strategy_backtest | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| core_paper | yes | ANKR | ANKR LONG Best | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | DYDX | DYDX Pullback SHORT x2 Protected | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 10 | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 11.2 | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 7.3 | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | RIF | RIF Regime Monitor | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| core_paper | yes | SPELL | SPELL SHORT Best | maker_limit_paper_fill | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-11.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-11.md; period inferred from same-market snapshot rows |
| strict | yes | ANKR | ANKR LONG strict | strict_fixed_maker_limit | data_api_spot | 2026-05-10T18:03:00+00:00 | 2026-05-11T18:02:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | 1d trades 0 < 1; 1d return +0.00% <= 0; 1d PF 0.00 < 1.01 |
| strict | yes | CHZ | CHZ LONG strict | strict_fixed_maker_limit | data_api_spot | 2026-05-10T18:03:00+00:00 | 2026-05-11T18:02:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | 1d trades 0 < 1; 1d return +0.00% <= 0; 1d PF 0.00 < 1.01 |
| strict | yes | GALA | GALA 11.2 strict | strict_fixed_maker_limit | data_api_spot | 2026-05-10T18:04:00+00:00 | 2026-05-11T18:03:59.999000+00:00 | 36 | 15 | 11 | -0.67% | 0.37 | n/a | 1d return -0.67% <= 0; 1d PF 0.37 < 1.01 |
| strict | yes | GALA | GALA 7.3 strict | strict_fixed_maker_limit | data_api_spot | 2026-05-10T18:04:00+00:00 | 2026-05-11T18:03:59.999000+00:00 | 38 | 21 | 21 | -0.80% | 0.44 | n/a | 1d return -0.80% <= 0; 1d PF 0.44 < 1.01 |
| cashflow | yes | Portfolio | cashflow1_gala20_spell80 | cashflow_stop_maker_limit | data_api_spot | 2026-05-10T18:03:00+00:00 | 2026-05-11T18:02:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow1_gala20_spell80-2026-05-11.md; period inferred from same-market snapshot rows |
| cashflow | yes | Portfolio | cashflow2_chz10_shib10_spell80 | cashflow_stop_maker_limit | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow2_chz10_shib10_spell80-2026-05-11.md; period inferred from same-market snapshot rows |
| cashflow | yes | Portfolio | cashflow3_one_rif_spell | cashflow_stop_maker_limit | futures_archive | 2026-05-10T00:00:00+00:00 | 2026-05-10T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow3_one_rif_spell-2026-05-11.md; period inferred from same-market snapshot rows |
| diagnostic | no | GALA | GALA 11.2 base | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |
| diagnostic | no | GALA | GALA 11.2 diagnostic ret7<=25 | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 37 | 21 | 15 | -0.42% | 0.68 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |
| diagnostic | no | GALA | GALA 11.2 diagnostic ret7<=25 short score 50-79 | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 51 | 21 | 16 | +0.15% | 1.31 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |
| diagnostic | no | GALA | GALA 7.3 base | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |
| diagnostic | no | GALA | GALA 7.3 diagnostic ret7<=25 | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 25 | 14 | 14 | -0.33% | 0.66 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |
| diagnostic | no | GALA | GALA 7.3 diagnostic ret7<=25 score 50-79 | diagnostic_variant_maker_limit | data_api_spot | 2026-05-10T18:06:00+00:00 | 2026-05-11T18:05:59.999000+00:00 | 39 | 14 | 14 | +0.09% | 1.17 | n/a | not fixed; report=strategies/24h-snapshot-gala-diagnostic-2026-05-11.md |

## Files

- Snapshot CSV: `data/24h_strategy_snapshot_2026-05-11.csv`

## Reading Rules

- `operational_backtest`: обычный backtest по последнему полному дню futures archive.
- `core_paper`: лимитный paper-fill; если нет сигналов, это не значит, что другой слой тоже пустой.
- `strict`: зафиксированные strict-версии, выбранные отдельно.
- `cashflow`: портфельная cashflow-обертка с остановкой после цели/стопа.
- `diagnostic`: не зафиксированная рабочая стратегия, только проверка гипотез.
