#!/usr/bin/env python3
"""Compact rescue validation for the top-N stage-4 candidates.

This keeps every candidate's original direction and entry logic, then adds a
small practical overlay grid:

- no higher timeframe filter / 1h / 4h / 1h+4h;
- no return guard / conservative return guard;
- no kill switch / daily 1% + weekly 4%;
- position 10/15/20/25%;
- base and stress execution.
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


def parse_args():
    parser = argparse.ArgumentParser(description="Stage-5 compact rescue test for top-N market candidates.")
    parser.add_argument("--input", default="data/market_stage4_top50_universe.csv")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default="data/market_stage5_top20_rescue_summary.csv")
    parser.add_argument("--save-windows", default="data/market_stage5_top20_rescue_windows.csv")
    parser.add_argument("--save-months", default="data/market_stage5_top20_rescue_months.csv")
    parser.add_argument("--save-report", default="strategies/market-stage5-top20-rescue.md")
    return parser.parse_args()


def read_rows(path, top_n):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))[:top_n]
    return rows


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
    df["ret_24h"] = close / close.shift(1440) - 1.0
    df["ret_7d"] = close / close.shift(1440 * 7) - 1.0
    return df


def add_closed_htf_permissions(df, minutes):
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


def score_arrays(df, regime):
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
    return long_score, short_score


def params_from_row(row):
    return {
        "symbol": row["symbol"],
        "variant": row["variant"],
        "direction": row["direction"],
        "threshold": int(float(row["threshold"])),
        "regime": row["regime"],
        "tp": float(row["tp"]),
        "sl": float(row["sl"]),
        "time_stop": int(float(row["time"])),
    }


def base_signal(df, params):
    long_score, short_score = score_arrays(df, params["regime"])
    if params["direction"] == "long":
        return (
            (long_score >= params["threshold"])
            & (df["close"] <= df["ema20"] * 1.010)
            & (df["upper_wick_ratio"].fillna(1) <= 0.35)
        ).to_numpy()
    return (short_score >= params["threshold"]).to_numpy()


def overlay_grid():
    rows = []
    for htf in ["none", "1h", "4h", "1h_and_4h"]:
        for return_guard in [False, True]:
            for daily_stop, weekly_stop in [(0.0, 0.0), (0.01, 0.04)]:
                rows.append(
                    {
                        "overlay": f"{htf} guard{int(return_guard)} d{daily_stop:.2f} w{weekly_stop:.2f}",
                        "htf": htf,
                        "return_guard": return_guard,
                        "daily_stop_pct": daily_stop,
                        "weekly_stop_pct": weekly_stop,
                    }
                )
    return rows


def apply_overlay(df, signal, params, overlay):
    out = signal.copy()
    direction = params["direction"]
    if overlay["htf"] == "1h":
        out &= df[f"htf60_{direction}"].to_numpy()
    elif overlay["htf"] == "4h":
        out &= df[f"htf240_{direction}"].to_numpy()
    elif overlay["htf"] == "1h_and_4h":
        out &= df[f"htf60_{direction}"].to_numpy() & df[f"htf240_{direction}"].to_numpy()
    if overlay["return_guard"]:
        if direction == "long":
            out &= (df["ret_24h"].fillna(0).to_numpy() <= 0.10) & (df["ret_7d"].fillna(0).to_numpy() <= 0.25)
        else:
            out &= (df["ret_24h"].fillna(0).to_numpy() >= -0.06) & (df["ret_7d"].fillna(0).to_numpy() >= -0.15)
    return out


def period_key(ms, mode):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    if mode == "day":
        return dt.strftime("%Y-%m-%d")
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def summarize(trades, equity_curve):
    if not trades:
        return {"trades": 0, "return_pct": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "max_dd_pct": 0.0, "expectancy_pct": 0.0, "final_equity": INITIAL_BALANCE, "exit_reasons": {}}
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
        "return_pct": (equity_curve[-1] / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (999 if gross_win > 0 else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "final_equity": equity_curve[-1],
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, signal, params, position_pct, fee_pct, slippage_pct, daily_stop_pct, weekly_stop_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    equity = INITIAL_BALANCE
    equity_curve = [equity]
    trades = []
    daily_start = {}
    weekly_start = {}
    blocked_days = set()
    blocked_weeks = set()
    n = len(df)
    signal_indices = np.flatnonzero(signal)
    ptr = 0
    i = 250
    while i < n - 2:
        while ptr < len(signal_indices) and signal_indices[ptr] < i:
            ptr += 1
        if ptr >= len(signal_indices):
            break
        i = int(signal_indices[ptr])
        if i >= n - 2:
            break
        day = period_key(times[i], "day")
        week = period_key(times[i], "week")
        daily_start.setdefault(day, equity)
        weekly_start.setdefault(week, equity)
        if day in blocked_days or week in blocked_weeks:
            i += 1
            continue
        entry_idx = i + 1
        raw_entry = open_[entry_idx]
        if params["direction"] == "long":
            entry = raw_entry * (1.0 + slippage_pct)
            tp_price = entry * (1.0 + params["tp"])
            sl_price = entry * (1.0 - params["sl"])
        else:
            entry = raw_entry * (1.0 - slippage_pct)
            tp_price = entry * (1.0 - params["tp"])
            sl_price = entry * (1.0 + params["sl"])
        notional = equity * position_pct
        exit_idx = min(entry_idx + params["time_stop"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        if params["direction"] == "long":
            for j in range(entry_idx, exit_idx + 1):
                if low[j] <= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if high[j] >= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            exit_exec = exit_price * (1.0 - slippage_pct)
            gross = exit_exec / entry - 1.0
        else:
            for j in range(entry_idx, exit_idx + 1):
                if high[j] >= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if low[j] <= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            exit_exec = exit_price * (1.0 + slippage_pct)
            gross = entry / exit_exec - 1.0
        net = gross - 2.0 * fee_pct
        equity += notional * net
        equity_curve.append(equity)
        trades.append({"exit_time_ms": int(times[exit_idx]), "net_return_pct": net * 100.0, "reason": reason})
        exit_day = period_key(times[exit_idx], "day")
        exit_week = period_key(times[exit_idx], "week")
        daily_start.setdefault(exit_day, equity)
        weekly_start.setdefault(exit_week, equity)
        if daily_stop_pct and equity / daily_start[exit_day] - 1.0 <= -daily_stop_pct:
            blocked_days.add(exit_day)
        if weekly_stop_pct and equity / weekly_start[exit_week] - 1.0 <= -weekly_stop_pct:
            blocked_weeks.add(exit_week)
        i = exit_idx + 1
    summary = summarize(trades, equity_curve)
    summary["blocked_days"] = len(blocked_days)
    summary["blocked_weeks"] = len(blocked_weeks)
    return summary, trades


def month_key(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m")


def monthly_from_trades(trades, position_pct):
    months = {}
    equity = INITIAL_BALANCE
    for trade in trades:
        key = month_key(trade["exit_time_ms"])
        item = months.setdefault(key, {"month": key, "start_equity": equity, "pnl": 0.0, "trades": 0})
        pnl = equity * position_pct * (trade["net_return_pct"] / 100.0)
        equity += pnl
        item["pnl"] += pnl
        item["trades"] += 1
        item["end_equity"] = equity
    out = []
    for item in months.values():
        start = item["start_equity"]
        item["return_pct"] = (item.get("end_equity", start) / start - 1.0) * 100.0 if start else 0.0
        out.append(item)
    return out


def build_summary(windows, months):
    grouped = {}
    for row in windows:
        key = (row["symbol"], row["variant"], row["overlay"], row["scenario"], row["position_pct"])
        grouped.setdefault(key, []).append(row)
    month_group = {}
    for row in months:
        key = (row["symbol"], row["variant"], row["overlay"], row["scenario"], row["position_pct"])
        month_group.setdefault(key, []).append(row)
    out = []
    for key, rows in grouped.items():
        by_period = {row["period"]: row for row in rows}
        ref = by_period.get("730d") or by_period.get("365d")
        if not ref:
            continue
        returns = [float(row["return_pct"]) for row in rows]
        dds = [float(row["max_dd_pct"]) for row in rows]
        pfs = [float(row["profit_factor"]) for row in rows]
        mrows = month_group.get(key, [])
        out.append(
            {
                **{k: ref.get(k, "") for k in ["symbol", "variant", "direction", "overlay", "scenario", "position_pct", "fee_pct", "slippage_pct"]},
                "windows_count": len(rows),
                "positive_windows": sum(r > 0 for r in returns),
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
                "positive_months": sum(float(m.get("return_pct") or 0) > 0 for m in mrows),
                "months_count": len(mrows),
                "months_40usd_plus": sum(float(m.get("pnl") or 0) >= 40 for m in mrows),
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "stress",
            int(r["positive_windows"]),
            float(r.get("return_730d_pct") or -999),
            float(r.get("pf_730d") or 0),
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
        "symbol", "variant", "direction", "overlay", "scenario", "position_pct",
        "positive_windows", "windows_count", "return_30d_pct", "return_60d_pct",
        "return_90d_pct", "return_180d_pct", "return_365d_pct", "return_730d_pct",
        "pf_365d", "pf_730d", "dd_365d_pct", "dd_730d_pct", "max_dd_any_pct",
        "positive_months", "months_count", "months_40usd_plus",
    ]
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(v):
    if v in ("", None) or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{float(v):+.2f}"


def save_report(path, summary, windows, months, top_n):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stress_ok = [
        row for row in summary
        if row["scenario"] == "stress"
        and int(row["positive_windows"]) >= 5
        and float(row.get("return_365d_pct") or -999) > 0
        and float(row.get("return_730d_pct") or -999) > 0
        and float(row.get("pf_365d") or 0) >= 1.05
        and float(row.get("pf_730d") or 0) >= 1.02
        and float(row.get("max_dd_any_pct") or 999) <= 40
    ]
    lines = [
        f"# Stage-5 Top-{top_n} Rescue",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        f"- Summary rows: `{len(summary)}`",
        f"- Window rows: `{len(windows)}`",
        f"- Monthly rows: `{len(months)}`",
        f"- Strict stress pass: `{len(stress_ok)}`",
        "",
        "## Strict Stress Pass",
        "",
        "| # | Symbol | Direction | Variant | Pos | Overlay | Win | 365d | 730d | PF365 | PF730 | DD730 | Months + | $40+ |",
        "|---:|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(stress_ok[:80], 1):
        lines.append(
            f"| {i} | `{row['symbol']}` | {row['direction']} | {row['variant']} | {float(row['position_pct']):.0%} | `{row['overlay']}` | "
            f"{row['positive_windows']}/{row['windows_count']} | {fmt(row['return_365d_pct'])}% | {fmt(row['return_730d_pct'])}% | "
            f"{float(row.get('pf_365d') or 0):.2f} | {float(row.get('pf_730d') or 0):.2f} | "
            f"{float(row.get('dd_730d_pct') or 0):.2f}% | {row['positive_months']}/{row['months_count']} | {row['months_40usd_plus']}/{row['months_count']} |"
        )
    lines.extend(["", "## Top Overall", ""])
    lines.extend(lines[9:11])
    for i, row in enumerate(summary[:80], 1):
        lines.append(
            f"| {i} | `{row['symbol']}` | {row['direction']} | {row['variant']} | {float(row['position_pct']):.0%} | `{row['overlay']}` | "
            f"{row['positive_windows']}/{row['windows_count']} | {fmt(row['return_365d_pct'])}% | {fmt(row['return_730d_pct'])}% | "
            f"{float(row.get('pf_365d') or 0):.2f} | {float(row.get('pf_730d') or 0):.2f} | "
            f"{float(row.get('dd_730d_pct') or 0):.2f}% | {row['positive_months']}/{row['months_count']} | {row['months_40usd_plus']}/{row['months_count']} |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    rows = read_rows(os.path.join(ROOT, args.input), args.top_n)
    overlays = overlay_grid()
    scenarios = [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]
    positions = [0.10, 0.15, 0.20, 0.25]
    cache = {}
    windows_out = []
    months_out = []
    for idx, row in enumerate(rows, 1):
        params = params_from_row(row)
        symbol = params["symbol"]
        if symbol not in cache:
            print(f"Loading {symbol}", flush=True)
            path = os.path.join(ROOT, args.raw_1m_dir, f"{symbol}_1m.csv")
            df = add_closed_htf_permissions(add_closed_htf_permissions(add_indicators(read_symbol(path)), 60), 240)
            cache[symbol] = df
        df = cache[symbol]
        base = base_signal(df, params)
        print(f"[{idx}/{len(rows)}] {symbol} {params['variant']} signals={int(base.sum())}", flush=True)
        for overlay in overlays:
            signal = apply_overlay(df, base, params, overlay)
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
                        summary, trades = run_backtest(
                            sub, sub_signal, params, position_pct, fee_pct, slippage_pct,
                            overlay["daily_stop_pct"], overlay["weekly_stop_pct"]
                        )
                        out = {
                            **params,
                            "overlay": overlay["overlay"],
                            "scenario": scenario,
                            "position_pct": position_pct,
                            "fee_pct": fee_pct,
                            "slippage_pct": slippage_pct,
                            "period": f"{days}d",
                            **{k: v for k, v in summary.items() if k != "exit_reasons"},
                            "take_profit": summary["exit_reasons"].get("take_profit", 0),
                            "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                            "time_stop_exit": summary["exit_reasons"].get("time_stop", 0),
                        }
                        windows_out.append(out)
                        if days == 730:
                            for month in monthly_from_trades(trades, position_pct):
                                months_out.append({**out, **month})
    summary = build_summary(windows_out, months_out)
    save_csv(os.path.join(ROOT, args.save_windows), windows_out)
    save_csv(os.path.join(ROOT, args.save_months), months_out)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_report(os.path.join(ROOT, args.save_report), summary, windows_out, months_out, args.top_n)
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
