#!/usr/bin/env python3
"""Realistic maker-limit backtest for selected4 portfolios.

Unlike the previous stress model, this test only enters when the SHORT limit
order is actually touched after the signal. Unfilled orders are skipped.
"""

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

import overnight_strategy_research as ov
import selected4_protection_deep_test as s4


INITIAL_BALANCE = 1000.0
SYMBOLS = ["ALICEUSDT", "DYDXUSDT", "REZUSDT", "TAOUSDT"]
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
PORTFOLIOS = {
    "income_A50_D20_R10_T20": {
        "ALICEUSDT": 0.50,
        "DYDXUSDT": 0.20,
        "REZUSDT": 0.10,
        "TAOUSDT": 0.20,
    },
    "defensive_A30_D20_R20_T30": {
        "ALICEUSDT": 0.30,
        "DYDXUSDT": 0.20,
        "REZUSDT": 0.20,
        "TAOUSDT": 0.30,
    },
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Realistic maker-limit backtest for selected4.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--summary", default=f"data/selected4_protection_summary_{today}.csv")
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--exit-slippage-pct", type=float, default=0.0002)
    parser.add_argument("--offsets", type=float, nargs="+", default=[0.0, 0.0002, 0.0005])
    parser.add_argument("--timeouts", type=int, nargs="+", default=[1, 3])
    parser.add_argument("--save-windows", default=f"data/selected4_maker_realistic_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/selected4_maker_realistic_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected4-maker-realistic-backtest-{today}.md")
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
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "portfolio",
        "symbol",
        "period",
        "month",
        "offset_pct",
        "timeout_min",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "trades",
        "signals",
        "filled",
        "fill_rate_pct",
    ]
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(trades, curve, signals, filled):
    if not trades:
        return {
            "trades": 0,
            "signals": signals,
            "filled": filled,
            "fill_rate_pct": filled / signals * 100.0 if signals else 0.0,
            "return_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "expectancy_pct": 0.0,
            "exit_reasons": {},
        }
    returns = [t["deposit_return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    peak = curve[0][1]
    max_dd = 0.0
    for _, value in curve:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return {
        "trades": len(trades),
        "signals": signals,
        "filled": filled,
        "fill_rate_pct": filled / signals * 100.0 if signals else 0.0,
        "return_pct": (curve[-1][1] / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": gross_win / gross_loss if gross_loss else (999 if gross_win else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_maker_backtest(df, sig, variant, offset_pct, timeout_min, fee_pct, exit_slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    indices = np.flatnonzero(sig)
    ptr = 0
    i = 250
    n = len(df)
    equity = INITIAL_BALANCE
    curve = [(int(times[min(250, n - 1)]), equity)]
    trades = []
    signals = 0
    filled = 0
    while i < n - 2 and equity > 0:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        signal_idx = int(indices[ptr])
        order_start = signal_idx + 1
        if order_start >= n:
            break
        signals += 1
        entry = open_[order_start] * (1.0 + offset_pct)
        last_wait = min(n - 1, order_start + timeout_min - 1)
        entry_idx = None
        for j in range(order_start, last_wait + 1):
            if high[j] >= entry:
                entry_idx = j
                break
        if entry_idx is None:
            i = last_wait + 1
            continue
        filled += 1
        tp = entry * (1.0 - variant["tp"])
        sl = entry * (1.0 + variant["sl"])
        exit_idx = min(entry_idx + variant["time_stop"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        for j in range(entry_idx, exit_idx + 1):
            if high[j] >= sl:
                exit_idx, exit_price, reason = j, sl, "stop_loss"
                break
            if low[j] <= tp:
                exit_idx, exit_price, reason = j, tp, "take_profit"
                break
        exit_exec = exit_price * (1.0 + exit_slippage_pct)
        gross = entry / exit_exec - 1.0
        net = gross - 2.0 * fee_pct
        dep_ret = variant["position_pct"] * net
        equity *= 1.0 + dep_ret
        equity = max(equity, 0.0)
        curve.append((int(times[exit_idx]), equity))
        trades.append({"deposit_return_pct": dep_ret * 100.0, "reason": reason})
        i = exit_idx + 1
    return summarize(trades, curve, signals, filled), curve


def combine_curves(curves_by_symbol, weights):
    all_times = sorted({t for curve in curves_by_symbol.values() for t, _ in curve})
    ptr = {symbol: 0 for symbol in curves_by_symbol}
    values = []
    for t in all_times:
        total = 0.0
        for symbol, curve in curves_by_symbol.items():
            while ptr[symbol] + 1 < len(curve) and curve[ptr[symbol] + 1][0] <= t:
                ptr[symbol] += 1
            total += weights[symbol] * curve[ptr[symbol]][1]
        values.append(total)
    if not values:
        return {"return_pct": 0.0, "max_dd_pct": 0.0}
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return {"return_pct": (values[-1] / INITIAL_BALANCE - 1.0) * 100.0, "max_dd_pct": max_dd}


def load_context(args):
    variants = selected_variants(os.path.join(ROOT, args.summary))
    context = {}
    for symbol in SYMBOLS:
        print(f"loading {symbol}", flush=True)
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")))
        all_variants = s4.trend_variants(symbol) if symbol in s4.TREND_SYMBOLS else s4.exhaustion_variants(symbol)
        variant = next(item for item in all_variants if item["variant"] == variants[symbol])
        sig = s4.signal_for(df, variant)
        context[symbol] = {"df": df, "variant": variant, "signal": sig}
    return context


def save_report(path, windows, monthly):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(windows)
    lines = [
        "# Selected 4 Maker Realistic Backtest",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Only filled maker-limit entries are counted. Unfilled signals are skipped.",
        "",
        "## Portfolio Results",
        "",
        "| Portfolio | Offset | Timeout | 30d | 90d | 365d | 730d | DD365 | DD730 | Fill365 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    view = df[df["portfolio"].notna()].copy()
    for (portfolio, offset_pct, timeout_min), group in view.groupby(["portfolio", "offset_pct", "timeout_min"]):
        by = {row["period"]: row for _, row in group.iterrows()}
        lines.append(
            f"| `{portfolio}` | {offset_pct:.2f}% | {int(timeout_min)} | "
            f"{by.get('30d', {}).get('return_pct', 0):+.2f}% | {by.get('90d', {}).get('return_pct', 0):+.2f}% | "
            f"{by.get('365d', {}).get('return_pct', 0):+.2f}% | {by.get('730d', {}).get('return_pct', 0):+.2f}% | "
            f"{by.get('365d', {}).get('max_dd_pct', 0):.2f}% | {by.get('730d', {}).get('max_dd_pct', 0):.2f}% | "
            f"{by.get('365d', {}).get('fill_rate_pct', 0):.1f}% |"
        )
    lines.extend(["", "## Monthly Check", ""])
    lines.extend([
        "| Portfolio | Offset | Timeout | Months + | Months >= 4% | Worst | Best | Avg |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    mdf = pd.DataFrame(monthly)
    for (portfolio, offset_pct, timeout_min), group in mdf.groupby(["portfolio", "offset_pct", "timeout_min"]):
        ret = group["return_pct"]
        lines.append(
            f"| `{portfolio}` | {offset_pct:.2f}% | {int(timeout_min)} | {(ret > 0).sum()}/{len(ret)} | "
            f"{(ret >= 4.0).sum()}/{len(ret)} | {ret.min():+.2f}% | {ret.max():+.2f}% | {ret.mean():+.2f}% |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    context = load_context(args)
    windows = []
    monthly = []
    for offset_pct in args.offsets:
        for timeout_min in args.timeouts:
            print(f"offset={offset_pct} timeout={timeout_min}", flush=True)
            period_results = {}
            month_results = {}
            for symbol, item in context.items():
                period_results[symbol] = {}
                for days in WINDOWS:
                    bars = days * 1440
                    if len(item["df"]) < bars + 300:
                        continue
                    sub_len = bars + 300
                    sub = item["df"].tail(sub_len).reset_index(drop=True)
                    sig = item["signal"][-sub_len:]
                    sm, curve = run_maker_backtest(sub, sig, item["variant"], offset_pct, timeout_min, args.fee_pct, args.exit_slippage_pct)
                    row = {
                        "symbol": symbol,
                        "period": f"{days}d",
                        "offset_pct": offset_pct * 100,
                        "timeout_min": timeout_min,
                        **{k: val for k, val in sm.items() if k != "exit_reasons"},
                    }
                    row.update({f"exit_{k}": v for k, v in sm["exit_reasons"].items()})
                    windows.append(row)
                    period_results[symbol][f"{days}d"] = {"summary": sm, "curve": curve}
                month_results[symbol] = {}
                df = item["df"]
                sig_all = item["signal"]
                times = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
                month_keys = times.dt.strftime("%Y-%m")
                for month in sorted(month_keys.unique())[-36:]:
                    idx = np.flatnonzero((month_keys == month).to_numpy())
                    if len(idx) < 300:
                        continue
                    start = max(0, idx[0] - 300)
                    end = idx[-1] + 1
                    sub = df.iloc[start:end].reset_index(drop=True)
                    sig = sig_all[start:end]
                    sm, curve = run_maker_backtest(sub, sig, item["variant"], offset_pct, timeout_min, args.fee_pct, args.exit_slippage_pct)
                    month_results[symbol][month] = {"summary": sm, "curve": curve}
            for portfolio, weights in PORTFOLIOS.items():
                for days in WINDOWS:
                    period = f"{days}d"
                    curves = {symbol: period_results[symbol][period]["curve"] for symbol in SYMBOLS if period in period_results[symbol]}
                    if len(curves) != len(SYMBOLS):
                        continue
                    sm = combine_curves(curves, weights)
                    signals = sum(period_results[symbol][period]["summary"]["signals"] for symbol in SYMBOLS)
                    filled = sum(period_results[symbol][period]["summary"]["filled"] for symbol in SYMBOLS)
                    windows.append(
                        {
                            "portfolio": portfolio,
                            "period": period,
                            "offset_pct": offset_pct * 100,
                            "timeout_min": timeout_min,
                            **sm,
                            "signals": signals,
                            "filled": filled,
                            "fill_rate_pct": filled / signals * 100.0 if signals else 0.0,
                        }
                    )
                months = sorted(set.intersection(*(set(month_results[symbol].keys()) for symbol in SYMBOLS)))
                for month in months:
                    curves = {symbol: month_results[symbol][month]["curve"] for symbol in SYMBOLS}
                    sm = combine_curves(curves, weights)
                    signals = sum(month_results[symbol][month]["summary"]["signals"] for symbol in SYMBOLS)
                    filled = sum(month_results[symbol][month]["summary"]["filled"] for symbol in SYMBOLS)
                    monthly.append(
                        {
                            "portfolio": portfolio,
                            "month": month,
                            "offset_pct": offset_pct * 100,
                            "timeout_min": timeout_min,
                            **sm,
                            "signals": signals,
                            "filled": filled,
                            "fill_rate_pct": filled / signals * 100.0 if signals else 0.0,
                        }
                    )
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly)
    save_report(os.path.join(ROOT, args.save_report), windows, monthly)
    print(f"windows={len(windows)} monthly={len(monthly)}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
