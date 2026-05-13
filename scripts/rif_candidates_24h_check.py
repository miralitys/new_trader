#!/usr/bin/env python3
"""Fresh 24h check for RIF-like regime candidates.

Binance Futures API can be geo-blocked from this environment, so this script
defaults to Binance data-api spot candles. It keeps the fixed RIF setup:

LONG th50 wide, TP 1.2%, SL 4%, time-stop 90m, maker fee 0.02%,
strict maker limit offset 0.05%, 1 minute fill timeout.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")

INITIAL_BALANCE = 1000.0
DEFAULT_SYMBOLS = ["RIFUSDT", "ENAUSDT", "MOVRUSDT", "UMAUSDT", "COMPUSDT", "CVCUSDT", "1000XECUSDT"]

FIXED_SPEC = {
    "coin": "",
    "symbol": "",
    "kind": "single",
    "direction": "long",
    "threshold": 50,
    "regime": "wide",
    "position_pct": 1.0,
    "tp_pct": 0.012,
    "sl_pct": 0.04,
    "time_stop_min": 90,
}

POLICIES = [
    {
        "policy": "raw_always_on",
        "gate": "always",
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60",
        "gate": "health30_60",
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": None,
    },
    {
        "policy": "health30_60_weekly_kill",
        "gate": "health30_60",
        "daily_loss_stop_pct": 0.02,
        "weekly_loss_stop_pct": 0.02,
    },
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    return f"{float(value):+.2f}%"


def fmt_num(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def coin_from_symbol(symbol):
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def data_symbol_for(symbol):
    if symbol == "1000XECUSDT":
        return "XECUSDT", "spot proxy for 1000XECUSDT; Binance data-api spot has XECUSDT, not 1000XECUSDT"
    return symbol, ""


def fixed_spec(symbol):
    spec = dict(FIXED_SPEC)
    spec["symbol"] = symbol
    spec["coin"] = coin_from_symbol(symbol)
    return spec


def utc_day_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def add_indicators(bt, reinvest, multi, candles, symbol):
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)


def health_start_for_target(rif, candles, target_rows):
    starts = rif.daily_start_indices(candles)
    start_by_day = {day: index for day, index in starts}
    target_days = sorted({utc_day_from_ms(row["open_time_ms"]) for row in target_rows})
    indices = [start_by_day[day] for day in target_days if day in start_by_day]
    return min(indices) if indices else len(candles) - len(target_rows), starts, target_days


def active_days_for_policy(rif, policy, health_cache, target_days):
    active_days = []
    gate_reasons = Counter()
    for day in target_days:
        passed, reason = rif.passes_gate(policy["gate"], health_cache.get(day, {}))
        gate_reasons[reason if passed else f"blocked:{reason}"] += 1
        if passed:
            active_days.append(day)
    return active_days, gate_reasons


def gated_rows(cf, target_rows, spec, active_days):
    rows = [dict(row) for row in target_rows]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    active = set(active_days)
    for row in rows:
        if utc_day_from_ms(row["open_time_ms"]) not in active:
            row["long_signal"] = False
            row["short_signal"] = False
    return rows


def args_for_policy(rif, multi, reinvest, cf, spec, policy):
    return rif.make_args(
        multi,
        reinvest,
        cf,
        spec,
        position_pct=1.0,
        daily_loss_stop_pct=policy["daily_loss_stop_pct"],
        weekly_loss_stop_pct=policy["weekly_loss_stop_pct"],
    )


def summarize_journal(rows):
    signals = len(rows)
    filled = [row for row in rows if row["order_status"] == "filled"]
    unfilled = [row for row in rows if row["order_status"] == "unfilled"]
    accepted = [row for row in filled if row["portfolio_status"] in {"candidate", "accepted"}]
    returns = [float(row["portfolio_return_pct"] or row["net_return_pct"] or 0.0) for row in accepted]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    return {
        "signals": signals,
        "filled": len(filled),
        "unfilled": len(unfilled),
        "accepted": len(accepted),
        "fill_rate_pct": len(filled) / signals * 100.0 if signals else 0.0,
        "accepted_return_sum_pct": sum(returns),
        "accepted_profit_factor": gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0),
        "exit_reasons": ";".join(f"{key}={value}" for key, value in Counter(row["reason"] for row in accepted).most_common()),
    }


def run_symbol(bt, reinvest, multi, cf, rif, paper, symbol, args):
    data_symbol, note = data_symbol_for(symbol)
    total_days = args.days + args.health_days + args.warmup_days
    candles = bt.fetch_klines(args.market, data_symbol, total_days, "1m")
    if len(candles) < args.days * 1440:
        raise RuntimeError(f"not enough candles: {len(candles)}")
    add_indicators(bt, reinvest, multi, candles, data_symbol)

    target_bars = args.days * 1440
    target_rows = candles[-target_bars:]
    target_start_index = len(candles) - target_bars
    health_start, starts, target_days = health_start_for_target(rif, candles, target_rows)
    spec = fixed_spec(symbol)
    health_cache = rif.compute_health_cache(
        bt,
        multi,
        reinvest,
        cf,
        candles,
        spec,
        starts,
        health_start,
        [30, 60, 90],
    )

    summary_rows = []
    journal_rows = []
    for policy in POLICIES:
        if policy["gate"] == "always":
            active_days = target_days
            gate_reasons = Counter({"always_on": len(target_days)})
        else:
            active_days, gate_reasons = active_days_for_policy(rif, policy, health_cache, target_days)
        rows = gated_rows(cf, target_rows, spec, active_days)
        bt_args = args_for_policy(rif, multi, reinvest, cf, spec, policy)
        trades, equity, stats = bt.run_backtest(rows, bt_args)
        metrics = bt.summarize_trades(trades, INITIAL_BALANCE, equity)

        paper_rows = paper.journal_loop(
            bt,
            rows,
            bt_args,
            {
                "asset": coin_from_symbol(symbol),
                "symbol": symbol,
                "strategy": "RIF-like 24h",
                "module": policy["policy"],
            },
        )
        for row in paper_rows:
            row["data_symbol"] = data_symbol
            row["market"] = args.market
        journal_summary = summarize_journal(paper_rows)
        journal_rows.extend(paper_rows)
        reasons = metrics.get("exit_reasons", {})
        summary_rows.append(
            {
                "symbol": symbol,
                "data_symbol": data_symbol,
                "market": args.market,
                "policy": policy["policy"],
                "window_start": target_rows[0]["open_time"],
                "window_end": target_rows[-1]["close_time"],
                "target_start_index": target_start_index,
                "target_days_utc": ";".join(day.isoformat() for day in target_days),
                "active_days": len(active_days),
                "inactive_days": len(target_days) - len(active_days),
                "signals": journal_summary["signals"],
                "filled": journal_summary["filled"],
                "unfilled": journal_summary["unfilled"],
                "fill_rate_pct": journal_summary["fill_rate_pct"],
                "trades": metrics["total_trades"],
                "return_pct": metrics["total_return_pct"],
                "max_dd_pct": metrics["max_drawdown_pct"],
                "win_rate_pct": metrics["win_rate_pct"],
                "profit_factor": metrics["profit_factor"],
                "expectancy_pct": metrics["expectancy_pct"],
                "final_equity": metrics["final_equity"],
                "take_profit": reasons.get("take_profit", 0),
                "stop_loss": reasons.get("stop_loss", 0),
                "time_stop": reasons.get("time_stop", 0),
                "end_of_data": reasons.get("end_of_data", 0),
                "daily_loss_stop_events": stats.get("daily_loss_stop_events", 0),
                "weekly_loss_stop_events": stats.get("weekly_loss_stop_events", 0),
                "paper_return_sum_pct": journal_summary["accepted_return_sum_pct"],
                "paper_profit_factor": journal_summary["accepted_profit_factor"],
                "paper_exit_reasons": journal_summary["exit_reasons"],
                "gate_reasons": ";".join(f"{key}={value}" for key, value in gate_reasons.items()),
                "note": note,
                "error": "",
            }
        )
    return summary_rows, journal_rows


def write_report(path, summary_rows, summary_path, journal_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    health_rows = [row for row in summary_rows if row["policy"] == "health30_60"]
    defensive_rows = [row for row in summary_rows if row["policy"] == "health30_60_weekly_kill"]
    raw_rows = [row for row in summary_rows if row["policy"] == "raw_always_on"]

    def line_for(row):
        return (
            f"| `{row['symbol']}` | {row['policy']} | {row['active_days']}/{row['active_days'] + row['inactive_days']} | "
            f"{row['signals']} | {row['filled']} | {row['trades']} | {fmt_pct(row['return_pct'])} | "
            f"{fmt_num(row['max_dd_pct'])}% | {fmt_num(row['profit_factor'])} | "
            f"{fmt_pct(row['expectancy_pct'])} | {row['paper_exit_reasons']} |"
        )

    lines = [
        "# RIF-like Candidates 24h Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker offset `0.05%`, maker fee `0.02%`, slippage `0`.",
        "",
        "Источник: свежие Binance `data_api_spot` свечи. `1000XECUSDT` посчитан через `XECUSDT` как spot-proxy, потому что spot data-api не имеет `1000XECUSDT`.",
        "",
        "## Main: Health 30/60",
        "",
        "| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    lines.extend(line_for(row) for row in health_rows)
    lines.extend(
        [
            "",
            "## Defensive: Health 30/60 + Weekly Kill",
            "",
            "| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    lines.extend(line_for(row) for row in defensive_rows)
    lines.extend(
        [
            "",
            "## Raw Always-On Reference",
            "",
            "| Symbol | Policy | Active Days | Signals | Filled | Trades | Return | MaxDD | PF | Expectancy | Exit Reasons |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    lines.extend(line_for(row) for row in raw_rows)
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
            f"- Journal CSV: `{journal_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Run fresh 24h check for RIF-like candidates.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--market", default="data_api_spot", choices=["data_api_spot", "spot_global", "spot_us", "futures_global"])
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--health-days", type=int, default=60)
    parser.add_argument("--warmup-days", type=int, default=8)
    parser.add_argument("--save-summary", default=f"data/rif_candidates_24h_summary_{today}.csv")
    parser.add_argument("--save-journal", default=f"data/rif_candidates_24h_journal_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-candidates-24h-check-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)

    all_summary = []
    all_journal = []
    for symbol in args.symbols:
        print(f"running {symbol}", flush=True)
        try:
            summary_rows, journal_rows = run_symbol(bt, reinvest, multi, cf, rif, paper, symbol, args)
            all_summary.extend(summary_rows)
            all_journal.extend(journal_rows)
        except Exception as exc:
            all_summary.append(
                {
                    "symbol": symbol,
                    "data_symbol": data_symbol_for(symbol)[0],
                    "market": args.market,
                    "policy": "error",
                    "window_start": "",
                    "window_end": "",
                    "target_start_index": "",
                    "target_days_utc": "",
                    "active_days": 0,
                    "inactive_days": 0,
                    "signals": 0,
                    "filled": 0,
                    "unfilled": 0,
                    "fill_rate_pct": 0,
                    "trades": 0,
                    "return_pct": 0,
                    "max_dd_pct": 0,
                    "win_rate_pct": 0,
                    "profit_factor": 0,
                    "expectancy_pct": 0,
                    "final_equity": INITIAL_BALANCE,
                    "take_profit": 0,
                    "stop_loss": 0,
                    "time_stop": 0,
                    "end_of_data": 0,
                    "daily_loss_stop_events": 0,
                    "weekly_loss_stop_events": 0,
                    "paper_return_sum_pct": 0,
                    "paper_profit_factor": 0,
                    "paper_exit_reasons": "",
                    "gate_reasons": "",
                    "note": "",
                    "error": str(exc),
                }
            )
            print(f"ERROR {symbol}: {exc}", flush=True)

    summary_fields = [
        "symbol",
        "data_symbol",
        "market",
        "policy",
        "window_start",
        "window_end",
        "target_start_index",
        "target_days_utc",
        "active_days",
        "inactive_days",
        "signals",
        "filled",
        "unfilled",
        "fill_rate_pct",
        "trades",
        "return_pct",
        "max_dd_pct",
        "win_rate_pct",
        "profit_factor",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
        "end_of_data",
        "daily_loss_stop_events",
        "weekly_loss_stop_events",
        "paper_return_sum_pct",
        "paper_profit_factor",
        "paper_exit_reasons",
        "gate_reasons",
        "note",
        "error",
    ]
    journal_fields = [
        "asset",
        "symbol",
        "data_symbol",
        "market",
        "strategy",
        "module",
        "portfolio_status",
        "attempt_number",
        "direction",
        "entry_mode",
        "fee_pct",
        "slippage_pct",
        "limit_entry_offset_pct",
        "limit_entry_timeout_min",
        "signal_idx",
        "signal_time",
        "signal_close",
        "order_start_time",
        "order_open",
        "limit_price",
        "order_status",
        "fill_time",
        "fill_delay_min",
        "entry",
        "tp_level",
        "sl_level",
        "exit_time",
        "exit",
        "reason",
        "duration_min",
        "net_return_pct",
        "portfolio_return_pct",
        "pnl",
        "equity_after",
        "waited_until_time",
        "long_score",
        "short_score",
        "atr_pct",
        "return_7d",
        "dist_ema200",
        "portfolio_weight",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), all_summary, summary_fields)
    save_csv(os.path.join(ROOT, args.save_journal), all_journal, journal_fields)
    write_report(args.save_report, all_summary, args.save_summary, args.save_journal)
    print(f"saved summary: {args.save_summary}")
    print(f"saved journal: {args.save_journal}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
