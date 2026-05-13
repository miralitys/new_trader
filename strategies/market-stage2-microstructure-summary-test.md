# Market Stage-2 Microstructure Scan

Generated UTC: `2026-05-08T23:30:49.136874+00:00`.

Universe: `leader + hot_wave + wave_watch` from the stage-1 market structure scan.

## Summary

- Symbols scanned: `10`
- deep_test_leader: `2`
- deep_test_wave: `4`
- monitor: `3`
- reject_execution: `1`

## Deep Test Candidates

| # | Symbol | Market | Stage2 | S2 | 1d | 7d | 30d | Vol7d/day | Thin<$1k | Range7d | Spikes>2% |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `GWEIUSDT` | hot_wave | deep_test_wave | 89.45 | -3.2323% | 20.2063% | 128.1355% | 13279156.51 | 16.131% | 13.4091% | 9 |
| 2 | `CFGUSDT` | hot_wave | deep_test_wave | 89.22 | 5.9963% | 44.2289% | 64.3424% | 23570411.2 | 27.371% | 14.7217% | 8 |
| 3 | `INTCUSDT` | hot_wave | deep_test_wave | 86.87 | -2.493% | 15.6861% | 97.4125% | 46382156.73 | 21.9643% | 8.1165% | 0 |
| 4 | `STGUSDT` | hot_wave | deep_test_wave | 67.8 | -2.5689% | 19.6752% | 20.0093% | 3224343.54 | 62.004% | 8.2579% | 0 |
| 5 | `CHZUSDT` | leader | deep_test_leader | 65.8 | 2.3704% | 6.8656% | 11.4062% | 22191877.08 | 3.5913% | 5.5611% | 0 |
| 6 | `MORPHOUSDT` | leader | deep_test_leader | 65.8 | -6.4608% | 4.8672% | 19.9451% | 11245454.13 | 24.3155% | 6.7319% | 0 |

## Monitor Candidates

| # | Symbol | Market | Stage2 | S2 | 1d | 7d | 30d | Vol7d/day | Thin<$1k | Range7d | Spikes>2% |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `RIFUSDT` | hot_wave | monitor | 77.5 | 12.0457% | 9.3619% | 68.0528% | 2443722.58 | 59.7123% | 13.0132% | 1 |
| 2 | `JSTUSDT` | hot_wave | monitor | 62.31 | 5.6792% | -3.2414% | 36.0715% | 6126836.8 | 35.0397% | 7.4744% | 3 |
| 3 | `GUAUSDT` | hot_wave | monitor | 57.82 | -5.3978% | 0.7852% | 82.8389% | 11015301.79 | 23.998% | 19.6357% | 40 |

## Rejected By Execution/Microstructure

| # | Symbol | Market | Stage2 | S2 | 1d | 7d | 30d | Vol7d/day | Thin<$1k | Range7d | Spikes>2% |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `BCHUSDT` | leader | reject_execution | 40.17 | -3.33% | 2.1082% | 0.9785% | 79831857.32 | 1.6071% | 3.7181% | 1 |

## Human Read

- `deep_test_leader` means the symbol was already structurally strong and passed recent execution filters.
- `deep_test_wave` means it is hot now and still tradable enough to test deeply.
- `monitor` means worth watching, but not first priority.
- `reject_execution` usually means volume is too thin or too many tiny candles for realistic execution.
