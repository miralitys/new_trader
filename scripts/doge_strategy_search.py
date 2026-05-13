#!/usr/bin/env python3
"""Search a small no-leverage score-based strategy variant.

This is intentionally constrained:
- position_pct <= 1.0, so no leverage;
- the entry signal family stays close to the existing Minutka score logic;
- candidates must be checked on 7/30/60/90/180/365 day windows.
"""

import csv
import importlib.util
import math
import os
import time
import argparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

SYMBOL = "DOGEUSDT"
WINDOWS = [7, 30, 60, 90, 180, 365]
INITIAL_BALANCE = 1000.0


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_ok(row, regime):
    if regime == "base":
        return (
            in_range(row.get("atr_pct"), 0.0025, None)
            and in_range(row.get("dist_ema200"), -0.015, 0.015)
            and in_range(row.get("return_7d"), -0.40, 0.10)
        )
    if regime == "wide":
        return (
            in_range(row.get("atr_pct"), 0.0025, None)
            and in_range(row.get("dist_ema200"), -0.025, 0.025)
            and in_range(row.get("return_7d"), -0.50, 0.20)
        )
    raise ValueError(regime)


def apply_signals(rows, direction, threshold, regime):
    for row in rows:
        passed = regime_ok(row, regime)
        row["long_signal"] = False
        row["short_signal"] = False
        if direction == "long":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= threshold
                and bool(row.get("smart_long_filter"))
                and passed
            )
        elif direction == "short":
            row["short_signal"] = row.get("short_score", 0.0) >= threshold and passed
        else:
            raise ValueError(direction)


def make_args(multi, reinvest, direction, position_pct, tp_pct, sl_pct, time_stop_min):
    template = "10" if direction == "long" else "7.3"
    args = multi.make_strategy_args(reinvest, template, SYMBOL)
    args.direction = direction
    args.position_pct = position_pct
    args.fee_pct = 0.0002
    args.slippage_pct = 0.0
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0
    args.limit_entry_timeout_min = 1
    args.daily_loss_stop_pct = 0.02
    args.time_stop_min = time_stop_min
    args.long_time_stop_min = time_stop_min if direction == "long" else None
    args.short_time_stop_min = time_stop_min if direction == "short" else None
    if direction == "long":
        args.long_tp_pct = tp_pct
        args.long_sl_pct = sl_pct
    else:
        args.short_tp_pct = tp_pct
        args.short_sl_pct = sl_pct
    return args


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def run_variant(bt, multi, reinvest, base_windows, period, variant):
    rows = [dict(row) for row in base_windows[period]]
    apply_signals(rows, variant["direction"], variant["threshold"], variant["regime"])
    args = make_args(
        multi,
        reinvest,
        variant["direction"],
        variant["position_pct"],
        variant["tp_pct"],
        variant["sl_pct"],
        variant["time_stop_min"],
    )
    trades, equity, _ = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return trades, equity, summary


def flat_row(variant, period, summary):
    reasons = summary["exit_reasons"]
    return {
        **variant,
        "period": f"{period}d",
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "avg_win_pct": summary["avg_win_pct"],
        "avg_loss_pct": summary["avg_loss_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "final_equity": summary["final_equity"],
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "end_of_data": reasons["end_of_data"],
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fetch_candles(multi):
    last_error = None
    for attempt in range(4):
        try:
            return multi.fetch_klines_fast(SYMBOL, 365, 7)
        except Exception as exc:
            last_error = exc
            print(f"fetch failed attempt {attempt + 1}: {exc}")
            time.sleep(2 * (attempt + 1))
    raise last_error


def main():
    global SYMBOL

    parser = argparse.ArgumentParser(description="Search/refine no-leverage score-based strategy variants.")
    parser.add_argument("--symbol", default=SYMBOL)
    parser.add_argument("--output-prefix", default="")
    parser.add_argument("--stress-only", action="store_true")
    parser.add_argument("--stress-direction", default="short", choices=["long", "short"])
    parser.add_argument("--stress-threshold", type=int, default=50)
    parser.add_argument("--stress-regime", default="base", choices=["base", "wide"])
    parser.add_argument("--stress-position-pct", type=float, default=0.50)
    parser.add_argument("--stress-tp-pct", type=float, default=0.0100)
    parser.add_argument("--stress-sl-pct", type=float, default=0.04)
    parser.add_argument("--stress-time-stop-min", type=int, default=120)
    args = parser.parse_args()
    SYMBOL = args.symbol.upper()
    output_prefix = args.output_prefix or SYMBOL.lower().replace("usdt", "")

    def output_path(suffix):
        return os.path.join(ROOT, "data", f"{output_prefix}_{suffix}.csv")

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    candles, _, _ = fetch_candles(multi)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", SYMBOL)
    bt.add_indicators_and_signals(candles, indicator_args)
    print(f"candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}")

    base_windows = {}
    for period in WINDOWS:
        bars = period * bt.candles_per_day("1m")
        base_windows[period] = candles[-bars:]

    if args.stress_only:
        variant = {
            "symbol": SYMBOL,
            "direction": args.stress_direction,
            "threshold": args.stress_threshold,
            "regime": args.stress_regime,
            "position_pct": args.stress_position_pct,
            "tp_pct": args.stress_tp_pct,
            "sl_pct": args.stress_sl_pct,
            "time_stop_min": args.stress_time_stop_min,
        }
        scenarios = [
            ("base_fee002_slip0", 0.0002, 0.0),
            ("fee004_slip0", 0.0004, 0.0),
            ("fee004_slip001", 0.0004, 0.0001),
        ]
        rows = []
        for scenario, fee_pct, slippage_pct in scenarios:
            for period in WINDOWS:
                test_variant = dict(variant)
                rows_for_period = [dict(row) for row in base_windows[period]]
                apply_signals(
                    rows_for_period,
                    test_variant["direction"],
                    test_variant["threshold"],
                    test_variant["regime"],
                )
                run_args = make_args(
                    multi,
                    reinvest,
                    test_variant["direction"],
                    test_variant["position_pct"],
                    test_variant["tp_pct"],
                    test_variant["sl_pct"],
                    test_variant["time_stop_min"],
                )
                run_args.fee_pct = fee_pct
                run_args.slippage_pct = slippage_pct
                trades, equity, _ = bt.run_backtest(rows_for_period, run_args)
                summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
                row = flat_row(test_variant, period, summary)
                row["scenario"] = scenario
                row["fee_pct"] = fee_pct
                row["slippage_pct"] = slippage_pct
                rows.append(row)
                print(
                    f"{scenario} {period}d: "
                    f"ret={row['return_pct']:+.2f}% DD={row['max_dd_pct']:.2f}% "
                    f"PF={row['profit_factor']:.2f} win={row['win_rate_pct']:.2f}%"
                )
        save_csv(
            output_path("strategy_stress"),
            rows,
            list(rows[0].keys()),
        )
        return

    variants = []
    for direction, thresholds in (("short", [40, 50, 60]), ("long", [50, 60, 70])):
        for threshold in thresholds:
            for regime in ("base", "wide"):
                for tp_pct in (0.0035, 0.0050, 0.0070, 0.0100, 0.0120):
                    for time_stop_min in (60, 90, 120, 180):
                        variants.append(
                            {
                                "symbol": SYMBOL,
                                "direction": direction,
                                "threshold": threshold,
                                "regime": regime,
                                "position_pct": 1.0,
                                "tp_pct": tp_pct,
                                "sl_pct": 0.04,
                                "time_stop_min": time_stop_min,
                            }
                        )

    first_pass = []
    for index, variant in enumerate(variants, start=1):
        _, _, summary = run_variant(bt, multi, reinvest, base_windows, 365, variant)
        row = flat_row(variant, 365, summary)
        first_pass.append(row)
        if index % 12 == 0:
            print(f"first pass {index}/{len(variants)}")

    first_pass.sort(
        key=lambda row: (
            row["return_pct"],
            row["profit_factor"],
            -row["max_dd_pct"],
        ),
        reverse=True,
    )
    save_csv(
        output_path("strategy_search_365"),
        first_pass,
        list(first_pass[0].keys()),
    )

    top_variants = []
    seen = set()
    for row in first_pass:
        if row["trades"] < 50:
            continue
        key = (
            row["direction"],
            row["threshold"],
            row["regime"],
            row["tp_pct"],
            row["sl_pct"],
            row["time_stop_min"],
        )
        if key in seen:
            continue
        seen.add(key)
        top_variants.append({key: row[key] for key in variants[0].keys()})
        if len(top_variants) >= 30:
            break

    full_rows = []
    for variant in top_variants:
        period_rows = []
        for period in WINDOWS:
            _, _, summary = run_variant(bt, multi, reinvest, base_windows, period, variant)
            row = flat_row(variant, period, summary)
            period_rows.append(row)
            full_rows.append(row)
        valid = all(row["return_pct"] > 0 for row in period_rows)
        print(
            f"full {variant['direction']} thr={variant['threshold']} {variant['regime']} "
            f"tp={variant['tp_pct'] * 100:.2f}% t={variant['time_stop_min']} "
            f"365={period_rows[-1]['return_pct']:+.2f}% "
            f"dd={period_rows[-1]['max_dd_pct']:.2f}% valid={valid}"
        )

    save_csv(
        output_path("strategy_search_full"),
        full_rows,
        list(full_rows[0].keys()) if full_rows else list(first_pass[0].keys()),
    )

    valid_groups = []
    for variant in top_variants:
        rows = [
            row
            for row in full_rows
            if all(row[field] == variant[field] for field in variant.keys())
        ]
        if len(rows) != len(WINDOWS):
            continue
        if all(row["return_pct"] > 0 for row in rows):
            row365 = next(row for row in rows if row["period"] == "365d")
            valid_groups.append(
                {
                    **variant,
                    "return_365d_pct": row365["return_pct"],
                    "max_dd_365d_pct": row365["max_dd_pct"],
                    "win_rate_365d_pct": row365["win_rate_pct"],
                    "profit_factor_365d": row365["profit_factor"],
                    "expectancy_365d_pct": row365["expectancy_pct"],
                    "trades_365d": row365["trades"],
                    "max_dd_any_pct": max(row["max_dd_pct"] for row in rows),
                    "min_return_any_pct": min(row["return_pct"] for row in rows),
                }
            )

    if valid_groups:
        valid_groups.sort(
            key=lambda row: (
                row["return_365d_pct"],
                row["profit_factor_365d"],
                -row["max_dd_any_pct"],
            ),
            reverse=True,
        )
        save_csv(
            output_path("strategy_search_valid"),
            valid_groups,
            list(valid_groups[0].keys()),
        )
        print("best valid:", valid_groups[0])

        best = valid_groups[0]
        position_rows = []
        for position_pct in (0.25, 0.35, 0.50, 0.65, 0.75, 1.00):
            variant = {
                "symbol": SYMBOL,
                "direction": best["direction"],
                "threshold": best["threshold"],
                "regime": best["regime"],
                "position_pct": position_pct,
                "tp_pct": best["tp_pct"],
                "sl_pct": best["sl_pct"],
                "time_stop_min": best["time_stop_min"],
            }
            rows = []
            for period in WINDOWS:
                _, _, summary = run_variant(bt, multi, reinvest, base_windows, period, variant)
                rows.append(flat_row(variant, period, summary))
            row365 = next(row for row in rows if row["period"] == "365d")
            output = {
                **variant,
                "return_7d_pct": next(row for row in rows if row["period"] == "7d")["return_pct"],
                "return_30d_pct": next(row for row in rows if row["period"] == "30d")["return_pct"],
                "return_60d_pct": next(row for row in rows if row["period"] == "60d")["return_pct"],
                "return_90d_pct": next(row for row in rows if row["period"] == "90d")["return_pct"],
                "return_180d_pct": next(row for row in rows if row["period"] == "180d")["return_pct"],
                "return_365d_pct": row365["return_pct"],
                "max_dd_7d_pct": next(row for row in rows if row["period"] == "7d")["max_dd_pct"],
                "max_dd_30d_pct": next(row for row in rows if row["period"] == "30d")["max_dd_pct"],
                "max_dd_60d_pct": next(row for row in rows if row["period"] == "60d")["max_dd_pct"],
                "max_dd_90d_pct": next(row for row in rows if row["period"] == "90d")["max_dd_pct"],
                "max_dd_180d_pct": next(row for row in rows if row["period"] == "180d")["max_dd_pct"],
                "max_dd_365d_pct": row365["max_dd_pct"],
                "max_dd_any_pct": max(row["max_dd_pct"] for row in rows),
                "min_return_any_pct": min(row["return_pct"] for row in rows),
                "trades_365d": row365["trades"],
                "win_rate_365d_pct": row365["win_rate_pct"],
                "profit_factor_365d": row365["profit_factor"],
                "expectancy_365d_pct": row365["expectancy_pct"],
            }
            position_rows.append(output)
            print(
                f"position {position_pct:.2f}: "
                f"365={output['return_365d_pct']:+.2f}% "
                f"maxDDany={output['max_dd_any_pct']:.2f}% "
                f"PF={output['profit_factor_365d']:.2f}"
            )
        save_csv(
            output_path("strategy_position_sweep"),
            position_rows,
            list(position_rows[0].keys()),
        )
    else:
        print("No all-window-positive DOGE variant found in this constrained search.")


if __name__ == "__main__":
    main()
