#!/usr/bin/env python3
"""Maker-limit fill-rate check for the selected4 portfolio strategies."""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

import overnight_strategy_research as ov
import selected4_protection_deep_test as s4


SYMBOLS = ["ALICEUSDT", "DYDXUSDT", "REZUSDT", "TAOUSDT"]
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Check maker-limit fill rates for selected4.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--summary", default=f"data/selected4_protection_summary_{today}.csv")
    parser.add_argument("--offsets", type=float, nargs="+", default=[0.0, 0.0002, 0.0005, 0.0010])
    parser.add_argument("--timeouts", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--save", default=f"data/selected4_maker_fill_rate_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected4-maker-fill-rate-{today}.md")
    return parser.parse_args()


def selected_variants(summary_path):
    df = pd.read_csv(summary_path)
    df = s4.score_frame(df)
    out = {}
    for symbol, group in df.groupby("symbol"):
        out[symbol] = group.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0]["variant"]
    return out


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = [
        "symbol",
        "period",
        "offset_pct",
        "timeout_min",
        "signals",
        "filled",
        "unfilled",
        "fill_rate_pct",
        "avg_fill_delay_min",
        "p95_fill_delay_min",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fill_stats(df, sig, offset_pct, timeout_min):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    indices = np.flatnonzero(sig)
    signals = 0
    filled = 0
    delays = []
    n = len(df)
    i = 250
    ptr = 0
    while i < n - 2:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        signal_idx = int(indices[ptr])
        order_start = signal_idx + 1
        if order_start >= n:
            break
        signals += 1
        limit_price = open_[order_start] * (1.0 + offset_pct)
        last_wait = min(n - 1, order_start + timeout_min - 1)
        fill_idx = None
        for j in range(order_start, last_wait + 1):
            if high[j] >= limit_price:
                fill_idx = j
                break
        if fill_idx is not None:
            filled += 1
            delays.append(fill_idx - order_start)
            i = fill_idx + 1
        else:
            i = last_wait + 1
    unfilled = signals - filled
    return {
        "signals": signals,
        "filled": filled,
        "unfilled": unfilled,
        "fill_rate_pct": filled / signals * 100.0 if signals else 0.0,
        "avg_fill_delay_min": float(np.mean(delays)) if delays else 0.0,
        "p95_fill_delay_min": float(np.percentile(delays, 95)) if delays else 0.0,
    }


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(rows)
    lines = [
        "# Selected 4 Maker Fill Rate",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Logic: signal forms on closed candle; SHORT limit order is placed on next candle.",
        "Limit price = next open * `(1 + offset)`; order is cancelled after timeout if not touched.",
        "",
        "## 30d / 365d Practical View",
        "",
        "| Symbol | Period | Offset | Timeout | Signals | Filled | Fill Rate | Avg Delay | P95 Delay |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    view = df[df["period"].isin(["30d", "365d"])].copy()
    view = view[
        ((view["offset_pct"].isin([0.0, 0.05, 0.10])) & (view["timeout_min"].isin([1, 3])))
    ]
    for _, row in view.sort_values(["symbol", "period", "offset_pct", "timeout_min"]).iterrows():
        lines.append(
            f"| `{row['symbol']}` | {row['period']} | {row['offset_pct']:.2f}% | {int(row['timeout_min'])} | "
            f"{int(row['signals'])} | {int(row['filled'])} | {row['fill_rate_pct']:.1f}% | "
            f"{row['avg_fill_delay_min']:.2f}m | {row['p95_fill_delay_min']:.2f}m |"
        )
    lines.extend(["", "## Best Fill Rate By Symbol And Period", ""])
    lines.extend(["| Symbol | Period | Best Offset | Timeout | Fill Rate | Signals |", "|---|---:|---:|---:|---:|---:|"])
    for (symbol, period), group in df.groupby(["symbol", "period"]):
        best = group.sort_values(["fill_rate_pct", "signals"], ascending=False).iloc[0]
        lines.append(
            f"| `{symbol}` | {period} | {best['offset_pct']:.2f}% | {int(best['timeout_min'])} | "
            f"{best['fill_rate_pct']:.1f}% | {int(best['signals'])} |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    variants = selected_variants(os.path.join(ROOT, args.summary))
    rows = []
    for symbol in SYMBOLS:
        print(f"loading {symbol}", flush=True)
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")))
        all_variants = s4.trend_variants(symbol) if symbol in s4.TREND_SYMBOLS else s4.exhaustion_variants(symbol)
        variant = next(item for item in all_variants if item["variant"] == variants[symbol])
        sig = s4.signal_for(df, variant)
        for days, offset_pct, timeout_min in product(WINDOWS, args.offsets, args.timeouts):
            bars = days * 1440
            if len(df) < bars + 300:
                continue
            sub_len = bars + 300
            sub = df.tail(sub_len).reset_index(drop=True)
            sub_sig = sig[-sub_len:]
            sm = fill_stats(sub, sub_sig, offset_pct, timeout_min)
            rows.append(
                {
                    "symbol": symbol,
                    "period": f"{days}d",
                    "offset_pct": offset_pct * 100.0,
                    "timeout_min": timeout_min,
                    **sm,
                }
            )
    save_csv(os.path.join(ROOT, args.save), rows)
    save_report(os.path.join(ROOT, args.save_report), rows)
    print(f"rows={len(rows)}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
