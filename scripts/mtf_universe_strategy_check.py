#!/usr/bin/env python3
"""Run MTF regime checks for accepted and watchlist strategies."""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")

INITIAL_BALANCE = 1000.0
BASELINE = "1m_only"


DEFAULT_SPECS = [
    {"name": "GALA 7.3", "coin": "GALA", "symbol": "GALAUSDT", "kind": "template", "template": "7.3"},
    {"name": "GALA 10", "coin": "GALA", "symbol": "GALAUSDT", "kind": "template", "template": "10"},
    {"name": "GALA 11.2", "coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
    {"name": "ONE 11.2", "coin": "ONE", "symbol": "ONEUSDT", "kind": "gala_112"},
    {
        "name": "CHZ Best",
        "coin": "CHZ",
        "symbol": "CHZUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "name": "SHIB Best",
        "coin": "SHIB",
        "symbol": "1000SHIBUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "name": "JASMY Best",
        "coin": "JASMY",
        "symbol": "JASMYUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 0.90,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "name": "SAND Best",
        "coin": "SAND",
        "symbol": "SANDUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "name": "MANA Best",
        "coin": "MANA",
        "symbol": "MANAUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
    {
        "name": "ANKR Best",
        "coin": "ANKR",
        "symbol": "ANKRUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 120,
    },
    {
        "name": "SPELL Best",
        "coin": "SPELL",
        "symbol": "SPELLUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
    {
        "name": "AXL Watchlist",
        "coin": "AXL",
        "symbol": "AXLUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 40,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
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


def parse_bool(value):
    return str(value).lower() in {"1", "true", "yes", "y"}


def load_extra_specs(path):
    if not path or not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "name": row.get("name") or f"{row['symbol']} leader",
                    "coin": row.get("coin") or row["symbol"].replace("USDT", ""),
                    "symbol": row["symbol"],
                    "kind": row.get("kind", "single"),
                    "direction": row["direction"],
                    "threshold": int(float(row["threshold"])),
                    "regime": row["regime"],
                    "position_pct": float(row.get("position_pct", 1.0)),
                    "tp_pct": float(row["tp_pct"]),
                    "sl_pct": float(row.get("sl_pct", 0.04)),
                    "time_stop_min": int(float(row["time_stop_min"])),
                    "leader_from_new_screen": parse_bool(row.get("leader_from_new_screen", "1")),
                }
            )
    return rows


def make_windows(bt, candles, periods):
    output = {}
    for period in periods:
        bars = period * bt.candles_per_day("1m")
        if len(candles) >= bars:
            output[period] = candles[-bars:]
    return output


def apply_spec_signals(multi, cf, rows, spec):
    if spec["kind"] == "template":
        multi.apply_strategy_signals(rows, spec["template"])
        return
    if spec["kind"] == "single":
        cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
        return
    raise ValueError(f"Unsupported signal kind: {spec['kind']}")


def make_spec_args(multi, reinvest, cf, spec):
    if spec["kind"] == "template":
        return multi.make_strategy_args(reinvest, spec["template"], spec["symbol"])
    if spec["kind"] == "single":
        single_spec = {"kind": "single", **spec}
        return cf.make_single_args(multi, reinvest, single_spec)
    raise ValueError(f"Unsupported args kind: {spec['kind']}")


def run_single_spec(bt, reinvest, multi, cf, mtf, candles, spec, period, permissions):
    rows = [dict(row) for row in candles]
    apply_spec_signals(multi, cf, rows, spec)
    mtf_stats = Counter()
    if permissions is not None:
        mtf_stats.update(mtf.apply_htf_filter(rows, permissions))
    args = make_spec_args(multi, reinvest, cf, spec)
    trades, equity, stats = bt.run_backtest(rows, args)
    stats.update(mtf_stats)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return trades, equity, summary, stats


def run_gala_112(bt, reinvest, multi, mtf, candles, spec, permissions):
    short_spec = {"kind": "template", "template": "7.3", "symbol": spec["symbol"]}
    long_spec = {"kind": "template", "template": "10", "symbol": spec["symbol"]}
    short_trades, _, _, short_stats = run_single_spec(
        bt, reinvest, multi, None, mtf, candles, short_spec, None, permissions
    )
    long_trades, _, _, long_stats = run_single_spec(
        bt, reinvest, multi, None, mtf, candles, long_spec, None, permissions
    )
    portfolio_trades, portfolio_equity, portfolio_summary = multi.build_112_portfolio(
        short_trades, long_trades
    )
    stats = Counter()
    stats.update(short_stats)
    stats.update(long_stats)
    return portfolio_trades, portfolio_equity, portfolio_summary, stats


def summary_row(spec, htf, period, summary, stats, data_start, data_end, candles_count):
    reasons = summary.get("exit_reasons", Counter())
    return {
        "name": spec["name"],
        "coin": spec["coin"],
        "symbol": spec["symbol"],
        "kind": spec["kind"],
        "htf": htf,
        "period": f"{period}d",
        "days": period,
        "candles": candles_count,
        "data_start": data_start,
        "data_end": data_end,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "expectancy_pct": summary.get("expectancy_pct", 0.0),
        "final_equity": summary["final_equity"],
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "end_of_data": reasons["end_of_data"],
        "mtf_candidate_signals": stats.get("mtf_candidate_signals", 0),
        "mtf_blocked_total": stats.get("mtf_blocked_total", 0),
    }


def error_row(spec, htf, period, error):
    return {
        "name": spec["name"],
        "coin": spec["coin"],
        "symbol": spec["symbol"],
        "kind": spec["kind"],
        "htf": htf,
        "period": f"{period}d",
        "days": period,
        "candles": 0,
        "data_start": "",
        "data_end": "",
        "trades": 0,
        "return_pct": 0.0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "max_dd_pct": 0.0,
        "expectancy_pct": 0.0,
        "final_equity": INITIAL_BALANCE,
        "take_profit": 0,
        "stop_loss": 0,
        "time_stop": 0,
        "end_of_data": 0,
        "mtf_candidate_signals": 0,
        "mtf_blocked_total": 0,
        "status": "error",
        "error": str(error),
    }


def fmt_pct(value):
    return f"{value:+.2f}%"


def fmt_pf(value):
    return "inf" if value == math.inf else f"{value:.2f}"


def save_report(path, rows, periods, htfs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok_rows = [row for row in rows if row.get("status", "ok") == "ok"]
    by_key = {(row["name"], row["htf"], int(row["days"])): row for row in ok_rows}
    names = []
    for row in ok_rows:
        if row["name"] not in names:
            names.append(row["name"])

    lines = [
        "# MTF Universe Strategy Check",
        "",
        "Статус: исследовательский срез по рабочим и watchlist-стратегиям.",
        "",
        "Вход остается на `1m`; старший таймфрейм только разрешает или блокирует вход после закрытия старшей свечи.",
        "",
        "## 365d / 730d Summary",
        "",
        "| Strategy | Best HTF 730 | 365d Return | 365d DD | 365d PF | 730d Return | 730d DD | 730d PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in names:
        candidates = []
        for htf in [BASELINE] + htfs:
            row730 = by_key.get((name, htf, 730))
            row365 = by_key.get((name, htf, 365))
            if row730 and row365:
                candidates.append((row730["return_pct"], row730["profit_factor"], -row730["max_dd_pct"], htf, row365, row730))
        if not candidates:
            continue
        _, _, _, best_htf, row365, row730 = max(candidates)
        lines.append(
            f"| {name} | {best_htf} | {fmt_pct(row365['return_pct'])} | "
            f"{row365['max_dd_pct']:.2f}% | {fmt_pf(row365['profit_factor'])} | "
            f"{fmt_pct(row730['return_pct'])} | {row730['max_dd_pct']:.2f}% | "
            f"{fmt_pf(row730['profit_factor'])} |"
        )

    lines.extend(
        [
            "",
            "## Full MTF Matrix",
            "",
            "| Strategy | HTF | 7d | 30d | 60d | 90d | 180d | 365d | 730d | Worst DD |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in names:
        for htf in [BASELINE] + htfs:
            values = []
            dds = []
            has_any = False
            for period in periods:
                row = by_key.get((name, htf, period))
                if row:
                    has_any = True
                    values.append(fmt_pct(row["return_pct"]))
                    dds.append(row["max_dd_pct"])
                else:
                    values.append("-")
            if has_any:
                lines.append(
                    f"| {name} | {htf} | "
                    + " | ".join(values)
                    + f" | {(max(dds) if dds else 0):.2f}% |"
                )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run MTF checks for the strategy universe.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--periods", nargs="*", type=int, default=[7, 30, 60, 90, 180, 365, 730])
    parser.add_argument("--htfs", nargs="*", default=["3m", "5m", "10m", "15m", "30m", "1h"])
    parser.add_argument("--extra-specs", default="")
    parser.add_argument("--save-summary", default="data/mtf_universe_summary.csv")
    parser.add_argument("--save-diagnostics", default="data/mtf_universe_diagnostics.csv")
    parser.add_argument("--save-report", default="strategies/mtf-universe-summary.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    mtf = load_module("gala_mtf_regime_backtest", MTF_PATH)

    specs = DEFAULT_SPECS + load_extra_specs(os.path.join(ROOT, args.extra_specs) if args.extra_specs else "")
    fields = [
        "name",
        "coin",
        "symbol",
        "kind",
        "htf",
        "period",
        "days",
        "candles",
        "data_start",
        "data_end",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
        "end_of_data",
        "mtf_candidate_signals",
        "mtf_blocked_total",
    ]
    diagnostics = []
    rows = []

    for index, spec in enumerate(specs, start=1):
        print(f"\n=== [{index}/{len(specs)}] {spec['name']} {spec['symbol']} ===", flush=True)
        try:
            candles, _, _ = multi.fetch_klines_fast(spec["symbol"], args.days, args.warmup_days)
            if not candles:
                raise RuntimeError("no candles")
            base_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
            bt.add_indicators_and_signals(candles, base_args)
            test_bars = args.days * bt.candles_per_day("1m")
            candles = candles[-test_bars:]
            windows = make_windows(bt, candles, args.periods)
            permissions = {}
            for htf in args.htfs:
                permissions[htf] = mtf.build_htf_permissions(bt, candles, base_args, htf)

            diagnostics.append(
                {
                    "name": spec["name"],
                    "symbol": spec["symbol"],
                    "status": "ok",
                    "candles": len(candles),
                    "start": candles[0]["open_time"],
                    "end": candles[-1]["close_time"],
                    "error": "",
                }
            )

            for htf in [BASELINE] + args.htfs:
                active_permissions = None if htf == BASELINE else permissions[htf]
                for period in args.periods:
                    if period not in windows:
                        continue
                    print(f"run {spec['name']} {htf} {period}d", flush=True)
                    period_candles = windows[period]
                    if spec["kind"] == "gala_112":
                        _, _, summary, stats = run_gala_112(
                            bt, reinvest, multi, mtf, period_candles, spec, active_permissions
                        )
                    else:
                        _, _, summary, stats = run_single_spec(
                            bt, reinvest, multi, cf, mtf, period_candles, spec, period, active_permissions
                        )
                    row = summary_row(
                        spec,
                        htf,
                        period,
                        summary,
                        stats,
                        candles[0]["open_time"],
                        candles[-1]["close_time"],
                        len(candles),
                    )
                    row["status"] = "ok"
                    row["error"] = ""
                    rows.append(row)
        except Exception as exc:
            diagnostics.append(
                {
                    "name": spec["name"],
                    "symbol": spec["symbol"],
                    "status": "error",
                    "candles": 0,
                    "start": "",
                    "end": "",
                    "error": str(exc),
                }
            )
            for htf in [BASELINE] + args.htfs:
                for period in args.periods:
                    rows.append(error_row(spec, htf, period, exc))
            print(f"error {spec['name']}: {exc}", flush=True)

    save_csv(os.path.join(ROOT, args.save_summary), rows, fields + ["status", "error"])
    save_csv(
        os.path.join(ROOT, args.save_diagnostics),
        diagnostics,
        ["name", "symbol", "status", "candles", "start", "end", "error"],
    )
    save_report(os.path.join(ROOT, args.save_report), rows, args.periods, args.htfs)
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved diagnostics: {os.path.join(ROOT, args.save_diagnostics)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
