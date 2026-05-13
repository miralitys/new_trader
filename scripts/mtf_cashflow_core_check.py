#!/usr/bin/env python3
"""Check MTF filters on the fixed cashflow-core portfolios.

This is intentionally narrower than the full MTF universe pass. It answers one
specific question: if we apply the same higher-timeframe permission filter to
the components of GALA20/SPELL80 and ONE20/SPELL80, does monthly cashflow get
better or worse?
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
MTF_PATH = os.path.join(ROOT, "scripts", "gala_mtf_regime_backtest.py")
MTF_UNIVERSE_PATH = os.path.join(ROOT, "scripts", "mtf_universe_strategy_check.py")
MONTHLY_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_search.py")

BASELINE = "1m_only"
INITIAL_BALANCE = 1000.0


COMPONENT_SPECS = {
    "GALA": {"name": "GALA 11.2", "coin": "GALA", "symbol": "GALAUSDT", "kind": "gala_112"},
    "ONE": {"name": "ONE 11.2", "coin": "ONE", "symbol": "ONEUSDT", "kind": "gala_112"},
    "SPELL": {
        "name": "SPELL Best",
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
}

PORTFOLIOS = [
    {"name": "GALA20_SPELL80", "weights": {"GALA": 0.20, "SPELL": 0.80}},
    {"name": "ONE20_SPELL80", "weights": {"ONE": 0.20, "SPELL": 0.80}},
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


def parse_time(value):
    return value[:7]


def normalize_trade(spec, trade):
    if spec["kind"] == "gala_112":
        raw_return_pct = trade["risk_return_pct"]
        strategy = "11.2"
    else:
        raw_return_pct = trade["net_return_pct"]
        strategy = (
            f"{spec['direction']} thr{spec['threshold']} {spec['regime']} "
            f"tp{spec['tp_pct']:.4f} t{spec['time_stop_min']}"
        )
    return {
        "coin": spec["coin"],
        "symbol": spec["symbol"],
        "strategy": strategy,
        "direction": trade.get("direction", ""),
        "module": trade.get("module", spec["name"]),
        "entry_time": trade["entry_time"],
        "exit_time": trade["exit_time"],
        "reason": trade.get("reason", ""),
        "raw_return_pct": raw_return_pct,
        "month": parse_time(trade["exit_time"]),
    }


def build_component_trades(bt, reinvest, multi, cf, mtf, mtf_universe, spec, htf, candles, permissions):
    active_permissions = None if htf == BASELINE else permissions[htf]
    if spec["kind"] == "gala_112":
        trades, _, _, _ = mtf_universe.run_gala_112(
            bt, reinvest, multi, mtf, candles, spec, active_permissions
        )
    else:
        trades, _, _, _ = mtf_universe.run_single_spec(
            bt, reinvest, multi, cf, mtf, candles, spec, 730, active_permissions
        )
    return [normalize_trade(spec, trade) for trade in trades]


def max_drawdown(points):
    peak = points[0] if points else INITIAL_BALANCE
    output = 0.0
    for point in points:
        peak = max(peak, point)
        if peak:
            output = max(output, (peak - point) / peak * 100.0)
    return output


def compound_summary(trades, weights, scale):
    equity = INITIAL_BALANCE
    points = [equity]
    pnls = []
    selected = set(weights)
    for trade in sorted(trades, key=lambda item: (item["exit_time"], item["entry_time"], item["coin"])):
        coin = trade["coin"]
        if coin not in selected:
            continue
        before = equity
        ret = (trade["raw_return_pct"] / 100.0) * weights[coin] * scale
        equity *= 1.0 + ret
        pnls.append(equity - before)
        points.append(equity)

    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    return {
        "compound_return_pct": (equity / INITIAL_BALANCE - 1.0) * 100.0,
        "compound_max_dd_pct": max_drawdown(points),
        "compound_profit_factor": gross_profit / gross_loss if gross_loss else math.inf,
    }


def format_weights(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# MTF Cashflow Core Check",
        "",
        "Проверка портфелей `GALA20/SPELL80` и `ONE20/SPELL80` с MTF-фильтрами. Вход остается на `1m`; старший таймфрейм только блокирует часть входов.",
        "",
        "## Top Cashflow Rows",
        "",
        "| Portfolio | HTF | Scale | Loss stop | $40+ months | Withdrawn | MaxDD | PF | Compound | Compound DD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows[:30]:
        lines.append(
            f"| {row['portfolio']} | {row['htf']} | {float(row['scale']):.2f} | "
            f"{float(row['loss_stop_pct']):.2f} | {row['cash_hits']}/{row['months']} | "
            f"${float(row['cash_withdrawn']):.2f} | {float(row['max_drawdown_pct']):.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['compound_return_pct']):+.2f}% | "
            f"{float(row['compound_max_dd_pct']):.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Вывод",
            "",
            "Если MTF дает меньше cashflow-месяцев, значит фильтр стал хорошим для compounded-режима, но хуже для ежемесячной кассы.",
            "Строгий no-extra-exposure режим смотрится по `scale=1.0`; `scale=2.0` — повышенная экспозиция.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="MTF cashflow-core check.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--htfs", nargs="*", default=["3m", "5m", "10m", "15m", "30m", "1h"])
    parser.add_argument("--start-month", default="2024-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--target-cash", type=float, default=40.0)
    parser.add_argument("--scales", nargs="*", type=float, default=[1.0, 2.0])
    parser.add_argument("--loss-stops", nargs="*", type=float, default=[0.04, 0.08, 0.10, 0.12, 0.15])
    parser.add_argument("--save-summary", default="data/mtf_cashflow_core_summary.csv")
    parser.add_argument("--save-trades", default="data/mtf_cashflow_core_trades.csv")
    parser.add_argument("--save-report", default="strategies/mtf-cashflow-core-summary.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    mtf = load_module("gala_mtf_regime_backtest", MTF_PATH)
    mtf_universe = load_module("mtf_universe_strategy_check", MTF_UNIVERSE_PATH)
    monthly = load_module("monthly_cashflow_search", MONTHLY_PATH)

    component_data = {}
    needed_coins = sorted({coin for portfolio in PORTFOLIOS for coin in portfolio["weights"]})
    for coin in needed_coins:
        spec = COMPONENT_SPECS[coin]
        print(f"fetch {coin} {spec['symbol']}", flush=True)
        candles, _, _ = multi.fetch_klines_fast(spec["symbol"], args.days, args.warmup_days)
        base_args = multi.make_strategy_args(reinvest, "7.3", spec["symbol"])
        bt.add_indicators_and_signals(candles, base_args)
        test_bars = args.days * bt.candles_per_day("1m")
        candles = candles[-test_bars:]
        permissions = {}
        for htf in args.htfs:
            permissions[htf] = mtf.build_htf_permissions(bt, candles, base_args, htf)
        component_data[coin] = {"spec": spec, "candles": candles, "permissions": permissions}

    all_htfs = [BASELINE] + args.htfs
    trades_by_htf_coin = defaultdict(dict)
    trade_rows = []
    for htf in all_htfs:
        for coin in needed_coins:
            data = component_data[coin]
            print(f"build trades {coin} {htf}", flush=True)
            rows = build_component_trades(
                bt,
                reinvest,
                multi,
                cf,
                mtf,
                mtf_universe,
                data["spec"],
                htf,
                data["candles"],
                data["permissions"],
            )
            trades_by_htf_coin[htf][coin] = rows
            for row in rows:
                output = dict(row)
                output["htf"] = htf
                trade_rows.append(output)

    months = list(monthly.month_iter(args.start_month, args.end_month))
    target_balance = INITIAL_BALANCE + args.target_cash
    summary_rows = []
    for portfolio in PORTFOLIOS:
        weights = portfolio["weights"]
        for htf in all_htfs:
            trades = []
            for coin in weights:
                trades.extend(trades_by_htf_coin[htf].get(coin, []))
            rows_by_month_coin = monthly.index_trades_by_month_coin(
                [row for row in trades if args.start_month <= row["month"] <= args.end_month]
            )
            rows_by_month = monthly.candidate_rows_by_month(rows_by_month_coin, months, weights)
            for scale in args.scales:
                compound = compound_summary(trades, weights, scale)
                for loss_stop in args.loss_stops:
                    result = monthly.simulate(rows_by_month, months, weights, loss_stop, target_balance, scale)
                    summary_rows.append(
                        {
                            "portfolio": portfolio["name"],
                            "weights": format_weights(weights),
                            "htf": htf,
                            "scale": scale,
                            "loss_stop_pct": loss_stop,
                            "target_cash": args.target_cash,
                            "months": len(months),
                            **{key: value for key, value in result.items() if key != "monthly"},
                            **compound,
                        }
                    )

    summary_rows.sort(
        key=lambda row: (
            row["cash_hits"],
            row["withdrawal_months"],
            row["positive_months"],
            row["cash_withdrawn"],
            -row["max_drawdown_pct"],
        ),
        reverse=True,
    )

    summary_fields = [
        "portfolio",
        "weights",
        "htf",
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
        "compound_return_pct",
        "compound_max_dd_pct",
        "compound_profit_factor",
    ]
    trade_fields = [
        "htf",
        "coin",
        "symbol",
        "strategy",
        "direction",
        "module",
        "entry_time",
        "exit_time",
        "reason",
        "raw_return_pct",
        "month",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_trades), trade_rows, trade_fields)
    save_report(os.path.join(ROOT, args.save_report), summary_rows)

    print("portfolio,htf,scale,loss,cash_hits,withdrawn,dd,pf,compound,compound_dd")
    for row in summary_rows[:20]:
        print(
            f"{row['portfolio']},{row['htf']},{row['scale']:.2f},{row['loss_stop_pct']:.2f},"
            f"{row['cash_hits']}/{row['months']},{row['cash_withdrawn']:.2f},"
            f"{row['max_drawdown_pct']:.2f},{row['profit_factor']:.3f},"
            f"{row['compound_return_pct']:.2f},{row['compound_max_dd_pct']:.2f}"
        )
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved trades: {os.path.join(ROOT, args.save_trades)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
