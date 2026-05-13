#!/usr/bin/env python3
"""Search defensive tweaks for the strategies listed in "Лучшие стратегии".

This is not a parameter-optimization engine. It applies a small set of sane
rescue ideas to every fixed best strategy:

- stricter signal threshold;
- narrower return_7d regime;
- shorter time stop;
- higher-timeframe permission filter;
- for 11.2 portfolios, weaker/stricter short sleeve.

The goal is to find candidates worth deeper 30/90/365d validation, not to
declare a final winner from one short window.
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
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")
STRICT_SHORTLIST_PATH = os.path.join(
    ROOT, "data", "hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv"
)


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
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_pf(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_bounds(regime):
    if regime == "base":
        return {
            "atr_min": 0.0025,
            "dist_min": -0.015,
            "dist_max": 0.015,
            "ret_min": -0.40,
            "ret_max": 0.10,
        }
    if regime == "wide":
        return {
            "atr_min": 0.0025,
            "dist_min": -0.025,
            "dist_max": 0.025,
            "ret_min": -0.50,
            "ret_max": 0.20,
        }
    raise ValueError(regime)


def regime_ok(row, regime, return_7d_max=None, dist_abs_max=None):
    bounds = regime_bounds(regime)
    dist_min = -dist_abs_max if dist_abs_max is not None else bounds["dist_min"]
    dist_max = dist_abs_max if dist_abs_max is not None else bounds["dist_max"]
    ret_max = return_7d_max if return_7d_max is not None else bounds["ret_max"]
    return (
        in_range(row.get("atr_pct"), bounds["atr_min"], None)
        and in_range(row.get("dist_ema200"), dist_min, dist_max)
        and in_range(row.get("return_7d"), bounds["ret_min"], ret_max)
    )


def fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market):
    if market == "futures_archive":
        candles, _, _ = multi.fetch_klines_fast(symbol, days, warmup_days)
    else:
        candles = bt.fetch_klines(market, symbol, days + warmup_days, "1m")
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    bars = days * bt.candles_per_day("1m")
    return candles, candles[-bars:]


def apply_single_signals(rows, spec, variant):
    threshold = variant.get("threshold", spec["threshold"])
    regime = variant.get("regime", spec["regime"])
    direction = spec["direction"]
    ret_max = variant.get("return_7d_max")
    dist_abs_max = variant.get("dist_abs_max")
    for row in rows:
        passed = regime_ok(row, regime, ret_max, dist_abs_max)
        row["long_signal"] = False
        row["short_signal"] = False
        if direction == "long":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= threshold
                and bool(row.get("smart_long_filter"))
                and passed
            )
        elif direction == "short":
            row["short_signal"] = row.get("short_score", 0.0) >= threshold and passed
        else:
            raise ValueError(direction)


def apply_gala_template_signals(rows, template, variant):
    if template == "7.3":
        spec = {
            "direction": "short",
            "threshold": variant.get("short_threshold", 40),
            "regime": "base",
        }
        apply_single_signals(rows, spec, {"threshold": spec["threshold"], "return_7d_max": variant.get("short_return_7d_max")})
        return

    if template == "10":
        spec = {
            "direction": "long",
            "threshold": variant.get("long_threshold", 50),
            "regime": "base",
        }
        apply_single_signals(rows, spec, {"threshold": spec["threshold"], "return_7d_max": variant.get("long_return_7d_max")})
        return

    raise ValueError(template)


def apply_execution(paper, args, execution, overrides=None):
    paper.apply_execution(args, **execution)
    for key, value in (overrides or {}).items():
        setattr(args, key, value)
    return args


def maybe_apply_htf(mtf, rows, permissions):
    if permissions is None:
        return 0
    return mtf.apply_htf_filter(rows, permissions).get("mtf_blocked_total", 0)


def run_single_variant(bt, reinvest, multi, cf, paper, mtf, candles, permissions, spec, variant, execution):
    rows = [dict(row) for row in candles]
    apply_single_signals(rows, spec, variant)
    htf_blocked = maybe_apply_htf(mtf, rows, permissions if variant.get("htf") else None)
    args = cf.make_single_args(multi, reinvest, spec)
    arg_overrides = {
        "time_stop_min": variant.get("time_stop_min", spec["time_stop_min"]),
    }
    if spec["direction"] == "long":
        arg_overrides["long_time_stop_min"] = variant.get("time_stop_min", spec["time_stop_min"])
        arg_overrides["long_tp_pct"] = variant.get("tp_pct", spec["tp_pct"])
    else:
        arg_overrides["short_time_stop_min"] = variant.get("time_stop_min", spec["time_stop_min"])
        arg_overrides["short_tp_pct"] = variant.get("tp_pct", spec["tp_pct"])
    apply_execution(paper, args, execution, arg_overrides)
    journal = paper.journal_loop(
        bt,
        rows,
        args,
        {
            "asset": spec["coin"],
            "symbol": spec["symbol"],
            "strategy": spec["name"],
            "module": variant["name"],
        },
    )
    return journal, {"htf_blocked": htf_blocked}


def run_gala_single_variant(bt, reinvest, multi, paper, mtf, candles, permissions, spec, variant, execution):
    rows = [dict(row) for row in candles]
    apply_gala_template_signals(rows, spec["template"], variant)
    htf_blocked = maybe_apply_htf(mtf, rows, permissions if variant.get("htf") else None)
    args = multi.make_strategy_args(reinvest, spec["template"], spec["symbol"])
    apply_execution(paper, args, execution, variant.get("arg_overrides"))
    journal = paper.journal_loop(
        bt,
        rows,
        args,
        {
            "asset": spec["coin"],
            "symbol": spec["symbol"],
            "strategy": spec["name"],
            "module": variant["name"],
        },
    )
    return journal, {"htf_blocked": htf_blocked}


def run_112_variant(bt, reinvest, multi, paper, mtf, candles, permissions, spec, variant, execution):
    all_rows = []

    short_rows = [dict(row) for row in candles]
    apply_gala_template_signals(short_rows, "7.3", variant)
    short_blocked = maybe_apply_htf(mtf, short_rows, permissions if variant.get("htf") else None)
    short_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
    apply_execution(paper, short_args, execution, variant.get("short_arg_overrides"))
    all_rows.extend(
        paper.journal_loop(
            bt,
            short_rows,
            short_args,
            {
                "asset": spec["coin"],
                "symbol": spec["symbol"],
                "strategy": spec["name"],
                "module": variant["name"] + " short",
            },
            portfolio_weight=variant.get("short_weight", 1.5 * 0.9),
        )
    )

    long_rows = [dict(row) for row in candles]
    apply_gala_template_signals(long_rows, "10", variant)
    long_blocked = maybe_apply_htf(mtf, long_rows, permissions if variant.get("htf") else None)
    long_args = multi.make_strategy_args(reinvest, "10", spec["symbol"])
    apply_execution(paper, long_args, execution, variant.get("long_arg_overrides"))
    all_rows.extend(
        paper.journal_loop(
            bt,
            long_rows,
            long_args,
            {
                "asset": spec["coin"],
                "symbol": spec["symbol"],
                "strategy": spec["name"],
                "module": variant["name"] + " long",
            },
            portfolio_weight=variant.get("long_weight", 0.9),
        )
    )

    open_until = None
    for row in sorted(
        all_rows,
        key=lambda item: (
            paper.parse_time(item["order_start_time"]),
            paper.parse_time(item["signal_time"]),
            item["module"],
        ),
    ):
        if row["order_status"] != "filled":
            row["portfolio_status"] = "unfilled"
            continue
        entry_time = paper.parse_time(row["fill_time"])
        if open_until is not None and entry_time < open_until:
            row["portfolio_status"] = "skipped_overlap"
            continue
        row["portfolio_status"] = "accepted"
        open_until = paper.parse_time(row["exit_time"])
    return all_rows, {"htf_blocked": short_blocked + long_blocked}


def summarize_rows(spec, variant, rows, extra, data_start, data_end, candles_count):
    accepted = [row for row in rows if row.get("portfolio_status") == "accepted"]
    filled = [row for row in rows if row.get("order_status") == "filled"]
    unfilled = [row for row in rows if row.get("order_status") == "unfilled"]
    skipped_overlap = [row for row in rows if row.get("portfolio_status") == "skipped_overlap"]
    returns = [
        float(row["portfolio_return_pct"])
        for row in accepted
        if row.get("portfolio_return_pct") not in ("", None)
    ]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    total = sum(returns)
    pf = gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0)
    reasons = Counter(row.get("reason", "") for row in accepted)
    return {
        "coin": spec["coin"],
        "symbol": spec["symbol"],
        "strategy": spec["name"],
        "variant": variant["name"],
        "candles": candles_count,
        "data_start": data_start,
        "data_end": data_end,
        "signals": len(rows),
        "filled": len(filled),
        "unfilled": len(unfilled),
        "accepted": len(accepted),
        "skipped_overlap": len(skipped_overlap),
        "fill_rate_pct": len(filled) / len(rows) * 100.0 if rows else 0.0,
        "return_sum_pct": total,
        "profit_factor": pf,
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "expectancy_pct": total / len(accepted) if accepted else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in reasons.items() if key),
        "htf_blocked": extra.get("htf_blocked", 0),
    }


def core_specs(cf):
    specs = [
        {"coin": "GALA", "symbol": "GALAUSDT", "name": "GALA Minutka 7.3", "kind": "gala_single", "template": "7.3"},
        {"coin": "GALA", "symbol": "GALAUSDT", "name": "GALA Minutka 10", "kind": "gala_single", "template": "10"},
    ]
    for item in cf.BEST_SPECS:
        if item["kind"] == "gala_112":
            specs.append(
                {
                    "coin": item["coin"],
                    "symbol": item["symbol"],
                    "name": f"{item['coin']} Minutka 11.2",
                    "kind": "gala_112",
                }
            )
        else:
            row = dict(item)
            row["name"] = f"{item['coin']} {'LONG' if item['direction'] == 'long' else 'SHORT'} Best"
            row["kind"] = "single"
            specs.append(row)
    return specs


def variants_for(spec):
    if spec["kind"] == "single":
        threshold = spec["threshold"]
        base_ret = regime_bounds(spec["regime"])["ret_max"]
        shorter = max(30, int(spec["time_stop_min"] * 0.5))
        return [
            {"name": "base"},
            {"name": f"threshold>={threshold + 10}", "threshold": threshold + 10},
            {"name": f"threshold>={threshold + 20}", "threshold": threshold + 20},
            {"name": f"return_7d<={min(base_ret, 0.05):.2f}", "return_7d_max": min(base_ret, 0.05)},
            {"name": f"threshold+10 return_7d<=0.05", "threshold": threshold + 10, "return_7d_max": min(base_ret, 0.05)},
            {"name": f"time_stop {shorter}m", "time_stop_min": shorter},
            {"name": "1h filter", "htf": "1h"},
            {"name": "1h threshold+10", "htf": "1h", "threshold": threshold + 10},
        ]

    if spec["kind"] == "gala_single":
        if spec["template"] == "7.3":
            return [
                {"name": "base"},
                {"name": "short_score>=50", "short_threshold": 50},
                {"name": "short_score>=60", "short_threshold": 60},
                {"name": "short_score>=60 return_7d<=0.05", "short_threshold": 60, "short_return_7d_max": 0.05},
                {"name": "time_stop 60m", "arg_overrides": {"short_time_stop_min": 60, "time_stop_min": 60}},
                {"name": "1h filter", "htf": "1h"},
                {"name": "1h short_score>=60", "htf": "1h", "short_threshold": 60},
            ]
        return [
            {"name": "base"},
            {"name": "long_score>=60", "long_threshold": 60},
            {"name": "long_score>=70", "long_threshold": 70},
            {"name": "return_7d<=0.05", "long_return_7d_max": 0.05},
            {"name": "time_stop 45m", "arg_overrides": {"long_time_stop_min": 45, "time_stop_min": 45}},
            {"name": "1h filter", "htf": "1h"},
            {"name": "1h long_score>=60", "htf": "1h", "long_threshold": 60},
        ]

    if spec["kind"] == "gala_112":
        return [
            {"name": "base"},
            {"name": "short_score>=50 no x1.5", "short_threshold": 50, "short_weight": 0.9, "long_weight": 0.9},
            {"name": "short_score>=60 no x1.5", "short_threshold": 60, "short_weight": 0.9, "long_weight": 0.9},
            {
                "name": "short_score>=60 short_return_7d<=0.05 no x1.5",
                "short_threshold": 60,
                "short_return_7d_max": 0.05,
                "short_weight": 0.9,
                "long_weight": 0.9,
            },
            {"name": "long only", "short_threshold": 999, "short_weight": 0.0, "long_weight": 0.9},
            {"name": "1h filter", "htf": "1h"},
            {"name": "1h no x1.5", "htf": "1h", "short_weight": 0.9, "long_weight": 0.9},
            {"name": "1h short_score>=60", "htf": "1h", "short_threshold": 60, "short_weight": 0.9, "long_weight": 0.9},
        ]

    raise ValueError(spec["kind"])


def write_report(path, rows, best_rows, diagnostics, summary_path, diagnostics_path):
    lines = [
        "# Best Strategies Rescue Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Это первичный defensive-search по зафиксированным лучшим стратегиям. Он не является финальной оптимизацией.",
        "",
        "## Best Per Strategy",
        "",
        "| Coin | Strategy | Best Variant | Return | PF | Win | Accepted | Base Return | Verdict |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in best_rows:
        lines.append(
            f"| {row['coin']} | {row['strategy']} | {row['variant']} | "
            f"{fmt_pct(row['return_sum_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{float(row['win_rate_pct']):.2f}% | {row['accepted']} | "
            f"{fmt_pct(row['base_return_sum_pct'])} | {row['verdict']} |"
        )
    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            "| Symbol | Status | Error |",
            "|---|---|---|",
        ]
    )
    for row in diagnostics:
        lines.append(f"| {row['symbol']} | {row['status']} | {row.get('error', '')} |")
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
            f"- Diagnostics CSV: `{diagnostics_path}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--market", choices=["futures_archive", "data_api_spot"], default="futures_archive")
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--save-summary", default="data/best_strategy_rescue_summary.csv")
    parser.add_argument("--save-best", default="data/best_strategy_rescue_best.csv")
    parser.add_argument("--save-diagnostics", default="data/best_strategy_rescue_diagnostics.csv")
    parser.add_argument("--save-report", default="strategies/best-strategies-rescue-search.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    mtf = load_module("gala_mtf_regime_backtest", MTF_PATH)

    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": args.fee_pct,
        "slippage_pct": args.slippage_pct,
        "limit_offset": args.limit_entry_offset_pct,
        "timeout_min": args.limit_entry_timeout_min,
    }

    rows = []
    diagnostics = []
    candle_cache = {}
    permission_cache = {}

    for index, spec in enumerate(core_specs(cf), start=1):
        symbol = spec["symbol"]
        print(f"[{index}] {spec['name']} {symbol}", flush=True)
        try:
            if symbol not in candle_cache:
                full_candles, run_candles = fetch_candles(
                    bt, reinvest, multi, symbol, args.days, args.warmup_days, args.market
                )
                candle_cache[symbol] = (full_candles, run_candles)
                base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
                permission_cache[symbol] = mtf.build_htf_permissions(bt, full_candles, base_args, "1h")
            full_candles, run_candles = candle_cache[symbol]
            permissions = permission_cache[symbol]
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "ok",
                    "candles": len(run_candles),
                    "start": run_candles[0]["open_time"],
                    "end": run_candles[-1]["close_time"],
                    "error": "",
                }
            )
            for variant in variants_for(spec):
                if spec["kind"] == "single":
                    journal, extra = run_single_variant(
                        bt, reinvest, multi, cf, paper, mtf, run_candles, permissions, spec, variant, execution
                    )
                elif spec["kind"] == "gala_single":
                    journal, extra = run_gala_single_variant(
                        bt, reinvest, multi, paper, mtf, run_candles, permissions, spec, variant, execution
                    )
                elif spec["kind"] == "gala_112":
                    journal, extra = run_112_variant(
                        bt, reinvest, multi, paper, mtf, run_candles, permissions, spec, variant, execution
                    )
                else:
                    raise ValueError(spec["kind"])
                rows.append(
                    summarize_rows(
                        spec,
                        variant,
                        journal,
                        extra,
                        run_candles[0]["open_time"],
                        run_candles[-1]["close_time"],
                        len(run_candles),
                    )
                )
        except Exception as exc:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "error",
                    "candles": "",
                    "start": "",
                    "end": "",
                    "error": str(exc),
                }
            )

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["coin"], row["strategy"])].append(row)

    best_rows = []
    for key, items in sorted(grouped.items()):
        base = next((row for row in items if row["variant"] == "base"), None)
        viable = [
            row
            for row in items
            if row["accepted"] >= max(3, int((base or row)["accepted"] * 0.20))
        ]
        if not viable:
            viable = items
        best = sorted(
            viable,
            key=lambda row: (
                row["return_sum_pct"],
                row["profit_factor"] if not math.isinf(row["profit_factor"]) else 999.0,
                row["accepted"],
            ),
            reverse=True,
        )[0]
        out = dict(best)
        out["base_return_sum_pct"] = base["return_sum_pct"] if base else ""
        out["base_profit_factor"] = base["profit_factor"] if base else ""
        if best["return_sum_pct"] > 0 and (not base or best["return_sum_pct"] > base["return_sum_pct"]):
            out["verdict"] = "improved"
        elif best["return_sum_pct"] > 0:
            out["verdict"] = "already_plus"
        else:
            out["verdict"] = "still_minus"
        best_rows.append(out)

    summary_fields = [
        "coin",
        "symbol",
        "strategy",
        "variant",
        "candles",
        "data_start",
        "data_end",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "skipped_overlap",
        "fill_rate_pct",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
        "htf_blocked",
    ]
    best_fields = summary_fields + ["base_return_sum_pct", "base_profit_factor", "verdict"]
    diagnostic_fields = ["symbol", "status", "candles", "start", "end", "error"]
    save_csv(args.save_summary, rows, summary_fields)
    save_csv(args.save_best, best_rows, best_fields)
    save_csv(args.save_diagnostics, diagnostics, diagnostic_fields)
    write_report(args.save_report, rows, best_rows, diagnostics, args.save_summary, args.save_diagnostics)

    print("best variants:")
    for row in best_rows:
        print(
            f"{row['coin']} {row['strategy']} -> {row['variant']}: "
            f"{fmt_pct(row['return_sum_pct'])} PF={fmt_pf(row['profit_factor'])} "
            f"accepted={row['accepted']} ({row['verdict']})"
        )
    print(f"report: {args.save_report}")


if __name__ == "__main__":
    main()
