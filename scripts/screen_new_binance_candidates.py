#!/usr/bin/env python3
"""Fast first-pass screening for new Binance Futures coin candidates.

This is intentionally smaller than the full strategy search. It tests only
strategy archetypes that already worked on earlier coins, then ranks candidates
for a later full search and cashflow integration.
"""

import argparse
import csv
import importlib.util
import math
import os
import time


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")

WINDOWS = [7, 30, 60, 90, 180, 365]
INITIAL_BALANCE = 1000.0

DEFAULT_SYMBOLS = [
    "1000LUNCUSDT",
    "XVGUSDT",
    "REZUSDT",
    "BBUSDT",
    "AIUSDT",
    "ZENUSDT",
    "KNCUSDT",
    "ORDIUSDT",
    "AXLUSDT",
    "RLCUSDT",
    "BATUSDT",
    "API3USDT",
    "DYDXUSDT",
    "INJUSDT",
    "ICPUSDT",
    "AXSUSDT",
    "TRBUSDT",
    "ONDOUSDT",
    "IOTAUSDT",
    "NOTUSDT",
    "FILUSDT",
    "NEOUSDT",
    "HYPEUSDT",
    "STRKUSDT",
    "SLPUSDT",
    "MINAUSDT",
    "RVNUSDT",
    "RUNEUSDT",
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def variant_key(row):
    return (
        row["symbol"],
        row["direction"],
        int(row["threshold"]),
        row["regime"],
        float(row["tp_pct"]),
        float(row["sl_pct"]),
        int(row["time_stop_min"]),
    )


def flat_row(symbol, variant, period, summary):
    reasons = summary["exit_reasons"]
    return {
        "symbol": symbol,
        **variant,
        "period": f"{period}d",
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
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "end_of_data": reasons["end_of_data"],
    }


def candidate_variants():
    variants = []

    def add(direction, threshold, regime, tp_pct, time_stop_min):
        item = {
            "direction": direction,
            "threshold": threshold,
            "regime": regime,
            "position_pct": 1.0,
            "tp_pct": tp_pct,
            "sl_pct": 0.04,
            "time_stop_min": time_stop_min,
        }
        if item not in variants:
            variants.append(item)

    # SHORT archetypes from SPELL/JASMY/BONK/PEPE/SAND/DOGE-style candidates.
    for threshold, regime, tp_pct, time_stop in [
        (40, "base", 0.0120, 90),
        (40, "base", 0.0120, 120),
        (40, "wide", 0.0070, 60),
        (40, "wide", 0.0100, 90),
        (40, "wide", 0.0120, 90),
        (50, "base", 0.0070, 60),
        (50, "base", 0.0100, 60),
        (50, "base", 0.0120, 60),
        (50, "wide", 0.0070, 60),
        (50, "wide", 0.0070, 90),
        (50, "wide", 0.0100, 90),
        (50, "wide", 0.0120, 120),
        (50, "wide", 0.0120, 180),
        (60, "base", 0.0070, 60),
        (60, "base", 0.0070, 180),
        (60, "base", 0.0100, 60),
        (60, "base", 0.0100, 90),
        (60, "base", 0.0100, 180),
        (60, "base", 0.0120, 60),
        (60, "base", 0.0120, 90),
        (60, "wide", 0.0070, 180),
        (60, "wide", 0.0100, 90),
        (60, "wide", 0.0120, 90),
    ]:
        add("short", threshold, regime, tp_pct, time_stop)

    # LONG archetypes from CHZ/SHIB/MANA/SAND/ANKR/ZIL-style candidates.
    for threshold, regime, tp_pct, time_stop in [
        (50, "base", 0.0050, 90),
        (50, "base", 0.0070, 120),
        (50, "base", 0.0070, 180),
        (50, "base", 0.0100, 120),
        (50, "base", 0.0100, 180),
        (50, "base", 0.0120, 120),
        (50, "wide", 0.0070, 120),
        (50, "wide", 0.0100, 90),
        (50, "wide", 0.0120, 90),
        (50, "wide", 0.0120, 120),
        (60, "base", 0.0050, 60),
        (60, "base", 0.0050, 180),
        (60, "base", 0.0070, 90),
        (60, "base", 0.0070, 180),
        (60, "base", 0.0100, 90),
        (60, "base", 0.0120, 120),
        (60, "base", 0.0120, 180),
        (70, "base", 0.0035, 180),
        (70, "base", 0.0050, 120),
        (70, "base", 0.0050, 180),
        (70, "base", 0.0070, 180),
        (70, "base", 0.0100, 60),
        (70, "base", 0.0100, 90),
        (70, "base", 0.0100, 120),
        (70, "base", 0.0100, 180),
        (70, "base", 0.0120, 60),
        (70, "base", 0.0120, 180),
    ]:
        add("long", threshold, regime, tp_pct, time_stop)

    return variants


def run_symbol(bt, reinvest, multi, cf, symbol, variants):
    candles, _, _ = multi.fetch_klines_fast(symbol, 365, 7)
    if not candles:
        raise RuntimeError("no candles")

    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)

    base_windows = {}
    for period in WINDOWS:
        bars = period * bt.candles_per_day("1m")
        base_windows[period] = candles[-bars:]

    rows = []
    for index, variant in enumerate(variants, start=1):
        period_rows = []
        for period in WINDOWS:
            period_candles = [dict(row) for row in base_windows[period]]
            spec = {
                "coin": symbol.replace("USDT", ""),
                "symbol": symbol,
                "kind": "single",
                **variant,
            }
            cf.apply_single_signals(
                period_candles,
                variant["direction"],
                variant["threshold"],
                variant["regime"],
            )
            args = cf.make_single_args(multi, reinvest, spec)
            trades, equity, _ = bt.run_backtest(period_candles, args)
            summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
            row = flat_row(symbol, variant, period, summary)
            rows.append(row)
            period_rows.append(row)

        if index % 10 == 0:
            best_so_far = max(
                (row for row in rows if row["period"] == "365d"),
                key=lambda item: item["return_pct"],
            )
            print(
                f"  {symbol} variants {index}/{len(variants)} "
                f"best365={best_so_far['return_pct']:+.2f}% "
                f"PF={best_so_far['profit_factor']:.2f}",
                flush=True,
            )

    return candles, rows


def summarize(rows):
    by_variant = {}
    for row in rows:
        by_variant.setdefault(variant_key(row), []).append(row)

    summaries = []
    for key, group in by_variant.items():
        if len(group) != len(WINDOWS):
            continue
        row365 = next(row for row in group if row["period"] == "365d")
        valid = all(row["return_pct"] > 0 for row in group)
        positive_windows = sum(1 for row in group if row["return_pct"] > 0)
        summaries.append(
            {
                "symbol": row365["symbol"],
                "direction": row365["direction"],
                "threshold": row365["threshold"],
                "regime": row365["regime"],
                "position_pct": row365["position_pct"],
                "tp_pct": row365["tp_pct"],
                "sl_pct": row365["sl_pct"],
                "time_stop_min": row365["time_stop_min"],
                "valid_all_windows": valid,
                "positive_windows": positive_windows,
                "return_7d_pct": next(row for row in group if row["period"] == "7d")["return_pct"],
                "return_30d_pct": next(row for row in group if row["period"] == "30d")["return_pct"],
                "return_60d_pct": next(row for row in group if row["period"] == "60d")["return_pct"],
                "return_90d_pct": next(row for row in group if row["period"] == "90d")["return_pct"],
                "return_180d_pct": next(row for row in group if row["period"] == "180d")["return_pct"],
                "return_365d_pct": row365["return_pct"],
                "max_dd_365d_pct": row365["max_dd_pct"],
                "max_dd_any_pct": max(row["max_dd_pct"] for row in group),
                "win_rate_365d_pct": row365["win_rate_pct"],
                "profit_factor_365d": row365["profit_factor"],
                "expectancy_365d_pct": row365["expectancy_pct"],
                "trades_365d": row365["trades"],
                "min_return_any_pct": min(row["return_pct"] for row in group),
            }
        )

    summaries.sort(
        key=lambda row: (
            row["valid_all_windows"],
            row["positive_windows"],
            row["return_365d_pct"],
            row["profit_factor_365d"],
            -row["max_dd_any_pct"],
        ),
        reverse=True,
    )
    return summaries


def main():
    parser = argparse.ArgumentParser(description="Screen new Binance candidates.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--output-prefix", default="new_candidates")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    variants = candidate_variants()

    all_rows = []
    summary_rows = []
    diagnostics = []
    for index, symbol in enumerate([item.upper() for item in args.symbols], start=1):
        print(f"\n=== [{index}/{len(args.symbols)}] {symbol} ===", flush=True)
        started = time.time()
        try:
            candles, rows = run_symbol(bt, reinvest, multi, cf, symbol, variants)
            all_rows.extend(rows)
            symbol_summary = summarize(rows)
            summary_rows.extend(symbol_summary)
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "ok",
                    "candles": len(candles),
                    "start": candles[0]["open_time"],
                    "end": candles[-1]["close_time"],
                    "variants": len(variants),
                    "elapsed_sec": round(time.time() - started, 1),
                    "error": "",
                }
            )
            best = symbol_summary[0] if symbol_summary else None
            if best:
                print(
                    f"best {symbol}: valid={best['valid_all_windows']} "
                    f"pos={best['positive_windows']}/6 "
                    f"365={best['return_365d_pct']:+.2f}% "
                    f"DDany={best['max_dd_any_pct']:.2f}% "
                    f"PF={best['profit_factor_365d']:.2f}",
                    flush=True,
                )
        except Exception as exc:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "error",
                    "candles": 0,
                    "start": "",
                    "end": "",
                    "variants": len(variants),
                    "elapsed_sec": round(time.time() - started, 1),
                    "error": str(exc),
                }
            )
            print(f"error {symbol}: {exc}", flush=True)

    summary_rows.sort(
        key=lambda row: (
            row["valid_all_windows"],
            row["positive_windows"],
            row["return_365d_pct"],
            row["profit_factor_365d"],
            -row["max_dd_any_pct"],
        ),
        reverse=True,
    )

    prefix = args.output_prefix
    all_path = os.path.join(ROOT, "data", f"{prefix}_screen_full.csv")
    summary_path = os.path.join(ROOT, "data", f"{prefix}_screen_summary.csv")
    diag_path = os.path.join(ROOT, "data", f"{prefix}_screen_diagnostics.csv")

    if all_rows:
        save_csv(all_path, all_rows, list(all_rows[0].keys()))
    if summary_rows:
        save_csv(summary_path, summary_rows, list(summary_rows[0].keys()))
    save_csv(
        diag_path,
        diagnostics,
        ["symbol", "status", "candles", "start", "end", "variants", "elapsed_sec", "error"],
    )

    print("\nTOP SCREEN RESULTS")
    for row in summary_rows[:30]:
        pf = row["profit_factor_365d"]
        pf_text = "inf" if pf == math.inf else f"{pf:.2f}"
        print(
            f"{row['symbol']} {row['direction']} th{row['threshold']} {row['regime']} "
            f"tp={row['tp_pct']*100:.2f}% t={row['time_stop_min']} "
            f"valid={row['valid_all_windows']} pos={row['positive_windows']}/6 "
            f"365={row['return_365d_pct']:+.2f}% DDany={row['max_dd_any_pct']:.2f}% "
            f"PF={pf_text} win={row['win_rate_365d_pct']:.2f}%"
        )
    print(f"saved: {summary_path}")
    print(f"saved: {all_path}")
    print(f"saved: {diag_path}")


if __name__ == "__main__":
    main()
