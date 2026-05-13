#!/usr/bin/env python3
"""Search a LONG strategy derived from Minutka 7.3.

The search is intentionally small and reproducible. It keeps the Minutka 7.3
execution assumptions: maker limit entry at current price, maker fee, no
slippage, daily loss stop, and regime filters. The goal is not endless fitting,
but checking whether the 7.3 SHORT idea has a useful LONG sibling.
"""

import argparse
import csv
import importlib.util
import math
import os
from datetime import datetime
from itertools import product


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKTEST_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("gala_mb_backtest", BACKTEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args():
    parser = argparse.ArgumentParser(description="Search LONG clone of Minutka 7.3.")
    parser.add_argument("--candles-csv", default="data/strategy7_365d_candles.csv")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--position-pct", type=float, default=0.24)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--save-results", default="data/minutka_long_from_73_search.csv")
    parser.add_argument("--save-best-trades", default="data/minutka_long_from_73_best_trades.csv")
    parser.add_argument("--save-best-equity", default="data/minutka_long_from_73_best_equity.csv")
    return parser.parse_args()


FLOAT_FIELDS = {
    "open",
    "high",
    "low",
    "close",
    "volume",
    "ema20",
    "ema50",
    "ema200",
    "rsi14",
    "atr14",
    "atr_pct",
    "volume_sma20",
    "recent_high20",
    "recent_low20",
    "dist_ema200",
    "return_1d",
    "return_7d",
    "body_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "long_score",
    "short_score",
}


def iso_to_ms(value):
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def load_candles(path):
    candles = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if key in FLOAT_FIELDS:
                    parsed[key] = float(value) if value != "" else None
                elif key in {"smart_long_filter", "regime_filter_passed", "long_signal", "short_signal"}:
                    parsed[key] = value in {"1", "True", "true"}
                else:
                    parsed[key] = value
            parsed["open_time_ms"] = iso_to_ms(parsed["open_time"])
            parsed["close_time_ms"] = iso_to_ms(parsed["close_time"])
            candles.append(parsed)
    return candles


def in_range(value, min_value, max_value):
    if min_value is None and max_value is None:
        return True
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def make_bt_args(base_args, params):
    return argparse.Namespace(
        market="futures_archive",
        symbol="GALAUSDT",
        interval="1m",
        days=365,
        warmup_days=7,
        direction="long",
        initial_balance=base_args.initial_balance,
        position_pct=params["position_pct"],
        fee_pct=base_args.fee_pct,
        slippage_pct=base_args.slippage_pct,
        entry_mode="maker_limit",
        limit_entry_offset_pct=0.0,
        limit_entry_timeout_min=1,
        long_tp_pct=params["tp_pct"],
        long_sl_pct=params["sl_pct"],
        short_tp_pct=0.003,
        short_sl_pct=0.003,
        time_stop_min=params["time_stop_min"],
        long_time_stop_min=params["time_stop_min"],
        short_time_stop_min=params["time_stop_min"],
        daily_loss_stop_pct=params["daily_loss_stop_pct"],
        filter_atr_min_pct=None,
        filter_atr_max_pct=None,
        filter_dist_ema200_min=None,
        filter_dist_ema200_max=None,
        filter_return_1d_min=None,
        filter_return_1d_max=None,
        filter_return_7d_min=None,
        filter_return_7d_max=None,
        save_candles="",
        save_trades="",
        save_equity="",
        long_threshold=params["threshold"],
        short_threshold=40,
        volume_multiplier=1.5,
        atr_min_pct=0.0015,
        atr_max_pct=0.0120,
    )


def apply_signals(candles, params):
    for row in candles:
        regime_ok = (
            in_range(row.get("atr_pct"), params["atr_min"], params["atr_max"])
            and in_range(row.get("dist_ema200"), params["dist_min"], params["dist_max"])
            and in_range(row.get("return_1d"), params["return_1d_min"], params["return_1d_max"])
            and in_range(row.get("return_7d"), params["return_7d_min"], params["return_7d_max"])
        )
        row["long_signal"] = (
            row.get("long_score", 0.0) >= params["threshold"]
            and bool(row.get("smart_long_filter"))
            and regime_ok
        )
        row["short_signal"] = False


def run_window(bt, candles, params, base_args, days):
    bars = days * bt.candles_per_day("1m")
    window = candles[-bars:]
    apply_signals(window, params)
    bt_args = make_bt_args(base_args, params)
    trades, equity_curve, stats = bt.run_backtest(window, bt_args)
    summary = bt.summarize_trades(trades, base_args.initial_balance, equity_curve)
    return trades, equity_curve, stats, summary


def compact_summary(summary):
    return {
        "trades": summary["total_trades"],
        "return": summary["total_return_pct"],
        "win": summary["win_rate_pct"],
        "pf": summary["profit_factor"],
        "dd": summary["max_drawdown_pct"],
        "expectancy": summary["expectancy_pct"],
    }


def score_result(row):
    if min(row[f"return_{days}d"] for days in WINDOWS) <= 0:
        return -10**9
    if max(row[f"dd_{days}d"] for days in WINDOWS) > 25:
        return -10**8
    return (
        row["return_365d"]
        + 0.50 * row["return_90d"]
        + 12.0 * (row["pf_365d"] - 1.0)
        - 0.80 * row["dd_365d"]
        - 0.30 * max(row[f"dd_{days}d"] for days in WINDOWS)
    )


WINDOWS = [7, 30, 90, 180, 365]


REGIME_PRESETS = [
    {
        "regime": "mirror_73",
        "atr_min": 0.0025,
        "atr_max": None,
        "dist_min": -0.015,
        "dist_max": 0.015,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": -0.40,
        "return_7d_max": 0.10,
    },
    {
        "regime": "near_ema_recovery",
        "atr_min": 0.0025,
        "atr_max": None,
        "dist_min": -0.015,
        "dist_max": 0.020,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": -0.20,
        "return_7d_max": 0.20,
    },
    {
        "regime": "long_moderate_trend",
        "atr_min": 0.0020,
        "atr_max": None,
        "dist_min": -0.005,
        "dist_max": 0.040,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": -0.10,
        "return_7d_max": 0.40,
    },
    {
        "regime": "long_trend",
        "atr_min": 0.0020,
        "atr_max": None,
        "dist_min": 0.000,
        "dist_max": 0.060,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": 0.00,
        "return_7d_max": 0.60,
    },
    {
        "regime": "post_dump_bounce",
        "atr_min": 0.0025,
        "atr_max": None,
        "dist_min": -0.040,
        "dist_max": 0.020,
        "return_1d_min": -0.20,
        "return_1d_max": 0.08,
        "return_7d_min": -0.50,
        "return_7d_max": 0.15,
    },
    {
        "regime": "quiet_near_ema",
        "atr_min": 0.0015,
        "atr_max": 0.0100,
        "dist_min": -0.015,
        "dist_max": 0.025,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": -0.20,
        "return_7d_max": 0.25,
    },
]


def param_grid(position_pct):
    thresholds = [40, 50, 60]
    tps = [0.0025, 0.0028, 0.0032]
    sls = [0.030, 0.040, 0.050]
    time_stops = [90, 120, 180, 240]
    for regime, threshold, tp_pct, sl_pct, time_stop_min in product(
        REGIME_PRESETS, thresholds, tps, sls, time_stops
    ):
        params = dict(regime)
        params.update(
            {
                "threshold": threshold,
                "tp_pct": tp_pct,
                "sl_pct": sl_pct,
                "time_stop_min": time_stop_min,
                "daily_loss_stop_pct": 0.02,
                "position_pct": position_pct,
            }
        )
        yield params


def row_from_result(params, summaries):
    row = {
        "regime": params["regime"],
        "position_pct": params["position_pct"],
        "threshold": params["threshold"],
        "tp_pct": params["tp_pct"],
        "sl_pct": params["sl_pct"],
        "time_stop_min": params["time_stop_min"],
        "daily_loss_stop_pct": params["daily_loss_stop_pct"],
        "atr_min": params["atr_min"],
        "atr_max": params["atr_max"],
        "dist_min": params["dist_min"],
        "dist_max": params["dist_max"],
        "return_1d_min": params["return_1d_min"],
        "return_1d_max": params["return_1d_max"],
        "return_7d_min": params["return_7d_min"],
        "return_7d_max": params["return_7d_max"],
    }
    for days, summary in summaries.items():
        compact = compact_summary(summary)
        row[f"trades_{days}d"] = compact["trades"]
        row[f"return_{days}d"] = compact["return"]
        row[f"win_{days}d"] = compact["win"]
        row[f"pf_{days}d"] = compact["pf"]
        row[f"dd_{days}d"] = compact["dd"]
        row[f"expectancy_{days}d"] = compact["expectancy"]
    row["score"] = score_result(row)
    return row


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def format_pf(value):
    if value == math.inf:
        return "inf"
    return f"{value:.2f}"


def print_row(label, row):
    print(label)
    print(
        "  params: "
        f"regime={row['regime']}, threshold={row['threshold']}, "
        f"tp={row['tp_pct']:.4f}, sl={row['sl_pct']:.3f}, "
        f"time={row['time_stop_min']}m, position={row['position_pct']:.2f}"
    )
    for days in WINDOWS:
        print(
            f"  {days}d: trades={row[f'trades_{days}d']}, "
            f"return={row[f'return_{days}d']:.2f}%, "
            f"win={row[f'win_{days}d']:.2f}%, "
            f"PF={format_pf(row[f'pf_{days}d'])}, "
            f"DD={row[f'dd_{days}d']:.2f}%"
        )


def main():
    args = parse_args()
    bt = load_backtest_module()
    candles = load_candles(args.candles_csv)
    print(f"loaded candles: {len(candles)} from {args.candles_csv}", flush=True)
    print(f"period: {candles[0]['open_time']} .. {candles[-1]['close_time']}", flush=True)

    mirror = {
        "regime": "mirror_73",
        "atr_min": 0.0025,
        "atr_max": None,
        "dist_min": -0.015,
        "dist_max": 0.015,
        "return_1d_min": None,
        "return_1d_max": None,
        "return_7d_min": -0.40,
        "return_7d_max": 0.10,
        "threshold": 40,
        "tp_pct": 0.0028,
        "sl_pct": 0.040,
        "time_stop_min": 120,
        "daily_loss_stop_pct": 0.02,
        "position_pct": args.position_pct,
    }

    mirror_summaries = {}
    for days in WINDOWS:
        _, _, _, summary = run_window(bt, candles, mirror, args, days)
        mirror_summaries[days] = summary
    mirror_row = row_from_result(mirror, mirror_summaries)
    print_row("mirror LONG clone of 7.3:", mirror_row)
    print("", flush=True)

    rows = [mirror_row]
    for index, params in enumerate(param_grid(args.position_pct), start=1):
        if index % 50 == 0:
            print(f"checked 365d candidates: {index}", flush=True)
        summaries = {}
        # First check the long window. Only expensive full-window survivors are
        # evaluated across all shorter windows.
        _, _, _, summary365 = run_window(bt, candles, params, args, 365)
        if summary365["total_trades"] < 100:
            continue
        if summary365["total_return_pct"] <= 0:
            continue
        if summary365["profit_factor"] <= 1.0:
            continue
        if summary365["max_drawdown_pct"] > 35:
            continue
        summaries[365] = summary365

        failed = False
        for days in [7, 30, 90, 180]:
            _, _, _, summary = run_window(bt, candles, params, args, days)
            summaries[days] = summary
            if summary["total_trades"] < 5 or summary["total_return_pct"] <= -3:
                failed = True
                break
        if failed:
            continue

        rows.append(row_from_result(params, summaries))

    rows.sort(key=lambda row: row["score"], reverse=True)
    fields = list(rows[0].keys()) if rows else []
    save_csv(args.save_results, rows, fields)

    print(f"saved search results: {args.save_results}")
    print(f"candidates saved: {len(rows)}")
    for rank, row in enumerate(rows[: args.top], start=1):
        print_row(f"#{rank}", row)

    best = rows[0]
    best_params = {
        key: best[key]
        for key in [
            "regime",
            "atr_min",
            "atr_max",
            "dist_min",
            "dist_max",
            "return_1d_min",
            "return_1d_max",
            "return_7d_min",
            "return_7d_max",
            "threshold",
            "tp_pct",
            "sl_pct",
            "time_stop_min",
            "daily_loss_stop_pct",
            "position_pct",
        ]
    }
    trades, equity, _, _ = run_window(bt, candles, best_params, args, 365)
    trade_fields = [
        "direction",
        "entry_time",
        "exit_time",
        "entry",
        "exit",
        "reason",
        "gross_return_pct",
        "net_return_pct",
        "pnl",
        "duration_min",
        "equity_after",
    ]
    save_csv(args.save_best_trades, trades, trade_fields)
    save_csv(args.save_best_equity, equity, ["time", "equity"])
    print(f"saved best trades: {args.save_best_trades}")
    print(f"saved best equity: {args.save_best_equity}")


if __name__ == "__main__":
    main()
