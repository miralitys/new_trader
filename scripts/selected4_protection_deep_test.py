#!/usr/bin/env python3
"""Deep protection test for the four selected candidates.

Candidates:
- ALICEUSDT, DYDXUSDT: aggressive trend-pullback SHORT.
- REZUSDT, TAOUSDT: calmer exhaustion-reversal SHORT.

The script keeps the same strategy families from selected7_strategy_tune, then
adds risk controls and position sweeps:
- daily loss stop;
- weekly loss stop;
- stricter 24h/7d movement guards;
- position_pct sweep;
- portfolio sleeve checks.
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


INITIAL_BALANCE = 1000.0
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
TREND_SYMBOLS = ["ALICEUSDT", "DYDXUSDT"]
EXHAUSTION_SYMBOLS = ["REZUSDT", "TAOUSDT"]
SYMBOLS = TREND_SYMBOLS + EXHAUSTION_SYMBOLS


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Deep protection test for ALICE/DYDX/REZ/TAO.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--fee-pct", type=float, default=0.0004)
    parser.add_argument("--slippage-pct", type=float, default=0.0002)
    parser.add_argument("--save-windows", default=f"data/selected4_protection_windows_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/selected4_protection_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/selected4_protection_monthly_{today}.csv")
    parser.add_argument("--save-portfolio", default=f"data/selected4_protection_portfolio_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected4-protection-deep-test-{today}.md")
    return parser.parse_args()


def trend_variants(symbol):
    rows = []
    rsi_bands = [(42, 58), (48, 52), (48, 58)]
    ret24_limits = [0.10, 0.15, 0.22]
    ret7_limits = [0.30, 0.45]
    exits = [
        (0.005, 0.025, 180),
        (0.005, 0.030, 180),
        (0.008, 0.020, 240),
        (0.008, 0.030, 180),
        (0.010, 0.035, 240),
    ]
    protections = [
        (None, None),
        (3.0, 8.0),
        (5.0, 12.0),
        (8.0, 18.0),
    ]
    for (rsi_min, rsi_max), ret24_abs, ret7_abs, (tp, sl, time_stop), position_pct, (daily_stop, weekly_stop) in product(
        rsi_bands,
        ret24_limits,
        ret7_limits,
        exits,
        [0.25, 0.50, 0.75, 1.0],
        protections,
    ):
        rows.append(
            {
                "symbol": symbol,
                "family": "trend_pullback_short_protected",
                "direction": "short",
                "variant": (
                    f"trendP_rsi{rsi_min}-{rsi_max}_r24{ret24_abs:g}_r7{ret7_abs:g}"
                    f"_d{daily_stop or 0:g}_w{weekly_stop or 0:g}"
                    f"_tp{tp:g}_sl{sl:g}_t{time_stop}_pos{position_pct:g}"
                ),
                "rsi_min": rsi_min,
                "rsi_max": rsi_max,
                "ret24_abs_limit": ret24_abs,
                "ret7_abs_limit": ret7_abs,
                "tp": tp,
                "sl": sl,
                "time_stop": time_stop,
                "position_pct": position_pct,
                "daily_stop_pct": daily_stop,
                "weekly_stop_pct": weekly_stop,
                "volume_mult": "",
                "ret_limit": "",
            }
        )
    return rows


def exhaustion_variants(symbol):
    rows = []
    exits = [
        (0.004, 0.018, 90),
        (0.006, 0.025, 90),
        (0.006, 0.025, 150),
        (0.008, 0.025, 90),
        (0.008, 0.030, 150),
    ]
    protections = [(None, None), (2.0, 5.0), (3.0, 8.0)]
    for ret_limit, rsi_min, volume_mult, (tp, sl, time_stop), position_pct, (daily_stop, weekly_stop) in product(
        [0.06, 0.08, 0.10],
        [64, 68, 72],
        [1.0, 1.2],
        exits,
        [0.25, 0.35, 0.50, 0.75, 1.0],
        protections,
    ):
        rows.append(
            {
                "symbol": symbol,
                "family": "exhaustion_reversal_short_protected",
                "direction": "short",
                "variant": (
                    f"exhP_ret{ret_limit:g}_rsi{rsi_min}_vol{volume_mult:g}"
                    f"_d{daily_stop or 0:g}_w{weekly_stop or 0:g}"
                    f"_tp{tp:g}_sl{sl:g}_t{time_stop}_pos{position_pct:g}"
                ),
                "ret_limit": ret_limit,
                "rsi_min": rsi_min,
                "rsi_max": "",
                "volume_mult": volume_mult,
                "tp": tp,
                "sl": sl,
                "time_stop": time_stop,
                "position_pct": position_pct,
                "ret24_abs_limit": 0.35,
                "ret7_abs_limit": 0.65,
                "daily_stop_pct": daily_stop,
                "weekly_stop_pct": weekly_stop,
            }
        )
    return rows


def signal_for(df, v):
    if v["family"] == "trend_pullback_short_protected":
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
    elif v["family"] == "exhaustion_reversal_short_protected":
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
    else:
        raise ValueError(v["family"])
    return sig.fillna(False).to_numpy()


def date_key(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def week_key(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def summarize(trades, curve):
    if not trades:
        return {
            "trades": 0,
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
        "return_pct": (curve[-1][1] / INITIAL_BALANCE - 1.0) * 100.0,
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
    times = df["open_time_ms"].to_numpy()
    equity = INITIAL_BALANCE
    curve = [(int(times[min(250, len(times) - 1)]), equity)]
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
        dk = date_key(t)
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
        exit_time = int(times[exit_idx])
        curve.append((exit_time, equity))
        trades.append(
            {
                "entry_time_ms": int(times[entry_idx]),
                "exit_time_ms": exit_time,
                "deposit_return_pct": dep_ret * 100.0,
                "reason": reason,
            }
        )
        i = exit_idx + 1
    return summarize(trades, curve), trades, curve


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "symbol",
        "family",
        "variant",
        "period",
        "position_pct",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "trades",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["symbol"], row["family"], row["variant"])].append(row)
    out = []
    for _, items in grouped.items():
        by = {r["period"]: r for r in items}
        returns = [float(r["return_pct"]) for r in items]
        dds = [float(r["max_dd_pct"]) for r in items]
        pfs = [float(r["profit_factor"]) for r in items if int(r["trades"]) > 0]
        ref = items[0]
        out.append(
            {
                "symbol": ref["symbol"],
                "family": ref["family"],
                "variant": ref["variant"],
                "position_pct": ref["position_pct"],
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
                "trades_365d": by.get("365d", {}).get("trades", ""),
                "trades_730d": by.get("730d", {}).get("trades", ""),
            }
        )
    out.sort(
        key=lambda r: (
            int(r["positive_windows"]),
            float(r["return_365d_pct"] or -999),
            float(r["return_730d_pct"] or -999),
            -float(r["dd_365d_pct"] or 999),
        ),
        reverse=True,
    )
    return out


def score_frame(summary_df):
    g = summary_df.copy()
    g["score"] = (
        g["positive_windows"].astype(float) * 120
        + g["return_365d_pct"].fillna(0).clip(upper=250) / 4
        + g["return_730d_pct"].fillna(0).clip(upper=250) / 5
        + g["pf_365d"].fillna(0) * 7
        - g["dd_365d_pct"].fillna(99) * 1.6
        - g["max_dd_any_pct"].fillna(99) * 0.7
    )
    return g


def monthly_rows(df, sig, v, args):
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
        sm, _, _ = run_backtest(sub, sub_sig, v, args.fee_pct, args.slippage_pct)
        rows.append({**v, "month": month, **{k: val for k, val in sm.items() if k != "exit_reasons"}})
    return rows


def run_windows_for_variant(df, sig, v, args):
    rows = []
    for days in WINDOWS:
        bars = days * 1440
        if len(df) < bars + 300:
            continue
        sub_len = bars + 300
        sub = df.tail(sub_len).reset_index(drop=True)
        sub_sig = sig[-sub_len:]
        sm, _, _ = run_backtest(sub, sub_sig, v, args.fee_pct, args.slippage_pct)
        rows.append(
            {
                **v,
                "period": f"{days}d",
                **{k: val for k, val in sm.items() if k != "exit_reasons"},
                "take_profit": sm["exit_reasons"].get("take_profit", 0),
                "stop_loss": sm["exit_reasons"].get("stop_loss", 0),
                "time_stop_exit": sm["exit_reasons"].get("time_stop", 0),
            }
        )
    return rows


def portfolio_summary(curves_by_symbol):
    if not curves_by_symbol:
        return {"return_pct": 0.0, "max_dd_pct": 0.0}
    weights = {symbol: 1.0 / len(curves_by_symbol) for symbol in curves_by_symbol}
    all_times = sorted({t for curve in curves_by_symbol.values() for t, _ in curve})
    current = {symbol: INITIAL_BALANCE for symbol in curves_by_symbol}
    ptr = {symbol: 0 for symbol in curves_by_symbol}
    values = []
    for t in all_times:
        total = 0.0
        for symbol, curve in curves_by_symbol.items():
            while ptr[symbol] + 1 < len(curve) and curve[ptr[symbol] + 1][0] <= t:
                ptr[symbol] += 1
            current[symbol] = curve[ptr[symbol]][1]
            total += weights[symbol] * current[symbol]
        values.append(total)
    peak = values[0] if values else INITIAL_BALANCE
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return {"return_pct": (values[-1] / INITIAL_BALANCE - 1.0) * 100.0 if values else 0.0, "max_dd_pct": max_dd}


def fmt(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):+.2f}%"


def num(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):.2f}"


def save_report(path, best_rows, monthly, portfolio_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Selected 4 Protection Deep Test",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Execution stress: fee `0.04%` per side + slippage `0.02%` per side.",
        "",
        "## Best By Symbol",
        "",
        "| Symbol | Family | Variant | Win | 1d | 7d | 30d | 90d | 365d | 730d | PF365 | DD365 | Trades365 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in best_rows:
        lines.append(
            f"| `{r['symbol']}` | {r['family']} | `{r['variant']}` | {int(r['positive_windows'])}/{int(r['windows_count'])} | "
            f"{fmt(r['return_1d_pct'])} | {fmt(r['return_7d_pct'])} | {fmt(r['return_30d_pct'])} | {fmt(r['return_90d_pct'])} | "
            f"{fmt(r['return_365d_pct'])} | {fmt(r['return_730d_pct'])} | {num(r['pf_365d'])} | {num(r['dd_365d_pct'])}% | {r['trades_365d']} |"
        )
    if monthly:
        df = pd.DataFrame(monthly)
        lines.extend(["", "## Monthly Check", ""])
        lines.extend(["| Symbol | Months + | Months - | Worst | Best | Avg |", "|---|---:|---:|---:|---:|---:|"])
        for symbol, group in df.groupby("symbol"):
            ret = group["return_pct"]
            lines.append(f"| `{symbol}` | {(ret > 0).sum()}/{len(ret)} | {(ret < 0).sum()}/{len(ret)} | {ret.min():+.2f}% | {ret.max():+.2f}% | {ret.mean():+.2f}% |")
    if portfolio_rows:
        lines.extend(["", "## Portfolio Sleeves", ""])
        lines.extend(["| Portfolio | Period | Return | MaxDD |", "|---|---:|---:|---:|"])
        for row in portfolio_rows:
            lines.append(f"| `{row['portfolio']}` | {row['period']} | {row['return_pct']:+.2f}% | {row['max_dd_pct']:.2f}% |")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    windows = []
    signals = {}
    frames = {}
    variants_by_symbol = {}
    for symbol in SYMBOLS:
        print(f"loading {symbol}", flush=True)
        path = os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")
        df = ov.prepare(ov.read_symbol(path))
        frames[symbol] = df
        variants = trend_variants(symbol) if symbol in TREND_SYMBOLS else exhaustion_variants(symbol)
        variants_by_symbol[symbol] = variants
        for idx, v in enumerate(variants, 1):
            sig = signal_for(df, v)
            if int(sig.sum()) < 10:
                continue
            signals[(symbol, v["variant"])] = sig
            windows.extend(run_windows_for_variant(df, sig, v, args))
            if idx % 250 == 0:
                print(f"{symbol} {idx}/{len(variants)} rows={len(windows)}", flush=True)
        save_csv(os.path.join(ROOT, args.save_windows), windows)
    summary = aggregate(windows)
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_summary), summary)

    summary_df = score_frame(pd.DataFrame(summary))
    best_rows = []
    monthly = []
    selected = {}
    for symbol, group in summary_df.groupby("symbol"):
        best = group.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0].to_dict()
        best_rows.append(best)
        selected[symbol] = best
        v = next(item for item in variants_by_symbol[symbol] if item["variant"] == best["variant"])
        sig = signals[(symbol, best["variant"])]
        monthly.extend(monthly_rows(frames[symbol], sig, v, args))
    best_rows = sorted(best_rows, key=lambda r: float(r.get("return_365d_pct") or -999), reverse=True)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly)

    portfolio_rows = []
    portfolios = {
        "aggressive_ALICE_DYDX": ["ALICEUSDT", "DYDXUSDT"],
        "calm_REZ_TAO": ["REZUSDT", "TAOUSDT"],
        "all4_equal": ["ALICEUSDT", "DYDXUSDT", "REZUSDT", "TAOUSDT"],
    }
    for pname, symbols in portfolios.items():
        for days in WINDOWS:
            curves = {}
            for symbol in symbols:
                if symbol not in selected:
                    continue
                v = next(item for item in variants_by_symbol[symbol] if item["variant"] == selected[symbol]["variant"])
                df = frames[symbol]
                bars = days * 1440
                if len(df) < bars + 300:
                    continue
                sub_len = bars + 300
                sub = df.tail(sub_len).reset_index(drop=True)
                sig = signals[(symbol, selected[symbol]["variant"])][-sub_len:]
                _, _, curve = run_backtest(sub, sig, v, args.fee_pct, args.slippage_pct)
                curves[symbol] = curve
            if curves:
                portfolio_rows.append({"portfolio": pname, "period": f"{days}d", **portfolio_summary(curves)})
    save_csv(os.path.join(ROOT, args.save_portfolio), portfolio_rows)
    save_report(os.path.join(ROOT, args.save_report), best_rows, monthly, portfolio_rows)
    print(f"windows={len(windows)} summary={len(summary)} monthly={len(monthly)} portfolio={len(portfolio_rows)}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
