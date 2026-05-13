#!/usr/bin/env python3
"""Risk sweep for ONE/RIF/SPELL 10% cashflow v2.1.

The entry pool is fixed. This script only changes the risk overlay:
scale, monthly loss stop, daily loss stop, trade throttling, loss-pause,
and optional rolling health gates.
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

WEIGHTS = {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80}
TARGET_CASH = 100.0
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


def month_count(months):
    return len(months)


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


def generate_policies():
    gates = [
        (0, 0.0, 0.0, 0),
    ]
    # Keep the first-pass sweep intentionally small and practical. If this
    # finds a promising risk band, a deeper health-gate sweep can follow.
    daily_stops = [None, 0.05, 0.08]
    max_trades = [25, 50, 100]
    streaks = [(None, 0), (3, 1)]
    rows = []
    for gate_window, min_ret, min_pf, min_trades in gates:
        for daily_stop in daily_stops:
            for max_day in max_trades:
                for max_loss_streak, pause_days in streaks:
                    rows.append(
                        policy(
                            gate_window=gate_window,
                            min_health_return_pct=min_ret,
                            min_health_pf=min_pf,
                            min_health_trades=min_trades,
                            daily_loss_stop_pct=daily_stop,
                            max_trades_per_coin_day=max_day,
                            max_loss_streak=max_loss_streak,
                            pause_days=pause_days,
                        )
                    )
    return rows


def row_from_result(tuner, scenario_name, scale, loss_stop, policy_row, result):
    return {
        "scenario": scenario_name,
        "weights": tuner.format_weights(WEIGHTS),
        "scale": scale,
        "monthly_loss_stop_pct": loss_stop,
        "policy": tuner.policy_name(policy_row),
        "gate_window": policy_row["gate_window"],
        "min_health_pf": policy_row["min_health_pf"],
        "daily_loss_stop_pct": policy_row["daily_loss_stop_pct"] if policy_row["daily_loss_stop_pct"] is not None else "",
        "max_trades_per_coin_day": policy_row["max_trades_per_coin_day"] if policy_row["max_trades_per_coin_day"] is not None else "",
        "max_loss_streak": policy_row["max_loss_streak"] if policy_row["max_loss_streak"] is not None else "",
        "pause_days": policy_row["pause_days"],
        "cash_hits": result["cash_hits"],
        "withdrawal_months": result["withdrawal_months"],
        "positive_months": result["positive_months"],
        "negative_months": result["negative_months"],
        "cash_withdrawn": result["cash_withdrawn"],
        "final_balance": result["final_balance"],
        "net_result": result["net_result"],
        "worst_month_pnl": result["worst_month_pnl"],
        "best_month_pnl": result["best_month_pnl"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "profit_factor": result["profit_factor"],
        "win_rate_pct": result["win_rate_pct"],
        "trades": result["trades"],
        "skipped_total": result["skipped_total"],
        "skipped_health_gate": result["skipped_health_gate"],
        "skipped_daily_loss_stop": result["skipped_daily_loss_stop"],
        "skipped_loss_pause": result["skipped_loss_pause"],
        "skipped_max_trades_day": result["skipped_max_trades_day"],
        "skipped_month_closed": result["skipped_month_closed"],
    }


def sort_search_rows(rows, months_total):
    return sorted(
        rows,
        key=lambda row: (
            int(row["cash_hits"]) == months_total,
            int(row["cash_hits"]),
            int(row["withdrawal_months"]),
            -float(row["max_drawdown_pct"]),
            float(row["profit_factor"]),
            float(row["net_result"]),
        ),
        reverse=True,
    )


def write_report(path, args, search_rows, eval_rows, generated_at, months_total):
    best = search_rows[0] if search_rows else None
    base_rows = [row for row in eval_rows if row["scenario"] == "base_fee002_slip0"]
    stress_rows = [row for row in eval_rows if row["scenario"] == "fee003_slip0005"]

    lines = [
        "# ONE/RIF/SPELL 10% v2.1 Risk Sweep",
        "",
        f"Generated: {generated_at}",
        "",
        f"Период: `{args.start_month}` - `{args.end_month}`.",
        "Входы не менялись: ONE 10% / RIF 10% / SPELL 80%. Менялась только риск-обвязка.",
        "",
    ]
    if best:
        lines.extend(
            [
                "## Лучший вариант в поисковом stress-сценарии",
                "",
                f"- Scale: `{float(best['scale']):.2f}`",
                f"- Monthly loss stop: `{float(best['monthly_loss_stop_pct']) * 100:.0f}%`",
                f"- Policy: `{best['policy']}`",
                f"- Stress hits: `{best['cash_hits']}/{months_total}`",
                f"- Stress MaxDD: `{fmt_pct(best['max_drawdown_pct'])}`",
                f"- Stress PF: `{fmt_pf(best['profit_factor'])}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Top 20 Search",
            "",
            "| # | Scenario | Scale | Loss stop | Policy | Hits | Net | MaxDD | PF | Worst month | Trades |",
            "|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for idx, row in enumerate(search_rows[:20], start=1):
        lines.append(
            f"| {idx} | `{row['scenario']}` | {float(row['scale']):.2f} | "
            f"{float(row['monthly_loss_stop_pct']) * 100:.0f}% | `{row['policy']}` | "
            f"{row['cash_hits']}/{months_total} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Scenario Check For Selected Top Variants",
            "",
            "| Scenario | Scale | Loss stop | Policy | Hits | Net | MaxDD | PF | Worst month | Trades |",
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in eval_rows[:120]:
        lines.append(
            f"| `{row['scenario']}` | {float(row['scale']):.2f} | "
            f"{float(row['monthly_loss_stop_pct']) * 100:.0f}% | `{row['policy']}` | "
            f"{row['cash_hits']}/{months_total} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
        )

    lines.extend(["", "## Короткий вывод", ""])
    if stress_rows:
        best_stress = sorted(
            stress_rows,
            key=lambda row: (int(row["cash_hits"]), -float(row["max_drawdown_pct"]), float(row["profit_factor"])),
            reverse=True,
        )[0]
        lines.append(
            f"Лучший stress-вариант дает `{best_stress['cash_hits']}/{months_total}` месяцев "
            f"при MaxDD `{fmt_pct(best_stress['max_drawdown_pct'])}`."
        )
    if base_rows:
        best_base = sorted(
            base_rows,
            key=lambda row: (int(row["cash_hits"]), -float(row["max_drawdown_pct"]), float(row["profit_factor"])),
            reverse=True,
        )[0]
        lines.append(
            f"В базовом maker-сценарии лучший вариант дает `{best_base['cash_hits']}/{months_total}` месяцев "
            f"при MaxDD `{fmt_pct(best_base['max_drawdown_pct'])}`."
        )

    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Search CSV: `{args.save_search}`",
            f"- Eval CSV: `{args.save_eval}`",
            f"- Monthly CSV: `{args.save_monthly}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="ONE/RIF/SPELL v2.1 risk sweep.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--search-scenario", default="fee003_slip0005")
    parser.add_argument("--save-search", default=f"data/one_rif_spell_v21_risk_sweep_search_{today}.csv")
    parser.add_argument("--save-eval", default=f"data/one_rif_spell_v21_risk_sweep_eval_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/one_rif_spell_v21_risk_sweep_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/one-rif-spell-v21-risk-sweep-{today}.md")
    args = parser.parse_args()

    tuner = load_module("regime_cashflow_tuner", TUNER_PATH)
    robust = load_module("monthly_cashflow_5pct_robust_search", ROBUST_PATH)
    months = list(tuner.month_iter(args.start_month, args.end_month))
    months_total = len(months)

    base_trades = tuner.load_trades(
        os.path.join(ROOT, args.trades_path),
        args.start_month,
        args.end_month,
        list(WEIGHTS),
    )

    scenario_map = {}
    health_map = {}
    for scenario in SCENARIOS:
        adjusted, _skipped, _total_cost = tuner.scenario_trades(robust, base_trades, scenario)
        scenario_map[scenario["name"]] = adjusted
        health_map[scenario["name"]] = tuner.build_health(adjusted, args.start_month, args.end_month, [7, 14, 30])

    policies = generate_policies()
    search_rows = []
    search_trades = scenario_map[args.search_scenario]
    search_health = health_map[args.search_scenario]

    for scale in [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
        for loss_stop in [0.20, 0.25, 0.30, 0.35, 0.40, 0.50]:
            for policy_row in policies:
                result = tuner.simulate(search_trades, months, WEIGHTS, scale, TARGET_CASH, loss_stop, policy_row, search_health)
                search_rows.append(row_from_result(tuner, args.search_scenario, scale, loss_stop, policy_row, result))

    search_rows = sort_search_rows(search_rows, months_total)
    top_configs = []
    seen = set()
    for row in search_rows:
        key = (
            row["scale"],
            row["monthly_loss_stop_pct"],
            row["policy"],
            row["gate_window"],
            row["daily_loss_stop_pct"],
            row["max_trades_per_coin_day"],
            row["max_loss_streak"],
            row["pause_days"],
        )
        if key in seen:
            continue
        top_configs.append(row)
        seen.add(key)
        if len(top_configs) >= 20:
            break

    eval_rows = []
    monthly_rows = []
    for config in top_configs:
        policy_row = policy(
            gate_window=int(config["gate_window"]),
            min_health_pf=float(config["min_health_pf"]),
            min_health_trades=0 if int(config["gate_window"]) == 0 else (5 if int(config["gate_window"]) == 7 else 10 if int(config["gate_window"]) == 14 else 20),
            daily_loss_stop_pct=float(config["daily_loss_stop_pct"]) if config["daily_loss_stop_pct"] != "" else None,
            max_trades_per_coin_day=int(float(config["max_trades_per_coin_day"])) if config["max_trades_per_coin_day"] != "" else None,
            max_loss_streak=int(float(config["max_loss_streak"])) if config["max_loss_streak"] != "" else None,
            pause_days=int(float(config["pause_days"])),
        )
        for scenario in SCENARIOS:
            result = tuner.simulate(
                scenario_map[scenario["name"]],
                months,
                WEIGHTS,
                float(config["scale"]),
                TARGET_CASH,
                float(config["monthly_loss_stop_pct"]),
                policy_row,
                health_map[scenario["name"]],
            )
            row = row_from_result(tuner, scenario["name"], float(config["scale"]), float(config["monthly_loss_stop_pct"]), policy_row, result)
            eval_rows.append(row)
            for monthly in result["monthly"]:
                monthly_rows.append(
                    {
                        "scenario": scenario["name"],
                        "weights": tuner.format_weights(WEIGHTS),
                        "scale": config["scale"],
                        "monthly_loss_stop_pct": config["monthly_loss_stop_pct"],
                        "policy": config["policy"],
                        **monthly,
                    }
                )

    fields = [
        "scenario",
        "weights",
        "scale",
        "monthly_loss_stop_pct",
        "policy",
        "gate_window",
        "min_health_pf",
        "daily_loss_stop_pct",
        "max_trades_per_coin_day",
        "max_loss_streak",
        "pause_days",
        "cash_hits",
        "withdrawal_months",
        "positive_months",
        "negative_months",
        "cash_withdrawn",
        "final_balance",
        "net_result",
        "worst_month_pnl",
        "best_month_pnl",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "trades",
        "skipped_total",
        "skipped_health_gate",
        "skipped_daily_loss_stop",
        "skipped_loss_pause",
        "skipped_max_trades_day",
        "skipped_month_closed",
    ]
    monthly_fields = [
        "scenario",
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

    save_csv(os.path.join(ROOT, args.save_search), search_rows, fields)
    save_csv(os.path.join(ROOT, args.save_eval), eval_rows, fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(
        os.path.join(ROOT, args.save_report),
        args,
        search_rows,
        eval_rows,
        datetime.now(timezone.utc).isoformat(),
        months_total,
    )

    print(f"searched rows: {len(search_rows)}")
    print(f"saved search: {args.save_search}")
    print(f"saved eval: {args.save_eval}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
