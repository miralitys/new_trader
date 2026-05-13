#!/usr/bin/env python3
"""Collect top full-search variants into a strategy spec CSV."""

import argparse
import csv
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_first(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            return row
    return None


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Collect full-search leaders.")
    parser.add_argument("--symbols", nargs="*", required=True)
    parser.add_argument("--prefix-template", default="data/big_{symbol}_full_2026_05_04_full_search_summary.csv")
    parser.add_argument("--save-specs", default="data/big_new_coin_full_leader_specs.csv")
    parser.add_argument("--save-status", default="data/big_new_coin_full_leader_status.csv")
    args = parser.parse_args()

    specs = []
    statuses = []
    for symbol in [item.upper() for item in args.symbols]:
        path = os.path.join(ROOT, args.prefix_template.format(symbol=symbol.lower()))
        if not os.path.exists(path):
            statuses.append({"symbol": symbol, "status": "missing", "path": path, "error": "summary not found"})
            continue
        row = load_first(path)
        if not row:
            statuses.append({"symbol": symbol, "status": "empty", "path": path, "error": "summary empty"})
            continue
        specs.append(
            {
                "name": f"{symbol.replace('USDT', '')} full leader",
                "coin": symbol.replace("USDT", ""),
                "symbol": symbol,
                "kind": "single",
                "direction": row["direction"],
                "threshold": row["threshold"],
                "regime": row["regime"],
                "position_pct": row.get("position_pct", 1.0),
                "tp_pct": row["tp_pct"],
                "sl_pct": row["sl_pct"],
                "time_stop_min": row["time_stop_min"],
                "leader_from_new_screen": "1",
            }
        )
        statuses.append(
            {
                "symbol": symbol,
                "status": "ok",
                "path": path,
                "error": "",
                "direction": row["direction"],
                "threshold": row["threshold"],
                "regime": row["regime"],
                "tp_pct": row["tp_pct"],
                "sl_pct": row["sl_pct"],
                "time_stop_min": row["time_stop_min"],
                "return_365d_pct": row.get("return_365d_pct", ""),
                "max_dd_any_pct": row.get("max_dd_any_pct", ""),
                "profit_factor_365d": row.get("profit_factor_365d", ""),
                "positive_windows": row.get("positive_windows", ""),
            }
        )

    fields = [
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
    ]
    save_csv(os.path.join(ROOT, args.save_specs), specs, fields)
    save_csv(
        os.path.join(ROOT, args.save_status),
        statuses,
        [
            "symbol",
            "status",
            "path",
            "error",
            "direction",
            "threshold",
            "regime",
            "tp_pct",
            "sl_pct",
            "time_stop_min",
            "return_365d_pct",
            "max_dd_any_pct",
            "profit_factor_365d",
            "positive_windows",
        ],
    )
    print(f"collected full leaders: {len(specs)}")
    for row in specs:
        print(
            f"{row['symbol']} {row['direction']} th{row['threshold']} "
            f"{row['regime']} tp={float(row['tp_pct']) * 100:.2f}% t={row['time_stop_min']}"
        )
    print(f"saved specs: {os.path.join(ROOT, args.save_specs)}")
    print(f"saved status: {os.path.join(ROOT, args.save_status)}")


if __name__ == "__main__":
    main()
