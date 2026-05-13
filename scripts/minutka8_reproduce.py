#!/usr/bin/env python3
"""Local reproduction attempt for Minutka 8.

This script does not claim to know the original mb80/mb40/smart/momex rules.
It runs an explicit, reproducible portfolio approximation that was fitted
against the shared screenshots:

- GALAUSDT 1m LONG approximation.
- GALAUSDT 1m SHORT approximation.
- ALPINEUSDT 5m SHORT approximation.

The goal is to compare local, inspectable numbers with the external report.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKTEST_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("gala_mb_backtest", BACKTEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class ModuleConfig:
    name: str
    symbol: str
    interval: str
    direction: str
    threshold: float
    tp_pct: float
    sl_pct: float
    time_stop_min: int
    limit_timeout_min: int
    position_pct: float = 1.0
    signal_mode: str = "standard"
    cooldown_min: Optional[int] = None
    atr_filter_min_pct: Optional[float] = None
    rsi_max: Optional[float] = None
    fee_pct: Optional[float] = None
    slippage_pct: Optional[float] = None
    portfolio_weight: float = 1.0
    daily_loss_stop_pct: Optional[float] = None
    filter_atr_min_pct: Optional[float] = None
    filter_atr_max_pct: Optional[float] = None
    filter_dist_ema200_min: Optional[float] = None
    filter_dist_ema200_max: Optional[float] = None
    filter_return_1d_min: Optional[float] = None
    filter_return_1d_max: Optional[float] = None
    filter_return_7d_min: Optional[float] = None
    filter_return_7d_max: Optional[float] = None


MODULES_V1 = [
    ModuleConfig(
        name="GALA 1m LONG mb80+smart local",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=40,
        tp_pct=0.0025,
        sl_pct=0.0600,
        time_stop_min=90,
        limit_timeout_min=1,
    ),
    ModuleConfig(
        name="GALA 1m SHORT mb40 base local",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=55,
        tp_pct=0.0020,
        sl_pct=0.0150,
        time_stop_min=90,
        limit_timeout_min=1,
    ),
    ModuleConfig(
        name="ALPINE 5m SHORT momex local",
        symbol="ALPINEUSDT",
        interval="5m",
        direction="short",
        threshold=90,
        tp_pct=0.0035,
        sl_pct=0.0400,
        time_stop_min=360,
        limit_timeout_min=5,
    ),
]

MODULES_V2 = [
    ModuleConfig(
        name="GALA 1m LONG mb80+smart local v2",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=25,
        tp_pct=0.0025,
        sl_pct=0.0300,
        time_stop_min=720,
        limit_timeout_min=1,
        position_pct=0.765,
        signal_mode="cooldown",
        cooldown_min=19,
        atr_filter_min_pct=0.0012,
    ),
    ModuleConfig(
        name="GALA 1m SHORT mb40 base local v2",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=55,
        tp_pct=0.0020,
        sl_pct=0.0150,
        time_stop_min=90,
        limit_timeout_min=1,
        position_pct=1.16,
    ),
    ModuleConfig(
        name="ALPINE 5m SHORT momex local v2",
        symbol="ALPINEUSDT",
        interval="5m",
        direction="short",
        threshold=100,
        tp_pct=0.0035,
        sl_pct=0.0400,
        time_stop_min=720,
        limit_timeout_min=5,
        position_pct=0.935,
        signal_mode="cooldown",
        cooldown_min=900,
        rsi_max=35,
    ),
]

MODULES_V3 = [
    ModuleConfig(
        name="GALA 1m LONG mb80+smart local v2",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=25,
        tp_pct=0.0025,
        sl_pct=0.0300,
        time_stop_min=720,
        limit_timeout_min=1,
        position_pct=0.765,
        signal_mode="cooldown",
        cooldown_min=19,
        atr_filter_min_pct=0.0012,
    ),
    ModuleConfig(
        name="GALA 1m SHORT Minutka 7.3 x1.5",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=40,
        tp_pct=0.0028,
        sl_pct=0.0400,
        time_stop_min=120,
        limit_timeout_min=1,
        position_pct=0.24,
        fee_pct=0.0002,
        slippage_pct=0.0,
        portfolio_weight=1.5,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
    ModuleConfig(
        name="ALPINE 5m SHORT momex local v2",
        symbol="ALPINEUSDT",
        interval="5m",
        direction="short",
        threshold=100,
        tp_pct=0.0035,
        sl_pct=0.0400,
        time_stop_min=720,
        limit_timeout_min=5,
        position_pct=0.935,
        signal_mode="cooldown",
        cooldown_min=900,
        rsi_max=35,
    ),
]

MODULES_V4 = [
    ModuleConfig(
        name="GALA 1m LONG Minutka 10",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=50,
        tp_pct=0.0025,
        sl_pct=0.0400,
        time_stop_min=90,
        limit_timeout_min=1,
        position_pct=0.18,
        fee_pct=0.0002,
        slippage_pct=0.0,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
    ModuleConfig(
        name="GALA 1m SHORT Minutka 7.3 x1.5",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=40,
        tp_pct=0.0028,
        sl_pct=0.0400,
        time_stop_min=120,
        limit_timeout_min=1,
        position_pct=0.24,
        fee_pct=0.0002,
        slippage_pct=0.0,
        portfolio_weight=1.5,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
    ModuleConfig(
        name="ALPINE 5m SHORT momex local v2",
        symbol="ALPINEUSDT",
        interval="5m",
        direction="short",
        threshold=100,
        tp_pct=0.0035,
        sl_pct=0.0400,
        time_stop_min=720,
        limit_timeout_min=5,
        position_pct=0.935,
        signal_mode="cooldown",
        cooldown_min=900,
        rsi_max=35,
    ),
]

MODULES_V5 = [
    ModuleConfig(
        name="GALA 1m LONG Minutka 10",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=50,
        tp_pct=0.0025,
        sl_pct=0.0400,
        time_stop_min=90,
        limit_timeout_min=1,
        position_pct=0.18,
        fee_pct=0.0002,
        slippage_pct=0.0,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
    ModuleConfig(
        name="GALA 1m SHORT Minutka 7.3 x1.5",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=40,
        tp_pct=0.0028,
        sl_pct=0.0400,
        time_stop_min=120,
        limit_timeout_min=1,
        position_pct=0.24,
        fee_pct=0.0002,
        slippage_pct=0.0,
        portfolio_weight=1.5,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
]

MODULES_V6 = [
    ModuleConfig(
        name="GALA 1m LONG mb80+smart local v2",
        symbol="GALAUSDT",
        interval="1m",
        direction="long",
        threshold=25,
        tp_pct=0.0025,
        sl_pct=0.0300,
        time_stop_min=720,
        limit_timeout_min=1,
        position_pct=0.765,
        signal_mode="cooldown",
        cooldown_min=19,
        atr_filter_min_pct=0.0012,
    ),
    ModuleConfig(
        name="GALA 1m SHORT Minutka 7.3 x1.5",
        symbol="GALAUSDT",
        interval="1m",
        direction="short",
        threshold=40,
        tp_pct=0.0028,
        sl_pct=0.0400,
        time_stop_min=120,
        limit_timeout_min=1,
        position_pct=0.24,
        fee_pct=0.0002,
        slippage_pct=0.0,
        portfolio_weight=1.5,
        daily_loss_stop_pct=0.02,
        filter_atr_min_pct=0.0025,
        filter_dist_ema200_min=-0.015,
        filter_dist_ema200_max=0.015,
        filter_return_7d_min=-0.40,
        filter_return_7d_max=0.10,
    ),
]


TARGET_7D = {
    "GALA 1m LONG mb80+smart local": {"trades": 347, "win_rate": 93.9, "return": 21.10},
    "GALA 1m SHORT mb40 base local": {"trades": 370, "win_rate": 88.9, "return": 10.72},
    "ALPINE 5m SHORT momex local": {"trades": 6, "win_rate": 100.0, "return": 1.82},
    "GALA 1m LONG mb80+smart local v2": {"trades": 347, "win_rate": 93.9, "return": 21.10},
    "GALA 1m SHORT mb40 base local v2": {"trades": 370, "win_rate": 88.9, "return": 10.72},
    "ALPINE 5m SHORT momex local v2": {"trades": 6, "win_rate": 100.0, "return": 1.82},
    "PORTFOLIO": {"trades": 738, "win_rate": 90.5, "return": 31.46, "max_dd": 4.81},
}


def parse_args():
    parser = argparse.ArgumentParser(description="Reproduce Minutka 8 approximation locally.")
    parser.add_argument("--market", default="futures_archive")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--position-pct", type=float, default=1.0)
    parser.add_argument("--fee-pct", type=float, default=0.00014)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--entry-mode", choices=["maker_limit", "next_open"], default="maker_limit")
    parser.add_argument("--variant", choices=["v1", "v2", "v3", "v4", "v5", "v6"], default="v1")
    parser.add_argument("--portfolio-model", choices=["compound", "fixed_notional"], default="compound")
    parser.add_argument("--portfolio-scale", type=float, default=1.0)
    parser.add_argument("--portfolio-max-open", type=int, default=None)
    parser.add_argument("--portfolio-skip-end-of-data", action="store_true")
    parser.add_argument("--save-prefix", default="data/minutka8_repro")
    return parser.parse_args()


def make_args(bt, base_args, config):
    return argparse.Namespace(
        market=base_args.market,
        symbol=config.symbol,
        interval=config.interval,
        days=base_args.days,
        warmup_days=base_args.warmup_days,
        direction=config.direction,
        initial_balance=base_args.initial_balance,
        position_pct=base_args.position_pct * config.position_pct,
        fee_pct=config.fee_pct if config.fee_pct is not None else base_args.fee_pct,
        slippage_pct=(
            config.slippage_pct if config.slippage_pct is not None else base_args.slippage_pct
        ),
        entry_mode=base_args.entry_mode,
        limit_entry_offset_pct=0.0,
        limit_entry_timeout_min=config.limit_timeout_min,
        long_tp_pct=config.tp_pct,
        long_sl_pct=config.sl_pct,
        short_tp_pct=config.tp_pct,
        short_sl_pct=config.sl_pct,
        time_stop_min=config.time_stop_min,
        long_time_stop_min=config.time_stop_min,
        short_time_stop_min=config.time_stop_min,
        daily_loss_stop_pct=config.daily_loss_stop_pct,
        filter_atr_min_pct=config.filter_atr_min_pct,
        filter_atr_max_pct=config.filter_atr_max_pct,
        filter_dist_ema200_min=config.filter_dist_ema200_min,
        filter_dist_ema200_max=config.filter_dist_ema200_max,
        filter_return_1d_min=config.filter_return_1d_min,
        filter_return_1d_max=config.filter_return_1d_max,
        filter_return_7d_min=config.filter_return_7d_min,
        filter_return_7d_max=config.filter_return_7d_max,
        long_threshold=config.threshold,
        short_threshold=config.threshold,
        volume_multiplier=1.5,
        atr_min_pct=0.0015,
        atr_max_pct=0.0120,
    )


def value_in_optional_range(value, min_value, max_value):
    if min_value is None and max_value is None:
        return True
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def signal_passes_filters(row, config):
    if config.atr_filter_min_pct is not None:
        atr_pct = row.get("atr_pct")
        if atr_pct is None or atr_pct < config.atr_filter_min_pct:
            return False
    if config.rsi_max is not None:
        rsi14 = row.get("rsi14")
        if rsi14 is None or rsi14 >= config.rsi_max:
            return False
    if not value_in_optional_range(
        row.get("atr_pct"), config.filter_atr_min_pct, config.filter_atr_max_pct
    ):
        return False
    if not value_in_optional_range(
        row.get("dist_ema200"),
        config.filter_dist_ema200_min,
        config.filter_dist_ema200_max,
    ):
        return False
    if not value_in_optional_range(
        row.get("return_1d"), config.filter_return_1d_min, config.filter_return_1d_max
    ):
        return False
    if not value_in_optional_range(
        row.get("return_7d"), config.filter_return_7d_min, config.filter_return_7d_max
    ):
        return False
    return True


def force_module_signals(candles, config):
    for row in candles:
        row["long_signal"] = False
        row["short_signal"] = False
        if not signal_passes_filters(row, config):
            continue
        if config.direction == "long":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= config.threshold
                and bool(row.get("smart_long_filter"))
            )
        else:
            row["short_signal"] = row.get("short_score", 0.0) >= config.threshold


def run_module(bt, base_args, config):
    args = make_args(bt, base_args, config)
    fetch_days = args.days + max(0, args.warmup_days)
    candles = bt.fetch_klines(args.market, args.symbol, fetch_days, args.interval)
    bt.add_indicators_and_signals(candles, args)
    if args.warmup_days > 0:
        candles = candles[-args.days * bt.candles_per_day(args.interval) :]
    force_module_signals(candles, config)
    if config.signal_mode == "cooldown":
        trades, equity_curve, stats = run_cooldown_module(bt, candles, args, config)
        summary = summarize_trade_returns(trades, args.initial_balance, equity_curve)
    else:
        trades, equity_curve, stats = bt.run_backtest(candles, args)
        summary = bt.summarize_trades(trades, args.initial_balance, equity_curve)
    for trade in trades:
        trade["module"] = config.name
        trade["symbol"] = config.symbol
        trade["interval"] = config.interval
        trade["portfolio_weight"] = config.portfolio_weight
    return trades, equity_curve, stats, summary


def row_has_signal(row, config):
    if not signal_passes_filters(row, config):
        return False
    if config.direction == "long":
        return row.get("long_score", 0.0) >= config.threshold and bool(
            row.get("smart_long_filter")
        )
    return row.get("short_score", 0.0) >= config.threshold


def run_cooldown_module(bt, candles, args, config):
    trades = []
    stats = Counter()
    last_entry_idx = -10**9
    cooldown_bars = bt.minute_count_to_bars(config.cooldown_min or 1, config.interval)
    equity_curve = [{"time": candles[0]["open_time"], "equity": args.initial_balance}]

    for index in range(len(candles) - 1):
        if not row_has_signal(candles[index], config):
            continue
        entry_info, waited_until_idx = bt.find_entry_fill(candles, index, config.direction, args)
        stats["entry_signals"] += 1
        stats[f"{config.direction}_entry_signals"] += 1
        if entry_info is None:
            stats["unfilled_entry_orders"] += 1
            stats[f"{config.direction}_unfilled_entry_orders"] += 1
            continue
        if entry_info["entry_idx"] - last_entry_idx < cooldown_bars:
            stats["cooldown_skipped_orders"] += 1
            continue

        trade = bt.simulate_trade(candles, entry_info, config.direction, args.initial_balance, args)
        trades.append(trade)
        last_entry_idx = entry_info["entry_idx"]
        stats["filled_entry_orders"] += 1
        stats[f"{config.direction}_filled_entry_orders"] += 1

    equity = args.initial_balance
    for trade in sorted(trades, key=lambda row: (row["entry_time"], row["exit_time"])):
        equity *= 1.0 + trade["net_return_pct"] / 100.0
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

    return trades, equity_curve, stats


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    max_dd = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return max_dd


def summarize_trade_returns(trades, initial_balance, equity_curve):
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_balance
    winning_returns = [trade["net_return_pct"] for trade in trades if trade["net_return_pct"] > 0]
    losing_returns = [trade["net_return_pct"] for trade in trades if trade["net_return_pct"] < 0]
    gross_wins = sum(trade["pnl"] for trade in trades if trade["pnl"] > 0)
    gross_losses = abs(sum(trade["pnl"] for trade in trades if trade["pnl"] < 0))
    return {
        "total_trades": len(trades),
        "total_return_pct": (final_equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(winning_returns) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(trade["net_return_pct"] for trade in trades) / len(trades)
        if trades
        else 0.0,
        "total_fees_pct": sum(trade["fee_assumed_pct"] for trade in trades),
        "total_slippage_pct": sum(trade["slippage_assumed_pct"] for trade in trades),
        "exit_reasons": Counter(trade["reason"] for trade in trades),
        "final_equity": final_equity,
    }


def parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def select_portfolio_trades(trades, max_open=None, skip_end_of_data=False):
    selected = []
    open_trades = []
    for trade in sorted(trades, key=lambda row: (row["entry_time"], row["exit_time"])):
        if skip_end_of_data and trade["reason"] == "end_of_data":
            continue

        entry_time = parse_iso(trade["entry_time"])
        open_trades = [
            item for item in open_trades if parse_iso(item["exit_time"]) > entry_time
        ]
        if max_open is not None and len(open_trades) >= max_open:
            continue

        selected.append(trade)
        open_trades.append(trade)
    return selected


def build_portfolio(
    trades,
    initial_balance,
    portfolio_model="compound",
    portfolio_scale=1.0,
    portfolio_max_open=None,
    portfolio_skip_end_of_data=False,
):
    trades = select_portfolio_trades(
        trades,
        max_open=portfolio_max_open,
        skip_end_of_data=portfolio_skip_end_of_data,
    )
    equity = initial_balance
    equity_curve = [{"time": "initial", "equity": equity}]
    portfolio_trades = []

    for trade in sorted(trades, key=lambda row: (row["entry_time"], row["exit_time"])):
        equity_before = equity
        portfolio_weight = float(trade.get("portfolio_weight", 1.0))
        net_return_pct = float(trade["net_return_pct"]) * portfolio_scale * portfolio_weight
        if portfolio_model == "fixed_notional":
            pnl = initial_balance * net_return_pct / 100.0
        else:
            pnl = equity_before * net_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output["portfolio_model"] = portfolio_model
        output["portfolio_scale"] = portfolio_scale
        output["portfolio_weight"] = portfolio_weight
        output["portfolio_equity_before"] = equity_before
        output["portfolio_pnl"] = pnl
        output["portfolio_equity_after"] = equity
        portfolio_trades.append(output)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

    wins = [trade for trade in portfolio_trades if trade["portfolio_pnl"] > 0]
    losses = [trade for trade in portfolio_trades if trade["portfolio_pnl"] < 0]
    gross_wins = sum(trade["portfolio_pnl"] for trade in wins)
    gross_losses = abs(sum(trade["portfolio_pnl"] for trade in losses))

    summary = {
        "trades": len(portfolio_trades),
        "return_pct": (equity / initial_balance - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(portfolio_trades) * 100.0 if portfolio_trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_dd_pct": max_drawdown(equity_curve),
        "final_equity": equity,
        "exit_reasons": Counter(trade["reason"] for trade in portfolio_trades),
        "modules": Counter(trade["module"] for trade in portfolio_trades),
    }
    return portfolio_trades, equity_curve, summary


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    if value == math.inf:
        return "inf"
    return f"{value:.2f}"


def print_module(name, summary):
    target = TARGET_7D.get(name)
    print(f"{name}:")
    print(
        f"  local: trades={summary['total_trades']}, "
        f"win={summary['win_rate_pct']:.2f}%, "
        f"return={summary['total_return_pct']:.2f}%, "
        f"PF={fmt(summary['profit_factor'])}, "
        f"maxDD={summary['max_drawdown_pct']:.2f}%"
    )
    if target:
        print(
            f"  target screenshot: trades={target['trades']}, "
            f"win={target['win_rate']}%, return={target['return']}%"
        )
    print(f"  exits: {dict(summary['exit_reasons'])}")


def main():
    args = parse_args()
    bt = load_backtest_module()
    if args.variant == "v6":
        modules = MODULES_V6
    elif args.variant == "v5":
        modules = MODULES_V5
    elif args.variant == "v4":
        modules = MODULES_V4
    elif args.variant == "v3":
        modules = MODULES_V3
    elif args.variant == "v2":
        modules = MODULES_V2
    else:
        modules = MODULES_V1

    all_trades = []
    module_rows = []
    for config in modules:
        trades, equity_curve, stats, summary = run_module(bt, args, config)
        all_trades.extend(trades)
        print_module(config.name, summary)
        module_rows.append(
            {
                "module": config.name,
                "symbol": config.symbol,
                "interval": config.interval,
                "direction": config.direction,
                "threshold": config.threshold,
                "tp_pct": config.tp_pct,
                "sl_pct": config.sl_pct,
                "time_stop_min": config.time_stop_min,
                "position_pct": config.position_pct,
                "portfolio_weight": config.portfolio_weight,
                "fee_pct": config.fee_pct if config.fee_pct is not None else args.fee_pct,
                "slippage_pct": (
                    config.slippage_pct if config.slippage_pct is not None else args.slippage_pct
                ),
                "signal_mode": config.signal_mode,
                "cooldown_min": config.cooldown_min,
                "atr_filter_min_pct": config.atr_filter_min_pct,
                "rsi_max": config.rsi_max,
                "daily_loss_stop_pct": config.daily_loss_stop_pct,
                "filter_atr_min_pct": config.filter_atr_min_pct,
                "filter_atr_max_pct": config.filter_atr_max_pct,
                "filter_dist_ema200_min": config.filter_dist_ema200_min,
                "filter_dist_ema200_max": config.filter_dist_ema200_max,
                "filter_return_1d_min": config.filter_return_1d_min,
                "filter_return_1d_max": config.filter_return_1d_max,
                "filter_return_7d_min": config.filter_return_7d_min,
                "filter_return_7d_max": config.filter_return_7d_max,
                "trades": summary["total_trades"],
                "return_pct": summary["total_return_pct"],
                "win_rate_pct": summary["win_rate_pct"],
                "profit_factor": summary["profit_factor"],
                "max_dd_pct": summary["max_drawdown_pct"],
            }
        )

    portfolio_trades, portfolio_equity, portfolio = build_portfolio(
        all_trades,
        args.initial_balance,
        portfolio_model=args.portfolio_model,
        portfolio_scale=args.portfolio_scale,
        portfolio_max_open=args.portfolio_max_open,
        portfolio_skip_end_of_data=args.portfolio_skip_end_of_data,
    )
    target = TARGET_7D["PORTFOLIO"]
    print("PORTFOLIO:")
    print(
        f"  local: trades={portfolio['trades']}, "
        f"win={portfolio['win_rate_pct']:.2f}%, "
        f"return={portfolio['return_pct']:.2f}%, "
        f"PF={fmt(portfolio['profit_factor'])}, "
        f"maxDD={portfolio['max_dd_pct']:.2f}%, "
        f"final=${portfolio['final_equity']:.2f}"
    )
    print(
        f"  portfolio model: {args.portfolio_model}, "
        f"scale={args.portfolio_scale}, "
        f"max_open={args.portfolio_max_open}, "
        f"skip_end_of_data={args.portfolio_skip_end_of_data}"
    )
    print(
        f"  target screenshot: trades={target['trades']}, "
        f"win={target['win_rate']}%, return={target['return']}%, "
        f"maxDD={target['max_dd']}%"
    )
    print(f"  modules: {dict(portfolio['modules'])}")
    print(f"  exits: {dict(portfolio['exit_reasons'])}")

    risk_suffix = ""
    if (
        args.portfolio_model != "compound"
        or args.portfolio_scale != 1.0
        or args.portfolio_max_open is not None
        or args.portfolio_skip_end_of_data
    ):
        max_open_text = args.portfolio_max_open if args.portfolio_max_open is not None else "none"
        eod_text = "noeod" if args.portfolio_skip_end_of_data else "eod"
        risk_suffix = (
            f"_{args.portfolio_model}_scale{args.portfolio_scale:g}"
            f"_maxopen{max_open_text}_{eod_text}"
        )
    prefix = f"{args.save_prefix}_{args.variant}_{args.days}d{risk_suffix}"
    save_csv(
        f"{prefix}_modules.csv",
        module_rows,
        [
            "module",
            "symbol",
            "interval",
            "direction",
            "threshold",
            "tp_pct",
            "sl_pct",
            "time_stop_min",
            "position_pct",
            "portfolio_weight",
            "fee_pct",
            "slippage_pct",
            "signal_mode",
            "cooldown_min",
            "atr_filter_min_pct",
            "rsi_max",
            "daily_loss_stop_pct",
            "filter_atr_min_pct",
            "filter_atr_max_pct",
            "filter_dist_ema200_min",
            "filter_dist_ema200_max",
            "filter_return_1d_min",
            "filter_return_1d_max",
            "filter_return_7d_min",
            "filter_return_7d_max",
            "trades",
            "return_pct",
            "win_rate_pct",
            "profit_factor",
            "max_dd_pct",
        ],
    )
    save_csv(
        f"{prefix}_trades.csv",
        portfolio_trades,
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
            "portfolio_model",
            "portfolio_scale",
            "portfolio_weight",
            "portfolio_pnl",
            "portfolio_equity_after",
        ],
    )
    save_csv(f"{prefix}_equity.csv", portfolio_equity, ["time", "equity"])
    print(f"saved modules: {prefix}_modules.csv")
    print(f"saved trades: {prefix}_trades.csv")
    print(f"saved equity: {prefix}_equity.csv")


if __name__ == "__main__":
    main()
