#!/usr/bin/env python3
"""Run a fresh 24h paper-execution rescue check for GALA 7.3 and 11.2.

This is intentionally separate from the fixed strategy files. It compares the
current paper execution against defensive variants so we can see whether the
idea is worth promoting into a named strategy later.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")


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
    return f"{value:+.2f}%"


def fmt_pf(value):
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def fetch_fresh_candles(bt, reinvest, multi, symbol, days, warmup_days, market):
    candles = bt.fetch_klines(market, symbol, days + warmup_days, "1m")
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    bars = days * bt.candles_per_day("1m")
    return candles, candles[-bars:]


def make_execution_args(paper, multi, reinvest, strategy, symbol, execution, overrides=None):
    args = multi.make_strategy_args(reinvest, strategy, symbol)
    paper.apply_execution(args, **execution)
    for key, value in (overrides or {}).items():
        setattr(args, key, value)
    return args


def apply_score_filter(rows, direction, score_min=None, score_max=None):
    blocked = 0
    score_key = f"{direction}_score"
    signal_key = f"{direction}_signal"
    for row in rows:
        if not row.get(signal_key):
            continue
        score = row.get(score_key)
        if score is None:
            row[signal_key] = False
            blocked += 1
            continue
        if score_min is not None and score < score_min:
            row[signal_key] = False
            blocked += 1
            continue
        if score_max is not None and score > score_max:
            row[signal_key] = False
            blocked += 1
            continue
    return blocked


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def custom_regime_ok(row, return_7d_max):
    return (
        in_range(row.get("atr_pct"), 0.0025, None)
        and in_range(row.get("dist_ema200"), -0.015, 0.015)
        and in_range(row.get("return_7d"), -0.40, return_7d_max)
    )


def apply_strategy_signals(multi, rows, strategy, return_7d_max=None):
    if return_7d_max is None:
        multi.apply_strategy_signals(rows, strategy)
        return

    for row in rows:
        regime_passed = custom_regime_ok(row, return_7d_max)
        if strategy == "7.3":
            row["long_signal"] = False
            row["short_signal"] = row.get("short_score", 0.0) >= 40 and regime_passed
        elif strategy == "10":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= 50
                and bool(row.get("smart_long_filter"))
                and regime_passed
            )
            row["short_signal"] = False
        else:
            raise ValueError(strategy)


def apply_cooldown(rows, bad_event_cooldown_min):
    """Post-process journal rows to approximate a live pause after bad exits."""
    if not bad_event_cooldown_min:
        return rows, 0

    kept = []
    skipped = 0
    pause_until_ms = None
    for row in rows:
        start_ms = paper_time_to_ms(row["order_start_time"])
        if pause_until_ms is not None and start_ms < pause_until_ms:
            skipped += 1
            row = dict(row)
            row["portfolio_status"] = "skipped_cooldown"
            kept.append(row)
            continue

        kept.append(row)
        if row.get("order_status") != "filled":
            continue
        if row.get("portfolio_status") not in ("accepted", "candidate"):
            continue
        net = float(row["portfolio_return_pct"] or row["net_return_pct"] or 0.0)
        if row.get("reason") in {"stop_loss", "time_stop"} and net < 0:
            exit_ms = paper_time_to_ms(row["exit_time"])
            pause_until_ms = exit_ms + bad_event_cooldown_min * 60_000
    return kept, skipped


def paper_time_to_ms(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def run_single_variant(
    bt,
    paper,
    multi,
    reinvest,
    candles,
    permissions,
    variant,
    execution,
):
    rows = [dict(row) for row in candles]
    apply_strategy_signals(
        multi,
        rows,
        "7.3",
        variant.get("short_return_7d_max", variant.get("return_7d_max")),
    )
    mtf_stats = Counter()
    if variant.get("htf") == "1h":
        mtf_stats.update(mtf_module.apply_htf_filter(rows, permissions))
    score_blocked = apply_score_filter(
        rows,
        "short",
        variant.get("short_score_min"),
        variant.get("short_score_max"),
    )
    args = make_execution_args(
        paper,
        multi,
        reinvest,
        "7.3",
        "GALAUSDT",
        execution,
        variant.get("arg_overrides"),
    )
    journal = paper.journal_loop(
        bt,
        rows,
        args,
        {
            "asset": "GALA",
            "symbol": "GALAUSDT",
            "strategy": variant["name"],
            "module": "7.3 short",
        },
    )
    journal, cooldown_skipped = apply_cooldown(journal, variant.get("cooldown_min"))
    return journal, {
        "mtf_blocked": mtf_stats.get("mtf_blocked_total", 0),
        "score_blocked": score_blocked,
        "cooldown_skipped": cooldown_skipped,
    }


def run_112_variant(
    bt,
    paper,
    multi,
    reinvest,
    candles,
    permissions,
    variant,
    execution,
):
    all_rows = []
    extra = Counter()

    short_rows = [dict(row) for row in candles]
    apply_strategy_signals(
        multi,
        short_rows,
        "7.3",
        variant.get("short_return_7d_max", variant.get("return_7d_max")),
    )
    if variant.get("htf") == "1h":
        extra.update(mtf_module.apply_htf_filter(short_rows, permissions))
    extra["score_blocked"] += apply_score_filter(
        short_rows,
        "short",
        variant.get("short_score_min"),
        variant.get("short_score_max"),
    )
    short_args = make_execution_args(
        paper,
        multi,
        reinvest,
        "7.3",
        "GALAUSDT",
        execution,
        variant.get("short_arg_overrides") or variant.get("arg_overrides"),
    )
    all_rows.extend(
        paper.journal_loop(
            bt,
            short_rows,
            short_args,
            {
                "asset": "GALA",
                "symbol": "GALAUSDT",
                "strategy": variant["name"],
                "module": "7.3 short",
            },
            portfolio_weight=variant.get("short_weight", 1.5 * 0.9),
        )
    )

    long_rows = [dict(row) for row in candles]
    apply_strategy_signals(
        multi,
        long_rows,
        "10",
        variant.get("long_return_7d_max", variant.get("return_7d_max")),
    )
    if variant.get("htf") == "1h":
        extra.update(mtf_module.apply_htf_filter(long_rows, permissions))
    long_args = make_execution_args(
        paper,
        multi,
        reinvest,
        "10",
        "GALAUSDT",
        execution,
        variant.get("long_arg_overrides") or variant.get("arg_overrides"),
    )
    all_rows.extend(
        paper.journal_loop(
            bt,
            long_rows,
            long_args,
            {
                "asset": "GALA",
                "symbol": "GALAUSDT",
                "strategy": variant["name"],
                "module": "10 long",
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

    all_rows, cooldown_skipped = apply_cooldown(all_rows, variant.get("cooldown_min"))
    extra["cooldown_skipped"] = cooldown_skipped
    return all_rows, {
        "mtf_blocked": extra.get("mtf_blocked_total", 0),
        "score_blocked": extra.get("score_blocked", 0),
        "cooldown_skipped": extra.get("cooldown_skipped", 0),
    }


def summarize_variant(name, rows, extra, data_start, data_end, candle_count):
    accepted = [row for row in rows if row.get("portfolio_status") == "accepted"]
    filled = [row for row in rows if row.get("order_status") == "filled"]
    unfilled = [row for row in rows if row.get("order_status") == "unfilled"]
    skipped_overlap = [row for row in rows if row.get("portfolio_status") == "skipped_overlap"]
    skipped_cooldown = [row for row in rows if row.get("portfolio_status") == "skipped_cooldown"]
    returns = [float(row["portfolio_return_pct"]) for row in accepted if row.get("portfolio_return_pct") not in ("", None)]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    return_sum = sum(returns)
    return {
        "strategy": name,
        "candles": candle_count,
        "data_start": data_start,
        "data_end": data_end,
        "signals": len(rows),
        "filled": len(filled),
        "unfilled": len(unfilled),
        "accepted": len(accepted),
        "skipped_overlap": len(skipped_overlap),
        "skipped_cooldown": len(skipped_cooldown),
        "fill_rate_pct": len(filled) / len(rows) * 100.0 if rows else 0.0,
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "return_sum_pct": return_sum,
        "expectancy_pct": return_sum / len(accepted) if accepted else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0),
        "exit_reasons": ";".join(f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted).items() if key),
        "mtf_blocked": extra.get("mtf_blocked", 0),
        "score_blocked": extra.get("score_blocked", 0),
        "cooldown_skipped": extra.get("cooldown_skipped", 0),
    }


def write_report(path, rows, journal_path, summary_path):
    lines = [
        "# GALA Rescue Paper Test",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Variant | Signals | Filled | Accepted | Return | PF | Win Rate | Expectancy | Exit Reasons | Blocked |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        blocked = int(row["mtf_blocked"]) + int(row["score_blocked"]) + int(row["cooldown_skipped"])
        lines.append(
            f"| {row['strategy']} | {row['signals']} | {row['filled']} | {row['accepted']} | "
            f"{fmt_pct(row['return_sum_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{row['win_rate_pct']:.2f}% | {fmt_pct(row['expectancy_pct'])} | "
            f"{row['exit_reasons']} | {blocked} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Journal CSV: `{journal_path}`",
            f"- Summary CSV: `{summary_path}`",
            "",
            "## Notes",
            "",
            "- `R 1h` means the 1m signal is allowed only after a closed 1h candle confirms the direction.",
            "- `short_score >= 60` is a defensive short filter: weak short signals are ignored.",
            "- This is a rolling paper-execution check with maker-limit fill validation.",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="data_api_spot", choices=["data_api_spot", "futures_archive", "futures_global", "spot_global", "spot_us"])
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--save-journal", default="data/gala_rescue_24h_journal.csv")
    parser.add_argument("--save-summary", default="data/gala_rescue_24h_summary.csv")
    parser.add_argument("--save-report", default="strategies/GALA/gala-rescue-24h-paper-test.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    global mtf_module
    mtf_module = load_module("gala_mtf_regime_backtest", MTF_PATH)

    full_candles, run_candles = fetch_fresh_candles(bt, reinvest, multi, "GALAUSDT", args.days, args.warmup_days, args.market)
    base_args = multi.make_strategy_args(reinvest, "7.3", "GALAUSDT")
    permissions_1h = mtf_module.build_htf_permissions(bt, full_candles, base_args, "1h")
    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": args.fee_pct,
        "slippage_pct": args.slippage_pct,
        "limit_offset": args.limit_entry_offset_pct,
        "timeout_min": args.limit_entry_timeout_min,
    }

    variants = [
        {"name": "GALA 7.3 base", "kind": "single"},
        {"name": "GALA 7.3R short_score>=50", "kind": "single", "short_score_min": 50},
        {"name": "GALA 7.3R short_score>=60", "kind": "single", "short_score_min": 60},
        {"name": "GALA 7.3R short_score>=60 ret7<=5", "kind": "single", "short_score_min": 60, "short_return_7d_max": 0.05},
        {"name": "GALA 7.3R short_score>=60 fast60", "kind": "single", "short_score_min": 60, "arg_overrides": {"short_time_stop_min": 60, "time_stop_min": 60}},
        {"name": "GALA 7.3R 1h", "kind": "single", "htf": "1h"},
        {"name": "GALA 7.3R 1h score 50-79", "kind": "single", "htf": "1h", "short_score_min": 50, "short_score_max": 79},
        {"name": "GALA 7.3 diagnostic ret7<=25", "kind": "single", "return_7d_max": 0.25},
        {"name": "GALA 7.3 diagnostic ret7<=25 score 50-79", "kind": "single", "return_7d_max": 0.25, "short_score_min": 50, "short_score_max": 79},
        {"name": "GALA 7.3R ret7<=25 1h score 50-79", "kind": "single", "return_7d_max": 0.25, "htf": "1h", "short_score_min": 50, "short_score_max": 79},
        {"name": "GALA 7.3R 1h short_score>=60", "kind": "single", "htf": "1h", "short_score_min": 60},
        {
            "name": "GALA 7.3R 1h score 50-79 fast",
            "kind": "single",
            "htf": "1h",
            "short_score_min": 50,
            "short_score_max": 79,
            "arg_overrides": {"short_sl_pct": 0.020, "short_time_stop_min": 60, "time_stop_min": 60},
        },
        {"name": "GALA 11.2 base", "kind": "112"},
        {"name": "GALA 11.2R short_score>=50 no x1.5", "kind": "112", "short_score_min": 50, "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R short_score>=60 no x1.5", "kind": "112", "short_score_min": 60, "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R short_score>=60 ret7<=5 no x1.5", "kind": "112", "short_score_min": 60, "short_return_7d_max": 0.05, "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R short_score>=60 keep x1.5", "kind": "112", "short_score_min": 60, "short_weight": 1.5 * 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R 1h", "kind": "112", "htf": "1h"},
        {"name": "GALA 11.2R 1h no x1.5", "kind": "112", "htf": "1h", "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R 1h short score 50-79", "kind": "112", "htf": "1h", "short_score_min": 50, "short_score_max": 79, "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2 diagnostic ret7<=25", "kind": "112", "return_7d_max": 0.25},
        {"name": "GALA 11.2 diagnostic ret7<=25 short score 50-79", "kind": "112", "return_7d_max": 0.25, "short_score_min": 50, "short_score_max": 79, "short_weight": 0.9, "long_weight": 0.9},
        {"name": "GALA 11.2R ret7<=25 1h no x1.5", "kind": "112", "return_7d_max": 0.25, "htf": "1h", "short_weight": 0.9, "long_weight": 0.9},
    ]

    all_journal = []
    summary = []
    data_start = run_candles[0]["open_time"] if run_candles else ""
    data_end = run_candles[-1]["close_time"] if run_candles else ""
    for variant in variants:
        if variant["kind"] == "single":
            journal_rows, extra = run_single_variant(bt, paper, multi, reinvest, run_candles, permissions_1h, variant, execution)
        else:
            journal_rows, extra = run_112_variant(bt, paper, multi, reinvest, run_candles, permissions_1h, variant, execution)
        all_journal.extend(journal_rows)
        summary.append(summarize_variant(variant["name"], journal_rows, extra, data_start, data_end, len(run_candles)))

    journal_fields = [
        "asset",
        "symbol",
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
    summary_fields = [
        "strategy",
        "candles",
        "data_start",
        "data_end",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "skipped_overlap",
        "skipped_cooldown",
        "fill_rate_pct",
        "win_rate_pct",
        "return_sum_pct",
        "expectancy_pct",
        "profit_factor",
        "exit_reasons",
        "mtf_blocked",
        "score_blocked",
        "cooldown_skipped",
    ]
    save_csv(args.save_journal, all_journal, journal_fields)
    save_csv(args.save_summary, summary, summary_fields)
    write_report(args.save_report, summary, args.save_journal, args.save_summary)

    print(f"data: {data_start} -> {data_end}, candles={len(run_candles)}")
    for row in summary:
        print(
            f"{row['strategy']}: signals={row['signals']} accepted={row['accepted']} "
            f"return={fmt_pct(row['return_sum_pct'])} PF={fmt_pf(row['profit_factor'])} "
            f"win={row['win_rate_pct']:.2f}% exp={fmt_pct(row['expectancy_pct'])} exits={row['exit_reasons']}"
        )
    print(f"report: {args.save_report}")


if __name__ == "__main__":
    main()
