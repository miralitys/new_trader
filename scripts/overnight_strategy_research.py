#!/usr/bin/env python3
"""Overnight search for new, diverse 1m strategy families.

This is intentionally broader than the GALA/DYDX work:

Stage 1:
- scan many symbols with compact, diverse strategy families;
- use stress execution as the main filter;
- keep candidates that survive 30/90/365d.

Stage 2:
- run deeper 1/7/30/60/90/180/365/730d validation on the best candidates;
- save monthly checks for the strongest final candidates.

The script is designed for unattended overnight runs. It writes incremental CSV
and Markdown reports as it progresses.
"""

import argparse
import csv
import math
import os
import random
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from glob import glob

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0
STAGE1_WINDOWS = [30, 90, 365]
DEEP_WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
SCENARIOS = {
    "base": (0.0002, 0.0),
    "stress": (0.0004, 0.0002),
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Overnight new strategy research.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--max-hours", type=float, default=7.0)
    parser.add_argument("--max-symbols", type=int, default=0, help="0 means all available symbols")
    parser.add_argument("--stage1-top", type=int, default=80)
    parser.add_argument("--deep-top", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-stage1", default=f"data/overnight_strategy_stage1_{today}.csv")
    parser.add_argument("--save-deep", default=f"data/overnight_strategy_deep_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/overnight_strategy_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/overnight-new-strategy-research-{today}.md")
    return parser.parse_args()


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def symbol_from_path(path):
    return os.path.basename(path).replace("_1m.csv", "")


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
    open_ = df["open"]
    volume = df["volume"]
    df["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    df["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    df["ema200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    df["ema_slope20"] = df["ema20"] / df["ema20"].shift(20) - 1.0
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
    df["vol_sma60"] = volume.rolling(60, min_periods=60).mean()
    df["high20"] = high.shift(1).rolling(20, min_periods=20).max()
    df["low20"] = low.shift(1).rolling(20, min_periods=20).min()
    df["high60"] = high.shift(1).rolling(60, min_periods=60).max()
    df["low60"] = low.shift(1).rolling(60, min_periods=60).min()
    rng = (high - low).replace(0, np.nan)
    df["body_ratio"] = (close - open_).abs() / rng
    df["green"] = close > open_
    df["red"] = close < open_
    df["upper_wick_ratio"] = (high - pd.concat([close, open_], axis=1).max(axis=1)) / rng
    df["lower_wick_ratio"] = (pd.concat([close, open_], axis=1).min(axis=1) - low) / rng
    df["ret_1h"] = close / close.shift(60) - 1.0
    df["ret_24h"] = close / close.shift(1440) - 1.0
    df["ret_7d"] = close / close.shift(1440 * 7) - 1.0
    return df


def add_htf(df, minutes):
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


def prepare(df):
    return add_htf(add_htf(add_indicators(df), 60), 240)


def strategy_variants(stage="stage1"):
    variants = []
    # 1. Trend pullback: similar idea to DYDX, but both long and short.
    for direction in ["long", "short"]:
        for rsi_min, rsi_max in ([(38, 52), (42, 58), (48, 62)] if direction == "short" else [(38, 52), (42, 58), (50, 65)]):
            for tp, sl, tstop in [(0.005, 0.020, 120), (0.008, 0.030, 180)]:
                variants.append(
                    {
                        "family": "trend_pullback",
                        "direction": direction,
                        "variant": f"trend_pullback_{direction}_rsi{rsi_min}-{rsi_max}_tp{tp}_sl{sl}_t{tstop}",
                        "rsi_min": rsi_min,
                        "rsi_max": rsi_max,
                        "tp": tp,
                        "sl": sl,
                        "time_stop": tstop,
                        "position_pct": 0.65,
                    }
                )
    # 2. Breakout continuation with volume.
    for direction in ["long", "short"]:
        for breakout in [20, 60]:
            for tp, sl, tstop in [(0.004, 0.018, 90), (0.007, 0.025, 150)]:
                variants.append(
                    {
                        "family": "breakout_continuation",
                        "direction": direction,
                        "variant": f"breakout_{direction}_{breakout}_tp{tp}_sl{sl}_t{tstop}",
                        "breakout": breakout,
                        "tp": tp,
                        "sl": sl,
                        "time_stop": tstop,
                        "position_pct": 0.50,
                    }
                )
    # 3. Reversal after exhaustion, more conservative size.
    for direction in ["long", "short"]:
        for ret_limit in [0.05, 0.08]:
            for tp, sl, tstop in [(0.004, 0.018, 90), (0.006, 0.025, 150)]:
                variants.append(
                    {
                        "family": "exhaustion_reversal",
                        "direction": direction,
                        "variant": f"exhaustion_{direction}_ret{ret_limit}_tp{tp}_sl{sl}_t{tstop}",
                        "ret_limit": ret_limit,
                        "tp": tp,
                        "sl": sl,
                        "time_stop": tstop,
                        "position_pct": 0.35,
                    }
                )
    # 4. Volatility expansion in HTF regime.
    for direction in ["long", "short"]:
        for atr_min in [0.0025, 0.004]:
            variants.append(
                {
                    "family": "vol_expansion",
                    "direction": direction,
                    "variant": f"vol_expansion_{direction}_atr{atr_min}",
                    "atr_min": atr_min,
                    "tp": 0.008,
                    "sl": 0.028,
                    "time_stop": 180,
                    "position_pct": 0.50,
                }
            )
    if stage == "deep":
        deep = []
        for v in variants:
            deep.append(v)
            for pos in [0.25, 0.50, 0.75, 1.0]:
                vv = dict(v)
                vv["position_pct"] = pos
                vv["variant"] = f"{v['variant']}_pos{pos:g}"
                deep.append(vv)
        return deep
    return variants


def signal_for(df, v):
    direction = v["direction"]
    if v["family"] == "trend_pullback":
        if direction == "short":
            sig = (
                df["htf60_short"]
                & df["htf240_short"]
                & (df["close"] < df["ema200"])
                & (df["close"] >= df["ema20"] * 0.995)
                & (df["close"] <= df["ema50"] * 1.012)
                & df["rsi14"].between(v["rsi_min"], v["rsi_max"])
                & df["red"]
                & df["atr_pct"].between(0.002, 0.018)
                & (df["upper_wick_ratio"] < 0.50)
                & (df["ret_24h"].fillna(0).abs() <= 0.20)
            )
        else:
            sig = (
                df["htf60_long"]
                & df["htf240_long"]
                & (df["close"] > df["ema200"])
                & (df["close"] <= df["ema20"] * 1.005)
                & (df["close"] >= df["ema50"] * 0.988)
                & df["rsi14"].between(v["rsi_min"], v["rsi_max"])
                & df["green"]
                & df["atr_pct"].between(0.002, 0.018)
                & (df["lower_wick_ratio"] < 0.50)
                & (df["ret_24h"].fillna(0).abs() <= 0.20)
            )
    elif v["family"] == "breakout_continuation":
        level = df["high20"] if v["breakout"] == 20 else df["high60"]
        low_level = df["low20"] if v["breakout"] == 20 else df["low60"]
        if direction == "long":
            sig = (
                df["htf60_long"]
                & (df["close"] > level)
                & df["green"]
                & (df["body_ratio"] > 0.45)
                & (df["volume"] > df["vol_sma20"] * 1.3)
                & df["atr_pct"].between(0.0015, 0.020)
            )
        else:
            sig = (
                df["htf60_short"]
                & (df["close"] < low_level)
                & df["red"]
                & (df["body_ratio"] > 0.45)
                & (df["volume"] > df["vol_sma20"] * 1.3)
                & df["atr_pct"].between(0.0015, 0.020)
            )
    elif v["family"] == "exhaustion_reversal":
        if direction == "long":
            sig = (
                (df["ret_24h"] <= -v["ret_limit"])
                & (df["rsi14"] < 32)
                & (df["lower_wick_ratio"] > 0.35)
                & df["green"]
                & (df["volume"] > df["vol_sma20"] * 1.1)
                & df["atr_pct"].between(0.003, 0.030)
            )
        else:
            sig = (
                (df["ret_24h"] >= v["ret_limit"])
                & (df["rsi14"] > 68)
                & (df["upper_wick_ratio"] > 0.35)
                & df["red"]
                & (df["volume"] > df["vol_sma20"] * 1.1)
                & df["atr_pct"].between(0.003, 0.030)
            )
    elif v["family"] == "vol_expansion":
        if direction == "long":
            sig = (
                df["htf60_long"]
                & (df["atr_pct"] >= v["atr_min"])
                & (df["atr_pct"] > df["atr_pct"].rolling(120, min_periods=120).median() * 1.3)
                & (df["volume"] > df["vol_sma60"] * 1.5)
                & (df["close"] > df["ema20"])
                & df["green"]
                & (df["ret_1h"] > 0)
            )
        else:
            sig = (
                df["htf60_short"]
                & (df["atr_pct"] >= v["atr_min"])
                & (df["atr_pct"] > df["atr_pct"].rolling(120, min_periods=120).median() * 1.3)
                & (df["volume"] > df["vol_sma60"] * 1.5)
                & (df["close"] < df["ema20"])
                & df["red"]
                & (df["ret_1h"] < 0)
            )
    else:
        raise ValueError(v["family"])
    return sig.fillna(False).to_numpy()


def summarize(trades, curve):
    if not trades:
        return {"trades": 0, "return_pct": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "max_dd_pct": 0.0, "expectancy_pct": 0.0, "exit_reasons": {}}
    returns = [t["deposit_return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100 if peak else 0.0)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "return_pct": (curve[-1] / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, sig, v, fee_pct, slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    equity = INITIAL_BALANCE
    curve = [equity]
    trades = []
    indices = np.flatnonzero(sig)
    ptr = 0
    i = 250
    n = len(df)
    direction = v["direction"]
    while i < n - 2 and equity > 0:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        i = int(indices[ptr])
        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = open_[entry_idx] * (1 + slippage_pct if direction == "long" else 1 - slippage_pct)
        if direction == "long":
            tp = entry * (1 + v["tp"])
            sl = entry * (1 - v["sl"])
        else:
            tp = entry * (1 - v["tp"])
            sl = entry * (1 + v["sl"])
        exit_idx = min(entry_idx + v["time_stop"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        for j in range(entry_idx, exit_idx + 1):
            if direction == "long":
                if low[j] <= sl:
                    exit_idx, exit_price, reason = j, sl, "stop_loss"
                    break
                if high[j] >= tp:
                    exit_idx, exit_price, reason = j, tp, "take_profit"
                    break
            else:
                if high[j] >= sl:
                    exit_idx, exit_price, reason = j, sl, "stop_loss"
                    break
                if low[j] <= tp:
                    exit_idx, exit_price, reason = j, tp, "take_profit"
                    break
        exit_exec = exit_price * (1 - slippage_pct if direction == "long" else 1 + slippage_pct)
        gross = exit_exec / entry - 1 if direction == "long" else entry / exit_exec - 1
        net = gross - 2 * fee_pct
        dep_ret = v["position_pct"] * net
        equity *= 1 + dep_ret
        equity = max(equity, 0.0)
        curve.append(equity)
        trades.append({"deposit_return_pct": dep_ret * 100, "reason": reason})
        i = exit_idx + 1
    return summarize(trades, curve)


def period_slice(df, sig, days):
    bars = days * 1440
    if len(df) < bars + 300:
        return None, None
    sub_len = bars + 300
    return df.tail(sub_len).reset_index(drop=True), sig[-sub_len:]


def row_for(symbol, df, sig, v, days, scenario):
    sub, sub_sig = period_slice(df, sig, days)
    if sub is None:
        return None
    fee, slip = SCENARIOS[scenario]
    summary = run_backtest(sub, sub_sig, v, fee, slip)
    return {
        "symbol": symbol,
        "family": v["family"],
        "direction": v["direction"],
        "variant": v["variant"],
        "scenario": scenario,
        "period": f"{days}d",
        "position_pct": v["position_pct"],
        "tp": v["tp"],
        "sl": v["sl"],
        "time_stop": v["time_stop"],
        **{k: val for k, val in summary.items() if k != "exit_reasons"},
        "take_profit": summary["exit_reasons"].get("take_profit", 0),
        "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
        "time_stop_exit": summary["exit_reasons"].get("time_stop", 0),
    }


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "symbol", "family", "direction", "variant", "scenario", "period", "position_pct",
        "return_pct", "max_dd_pct", "profit_factor", "win_rate_pct", "expectancy_pct", "trades",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["symbol"], row["family"], row["direction"], row["variant"], row["scenario"])].append(row)
    out = []
    for key, items in grouped.items():
        by = {r["period"]: r for r in items}
        returns = [r["return_pct"] for r in items]
        dds = [r["max_dd_pct"] for r in items]
        pfs = [r["profit_factor"] for r in items if r["trades"] > 0]
        ref = items[0]
        out.append(
            {
                "symbol": ref["symbol"],
                "family": ref["family"],
                "direction": ref["direction"],
                "variant": ref["variant"],
                "scenario": ref["scenario"],
                "positive_windows": sum(r > 0 for r in returns),
                "windows_count": len(items),
                "min_return_pct": min(returns),
                "max_dd_any_pct": max(dds),
                "min_pf": min(pfs) if pfs else 0.0,
                "return_1d_pct": by.get("1d", {}).get("return_pct", ""),
                "return_7d_pct": by.get("7d", {}).get("return_pct", ""),
                "return_30d_pct": by.get("30d", {}).get("return_pct", ""),
                "return_60d_pct": by.get("60d", {}).get("return_pct", ""),
                "return_90d_pct": by.get("90d", {}).get("return_pct", ""),
                "return_180d_pct": by.get("180d", {}).get("return_pct", ""),
                "return_365d_pct": by.get("365d", {}).get("return_pct", ""),
                "return_730d_pct": by.get("730d", {}).get("return_pct", ""),
                "pf_365d": by.get("365d", {}).get("profit_factor", ""),
                "pf_730d": by.get("730d", {}).get("profit_factor", ""),
                "dd_365d_pct": by.get("365d", {}).get("max_dd_pct", ""),
                "dd_730d_pct": by.get("730d", {}).get("max_dd_pct", ""),
                "trades_30d": by.get("30d", {}).get("trades", ""),
                "trades_365d": by.get("365d", {}).get("trades", ""),
                "trades_730d": by.get("730d", {}).get("trades", ""),
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "stress",
            int(r["positive_windows"]),
            float(r.get("return_365d_pct") or -999),
            float(r.get("return_730d_pct") or -999),
            -float(r.get("max_dd_any_pct") or 999),
        ),
        reverse=True,
    )
    return out


def monthly_check(symbol, df, sig, v, scenario):
    fee, slip = SCENARIOS[scenario]
    months = []
    times = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    month_keys = times.dt.strftime("%Y-%m")
    for month in sorted(month_keys.unique())[-36:]:
        mask = month_keys == month
        idx = np.flatnonzero(mask.to_numpy())
        if len(idx) < 300:
            continue
        start = max(0, idx[0] - 300)
        end = idx[-1] + 1
        sub = df.iloc[start:end].reset_index(drop=True)
        sub_sig = sig[start:end]
        summary = run_backtest(sub, sub_sig, v, fee, slip)
        months.append(
            {
                "symbol": symbol,
                "family": v["family"],
                "direction": v["direction"],
                "variant": v["variant"],
                "scenario": scenario,
                "month": month,
                **{k: val for k, val in summary.items() if k != "exit_reasons"},
            }
        )
    return months


def write_report(path, stage1_rows, deep_rows, monthly_rows, started_at, finished=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stage1 = aggregate(stage1_rows)
    deep = aggregate(deep_rows)
    stress_deep = [
        r for r in deep
        if r["scenario"] == "stress"
        and int(r["positive_windows"]) >= max(3, int(r["windows_count"]) - 1)
        and float(r.get("return_365d_pct") or -999) > 0
        and float(r.get("pf_365d") or 0) >= 1.05
    ]
    lines = [
        "# Overnight New Strategy Research",
        "",
        f"Started UTC: `{started_at}`",
        f"Updated UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"Status: `{'finished' if finished else 'running'}`",
        "",
        f"- Stage 1 rows: `{len(stage1_rows)}`",
        f"- Deep rows: `{len(deep_rows)}`",
        f"- Monthly rows: `{len(monthly_rows)}`",
        "",
        "## Best Deep Stress Candidates",
        "",
        "| # | Symbol | Family | Dir | Variant | Win | 1d | 7d | 30d | 90d | 365d | 730d | PF365 | DD365 | Trades365 |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(stress_deep[:60], 1):
        lines.append(
            f"| {i} | `{row['symbol']}` | {row['family']} | {row['direction']} | `{row['variant']}` | "
            f"{row['positive_windows']}/{row['windows_count']} | {fmt(row.get('return_1d_pct'))} | "
            f"{fmt(row.get('return_7d_pct'))} | {fmt(row.get('return_30d_pct'))} | "
            f"{fmt(row.get('return_90d_pct'))} | {fmt(row.get('return_365d_pct'))} | "
            f"{fmt(row.get('return_730d_pct'))} | {num(row.get('pf_365d'))} | "
            f"{num(row.get('dd_365d_pct'))}% | {row.get('trades_365d')} |"
        )
    lines.extend(["", "## Best Stage 1 Stress Candidates", ""])
    lines.extend(["| # | Symbol | Family | Dir | Variant | Win | 30d | 90d | 365d | PF365 | DD365 |", "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|"])
    for i, row in enumerate([r for r in stage1 if r["scenario"] == "stress"][:80], 1):
        lines.append(
            f"| {i} | `{row['symbol']}` | {row['family']} | {row['direction']} | `{row['variant']}` | "
            f"{row['positive_windows']}/{row['windows_count']} | {fmt(row.get('return_30d_pct'))} | "
            f"{fmt(row.get('return_90d_pct'))} | {fmt(row.get('return_365d_pct'))} | "
            f"{num(row.get('pf_365d'))} | {num(row.get('dd_365d_pct'))}% |"
        )
    if monthly_rows:
        mdf = pd.DataFrame(monthly_rows)
        lines.extend(["", "## Monthly Stability For Final Candidates", ""])
        lines.extend(["| Symbol | Family | Variant | Scenario | Months + | Months - | Worst | Best | Avg |", "|---|---|---|---|---:|---:|---:|---:|---:|"])
        for (symbol, family, variant, scenario), group in mdf.groupby(["symbol", "family", "variant", "scenario"]):
            ret = group["return_pct"]
            lines.append(
                f"| `{symbol}` | {family} | `{variant}` | {scenario} | {(ret > 0).sum()}/{len(ret)} | "
                f"{(ret < 0).sum()}/{len(ret)} | {ret.min():+.2f}% | {ret.max():+.2f}% | {ret.mean():+.2f}% |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Stage 1 CSV: `{os.path.relpath(args_global.save_stage1, ROOT) if args_global else ''}`",
            f"- Deep CSV: `{os.path.relpath(args_global.save_deep, ROOT) if args_global else ''}`",
            f"- Monthly CSV: `{os.path.relpath(args_global.save_monthly, ROOT) if args_global else ''}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def fmt(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):+.2f}%"


def num(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


args_global = None


def main():
    global args_global
    args = parse_args()
    args_global = args
    random.seed(args.seed)
    started = datetime.now(timezone.utc).isoformat()
    deadline = time.time() + args.max_hours * 3600
    paths = sorted(glob(os.path.join(ROOT, args.raw_dir, "*USDT_1m.csv")))
    random.shuffle(paths)
    if args.max_symbols > 0:
        paths = paths[: args.max_symbols]

    stage1_rows = []
    deep_rows = []
    monthly_rows = []
    stage1_variants = strategy_variants("stage1")
    deep_variants = strategy_variants("deep")

    print(f"started={started} symbols={len(paths)} stage1_variants={len(stage1_variants)}", flush=True)
    for index, path in enumerate(paths, 1):
        if time.time() > deadline:
            print("deadline reached during stage1", flush=True)
            break
        symbol = symbol_from_path(path)
        try:
            raw = read_symbol(path)
            if len(raw) < 365 * 1440 + 300:
                continue
            df = prepare(raw)
            for variant in stage1_variants:
                sig = signal_for(df, variant)
                if int(sig.sum()) < 30:
                    continue
                for scenario in ["stress"]:
                    for days in STAGE1_WINDOWS:
                        row = row_for(symbol, df, sig, variant, days, scenario)
                        if row:
                            stage1_rows.append(row)
            if index % 10 == 0:
                print(f"stage1 {index}/{len(paths)} rows={len(stage1_rows)} symbol={symbol}", flush=True)
                save_csv(os.path.join(ROOT, args.save_stage1), stage1_rows)
                write_report(os.path.join(ROOT, args.save_report), stage1_rows, deep_rows, monthly_rows, started)
        except Exception as exc:
            print(f"stage1 error {symbol}: {exc}", flush=True)

    save_csv(os.path.join(ROOT, args.save_stage1), stage1_rows)
    stage1_agg = aggregate(stage1_rows)
    candidate_keys = []
    for row in stage1_agg:
        if row["scenario"] != "stress":
            continue
        if int(row["positive_windows"]) < 2:
            continue
        if float(row.get("return_365d_pct") or -999) <= 0:
            continue
        if float(row.get("pf_365d") or 0) < 1.03:
            continue
        if float(row.get("trades_365d") or 0) < 20:
            continue
        candidate_keys.append((row["symbol"], row["family"], row["direction"]))
        if len(candidate_keys) >= args.stage1_top:
            break
    candidate_symbols = sorted(set(symbol for symbol, _, _ in candidate_keys))
    print(f"stage2 candidates={len(candidate_symbols)}", flush=True)

    for index, symbol in enumerate(candidate_symbols, 1):
        if time.time() > deadline:
            print("deadline reached during deep", flush=True)
            break
        path = os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")
        try:
            df = prepare(read_symbol(path))
            wanted_families = {family for sym, family, _ in candidate_keys if sym == symbol}
            for variant in deep_variants:
                if variant["family"] not in wanted_families:
                    continue
                sig = signal_for(df, variant)
                if int(sig.sum()) < 30:
                    continue
                for scenario in ["base", "stress"]:
                    for days in DEEP_WINDOWS:
                        row = row_for(symbol, df, sig, variant, days, scenario)
                        if row:
                            deep_rows.append(row)
            if index % 5 == 0:
                print(f"deep {index}/{len(candidate_symbols)} rows={len(deep_rows)} symbol={symbol}", flush=True)
                save_csv(os.path.join(ROOT, args.save_deep), deep_rows)
                write_report(os.path.join(ROOT, args.save_report), stage1_rows, deep_rows, monthly_rows, started)
        except Exception as exc:
            print(f"deep error {symbol}: {exc}", flush=True)

    save_csv(os.path.join(ROOT, args.save_deep), deep_rows)
    deep_agg = aggregate(deep_rows)
    final = [
        r for r in deep_agg
        if r["scenario"] == "stress"
        and int(r["positive_windows"]) >= max(5, int(r["windows_count"]) - 2)
        and float(r.get("return_365d_pct") or -999) > 0
        and float(r.get("pf_365d") or 0) >= 1.05
        and float(r.get("trades_365d") or 0) >= 20
    ][: args.deep_top]
    for row in final:
        if time.time() > deadline:
            break
        try:
            df = prepare(read_symbol(os.path.join(ROOT, args.raw_dir, f"{row['symbol']}_1m.csv")))
            variant = next(v for v in deep_variants if v["variant"] == row["variant"])
            sig = signal_for(df, variant)
            monthly_rows.extend(monthly_check(row["symbol"], df, sig, variant, "stress"))
        except Exception as exc:
            print(f"monthly error {row['symbol']} {row['variant']}: {exc}", flush=True)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows)
    write_report(os.path.join(ROOT, args.save_report), stage1_rows, deep_rows, monthly_rows, started, finished=True)
    print(f"finished stage1={len(stage1_rows)} deep={len(deep_rows)} monthly={len(monthly_rows)}", flush=True)
    print(f"report={os.path.join(ROOT, args.save_report)}", flush=True)


if __name__ == "__main__":
    main()
