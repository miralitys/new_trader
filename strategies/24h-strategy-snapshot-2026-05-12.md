# 24h Strategy Snapshot

Generated: 2026-05-12T12:17:11.737862+00:00

Этот отчет специально разделяет разные смыслы `24 часа`: обычный backtest, maker-fill paper, strict-варианты и cashflow-обертки.

Status counts: `{'OK': 25, 'WATCH': 2, 'PASS': 2}`

| Layer | Fixed | Asset | Strategy | Mode | Market | Data start | Data end | Signals | Filled | Trades | Return | PF | DD | Note |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| operational_backtest | yes | ACH | ACH Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | ANKR | ANKR LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | CHZ | Минутка 10 CHZ Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | DYDX | DYDX Pullback SHORT x2 Protected | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 10 | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 11.2 | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | inf | +0.00% |  |
| operational_backtest | yes | GALA | Минутка 7.3 | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | JASMY | JASMY SHORT Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | MANA | MANA LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | ONE | Минутка 11.2 | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | inf | +0.00% |  |
| operational_backtest | yes | REZ | REZ Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | RIF | RIF Regime Monitor | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SAND | SAND LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SHIB | SHIB LONG Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| operational_backtest | yes | SPELL | SPELL SHORT Best | theoretical_strategy_backtest | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% |  |
| core_paper | yes | ANKR | ANKR LONG Best | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | DYDX | DYDX Pullback SHORT x2 Protected | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 10 | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 11.2 | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | GALA | Минутка 7.3 | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | RIF | RIF Regime Monitor | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| core_paper | yes | SPELL | SPELL SHORT Best | maker_limit_paper_fill | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | summary=data/24h_snapshot_core_futures_archive_summary_2026-05-12.csv; report=strategies/24h-snapshot-core-futures_archive-2026-05-12.md; period inferred from same-market snapshot rows |
| strict | yes | ANKR | ANKR LONG strict | strict_fixed_maker_limit | data_api_spot | 2026-05-11T12:20:00+00:00 | 2026-05-12T12:19:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | 1d trades 0 < 1; 1d return +0.00% <= 0; 1d PF 0.00 < 1.01 |
| strict | yes | CHZ | CHZ LONG strict | strict_fixed_maker_limit | data_api_spot | 2026-05-11T12:20:00+00:00 | 2026-05-12T12:19:59.999000+00:00 | 0 | 0 | 0 | +0.00% | 0.00 | n/a | 1d trades 0 < 1; 1d return +0.00% <= 0; 1d PF 0.00 < 1.01 |
| strict | yes | GALA | GALA 11.2 strict | strict_fixed_maker_limit | data_api_spot | 2026-05-11T12:21:00+00:00 | 2026-05-12T12:20:59.999000+00:00 | 74 | 35 | 21 | +0.20% | 1.35 | n/a |  |
| strict | yes | GALA | GALA 7.3 strict | strict_fixed_maker_limit | data_api_spot | 2026-05-11T12:21:00+00:00 | 2026-05-12T12:20:59.999000+00:00 | 93 | 47 | 47 | +0.39% | 1.27 | n/a |  |
| cashflow | yes | Portfolio | cashflow1_gala20_spell80 | cashflow_stop_maker_limit | data_api_spot | 2026-05-11T12:20:00+00:00 | 2026-05-12T12:19:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow1_gala20_spell80-2026-05-12.md; period inferred from same-market snapshot rows |
| cashflow | yes | Portfolio | cashflow2_chz10_shib10_spell80 | cashflow_stop_maker_limit | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow2_chz10_shib10_spell80-2026-05-12.md; period inferred from same-market snapshot rows |
| cashflow | yes | Portfolio | cashflow3_one_rif_spell | cashflow_stop_maker_limit | futures_archive | 2026-05-11T00:00:00+00:00 | 2026-05-11T23:59:59.999000+00:00 |  |  | 0 | +0.00% | 0.00 | +0.00% | hit_target=False; stop=period_end; assets=; report=strategies/Portfolio/24h-snapshot-cashflow3_one_rif_spell-2026-05-12.md; period inferred from same-market snapshot rows |

## Files

- Snapshot CSV: `data/24h_strategy_snapshot_2026-05-12.csv`

## Reading Rules

- `operational_backtest`: обычный backtest по последнему полному дню futures archive.
- `core_paper`: лимитный paper-fill; если нет сигналов, это не значит, что другой слой тоже пустой.
- `strict`: зафиксированные strict-версии, выбранные отдельно.
- `cashflow`: портфельная cashflow-обертка с остановкой после цели/стопа.
- `diagnostic`: не зафиксированная рабочая стратегия, только проверка гипотез.
