#!/usr/bin/env python3
"""Stage-2 microstructure scan for selected futures symbols.

Uses cached raw 1m plus 5m/15m candles to estimate whether a market candidate
is actually tradable: recent volume, thin candles, spikes, activity and fresh
wave behavior.
"""

import argparse
import csv
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    parser = argparse.ArgumentParser(description="Stage-2 microstructure scan.")
    parser.add_argument("--universe", default="data/market_structure_stage2_universe.csv")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--history-5m-dir", default="data/futures_5m_history")
    parser.add_argument("--history-15m-dir", default="data/futures_15m_history")
    parser.add_argument("--save", default="data/market_stage2_microstructure_summary.csv")
    parser.add_argument("--save-report", default="strategies/market-stage2-microstructure-summary.md")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def load_universe(path, limit=None):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if limit:
        rows = rows[:limit]
    return rows


def read_tail_csv(path, days, interval_minutes, raw=False):
    if not os.path.exists(path):
        return None
    rows_needed = int(days * 24 * 60 / interval_minutes) + 5
    # Pandas can read these files fast enough. nrows is unknown, so read all for
    # smaller 5m/15m and use only needed columns.
    cols = ["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume", "trades"]
    df = pd.read_csv(
        path,
        usecols=lambda col: col in cols,
        dtype={
            "open_time_ms": "int64",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "float64",
            "quote_volume": "float64",
            "trades": "float64",
        },
    )
    if df.empty:
        return None
    df = df.tail(rows_needed).copy()
    df = df.sort_values("open_time_ms").drop_duplicates("open_time_ms")
    return df


def safe_num(value, digits=4):
    if value is None or pd.isna(value) or math.isinf(value):
        return ""
    return round(float(value), digits)


def safe_pct(value):
    if value is None or pd.isna(value) or math.isinf(value):
        return ""
    return round(float(value) * 100.0, 4)


def window_return(df, bars):
    if df is None or len(df) <= bars:
        return None
    return df["close"].iloc[-1] / df["close"].iloc[-bars - 1] - 1.0


def thin_candle_pct(df, quote_threshold):
    if df is None or df.empty or "quote_volume" not in df:
        return None
    return (df["quote_volume"] < quote_threshold).mean()


def spike_stats(df):
    if df is None or df.empty:
        return {}
    ret = df["close"].pct_change().abs()
    wick_range = df["high"] / df["low"] - 1.0
    return {
        "max_1m_abs_move_pct": safe_pct(ret.max()),
        "p99_1m_abs_move_pct": safe_pct(ret.quantile(0.99)),
        "spike_1m_gt_1pct": int((ret > 0.01).sum()),
        "spike_1m_gt_2pct": int((ret > 0.02).sum()),
        "max_1m_range_pct": safe_pct(wick_range.max()),
        "p99_1m_range_pct": safe_pct(wick_range.quantile(0.99)),
    }


def resample_daily_from_1m(df):
    if df is None or df.empty:
        return None
    work = df.copy()
    work["time"] = pd.to_datetime(work["open_time_ms"], unit="ms", utc=True)
    daily = (
        work.set_index("time")
        .resample("1D")
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), quote_volume=("quote_volume", "sum"))
        .dropna()
    )
    if daily.empty:
        return None
    daily["range_pct"] = daily["high"] / daily["low"] - 1.0
    daily["ret"] = daily["close"].pct_change()
    return daily


def score_stage2(row):
    vol = float(row.get("quote_volume_1m_7d_avg_daily") or 0)
    thin = float(row.get("thin_1m_pct_lt_100") or 100)
    spikes = float(row.get("spike_1m_gt_2pct") or 0)
    ret7 = float(row.get("ret_7d_1m_pct") or 0)
    ret30 = float(row.get("ret_30d_1m_pct") or 0)
    range7 = float(row.get("avg_daily_range_7d_pct") or 0)
    p99_move = float(row.get("p99_1m_abs_move_pct") or 0)

    liquidity = min(100, math.log10(max(vol, 1)) * 12)
    thin_score = max(0, 100 - thin * 2.0)
    freshness = max(0, min(100, ret7 * 2.2 + ret30 * 0.6))
    movement = min(100, range7 * 8 + p99_move * 8)
    spike_penalty = min(30, spikes * 0.6)
    total = 0.35 * liquidity + 0.20 * thin_score + 0.25 * freshness + 0.20 * movement - spike_penalty
    return safe_num(total, 2)


def classify(row):
    history_class = row.get("market_class", "")
    score = float(row.get("stage2_score") or 0)
    vol = float(row.get("quote_volume_1m_7d_avg_daily") or 0)
    thin = float(row.get("thin_1m_pct_lt_100") or 100)
    candles = int(float(row.get("candles_1m_30d") or 0))
    ret7 = float(row.get("ret_7d_1m_pct") or 0)
    ret30 = float(row.get("ret_30d_1m_pct") or 0)
    if candles < 7 * 24 * 60:
        return "insufficient_micro"
    if vol < 500_000 or thin > 35:
        return "reject_execution"
    if history_class == "leader" and score >= 45:
        return "deep_test_leader"
    if ret7 > 10 and ret30 > 15 and score >= 45:
        return "deep_test_wave"
    if score >= 38:
        return "monitor"
    return "reject"


def scan_symbol(base_row, args):
    symbol = base_row["symbol"]
    try:
        one_m = read_tail_csv(os.path.join(ROOT, args.raw_1m_dir, f"{symbol}_1m.csv"), 30, 1, raw=True)
        five_m = read_tail_csv(os.path.join(ROOT, args.history_5m_dir, f"{symbol}_5m.csv"), 90, 5)
        fifteen_m = read_tail_csv(os.path.join(ROOT, args.history_15m_dir, f"{symbol}_15m.csv"), 90, 15)
        if one_m is None:
            raise RuntimeError("missing 1m raw data")
        daily = resample_daily_from_1m(one_m)
        row = dict(base_row)
        row.update(
            {
                "candles_1m_30d": len(one_m),
                "candles_5m_90d": len(five_m) if five_m is not None else 0,
                "candles_15m_90d": len(fifteen_m) if fifteen_m is not None else 0,
                "ret_1d_1m_pct": safe_pct(window_return(one_m, 24 * 60)),
                "ret_7d_1m_pct": safe_pct(window_return(one_m, 7 * 24 * 60)),
                "ret_30d_1m_pct": safe_pct(window_return(one_m, 30 * 24 * 60)),
                "ret_7d_5m_pct": safe_pct(window_return(five_m, 7 * 24 * 12)),
                "ret_30d_15m_pct": safe_pct(window_return(fifteen_m, 30 * 24 * 4)),
                "quote_volume_1m_24h": safe_num(one_m["quote_volume"].tail(24 * 60).sum(), 2),
                "quote_volume_1m_7d_avg_daily": safe_num(one_m["quote_volume"].tail(7 * 24 * 60).sum() / 7, 2),
                "median_quote_volume_1m_7d": safe_num(one_m["quote_volume"].tail(7 * 24 * 60).median(), 2),
                "median_trades_1m_7d": safe_num(one_m["trades"].tail(7 * 24 * 60).median(), 2),
                "thin_1m_pct_lt_100": safe_pct(thin_candle_pct(one_m.tail(7 * 24 * 60), 100)),
                "thin_1m_pct_lt_1000": safe_pct(thin_candle_pct(one_m.tail(7 * 24 * 60), 1000)),
                "status_stage2": "scanned",
                "error_stage2": "",
            }
        )
        row.update(spike_stats(one_m.tail(7 * 24 * 60)))
        if daily is not None:
            row.update(
                {
                    "avg_daily_range_7d_pct": safe_pct(daily["range_pct"].tail(7).mean()),
                    "avg_daily_range_30d_pct": safe_pct(daily["range_pct"].tail(30).mean()),
                    "green_days_7d": int((daily["ret"].tail(7) > 0).sum()),
                    "green_days_30d": int((daily["ret"].tail(30) > 0).sum()),
                    "range_gt_10_days_30d": int((daily["range_pct"].tail(30) > 0.10).sum()),
                }
            )
        else:
            row.update(
                {
                    "avg_daily_range_7d_pct": "",
                    "avg_daily_range_30d_pct": "",
                    "green_days_7d": "",
                    "green_days_30d": "",
                    "range_gt_10_days_30d": "",
                }
            )
        row["stage2_score"] = score_stage2(row)
        row["stage2_class"] = classify(row)
        return row
    except Exception as exc:
        row = dict(base_row)
        row.update({"status_stage2": "error", "error_stage2": str(exc), "stage2_score": "", "stage2_class": "error"})
        return row


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    preferred = [
        "symbol",
        "market_class",
        "stage2_class",
        "market_score",
        "stage2_score",
        "ret_1d_1m_pct",
        "ret_7d_1m_pct",
        "ret_30d_1m_pct",
        "quote_volume_1m_24h",
        "quote_volume_1m_7d_avg_daily",
        "median_quote_volume_1m_7d",
        "thin_1m_pct_lt_100",
        "thin_1m_pct_lt_1000",
        "avg_daily_range_7d_pct",
        "spike_1m_gt_1pct",
        "spike_1m_gt_2pct",
        "p99_1m_abs_move_pct",
        "candles_1m_30d",
    ]
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def report_table(rows, title, limit=30):
    lines = [
        f"## {title}",
        "",
        "| # | Symbol | Market | Stage2 | S2 | 1d | 7d | 30d | Vol7d/day | Thin<$1k | Range7d | Spikes>2% |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(rows[:limit], start=1):
        lines.append(
            f"| {i} | `{row['symbol']}` | {row.get('market_class','')} | {row.get('stage2_class','')} | "
            f"{row.get('stage2_score','')} | {row.get('ret_1d_1m_pct','')}% | {row.get('ret_7d_1m_pct','')}% | "
            f"{row.get('ret_30d_1m_pct','')}% | {row.get('quote_volume_1m_7d_avg_daily','')} | "
            f"{row.get('thin_1m_pct_lt_1000','')}% | {row.get('avg_daily_range_7d_pct','')}% | "
            f"{row.get('spike_1m_gt_2pct','')} |"
        )
    lines.append("")
    return lines


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    from collections import Counter

    classes = Counter(row.get("stage2_class") for row in rows)
    sorted_rows = sorted(rows, key=lambda row: float(row.get("stage2_score") or -999), reverse=True)
    deep = [row for row in sorted_rows if row.get("stage2_class") in ("deep_test_leader", "deep_test_wave")]
    monitor = [row for row in sorted_rows if row.get("stage2_class") == "monitor"]
    rejected = [row for row in sorted_rows if str(row.get("stage2_class", "")).startswith("reject")]
    lines = [
        "# Market Stage-2 Microstructure Scan",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Universe: `leader + hot_wave + wave_watch` from the stage-1 market structure scan.",
        "",
        "## Summary",
        "",
        f"- Symbols scanned: `{len(rows)}`",
    ]
    for key in sorted(classes):
        lines.append(f"- {key}: `{classes[key]}`")
    lines.append("")
    lines.extend(report_table(deep, "Deep Test Candidates", 50))
    lines.extend(report_table(monitor, "Monitor Candidates", 40))
    lines.extend(report_table(rejected, "Rejected By Execution/Microstructure", 30))
    lines.extend(
        [
            "## Human Read",
            "",
            "- `deep_test_leader` means the symbol was already structurally strong and passed recent execution filters.",
            "- `deep_test_wave` means it is hot now and still tradable enough to test deeply.",
            "- `monitor` means worth watching, but not first priority.",
            "- `reject_execution` usually means volume is too thin or too many tiny candles for realistic execution.",
            "",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    universe = load_universe(os.path.join(ROOT, args.universe), args.limit)
    rows = []
    print(f"Stage-2 scanning {len(universe)} symbols with {args.workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scan_symbol, row, args): row["symbol"] for row in universe}
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            if index % 20 == 0 or index == len(universe):
                print(f"[{index}/{len(universe)}] {row.get('symbol')} {row.get('stage2_class')}", flush=True)
    rows = sorted(rows, key=lambda row: float(row.get("stage2_score") or -999), reverse=True)
    save_csv(os.path.join(ROOT, args.save), rows)
    save_report(os.path.join(ROOT, args.save_report), rows)
    print(f"Saved CSV: {os.path.join(ROOT, args.save)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
