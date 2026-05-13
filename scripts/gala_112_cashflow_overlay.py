#!/usr/bin/env python3
"""Cashflow overlay tests for GALA Minutka 11.2.

The input is the already-built Minutka 11.2 portfolio trade stream. The overlay
models a monthly withdrawal rule:

- start with current account balance;
- if month-end equity is above the withdrawal floor, withdraw the excess;
- if month-end equity is below the withdrawal floor, do not top up;
- optional monthly loss stop, profit target, and stop-loss count limit.

This is a portfolio-level risk layer. It stops all further trading in a month
after a stop condition is hit.
"""

import argparse
import csv
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


INITIAL_BALANCE = 1000.0
WITHDRAWAL_FLOOR = 1000.0


@dataclass(frozen=True)
class CashflowConfig:
    name: str
    monthly_loss_stop_pct: Optional[float] = None
    monthly_profit_target_pct: Optional[float] = None
    max_stop_losses_per_month: Optional[int] = None


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def load_trades(path, start_month, end_month):
    months = set(month_iter(start_month, end_month))
    trades = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            month = row["exit_time"][:7]
            if month not in months:
                continue
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            row["risk_return_pct"] = float(row["risk_return_pct"])
            trades.append(row)
    return sorted(trades, key=lambda item: (item["entry_dt"], item["exit_dt"]))


def max_drawdown(points):
    if not points:
        return 0.0
    peak = points[0]["equity"]
    drawdown = 0.0
    for point in points:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def profit_factor(pnls):
    gross_win = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    if gross_loss == 0:
        return math.inf
    return gross_win / gross_loss


def simulate_config(trades, months, config, initial_balance=INITIAL_BALANCE, floor=WITHDRAWAL_FLOOR):
    by_month = {month: [] for month in months}
    for trade in trades:
        by_month[trade["exit_time"][:7]].append(trade)

    balance = initial_balance
    cash_withdrawn = 0.0
    equity_curve = [{"time": f"{months[0]}-01T00:00:00+00:00", "equity": balance}]
    monthly_rows = []
    all_pnls = []
    trades_taken = 0
    skipped_trades = 0

    for month in months:
        month_trades = by_month.get(month, [])
        start_balance = balance
        month_peak = balance
        month_stop_balance = (
            start_balance * (1.0 - config.monthly_loss_stop_pct)
            if config.monthly_loss_stop_pct is not None
            else None
        )
        month_target_balance = (
            floor * (1.0 + config.monthly_profit_target_pct)
            if config.monthly_profit_target_pct is not None
            else None
        )
        stopped = False
        stop_reason = "month_end"
        stop_losses = 0
        wins = 0
        losses = 0
        pnls = []
        reasons = Counter()
        modules = Counter()

        for trade in month_trades:
            if stopped:
                skipped_trades += 1
                continue

            before = balance
            ret = trade["risk_return_pct"] / 100.0
            balance *= 1.0 + ret
            pnl = balance - before
            month_peak = max(month_peak, balance)
            equity_curve.append({"time": trade["exit_time"], "equity": balance})
            trades_taken += 1
            pnls.append(pnl)
            all_pnls.append(pnl)
            reasons[trade["reason"]] += 1
            modules[trade["module"]] += 1
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

            if trade["reason"] == "stop_loss":
                stop_losses += 1

            if month_target_balance is not None and balance >= month_target_balance:
                stopped = True
                stop_reason = "profit_target"
            elif month_stop_balance is not None and balance <= month_stop_balance:
                stopped = True
                stop_reason = "loss_stop"
            elif (
                config.max_stop_losses_per_month is not None
                and stop_losses >= config.max_stop_losses_per_month
            ):
                stopped = True
                stop_reason = "stop_loss_limit"

        end_before_withdraw = balance
        month_pnl = end_before_withdraw - start_balance
        month_return_pct = (
            (end_before_withdraw / start_balance - 1.0) * 100.0 if start_balance else 0.0
        )
        withdrawal = max(0.0, end_before_withdraw - floor)
        if withdrawal > 0:
            cash_withdrawn += withdrawal
            balance = floor
            equity_curve.append({"time": f"{month}-withdraw", "equity": balance})

        monthly_rows.append(
            {
                "config": config.name,
                "month": month,
                "start_balance": start_balance,
                "trades": len(pnls),
                "skipped_trades": sum(1 for _ in month_trades) - len(pnls),
                "win_rate_pct": wins / len(pnls) * 100.0 if pnls else 0.0,
                "profit_factor": profit_factor(pnls),
                "month_return_pct": month_return_pct,
                "month_pnl_before_withdraw": month_pnl,
                "end_before_withdraw": end_before_withdraw,
                "withdrawal": withdrawal,
                "end_after_withdraw": balance,
                "cash_withdrawn_total": cash_withdrawn,
                "stop_reason": stop_reason,
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "short_trades": modules["7.3 short x1.5"],
                "long_trades": modules["10 long"],
            }
        )

    final_balance = balance
    net_result = cash_withdrawn + final_balance - initial_balance
    withdrawal_months = sum(1 for row in monthly_rows if row["withdrawal"] > 0)
    months_ending_above_floor = sum(1 for row in monthly_rows if row["end_before_withdraw"] > floor)
    negative_months = sum(1 for row in monthly_rows if row["month_pnl_before_withdraw"] < 0)
    return {
        "config": config.name,
        "months": len(months),
        "trades": trades_taken,
        "skipped_trades": skipped_trades,
        "total_withdrawn": cash_withdrawn,
        "final_balance": final_balance,
        "net_result": net_result,
        "net_result_pct": net_result / initial_balance * 100.0,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "profit_factor": profit_factor(all_pnls),
        "win_rate_pct": (
            sum(1 for pnl in all_pnls if pnl > 0) / len(all_pnls) * 100.0
            if all_pnls
            else 0.0
        ),
        "withdrawal_months": withdrawal_months,
        "months_ending_above_floor": months_ending_above_floor,
        "negative_months": negative_months,
        "loss_stop_months": sum(1 for row in monthly_rows if row["stop_reason"] == "loss_stop"),
        "profit_target_months": sum(
            1 for row in monthly_rows if row["stop_reason"] == "profit_target"
        ),
        "stop_loss_limit_months": sum(
            1 for row in monthly_rows if row["stop_reason"] == "stop_loss_limit"
        ),
        "monthly_rows": monthly_rows,
    }


def preset_configs():
    configs = [CashflowConfig("base_no_overlay")]
    for loss_stop in [0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]:
        configs.append(CashflowConfig(f"loss{loss_stop:.2%}_only", monthly_loss_stop_pct=loss_stop))

    for loss_stop in [0.03, 0.04, 0.05]:
        for target in [0.03, 0.05, 0.07]:
            configs.append(
                CashflowConfig(
                    f"loss{loss_stop:.0%}_target{target:.0%}",
                    monthly_loss_stop_pct=loss_stop,
                    monthly_profit_target_pct=target,
                )
            )
            configs.append(
                CashflowConfig(
                    f"loss{loss_stop:.0%}_target{target:.0%}_max2sl",
                    monthly_loss_stop_pct=loss_stop,
                    monthly_profit_target_pct=target,
                    max_stop_losses_per_month=2,
                )
            )
    for target in [0.03, 0.05, 0.07]:
        configs.append(
            CashflowConfig(f"target{target:.0%}_only", monthly_profit_target_pct=target)
        )
    return configs


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Test GALA 11.2 monthly cashflow overlays.")
    parser.add_argument("--trades", default="data/gala_minutka_11_2_1095d_trades.csv")
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--summary", default="data/gala_minutka_11_2_cashflow_summary.csv")
    parser.add_argument("--monthly", default="data/gala_minutka_11_2_cashflow_monthly.csv")
    args = parser.parse_args()

    months = list(month_iter(args.start_month, args.end_month))
    trades = load_trades(args.trades, args.start_month, args.end_month)
    results = [simulate_config(trades, months, config) for config in preset_configs()]
    results.sort(
        key=lambda item: (
            item["withdrawal_months"],
            item["net_result"],
            -item["max_drawdown_pct"],
        ),
        reverse=True,
    )

    summary_fields = [
        "config",
        "months",
        "trades",
        "skipped_trades",
        "total_withdrawn",
        "final_balance",
        "net_result",
        "net_result_pct",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "withdrawal_months",
        "months_ending_above_floor",
        "negative_months",
        "loss_stop_months",
        "profit_target_months",
        "stop_loss_limit_months",
    ]
    save_csv(args.summary, results, summary_fields)

    monthly_rows = []
    for result in results:
        monthly_rows.extend(result["monthly_rows"])
    monthly_fields = [
        "config",
        "month",
        "start_balance",
        "trades",
        "skipped_trades",
        "win_rate_pct",
        "profit_factor",
        "month_return_pct",
        "month_pnl_before_withdraw",
        "end_before_withdraw",
        "withdrawal",
        "end_after_withdraw",
        "cash_withdrawn_total",
        "stop_reason",
        "take_profit",
        "time_stop",
        "stop_loss",
        "short_trades",
        "long_trades",
    ]
    save_csv(args.monthly, monthly_rows, monthly_fields)

    print("config,trades,withdrawn,final,net,net_pct,max_dd,pf,win,withdraw_months,negative_months,loss_stop,target,stoploss_limit")
    for result in results:
        pf = result["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.3f}"
        print(
            f"{result['config']},{result['trades']},{result['total_withdrawn']:.2f},"
            f"{result['final_balance']:.2f},{result['net_result']:.2f},"
            f"{result['net_result_pct']:.2f},{result['max_drawdown_pct']:.2f},"
            f"{pf_text},{result['win_rate_pct']:.2f},{result['withdrawal_months']},"
            f"{result['negative_months']},{result['loss_stop_months']},"
            f"{result['profit_target_months']},{result['stop_loss_limit_months']}"
        )


if __name__ == "__main__":
    main()
