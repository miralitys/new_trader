#!/usr/bin/env python3
"""Stress-aware search for a 5% monthly cashflow mix.

This script searches the existing combined trade pool instead of re-running
candle backtests. The point is to find candidates that still work after a
small execution-cost deterioration, not just in the optimistic base case.
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


def deterministic_fraction(*parts):
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def embedded_exposure(trade):
    """Approximate the notional exposure represented by raw_return_pct.

    GALA and ONE portfolio rows already contain internal module sizing. Most
    single-coin best rows are treated as full-notional rows.
    """
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


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def parse_weight_grid(value):
    parts = [float(item) for item in value.split(",") if item.strip()]
    return sorted(set(parts))


def normalize(weights):
    total = sum(weights.values())
    return {coin: value / total for coin, value in weights.items() if value > 0}


def name_weights(weights):
    return "_".join(f"{coin}{int(round(weight * 100))}" for coin, weight in sorted(weights.items()))


def generate_weight_candidates(coins, weight_grid, max_combo_size):
    """Generate focused one/two/three/four-asset portfolios."""
    coins = sorted(set(coins))
    candidates = {}

    for coin in coins:
        candidates[f"{coin}100"] = {coin: 1.0}

    for a, b in itertools.combinations(coins, 2):
        for aw in weight_grid:
            if 0.0 < aw < 1.0:
                weights = {a: aw, b: 1.0 - aw}
                candidates[name_weights(weights)] = weights

    if max_combo_size >= 3:
        triple_templates = [
            (1 / 3, 1 / 3, 1 / 3),
            (0.50, 0.25, 0.25),
            (0.60, 0.20, 0.20),
            (0.70, 0.15, 0.15),
            (0.80, 0.10, 0.10),
        ]
        for combo in itertools.combinations(coins, 3):
            for template in triple_templates:
                for values in set(itertools.permutations(template)):
                    weights = dict(zip(combo, values))
                    candidates[name_weights(weights)] = weights

    if max_combo_size >= 4:
        quad_templates = [
            (0.25, 0.25, 0.25, 0.25),
            (0.40, 0.20, 0.20, 0.20),
            (0.50, 0.20, 0.15, 0.15),
            (0.60, 0.20, 0.10, 0.10),
        ]
        for combo in itertools.combinations(coins, 4):
            for template in quad_templates:
                for values in set(itertools.permutations(template)):
                    weights = dict(zip(combo, values))
                    candidates[name_weights(weights)] = weights

    presets = [
        {"GALA": 0.40, "SPELL": 0.60},
        {"GALA": 0.30, "SPELL": 0.70},
        {"GALA": 0.20, "SPELL": 0.80},
        {"ONE": 0.20, "SPELL": 0.80},
        {"GALA": 0.20, "SPELL": 0.60, "RIF": 0.20},
        {"GALA": 0.20, "SPELL": 0.50, "RIF": 0.30},
        {"GALA": 0.20, "SPELL": 0.50, "ANKR": 0.30},
        {"GALA": 0.20, "SPELL": 0.50, "JASMY": 0.30},
        {"GALA": 0.20, "SPELL": 0.40, "JASMY": 0.20, "ANKR": 0.20},
        {"GALA": 0.20, "SPELL": 0.40, "RIF": 0.20, "ANKR": 0.20},
        {"SPELL": 0.40, "JASMY": 0.20, "ANKR": 0.20, "RIF": 0.20},
        {"SPELL": 0.40, "CHZ": 0.20, "MANA": 0.20, "RIF": 0.20},
        {"MOVR": 0.50, "CHZ": 0.25, "MANA": 0.25},
        {"MOVR_M": 0.50, "CHZ": 0.25, "MANA": 0.25},
    ]
    for preset in presets:
        if all(coin in coins for coin in preset):
            weights = normalize(preset)
            candidates[name_weights(weights)] = weights

    return candidates


def load_trades(monthly, path, start_month, end_month, coins):
    trades = monthly.load_trades(path, start_month, end_month)
    if coins:
        selected = set(coins)
        trades = [trade for trade in trades if trade["coin"] in selected]
    return trades


def rows_for_weights(monthly, rows_by_month_coin, months, weights):
    return monthly.candidate_rows_by_month(rows_by_month_coin, months, weights)


def run_candidate(monthly, rows_by_month_coin, months, weights, loss_stop, scale, target_balance):
    rows_by_month = rows_for_weights(monthly, rows_by_month_coin, months, weights)
    return monthly.simulate(rows_by_month, months, weights, loss_stop, target_balance, scale)


def result_row(name, weights, scale, loss_stop, scenario_name, target_cash, result):
    return {
        "scenario": scenario_name,
        "name": name,
        "weights": monthly_format_weights(weights),
        "scale": scale,
        "loss_stop_pct": loss_stop,
        "target_cash": target_cash,
        "months": len(result["monthly"]),
        **{key: value for key, value in result.items() if key != "monthly"},
    }


def monthly_format_weights(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def run_search(monthly, trades, months, candidates, scales, loss_stops, target_cash, search_scenario, top_keep):
    target_balance = INITIAL_BALANCE + target_cash
    adjusted, skipped, total_extra_cost = adjust_trades(trades, search_scenario)
    rows_by_month_coin = monthly.index_trades_by_month_coin(adjusted)
    rows = []
    monthly_map = {}
    total = len(candidates) * len(scales) * len(loss_stops)
    done = 0

    for name, weights in candidates.items():
        candidate_rows = rows_for_weights(monthly, rows_by_month_coin, months, weights)
        for scale in scales:
            for loss_stop in loss_stops:
                done += 1
                result = monthly.simulate(candidate_rows, months, weights, loss_stop, target_balance, scale)
                row = result_row(name, weights, scale, loss_stop, search_scenario["name"], target_cash, result)
                row["stress_skipped_for_fill"] = skipped
                row["stress_sum_raw_extra_execution_cost_pct"] = total_extra_cost
                rows.append(row)
                key = (name, scale, loss_stop)
                monthly_map[key] = result["monthly"]
        if done and done % 5000 == 0:
            print(f"searched {done}/{total} configs", flush=True)

    rows.sort(
        key=lambda row: (
            row["cash_hits"],
            row["withdrawal_months"],
            row["positive_months"],
            row["profit_factor"] if not math.isinf(row["profit_factor"]) else 999.0,
            -row["max_drawdown_pct"],
            row["net_result"],
        ),
        reverse=True,
    )
    return rows[:top_keep], monthly_map


def evaluate_scenarios(monthly, trades, months, configs, scenarios, target_cash):
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


def parse_weights(text):
    weights = {}
    for part in text.split(";"):
        if not part:
            continue
        coin, value = part.split(":")
        weights[coin] = float(value)
    return weights


def write_report(path, args, search_rows, eval_rows, eval_monthly_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    robust_rows = [
        row
        for row in eval_rows
        if row["scenario"] == args.robust_scenario_name and row["cash_hits"] == row["months"]
    ]
    best_by_name = defaultdict(dict)
    for row in eval_rows:
        key = (row["name"], row["scale"], row["loss_stop_pct"], row["weights"])
        best_by_name[key][row["scenario"]] = row

    lines = [
        "# Monthly Cashflow Robust Search",
        "",
        f"Generated: `{generated}`",
        "",
        f"Цель: найти смесь стратегий, которая дает `${args.target_cash:.0f}+` в месяц на стартовом балансе `$1000` за выбранный период и не разваливается от ухудшения комиссии/исполнения.",
        "",
        "Важно: это поиск по уже готовому пулу сделок. База уже содержит maker fee `0.02%` за сторону и `0` slippage; стресс добавляет extra-cost поверх базы.",
        "",
        "## Поисковая настройка",
        "",
        f"- Trade pool: `{args.trades_path}`",
        f"- Period: `{args.start_month}` - `{args.end_month}`",
        f"- Search stress: `{args.robust_scenario_name}`",
        f"- Target: `${args.target_cash:.2f}` per month",
        "",
        "## Лучшие кандидаты в поисковом stress-сценарии",
        "",
        f"| # | Name | Weights | Scale | Loss Stop | ${args.target_cash:.0f}+ Months | Net | MaxDD | PF | Worst Month | Trades |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(search_rows[:20], start=1):
        lines.append(
            f"| {idx} | `{row['name']}` | `{row['weights']}` | {row['scale']:.2f} | "
            f"{row['loss_stop_pct']:.2f} | {row['cash_hits']}/{row['months']} | "
            f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Проверка топ-кандидатов по сценариям",
            "",
            f"| Candidate | Scenario | ${args.target_cash:.0f}+ Months | Net | MaxDD | PF | Worst Month | Trades |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, scenario_map in list(best_by_name.items())[:25]:
        name, scale, loss_stop, weights = key
        candidate_label = f"`{name}` scale {float(scale):.2f} loss {float(loss_stop):.2f}"
        for scenario in args.eval_scenarios_order:
            row = scenario_map.get(scenario)
            if not row:
                continue
            lines.append(
                f"| {candidate_label} | `{scenario}` | {row['cash_hits']}/{row['months']} | "
                f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
                f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
            )

    lines.extend(
        [
            "",
            "## Вывод",
            "",
        ]
    )
    if robust_rows:
        best = sorted(
            robust_rows,
            key=lambda row: (row["max_drawdown_pct"], -row["profit_factor"], -row["net_result"]),
        )[0]
        lines.extend(
            [
                f"Найден кандидат, который держит `36/36` месяцев даже в stress-сценарии `{args.robust_scenario_name}`:",
                "",
                f"- `{best['name']}`",
                f"- веса: `{best['weights']}`",
                f"- scale: `{best['scale']:.2f}`",
                f"- monthly loss stop: `{best['loss_stop_pct']:.2f}`",
                f"- MaxDD в stress: `{fmt_pct(best['max_drawdown_pct'])}`",
                f"- PF в stress: `{fmt_pf(best['profit_factor'])}`",
                "",
                "Но перед live его все равно надо отдельно проверить на свежих 24h/7d и strict maker-fill.",
            ]
        )
    else:
        best = search_rows[0] if search_rows else None
        if best:
            lines.extend(
                [
                f"Строго живучего варианта `{len(list(month_iter(args.start_month, args.end_month)))}/{len(list(month_iter(args.start_month, args.end_month)))}` в stress-сценарии `{args.robust_scenario_name}` не найдено.",
                    "",
                    "Лучший результат поиска:",
                    "",
                    f"- `{best['name']}`",
                    f"- веса: `{best['weights']}`",
                    f"- scale: `{best['scale']:.2f}`",
                    f"- monthly loss stop: `{best['loss_stop_pct']:.2f}`",
                    f"- ${args.target_cash:.0f}+ месяцев: `{best['cash_hits']}/{best['months']}`",
                    f"- MaxDD: `{fmt_pct(best['max_drawdown_pct'])}`",
                    f"- PF: `{fmt_pf(best['profit_factor'])}`",
                    "",
                    "Практический вывод: месячную цель можно собрать в базе, но устойчивой версии под ухудшенное исполнение пока нет. Значит дальше надо искать не просто веса, а менять сами входы/фильтры или снижать месячную цель.",
                ]
            )

    monthly_by_scenario = defaultdict(list)
    for row in eval_monthly_rows:
        monthly_by_scenario[(row["name"], row["scenario"])].append(row)
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
    parser = argparse.ArgumentParser(description="Stress-aware 5% monthly cashflow search.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--target-cash", type=float, default=50.0)
    parser.add_argument(
        "--coins",
        nargs="*",
        default=["GALA", "SPELL", "JASMY", "ANKR", "RIF", "SHIB", "CHZ", "MANA", "SAND", "MOVR", "MOVR_M"],
    )
    parser.add_argument("--scales", nargs="*", type=float, default=[2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0])
    parser.add_argument("--loss-stops", nargs="*", type=float, default=[0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50])
    parser.add_argument("--weight-grid", default="0.2,0.3,0.4,0.5,0.6,0.7,0.8")
    parser.add_argument("--max-combo-size", type=int, choices=[1, 2, 3, 4], default=3)
    parser.add_argument("--top-keep", type=int, default=30)
    parser.add_argument("--summary-path", default="data/monthly_cashflow_5pct_36m_robust_search_summary_2026-05-08.csv")
    parser.add_argument("--eval-summary-path", default="data/monthly_cashflow_5pct_36m_robust_eval_summary_2026-05-08.csv")
    parser.add_argument("--eval-monthly-path", default="data/monthly_cashflow_5pct_36m_robust_eval_monthly_2026-05-08.csv")
    parser.add_argument("--report-path", default="strategies/monthly-cashflow-5pct-36m-robust-search-2026-05-08.md")
    args = parser.parse_args()

    monthly = load_module("monthly_cashflow_search", MONTHLY_PATH)
    trades_path = os.path.join(ROOT, args.trades_path)
    months = list(month_iter(args.start_month, args.end_month))
    trades = load_trades(monthly, trades_path, args.start_month, args.end_month, args.coins)
    coins = sorted({trade["coin"] for trade in trades})
    candidates = generate_weight_candidates(coins, parse_weight_grid(args.weight_grid), args.max_combo_size)

    search_scenario = {
        "name": "fee003_slip0",
        "fee_pct": 0.0003,
        "slippage_pct": 0.0,
        "skip_winner_pct": 0.0,
    }
    args.robust_scenario_name = search_scenario["name"]
    eval_scenarios = [
        {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
        {"name": "fee0025_slip0", "fee_pct": 0.00025, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
        search_scenario,
        {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005, "skip_winner_pct": 0.0},
        {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
        {"name": "miss_5pct_winners", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.05},
    ]
    args.eval_scenarios_order = [scenario["name"] for scenario in eval_scenarios]

    print(f"loaded trades: {len(trades)}")
    print(f"period months: {args.start_month}..{args.end_month} ({len(months)})")
    print(f"coins: {','.join(coins)}")
    print(f"candidates: {len(candidates)}")
    print(f"configs: {len(candidates) * len(args.scales) * len(args.loss_stops)}")

    search_rows, _ = run_search(
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

    summary_path = os.path.join(ROOT, args.summary_path)
    eval_summary_path = os.path.join(ROOT, args.eval_summary_path)
    eval_monthly_path = os.path.join(ROOT, args.eval_monthly_path)
    report_path = os.path.join(ROOT, args.report_path)

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
    save_csv(summary_path, search_rows, summary_fields)

    eval_rows, eval_monthly_rows = evaluate_scenarios(
        monthly,
        trades,
        months,
        search_rows,
        eval_scenarios,
        args.target_cash,
    )
    save_csv(eval_summary_path, eval_rows, summary_fields)
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
    save_csv(eval_monthly_path, eval_monthly_rows, monthly_fields)

    write_report(report_path, args, search_rows, eval_rows, eval_monthly_rows)

    print("top search results:")
    for row in search_rows[:10]:
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
