#!/usr/bin/env python3
"""Stage-3 deep screen for selected futures symbols.

This is a practical broad backtest pass over the stage-2 universe. It is not
the final per-coin full search; it uses a small fixed LONG/SHORT grid to find
which symbols deserve expensive 730d/stress/cashflow validation.
"""

import argparse
import csv
import math
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERIODS = [7, 30, 60, 90, 180, 365]
INITIAL_BALANCE = 1000.0


VARIANTS = [
    {"variant": "LONG th50 wide TP1.2 T90", "direction": "long", "threshold": 50, "regime": "wide", "tp": 0.012, "sl": 0.04, "time": 90},
    {"variant": "LONG th60 wide TP0.7 T90", "direction": "long", "threshold": 60, "regime": "wide", "tp": 0.007, "sl": 0.035, "time": 90},
    {"variant": "LONG th70 base TP0.5 T60", "direction": "long", "threshold": 70, "regime": "base", "tp": 0.005, "sl": 0.03, "time": 60},
    {"variant": "SHORT th40 wide TP0.35 T60", "direction": "short", "threshold": 40, "regime": "wide", "tp": 0.0035, "sl": 0.04, "time": 60},
    {"variant": "SHORT th50 wide TP0.5 T90", "direction": "short", "threshold": 50, "regime": "wide", "tp": 0.005, "sl": 0.04, "time": 90},
    {"variant": "SHORT th60 base TP0.7 T120", "direction": "short", "threshold": 60, "regime": "base", "tp": 0.007, "sl": 0.035, "time": 120},
]


def parse_args():
    parser = argparse.ArgumentParser(description="Stage-3 broad deep strategy screen.")
    parser.add_argument("--universe", default="data/market_stage3_deep_test_universe.csv")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default="data/market_stage3_deep_screen_summary.csv")
    parser.add_argument("--save-windows", default="data/market_stage3_deep_screen_windows.csv")
    parser.add_argument("--save-report", default="strategies/market-stage3-deep-screen-summary.md")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--position-pct", type=float, default=1.0)
    return parser.parse_args()


def load_universe(path, limit=None):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return rows[:limit] if limit else rows


def read_symbol_tail(path, days=372):
    rows_needed = days * 1440 + 300
    df = pd.read_csv(
        path,
        usecols=["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume", "trades"],
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
    if len(df) > rows_needed:
        df = df.tail(rows_needed).copy()
    df = df.sort_values("open_time_ms").drop_duplicates("open_time_ms").reset_index(drop=True)
    return df


def add_indicators(df):
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    df["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    df["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    df["ema200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14, min_periods=14).mean()
    df["atr_pct"] = df["atr14"] / close
    df["vol_sma20"] = volume.rolling(20, min_periods=20).mean()
    df["recent_high20"] = high.rolling(20, min_periods=20).max().shift(1)
    df["recent_low20"] = low.rolling(20, min_periods=20).min().shift(1)
    rng = (high - low).replace(0, np.nan)
    body = (close - df["open"]).abs()
    df["body_ratio"] = body / rng
    df["green"] = close > df["open"]
    df["red"] = close < df["open"]
    df["upper_wick_ratio"] = (high - pd.concat([close, df["open"]], axis=1).max(axis=1)) / rng
    df["lower_wick_ratio"] = (pd.concat([close, df["open"]], axis=1).min(axis=1) - low) / rng
    return df


def apply_scores(df, regime):
    if regime == "wide":
        atr_min, atr_max, vol_mult = 0.0010, 0.0200, 1.2
    else:
        atr_min, atr_max, vol_mult = 0.0015, 0.0120, 1.5
    long_score = (
        ((df["close"] > df["ema200"]) & (df["ema20"] > df["ema50"])).astype(int) * 25
        + (df["close"] > df["recent_high20"]).astype(int) * 25
        + (df["volume"] > df["vol_sma20"] * vol_mult).astype(int) * 20
        + ((df["atr_pct"] >= atr_min) & (df["atr_pct"] <= atr_max)).astype(int) * 15
        + ((df["body_ratio"] > 0.60) & df["green"]).astype(int) * 15
    )
    short_score = (
        ((df["close"] < df["ema200"]) & (df["ema20"] < df["ema50"])).astype(int) * 25
        + (df["close"] < df["recent_low20"]).astype(int) * 25
        + (df["volume"] > df["vol_sma20"] * vol_mult).astype(int) * 20
        + ((df["atr_pct"] >= atr_min) & (df["atr_pct"] <= atr_max)).astype(int) * 15
        + ((df["body_ratio"] > 0.60) & df["red"]).astype(int) * 15
    )
    return long_score.to_numpy(), short_score.to_numpy()


def summarize(trades, equity_curve):
    if not trades:
        return {
            "trades": 0,
            "return_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "expectancy_pct": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "final_equity": INITIAL_BALANCE,
            "exit_reasons": {},
        }
    final = equity_curve[-1]
    returns = [t["net_return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    running_max = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        running_max = max(running_max, value)
        max_dd = max(max_dd, (running_max - value) / running_max * 100.0)
    reasons = Counter(t["reason"] for t in trades)
    return {
        "trades": len(trades),
        "return_pct": (final / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "avg_win_pct": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss_pct": sum(losses) / len(losses) if losses else 0.0,
        "final_equity": final,
        "exit_reasons": dict(reasons),
    }


def backtest_arrays(df, signal, direction, tp, sl, time_stop, fee_pct, position_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    n = len(df)
    equity = INITIAL_BALANCE
    equity_curve = [equity]
    trades = []
    i = 250
    while i < n - 2:
        if not signal[i]:
            i += 1
            continue
        entry_idx = i + 1
        entry = open_[entry_idx]
        notional = equity * position_pct
        exit_idx = min(entry_idx + time_stop, n - 1)
        reason = "time_stop"
        exit_price = close[exit_idx]
        if direction == "long":
            tp_price = entry * (1.0 + tp)
            sl_price = entry * (1.0 - sl)
            for j in range(entry_idx, exit_idx + 1):
                if low[j] <= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if high[j] >= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            gross = exit_price / entry - 1.0
        else:
            tp_price = entry * (1.0 - tp)
            sl_price = entry * (1.0 + sl)
            for j in range(entry_idx, exit_idx + 1):
                if high[j] >= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if low[j] <= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            gross = entry / exit_price - 1.0
        net = gross - fee_pct * 2.0
        pnl = notional * net
        equity += pnl
        equity_curve.append(equity)
        trades.append(
            {
                "entry_time_ms": int(times[entry_idx]),
                "exit_time_ms": int(times[exit_idx]),
                "net_return_pct": net * 100.0,
                "reason": reason,
            }
        )
        i = exit_idx + 1
    return summarize(trades, equity_curve)


def run_symbol(row, args):
    symbol = row["symbol"]
    path = os.path.join(ROOT, args.raw_1m_dir, f"{symbol}_1m.csv")
    out = []
    try:
        df = add_indicators(read_symbol_tail(path))
        for variant in VARIANTS:
            long_score, short_score = apply_scores(df, variant["regime"])
            if variant["direction"] == "long":
                signal = (long_score >= variant["threshold"]) & (df["close"].to_numpy() <= df["ema20"].to_numpy() * 1.010) & (df["upper_wick_ratio"].fillna(1).to_numpy() <= 0.35)
            else:
                signal = short_score >= variant["threshold"]
            for period in PERIODS:
                bars = period * 1440
                if len(df) < bars + 300:
                    continue
                window_df = df.tail(bars + 300).reset_index(drop=True)
                window_signal = signal[-(bars + 300) :]
                summary = backtest_arrays(
                    window_df,
                    window_signal,
                    variant["direction"],
                    variant["tp"],
                    variant["sl"],
                    variant["time"],
                    args.fee_pct,
                    args.position_pct,
                )
                out.append(
                    {
                        "symbol": symbol,
                        "market_class": row.get("market_class", ""),
                        "stage2_class": row.get("stage2_class", ""),
                        **variant,
                        "period": f"{period}d",
                        **{k: v for k, v in summary.items() if k != "exit_reasons"},
                        "take_profit": summary["exit_reasons"].get("take_profit", 0),
                        "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                        "time_stop": summary["exit_reasons"].get("time_stop", 0),
                        "status": "ok",
                        "error": "",
                    }
                )
        return out
    except Exception as exc:
        return [
            {
                "symbol": symbol,
                "market_class": row.get("market_class", ""),
                "stage2_class": row.get("stage2_class", ""),
                "variant": "",
                "direction": "",
                "period": "",
                "status": "error",
                "error": str(exc),
            }
        ]


def build_summary(rows):
    grouped = {}
    for row in rows:
        if row.get("status") != "ok":
            continue
        key = (row["symbol"], row["variant"])
        grouped.setdefault(key, []).append(row)
    summaries = []
    for (symbol, variant), items in grouped.items():
        by_period = {row["period"]: row for row in items}
        if "365d" not in by_period:
            continue
        row365 = by_period["365d"]
        periods = [f"{p}d" for p in PERIODS if f"{p}d" in by_period]
        returns = [float(by_period[p]["return_pct"]) for p in periods]
        pfs = [float(by_period[p]["profit_factor"]) for p in periods]
        dds = [float(by_period[p]["max_dd_pct"]) for p in periods]
        base = dict(row365)
        base.update(
            {
                "positive_windows": sum(1 for r in returns if r > 0),
                "windows_count": len(returns),
                "min_return_pct": min(returns),
                "max_dd_any_pct": max(dds),
                "min_pf": min(pfs),
                "return_7d_pct": by_period.get("7d", {}).get("return_pct", ""),
                "return_30d_pct": by_period.get("30d", {}).get("return_pct", ""),
                "return_60d_pct": by_period.get("60d", {}).get("return_pct", ""),
                "return_90d_pct": by_period.get("90d", {}).get("return_pct", ""),
                "return_180d_pct": by_period.get("180d", {}).get("return_pct", ""),
                "return_365d_pct": row365["return_pct"],
                "trades_365d": row365["trades"],
                "pf_365d": row365["profit_factor"],
                "dd_365d_pct": row365["max_dd_pct"],
            }
        )
        summaries.append(base)
    summaries.sort(
        key=lambda r: (
            int(r["positive_windows"]),
            float(r["min_pf"]),
            float(r["return_365d_pct"]),
            -float(r["max_dd_any_pct"]),
        ),
        reverse=True,
    )
    return summaries


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = sorted({k for row in rows for k in row.keys()})
    preferred = [
        "symbol",
        "market_class",
        "stage2_class",
        "variant",
        "direction",
        "positive_windows",
        "windows_count",
        "return_7d_pct",
        "return_30d_pct",
        "return_60d_pct",
        "return_90d_pct",
        "return_180d_pct",
        "return_365d_pct",
        "pf_365d",
        "dd_365d_pct",
        "max_dd_any_pct",
        "min_pf",
        "trades_365d",
        "win_rate_pct",
        "expectancy_pct",
        "period",
        "return_pct",
        "profit_factor",
        "max_dd_pct",
        "trades",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    if value in ("", None):
        return "n/a"
    try:
        return f"{float(value):+.2f}"
    except Exception:
        return str(value)


def save_report(path, summary, windows, errors):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    strong = [
        r
        for r in summary
        if int(r["positive_windows"]) >= 5
        and float(r["return_365d_pct"]) > 0
        and float(r["pf_365d"]) >= 1.05
        and int(float(r["trades_365d"])) >= 20
    ]
    lines = [
        "# Market Stage-3 Deep Screen",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Small fixed LONG/SHORT grid over cached raw `1m` candles. This is a broad deep screen, not the final optimized full search.",
        "",
        "## Summary",
        "",
        f"- Variant summaries: `{len(summary)}`",
        f"- Window rows: `{len(windows)}`",
        f"- Strong candidates: `{len(strong)}`",
        f"- Errors: `{len(errors)}`",
        "",
        "## Strong Candidates",
        "",
        "| # | Symbol | Stage2 | Variant | Pos | 7d | 30d | 60d | 90d | 180d | 365d | PF365 | DD365 | Trades365 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(strong[:80], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | {r.get('stage2_class','')} | {r['variant']} | {r['positive_windows']}/{r['windows_count']} | "
            f"{fmt(r.get('return_7d_pct'))}% | {fmt(r.get('return_30d_pct'))}% | {fmt(r.get('return_60d_pct'))}% | "
            f"{fmt(r.get('return_90d_pct'))}% | {fmt(r.get('return_180d_pct'))}% | {fmt(r.get('return_365d_pct'))}% | "
            f"{float(r.get('pf_365d') or 0):.2f} | {float(r.get('dd_365d_pct') or 0):.2f}% | {int(float(r.get('trades_365d') or 0))} |"
        )
    lines.extend(
        [
            "",
            "## Top By Rank",
            "",
            "| # | Symbol | Stage2 | Variant | Pos | 365d | PF365 | DD365 | Trades365 |",
            "|---:|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for i, r in enumerate(summary[:80], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | {r.get('stage2_class','')} | {r['variant']} | {r['positive_windows']}/{r['windows_count']} | "
            f"{fmt(r.get('return_365d_pct'))}% | {float(r.get('pf_365d') or 0):.2f} | "
            f"{float(r.get('dd_365d_pct') or 0):.2f}% | {int(float(r.get('trades_365d') or 0))} |"
        )
    if errors:
        lines.extend(["", "## Errors", ""])
        for row in errors[:50]:
            lines.append(f"- `{row['symbol']}`: {row.get('error')}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    universe = list(csv.DictReader(open(os.path.join(ROOT, args.universe), encoding="utf-8")))
    if args.limit:
        universe = universe[: args.limit]
    print(f"Stage-3 deep screening {len(universe)} symbols with {args.workers} workers", flush=True)
    all_rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_symbol, row, args): row["symbol"] for row in universe}
        for i, future in enumerate(as_completed(futures), 1):
            rows = future.result()
            all_rows.extend(rows)
            if i % 10 == 0 or i == len(universe):
                ok = sum(1 for r in rows if r.get("status") == "ok")
                print(f"[{i}/{len(universe)}] {futures[future]} rows={ok}", flush=True)
    errors = [r for r in all_rows if r.get("status") == "error"]
    windows = [r for r in all_rows if r.get("status") == "ok"]
    summary = build_summary(windows)
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_summary), summary + errors)
    save_report(os.path.join(ROOT, args.save_report), summary, windows, errors)
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved windows: {os.path.join(ROOT, args.save_windows)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
