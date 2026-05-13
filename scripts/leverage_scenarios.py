#!/usr/bin/env python3
"""Calculate selected leverage scenarios for current GALA Minutka candidates."""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAILING_PATH = os.path.join(ROOT, "scripts", "trailing_stop_strategies.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
WINDOWS = [30, 60, 90, 180, 365]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def duration_min(entry_time, exit_time):
    return (parse_time(exit_time) - parse_time(entry_time)).total_seconds() / 60.0


def max_drawdown(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]["equity"]
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def summarize_from_returns(trades, equity_curve, initial_balance, return_key, pnl_key):
    wins = [trade for trade in trades if trade[pnl_key] > 0]
    losses = [trade for trade in trades if trade[pnl_key] < 0]
    gross_wins = sum(trade[pnl_key] for trade in wins)
    gross_losses = abs(sum(trade[pnl_key] for trade in losses))
    returns = [trade[return_key] for trade in trades]
    winning_returns = [value for value in returns if value > 0]
    losing_returns = [value for value in returns if value < 0]
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_balance
    return {
        "trades": len(trades),
        "return_pct": (final_equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_dd_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "avg_duration_min": (
            sum(trade.get("duration_min", 0.0) for trade in trades) / len(trades)
            if trades
            else 0.0
        ),
        "final_equity": final_equity,
    }


def run_trailing_single(tss, bt, candles, label, strategy, leverage, days, initial_balance):
    bars = days * bt.candles_per_day("1m")
    window = [dict(row) for row in candles[-bars:]]
    if strategy == "minutka_7_4":
        tss.apply_minutka73_signals(window)
    elif strategy == "minutka_10_1":
        tss.apply_minutka10_signals(window)
    else:
        raise ValueError(strategy)

    args = tss.make_args(strategy, initial_balance, trailing_pct=0.0015, tp1_fraction=0.50)
    args.position_pct *= leverage
    trades, equity_curve, _ = tss.run_trailing_backtest(bt, window, args)
    summary = tss.summarize_trades(trades, initial_balance, equity_curve)
    return row_from_summary(label, leverage, days, summary, trades)


def run_trailing_portfolio(tss, bt, candles, leverage, days, initial_balance):
    short_trades, _, _, _ = tss.run_module(
        bt, candles, "minutka_7_4", days, initial_balance, 0.0015, 0.50
    )
    for trade in short_trades:
        trade["module"] = "GALA 1m SHORT Minutka 7.4 trailing"
        trade["portfolio_weight"] = 1.5

    long_trades, _, _, _ = tss.run_module(
        bt, candles, "minutka_10_1", days, initial_balance, 0.0015, 0.50
    )
    for trade in long_trades:
        trade["module"] = "GALA 1m LONG Minutka 10.1 trailing"
        trade["portfolio_weight"] = 1.0

    trades, equity_curve = tss.build_portfolio(
        short_trades + long_trades,
        initial_balance,
        portfolio_scale=0.9 * leverage,
    )
    summary = tss.summarize_portfolio(trades, initial_balance, equity_curve)
    module_counts = {
        "long_trades": sum(1 for trade in trades if trade["direction"] == "long"),
        "short_trades": sum(1 for trade in trades if trade["direction"] == "short"),
    }
    return row_from_summary("11.3", leverage, days, summary, trades, module_counts)


def run_112(reinvest, leverage, days, initial_balance):
    trades = reinvest.load_portfolio_trades(reinvest.MINUTKA11_1_TEMPLATE.format(days=days))
    selected = []
    open_trades = []
    equity = initial_balance
    equity_curve = [{"time": "initial", "equity": equity}]

    for trade in trades:
        open_trades = [item for item in open_trades if item["exit_dt"] > trade["entry_dt"]]
        if open_trades:
            continue

        adjusted_return_pct = (
            trade["net_return_pct"]
            * trade["portfolio_scale"]
            * trade["portfolio_weight"]
            * leverage
        )
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output.pop("entry_dt", None)
        output.pop("exit_dt", None)
        output["risk_layer"] = "max_open_1_compound_leverage"
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        output["duration_min"] = duration_min(output["entry_time"], output["exit_time"])
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

    summary = summarize_from_returns(selected, equity_curve, initial_balance, "risk_return_pct", "risk_pnl")
    module_counts = {
        "long_trades": sum(1 for trade in selected if trade["direction"] == "long"),
        "short_trades": sum(1 for trade in selected if trade["direction"] == "short"),
    }
    return row_from_summary("11.2", leverage, days, summary, selected, module_counts)


def reason_counts(trades):
    reasons = Counter(trade["reason"] for trade in trades)
    return {
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "tp1_trailing_stop": reasons["tp1_trailing_stop"],
        "tp1_time_stop": reasons["tp1_time_stop"],
        "end_of_data": reasons["end_of_data"] + reasons["tp1_end_of_data"],
    }


def row_from_summary(label, leverage, days, summary, trades, module_counts=None):
    row = {
        "strategy": label,
        "leverage": leverage,
        "period": f"{days}d",
        "trades": summary["trades"],
        "return_pct": summary["return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_dd_pct"],
        "avg_win_pct": summary.get("avg_win_pct", 0.0),
        "avg_loss_pct": summary.get("avg_loss_pct", 0.0),
        "expectancy_pct": summary.get("expectancy_pct", 0.0),
        "avg_duration_min": summary.get("avg_duration_min", 0.0),
        "final_equity": summary["final_equity"],
        **reason_counts(trades),
    }
    if module_counts:
        row.update(module_counts)
    return row


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Calculate leverage scenarios.")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--save-summary", default="data/leverage_scenarios_summary.csv")
    args = parser.parse_args()

    tss = load_module("trailing_stop_strategies", TRAILING_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    bt = tss.load_backtest_module()
    candles = tss.load_candles(tss.CANDLES_PATH)

    rows = []
    for days in WINDOWS:
        rows.append(
            run_trailing_single(tss, bt, candles, "7.4", "minutka_7_4", 1.5, days, args.initial_balance)
        )
        rows.append(
            run_trailing_single(tss, bt, candles, "10.1", "minutka_10_1", 1.1, days, args.initial_balance)
        )
        rows.append(run_112(reinvest, 1.2, days, args.initial_balance))
        rows.append(run_trailing_portfolio(tss, bt, candles, 2.0, days, args.initial_balance))

    fields = [
        "strategy",
        "leverage",
        "period",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "avg_win_pct",
        "avg_loss_pct",
        "expectancy_pct",
        "avg_duration_min",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
        "tp1_trailing_stop",
        "tp1_time_stop",
        "end_of_data",
        "long_trades",
        "short_trades",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields)

    for row in rows:
        print(
            f"{row['strategy']} {row['leverage']}x {row['period']}: "
            f"trades={row['trades']} return={row['return_pct']:.2f}% "
            f"win={row['win_rate_pct']:.2f}% PF={row['profit_factor']:.2f} "
            f"DD={row['max_dd_pct']:.2f}% final=${row['final_equity']:.2f}"
        )
    print(f"saved summary: {args.save_summary}")


if __name__ == "__main__":
    main()
