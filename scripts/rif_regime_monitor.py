#!/usr/bin/env python3
"""RIF regime monitor backtest.

RIF looked good on the most recent 365d window but failed 730d. This script
tests a regime-monitor approach: each UTC day the bot looks only backward at
RIF's own rolling 30/60/90d health and decides whether the next day is allowed
to trade.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import date, datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
DEEP_PATH = os.path.join(ROOT, "scripts", "deep_validate_hot_shortlist.py")
INITIAL_BALANCE = 1000.0


POLICIES = [
    {
        "policy": "always_on_base",
        "gate": "always",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "always_on_best_kill",
        "gate": "always",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.005,
        "weekly_loss_stop_pct": 0.02,
    },
    {
        "policy": "health30_loose",
        "gate": "health30_loose",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_strict",
        "gate": "health30_strict",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60",
        "gate": "health30_60",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60_weekly_kill",
        "gate": "health30_60",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": 0.02,
    },
    {
        "policy": "health30_60_90",
        "gate": "health30_60_90",
        "position_pct": 1.0,
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row, key, default=0.0):
    try:
        value = row.get(key, default)
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(row, key, default=0):
    try:
        value = row.get(key, default)
        if value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def utc_day_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def fmt_pct(value):
    if value is None or value == "":
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value is None or value == "":
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def spec_from_shortlist(path, symbol):
    for row in read_csv(path):
        if row["symbol"] != symbol:
            continue
        return {
            "coin": row.get("coin") or symbol.replace("USDT", ""),
            "symbol": symbol,
            "kind": "single",
            "direction": row["direction"],
            "threshold": as_int(row, "threshold"),
            "regime": row["regime"],
            "position_pct": 1.0,
            "tp_pct": as_float(row, "tp_pct"),
            "sl_pct": as_float(row, "sl_pct", 0.04),
            "time_stop_min": as_int(row, "time_stop_min"),
        }
    raise RuntimeError(f"{symbol} not found in {path}")


def make_args(multi, reinvest, cf, spec, position_pct, daily_loss_stop_pct, weekly_loss_stop_pct):
    local_spec = dict(spec)
    local_spec["position_pct"] = position_pct
    args = cf.make_single_args(multi, reinvest, local_spec)
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0005
    args.limit_entry_timeout_min = 1
    args.fee_pct = 0.0002
    args.slippage_pct = 0.0
    args.daily_loss_stop_pct = daily_loss_stop_pct
    if weekly_loss_stop_pct is not None:
        args.weekly_loss_stop_pct = weekly_loss_stop_pct
    elif hasattr(args, "weekly_loss_stop_pct"):
        args.weekly_loss_stop_pct = None
    return args


def run_rows(bt, multi, reinvest, cf, rows, spec, position_pct=1.0, daily_loss_stop_pct=0.02, weekly_loss_stop_pct=None):
    test_rows = [dict(row) for row in rows]
    cf.apply_single_signals(test_rows, spec["direction"], spec["threshold"], spec["regime"])
    args = make_args(multi, reinvest, cf, spec, position_pct, daily_loss_stop_pct, weekly_loss_stop_pct)
    trades, equity, stats = bt.run_backtest(test_rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return summary, stats


def daily_start_indices(candles):
    starts = []
    previous_day = None
    for index, row in enumerate(candles):
        day = utc_day_from_ms(row["open_time_ms"])
        if day != previous_day:
            starts.append((day, index))
            previous_day = day
    return starts


def compute_health_cache(bt, multi, reinvest, cf, candles, spec, starts, target_start, health_windows):
    cache = {}
    for number, (day, index) in enumerate(starts, start=1):
        if index < target_start:
            continue
        cache[day] = {}
        for window in health_windows:
            bars = window * 1440
            if index < bars:
                continue
            rows = candles[index - bars : index]
            summary, _ = run_rows(bt, multi, reinvest, cf, rows, spec)
            cache[day][window] = {
                "return_pct": summary["total_return_pct"],
                "profit_factor": summary["profit_factor"],
                "max_dd_pct": summary["max_drawdown_pct"],
                "trades": summary["total_trades"],
            }
        if number % 50 == 0:
            print(f"  health days computed through {day}", flush=True)
    return cache


def passes_gate(gate, health):
    if gate == "always":
        return True, "always_on"
    h30 = health.get(30)
    h60 = health.get(60)
    h90 = health.get(90)

    def ok(row, min_return, min_pf, max_dd, min_trades):
        return (
            row is not None
            and row["return_pct"] > min_return
            and row["profit_factor"] >= min_pf
            and row["max_dd_pct"] <= max_dd
            and row["trades"] >= min_trades
        )

    if gate == "health30_loose":
        passed = ok(h30, 0.0, 1.05, 20.0, 20)
        return passed, "30d ret>0 pf>=1.05 dd<=20 trades>=20"
    if gate == "health30_strict":
        passed = ok(h30, 5.0, 1.15, 15.0, 20)
        return passed, "30d ret>5 pf>=1.15 dd<=15 trades>=20"
    if gate == "health30_60":
        passed = ok(h30, 0.0, 1.10, 15.0, 20) and ok(h60, 0.0, 1.05, 20.0, 40)
        return passed, "30d+60d health"
    if gate == "health30_60_90":
        passed = (
            ok(h30, 0.0, 1.10, 15.0, 20)
            and ok(h60, 0.0, 1.05, 20.0, 40)
            and ok(h90, 0.0, 1.03, 25.0, 60)
        )
        return passed, "30d+60d+90d health"
    raise ValueError(gate)


def gate_target_rows(cf, candles, spec, target_start, target_end, starts, active_days):
    rows = [dict(row) for row in candles[target_start:target_end]]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    active = set(active_days)
    for row in rows:
        if utc_day_from_ms(row["open_time_ms"]) not in active:
            row["long_signal"] = False
            row["short_signal"] = False
    return rows


def run_policy(bt, multi, reinvest, cf, candles, spec, days, policy, health_cache):
    target_bars = days * 1440
    target_start = len(candles) - target_bars
    target_end = len(candles)
    starts = [(day, index) for day, index in daily_start_indices(candles) if target_start <= index < target_end]

    active_days = []
    gate_reasons = Counter()
    for day, _index in starts:
        passed, reason = passes_gate(policy["gate"], health_cache.get(day, {}))
        gate_reasons[reason if passed else f"blocked:{reason}"] += 1
        if passed:
            active_days.append(day)

    rows = gate_target_rows(cf, candles, spec, target_start, target_end, starts, active_days)
    args = make_args(
        multi,
        reinvest,
        cf,
        spec,
        policy["position_pct"],
        policy["daily_loss_stop_pct"],
        policy["weekly_loss_stop_pct"],
    )
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return {
        "symbol": spec["symbol"],
        "policy": policy["policy"],
        "gate": policy["gate"],
        "period_days": days,
        "active_days": len(active_days),
        "inactive_days": len(starts) - len(active_days),
        "active_ratio_pct": len(active_days) / len(starts) * 100.0 if starts else 0.0,
        "position_pct": policy["position_pct"],
        "daily_loss_stop_pct": policy["daily_loss_stop_pct"],
        "weekly_loss_stop_pct": policy["weekly_loss_stop_pct"] if policy["weekly_loss_stop_pct"] is not None else "",
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "profit_factor": summary["profit_factor"],
        "win_rate_pct": summary["win_rate_pct"],
        "expectancy_pct": summary["expectancy_pct"],
        "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
        "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
        "gate_reasons": ";".join(f"{key}={value}" for key, value in gate_reasons.items()),
    }


def save_report(path, rows, symbol):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# {symbol} Regime Monitor",
        "",
        f"Проверка идеи: {symbol} не торгуется постоянно. Каждый день бот смотрит только назад на rolling 30/60/90d health и решает, включать ли следующий день.",
        "",
        "## Results",
        "",
        "| Policy | Period | Active Days | Return | MaxDD | PF | Win | Trades | Daily/Weekly Stops |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: (int(item["period_days"]), -float(item["return_pct"]))):
        lines.append(
            f"| {row['policy']} | {row['period_days']} | {row['active_days']} / "
            f"{row['active_days'] + row['inactive_days']} ({float(row['active_ratio_pct']):.1f}%) | "
            f"{fmt_pct(row['return_pct'])} | {fmt_num(row['max_dd_pct'])}% | {fmt_num(row['profit_factor'])} | "
            f"{fmt_num(row['win_rate_pct'])}% | {row['trades']} | "
            f"{row['daily_loss_stop_events']}/{row['weekly_loss_stop_events']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Если 730d остается около нуля или минусовым, {symbol} не превращается в core даже с regime monitor.",
            f"- Если 365d хороший, но 730d плохой, {symbol} можно оставить только как watchlist/regime idea.",
            "- Health-gate считается только по прошлым данным, без подглядывания в будущее.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run RIF regime monitor.")
    parser.add_argument("--symbol", default="RIFUSDT")
    parser.add_argument("--input", default="data/hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--periods", nargs="*", type=int, default=[365, 730])
    parser.add_argument("--max-health-window", type=int, default=90)
    parser.add_argument("--save-summary", default="data/rif_regime_monitor_summary_2026-05-04.csv")
    parser.add_argument("--save-report", default="strategies/rif-regime-monitor-2026-05-04.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    deep = load_module("deep_validate_hot_shortlist", DEEP_PATH)

    if args.archive_end_day:
        fixed_end_day = date.fromisoformat(args.archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    spec = spec_from_shortlist(os.path.join(ROOT, args.input), args.symbol)
    first_days = deep.load_inventory_first_days(os.path.join(ROOT, args.inventory))
    max_period = max(args.periods)
    fetch_days = max_period + args.max_health_window
    candles, _, _ = deep.fetch_klines_bounded(multi, args.symbol, fetch_days, 0, first_days.get(args.symbol))
    if len(candles) < max_period * 1440:
        raise RuntimeError(f"not enough candles: {len(candles)}")

    base_args = multi.make_strategy_args(reinvest, "7.3", args.symbol)
    bt.add_indicators_and_signals(candles, base_args)
    print(f"candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}", flush=True)

    target_start = len(candles) - max_period * 1440
    starts = daily_start_indices(candles)
    print("computing rolling health cache...", flush=True)
    health_cache = compute_health_cache(bt, multi, reinvest, cf, candles, spec, starts, target_start, [30, 60, 90])

    rows = []
    for period in args.periods:
        print(f"period {period}d", flush=True)
        for policy in POLICIES:
            result = run_policy(bt, multi, reinvest, cf, candles, spec, period, policy, health_cache)
            rows.append(result)
            print(
                f"  {policy['policy']}: ret={result['return_pct']:+.2f}% "
                f"dd={result['max_dd_pct']:.2f}% pf={result['profit_factor']:.3f} "
                f"active={result['active_days']}",
                flush=True,
            )

    fields = [
        "symbol",
        "policy",
        "gate",
        "period_days",
        "active_days",
        "inactive_days",
        "active_ratio_pct",
        "position_pct",
        "daily_loss_stop_pct",
        "weekly_loss_stop_pct",
        "trades",
        "return_pct",
        "max_dd_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
        "gate_reasons",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields)
    save_report(os.path.join(ROOT, args.save_report), rows, args.symbol)
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
