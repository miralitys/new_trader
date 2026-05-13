#!/usr/bin/env python3
"""Funding, liquidation-buffer, and execution stress checks for ONE 11.2.1 x2."""

import argparse
import csv
import importlib.util
import io
import json
import math
import os
import time
import zipfile
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
ONE_PATH = os.path.join(ROOT, "scripts", "one_strategy_tweak_search.py")

SYMBOL = "ONEUSDT"
WINDOWS = [7, 30, 60, 90, 180, 365]
INITIAL_BALANCE = 1000.0
FUNDING_ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"

# ONE 11.2.1 x2: base portfolio_scale 1.05, then x2 leverage.
PORTFOLIO_SCALE_X2 = 2.10
SHORT_WEIGHT = 1.00
LONG_WEIGHT = 2.00
SHORT_BASE_POSITION = 0.24
LONG_BASE_POSITION = 0.18


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def time_ms(value):
    return int(parse_time(value).timestamp() * 1000)


def max_drawdown(equity_curve):
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, (peak - equity) / peak * 100.0)
    return drawdown


def summarize(trades, equity_curve, pnl_key="risk_pnl", return_key="risk_return_pct"):
    wins = [trade for trade in trades if trade[pnl_key] > 0]
    losses = [trade for trade in trades if trade[pnl_key] < 0]
    gross_wins = sum(trade[pnl_key] for trade in wins)
    gross_losses = abs(sum(trade[pnl_key] for trade in losses))
    returns = [trade[return_key] for trade in trades]
    winning_returns = [value for value in returns if value > 0]
    losing_returns = [value for value in returns if value < 0]
    final_equity = equity_curve[-1]["equity"] if equity_curve else INITIAL_BALANCE
    reasons = Counter(trade["reason"] for trade in trades)
    return {
        "trades": len(trades),
        "return_pct": (final_equity / INITIAL_BALANCE - 1.0) * 100.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else math.inf,
        "max_dd_pct": max_drawdown(equity_curve),
        "avg_win_pct": sum(winning_returns) / len(winning_returns) if winning_returns else 0.0,
        "avg_loss_pct": sum(losing_returns) / len(losing_returns) if losing_returns else 0.0,
        "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
        "final_equity": final_equity,
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
    }


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def strategy_args(multi, reinvest, strategy, fee_pct, slippage_pct, limit_offset, entry_mode):
    args = multi.make_strategy_args(reinvest, strategy, SYMBOL)
    args.fee_pct = fee_pct
    args.slippage_pct = slippage_pct
    args.limit_entry_offset_pct = limit_offset
    args.entry_mode = entry_mode
    return args


def run_base_trades(bt, reinvest, multi, candles, period, config):
    bars = period * bt.candles_per_day("1m")
    window = candles[-bars:]
    short_window = [dict(row) for row in window]
    long_window = [dict(row) for row in window]
    multi.apply_strategy_signals(short_window, "7.3")
    multi.apply_strategy_signals(long_window, "10")

    short_args = strategy_args(
        multi,
        reinvest,
        "7.3",
        config["fee_pct"],
        config["slippage_pct"],
        config["limit_offset"],
        config["entry_mode"],
    )
    long_args = strategy_args(
        multi,
        reinvest,
        "10",
        config["fee_pct"],
        config["slippage_pct"],
        config["limit_offset"],
        config["entry_mode"],
    )
    short_trades, _, _ = bt.run_backtest(short_window, short_args)
    long_trades, _, _ = bt.run_backtest(long_window, long_args)
    return short_trades, long_trades


def effective_position_pct(direction):
    if direction == "short":
        return SHORT_BASE_POSITION * PORTFOLIO_SCALE_X2 * SHORT_WEIGHT
    return LONG_BASE_POSITION * PORTFOLIO_SCALE_X2 * LONG_WEIGHT


def build_portfolio(short_trades, long_trades):
    source = []
    for trade in short_trades:
        item = dict(trade)
        item["module"] = "7.3 short"
        item["portfolio_weight"] = SHORT_WEIGHT
        source.append(item)
    for trade in long_trades:
        item = dict(trade)
        item["module"] = "10 long"
        item["portfolio_weight"] = LONG_WEIGHT
        source.append(item)

    selected = []
    open_trades = []
    equity = INITIAL_BALANCE
    equity_curve = [{"time": "initial", "equity": equity}]
    for trade in sorted(source, key=lambda item: (parse_time(item["entry_time"]), parse_time(item["exit_time"]))):
        entry_dt = parse_time(trade["entry_time"])
        open_trades = [item for item in open_trades if parse_time(item["exit_time"]) > entry_dt]
        if open_trades:
            continue

        adjusted_return_pct = trade["net_return_pct"] * PORTFOLIO_SCALE_X2 * trade["portfolio_weight"]
        equity_before = equity
        pnl = equity_before * adjusted_return_pct / 100.0
        equity += pnl

        output = dict(trade)
        output["portfolio_scale"] = PORTFOLIO_SCALE_X2
        output["risk_return_pct"] = adjusted_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        output["effective_position_pct"] = effective_position_pct(output["direction"])
        selected.append(output)
        open_trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})
    return selected, equity_curve


def fetch_funding_rates(start_ms, end_ms, cache_path):
    if os.path.exists(cache_path):
        rows = []
        with open(cache_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(
                    {
                        "funding_time_ms": int(row["funding_time_ms"]),
                        "funding_time": row["funding_time"],
                        "funding_rate": float(row["funding_rate"]),
                    }
                )
        return rows

    return fetch_funding_rates_from_archive(start_ms, end_ms, cache_path)


def fetch_funding_rates_from_api(start_ms, end_ms, cache_path):
    endpoint = "https://fapi.binance.com/fapi/v1/fundingRate"
    rows = []
    cursor = start_ms
    while cursor <= end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": SYMBOL,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        request = urllib.request.Request(
            f"{endpoint}?{params}", headers={"User-Agent": "one-risk-check/1.0"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        for item in payload:
            funding_ms = int(item["fundingTime"])
            rows.append(
                {
                    "funding_time_ms": funding_ms,
                    "funding_time": datetime.fromtimestamp(funding_ms / 1000).astimezone().isoformat(),
                    "funding_rate": float(item["fundingRate"]),
                }
            )
        last_ms = int(payload[-1]["fundingTime"])
        cursor = last_ms + 1
        if len(payload) < 1000:
            break
        time.sleep(0.1)

    save_csv(cache_path, rows, ["funding_time_ms", "funding_time", "funding_rate"])
    return rows


def first_day_of_month(value):
    return datetime(value.year, value.month, 1, tzinfo=value.tzinfo)


def next_month(value):
    if value.month == 12:
        return datetime(value.year + 1, 1, 1, tzinfo=value.tzinfo)
    return datetime(value.year, value.month + 1, 1, tzinfo=value.tzinfo)


def funding_archive_url(month):
    month_text = f"{month.year:04d}-{month.month:02d}"
    return f"{FUNDING_ARCHIVE_BASE}/{SYMBOL}/{SYMBOL}-fundingRate-{month_text}.zip"


def fetch_funding_rates_from_archive(start_ms, end_ms, cache_path):
    start_dt = datetime.fromtimestamp(start_ms / 1000).astimezone()
    end_dt = datetime.fromtimestamp(end_ms / 1000).astimezone()
    month = first_day_of_month(start_dt)
    end_month = first_day_of_month(end_dt)
    rows = []

    while month <= end_month:
        url = funding_archive_url(month)
        request = urllib.request.Request(url, headers={"User-Agent": "one-risk-check/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                month = next_month(month)
                continue
            raise

        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
            if csv_names:
                with archive.open(csv_names[0]) as handle:
                    reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"))
                    for item in reader:
                        funding_ms = int(item["calc_time"])
                        if start_ms <= funding_ms <= end_ms:
                            rows.append(
                                {
                                    "funding_time_ms": funding_ms,
                                    "funding_time": datetime.fromtimestamp(funding_ms / 1000)
                                    .astimezone()
                                    .isoformat(),
                                    "funding_rate": float(item["last_funding_rate"]),
                                }
                            )
        month = next_month(month)

    rows.sort(key=lambda row: row["funding_time_ms"])
    save_csv(cache_path, rows, ["funding_time_ms", "funding_time", "funding_rate"])
    return rows


def funding_return_pct_for_trade(trade, funding_rates):
    entry_ms = time_ms(trade["entry_time"])
    exit_ms = time_ms(trade["exit_time"])
    rates = [
        row["funding_rate"]
        for row in funding_rates
        if entry_ms <= row["funding_time_ms"] <= exit_ms
    ]
    rate_sum = sum(rates)
    exposure = trade["effective_position_pct"]
    if trade["direction"] == "long":
        return -exposure * rate_sum * 100.0, len(rates), rate_sum
    return exposure * rate_sum * 100.0, len(rates), rate_sum


def apply_funding(portfolio_trades, funding_rates):
    equity = INITIAL_BALANCE
    funded = []
    equity_curve = [{"time": "initial", "equity": equity}]
    total_funding_return_pct = 0.0
    total_events = 0
    for trade in portfolio_trades:
        funding_return_pct, funding_events, funding_rate_sum = funding_return_pct_for_trade(
            trade, funding_rates
        )
        total_return_pct = trade["risk_return_pct"] + funding_return_pct
        equity_before = equity
        pnl = equity_before * total_return_pct / 100.0
        equity += pnl
        output = dict(trade)
        output["funding_events"] = funding_events
        output["funding_rate_sum"] = funding_rate_sum
        output["funding_return_pct"] = funding_return_pct
        output["risk_return_pct_before_funding"] = trade["risk_return_pct"]
        output["risk_pnl_before_funding"] = trade["risk_pnl"]
        output["risk_return_pct"] = total_return_pct
        output["risk_equity_before"] = equity_before
        output["risk_pnl"] = pnl
        output["risk_equity_after"] = equity
        funded.append(output)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})
        total_funding_return_pct += funding_return_pct
        total_events += funding_events
    return funded, equity_curve, total_funding_return_pct, total_events


def liquidation_rows(portfolio_trades, candles, leverage, maintenance_margin_rate):
    open_index = {row["open_time"]: index for index, row in enumerate(candles)}
    close_index = {row["close_time"]: index for index, row in enumerate(candles)}
    isolated_liq_distance_pct = max(0.0, (1.0 / leverage - maintenance_margin_rate) * 100.0)
    rows = []
    worst = []
    for trade in portfolio_trades:
        entry_idx = open_index.get(trade["entry_time"])
        exit_idx = close_index.get(trade["exit_time"])
        if entry_idx is None or exit_idx is None:
            continue
        window = candles[entry_idx : exit_idx + 1]
        entry = float(trade["entry"])
        if trade["direction"] == "long":
            worst_price = min(row["low"] for row in window)
            mae_pct = max(0.0, (entry - worst_price) / entry * 100.0)
        else:
            worst_price = max(row["high"] for row in window)
            mae_pct = max(0.0, (worst_price - entry) / entry * 100.0)
        distance_to_liq_after_mae = isolated_liq_distance_pct - mae_pct
        rows.append(
            {
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "direction": trade["direction"],
                "effective_position_pct": trade["effective_position_pct"],
                "mae_pct": mae_pct,
                "approx_isolated_x2_liq_distance_pct": isolated_liq_distance_pct,
                "distance_to_liq_after_mae_pct": distance_to_liq_after_mae,
                "reason": trade["reason"],
            }
        )
        worst.append(mae_pct)
    worst_sorted = sorted(worst, reverse=True)
    summary = {
        "trades_checked": len(rows),
        "approx_isolated_x2_liq_distance_pct": isolated_liq_distance_pct,
        "worst_mae_pct": worst_sorted[0] if worst_sorted else 0.0,
        "p95_mae_pct": percentile(worst, 95),
        "p99_mae_pct": percentile(worst, 99),
        "trades_mae_over_10pct": sum(1 for value in worst if value >= 10.0),
        "trades_mae_over_25pct": sum(1 for value in worst if value >= 25.0),
        "trades_mae_over_liq_distance": sum(
            1 for value in worst if value >= isolated_liq_distance_pct
        ),
    }
    return rows, summary


def percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100.0) - 1))
    return ordered[index]


def row_from_summary(config_name, period, summary):
    return {"scenario": config_name, "period": f"{period}d", **summary}


def main():
    parser = argparse.ArgumentParser(description="Risk checks for ONE 11.2.1 x2.")
    parser.add_argument("--leverage", type=float, default=2.0)
    parser.add_argument("--maintenance-margin-rate", type=float, default=0.005)
    parser.add_argument("--save-prefix", default="data/one_11_2_1_x2")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    candles, _, _ = multi.fetch_klines_fast(SYMBOL, 365, 7)
    indicator_args = multi.make_strategy_args(reinvest, "7.3", SYMBOL)
    bt.add_indicators_and_signals(candles, indicator_args)

    stress_configs = [
        {
            "name": "base_maker",
            "fee_pct": 0.0002,
            "slippage_pct": 0.0,
            "limit_offset": 0.0,
            "entry_mode": "maker_limit",
        },
        {
            "name": "fee_0.04pct",
            "fee_pct": 0.0004,
            "slippage_pct": 0.0,
            "limit_offset": 0.0,
            "entry_mode": "maker_limit",
        },
        {
            "name": "fee_0.04pct_slip_0.01pct",
            "fee_pct": 0.0004,
            "slippage_pct": 0.0001,
            "limit_offset": 0.0,
            "entry_mode": "maker_limit",
        },
        {
            "name": "fee_0.04pct_slip_0.02pct",
            "fee_pct": 0.0004,
            "slippage_pct": 0.0002,
            "limit_offset": 0.0,
            "entry_mode": "maker_limit",
        },
        {
            "name": "strict_maker_offset_0.05pct",
            "fee_pct": 0.0002,
            "slippage_pct": 0.0,
            "limit_offset": 0.0005,
            "entry_mode": "maker_limit",
        },
    ]

    stress_rows = []
    base_portfolio_by_period = {}
    for config in stress_configs:
        for period in WINDOWS:
            short_trades, long_trades = run_base_trades(bt, reinvest, multi, candles, period, config)
            portfolio_trades, equity_curve = build_portfolio(short_trades, long_trades)
            summary = summarize(portfolio_trades, equity_curve)
            stress_rows.append(row_from_summary(config["name"], period, summary))
            if config["name"] == "base_maker":
                base_portfolio_by_period[period] = (portfolio_trades, equity_curve)

    start_ms = candles[0]["open_time_ms"]
    end_ms = candles[-1]["close_time_ms"]
    funding_path = os.path.join(ROOT, f"{args.save_prefix}_funding_rates.csv")
    funding_rates = fetch_funding_rates(start_ms, end_ms, funding_path)

    funding_rows = []
    for period in WINDOWS:
        portfolio_trades, _ = base_portfolio_by_period[period]
        funded_trades, funded_equity, total_funding_return_pct, total_funding_events = apply_funding(
            portfolio_trades, funding_rates
        )
        summary = summarize(funded_trades, funded_equity)
        row = row_from_summary("base_maker_plus_funding", period, summary)
        row["funding_events"] = total_funding_events
        row["sum_trade_funding_return_pct"] = total_funding_return_pct
        funding_rows.append(row)

    liq_trades, liq_summary = liquidation_rows(
        base_portfolio_by_period[365][0],
        candles,
        args.leverage,
        args.maintenance_margin_rate,
    )

    summary_fields = [
        "scenario",
        "period",
        "trades",
        "return_pct",
        "win_rate_pct",
        "profit_factor",
        "max_dd_pct",
        "avg_win_pct",
        "avg_loss_pct",
        "expectancy_pct",
        "final_equity",
        "take_profit",
        "stop_loss",
        "time_stop",
    ]
    funding_fields = summary_fields + ["funding_events", "sum_trade_funding_return_pct"]
    liq_trade_fields = [
        "entry_time",
        "exit_time",
        "direction",
        "effective_position_pct",
        "mae_pct",
        "approx_isolated_x2_liq_distance_pct",
        "distance_to_liq_after_mae_pct",
        "reason",
    ]
    liq_summary_fields = [
        "trades_checked",
        "approx_isolated_x2_liq_distance_pct",
        "worst_mae_pct",
        "p95_mae_pct",
        "p99_mae_pct",
        "trades_mae_over_10pct",
        "trades_mae_over_25pct",
        "trades_mae_over_liq_distance",
    ]

    save_csv(os.path.join(ROOT, f"{args.save_prefix}_execution_stress.csv"), stress_rows, summary_fields)
    save_csv(os.path.join(ROOT, f"{args.save_prefix}_funding_summary.csv"), funding_rows, funding_fields)
    save_csv(os.path.join(ROOT, f"{args.save_prefix}_liquidation_trades.csv"), liq_trades, liq_trade_fields)
    save_csv(os.path.join(ROOT, f"{args.save_prefix}_liquidation_summary.csv"), [liq_summary], liq_summary_fields)

    print("Execution stress:")
    for row in stress_rows:
        if row["period"] in ("365d", "180d", "90d"):
            print(
                f"{row['scenario']} {row['period']}: return={row['return_pct']:.2f}% "
                f"DD={row['max_dd_pct']:.2f}% PF={row['profit_factor']:.2f}"
            )
    print("Funding:")
    for row in funding_rows:
        print(
            f"{row['period']}: return={row['return_pct']:.2f}% DD={row['max_dd_pct']:.2f}% "
            f"events={row['funding_events']} funding_sum={row['sum_trade_funding_return_pct']:.4f}%"
        )
    print("Liquidation:")
    print(liq_summary)


if __name__ == "__main__":
    main()
