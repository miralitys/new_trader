#!/usr/bin/env python3
"""Search monthly-stable adaptations for RIF/MOVR fixed interval strategies.

The goal is different from max annual return: prefer variants that avoid red
calendar months. This is intentionally an in-sample research tool; results must
be stress-tested and forward-checked before promoting.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0


BASE_SPECS = [
    {
        "strategy": "RIF 5m LONG monthly search",
        "symbol": "RIFUSDT",
        "interval": "5m",
        "direction": "long",
        "thresholds": [40, 50],
        "regimes": ["wide"],
        "atr_maxes": [0.025, 0.050],
        "tps": [0.005, 0.0075, 0.010],
        "sls": [0.030, 0.040, 0.060],
        "time_stops": [120, 180],
    },
    {
        "strategy": "MOVR 1h LONG monthly search",
        "symbol": "MOVRUSDT",
        "interval": "1h",
        "direction": "long",
        "thresholds": [60, 70],
        "regimes": ["base"],
        "atr_maxes": [0.050],
        "tps": [0.020, 0.035, 0.050],
        "sls": [0.050, 0.080],
        "time_stops": [720, 1440],
    },
]


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


def month_key(iso_value):
    return iso_value[:7]


def day_start_ms(day):
    return int(datetime.combine(day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)


def day_end_ms(day):
    return int(datetime.combine(day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)


def parse_ms(iso_value):
    return int(datetime.fromisoformat(iso_value.replace("Z", "+00:00")).timestamp() * 1000)


def month_floor(day):
    return date(day.year, day.month, 1)


def next_month(day):
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def month_ranges(start_day, end_day):
    current = month_floor(start_day)
    while current <= month_floor(end_day):
        start = max(current, start_day)
        end = min(next_month(current) - timedelta(days=1), end_day)
        yield current.strftime("%Y-%m"), start, end
        current = next_month(current)


def variant_id(variant):
    weekly = "wk2" if variant["weekly_loss_stop_pct"] else "wk0"
    monthly_target = f"mt{variant['monthly_profit_target_pct']}" if variant["monthly_profit_target_pct"] else "mtoff"
    monthly_loss = f"ml{variant['monthly_loss_stop_pct']}" if variant["monthly_loss_stop_pct"] else "mloff"
    return (
        f"{variant['direction']}_th{variant['threshold']}_{variant['regime']}_atr{variant['atr_max_pct']}"
        f"_tp{variant['tp_pct']}_sl{variant['sl_pct']}_t{variant['time_stop_min']}_{weekly}_{monthly_target}_{monthly_loss}"
    )


def strategy_grid(spec):
    weekly_stops = [0.02]
    monthly_targets = [0.01, 0.02, 0.03]
    monthly_losses = [0.01, 0.02]
    for threshold in spec["thresholds"]:
        for regime in spec["regimes"]:
            for atr_max in spec["atr_maxes"]:
                for tp in spec["tps"]:
                    for sl in spec["sls"]:
                        for time_stop in spec["time_stops"]:
                            for weekly_stop in weekly_stops:
                                for monthly_target in monthly_targets:
                                    for monthly_loss in monthly_losses:
                                        yield {
                                            "direction": spec["direction"],
                                            "threshold": threshold,
                                            "regime": regime,
                                            "volume_multiplier": 1.5,
                                            "atr_min_pct": 0.0015,
                                            "atr_max_pct": atr_max,
                                            "tp_pct": tp,
                                            "sl_pct": sl,
                                            "time_stop_min": time_stop,
                                            "weekly_loss_stop_pct": weekly_stop,
                                            "monthly_profit_target_pct": monthly_target,
                                            "monthly_loss_stop_pct": monthly_loss,
                                        }


def make_args(adapt, multi, reinvest, variant, symbol, interval):
    args = adapt.make_args(multi, reinvest, variant, symbol, interval)
    args.initial_balance = INITIAL_BALANCE
    return args


def run_backtest_month_controls(bt, candles, args, variant):
    trades = []
    equity = args.initial_balance
    equity_curve = []
    stats = Counter()
    killed_days = set()
    killed_weeks = set()
    killed_months = set()
    day_start_equity = {}
    week_start_equity = {}
    week_peak_equity = {}
    month_start_equity = {}

    if candles:
        equity_curve.append({"time": candles[0]["open_time"], "equity": equity})

    index = 0
    while index < len(candles) - 1:
        signal_day = candles[index]["open_time"][:10]
        signal_week = bt.iso_week_key(candles[index]["open_time"])
        signal_month = month_key(candles[index]["open_time"])
        if signal_day not in day_start_equity:
            day_start_equity[signal_day] = equity
        if signal_week not in week_start_equity:
            week_start_equity[signal_week] = equity
            week_peak_equity[signal_week] = equity
        if signal_month not in month_start_equity:
            month_start_equity[signal_month] = equity
        week_peak_equity[signal_week] = max(week_peak_equity[signal_week], equity)

        if signal_day in killed_days:
            stats["daily_loss_stop_skipped_candles"] += 1
            index += 1
            continue
        if signal_week in killed_weeks:
            stats["weekly_loss_stop_skipped_candles"] += 1
            index += 1
            continue
        if signal_month in killed_months:
            stats["monthly_stop_skipped_candles"] += 1
            index += 1
            continue

        direction = bt.pick_signal(candles[index], args.direction)
        if direction is None:
            index += 1
            continue

        stats["entry_signals"] += 1
        stats[f"{direction}_entry_signals"] += 1
        entry_info, waited_until_idx = bt.find_entry_fill(candles, index, direction, args)
        if entry_info is None:
            stats["unfilled_entry_orders"] += 1
            stats[f"{direction}_unfilled_entry_orders"] += 1
            index = waited_until_idx + 1
            continue

        stats["filled_entry_orders"] += 1
        stats[f"{direction}_filled_entry_orders"] += 1
        trade = bt.simulate_trade(candles, entry_info, direction, equity, args)
        equity = trade["equity_after"]
        trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

        exit_day = trade["exit_time"][:10]
        exit_week = bt.iso_week_key(trade["exit_time"])
        exit_month = month_key(trade["exit_time"])
        if exit_day not in day_start_equity:
            day_start_equity[exit_day] = trade["equity_before"]
        if exit_week not in week_start_equity:
            week_start_equity[exit_week] = trade["equity_before"]
            week_peak_equity[exit_week] = trade["equity_before"]
        if exit_month not in month_start_equity:
            month_start_equity[exit_month] = trade["equity_before"]

        if args.daily_loss_stop_pct is not None and args.daily_loss_stop_pct > 0:
            daily_return = equity / day_start_equity[exit_day] - 1.0
            if daily_return <= -args.daily_loss_stop_pct and exit_day not in killed_days:
                killed_days.add(exit_day)
                stats["daily_loss_stop_events"] += 1
                stats[f"{direction}_daily_loss_stop_events"] += 1

        weekly_loss_stop_pct = getattr(args, "weekly_loss_stop_pct", None)
        week_peak_equity[exit_week] = max(week_peak_equity[exit_week], trade["equity_before"])
        if weekly_loss_stop_pct is not None and weekly_loss_stop_pct > 0:
            weekly_drawdown = equity / week_peak_equity[exit_week] - 1.0
            if weekly_drawdown <= -weekly_loss_stop_pct and exit_week not in killed_weeks:
                killed_weeks.add(exit_week)
                stats["weekly_loss_stop_events"] += 1
                stats[f"{direction}_weekly_loss_stop_events"] += 1
        week_peak_equity[exit_week] = max(week_peak_equity[exit_week], equity)

        month_return = equity / month_start_equity[exit_month] - 1.0
        target = variant.get("monthly_profit_target_pct")
        loss_stop = variant.get("monthly_loss_stop_pct")
        if target is not None and target > 0 and month_return >= target and exit_month not in killed_months:
            killed_months.add(exit_month)
            stats["monthly_profit_lock_events"] += 1
        if loss_stop is not None and loss_stop > 0 and month_return <= -loss_stop and exit_month not in killed_months:
            killed_months.add(exit_month)
            stats["monthly_loss_stop_events"] += 1

        index = trade["exit_idx"] + 1

    return trades, equity_curve, stats


def profit_factor(trades):
    wins = sum(trade["pnl"] for trade in trades if trade["pnl"] > 0)
    losses = sum(trade["pnl"] for trade in trades if trade["pnl"] < 0)
    if losses == 0:
        return math.inf if wins > 0 else 0.0
    return wins / abs(losses)


def max_drawdown(points):
    if not points:
        return 0.0
    peak = points[0][1]
    max_dd = 0.0
    for _, equity in points:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return max_dd


def monthly_breakdown(trades, equity_curve, start_day, end_day):
    points = [(day_start_ms(start_day), INITIAL_BALANCE)]
    points.extend((parse_ms(point["time"]), point["equity"]) for point in equity_curve)
    points.sort(key=lambda item: item[0])

    def equity_at(timestamp_ms):
        equity = INITIAL_BALANCE
        for point_time, point_equity in points:
            if point_time <= timestamp_ms:
                equity = point_equity
            else:
                break
        return equity

    rows = []
    for month, start, end in month_ranges(start_day, end_day):
        start_ms = day_start_ms(start)
        end_ms = day_end_ms(end)
        start_equity = equity_at(start_ms - 1)
        end_equity = equity_at(end_ms)
        month_trades = [trade for trade in trades if start_ms <= parse_ms(trade["exit_time"]) <= end_ms]
        month_points = [(start_ms, start_equity)]
        month_points.extend((point_time, equity) for point_time, equity in points if start_ms <= point_time <= end_ms)
        if month_points[-1][0] < end_ms:
            month_points.append((end_ms, end_equity))
        winning = [trade for trade in month_trades if trade["net_return_pct"] > 0]
        rows.append(
            {
                "month": month,
                "range_start": start.isoformat(),
                "range_end": end.isoformat(),
                "trades": len(month_trades),
                "return_pct": (end_equity / start_equity - 1.0) * 100.0 if start_equity else 0.0,
                "max_dd_pct": max_drawdown(month_points),
                "profit_factor": profit_factor(month_trades),
                "win_rate_pct": len(winning) / len(month_trades) * 100.0 if month_trades else 0.0,
                "start_equity": start_equity,
                "end_equity": end_equity,
            }
        )
    return rows


def candidate_score(months, summary):
    returns = [float(row["return_pct"]) for row in months]
    positive = sum(value > 0 for value in returns)
    negative = sum(value < -0.000001 for value in returns)
    flat = len(returns) - positive - negative
    worst = min(returns) if returns else 0.0
    median = sorted(returns)[len(returns) // 2] if returns else 0.0
    return (
        positive * 100.0
        + flat * 15.0
        + summary["total_return_pct"] * 1.0
        + min(summary["profit_factor"], 3.0) * 20.0
        - summary["max_drawdown_pct"] * 3.0
        + worst * 20.0
        + median * 5.0
        - negative * 120.0
    )


def evaluate_variant(bt, adapt, multi, reinvest, candles, spec, variant, start_day, end_day):
    rows = [dict(row) for row in candles if day_start_ms(start_day) <= row["open_time_ms"] <= day_end_ms(end_day)]
    if len(rows) < 2:
        return None, None, None
    adapt.apply_variant_signals(rows, variant)
    args = make_args(adapt, multi, reinvest, variant, spec["symbol"], spec["interval"])
    trades, equity_curve, stats = run_backtest_month_controls(bt, rows, args, variant)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity_curve)
    months = monthly_breakdown(trades, equity_curve, start_day, end_day)
    summary["positive_months"] = sum(float(row["return_pct"]) > 0 for row in months)
    summary["negative_months"] = sum(float(row["return_pct"]) < -0.000001 for row in months)
    summary["flat_months"] = len(months) - summary["positive_months"] - summary["negative_months"]
    summary["worst_month_pct"] = min(float(row["return_pct"]) for row in months) if months else 0.0
    summary["best_month_pct"] = max(float(row["return_pct"]) for row in months) if months else 0.0
    summary["monthly_profit_lock_events"] = stats.get("monthly_profit_lock_events", 0)
    summary["monthly_loss_stop_events"] = stats.get("monthly_loss_stop_events", 0)
    return summary, months, stats


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_num(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def write_report(path, best_rows, month_rows, csv_summary, csv_months):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# RIF/MOVR Monthly Positive Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Цель поиска: уменьшить количество красных месяцев. Это in-sample исследование, не гарантия будущих плюсов каждый месяц.",
        "",
        "Исполнение: maker-limit offset `0.05%`, maker fee `0.02%`, slippage `0`, без плеча.",
        "",
        "## Best Variants",
        "",
        "| Strategy | Variant | Return | MaxDD | PF | Trades | + Months | 0 Months | - Months | Worst Month | Best Month |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in best_rows:
        lines.append(
            f"| {row['strategy']} | `{row['variant_id']}` | {fmt_pct(row['return_pct'])} | "
            f"{fmt_pct(row['max_dd_pct'])} | {fmt_num(row['profit_factor'])} | {row['trades']} | "
            f"{row['positive_months']} | {row['flat_months']} | {row['negative_months']} | "
            f"{fmt_pct(row['worst_month_pct'])} | {fmt_pct(row['best_month_pct'])} |"
        )

    for row in best_rows[:4]:
        lines.extend(
            [
                "",
                f"## Monthly: {row['strategy']} / `{row['variant_id']}`",
                "",
                "| Month | Trades | Return | MaxDD | PF | Win rate | Equity |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for month in month_rows:
            if month["strategy"] != row["strategy"] or month["variant_id"] != row["variant_id"]:
                continue
            lines.append(
                f"| {month['month']} | {month['trades']} | {fmt_pct(month['return_pct'])} | "
                f"{fmt_pct(month['max_dd_pct'])} | {fmt_num(month['profit_factor'])} | "
                f"{fmt_pct(month['win_rate_pct'])} | ${float(month['start_equity']):.2f} -> ${float(month['end_equity']):.2f} |"
            )
    lines.extend(["", "## Files", "", f"- Summary CSV: `{csv_summary}`", f"- Monthly CSV: `{csv_months}`", ""])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Search monthly-positive RIF/MOVR adaptations.")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--save-summary", default=f"data/rif_movr_monthly_positive_search_summary_{today}.csv")
    parser.add_argument("--save-months", default=f"data/rif_movr_monthly_positive_search_months_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-movr-monthly-positive-search-{today}.md")
    args = parser.parse_args()

    interval_mod = load_module("rif_interval_windows_check", INTERVAL_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    end_day = date.fromisoformat(args.archive_end_day)
    start_day = end_day - timedelta(days=args.days - 1)

    all_summary = []
    all_months = []
    for spec in BASE_SPECS:
        candles, data_start, data_end = interval_mod.fetch_archive_klines(
            spec["symbol"], spec["interval"], args.days + args.warmup_days, args.archive_end_day
        )
        indicator_args = multi.make_strategy_args(reinvest, "10", spec["symbol"])
        indicator_args.interval = spec["interval"]
        indicator_args.atr_max_pct = 0.050
        bt.add_indicators_and_signals(candles, indicator_args)

        candidates = []
        for index, variant in enumerate(strategy_grid(spec), start=1):
            summary, months, stats = evaluate_variant(bt, adapt, multi, reinvest, candles, spec, variant, start_day, end_day)
            if summary is None:
                continue
            vid = variant_id(variant)
            score = candidate_score(months, summary)
            summary_row = {
                "strategy": spec["strategy"],
                "symbol": spec["symbol"],
                "interval": spec["interval"],
                "variant_id": vid,
                **variant,
                "trades": summary["total_trades"],
                "return_pct": summary["total_return_pct"],
                "max_dd_pct": summary["max_drawdown_pct"],
                "profit_factor": summary["profit_factor"],
                "win_rate_pct": summary["win_rate_pct"],
                "expectancy_pct": summary["expectancy_pct"],
                "positive_months": summary["positive_months"],
                "flat_months": summary["flat_months"],
                "negative_months": summary["negative_months"],
                "worst_month_pct": summary["worst_month_pct"],
                "best_month_pct": summary["best_month_pct"],
                "monthly_profit_lock_events": summary["monthly_profit_lock_events"],
                "monthly_loss_stop_events": summary["monthly_loss_stop_events"],
                "score": score,
                "data_start": data_start.isoformat(),
                "data_end": data_end.isoformat(),
            }
            month_rows = [
                {
                    "strategy": spec["strategy"],
                    "symbol": spec["symbol"],
                    "interval": spec["interval"],
                    "variant_id": vid,
                    **month,
                }
                for month in months
            ]
            candidates.append((score, summary_row, month_rows))
            if index % 1000 == 0:
                print(f"{spec['symbol']} {spec['interval']}: checked {index} variants", flush=True)
        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, summary_row, month_rows in candidates[: args.top_n]:
            all_summary.append(summary_row)
            all_months.extend(month_rows)

    summary_fields = [
        "strategy",
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
        "monthly_profit_target_pct",
        "monthly_loss_stop_pct",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "positive_months",
        "flat_months",
        "negative_months",
        "worst_month_pct",
        "best_month_pct",
        "monthly_profit_lock_events",
        "monthly_loss_stop_events",
        "score",
        "data_start",
        "data_end",
    ]
    month_fields = [
        "strategy",
        "symbol",
        "interval",
        "variant_id",
        "month",
        "range_start",
        "range_end",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "start_equity",
        "end_equity",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), all_summary, summary_fields)
    save_csv(os.path.join(ROOT, args.save_months), all_months, month_fields)
    write_report(os.path.join(ROOT, args.save_report), all_summary, all_months, args.save_summary, args.save_months)
    print(f"saved summary: {args.save_summary}")
    print(f"saved months: {args.save_months}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
