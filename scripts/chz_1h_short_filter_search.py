#!/usr/bin/env python3
"""Search activation filters for the CHZ 1h SHORT candidate."""

import argparse
import csv
import importlib.util
import math
import os
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_FETCH_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
SCENARIOS = [
    {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0},
    {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005},
    {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0},
]
BASE_VARIANT = {
    "direction": "short",
    "threshold": 50,
    "regime": "base",
    "volume_multiplier": 1.5,
    "atr_min_pct": 0.0015,
    "atr_max_pct": 0.025,
    "tp_pct": 0.050,
    "sl_pct": 0.050,
    "time_stop_min": 1440,
    "weekly_loss_stop_pct": 0.02,
}


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


def fmt_pct(value, signed=True):
    if value in ("", None):
        return "n/a"
    value = float(value)
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def add_return_30d(candles, interval_fetch, bt):
    per_day = bt.candles_per_day("1h")
    lookback = 30 * per_day
    for index, row in enumerate(candles):
        if index < lookback:
            row["return_30d"] = None
            continue
        prev = candles[index - lookback]["close"]
        row["return_30d"] = row["close"] / prev - 1.0 if prev else None


def in_range(value, low, high):
    if value is None:
        return False
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def filter_id(config):
    return (
        f"th{config['threshold']}_r7{config['ret7_min']}..{config['ret7_max']}"
        f"_r30{config['ret30_min']}..{config['ret30_max']}"
        f"_dist{config['dist_min']}..{config['dist_max']}"
        f"_trend{int(config['require_trend'])}_rsi{config['rsi_min']}..{config['rsi_max']}"
        f"_red{int(config['require_red'])}"
    )


def passes_extra(row, config):
    if not in_range(row.get("return_7d"), config["ret7_min"], config["ret7_max"]):
        return False
    if not in_range(row.get("return_30d"), config["ret30_min"], config["ret30_max"]):
        return False
    if not in_range(row.get("dist_ema200"), config["dist_min"], config["dist_max"]):
        return False
    if not in_range(row.get("rsi14"), config["rsi_min"], config["rsi_max"]):
        return False
    if config["require_trend"]:
        if not (
            row.get("ema20") is not None
            and row.get("ema50") is not None
            and row.get("ema200") is not None
            and row["close"] < row["ema200"]
            and row["ema20"] < row["ema50"]
        ):
            return False
    if config["require_red"] and row["close"] >= row["open"]:
        return False
    return True


def apply_config(adapt, candles, config):
    rows = [dict(row) for row in candles]
    variant = dict(BASE_VARIANT)
    variant["threshold"] = config["threshold"]
    adapt.apply_variant_signals(rows, variant)
    for row in rows:
        if row.get("short_signal") and not passes_extra(row, config):
            row["short_signal"] = False
    return rows


def make_args(multi, reinvest, config, scenario):
    variant = dict(BASE_VARIANT)
    variant["threshold"] = config["threshold"]
    args = multi.make_strategy_args(reinvest, "7.3", "CHZUSDT")
    args.symbol = "CHZUSDT"
    args.interval = "1h"
    args.direction = "short"
    args.position_pct = 1.0
    args.fee_pct = scenario["fee_pct"]
    args.slippage_pct = scenario["slippage_pct"]
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0005
    args.limit_entry_timeout_min = 1
    args.daily_loss_stop_pct = 0.02
    args.weekly_loss_stop_pct = variant["weekly_loss_stop_pct"]
    args.time_stop_min = variant["time_stop_min"]
    args.long_time_stop_min = None
    args.short_time_stop_min = variant["time_stop_min"]
    args.long_tp_pct = variant["tp_pct"]
    args.long_sl_pct = variant["sl_pct"]
    args.short_tp_pct = variant["tp_pct"]
    args.short_sl_pct = variant["sl_pct"]
    return args


def run_rows(bt, multi, reinvest, rows, config, scenario):
    args = make_args(multi, reinvest, config, scenario)
    args.initial_balance = INITIAL_BALANCE
    trades, equity_curve, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity_curve)
    return summary, stats


def evaluate_period(bt, adapt, multi, reinvest, candles, config, scenario, period):
    per_day = bt.candles_per_day("1h")
    rows = apply_config(adapt, candles[-period * per_day :], config)
    summary, stats = run_rows(bt, multi, reinvest, rows, config, scenario)
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


def candidate_grid():
    ret7_ranges = [
        (-0.40, 0.10),
        (-0.40, 0.05),
        (-0.30, 0.05),
        (-0.20, 0.05),
        (-0.40, 0.00),
        (-0.30, 0.00),
        (-0.20, 0.00),
        (-0.15, 0.05),
    ]
    ret30_ranges = [
        (None, None),
        (-0.50, 0.30),
        (-0.30, 0.20),
        (-0.20, 0.10),
        (-0.20, 0.05),
        (-0.10, 0.10),
    ]
    dist_ranges = [
        (-0.015, 0.015),
        (-0.020, 0.005),
        (-0.020, 0.000),
        (-0.015, 0.000),
        (-0.010, 0.005),
    ]
    rsi_ranges = [
        (None, None),
        (35.0, 65.0),
        (40.0, 65.0),
        (35.0, 60.0),
        (40.0, 60.0),
    ]
    for threshold in (50, 60):
        for ret7_min, ret7_max in ret7_ranges:
            for ret30_min, ret30_max in ret30_ranges:
                for dist_min, dist_max in dist_ranges:
                    for require_trend in (False, True):
                        for rsi_min, rsi_max in rsi_ranges:
                            for require_red in (False, True):
                                yield {
                                    "threshold": threshold,
                                    "ret7_min": ret7_min,
                                    "ret7_max": ret7_max,
                                    "ret30_min": ret30_min,
                                    "ret30_max": ret30_max,
                                    "dist_min": dist_min,
                                    "dist_max": dist_max,
                                    "require_trend": require_trend,
                                    "rsi_min": rsi_min,
                                    "rsi_max": rsi_max,
                                    "require_red": require_red,
                                }


def score(stage):
    return (
        (1 if stage["ret_7d"] >= 0 else 0) * 60
        + (1 if stage["ret_30d"] >= 0 else 0) * 80
        + stage["ret_730d"] * 0.35
        + stage["ret_365d"] * 0.25
        + min(stage["pf_730d"], 3.0) * 18
        - stage["dd_730d"] * 2.2
        + min(stage["trades_730d"], 160) * 0.08
    )


def stage_search(bt, adapt, multi, reinvest, candles, top_keep):
    rows = []
    base = SCENARIOS[0]
    for index, config in enumerate(candidate_grid(), start=1):
        metrics = {}
        for period in (7, 30, 365, 730):
            metrics[period] = evaluate_period(bt, adapt, multi, reinvest, candles, config, base, period)
        row = {
            "filter_id": filter_id(config),
            **config,
            "ret_7d": metrics[7]["return_pct"],
            "trades_7d": metrics[7]["trades"],
            "ret_30d": metrics[30]["return_pct"],
            "trades_30d": metrics[30]["trades"],
            "ret_365d": metrics[365]["return_pct"],
            "dd_365d": metrics[365]["max_dd_pct"],
            "pf_365d": metrics[365]["profit_factor"],
            "trades_365d": metrics[365]["trades"],
            "ret_730d": metrics[730]["return_pct"],
            "dd_730d": metrics[730]["max_dd_pct"],
            "pf_730d": metrics[730]["profit_factor"],
            "trades_730d": metrics[730]["trades"],
        }
        row["score"] = score(row)
        rows.append(row)
        if index % 1000 == 0:
            print(f"searched {index}", flush=True)
    rows.sort(
        key=lambda row: (
            row["ret_7d"] >= 0,
            row["ret_30d"] >= 0,
            row["ret_730d"] > 0,
            row["pf_730d"],
            -row["dd_730d"],
            row["score"],
        ),
        reverse=True,
    )
    return rows[:top_keep], rows


def deep_eval(bt, adapt, multi, reinvest, candles, configs):
    rows = []
    for config in configs:
        for scenario in SCENARIOS:
            for period in WINDOWS:
                result = evaluate_period(bt, adapt, multi, reinvest, candles, config, scenario, period)
                rows.append(
                    {
                        "filter_id": filter_id(config),
                        "scenario": scenario["name"],
                        **config,
                        **result,
                    }
                )
    return rows


def month_floor(day):
    return date(day.year, day.month, 1)


def next_month(day):
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def iter_month_ranges(start_day, end_day):
    current = month_floor(start_day)
    while current <= month_floor(end_day):
        yield current.strftime("%Y-%m"), max(current, start_day), min(next_month(current) - timedelta(days=1), end_day)
        current = next_month(current)


def day_start_ms(day):
    return int(datetime.combine(day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)


def day_end_ms(day):
    return int(datetime.combine(day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)


def monthly_eval(bt, adapt, multi, reinvest, candles, config, start_day, end_day):
    rows = []
    base = SCENARIOS[0]
    for month, month_start, month_end in iter_month_ranges(start_day, end_day):
        start_ms = day_start_ms(month_start)
        end_ms = day_end_ms(month_end)
        month_rows = [row for row in candles if start_ms <= row["open_time_ms"] <= end_ms]
        if len(month_rows) < 2:
            summary = {"total_trades": 0, "total_return_pct": 0.0, "max_drawdown_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "expectancy_pct": 0.0}
            stats = {}
        else:
            filtered = apply_config(adapt, month_rows, config)
            summary, stats = run_rows(bt, multi, reinvest, filtered, config, base)
        rows.append(
            {
                "filter_id": filter_id(config),
                "month": month,
                "range_start": month_start.isoformat(),
                "range_end": month_end.isoformat(),
                "trades": summary["total_trades"],
                "return_pct": summary["total_return_pct"],
                "max_dd_pct": summary["max_drawdown_pct"],
                "profit_factor": summary["profit_factor"],
                "win_rate_pct": summary["win_rate_pct"],
                "expectancy_pct": summary["expectancy_pct"],
                "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
                "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
            }
        )
    return rows


def write_report(path, stage_rows, deep_rows, monthly_rows, args, data_start, data_end):
    grouped = {}
    for row in deep_rows:
        grouped[(row["filter_id"], row["scenario"], int(row["period_days"]))] = row
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# CHZ 1h SHORT Filter Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Data: `{data_start}` - `{data_end}`.",
        "",
        "Цель: найти фильтр включения, который чинит свежий минус `7d/30d`, но не убивает `365d/730d`.",
        "",
        "## Top Stage Results",
        "",
        "| # | Filter | 7d | 30d | 365d | DD365 | PF365 | 730d | DD730 | PF730 | Trades730 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(stage_rows[:15], start=1):
        lines.append(
            f"| {idx} | `{row['filter_id']}` | {fmt_pct(row['ret_7d'])} | {fmt_pct(row['ret_30d'])} | "
            f"{fmt_pct(row['ret_365d'])} | {fmt_pct(row['dd_365d'], signed=False)} | {fmt_num(row['pf_365d'])} | "
            f"{fmt_pct(row['ret_730d'])} | {fmt_pct(row['dd_730d'], signed=False)} | {fmt_num(row['pf_730d'])} | {row['trades_730d']} |"
        )

    lines.extend(
        [
            "",
            "## Deep Scenario Check",
            "",
            "| Filter | Scenario | 1d | 7d | 30d | 60d | 90d | 180d | 365d | 730d | DD730 | PF730 | Trades730 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for config in stage_rows[:5]:
        fid = config["filter_id"]
        for scenario in [item["name"] for item in SCENARIOS]:
            values = {period: grouped[(fid, scenario, period)] for period in WINDOWS}
            row730 = values[730]
            lines.append(
                f"| `{fid}` | `{scenario}` | {fmt_pct(values[1]['return_pct'])} | {fmt_pct(values[7]['return_pct'])} | "
                f"{fmt_pct(values[30]['return_pct'])} | {fmt_pct(values[60]['return_pct'])} | "
                f"{fmt_pct(values[90]['return_pct'])} | {fmt_pct(values[180]['return_pct'])} | "
                f"{fmt_pct(values[365]['return_pct'])} | {fmt_pct(values[730]['return_pct'])} | "
                f"{fmt_pct(row730['max_dd_pct'], signed=False)} | {fmt_num(row730['profit_factor'])} | {row730['trades']} |"
            )
    if monthly_rows:
        positives = sum(1 for row in monthly_rows if float(row["return_pct"]) > 0)
        negatives = sum(1 for row in monthly_rows if float(row["return_pct"]) < 0)
        zeroes = len(monthly_rows) - positives - negatives
        worst = min(monthly_rows, key=lambda row: float(row["return_pct"]))
        best = max(monthly_rows, key=lambda row: float(row["return_pct"]))
        lines.extend(
            [
                "",
                "## Monthly For Best Filter",
                "",
                f"- Positive months: `{positives}/{len(monthly_rows)}`",
                f"- Negative months: `{negatives}/{len(monthly_rows)}`",
                f"- Flat months: `{zeroes}/{len(monthly_rows)}`",
                f"- Worst month: `{worst['month']}` `{fmt_pct(worst['return_pct'])}`",
                f"- Best month: `{best['month']}` `{fmt_pct(best['return_pct'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Files",
            "",
            f"- Stage CSV: `{args.save_stage}`",
            f"- Deep CSV: `{args.save_deep}`",
            f"- Monthly CSV: `{args.save_monthly}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Search CHZ 1h SHORT activation filters.")
    parser.add_argument("--archive-end-day", default="")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--top-keep", type=int, default=60)
    parser.add_argument("--save-stage", default=f"data/chz_1h_short_filter_search_stage_{today}.csv")
    parser.add_argument("--save-deep", default=f"data/chz_1h_short_filter_search_deep_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/chz_1h_short_filter_search_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/CHZ/chz-1h-short-filter-search-{today}.md")
    args = parser.parse_args()

    interval_fetch = load_module("rif_interval_windows_check", INTERVAL_FETCH_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    candles, data_start, data_end = interval_fetch.fetch_archive_klines(
        "CHZUSDT", "1h", args.days + args.warmup_days, args.archive_end_day or None
    )
    indicator_args = multi.make_strategy_args(reinvest, "7.3", "CHZUSDT")
    indicator_args.interval = "1h"
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)
    add_return_30d(candles, interval_fetch, bt)

    start_day = data_end - timedelta(days=args.days - 1)
    start_ms = day_start_ms(start_day)
    test_candles = [row for row in candles if row["open_time_ms"] >= start_ms]

    top_rows, all_stage = stage_search(bt, adapt, multi, reinvest, test_candles, args.top_keep)
    configs = []
    seen = set()
    for row in top_rows:
        fid = row["filter_id"]
        if fid in seen:
            continue
        seen.add(fid)
        configs.append({key: row[key] for key in (
            "threshold",
            "ret7_min",
            "ret7_max",
            "ret30_min",
            "ret30_max",
            "dist_min",
            "dist_max",
            "require_trend",
            "rsi_min",
            "rsi_max",
            "require_red",
        )})
        if len(configs) >= 10:
            break
    deep_rows = deep_eval(bt, adapt, multi, reinvest, test_candles, configs)
    monthly_rows = monthly_eval(bt, adapt, multi, reinvest, candles, configs[0], start_day, data_end) if configs else []

    stage_fields = [
        "filter_id",
        "threshold",
        "ret7_min",
        "ret7_max",
        "ret30_min",
        "ret30_max",
        "dist_min",
        "dist_max",
        "require_trend",
        "rsi_min",
        "rsi_max",
        "require_red",
        "ret_7d",
        "trades_7d",
        "ret_30d",
        "trades_30d",
        "ret_365d",
        "dd_365d",
        "pf_365d",
        "trades_365d",
        "ret_730d",
        "dd_730d",
        "pf_730d",
        "trades_730d",
        "score",
    ]
    deep_fields = [
        "filter_id",
        "scenario",
        "threshold",
        "ret7_min",
        "ret7_max",
        "ret30_min",
        "ret30_max",
        "dist_min",
        "dist_max",
        "require_trend",
        "rsi_min",
        "rsi_max",
        "require_red",
        "period_days",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
    ]
    monthly_fields = [
        "filter_id",
        "month",
        "range_start",
        "range_end",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
    ]
    save_csv(os.path.join(ROOT, args.save_stage), all_stage, stage_fields)
    save_csv(os.path.join(ROOT, args.save_deep), deep_rows, deep_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(os.path.join(ROOT, args.save_report), top_rows, deep_rows, monthly_rows, args, data_start, data_end)

    print(f"data: {data_start}..{data_end} candles={len(candles)}")
    print("top filters:")
    for row in top_rows[:10]:
        print(
            f"{row['filter_id']} 7d={row['ret_7d']:.2f} 30d={row['ret_30d']:.2f} "
            f"365d={row['ret_365d']:.2f} dd365={row['dd_365d']:.2f} pf365={fmt_num(row['pf_365d'])} "
            f"730d={row['ret_730d']:.2f} dd730={row['dd_730d']:.2f} pf730={fmt_num(row['pf_730d'])} trades730={row['trades_730d']}"
        )
    print(f"saved stage: {args.save_stage}")
    print(f"saved deep: {args.save_deep}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
