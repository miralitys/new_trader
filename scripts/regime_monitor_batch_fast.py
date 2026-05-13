#!/usr/bin/env python3
"""Fast batch screen for RIF-like regime-monitor candidates.

This is a first-pass scan. It builds a rolling health gate from raw always-on
trades, then runs the strategy only on days where 30d/60d health is alive.
Promising symbols should be rechecked with the exact per-day health script.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
DEEP_PATH = os.path.join(ROOT, "scripts", "deep_validate_hot_shortlist.py")
INITIAL_BALANCE = 1000.0


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


def fmt_pct(value):
    if value is None or value == "":
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value is None or value == "":
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def utc_day_from_iso(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def utc_day_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def spec_from_row(row):
    return {
        "coin": row.get("coin") or row["symbol"].replace("USDT", ""),
        "symbol": row["symbol"],
        "kind": "single",
        "direction": row["direction"],
        "threshold": as_int(row, "threshold"),
        "regime": row["regime"],
        "position_pct": 1.0,
        "tp_pct": as_float(row, "tp_pct"),
        "sl_pct": as_float(row, "sl_pct", 0.04),
        "time_stop_min": as_int(row, "time_stop_min"),
    }


def make_args(multi, reinvest, cf, spec, weekly_loss_stop_pct=None):
    args = cf.make_single_args(multi, reinvest, spec)
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0005
    args.limit_entry_timeout_min = 1
    args.fee_pct = 0.0002
    args.slippage_pct = 0.0
    args.daily_loss_stop_pct = 0.02
    if weekly_loss_stop_pct is not None:
        args.weekly_loss_stop_pct = weekly_loss_stop_pct
    elif hasattr(args, "weekly_loss_stop_pct"):
        args.weekly_loss_stop_pct = None
    return args


def compounded_return(returns):
    equity = 1.0
    for value in returns:
        equity *= 1.0 + value / 100.0
    return (equity - 1.0) * 100.0


def sequence_dd(returns):
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for value in returns:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100.0 if peak else 0.0)
    return max_dd


def trade_health(trades, end_day, lookback_days):
    start_day = end_day - timedelta(days=lookback_days)
    selected = [
        trade
        for trade in trades
        if start_day <= utc_day_from_iso(trade["exit_time"]) < end_day
    ]
    returns = [float(trade["net_return_pct"]) for trade in selected]
    wins = [ret for ret in returns if ret > 0]
    losses = [ret for ret in returns if ret < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    pf = gross_profit / gross_loss if gross_loss else (math.inf if gross_profit > 0 else 0.0)
    return {
        "return_pct": compounded_return(returns),
        "profit_factor": pf,
        "max_dd_pct": sequence_dd(returns),
        "trades": len(returns),
    }


def pass_health(day, trades):
    h30 = trade_health(trades, day, 30)
    h60 = trade_health(trades, day, 60)
    passed = (
        h30["return_pct"] > 0
        and h30["profit_factor"] >= 1.10
        and h30["max_dd_pct"] <= 15.0
        and h30["trades"] >= 20
        and h60["return_pct"] > 0
        and h60["profit_factor"] >= 1.05
        and h60["max_dd_pct"] <= 20.0
        and h60["trades"] >= 40
    )
    return passed, h30, h60


def daily_start_indices(candles):
    starts = []
    previous = None
    for index, row in enumerate(candles):
        day = utc_day_from_ms(row["open_time_ms"])
        if day != previous:
            starts.append((day, index))
            previous = day
    return starts


def gate_rows(cf, rows, spec, active_days):
    gated = [dict(row) for row in rows]
    cf.apply_single_signals(gated, spec["direction"], spec["threshold"], spec["regime"])
    active = set(active_days)
    for row in gated:
        if utc_day_from_ms(row["open_time_ms"]) not in active:
            row["long_signal"] = False
            row["short_signal"] = False
    return gated


def run_strategy(bt, multi, reinvest, cf, rows, spec, weekly_loss_stop_pct=None):
    test = [dict(row) for row in rows]
    cf.apply_single_signals(test, spec["direction"], spec["threshold"], spec["regime"])
    args = make_args(multi, reinvest, cf, spec, weekly_loss_stop_pct)
    trades, equity, stats = bt.run_backtest(test, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return trades, summary, stats


def run_gated(bt, multi, reinvest, cf, rows, spec, active_days, weekly_loss_stop_pct=None):
    test = gate_rows(cf, rows, spec, active_days)
    args = make_args(multi, reinvest, cf, spec, weekly_loss_stop_pct)
    trades, equity, stats = bt.run_backtest(test, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return summary, stats


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ranked = sorted(rows, key=lambda row: (float(row["gated_730_return_pct"]), -float(row["gated_730_dd_pct"])), reverse=True)
    lines = [
        "# Regime Monitor Batch Fast",
        "",
        "Быстрый первичный поиск монет, похожих на RIF: always-on может быть плохим, но rolling 30/60d health включает только рабочие дни.",
        "",
        "Важно: это быстрый screen по rolling trade-health. Кандидатов надо потом добивать точным per-day health script.",
        "",
        "| Symbol | Direction | Always 730 | Always DD | Gated 730 | Gated DD | Gated PF | Active Days | Weekly Kill 730 | Weekly DD | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in ranked:
        lines.append(
            f"| `{row['symbol']}` | {row['direction']} | {fmt_pct(row['always_730_return_pct'])} | "
            f"{fmt_num(row['always_730_dd_pct'])}% | {fmt_pct(row['gated_730_return_pct'])} | "
            f"{fmt_num(row['gated_730_dd_pct'])}% | {fmt_num(row['gated_730_pf'])} | "
            f"{row['active_days_730']} | {fmt_pct(row['gated_weekly_730_return_pct'])} | "
            f"{fmt_num(row['gated_weekly_730_dd_pct'])}% | {row['decision']} |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Fast batch regime-monitor screen.")
    parser.add_argument("--input", default="data/hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv")
    parser.add_argument("--deep-metrics", default="data/deep_hot_shortlist_metrics_2026-05-04.csv")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--save-summary", default="data/regime_monitor_batch_fast_2026-05-04.csv")
    parser.add_argument("--save-report", default="strategies/regime-monitor-batch-fast-2026-05-04.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    deep = load_module("deep_validate_hot_shortlist", DEEP_PATH)

    if args.archive_end_day:
        fixed_end_day = date.fromisoformat(args.archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    shortlist = {row["symbol"]: row for row in read_csv(os.path.join(ROOT, args.input))}
    deep_rows = read_csv(os.path.join(ROOT, args.deep_metrics))
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = sorted(
            {
                row["symbol"]
                for row in deep_rows
                if row["scenario"] == "strict_maker"
                and row["period_days"] == "730"
                and row["valid"] == "True"
                and row["symbol"] in shortlist
            }
        )

    first_days = deep.load_inventory_first_days(os.path.join(ROOT, args.inventory))
    output = []
    for index, symbol in enumerate(symbols, start=1):
        spec = spec_from_row(shortlist[symbol])
        print(f"[{index}/{len(symbols)}] {symbol}", flush=True)
        candles, _, _ = deep.fetch_klines_bounded(multi, symbol, 820, 0, first_days.get(symbol))
        if len(candles) < 730 * 1440:
            print(f"  skip: not enough candles {len(candles)}", flush=True)
            continue
        base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
        bt.add_indicators_and_signals(candles, base_args)

        rows730 = [dict(row) for row in candles[-730 * 1440 :]]
        rows365 = [dict(row) for row in candles[-365 * 1440 :]]
        raw_trades, always730, _ = run_strategy(bt, multi, reinvest, cf, rows730, spec)
        _, always365, _ = run_strategy(bt, multi, reinvest, cf, rows365, spec)

        active_by_day = defaultdict(bool)
        starts = daily_start_indices(rows730)
        for day, _idx in starts:
            passed, _h30, _h60 = pass_health(day, raw_trades)
            active_by_day[day] = passed
        active_days = [day for day, passed in active_by_day.items() if passed]

        gated730, _ = run_gated(bt, multi, reinvest, cf, rows730, spec, active_days)
        gated730_weekly, _ = run_gated(bt, multi, reinvest, cf, rows730, spec, active_days, weekly_loss_stop_pct=0.02)

        active365 = [day for day in active_days if day >= utc_day_from_ms(rows365[0]["open_time_ms"])]
        gated365, _ = run_gated(bt, multi, reinvest, cf, rows365, spec, active365)
        gated365_weekly, _ = run_gated(bt, multi, reinvest, cf, rows365, spec, active365, weekly_loss_stop_pct=0.02)

        decision = "reject"
        if gated730["total_return_pct"] > 0 and gated730["profit_factor"] >= 1.10 and gated730["max_drawdown_pct"] <= 25:
            decision = "regime_candidate"
        if gated730_weekly["total_return_pct"] > 0 and gated730_weekly["profit_factor"] >= 1.20 and gated730_weekly["max_drawdown_pct"] <= 15:
            decision = "regime_candidate_defensive"

        row = {
            "symbol": symbol,
            "direction": spec["direction"],
            "threshold": spec["threshold"],
            "regime": spec["regime"],
            "tp_pct": spec["tp_pct"],
            "sl_pct": spec["sl_pct"],
            "time_stop_min": spec["time_stop_min"],
            "always_365_return_pct": always365["total_return_pct"],
            "always_365_dd_pct": always365["max_drawdown_pct"],
            "always_365_pf": always365["profit_factor"],
            "always_730_return_pct": always730["total_return_pct"],
            "always_730_dd_pct": always730["max_drawdown_pct"],
            "always_730_pf": always730["profit_factor"],
            "active_days_365": len(active365),
            "active_days_730": len(active_days),
            "gated_365_return_pct": gated365["total_return_pct"],
            "gated_365_dd_pct": gated365["max_drawdown_pct"],
            "gated_365_pf": gated365["profit_factor"],
            "gated_730_return_pct": gated730["total_return_pct"],
            "gated_730_dd_pct": gated730["max_drawdown_pct"],
            "gated_730_pf": gated730["profit_factor"],
            "gated_weekly_365_return_pct": gated365_weekly["total_return_pct"],
            "gated_weekly_365_dd_pct": gated365_weekly["max_drawdown_pct"],
            "gated_weekly_365_pf": gated365_weekly["profit_factor"],
            "gated_weekly_730_return_pct": gated730_weekly["total_return_pct"],
            "gated_weekly_730_dd_pct": gated730_weekly["max_drawdown_pct"],
            "gated_weekly_730_pf": gated730_weekly["profit_factor"],
            "decision": decision,
        }
        output.append(row)
        print(
            f"  always730={always730['total_return_pct']:+.2f}% "
            f"gated730={gated730['total_return_pct']:+.2f}% "
            f"weekly730={gated730_weekly['total_return_pct']:+.2f}% {decision}",
            flush=True,
        )

    fields = [
        "symbol",
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "always_365_return_pct",
        "always_365_dd_pct",
        "always_365_pf",
        "always_730_return_pct",
        "always_730_dd_pct",
        "always_730_pf",
        "active_days_365",
        "active_days_730",
        "gated_365_return_pct",
        "gated_365_dd_pct",
        "gated_365_pf",
        "gated_730_return_pct",
        "gated_730_dd_pct",
        "gated_730_pf",
        "gated_weekly_365_return_pct",
        "gated_weekly_365_dd_pct",
        "gated_weekly_365_pf",
        "gated_weekly_730_return_pct",
        "gated_weekly_730_dd_pct",
        "gated_weekly_730_pf",
        "decision",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), output, fields)
    save_report(os.path.join(ROOT, args.save_report), output)
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
