#!/usr/bin/env python3
"""Build and test a monthly cashflow portfolio across fixed best strategies.

This script uses the currently fixed no-leverage strategies:

- GALA 11.2 portfolio
- ONE 11.2 portfolio
- CHZ LONG Best
- SHIB LONG Best
- JASMY SHORT Best
- SAND LONG Best
- MANA LONG Best
- ANKR LONG Best
- SPELL SHORT Best

Each module is treated as an equal-weight sleeve of the same account. A trade's
standalone return is multiplied by the sleeve allocation before being applied to
portfolio equity.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0


BEST_SPECS = [
    {"coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
    {"coin": "ONE", "symbol": "ONEUSDT", "kind": "gala_112"},
    {
        "coin": "CHZ",
        "symbol": "CHZUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 90,
    },
    {
        "coin": "SHIB",
        "symbol": "1000SHIBUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 50,
        "regime": "wide",
        "position_pct": 1.0,
        "tp_pct": 0.0120,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "JASMY",
        "symbol": "JASMYUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 0.90,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "SAND",
        "symbol": "SANDUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 60,
    },
    {
        "coin": "MANA",
        "symbol": "MANAUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 70,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0050,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
    {
        "coin": "ANKR",
        "symbol": "ANKRUSDT",
        "kind": "single",
        "direction": "long",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 120,
    },
    {
        "coin": "SPELL",
        "symbol": "SPELLUSDT",
        "kind": "single",
        "direction": "short",
        "threshold": 60,
        "regime": "base",
        "position_pct": 1.0,
        "tp_pct": 0.0100,
        "sl_pct": 0.0400,
        "time_stop_min": 180,
    },
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_ok(row, regime):
    if regime == "base":
        return (
            in_range(row.get("atr_pct"), 0.0025, None)
            and in_range(row.get("dist_ema200"), -0.015, 0.015)
            and in_range(row.get("return_7d"), -0.40, 0.10)
        )
    if regime == "wide":
        return (
            in_range(row.get("atr_pct"), 0.0025, None)
            and in_range(row.get("dist_ema200"), -0.025, 0.025)
            and in_range(row.get("return_7d"), -0.50, 0.20)
        )
    raise ValueError(regime)


def apply_single_signals(rows, direction, threshold, regime):
    for row in rows:
        passed = regime_ok(row, regime)
        row["long_signal"] = False
        row["short_signal"] = False
        if direction == "long":
            row["long_signal"] = (
                row.get("long_score", 0.0) >= threshold
                and bool(row.get("smart_long_filter"))
                and passed
            )
        elif direction == "short":
            row["short_signal"] = row.get("short_score", 0.0) >= threshold and passed
        else:
            raise ValueError(direction)


def make_single_args(multi, reinvest, spec):
    template = "10" if spec["direction"] == "long" else "7.3"
    args = multi.make_strategy_args(reinvest, template, spec["symbol"])
    args.direction = spec["direction"]
    args.position_pct = spec["position_pct"]
    args.fee_pct = 0.0002
    args.slippage_pct = 0.0
    args.entry_mode = "maker_limit"
    args.limit_entry_offset_pct = 0.0
    args.limit_entry_timeout_min = 1
    args.daily_loss_stop_pct = 0.02
    args.time_stop_min = spec["time_stop_min"]
    args.long_time_stop_min = spec["time_stop_min"] if spec["direction"] == "long" else None
    args.short_time_stop_min = spec["time_stop_min"] if spec["direction"] == "short" else None
    if spec["direction"] == "long":
        args.long_tp_pct = spec["tp_pct"]
        args.long_sl_pct = spec["sl_pct"]
    else:
        args.short_tp_pct = spec["tp_pct"]
        args.short_sl_pct = spec["sl_pct"]
    return args


def normalize_trade(spec, trade, return_field="net_return_pct"):
    raw_return_pct = float(trade[return_field])
    return {
        "coin": spec["coin"],
        "symbol": spec["symbol"],
        "strategy": spec.get("strategy_name", spec["kind"]),
        "direction": trade.get("direction", ""),
        "module": trade.get("module", spec["coin"]),
        "entry_time": trade["entry_time"],
        "exit_time": trade["exit_time"],
        "entry_dt": parse_time(trade["entry_time"]),
        "exit_dt": parse_time(trade["exit_time"]),
        "reason": trade.get("reason", ""),
        "raw_return_pct": raw_return_pct,
    }


def build_gala_112(bt, reinvest, multi, candles, spec):
    short_window = [dict(row) for row in candles]
    long_window = [dict(row) for row in candles]
    multi.apply_strategy_signals(short_window, "7.3")
    multi.apply_strategy_signals(long_window, "10")
    short_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
    long_args = multi.make_strategy_args(reinvest, "10", spec["symbol"])
    short_trades, _, _ = bt.run_backtest(short_window, short_args)
    long_trades, _, _ = bt.run_backtest(long_window, long_args)
    portfolio_trades, _, _ = multi.build_112_portfolio(short_trades, long_trades)
    spec = dict(spec)
    spec["strategy_name"] = "11.2"
    return [normalize_trade(spec, trade, "risk_return_pct") for trade in portfolio_trades]


def build_single(bt, reinvest, multi, candles, spec):
    rows = [dict(row) for row in candles]
    apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = make_single_args(multi, reinvest, spec)
    trades, _, _ = bt.run_backtest(rows, args)
    spec = dict(spec)
    spec["strategy_name"] = (
        f"{spec['direction']} thr{spec['threshold']} {spec['regime']} "
        f"tp{spec['tp_pct']:.4f} t{spec['time_stop_min']}"
    )
    return [normalize_trade(spec, trade, "net_return_pct") for trade in trades]


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_existing_trades(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["raw_return_pct"] = float(row["raw_return_pct"])
            row["allocation"] = float(row.get("allocation", 0.0) or 0.0)
            row["portfolio_return_pct"] = float(row.get("portfolio_return_pct", 0.0) or 0.0)
            row["entry_dt"] = parse_time(row["entry_time"])
            row["exit_dt"] = parse_time(row["exit_time"])
            rows.append(row)
    return rows


def build_all_trades(days, warmup_days, save_path, reuse_existing=False):
    if reuse_existing:
        existing = load_existing_trades(save_path)
        if existing:
            return existing

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    all_trades = []
    diagnostics = []
    for spec in BEST_SPECS:
        print(f"Fetching/building {spec['coin']} {spec['symbol']} {spec['kind']}...")
        try:
            candles, start_day, end_day = multi.fetch_klines_fast(
                spec["symbol"], days, warmup_days
            )
            if not candles:
                raise RuntimeError("no candles")
            indicator_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
            bt.add_indicators_and_signals(candles, indicator_args)
            test_bars = days * bt.candles_per_day("1m")
            candles = candles[-test_bars:]
            if spec["kind"] == "gala_112":
                trades = build_gala_112(bt, reinvest, multi, candles, spec)
            else:
                trades = build_single(bt, reinvest, multi, candles, spec)
            all_trades.extend(trades)
            diagnostics.append(
                {
                    "coin": spec["coin"],
                    "symbol": spec["symbol"],
                    "status": "ok",
                    "candles": len(candles),
                    "start": candles[0]["open_time"],
                    "end": candles[-1]["close_time"],
                    "trades": len(trades),
                    "error": "",
                }
            )
            print(
                f"  ok candles={len(candles)} trades={len(trades)} "
                f"{candles[0]['open_time']}..{candles[-1]['close_time']}"
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "coin": spec["coin"],
                    "symbol": spec["symbol"],
                    "status": "error",
                    "candles": 0,
                    "start": "",
                    "end": "",
                    "trades": 0,
                    "error": str(exc),
                }
            )
            print(f"  error {spec['coin']}: {exc}")

    active_coins = sorted({trade["coin"] for trade in all_trades})
    allocation = 1.0 / len(active_coins) if active_coins else 0.0
    for trade in all_trades:
        trade["allocation"] = allocation
        trade["portfolio_return_pct"] = trade["raw_return_pct"] * allocation

    all_trades.sort(key=lambda item: (item["entry_dt"], item["exit_dt"], item["coin"]))
    fields = [
        "coin",
        "symbol",
        "strategy",
        "direction",
        "module",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "allocation",
        "portfolio_return_pct",
    ]
    save_csv(save_path, all_trades, fields)
    save_csv(
        os.path.splitext(save_path)[0] + "_diagnostics.csv",
        diagnostics,
        ["coin", "symbol", "status", "candles", "start", "end", "trades", "error"],
    )
    return all_trades


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


def simulate_months(
    trades,
    months,
    monthly_loss_stop_pct,
    monthly_profit_target_pct,
    mode,
    close_all_on_stop,
    initial_balance=INITIAL_BALANCE,
):
    trades_by_month = defaultdict(list)
    for trade in trades:
        month = trade["exit_time"][:7]
        if month in months:
            trades_by_month[month].append(trade)

    balance = initial_balance
    cash_withdrawn = 0.0
    equity_curve = [{"time": f"{months[0]}-01T00:00:00+00:00", "equity": balance}]
    monthly_rows = []
    all_pnls = []
    total_taken = 0
    total_skipped = 0

    for month in months:
        if mode == "monthly_reset":
            balance = initial_balance

        start_balance = balance
        loss_stop_balance = (
            start_balance * (1.0 - monthly_loss_stop_pct)
            if monthly_loss_stop_pct is not None
            else None
        )
        profit_target_balance = (
            start_balance * (1.0 + monthly_profit_target_pct)
            if monthly_profit_target_pct is not None
            else None
        )
        stop_time = None
        stop_reason = "month_end"
        pnls = []
        wins = 0
        losses = 0
        reasons = Counter()
        coins = Counter()

        month_trades = sorted(
            trades_by_month.get(month, []),
            key=lambda item: (item["exit_dt"], item["entry_dt"], item["coin"]),
        )
        for trade in month_trades:
            if stop_time is not None and (close_all_on_stop or trade["entry_dt"] >= stop_time):
                total_skipped += 1
                continue

            before = balance
            balance *= 1.0 + trade["portfolio_return_pct"] / 100.0
            pnl = balance - before
            pnls.append(pnl)
            all_pnls.append(pnl)
            total_taken += 1
            equity_curve.append({"time": trade["exit_time"], "equity": balance})
            reasons[trade["reason"]] += 1
            coins[trade["coin"]] += 1
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

            if profit_target_balance is not None and balance >= profit_target_balance:
                stop_time = trade["exit_dt"]
                stop_reason = "profit_target"
            elif loss_stop_balance is not None and balance <= loss_stop_balance:
                stop_time = trade["exit_dt"]
                stop_reason = "loss_stop"

        end_before_withdraw = balance
        month_pnl = end_before_withdraw - start_balance
        month_return_pct = (
            end_before_withdraw / start_balance - 1.0
        ) * 100.0 if start_balance else 0.0

        if mode == "carryover":
            withdrawal = max(0.0, end_before_withdraw - initial_balance)
            if withdrawal:
                cash_withdrawn += withdrawal
                balance = initial_balance
                equity_curve.append({"time": f"{month}-withdraw", "equity": balance})
        else:
            withdrawal = max(0.0, end_before_withdraw - initial_balance)
            cash_withdrawn += withdrawal
            balance = initial_balance

        monthly_rows.append(
            {
                "month": month,
                "mode": mode,
                "stop_handling": "close_all" if close_all_on_stop else "let_open_close",
                "loss_stop_pct": monthly_loss_stop_pct,
                "profit_target_pct": monthly_profit_target_pct,
                "start_balance": start_balance,
                "trades": len(pnls),
                "skipped_trades": len(month_trades) - len(pnls),
                "month_return_pct": month_return_pct,
                "month_pnl": month_pnl,
                "withdrawal": withdrawal,
                "end_before_withdraw": end_before_withdraw,
                "end_after_withdraw": balance,
                "stop_reason": stop_reason,
                "win_rate_pct": wins / len(pnls) * 100.0 if pnls else 0.0,
                "profit_factor": profit_factor(pnls),
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(5)),
            }
        )

    final_balance = balance
    if mode == "carryover":
        net_result = cash_withdrawn + final_balance - initial_balance
    else:
        net_result = sum(row["month_pnl"] for row in monthly_rows)

    positive_months = sum(1 for row in monthly_rows if row["month_pnl"] > 0)
    withdrawal_months = sum(1 for row in monthly_rows if row["withdrawal"] > 0)
    negative_months = sum(1 for row in monthly_rows if row["month_pnl"] < 0)

    return {
        "mode": mode,
        "stop_handling": "close_all" if close_all_on_stop else "let_open_close",
        "loss_stop_pct": monthly_loss_stop_pct,
        "profit_target_pct": monthly_profit_target_pct,
        "months": len(months),
        "positive_months": positive_months,
        "withdrawal_months": withdrawal_months,
        "negative_months": negative_months,
        "trades": total_taken,
        "skipped_trades": total_skipped,
        "cash_withdrawn": cash_withdrawn,
        "final_balance": final_balance,
        "net_result": net_result,
        "net_result_pct": net_result / initial_balance * 100.0,
        "max_drawdown_pct": max_drawdown(equity_curve),
        "profit_factor": profit_factor(all_pnls),
        "win_rate_pct": (
            sum(1 for pnl in all_pnls if pnl > 0) / len(all_pnls) * 100.0 if all_pnls else 0.0
        ),
        "worst_month_pnl": min((row["month_pnl"] for row in monthly_rows), default=0.0),
        "best_month_pnl": max((row["month_pnl"] for row in monthly_rows), default=0.0),
        "monthly_rows": monthly_rows,
    }


def run_search(trades, months):
    loss_values = [None, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.04]
    target_values = [None, 0.001, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03]
    results = []
    for mode in ("carryover", "monthly_reset"):
        for close_all_on_stop in (False, True):
            for loss_stop in loss_values:
                for target in target_values:
                    if loss_stop is None and target is None:
                        pass
                    results.append(
                        simulate_months(
                            trades,
                            months,
                            loss_stop,
                            target,
                            mode,
                            close_all_on_stop,
                        )
                    )
    results.sort(
        key=lambda item: (
            item["positive_months"],
            item["withdrawal_months"],
            item["net_result"],
            -item["max_drawdown_pct"],
        ),
        reverse=True,
    )
    return results


def save_results(summary_path, monthly_path, results):
    summary_fields = [
        "mode",
        "stop_handling",
        "loss_stop_pct",
        "profit_target_pct",
        "months",
        "positive_months",
        "withdrawal_months",
        "negative_months",
        "trades",
        "skipped_trades",
        "cash_withdrawn",
        "final_balance",
        "net_result",
        "net_result_pct",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "worst_month_pnl",
        "best_month_pnl",
    ]
    save_csv(summary_path, results, summary_fields)
    monthly_rows = []
    for index, result in enumerate(results):
        config = (
            f"{result['mode']}_{result['stop_handling']}_loss{result['loss_stop_pct']}_target"
            f"{result['profit_target_pct']}"
        )
        for row in result["monthly_rows"]:
            item = dict(row)
            item["config"] = config
            monthly_rows.append(item)
    monthly_fields = [
        "config",
        "month",
        "mode",
        "stop_handling",
        "loss_stop_pct",
        "profit_target_pct",
        "start_balance",
        "trades",
        "skipped_trades",
        "month_return_pct",
        "month_pnl",
        "withdrawal",
        "end_before_withdraw",
        "end_after_withdraw",
        "stop_reason",
        "win_rate_pct",
        "profit_factor",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
    ]
    save_csv(monthly_path, monthly_rows, monthly_fields)


def print_top(results, limit):
    print(
        "mode,stop_handling,loss,target,pos_months,withdraw_months,net,withdrawn,final,dd,pf,worst,best,trades,skipped"
    )
    for result in results[:limit]:
        pf = result["profit_factor"]
        pf_text = "inf" if pf == math.inf else f"{pf:.3f}"
        print(
            f"{result['mode']},{result['stop_handling']},"
            f"{result['loss_stop_pct']},{result['profit_target_pct']},"
            f"{result['positive_months']}/{result['months']},"
            f"{result['withdrawal_months']}/{result['months']},"
            f"{result['net_result']:.2f},{result['cash_withdrawn']:.2f},"
            f"{result['final_balance']:.2f},{result['max_drawdown_pct']:.2f},"
            f"{pf_text},{result['worst_month_pnl']:.2f},{result['best_month_pnl']:.2f},"
            f"{result['trades']},{result['skipped_trades']}"
        )


def main():
    parser = argparse.ArgumentParser(description="Test fixed best-strategy cashflow portfolio.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument(
        "--trades-path",
        default="data/cashflow_portfolio_best_trades_24m.csv",
    )
    parser.add_argument(
        "--summary-path",
        default="data/cashflow_portfolio_best_summary_24m.csv",
    )
    parser.add_argument(
        "--monthly-path",
        default="data/cashflow_portfolio_best_monthly_24m.csv",
    )
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    trades_path = os.path.join(ROOT, args.trades_path)
    summary_path = os.path.join(ROOT, args.summary_path)
    monthly_path = os.path.join(ROOT, args.monthly_path)

    trades = build_all_trades(
        args.days,
        args.warmup_days,
        trades_path,
        reuse_existing=args.reuse_existing,
    )
    months = list(month_iter(args.start_month, args.end_month))
    results = run_search(trades, months)
    save_results(summary_path, monthly_path, results)
    print_top(results, args.top)


if __name__ == "__main__":
    main()
