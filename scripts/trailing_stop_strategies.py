#!/usr/bin/env python3
"""Backtest trailing-exit versions of the current winning Minutka strategies.

New variants:
- 7.4 = 7.3 SHORT with TP1 + breakeven + trailing runner.
- 10.1 = 10 LONG with TP1 + breakeven + trailing runner.
- 11.3 = 11.2 compound portfolio using trailing 7.4/10.1 modules.

This is a first reproducible trailing approximation, not parameter optimization.
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
CANDLES_PATH = os.path.join(ROOT, "data", "strategy7_365d_candles.csv")
WINDOWS = [30, 60, 90, 180, 365]


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


def make_args(strategy, initial_balance, trailing_pct, tp1_fraction):
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
        "weekly_loss_stop_pct": None,
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
        "trailing_pct": trailing_pct,
        "tp1_fraction": tp1_fraction,
        "breakeven_buffer_pct": 0.0004,
    }
    if strategy == "minutka_7_4":
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
    elif strategy == "minutka_10_1":
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


def trailing_stop_from_extreme(direction, extreme, args):
    if direction == "long":
        return extreme * (1.0 - args.trailing_pct)
    return extreme * (1.0 + args.trailing_pct)


def breakeven_stop(direction, entry_fill, args):
    if direction == "long":
        return entry_fill * (1.0 + args.breakeven_buffer_pct)
    return entry_fill * (1.0 - args.breakeven_buffer_pct)


def better_stop(direction, current, candidate):
    if current is None:
        return candidate
    if direction == "long":
        return max(current, candidate)
    return min(current, candidate)


def simulate_trailing_trade(bt, candles, entry_info, direction, equity_before, args):
    entry_idx = entry_info["entry_idx"]
    entry_fill = entry_info["entry_fill"]

    if direction == "long":
        tp_level = entry_fill * (1.0 + args.long_tp_pct)
        initial_sl_level = entry_fill * (1.0 - args.long_sl_pct)
        time_stop_min = args.long_time_stop_min or args.time_stop_min
    else:
        tp_level = entry_fill * (1.0 - args.short_tp_pct)
        initial_sl_level = entry_fill * (1.0 + args.short_sl_pct)
        time_stop_min = args.short_time_stop_min or args.time_stop_min

    position_notional = equity_before * args.position_pct
    quantity = position_notional / entry_fill if entry_fill > 0 else 0.0
    remaining_qty = quantity
    tp1_qty = quantity * args.tp1_fraction
    runner_qty = quantity - tp1_qty
    exits = []

    activated = False
    activation_time = ""
    trailing_stop = None
    extreme = entry_fill
    best_price = entry_fill
    exit_idx = len(candles) - 1
    reason = "end_of_data"

    for index in range(entry_idx, len(candles)):
        row = candles[index]
        elapsed_min = (index - entry_idx + 1) * bt.interval_minutes(args.interval)

        if direction == "long":
            best_price = max(best_price, row["high"])
        else:
            best_price = min(best_price, row["low"])

        if not activated:
            if direction == "long":
                stop_hit = row["low"] <= initial_sl_level
                target_hit = row["high"] >= tp_level
            else:
                stop_hit = row["high"] >= initial_sl_level
                target_hit = row["low"] <= tp_level

            if args.entry_mode == "maker_limit" and index == entry_idx:
                target_hit = False

            if stop_hit:
                exit_idx = index
                exit_fill = bt.apply_exit_slippage(direction, initial_sl_level, args.slippage_pct)
                exits.append((remaining_qty, exit_fill))
                remaining_qty = 0.0
                reason = "stop_loss"
                break

            if target_hit:
                exit_fill = bt.apply_exit_slippage(direction, tp_level, args.slippage_pct)
                exits.append((tp1_qty, exit_fill))
                remaining_qty = runner_qty
                activated = True
                activation_time = row["close_time"]
                if direction == "long":
                    extreme = max(entry_fill, row["high"])
                else:
                    extreme = min(entry_fill, row["low"])
                trailing_stop = better_stop(
                    direction,
                    breakeven_stop(direction, entry_fill, args),
                    trailing_stop_from_extreme(direction, extreme, args),
                )
                if remaining_qty <= 0:
                    exit_idx = index
                    reason = "take_profit"
                    break
                continue

            if elapsed_min >= time_stop_min:
                exit_idx = index
                exit_fill = bt.apply_exit_slippage(direction, row["close"], args.slippage_pct)
                exits.append((remaining_qty, exit_fill))
                remaining_qty = 0.0
                reason = "time_stop"
                break

            continue

        if direction == "long":
            trailing_hit = row["low"] <= trailing_stop
        else:
            trailing_hit = row["high"] >= trailing_stop

        if trailing_hit:
            exit_idx = index
            exit_fill = bt.apply_exit_slippage(direction, trailing_stop, args.slippage_pct)
            exits.append((remaining_qty, exit_fill))
            remaining_qty = 0.0
            reason = "tp1_trailing_stop"
            break

        if direction == "long":
            extreme = max(extreme, row["high"])
        else:
            extreme = min(extreme, row["low"])
        trailing_stop = better_stop(
            direction,
            trailing_stop,
            trailing_stop_from_extreme(direction, extreme, args),
        )
        trailing_stop = better_stop(
            direction,
            trailing_stop,
            breakeven_stop(direction, entry_fill, args),
        )

        if elapsed_min >= time_stop_min:
            exit_idx = index
            exit_fill = bt.apply_exit_slippage(direction, row["close"], args.slippage_pct)
            exits.append((remaining_qty, exit_fill))
            remaining_qty = 0.0
            reason = "tp1_time_stop"
            break

    if remaining_qty > 0:
        exit_idx = len(candles) - 1
        exit_fill = bt.apply_exit_slippage(direction, candles[-1]["close"], args.slippage_pct)
        exits.append((remaining_qty, exit_fill))
        reason = "tp1_end_of_data" if activated else "end_of_data"

    gross_pnl = 0.0
    exit_notional = 0.0
    weighted_exit = 0.0
    for qty, fill in exits:
        weighted_exit += qty * fill
        exit_notional += qty * fill
        if direction == "long":
            gross_pnl += (fill - entry_fill) * qty
        else:
            gross_pnl += (entry_fill - fill) * qty

    entry_fee = position_notional * args.fee_pct
    exit_fee = exit_notional * args.fee_pct
    fee_paid = entry_fee + exit_fee
    net_pnl = gross_pnl - fee_paid
    equity_after = equity_before + net_pnl
    avg_exit = weighted_exit / quantity if quantity else 0.0
    gross_return_pct = gross_pnl / equity_before * 100.0 if equity_before else 0.0
    net_return_pct = net_pnl / equity_before * 100.0 if equity_before else 0.0

    if direction == "long":
        mfe_price_return = best_price / entry_fill - 1.0
    else:
        mfe_price_return = entry_fill / best_price - 1.0 if best_price else 0.0
    mfe_return_pct = mfe_price_return * args.position_pct * 100.0
    missed_return_pct = max(0.0, mfe_return_pct - net_return_pct)

    return {
        "direction": direction,
        "entry_mode": args.entry_mode,
        "signal_time": entry_info["signal_time"],
        "order_start_time": entry_info["order_start_time"],
        "entry_time": entry_info["entry_time"],
        "exit_time": candles[exit_idx]["close_time"],
        "entry": entry_fill,
        "exit": avg_exit,
        "limit_price": entry_info["limit_price"],
        "fill_delay_min": entry_info["fill_delay_min"],
        "reason": reason,
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "pnl": net_pnl,
        "duration_min": (exit_idx - entry_idx + 1) * bt.interval_minutes(args.interval),
        "equity_before": equity_before,
        "equity_after": equity_after,
        "exit_idx": exit_idx,
        "tp1_fraction": args.tp1_fraction,
        "tp1_level": tp_level,
        "trailing_pct": args.trailing_pct,
        "trailing_activated": activated,
        "activation_time": activation_time,
        "best_price": best_price,
        "mfe_return_pct": mfe_return_pct,
        "missed_return_pct": missed_return_pct,
    }


def run_trailing_backtest(bt, candles, args):
    trades = []
    equity = args.initial_balance
    equity_curve = []
    stats = Counter()
    killed_days = set()
    day_start_equity = {}

    if candles:
        equity_curve.append({"time": candles[0]["open_time"], "equity": equity})

    index = 0
    while index < len(candles) - 1:
        signal_day = candles[index]["open_time"][:10]
        if signal_day not in day_start_equity:
            day_start_equity[signal_day] = equity
        if signal_day in killed_days:
            stats["daily_loss_stop_skipped_candles"] += 1
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
        trade = simulate_trailing_trade(bt, candles, entry_info, direction, equity, args)
        equity = trade["equity_after"]
        trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

        exit_day = trade["exit_time"][:10]
        if exit_day not in day_start_equity:
            day_start_equity[exit_day] = trade["equity_before"]
        if args.daily_loss_stop_pct is not None and args.daily_loss_stop_pct > 0:
            daily_return = equity / day_start_equity[exit_day] - 1.0
            if daily_return <= -args.daily_loss_stop_pct and exit_day not in killed_days:
                killed_days.add(exit_day)
                stats["daily_loss_stop_events"] += 1
                stats[f"{direction}_daily_loss_stop_events"] += 1

        index = trade["exit_idx"] + 1

    return trades, equity_curve, stats


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def summarize_trades(trades, initial_balance, equity_curve, pnl_key="pnl"):
    wins = [trade for trade in trades if trade[pnl_key] > 0]
    losses = [trade for trade in trades if trade[pnl_key] < 0]
    gross_wins = sum(trade[pnl_key] for trade in wins)
    gross_losses = abs(sum(trade[pnl_key] for trade in losses))
    returns = [trade["net_return_pct"] for trade in trades]
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
        "avg_duration_min": sum(trade["duration_min"] for trade in trades) / len(trades)
        if trades
        else 0.0,
        "avg_missed_return_pct": sum(trade.get("missed_return_pct", 0.0) for trade in trades)
        / len(trades)
        if trades
        else 0.0,
        "tp1_activated": sum(1 for trade in trades if trade.get("trailing_activated")),
        "final_equity": final_equity,
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_module(bt, candles, strategy, days, initial_balance, trailing_pct, tp1_fraction):
    bars = days * bt.candles_per_day("1m")
    window = [dict(row) for row in candles[-bars:]]
    if strategy == "minutka_7_4":
        apply_minutka73_signals(window)
    elif strategy == "minutka_10_1":
        apply_minutka10_signals(window)
    args = make_args(strategy, initial_balance, trailing_pct, tp1_fraction)
    trades, equity, stats = run_trailing_backtest(bt, window, args)
    summary = summarize_trades(trades, initial_balance, equity)
    return trades, equity, stats, summary


def build_portfolio(trades, initial_balance, portfolio_scale=0.9):
    selected = []
    open_trades = []
    equity = initial_balance
    equity_curve = [{"time": "initial", "equity": equity}]
    for trade in sorted(trades, key=lambda item: (parse_time(item["entry_time"]), parse_time(item["exit_time"]))):
        entry_dt = parse_time(trade["entry_time"])
        open_trades = [item for item in open_trades if parse_time(item["exit_time"]) > entry_dt]
        if open_trades:
            continue

        portfolio_weight = trade["portfolio_weight"]
        adjusted_return_pct = trade["net_return_pct"] * portfolio_scale * portfolio_weight
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output["portfolio_scale"] = portfolio_scale
        output["portfolio_weight"] = portfolio_weight
        output["portfolio_return_pct"] = adjusted_return_pct
        output["portfolio_pnl"] = pnl
        output["portfolio_equity_before"] = equity_before
        output["portfolio_equity_after"] = equity
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})
    return selected, equity_curve


def summarize_portfolio(trades, initial_balance, equity_curve):
    wins = [trade for trade in trades if trade["portfolio_pnl"] > 0]
    losses = [trade for trade in trades if trade["portfolio_pnl"] < 0]
    gross_wins = sum(trade["portfolio_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["portfolio_pnl"] for trade in losses))
    returns = [trade["portfolio_return_pct"] for trade in trades]
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
        "avg_duration_min": sum(trade["duration_min"] for trade in trades) / len(trades)
        if trades
        else 0.0,
        "avg_missed_return_pct": sum(trade.get("missed_return_pct", 0.0) for trade in trades)
        / len(trades)
        if trades
        else 0.0,
        "tp1_activated": sum(1 for trade in trades if trade.get("trailing_activated")),
        "final_equity": final_equity,
    }


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


def row_from_summary(strategy, period, summary, trades, module_counts=None):
    reasons = reason_counts(trades)
    row = {
        "strategy": strategy,
        "period": f"{period}d",
        "trades": summary["trades"],
        "return_pct": summary["return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_dd_pct"],
        "avg_win_pct": summary["avg_win_pct"],
        "avg_loss_pct": summary["avg_loss_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "avg_duration_min": summary["avg_duration_min"],
        "avg_missed_return_pct": summary["avg_missed_return_pct"],
        "tp1_activated": summary["tp1_activated"],
        "final_equity": summary["final_equity"],
        **reasons,
    }
    if module_counts:
        row.update(module_counts)
    return row


def write_trade_artifacts(prefix, trades, equity):
    save_csv(
        f"{prefix}_trades.csv",
        trades,
        [
            "module",
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
            "portfolio_return_pct",
            "pnl",
            "portfolio_pnl",
            "duration_min",
            "equity_after",
            "portfolio_equity_after",
            "tp1_fraction",
            "tp1_level",
            "trailing_pct",
            "trailing_activated",
            "activation_time",
            "best_price",
            "mfe_return_pct",
            "missed_return_pct",
        ],
    )
    save_csv(f"{prefix}_equity.csv", equity, ["time", "equity"])


def main():
    parser = argparse.ArgumentParser(description="Backtest trailing-stop Minutka variants.")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--trailing-pct", type=float, default=0.0015)
    parser.add_argument("--tp1-fraction", type=float, default=0.50)
    parser.add_argument("--save-summary", default="data/trailing_stop_summary.csv")
    args = parser.parse_args()

    bt = load_backtest_module()
    candles = load_candles(CANDLES_PATH)
    rows = []

    for days in WINDOWS:
        short_trades, short_equity, _, short_summary = run_module(
            bt, candles, "minutka_7_4", days, args.initial_balance, args.trailing_pct, args.tp1_fraction
        )
        for trade in short_trades:
            trade["module"] = "GALA 1m SHORT Minutka 7.4 trailing"
            trade["portfolio_weight"] = 1.5
        rows.append(row_from_summary("7.4", days, short_summary, short_trades))
        write_trade_artifacts(
            os.path.join(ROOT, "data", f"trailing_stop_7_4_{days}d"),
            short_trades,
            short_equity,
        )

        long_trades, long_equity, _, long_summary = run_module(
            bt, candles, "minutka_10_1", days, args.initial_balance, args.trailing_pct, args.tp1_fraction
        )
        for trade in long_trades:
            trade["module"] = "GALA 1m LONG Minutka 10.1 trailing"
            trade["portfolio_weight"] = 1.0
        rows.append(row_from_summary("10.1", days, long_summary, long_trades))
        write_trade_artifacts(
            os.path.join(ROOT, "data", f"trailing_stop_10_1_{days}d"),
            long_trades,
            long_equity,
        )

        portfolio_trades, portfolio_equity = build_portfolio(
            short_trades + long_trades,
            args.initial_balance,
            portfolio_scale=0.9,
        )
        portfolio_summary = summarize_portfolio(portfolio_trades, args.initial_balance, portfolio_equity)
        module_counts = {
            "long_trades": sum(1 for trade in portfolio_trades if trade["direction"] == "long"),
            "short_trades": sum(1 for trade in portfolio_trades if trade["direction"] == "short"),
        }
        rows.append(row_from_summary("11.3", days, portfolio_summary, portfolio_trades, module_counts))
        write_trade_artifacts(
            os.path.join(ROOT, "data", f"trailing_stop_11_3_{days}d"),
            portfolio_trades,
            portfolio_equity,
        )

    fields = [
        "strategy",
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
        "avg_missed_return_pct",
        "tp1_activated",
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
        pf = row["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.2f}"
        print(
            f"{row['strategy']} {row['period']}: trades={row['trades']} "
            f"return={row['return_pct']:.2f}% win={row['win_rate_pct']:.2f}% "
            f"PF={pf_text} DD={row['max_dd_pct']:.2f}% "
            f"avg_dur={row['avg_duration_min']:.1f}m "
            f"tp1={row['tp1_activated']} final=${row['final_equity']:.2f}"
        )
    print(f"saved summary: {args.save_summary}")


if __name__ == "__main__":
    main()
