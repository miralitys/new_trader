#!/usr/bin/env python3
"""Select broad-filter leaders from a new-coin screen summary."""

import argparse
import csv
import os
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_bool(value):
    return str(value).lower() in {"1", "true", "yes", "y"}


def parse_float(row, key, default=0.0):
    value = row.get(key)
    if value in (None, ""):
        return default
    return float(value)


def parse_int(row, key, default=0):
    value = row.get(key)
    if value in (None, ""):
        return default
    return int(float(value))


def leader_passed(row):
    return (
        parse_float(row, "return_365d_pct") > 0.0
        and parse_float(row, "profit_factor_365d") >= 1.05
        and parse_int(row, "positive_windows") >= 5
    )


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Select broad-filter new coin leaders.")
    parser.add_argument("--screen-summary", required=True)
    parser.add_argument("--screen-diagnostics", default="")
    parser.add_argument("--save-leaders", default="data/big_new_coin_leaders.csv")
    parser.add_argument("--save-status", default="data/big_new_coin_status.csv")
    args = parser.parse_args()

    summary_path = os.path.join(ROOT, args.screen_summary)
    rows = load_rows(summary_path)
    by_symbol = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append(row)

    diagnostics = {}
    if args.screen_diagnostics:
        diag_path = os.path.join(ROOT, args.screen_diagnostics)
        if os.path.exists(diag_path):
            diagnostics = {row["symbol"]: row for row in load_rows(diag_path)}

    leader_rows = []
    status_rows = []
    for symbol, symbol_rows in sorted(by_symbol.items()):
        passed = [row for row in symbol_rows if leader_passed(row)]
        best = passed[0] if passed else symbol_rows[0]
        status = "leader" if passed else "watchlist" if parse_float(best, "return_365d_pct") > 0 else "reject"
        note = (
            "broad filter passed"
            if passed
            else "positive but broad filter failed"
            if status == "watchlist"
            else "best 365d return <= 0"
        )
        diag = diagnostics.get(symbol, {})
        status_rows.append(
            {
                "symbol": symbol,
                "status": status,
                "best_direction": best["direction"],
                "best_threshold": best["threshold"],
                "best_regime": best["regime"],
                "best_tp_pct": best["tp_pct"],
                "best_sl_pct": best["sl_pct"],
                "best_time_stop_min": best["time_stop_min"],
                "return_365d_pct": best["return_365d_pct"],
                "max_dd_any_pct": best["max_dd_any_pct"],
                "profit_factor_365d": best["profit_factor_365d"],
                "positive_windows": best["positive_windows"],
                "valid_all_windows": best["valid_all_windows"],
                "candles": diag.get("candles", ""),
                "data_start": diag.get("start", ""),
                "data_end": diag.get("end", ""),
                "note": note,
            }
        )
        if passed:
            leader_rows.append(
                {
                    "name": f"{symbol.replace('USDT', '')} leader",
                    "coin": symbol.replace("USDT", ""),
                    "symbol": symbol,
                    "kind": "single",
                    "direction": best["direction"],
                    "threshold": best["threshold"],
                    "regime": best["regime"],
                    "position_pct": best.get("position_pct", 1.0),
                    "tp_pct": best["tp_pct"],
                    "sl_pct": best["sl_pct"],
                    "time_stop_min": best["time_stop_min"],
                    "leader_from_new_screen": "1",
                }
            )

    save_csv(
        os.path.join(ROOT, args.save_leaders),
        leader_rows,
        [
            "name",
            "coin",
            "symbol",
            "kind",
            "direction",
            "threshold",
            "regime",
            "position_pct",
            "tp_pct",
            "sl_pct",
            "time_stop_min",
            "leader_from_new_screen",
        ],
    )
    save_csv(
        os.path.join(ROOT, args.save_status),
        status_rows,
        [
            "symbol",
            "status",
            "best_direction",
            "best_threshold",
            "best_regime",
            "best_tp_pct",
            "best_sl_pct",
            "best_time_stop_min",
            "return_365d_pct",
            "max_dd_any_pct",
            "profit_factor_365d",
            "positive_windows",
            "valid_all_windows",
            "candles",
            "data_start",
            "data_end",
            "note",
        ],
    )
    print(f"leaders: {len(leader_rows)}")
    for row in leader_rows:
        print(
            f"{row['symbol']} {row['direction']} th{row['threshold']} "
            f"{row['regime']} tp={float(row['tp_pct']) * 100:.2f}% t={row['time_stop_min']}"
        )
    print(f"saved leaders: {os.path.join(ROOT, args.save_leaders)}")
    print(f"saved status: {os.path.join(ROOT, args.save_status)}")


if __name__ == "__main__":
    main()
