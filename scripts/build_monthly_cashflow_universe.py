#!/usr/bin/env python3
"""Build a wider monthly-cashflow trade universe.

The fixed cashflow portfolio only uses the accepted "best" coins. This helper
adds paper/rejected candidates too, so we can test whether the monthly cashflow
method transfers beyond the current GALA/SPELL core.
"""

import argparse
import importlib.util
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UNIVERSE_SPECS = [
    # Accepted/core modules.
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
    {"coin": "ONE", "symbol": "ONEUSDT", "kind": "gala_112"},
    {
        "coin": "CHZ",
        "symbol": "CHZUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "coin": "SHIB",
        "symbol": "1000SHIBUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "JASMY",
        "symbol": "JASMYUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 0.90,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "SAND",
        "symbol": "SANDUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "MANA",
        "symbol": "MANAUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
    {
        "coin": "ANKR",
        "symbol": "ANKRUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 120,
    },
    {
        "coin": "SPELL",
        "symbol": "SPELLUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
    # Extra paper candidates. These were not accepted as "best" because their
    # standalone stress profiles are weak, but they may still diversify monthly
    # cashflow. The search result must prove that; they do not get a free pass.
    {
        "coin": "APE",
        "symbol": "APEUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "coin": "BONK",
        "symbol": "1000BONKUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 40,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "coin": "COTI",
        "symbol": "COTIUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0070,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "DOGE",
        "symbol": "DOGEUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 50,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 120,
    },
    {
        "coin": "IOTX",
        "symbol": "IOTXUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 120,
    },
    {
        "coin": "PEPE",
        "symbol": "1000PEPEUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 40,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "coin": "ZIL",
        "symbol": "ZILUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0070,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
]


def main():
    parser = argparse.ArgumentParser(description="Build wider monthly-cashflow trade universe.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument(
        "--trades-path",
        default="data/monthly_cashflow_universe_trades_24m.csv",
    )
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()

    cf = load_module("cashflow_portfolio", CF_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    save_path = os.path.join(ROOT, args.trades_path)
    if args.reuse_existing:
        existing = cf.load_existing_trades(save_path)
        if existing:
            print(f"reused trades: {len(existing)} from {save_path}")
            return

    all_trades = []
    diagnostics = []
    for spec in UNIVERSE_SPECS:
        print(f"Fetching/building {spec['coin']} {spec['symbol']} {spec['kind']}...")
        try:
            candles, _, _ = multi.fetch_klines_fast(spec["symbol"], args.days, args.warmup_days)
            if not candles:
                raise RuntimeError("no candles")
            indicator_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
            bt.add_indicators_and_signals(candles, indicator_args)
            test_bars = args.days * bt.candles_per_day("1m")
            candles = candles[-test_bars:]
            if spec["kind"] == "gala_112":
                trades = cf.build_gala_112(bt, reinvest, multi, candles, spec)
            else:
                trades = cf.build_single(bt, reinvest, multi, candles, spec)
            all_trades.extend(trades)
            diagnostics.append(
                {
                    "coin": spec["coin"],
                    "symbol": spec["symbol"],
                    "status": "ok",
                    "candles": len(candles),
                    "start": candles[0]["open_time"],
                    "end": candles[-1]["close_time"],
                    "trades": len(trades),
                    "error": "",
                }
            )
            print(
                f"  ok candles={len(candles)} trades={len(trades)} "
                f"{candles[0]['open_time']}..{candles[-1]['close_time']}"
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "coin": spec["coin"],
                    "symbol": spec["symbol"],
                    "status": "error",
                    "candles": 0,
                    "start": "",
                    "end": "",
                    "trades": 0,
                    "error": str(exc),
                }
            )
            print(f"  error {spec['coin']}: {exc}")

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
        diagnostics,
        ["coin", "symbol", "status", "candles", "start", "end", "trades", "error"],
    )
    print(f"saved trades: {save_path}")
    print(f"active coins: {','.join(active_coins)}")
    print(f"total trades: {len(all_trades)}")


if __name__ == "__main__":
    main()
