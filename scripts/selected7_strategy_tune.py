#!/usr/bin/env python3
"""Tune the seven candidates from the overnight shortlist.

Symbols:
- NFP, REZ, TAO, SANTOS: exhaustion_reversal SHORT.
- CELO, ALICE, DYDX: trend_pullback SHORT.

The goal is to improve the first overnight candidates without mixing them with
old GALA logic.
"""

import argparse
import csv
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

import overnight_strategy_research as ov


WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
EXHAUSTION_SYMBOLS = ["NFPUSDT", "REZUSDT", "TAOUSDT", "SANTOSUSDT"]
TREND_SYMBOLS = ["CELOUSDT", "ALICEUSDT", "DYDXUSDT"]


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Tune selected seven overnight candidates.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-windows", default=f"data/selected7_strategy_tune_windows_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/selected7_strategy_tune_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/selected7_strategy_tune_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected7-strategy-tune-{today}.md")
    return parser.parse_args()


def exhaustion_variants(symbol):
    rows = []
    for ret_limit, tp, sl, time_stop, position_pct, rsi_min, volume_mult in product(
        [0.04, 0.05, 0.06, 0.08, 0.10],
        [0.004, 0.006, 0.008],
        [0.018, 0.025, 0.030],
        [90, 150, 240],
        [0.25, 0.50, 0.75, 1.0],
        [64, 68, 72],
        [1.0, 1.2],
    ):
        rows.append(
            {
                "symbol": symbol,
                "family": "exhaustion_reversal_tuned",
                "direction": "short",
                "variant": (
                    f"exh_short_ret{ret_limit:g}_rsi{rsi_min}_vol{volume_mult:g}"
                    f"_tp{tp:g}_sl{sl:g}_t{time_stop}_pos{position_pct:g}"
                ),
                "ret_limit": ret_limit,
                "rsi_min": rsi_min,
                "volume_mult": volume_mult,
                "tp": tp,
                "sl": sl,
                "time_stop": time_stop,
                "position_pct": position_pct,
                "ret24_abs_limit": 0.35,
                "ret7_abs_limit": 0.65,
                "daily_stop_pct": None,
                "weekly_stop_pct": None,
            }
        )
    return rows


def trend_variants(symbol):
    rows = []
    for rsi_min, rsi_max, tp, sl, time_stop, position_pct, ret24_abs, daily_stop, weekly_stop in product(
        [38, 42, 48],
        [52, 58, 62],
        [0.005, 0.008, 0.010],
        [0.020, 0.030, 0.035],
        [120, 180, 240],
        [0.25, 0.50, 0.75, 1.0],
        [0.12, 0.18, 0.25],
        [None, 10.0],
        [None, 20.0],
    ):
        if rsi_min >= rsi_max:
            continue
        rows.append(
            {
                "symbol": symbol,
                "family": "trend_pullback_short_tuned",
                "direction": "short",
                "variant": (
                    f"trend_short_rsi{rsi_min}-{rsi_max}_r24{ret24_abs:g}_d{daily_stop or 0:g}"
                    f"_w{weekly_stop or 0:g}_tp{tp:g}_sl{sl:g}_t{time_stop}_pos{position_pct:g}"
                ),
                "rsi_min": rsi_min,
                "rsi_max": rsi_max,
                "tp": tp,
                "sl": sl,
                "time_stop": time_stop,
                "position_pct": position_pct,
                "ret24_abs_limit": ret24_abs,
                "ret7_abs_limit": 0.45,
                "daily_stop_pct": daily_stop,
                "weekly_stop_pct": weekly_stop,
            }
        )
    return rows


def signal_for(df, v):
    if v["family"] == "exhaustion_reversal_tuned":
        sig = (
            (df["ret_24h"] >= v["ret_limit"])
            & (df["rsi14"] > v["rsi_min"])
            & (df["upper_wick_ratio"] > 0.30)
            & df["red"]
            & (df["volume"] > df["vol_sma20"] * v["volume_mult"])
            & df["atr_pct"].between(0.0025, 0.035)
            & (df["ret_24h"].abs() <= v["ret24_abs_limit"])
            & (df["ret_7d"].fillna(0).abs() <= v["ret7_abs_limit"])
        )
    elif v["family"] == "trend_pullback_short_tuned":
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
            & (df["ret_24h"].fillna(0).abs() <= v["ret24_abs_limit"])
            & (df["ret_7d"].fillna(0).abs() <= v["ret7_abs_limit"])
        )
    else:
        raise ValueError(v["family"])
    return sig.fillna(False).to_numpy()


def day_key(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def week_key(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


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
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "return_pct": (curve[-1] / 1000.0 - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, sig, v, fee_pct=0.0004, slippage_pct=0.0002):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    equity = 1000.0
    curve = [equity]
    trades = []
    indices = np.flatnonzero(sig)
    ptr = 0
    i = 250
    n = len(df)
    current_day = None
    current_week = None
    day_start = equity
    week_start = equity
    while i < n - 2 and equity > 0:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        i = int(indices[ptr])
        t = int(times[i])
        dk = day_key(t)
        wk = week_key(t)
        if dk != current_day:
            current_day = dk
            day_start = equity
        if wk != current_week:
            current_week = wk
            week_start = equity
        if v.get("daily_stop_pct") is not None and day_start and (equity / day_start - 1.0) * 100.0 <= -v["daily_stop_pct"]:
            i += 1
            continue
        if v.get("weekly_stop_pct") is not None and week_start and (equity / week_start - 1.0) * 100.0 <= -v["weekly_stop_pct"]:
            i += 1
            continue
        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = open_[entry_idx] * (1.0 - slippage_pct)
        tp = entry * (1.0 - v["tp"])
        sl = entry * (1.0 + v["sl"])
        exit_idx = min(entry_idx + v["time_stop"], n - 1)
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
        dep_ret = v["position_pct"] * net
        equity *= 1.0 + dep_ret
        equity = max(equity, 0.0)
        curve.append(equity)
        trades.append({"deposit_return_pct": dep_ret * 100.0, "reason": reason})
        i = exit_idx + 1
    return summarize(trades, curve)


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "symbol", "family", "direction", "variant", "period", "position_pct", "return_pct",
        "max_dd_pct", "profit_factor", "win_rate_pct", "expectancy_pct", "trades",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["symbol"], row["family"], row["direction"], row["variant"])].append(row)
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
                "position_pct": ref["position_pct"],
            }
        )
    out.sort(
        key=lambda r: (
            int(r["positive_windows"]),
            float(r.get("return_365d_pct") or -999),
            float(r.get("return_730d_pct") or -999),
            -float(r.get("max_dd_any_pct") or 999),
        ),
        reverse=True,
    )
    return out


def monthly(df, sig, v):
    rows = []
    times = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    month_keys = times.dt.strftime("%Y-%m")
    for month in sorted(month_keys.unique())[-36:]:
        idx = np.flatnonzero((month_keys == month).to_numpy())
        if len(idx) < 300:
            continue
        start = max(0, idx[0] - 300)
        end = idx[-1] + 1
        sub = df.iloc[start:end].reset_index(drop=True)
        sub_sig = sig[start:end]
        sm = run_backtest(sub, sub_sig, v)
        rows.append({"month": month, **{k: val for k, val in sm.items() if k != "exit_reasons"}})
    return rows


def fmt(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):+.2f}%"


def num(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def save_report(path, summary, monthly_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    best_by_symbol = []
    for symbol, group in pd.DataFrame(summary).groupby("symbol"):
        g = group.copy()
        g["score"] = (
            g["positive_windows"] * 100
            + g["return_365d_pct"].fillna(0).clip(upper=300) / 5
            + g["pf_365d"].fillna(0) * 5
            - g["dd_365d_pct"].fillna(99)
        )
        best_by_symbol.append(g.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0].to_dict())
    best_by_symbol = sorted(best_by_symbol, key=lambda r: r["return_365d_pct"], reverse=True)
    lines = [
        "# Selected 7 Strategy Tune",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Stress execution: fee `0.04%` per side + slippage `0.02%` per side.",
        "",
        "## Best By Symbol",
        "",
        "| Symbol | Family | Variant | Win | 1d | 7d | 30d | 365d | 730d | PF365 | DD365 | Trades365 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in best_by_symbol:
        lines.append(
            f"| `{r['symbol']}` | {r['family']} | `{r['variant']}` | {int(r['positive_windows'])}/{int(r['windows_count'])} | "
            f"{fmt(r['return_1d_pct'])} | {fmt(r['return_7d_pct'])} | {fmt(r['return_30d_pct'])} | "
            f"{fmt(r['return_365d_pct'])} | {fmt(r['return_730d_pct'])} | {num(r['pf_365d'])} | "
            f"{num(r['dd_365d_pct'])}% | {r['trades_365d']} |"
        )
    if monthly_rows:
        df = pd.DataFrame(monthly_rows)
        lines.extend(["", "## Monthly Check For Selected Best", ""])
        lines.extend(["| Symbol | Variant | Months + | Months - | Worst | Best | Avg |", "|---|---|---:|---:|---:|---:|---:|"])
        for (symbol, variant), group in df.groupby(["symbol", "variant"]):
            ret = group["return_pct"]
            lines.append(
                f"| `{symbol}` | `{variant}` | {(ret > 0).sum()}/{len(ret)} | {(ret < 0).sum()}/{len(ret)} | "
                f"{ret.min():+.2f}% | {ret.max():+.2f}% | {ret.mean():+.2f}% |"
            )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    windows = []
    selected_monthly = []
    symbols = EXHAUSTION_SYMBOLS + TREND_SYMBOLS
    for symbol in symbols:
        print(f"loading {symbol}", flush=True)
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")))
        variants = exhaustion_variants(symbol) if symbol in EXHAUSTION_SYMBOLS else trend_variants(symbol)
        for idx, v in enumerate(variants, 1):
            sig = signal_for(df, v)
            if int(sig.sum()) < 15:
                continue
            for days in WINDOWS:
                bars = days * 1440
                if len(df) < bars + 300:
                    continue
                sub_len = bars + 300
                sub = df.tail(sub_len).reset_index(drop=True)
                sub_sig = sig[-sub_len:]
                sm = run_backtest(sub, sub_sig, v)
                windows.append(
                    {
                        **v,
                        "period": f"{days}d",
                        **{k: val for k, val in sm.items() if k != "exit_reasons"},
                        "take_profit": sm["exit_reasons"].get("take_profit", 0),
                        "stop_loss": sm["exit_reasons"].get("stop_loss", 0),
                        "time_stop_exit": sm["exit_reasons"].get("time_stop", 0),
                    }
                )
            if idx % 250 == 0:
                print(f"{symbol} {idx}/{len(variants)} rows={len(windows)}", flush=True)
        save_csv(os.path.join(ROOT, args.save_windows), windows)
    summary = aggregate(windows)
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_summary), summary)

    # Monthly only for best per symbol.
    summary_df = pd.DataFrame(summary)
    for symbol, group in summary_df.groupby("symbol"):
        g = group.copy()
        g["score"] = (
            g["positive_windows"] * 100
            + g["return_365d_pct"].fillna(0).clip(upper=300) / 5
            + g["pf_365d"].fillna(0) * 5
            - g["dd_365d_pct"].fillna(99)
        )
        best = g.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0]
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")))
        variants = exhaustion_variants(symbol) if symbol in EXHAUSTION_SYMBOLS else trend_variants(symbol)
        v = next(item for item in variants if item["variant"] == best["variant"])
        sig = signal_for(df, v)
        for row in monthly(df, sig, v):
            selected_monthly.append({**v, **row})
    save_csv(os.path.join(ROOT, args.save_monthly), selected_monthly)
    save_report(os.path.join(ROOT, args.save_report), summary, selected_monthly)
    print(f"windows={len(windows)} summary={len(summary)} monthly={len(selected_monthly)}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
