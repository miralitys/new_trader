#!/usr/bin/env python3
"""Search shortlist tweaks that survive 1d/7d/30d/60d together.

This is intentionally stricter than `shortlist_24h_tweak_search.py`: a variant
is accepted only if the same parameters are positive on every requested window.
The script is still a research tool, not a live-trading guarantee.
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
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")
TWEAK_PATH = os.path.join(ROOT, "scripts", "shortlist_24h_tweak_search.py")


SHORTLIST = [
    {"coin": "CHZ", "symbol": "CHZUSDT", "kind": "single"},
    {"coin": "ANKR", "symbol": "ANKRUSDT", "kind": "single"},
    {"coin": "MANA", "symbol": "MANAUSDT", "kind": "single"},
    {"coin": "SPELL", "symbol": "SPELLUSDT", "kind": "single"},
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_73"},
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
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
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_pf(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def bars_for(bt, days):
    return int(days * bt.candles_per_day("1m"))


def slice_period(bt, candles, days):
    bars = bars_for(bt, days)
    if len(candles) < bars:
        raise RuntimeError(f"not enough candles for {days}d: {len(candles)} < {bars}")
    return candles[-bars:]


def spec_by_coin(cf, coin):
    for spec in cf.BEST_SPECS:
        if spec.get("coin") == coin and spec.get("kind") == "single":
            row = dict(spec)
            row["kind"] = "single"
            return row
    raise RuntimeError(f"single spec not found: {coin}")


def variant_key(variant):
    return tuple(sorted(variant.items()))


def variant_name(tweak, item, variant):
    if item["kind"] == "gala_112":
        return tweak.gala_112_name(variant)
    return tweak.variant_name(variant)


def variant_stream(tweak, cf, item):
    if item["kind"] == "single":
        return list(tweak.single_variants(spec_by_coin(cf, item["coin"])))
    if item["kind"] == "gala_73":
        return list(tweak.gala_73_variants())
    if item["kind"] == "gala_112":
        return list(tweak.gala_112_variants())
    raise ValueError(item["kind"])


def run_variant(tweak, bt, reinvest, multi, cf, paper, item, candles, variant):
    if item["kind"] == "single":
        spec = spec_by_coin(cf, item["coin"])
        return tweak.run_single(
            bt,
            reinvest,
            multi,
            cf,
            paper,
            candles,
            spec,
            variant,
            f"{item['coin']} {spec['direction'].upper()} multi-window",
        )
    if item["kind"] == "gala_73":
        spec = {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_73", "direction": "short"}
        return tweak.run_single(
            bt,
            reinvest,
            multi,
            cf,
            paper,
            candles,
            spec,
            variant,
            "GALA 7.3 multi-window",
        )
    if item["kind"] == "gala_112":
        return tweak.run_gala_112(bt, reinvest, multi, paper, candles, variant)
    raise ValueError(item["kind"])


def summarize(tweak, rows):
    summary = tweak.summarize(rows)
    accepted_rows = [row for row in rows if row.get("portfolio_status") == "accepted"]
    summary["exit_reasons"] = ";".join(
        f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted_rows).items() if key
    )
    return summary


def min_trades_for(days, min_trades_1d):
    if days <= 1:
        return min_trades_1d
    if days <= 7:
        return max(3, min_trades_1d * 2)
    if days <= 30:
        return max(8, min_trades_1d * 4)
    return max(12, min_trades_1d * 6)


def passes_window(summary, days, min_trades_1d, min_pf):
    return (
        summary["accepted"] >= min_trades_for(days, min_trades_1d)
        and summary["return_sum_pct"] > 0
        and summary["profit_factor"] >= min_pf
    )


def variant_score(period_summaries):
    returns = [row["return_sum_pct"] for row in period_summaries.values()]
    pfs = [row["profit_factor"] if not math.isinf(row["profit_factor"]) else 10.0 for row in period_summaries.values()]
    trades = [row["accepted"] for row in period_summaries.values()]
    # Prefer the worst window being healthy over one large lucky return.
    return (
        min(returns) * 5.0
        + sum(returns) / len(returns)
        + min(pfs) * 2.0
        + math.log1p(sum(trades)) * 0.25
    )


def flatten_row(item, strategy, variant_label, verdict, score, period_summaries):
    row = {
        "coin": item["coin"],
        "symbol": item["symbol"],
        "strategy": strategy,
        "variant": variant_label,
        "verdict": verdict,
        "score": score,
    }
    for days, summary in sorted(period_summaries.items()):
        prefix = f"{days}d"
        row[f"{prefix}_return_sum_pct"] = summary["return_sum_pct"]
        row[f"{prefix}_profit_factor"] = summary["profit_factor"]
        row[f"{prefix}_win_rate_pct"] = summary["win_rate_pct"]
        row[f"{prefix}_expectancy_pct"] = summary["expectancy_pct"]
        row[f"{prefix}_accepted"] = summary["accepted"]
        row[f"{prefix}_exit_reasons"] = summary["exit_reasons"]
    return row


def strategy_name(cf, item):
    if item["kind"] == "single":
        spec = spec_by_coin(cf, item["coin"])
        return f"{item['coin']} {spec['direction'].upper()} Best"
    if item["kind"] == "gala_73":
        return "GALA 7.3 protected"
    if item["kind"] == "gala_112":
        return "GALA 11.2 watchlist"
    raise ValueError(item["kind"])


def write_report(path, periods, best_rows, pass_rows, fallback_rows, diagnostics, summary_path, pass_path):
    lines = [
        "# Shortlist Multi-Window Tune Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Ищем одну и ту же настройку, которая одновременно дает плюс на 1d / 7d / 30d / 60d.",
        "Это не доказательство будущей прибыли, а фильтр против грубой подгонки под одни сутки.",
        "",
        "## Best Per Strategy",
        "",
        "| Coin | Strategy | Verdict | Variant | "
        + " | ".join(f"{period}d Return / PF / Trades" for period in periods)
        + " |",
        "|---|---|---|---|" + "|".join("---:" for _ in periods) + "|",
    ]
    for row in best_rows:
        metrics = []
        for period in periods:
            metrics.append(
                f"{fmt_pct(row.get(f'{period}d_return_sum_pct'))} / "
                f"{fmt_pf(row.get(f'{period}d_profit_factor'))} / "
                f"{row.get(f'{period}d_accepted', '')}"
            )
        lines.append(
            f"| {row['coin']} | {row['strategy']} | {row['verdict']} | {row['variant']} | "
            + " | ".join(metrics)
            + " |"
        )

    if pass_rows:
        lines.extend(
            [
                "",
                "## Survivors",
                "",
                f"Найдено устойчивых кандидатов: {len(pass_rows)}.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Survivors",
                "",
                "Устойчивых кандидатов, которые прошли все окна, не найдено.",
            ]
        )

    lines.extend(["", "## Diagnostics", "", "| Symbol | Status | Candles | Start | End | Error |", "|---|---:|---:|---|---|---|"])
    for row in diagnostics:
        lines.append(
            f"| {row['symbol']} | {row['status']} | {row.get('candles', '')} | "
            f"{row.get('start', '')} | {row.get('end', '')} | {row.get('error', '')} |"
        )
    lines.extend(["", "## Files", "", f"- Best CSV: `{summary_path}`", f"- Passing CSV: `{pass_path}`"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["data_api_spot", "futures_archive"], default="data_api_spot")
    parser.add_argument("--periods", nargs="*", type=int, default=[1, 7, 30, 60])
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--min-trades-1d", type=int, default=1)
    parser.add_argument("--min-pf", type=float, default=1.01)
    parser.add_argument("--max-variants", type=int, default=0, help="Debug cap per strategy; 0 means all.")
    parser.add_argument("--save-best", default="data/shortlist_multi_window_tune_best.csv")
    parser.add_argument("--save-passing", default="data/shortlist_multi_window_tune_passing.csv")
    parser.add_argument("--save-diagnostics", default="data/shortlist_multi_window_tune_diagnostics.csv")
    parser.add_argument("--save-report", default="strategies/shortlist-multi-window-tune-search.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    tweak = load_module("shortlist_24h_tweak_search", TWEAK_PATH)

    periods = sorted(set(args.periods))
    max_days = max(periods)
    diagnostics = []
    best_rows = []
    pass_rows = []
    fallback_rows = []
    candle_cache = {}

    for item in SHORTLIST:
        symbol = item["symbol"]
        name = strategy_name(cf, item)
        print(f"search {name} {symbol}", flush=True)
        try:
            if symbol not in candle_cache:
                _full, run_candles = tweak.fetch_candles(
                    bt, reinvest, multi, symbol, max_days, args.warmup_days, args.market
                )
                candle_cache[symbol] = run_candles
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
            period_candles = {
                period: slice_period(bt, candle_cache[symbol], period)
                for period in periods
            }
            variants = variant_stream(tweak, cf, item)
            if args.max_variants > 0:
                variants = variants[: args.max_variants]

            survivors = []
            best_any = None
            best_any_tuple = None
            checked = 0

            for variant in variants:
                checked += 1
                period_summaries = {}
                positive_windows = 0
                failed = False
                for period in periods:
                    journal = run_variant(tweak, bt, reinvest, multi, cf, paper, item, period_candles[period], variant)
                    summary = summarize(tweak, journal)
                    period_summaries[period] = summary
                    if passes_window(summary, period, args.min_trades_1d, args.min_pf):
                        positive_windows += 1
                    else:
                        failed = True
                        # Prune early. A strategy must pass every window.
                        break

                # For diagnostics, fill missing period results only for promising failed variants.
                if failed and positive_windows >= max(1, len(periods) - 1):
                    for period in periods:
                        if period in period_summaries:
                            continue
                        journal = run_variant(tweak, bt, reinvest, multi, cf, paper, item, period_candles[period], variant)
                        period_summaries[period] = summarize(tweak, journal)

                if len(period_summaries) == len(periods):
                    score = variant_score(period_summaries)
                    full_row = flatten_row(
                        item,
                        name,
                        variant_name(tweak, item, variant),
                        "passed" if not failed else "near_miss",
                        score,
                        period_summaries,
                    )
                    if not failed:
                        survivors.append(full_row)
                    fallback_tuple = (
                        positive_windows,
                        min(row["return_sum_pct"] for row in period_summaries.values()),
                        score,
                    )
                    if best_any is None or fallback_tuple > best_any_tuple:
                        best_any = full_row
                        best_any_tuple = fallback_tuple

            if survivors:
                survivors.sort(key=lambda row: float(row["score"]), reverse=True)
                best = dict(survivors[0])
                best["verdict"] = "passed_all_windows"
                pass_rows.extend(survivors)
            elif best_any is not None:
                best = dict(best_any)
                best["verdict"] = "no_full_pass_best_near_miss"
                fallback_rows.append(best)
            else:
                best = {
                    "coin": item["coin"],
                    "symbol": symbol,
                    "strategy": name,
                    "variant": "",
                    "verdict": "no_candidates",
                    "score": "",
                }
            best_rows.append(best)
            print(
                f"{name}: checked={checked} pass={len(survivors)} best={best['verdict']} {best.get('variant', '')}",
                flush=True,
            )
        except Exception as exc:
            diagnostics.append({"symbol": symbol, "status": "error", "candles": "", "start": "", "end": "", "error": str(exc)})
            best_rows.append(
                {
                    "coin": item["coin"],
                    "symbol": symbol,
                    "strategy": name,
                    "variant": "",
                    "verdict": "error",
                    "score": "",
                }
            )

    period_fields = []
    for period in periods:
        prefix = f"{period}d"
        period_fields.extend(
            [
                f"{prefix}_return_sum_pct",
                f"{prefix}_profit_factor",
                f"{prefix}_win_rate_pct",
                f"{prefix}_expectancy_pct",
                f"{prefix}_accepted",
                f"{prefix}_exit_reasons",
            ]
        )
    fields = ["coin", "symbol", "strategy", "variant", "verdict", "score"] + period_fields
    diagnostic_fields = ["symbol", "status", "candles", "start", "end", "error"]

    save_csv(args.save_best, best_rows, fields)
    save_csv(args.save_passing, pass_rows, fields)
    save_csv(args.save_diagnostics, diagnostics, diagnostic_fields)
    write_report(args.save_report, periods, best_rows, pass_rows, fallback_rows, diagnostics, args.save_best, args.save_passing)

    print("best variants:")
    for row in best_rows:
        metrics = []
        for period in periods:
            value = row.get(f"{period}d_return_sum_pct", "")
            pf = row.get(f"{period}d_profit_factor", "")
            accepted = row.get(f"{period}d_accepted", "")
            metrics.append(f"{period}d={fmt_pct(value)} PF={fmt_pf(pf)} n={accepted}")
        print(f"{row['coin']} {row['strategy']} {row['verdict']}: {row.get('variant', '')} | " + " | ".join(metrics))
    print(f"report: {args.save_report}")


if __name__ == "__main__":
    main()
