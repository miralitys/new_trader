#!/usr/bin/env python3
"""Targeted 10% monthly cashflow portfolio search.

This is a faster, narrower search than the generic robust search. It focuses
on SPELL-heavy portfolios and tests whether adding/replacing satellites can
improve the current ONE/RIF/SPELL cashflow mix.
"""

import argparse
import csv
import hashlib
import importlib.util
import itertools
import math
import os
from collections import defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHLY_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_search.py")
BASE_FEE_PCT = 0.0002
INITIAL_BALANCE = 1000.0


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


def deterministic_fraction(*parts):
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def embedded_exposure(trade):
    coin = trade.get("coin", "")
    direction = trade.get("direction", "")
    if coin in {"GALA", "ONE"}:
        if direction == "long":
            return 0.18
        if direction == "short":
            return 0.36
    return 1.0


def stressed_trade(trade, scenario):
    row = dict(trade)
    raw_return = float(row["raw_return_pct"])
    exposure = embedded_exposure(row)
    extra_fee = max(0.0, scenario["fee_pct"] - BASE_FEE_PCT)
    extra_cost_pct = exposure * 2.0 * (extra_fee + scenario["slippage_pct"]) * 100.0
    adjusted = raw_return - extra_cost_pct

    if scenario.get("skip_winner_pct", 0.0) > 0.0 and adjusted > 0.0:
        if (
            deterministic_fraction(
                row.get("coin"),
                row.get("entry_time"),
                row.get("exit_time"),
                row.get("strategy"),
                scenario["name"],
            )
            < scenario["skip_winner_pct"]
        ):
            return None

    row["raw_return_pct"] = adjusted
    row["base_raw_return_pct"] = raw_return
    row["extra_execution_cost_pct"] = extra_cost_pct
    row["stress_scenario"] = scenario["name"]
    return row


def adjust_trades(trades, scenario):
    adjusted = []
    skipped = 0
    total_extra_cost = 0.0
    for trade in trades:
        item = stressed_trade(trade, scenario)
        if item is None:
            skipped += 1
            continue
        total_extra_cost += item["extra_execution_cost_pct"]
        adjusted.append(item)
    return adjusted, skipped, total_extra_cost


def normalize(weights):
    total = sum(weights.values())
    return {coin: value / total for coin, value in weights.items() if value > 0}


def weight_name(weights):
    return "_".join(f"{coin}{int(round(weight * 100))}" for coin, weight in sorted(weights.items()))


def format_weights(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def parse_weights(text):
    weights = {}
    for part in text.split(";"):
        if not part:
            continue
        coin, value = part.split(":")
        weights[coin] = float(value)
    return weights


def generate_candidates(core_coin, satellites, core_weights):
    satellites = sorted(set(satellites) - {core_coin})
    candidates = {}

    def add(weights):
        weights = normalize(weights)
        candidates[weight_name(weights)] = weights

    # Current baseline and the most important known variants.
    presets = [
        {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80},
        {"ONE": 0.20, "SPELL": 0.80},
        {"GALA": 0.20, "SPELL": 0.80},
        {"ANKR": 0.10, "CHZ": 0.10, "SPELL": 0.80},
        {"CHZ": 0.10, "MANA": 0.10, "RIF": 0.10, "SPELL": 0.70},
        {"GALA": 0.10, "ONE": 0.10, "RIF": 0.10, "SPELL": 0.70},
    ]
    for preset in presets:
        if core_coin in preset and all(coin == core_coin or coin in satellites for coin in preset):
            add(preset)

    for core_weight in core_weights:
        rest = 1.0 - core_weight
        if rest <= 0:
            continue

        for coin in satellites:
            add({core_coin: core_weight, coin: rest})

        for a, b in itertools.combinations(satellites, 2):
            for ratio in (0.30, 0.50, 0.70):
                add({core_coin: core_weight, a: rest * ratio, b: rest * (1.0 - ratio)})

        # A tiny fourth leg only where the current ONE/RIF/SPELL core remains.
        if "ONE" in satellites and "RIF" in satellites:
            for extra in satellites:
                if extra in {"ONE", "RIF"}:
                    continue
                if core_weight <= 0.75:
                    add(
                        {
                            core_coin: core_weight,
                            "ONE": 0.10,
                            "RIF": 0.10,
                            extra: max(0.0, 1.0 - core_weight - 0.20),
                        }
                    )

    return candidates


def result_row(name, weights, scale, loss_stop, scenario_name, target_cash, result):
    return {
        "scenario": scenario_name,
        "name": name,
        "weights": format_weights(weights),
        "scale": scale,
        "loss_stop_pct": loss_stop,
        "target_cash": target_cash,
        "months": len(result["monthly"]),
        **{key: value for key, value in result.items() if key != "monthly"},
    }


def run_candidate(monthly, rows_by_month_coin, months, weights, loss_stop, scale, target_balance):
    rows_by_month = monthly.candidate_rows_by_month(rows_by_month_coin, months, weights)
    return monthly.simulate(rows_by_month, months, weights, loss_stop, target_balance, scale)


def search(monthly, trades, months, candidates, scales, loss_stops, target_cash, scenario, top_keep):
    adjusted, skipped, total_extra_cost = adjust_trades(trades, scenario)
    rows_by_month_coin = monthly.index_trades_by_month_coin(adjusted)
    target_balance = INITIAL_BALANCE + target_cash
    rows = []
    monthly_by_key = {}
    total = len(candidates) * len(scales) * len(loss_stops)
    done = 0

    for name, weights in candidates.items():
        candidate_rows_by_month = monthly.candidate_rows_by_month(rows_by_month_coin, months, weights)
        for scale in scales:
            for loss_stop in loss_stops:
                result = monthly.simulate(
                    candidate_rows_by_month,
                    months,
                    weights,
                    loss_stop,
                    target_balance,
                    scale,
                )
                row = result_row(name, weights, scale, loss_stop, scenario["name"], target_cash, result)
                row["stress_skipped_for_fill"] = skipped
                row["stress_sum_raw_extra_execution_cost_pct"] = total_extra_cost
                rows.append(row)
                monthly_by_key[(name, scale, loss_stop)] = result["monthly"]
                done += 1
        if done and done % 2000 == 0:
            print(f"searched {done}/{total}", flush=True)

    rows.sort(
        key=lambda row: (
            row["cash_hits"],
            row["withdrawal_months"],
            row["positive_months"],
            -row["max_drawdown_pct"],
            row["profit_factor"] if not math.isinf(row["profit_factor"]) else 999.0,
            row["net_result"],
        ),
        reverse=True,
    )
    return rows[:top_keep], monthly_by_key


def evaluate(monthly, trades, months, configs, scenarios, target_cash):
    target_balance = INITIAL_BALANCE + target_cash
    rows = []
    monthly_rows = []
    scenario_cache = {}
    for scenario in scenarios:
        adjusted, skipped, total_extra_cost = adjust_trades(trades, scenario)
        scenario_cache[scenario["name"]] = (
            monthly.index_trades_by_month_coin(adjusted),
            skipped,
            total_extra_cost,
        )

    for config in configs:
        name = config["name"]
        weights = parse_weights(config["weights"])
        scale = float(config["scale"])
        loss_stop = float(config["loss_stop_pct"])
        for scenario in scenarios:
            rows_by_month_coin, skipped, total_extra_cost = scenario_cache[scenario["name"]]
            result = run_candidate(monthly, rows_by_month_coin, months, weights, loss_stop, scale, target_balance)
            row = result_row(name, weights, scale, loss_stop, scenario["name"], target_cash, result)
            row["stress_skipped_for_fill"] = skipped
            row["stress_sum_raw_extra_execution_cost_pct"] = total_extra_cost
            rows.append(row)
            for item in result["monthly"]:
                monthly_rows.append(
                    {
                        "scenario": scenario["name"],
                        "name": name,
                        "weights": row["weights"],
                        "scale": scale,
                        "loss_stop_pct": loss_stop,
                        **item,
                    }
                )
    return rows, monthly_rows


def write_report(path, args, search_rows, eval_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Monthly Cashflow 10% Targeted Portfolio Search",
        "",
        f"Generated: `{generated}`",
        "",
        f"Период: `{args.start_month}` - `{args.end_month}`.",
        f"Цель: `${args.target_cash:.0f}+` в месяц на стартовом балансе `$1000`.",
        "",
        "Поиск ограничен SPELL-heavy смесями и проверяет, можно ли улучшить ONE/RIF/SPELL без полной переоптимизации входов.",
        "",
        "## Top Search",
        "",
        f"| # | Candidate | Scale | Loss Stop | ${args.target_cash:.0f}+ Months | Net | MaxDD | PF | Worst Month | Trades | Weights |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, row in enumerate(search_rows[:20], start=1):
        lines.append(
            f"| {index} | `{row['name']}` | {row['scale']:.2f} | {row['loss_stop_pct']:.2f} | "
            f"{row['cash_hits']}/{row['months']} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{fmt_money(row['worst_month_pnl'])} | {row['trades']} | `{row['weights']}` |"
        )

    grouped = defaultdict(dict)
    for row in eval_rows:
        key = (row["name"], row["scale"], row["loss_stop_pct"], row["weights"])
        grouped[key][row["scenario"]] = row

    lines.extend(
        [
            "",
            "## Scenario Check",
            "",
            f"| Candidate | Scenario | ${args.target_cash:.0f}+ Months | Net | MaxDD | PF | Worst Month | Trades |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, scenarios in list(grouped.items())[:20]:
        name, scale, loss_stop, _weights = key
        label = f"`{name}` scale {float(scale):.2f} loss {float(loss_stop):.2f}"
        for scenario_name in args.eval_scenarios_order:
            row = scenarios.get(scenario_name)
            if not row:
                continue
            lines.append(
                f"| {label} | `{scenario_name}` | {row['cash_hits']}/{row['months']} | "
                f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
                f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Search summary CSV: `{args.summary_path}`",
            f"- Scenario summary CSV: `{args.eval_summary_path}`",
            f"- Scenario monthly CSV: `{args.eval_monthly_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Targeted 10% monthly portfolio search.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--target-cash", type=float, default=100.0)
    parser.add_argument("--core-coin", default="SPELL")
    parser.add_argument("--satellites", nargs="*", default=["ONE", "RIF", "GALA", "ANKR", "CHZ", "MANA", "JASMY", "SHIB"])
    parser.add_argument("--core-weights", nargs="*", type=float, default=[0.65, 0.70, 0.75, 0.80, 0.85])
    parser.add_argument("--scales", nargs="*", type=float, default=[4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0])
    parser.add_argument("--loss-stops", nargs="*", type=float, default=[0.30, 0.35, 0.40, 0.50])
    parser.add_argument("--top-keep", type=int, default=80)
    parser.add_argument("--summary-path", default="data/monthly_cashflow_10pct_24m_targeted_portfolio_search_2026-05-08.csv")
    parser.add_argument("--eval-summary-path", default="data/monthly_cashflow_10pct_24m_targeted_portfolio_eval_2026-05-08.csv")
    parser.add_argument("--eval-monthly-path", default="data/monthly_cashflow_10pct_24m_targeted_portfolio_monthly_2026-05-08.csv")
    parser.add_argument("--report-path", default="strategies/monthly-cashflow-10pct-24m-targeted-portfolio-search-2026-05-08.md")
    args = parser.parse_args()

    monthly = load_module("monthly_cashflow_search", MONTHLY_PATH)
    trades_path = os.path.join(ROOT, args.trades_path)
    months = list(month_iter(args.start_month, args.end_month))
    trades = monthly.load_trades(trades_path, args.start_month, args.end_month)
    selected = {args.core_coin, *args.satellites}
    trades = [trade for trade in trades if trade["coin"] in selected]
    available = sorted({trade["coin"] for trade in trades})
    satellites = [coin for coin in args.satellites if coin in available]
    candidates = generate_candidates(args.core_coin, satellites, args.core_weights)

    search_scenario = {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0, "skip_winner_pct": 0.0}
    eval_scenarios = [
        {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
        search_scenario,
        {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005, "skip_winner_pct": 0.0},
        {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
        {"name": "miss_5pct_winners", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.05},
    ]
    args.eval_scenarios_order = [scenario["name"] for scenario in eval_scenarios]

    print(f"loaded trades: {len(trades)}")
    print(f"period months: {args.start_month}..{args.end_month} ({len(months)})")
    print(f"available coins: {','.join(available)}")
    print(f"candidates: {len(candidates)}")
    print(f"configs: {len(candidates) * len(args.scales) * len(args.loss_stops)}")

    search_rows, _monthly_map = search(
        monthly,
        trades,
        months,
        candidates,
        args.scales,
        args.loss_stops,
        args.target_cash,
        search_scenario,
        args.top_keep,
    )
    eval_rows, eval_monthly_rows = evaluate(
        monthly,
        trades,
        months,
        search_rows,
        eval_scenarios,
        args.target_cash,
    )

    summary_fields = [
        "scenario",
        "name",
        "weights",
        "scale",
        "loss_stop_pct",
        "target_cash",
        "months",
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
        "skipped_trades",
        "stress_skipped_for_fill",
        "stress_sum_raw_extra_execution_cost_pct",
    ]
    monthly_fields = [
        "scenario",
        "name",
        "weights",
        "scale",
        "loss_stop_pct",
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
    summary_path = os.path.join(ROOT, args.summary_path)
    eval_summary_path = os.path.join(ROOT, args.eval_summary_path)
    eval_monthly_path = os.path.join(ROOT, args.eval_monthly_path)
    report_path = os.path.join(ROOT, args.report_path)
    save_csv(summary_path, search_rows, summary_fields)
    save_csv(eval_summary_path, eval_rows, summary_fields)
    save_csv(eval_monthly_path, eval_monthly_rows, monthly_fields)
    write_report(report_path, args, search_rows, eval_rows)

    print("top search results:")
    for row in search_rows[:12]:
        print(
            f"{row['name']} scale={row['scale']:.2f} loss={row['loss_stop_pct']:.2f} "
            f"cash={row['cash_hits']}/{row['months']} net={row['net_result']:.2f} "
            f"dd={row['max_drawdown_pct']:.2f} pf={fmt_pf(row['profit_factor'])} "
            f"weights={row['weights']}"
        )
    print(f"saved summary: {summary_path}")
    print(f"saved eval summary: {eval_summary_path}")
    print(f"saved eval monthly: {eval_monthly_path}")
    print(f"saved report: {report_path}")


if __name__ == "__main__":
    main()
