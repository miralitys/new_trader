#!/usr/bin/env python3
"""Aggressive follow-up search for DYDX Pullback SHORT.

This keeps the same new strategy family found in the first DYDX search, but
tests whether return can be raised by:
- using larger position sizes;
- allowing slightly wider pullbacks;
- testing bigger TP / wider SL / longer time stops.

The goal is not to optimize endlessly, but to find a practical return/DD tradeoff.
"""

import argparse
import csv
import math
import os
from datetime import datetime, timezone
from itertools import product

import dydx_pullback_short_tune as base


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOWS = [30, 60, 90, 180, 365, 730]


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Aggressive DYDX Pullback SHORT search.")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default=f"data/dydx_pullback_short_aggressive_summary_{today}.csv")
    parser.add_argument("--save-windows", default=f"data/dydx_pullback_short_aggressive_windows_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/DYDX/dydx-pullback-short-aggressive-{today}.md")
    return parser.parse_args()


def aggressive_variants():
    rows = []
    rsi_bands = [(45, 60), (48, 62), (50, 65)]
    ema_bands = [(0.997, 1.008), (0.997, 1.012), (0.995, 1.010)]
    atr_bands = [(0.0025, 0.012), (0.0020, 0.014), (0.0030, 0.014)]
    guards = ["none", "avoid_after_dump"]
    exits = [
        (0.007, 0.030, 180),
        (0.008, 0.030, 180),
        (0.010, 0.035, 240),
        (0.012, 0.040, 240),
        (0.006, 0.025, 180),
    ]
    for (rsi_min, rsi_max), (ema20_low, ema50_high), (atr_min, atr_max), guard, (tp, sl, time_stop) in product(
        rsi_bands, ema_bands, atr_bands, guards, exits
    ):
        rows.append(
            {
                "variant": (
                    f"aggr_rsi{rsi_min}-{rsi_max}_ema{ema20_low}-{ema50_high}"
                    f"_atr{atr_min}-{atr_max}_guard{guard}_tp{tp}_sl{sl}_t{time_stop}"
                ),
                "rsi_min": rsi_min,
                "rsi_max": rsi_max,
                "ema20_low": ema20_low,
                "ema50_high": ema50_high,
                "atr_min": atr_min,
                "atr_max": atr_max,
                "vol_mult": 0.0,
                "guard": guard,
                "tp": tp,
                "sl": sl,
                "time_stop": time_stop,
            }
        )
    return rows


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "symbol", "family", "variant", "scenario", "position_pct", "positive_windows", "windows_count",
        "return_30d_pct", "return_60d_pct", "return_90d_pct", "return_180d_pct", "return_365d_pct",
        "return_730d_pct", "pf_365d", "pf_730d", "dd_365d_pct", "dd_730d_pct", "max_dd_any_pct",
        "trades_365d", "trades_730d",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):+.2f}"


def save_report(path, summary):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    strict = [
        r for r in summary
        if r["scenario"] == "stress"
        and int(r["positive_windows"]) == int(r["windows_count"])
        and float(r.get("return_365d_pct") or -999) > 0
        and float(r.get("return_730d_pct") or -999) > 0
        and float(r.get("pf_730d") or 0) >= 1.05
        and float(r.get("max_dd_any_pct") or 999) <= 35
    ]
    lines = [
        "# DYDX Pullback SHORT Aggressive Search",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        f"- Summary rows: `{len(summary)}`",
        f"- Strict stress pass: `{len(strict)}`",
        "",
        "## Best Strict Stress Candidates",
        "",
        "| # | Pos | Variant | 30d | 60d | 90d | 180d | 365d | 730d | PF730 | DD730 | MaxDD | Trades365 |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(strict[:50], 1):
        lines.append(
            f"| {i} | {float(r['position_pct']):.0%} | `{r['variant']}` | "
            f"{fmt(r.get('return_30d_pct'))}% | {fmt(r.get('return_60d_pct'))}% | "
            f"{fmt(r.get('return_90d_pct'))}% | {fmt(r.get('return_180d_pct'))}% | "
            f"{fmt(r.get('return_365d_pct'))}% | {fmt(r.get('return_730d_pct'))}% | "
            f"{float(r.get('pf_730d') or 0):.2f} | {float(r.get('dd_730d_pct') or 0):.2f}% | "
            f"{float(r.get('max_dd_any_pct') or 0):.2f}% | {r.get('trades_365d')} |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    df = base.read_symbol(os.path.join(ROOT, args.raw_1m_dir, "DYDXUSDT_1m.csv"))
    df = base.add_closed_htf(base.add_closed_htf(base.add_indicators(df), 60), 240)
    scenarios = [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]
    positions = [0.25, 0.35, 0.50, 0.65]
    vars_ = aggressive_variants()
    windows_out = []
    for idx, variant in enumerate(vars_, 1):
        sig = base.signal_for(df, variant)
        if sig.sum() < 100:
            continue
        if idx % 25 == 0:
            print(f"[{idx}/{len(vars_)}] rows={len(windows_out)}", flush=True)
        for scenario, fee_pct, slippage_pct in scenarios:
            for position_pct in positions:
                for days in WINDOWS:
                    bars = days * 1440
                    if len(df) < bars + 300:
                        continue
                    sub = df.tail(bars + 300).reset_index(drop=True)
                    sub_signal = sig[-(bars + 300):]
                    summary = base.run_backtest(sub, sub_signal, variant, position_pct, fee_pct, slippage_pct)
                    windows_out.append(
                        {
                            **variant,
                            "symbol": "DYDXUSDT",
                            "family": "dydx_pullback_short_aggressive",
                            "scenario": scenario,
                            "position_pct": position_pct,
                            "fee_pct": fee_pct,
                            "slippage_pct": slippage_pct,
                            "period": f"{days}d",
                            **{k: val for k, val in summary.items() if k != "exit_reasons"},
                            "take_profit": summary["exit_reasons"].get("take_profit", 0),
                            "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                            "time_stop_exit": summary["exit_reasons"].get("time_stop", 0),
                        }
                    )
    summary = base.build_summary(windows_out)
    save_csv(os.path.join(ROOT, args.save_windows), windows_out)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_report(os.path.join(ROOT, args.save_report), summary)
    print(f"variants={len(vars_)} windows={len(windows_out)} summary={len(summary)}")
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
