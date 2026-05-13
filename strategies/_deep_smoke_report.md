# Deep Validation: Binance Hot Shortlist

Проверка берет **ровно тот setup**, который нашел быстрый Binance-wide hot-scan, и гонит его на больших окнах.

Сценарии:

- `base_maker`: maker 0.02%, лимит у текущей цены.
- `strict_maker`: maker 0.02%, лимитка засчитывается только после возврата цены на 0.05%.
- `taker_like`: fee 0.04% + slippage 0.02%, вход по следующему open.

## Status Counts

| Status | Count |
|---|---:|
| deep_pass_730 | 0 |
| deep_pass_365 | 0 |
| fresh_watch | 1 |
| maker_only_watch | 0 |
| reject_or_too_early | 0 |

## Data Counts

| Status | Count |
|---|---:|
| ok | 1 |

## Per-Symbol Summary

| Symbol | Class | Strict 30d | Strict 90d | Strict 180d | Strict 365d | Strict 730d | Taker 30d |
|---|---|---:|---:|---:|---:|---:|---:|
| `UBUSDT` | fresh_watch | +73.14% / PF 1.59 | +76.97% / PF 1.19 | n/a | n/a | n/a | +49.88% |

## Top Strict 30d

| Symbol | Direction | Period | Return | PF | DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| `UBUSDT` | long | 30 | +73.14% | 1.59 | 11.21% | 218 |

## Top Strict 365d

| Symbol | Direction | Period | Return | PF | DD | Trades |
|---|---|---:|---:|---:|---:|---:|
