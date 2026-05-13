#!/usr/bin/env python3
"""Search monthly cashflow overlays on an existing trade pool.

The goal is not max yearly return. The goal is cashflow:
- start with 1000;
- withdraw profit above 1000 at month end;
- if balance is below 1000, do not top up;
- count months where at least 40 was actually withdrawn.

This script intentionally works from an existing trade pool CSV so the
cashflow/risk layer can be iterated quickly without re-downloading candles.
"""

import argparse
import csv
import itertools
import math
import os
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0


def parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    return float(value)


def load_trades(path, start_month, end_month):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Cashflow is based on realized PnL, so month assignment and ordering
            # use exit time rather than entry time.
            month = row["exit_time"][:7]
            if start_month <= month <= end_month:
                row["month"] = month
                row["raw_return_pct"] = parse_float(row["raw_return_pct"])
                rows.append(row)
    rows.sort(key=lambda item: (item["exit_time"], item["entry_time"], item["coin"]))
    return rows


def index_trades_by_month_coin(trades):
    rows_by_month_coin = defaultdict(lambda: defaultdict(list))
    for trade in trades:
        rows_by_month_coin[trade["month"]][trade["coin"]].append(trade)
    return rows_by_month_coin


def candidate_rows_by_month(rows_by_month_coin, months, weights):
    selected = set(weights)
    rows_by_month = {}
    for month in months:
        rows = []
        month_map = rows_by_month_coin.get(month, {})
        for coin in selected:
            rows.extend(month_map.get(coin, []))
        rows.sort(key=lambda item: (item["exit_time"], item["entry_time"], item["coin"]))
        rows_by_month[month] = rows
    return rows_by_month


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


def candidate_weights(coins, focus_coins, max_combo_size=3):
    candidates = {}
    coins = sorted(coins)
    focus = [coin for coin in focus_coins if coin in coins]

    if coins:
        candidates["equal_all"] = {coin: 1.0 / len(coins) for coin in coins}

    for coin in coins:
        candidates[f"{coin}_100"] = {coin: 1.0}

    pair_source = focus or coins
    for a, b in itertools.combinations(pair_source, 2):
        for aw in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            candidates[f"{a}{int(aw*100)}_{b}{int((1-aw)*100)}"] = {
                a: aw,
                b: 1.0 - aw,
            }

    if max_combo_size >= 3:
        for combo in itertools.combinations(pair_source, 3):
            candidates["_".join(combo) + "_equal"] = {coin: 1.0 / 3.0 for coin in combo}
            for heavy in combo:
                weights = {}
                for coin in combo:
                    weights[coin] = 0.5 if coin == heavy else 0.25
                candidates["_".join(combo) + f"_{heavy}50"] = weights

    # Keep the strongest hand-found combinations explicit.
    presets = {
        "JASMY30_SPELL70": {"JASMY": 0.3, "SPELL": 0.7},
        "GALA30_SHIB70": {"GALA": 0.3, "SHIB": 0.7},
        "CHZ30_SHIB70": {"CHZ": 0.3, "SHIB": 0.7},
        "CHZ30_SPELL70": {"CHZ": 0.3, "SPELL": 0.7},
        "ONE30_SPELL70": {"ONE": 0.3, "SPELL": 0.7},
        "JASMY50_ONE25_SPELL25": {"JASMY": 0.5, "ONE": 0.25, "SPELL": 0.25},
        "GALA20_SPELL75_AXL05": {"GALA": 0.20, "SPELL": 0.75, "AXL": 0.05},
        "GALA20_SPELL70_AXL10": {"GALA": 0.20, "SPELL": 0.70, "AXL": 0.10},
        "GALA20_SPELL65_AXL15": {"GALA": 0.20, "SPELL": 0.65, "AXL": 0.15},
        "GALA20_SPELL60_AXL20": {"GALA": 0.20, "SPELL": 0.60, "AXL": 0.20},
        "GALA20_SPELL55_AXL25": {"GALA": 0.20, "SPELL": 0.55, "AXL": 0.25},
        "GALA15_SPELL80_AXL05": {"GALA": 0.15, "SPELL": 0.80, "AXL": 0.05},
        "GALA15_SPELL75_AXL10": {"GALA": 0.15, "SPELL": 0.75, "AXL": 0.10},
        "GALA15_SPELL70_AXL15": {"GALA": 0.15, "SPELL": 0.70, "AXL": 0.15},
        "GALA10_SPELL85_AXL05": {"GALA": 0.10, "SPELL": 0.85, "AXL": 0.05},
        "GALA10_SPELL80_AXL10": {"GALA": 0.10, "SPELL": 0.80, "AXL": 0.10},
        "GALA25_SPELL70_AXL05": {"GALA": 0.25, "SPELL": 0.70, "AXL": 0.05},
        "GALA25_SPELL65_AXL10": {"GALA": 0.25, "SPELL": 0.65, "AXL": 0.10},
        "GALA30_SPELL65_AXL05": {"GALA": 0.30, "SPELL": 0.65, "AXL": 0.05},
        "GALA30_SPELL60_AXL10": {"GALA": 0.30, "SPELL": 0.60, "AXL": 0.10},
    }
    for name, weights in presets.items():
        if all(coin in coins for coin in weights):
            candidates[name] = weights

    return candidates


def simulate(rows_by_month, months, weights, loss_stop_pct, target_balance, scale):
    equity = INITIAL_BALANCE
    cash_withdrawn = 0.0
    all_pnls = []
    equity_points = [equity]
    monthly = []
    total_trades = 0
    skipped_trades = 0
    selected = set(weights)

    for month in months:
        start_balance = equity
        loss_floor = (
            start_balance * (1.0 - loss_stop_pct)
            if loss_stop_pct is not None
            else -math.inf
        )
        stop_reason = "month_end"
        closed = False
        month_pnls = []
        reasons = Counter()
        coins = Counter()

        for trade in rows_by_month.get(month, []):
            coin = trade["coin"]
            if coin not in selected:
                continue
            if closed:
                skipped_trades += 1
                continue

            ret = (trade["raw_return_pct"] / 100.0) * weights[coin] * scale
            before = equity
            equity *= 1.0 + ret
            pnl = equity - before
            all_pnls.append(pnl)
            month_pnls.append(pnl)
            equity_points.append(equity)
            total_trades += 1
            reasons[trade.get("reason", "")] += 1
            coins[coin] += 1

            if equity >= target_balance:
                stop_reason = "cash_target"
                closed = True
            elif equity <= loss_floor:
                stop_reason = "loss_stop"
                closed = True

        end_before_withdraw = equity
        month_pnl = end_before_withdraw - start_balance
        withdrawal = 0.0
        if equity > INITIAL_BALANCE:
            withdrawal = equity - INITIAL_BALANCE
            cash_withdrawn += withdrawal
            equity = INITIAL_BALANCE
            equity_points.append(equity)

        monthly.append(
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
                "win_rate_pct": (
                    sum(1 for pnl in month_pnls if pnl > 0) / len(month_pnls) * 100.0
                    if month_pnls
                    else 0.0
                ),
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(5)),
            }
        )

    gross_profit = sum(pnl for pnl in all_pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in all_pnls if pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else math.inf

    peak = equity_points[0] if equity_points else INITIAL_BALANCE
    max_dd = 0.0
    for point in equity_points:
        peak = max(peak, point)
        if peak:
            max_dd = max(max_dd, (peak - point) / peak * 100.0)

    cash_target = target_balance - INITIAL_BALANCE
    return {
        "cash_hits": sum(1 for row in monthly if row["withdrawal"] >= cash_target),
        "withdrawal_months": sum(1 for row in monthly if row["withdrawal"] > 0),
        "positive_months": sum(1 for row in monthly if row["month_pnl"] > 0),
        "negative_months": sum(1 for row in monthly if row["month_pnl"] < 0),
        "cash_withdrawn": cash_withdrawn,
        "final_balance": equity,
        "net_result": cash_withdrawn + equity - INITIAL_BALANCE,
        "worst_month_pnl": min((row["month_pnl"] for row in monthly), default=0.0),
        "best_month_pnl": max((row["month_pnl"] for row in monthly), default=0.0),
        "max_drawdown_pct": max_dd,
        "profit_factor": profit_factor,
        "win_rate_pct": (
            sum(1 for pnl in all_pnls if pnl > 0) / len(all_pnls) * 100.0
            if all_pnls
            else 0.0
        ),
        "trades": total_trades,
        "skipped_trades": skipped_trades,
        "monthly": monthly,
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Search monthly cashflow overlays.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_trades_24m.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--target-cash", type=float, default=40.0)
    parser.add_argument("--focus-coins", nargs="*", default=["GALA", "ONE", "CHZ", "SHIB", "JASMY", "SPELL"])
    parser.add_argument("--loss-stops", nargs="*", type=float, default=[0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12])
    parser.add_argument("--scales", nargs="*", type=float, default=[1.0, 1.25, 1.5, 2.0])
    parser.add_argument("--max-combo-size", type=int, choices=[1, 2, 3], default=3)
    parser.add_argument("--summary-path", default="data/monthly_cashflow_search_summary.csv")
    parser.add_argument("--monthly-path", default="data/monthly_cashflow_search_best_monthly.csv")
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()

    trades_path = os.path.join(ROOT, args.trades_path)
    summary_path = os.path.join(ROOT, args.summary_path)
    monthly_path = os.path.join(ROOT, args.monthly_path)
    months = list(month_iter(args.start_month, args.end_month))
    trades = load_trades(trades_path, args.start_month, args.end_month)
    rows_by_month = defaultdict(list)
    for trade in trades:
        rows_by_month[trade["month"]].append(trade)
    rows_by_month_coin = index_trades_by_month_coin(trades)

    coins = sorted({trade["coin"] for trade in trades})
    candidates = candidate_weights(
        coins,
        [coin.upper() for coin in args.focus_coins],
        max_combo_size=args.max_combo_size,
    )
    target_balance = INITIAL_BALANCE + args.target_cash

    results = []
    for name, weights in candidates.items():
        candidate_month_rows = candidate_rows_by_month(rows_by_month_coin, months, weights)
        for loss_stop in args.loss_stops:
            for scale in args.scales:
                result = simulate(candidate_month_rows, months, weights, loss_stop, target_balance, scale)
                row = {
                    "name": name,
                    "weights": format_weights(weights),
                    "scale": scale,
                    "loss_stop_pct": loss_stop,
                    "target_cash": args.target_cash,
                    "target_balance": target_balance,
                    "months": len(months),
                    **{key: value for key, value in result.items() if key != "monthly"},
                }
                results.append((row, result["monthly"]))

    results.sort(
        key=lambda item: (
            item[0]["cash_hits"],
            item[0]["withdrawal_months"],
            item[0]["positive_months"],
            item[0]["net_result"],
            -item[0]["max_drawdown_pct"],
        ),
        reverse=True,
    )

    summary_fields = [
        "name",
        "weights",
        "scale",
        "loss_stop_pct",
        "target_cash",
        "target_balance",
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
    ]
    save_csv(summary_path, [row for row, _ in results], summary_fields)

    best_row, best_monthly = results[0]
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
        "win_rate_pct",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
    ]
    save_csv(monthly_path, best_monthly, monthly_fields)

    print(
        "name,scale,loss,cash_hits,withdraw_months,pos_months,net,withdrawn,final,"
        "worst,best,dd,pf,win,trades,weights"
    )
    for row, _ in results[: args.top]:
        pf = row["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.3f}"
        print(
            f"{row['name']},{row['scale']:.2f},{row['loss_stop_pct']},"
            f"{row['cash_hits']}/{row['months']},"
            f"{row['withdrawal_months']}/{row['months']},"
            f"{row['positive_months']}/{row['months']},"
            f"{row['net_result']:.2f},{row['cash_withdrawn']:.2f},"
            f"{row['final_balance']:.2f},{row['worst_month_pnl']:.2f},"
            f"{row['best_month_pnl']:.2f},{row['max_drawdown_pct']:.2f},"
            f"{pf_text},{row['win_rate_pct']:.2f},{row['trades']},{row['weights']}"
        )
    print(f"saved summary: {summary_path}")
    print(f"saved best monthly: {monthly_path}")


if __name__ == "__main__":
    main()
