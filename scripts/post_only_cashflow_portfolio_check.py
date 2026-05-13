#!/usr/bin/env python3
"""Focused post-only cashflow portfolio check.

This is a small, reproducible wrapper around the existing regime cashflow
simulator. It does not search the whole universe again. It checks the exact
cashflow mixes we discussed and reports how many already-filled post-only rows
turn into actual portfolio trades after cash target / loss stop / overlay rules.
"""

import argparse
import csv
import importlib.util
import math
import os
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUNER_PATH = os.path.join(ROOT, "scripts", "regime_cashflow_tuner.py")
ROBUST_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_5pct_robust_search.py")


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
    return f"${float(value):,.2f}"


def fmt_pct(value):
    return f"{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def policy(**overrides):
    row = {
        "gate_window": 0,
        "min_health_return_pct": 0.0,
        "min_health_pf": 0.0,
        "min_health_trades": 0,
        "daily_loss_stop_pct": None,
        "max_trades_per_coin_day": None,
        "max_loss_streak": None,
        "pause_days": 0,
    }
    row.update(overrides)
    return row


def config_name(weights):
    return "_".join(f"{coin}{int(round(weight * 100))}" for coin, weight in sorted(weights.items()))


def result_row(tuner, name, target_cash, weights, scale, loss_stop, policy_row, scenario, result, candidate_trades):
    return {
        "portfolio": name,
        "config": config_name(weights),
        "weights": tuner.format_weights(weights),
        "scenario": scenario,
        "target_cash": target_cash,
        "scale": scale,
        "monthly_loss_stop_pct": loss_stop,
        "policy": tuner.policy_name(policy_row),
        "candidate_post_only_rows": candidate_trades,
        "accepted_trades": result["trades"],
        "cash_hits": result["cash_hits"],
        "withdrawal_months": result["withdrawal_months"],
        "positive_months": result["positive_months"],
        "negative_months": result["negative_months"],
        "net_result": result["net_result"],
        "cash_withdrawn": result["cash_withdrawn"],
        "final_balance": result["final_balance"],
        "worst_month_pnl": result["worst_month_pnl"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "profit_factor": result["profit_factor"],
        "win_rate_pct": result["win_rate_pct"],
        "skipped_month_closed": result["skipped_month_closed"],
        "skipped_max_trades_day": result["skipped_max_trades_day"],
        "skipped_daily_loss_stop": result["skipped_daily_loss_stop"],
        "skipped_loss_pause": result["skipped_loss_pause"],
        "skipped_health_gate": result["skipped_health_gate"],
    }


def evaluate(tuner, robust, base_trades, months, name, target_cash, weights, scale, loss_stop, policy_row):
    selected = set(weights)
    candidate_trades = sum(1 for trade in base_trades if trade["coin"] in selected)
    output = []
    monthly = []
    for scenario in SCENARIOS:
        adjusted, _skipped, _total_cost = tuner.scenario_trades(robust, base_trades, scenario)
        health = tuner.build_health(adjusted, months[0], months[-1], [7, 14, 30])
        result = tuner.simulate(adjusted, months, weights, scale, target_cash, loss_stop, policy_row, health)
        output.append(
            result_row(
                tuner,
                name,
                target_cash,
                weights,
                scale,
                loss_stop,
                policy_row,
                scenario["name"],
                result,
                candidate_trades,
            )
        )
        for row in result["monthly"]:
            monthly.append(
                {
                    "portfolio": name,
                    "scenario": scenario["name"],
                    "config": config_name(weights),
                    "weights": tuner.format_weights(weights),
                    "scale": scale,
                    "monthly_loss_stop_pct": loss_stop,
                    "policy": tuner.policy_name(policy_row),
                    **row,
                }
            )
    return output, monthly


def search_exact_chz_mana_rif_spell(tuner, robust, base_trades, months):
    weights = {"CHZ": 0.10, "MANA": 0.10, "RIF": 0.20, "SPELL": 0.60}
    target_cash = 40.0
    search_scenario = {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005, "skip_winner_pct": 0.0}
    adjusted, _skipped, _total_cost = tuner.scenario_trades(robust, base_trades, search_scenario)
    health = tuner.build_health(adjusted, months[0], months[-1], [7, 14, 30])
    candidates = []
    policies = [
        policy(max_trades_per_coin_day=50),
        policy(max_trades_per_coin_day=100),
        policy(daily_loss_stop_pct=0.05, max_trades_per_coin_day=50),
        policy(daily_loss_stop_pct=0.08, max_trades_per_coin_day=50),
        policy(max_trades_per_coin_day=50, max_loss_streak=3, pause_days=1),
        policy(daily_loss_stop_pct=0.05, max_trades_per_coin_day=50, max_loss_streak=3, pause_days=1),
    ]
    for scale in [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
        for loss_stop in [0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50]:
            for policy_row in policies:
                result = tuner.simulate(adjusted, months, weights, scale, target_cash, loss_stop, policy_row, health)
                candidates.append((result, scale, loss_stop, policy_row))
    candidates.sort(
        key=lambda item: (
            item[0]["cash_hits"],
            item[0]["withdrawal_months"],
            item[0]["profit_factor"],
            -item[0]["max_drawdown_pct"],
            item[0]["net_result"],
        ),
        reverse=True,
    )
    result, scale, loss_stop, policy_row = candidates[0]
    return weights, target_cash, scale, loss_stop, policy_row, result


def write_report(path, rows, monthly_path, summary_path, generated_at, months_count):
    lines = [
        "# Post-Only Cashflow Portfolio Check",
        "",
        f"Generated: {generated_at}",
        "",
        "Проверка только по нужным cashflow-связкам.",
        "",
        "Важно: входной trade-pool уже содержит только сделки, которые были исполнены как maker-limit/post-only rows. Поэтому `candidate_post_only_rows` - это не все сигналы, а уже реально заполненные исторические лимитные входы в пуле.",
        "",
        "| Portfolio | Scenario | Scale | Loss stop | Post-only rows | Accepted trades | Hits | Net | MaxDD | PF | Worst month |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['portfolio']} | `{row['scenario']}` | {float(row['scale']):.2f} | "
            f"{float(row['monthly_loss_stop_pct']) * 100:.0f}% | {row['candidate_post_only_rows']} | "
            f"{row['accepted_trades']} | {row['cash_hits']}/{months_count} | "
            f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_path}`",
            f"- Monthly CSV: `{monthly_path}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Check selected post-only cashflow portfolios.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--save-summary", default=f"data/post_only_cashflow_portfolio_check_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/post_only_cashflow_portfolio_check_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/post-only-cashflow-portfolio-check-{today}.md")
    args = parser.parse_args()

    tuner = load_module("regime_cashflow_tuner", TUNER_PATH)
    robust = load_module("monthly_cashflow_5pct_robust_search", ROBUST_PATH)
    months = list(tuner.month_iter(args.start_month, args.end_month))
    all_coins = ["ONE", "RIF", "SPELL", "CHZ", "MANA"]
    base_trades = tuner.load_trades(os.path.join(ROOT, args.trades_path), args.start_month, args.end_month, all_coins)

    rows = []
    monthly_rows = []

    fixed_configs = [
        (
            "ONE/RIF/SPELL 10% v2 max50",
            100.0,
            {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80},
            10.0,
            0.50,
            policy(max_trades_per_coin_day=50),
        ),
        (
            "ONE/RIF/SPELL 10% v2 max100",
            100.0,
            {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80},
            10.0,
            0.50,
            policy(max_trades_per_coin_day=100),
        ),
    ]

    for name, target_cash, weights, scale, loss_stop, policy_row in fixed_configs:
        summary, monthly = evaluate(tuner, robust, base_trades, months, name, target_cash, weights, scale, loss_stop, policy_row)
        rows.extend(summary)
        monthly_rows.extend(monthly)

    weights, target_cash, scale, loss_stop, policy_row, _best = search_exact_chz_mana_rif_spell(
        tuner, robust, base_trades, months
    )
    summary, monthly = evaluate(
        tuner,
        robust,
        base_trades,
        months,
        "CHZ/MANA/RIF/SPELL 4% v2 exact-best",
        target_cash,
        weights,
        scale,
        loss_stop,
        policy_row,
    )
    rows.extend(summary)
    monthly_rows.extend(monthly)

    summary_fields = [
        "portfolio",
        "config",
        "weights",
        "scenario",
        "target_cash",
        "scale",
        "monthly_loss_stop_pct",
        "policy",
        "candidate_post_only_rows",
        "accepted_trades",
        "cash_hits",
        "withdrawal_months",
        "positive_months",
        "negative_months",
        "net_result",
        "cash_withdrawn",
        "final_balance",
        "worst_month_pnl",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "skipped_month_closed",
        "skipped_max_trades_day",
        "skipped_daily_loss_stop",
        "skipped_loss_pause",
        "skipped_health_gate",
    ]
    monthly_fields = [
        "portfolio",
        "scenario",
        "config",
        "weights",
        "scale",
        "monthly_loss_stop_pct",
        "policy",
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
    save_csv(os.path.join(ROOT, args.save_summary), rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(
        os.path.join(ROOT, args.save_report),
        rows,
        args.save_monthly,
        args.save_summary,
        datetime.now(timezone.utc).isoformat(),
        len(months),
    )
    print(f"saved summary: {args.save_summary}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
