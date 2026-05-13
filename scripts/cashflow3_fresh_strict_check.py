#!/usr/bin/env python3
"""Fresh strict maker-fill check for Minutka Cashflow 3.

Fixed strategy:
- ONE 12%
- RIF 12%
- SPELL 75%
- scale 5.5
- target cash $100
- loss stop 35%
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
RIF_ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")


WEIGHTS = {"ONE": 0.12, "RIF": 0.12, "SPELL": 0.75}
RIF_VARIANT = {
    "direction": "long",
    "threshold": 40,
    "regime": "wide",
    "volume_multiplier": 1.5,
    "atr_min_pct": 0.0015,
    "atr_max_pct": 0.025,
    "tp_pct": 0.010,
    "sl_pct": 0.060,
    "time_stop_min": 180,
    "weekly_loss_stop_pct": 0.02,
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    return f"{float(value):+.2f}%"


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_num(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def fetch_candles(bt, market, symbol, interval, days, warmup_days):
    candles = bt.fetch_klines(market, symbol, days + warmup_days, interval)
    if not candles:
        raise RuntimeError(f"no candles for {symbol} {interval}")
    bars = days * bt.candles_per_day(interval)
    return candles, candles[-bars:]


def add_indicators(bt, multi, reinvest, candles, symbol, interval, template="7.3"):
    args = multi.make_strategy_args(reinvest, template, symbol)
    args.interval = interval
    args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, args)


def build_one_112_journal(bt, reinvest, multi, paper, market, days, warmup_days, execution):
    full, candles = fetch_candles(bt, market, "ONEUSDT", "1m", days, warmup_days)
    add_indicators(bt, multi, reinvest, full, "ONEUSDT", "1m")
    candles = full[-days * bt.candles_per_day("1m") :]

    all_rows = []
    short_rows = [dict(row) for row in candles]
    multi.apply_strategy_signals(short_rows, "7.3")
    short_args = multi.make_strategy_args(reinvest, "7.3", "ONEUSDT")
    paper.apply_execution(short_args, **execution)
    all_rows.extend(
        paper.journal_loop(
            bt,
            short_rows,
            short_args,
            {
                "asset": "ONE",
                "symbol": "ONEUSDT",
                "strategy": "ONE 11.2",
                "module": "7.3 short x1.5",
            },
            portfolio_weight=1.5 * 0.9,
        )
    )

    long_rows = [dict(row) for row in candles]
    multi.apply_strategy_signals(long_rows, "10")
    long_args = multi.make_strategy_args(reinvest, "10", "ONEUSDT")
    paper.apply_execution(long_args, **execution)
    all_rows.extend(
        paper.journal_loop(
            bt,
            long_rows,
            long_args,
            {
                "asset": "ONE",
                "symbol": "ONEUSDT",
                "strategy": "ONE 11.2",
                "module": "10 long",
            },
            portfolio_weight=0.9,
        )
    )

    open_until = None
    for row in sorted(all_rows, key=lambda item: (parse_time(item["order_start_time"]), item["module"])):
        if row["order_status"] != "filled":
            row["portfolio_status"] = "unfilled"
            continue
        entry_time = parse_time(row["fill_time"])
        if open_until is not None and entry_time < open_until:
            row["portfolio_status"] = "skipped_overlap"
            continue
        row["portfolio_status"] = "accepted"
        open_until = parse_time(row["exit_time"])
    return all_rows


def build_spell_journal(bt, reinvest, multi, cf, paper, market, days, warmup_days, execution):
    return paper.build_single_journal(
        bt,
        reinvest,
        multi,
        cf,
        "SPELLUSDT",
        "SPELL",
        "SPELL SHORT Best",
        days,
        warmup_days,
        execution,
        market,
    )


def build_rif_5m_journal(bt, reinvest, multi, paper, adapt, market, days, warmup_days, execution):
    full, candles = fetch_candles(bt, market, "RIFUSDT", "5m", days, warmup_days)
    add_indicators(bt, multi, reinvest, full, "RIFUSDT", "5m", template="10")
    candles = full[-days * bt.candles_per_day("5m") :]
    rows = [dict(row) for row in candles]
    adapt.apply_variant_signals(rows, RIF_VARIANT)
    args = adapt.make_args(multi, reinvest, RIF_VARIANT, "RIFUSDT", "5m")
    paper.apply_execution(args, **execution)
    return paper.journal_loop(
        bt,
        rows,
        args,
        {
            "asset": "RIF",
            "symbol": "RIFUSDT",
            "strategy": "RIF 5m LONG Best",
            "module": "RIF 5m LONG Best",
        },
    )


def accepted_rows(rows):
    return [
        row
        for row in rows
        if row.get("order_status") == "filled"
        and row.get("portfolio_status") in {"candidate", "accepted"}
    ]


def row_exit_time(row):
    return parse_time(row.get("exit_time") or row.get("waited_until_time") or row["order_start_time"])


def profit_factor(values):
    gross_win = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    if gross_loss:
        return gross_win / gross_loss
    return math.inf if gross_win else 0.0


def max_drawdown(points):
    peak = points[0] if points else 1000.0
    dd = 0.0
    for value in points:
        peak = max(peak, value)
        dd = max(dd, (peak - value) / peak * 100.0 if peak else 0.0)
    return dd


def simulate(rows, scale, target_cash, loss_stop_pct, stop_enabled):
    equity = 1000.0
    equity_points = [equity]
    target_balance = equity + target_cash
    loss_floor = equity * (1.0 - loss_stop_pct)
    stop_reason = "period_end"
    stop_time = ""
    skipped_after_stop = 0
    returns = []
    pnls = []
    reasons = Counter()
    assets = Counter()

    for row in sorted(accepted_rows(rows), key=lambda item: (row_exit_time(item), parse_time(item["fill_time"]), item["asset"])):
        if stop_enabled and stop_reason != "period_end":
            skipped_after_stop += 1
            continue
        base_return = float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0)
        ret_pct = base_return * WEIGHTS[row["asset"]] * scale
        before = equity
        equity *= 1.0 + ret_pct / 100.0
        pnl = equity - before
        returns.append(ret_pct)
        pnls.append(pnl)
        equity_points.append(equity)
        reasons[row.get("reason", "")] += 1
        assets[row["asset"]] += 1
        if stop_enabled and equity >= target_balance:
            stop_reason = "profit_target"
            stop_time = row["exit_time"]
        elif stop_enabled and equity <= loss_floor:
            stop_reason = "loss_stop"
            stop_time = row["exit_time"]

    wins = [value for value in pnls if value > 0]
    return {
        "trades": len(pnls),
        "skipped_after_stop": skipped_after_stop,
        "total_return_pct": (equity / 1000.0 - 1.0) * 100.0,
        "final_equity": equity,
        "withdrawal": max(0.0, equity - 1000.0),
        "hit_target": equity >= target_balance,
        "stop_reason": stop_reason,
        "stop_time": stop_time,
        "max_drawdown_pct": max_drawdown(equity_points),
        "profit_factor": profit_factor(pnls),
        "win_rate_pct": len(wins) / len(pnls) * 100.0 if pnls else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in reasons.most_common() if key),
        "asset_breakdown": ";".join(f"{key}={value}" for key, value in assets.most_common()),
    }


def summarize_module(rows):
    filled = [row for row in rows if row.get("order_status") == "filled"]
    accepted = accepted_rows(rows)
    values = [float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0) for row in accepted]
    wins = [value for value in values if value > 0]
    return {
        "signals": len(rows),
        "filled": len(filled),
        "unfilled": sum(1 for row in rows if row.get("order_status") == "unfilled"),
        "accepted": len(accepted),
        "fill_rate_pct": len(filled) / len(rows) * 100.0 if rows else 0.0,
        "return_sum_pct": sum(values),
        "profit_factor": profit_factor(values),
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted).most_common()),
    }


def write_report(path, summary_rows, module_rows, journal_path, summary_path, modules_path, generated_at, target_cash):
    lines = [
        "# Cashflow 3 Fresh Strict Check",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Fixed strategy: `ONE 12% / RIF 12% / SPELL 75%`, scale `5.5`, strict maker-fill.",
        "",
        "| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target | MaxDD | PF | Win | Stop | Assets |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['days']}d | {row['mode']} | {row['trades']} | {fmt_pct(row['total_return_pct'])} | "
            f"{fmt_money(row['final_equity'])} | {fmt_money(row['withdrawal'])} | "
            f"{'yes' if row['hit_target'] else 'no'} `${target_cash:.0f}` | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_num(row['profit_factor'])} | "
            f"{fmt_pct(row['win_rate_pct'])} | {row['stop_reason']} | {row['asset_breakdown']} |"
        )
    lines.extend(
        [
            "",
            "## Module Detail",
            "",
            "| Period | Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Win | Exit Reasons |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in module_rows:
        lines.append(
            f"| {row['days']}d | {row['asset']} | {row['strategy']} | {row['signals']} | "
            f"{row['filled']} | {fmt_pct(row['fill_rate_pct'])} | {row['accepted']} | "
            f"{fmt_pct(row['return_sum_pct'])} | {fmt_num(row['profit_factor'])} | "
            f"{fmt_pct(row['win_rate_pct'])} | {row['exit_reasons']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Journal CSV: `{journal_path}`",
            f"- Summary CSV: `{summary_path}`",
            f"- Modules CSV: `{modules_path}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Fresh strict maker-fill check for Minutka Cashflow 3.")
    parser.add_argument("--market", choices=["futures_global", "futures_archive"], default="futures_global")
    parser.add_argument("--periods", nargs="*", type=int, default=[1])
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--scale", type=float, default=5.5)
    parser.add_argument("--target-cash", type=float, default=100.0)
    parser.add_argument("--loss-stop-pct", type=float, default=0.35)
    parser.add_argument("--save-journal", default=f"data/cashflow3_one_rif_spell_fresh_strict_journal_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/cashflow3_one_rif_spell_fresh_strict_summary_{today}.csv")
    parser.add_argument("--save-modules", default=f"data/cashflow3_one_rif_spell_fresh_strict_modules_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/Portfolio/cashflow-3-one-rif-spell-fresh-strict-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    adapt = load_module("rif_interval_adaptation_search", RIF_ADAPT_PATH)

    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": args.fee_pct,
        "slippage_pct": args.slippage_pct,
        "limit_offset": args.limit_entry_offset_pct,
        "timeout_min": args.limit_entry_timeout_min,
    }

    all_rows = []
    summary_rows = []
    module_rows = []
    for days in sorted(args.periods):
        print(f"checking {days}d...", flush=True)
        period_rows = []
        period_rows.extend(build_one_112_journal(bt, reinvest, multi, paper, args.market, days, args.warmup_days, execution))
        period_rows.extend(build_rif_5m_journal(bt, reinvest, multi, paper, adapt, args.market, days, args.warmup_days, execution))
        period_rows.extend(build_spell_journal(bt, reinvest, multi, cf, paper, args.market, days, args.warmup_days, execution))
        for row in period_rows:
            row["days"] = days
            all_rows.append(row)

        grouped = defaultdict(list)
        for row in period_rows:
            grouped[(row["asset"], row["strategy"])].append(row)
        for (asset, strategy), rows in sorted(grouped.items()):
            module_rows.append({"days": days, "asset": asset, "strategy": strategy, **summarize_module(rows)})

        continuous = simulate(period_rows, args.scale, args.target_cash, args.loss_stop_pct, stop_enabled=False)
        summary_rows.append({"days": days, "mode": "continuous", **continuous})
        cashflow = simulate(period_rows, args.scale, args.target_cash, args.loss_stop_pct, stop_enabled=True)
        summary_rows.append({"days": days, "mode": "cashflow_stop", **cashflow})

    journal_fields = [
        "days",
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
        "signal_time",
        "order_start_time",
        "order_open",
        "limit_price",
        "order_status",
        "fill_time",
        "fill_delay_min",
        "entry",
        "exit_time",
        "exit",
        "reason",
        "duration_min",
        "net_return_pct",
        "portfolio_return_pct",
        "waited_until_time",
        "long_score",
        "short_score",
        "atr_pct",
        "return_7d",
        "dist_ema200",
        "portfolio_weight",
    ]
    summary_fields = [
        "days",
        "mode",
        "trades",
        "skipped_after_stop",
        "total_return_pct",
        "final_equity",
        "withdrawal",
        "hit_target",
        "stop_reason",
        "stop_time",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
        "asset_breakdown",
    ]
    module_fields = [
        "days",
        "asset",
        "strategy",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "fill_rate_pct",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "exit_reasons",
    ]
    save_csv(os.path.join(ROOT, args.save_journal), all_rows, journal_fields)
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_modules), module_rows, module_fields)
    write_report(
        os.path.join(ROOT, args.save_report),
        summary_rows,
        module_rows,
        args.save_journal,
        args.save_summary,
        args.save_modules,
        datetime.now(timezone.utc).isoformat(),
        args.target_cash,
    )
    print(f"saved journal: {args.save_journal}")
    print(f"saved summary: {args.save_summary}")
    print(f"saved modules: {args.save_modules}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
