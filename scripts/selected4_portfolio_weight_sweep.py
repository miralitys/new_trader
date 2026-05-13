#!/usr/bin/env python3
"""Weight sweep for the selected ALICE/DYDX/REZ/TAO protected portfolio."""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

import overnight_strategy_research as ov
import selected4_protection_deep_test as s4


SYMBOLS = ["ALICEUSDT", "DYDXUSDT", "REZUSDT", "TAOUSDT"]
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
INITIAL_BALANCE = 1000.0


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Sweep selected4 portfolio weights.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--summary", default=f"data/selected4_protection_summary_{today}.csv")
    parser.add_argument("--fee-pct", type=float, default=0.0004)
    parser.add_argument("--slippage-pct", type=float, default=0.0002)
    parser.add_argument("--step", type=int, default=10, help="Weight step in percent.")
    parser.add_argument("--save-windows", default=f"data/selected4_portfolio_weight_sweep_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/selected4_portfolio_weight_sweep_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected4-portfolio-weight-sweep-{today}.md")
    return parser.parse_args()


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "portfolio",
        "period",
        "return_pct",
        "max_dd_pct",
        "positive_windows",
        "score",
        "w_ALICEUSDT",
        "w_DYDXUSDT",
        "w_REZUSDT",
        "w_TAOUSDT",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def selected_variants(summary_path):
    df = pd.read_csv(summary_path)
    df = s4.score_frame(df)
    out = {}
    for symbol, group in df.groupby("symbol"):
        out[symbol] = group.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0]["variant"]
    return out


def load_frames_and_curves(args, variants):
    frames = {}
    curves = {}
    monthly_curves = {}
    for symbol in SYMBOLS:
        print(f"loading {symbol}", flush=True)
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, args.raw_dir, f"{symbol}_1m.csv")))
        frames[symbol] = df
        all_variants = s4.trend_variants(symbol) if symbol in s4.TREND_SYMBOLS else s4.exhaustion_variants(symbol)
        variant = next(v for v in all_variants if v["variant"] == variants[symbol])
        sig = s4.signal_for(df, variant)
        curves[symbol] = {}
        for days in WINDOWS:
            bars = days * 1440
            if len(df) < bars + 300:
                continue
            sub_len = bars + 300
            sub = df.tail(sub_len).reset_index(drop=True)
            sub_sig = sig[-sub_len:]
            _, _, curve = s4.run_backtest(sub, sub_sig, variant, args.fee_pct, args.slippage_pct)
            curves[symbol][f"{days}d"] = curve
        monthly_curves[symbol] = {}
        times = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
        months = times.dt.strftime("%Y-%m")
        for month in sorted(months.unique())[-36:]:
            idx = np.flatnonzero((months == month).to_numpy())
            if len(idx) < 300:
                continue
            start = max(0, idx[0] - 300)
            end = idx[-1] + 1
            sub = df.iloc[start:end].reset_index(drop=True)
            sub_sig = sig[start:end]
            _, _, curve = s4.run_backtest(sub, sub_sig, variant, args.fee_pct, args.slippage_pct)
            monthly_curves[symbol][month] = curve
    return curves, monthly_curves


def combine_curves(curves_by_symbol, weights):
    if not curves_by_symbol:
        return {"return_pct": 0.0, "max_dd_pct": 0.0}
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
    peak = values[0] if values else INITIAL_BALANCE
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return {
        "return_pct": (values[-1] / INITIAL_BALANCE - 1.0) * 100.0 if values else 0.0,
        "max_dd_pct": max_dd,
    }


def weight_grid(step):
    values = range(0, 101, step)
    for a, d, r, t in product(values, values, values, values):
        if a + d + r + t != 100:
            continue
        if a + d == 0 or r + t == 0:
            continue
        yield {
            "ALICEUSDT": a / 100.0,
            "DYDXUSDT": d / 100.0,
            "REZUSDT": r / 100.0,
            "TAOUSDT": t / 100.0,
        }


def portfolio_name(weights):
    return "A{:.0f}_D{:.0f}_R{:.0f}_T{:.0f}".format(
        weights["ALICEUSDT"] * 100,
        weights["DYDXUSDT"] * 100,
        weights["REZUSDT"] * 100,
        weights["TAOUSDT"] * 100,
    )


def score_row(rows, monthly_rows):
    by = {row["period"]: row for row in rows}
    returns = [row["return_pct"] for row in rows]
    positive_windows = sum(value > 0 for value in returns)
    monthly_returns = [row["return_pct"] for row in monthly_rows]
    monthly_positive = sum(value > 0 for value in monthly_returns)
    worst_month = min(monthly_returns) if monthly_returns else 0.0
    return {
        "positive_windows": positive_windows,
        "monthly_positive": monthly_positive,
        "monthly_count": len(monthly_returns),
        "worst_month_pct": worst_month,
        "avg_month_pct": sum(monthly_returns) / len(monthly_returns) if monthly_returns else 0.0,
        "return_30d_pct": by.get("30d", {}).get("return_pct", 0.0),
        "return_60d_pct": by.get("60d", {}).get("return_pct", 0.0),
        "return_90d_pct": by.get("90d", {}).get("return_pct", 0.0),
        "return_180d_pct": by.get("180d", {}).get("return_pct", 0.0),
        "return_365d_pct": by.get("365d", {}).get("return_pct", 0.0),
        "return_730d_pct": by.get("730d", {}).get("return_pct", 0.0),
        "dd_365d_pct": by.get("365d", {}).get("max_dd_pct", 0.0),
        "dd_730d_pct": by.get("730d", {}).get("max_dd_pct", 0.0),
    }


def save_report(path, ranked, monthly_ranked):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Selected 4 Portfolio Weight Sweep",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Execution stress: fee `0.04%` per side + slippage `0.02%` per side.",
        "",
        "## Top Balanced Weights",
        "",
        "| Rank | Weights | 30d | 90d | 365d | 730d | DD365 | DD730 | Months + | Worst Month | Score |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(ranked[:20], 1):
        weights = f"A{row['w_ALICEUSDT']:.0f}/D{row['w_DYDXUSDT']:.0f}/R{row['w_REZUSDT']:.0f}/T{row['w_TAOUSDT']:.0f}"
        lines.append(
            f"| {idx} | `{weights}` | {row['return_30d_pct']:+.2f}% | {row['return_90d_pct']:+.2f}% | "
            f"{row['return_365d_pct']:+.2f}% | {row['return_730d_pct']:+.2f}% | {row['dd_365d_pct']:.2f}% | "
            f"{row['dd_730d_pct']:.2f}% | {row['monthly_positive']}/{row['monthly_count']} | "
            f"{row['worst_month_pct']:+.2f}% | {row['score']:.2f} |"
        )
    lines.extend(["", "## Best Monthly Stability", ""])
    lines.extend([
        "| Rank | Weights | 365d | 730d | DD365 | DD730 | Months + | Worst Month | Avg Month |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for idx, row in enumerate(monthly_ranked[:15], 1):
        weights = f"A{row['w_ALICEUSDT']:.0f}/D{row['w_DYDXUSDT']:.0f}/R{row['w_REZUSDT']:.0f}/T{row['w_TAOUSDT']:.0f}"
        lines.append(
            f"| {idx} | `{weights}` | {row['return_365d_pct']:+.2f}% | {row['return_730d_pct']:+.2f}% | "
            f"{row['dd_365d_pct']:.2f}% | {row['dd_730d_pct']:.2f}% | {row['monthly_positive']}/{row['monthly_count']} | "
            f"{row['worst_month_pct']:+.2f}% | {row['avg_month_pct']:+.2f}% |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    variants = selected_variants(os.path.join(ROOT, args.summary))
    curves, monthly_curves = load_frames_and_curves(args, variants)
    window_rows = []
    monthly_rows = []
    ranked = []
    for weights in weight_grid(args.step):
        name = portfolio_name(weights)
        rows = []
        for period in [f"{d}d" for d in WINDOWS]:
            period_curves = {symbol: curves[symbol][period] for symbol in SYMBOLS if period in curves[symbol]}
            if not period_curves:
                continue
            row = {"portfolio": name, "period": period, **combine_curves(period_curves, weights)}
            row.update({f"w_{symbol}": weight * 100 for symbol, weight in weights.items()})
            rows.append(row)
            window_rows.append(row)
        months = sorted(set.intersection(*(set(monthly_curves[s].keys()) for s in SYMBOLS)))
        mrows = []
        for month in months:
            month_curves = {symbol: monthly_curves[symbol][month] for symbol in SYMBOLS}
            row = {"portfolio": name, "month": month, **combine_curves(month_curves, weights)}
            row.update({f"w_{symbol}": weight * 100 for symbol, weight in weights.items()})
            mrows.append(row)
            monthly_rows.append(row)
        metrics = score_row(rows, mrows)
        score = (
            metrics["positive_windows"] * 100
            + min(metrics["return_365d_pct"], 250) / 2
            + min(metrics["return_730d_pct"], 250) / 3
            + metrics["monthly_positive"] * 5
            + metrics["avg_month_pct"] * 4
            - metrics["dd_365d_pct"] * 4
            - metrics["dd_730d_pct"] * 2
            + metrics["worst_month_pct"] * 3
        )
        ranked.append(
            {
                "portfolio": name,
                **metrics,
                "score": score,
                **{f"w_{symbol}": weight * 100 for symbol, weight in weights.items()},
            }
        )
    ranked.sort(key=lambda row: row["score"], reverse=True)
    monthly_ranked = sorted(
        ranked,
        key=lambda row: (
            row["monthly_positive"],
            row["worst_month_pct"],
            -row["dd_365d_pct"],
            row["return_365d_pct"],
        ),
        reverse=True,
    )
    save_csv(os.path.join(ROOT, args.save_windows), window_rows)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows)
    save_report(os.path.join(ROOT, args.save_report), ranked, monthly_ranked)
    print(f"portfolios={len(ranked)} windows={len(window_rows)} monthly={len(monthly_rows)}")
    print(f"best={ranked[0]['portfolio']} score={ranked[0]['score']:.2f}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
