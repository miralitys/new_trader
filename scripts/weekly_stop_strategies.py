#!/usr/bin/env python3
"""Compare winning Minutka strategies with a weekly loss stop.

New variants:
- 7.4 = 7.3 + weekly stop after -12% from the current week's equity peak.
- 10.1 = 10 + weekly stop after -12% from the current week's equity peak.
- 11.3 = 11.2 compound + weekly stop after -12% from the current week's equity peak.
"""

import argparse
import csv
import importlib.util
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKTEST_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
CANDLES_PATH = os.path.join(ROOT, "data", "strategy7_365d_candles.csv")
WINDOWS = [30, 60, 90, 180, 365]
WEEKLY_STOP = 0.12
MINUTKA11_1_TEMPLATE = os.path.join(
    ROOT,
    "data",
    "minutka11_1_v5_{days}d_fixed_notional_scale0.9_maxopennone_noeod_trades.csv",
)


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


BOOL_FIELDS = {
    "smart_long_filter",
    "regime_filter_passed",
    "long_signal",
    "short_signal",
}


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("gala_mb_backtest", BACKTEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iso_to_ms(value):
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def parse_float(value):
    if value in ("", None):
        return None
    return float(value)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def week_key(value):
    dt = parse_time(value)
    year, week, _ = dt.date().isocalendar()
    return f"{year}-W{week:02d}"


def load_candles(path):
    candles = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if key in FLOAT_FIELDS:
                    parsed[key] = parse_float(value)
                elif key in BOOL_FIELDS:
                    parsed[key] = value in {"1", "True", "true"}
                else:
                    parsed[key] = value
            parsed["open_time_ms"] = iso_to_ms(parsed["open_time"])
            parsed["close_time_ms"] = iso_to_ms(parsed["close_time"])
            candles.append(parsed)
    return candles


def in_range(value, min_value=None, max_value=None):
    if min_value is None and max_value is None:
        return True
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_ok(row):
    return (
        in_range(row.get("atr_pct"), 0.0025, None)
        and in_range(row.get("dist_ema200"), -0.015, 0.015)
        and in_range(row.get("return_7d"), -0.40, 0.10)
    )


def apply_minutka73_signals(candles):
    for row in candles:
        row["long_signal"] = False
        row["short_signal"] = row.get("short_score", 0.0) >= 40 and regime_ok(row)


def apply_minutka10_signals(candles):
    for row in candles:
        row["long_signal"] = (
            row.get("long_score", 0.0) >= 50
            and bool(row.get("smart_long_filter"))
            and regime_ok(row)
        )
        row["short_signal"] = False


def make_args(strategy, initial_balance, weekly_stop=None):
    common = {
        "market": "futures_archive",
        "symbol": "GALAUSDT",
        "interval": "1m",
        "days": 365,
        "warmup_days": 7,
        "initial_balance": initial_balance,
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": weekly_stop,
        "filter_atr_min_pct": 0.0025,
        "filter_atr_max_pct": None,
        "filter_dist_ema200_min": -0.015,
        "filter_dist_ema200_max": 0.015,
        "filter_return_1d_min": None,
        "filter_return_1d_max": None,
        "filter_return_7d_min": -0.40,
        "filter_return_7d_max": 0.10,
        "save_candles": "",
        "save_trades": "",
        "save_equity": "",
        "volume_multiplier": 1.5,
        "atr_min_pct": 0.0015,
        "atr_max_pct": 0.0120,
    }

    if strategy == "minutka_7_3":
        common.update(
            {
                "direction": "short",
                "position_pct": 0.24,
                "long_tp_pct": 0.004,
                "long_sl_pct": 0.003,
                "short_tp_pct": 0.0028,
                "short_sl_pct": 0.040,
                "time_stop_min": 120,
                "long_time_stop_min": None,
                "short_time_stop_min": 120,
                "long_threshold": 80,
                "short_threshold": 40,
            }
        )
    elif strategy == "minutka_10":
        common.update(
            {
                "direction": "long",
                "position_pct": 0.18,
                "long_tp_pct": 0.0025,
                "long_sl_pct": 0.040,
                "short_tp_pct": 0.003,
                "short_sl_pct": 0.003,
                "time_stop_min": 90,
                "long_time_stop_min": 90,
                "short_time_stop_min": None,
                "long_threshold": 50,
                "short_threshold": 40,
            }
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return argparse.Namespace(**common)


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_single_strategy(bt, candles, strategy, days, initial_balance, weekly_stop=None):
    bars = days * bt.candles_per_day("1m")
    window = [dict(row) for row in candles[-bars:]]
    if strategy == "minutka_7_3":
        apply_minutka73_signals(window)
    elif strategy == "minutka_10":
        apply_minutka10_signals(window)
    args = make_args(strategy, initial_balance, weekly_stop)
    trades, equity, stats = bt.run_backtest(window, args)
    summary = bt.summarize_trades(trades, initial_balance, equity)
    return trades, equity, stats, summary


def ensure_minutka11_source(days):
    path = MINUTKA11_1_TEMPLATE.format(days=days)
    if os.path.exists(path):
        return path
    command = [
        sys.executable,
        os.path.join(ROOT, "scripts", "minutka8_reproduce.py"),
        "--variant",
        "v5",
        "--days",
        str(days),
        "--warmup-days",
        "7",
        "--portfolio-model",
        "fixed_notional",
        "--portfolio-scale",
        "0.9",
        "--portfolio-skip-end-of-data",
        "--save-prefix",
        "data/minutka11_1",
    ]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return path


def load_portfolio_trades(days):
    path = ensure_minutka11_source(days)
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            row["net_return_pct"] = float(row["net_return_pct"])
            row["portfolio_scale"] = float(row["portfolio_scale"])
            row["portfolio_weight"] = float(row["portfolio_weight"])
            rows.append(row)
    return sorted(rows, key=lambda item: (item["entry_dt"], item["exit_dt"]))


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def summarize_portfolio(trades, equity_curve, initial_balance):
    wins = [trade for trade in trades if trade["risk_pnl"] > 0]
    losses = [trade for trade in trades if trade["risk_pnl"] < 0]
    gross_wins = sum(trade["risk_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["risk_pnl"] for trade in losses))
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_balance
    returns = [trade["risk_return_pct"] for trade in trades]
    winning_returns = [value for value in returns if value > 0]
    losing_returns = [value for value in returns if value < 0]
    reasons = Counter(trade["reason"] for trade in trades)
    modules = Counter(trade["module"] for trade in trades)
    return {
        "total_trades": len(trades),
        "total_return_pct": (final_equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "final_equity": final_equity,
        "take_profit": reasons["take_profit"],
        "time_stop": reasons["time_stop"],
        "stop_loss": reasons["stop_loss"],
        "long_trades": modules["GALA 1m LONG Minutka 10"],
        "short_trades": modules["GALA 1m SHORT Minutka 7.3 x1.5"],
    }


def run_minutka112(days, initial_balance, weekly_stop=None):
    source = load_portfolio_trades(days)
    selected = []
    open_trades = []
    killed_weeks = set()
    week_start_equity = {}
    week_peak_equity = {}
    skipped_weekly = 0
    weekly_events = 0
    equity = initial_balance
    equity_curve = [{"time": "initial", "equity": equity}]

    for trade in source:
        entry_time = trade["entry_dt"]
        open_trades = [item for item in open_trades if item["exit_dt"] > entry_time]
        if open_trades:
            continue

        entry_week = week_key(trade["entry_time"])
        if entry_week not in week_start_equity:
            week_start_equity[entry_week] = equity
            week_peak_equity[entry_week] = equity
        week_peak_equity[entry_week] = max(week_peak_equity[entry_week], equity)
        if weekly_stop is not None and entry_week in killed_weeks:
            skipped_weekly += 1
            continue

        adjusted_return_pct = (
            trade["net_return_pct"] * trade["portfolio_scale"] * trade["portfolio_weight"]
        )
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output.pop("entry_dt", None)
        output.pop("exit_dt", None)
        output["risk_layer"] = "max_open_1_compound"
        output["weekly_loss_stop_pct"] = weekly_stop if weekly_stop is not None else ""
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

        if weekly_stop is not None and weekly_stop > 0:
            exit_week = week_key(trade["exit_time"])
            if exit_week not in week_start_equity:
                week_start_equity[exit_week] = equity_before
                week_peak_equity[exit_week] = equity_before
            week_peak_equity[exit_week] = max(week_peak_equity[exit_week], equity_before)
            weekly_drawdown = equity / week_peak_equity[exit_week] - 1.0
            if weekly_drawdown <= -weekly_stop and exit_week not in killed_weeks:
                killed_weeks.add(exit_week)
                weekly_events += 1
            week_peak_equity[exit_week] = max(week_peak_equity[exit_week], equity)

    stats = Counter(
        {
            "weekly_loss_stop_events": weekly_events,
            "weekly_loss_stop_skipped_trades": skipped_weekly,
        }
    )
    return selected, equity_curve, stats, summarize_portfolio(selected, equity_curve, initial_balance)


def reason_counts(trades):
    reasons = Counter(trade["reason"] for trade in trades)
    return {
        "take_profit": reasons["take_profit"],
        "time_stop": reasons["time_stop"],
        "stop_loss": reasons["stop_loss"],
    }


def row_from_single(label, variant, days, summary, stats, trades):
    reasons = reason_counts(trades)
    return {
        "strategy": label,
        "variant": variant,
        "period": f"{days}d",
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
        "time_stop": reasons["time_stop"],
        "stop_loss": reasons["stop_loss"],
        "weekly_stop_events": stats.get("weekly_loss_stop_events", 0),
        "weekly_skipped": stats.get("weekly_loss_stop_skipped_candles", 0),
        "long_trades": sum(1 for trade in trades if trade.get("direction") == "long"),
        "short_trades": sum(1 for trade in trades if trade.get("direction") == "short"),
    }


def row_from_portfolio(label, variant, days, summary, stats):
    return {
        "strategy": label,
        "variant": variant,
        "period": f"{days}d",
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "avg_win_pct": summary["avg_win_pct"],
        "avg_loss_pct": summary["avg_loss_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "final_equity": summary["final_equity"],
        "take_profit": summary["take_profit"],
        "time_stop": summary["time_stop"],
        "stop_loss": summary["stop_loss"],
        "weekly_stop_events": stats.get("weekly_loss_stop_events", 0),
        "weekly_skipped": stats.get("weekly_loss_stop_skipped_trades", 0),
        "long_trades": summary["long_trades"],
        "short_trades": summary["short_trades"],
    }


def write_artifacts(prefix, trades, equity):
    save_csv(
        f"{prefix}_trades.csv",
        trades,
        [
            "module",
            "symbol",
            "interval",
            "direction",
            "entry_mode",
            "signal_time",
            "order_start_time",
            "entry_time",
            "exit_time",
            "entry",
            "exit",
            "limit_price",
            "fill_delay_min",
            "reason",
            "gross_return_pct",
            "net_return_pct",
            "portfolio_scale",
            "portfolio_weight",
            "risk_layer",
            "weekly_loss_stop_pct",
            "risk_return_pct",
            "risk_equity_before",
            "pnl",
            "risk_pnl",
            "duration_min",
            "equity_after",
            "risk_equity_after",
        ],
    )
    save_csv(f"{prefix}_equity.csv", equity, ["time", "equity"])


def stop_tag(stop_pct):
    return f"{stop_pct * 100:g}pct".replace(".", "_")


def main():
    parser = argparse.ArgumentParser(description="Apply weekly stop to winning strategies.")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--weekly-stop-pct", type=float, default=WEEKLY_STOP)
    parser.add_argument("--save-summary", default="data/weekly_stop_summary.csv")
    args = parser.parse_args()

    bt = load_backtest_module()
    candles = load_candles(CANDLES_PATH)
    rows = []
    tag = stop_tag(args.weekly_stop_pct)
    variant_name = f"weekly_stop_{tag}"

    for strategy, base_label, new_label in [
        ("minutka_7_3", "7.3", "7.4"),
        ("minutka_10", "10", "10.1"),
    ]:
        for days in WINDOWS:
            base_trades, base_equity, base_stats, base_summary = run_single_strategy(
                bt, candles, strategy, days, args.initial_balance, weekly_stop=None
            )
            rows.append(row_from_single(base_label, "base", days, base_summary, base_stats, base_trades))
            write_artifacts(
                os.path.join(ROOT, "data", f"weekly_stop_{base_label.replace('.', '_')}_base_{days}d"),
                base_trades,
                base_equity,
            )

            new_trades, new_equity, new_stats, new_summary = run_single_strategy(
                bt, candles, strategy, days, args.initial_balance, weekly_stop=args.weekly_stop_pct
            )
            rows.append(
                row_from_single(new_label, variant_name, days, new_summary, new_stats, new_trades)
            )
            write_artifacts(
                os.path.join(
                    ROOT,
                    "data",
                    f"weekly_stop_{new_label.replace('.', '_')}_{tag}_{days}d",
                ),
                new_trades,
                new_equity,
            )

    for days in WINDOWS:
        base_trades, base_equity, base_stats, base_summary = run_minutka112(
            days, args.initial_balance, weekly_stop=None
        )
        rows.append(row_from_portfolio("11.2", "base_compound", days, base_summary, base_stats))
        write_artifacts(
            os.path.join(ROOT, "data", f"weekly_stop_11_2_base_{days}d"),
            base_trades,
            base_equity,
        )

        new_trades, new_equity, new_stats, new_summary = run_minutka112(
            days, args.initial_balance, weekly_stop=args.weekly_stop_pct
        )
        rows.append(row_from_portfolio("11.3", variant_name, days, new_summary, new_stats))
        write_artifacts(
            os.path.join(ROOT, "data", f"weekly_stop_11_3_{tag}_{days}d"),
            new_trades,
            new_equity,
        )

    fields = [
        "strategy",
        "variant",
        "period",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "avg_win_pct",
        "avg_loss_pct",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "time_stop",
        "stop_loss",
        "weekly_stop_events",
        "weekly_skipped",
        "long_trades",
        "short_trades",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields)

    for row in rows:
        pf = row["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.2f}"
        print(
            f"{row['strategy']} {row['period']} {row['variant']}: "
            f"trades={row['trades']} return={row['return_pct']:.2f}% "
            f"win={row['win_rate_pct']:.2f}% PF={pf_text} "
            f"DD={row['max_dd_pct']:.2f}% final=${row['final_equity']:.2f} "
            f"weekly_events={row['weekly_stop_events']} weekly_skipped={row['weekly_skipped']}"
        )
    print(f"saved summary: {args.save_summary}")


if __name__ == "__main__":
    main()
