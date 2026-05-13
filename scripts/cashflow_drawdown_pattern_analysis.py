#!/usr/bin/env python3
"""Analyze drawdown patterns for fixed monthly cashflow portfolios.

The script answers two questions:
- where does the deep drawdown come from;
- can simple risk guards reduce max monthly DD while keeping monthly cashflow.
"""

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INITIAL_BALANCE = 1000.0


CANDIDATES = {
    "cashflow_1": {
        "label": "Минутка Cashflow 1 - GALA 20% / SPELL 80%",
        "weights": {"GALA": 0.20, "SPELL": 0.80},
        "scale": 6.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.35,
    },
    "cashflow_2": {
        "label": "Минутка Cashflow 2 - CHZ 10% / SHIB 10% / SPELL 80%",
        "weights": {"CHZ": 0.10, "SHIB": 0.10, "SPELL": 0.80},
        "scale": 10.0,
        "target_cash": 50.0,
        "monthly_loss_stop_pct": 0.50,
    },
}


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


def load_trades(path, start_month, end_month, coins):
    rows = []
    selected = set(coins)
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["coin"] not in selected:
                continue
            month = row["exit_time"][:7]
            if not (start_month <= month <= end_month):
                continue
            row = dict(row)
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            row["month"] = month
            row["raw_return_pct"] = float(row["raw_return_pct"])
            rows.append(row)
    rows.sort(key=lambda item: (item["exit_dt"], item["entry_dt"], item["coin"]))
    return rows


def profit_factor(values):
    gross_win = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    if gross_loss:
        return gross_win / gross_loss
    return math.inf if gross_win else 0.0


def max_drawdown(points):
    peak = points[0] if points else INITIAL_BALANCE
    dd = 0.0
    for value in points:
        peak = max(peak, value)
        if peak:
            dd = max(dd, (peak - value) / peak * 100.0)
    return dd


def apply_return(trade, weights, scale):
    return trade["raw_return_pct"] * weights.get(trade["coin"], 0.0) * scale


def simulate(
    trades,
    months,
    weights,
    scale,
    target_cash,
    monthly_loss_stop_pct,
    daily_loss_stop_pct=None,
):
    trades_by_month = defaultdict(list)
    for trade in trades:
        trades_by_month[trade["month"]].append(trade)

    equity = INITIAL_BALANCE
    all_pnls = []
    equity_points = [equity]
    monthly_rows = []
    trade_rows = []

    for month in months:
        start_equity = equity
        target_balance = INITIAL_BALANCE + target_cash
        loss_floor = start_equity * (1.0 - monthly_loss_stop_pct) if monthly_loss_stop_pct is not None else -math.inf
        month_peak = equity
        month_min = equity
        month_points = [equity]
        month_pnls = []
        month_rets = []
        reasons = Counter()
        coins = Counter()
        coin_pnl = Counter()
        coin_loss = Counter()
        daily_start = {}
        disabled_days = set()
        stop_reason = "month_end"
        stop_time = ""
        skipped_after_stop = 0
        skipped_daily = 0

        for trade in trades_by_month.get(month, []):
            day = trade["exit_time"][:10]
            if stop_reason != "month_end":
                skipped_after_stop += 1
                continue
            if day in disabled_days:
                skipped_daily += 1
                continue
            daily_start.setdefault(day, equity)

            before = equity
            ret_pct = apply_return(trade, weights, scale)
            equity *= 1.0 + ret_pct / 100.0
            pnl = equity - before
            month_pnls.append(pnl)
            month_rets.append(ret_pct)
            all_pnls.append(pnl)
            equity_points.append(equity)
            month_points.append(equity)
            month_peak = max(month_peak, equity)
            month_min = min(month_min, equity)
            reasons[trade["reason"]] += 1
            coins[trade["coin"]] += 1
            coin_pnl[trade["coin"]] += pnl
            if pnl < 0:
                coin_loss[trade["coin"]] += pnl

            trade_dd = (month_peak - equity) / month_peak * 100.0 if month_peak else 0.0
            trade_rows.append(
                {
                    "month": month,
                    "coin": trade["coin"],
                    "symbol": trade["symbol"],
                    "direction": trade.get("direction", ""),
                    "module": trade.get("module", ""),
                    "entry_time": trade["entry_time"],
                    "exit_time": trade["exit_time"],
                    "reason": trade["reason"],
                    "raw_return_pct": trade["raw_return_pct"],
                    "portfolio_return_pct": ret_pct,
                    "equity_before": before,
                    "equity_after": equity,
                    "pnl": pnl,
                    "month_drawdown_after_pct": trade_dd,
                }
            )

            if equity >= target_balance:
                stop_reason = "cash_target"
                stop_time = trade["exit_time"]
            elif equity <= loss_floor:
                stop_reason = "monthly_loss_stop"
                stop_time = trade["exit_time"]
            elif daily_loss_stop_pct is not None:
                daily_floor = daily_start[day] * (1.0 - daily_loss_stop_pct)
                if equity <= daily_floor:
                    disabled_days.add(day)

        end_before_withdraw = equity
        month_pnl = end_before_withdraw - start_equity
        withdrawal = 0.0
        if equity > INITIAL_BALANCE:
            withdrawal = equity - INITIAL_BALANCE
            equity = INITIAL_BALANCE
            equity_points.append(equity)

        monthly_rows.append(
            {
                "month": month,
                "start_equity": start_equity,
                "end_before_withdraw": end_before_withdraw,
                "end_after_withdraw": equity,
                "month_pnl": month_pnl,
                "withdrawal": withdrawal,
                "hit_target": withdrawal >= target_cash,
                "stop_reason": stop_reason,
                "stop_time": stop_time,
                "trades": len(month_pnls),
                "skipped_after_stop": skipped_after_stop,
                "skipped_daily": skipped_daily,
                "month_min_equity": month_min,
                "month_max_drawdown_pct": max_drawdown(month_points),
                "win_rate_pct": (
                    sum(1 for value in month_pnls if value > 0) / len(month_pnls) * 100.0
                    if month_pnls
                    else 0.0
                ),
                "profit_factor": profit_factor(month_pnls),
                "expectancy_pct": sum(month_rets) / len(month_rets) if month_rets else 0.0,
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(5)),
                "coin_pnl": repr(dict(coin_pnl)),
                "coin_loss": repr(dict(coin_loss)),
            }
        )

    return {
        "cash_hits": sum(1 for row in monthly_rows if row["hit_target"]),
        "withdrawal_months": sum(1 for row in monthly_rows if row["withdrawal"] > 0),
        "positive_months": sum(1 for row in monthly_rows if row["month_pnl"] > 0),
        "cash_withdrawn": sum(row["withdrawal"] for row in monthly_rows),
        "final_balance": equity,
        "net_result": sum(row["withdrawal"] for row in monthly_rows) + equity - INITIAL_BALANCE,
        "worst_month_pnl": min((row["month_pnl"] for row in monthly_rows), default=0.0),
        "max_drawdown_pct": max_drawdown(equity_points),
        "max_month_drawdown_pct": max((row["month_max_drawdown_pct"] for row in monthly_rows), default=0.0),
        "profit_factor": profit_factor(all_pnls),
        "trades": sum(row["trades"] for row in monthly_rows),
        "monthly": monthly_rows,
        "trades_detail": trade_rows,
    }


def row_for_sweep(candidate_key, candidate, label, target_cash, monthly_loss_stop_pct, daily_loss_stop_pct, scale, result):
    return {
        "candidate_key": candidate_key,
        "candidate": candidate["label"],
        "test": label,
        "target_cash": target_cash,
        "target_pct": target_cash / INITIAL_BALANCE * 100.0,
        "scale": scale,
        "monthly_loss_stop_pct": monthly_loss_stop_pct,
        "daily_loss_stop_pct": daily_loss_stop_pct if daily_loss_stop_pct is not None else "",
        "cash_hits": result["cash_hits"],
        "months": len(result["monthly"]),
        "cash_withdrawn": result["cash_withdrawn"],
        "net_result": result["net_result"],
        "final_balance": result["final_balance"],
        "worst_month_pnl": result["worst_month_pnl"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "max_month_drawdown_pct": result["max_month_drawdown_pct"],
        "profit_factor": result["profit_factor"],
        "trades": result["trades"],
    }


def run_sweeps(trades, months, candidate_key, candidate):
    rows = []
    weights = candidate["weights"]

    for scale in [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
        result = simulate(
            trades,
            months,
            weights,
            scale,
            candidate["target_cash"],
            candidate["monthly_loss_stop_pct"],
        )
        rows.append(row_for_sweep(candidate_key, candidate, "scale_sweep", candidate["target_cash"], candidate["monthly_loss_stop_pct"], None, scale, result))

    for monthly_stop in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        result = simulate(trades, months, weights, candidate["scale"], candidate["target_cash"], monthly_stop)
        rows.append(row_for_sweep(candidate_key, candidate, "monthly_stop_sweep", candidate["target_cash"], monthly_stop, None, candidate["scale"], result))

    for daily_stop in [0.02, 0.03, 0.05, 0.07, 0.10]:
        result = simulate(
            trades,
            months,
            weights,
            candidate["scale"],
            candidate["target_cash"],
            candidate["monthly_loss_stop_pct"],
            daily_loss_stop_pct=daily_stop,
        )
        rows.append(row_for_sweep(candidate_key, candidate, "daily_stop_sweep", candidate["target_cash"], candidate["monthly_loss_stop_pct"], daily_stop, candidate["scale"], result))

    for monthly_stop in [0.20, 0.25, 0.30, 0.35]:
        for daily_stop in [0.02, 0.03, 0.05]:
            result = simulate(
                trades,
                months,
                weights,
                candidate["scale"],
                candidate["target_cash"],
                monthly_stop,
                daily_loss_stop_pct=daily_stop,
            )
            rows.append(row_for_sweep(candidate_key, candidate, "combined_stop_sweep", candidate["target_cash"], monthly_stop, daily_stop, candidate["scale"], result))
    return rows


def write_report(path, args, candidate, baseline, worst_months, sweep_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    passing = [row for row in sweep_rows if int(row["cash_hits"]) == int(row["months"])]
    passing.sort(key=lambda row: (float(row["max_month_drawdown_pct"]), -float(row["profit_factor"]), -float(row["net_result"])))

    lines = [
        "# Cashflow Drawdown Pattern Analysis",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        f"Strategy: `{candidate['label']}`",
        "",
        "## Baseline",
        "",
        "| Target | Scale | Monthly Stop | Cash Hits | MaxDD | Max Month DD | PF | Net | Trades |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {fmt_pct(candidate['target_cash'] / INITIAL_BALANCE * 100.0)} | "
            f"{candidate['scale']:.2f} | {candidate['monthly_loss_stop_pct']:.0%} | "
            f"{baseline['cash_hits']}/{len(baseline['monthly'])} | {fmt_pct(baseline['max_drawdown_pct'])} | "
            f"{fmt_pct(baseline['max_month_drawdown_pct'])} | {fmt_pf(baseline['profit_factor'])} | "
            f"{fmt_money(baseline['net_result'])} | {baseline['trades']} |"
        ),
        "",
        "## Worst Drawdown Months",
        "",
        "| Month | Month DD | Withdrawal | Stop | Trades | PF | Coin PnL | Coin Loss |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ]
    for row in worst_months:
        lines.append(
            f"| {row['month']} | {fmt_pct(row['month_max_drawdown_pct'])} | "
            f"{fmt_money(row['withdrawal'])} | {row['stop_reason']} | {row['trades']} | "
            f"{fmt_pf(row['profit_factor'])} | `{row['coin_pnl']}` | `{row['coin_loss']}` |"
        )

    lines.extend(
        [
            "",
            "## Best Passing Risk Controls",
            "",
            "| Test | Scale | Monthly Stop | Daily Stop | Cash Hits | Max Month DD | PF | Net | Trades |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in passing[:15]:
        daily = f"{float(row['daily_loss_stop_pct']):.0%}" if row["daily_loss_stop_pct"] != "" else ""
        lines.append(
            f"| {row['test']} | {float(row['scale']):.2f} | {float(row['monthly_loss_stop_pct']):.0%} | "
            f"{daily} | {row['cash_hits']}/{row['months']} | "
            f"{fmt_pct(row['max_month_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{fmt_money(row['net_result'])} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Human Read",
            "",
        ]
    )
    if passing:
        best = passing[0]
        lines.append(
            f"Самый аккуратный вариант, который все еще держит все месяцы: `{best['test']}`, "
            f"scale `{float(best['scale']):.2f}`, monthly stop `{float(best['monthly_loss_stop_pct']):.0%}`, "
            f"daily stop `{best['daily_loss_stop_pct'] or 'off'}`. "
            f"Max month DD падает до `{fmt_pct(best['max_month_drawdown_pct'])}`."
        )
    else:
        lines.append("В проверенном наборе защит не найдено варианта, который сохраняет все месяцы и снижает DD.")
    lines.extend(
        [
            "",
            f"- Monthly CSV: `{args.save_monthly}`",
            f"- Sweep CSV: `{args.save_sweep}`",
            f"- Trades CSV: `{args.save_trades}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Analyze cashflow drawdown patterns.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), default="cashflow_2")
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--save-monthly", default=f"data/cashflow_drawdown_pattern_monthly_{today}.csv")
    parser.add_argument("--save-sweep", default=f"data/cashflow_drawdown_pattern_sweep_{today}.csv")
    parser.add_argument("--save-trades", default=f"data/cashflow_drawdown_pattern_trades_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/cashflow-drawdown-pattern-analysis-{today}.md")
    args = parser.parse_args()

    candidate = CANDIDATES[args.candidate]
    months = list(month_iter(args.start_month, args.end_month))
    trades = load_trades(os.path.join(ROOT, args.trades_path), args.start_month, args.end_month, candidate["weights"].keys())
    baseline = simulate(
        trades,
        months,
        candidate["weights"],
        candidate["scale"],
        candidate["target_cash"],
        candidate["monthly_loss_stop_pct"],
    )
    sweep_rows = run_sweeps(trades, months, args.candidate, candidate)
    worst_months = sorted(baseline["monthly"], key=lambda row: float(row["month_max_drawdown_pct"]), reverse=True)[:12]

    monthly_fields = [
        "month",
        "start_equity",
        "end_before_withdraw",
        "end_after_withdraw",
        "month_pnl",
        "withdrawal",
        "hit_target",
        "stop_reason",
        "stop_time",
        "trades",
        "skipped_after_stop",
        "skipped_daily",
        "month_min_equity",
        "month_max_drawdown_pct",
        "win_rate_pct",
        "profit_factor",
        "expectancy_pct",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
        "coin_pnl",
        "coin_loss",
    ]
    sweep_fields = [
        "candidate_key",
        "candidate",
        "test",
        "target_cash",
        "target_pct",
        "scale",
        "monthly_loss_stop_pct",
        "daily_loss_stop_pct",
        "cash_hits",
        "months",
        "cash_withdrawn",
        "net_result",
        "final_balance",
        "worst_month_pnl",
        "max_drawdown_pct",
        "max_month_drawdown_pct",
        "profit_factor",
        "trades",
    ]
    trade_fields = [
        "month",
        "coin",
        "symbol",
        "direction",
        "module",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "portfolio_return_pct",
        "equity_before",
        "equity_after",
        "pnl",
        "month_drawdown_after_pct",
    ]
    save_csv(os.path.join(ROOT, args.save_monthly), baseline["monthly"], monthly_fields)
    save_csv(os.path.join(ROOT, args.save_sweep), sweep_rows, sweep_fields)
    save_csv(os.path.join(ROOT, args.save_trades), baseline["trades_detail"], trade_fields)
    write_report(os.path.join(ROOT, args.save_report), args, candidate, baseline, worst_months, sweep_rows)

    print(f"candidate: {candidate['label']}")
    print(
        f"baseline cash={baseline['cash_hits']}/{len(months)} "
        f"max_month_dd={baseline['max_month_drawdown_pct']:.2f}% "
        f"pf={baseline['profit_factor']:.2f} net={baseline['net_result']:.2f}"
    )
    passing = [row for row in sweep_rows if int(row["cash_hits"]) == int(row["months"])]
    passing.sort(key=lambda row: (float(row["max_month_drawdown_pct"]), -float(row["profit_factor"]), -float(row["net_result"])))
    for row in passing[:10]:
        print(
            f"{row['test']} scale={float(row['scale']):.2f} "
            f"mstop={float(row['monthly_loss_stop_pct']):.2f} "
            f"dstop={row['daily_loss_stop_pct']} "
            f"cash={row['cash_hits']}/{row['months']} "
            f"max_month_dd={float(row['max_month_drawdown_pct']):.2f}% "
            f"pf={float(row['profit_factor']):.2f} net={float(row['net_result']):.2f}"
        )
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved sweep: {args.save_sweep}")
    print(f"saved trades: {args.save_trades}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
