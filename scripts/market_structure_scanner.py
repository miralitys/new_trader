#!/usr/bin/env python3
"""Scan the full Binance Futures USDT universe for market structure stats.

This is not a strategy backtest. It builds a broad market map from cached
1h/4h candles so we can decide which symbols deserve deeper 1m/5m tests.
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
    parser = argparse.ArgumentParser(description="Scan cached futures candles for broad market statistics.")
    parser.add_argument("--symbols-file", default="data/binance_futures_active_usdt_ascii_symbols_2026-05-04.txt")
    parser.add_argument("--history-1h-dir", default="data/futures_1h_history")
    parser.add_argument("--history-4h-dir", default="data/futures_4h_history")
    parser.add_argument("--save", default="data/market_structure_scan_summary.csv")
    parser.add_argument("--save-report", default="strategies/market-structure-scan-summary.md")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def load_symbols(path, limit=None):
    with open(path, encoding="utf-8") as handle:
        symbols = [line.strip().upper() for line in handle if line.strip()]
    symbols = [symbol for symbol in symbols if symbol.endswith("USDT") and "_" not in symbol]
    return symbols[:limit] if limit else symbols


def read_kline_csv(path):
    if not os.path.exists(path):
        return None
    columns = ["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume", "trades"]
    df = pd.read_csv(
        path,
        usecols=lambda col: col in columns,
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
    df = df.sort_values("open_time_ms").drop_duplicates("open_time_ms")
    df["time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    return df


def safe_pct(value):
    if value is None or pd.isna(value) or math.isinf(value):
        return ""
    return round(float(value) * 100, 4)


def safe_num(value, digits=4):
    if value is None or pd.isna(value) or math.isinf(value):
        return ""
    return round(float(value), digits)


def ema(series, span):
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def max_drawdown_from_close(close):
    if close.empty:
        return None
    running_max = close.cummax()
    dd = close / running_max - 1.0
    return float(dd.min())


def trend_run_stats(is_up):
    values = is_up.dropna().astype(bool).tolist()
    if not values:
        return 0, 0.0
    runs = []
    current = values[0]
    length = 1
    for value in values[1:]:
        if value == current:
            length += 1
        else:
            runs.append(length)
            current = value
            length = 1
    runs.append(length)
    return len(runs), sum(runs) / len(runs)


def daily_stats(df):
    daily = (
        df.set_index("time")
        .resample("1D")
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), quote_volume=("quote_volume", "sum"))
        .dropna()
    )
    if daily.empty:
        return daily, {}
    daily["ret"] = daily["close"].pct_change()
    daily["range_pct"] = daily["high"] / daily["low"] - 1.0
    daily["pump_pct"] = daily["high"] / daily["open"] - 1.0
    daily["dump_pct"] = daily["low"] / daily["open"] - 1.0
    stats = {
        "daily_count": len(daily),
        "avg_daily_abs_ret_pct": safe_pct(daily["ret"].abs().mean()),
        "avg_daily_range_pct": safe_pct(daily["range_pct"].mean()),
        "max_daily_pump_pct": safe_pct(daily["pump_pct"].max()),
        "max_daily_dump_pct": safe_pct(daily["dump_pct"].min()),
        "days_range_gt_5": int((daily["range_pct"] > 0.05).sum()),
        "days_range_gt_10": int((daily["range_pct"] > 0.10).sum()),
        "days_range_gt_20": int((daily["range_pct"] > 0.20).sum()),
        "avg_daily_quote_volume_30d": safe_num(daily["quote_volume"].tail(30).mean(), 2),
        "avg_daily_quote_volume_90d": safe_num(daily["quote_volume"].tail(90).mean(), 2),
    }
    return daily, stats


def window_return(close, bars):
    if len(close) <= bars:
        return None
    return close.iloc[-1] / close.iloc[-bars - 1] - 1.0


def impulse_follow_through(daily, threshold=0.10, lookahead=3):
    if len(daily) <= lookahead:
        return "", "", ""
    events = daily[daily["pump_pct"] >= threshold]
    if events.empty:
        return 0, "", ""
    wins = 0
    returns = []
    for idx in events.index:
        loc = daily.index.get_loc(idx)
        if loc + lookahead >= len(daily):
            continue
        entry = daily["close"].iloc[loc]
        future = daily["close"].iloc[loc + lookahead]
        ret = future / entry - 1.0
        returns.append(ret)
        if ret > 0:
            wins += 1
    if not returns:
        return int(len(events)), "", ""
    return int(len(events)), safe_pct(wins / len(returns)), safe_pct(sum(returns) / len(returns))


def score_row(row):
    history_days = float(row.get("history_days") or 0)
    avg_range = float(row.get("avg_daily_range_pct") or 0)
    days10 = float(row.get("days_range_gt_10") or 0)
    vol30 = float(row.get("avg_daily_quote_volume_30d") or 0)
    ret30 = float(row.get("ret_30d_pct") or 0)
    ret90 = float(row.get("ret_90d_pct") or 0)
    trend4h = float(row.get("trend_4h_above_ema200_pct") or 0)
    dd365 = abs(float(row.get("drawdown_365d_pct") or 0))

    liquidity_score = min(100.0, math.log10(max(vol30, 1.0)) * 12.0)
    volatility_score = min(100.0, avg_range * 7.0 + days10 * 0.8)
    heat_score = max(0.0, min(100.0, ret30 * 1.8 + ret90 * 0.7 + days10 * 0.3))
    trend_score = 100.0 - min(abs(trend4h - 50.0) * 2.0, 100.0)
    risk_penalty = min(40.0, dd365 * 0.5)
    maturity_score = min(100.0, history_days / 365.0 * 100.0)
    total = 0.25 * liquidity_score + 0.25 * volatility_score + 0.25 * heat_score + 0.15 * trend_score + 0.10 * maturity_score - risk_penalty
    return {
        "liquidity_score": safe_num(liquidity_score, 2),
        "volatility_score": safe_num(volatility_score, 2),
        "heat_score": safe_num(heat_score, 2),
        "trend_score": safe_num(trend_score, 2),
        "market_score": safe_num(total, 2),
    }


def classify(row):
    history_days = float(row.get("history_days") or 0)
    score = float(row.get("market_score") or 0)
    vol30 = float(row.get("avg_daily_quote_volume_30d") or 0)
    ret30 = float(row.get("ret_30d_pct") or 0)
    ret90 = float(row.get("ret_90d_pct") or 0)
    range10 = int(row.get("days_range_gt_10") or 0)
    dd365 = abs(float(row.get("drawdown_365d_pct") or 0))
    if history_days < 30:
        return "insufficient"
    if vol30 < 250_000:
        return "avoid_thin"
    if ret30 > 20 and range10 >= 3:
        return "hot_wave"
    if score >= 55 and history_days >= 180 and dd365 <= 80:
        return "leader"
    if ret90 > 20 and range10 >= 5:
        return "wave_watch"
    if score >= 45 and history_days >= 90:
        return "watchlist"
    return "avoid"


def scan_symbol(symbol, args):
    one_h_path = os.path.join(ROOT, args.history_1h_dir, f"{symbol}_1h.csv")
    four_h_path = os.path.join(ROOT, args.history_4h_dir, f"{symbol}_4h.csv")
    try:
        h1 = read_kline_csv(one_h_path)
        h4 = read_kline_csv(four_h_path)
        if h1 is None:
            return {"symbol": symbol, "status": "error", "error": "missing 1h data"}

        start = h1["time"].iloc[0]
        end = h1["time"].iloc[-1]
        history_days = (end - start).total_seconds() / 86400.0 + 1 / 24.0
        close = h1["close"]
        daily, d_stats = daily_stats(h1)
        pump_events, pump_follow_win, pump_follow_avg = impulse_follow_through(daily)

        ema200_1h = ema(close, 200)
        above_1h = close > ema200_1h
        runs_1h, avg_run_1h = trend_run_stats(above_1h)
        ret_1d = window_return(close, 24)
        ret_7d = window_return(close, 24 * 7)
        ret_30d = window_return(close, 24 * 30)
        ret_90d = window_return(close, 24 * 90)
        ret_180d = window_return(close, 24 * 180)
        ret_365d = window_return(close, 24 * 365)

        row = {
            "symbol": symbol,
            "status": "scanned",
            "candles_1h": len(h1),
            "candles_4h": len(h4) if h4 is not None else 0,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "history_days": safe_num(history_days, 2),
            "ret_1d_pct": safe_pct(ret_1d),
            "ret_7d_pct": safe_pct(ret_7d),
            "ret_30d_pct": safe_pct(ret_30d),
            "ret_90d_pct": safe_pct(ret_90d),
            "ret_180d_pct": safe_pct(ret_180d),
            "ret_365d_pct": safe_pct(ret_365d),
            "drawdown_365d_pct": safe_pct(max_drawdown_from_close(close.tail(24 * 365))),
            "trend_1h_above_ema200_pct": safe_pct(above_1h.mean()),
            "trend_1h_runs": runs_1h,
            "trend_1h_avg_run_hours": safe_num(avg_run_1h, 2),
            "pump10_events": pump_events,
            "pump10_follow_3d_win_pct": pump_follow_win,
            "pump10_follow_3d_avg_pct": pump_follow_avg,
            "error": "",
        }
        row.update(d_stats)

        if h4 is not None and len(h4) >= 220:
            close4 = h4["close"]
            ema200_4h = ema(close4, 200)
            above_4h = close4 > ema200_4h
            runs_4h, avg_run_4h = trend_run_stats(above_4h)
            row.update(
                {
                    "trend_4h_above_ema200_pct": safe_pct(above_4h.mean()),
                    "trend_4h_runs": runs_4h,
                    "trend_4h_avg_run_hours": safe_num(avg_run_4h * 4, 2),
                    "ret_4h_last_pct": safe_pct(window_return(close4, 1)),
                    "ret_4h_7d_pct": safe_pct(window_return(close4, 6 * 7)),
                }
            )
        else:
            row.update(
                {
                    "trend_4h_above_ema200_pct": "",
                    "trend_4h_runs": "",
                    "trend_4h_avg_run_hours": "",
                    "ret_4h_last_pct": "",
                    "ret_4h_7d_pct": "",
                }
            )

        row.update(score_row(row))
        row["market_class"] = classify(row)
        return row
    except Exception as exc:
        return {"symbol": symbol, "status": "error", "error": str(exc)}


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    preferred = [
        "symbol",
        "market_class",
        "market_score",
        "history_days",
        "candles_1h",
        "start",
        "end",
        "ret_1d_pct",
        "ret_7d_pct",
        "ret_30d_pct",
        "ret_90d_pct",
        "ret_180d_pct",
        "ret_365d_pct",
        "drawdown_365d_pct",
        "avg_daily_range_pct",
        "days_range_gt_10",
        "avg_daily_quote_volume_30d",
        "trend_4h_above_ema200_pct",
        "pump10_events",
        "pump10_follow_3d_avg_pct",
    ]
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return "n/a" if value in ("", None) else str(value)


def report_table(rows, title, limit=20):
    lines = [f"## {title}", "", "| # | Symbol | Class | Score | 30d | 90d | 365d | DD365 | Avg range | Vol30 | Pump10 |", "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for index, row in enumerate(rows[:limit], start=1):
        lines.append(
            f"| {index} | `{row['symbol']}` | {row.get('market_class','')} | {fmt(row.get('market_score'))} | "
            f"{fmt(row.get('ret_30d_pct'))}% | {fmt(row.get('ret_90d_pct'))}% | {fmt(row.get('ret_365d_pct'))}% | "
            f"{fmt(row.get('drawdown_365d_pct'))}% | {fmt(row.get('avg_daily_range_pct'))}% | "
            f"{fmt(row.get('avg_daily_quote_volume_30d'))} | {fmt(row.get('pump10_events'))} |"
        )
    lines.append("")
    return lines


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scanned = [row for row in rows if row.get("status") != "error"]
    errors = [row for row in rows if row.get("status") == "error"]
    classes = {}
    for row in scanned:
        classes[row.get("market_class", "unknown")] = classes.get(row.get("market_class", "unknown"), 0) + 1

    def by_score(items):
        return sorted(items, key=lambda row: float(row.get("market_score") or -999), reverse=True)

    leaders = by_score([row for row in scanned if row.get("market_class") == "leader"])
    hot = by_score([row for row in scanned if row.get("market_class") == "hot_wave"])
    wave = by_score([row for row in scanned if row.get("market_class") == "wave_watch"])
    watch = by_score([row for row in scanned if row.get("market_class") == "watchlist"])
    liquid = sorted(scanned, key=lambda row: float(row.get("avg_daily_quote_volume_30d") or 0), reverse=True)
    volatile = sorted(scanned, key=lambda row: float(row.get("avg_daily_range_pct") or 0), reverse=True)

    lines = [
        "# Market Structure Scan",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "This scan is a market map, not a trading strategy. It uses cached `1h` and `4h` futures candles to rank symbols by history, liquidity, volatility, trend regime and recent heat.",
        "",
        "## Summary",
        "",
        f"- Symbols scanned: `{len(scanned)}`",
        f"- Errors: `{len(errors)}`",
    ]
    for key in sorted(classes):
        lines.append(f"- {key}: `{classes[key]}`")
    lines.append("")
    lines.extend(report_table(leaders, "Top Leaders", 25))
    lines.extend(report_table(hot, "Hot Wave Now", 25))
    lines.extend(report_table(wave, "Wave Watch", 25))
    lines.extend(report_table(watch, "General Watchlist", 25))
    lines.extend(report_table(liquid, "Most Liquid", 20))
    lines.extend(report_table(volatile, "Most Volatile", 20))
    if errors:
        lines.extend(["## Errors", ""])
        for row in errors[:50]:
            lines.append(f"- `{row['symbol']}`: {row.get('error')}")
        lines.append("")
    lines.extend(
        [
            "## Human Read",
            "",
            "- `leader` means the symbol has enough history, acceptable liquidity and a broad market score worth deeper tests.",
            "- `hot_wave` means recent movement is strong; it may be good for wave-monitor tests but risky for long-term conclusions.",
            "- `wave_watch` means there is impulse behavior, but not enough quality to call it a leader yet.",
            "- `avoid_thin` and `insufficient` should not be used for real strategy selection without extra checks.",
            "",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    symbols = load_symbols(os.path.join(ROOT, args.symbols_file), args.limit)
    rows = []
    print(f"Scanning {len(symbols)} symbols with {args.workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scan_symbol, symbol, args): symbol for symbol in symbols}
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            if index % 25 == 0 or index == len(symbols):
                print(f"[{index}/{len(symbols)}] {row.get('symbol')} {row.get('market_class', row.get('status'))}", flush=True)
    rows = sorted(rows, key=lambda row: float(row.get("market_score") or -999), reverse=True)
    save_csv(os.path.join(ROOT, args.save), rows)
    save_report(os.path.join(ROOT, args.save_report), rows)
    print(f"Saved CSV: {os.path.join(ROOT, args.save)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
