#!/usr/bin/env python3
"""Find the maximum monthly cash target that hits every month.

The inputs are fixed portfolio candidates. The script only sweeps the monthly
cash target and keeps the strategy weights, scale, and monthly loss stop fixed.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHLY_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_search.py")
ROBUST_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_5pct_robust_search.py")
INITIAL_BALANCE = 1000.0


CANDIDATES = {
    "gala20_spell80": {
        "label": "GALA 20% / SPELL 80%",
        "weights": {"GALA": 0.20, "SPELL": 0.80},
        "scale": 6.0,
        "loss_stop_pct": 0.35,
    },
    "chz10_shib10_spell80": {
        "label": "CHZ 10% / SHIB 10% / SPELL 80%",
        "weights": {"CHZ": 0.10, "SHIB": 0.10, "SPELL": 0.80},
        "scale": 10.0,
        "loss_stop_pct": 0.50,
    },
}


SCENARIOS = [
    {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
    {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
    {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005, "skip_winner_pct": 0.0},
    {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
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


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def weight_text(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def load_trades(monthly, trades_path, start_month, end_month, candidates):
    coins = sorted({coin for name in candidates for coin in CANDIDATES[name]["weights"]})
    rows = monthly.load_trades(trades_path, start_month, end_month)
    selected = [row for row in rows if row["coin"] in coins]
    return selected


def candidate_rows(monthly, rows_by_month_coin, months, weights):
    return monthly.candidate_rows_by_month(rows_by_month_coin, months, weights)


def success(result, months_count):
    return int(result["cash_hits"]) == months_count


def run_target(monthly, rows_by_month, months, candidate, target_cash):
    return monthly.simulate(
        rows_by_month,
        months,
        candidate["weights"],
        candidate["loss_stop_pct"],
        INITIAL_BALANCE + target_cash,
        candidate["scale"],
    )


def find_ceiling(monthly, rows_by_month, months, candidate, max_target_cash, cents_step):
    max_units = int(round(max_target_cash * 100 / cents_step))
    low = 0
    high = max_units
    best_result = run_target(monthly, rows_by_month, months, candidate, 0.0)
    while low < high:
        mid = (low + high + 1) // 2
        target_cash = mid * cents_step / 100.0
        result = run_target(monthly, rows_by_month, months, candidate, target_cash)
        if success(result, len(months)):
            low = mid
            best_result = result
        else:
            high = mid - 1
    target_cash = low * cents_step / 100.0
    result = run_target(monthly, rows_by_month, months, candidate, target_cash)
    next_target = (low + 1) * cents_step / 100.0
    next_result = (
        run_target(monthly, rows_by_month, months, candidate, next_target)
        if next_target <= max_target_cash
        else None
    )
    return target_cash, result, next_target, next_result


def summarize(candidate_key, candidate, scenario, target_cash, result, next_target, next_result):
    monthly_rows = result["monthly"]
    return {
        "candidate_key": candidate_key,
        "candidate": candidate["label"],
        "scenario": scenario["name"],
        "weights": weight_text(candidate["weights"]),
        "scale": candidate["scale"],
        "loss_stop_pct": candidate["loss_stop_pct"],
        "months": len(monthly_rows),
        "max_target_cash": target_cash,
        "max_target_pct": target_cash / INITIAL_BALANCE * 100.0,
        "cash_hits": result["cash_hits"],
        "withdrawal_months": result["withdrawal_months"],
        "positive_months": result["positive_months"],
        "cash_withdrawn": result["cash_withdrawn"],
        "final_balance": result["final_balance"],
        "net_result": result["net_result"],
        "worst_month_pnl": result["worst_month_pnl"],
        "best_month_pnl": result["best_month_pnl"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "profit_factor": result["profit_factor"],
        "win_rate_pct": result["win_rate_pct"],
        "trades": result["trades"],
        "next_target_cash": next_target if next_result else "",
        "next_target_cash_hits": next_result["cash_hits"] if next_result else "",
        "next_target_worst_month_pnl": next_result["worst_month_pnl"] if next_result else "",
    }


def write_report(path, args, summary_rows, monthly_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Monthly Cashflow Target Ceiling",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "Цель: найти максимальную месячную цель, которую фиксированная стратегия выполняет во всех 36 месяцах.",
        "",
        f"Период: `{args.start_month}` - `{args.end_month}`.",
        f"Trade pool: `{args.trades_path}`.",
        "",
        "## Ceiling Summary",
        "",
        "| Strategy | Scenario | Max Stable % / $ | Next Target | Cash Hits | MaxDD | PF | Worst Month | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['candidate']} | `{row['scenario']}` | "
            f"{row['max_target_pct']:.2f}% / {fmt_money(row['max_target_cash'])} | "
            f"{fmt_money(row['next_target_cash']) if row['next_target_cash'] != '' else 'n/a'} "
            f"({row['next_target_cash_hits']}/{row['months']} months) | "
            f"{row['cash_hits']}/{row['months']} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Human Read",
            "",
        ]
    )
    base_rows = [row for row in summary_rows if row["scenario"] == "base_fee002_slip0"]
    for row in base_rows:
        lines.append(
            f"- `{row['candidate']}`: исторический потолок в базе - примерно "
            f"`{row['max_target_pct']:.2f}%` в месяц. Следующий шаг "
            f"`{fmt_money(row['next_target_cash'])}` уже не проходит все 36 месяцев "
            f"({row['next_target_cash_hits']}/{row['months']})."
        )
    lines.extend(
        [
            "",
            "Важно: это потолок по истории. Его нельзя автоматически ставить в live. Чем ближе цель к потолку, тем меньше запас на исполнение, slippage, пропущенные fill и изменение режима рынка.",
            "",
            "## Files",
            "",
            f"- Summary CSV: `{args.save_summary}`",
            f"- Monthly CSV: `{args.save_monthly}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Find max stable monthly target for fixed cashflow candidates.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--candidates", nargs="*", choices=sorted(CANDIDATES), default=["gala20_spell80", "chz10_shib10_spell80"])
    parser.add_argument("--scenarios", nargs="*", default=[scenario["name"] for scenario in SCENARIOS])
    parser.add_argument("--max-target-pct", type=float, default=30.0)
    parser.add_argument("--cents-step", type=int, default=1, help="Target step in cents.")
    parser.add_argument("--save-summary", default=f"data/monthly_cashflow_target_ceiling_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/monthly_cashflow_target_ceiling_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/monthly-cashflow-target-ceiling-{today}.md")
    args = parser.parse_args()

    monthly = load_module("monthly_cashflow_search", MONTHLY_PATH)
    robust = load_module("monthly_cashflow_5pct_robust_search", ROBUST_PATH)
    trades_path = os.path.join(ROOT, args.trades_path)
    months = list(month_iter(args.start_month, args.end_month))
    trades = load_trades(monthly, trades_path, args.start_month, args.end_month, args.candidates)
    scenario_map = {scenario["name"]: scenario for scenario in SCENARIOS}

    summary_rows = []
    all_monthly_rows = []
    max_target_cash = INITIAL_BALANCE * args.max_target_pct / 100.0

    print(f"loaded trades: {len(trades)}")
    print(f"months: {args.start_month}..{args.end_month} ({len(months)})")
    for scenario_name in args.scenarios:
        scenario = scenario_map[scenario_name]
        stressed, skipped, _total_extra = robust.adjust_trades(trades, scenario)
        rows_by_month_coin = monthly.index_trades_by_month_coin(stressed)
        for candidate_key in args.candidates:
            candidate = CANDIDATES[candidate_key]
            rows_by_month = candidate_rows(monthly, rows_by_month_coin, months, candidate["weights"])
            target_cash, result, next_target, next_result = find_ceiling(
                monthly,
                rows_by_month,
                months,
                candidate,
                max_target_cash,
                args.cents_step,
            )
            row = summarize(candidate_key, candidate, scenario, target_cash, result, next_target, next_result)
            row["stress_skipped_for_fill"] = skipped
            summary_rows.append(row)
            for month_row in result["monthly"]:
                all_monthly_rows.append(
                    {
                        "candidate_key": candidate_key,
                        "candidate": candidate["label"],
                        "scenario": scenario_name,
                        "max_target_cash": target_cash,
                        "max_target_pct": target_cash / INITIAL_BALANCE * 100.0,
                        **month_row,
                    }
                )
            print(
                f"{candidate['label']} {scenario_name}: "
                f"{target_cash / INITIAL_BALANCE * 100.0:.2f}% "
                f"({target_cash:.2f}), next {next_target:.2f} -> "
                f"{next_result['cash_hits'] if next_result else 'n/a'}/{len(months)}",
                flush=True,
            )

    summary_fields = [
        "candidate_key",
        "candidate",
        "scenario",
        "weights",
        "scale",
        "loss_stop_pct",
        "months",
        "max_target_cash",
        "max_target_pct",
        "cash_hits",
        "withdrawal_months",
        "positive_months",
        "cash_withdrawn",
        "final_balance",
        "net_result",
        "worst_month_pnl",
        "best_month_pnl",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "trades",
        "next_target_cash",
        "next_target_cash_hits",
        "next_target_worst_month_pnl",
        "stress_skipped_for_fill",
    ]
    monthly_fields = [
        "candidate_key",
        "candidate",
        "scenario",
        "max_target_cash",
        "max_target_pct",
        "month",
        "start_balance",
        "month_pnl",
        "month_return_pct",
        "withdrawal",
        "end_before_withdraw",
        "end_after_withdraw",
        "stop_reason",
        "trades",
        "win_rate_pct",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), all_monthly_rows, monthly_fields)
    write_report(os.path.join(ROOT, args.save_report), args, summary_rows, all_monthly_rows)
    print(f"saved summary: {args.save_summary}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
