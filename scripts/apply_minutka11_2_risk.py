#!/usr/bin/env python3
"""Apply Minutka 11.2 portfolio risk layer to Minutka 11.1 trades.

Minutka 11.2 keeps the same GALA modules as 11.1, but allows only one open
GALA position at a time. In practice this is equivalent to
`--portfolio-max-open 1` for the two-module GALA portfolio.
"""

import csv
import math
import os
from collections import Counter
from datetime import datetime


WINDOWS = [7, 30, 90, 180, 365]
INPUT_TEMPLATE = (
    "data/minutka11_1_v5_{days}d_"
    "fixed_notional_scale0.9_maxopennone_noeod_trades.csv"
)
OUTPUT_TEMPLATE = "data/minutka11_2_{days}d_trades.csv"
EQUITY_TEMPLATE = "data/minutka11_2_{days}d_equity.csv"
SUMMARY_PATH = "data/minutka11_2_summary.csv"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_trades(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            row["portfolio_pnl"] = float(row["portfolio_pnl"])
            row["portfolio_scale"] = float(row["portfolio_scale"])
            row["portfolio_weight"] = float(row["portfolio_weight"])
            row["net_return_pct"] = float(row["net_return_pct"])
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


def apply_max_open_one(trades, initial_balance=1000.0):
    selected = []
    equity_curve = [{"time": "initial", "equity": initial_balance}]
    equity = initial_balance
    open_trades = []

    for trade in trades:
        entry_time = trade["entry_dt"]
        open_trades = [item for item in open_trades if item["exit_dt"] > entry_time]
        if open_trades:
            continue

        pnl = trade["portfolio_pnl"]
        equity += pnl
        output = dict(trade)
        output.pop("entry_dt", None)
        output.pop("exit_dt", None)
        output["risk_layer"] = "max_open_1"
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

    return selected, equity_curve


def summarize(trades, equity_curve, initial_balance=1000.0):
    wins = [trade for trade in trades if trade["risk_pnl"] > 0]
    losses = [trade for trade in trades if trade["risk_pnl"] < 0]
    gross_wins = sum(trade["risk_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["risk_pnl"] for trade in losses))
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_balance
    return {
        "trades": len(trades),
        "return_pct": (final_equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_dd_pct": max_drawdown(equity_curve),
        "final_equity": final_equity,
        "take_profit": Counter(trade["reason"] for trade in trades)["take_profit"],
        "time_stop": Counter(trade["reason"] for trade in trades)["time_stop"],
        "stop_loss": Counter(trade["reason"] for trade in trades)["stop_loss"],
        "long_trades": Counter(trade["module"] for trade in trades)["GALA 1m LONG Minutka 10"],
        "short_trades": Counter(trade["module"] for trade in trades)[
            "GALA 1m SHORT Minutka 7.3 x1.5"
        ],
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    summary_rows = []
    for days in WINDOWS:
        trades = load_trades(INPUT_TEMPLATE.format(days=days))
        selected, equity_curve = apply_max_open_one(trades)
        summary = summarize(selected, equity_curve)
        summary["period"] = f"{days}d"
        summary_rows.append(summary)

        trade_fields = [
            "module",
            "symbol",
            "interval",
            "direction",
            "entry_time",
            "exit_time",
            "entry",
            "exit",
            "reason",
            "net_return_pct",
            "portfolio_scale",
            "portfolio_weight",
            "portfolio_pnl",
            "risk_layer",
            "risk_pnl",
            "risk_equity_after",
        ]
        save_csv(OUTPUT_TEMPLATE.format(days=days), selected, trade_fields)
        save_csv(EQUITY_TEMPLATE.format(days=days), equity_curve, ["time", "equity"])

        print(
            f"{days}d: trades={summary['trades']} "
            f"return={summary['return_pct']:.2f}% "
            f"win={summary['win_rate_pct']:.2f}% "
            f"PF={summary['profit_factor']:.2f} "
            f"MaxDD={summary['max_dd_pct']:.2f}% "
            f"final=${summary['final_equity']:.2f}"
        )

    summary_fields = [
        "period",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "final_equity",
        "take_profit",
        "time_stop",
        "stop_loss",
        "long_trades",
        "short_trades",
    ]
    save_csv(SUMMARY_PATH, summary_rows, summary_fields)
    print(f"saved summary: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
