#!/usr/bin/env python3
"""Search adapted RIF-like variants for 5m and 1h.

This is a conservative adaptation layer. The original minute strategy used a
fixed LONG th50 wide TP 1.2% SL 4% T90 setup. On higher intervals that exact
shape often produces too few signals or bad timing, so this script searches a
small, explicit grid over threshold/regime/TP/SL/time-stop while keeping maker
execution, fees, no slippage, and no future leakage.
"""

import argparse
import csv
import importlib.util
import math
import os
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0
DEFAULT_SYMBOLS = ["RIFUSDT", "MOVRUSDT"]
DEFAULT_INTERVALS = ["5m", "1h"]
WINDOWS = [1, 7, 30, 60, 90, 180, 365]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    return f"{float(value):+.2f}%"


def fmt_num(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_ok(row, regime):
    if regime == "off":
        return True
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


def score_row(row, direction, volume_multiplier, atr_min_pct, atr_max_pct):
    score = 0.0
    if direction == "long":
        if row.get("ema200") is not None and row.get("ema20") is not None and row.get("ema50") is not None:
            if row["close"] > row["ema200"] and row["ema20"] > row["ema50"]:
                score += 25.0
        if row.get("recent_high20") is not None and row["close"] > row["recent_high20"]:
            score += 25.0
        if row.get("volume_sma20") is not None and row["volume"] > row["volume_sma20"] * volume_multiplier:
            score += 20.0
        if row.get("atr_pct") is not None and atr_min_pct <= row["atr_pct"] <= atr_max_pct:
            score += 15.0
        if row.get("body_ratio", 0.0) > 0.60 and row["close"] > row["open"]:
            score += 15.0
        return score

    if row.get("ema200") is not None and row.get("ema20") is not None and row.get("ema50") is not None:
        if row["close"] < row["ema200"] and row["ema20"] < row["ema50"]:
            score += 25.0
    if row.get("recent_low20") is not None and row["close"] < row["recent_low20"]:
        score += 25.0
    if row.get("volume_sma20") is not None and row["volume"] > row["volume_sma20"] * volume_multiplier:
        score += 20.0
    if row.get("atr_pct") is not None and atr_min_pct <= row["atr_pct"] <= atr_max_pct:
        score += 15.0
    if row.get("body_ratio", 0.0) > 0.60 and row["close"] < row["open"]:
        score += 15.0
    return score


def smart_long_ok(row):
    if row.get("ema20") is None or row["close"] > row["ema20"] * 1.010:
        return False
    if row.get("upper_wick_ratio", 0.0) > 0.35:
        return False
    return True


def apply_variant_signals(rows, variant):
    for row in rows:
        row["long_signal"] = False
        row["short_signal"] = False
        if not regime_ok(row, variant["regime"]):
            continue
        score = score_row(
            row,
            variant["direction"],
            variant["volume_multiplier"],
            variant["atr_min_pct"],
            variant["atr_max_pct"],
        )
        if score < variant["threshold"]:
            continue
        if variant["direction"] == "long":
            row["long_signal"] = smart_long_ok(row)
        else:
            row["short_signal"] = True


def make_args(multi, reinvest, variant, symbol, interval):
    template = "10" if variant["direction"] == "long" else "7.3"
    args = multi.make_strategy_args(reinvest, template, symbol)
    args.symbol = symbol
    args.interval = interval
    args.direction = variant["direction"]
    args.position_pct = 1.0
    args.fee_pct = 0.0002
    args.slippage_pct = 0.0
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0005
    args.limit_entry_timeout_min = 1
    args.daily_loss_stop_pct = 0.02
    args.weekly_loss_stop_pct = variant["weekly_loss_stop_pct"]
    args.time_stop_min = variant["time_stop_min"]
    args.long_time_stop_min = variant["time_stop_min"] if variant["direction"] == "long" else None
    args.short_time_stop_min = variant["time_stop_min"] if variant["direction"] == "short" else None
    args.long_tp_pct = variant["tp_pct"]
    args.long_sl_pct = variant["sl_pct"]
    args.short_tp_pct = variant["tp_pct"]
    args.short_sl_pct = variant["sl_pct"]
    return args


def run_variant_window(bt, multi, reinvest, candles, symbol, interval, variant, period):
    per_day = bt.candles_per_day(interval)
    bars = period * per_day
    if len(candles) < bars:
        return None
    rows = [dict(row) for row in candles[-bars:]]
    apply_variant_signals(rows, variant)
    args = make_args(multi, reinvest, variant, symbol, interval)
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return {
        "period_days": period,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "profit_factor": summary["profit_factor"],
        "win_rate_pct": summary["win_rate_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
        "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
    }


def score_candidate(metrics_by_period):
    def metric(period, key, default=0.0):
        row = metrics_by_period.get(period)
        if not row:
            return default
        return float(row.get(key, default) or default)

    windows = [30, 60, 90, 180, 365]
    positive = sum(1 for period in windows if metric(period, "return_pct") > 0)
    active = sum(1 for period in windows if metric(period, "trades") >= 5)
    ret365 = metric(365, "return_pct")
    dd365 = metric(365, "max_dd_pct")
    pf365 = metric(365, "profit_factor")
    ret180 = metric(180, "return_pct")
    ret90 = metric(90, "return_pct")
    ret30 = metric(30, "return_pct")
    if math.isinf(pf365):
        pf365_score = 3.0
    else:
        pf365_score = min(pf365, 3.0)
    return (
        positive * 25.0
        + active * 8.0
        + ret365 * 1.0
        + ret180 * 0.45
        + ret90 * 0.35
        + ret30 * 0.25
        + pf365_score * 15.0
        - dd365 * 1.8
    )


def variant_grid(interval, directions):
    thresholds = [40, 50, 60]
    regimes = ["base", "wide"]
    volume_multipliers = [1.5]
    atr_maxes = [0.025, 0.050]
    weekly_stops = [None, 0.02]
    if interval == "5m":
        tps = [0.010, 0.020, 0.030]
        sls = [0.040, 0.060]
        stops = [180, 360, 720]
    else:
        tps = [0.020, 0.035, 0.050]
        sls = [0.050, 0.080]
        stops = [720, 1440, 2880]
    for direction in directions:
        for threshold in thresholds:
            for regime in regimes:
                for volume_multiplier in volume_multipliers:
                    for atr_max_pct in atr_maxes:
                        for tp_pct in tps:
                            for sl_pct in sls:
                                for time_stop_min in stops:
                                    for weekly_loss_stop_pct in weekly_stops:
                                        yield {
                                            "direction": direction,
                                            "threshold": threshold,
                                            "regime": regime,
                                            "volume_multiplier": volume_multiplier,
                                            "atr_min_pct": 0.0015,
                                            "atr_max_pct": atr_max_pct,
                                            "tp_pct": tp_pct,
                                            "sl_pct": sl_pct,
                                            "time_stop_min": time_stop_min,
                                            "weekly_loss_stop_pct": weekly_loss_stop_pct,
                                        }


def variant_id(variant):
    weekly = "wk2" if variant["weekly_loss_stop_pct"] else "wk0"
    return (
        f"{variant['direction']}_th{variant['threshold']}_{variant['regime']}"
        f"_vm{variant['volume_multiplier']}_atr{variant['atr_max_pct']}"
        f"_tp{variant['tp_pct']}_sl{variant['sl_pct']}_t{variant['time_stop_min']}_{weekly}"
    )


def search_symbol_interval(bt, interval_mod, reinvest, multi, symbol, interval, args):
    fetch_days = max(WINDOWS) + args.warmup_days
    candles, start_day, end_day = interval_mod.fetch_archive_klines(symbol, interval, fetch_days, args.archive_end_day or None)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    indicator_args.interval = interval
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)
    print(f"{symbol} {interval}: candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}", flush=True)

    stage_rows = []
    candidates = []
    for index, variant in enumerate(variant_grid(interval, args.directions), start=1):
        result = run_variant_window(bt, multi, reinvest, candles, symbol, interval, variant, 365)
        if result is None:
            continue
        row = {
            "symbol": symbol,
            "interval": interval,
            "variant_id": variant_id(variant),
            **variant,
            **{f"p365_{key}": value for key, value in result.items() if key != "period_days"},
            "data_start_day": start_day.isoformat(),
            "data_end_day": end_day.isoformat(),
        }
        row["stage_score"] = score_candidate({365: result})
        stage_rows.append(row)
        if index % 500 == 0:
            print(f"  staged {index} variants", flush=True)

    filtered = [
        row
        for row in stage_rows
        if float(row["p365_return_pct"]) > 0
        and float(row["p365_profit_factor"]) >= args.min_pf
        and float(row["p365_max_dd_pct"]) <= args.max_dd
        and int(row["p365_trades"]) >= args.min_trades
    ]
    filtered.sort(key=lambda row: float(row["stage_score"]), reverse=True)
    if not filtered:
        filtered = sorted(stage_rows, key=lambda row: float(row["stage_score"]), reverse=True)[: args.top_n]
    else:
        filtered = filtered[: args.top_n]

    window_rows = []
    for rank, row in enumerate(filtered, start=1):
        variant = {
            "direction": row["direction"],
            "threshold": int(row["threshold"]),
            "regime": row["regime"],
            "volume_multiplier": float(row["volume_multiplier"]),
            "atr_min_pct": float(row["atr_min_pct"]),
            "atr_max_pct": float(row["atr_max_pct"]),
            "tp_pct": float(row["tp_pct"]),
            "sl_pct": float(row["sl_pct"]),
            "time_stop_min": int(row["time_stop_min"]),
            "weekly_loss_stop_pct": float(row["weekly_loss_stop_pct"]) if row["weekly_loss_stop_pct"] not in ("", None) else None,
        }
        metrics_by_period = {}
        for period in WINDOWS:
            result = run_variant_window(bt, multi, reinvest, candles, symbol, interval, variant, period)
            metrics_by_period[period] = result
            window_rows.append(
                {
                    "rank": rank,
                    "symbol": symbol,
                    "interval": interval,
                    "variant_id": row["variant_id"],
                    **variant,
                    **result,
                    "score": 0.0,
                    "data_start_day": start_day.isoformat(),
                    "data_end_day": end_day.isoformat(),
                }
            )
        final_score = score_candidate(metrics_by_period)
        for item in window_rows:
            if item["symbol"] == symbol and item["interval"] == interval and item["variant_id"] == row["variant_id"]:
                item["score"] = final_score
    return stage_rows, window_rows


def summarize_best(window_rows):
    grouped = {}
    for row in window_rows:
        key = (row["symbol"], row["interval"], row["variant_id"])
        grouped.setdefault(key, []).append(row)
    best = []
    for (symbol, interval, vid), rows in grouped.items():
        by_period = {int(row["period_days"]): row for row in rows}
        row365 = by_period.get(365, {})
        best.append(
            {
                "symbol": symbol,
                "interval": interval,
                "variant_id": vid,
                "direction": rows[0]["direction"],
                "threshold": rows[0]["threshold"],
                "regime": rows[0]["regime"],
                "volume_multiplier": rows[0]["volume_multiplier"],
                "atr_max_pct": rows[0]["atr_max_pct"],
                "tp_pct": rows[0]["tp_pct"],
                "sl_pct": rows[0]["sl_pct"],
                "time_stop_min": rows[0]["time_stop_min"],
                "weekly_loss_stop_pct": rows[0]["weekly_loss_stop_pct"] or "",
                "score": rows[0]["score"],
                "return_1d": by_period.get(1, {}).get("return_pct", ""),
                "return_7d": by_period.get(7, {}).get("return_pct", ""),
                "return_30d": by_period.get(30, {}).get("return_pct", ""),
                "return_60d": by_period.get(60, {}).get("return_pct", ""),
                "return_90d": by_period.get(90, {}).get("return_pct", ""),
                "return_180d": by_period.get(180, {}).get("return_pct", ""),
                "return_365d": row365.get("return_pct", ""),
                "dd_365d": row365.get("max_dd_pct", ""),
                "pf_365d": row365.get("profit_factor", ""),
                "trades_365d": row365.get("trades", ""),
            }
        )
    best.sort(key=lambda row: float(row["score"]), reverse=True)
    return best


def write_report(path, best_rows, window_path, stage_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# RIF/MOVR Interval Adaptation Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Методика: small-grid search по direction/threshold/regime/TP/SL/time-stop на 5m и 1h. Исполнение: maker limit offset 0.05%, fee 0.02%, slippage 0.",
        "",
        "| Symbol | TF | Direction | Params | 1d | 7d | 30d | 60d | 90d | 180d | 365d | DD365 | PF365 | Trades365 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in best_rows[:20]:
        params = (
            f"th{row['threshold']} {row['regime']} vm{row['volume_multiplier']} "
            f"atrMax{row['atr_max_pct']} TP{float(row['tp_pct']) * 100:.2f}% "
            f"SL{float(row['sl_pct']) * 100:.2f}% T{row['time_stop_min']} "
            f"wk{row['weekly_loss_stop_pct'] or 'off'}"
        )
        lines.append(
            f"| `{row['symbol']}` | {row['interval']} | {row['direction']} | {params} | "
            f"{fmt_pct(row['return_1d'])} | {fmt_pct(row['return_7d'])} | {fmt_pct(row['return_30d'])} | "
            f"{fmt_pct(row['return_60d'])} | {fmt_pct(row['return_90d'])} | {fmt_pct(row['return_180d'])} | "
            f"{fmt_pct(row['return_365d'])} | {fmt_num(row['dd_365d'])}% | {fmt_num(row['pf_365d'])} | {row['trades_365d']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Window CSV: `{window_path}`",
            f"- Stage CSV: `{stage_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Search adapted RIF/MOVR interval strategies.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--intervals", nargs="*", default=DEFAULT_INTERVALS, choices=["5m", "1h"])
    parser.add_argument("--directions", nargs="*", default=["long"], choices=["long", "short"])
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--min-pf", type=float, default=1.05)
    parser.add_argument("--max-dd", type=float, default=25.0)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--save-stage", default=f"data/rif_interval_adaptation_stage_{today}.csv")
    parser.add_argument("--save-windows", default=f"data/rif_interval_adaptation_windows_{today}.csv")
    parser.add_argument("--save-best", default=f"data/rif_interval_adaptation_best_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-interval-adaptation-search-{today}.md")
    args = parser.parse_args()

    interval_mod = load_module("rif_interval_windows_check", INTERVAL_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    all_stage = []
    all_windows = []
    for symbol in args.symbols:
        for interval in args.intervals:
            stage_rows, window_rows = search_symbol_interval(bt, interval_mod, reinvest, multi, symbol, interval, args)
            all_stage.extend(stage_rows)
            all_windows.extend(window_rows)

    best_rows = summarize_best(all_windows)

    stage_fields = [
        "symbol",
        "interval",
        "variant_id",
        "direction",
        "threshold",
        "regime",
        "volume_multiplier",
        "atr_min_pct",
        "atr_max_pct",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "weekly_loss_stop_pct",
        "p365_trades",
        "p365_return_pct",
        "p365_max_dd_pct",
        "p365_profit_factor",
        "p365_win_rate_pct",
        "p365_expectancy_pct",
        "stage_score",
        "data_start_day",
        "data_end_day",
    ]
    window_fields = [
        "rank",
        "symbol",
        "interval",
        "variant_id",
        "direction",
        "threshold",
        "regime",
        "volume_multiplier",
        "atr_min_pct",
        "atr_max_pct",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "weekly_loss_stop_pct",
        "period_days",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
        "score",
        "data_start_day",
        "data_end_day",
    ]
    best_fields = [
        "symbol",
        "interval",
        "variant_id",
        "direction",
        "threshold",
        "regime",
        "volume_multiplier",
        "atr_max_pct",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "weekly_loss_stop_pct",
        "score",
        "return_1d",
        "return_7d",
        "return_30d",
        "return_60d",
        "return_90d",
        "return_180d",
        "return_365d",
        "dd_365d",
        "pf_365d",
        "trades_365d",
    ]
    save_csv(os.path.join(ROOT, args.save_stage), all_stage, stage_fields)
    save_csv(os.path.join(ROOT, args.save_windows), all_windows, window_fields)
    save_csv(os.path.join(ROOT, args.save_best), best_rows, best_fields)
    write_report(args.save_report, best_rows, args.save_windows, args.save_stage)
    print(f"saved stage: {args.save_stage}")
    print(f"saved windows: {args.save_windows}")
    print(f"saved best: {args.save_best}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
