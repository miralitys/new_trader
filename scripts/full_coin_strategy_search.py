#!/usr/bin/env python3
"""Full constrained search for one score-based coin strategy.

This is the heavier follow-up after the fast screening step. It searches the
same constrained family used for DOGE/SHIB/etc., then runs position sweep,
long-window validation, and execution stress for the selected candidate.
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
LONG_WINDOWS = [7, 30, 60, 90, 180, 365, 730]
INITIAL_BALANCE = 1000.0


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


def full_variants(symbol):
    variants = []
    for direction, thresholds in (("short", [40, 50, 60]), ("long", [50, 60, 70])):
        for threshold in thresholds:
            for regime in ("base", "wide"):
                for tp_pct in (0.0035, 0.0050, 0.0070, 0.0100, 0.0120):
                    for time_stop_min in (60, 90, 120, 180):
                        variants.append(
                            {
                                "symbol": symbol,
                                "direction": direction,
                                "threshold": threshold,
                                "regime": regime,
                                "position_pct": 1.0,
                                "tp_pct": tp_pct,
                                "sl_pct": 0.04,
                                "time_stop_min": time_stop_min,
                            }
                        )
    return variants


def make_windows(bt, candles, windows):
    output = {}
    for period in windows:
        bars = period * bt.candles_per_day("1m")
        if len(candles) >= bars:
            output[period] = candles[-bars:]
    return output


def flat_row(
    variant,
    period,
    summary,
    scenario="base_fee002_slip0",
    fee_pct=0.0002,
    slippage_pct=0.0,
    entry_mode="maker_limit",
    limit_entry_offset_pct=0.0,
):
    reasons = summary["exit_reasons"]
    return {
        **variant,
        "period": f"{period}d",
        "scenario": scenario,
        "fee_pct": fee_pct,
        "slippage_pct": slippage_pct,
        "entry_mode": entry_mode,
        "limit_entry_offset_pct": limit_entry_offset_pct,
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


def run_variant(
    bt,
    reinvest,
    multi,
    cf,
    windows,
    variant,
    period,
    fee_pct=0.0002,
    slippage_pct=0.0,
    entry_mode="maker_limit",
    limit_entry_offset_pct=0.0,
    limit_entry_timeout_min=1,
):
    candles = [dict(row) for row in windows[period]]
    cf.apply_single_signals(
        candles,
        variant["direction"],
        variant["threshold"],
        variant["regime"],
    )
    spec = {
        "coin": variant["symbol"].replace("USDT", ""),
        "symbol": variant["symbol"],
        "kind": "single",
        **variant,
    }
    args = cf.make_single_args(multi, reinvest, spec)
    args.fee_pct = fee_pct
    args.slippage_pct = slippage_pct
    args.entry_mode = entry_mode
    args.limit_entry_offset_pct = limit_entry_offset_pct
    args.limit_entry_timeout_min = limit_entry_timeout_min
    trades, equity, _ = bt.run_backtest(candles, args)
    return bt.summarize_trades(trades, INITIAL_BALANCE, equity)


def variant_summary(variant, rows):
    row365 = next(row for row in rows if row["period"] == "365d")
    return {
        **variant,
        "valid_all_windows": all(row["return_pct"] > 0 for row in rows),
        "positive_windows": sum(1 for row in rows if row["return_pct"] > 0),
        "return_7d_pct": next(row for row in rows if row["period"] == "7d")["return_pct"],
        "return_30d_pct": next(row for row in rows if row["period"] == "30d")["return_pct"],
        "return_60d_pct": next(row for row in rows if row["period"] == "60d")["return_pct"],
        "return_90d_pct": next(row for row in rows if row["period"] == "90d")["return_pct"],
        "return_180d_pct": next(row for row in rows if row["period"] == "180d")["return_pct"],
        "return_365d_pct": row365["return_pct"],
        "max_dd_365d_pct": row365["max_dd_pct"],
        "max_dd_any_pct": max(row["max_dd_pct"] for row in rows),
        "profit_factor_365d": row365["profit_factor"],
        "win_rate_365d_pct": row365["win_rate_pct"],
        "expectancy_365d_pct": row365["expectancy_pct"],
        "trades_365d": row365["trades"],
        "min_return_any_pct": min(row["return_pct"] for row in rows),
    }


def sort_summaries(rows):
    rows.sort(
        key=lambda row: (
            row["valid_all_windows"],
            row["positive_windows"],
            row["return_365d_pct"],
            row["profit_factor_365d"],
            -row["max_dd_any_pct"],
        ),
        reverse=True,
    )


def run_search(bt, reinvest, multi, cf, windows, variants, output_prefix):
    full_rows = []
    summary_rows = []
    started = time.time()
    for index, variant in enumerate(variants, start=1):
        rows = []
        for period in WINDOWS:
            summary = run_variant(bt, reinvest, multi, cf, windows, variant, period)
            row = flat_row(variant, period, summary)
            rows.append(row)
            full_rows.append(row)
        summary_rows.append(variant_summary(variant, rows))

        if index % 12 == 0 or index == len(variants):
            best = max(summary_rows, key=lambda row: row["return_365d_pct"])
            valid = [row for row in summary_rows if row["valid_all_windows"]]
            best_valid = max(valid, key=lambda row: row["return_365d_pct"]) if valid else None
            print(
                f"search {index}/{len(variants)} elapsed={time.time() - started:.1f}s "
                f"best365={best['return_365d_pct']:+.2f}% "
                f"valid_best={(best_valid['return_365d_pct'] if best_valid else 0):+.2f}%",
                flush=True,
            )

    sort_summaries(summary_rows)
    full_path = os.path.join(ROOT, "data", f"{output_prefix}_full_search_rows.csv")
    summary_path = os.path.join(ROOT, "data", f"{output_prefix}_full_search_summary.csv")
    save_csv(full_path, full_rows, list(full_rows[0].keys()))
    save_csv(summary_path, summary_rows, list(summary_rows[0].keys()))
    return summary_rows, full_rows, summary_path, full_path


def run_position_sweep(bt, reinvest, multi, cf, windows, best, output_prefix):
    rows = []
    for position_pct in (0.25, 0.35, 0.50, 0.65, 0.75, 1.00):
        variant = {
            key: best[key]
            for key in (
                "symbol",
                "direction",
                "threshold",
                "regime",
                "tp_pct",
                "sl_pct",
                "time_stop_min",
            )
        }
        variant["position_pct"] = position_pct
        period_rows = []
        for period in LONG_WINDOWS:
            if period not in windows:
                continue
            summary = run_variant(bt, reinvest, multi, cf, windows, variant, period)
            period_rows.append(flat_row(variant, period, summary))
        row365 = next(row for row in period_rows if row["period"] == "365d")
        output = {
            **variant,
            "return_7d_pct": next(row for row in period_rows if row["period"] == "7d")["return_pct"],
            "return_30d_pct": next(row for row in period_rows if row["period"] == "30d")["return_pct"],
            "return_60d_pct": next(row for row in period_rows if row["period"] == "60d")["return_pct"],
            "return_90d_pct": next(row for row in period_rows if row["period"] == "90d")["return_pct"],
            "return_180d_pct": next(row for row in period_rows if row["period"] == "180d")["return_pct"],
            "return_365d_pct": row365["return_pct"],
            "return_730d_pct": (
                next(row for row in period_rows if row["period"] == "730d")["return_pct"]
                if any(row["period"] == "730d" for row in period_rows)
                else None
            ),
            "max_dd_any_pct": max(row["max_dd_pct"] for row in period_rows),
            "max_dd_365d_pct": row365["max_dd_pct"],
            "max_dd_730d_pct": (
                next(row for row in period_rows if row["period"] == "730d")["max_dd_pct"]
                if any(row["period"] == "730d" for row in period_rows)
                else None
            ),
            "profit_factor_365d": row365["profit_factor"],
            "profit_factor_730d": (
                next(row for row in period_rows if row["period"] == "730d")["profit_factor"]
                if any(row["period"] == "730d" for row in period_rows)
                else None
            ),
            "win_rate_365d_pct": row365["win_rate_pct"],
            "trades_365d": row365["trades"],
            "positive_windows": sum(row["return_pct"] > 0 for row in period_rows),
            "min_return_any_pct": min(row["return_pct"] for row in period_rows),
        }
        rows.append(output)
        print(
            f"position {position_pct:.2f}: 365={output['return_365d_pct']:+.2f}% "
            f"730={output['return_730d_pct']:+.2f}% DDany={output['max_dd_any_pct']:.2f}% "
            f"PF730={output['profit_factor_730d']:.2f}",
            flush=True,
        )

    path = os.path.join(ROOT, "data", f"{output_prefix}_position_sweep_730.csv")
    save_csv(path, rows, list(rows[0].keys()))
    return rows, path


def run_stress(bt, reinvest, multi, cf, windows, best, output_prefix):
    scenarios = [
        {
            "name": "base_fee002_slip0",
            "fee_pct": 0.0002,
            "slippage_pct": 0.0,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "fee0025_slip0",
            "fee_pct": 0.00025,
            "slippage_pct": 0.0,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "fee003_slip0",
            "fee_pct": 0.0003,
            "slippage_pct": 0.0,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "fee004_slip0",
            "fee_pct": 0.0004,
            "slippage_pct": 0.0,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "fee002_slip0005",
            "fee_pct": 0.0002,
            "slippage_pct": 0.00005,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "strict_maker_005",
            "fee_pct": 0.0002,
            "slippage_pct": 0.0,
            "entry_mode": "maker_limit",
            "limit_entry_offset_pct": 0.0005,
            "limit_entry_timeout_min": 1,
        },
        {
            "name": "taker_like_fee004_slip002",
            "fee_pct": 0.0004,
            "slippage_pct": 0.0002,
            "entry_mode": "next_open",
            "limit_entry_offset_pct": 0.0,
            "limit_entry_timeout_min": 1,
        },
    ]
    rows = []
    variant = {
        key: best[key]
        for key in (
            "symbol",
            "direction",
            "threshold",
            "regime",
            "position_pct",
            "tp_pct",
            "sl_pct",
            "time_stop_min",
        )
    }
    for scenario in scenarios:
        for period in LONG_WINDOWS:
            if period not in windows:
                continue
            summary = run_variant(
                bt,
                reinvest,
                multi,
                cf,
                windows,
                variant,
                period,
                fee_pct=scenario["fee_pct"],
                slippage_pct=scenario["slippage_pct"],
                entry_mode=scenario["entry_mode"],
                limit_entry_offset_pct=scenario["limit_entry_offset_pct"],
                limit_entry_timeout_min=scenario["limit_entry_timeout_min"],
            )
            row = flat_row(
                variant,
                period,
                summary,
                scenario["name"],
                scenario["fee_pct"],
                scenario["slippage_pct"],
                scenario["entry_mode"],
                scenario["limit_entry_offset_pct"],
            )
            rows.append(row)
            if period in (365, 730):
                print(
                    f"stress {scenario['name']} {period}d: "
                    f"{row['return_pct']:+.2f}% DD={row['max_dd_pct']:.2f}% PF={row['profit_factor']:.2f}",
                    flush=True,
                )

    path = os.path.join(ROOT, "data", f"{output_prefix}_stress_730.csv")
    save_csv(path, rows, list(rows[0].keys()))
    return rows, path


def main():
    parser = argparse.ArgumentParser(description="Full constrained one-coin strategy search.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output-prefix", default="")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=7)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    output_prefix = args.output_prefix or symbol.lower().replace("usdt", "")

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)

    print(f"fetching {symbol} days={args.days} warmup={args.warmup_days}", flush=True)
    candles, _, _ = multi.fetch_klines_fast(symbol, args.days, args.warmup_days)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    print(
        f"candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}",
        flush=True,
    )

    windows = make_windows(bt, candles, LONG_WINDOWS)
    variants = full_variants(symbol)
    summary_rows, _, summary_path, full_path = run_search(
        bt, reinvest, multi, cf, windows, variants, output_prefix
    )
    best = summary_rows[0]
    print(
        "best full search: "
        f"{best['direction']} th{best['threshold']} {best['regime']} "
        f"tp={best['tp_pct'] * 100:.2f}% t={best['time_stop_min']} "
        f"valid={best['valid_all_windows']} 365={best['return_365d_pct']:+.2f}% "
        f"DDany={best['max_dd_any_pct']:.2f}% PF={best['profit_factor_365d']:.2f}",
        flush=True,
    )

    sweep_rows, sweep_path = run_position_sweep(bt, reinvest, multi, cf, windows, best, output_prefix)
    stress_rows, stress_path = run_stress(bt, reinvest, multi, cf, windows, best, output_prefix)

    print("saved:")
    print(summary_path)
    print(full_path)
    print(sweep_path)
    print(stress_path)


if __name__ == "__main__":
    main()
