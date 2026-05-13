#!/usr/bin/env python3
"""Stage-4 validation for the top-50 market strategy candidates.

Takes the broad stage-3 top-50 rows and validates the exact candidate variant
under smaller position sizes, 730d where available, stress costs, and monthly
stability. This is still a research filter, not an execution-ready strategy.
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
INITIAL_BALANCE = 1000.0
WINDOWS = [30, 60, 90, 180, 365, 730]


def parse_args():
    parser = argparse.ArgumentParser(description="Validate stage-3 top-50 candidates.")
    parser.add_argument("--top50", default="data/market_stage4_top50_universe.csv")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default="data/market_stage4_top50_validation_summary.csv")
    parser.add_argument("--save-windows", default="data/market_stage4_top50_validation_windows.csv")
    parser.add_argument("--save-months", default="data/market_stage4_top50_validation_months.csv")
    parser.add_argument("--save-report", default="strategies/market-stage4-top50-validation.md")
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def load_rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


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
    return long_score.to_numpy(), short_score.to_numpy()


def candidate_params(row):
    return {
        "symbol": row["symbol"],
        "variant": row["variant"],
        "direction": row["direction"],
        "threshold": int(float(row["threshold"])),
        "regime": row["regime"],
        "tp": float(row["tp"]),
        "sl": float(row["sl"]),
        "time": int(float(row["time"])),
        "stage2_class": row.get("stage2_class", ""),
        "market_class": row.get("market_class", ""),
    }


def build_signal(df, params):
    long_score, short_score = score_arrays(df, params["regime"])
    if params["direction"] == "long":
        return (
            (long_score >= params["threshold"])
            & (df["close"].to_numpy() <= df["ema20"].to_numpy() * 1.010)
            & (df["upper_wick_ratio"].fillna(1).to_numpy() <= 0.35)
        )
    return short_score >= params["threshold"]


def summarize(trades, equity_curve):
    if not trades:
        return {
            "trades": 0,
            "return_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "expectancy_pct": 0.0,
            "final_equity": INITIAL_BALANCE,
            "exit_reasons": {},
        }
    final = equity_curve[-1]
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
        "return_pct": (final / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (999 if gross_win > 0 else 0),
        "max_dd_pct": max_dd,
        "expectancy_pct": sum(returns) / len(returns),
        "final_equity": final,
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, signal, params, position_pct, fee_pct, slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    equity = INITIAL_BALANCE
    equity_curve = [equity]
    trades = []
    n = len(df)
    i = 250
    while i < n - 2:
        if not signal[i]:
            i += 1
            continue
        entry_idx = i + 1
        raw_entry = open_[entry_idx]
        if params["direction"] == "long":
            entry = raw_entry * (1 + slippage_pct)
        else:
            entry = raw_entry * (1 - slippage_pct)
        notional = equity * position_pct
        exit_idx = min(entry_idx + params["time"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        if params["direction"] == "long":
            tp_price = entry * (1 + params["tp"])
            sl_price = entry * (1 - params["sl"])
            for j in range(entry_idx, exit_idx + 1):
                if low[j] <= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if high[j] >= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            exit_exec = exit_price * (1 - slippage_pct)
            gross = exit_exec / entry - 1
        else:
            tp_price = entry * (1 - params["tp"])
            sl_price = entry * (1 + params["sl"])
            for j in range(entry_idx, exit_idx + 1):
                if high[j] >= sl_price:
                    exit_idx, exit_price, reason = j, sl_price, "stop_loss"
                    break
                if low[j] <= tp_price:
                    exit_idx, exit_price, reason = j, tp_price, "take_profit"
                    break
            exit_exec = exit_price * (1 + slippage_pct)
            gross = entry / exit_exec - 1
        net = gross - 2 * fee_pct
        equity += notional * net
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
    return summarize(trades, equity_curve), trades


def month_key(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m")


def monthly_from_trades(trades, position_pct):
    months = {}
    equity = INITIAL_BALANCE
    for trade in trades:
        key = month_key(trade["exit_time_ms"])
        before = months.setdefault(key, {"month": key, "start_equity": equity, "pnl": 0.0, "trades": 0})
        pnl = equity * position_pct * (trade["net_return_pct"] / 100.0)
        equity += pnl
        before["pnl"] += pnl
        before["trades"] += 1
        before["end_equity"] = equity
    rows = []
    for item in months.values():
        start = item["start_equity"]
        item["return_pct"] = (item.get("end_equity", start) / start - 1) * 100.0 if start else 0.0
        rows.append(item)
    return rows


def validate_candidate(row, args):
    params = candidate_params(row)
    path = os.path.join(ROOT, args.raw_1m_dir, f"{params['symbol']}_1m.csv")
    try:
        df = add_indicators(read_symbol(path))
        signal = build_signal(df, params)
        windows = []
        months = []
        scenarios = [
            ("pos25_base", 0.25, 0.0002, 0.0),
            ("pos35_base", 0.35, 0.0002, 0.0),
            ("pos50_base", 0.50, 0.0002, 0.0),
            ("pos25_stress", 0.25, 0.0004, 0.0002),
            ("pos35_stress", 0.35, 0.0004, 0.0002),
            ("pos50_stress", 0.50, 0.0004, 0.0002),
        ]
        for scenario, position_pct, fee_pct, slippage_pct in scenarios:
            for days in WINDOWS:
                bars = days * 1440
                if len(df) < bars + 300:
                    continue
                sub = df.tail(bars + 300).reset_index(drop=True)
                sub_signal = signal[-(bars + 300) :]
                summary, trades = run_backtest(sub, sub_signal, params, position_pct, fee_pct, slippage_pct)
                windows.append(
                    {
                        **params,
                        "scenario": scenario,
                        "position_pct": position_pct,
                        "fee_pct": fee_pct,
                        "slippage_pct": slippage_pct,
                        "period": f"{days}d",
                        **{k: v for k, v in summary.items() if k != "exit_reasons"},
                        "take_profit": summary["exit_reasons"].get("take_profit", 0),
                        "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                        "time_stop": summary["exit_reasons"].get("time_stop", 0),
                        "status": "ok",
                        "error": "",
                    }
                )
                if days == 730 and scenario == "pos25_base":
                    for item in monthly_from_trades(trades, position_pct):
                        months.append({**params, "scenario": scenario, **item})
        return windows, months
    except Exception as exc:
        return [
            {
                **params,
                "scenario": "",
                "period": "",
                "status": "error",
                "error": str(exc),
            }
        ], []


def build_summary(windows, months):
    grouped = {}
    for row in windows:
        if row.get("status") != "ok":
            continue
        key = (row["symbol"], row["variant"], row["scenario"])
        grouped.setdefault(key, []).append(row)
    month_group = {}
    for row in months:
        key = (row["symbol"], row["variant"], row["scenario"])
        month_group.setdefault(key, []).append(row)
    out = []
    for key, items in grouped.items():
        by_period = {row["period"]: row for row in items}
        ref = by_period.get("730d") or by_period.get("365d")
        if not ref:
            continue
        periods = list(by_period.keys())
        returns = [float(row["return_pct"]) for row in by_period.values()]
        dds = [float(row["max_dd_pct"]) for row in by_period.values()]
        pfs = [float(row["profit_factor"]) for row in by_period.values()]
        mrows = month_group.get(key, [])
        positive_months = sum(float(m.get("return_pct") or 0) > 0 for m in mrows)
        months_4pct = sum(float(m.get("pnl") or 0) >= 40 for m in mrows)
        out.append(
            {
                **{k: ref.get(k, "") for k in ("symbol", "variant", "direction", "stage2_class", "market_class", "scenario", "position_pct", "fee_pct", "slippage_pct")},
                "windows_count": len(periods),
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
                "months_count": len(mrows),
                "positive_months": positive_months,
                "months_40usd_plus": months_4pct,
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "pos25_stress",
            int(r["positive_windows"]),
            float(r.get("min_pf") or 0),
            -float(r.get("max_dd_any_pct") or 999),
            float(r.get("return_730d_pct") or r.get("return_365d_pct") or 0),
        ),
        reverse=True,
    )
    return out


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row.keys()})
    preferred = [
        "symbol",
        "variant",
        "scenario",
        "position_pct",
        "positive_windows",
        "windows_count",
        "return_30d_pct",
        "return_60d_pct",
        "return_90d_pct",
        "return_180d_pct",
        "return_365d_pct",
        "return_730d_pct",
        "pf_365d",
        "pf_730d",
        "dd_365d_pct",
        "dd_730d_pct",
        "max_dd_any_pct",
        "months_count",
        "positive_months",
        "months_40usd_plus",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(v):
    if v in ("", None):
        return "n/a"
    try:
        return f"{float(v):+.2f}"
    except Exception:
        return str(v)


def save_report(path, summary, windows, months):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    candidates = [
        r
        for r in summary
        if r["scenario"].endswith("stress")
        and int(r["positive_windows"]) >= 5
        and float(r.get("pf_365d") or 0) >= 1.05
        and float(r.get("max_dd_any_pct") or 999) <= 40
    ]
    lines = [
        "# Market Stage-4 Top-50 Validation",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Validation of the top-50 stage-3 rows with smaller position sizes, 730d where available, stress costs and monthly stability.",
        "",
        "## Summary",
        "",
        f"- Summary rows: `{len(summary)}`",
        f"- Window rows: `{len(windows)}`",
        f"- Monthly rows: `{len(months)}`",
        f"- Stress candidates with DD <= 40%: `{len(candidates)}`",
        "",
        "## Best Stress Candidates",
        "",
        "| # | Symbol | Variant | Scenario | Pos | Win | 365d | 730d | PF365 | PF730 | DD365 | DD730 | Months + | $40+ months |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(candidates[:60], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | {r['variant']} | {r['scenario']} | {float(r['position_pct']):.0%} | "
            f"{r['positive_windows']}/{r['windows_count']} | {fmt(r.get('return_365d_pct'))}% | {fmt(r.get('return_730d_pct'))}% | "
            f"{float(r.get('pf_365d') or 0):.2f} | {float(r.get('pf_730d') or 0):.2f} | "
            f"{float(r.get('dd_365d_pct') or 0):.2f}% | {float(r.get('dd_730d_pct') or 0):.2f}% | "
            f"{r.get('positive_months')}/{r.get('months_count')} | {r.get('months_40usd_plus')}/{r.get('months_count')} |"
        )
    lines.extend(
        [
            "",
            "## Top Overall",
            "",
            "| # | Symbol | Variant | Scenario | Win | 365d | 730d | PF365 | DD365 | DD730 |",
            "|---:|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for i, r in enumerate(summary[:80], 1):
        lines.append(
            f"| {i} | `{r['symbol']}` | {r['variant']} | {r['scenario']} | {r['positive_windows']}/{r['windows_count']} | "
            f"{fmt(r.get('return_365d_pct'))}% | {fmt(r.get('return_730d_pct'))}% | "
            f"{float(r.get('pf_365d') or 0):.2f} | {float(r.get('dd_365d_pct') or 0):.2f}% | {float(r.get('dd_730d_pct') or 0):.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Human Read",
            "",
            "If this table is empty under stress/DD filters, it means the broad strategy family is too aggressive and needs regime filters or cashflow sizing before being treated as permanent.",
            "",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    rows = load_rows(os.path.join(ROOT, args.top50))
    print(f"Stage-4 validating {len(rows)} top rows with {args.workers} workers", flush=True)
    windows = []
    months = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(validate_candidate, row, args): row["symbol"] for row in rows}
        for i, future in enumerate(as_completed(futures), 1):
            w, m = future.result()
            windows.extend(w)
            months.extend(m)
            if i % 5 == 0 or i == len(rows):
                print(f"[{i}/{len(rows)}] {futures[future]} windows={len(w)} months={len(m)}", flush=True)
    summary = build_summary(windows, months)
    save_csv(os.path.join(ROOT, args.save_windows), windows)
    save_csv(os.path.join(ROOT, args.save_months), months)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_report(os.path.join(ROOT, args.save_report), summary, windows, months)
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved windows: {os.path.join(ROOT, args.save_windows)}")
    print(f"Saved months: {os.path.join(ROOT, args.save_months)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
