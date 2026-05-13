#!/usr/bin/env python3
"""Scan Binance Futures universe with the fixed RIF Regime Monitor logic.

This is a broad first pass:

- universe: active ASCII USDT USD-M futures from the Binance archive inventory;
- setup: the fixed RIF setup, no optimization:
  LONG, threshold 50, wide regime, TP 1.2%, SL 4%, time stop 90m;
- execution: strict maker, fee 0.02%, limit offset 0.05%, no slippage;
- gate: trade only on days where the previous 30d and 60d strategy health pass;
- defensive version: same gate plus weekly loss stop 2%.

Symbols without 730d of 1m history are recorded as `insufficient_history`.
"""

import argparse
import csv
import importlib.util
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
DEEP_PATH = os.path.join(ROOT, "scripts", "deep_validate_hot_shortlist.py")
RMB_PATH = os.path.join(ROOT, "scripts", "regime_monitor_batch_fast.py")

RIF_SPEC = {
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


def bool_text(value):
    return str(value).lower() == "true"


def coin_from_symbol(symbol):
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def metric(prefix, summary):
    return {
        f"{prefix}_return_pct": summary["total_return_pct"],
        f"{prefix}_dd_pct": summary["max_drawdown_pct"],
        f"{prefix}_pf": summary["profit_factor"],
        f"{prefix}_trades": summary["total_trades"],
        f"{prefix}_win_rate_pct": summary["win_rate_pct"],
        f"{prefix}_expectancy_pct": summary["expectancy_pct"],
    }


def empty_metric(prefix):
    return {
        f"{prefix}_return_pct": "",
        f"{prefix}_dd_pct": "",
        f"{prefix}_pf": "",
        f"{prefix}_trades": "",
        f"{prefix}_win_rate_pct": "",
        f"{prefix}_expectancy_pct": "",
    }


def load_universe(path, symbols, require_24m=False):
    rows = read_csv(path)
    if symbols:
        wanted = set(symbols)
        return [row for row in rows if row["symbol"] in wanted]
    filtered = [
        row
        for row in rows
        if bool_text(row.get("is_active"))
        and row.get("quote_asset") == "USDT"
        and bool_text(row.get("is_ascii"))
        and not bool_text(row.get("is_delivery"))
    ]
    if require_24m:
        filtered = [row for row in filtered if bool_text(row.get("has_24m"))]
    return filtered


def first_days_from_inventory(rows):
    out = {}
    for row in rows:
        first_month = row.get("first_month")
        if not first_month:
            continue
        try:
            out[row["symbol"]] = date.fromisoformat(f"{first_month}-01")
        except ValueError:
            pass
    return out


def classify(row, min_pf, max_dd, min_trades, defensive_min_pf, defensive_max_dd):
    if row["status"] != "ok":
        return row["status"]
    ret = float(row["gated_730_return_pct"])
    pf = float(row["gated_730_pf"])
    dd = float(row["gated_730_dd_pct"])
    trades = int(row["gated_730_trades"])
    wret = float(row["weekly_730_return_pct"])
    wpf = float(row["weekly_730_pf"])
    wdd = float(row["weekly_730_dd_pct"])
    wtrades = int(row["weekly_730_trades"])
    if wret > 0 and wpf >= defensive_min_pf and wdd <= defensive_max_dd and wtrades >= min_trades:
        return "regime_candidate_defensive"
    if ret > 0 and pf >= min_pf and dd <= max_dd and trades >= min_trades:
        return "regime_candidate"
    return "reject"


def process_symbol(symbol, inventory_row, first_day, args):
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    deep = load_module("deep_validate_hot_shortlist", DEEP_PATH)
    rmb = load_module("regime_monitor_batch_fast", RMB_PATH)

    if args.archive_end_day:
        fixed_end = date.fromisoformat(args.archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end

    base = {
        "symbol": symbol,
        "coin": coin_from_symbol(symbol),
        "status": "ok",
        "decision": "",
        "months_count": inventory_row.get("months_count", ""),
        "has_12m": inventory_row.get("has_12m", ""),
        "has_24m": inventory_row.get("has_24m", ""),
        "has_36m": inventory_row.get("has_36m", ""),
        "data_start": "",
        "data_end": "",
        "candles": "",
        "available_days": "",
        "active_days_365": "",
        "active_days_730": "",
        "error": "",
    }
    for prefix in (
        "always_365",
        "always_730",
        "gated_365",
        "gated_730",
        "weekly_365",
        "weekly_730",
    ):
        base.update(empty_metric(prefix))

    try:
        candles, start_day, end_day = deep.fetch_klines_bounded(
            multi,
            symbol,
            args.days + args.warmup_days,
            0,
            first_day,
        )
        base["candles"] = len(candles)
        base["available_days"] = round(len(candles) / 1440, 2)
        if candles:
            base["data_start"] = candles[0]["open_time"]
            base["data_end"] = candles[-1]["close_time"]
        if len(candles) < args.days * 1440:
            base["status"] = "insufficient_history"
            base["decision"] = "insufficient_history"
            base["error"] = f"not enough candles: {len(candles)} < {args.days * 1440}"
            return base

        spec = dict(RIF_SPEC)
        spec["coin"] = coin_from_symbol(symbol)
        spec["symbol"] = symbol
        indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
        bt.add_indicators_and_signals(candles, indicator_args)

        rows730 = [dict(row) for row in candles[-730 * 1440 :]]
        rows365 = [dict(row) for row in candles[-365 * 1440 :]]

        raw_trades, always730, _ = rmb.run_strategy(bt, multi, reinvest, cf, rows730, spec)
        _, always365, _ = rmb.run_strategy(bt, multi, reinvest, cf, rows365, spec)
        base.update(metric("always_730", always730))
        base.update(metric("always_365", always365))

        active_by_day = {}
        for day, _idx in rmb.daily_start_indices(rows730):
            passed, _h30, _h60 = rmb.pass_health(day, raw_trades)
            active_by_day[day] = passed
        active_days = [day for day, passed in active_by_day.items() if passed]
        first_365_day = rmb.utc_day_from_ms(rows365[0]["open_time_ms"])
        active365 = [day for day in active_days if day >= first_365_day]

        gated730, _ = rmb.run_gated(bt, multi, reinvest, cf, rows730, spec, active_days)
        gated365, _ = rmb.run_gated(bt, multi, reinvest, cf, rows365, spec, active365)
        weekly730, _ = rmb.run_gated(bt, multi, reinvest, cf, rows730, spec, active_days, weekly_loss_stop_pct=0.02)
        weekly365, _ = rmb.run_gated(bt, multi, reinvest, cf, rows365, spec, active365, weekly_loss_stop_pct=0.02)

        base["active_days_730"] = len(active_days)
        base["active_days_365"] = len(active365)
        base.update(metric("gated_730", gated730))
        base.update(metric("gated_365", gated365))
        base.update(metric("weekly_730", weekly730))
        base.update(metric("weekly_365", weekly365))
        base["decision"] = classify(
            base,
            args.min_pf,
            args.max_dd,
            args.min_trades,
            args.defensive_min_pf,
            args.defensive_max_dd,
        )
        return base
    except Exception as exc:
        base["status"] = "error"
        base["decision"] = "error"
        base["error"] = repr(exc)
        return base


def write_report(path, rows, args, summary_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    counts = {}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    candidates = [
        row
        for row in rows
        if row["decision"] in {"regime_candidate", "regime_candidate_defensive"}
    ]
    ranked = sorted(
        candidates,
        key=lambda row: (
            row["decision"] == "regime_candidate_defensive",
            float(row["weekly_730_return_pct"] or 0),
            -float(row["weekly_730_dd_pct"] or 999),
        ),
        reverse=True,
    )
    top_rejected = sorted(
        [row for row in rows if row["decision"] == "reject"],
        key=lambda row: float(row["gated_730_return_pct"] or -999),
        reverse=True,
    )[:20]

    lines = [
        "# RIF Regime Scan All Binance",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Проверка применяет фиксированную механику `RIF Regime Monitor` ко всем активным Binance USD-M USDT futures из inventory.",
        "",
        "Фиксированная стратегия: `LONG th50 wide TP 1.2% SL 4% time-stop 90m`, strict maker `0.05%`, fee `0.02%`, slippage `0`.",
        "Gate: торговать только если прошлые 30d и 60d проходят health-check. Defensive версия добавляет weekly kill `2%`.",
        "",
        "## Counts",
        "",
        "| Decision | Count |",
        "|---|---:|",
    ]
    for key in sorted(counts):
        lines.append(f"| {key} | {counts[key]} |")
    lines.extend(
        [
            "",
            "## Top Candidates",
            "",
            "| Symbol | Decision | Active Days 730 | Always 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in ranked[:50]:
        lines.append(
            f"| `{row['symbol']}` | {row['decision']} | {row['active_days_730']} | "
            f"{fmt_pct(row['always_730_return_pct'])} | {fmt_pct(row['gated_730_return_pct'])} | "
            f"{fmt_num(row['gated_730_dd_pct'])}% | {fmt_num(row['gated_730_pf'])} | "
            f"{fmt_pct(row['weekly_730_return_pct'])} | {fmt_num(row['weekly_730_dd_pct'])}% | "
            f"{fmt_num(row['weekly_730_pf'])} |"
        )
    lines.extend(
        [
            "",
            "## Strong Rejected By Risk Filter",
            "",
            "| Symbol | Active Days 730 | Gated 730 | Gated DD | Gated PF | Weekly 730 | Weekly DD | Weekly PF |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_rejected:
        lines.append(
            f"| `{row['symbol']}` | {row['active_days_730']} | {fmt_pct(row['gated_730_return_pct'])} | "
            f"{fmt_num(row['gated_730_dd_pct'])}% | {fmt_num(row['gated_730_pf'])} | "
            f"{fmt_pct(row['weekly_730_return_pct'])} | {fmt_num(row['weekly_730_dd_pct'])}% | "
            f"{fmt_num(row['weekly_730_pf'])} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def fields():
    base = [
        "symbol",
        "coin",
        "status",
        "decision",
        "months_count",
        "has_12m",
        "has_24m",
        "has_36m",
        "data_start",
        "data_end",
        "candles",
        "available_days",
        "active_days_365",
        "active_days_730",
    ]
    metric_fields = []
    for prefix in (
        "always_365",
        "always_730",
        "gated_365",
        "gated_730",
        "weekly_365",
        "weekly_730",
    ):
        metric_fields.extend(
            [
                f"{prefix}_return_pct",
                f"{prefix}_dd_pct",
                f"{prefix}_pf",
                f"{prefix}_trades",
                f"{prefix}_win_rate_pct",
                f"{prefix}_expectancy_pct",
            ]
        )
    return base + metric_fields + ["error"]


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Scan Binance Futures with fixed RIF regime-monitor logic.")
    parser.add_argument("--inventory", default="data/binance_futures_universe_inventory_2026-05-04.csv")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--symbols", nargs="*", default=[])
    parser.add_argument("--require-24m", action="store_true", help="Scan only active USDT symbols with enough inventory history for 730d.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-pf", type=float, default=1.10)
    parser.add_argument("--max-dd", type=float, default=25.0)
    parser.add_argument("--min-trades", type=int, default=40)
    parser.add_argument("--defensive-min-pf", type=float, default=1.20)
    parser.add_argument("--defensive-max-dd", type=float, default=15.0)
    parser.add_argument("--save-summary", default=f"data/rif_regime_scan_all_binance_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/rif-regime-scan-all-binance-{today}.md")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    args = parser.parse_args()

    inventory_rows = load_universe(os.path.join(ROOT, args.inventory), args.symbols, args.require_24m)
    inventory_rows.sort(key=lambda row: row["symbol"])
    if args.limit > 0:
        inventory_rows = inventory_rows[: args.limit]
    first_days = first_days_from_inventory(inventory_rows)
    rows = []
    total = len(inventory_rows)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(process_symbol, row["symbol"], row, first_days.get(row["symbol"]), args): row["symbol"]
            for row in inventory_rows
        }
        for index, future in enumerate(as_completed(futures), start=1):
            symbol = futures[future]
            row = future.result()
            rows.append(row)
            print(
                f"[{index}/{total}] {symbol} {row['decision']} "
                f"gated730={fmt_pct(row.get('gated_730_return_pct'))} "
                f"weekly730={fmt_pct(row.get('weekly_730_return_pct'))}",
                flush=True,
            )
            if args.checkpoint_every > 0 and index % args.checkpoint_every == 0:
                save_csv(os.path.join(ROOT, args.save_summary), sorted(rows, key=lambda item: item["symbol"]), fields())

    rows.sort(key=lambda item: item["symbol"])
    save_csv(os.path.join(ROOT, args.save_summary), rows, fields())
    write_report(os.path.join(ROOT, args.save_report), rows, args, args.save_summary)
    print(f"saved summary: {args.save_summary}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
