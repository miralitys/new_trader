#!/usr/bin/env python3
"""Build a GALA/SPELL/AXL trade pool for monthly cashflow tests."""

import argparse
import importlib.util
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")


AXL_SPEC = {
    "coin": "AXL",
    "symbol": "AXLUSDT",
    "kind": "single",
    "direction": "short",
    "threshold": 40,
    "regime": "wide",
    "position_pct": 1.0,
    "tp_pct": 0.0100,
    "sl_pct": 0.0400,
    "time_stop_min": 180,
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Build GALA/SPELL plus AXL cashflow pool.")
    parser.add_argument("--days", type=int, default=733)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument(
        "--existing-path",
        default="data/cashflow_gala_spell_trades_36m.csv",
    )
    parser.add_argument(
        "--trades-path",
        default="data/cashflow_gala_spell_axl_trades_24m.csv",
    )
    args = parser.parse_args()

    cf = load_module("cashflow_portfolio", CF_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    existing_path = os.path.join(ROOT, args.existing_path)
    save_path = os.path.join(ROOT, args.trades_path)
    existing = cf.load_existing_trades(existing_path)
    print(f"loaded existing GALA/SPELL trades: {len(existing)}")

    print(
        f"Fetching/building AXL {AXL_SPEC['symbol']} "
        f"{AXL_SPEC['direction']} th{AXL_SPEC['threshold']} {AXL_SPEC['regime']}..."
    )
    candles, _, _ = multi.fetch_klines_fast(AXL_SPEC["symbol"], args.days, args.warmup_days)
    if not candles:
        raise RuntimeError("No AXL candles downloaded.")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", AXL_SPEC["symbol"])
    bt.add_indicators_and_signals(candles, indicator_args)
    test_bars = args.days * bt.candles_per_day("1m")
    candles = candles[-test_bars:]
    axl_trades = cf.build_single(bt, reinvest, multi, candles, AXL_SPEC)
    print(
        f"AXL candles={len(candles)} trades={len(axl_trades)} "
        f"{candles[0]['open_time']}..{candles[-1]['close_time']}"
    )

    all_trades = existing + axl_trades
    active_coins = sorted({trade["coin"] for trade in all_trades})
    allocation = 1.0 / len(active_coins) if active_coins else 0.0
    for trade in all_trades:
        trade["allocation"] = allocation
        trade["portfolio_return_pct"] = trade["raw_return_pct"] * allocation

    all_trades.sort(key=lambda item: (item["entry_dt"], item["exit_dt"], item["coin"]))
    fields = [
        "coin",
        "symbol",
        "strategy",
        "direction",
        "module",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "allocation",
        "portfolio_return_pct",
    ]
    cf.save_csv(save_path, all_trades, fields)
    cf.save_csv(
        os.path.splitext(save_path)[0] + "_diagnostics.csv",
        [
            {
                "coin": "AXL",
                "symbol": AXL_SPEC["symbol"],
                "status": "ok",
                "candles": len(candles),
                "start": candles[0]["open_time"],
                "end": candles[-1]["close_time"],
                "trades": len(axl_trades),
                "error": "",
            }
        ],
        ["coin", "symbol", "status", "candles", "start", "end", "trades", "error"],
    )
    print(f"saved trades: {save_path}")
    print(f"active coins: {','.join(active_coins)}")
    print(f"total trades: {len(all_trades)}")


if __name__ == "__main__":
    main()
