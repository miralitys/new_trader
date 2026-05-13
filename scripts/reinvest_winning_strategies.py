#!/usr/bin/env python3
"""Recalculate winning Minutka strategies with full reinvestment.

For single strategies 7.3 and 10, the core backtester already sizes each trade
from current equity. This script reruns them explicitly and saves fresh summary
files. For 11.2, it rebuilds the one-position portfolio and applies each
portfolio return to current equity instead of fixed starting notional.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKTEST_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
WINDOWS = [7, 30, 90, 180, 365]
CANDLES_PATH = os.path.join(ROOT, "data", "strategy7_365d_candles.csv")
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


def make_args(strategy, initial_balance):
    if strategy == "minutka_7_3":
        return argparse.Namespace(
            market="futures_archive",
            symbol="GALAUSDT",
            interval="1m",
            days=365,
            warmup_days=7,
            direction="short",
            initial_balance=initial_balance,
            position_pct=0.24,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_entry_offset_pct=0.0,
            limit_entry_timeout_min=1,
            long_tp_pct=0.004,
            long_sl_pct=0.003,
            short_tp_pct=0.0028,
            short_sl_pct=0.040,
            time_stop_min=120,
            long_time_stop_min=None,
            short_time_stop_min=120,
            daily_loss_stop_pct=0.02,
            filter_atr_min_pct=0.0025,
            filter_atr_max_pct=None,
            filter_dist_ema200_min=-0.015,
            filter_dist_ema200_max=0.015,
            filter_return_1d_min=None,
            filter_return_1d_max=None,
            filter_return_7d_min=-0.40,
            filter_return_7d_max=0.10,
            save_candles="",
            save_trades="",
            save_equity="",
            long_threshold=80,
            short_threshold=40,
            volume_multiplier=1.5,
            atr_min_pct=0.0015,
            atr_max_pct=0.0120,
        )
    if strategy == "minutka_10":
        return argparse.Namespace(
            market="futures_archive",
            symbol="GALAUSDT",
            interval="1m",
            days=365,
            warmup_days=7,
            direction="long",
            initial_balance=initial_balance,
            position_pct=0.18,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_entry_offset_pct=0.0,
            limit_entry_timeout_min=1,
            long_tp_pct=0.0025,
            long_sl_pct=0.040,
            short_tp_pct=0.003,
            short_sl_pct=0.003,
            time_stop_min=90,
            long_time_stop_min=90,
            short_time_stop_min=None,
            daily_loss_stop_pct=0.02,
            filter_atr_min_pct=0.0025,
            filter_atr_max_pct=None,
            filter_dist_ema200_min=-0.015,
            filter_dist_ema200_max=0.015,
            filter_return_1d_min=None,
            filter_return_1d_max=None,
            filter_return_7d_min=-0.40,
            filter_return_7d_max=0.10,
            save_candles="",
            save_trades="",
            save_equity="",
            long_threshold=50,
            short_threshold=40,
            volume_multiplier=1.5,
            atr_min_pct=0.0015,
            atr_max_pct=0.0120,
        )
    raise ValueError(f"Unknown strategy: {strategy}")


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_single_strategy(bt, candles, strategy, days, initial_balance):
    bars = days * bt.candles_per_day("1m")
    window = [dict(row) for row in candles[-bars:]]
    if strategy == "minutka_7_3":
        apply_minutka73_signals(window)
    elif strategy == "minutka_10":
        apply_minutka10_signals(window)
    args = make_args(strategy, initial_balance)
    trades, equity, _ = bt.run_backtest(window, args)
    summary = bt.summarize_trades(trades, initial_balance, equity)
    return trades, equity, summary


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_portfolio_trades(path):
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
    return {
        "total_trades": len(trades),
        "total_return_pct": (final_equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "final_equity": final_equity,
    }


def run_minutka112_compound(days, initial_balance):
    trades = load_portfolio_trades(MINUTKA11_1_TEMPLATE.format(days=days))
    selected = []
    open_trades = []
    equity = initial_balance
    equity_curve = [{"time": "initial", "equity": equity}]

    for trade in trades:
        open_trades = [item for item in open_trades if item["exit_dt"] > trade["entry_dt"]]
        if open_trades:
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
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

    return selected, equity_curve, summarize_portfolio(selected, equity_curve, initial_balance)


def summary_row(strategy, days, summary):
    return {
        "strategy": strategy,
        "period": f"{days}d",
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "final_equity": summary["final_equity"],
    }


def main():
    parser = argparse.ArgumentParser(description="Reinvest winning Minutka strategies.")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--save-summary", default="data/winning_reinvest_summary.csv")
    args = parser.parse_args()

    bt = load_backtest_module()
    candles = load_candles(CANDLES_PATH)
    rows = []

    for strategy in ["minutka_7_3", "minutka_10"]:
        for days in WINDOWS:
            trades, equity, summary = run_single_strategy(
                bt, candles, strategy, days, args.initial_balance
            )
            rows.append(summary_row(strategy, days, summary))
            prefix = os.path.join(ROOT, "data", f"winning_reinvest_{strategy}_{days}d")
            save_csv(
                f"{prefix}_trades.csv",
                trades,
                [
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
                    "pnl",
                    "duration_min",
                    "equity_after",
                ],
            )
            save_csv(f"{prefix}_equity.csv", equity, ["time", "equity"])

    for days in WINDOWS:
        trades, equity, summary = run_minutka112_compound(days, args.initial_balance)
        rows.append(summary_row("minutka_11_2_compound", days, summary))
        prefix = os.path.join(ROOT, "data", f"winning_reinvest_minutka_11_2_{days}d")
        save_csv(
            f"{prefix}_trades.csv",
            trades,
            [
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
                "risk_layer",
                "risk_return_pct",
                "risk_equity_before",
                "risk_pnl",
                "risk_equity_after",
            ],
        )
        save_csv(f"{prefix}_equity.csv", equity, ["time", "equity"])

    save_csv(
        os.path.join(ROOT, args.save_summary),
        rows,
        [
            "strategy",
            "period",
            "trades",
            "return_pct",
            "win_rate_pct",
            "profit_factor",
            "max_dd_pct",
            "final_equity",
        ],
    )

    for row in rows:
        pf = row["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.2f}"
        print(
            f"{row['strategy']} {row['period']}: "
            f"trades={row['trades']} "
            f"return={row['return_pct']:.2f}% "
            f"win={row['win_rate_pct']:.2f}% "
            f"PF={pf_text} "
            f"DD={row['max_dd_pct']:.2f}% "
            f"final=${row['final_equity']:.2f}"
        )
    print(f"saved summary: {args.save_summary}")


if __name__ == "__main__":
    main()
