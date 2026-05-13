#!/usr/bin/env python3
"""Validate the selected DYDX Pullback SHORT strategy.

Selected from `dydx_pullback_short_tune.py`:
- 1h + 4h short regime;
- close below EMA200;
- pullback near EMA20/EMA50;
- RSI 48-62;
- ATR% 0.25%-1.20%;
- TP 0.7%, SL 3%, time stop 180m.
"""

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0
WINDOWS_DAYS = [1, 7, 30, 60, 90, 180, 365, 730]
PARAMS = {
    "position_pct": 0.25,
    "tp": 0.007,
    "sl": 0.030,
    "time_stop": 180,
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Validate selected DYDX Pullback SHORT.")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-windows", default=f"data/dydx_pullback_short_selected_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/dydx_pullback_short_selected_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/DYDX/dydx-pullback-short-selected-{today}.md")
    return parser.parse_args()


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
    rng = (high - low).replace(0, np.nan)
    df["red"] = close < df["open"]
    df["upper_wick_ratio"] = (high - pd.concat([close, df["open"]], axis=1).max(axis=1)) / rng
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
    htf[f"htf{minutes}_short"] = (htf["close"] < htf["ema200"]) & (htf["ema20"] < htf["ema50"])
    htf["usable_time_ms"] = (htf["time"].astype("int64") // 1_000_000) + minutes * 60_000
    perm = htf[["usable_time_ms", f"htf{minutes}_short"]].rename(columns={"usable_time_ms": "open_time_ms"})
    merged = pd.merge_asof(
        df[["open_time_ms"]].sort_values("open_time_ms"),
        perm.sort_values("open_time_ms"),
        on="open_time_ms",
        direction="backward",
    )
    df[f"htf{minutes}_short"] = merged[f"htf{minutes}_short"].fillna(False).to_numpy()
    return df


def signal(df):
    return (
        df["htf60_short"]
        & df["htf240_short"]
        & (df["close"] < df["ema200"])
        & (df["close"] >= df["ema20"] * 0.997)
        & (df["close"] <= df["ema50"] * 1.008)
        & df["rsi14"].between(48, 62)
        & df["red"]
        & df["atr_pct"].between(0.0025, 0.012)
        & (df["upper_wick_ratio"] < 0.45)
    ).to_numpy()


def summarize(trades, curve):
    if not trades:
        return {"trades": 0, "return_pct": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "max_dd_pct": 0.0, "expectancy_pct": 0.0, "exit_reasons": {}}
    returns = [t["net_return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0)
    return {
        "trades": len(trades),
        "return_pct": (curve[-1] / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def run_backtest(df, sig, fee_pct, slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    equity = INITIAL_BALANCE
    curve = [equity]
    trades = []
    indices = np.flatnonzero(sig)
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
        entry = open_[entry_idx] * (1.0 - slippage_pct)
        tp = entry * (1.0 - PARAMS["tp"])
        sl = entry * (1.0 + PARAMS["sl"])
        exit_idx = min(entry_idx + PARAMS["time_stop"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        for j in range(entry_idx, exit_idx + 1):
            if high[j] >= sl:
                exit_idx, exit_price, reason = j, sl, "stop_loss"
                break
            if low[j] <= tp:
                exit_idx, exit_price, reason = j, tp, "take_profit"
                break
        exit_exec = exit_price * (1.0 + slippage_pct)
        gross = entry / exit_exec - 1.0
        net = gross - 2.0 * fee_pct
        equity += equity * PARAMS["position_pct"] * net
        curve.append(equity)
        trades.append(
            {
                "entry_time": iso(int(times[entry_idx])),
                "exit_time": iso(int(times[exit_idx])),
                "net_return_pct": net * 100.0,
                "reason": reason,
                "equity_after": equity,
            }
        )
        i = exit_idx + 1
    return summarize(trades, curve), trades


def month_key(value):
    return value[:7]


def monthly_from_trades(trades):
    months = defaultdict(list)
    for trade in trades:
        months[month_key(trade["exit_time"])].append(trade)
    rows = []
    equity = INITIAL_BALANCE
    for month in sorted(months):
        start = equity
        rets = []
        reasons = Counter()
        for trade in months[month]:
            ret = trade["net_return_pct"] * PARAMS["position_pct"]
            equity *= 1.0 + ret / 100.0
            rets.append(ret)
            reasons[trade["reason"]] += 1
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        rows.append(
            {
                "month": month,
                "start_equity": start,
                "end_equity": equity,
                "return_pct": (equity / start - 1.0) * 100.0 if start else 0.0,
                "trades": len(rets),
                "win_rate_pct": len(wins) / len(rets) * 100.0 if rets else 0.0,
                "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
            }
        )
    return rows


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(v):
    return f"{float(v):+.2f}"


def write_report(path, windows, monthly):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# DYDX Pullback SHORT Selected",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Новая стратегия: SHORT отката в нисходящем режиме DYDX.",
        "",
        "## Windows",
        "",
        "| Scenario | Period | Return | MaxDD | PF | Winrate | Trades | TP | Time | SL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in windows:
        lines.append(
            f"| {row['scenario']} | {row['period']} | {fmt(row['return_pct'])}% | {float(row['max_dd_pct']):.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% | {row['trades']} | "
            f"{row['take_profit']} | {row['time_stop']} | {row['stop_loss']} |"
        )
    pos_months = sum(float(row["return_pct"]) > 0 for row in monthly)
    lines.extend(
        [
            "",
            "## Monthly 730d Stress",
            "",
            f"- Плюсовые месяцы: `{pos_months}/{len(monthly)}`",
            "",
            "| Month | Return | Trades | PF | Winrate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in monthly:
        lines.append(
            f"| {row['month']} | {fmt(row['return_pct'])}% | {row['trades']} | {float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Direction: SHORT only.",
            "- Higher timeframe: closed 1h and closed 4h must both be bearish.",
            "- Entry: price below EMA200, pullback near EMA20/EMA50, RSI 48-62, red candle.",
            "- Volatility: ATR% between 0.25% and 1.20%.",
            "- Exit: TP 0.7%, SL 3%, time stop 180 minutes.",
            "- Position: 25% equity.",
            "- Stress used here: fee 0.04% per side, slippage 0.02% per side.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    df = read_symbol(os.path.join(ROOT, args.raw_1m_dir, "DYDXUSDT_1m.csv"))
    df = add_closed_htf(add_closed_htf(add_indicators(df), 60), 240)
    sig = signal(df)
    windows = []
    monthly = []
    for scenario, fee_pct, slippage_pct in [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]:
        for days in WINDOWS_DAYS:
            bars = days * 1440
            if len(df) < bars + 300:
                continue
            sub = df.tail(bars + 300).reset_index(drop=True)
            sub_sig = sig[-(bars + 300):]
            summary, trades = run_backtest(sub, sub_sig, fee_pct, slippage_pct)
            row = {
                "scenario": scenario,
                "period": f"{days}d",
                **{k: v for k, v in summary.items() if k != "exit_reasons"},
                "take_profit": summary["exit_reasons"].get("take_profit", 0),
                "time_stop": summary["exit_reasons"].get("time_stop", 0),
                "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
            }
            windows.append(row)
            if scenario == "stress" and days == 730:
                monthly = monthly_from_trades(trades)
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly)
    write_report(os.path.join(ROOT, args.save_report), windows, monthly)
    print(f"signals={int(sig.sum())}")
    for row in windows:
        print(
            f"{row['scenario']} {row['period']} return={row['return_pct']:.2f}% "
            f"dd={row['max_dd_pct']:.2f}% pf={row['profit_factor']:.2f} trades={row['trades']}"
        )
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
