#!/usr/bin/env python3
"""Deep exact validation for all RIF-like regime candidates.

Input comes from `rif_regime_scan_all_binance.py`. For every
`regime_candidate*` symbol, this script re-runs the exact per-day rolling
health logic from `rif_regime_monitor.py` with the fixed RIF setup:

LONG th50 wide, TP 1.2%, SL 4%, time-stop 90m, strict maker entry.

This is intentionally slow. It is the expensive validation layer after the
fast all-Binance scan.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import defaultdict
from datetime import date, datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
DEEP_PATH = os.path.join(ROOT, "scripts", "deep_validate_hot_shortlist.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")


RIF_FIXED_SPEC = {
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


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def coin_from_symbol(symbol):
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def load_candidates(path, symbols, limit):
    rows = read_csv(path)
    selected = [
        row
        for row in rows
        if row.get("decision") in {"regime_candidate", "regime_candidate_defensive"}
    ]
    if symbols:
        wanted = set(symbols)
        selected = [row for row in selected if row["symbol"] in wanted]
    selected.sort(key=lambda row: row["symbol"])
    if limit > 0:
        selected = selected[:limit]
    return selected


def fixed_spec(symbol):
    spec = dict(RIF_FIXED_SPEC)
    spec["symbol"] = symbol
    spec["coin"] = coin_from_symbol(symbol)
    return spec


def row_key(row):
    return (row["symbol"], row["period_days"], row["policy"])


def existing_keys(path):
    if not path or not os.path.exists(path):
        return set()
    return {row_key(row) for row in read_csv(path)}


def summarize_symbol(rows):
    by = {(int(row["period_days"]), row["policy"]): row for row in rows}
    h730 = by.get((730, "health30_60"))
    w730 = by.get((730, "health30_60_weekly_kill"))
    h365 = by.get((365, "health30_60"))
    w365 = by.get((365, "health30_60_weekly_kill"))

    def f(row, key, default=""):
        return row.get(key, default) if row else default

    verdict = "reject"
    reason = []
    if w730 and float(w730["return_pct"]) > 0 and float(w730["profit_factor"]) >= 1.20 and float(w730["max_dd_pct"]) <= 15.0 and int(w730["trades"]) >= 40:
        verdict = "defensive_candidate"
    if h730 and float(h730["return_pct"]) > 0 and float(h730["profit_factor"]) >= 1.10 and float(h730["max_dd_pct"]) <= 25.0 and int(h730["trades"]) >= 40:
        verdict = "candidate" if verdict == "reject" else "candidate_plus_defensive"
    if h365 and float(h365["return_pct"]) <= 0:
        reason.append("365d health30_60 <= 0")
    if h730 and float(h730["return_pct"]) <= 0:
        reason.append("730d health30_60 <= 0")
    if w730 and float(w730["return_pct"]) <= 0:
        reason.append("730d weekly <= 0")
    return {
        "symbol": rows[0]["symbol"],
        "verdict": verdict,
        "reason": "; ".join(reason),
        "h365_return_pct": f(h365, "return_pct"),
        "h365_dd_pct": f(h365, "max_dd_pct"),
        "h365_pf": f(h365, "profit_factor"),
        "h365_trades": f(h365, "trades"),
        "h365_active_days": f(h365, "active_days"),
        "w365_return_pct": f(w365, "return_pct"),
        "w365_dd_pct": f(w365, "max_dd_pct"),
        "w365_pf": f(w365, "profit_factor"),
        "w365_trades": f(w365, "trades"),
        "h730_return_pct": f(h730, "return_pct"),
        "h730_dd_pct": f(h730, "max_dd_pct"),
        "h730_pf": f(h730, "profit_factor"),
        "h730_trades": f(h730, "trades"),
        "h730_active_days": f(h730, "active_days"),
        "w730_return_pct": f(w730, "return_pct"),
        "w730_dd_pct": f(w730, "max_dd_pct"),
        "w730_pf": f(w730, "profit_factor"),
        "w730_trades": f(w730, "trades"),
    }


def run_symbol(bt, reinvest, multi, cf, deep, rif, symbol, inventory_first_days, periods, max_health_window, archive_end_day):
    if archive_end_day:
        fixed_end_day = date.fromisoformat(archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    max_period = max(periods)
    candles, _, _ = deep.fetch_klines_bounded(
        multi,
        symbol,
        max_period + max_health_window,
        0,
        inventory_first_days.get(symbol),
    )
    if len(candles) < max_period * 1440:
        raise RuntimeError(f"not enough candles: {len(candles)} < {max_period * 1440}")

    spec = fixed_spec(symbol)
    base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, base_args)
    print(f"{symbol}: candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}", flush=True)

    target_start = len(candles) - max_period * 1440
    starts = rif.daily_start_indices(candles)
    health_cache = rif.compute_health_cache(
        bt,
        multi,
        reinvest,
        cf,
        candles,
        spec,
        starts,
        target_start,
        [30, 60, 90],
    )

    output = []
    for period in periods:
        for policy in rif.POLICIES:
            result = rif.run_policy(bt, multi, reinvest, cf, candles, spec, period, policy, health_cache)
            output.append(result)
            print(
                f"  {period}d {policy['policy']}: ret={result['return_pct']:+.2f}% "
                f"dd={result['max_dd_pct']:.2f}% pf={result['profit_factor']:.3f} "
                f"active={result['active_days']}",
                flush=True,
            )
    return output


def write_report(path, best_rows, summary_path, detail_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    order = {
        "candidate_plus_defensive": 0,
        "defensive_candidate": 1,
        "candidate": 2,
        "reject": 3,
        "error": 4,
    }
    ranked = sorted(
        best_rows,
        key=lambda row: (
            order.get(row["verdict"], 9),
            float(row.get("w730_return_pct") or -999),
            float(row.get("h730_return_pct") or -999),
        ),
        reverse=False,
    )
    lines = [
        "# RIF Regime Deep Candidates",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Точная проверка всех RIF-like кандидатов из all-Binance scan. Параметры не оптимизируются.",
        "",
        "Setup: `LONG th50 wide TP 1.2% SL 4% T90`, strict maker `0.05%`, fee `0.02%`, slippage `0`.",
        "",
        "| Symbol | Verdict | 730 health30_60 | DD | PF | Trades | Active Days | 730 weekly kill | DD | PF | Reason |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in ranked:
        lines.append(
            f"| `{row['symbol']}` | {row['verdict']} | {fmt_pct(row.get('h730_return_pct'))} | "
            f"{fmt_num(row.get('h730_dd_pct'))}% | {fmt_num(row.get('h730_pf'))} | {row.get('h730_trades', '')} | "
            f"{row.get('h730_active_days', '')} | {fmt_pct(row.get('w730_return_pct'))} | "
            f"{fmt_num(row.get('w730_dd_pct'))}% | {fmt_num(row.get('w730_pf'))} | {row.get('reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
            f"- Detail CSV: `{detail_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Deep exact check for RIF-like candidates.")
    parser.add_argument("--input", default="data/rif_regime_scan_all_binance_overnight_2026-05-08.csv")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--periods", nargs="*", type=int, default=[365, 730])
    parser.add_argument("--max-health-window", type=int, default=90)
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--save-detail", default=f"data/rif_regime_deep_candidates_detail_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/rif_regime_deep_candidates_summary_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-regime-deep-candidates-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    deep = load_module("deep_validate_hot_shortlist", DEEP_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)

    first_days = deep.load_inventory_first_days(os.path.join(ROOT, args.inventory))
    candidates = load_candidates(os.path.join(ROOT, args.input), args.symbols, args.limit)

    detail_fields = [
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
    summary_fields = [
        "symbol",
        "verdict",
        "reason",
        "h365_return_pct",
        "h365_dd_pct",
        "h365_pf",
        "h365_trades",
        "h365_active_days",
        "w365_return_pct",
        "w365_dd_pct",
        "w365_pf",
        "w365_trades",
        "h730_return_pct",
        "h730_dd_pct",
        "h730_pf",
        "h730_trades",
        "h730_active_days",
        "w730_return_pct",
        "w730_dd_pct",
        "w730_pf",
        "w730_trades",
    ]

    detail_rows = read_csv(os.path.join(ROOT, args.save_detail)) if args.resume and os.path.exists(os.path.join(ROOT, args.save_detail)) else []
    completed = {row["symbol"] for row in detail_rows} if args.resume else set()
    summary_by_symbol = {}
    if detail_rows:
        grouped = defaultdict(list)
        for row in detail_rows:
            grouped[row["symbol"]].append(row)
        summary_by_symbol.update({symbol: summarize_symbol(rows) for symbol, rows in grouped.items()})

    for index, row in enumerate(candidates, start=1):
        symbol = row["symbol"]
        if symbol in completed:
            print(f"[{index}/{len(candidates)}] {symbol} skip completed", flush=True)
            continue
        print(f"[{index}/{len(candidates)}] {symbol}", flush=True)
        try:
            symbol_rows = run_symbol(
                bt,
                reinvest,
                multi,
                cf,
                deep,
                rif,
                symbol,
                first_days,
                args.periods,
                args.max_health_window,
                args.archive_end_day,
            )
            detail_rows.extend(symbol_rows)
            summary_by_symbol[symbol] = summarize_symbol(symbol_rows)
        except Exception as exc:
            summary_by_symbol[symbol] = {
                "symbol": symbol,
                "verdict": "error",
                "reason": repr(exc),
            }
        save_csv(os.path.join(ROOT, args.save_detail), detail_rows, detail_fields)
        save_csv(os.path.join(ROOT, args.save_summary), list(summary_by_symbol.values()), summary_fields)
        write_report(os.path.join(ROOT, args.save_report), list(summary_by_symbol.values()), args.save_summary, args.save_detail)

    print(f"saved detail: {args.save_detail}")
    print(f"saved summary: {args.save_summary}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
