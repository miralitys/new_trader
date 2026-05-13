#!/usr/bin/env python3
"""Check the fixed MOVR/CHZ/MANA monthly cashflow portfolio."""

import argparse
import csv
import importlib.util
import os
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_PATH = os.path.join(ROOT, "scripts", "movr_monthly_4pct_portfolio_search.py")


def load_search_module():
    spec = importlib.util.spec_from_file_location("movr_monthly_4pct_portfolio_search", SEARCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if value == float("inf") else f"{value:.2f}"


def write_report(path, summary, monthly, monthly_csv):
    lines = [
        "# MOVR / CHZ / MANA Monthly 4% Fixed Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Фиксированная стратегия: `MOVR 50% / CHZ 25% / MANA 25%`, scale `2.5x`, monthly target `$40`, monthly loss stop `2%`.",
        "",
        "Проверка сделана на полных месяцах `2023-05` - `2026-04`.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Months | {summary['months']} |",
        f"| Months with $40+ | {summary['cash_hits']}/{summary['months']} |",
        f"| Positive months | {summary['positive_months']}/{summary['months']} |",
        f"| Negative months | {summary['negative_months']} |",
        f"| Net cashflow/result | {fmt_money(summary['net_result'])} |",
        f"| MaxDD | {fmt_pct(summary['max_drawdown_pct'])} |",
        f"| Profit Factor | {fmt_pf(summary['profit_factor'])} |",
        f"| Worst month | {fmt_money(summary['worst_month_pnl'])} |",
        f"| Best month | {fmt_money(summary['best_month_pnl'])} |",
        f"| Trades | {summary['trades']} |",
        "",
        "## Monthly",
        "",
        "| Month | PnL | Return | Withdrawal | End balance | Stop | Trades | Top coins |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in monthly:
        lines.append(
            f"| {row['month']} | {fmt_money(row['month_pnl'])} | {fmt_pct(row['month_return_pct'])} | "
            f"{fmt_money(row['withdrawal'])} | {fmt_money(row['end_after_withdraw'])} | "
            f"{row['stop_reason']} | {row['trades']} | `{row['top_coins']}` |"
        )
    lines.extend(["", "## Files", "", f"- Monthly CSV: `{monthly_csv}`", ""])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Check fixed MOVR/CHZ/MANA monthly portfolio.")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=1096)
    parser.add_argument("--warmup-days", type=int, default=120)
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--best-trades", default="data/cashflow_portfolio_best_trades_35m.csv")
    parser.add_argument("--scale", type=float, default=2.5)
    parser.add_argument("--target-pct", type=float, default=0.04)
    parser.add_argument("--loss-stop-pct", type=float, default=0.02)
    parser.add_argument("--save-monthly", default="data/movr_chz_mana_monthly_4pct_fixed_35m_monthly_2026-05-08.csv")
    parser.add_argument("--save-report", default="strategies/movr-chz-mana-monthly-4pct-fixed-35m-2026-05-08.md")
    args = parser.parse_args()

    search = load_search_module()
    bt = search.load_module("gala_mb_backtest", search.BT_PATH)
    interval_mod = search.load_module("rif_interval_windows_check", search.INTERVAL_PATH)
    adapt = search.load_module("rif_interval_adaptation_search", search.ADAPT_PATH)
    monthly_mod = search.load_module("rif_movr_monthly_positive_search", search.MONTHLY_PATH)
    reinvest = search.load_module("reinvest_winning_strategies", search.REINVEST_PATH)
    multi = search.load_module("multi_coin_gala_strategy_check", search.MULTI_PATH)

    months = list(search.month_iter(args.start_month, args.end_month))
    trades = search.load_existing_best_trades(
        os.path.join(ROOT, args.best_trades),
        args.start_month,
        args.end_month,
        ["CHZ", "MANA"],
    )
    trades.extend(
        search.build_movr_trades(
            bt,
            interval_mod,
            adapt,
            monthly_mod,
            reinvest,
            multi,
            args.archive_end_day,
            args.days,
            args.warmup_days,
        )
    )
    trades = [trade for trade in trades if args.start_month <= trade["exit_time"][:7] <= args.end_month]

    weights = {"MOVR": 0.50, "CHZ": 0.25, "MANA": 0.25}
    summary = search.simulate(trades, months, weights, args.scale, args.target_pct, args.loss_stop_pct)
    monthly_rows = summary["monthly"]

    monthly_fields = [
        "month",
        "start_balance",
        "month_pnl",
        "month_return_pct",
        "withdrawal",
        "end_before_withdraw",
        "end_after_withdraw",
        "stop_reason",
        "trades",
        "skipped_trades",
        "win_rate_pct",
        "profit_factor",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
    ]
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(os.path.join(ROOT, args.save_report), summary, monthly_rows, args.save_monthly)

    print(
        f"fixed MOVR50/CHZ25/MANA25 scale={args.scale:.2f} "
        f"hits={summary['cash_hits']}/{summary['months']} "
        f"positive={summary['positive_months']} negative={summary['negative_months']} "
        f"net={summary['net_result']:.2f} dd={summary['max_drawdown_pct']:.2f} "
        f"pf={fmt_pf(summary['profit_factor'])}"
    )
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
