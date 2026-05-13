#!/usr/bin/env python3
"""Search genuinely new 1m strategy families on the current candidate universe.

This is a first-pass research scanner, not a final optimizer. It tests strategy
families that are different from the mb-score templates:

- trend pullback continuation;
- breakout / breakdown continuation;
- mean reversion scalps.

Every candidate is validated on multiple windows with base and stress execution.
"""

import argparse
import csv
import math
import os
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0
WINDOWS = [30, 60, 90, 180, 365, 730]


FAMILIES = [
    {"name": "trend_pullback_long", "direction": "long", "tp": 0.006, "sl": 0.025, "time": 180},
    {"name": "trend_pullback_short", "direction": "short", "tp": 0.006, "sl": 0.025, "time": 180},
    {"name": "breakout_long", "direction": "long", "tp": 0.008, "sl": 0.030, "time": 90},
    {"name": "breakdown_short", "direction": "short", "tp": 0.008, "sl": 0.030, "time": 90},
    {"name": "mean_revert_long", "direction": "long", "tp": 0.004, "sl": 0.020, "time": 60},
    {"name": "mean_revert_short", "direction": "short", "tp": 0.004, "sl": 0.020, "time": 60},
]


def parse_args():
    parser = argparse.ArgumentParser(description="Search new strategy families.")
    parser.add_argument("--universe", default="data/market_stage4_top50_universe.csv")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--top-symbols", type=int, default=50)
    parser.add_argument("--save-summary", default="data/new_strategy_family_search_summary.csv")
    parser.add_argument("--save-windows", default="data/new_strategy_family_search_windows.csv")
    parser.add_argument("--save-report", default="strategies/new-strategy-family-search.md")
    return parser.parse_args()


def load_symbols(path, limit):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    symbols = []
    for row in rows:
        symbol = row["symbol"]
        if symbol not in symbols:
            symbols.append(symbol)
        if len(symbols) >= limit:
            break
    return symbols


def read_symbol(path):
    df = pd.read_csv(
        path,
        usecols=["open_time_ms", "open", "high", "low", "close", "volume"],
        dtype={
            "open_time_ms": "int64",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "float64",
        },
    )
    return df.sort_values("open_time_ms").drop_duplicates("open_time_ms").reset_index(drop=True)


def add_indicators(df):
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    df["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    df["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    df["ema200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14, min_periods=14).mean()
    df["atr_pct"] = df["atr14"] / close
    df["vol_sma20"] = volume.rolling(20, min_periods=20).mean()
    df["high50"] = high.rolling(50, min_periods=50).max().shift(1)
    df["low50"] = low.rolling(50, min_periods=50).min().shift(1)
    rng = (high - low).replace(0, np.nan)
    df["body_ratio"] = (close - df["open"]).abs() / rng
    df["green"] = close > df["open"]
    df["red"] = close < df["open"]
    df["upper_wick_ratio"] = (high - pd.concat([close, df["open"]], axis=1).max(axis=1)) / rng
    df["lower_wick_ratio"] = (pd.concat([close, df["open"]], axis=1).min(axis=1) - low) / rng
    return df


def add_closed_htf(df, minutes):
    base = df[["open_time_ms", "open", "high", "low", "close", "volume"]].copy()
    base["time"] = pd.to_datetime(base["open_time_ms"], unit="ms", utc=True)
    htf = (
        base.set_index("time")
        .resample(f"{minutes}min", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    htf["ema20"] = htf["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    htf["ema50"] = htf["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    htf["ema200"] = htf["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    htf[f"htf{minutes}_long"] = (htf["close"] > htf["ema200"]) & (htf["ema20"] > htf["ema50"])
    htf[f"htf{minutes}_short"] = (htf["close"] < htf["ema200"]) & (htf["ema20"] < htf["ema50"])
    htf["usable_time_ms"] = (htf["time"].astype("int64") // 1_000_000) + minutes * 60_000
    perm = htf[["usable_time_ms", f"htf{minutes}_long", f"htf{minutes}_short"]].rename(columns={"usable_time_ms": "open_time_ms"})
    merged = pd.merge_asof(
        df[["open_time_ms"]].sort_values("open_time_ms"),
        perm.sort_values("open_time_ms"),
        on="open_time_ms",
        direction="backward",
    )
    df[f"htf{minutes}_long"] = merged[f"htf{minutes}_long"].fillna(False).to_numpy()
    df[f"htf{minutes}_short"] = merged[f"htf{minutes}_short"].fillna(False).to_numpy()
    return df


def build_signal(df, family):
    name = family["name"]
    atr_ok = df["atr_pct"].between(0.0015, 0.018)
    vol_ok = df["volume"] > df["vol_sma20"] * 1.1
    if name == "trend_pullback_long":
        return (
            df["htf60_long"]
            & df["htf240_long"]
            & (df["close"] > df["ema200"])
            & (df["close"] <= df["ema20"] * 1.003)
            & (df["close"] >= df["ema50"] * 0.992)
            & df["rsi14"].between(38, 58)
            & df["green"]
            & atr_ok
        ).to_numpy()
    if name == "trend_pullback_short":
        return (
            df["htf60_short"]
            & df["htf240_short"]
            & (df["close"] < df["ema200"])
            & (df["close"] >= df["ema20"] * 0.997)
            & (df["close"] <= df["ema50"] * 1.008)
            & df["rsi14"].between(42, 62)
            & df["red"]
            & atr_ok
        ).to_numpy()
    if name == "breakout_long":
        return (
            df["htf60_long"]
            & (df["close"] > df["high50"])
            & (df["volume"] > df["vol_sma20"] * 1.8)
            & (df["body_ratio"] > 0.45)
            & (df["upper_wick_ratio"] < 0.35)
            & atr_ok
        ).to_numpy()
    if name == "breakdown_short":
        return (
            df["htf60_short"]
            & (df["close"] < df["low50"])
            & (df["volume"] > df["vol_sma20"] * 1.8)
            & (df["body_ratio"] > 0.45)
            & (df["lower_wick_ratio"] < 0.35)
            & atr_ok
        ).to_numpy()
    if name == "mean_revert_long":
        return (
            (df["rsi14"] < 25)
            & (df["close"] < df["ema20"] * (1 - df["atr_pct"] * 1.3))
            & (df["lower_wick_ratio"] > 0.30)
            & (df["atr_pct"] < 0.025)
            & (df["htf240_short"] == False)
        ).to_numpy()
    if name == "mean_revert_short":
        return (
            (df["rsi14"] > 75)
            & (df["close"] > df["ema20"] * (1 + df["atr_pct"] * 1.3))
            & (df["upper_wick_ratio"] > 0.30)
            & (df["atr_pct"] < 0.025)
            & (df["htf240_long"] == False)
        ).to_numpy()
    raise ValueError(name)


def summarize(trades, equity_curve):
    if not trades:
        return {"trades": 0, "return_pct": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "max_dd_pct": 0.0, "expectancy_pct": 0.0, "exit_reasons": {}}
    returns = [t["net_return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0)
    return {
        "trades": len(trades),
        "return_pct": (equity_curve[-1] / INITIAL_BALANCE - 1) * 100,
        "win_rate_pct": len(wins) / len(trades) * 100,
        "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, signal, family, position_pct, fee_pct, slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    equity = INITIAL_BALANCE
    curve = [equity]
    trades = []
    indices = np.flatnonzero(signal)
    ptr = 0
    i = 250
    n = len(df)
    while i < n - 2:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        i = int(indices[ptr])
        entry_idx = i + 1
        if entry_idx >= n:
            break
        if family["direction"] == "long":
            entry = open_[entry_idx] * (1 + slippage_pct)
            tp = entry * (1 + family["tp"])
            sl = entry * (1 - family["sl"])
        else:
            entry = open_[entry_idx] * (1 - slippage_pct)
            tp = entry * (1 - family["tp"])
            sl = entry * (1 + family["sl"])
        exit_idx = min(entry_idx + family["time"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        if family["direction"] == "long":
            for j in range(entry_idx, exit_idx + 1):
                if low[j] <= sl:
                    exit_idx, exit_price, reason = j, sl, "stop_loss"
                    break
                if high[j] >= tp:
                    exit_idx, exit_price, reason = j, tp, "take_profit"
                    break
            exit_exec = exit_price * (1 - slippage_pct)
            gross = exit_exec / entry - 1
        else:
            for j in range(entry_idx, exit_idx + 1):
                if high[j] >= sl:
                    exit_idx, exit_price, reason = j, sl, "stop_loss"
                    break
                if low[j] <= tp:
                    exit_idx, exit_price, reason = j, tp, "take_profit"
                    break
            exit_exec = exit_price * (1 + slippage_pct)
            gross = entry / exit_exec - 1
        net = gross - 2 * fee_pct
        equity += equity * position_pct * net
        curve.append(equity)
        trades.append({"net_return_pct": net * 100, "reason": reason})
        i = exit_idx + 1
    return summarize(trades, curve)


def build_summary(windows):
    grouped = {}
    for row in windows:
        key = (row["symbol"], row["family"], row["scenario"], row["position_pct"])
        grouped.setdefault(key, []).append(row)
    out = []
    for key, rows in grouped.items():
        by_period = {r["period"]: r for r in rows}
        ref = by_period.get("730d") or by_period.get("365d")
        if not ref:
            continue
        returns = [float(r["return_pct"]) for r in rows]
        dds = [float(r["max_dd_pct"]) for r in rows]
        pfs = [float(r["profit_factor"]) for r in rows]
        out.append(
            {
                "symbol": ref["symbol"],
                "family": ref["family"],
                "direction": ref["direction"],
                "scenario": ref["scenario"],
                "position_pct": ref["position_pct"],
                "positive_windows": sum(r > 0 for r in returns),
                "windows_count": len(rows),
                "min_return_pct": min(returns),
                "max_dd_any_pct": max(dds),
                "min_pf": min(pfs),
                "return_30d_pct": by_period.get("30d", {}).get("return_pct", ""),
                "return_60d_pct": by_period.get("60d", {}).get("return_pct", ""),
                "return_90d_pct": by_period.get("90d", {}).get("return_pct", ""),
                "return_180d_pct": by_period.get("180d", {}).get("return_pct", ""),
                "return_365d_pct": by_period.get("365d", {}).get("return_pct", ""),
                "return_730d_pct": by_period.get("730d", {}).get("return_pct", ""),
                "pf_365d": by_period.get("365d", {}).get("profit_factor", ""),
                "pf_730d": by_period.get("730d", {}).get("profit_factor", ""),
                "dd_365d_pct": by_period.get("365d", {}).get("max_dd_pct", ""),
                "dd_730d_pct": by_period.get("730d", {}).get("max_dd_pct", ""),
                "trades_365d": by_period.get("365d", {}).get("trades", ""),
                "trades_730d": by_period.get("730d", {}).get("trades", ""),
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "stress",
            int(r["positive_windows"]),
            float(r.get("return_730d_pct") or r.get("return_365d_pct") or -999),
            float(r.get("pf_730d") or r.get("pf_365d") or 0),
            -float(r.get("max_dd_any_pct") or 999),
        ),
        reverse=True,
    )
    return out


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "symbol", "family", "direction", "scenario", "position_pct", "positive_windows", "windows_count",
        "return_30d_pct", "return_60d_pct", "return_90d_pct", "return_180d_pct",
        "return_365d_pct", "return_730d_pct", "pf_365d", "pf_730d",
        "dd_365d_pct", "dd_730d_pct", "max_dd_any_pct", "trades_365d", "trades_730d",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(v):
    if v in ("", None) or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{float(v):+.2f}"


def save_report(path, summary, windows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    strict = [
        r for r in summary
        if r["scenario"] == "stress"
        and int(r["positive_windows"]) >= 5
        and float(r.get("return_365d_pct") or -999) > 0
        and float(r.get("return_730d_pct") or 0) > -10
        and float(r.get("pf_365d") or 0) >= 1.05
        and float(r.get("max_dd_any_pct") or 999) <= 40
    ]
    lines = [
        "# New Strategy Family Search",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        f"- Summary rows: `{len(summary)}`",
        f"- Window rows: `{len(windows)}`",
        f"- Strict stress candidates: `{len(strict)}`",
        "",
        "## Strict Stress Candidates",
        "",
        "| # | Symbol | Family | Pos | Win | 365d | 730d | PF365 | PF730 | DD365 | DD730 | Trades365 |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(strict[:80], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | `{r['family']}` | {float(r['position_pct']):.0%} | "
            f"{r['positive_windows']}/{r['windows_count']} | {fmt(r['return_365d_pct'])}% | {fmt(r['return_730d_pct'])}% | "
            f"{float(r.get('pf_365d') or 0):.2f} | {float(r.get('pf_730d') or 0):.2f} | "
            f"{float(r.get('dd_365d_pct') or 0):.2f}% | {float(r.get('dd_730d_pct') or 0):.2f}% | {r.get('trades_365d')} |"
        )
    lines.extend(["", "## Top Overall", ""])
    lines.extend(lines[8:10])
    for i, r in enumerate(summary[:80], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | `{r['family']}` | {float(r['position_pct']):.0%} | "
            f"{r['positive_windows']}/{r['windows_count']} | {fmt(r['return_365d_pct'])}% | {fmt(r['return_730d_pct'])}% | "
            f"{float(r.get('pf_365d') or 0):.2f} | {float(r.get('pf_730d') or 0):.2f} | "
            f"{float(r.get('dd_365d_pct') or 0):.2f}% | {float(r.get('dd_730d_pct') or 0):.2f}% | {r.get('trades_365d')} |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    symbols = load_symbols(os.path.join(ROOT, args.universe), args.top_symbols)
    scenarios = [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]
    positions = [0.10, 0.25]
    windows_out = []
    for idx, symbol in enumerate(symbols, 1):
        path = os.path.join(ROOT, args.raw_1m_dir, f"{symbol}_1m.csv")
        print(f"[{idx}/{len(symbols)}] loading {symbol}", flush=True)
        df = read_symbol(path)
        df = add_closed_htf(add_closed_htf(add_indicators(df), 60), 240)
        for family in FAMILIES:
            signal = build_signal(df, family)
            print(f"  {family['name']} signals={int(signal.sum())}", flush=True)
            if signal.sum() == 0:
                continue
            for scenario, fee_pct, slippage_pct in scenarios:
                for position_pct in positions:
                    for days in WINDOWS:
                        bars = days * 1440
                        if len(df) < bars + 300:
                            continue
                        sub = df.tail(bars + 300).reset_index(drop=True)
                        sub_signal = signal[-(bars + 300):]
                        summary = run_backtest(sub, sub_signal, family, position_pct, fee_pct, slippage_pct)
                        windows_out.append(
                            {
                                "symbol": symbol,
                                "family": family["name"],
                                "direction": family["direction"],
                                "scenario": scenario,
                                "position_pct": position_pct,
                                "fee_pct": fee_pct,
                                "slippage_pct": slippage_pct,
                                "period": f"{days}d",
                                **{k: v for k, v in summary.items() if k != "exit_reasons"},
                                "take_profit": summary["exit_reasons"].get("take_profit", 0),
                                "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                                "time_stop": summary["exit_reasons"].get("time_stop", 0),
                            }
                        )
    summary = build_summary(windows_out)
    save_csv(os.path.join(ROOT, args.save_windows), windows_out)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_report(os.path.join(ROOT, args.save_report), summary, windows_out)
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
