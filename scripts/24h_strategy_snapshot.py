#!/usr/bin/env python3
"""Build one explicit 24h snapshot across the fixed strategy layers.

The project has several different "24h" checks:
- theoretical backtest on the latest full Binance Futures archive day;
- maker-limit paper execution on rolling API candles;
- strict fixed variants;
- cashflow portfolio wrappers.

This script keeps those layers separate in one table so a zero in one layer is
not confused with a zero in another.
"""

import argparse
import csv
import importlib.util
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")
OP_PATH = os.path.join(ROOT, "scripts", "operational_daily_monitor.py")
DYDX_TUNE_PATH = os.path.join(ROOT, "scripts", "dydx_pullback_short_tune.py")
DYDX_PROTECTION_PATH = os.path.join(ROOT, "scripts", "dydx_pullback_short_leverage_protection.py")


FIELDS = [
    "layer",
    "fixed",
    "asset",
    "symbol",
    "strategy",
    "mode",
    "market",
    "source",
    "data_start",
    "data_end",
    "signals",
    "filled",
    "unfilled",
    "trades",
    "return_pct",
    "profit_factor",
    "win_rate_pct",
    "expectancy_pct",
    "max_dd_pct",
    "exit_reasons",
    "status",
    "note",
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isinf(value):
        return "inf"
    return f"{value:+.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def numeric(value, default=0.0):
    try:
        if value in ("", None):
            return default
        if str(value).lower() == "inf":
            return math.inf
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minmax_times(rows, keys):
    times = []
    for row in rows:
        for key in keys:
            value = row.get(key)
            if value:
                parsed = parse_time(value)
                if parsed:
                    times.append(parsed)
    if not times:
        return "", ""
    return min(times).isoformat(), max(times).isoformat()


def add_row(rows, **kwargs):
    row = {field: "" for field in FIELDS}
    row.update(kwargs)
    rows.append(row)


def run_command(command, cwd, quiet=False):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message)
    if not quiet and result.stdout.strip():
        print(result.stdout.strip())
    return result


def archive_source(market):
    if market == "futures_archive":
        return "Binance Futures archive latest complete day"
    if market == "data_api_spot":
        return "rolling data_api_spot candles"
    if market == "futures_global":
        return "Binance Futures global API"
    return market


def operational_backtest_rows(args):
    op = load_module("operational_daily_monitor", OP_PATH)
    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)
    op.DYDX_TUNE = load_module("dydx_pullback_short_tune", DYDX_TUNE_PATH)
    op.DYDX_PROTECTION = load_module("dydx_pullback_short_leverage_protection", DYDX_PROTECTION_PATH)

    output = []
    cache = {}
    universe = read_csv(os.path.join(ROOT, args.universe))
    for source in universe:
        if source["monitor_group"] not in {"best_strategy", "regime_monitor"}:
            continue
        try:
            candles = op.cached_candles(bt, reinvest, multi, cache, source["symbol"], args.days, args.warmup_days)
            bars = args.days * bt.candles_per_day("1m")
            window = candles[-bars:]
            if source["monitor_group"] == "best_strategy":
                metrics = op.run_best_period(bt, reinvest, multi, cf, source, candles, args.days)
            else:
                spec = rif.spec_from_shortlist(op.STRICT_SHORTLIST_PATH, source["symbol"])
                metrics = op.run_regime_period(bt, reinvest, multi, cf, rif, candles, spec, args.days)
            add_row(
                output,
                layer="operational_backtest",
                fixed="yes",
                asset=source["asset"],
                symbol=source["symbol"],
                strategy=source["strategy"],
                mode="theoretical_strategy_backtest",
                market="futures_archive",
                source=archive_source("futures_archive"),
                data_start=window[0]["open_time"],
                data_end=window[-1]["close_time"],
                trades=metrics["trades"],
                return_pct=metrics["return_pct"],
                profit_factor=metrics["profit_factor"],
                win_rate_pct=metrics["win_rate_pct"],
                expectancy_pct=metrics["expectancy_pct"],
                max_dd_pct=metrics["max_dd_pct"],
                status="OK",
            )
        except Exception as exc:
            add_row(
                output,
                layer="operational_backtest",
                fixed="yes",
                asset=source.get("asset", ""),
                symbol=source.get("symbol", ""),
                strategy=source.get("strategy", ""),
                mode="theoretical_strategy_backtest",
                market="futures_archive",
                source=archive_source("futures_archive"),
                status="ERROR",
                note=str(exc),
            )
    return output


def core_paper_rows(args, tag):
    journal = f"data/24h_snapshot_core_{tag}_journal_{args.date}.csv"
    summary = f"data/24h_snapshot_core_{tag}_summary_{args.date}.csv"
    report = f"strategies/24h-snapshot-core-{tag}-{args.date}.md"
    command = [
        sys.executable,
        "scripts/paper_execution_journal.py",
        "--modules",
        "ANKR",
        "RIF",
        "GALA_73",
        "GALA_10",
        "GALA_112",
        "SPELL",
        "DYDX_X2",
        "--days",
        str(args.days),
        "--market",
        args.paper_market,
        "--entry-mode",
        "maker_limit",
        "--save-journal",
        journal,
        "--save-summary",
        summary,
        "--save-report",
        report,
    ]
    try:
        run_command(command, ROOT, quiet=args.quiet)
    except Exception as exc:
        return [
            {
                **{field: "" for field in FIELDS},
                "layer": "core_paper",
                "fixed": "yes",
                "mode": "maker_limit_paper_fill",
                "market": args.paper_market,
                "source": archive_source(args.paper_market),
                "status": "ERROR",
                "note": str(exc),
            }
        ]

    journal_rows = read_csv(os.path.join(ROOT, journal))
    data_start, data_end = minmax_times(journal_rows, ["signal_time", "order_start_time", "fill_time", "exit_time"])
    output = []
    for row in read_csv(os.path.join(ROOT, summary)):
        add_row(
            output,
            layer="core_paper",
            fixed="yes",
            asset=row["asset"],
            strategy=row["strategy"],
            mode="maker_limit_paper_fill",
            market=args.paper_market,
            source=archive_source(args.paper_market),
            data_start=data_start,
            data_end=data_end,
            signals=row["signals"],
            filled=row["filled"],
            unfilled=row["unfilled"],
            trades=row["accepted"],
            return_pct=row["accepted_return_sum_pct"],
            profit_factor=row["accepted_profit_factor"],
            win_rate_pct=row["accepted_win_rate_pct"],
            expectancy_pct=row["accepted_expectancy_pct"],
            exit_reasons=row["exit_reasons"],
            status="OK",
            note=f"summary={summary}; report={report}",
        )
    return output


def strict_rows(args):
    summary = f"data/24h_snapshot_strict_summary_{args.date}.csv"
    diagnostics = f"data/24h_snapshot_strict_diagnostics_{args.date}.csv"
    report = f"strategies/24h-snapshot-strict-{args.date}.md"
    command = [
        sys.executable,
        "scripts/daily_strict_survivor_check.py",
        "--market",
        args.strict_market,
        "--periods",
        str(args.days),
        "--save-summary",
        summary,
        "--save-diagnostics",
        diagnostics,
        "--save-report",
        report,
    ]
    try:
        run_command(command, ROOT, quiet=args.quiet)
    except Exception as exc:
        return [
            {
                **{field: "" for field in FIELDS},
                "layer": "strict",
                "fixed": "yes",
                "mode": "strict_fixed_maker_limit",
                "market": args.strict_market,
                "source": archive_source(args.strict_market),
                "status": "ERROR",
                "note": str(exc),
            }
        ]

    output = []
    for row in read_csv(os.path.join(ROOT, summary)):
        add_row(
            output,
            layer="strict",
            fixed="yes",
            asset=row["coin"],
            symbol=row["symbol"],
            strategy=row["strategy"],
            mode="strict_fixed_maker_limit",
            market=row["market"],
            source=archive_source(row["market"]),
            data_start=row["data_start"],
            data_end=row["data_end"],
            signals=row["signals"],
            filled=row["filled"],
            unfilled=row["unfilled"],
            trades=row["accepted"],
            return_pct=row["return_sum_pct"],
            profit_factor=row["profit_factor"],
            win_rate_pct=row["win_rate_pct"],
            expectancy_pct=row["expectancy_pct"],
            exit_reasons=row["exit_reasons"],
            status=row["status"],
            note=row["status_reason"],
        )
    return output


def cashflow_rows(args, candidate, script, market, tag):
    journal = f"data/24h_snapshot_{tag}_journal_{args.date}.csv"
    summary = f"data/24h_snapshot_{tag}_summary_{args.date}.csv"
    modules = f"data/24h_snapshot_{tag}_modules_{args.date}.csv"
    report = f"strategies/Portfolio/24h-snapshot-{tag}-{args.date}.md"
    command = [
        sys.executable,
        script,
        "--market",
        market,
        "--periods",
        str(args.days),
        "--save-journal",
        journal,
        "--save-summary",
        summary,
        "--save-modules",
        modules,
        "--save-report",
        report,
    ]
    if candidate:
        command[2:2] = ["--candidate", candidate]
    try:
        run_command(command, ROOT, quiet=args.quiet)
    except Exception as exc:
        return [
            {
                **{field: "" for field in FIELDS},
                "layer": "cashflow",
                "fixed": "yes",
                "strategy": tag,
                "mode": "cashflow_stop_maker_limit",
                "market": market,
                "source": archive_source(market),
                "status": "ERROR",
                "note": str(exc),
            }
        ]

    journal_rows = read_csv(os.path.join(ROOT, journal))
    data_start, data_end = minmax_times(journal_rows, ["signal_time", "order_start_time", "fill_time", "exit_time"])
    output = []
    for row in read_csv(os.path.join(ROOT, summary)):
        if row.get("mode") != "cashflow_stop":
            continue
        add_row(
            output,
            layer="cashflow",
            fixed="yes",
            asset="Portfolio",
            strategy=tag,
            mode="cashflow_stop_maker_limit",
            market=market,
            source=archive_source(market),
            data_start=data_start,
            data_end=data_end,
            trades=row["trades"],
            return_pct=row["total_return_pct"],
            profit_factor=row["profit_factor"],
            win_rate_pct=row["win_rate_pct"],
            expectancy_pct=row["expectancy_pct"],
            max_dd_pct=row["max_drawdown_pct"],
            exit_reasons=row["exit_reasons"],
            status="OK",
            note=f"hit_target={row['hit_target']}; stop={row['stop_reason']}; assets={row['asset_breakdown']}; report={report}",
        )
    return output


def gala_diagnostic_rows(args):
    if not args.include_diagnostics:
        return []
    journal = f"data/24h_snapshot_gala_diagnostic_journal_{args.date}.csv"
    summary = f"data/24h_snapshot_gala_diagnostic_summary_{args.date}.csv"
    report = f"strategies/24h-snapshot-gala-diagnostic-{args.date}.md"
    command = [
        sys.executable,
        "scripts/gala_rescue_24h_test.py",
        "--market",
        args.diagnostic_market,
        "--days",
        str(args.days),
        "--save-journal",
        journal,
        "--save-summary",
        summary,
        "--save-report",
        report,
    ]
    try:
        run_command(command, ROOT, quiet=args.quiet)
    except Exception as exc:
        return [
            {
                **{field: "" for field in FIELDS},
                "layer": "diagnostic",
                "fixed": "no",
                "strategy": "GALA diagnostics",
                "mode": "diagnostic_not_fixed",
                "market": args.diagnostic_market,
                "source": archive_source(args.diagnostic_market),
                "status": "ERROR",
                "note": str(exc),
            }
        ]

    output = []
    for row in read_csv(os.path.join(ROOT, summary)):
        accepted = int(float(row.get("accepted") or 0))
        is_base = row["strategy"] in {"GALA 7.3 base", "GALA 11.2 base"}
        if not is_base and accepted == 0:
            continue
        add_row(
            output,
            layer="diagnostic",
            fixed="no",
            asset="GALA",
            symbol="GALAUSDT",
            strategy=row["strategy"],
            mode="diagnostic_variant_maker_limit",
            market=args.diagnostic_market,
            source=archive_source(args.diagnostic_market),
            data_start=row["data_start"],
            data_end=row["data_end"],
            signals=row["signals"],
            filled=row["filled"],
            unfilled=row["unfilled"],
            trades=row["accepted"],
            return_pct=row["return_sum_pct"],
            profit_factor=row["profit_factor"],
            win_rate_pct=row["win_rate_pct"],
            expectancy_pct=row["expectancy_pct"],
            exit_reasons=row["exit_reasons"],
            status="DIAGNOSTIC",
            note=f"not fixed; report={report}",
        )
    return output


def write_report(path, rows, csv_path, generated_at):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# 24h Strategy Snapshot",
        "",
        f"Generated: {generated_at}",
        "",
        "Этот отчет специально разделяет разные смыслы `24 часа`: обычный backtest, maker-fill paper, strict-варианты и cashflow-обертки.",
        "",
        f"Status counts: `{dict(counts)}`",
        "",
        "| Layer | Fixed | Asset | Strategy | Mode | Market | Data start | Data end | Signals | Filled | Trades | Return | PF | DD | Note |",
        "|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    order = {
        "operational_backtest": 0,
        "core_paper": 1,
        "strict": 2,
        "cashflow": 3,
        "diagnostic": 4,
    }
    for row in sorted(rows, key=lambda item: (order.get(item["layer"], 99), item["asset"], item["strategy"], item["mode"])):
        lines.append(
            f"| {row['layer']} | {row['fixed']} | {row['asset']} | {row['strategy']} | {row['mode']} | "
            f"{row['market']} | {row['data_start']} | {row['data_end']} | {row['signals']} | {row['filled']} | "
            f"{row['trades']} | {fmt_pct(row['return_pct'])} | {fmt_num(row['profit_factor'])} | "
            f"{fmt_pct(row['max_dd_pct'])} | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Snapshot CSV: `{csv_path}`",
            "",
            "## Reading Rules",
            "",
            "- `operational_backtest`: обычный backtest по последнему полному дню futures archive.",
            "- `core_paper`: лимитный paper-fill; если нет сигналов, это не значит, что другой слой тоже пустой.",
            "- `strict`: зафиксированные strict-версии, выбранные отдельно.",
            "- `cashflow`: портфельная cashflow-обертка с остановкой после цели/стопа.",
            "- `diagnostic`: не зафиксированная рабочая стратегия, только проверка гипотез.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def backfill_missing_periods(rows):
    periods = {}
    for row in rows:
        if row["data_start"] and row["data_end"]:
            periods.setdefault(row["market"], (row["data_start"], row["data_end"]))

    for row in rows:
        if row["data_start"] and row["data_end"]:
            continue
        period = periods.get(row["market"])
        if not period:
            continue
        row["data_start"], row["data_end"] = period
        note = row["note"]
        suffix = "period inferred from same-market snapshot rows"
        row["note"] = f"{note}; {suffix}" if note else suffix


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Build explicit 24h snapshot for all fixed strategy layers.")
    parser.add_argument("--date", default=today)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--universe", default="data/operational_monitor_universe_2026-05-04.csv")
    parser.add_argument("--paper-market", choices=["futures_archive", "data_api_spot"], default="futures_archive")
    parser.add_argument("--strict-market", choices=["futures_archive", "data_api_spot"], default="data_api_spot")
    parser.add_argument("--diagnostic-market", choices=["futures_archive", "data_api_spot"], default="data_api_spot")
    parser.add_argument("--include-diagnostics", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--save", default=f"data/24h_strategy_snapshot_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/24h-strategy-snapshot-{today}.md")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).isoformat()
    rows = []
    rows.extend(operational_backtest_rows(args))
    rows.extend(core_paper_rows(args, args.paper_market))
    rows.extend(strict_rows(args))
    rows.extend(
        cashflow_rows(
            args,
            "gala20_spell80",
            "scripts/monthly_cashflow_5pct_fresh_strict_check.py",
            "data_api_spot",
            "cashflow1_gala20_spell80",
        )
    )
    rows.extend(
        cashflow_rows(
            args,
            "chz10_shib10_spell80",
            "scripts/monthly_cashflow_5pct_fresh_strict_check.py",
            "futures_archive",
            "cashflow2_chz10_shib10_spell80",
        )
    )
    rows.extend(
        cashflow_rows(
            args,
            None,
            "scripts/cashflow3_fresh_strict_check.py",
            "futures_archive",
            "cashflow3_one_rif_spell",
        )
    )
    rows.extend(gala_diagnostic_rows(args))
    backfill_missing_periods(rows)

    save_csv(os.path.join(ROOT, args.save), rows)
    write_report(os.path.join(ROOT, args.save_report), rows, args.save, generated_at)
    print(f"saved snapshot: {args.save}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
