#!/usr/bin/env python3
"""Small ONE-specific tweak around the GALA-derived Minutka 11.2 portfolio.

The tweak keeps the same entry/exit logic, indicators, filters, TP/SL, fees,
and max-open-one rule. Only portfolio allocation changes.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
WINDOWS = [7, 30, 60, 90, 180, 365]
INITIAL_BALANCE = 1000.0


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def build_portfolio(short_trades, long_trades, scale, short_weight, long_weight):
    source = []
    for trade in short_trades:
        item = dict(trade)
        item["module"] = "7.3 short"
        item["portfolio_weight"] = short_weight
        source.append(item)
    for trade in long_trades:
        item = dict(trade)
        item["module"] = "10 long"
        item["portfolio_weight"] = long_weight
        source.append(item)

    selected = []
    open_trades = []
    equity = INITIAL_BALANCE
    equity_curve = [{"time": "initial", "equity": equity}]
    for trade in sorted(source, key=lambda item: (parse_time(item["entry_time"]), parse_time(item["exit_time"]))):
        entry_dt = parse_time(trade["entry_time"])
        open_trades = [item for item in open_trades if parse_time(item["exit_time"]) > entry_dt]
        if open_trades:
            continue

        adjusted_return_pct = trade["net_return_pct"] * scale * trade["portfolio_weight"]
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output["portfolio_scale"] = scale
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})
    return selected, equity_curve


def summarize(trades, equity_curve):
    wins = [trade for trade in trades if trade["risk_pnl"] > 0]
    losses = [trade for trade in trades if trade["risk_pnl"] < 0]
    gross_wins = sum(trade["risk_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["risk_pnl"] for trade in losses))
    returns = [trade["risk_return_pct"] for trade in trades]
    winning_returns = [value for value in returns if value > 0]
    losing_returns = [value for value in returns if value < 0]
    reasons = Counter(trade["reason"] for trade in trades)
    modules = Counter(trade["module"] for trade in trades)
    final_equity = equity_curve[-1]["equity"] if equity_curve else INITIAL_BALANCE
    return {
        "trades": len(trades),
        "return_pct": (final_equity / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_dd_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "final_equity": final_equity,
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "long_trades": modules["10 long"],
        "short_trades": modules["7.3 short"],
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def row_from_summary(variant, scale, short_weight, long_weight, period, summary):
    return {
        "variant": variant,
        "symbol": "ONEUSDT",
        "period": f"{period}d",
        "portfolio_scale": scale,
        "short_weight": short_weight,
        "long_weight": long_weight,
        "effective_short_position_pct": 0.24 * scale * short_weight,
        "effective_long_position_pct": 0.18 * scale * long_weight,
        **summary,
    }


def run_base_trades(bt, reinvest, multi, candles, period):
    bars = period * bt.candles_per_day("1m")
    window = candles[-bars:]

    short_window = [dict(row) for row in window]
    long_window = [dict(row) for row in window]
    multi.apply_strategy_signals(short_window, "7.3")
    multi.apply_strategy_signals(long_window, "10")

    short_args = multi.make_strategy_args(reinvest, "7.3", "ONEUSDT")
    long_args = multi.make_strategy_args(reinvest, "10", "ONEUSDT")
    short_trades, _, _ = bt.run_backtest(short_window, short_args)
    long_trades, _, _ = bt.run_backtest(long_window, long_args)
    return short_trades, long_trades


def main():
    parser = argparse.ArgumentParser(description="Search a small ONE-specific 11.2 allocation tweak.")
    parser.add_argument("--save-summary", default="data/one_strategy_tweak_summary.csv")
    parser.add_argument("--save-top", default="data/one_strategy_tweak_weight_search.csv")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    candles, _, _ = multi.fetch_klines_fast("ONEUSDT", 365, 7)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", "ONEUSDT")
    bt.add_indicators_and_signals(candles, indicator_args)

    base_trades = {period: run_base_trades(bt, reinvest, multi, candles, period) for period in WINDOWS}

    variants = [
        ("ONE 11.2 baseline", 0.90, 1.50, 1.00),
        ("ONE 11.2.1 long-tilted", 1.05, 1.00, 2.00),
    ]
    rows = []
    for variant, scale, short_weight, long_weight in variants:
        for period in WINDOWS:
            short_trades, long_trades = base_trades[period]
            trades, equity = build_portfolio(short_trades, long_trades, scale, short_weight, long_weight)
            rows.append(
                row_from_summary(
                    variant,
                    scale,
                    short_weight,
                    long_weight,
                    period,
                    summarize(trades, equity),
                )
            )

    grid_rows = []
    for scale in [0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05]:
        for short_weight in [0.80, 1.00, 1.20, 1.35, 1.50]:
            for long_weight in [1.00, 1.15, 1.30, 1.50, 1.75, 2.00]:
                period_rows = []
                for period in WINDOWS:
                    short_trades, long_trades = base_trades[period]
                    trades, equity = build_portfolio(
                        short_trades, long_trades, scale, short_weight, long_weight
                    )
                    period_rows.append(
                        row_from_summary(
                            "grid",
                            scale,
                            short_weight,
                            long_weight,
                            period,
                            summarize(trades, equity),
                        )
                    )
                row365 = next(row for row in period_rows if row["period"] == "365d")
                if all(row["return_pct"] > 0 for row in period_rows):
                    grid_rows.append(
                        {
                            "portfolio_scale": scale,
                            "short_weight": short_weight,
                            "long_weight": long_weight,
                            "return_365d_pct": row365["return_pct"],
                            "max_dd_365d_pct": row365["max_dd_pct"],
                            "profit_factor_365d": row365["profit_factor"],
                            "return_180d_pct": next(row for row in period_rows if row["period"] == "180d")[
                                "return_pct"
                            ],
                            "max_dd_180d_pct": next(row for row in period_rows if row["period"] == "180d")[
                                "max_dd_pct"
                            ],
                            "min_return_any_window_pct": min(row["return_pct"] for row in period_rows),
                            "max_dd_any_window_pct": max(row["max_dd_pct"] for row in period_rows),
                        }
                    )

    grid_rows.sort(
        key=lambda row: (
            row["return_365d_pct"],
            -row["max_dd_365d_pct"],
            row["profit_factor_365d"],
        ),
        reverse=True,
    )

    summary_fields = [
        "variant",
        "symbol",
        "period",
        "portfolio_scale",
        "short_weight",
        "long_weight",
        "effective_short_position_pct",
        "effective_long_position_pct",
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
        "stop_loss",
        "time_stop",
        "long_trades",
        "short_trades",
    ]
    grid_fields = [
        "portfolio_scale",
        "short_weight",
        "long_weight",
        "return_365d_pct",
        "max_dd_365d_pct",
        "profit_factor_365d",
        "return_180d_pct",
        "max_dd_180d_pct",
        "min_return_any_window_pct",
        "max_dd_any_window_pct",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_top), grid_rows[:25], grid_fields)

    for row in rows:
        print(
            f"{row['variant']} {row['period']}: return={row['return_pct']:.2f}% "
            f"DD={row['max_dd_pct']:.2f}% PF={row['profit_factor']:.2f} "
            f"trades={row['trades']}"
        )
    print(f"saved summary: {args.save_summary}")
    print(f"saved top search: {args.save_top}")


if __name__ == "__main__":
    main()
