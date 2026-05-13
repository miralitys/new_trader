#!/usr/bin/env python3
"""Append strategy specs to an existing cashflow trade pool."""

import argparse
import csv
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


def load_specs(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "coin": row["coin"],
                    "symbol": row["symbol"],
                    "kind": row.get("kind", "single"),
                    "direction": row["direction"],
                    "threshold": int(float(row["threshold"])),
                    "regime": row["regime"],
                    "position_pct": float(row.get("position_pct", 1.0)),
                    "tp_pct": float(row["tp_pct"]),
                    "sl_pct": float(row.get("sl_pct", 0.04)),
                    "time_stop_min": int(float(row["time_stop_min"])),
                    "strategy_name": row.get("name") or f"{row['coin']} leader",
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Build cashflow pool with extra specs.")
    parser.add_argument("--specs", required=True)
    parser.add_argument("--existing-path", default="data/cashflow_portfolio_best_trades_24m.csv")
    parser.add_argument("--trades-path", default="data/big_cashflow_with_new_leaders_trades_24m.csv")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=7)
    args = parser.parse_args()

    cf = load_module("cashflow_portfolio", CF_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    specs = load_specs(os.path.join(ROOT, args.specs))
    all_trades = cf.load_existing_trades(os.path.join(ROOT, args.existing_path))
    diagnostics = []
    print(f"loaded existing trades: {len(all_trades)}")

    for index, spec in enumerate(specs, start=1):
        print(f"[{index}/{len(specs)}] building {spec['coin']} {spec['symbol']} {spec['strategy_name']}", flush=True)
        try:
            candles, _, _ = multi.fetch_klines_fast(spec["symbol"], args.days, args.warmup_days)
            if not candles:
                raise RuntimeError("no candles")
            indicator_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
            bt.add_indicators_and_signals(candles, indicator_args)
            test_bars = args.days * bt.candles_per_day("1m")
            candles = candles[-test_bars:]
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
            print(f"  ok trades={len(trades)}", flush=True)
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
            print(f"  error {spec['symbol']}: {exc}", flush=True)

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
    cf.save_csv(os.path.join(ROOT, args.trades_path), all_trades, fields)
    cf.save_csv(
        os.path.splitext(os.path.join(ROOT, args.trades_path))[0] + "_diagnostics.csv",
        diagnostics,
        ["coin", "symbol", "status", "candles", "start", "end", "trades", "error"],
    )
    print(f"saved trades: {os.path.join(ROOT, args.trades_path)}")
    print(f"active coins: {','.join(active_coins)}")
    print(f"total trades: {len(all_trades)}")


if __name__ == "__main__":
    main()
