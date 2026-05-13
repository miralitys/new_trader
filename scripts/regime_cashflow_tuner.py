#!/usr/bin/env python3
"""Search regime-aware monthly cashflow overlays on the existing trade pool.

The tuner is deliberately based on already-known trade rows. It does not
change entry logic. It only tests portfolio/risk overlays that could be known
at the moment of trading:

- rolling coin health from prior days only;
- daily loss stop;
- max trades per coin/day;
- pause after consecutive losing trades;
- monthly cash target shutdown.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHLY_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_search.py")
ROBUST_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_5pct_robust_search.py")
INITIAL_BALANCE = 1000.0


SCENARIOS = [
    {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
    {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
    {"name": "fee003_slip0005", "fee_pct": 0.0003, "slippage_pct": 0.00005, "skip_winner_pct": 0.0},
    {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0, "skip_winner_pct": 0.0},
]


PROFILES = {
    "one10_quick": {
        "title": "ONE/RIF/SPELL 10% Regime Cashflow Quick Sweep",
        "target_cash": 100.0,
        "coins": ["ONE", "RIF", "SPELL"],
        "weights": [
            {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80},
            {"ONE": 0.20, "SPELL": 0.80},
            {"ONE": 0.10, "SPELL": 0.90},
            {"RIF": 0.10, "SPELL": 0.90},
        ],
        "scales": [6.0, 7.0, 8.0, 9.0, 10.0],
        "monthly_loss_stops": [0.35, 0.40, 0.50],
    },
    "one10": {
        "title": "ONE/RIF/SPELL 10% Regime Cashflow",
        "target_cash": 100.0,
        "coins": ["ONE", "RIF", "SPELL"],
        "weights": [
            {"ONE": 0.20, "SPELL": 0.80},
            {"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80},
            {"ONE": 0.15, "RIF": 0.15, "SPELL": 0.70},
            {"ONE": 0.10, "SPELL": 0.90},
            {"RIF": 0.10, "SPELL": 0.90},
            {"ONE": 0.05, "RIF": 0.15, "SPELL": 0.80},
            {"ONE": 0.20, "RIF": 0.10, "SPELL": 0.70},
        ],
        "scales": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "monthly_loss_stops": [0.25, 0.30, 0.35, 0.40, 0.50],
    },
    "movr4": {
        "title": "MOVR/CHZ/MANA/RIF/SPELL 4% Regime Cashflow",
        "target_cash": 40.0,
        "coins": ["MOVR", "MOVR_M", "CHZ", "MANA", "RIF", "SPELL"],
        "weights": [
            {"MOVR": 0.50, "CHZ": 0.25, "MANA": 0.25},
            {"CHZ": 0.20, "RIF": 0.80},
            {"CHZ": 0.10, "RIF": 0.90},
            {"CHZ": 0.10, "MOVR": 0.10, "RIF": 0.80},
            {"CHZ": 0.15, "MOVR_M": 0.15, "RIF": 0.70},
            {"MANA": 0.20, "RIF": 0.80},
            {"CHZ": 0.60, "MANA": 0.40},
            {"CHZ": 0.20, "MANA": 0.20, "RIF": 0.60},
            {"CHZ": 0.20, "MANA": 0.20, "SPELL": 0.60},
            {"CHZ": 0.20, "RIF": 0.20, "SPELL": 0.60},
            {"CHZ": 0.10, "MANA": 0.10, "RIF": 0.20, "SPELL": 0.60},
            {"CHZ": 0.30, "MANA": 0.20, "SPELL": 0.50},
            {"MANA": 0.20, "RIF": 0.20, "SPELL": 0.60},
        ],
        "scales": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        "monthly_loss_stops": [0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30],
    },
}


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


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def day_text(value):
    return parse_time(value).date().isoformat()


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def format_weights(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def name_weights(weights):
    return "_".join(f"{coin}{int(round(weight * 100))}" for coin, weight in sorted(weights.items()))


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def load_trades(path, start_month, end_month, coins):
    rows = []
    selected = set(coins)
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["coin"] not in selected:
                continue
            month = row["exit_time"][:7]
            if not (start_month <= month <= end_month):
                continue
            row["month"] = month
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            row["entry_day"] = row["entry_dt"].date().isoformat()
            row["exit_day"] = row["exit_dt"].date().isoformat()
            row["raw_return_pct"] = float(row["raw_return_pct"])
            rows.append(row)
    rows.sort(key=lambda item: (item["exit_dt"], item["entry_dt"], item["coin"]))
    return rows


def scenario_trades(robust, trades, scenario):
    adjusted, skipped, total_cost = robust.adjust_trades(trades, scenario)
    for row in adjusted:
        row["entry_dt"] = parse_time(row["entry_time"])
        row["exit_dt"] = parse_time(row["exit_time"])
        row["entry_day"] = row["entry_dt"].date().isoformat()
        row["exit_day"] = row["exit_dt"].date().isoformat()
        row["month"] = row["exit_time"][:7]
        row["raw_return_pct"] = float(row["raw_return_pct"])
    adjusted.sort(key=lambda item: (item["exit_dt"], item["entry_dt"], item["coin"]))
    return adjusted, skipped, total_cost


def day_range(start_month, end_month):
    start = datetime.fromisoformat(start_month + "-01").date()
    end_year, end_m = [int(part) for part in end_month.split("-")]
    if end_m == 12:
        end = datetime(end_year + 1, 1, 1).date()
    else:
        end = datetime(end_year, end_m + 1, 1).date()
    day = start
    while day < end:
        yield day.isoformat()
        day += timedelta(days=1)


def build_health(trades, start_month, end_month, windows):
    by_coin_day = defaultdict(lambda: defaultdict(list))
    for trade in trades:
        by_coin_day[trade["coin"]][trade["exit_day"]].append(float(trade["raw_return_pct"]))

    days = list(day_range(start_month, end_month))
    health = defaultdict(lambda: defaultdict(dict))
    for coin, day_map in by_coin_day.items():
        queues = {window: deque() for window in windows if window > 0}
        values = {window: [] for window in windows if window > 0}
        for day in days:
            today_values = day_map.get(day, [])
            for window in values:
                current = values[window]
                wins = [value for value in current if value > 0]
                losses = [value for value in current if value < 0]
                gross_loss = abs(sum(losses))
                pf = sum(wins) / gross_loss if gross_loss else (math.inf if wins else 0.0)
                health[coin][day][window] = {
                    "return_pct": sum(current),
                    "profit_factor": pf,
                    "trades": len(current),
                }

                queues[window].append((day, today_values))
                current.extend(today_values)
                while len(queues[window]) > window:
                    _old_day, old_values = queues[window].popleft()
                    if old_values:
                        remove = Counter(old_values)
                        kept = []
                        for value in current:
                            if remove[value] > 0:
                                remove[value] -= 1
                            else:
                                kept.append(value)
                        values[window] = kept
    return health


def policy_name(policy):
    gate = "nogate" if policy["gate_window"] == 0 else (
        f"h{policy['gate_window']}_r{policy['min_health_return_pct']}_pf{policy['min_health_pf']}_t{policy['min_health_trades']}"
    )
    daily = "dloff" if policy["daily_loss_stop_pct"] is None else f"dl{policy['daily_loss_stop_pct']}"
    limit = "maxoff" if policy["max_trades_per_coin_day"] is None else f"max{policy['max_trades_per_coin_day']}"
    streak = "streakoff" if policy["max_loss_streak"] is None else f"streak{policy['max_loss_streak']}p{policy['pause_days']}"
    return "_".join([gate, daily, limit, streak])


def passes_health(trade, policy, health):
    window = policy["gate_window"]
    if window == 0:
        return True
    row = health.get(trade["coin"], {}).get(trade["entry_day"], {}).get(window)
    if not row:
        return False
    return (
        row["return_pct"] >= policy["min_health_return_pct"]
        and row["profit_factor"] >= policy["min_health_pf"]
        and row["trades"] >= policy["min_health_trades"]
    )


def simulate(trades, months, weights, scale, target_cash, monthly_loss_stop_pct, policy, health):
    equity = INITIAL_BALANCE
    target_balance = INITIAL_BALANCE + target_cash
    selected = set(weights)
    month_rows = []
    trade_rows = []
    equity_points = [equity]
    all_pnls = []
    cash_withdrawn = 0.0
    skipped = Counter()
    trades_by_month = defaultdict(list)

    for trade in trades:
        if trade["coin"] in selected and trade["month"] in months:
            trades_by_month[trade["month"]].append(trade)

    pause_until = defaultdict(lambda: "")
    loss_streak = Counter()

    for month in months:
        start_balance = equity
        loss_floor = start_balance * (1.0 - monthly_loss_stop_pct) if monthly_loss_stop_pct is not None else -math.inf
        closed_month = False
        stop_reason = "month_end"
        daily_start = {}
        killed_days = set()
        per_day_coin_trades = Counter()
        month_pnls = []
        reasons = Counter()
        coins = Counter()

        for trade in trades_by_month.get(month, []):
            coin = trade["coin"]
            day = trade["entry_day"]

            if closed_month:
                skipped["month_closed"] += 1
                continue
            if day in killed_days:
                skipped["daily_loss_stop"] += 1
                continue
            if pause_until[coin] and day <= pause_until[coin]:
                skipped["loss_pause"] += 1
                continue
            if not passes_health(trade, policy, health):
                skipped["health_gate"] += 1
                continue
            if policy["max_trades_per_coin_day"] is not None:
                key = (day, coin)
                if per_day_coin_trades[key] >= policy["max_trades_per_coin_day"]:
                    skipped["max_trades_day"] += 1
                    continue

            daily_start.setdefault(day, equity)
            raw_ret = float(trade["raw_return_pct"]) / 100.0
            weighted_ret = raw_ret * weights[coin] * scale
            before = equity
            equity *= 1.0 + weighted_ret
            pnl = equity - before
            all_pnls.append(pnl)
            month_pnls.append(pnl)
            equity_points.append(equity)
            per_day_coin_trades[(day, coin)] += 1
            reasons[trade.get("reason", "")] += 1
            coins[coin] += 1

            if pnl < 0:
                loss_streak[coin] += 1
            else:
                loss_streak[coin] = 0

            if policy["max_loss_streak"] is not None and loss_streak[coin] >= policy["max_loss_streak"]:
                pause_until_dt = parse_time(trade["entry_time"]).date() + timedelta(days=policy["pause_days"])
                pause_until[coin] = pause_until_dt.isoformat()
                loss_streak[coin] = 0

            trade_rows.append(
                {
                    "month": month,
                    "coin": coin,
                    "entry_time": trade["entry_time"],
                    "exit_time": trade["exit_time"],
                    "raw_return_pct": trade["raw_return_pct"],
                    "weighted_return_pct": weighted_ret * 100.0,
                    "pnl": pnl,
                    "equity_after": equity,
                    "reason": trade.get("reason", ""),
                }
            )

            if equity >= target_balance:
                stop_reason = "cash_target"
                closed_month = True
            elif equity <= loss_floor:
                stop_reason = "monthly_loss_stop"
                closed_month = True
            elif policy["daily_loss_stop_pct"] is not None:
                day_floor = daily_start[day] * (1.0 - policy["daily_loss_stop_pct"])
                if equity <= day_floor:
                    killed_days.add(day)

        end_before_withdraw = equity
        month_pnl = end_before_withdraw - start_balance
        withdrawal = 0.0
        if equity > INITIAL_BALANCE:
            withdrawal = equity - INITIAL_BALANCE
            cash_withdrawn += withdrawal
            equity = INITIAL_BALANCE
            equity_points.append(equity)

        month_rows.append(
            {
                "month": month,
                "start_balance": start_balance,
                "month_pnl": month_pnl,
                "month_return_pct": (month_pnl / start_balance * 100.0) if start_balance else 0.0,
                "withdrawal": withdrawal,
                "end_before_withdraw": end_before_withdraw,
                "end_after_withdraw": equity,
                "stop_reason": stop_reason,
                "trades": len(month_pnls),
                "win_rate_pct": (sum(1 for pnl in month_pnls if pnl > 0) / len(month_pnls) * 100.0) if month_pnls else 0.0,
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(6)),
            }
        )

    gross_profit = sum(pnl for pnl in all_pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in all_pnls if pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0)
    peak = equity_points[0] if equity_points else INITIAL_BALANCE
    max_dd = 0.0
    for value in equity_points:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak - value) / peak * 100.0)

    return {
        "cash_hits": sum(1 for row in month_rows if row["withdrawal"] >= target_cash),
        "withdrawal_months": sum(1 for row in month_rows if row["withdrawal"] > 0),
        "positive_months": sum(1 for row in month_rows if row["month_pnl"] > 0),
        "negative_months": sum(1 for row in month_rows if row["month_pnl"] < 0),
        "cash_withdrawn": cash_withdrawn,
        "final_balance": equity,
        "net_result": cash_withdrawn + equity - INITIAL_BALANCE,
        "worst_month_pnl": min((row["month_pnl"] for row in month_rows), default=0.0),
        "best_month_pnl": max((row["month_pnl"] for row in month_rows), default=0.0),
        "max_drawdown_pct": max_dd,
        "profit_factor": profit_factor,
        "win_rate_pct": (sum(1 for pnl in all_pnls if pnl > 0) / len(all_pnls) * 100.0) if all_pnls else 0.0,
        "trades": len(all_pnls),
        "skipped_total": sum(skipped.values()),
        "skipped_health_gate": skipped["health_gate"],
        "skipped_daily_loss_stop": skipped["daily_loss_stop"],
        "skipped_loss_pause": skipped["loss_pause"],
        "skipped_max_trades_day": skipped["max_trades_day"],
        "skipped_month_closed": skipped["month_closed"],
        "monthly": month_rows,
        "trades_rows": trade_rows,
    }


def generate_policies(mode):
    if mode == "quick":
        policies = []
        gates = [
            (0, 0.0, 0.0, 0),
            (7, 0.0, 1.02, 5),
            (14, 0.0, 1.05, 10),
        ]
        daily_stops = [None, 0.05, 0.08]
        max_trades = [50, 100]
        streaks = [(None, 0), (3, 1)]
        for gate_window, min_ret, min_pf, min_trades in gates:
            for daily_stop in daily_stops:
                for max_day in max_trades:
                    for max_loss_streak, pause_days in streaks:
                        policies.append(
                            {
                                "gate_window": gate_window,
                                "min_health_return_pct": min_ret,
                                "min_health_pf": min_pf,
                                "min_health_trades": min_trades,
                                "daily_loss_stop_pct": daily_stop,
                                "max_trades_per_coin_day": max_day,
                                "max_loss_streak": max_loss_streak,
                                "pause_days": pause_days,
                            }
                        )
        return policies

    if mode == "focused":
        policies = []
        gates = [
            (0, 0.0, 0.0, 0),
            (7, 0.0, 1.02, 5),
            (14, 0.0, 1.05, 10),
            (30, 0.0, 1.05, 20),
        ]
        daily_stops = [None, 0.05, 0.08]
        max_trades = [50, 100, 250]
        streaks = [(None, 0), (3, 1)]
        for gate_window, min_ret, min_pf, min_trades in gates:
            for daily_stop in daily_stops:
                for max_day in max_trades:
                    for max_loss_streak, pause_days in streaks:
                        policies.append(
                            {
                                "gate_window": gate_window,
                                "min_health_return_pct": min_ret,
                                "min_health_pf": min_pf,
                                "min_health_trades": min_trades,
                                "daily_loss_stop_pct": daily_stop,
                                "max_trades_per_coin_day": max_day,
                                "max_loss_streak": max_loss_streak,
                                "pause_days": pause_days,
                            }
                        )
        return policies

    policies = []
    gates = [
        (0, 0.0, 0.0, 0),
        (7, 0.0, 1.02, 5),
        (7, 1.0, 1.05, 5),
        (14, 0.0, 1.05, 10),
        (14, 2.0, 1.08, 10),
        (30, 0.0, 1.05, 20),
        (30, 3.0, 1.10, 20),
    ]
    daily_stops = [None, 0.03, 0.05, 0.08, 0.10]
    max_trades = [None, 25, 50, 100, 250]
    streaks = [(None, 0), (2, 1), (3, 1), (5, 1)]
    for gate_window, min_ret, min_pf, min_trades in gates:
        for daily_stop in daily_stops:
            for max_day in max_trades:
                for max_loss_streak, pause_days in streaks:
                    policies.append(
                        {
                            "gate_window": gate_window,
                            "min_health_return_pct": min_ret,
                            "min_health_pf": min_pf,
                            "min_health_trades": min_trades,
                            "daily_loss_stop_pct": daily_stop,
                            "max_trades_per_coin_day": max_day,
                            "max_loss_streak": max_loss_streak,
                            "pause_days": pause_days,
                        }
                    )
    return policies


def result_row(profile_name, scenario_name, config_name, weights, scale, monthly_loss_stop, policy, result):
    return {
        "profile": profile_name,
        "scenario": scenario_name,
        "config": config_name,
        "weights": format_weights(weights),
        "scale": scale,
        "monthly_loss_stop_pct": monthly_loss_stop,
        "policy": policy_name(policy),
        "gate_window": policy["gate_window"],
        "min_health_return_pct": policy["min_health_return_pct"],
        "min_health_pf": policy["min_health_pf"],
        "min_health_trades": policy["min_health_trades"],
        "daily_loss_stop_pct": policy["daily_loss_stop_pct"] if policy["daily_loss_stop_pct"] is not None else "",
        "max_trades_per_coin_day": policy["max_trades_per_coin_day"] if policy["max_trades_per_coin_day"] is not None else "",
        "max_loss_streak": policy["max_loss_streak"] if policy["max_loss_streak"] is not None else "",
        "pause_days": policy["pause_days"],
        **{key: value for key, value in result.items() if key not in ("monthly", "trades_rows")},
    }


def sort_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            int(row["cash_hits"]),
            int(row["withdrawal_months"]),
            float(row["profit_factor"]),
            -float(row["max_drawdown_pct"]),
            float(row["net_result"]),
        ),
        reverse=True,
    )


def write_report(path, profile, args, search_rows, eval_rows):
    lines = [
        f"# {profile['title']}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Период: `{args.start_month}` - `{args.end_month}`.",
        f"Поиск велся в scenario `{args.search_scenario}`.",
        "",
        "Этот тест не меняет входы. Он проверяет только режимный overlay: rolling health, дневной стоп, лимит сделок и паузу после серии убыточных сделок.",
        "",
        "## Top Search",
        "",
        "| # | Config | Scenario | Hits | Net | MaxDD | PF | Trades | Policy |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(search_rows[:20], start=1):
        lines.append(
            f"| {idx} | `{row['config']}` `{row['weights']}` scale `{float(row['scale']):.2f}` "
            f"mstop `{float(row['monthly_loss_stop_pct']):.2f}` | `{row['scenario']}` | "
            f"{row['cash_hits']}/{len(list(month_iter(args.start_month, args.end_month)))} | "
            f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_pf(row['profit_factor'])} | {row['trades']} | `{row['policy']}` |"
        )

    lines.extend(
        [
            "",
            "## Scenario Check",
            "",
            "| Config | Scenario | Hits | Net | MaxDD | PF | Worst Month | Trades | Skipped health/day/pause/max |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in eval_rows[:120]:
        lines.append(
            f"| `{row['config']}` | `{row['scenario']}` | "
            f"{row['cash_hits']}/{len(list(month_iter(args.start_month, args.end_month)))} | "
            f"{fmt_money(row['net_result'])} | {fmt_pct(row['max_drawdown_pct'])} | "
            f"{fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} | "
            f"{row['skipped_health_gate']}/{row['skipped_daily_loss_stop']}/{row['skipped_loss_pause']}/{row['skipped_max_trades_day']} |"
        )

    best = search_rows[0] if search_rows else None
    lines.extend(["", "## Вывод", ""])
    if best:
        months = len(list(month_iter(args.start_month, args.end_month)))
        if int(best["cash_hits"]) == months:
            lines.append(
                f"Лучший вариант закрывает цель `({best['cash_hits']}/{months})` в поисковом stress-сценарии. "
                "Дальше его надо проверять как отдельную стратегию на свежих 24h/7d/30d и в paper."
            )
        else:
            lines.append(
                f"Даже лучший вариант закрывает только `{best['cash_hits']}/{months}` месяцев. "
                "Значит текущий набор входов нельзя считать стабильной cashflow-системой в этом режиме."
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary: `{args.save_summary}`",
            f"- Eval summary: `{args.save_eval_summary}`",
            f"- Monthly: `{args.save_monthly}`",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now().date().isoformat()
    parser = argparse.ArgumentParser(description="Regime-aware monthly cashflow tuner.")
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--search-scenario", default="fee003_slip0005")
    parser.add_argument("--policy-mode", choices=["quick", "focused", "full"], default="focused")
    parser.add_argument("--top-keep", type=int, default=30)
    parser.add_argument("--save-summary", default=f"data/regime_cashflow_tuner_summary_{today}.csv")
    parser.add_argument("--save-eval-summary", default=f"data/regime_cashflow_tuner_eval_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/regime_cashflow_tuner_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/regime-cashflow-tuner-{today}.md")
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    robust = load_module("monthly_cashflow_5pct_robust_search", ROBUST_PATH)
    trades_path = os.path.join(ROOT, args.trades_path)
    base_trades = load_trades(trades_path, args.start_month, args.end_month, profile["coins"])
    months = list(month_iter(args.start_month, args.end_month))
    policies = generate_policies(args.policy_mode)

    print(f"profile: {args.profile}")
    print(f"loaded trades: {len(base_trades)}")
    print(f"months: {args.start_month}..{args.end_month} ({len(months)})")
    print(f"weight configs: {len(profile['weights'])}")
    print(f"policies: {len(policies)}")

    scenario_map = {}
    health_map = {}
    for scenario in SCENARIOS:
        adjusted, skipped, total_cost = scenario_trades(robust, base_trades, scenario)
        scenario_map[scenario["name"]] = adjusted
        health_map[scenario["name"]] = build_health(adjusted, args.start_month, args.end_month, [7, 14, 30])
        print(f"scenario {scenario['name']}: trades={len(adjusted)} skipped_fill={skipped}", flush=True)

    search_trades = scenario_map[args.search_scenario]
    search_health = health_map[args.search_scenario]
    search_rows = []
    total = len(profile["weights"]) * len(profile["scales"]) * len(profile["monthly_loss_stops"]) * len(policies)
    done = 0

    for weights in profile["weights"]:
        config_name = name_weights(weights)
        for scale in profile["scales"]:
            for monthly_loss_stop in profile["monthly_loss_stops"]:
                for policy in policies:
                    done += 1
                    result = simulate(
                        search_trades,
                        months,
                        weights,
                        scale,
                        profile["target_cash"],
                        monthly_loss_stop,
                        policy,
                        search_health,
                    )
                    search_rows.append(
                        result_row(args.profile, args.search_scenario, config_name, weights, scale, monthly_loss_stop, policy, result)
                    )
                    if done % 10000 == 0:
                        print(f"searched {done}/{total}", flush=True)

    search_rows = sort_rows(search_rows)[: args.top_keep]

    eval_rows = []
    monthly_rows = []
    for config in search_rows:
        weights = {}
        for part in config["weights"].split(";"):
            coin, value = part.split(":")
            weights[coin] = float(value)
        policy = {
            "gate_window": int(config["gate_window"]),
            "min_health_return_pct": float(config["min_health_return_pct"]),
            "min_health_pf": float(config["min_health_pf"]),
            "min_health_trades": int(float(config["min_health_trades"])),
            "daily_loss_stop_pct": float(config["daily_loss_stop_pct"]) if config["daily_loss_stop_pct"] != "" else None,
            "max_trades_per_coin_day": int(float(config["max_trades_per_coin_day"])) if config["max_trades_per_coin_day"] != "" else None,
            "max_loss_streak": int(float(config["max_loss_streak"])) if config["max_loss_streak"] != "" else None,
            "pause_days": int(float(config["pause_days"])),
        }
        for scenario in SCENARIOS:
            result = simulate(
                scenario_map[scenario["name"]],
                months,
                weights,
                float(config["scale"]),
                profile["target_cash"],
                float(config["monthly_loss_stop_pct"]),
                policy,
                health_map[scenario["name"]],
            )
            row = result_row(
                args.profile,
                scenario["name"],
                config["config"],
                weights,
                float(config["scale"]),
                float(config["monthly_loss_stop_pct"]),
                policy,
                result,
            )
            eval_rows.append(row)
            for monthly in result["monthly"]:
                monthly_rows.append(
                    {
                        "profile": args.profile,
                        "scenario": scenario["name"],
                        "config": config["config"],
                        "weights": config["weights"],
                        "scale": config["scale"],
                        "monthly_loss_stop_pct": config["monthly_loss_stop_pct"],
                        "policy": config["policy"],
                        **monthly,
                    }
                )

    eval_rows = sort_rows(eval_rows)

    summary_fields = [
        "profile",
        "scenario",
        "config",
        "weights",
        "scale",
        "monthly_loss_stop_pct",
        "policy",
        "gate_window",
        "min_health_return_pct",
        "min_health_pf",
        "min_health_trades",
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
        "profile",
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
    save_csv(os.path.join(ROOT, args.save_summary), search_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_eval_summary), eval_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(os.path.join(ROOT, args.save_report), profile, args, search_rows, eval_rows)

    print("top search:")
    for row in search_rows[:10]:
        print(
            f"{row['config']} {row['weights']} scale={float(row['scale']):.2f} "
            f"mstop={float(row['monthly_loss_stop_pct']):.2f} policy={row['policy']} "
            f"hits={row['cash_hits']}/{len(months)} net={float(row['net_result']):.2f} "
            f"dd={float(row['max_drawdown_pct']):.2f} pf={fmt_pf(row['profit_factor'])} trades={row['trades']}"
        )
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved eval summary: {os.path.join(ROOT, args.save_eval_summary)}")
    print(f"saved monthly: {os.path.join(ROOT, args.save_monthly)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
