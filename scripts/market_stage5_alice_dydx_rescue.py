#!/usr/bin/env python3
"""Focused rescue test for the ALICE/DYDX short candidates.

The stage-4 broad validation found two promising base candidates, but none of
the top-50 survived stress execution cleanly. This script keeps the original
short setup fixed and tests only risk/regime overlays:

- smaller position sizes;
- 1h/4h closed-candle trend filters;
- daily/weekly kill switches;
- base vs stress execution.

This is not a parameter optimization pass. It is a robustness check for whether
the two candidates can become practical research candidates.
"""

import argparse
import csv
import math
import os
from collections import Counter
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0
WINDOWS = [30, 60, 90, 180, 365, 730]
SYMBOLS = ["ALICEUSDT", "DYDXUSDT"]


def parse_args():
    parser = argparse.ArgumentParser(description="Stage-5 rescue test for ALICE/DYDX short candidates.")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--save-summary", default="data/market_stage5_alice_dydx_rescue_summary.csv")
    parser.add_argument("--save-windows", default="data/market_stage5_alice_dydx_rescue_windows.csv")
    parser.add_argument("--save-months", default="data/market_stage5_alice_dydx_rescue_months.csv")
    parser.add_argument("--save-report", default="strategies/market-stage5-alice-dydx-rescue.md")
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
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14, min_periods=14).mean()
    df["atr_pct"] = df["atr14"] / close
    df["vol_sma20"] = volume.rolling(20, min_periods=20).mean()
    df["recent_low20"] = low.rolling(20, min_periods=20).min().shift(1)
    rng = (high - low).replace(0, np.nan)
    body = (close - df["open"]).abs()
    df["body_ratio"] = body / rng
    df["red"] = close < df["open"]
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
    htf[f"htf{minutes}_short"] = (htf["close"] < htf["ema200"]) & (htf["ema20"] < htf["ema50"])
    # A higher-timeframe candle is usable only after it is closed.
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


def base_short_signal(df):
    atr_ok = (df["atr_pct"] >= 0.0015) & (df["atr_pct"] <= 0.0120)
    score = (
        ((df["close"] < df["ema200"]) & (df["ema20"] < df["ema50"])).astype(int) * 25
        + (df["close"] < df["recent_low20"]).astype(int) * 25
        + (df["volume"] > df["vol_sma20"] * 1.5).astype(int) * 20
        + atr_ok.astype(int) * 15
        + ((df["body_ratio"] > 0.60) & df["red"]).astype(int) * 15
    )
    return score >= 60


def apply_overlay(df, overlay):
    signal = base_short_signal(df).to_numpy()
    if overlay["htf"] == "1h":
        signal &= df["htf60_short"].to_numpy()
    elif overlay["htf"] == "4h":
        signal &= df["htf240_short"].to_numpy()
    elif overlay["htf"] == "1h_and_4h":
        signal &= df["htf60_short"].to_numpy() & df["htf240_short"].to_numpy()

    if overlay["ret_24h_min"] is not None:
        signal &= df["ret_24h"].fillna(0).to_numpy() >= overlay["ret_24h_min"]
    if overlay["ret_7d_min"] is not None:
        signal &= df["ret_7d"].fillna(0).to_numpy() >= overlay["ret_7d_min"]
    return signal


def period_key(ms, mode):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    if mode == "day":
        return dt.strftime("%Y-%m-%d")
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


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


def run_backtest(df, signal, position_pct, fee_pct, slippage_pct, daily_stop_pct, weekly_stop_pct):
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
    signal_ptr = 0
    i = 250
    while i < n - 2:
        while signal_ptr < len(signal_indices) and signal_indices[signal_ptr] < i:
            signal_ptr += 1
        if signal_ptr >= len(signal_indices):
            break
        sig_idx = int(signal_indices[signal_ptr])
        if sig_idx >= n - 2:
            break
        i = max(i, sig_idx)
        day = period_key(times[i], "day")
        week = period_key(times[i], "week")
        daily_start.setdefault(day, equity)
        weekly_start.setdefault(week, equity)
        if day in blocked_days or week in blocked_weeks:
            i += 1
            continue

        entry_idx = i + 1
        entry = open_[entry_idx] * (1.0 - slippage_pct)
        notional = equity * position_pct
        exit_idx = min(entry_idx + 120, n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
        tp_price = entry * (1.0 - 0.007)
        sl_price = entry * (1.0 + 0.04)
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
        trades.append(
            {
                "entry_time_ms": int(times[entry_idx]),
                "exit_time_ms": int(times[exit_idx]),
                "net_return_pct": net * 100.0,
                "reason": reason,
            }
        )

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
    rows = []
    for item in months.values():
        start = item["start_equity"]
        item["return_pct"] = (item.get("end_equity", start) / start - 1.0) * 100.0 if start else 0.0
        rows.append(item)
    return rows


def overlay_grid():
    rows = []
    htf_modes = ["none", "1h", "4h", "1h_and_4h"]
    protections = [
        (0.0, 0.0),
        (0.01, 0.0),
        (0.0, 0.04),
        (0.01, 0.04),
        (0.015, 0.08),
    ]
    return_filters = [
        (None, None),
        (-0.10, None),
        (None, -0.25),
        (-0.06, -0.15),
    ]
    for htf, (daily_stop, weekly_stop), (ret_24h_min, ret_7d_min) in product(htf_modes, protections, return_filters):
        name = f"{htf} d{daily_stop:.3f} w{weekly_stop:.3f} r24{ret_24h_min} r7{ret_7d_min}"
        rows.append(
            {
                "overlay": name,
                "htf": htf,
                "ret_24h_min": ret_24h_min,
                "ret_7d_min": ret_7d_min,
                "daily_stop_pct": daily_stop,
                "weekly_stop_pct": weekly_stop,
            }
        )
    return rows


def fmt(v):
    if v in ("", None) or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    try:
        return f"{float(v):+.2f}"
    except Exception:
        return str(v)


def build_summary(windows, months):
    grouped = {}
    for row in windows:
        if row.get("status") != "ok":
            continue
        key = (row["symbol"], row["overlay"], row["scenario"], row["position_pct"])
        grouped.setdefault(key, []).append(row)
    month_group = {}
    for row in months:
        key = (row["symbol"], row["overlay"], row["scenario"], row["position_pct"])
        month_group.setdefault(key, []).append(row)

    out = []
    for key, rows in grouped.items():
        by_period = {row["period"]: row for row in rows}
        ref = by_period.get("730d") or by_period.get("365d")
        if not ref:
            continue
        returns = [float(row["return_pct"]) for row in by_period.values()]
        dds = [float(row["max_dd_pct"]) for row in by_period.values()]
        pfs = [float(row["profit_factor"]) for row in by_period.values()]
        mrows = month_group.get(key, [])
        out.append(
            {
                "symbol": ref["symbol"],
                "strategy": "SHORT th60 base TP0.7 T120",
                "overlay": ref["overlay"],
                "scenario": ref["scenario"],
                "position_pct": ref["position_pct"],
                "fee_pct": ref["fee_pct"],
                "slippage_pct": ref["slippage_pct"],
                "windows_count": len(by_period),
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
                "blocked_days_730d": by_period.get("730d", {}).get("blocked_days", ""),
                "blocked_weeks_730d": by_period.get("730d", {}).get("blocked_weeks", ""),
                "months_count": len(mrows),
                "positive_months": sum(float(m.get("return_pct") or 0) > 0 for m in mrows),
                "months_40usd_plus": sum(float(m.get("pnl") or 0) >= 40 for m in mrows),
            }
        )
    out.sort(
        key=lambda r: (
            r["scenario"] == "stress",
            int(r["positive_windows"]),
            float(r["return_730d_pct"] or -999),
            float(r["pf_730d"] or 0),
            -float(r["max_dd_any_pct"] or 999),
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
        "symbol",
        "strategy",
        "overlay",
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
    fields = preferred + [field for field in fields if field not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_report(path, summary, windows, months):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stress_ok = [
        row
        for row in summary
        if row["scenario"] == "stress"
        and int(row["positive_windows"]) >= 5
        and float(row.get("return_365d_pct") or -999) > 0
        and float(row.get("return_730d_pct") or -999) > 0
        and float(row.get("pf_365d") or 0) >= 1.05
        and float(row.get("pf_730d") or 0) >= 1.02
        and float(row.get("max_dd_any_pct") or 999) <= 40
    ]
    base_ok = [
        row
        for row in summary
        if row["scenario"] == "base"
        and int(row["positive_windows"]) >= 5
        and float(row.get("return_365d_pct") or -999) > 0
        and float(row.get("return_730d_pct") or -999) > 0
        and float(row.get("max_dd_any_pct") or 999) <= 40
    ]

    def table(rows, limit):
        lines = [
            "| # | Монета | Позиция | Фильтр | Окна + | 365d | 730d | PF365 | PF730 | DD365 | DD730 | Месяцы + | $40+ |",
            "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for i, row in enumerate(rows[:limit], 1):
            lines.append(
                f"| {i} | `{row['symbol']}` | {float(row['position_pct']):.0%} | `{row['overlay']}` | "
                f"{row['positive_windows']}/{row['windows_count']} | {fmt(row['return_365d_pct'])}% | {fmt(row['return_730d_pct'])}% | "
                f"{float(row.get('pf_365d') or 0):.2f} | {float(row.get('pf_730d') or 0):.2f} | "
                f"{float(row.get('dd_365d_pct') or 0):.2f}% | {float(row.get('dd_730d_pct') or 0):.2f}% | "
                f"{row['positive_months']}/{row['months_count']} | {row['months_40usd_plus']}/{row['months_count']} |"
            )
        return lines

    lines = [
        "# Stage-5 ALICE/DYDX Rescue",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Проверка двух кандидатов из stage-4: `ALICEUSDT` и `DYDXUSDT`, только SHORT th60 base TP 0.7% T120.",
        "",
        "## Итог",
        "",
        f"- Строк summary: `{len(summary)}`",
        f"- Оконных тестов: `{len(windows)}`",
        f"- Месячных строк: `{len(months)}`",
        f"- Прошли строгий stress-фильтр: `{len(stress_ok)}`",
        f"- Прошли только base-фильтр: `{len(base_ok)}`",
        "",
        "## Лучшие под стрессом",
        "",
    ]
    lines.extend(table(stress_ok, 40) if stress_ok else ["Строгий стресс-фильтр никто не прошел."])
    lines.extend(["", "## Лучшие без стресса", ""])
    lines.extend(table(base_ok, 40) if base_ok else ["Даже базовый фильтр никто не прошел."])
    lines.extend(
        [
            "",
            "## Топ общий",
            "",
        ]
    )
    lines.extend(table(summary, 80))
    lines.extend(
        [
            "",
            "## Человеческий вывод",
            "",
            "Если stress-блок пустой, значит стратегия может выглядеть красиво на maker-условиях, но пока не доказала живучесть при ухудшении исполнения.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    overlays = overlay_grid()
    scenarios = [("base", 0.0002, 0.0), ("stress", 0.0004, 0.0002)]
    positions = [0.10, 0.15, 0.20, 0.25]
    windows_out = []
    months_out = []
    for symbol in SYMBOLS:
        path = os.path.join(ROOT, args.raw_1m_dir, f"{symbol}_1m.csv")
        print(f"Loading {symbol}", flush=True)
        df = add_closed_htf_permissions(add_closed_htf_permissions(add_indicators(read_symbol(path)), 60), 240)
        print(f"{symbol}: candles={len(df)} overlays={len(overlays)}", flush=True)
        for oi, overlay in enumerate(overlays, 1):
            signal = apply_overlay(df, overlay)
            if signal.sum() == 0:
                continue
            for scenario, fee_pct, slippage_pct in scenarios:
                for position_pct in positions:
                    for days in WINDOWS:
                        bars = days * 1440
                        if len(df) < bars + 300:
                            continue
                        sub = df.tail(bars + 300).reset_index(drop=True)
                        sub_signal = signal[-(bars + 300) :]
                        summary, trades = run_backtest(
                            sub,
                            sub_signal,
                            position_pct,
                            fee_pct,
                            slippage_pct,
                            overlay["daily_stop_pct"],
                            overlay["weekly_stop_pct"],
                        )
                        row = {
                            "symbol": symbol,
                            "strategy": "SHORT th60 base TP0.7 T120",
                            "overlay": overlay["overlay"],
                            "htf": overlay["htf"],
                            "ret_24h_min": overlay["ret_24h_min"],
                            "ret_7d_min": overlay["ret_7d_min"],
                            "daily_stop_pct": overlay["daily_stop_pct"],
                            "weekly_stop_pct": overlay["weekly_stop_pct"],
                            "scenario": scenario,
                            "position_pct": position_pct,
                            "fee_pct": fee_pct,
                            "slippage_pct": slippage_pct,
                            "period": f"{days}d",
                            "status": "ok",
                            **{k: v for k, v in summary.items() if k != "exit_reasons"},
                            "take_profit": summary["exit_reasons"].get("take_profit", 0),
                            "stop_loss": summary["exit_reasons"].get("stop_loss", 0),
                            "time_stop": summary["exit_reasons"].get("time_stop", 0),
                        }
                        windows_out.append(row)
                        if days == 730:
                            for month in monthly_from_trades(trades, position_pct):
                                months_out.append({**row, **month})
            if oi % 20 == 0:
                print(f"{symbol}: overlay {oi}/{len(overlays)} windows={len(windows_out)}", flush=True)

    summary = build_summary(windows_out, months_out)
    save_csv(os.path.join(ROOT, args.save_windows), windows_out)
    save_csv(os.path.join(ROOT, args.save_months), months_out)
    save_csv(os.path.join(ROOT, args.save_summary), summary)
    save_report(os.path.join(ROOT, args.save_report), summary, windows_out, months_out)
    print(f"Saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"Saved windows: {os.path.join(ROOT, args.save_windows)}")
    print(f"Saved months: {os.path.join(ROOT, args.save_months)}")
    print(f"Saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
