#!/usr/bin/env python3
"""Final validation for the two selected ALICE/DYDX/REZ/TAO portfolios."""

import argparse
import csv
import os
import sys
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
    "selected4_income_A50_D20_R10_T20": {
        "ALICEUSDT": 0.50,
        "DYDXUSDT": 0.20,
        "REZUSDT": 0.10,
        "TAOUSDT": 0.20,
    },
    "selected4_defensive_A30_D20_R20_T30": {
        "ALICEUSDT": 0.30,
        "DYDXUSDT": 0.20,
        "REZUSDT": 0.20,
        "TAOUSDT": 0.30,
    },
}
SCENARIOS = {
    "base_maker": (0.0002, 0.0),
    "stress": (0.0004, 0.0002),
    "harsh": (0.0005, 0.0005),
    "taker_like": (0.0006, 0.0005),
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Validate final selected4 portfolios.")
    parser.add_argument("--raw-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--summary", default=f"data/selected4_protection_summary_{today}.csv")
    parser.add_argument("--save-windows", default=f"data/selected4_portfolio_final_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/selected4_portfolio_final_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/selected4-portfolio-final-validation-{today}.md")
    return parser.parse_args()


def selected_variants(summary_path):
    df = pd.read_csv(summary_path)
    df = s4.score_frame(df)
    variants = {}
    for symbol, group in df.groupby("symbol"):
        variants[symbol] = group.sort_values(["score", "return_365d_pct"], ascending=False).iloc[0]["variant"]
    return variants


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "portfolio",
        "scenario",
        "period",
        "month",
        "return_pct",
        "cash_pnl",
        "hit_4pct",
        "positive",
        "max_dd_pct",
    ]
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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
        return {"return_pct": 0.0, "max_dd_pct": 0.0, "cash_pnl": 0.0}
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return {
        "return_pct": (values[-1] / INITIAL_BALANCE - 1.0) * 100.0,
        "max_dd_pct": max_dd,
        "cash_pnl": values[-1] - INITIAL_BALANCE,
    }


def load_strategy_context(raw_dir, summary_path):
    variants = selected_variants(summary_path)
    context = {}
    for symbol in SYMBOLS:
        print(f"loading {symbol}", flush=True)
        df = ov.prepare(ov.read_symbol(os.path.join(ROOT, raw_dir, f"{symbol}_1m.csv")))
        all_variants = s4.trend_variants(symbol) if symbol in s4.TREND_SYMBOLS else s4.exhaustion_variants(symbol)
        variant = next(item for item in all_variants if item["variant"] == variants[symbol])
        sig = s4.signal_for(df, variant)
        context[symbol] = {"df": df, "variant": variant, "signal": sig}
    return context


def curve_for_period(item, days, fee_pct, slippage_pct):
    df = item["df"]
    bars = days * 1440
    if len(df) < bars + 300:
        return None
    sub_len = bars + 300
    sub = df.tail(sub_len).reset_index(drop=True)
    sig = item["signal"][-sub_len:]
    _, _, curve = s4.run_backtest(sub, sig, item["variant"], fee_pct, slippage_pct)
    return curve


def monthly_curves(item, fee_pct, slippage_pct):
    df = item["df"]
    sig = item["signal"]
    rows = {}
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
        _, _, curve = s4.run_backtest(sub, sub_sig, item["variant"], fee_pct, slippage_pct)
        rows[month] = curve
    return rows


def fmt(value):
    return f"{float(value):+.2f}%"


def save_report(path, windows, monthly):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Selected 4 Portfolio Final Validation",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Portfolios:",
        "",
        "- `selected4_income_A50_D20_R10_T20`: ALICE 50%, DYDX 20%, REZ 10%, TAO 20%.",
        "- `selected4_defensive_A30_D20_R20_T30`: ALICE 30%, DYDX 20%, REZ 20%, TAO 30%.",
        "",
        "## Window Results",
        "",
        "| Portfolio | Scenario | 30d | 90d | 365d | 730d | DD365 | DD730 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    wdf = pd.DataFrame(windows)
    for (portfolio, scenario), group in wdf.groupby(["portfolio", "scenario"]):
        by = {row["period"]: row for _, row in group.iterrows()}
        lines.append(
            f"| `{portfolio}` | `{scenario}` | {fmt(by.get('30d', {}).get('return_pct', 0))} | "
            f"{fmt(by.get('90d', {}).get('return_pct', 0))} | {fmt(by.get('365d', {}).get('return_pct', 0))} | "
            f"{fmt(by.get('730d', {}).get('return_pct', 0))} | {by.get('365d', {}).get('max_dd_pct', 0):.2f}% | "
            f"{by.get('730d', {}).get('max_dd_pct', 0):.2f}% |"
        )
    lines.extend(["", "## Monthly Check", ""])
    lines.extend([
        "| Portfolio | Scenario | Months + | Months >= 4% | Worst | Best | Avg |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    mdf = pd.DataFrame(monthly)
    for (portfolio, scenario), group in mdf.groupby(["portfolio", "scenario"]):
        ret = group["return_pct"]
        lines.append(
            f"| `{portfolio}` | `{scenario}` | {(ret > 0).sum()}/{len(ret)} | {(ret >= 4.0).sum()}/{len(ret)} | "
            f"{ret.min():+.2f}% | {ret.max():+.2f}% | {ret.mean():+.2f}% |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    context = load_strategy_context(args.raw_dir, os.path.join(ROOT, args.summary))
    window_rows = []
    monthly_rows = []
    for scenario, (fee_pct, slippage_pct) in SCENARIOS.items():
        print(f"scenario {scenario}", flush=True)
        period_curves = {symbol: {} for symbol in SYMBOLS}
        month_curves = {}
        for symbol, item in context.items():
            for days in WINDOWS:
                curve = curve_for_period(item, days, fee_pct, slippage_pct)
                if curve is not None:
                    period_curves[symbol][f"{days}d"] = curve
            month_curves[symbol] = monthly_curves(item, fee_pct, slippage_pct)
        for portfolio, weights in PORTFOLIOS.items():
            for days in WINDOWS:
                period = f"{days}d"
                curves = {symbol: period_curves[symbol][period] for symbol in SYMBOLS if period in period_curves[symbol]}
                if len(curves) != len(SYMBOLS):
                    continue
                row = {"portfolio": portfolio, "scenario": scenario, "period": period, **combine_curves(curves, weights)}
                window_rows.append(row)
            months = sorted(set.intersection(*(set(month_curves[symbol].keys()) for symbol in SYMBOLS)))
            for month in months:
                curves = {symbol: month_curves[symbol][month] for symbol in SYMBOLS}
                sm = combine_curves(curves, weights)
                monthly_rows.append(
                    {
                        "portfolio": portfolio,
                        "scenario": scenario,
                        "month": month,
                        **sm,
                        "positive": sm["return_pct"] > 0,
                        "hit_4pct": sm["return_pct"] >= 4.0,
                    }
                )
    save_csv(os.path.join(ROOT, args.save_windows), window_rows)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows)
    save_report(os.path.join(ROOT, args.save_report), window_rows, monthly_rows)
    print(f"windows={len(window_rows)} monthly={len(monthly_rows)}")
    print(f"report={os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
