#!/usr/bin/env python3
"""Fresh strict maker-fill check for 5% monthly cashflow candidates.

This is not a new optimization. It takes fresh candles, records strict maker
limit fills, and then applies the fixed portfolio/cashflow layer.
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

INITIAL_BALANCE = 1000.0

CANDIDATES = {
    "gala20_spell80": {
        "label": "GALA 20% / SPELL 80%",
        "weights": {"GALA": 0.20, "SPELL": 0.80},
        "scale": 6.0,
        "loss_stop_pct": 0.35,
        "modules": [
            {"kind": "gala_112"},
            {"kind": "single", "symbol": "SPELLUSDT", "asset": "SPELL", "strategy": "SPELL SHORT Best"},
        ],
    },
    "chz10_shib10_spell80": {
        "label": "CHZ 10% / SHIB 10% / SPELL 80%",
        "weights": {"CHZ": 0.10, "SHIB": 0.10, "SPELL": 0.80},
        "scale": 10.0,
        "loss_stop_pct": 0.50,
        "modules": [
            {"kind": "single", "symbol": "CHZUSDT", "asset": "CHZ", "strategy": "CHZ LONG Best"},
            {"kind": "single", "symbol": "1000SHIBUSDT", "asset": "SHIB", "strategy": "SHIB LONG Best"},
            {"kind": "single", "symbol": "SPELLUSDT", "asset": "SPELL", "strategy": "SPELL SHORT Best"},
        ],
    },
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def fmt_money(value):
    if value in ("", None):
        return "n/a"
    return f"${float(value):.2f}"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def accepted_rows(rows):
    return [
        row
        for row in rows
        if row.get("order_status") == "filled"
        and row.get("portfolio_status") in {"candidate", "accepted"}
    ]


def row_exit_time(row):
    return parse_time(row.get("exit_time")) or parse_time(row.get("waited_until_time")) or parse_time(row.get("order_start_time"))


def row_portfolio_return_pct(row, scale, weights):
    base = float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0)
    sleeve_weight = weights.get(row["asset"], 0.0)
    return base * sleeve_weight * scale


def profit_factor(values):
    gross_win = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    if gross_loss:
        return gross_win / gross_loss
    return math.inf if gross_win else 0.0


def max_drawdown(equity_points):
    peak = equity_points[0] if equity_points else INITIAL_BALANCE
    dd = 0.0
    for value in equity_points:
        peak = max(peak, value)
        if peak:
            dd = max(dd, (peak - value) / peak * 100.0)
    return dd


def summarize_module(rows):
    accepted = accepted_rows(rows)
    filled = [row for row in rows if row.get("order_status") == "filled"]
    unfilled = [row for row in rows if row.get("order_status") == "unfilled"]
    returns = [float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0) for row in accepted]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    return {
        "signals": len(rows),
        "filled": len(filled),
        "unfilled": len(unfilled),
        "accepted": len(accepted),
        "skipped_overlap": sum(1 for row in rows if row.get("portfolio_status") == "skipped_overlap"),
        "fill_rate_pct": len(filled) / len(rows) * 100.0 if rows else 0.0,
        "return_sum_pct": sum(returns),
        "profit_factor": profit_factor(returns),
        "win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
        "expectancy_pct": sum(returns) / len(accepted) if accepted else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in Counter(row.get("reason", "") for row in accepted).most_common()),
    }


def simulate_portfolio(rows, scale, target_cash, loss_stop_pct, stop_enabled, weights):
    selected = sorted(accepted_rows(rows), key=lambda row: (row_exit_time(row), parse_time(row["fill_time"]), row["asset"]))
    equity = INITIAL_BALANCE
    equity_points = [equity]
    pnls = []
    returns = []
    reasons = Counter()
    assets = Counter()
    stop_reason = "period_end"
    stop_time = ""
    skipped_after_stop = 0
    target_balance = INITIAL_BALANCE + target_cash
    loss_floor = INITIAL_BALANCE * (1.0 - loss_stop_pct)

    for row in selected:
        if stop_enabled and stop_reason != "period_end":
            skipped_after_stop += 1
            continue
        ret_pct = row_portfolio_return_pct(row, scale, weights)
        before = equity
        equity *= 1.0 + ret_pct / 100.0
        pnl = equity - before
        pnls.append(pnl)
        returns.append(ret_pct)
        reasons[row.get("reason", "")] += 1
        assets[row["asset"]] += 1
        equity_points.append(equity)
        if stop_enabled and equity >= target_balance:
            stop_reason = "profit_target"
            stop_time = row["exit_time"]
        elif stop_enabled and equity <= loss_floor:
            stop_reason = "loss_stop"
            stop_time = row["exit_time"]

    withdrawal = max(0.0, equity - INITIAL_BALANCE)
    wins = [value for value in pnls if value > 0]
    return {
        "trades": len(pnls),
        "skipped_after_stop": skipped_after_stop,
        "total_return_pct": (equity / INITIAL_BALANCE - 1.0) * 100.0,
        "final_equity": equity,
        "withdrawal": withdrawal,
        "hit_target": withdrawal >= target_cash,
        "stop_reason": stop_reason,
        "stop_time": stop_time,
        "max_drawdown_pct": max_drawdown(equity_points),
        "profit_factor": profit_factor(pnls),
        "win_rate_pct": len(wins) / len(pnls) * 100.0 if pnls else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "exit_reasons": ";".join(f"{key}={value}" for key, value in reasons.most_common() if key),
        "asset_breakdown": ";".join(f"{key}={value}" for key, value in assets.most_common()),
    }


def build_period_journal(paper, bt, reinvest, multi, cf, days, warmup_days, execution, market, candidate):
    rows = []
    for module in candidate["modules"]:
        if module["kind"] == "gala_112":
            rows.extend(paper.build_gala_112_journal(bt, reinvest, multi, days, warmup_days, execution, market))
        elif module["kind"] == "single":
            rows.extend(
                paper.build_single_journal(
                    bt,
                    reinvest,
                    multi,
                    cf,
                    module["symbol"],
                    module["asset"],
                    module["strategy"],
                    days,
                    warmup_days,
                    execution,
                    market,
                )
            )
        else:
            raise ValueError(module["kind"])
    rows.sort(key=lambda row: (row["symbol"], parse_time(row["order_start_time"]), row["module"]))
    return rows


def write_report(path, summary_rows, module_rows, journal_path, summary_path, module_path, generated_at, args, candidate):
    periods = [int(row["days"]) for row in summary_rows if row["mode"] == "cashflow_stop"]
    lines = [
        "# Fresh Strict Check - Monthly Cashflow 5%",
        "",
        f"Generated: `{generated_at}`",
        "",
        f"Проверка фиксированного кандидата `{candidate['label']}`, scale `{args.scale:g}`, через strict maker-fill.",
        f"Monthly loss stop: `{args.loss_stop_pct:.0%}`. Target cash: `${args.target_cash:.2f}`.",
        "",
        "Сделка считается только если цена реально вернулась к лимитке. Вход: maker-limit, offset `0.05%`, timeout `1m`.",
        "",
        "## Portfolio Result",
        "",
        "| Period | Mode | Trades | Return | Final Equity | Withdrawal | Target $50 | MaxDD | PF | Win | Stop | Assets |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['days']}d | {row['mode']} | {row['trades']} | {fmt_pct(row['total_return_pct'])} | "
            f"{fmt_money(row['final_equity'])} | {fmt_money(row['withdrawal'])} | "
            f"{'yes' if row['hit_target'] else 'no'} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_num(row['profit_factor'])} | {fmt_pct(row['win_rate_pct'])} | "
            f"{row['stop_reason']} | {row['asset_breakdown']} |"
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
            "## Человеческий вывод",
            "",
        ]
    )
    continuous_by_days = {row["days"]: row for row in summary_rows if row["mode"] == "continuous"}
    cashflow_by_days = {row["days"]: row for row in summary_rows if row["mode"] == "cashflow_stop"}
    for days in sorted(cashflow_by_days):
        continuous = continuous_by_days.get(days)
        cashflow = cashflow_by_days[days]
        if continuous and cashflow["hit_target"] and continuous["total_return_pct"] < 0:
            lines.append(
                f"На `{days}d` видно главное: с остановкой после цели результат `{fmt_pct(cashflow['total_return_pct'])}`, "
                f"а если продолжать торговать без остановки - `{fmt_pct(continuous['total_return_pct'])}`. "
                "Значит profit-target shutdown является обязательной частью стратегии, а не косметикой."
            )
            lines.append("")
    cash_rows = [row for row in summary_rows if row["mode"] == "cashflow_stop"]
    bad = [row for row in cash_rows if not row["hit_target"]]
    if not bad:
        lines.append("На свежем strict maker-fill кандидат добрал `$50+` во всех проверенных окнах.")
    else:
        missed = ", ".join(f"{row['days']}d" for row in bad)
        lines.append(
            f"Кандидат не добрал `$50+` в окнах: {missed}. Это не обязательно ломает месячную идею, "
            "но показывает, что свежий участок нужно контролировать, а не включать стратегию вслепую."
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Journal CSV: `{journal_path}`",
            f"- Portfolio summary CSV: `{summary_path}`",
            f"- Module summary CSV: `{module_path}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Fresh strict maker-fill check for 5% cashflow candidates.")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), default="gala20_spell80")
    parser.add_argument("--market", choices=["futures_archive", "futures_global", "data_api_spot"], default="data_api_spot")
    parser.add_argument("--periods", nargs="*", type=int, default=[1, 7, 30])
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--scale", type=float, default=None)
    parser.add_argument("--target-cash", type=float, default=50.0)
    parser.add_argument("--loss-stop-pct", type=float, default=None)
    parser.add_argument("--save-journal", default=f"data/monthly_cashflow_5pct_fresh_strict_journal_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/monthly_cashflow_5pct_fresh_strict_summary_{today}.csv")
    parser.add_argument("--save-modules", default=f"data/monthly_cashflow_5pct_fresh_strict_modules_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/monthly-cashflow-5pct-fresh-strict-check-{today}.md")
    args = parser.parse_args()
    candidate = CANDIDATES[args.candidate]
    if args.scale is None:
        args.scale = candidate["scale"]
    if args.loss_stop_pct is None:
        args.loss_stop_pct = candidate["loss_stop_pct"]

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)

    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": args.fee_pct,
        "slippage_pct": args.slippage_pct,
        "limit_offset": args.limit_entry_offset_pct,
        "timeout_min": args.limit_entry_timeout_min,
    }

    all_journal = []
    summary_rows = []
    module_rows = []
    for days in sorted(args.periods):
        print(f"checking {days}d...", flush=True)
        period_rows = build_period_journal(paper, bt, reinvest, multi, cf, days, args.warmup_days, execution, args.market, candidate)
        for row in period_rows:
            row["days"] = days
            all_journal.append(row)

        grouped = defaultdict(list)
        for row in period_rows:
            grouped[(row["asset"], row["strategy"])].append(row)
        for (asset, strategy), rows in sorted(grouped.items()):
            module_rows.append({"days": days, "asset": asset, "strategy": strategy, **summarize_module(rows)})

        continuous = simulate_portfolio(period_rows, args.scale, args.target_cash, args.loss_stop_pct, stop_enabled=False, weights=candidate["weights"])
        summary_rows.append({"days": days, "mode": "continuous", **continuous})
        cashflow = simulate_portfolio(period_rows, args.scale, args.target_cash, args.loss_stop_pct, stop_enabled=True, weights=candidate["weights"])
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
        "skipped_overlap",
        "fill_rate_pct",
        "return_sum_pct",
        "profit_factor",
        "win_rate_pct",
        "expectancy_pct",
        "exit_reasons",
    ]
    save_csv(os.path.join(ROOT, args.save_journal), all_journal, journal_fields)
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_modules), module_rows, module_fields)
    write_report(
        args.save_report,
        summary_rows,
        module_rows,
        args.save_journal,
        args.save_summary,
        args.save_modules,
        datetime.now(timezone.utc).isoformat(),
        args,
        candidate,
    )
    print(f"saved journal: {args.save_journal}")
    print(f"saved summary: {args.save_summary}")
    print(f"saved modules: {args.save_modules}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
