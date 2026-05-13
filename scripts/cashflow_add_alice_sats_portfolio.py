#!/usr/bin/env python3
"""Test whether ALICE/1000SATS improve existing monthly cashflow portfolios.

The new candidates came from the stage-5 rescue test:

- ALICEUSDT SHORT th50 wide TP0.5 T90 with 4h trend + return guard;
- 1000SATSUSDT SHORT th60 base TP0.7 T120 with 1h+4h trend + return guard.

This script rebuilds their trade streams, appends them to the existing best
strategy trade pool, then compares old cashflow portfolios against variants
that allocate a small sleeve to ALICE/1000SATS.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXISTING_TRADES = "data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv"
INITIAL_BALANCE = 1000.0
BASE_FEE_PCT = 0.0002


NEW_SPECS = [
    {
        "coin": "ALICE",
        "symbol": "ALICEUSDT",
        "strategy": "ALICE SHORT Rescue 4h",
        "direction": "short",
        "threshold": 50,
        "regime": "wide",
        "tp": 0.005,
        "sl": 0.040,
        "time_stop": 90,
        "htf": "4h",
        "return_guard": True,
    },
    {
        "coin": "1000SATS",
        "symbol": "1000SATSUSDT",
        "strategy": "1000SATS SHORT Rescue 1h+4h",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "tp": 0.007,
        "sl": 0.035,
        "time_stop": 120,
        "htf": "1h_and_4h",
        "return_guard": True,
    },
]


PORTFOLIOS = {
    "cashflow1_old": {
        "label": "Cashflow 1 old - GALA20/SPELL80",
        "weights": {"GALA": 0.20, "SPELL": 0.80},
        "scale": 6.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.35,
        "daily_loss_stop_pct": 0.07,
    },
    "cashflow1_alice_sats": {
        "label": "Cashflow 1 + ALICE/1000SATS",
        "weights": {"GALA": 0.15, "SPELL": 0.65, "ALICE": 0.10, "1000SATS": 0.10},
        "scale": 6.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.35,
        "daily_loss_stop_pct": 0.07,
    },
    "cashflow1_small_new": {
        "label": "Cashflow 1 + small ALICE/1000SATS",
        "weights": {"GALA": 0.18, "SPELL": 0.72, "ALICE": 0.05, "1000SATS": 0.05},
        "scale": 6.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.35,
        "daily_loss_stop_pct": 0.07,
    },
    "cashflow2_old": {
        "label": "Cashflow 2 old - CHZ10/SHIB10/SPELL80",
        "weights": {"CHZ": 0.10, "SHIB": 0.10, "SPELL": 0.80},
        "scale": 8.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.50,
        "daily_loss_stop_pct": 0.07,
    },
    "cashflow2_alice_sats": {
        "label": "Cashflow 2 + ALICE/1000SATS",
        "weights": {"CHZ": 0.08, "SHIB": 0.08, "SPELL": 0.64, "ALICE": 0.10, "1000SATS": 0.10},
        "scale": 8.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.50,
        "daily_loss_stop_pct": 0.07,
    },
    "alice_sats_only": {
        "label": "ALICE/1000SATS only",
        "weights": {"ALICE": 0.50, "1000SATS": 0.50},
        "scale": 2.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.35,
        "daily_loss_stop_pct": 0.07,
    },
}


def parse_args():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Add ALICE/1000SATS candidates to cashflow portfolios.")
    parser.add_argument("--raw-1m-dir", default="data/futures_1m_raw_history")
    parser.add_argument("--existing-trades", default=EXISTING_TRADES)
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--save-new-trades", default=f"data/cashflow_alice_sats_new_trades_{today}.csv")
    parser.add_argument("--save-combined-trades", default=f"data/cashflow_plus_alice_sats_trades_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/cashflow_plus_alice_sats_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/cashflow_plus_alice_sats_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/cashflow-plus-alice-sats-portfolio-{today}.md")
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


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
    htf[f"htf{minutes}_short"] = (htf["close"] < htf["ema200"]) & (htf["ema20"] < htf["ema50"])
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


def short_signal(df, spec):
    if spec["regime"] == "wide":
        atr_min, atr_max, vol_mult = 0.0010, 0.0200, 1.2
    else:
        atr_min, atr_max, vol_mult = 0.0015, 0.0120, 1.5
    score = (
        ((df["close"] < df["ema200"]) & (df["ema20"] < df["ema50"])).astype(int) * 25
        + (df["close"] < df["recent_low20"]).astype(int) * 25
        + (df["volume"] > df["vol_sma20"] * vol_mult).astype(int) * 20
        + ((df["atr_pct"] >= atr_min) & (df["atr_pct"] <= atr_max)).astype(int) * 15
        + ((df["body_ratio"] > 0.60) & df["red"]).astype(int) * 15
    )
    signal = (score >= spec["threshold"]).to_numpy()
    if spec["htf"] == "4h":
        signal &= df["htf240_short"].to_numpy()
    elif spec["htf"] == "1h_and_4h":
        signal &= df["htf60_short"].to_numpy() & df["htf240_short"].to_numpy()
    if spec["return_guard"]:
        signal &= (df["ret_24h"].fillna(0).to_numpy() >= -0.06) & (df["ret_7d"].fillna(0).to_numpy() >= -0.15)
    return signal


def run_trade_stream(df, signal, spec, fee_pct=BASE_FEE_PCT, slippage_pct=0.0):
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df["open_time_ms"].to_numpy()
    trades = []
    indices = np.flatnonzero(signal)
    ptr = 0
    i = 250
    n = len(df)
    while i < n - 2:
        while ptr < len(indices) and indices[ptr] < i:
            ptr += 1
        if ptr >= len(indices):
            break
        i = int(indices[ptr])
        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = open_[entry_idx] * (1.0 - slippage_pct)
        tp_price = entry * (1.0 - spec["tp"])
        sl_price = entry * (1.0 + spec["sl"])
        exit_idx = min(entry_idx + spec["time_stop"], n - 1)
        exit_price = close[exit_idx]
        reason = "time_stop"
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
        trades.append(
            {
                "coin": spec["coin"],
                "symbol": spec["symbol"],
                "strategy": spec["strategy"],
                "direction": "short",
                "module": spec["strategy"],
                "entry_time": iso(int(times[entry_idx])),
                "exit_time": iso(int(times[exit_idx])),
                "reason": reason,
                "raw_return_pct": net * 100.0,
                "allocation": "",
                "portfolio_return_pct": "",
            }
        )
        i = exit_idx + 1
    return trades


def load_existing_trades(path, start_month, end_month):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            month = row["exit_time"][:7]
            if start_month <= month <= end_month:
                item = dict(row)
                item["raw_return_pct"] = float(item["raw_return_pct"])
                rows.append(item)
    return rows


def build_new_trades(args):
    all_trades = []
    for spec in NEW_SPECS:
        print(f"Building {spec['coin']} trades", flush=True)
        df = read_symbol(os.path.join(ROOT, args.raw_1m_dir, f"{spec['symbol']}_1m.csv"))
        df = add_closed_htf_permissions(add_closed_htf_permissions(add_indicators(df), 60), 240)
        signal = short_signal(df, spec)
        trades = run_trade_stream(df, signal, spec)
        all_trades.extend(trades)
        print(f"{spec['coin']}: {len(trades)} trades", flush=True)
    return all_trades


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def profit_factor(values):
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    return wins / losses if losses else (math.inf if wins else 0.0)


def max_drawdown(points):
    peak = points[0] if points else INITIAL_BALANCE
    dd = 0.0
    for value in points:
        peak = max(peak, value)
        dd = max(dd, (peak - value) / peak * 100.0)
    return dd


def embedded_exposure(trade):
    if trade["coin"] in {"GALA", "ONE"}:
        if trade.get("direction") == "long":
            return 0.18
        if trade.get("direction") == "short":
            return 0.36
    return 1.0


def adjusted_return(trade, scenario):
    extra_fee = max(0.0, scenario["fee_pct"] - BASE_FEE_PCT)
    extra_cost = embedded_exposure(trade) * 2.0 * (extra_fee + scenario["slippage_pct"]) * 100.0
    return float(trade["raw_return_pct"]) - extra_cost


def simulate(trades, months, portfolio, scenario):
    weights = portfolio["weights"]
    selected = [dict(t) for t in trades if t["coin"] in weights]
    for trade in selected:
        trade["exit_dt"] = parse_time(trade["exit_time"])
        trade["entry_dt"] = parse_time(trade["entry_time"])
        trade["month"] = trade["exit_time"][:7]
    selected.sort(key=lambda t: (t["exit_dt"], t["entry_dt"], t["coin"]))
    by_month = defaultdict(list)
    for trade in selected:
        by_month[trade["month"]].append(trade)

    equity = INITIAL_BALANCE
    equity_points = [equity]
    monthly = []
    all_pnls = []
    for month in months:
        start = equity
        target_balance = INITIAL_BALANCE + portfolio["target_cash"]
        loss_floor = start * (1.0 - portfolio["monthly_loss_stop_pct"])
        daily_start = {}
        disabled_days = set()
        stop_reason = "month_end"
        stop_time = ""
        month_points = [equity]
        month_pnls = []
        month_rets = []
        reasons = Counter()
        coins = Counter()
        skipped_after_stop = 0
        skipped_daily = 0
        for trade in by_month.get(month, []):
            day = trade["exit_time"][:10]
            if stop_reason != "month_end":
                skipped_after_stop += 1
                continue
            if day in disabled_days:
                skipped_daily += 1
                continue
            daily_start.setdefault(day, equity)
            before = equity
            ret_pct = adjusted_return(trade, scenario) * weights[trade["coin"]] * portfolio["scale"]
            equity *= 1.0 + ret_pct / 100.0
            pnl = equity - before
            month_pnls.append(pnl)
            month_rets.append(ret_pct)
            all_pnls.append(pnl)
            month_points.append(equity)
            equity_points.append(equity)
            reasons[trade["reason"]] += 1
            coins[trade["coin"]] += 1
            if equity >= target_balance:
                stop_reason = "cash_target"
                stop_time = trade["exit_time"]
            elif equity <= loss_floor:
                stop_reason = "monthly_loss_stop"
                stop_time = trade["exit_time"]
            elif portfolio.get("daily_loss_stop_pct") is not None:
                if equity <= daily_start[day] * (1.0 - portfolio["daily_loss_stop_pct"]):
                    disabled_days.add(day)
        end_before = equity
        month_pnl = end_before - start
        withdrawal = max(0.0, equity - INITIAL_BALANCE)
        if withdrawal:
            equity = INITIAL_BALANCE
            equity_points.append(equity)
        monthly.append(
            {
                "portfolio": portfolio["label"],
                "scenario": scenario["name"],
                "month": month,
                "start_equity": start,
                "end_before_withdraw": end_before,
                "end_after_withdraw": equity,
                "month_pnl": month_pnl,
                "withdrawal": withdrawal,
                "hit_target": withdrawal >= portfolio["target_cash"],
                "stop_reason": stop_reason,
                "stop_time": stop_time,
                "trades": len(month_pnls),
                "skipped_after_stop": skipped_after_stop,
                "skipped_daily": skipped_daily,
                "month_max_drawdown_pct": max_drawdown(month_points),
                "win_rate_pct": sum(1 for p in month_pnls if p > 0) / len(month_pnls) * 100.0 if month_pnls else 0.0,
                "profit_factor": profit_factor(month_pnls),
                "expectancy_pct": sum(month_rets) / len(month_rets) if month_rets else 0.0,
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(8)),
            }
        )
    return {
        "monthly": monthly,
        "months": len(monthly),
        "cash_hits": sum(1 for r in monthly if r["hit_target"]),
        "positive_months": sum(1 for r in monthly if r["month_pnl"] > 0),
        "cash_withdrawn": sum(r["withdrawal"] for r in monthly),
        "final_balance": equity,
        "net_result": sum(r["withdrawal"] for r in monthly) + equity - INITIAL_BALANCE,
        "max_drawdown_pct": max_drawdown(equity_points),
        "max_month_drawdown_pct": max(r["month_max_drawdown_pct"] for r in monthly),
        "worst_month_pnl": min(r["month_pnl"] for r in monthly),
        "profit_factor": profit_factor(all_pnls),
        "trades": sum(r["trades"] for r in monthly),
    }


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    fields = sorted({k for row in rows for k in row})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_money(v):
    return f"${float(v):.2f}"


def fmt_pct(v):
    return f"{float(v):+.2f}%"


def write_report(path, summary_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Cashflow + ALICE / 1000SATS Portfolio Test",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`.",
        "",
        "Проверка: добавляют ли новые rescue-кандидаты `ALICE SHORT` и `1000SATS SHORT` пользу к текущим cashflow-портфелям.",
        "",
        "| Portfolio | Scenario | Cash Hits | Positive Months | Net | Max DD | Max Month DD | PF | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['portfolio']} | {row['scenario']} | {row['cash_hits']}/{row['months']} | "
            f"{row['positive_months']}/{row['months']} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pct(row['max_month_drawdown_pct'])} | "
            f"{float(row['profit_factor']):.2f} | {row['trades']} |"
        )
    lines.extend(
        [
            "",
            "## Вывод",
            "",
            "Если новая версия дает меньше cash hits или выше просадку, ALICE/1000SATS не добавляем в основной cashflow, даже если отдельно они выглядят красиво.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    args = parse_args()
    months = list(month_iter(args.start_month, args.end_month))
    existing = load_existing_trades(os.path.join(ROOT, args.existing_trades), args.start_month, args.end_month)
    new_trades = build_new_trades(args)
    new_trades = [t for t in new_trades if args.start_month <= t["exit_time"][:7] <= args.end_month]
    combined = existing + new_trades
    combined.sort(key=lambda t: (t["exit_time"], t["entry_time"], t["coin"]))

    scenarios = [
        {"name": "base", "fee_pct": 0.0002, "slippage_pct": 0.0},
        {"name": "stress_0.03_fee_0.005_slip", "fee_pct": 0.0003, "slippage_pct": 0.00005},
        {"name": "stress_0.04_fee_0.02_slip", "fee_pct": 0.0004, "slippage_pct": 0.0002},
    ]
    summary_rows = []
    monthly_rows = []
    for key, portfolio in PORTFOLIOS.items():
        for scenario in scenarios:
            result = simulate(combined, months, portfolio, scenario)
            summary_rows.append(
                {
                    "portfolio_key": key,
                    "portfolio": portfolio["label"],
                    "scenario": scenario["name"],
                    "months": result["months"],
                    "cash_hits": result["cash_hits"],
                    "positive_months": result["positive_months"],
                    "cash_withdrawn": result["cash_withdrawn"],
                    "final_balance": result["final_balance"],
                    "net_result": result["net_result"],
                    "max_drawdown_pct": result["max_drawdown_pct"],
                    "max_month_drawdown_pct": result["max_month_drawdown_pct"],
                    "worst_month_pnl": result["worst_month_pnl"],
                    "profit_factor": result["profit_factor"],
                    "trades": result["trades"],
                    "weights": repr(portfolio["weights"]),
                    "scale": portfolio["scale"],
                }
            )
            monthly_rows.extend(result["monthly"])

    save_csv(os.path.join(ROOT, args.save_new_trades), new_trades)
    save_csv(os.path.join(ROOT, args.save_combined_trades), combined)
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows)
    write_report(os.path.join(ROOT, args.save_report), summary_rows)
    print(f"new trades: {len(new_trades)}")
    print(f"combined trades: {len(combined)}")
    for row in summary_rows:
        print(
            f"{row['portfolio']} | {row['scenario']} | cash {row['cash_hits']}/{row['months']} "
            f"net {row['net_result']:.2f} maxDD {row['max_drawdown_pct']:.2f}% "
            f"maxMonthDD {row['max_month_drawdown_pct']:.2f}% PF {row['profit_factor']:.2f}"
        )
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
