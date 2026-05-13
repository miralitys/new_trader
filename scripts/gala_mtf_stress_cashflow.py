#!/usr/bin/env python3
"""Stress and monthly-cashflow checks for the best GALA MTF candidates."""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")

INITIAL_BALANCE = 1000.0
SYMBOL = "GALAUSDT"

CANDIDATES = [
    {"name": "7.3 + 1h", "strategy": "7.3", "htf": "1h"},
    {"name": "11.2 + 30m", "strategy": "11.2", "htf": "30m"},
    {"name": "11.2 + 1h", "strategy": "11.2", "htf": "1h"},
]

SCENARIOS = [
    {
        "name": "base_fee002_slip0",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "fee0025_slip0",
        "fee_pct": 0.00025,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "fee003_slip0",
        "fee_pct": 0.0003,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "fee004_slip0",
        "fee_pct": 0.0004,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "fee002_slip0005",
        "fee_pct": 0.0002,
        "slippage_pct": 0.00005,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "strict_maker_005",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0005,
        "limit_entry_timeout_min": 1,
    },
    {
        "name": "taker_like_fee004_slip002",
        "fee_pct": 0.0004,
        "slippage_pct": 0.0002,
        "entry_mode": "next_open",
        "limit_entry_offset_pct": 0.0,
        "limit_entry_timeout_min": 1,
    },
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


def month_iter(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def configure_execution(args, scenario):
    args.fee_pct = scenario["fee_pct"]
    args.slippage_pct = scenario["slippage_pct"]
    args.entry_mode = scenario["entry_mode"]
    args.limit_entry_offset_pct = scenario["limit_entry_offset_pct"]
    args.limit_entry_timeout_min = scenario["limit_entry_timeout_min"]
    return args


def run_module(bt, reinvest, multi, mtf, candles, module_name, days, permissions, scenario):
    needed = days * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-needed:]]
    multi.apply_strategy_signals(rows, module_name)
    mtf_stats = Counter()
    mtf_stats.update(mtf.apply_htf_filter(rows, permissions))

    args = multi.make_strategy_args(reinvest, module_name, SYMBOL)
    configure_execution(args, scenario)
    trades, equity, stats = bt.run_backtest(rows, args)
    stats.update(mtf_stats)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return trades, equity, summary, stats


def run_candidate(bt, reinvest, multi, mtf, candles, candidate, days, permissions, scenario):
    if candidate["strategy"] == "7.3":
        trades, equity, summary, stats = run_module(
            bt, reinvest, multi, mtf, candles, "7.3", days, permissions, scenario
        )
        return trades, equity, summary, stats

    if candidate["strategy"] == "11.2":
        short_trades, _, _, short_stats = run_module(
            bt, reinvest, multi, mtf, candles, "7.3", days, permissions, scenario
        )
        long_trades, _, _, long_stats = run_module(
            bt, reinvest, multi, mtf, candles, "10", days, permissions, scenario
        )
        portfolio_trades, portfolio_equity, portfolio_summary = multi.build_112_portfolio(
            short_trades, long_trades
        )
        stats = Counter()
        stats.update(short_stats)
        stats.update(long_stats)
        return portfolio_trades, portfolio_equity, portfolio_summary, stats

    raise ValueError(candidate["strategy"])


def stress_row(candidate, scenario, days, summary, stats):
    reasons = summary.get("exit_reasons", Counter())
    return {
        "candidate": candidate["name"],
        "strategy": candidate["strategy"],
        "htf": candidate["htf"],
        "scenario": scenario["name"],
        "period": f"{days}d",
        "days": days,
        "fee_pct": scenario["fee_pct"],
        "slippage_pct": scenario["slippage_pct"],
        "entry_mode": scenario["entry_mode"],
        "limit_entry_offset_pct": scenario["limit_entry_offset_pct"],
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "expectancy_pct": summary.get("expectancy_pct", 0.0),
        "final_equity": summary["final_equity"],
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "mtf_candidate_signals": stats.get("mtf_candidate_signals", 0),
        "mtf_blocked_total": stats.get("mtf_blocked_total", 0),
    }


def normalize_trade(candidate, trade):
    if candidate["strategy"] == "11.2":
        raw_return_pct = float(trade["risk_return_pct"])
        equity_after = float(trade["risk_equity_after"])
        module = trade.get("module", "")
    else:
        raw_return_pct = float(trade["net_return_pct"])
        equity_after = float(trade["equity_after"])
        module = "7.3 short"
    return {
        "candidate": candidate["name"],
        "coin": "GALA",
        "symbol": SYMBOL,
        "strategy": candidate["strategy"],
        "htf": candidate["htf"],
        "module": module,
        "direction": trade.get("direction", ""),
        "entry_time": trade["entry_time"],
        "exit_time": trade["exit_time"],
        "reason": trade.get("reason", ""),
        "raw_return_pct": raw_return_pct,
        "equity_after": equity_after,
    }


def index_trades_by_month(rows, start_month, end_month):
    output = defaultdict(list)
    for row in rows:
        month = row["exit_time"][:7]
        if start_month <= month <= end_month:
            output[month].append(row)
    for month_rows in output.values():
        month_rows.sort(key=lambda item: (item["exit_time"], item["entry_time"]))
    return output


def simulate_cashflow(rows_by_month, months, scale, loss_stop_pct, target_cash):
    target_balance = INITIAL_BALANCE + target_cash
    equity = INITIAL_BALANCE
    cash_withdrawn = 0.0
    equity_points = [equity]
    pnls = []
    monthly = []
    total_trades = 0
    skipped_trades = 0

    for month in months:
        start_balance = equity
        loss_floor = start_balance * (1.0 - loss_stop_pct)
        stop_reason = "month_end"
        closed = False
        month_pnls = []
        reasons = Counter()

        for trade in rows_by_month.get(month, []):
            if closed:
                skipped_trades += 1
                continue
            ret = trade["raw_return_pct"] / 100.0 * scale
            before = equity
            equity *= 1.0 + ret
            pnl = equity - before
            pnls.append(pnl)
            month_pnls.append(pnl)
            equity_points.append(equity)
            total_trades += 1
            reasons[trade.get("reason", "")] += 1

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
            }
        )

    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    pf = gross_profit / gross_loss if gross_loss else math.inf
    peak = equity_points[0]
    max_dd = 0.0
    for point in equity_points:
        peak = max(peak, point)
        if peak:
            max_dd = max(max_dd, (peak - point) / peak * 100.0)

    return {
        "cash_hits": sum(1 for row in monthly if row["withdrawal"] >= target_cash),
        "withdrawal_months": sum(1 for row in monthly if row["withdrawal"] > 0),
        "positive_months": sum(1 for row in monthly if row["month_pnl"] > 0),
        "negative_months": sum(1 for row in monthly if row["month_pnl"] < 0),
        "cash_withdrawn": cash_withdrawn,
        "final_balance": equity,
        "net_result": cash_withdrawn + equity - INITIAL_BALANCE,
        "worst_month_pnl": min((row["month_pnl"] for row in monthly), default=0.0),
        "best_month_pnl": max((row["month_pnl"] for row in monthly), default=0.0),
        "max_drawdown_pct": max_dd,
        "profit_factor": pf,
        "win_rate_pct": (
            sum(1 for pnl in pnls if pnl > 0) / len(pnls) * 100.0
            if pnls
            else 0.0
        ),
        "trades": total_trades,
        "skipped_trades": skipped_trades,
        "monthly": monthly,
    }


def run_cashflow_search(trade_rows, start_month, end_month, target_cash, scales, loss_stops):
    months = list(month_iter(start_month, end_month))
    output_rows = []
    monthly_rows = []
    by_candidate = defaultdict(list)
    for row in trade_rows:
        by_candidate[row["candidate"]].append(row)

    for candidate_name, rows in by_candidate.items():
        rows_by_month = index_trades_by_month(rows, start_month, end_month)
        for scale in scales:
            for loss_stop in loss_stops:
                result = simulate_cashflow(rows_by_month, months, scale, loss_stop, target_cash)
                row = {
                    "candidate": candidate_name,
                    "scale": scale,
                    "loss_stop_pct": loss_stop,
                    "target_cash": target_cash,
                    "months": len(months),
                    **{key: value for key, value in result.items() if key != "monthly"},
                }
                output_rows.append(row)
                for monthly in result["monthly"]:
                    monthly_rows.append({"candidate": candidate_name, "scale": scale, "loss_stop_pct": loss_stop, **monthly})

    output_rows.sort(
        key=lambda row: (
            row["cash_hits"],
            row["withdrawal_months"],
            row["positive_months"],
            row["net_result"],
            -row["max_drawdown_pct"],
        ),
        reverse=True,
    )
    return output_rows, monthly_rows


def format_pct(value):
    return f"{value:+.2f}%"


def format_pf(value):
    return "inf" if value == math.inf else f"{value:.2f}"


def save_report(path, stress_rows, cashflow_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# GALA MTF Stress + Cashflow",
        "",
        "Статус: проверка кандидатов, не фиксация новой стратегии.",
        "",
        "Проверяем кандидатов:",
        "",
        "- `7.3 + 1h`",
        "- `11.2 + 30m`",
        "- `11.2 + 1h`",
        "",
        "## Stress 730d",
        "",
        "| Candidate | Scenario | Return | MaxDD | PF | Trades |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for candidate in [item["name"] for item in CANDIDATES]:
        for scenario in [item["name"] for item in SCENARIOS]:
            row = next(
                item
                for item in stress_rows
                if item["candidate"] == candidate and item["scenario"] == scenario and item["days"] == 730
            )
            lines.append(
                f"| {candidate} | {scenario} | {format_pct(row['return_pct'])} | "
                f"{row['max_dd_pct']:.2f}% | {format_pf(row['profit_factor'])} | {row['trades']} |"
            )

    lines.extend(
        [
            "",
            "## Monthly Cashflow 24M",
            "",
            "Режим: старт `$1000`, цель снять `$40+` в месяц, если баланс ниже `$1000` - не пополняем, следующий месяц начинается с текущего остатка.",
            "",
            "| Candidate | Scale | Loss stop | $40+ months | Withdrawn | Final | MaxDD | PF | WinRate | Trades |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    best_by_candidate = {}
    for row in cashflow_rows:
        best_by_candidate.setdefault(row["candidate"], row)

    for candidate in [item["name"] for item in CANDIDATES]:
        row = best_by_candidate[candidate]
        lines.append(
            f"| {candidate} | {row['scale']:.2f} | {row['loss_stop_pct']:.2f} | "
            f"{row['cash_hits']}/{row['months']} | ${row['cash_withdrawn']:.2f} | "
            f"${row['final_balance']:.2f} | {row['max_drawdown_pct']:.2f}% | "
            f"{format_pf(row['profit_factor'])} | {row['win_rate_pct']:.2f}% | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Вывод",
            "",
            "Фиксировать новую MTF-стратегию можно только если она проходит stress и дает нормальный cashflow без чрезмерного масштаба риска.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Stress and cashflow for GALA MTF candidates.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--stress-periods", nargs="*", type=int, default=[365, 730])
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--target-cash", type=float, default=40.0)
    parser.add_argument("--scales", nargs="*", type=float, default=[1.0, 1.25, 1.5, 2.0])
    parser.add_argument("--loss-stops", nargs="*", type=float, default=[0.04, 0.06, 0.08, 0.10, 0.12, 0.15])
    parser.add_argument("--save-stress", default="data/gala_mtf_stress_summary.csv")
    parser.add_argument("--save-trades", default="data/gala_mtf_cashflow_trades_24m.csv")
    parser.add_argument("--save-cashflow", default="data/gala_mtf_cashflow_summary_24m.csv")
    parser.add_argument("--save-monthly", default="data/gala_mtf_cashflow_monthly_24m.csv")
    parser.add_argument("--save-report", default="strategies/GALA/gala-mtf-stress-cashflow.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    mtf = load_module("gala_mtf_regime_backtest", MTF_PATH)

    print(f"fetching {SYMBOL} days={args.days} warmup={args.warmup_days}", flush=True)
    candles, _, _ = multi.fetch_klines_fast(SYMBOL, args.days, args.warmup_days)
    base_args = multi.make_strategy_args(reinvest, "7.3", SYMBOL)
    bt.add_indicators_and_signals(candles, base_args)
    test_bars = args.days * bt.candles_per_day("1m")
    candles = candles[-test_bars:]
    print(
        f"candles={len(candles)} start={candles[0]['open_time']} end={candles[-1]['close_time']}",
        flush=True,
    )

    permissions = {}
    for htf in sorted({candidate["htf"] for candidate in CANDIDATES}):
        print(f"building htf permissions {htf}", flush=True)
        permissions[htf] = mtf.build_htf_permissions(bt, candles, base_args, htf)

    stress_rows = []
    base_trade_rows = []
    for candidate in CANDIDATES:
        for scenario in SCENARIOS:
            for period in args.stress_periods:
                print(f"stress {candidate['name']} {scenario['name']} {period}d", flush=True)
                trades, _, summary, stats = run_candidate(
                    bt,
                    reinvest,
                    multi,
                    mtf,
                    candles,
                    candidate,
                    period,
                    permissions[candidate["htf"]],
                    scenario,
                )
                stress_rows.append(stress_row(candidate, scenario, period, summary, stats))
                if scenario["name"] == "base_fee002_slip0" and period == args.days:
                    base_trade_rows.extend(normalize_trade(candidate, trade) for trade in trades)

    cashflow_rows, monthly_rows = run_cashflow_search(
        base_trade_rows,
        args.start_month,
        args.end_month,
        args.target_cash,
        args.scales,
        args.loss_stops,
    )

    stress_fields = [
        "candidate",
        "strategy",
        "htf",
        "scenario",
        "period",
        "days",
        "fee_pct",
        "slippage_pct",
        "entry_mode",
        "limit_entry_offset_pct",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
        "mtf_candidate_signals",
        "mtf_blocked_total",
    ]
    trade_fields = [
        "candidate",
        "coin",
        "symbol",
        "strategy",
        "htf",
        "module",
        "direction",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "equity_after",
    ]
    cashflow_fields = [
        "candidate",
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
    ]
    monthly_fields = [
        "candidate",
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
    ]

    save_csv(os.path.join(ROOT, args.save_stress), stress_rows, stress_fields)
    save_csv(os.path.join(ROOT, args.save_trades), base_trade_rows, trade_fields)
    save_csv(os.path.join(ROOT, args.save_cashflow), cashflow_rows, cashflow_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    save_report(os.path.join(ROOT, args.save_report), stress_rows, cashflow_rows)

    print(f"saved stress: {os.path.join(ROOT, args.save_stress)}")
    print(f"saved trades: {os.path.join(ROOT, args.save_trades)}")
    print(f"saved cashflow: {os.path.join(ROOT, args.save_cashflow)}")
    print(f"saved monthly: {os.path.join(ROOT, args.save_monthly)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
