#!/usr/bin/env python3
"""Protection grid for DYDX Pullback SHORT aggressive leverage.

Tests x2/x3 with:
- daily realized loss stop;
- weekly realized loss stop;
- cooldown after consecutive stop losses;
- no-trade filter after too strong DYDX movement.
"""

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd

import dydx_pullback_short_tune as base


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_POSITION_PCT = 0.65
WINDOWS = [1, 7, 30, 60, 90, 180, 365, 730]
VARIANT = {
    "variant": "aggr_rsi48-62_ema0.995-1.01_atr0.003-0.014_guardnone_tp0.008_sl0.03_t180",
    "rsi_min": 48,
    "rsi_max": 62,
    "ema20_low": 0.995,
    "ema50_high": 1.010,
    "atr_min": 0.003,
    "atr_max": 0.014,
    "vol_mult": 0.0,
    "guard": "none",
    "tp": 0.008,
    "sl": 0.030,
    "time_stop": 180,
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="DYDX aggressive leverage protection grid.")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default=f"data/dydx_pullback_short_leverage_protection_summary_{today}.csv")
    parser.add_argument("--save-windows", default=f"data/dydx_pullback_short_leverage_protection_windows_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/dydx_pullback_short_leverage_protection_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/DYDX/dydx-pullback-short-leverage-protection-{today}.md")
    return parser.parse_args()


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def day_key(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def week_key(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def protection_grid():
    rows = []
    for leverage, daily_stop, weekly_stop, stop_streak, cooldown_hours, ret24_abs, ret7_abs in product(
        [2, 3],
        [6.0, 8.0, 10.0],
        [12.0, 16.0, 20.0],
        [2, 3],
        [12, 24],
        [0.12, 0.18, 0.25],
        [0.30, 0.45],
    ):
        rows.append(
            {
                "leverage": leverage,
                "effective_notional_pct": BASE_POSITION_PCT * leverage * 100.0,
                "daily_stop_pct": daily_stop,
                "weekly_stop_pct": weekly_stop,
                "stop_streak": stop_streak,
                "cooldown_hours": cooldown_hours,
                "ret24_abs_limit": ret24_abs,
                "ret7_abs_limit": ret7_abs,
                "name": (
                    f"x{leverage}_d{daily_stop:g}_w{weekly_stop:g}_st{stop_streak}"
                    f"_cd{cooldown_hours}_r24{ret24_abs:g}_r7{ret7_abs:g}"
                ),
            }
        )
    return rows


def summarize(trades, curve):
    if not trades:
        return {
            "trades": 0,
            "return_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "expectancy_pct": 0.0,
            "worst_trade_deposit_pct": 0.0,
            "exit_reasons": {},
        }
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
        "worst_trade_deposit_pct": min(returns),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
    }


def run_backtest(df, sig, protection, fee_pct, slippage_pct):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    ret24 = df["ret_24h"].fillna(0).to_numpy()
    ret7 = df["ret_7d"].fillna(0).to_numpy()
    effective_position = BASE_POSITION_PCT * protection["leverage"]

    equity = 1000.0
    curve = [equity]
    trades = []
    indices = np.flatnonzero(sig)
    ptr = 0
    i = 250
    n = len(df)
    current_day = None
    current_week = None
    day_start_equity = equity
    week_start_equity = equity
    cooldown_until_ms = -1
    consecutive_stops = 0
    skipped_daily_stop = 0
    skipped_weekly_stop = 0
    skipped_cooldown = 0
    skipped_movement = 0

    while i < n - 2 and equity > 0:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        i = int(indices[ptr])
        signal_time = int(times[i])
        dk = day_key(signal_time)
        wk = week_key(signal_time)
        if dk != current_day:
            current_day = dk
            day_start_equity = equity
            consecutive_stops = 0
        if wk != current_week:
            current_week = wk
            week_start_equity = equity

        day_return = (equity / day_start_equity - 1.0) * 100.0 if day_start_equity else 0.0
        week_return = (equity / week_start_equity - 1.0) * 100.0 if week_start_equity else 0.0
        if day_return <= -protection["daily_stop_pct"]:
            skipped_daily_stop += 1
            i += 1
            continue
        if week_return <= -protection["weekly_stop_pct"]:
            skipped_weekly_stop += 1
            i += 1
            continue
        if signal_time < cooldown_until_ms:
            skipped_cooldown += 1
            i += 1
            continue
        if abs(ret24[i]) > protection["ret24_abs_limit"] or abs(ret7[i]) > protection["ret7_abs_limit"]:
            skipped_movement += 1
            i += 1
            continue

        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = open_[entry_idx] * (1.0 - slippage_pct)
        tp = entry * (1.0 - VARIANT["tp"])
        sl = entry * (1.0 + VARIANT["sl"])
        exit_idx = min(entry_idx + VARIANT["time_stop"], n - 1)
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
        deposit_return = effective_position * net
        equity *= 1.0 + deposit_return
        equity = max(equity, 0.0)
        curve.append(equity)
        if reason == "stop_loss":
            consecutive_stops += 1
            if consecutive_stops >= protection["stop_streak"]:
                cooldown_until_ms = int(times[exit_idx]) + protection["cooldown_hours"] * 60 * 60 * 1000
                consecutive_stops = 0
        else:
            consecutive_stops = 0
        trades.append(
            {
                "entry_time": iso(int(times[entry_idx])),
                "exit_time": iso(int(times[exit_idx])),
                "net_return_pct": net * 100.0,
                "deposit_return_pct": deposit_return * 100.0,
                "reason": reason,
                "equity_after": equity,
            }
        )
        i = exit_idx + 1

    summary = summarize(trades, curve)
    summary["skipped_daily_stop"] = skipped_daily_stop
    summary["skipped_weekly_stop"] = skipped_weekly_stop
    summary["skipped_cooldown"] = skipped_cooldown
    summary["skipped_movement"] = skipped_movement
    return summary, trades


def build_summary(windows):
    grouped = defaultdict(list)
    for row in windows:
        grouped[(row["name"], row["scenario"])].append(row)
    out = []
    for (name, scenario), rows in grouped.items():
        by = {r["period"]: r for r in rows}
        returns = [r["return_pct"] for r in rows]
        dds = [r["max_dd_pct"] for r in rows]
        pfs = [r["profit_factor"] for r in rows if r["trades"] > 0]
        ref = rows[0]
        out.append(
            {
                "name": name,
                "scenario": scenario,
                "leverage": ref["leverage"],
                "effective_notional_pct": ref["effective_notional_pct"],
                "daily_stop_pct": ref["daily_stop_pct"],
                "weekly_stop_pct": ref["weekly_stop_pct"],
                "stop_streak": ref["stop_streak"],
                "cooldown_hours": ref["cooldown_hours"],
                "ret24_abs_limit": ref["ret24_abs_limit"],
                "ret7_abs_limit": ref["ret7_abs_limit"],
                "positive_windows": sum(r > 0 for r in returns),
                "nonnegative_windows": sum(r >= 0 for r in returns),
                "windows_count": len(rows),
                "min_return_pct": min(returns),
                "max_dd_any_pct": max(dds),
                "min_pf": min(pfs) if pfs else 0,
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
                "trades_1d": by.get("1d", {}).get("trades", ""),
                "trades_7d": by.get("7d", {}).get("trades", ""),
                "trades_365d": by.get("365d", {}).get("trades", ""),
                "trades_730d": by.get("730d", {}).get("trades", ""),
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "stress",
            r["nonnegative_windows"],
            float(r.get("return_730d_pct") or -999),
            -float(r.get("max_dd_any_pct") or 999),
        ),
        reverse=True,
    )
    return out


def monthly_rows(trades, scenario, protection):
    months = defaultdict(list)
    for trade in trades:
        months[trade["exit_time"][:7]].append(trade)
    rows = []
    for month in sorted(months):
        equity = 1000.0
        curve = [equity]
        month_trades = []
        reasons = Counter()
        for trade in months[month]:
            ret = trade["deposit_return_pct"] / 100.0
            equity *= 1.0 + ret
            equity = max(equity, 0.0)
            curve.append(equity)
            month_trades.append(trade)
            reasons[trade["reason"]] += 1
        summary = summarize(month_trades, curve)
        rows.append(
            {
                "scenario": scenario,
                **protection,
                "month": month,
                **{k: v for k, v in summary.items() if k != "exit_reasons"},
                "take_profit": reasons["take_profit"],
                "stop_loss": reasons["stop_loss"],
                "time_stop": reasons["time_stop"],
            }
        )
    return rows


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "name", "scenario", "leverage", "effective_notional_pct", "daily_stop_pct", "weekly_stop_pct",
        "stop_streak", "cooldown_hours", "ret24_abs_limit", "ret7_abs_limit", "period", "month",
        "return_1d_pct", "return_7d_pct", "return_30d_pct", "return_60d_pct", "return_90d_pct",
        "return_180d_pct", "return_365d_pct", "return_730d_pct", "return_pct", "max_dd_pct",
        "profit_factor", "pf_365d", "pf_730d", "dd_365d_pct", "dd_730d_pct", "trades",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    if value in ("", None) or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):+.2f}%"


def save_report(path, summary, monthly):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stress = [
        r for r in summary
        if r["scenario"] == "stress"
        and int(r["nonnegative_windows"]) == int(r["windows_count"])
        and float(r.get("return_365d_pct") or -999) > 0
        and float(r.get("return_730d_pct") or -999) > 0
        and float(r.get("pf_730d") or 0) >= 1.05
    ]
    lines = [
        "# DYDX Pullback SHORT x2/x3 Protection Test",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Stress: fee `0.04%` per side + slippage `0.02%` per side.",
        "",
        f"- Summary rows: `{len(summary)}`",
        f"- Stress candidates: `{len(stress)}`",
        "",
        "## Top Stress Candidates",
        "",
        "| # | Lev | Daily | Weekly | Streak | Cooldown | Move filter | 1d | 7d | 30d | 60d | 365d | 730d | DD730 | PF730 | Trades 1d/7d |",
        "|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(stress[:40], 1):
        lines.append(
            f"| {i} | x{int(row['leverage'])} | {row['daily_stop_pct']:.0f}% | {row['weekly_stop_pct']:.0f}% | "
            f"{int(row['stop_streak'])} | {int(row['cooldown_hours'])}h | "
            f"24h {row['ret24_abs_limit']:.0%}, 7d {row['ret7_abs_limit']:.0%} | "
            f"{fmt(row.get('return_1d_pct'))} | {fmt(row.get('return_7d_pct'))} | "
            f"{fmt(row.get('return_30d_pct'))} | {fmt(row.get('return_60d_pct'))} | "
            f"{fmt(row.get('return_365d_pct'))} | {fmt(row.get('return_730d_pct'))} | "
            f"{float(row.get('dd_730d_pct') or 0):.2f}% | {float(row.get('pf_730d') or 0):.2f} | "
            f"{row.get('trades_1d')}/{row.get('trades_7d')} |"
        )
    lines.extend(["", "## Monthly Stress Best By Leverage", ""])
    monthly_df = pd.DataFrame(monthly)
    for lev in [2, 3]:
        candidates = [r for r in stress if int(r["leverage"]) == lev]
        if not candidates:
            continue
        best = candidates[0]
        m = monthly_df[(monthly_df["scenario"] == "stress") & (monthly_df["name"] == best["name"])].tail(24)
        lines.append(
            f"- x{lev}: `{best['name']}` -> positive months `{int((m['return_pct'] > 0).sum())}/24`, "
            f"negative `{int((m['return_pct'] < 0).sum())}/24`, worst `{m['return_pct'].min():+.2f}%`, "
            f"best `{m['return_pct'].max():+.2f}%`."
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    df = base.read_symbol(os.path.join(ROOT, args.raw_1m_dir, "DYDXUSDT_1m.csv"))
    df = base.add_closed_htf(base.add_closed_htf(base.add_indicators(df), 60), 240)
    sig = base.signal_for(df, VARIANT)
    scenarios = [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]
    protections = protection_grid()
    windows_out = []
    monthly_out = []
    for idx, protection in enumerate(protections, 1):
        if idx % 50 == 0:
            print(f"[{idx}/{len(protections)}] rows={len(windows_out)}", flush=True)
        for scenario, fee_pct, slippage_pct in scenarios:
            full_summary, full_trades = run_backtest(df, sig, protection, fee_pct, slippage_pct)
            monthly_out.extend(monthly_rows(full_trades, scenario, protection))
            for days in WINDOWS:
                bars = days * 1440
                if len(df) < bars + 300:
                    continue
                sub = df.tail(bars + 300).reset_index(drop=True)
                sub_sig = sig[-(bars + 300):]
                summary, _ = run_backtest(sub, sub_sig, protection, fee_pct, slippage_pct)
                windows_out.append(
                    {
                        **protection,
                        "symbol": "DYDXUSDT",
                        "scenario": scenario,
                        "period": f"{days}d",
                        **{k: v for k, v in summary.items() if k != "exit_reasons"},
                        "take_profit": summary["exit_reasons"].get("take_profit", 0),
                        "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                        "time_stop": summary["exit_reasons"].get("time_stop", 0),
                    }
                )
    summary = build_summary(windows_out)
    save_csv(os.path.join(ROOT, args.save_windows), windows_out)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_out)
    save_report(os.path.join(ROOT, args.save_report), summary, monthly_out)
    print(f"protections={len(protections)} windows={len(windows_out)} summary={len(summary)} monthly={len(monthly_out)}")
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
