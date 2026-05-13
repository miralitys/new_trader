# RIF Regime Scan All Binance

Generated: 2026-05-08T01:55:11.809524+00:00

Проверка применяет фиксированную механику `RIF Regime Monitor` ко всем активным Binance USD-M USDT futures из inventory.

Фиксированная стратегия: `LONG th50 wide TP 1.2% SL 4% time-stop 90m`, strict maker `0.05%`, fee `0.02%`, slippage `0`.
Gate: торговать только если прошлые 30d и 60d проходят health-check. Defensive версия добавляет weekly kill `2%`.

## Counts

| Decision | Count |
|---|---:|
| reject | 1 |

## Top Candidates

| Symbol | Decision | Active Days 730 | Always 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|

## Strong Rejected By Risk Filter

| Symbol | Active Days 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `1000BONKUSDT` | 53 | -32.61% | 32.61% | 0.75 | -17.51% | 17.51% | 0.62 |

## Files

- Summary CSV: `data/_overnight_debug_one.csv`
