#!/usr/bin/env python3
"""Build a daily operational status table for the fixed strategy universe.

This is not an optimizer. It reads the fixed operational universe and answers a
small practical question for each row: trade, watch, or keep off based on recent
30/60 day health.
"""

import argparse
import csv
import importlib.util
import math
import os
import re
import sys
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
RIF_PATH = os.path.join(ROOT, "scripts", "rif_regime_monitor.py")
DYDX_TUNE_PATH = os.path.join(ROOT, "scripts", "dydx_pullback_short_tune.py")
DYDX_PROTECTION_PATH = os.path.join(ROOT, "scripts", "dydx_pullback_short_leverage_protection.py")
STRICT_SHORTLIST_PATH = os.path.join(
    ROOT, "data", "hot_coin_wave_strict_shortlist_binance_all_2026-05-04.csv"
)

INITIAL_BALANCE = 1000.0
HEALTH_WINDOWS = (30, 60)
DYDX_TUNE = None
DYDX_PROTECTION = None
STRESS_SCENARIOS = {
    "strict_maker": {
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "entry_mode": "maker_limit",
        "limit_entry_offset_pct": 0.0005,
    },
    "taker_like": {
        "fee_pct": 0.0004,
        "slippage_pct": 0.0002,
        "entry_mode": "next_open",
        "limit_entry_offset_pct": 0.0,
    },
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return "inf" if math.isinf(value) else f"{value:.2f}"


def latest_existing(pattern):
    import glob

    files = glob.glob(os.path.join(ROOT, pattern))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def parse_health_rule(rule):
    if not rule:
        return None
    window = re.search(r"(\d+)d\s+return", rule)
    min_return = re.search(r"return\s*>\s*([-+]?\d+(?:\.\d+)?)", rule)
    min_pf = re.search(r"PF\s*>=\s*([-+]?\d+(?:\.\d+)?)", rule)
    max_dd = re.search(r"MaxDD\s*<=\s*([-+]?\d+(?:\.\d+)?)%?", rule)
    min_trades = re.search(r"trades\s*>=\s*(\d+)", rule)
    if not window:
        return None
    return {
        "window": int(window.group(1)),
        "min_return": float(min_return.group(1)) if min_return else 0.0,
        "min_pf": float(min_pf.group(1)) if min_pf else 1.0,
        "max_dd": float(max_dd.group(1)) if max_dd else 100.0,
        "min_trades": int(min_trades.group(1)) if min_trades else 0,
    }


def passes_rule(rule, metrics):
    if rule is None:
        return False, "no numeric health rule"
    row = metrics.get(rule["window"])
    if not row:
        return False, f"no {rule['window']}d metrics"
    checks = [
        (
            row["return_pct"] > rule["min_return"],
            f"return {fmt_pct(row['return_pct'])} > {rule['min_return']:.2f}%",
            f"return {fmt_pct(row['return_pct'])} <= {rule['min_return']:.2f}%",
        ),
        (
            row["profit_factor"] >= rule["min_pf"],
            f"PF {fmt_num(row['profit_factor'])} >= {rule['min_pf']:.2f}",
            f"PF {fmt_num(row['profit_factor'])} < {rule['min_pf']:.2f}",
        ),
        (
            row["max_dd_pct"] <= rule["max_dd"],
            f"DD {fmt_num(row['max_dd_pct'])}% <= {rule['max_dd']:.2f}%",
            f"DD {fmt_num(row['max_dd_pct'])}% > {rule['max_dd']:.2f}%",
        ),
        (
            row["trades"] >= rule["min_trades"],
            f"trades {row['trades']} >= {rule['min_trades']}",
            f"trades {row['trades']} < {rule['min_trades']}",
        ),
    ]
    failed = [failed_text for passed, _, failed_text in checks if not passed]
    if failed:
        return False, "; ".join(failed)
    return True, "; ".join(passed_text for _, passed_text, _ in checks)


def empty_metrics():
    return {
        period: {
            "trades": "",
            "return_pct": "",
            "win_rate_pct": "",
            "profit_factor": "",
            "max_dd_pct": "",
            "expectancy_pct": "",
        }
        for period in HEALTH_WINDOWS
    }


def empty_stress_metrics():
    return {
        scenario: {
            "trades": "",
            "return_pct": "",
            "profit_factor": "",
            "max_dd_pct": "",
        }
        for scenario in STRESS_SCENARIOS
    }


def summarize(bt, trades, equity):
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    return {
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "expectancy_pct": summary["expectancy_pct"],
    }


def apply_execution(args, execution):
    if not execution:
        return args
    args.fee_pct = execution["fee_pct"]
    args.slippage_pct = execution["slippage_pct"]
    args.entry_mode = execution["entry_mode"]
    args.limit_entry_offset_pct = execution["limit_entry_offset_pct"]
    args.limit_entry_timeout_min = 1
    return args


def fetch_candles(bt, reinvest, multi, symbol, days, warmup_days):
    candles, _, _ = multi.fetch_klines_fast(symbol, days, warmup_days)
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    return candles


def run_template_strategy(bt, reinvest, multi, candles, symbol, template, period, execution=None):
    bars = period * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-bars:]]
    multi.apply_strategy_signals(rows, template)
    args = multi.make_strategy_args(reinvest, template, symbol)
    apply_execution(args, execution)
    trades, equity, _ = bt.run_backtest(rows, args)
    return summarize(bt, trades, equity)


def run_gala_112(bt, reinvest, multi, candles, symbol, period, execution=None):
    bars = period * bt.candles_per_day("1m")
    base = candles[-bars:]
    short_rows = [dict(row) for row in base]
    long_rows = [dict(row) for row in base]
    multi.apply_strategy_signals(short_rows, "7.3")
    multi.apply_strategy_signals(long_rows, "10")
    short_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    long_args = multi.make_strategy_args(reinvest, "10", symbol)
    apply_execution(short_args, execution)
    apply_execution(long_args, execution)
    short_trades, _, _ = bt.run_backtest(short_rows, short_args)
    long_trades, _, _ = bt.run_backtest(long_rows, long_args)
    _, _, summary = multi.build_112_portfolio(short_trades, long_trades)
    return {
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "expectancy_pct": summary["expectancy_pct"],
    }


def dydx_df_from_candles(candles):
    df = DYDX_TUNE.pd.DataFrame(
        candles,
        columns=["open_time_ms", "open", "high", "low", "close", "volume"],
    )
    for column in ["open_time_ms"]:
        df[column] = df[column].astype("int64")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = df[column].astype("float64")
    return df.sort_values("open_time_ms").drop_duplicates("open_time_ms").reset_index(drop=True)


def dydx_selected_protection():
    return {
        "leverage": 2,
        "effective_notional_pct": 130.0,
        "daily_stop_pct": 10.0,
        "weekly_stop_pct": 12.0,
        "stop_streak": 2,
        "cooldown_hours": 24,
        "ret24_abs_limit": 0.12,
        "ret7_abs_limit": 0.45,
        "name": "x2_d10_w12_st2_cd24_r240.12_r70.45",
    }


def run_dydx_x2_protected(candles, period, execution=None):
    bars = period * 1440
    df = dydx_df_from_candles(candles)
    df = DYDX_TUNE.add_closed_htf(DYDX_TUNE.add_closed_htf(DYDX_TUNE.add_indicators(df), 60), 240)
    signal = DYDX_TUNE.signal_for(df, DYDX_PROTECTION.VARIANT)
    sub_len = min(len(df), bars + 300)
    sub = df.tail(sub_len).reset_index(drop=True)
    sub_signal = signal[-sub_len:]
    fee_pct = execution["fee_pct"] if execution else 0.0002
    slippage_pct = execution["slippage_pct"] if execution else 0.0
    summary, _ = DYDX_PROTECTION.run_backtest(
        sub,
        sub_signal,
        dydx_selected_protection(),
        fee_pct,
        slippage_pct,
    )
    return {
        "trades": summary["trades"],
        "return_pct": summary["return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_dd_pct"],
        "expectancy_pct": summary["expectancy_pct"],
    }


def best_spec_for_symbol(cf, symbol):
    for spec in cf.BEST_SPECS:
        if spec["symbol"] == symbol and spec["kind"] == "single":
            return dict(spec)
    return None


def run_single_best(bt, reinvest, multi, cf, candles, spec, period, execution=None):
    bars = period * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-bars:]]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = cf.make_single_args(multi, reinvest, spec)
    apply_execution(args, execution)
    trades, equity, _ = bt.run_backtest(rows, args)
    return summarize(bt, trades, equity)


def cached_candles(bt, reinvest, multi, cache, symbol, days, warmup_days):
    candles = cache.get(symbol)
    if candles is None:
        candles = fetch_candles(bt, reinvest, multi, symbol, days, warmup_days)
        cache[symbol] = candles
    return candles


def run_best_period(bt, reinvest, multi, cf, source, candles, period, execution=None):
    symbol = source["symbol"]
    if source["strategy"] == "DYDX Pullback SHORT x2 Protected":
        return run_dydx_x2_protected(candles, period, execution)
    if source["strategy"] == "Минутка 7.3":
        return run_template_strategy(bt, reinvest, multi, candles, symbol, "7.3", period, execution)
    if source["strategy"] == "Минутка 10":
        return run_template_strategy(bt, reinvest, multi, candles, symbol, "10", period, execution)
    if source["strategy"] == "Минутка 11.2":
        return run_gala_112(bt, reinvest, multi, candles, symbol, period, execution)
    spec = best_spec_for_symbol(cf, symbol)
    if spec is None:
        raise RuntimeError(f"no fixed best spec for {symbol} / {source['strategy']}")
    return run_single_best(bt, reinvest, multi, cf, candles, spec, period, execution)


def evaluate_best_strategy(bt, reinvest, multi, cf, row, cache, days, warmup_days):
    symbol = row["symbol"]
    candles = cached_candles(bt, reinvest, multi, cache, symbol, days, warmup_days)
    return {
        period: run_best_period(bt, reinvest, multi, cf, row, candles, period)
        for period in HEALTH_WINDOWS
    }


def run_regime_period(bt, reinvest, multi, cf, rif, candles, spec, period, execution=None):
    bars = period * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-bars:]]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = rif.make_args(
        multi,
        reinvest,
        cf,
        spec,
        position_pct=1.0,
        daily_loss_stop_pct=0.02,
        weekly_loss_stop_pct=None,
    )
    apply_execution(args, execution)
    trades, equity, _ = bt.run_backtest(rows, args)
    return summarize(bt, trades, equity)


def evaluate_regime(bt, reinvest, multi, cf, rif, row, cache, days, warmup_days):
    symbol = row["symbol"]
    candles = cached_candles(bt, reinvest, multi, cache, symbol, days, warmup_days)
    spec = rif.spec_from_shortlist(STRICT_SHORTLIST_PATH, symbol)
    return {
        period: run_regime_period(bt, reinvest, multi, cf, rif, candles, spec, period)
        for period in HEALTH_WINDOWS
    }


def evaluate_best_stress(bt, reinvest, multi, cf, row, cache, period, days, warmup_days):
    candles = cached_candles(bt, reinvest, multi, cache, row["symbol"], days, warmup_days)
    return {
        name: run_best_period(bt, reinvest, multi, cf, row, candles, period, execution)
        for name, execution in STRESS_SCENARIOS.items()
    }


def evaluate_regime_stress(bt, reinvest, multi, cf, rif, row, cache, period, days, warmup_days):
    candles = cached_candles(bt, reinvest, multi, cache, row["symbol"], days, warmup_days)
    spec = rif.spec_from_shortlist(STRICT_SHORTLIST_PATH, row["symbol"])
    return {
        name: run_regime_period(bt, reinvest, multi, cf, rif, candles, spec, period, execution)
        for name, execution in STRESS_SCENARIOS.items()
    }


def passes_stress(stress_metrics, min_pf=1.0, max_dd=25.0, min_trades=3):
    failed = []
    passed_text = []
    for scenario in STRESS_SCENARIOS:
        row = stress_metrics.get(scenario)
        if not row:
            failed.append(f"{scenario}: no metrics")
            continue
        checks = [
            (row["return_pct"] > 0, f"return {fmt_pct(row['return_pct'])} > 0", f"return {fmt_pct(row['return_pct'])} <= 0"),
            (row["profit_factor"] >= min_pf, f"PF {fmt_num(row['profit_factor'])} >= {min_pf:.2f}", f"PF {fmt_num(row['profit_factor'])} < {min_pf:.2f}"),
            (row["max_dd_pct"] <= max_dd, f"DD {fmt_num(row['max_dd_pct'])}% <= {max_dd:.2f}%", f"DD {fmt_num(row['max_dd_pct'])}% > {max_dd:.2f}%"),
            (row["trades"] >= min_trades, f"trades {row['trades']} >= {min_trades}", f"trades {row['trades']} < {min_trades}"),
        ]
        scenario_failed = [failed_item for ok, _, failed_item in checks if not ok]
        if scenario_failed:
            failed.append(f"{scenario}: " + "; ".join(scenario_failed))
        else:
            passed_text.append(f"{scenario}: " + "; ".join(ok_item for _, ok_item, _ in checks))
    if failed:
        return False, " | ".join(failed)
    return True, " | ".join(passed_text)


def row_from_metrics(
    source,
    metrics,
    passed,
    reason,
    status,
    stress_metrics=None,
    stress_passed="",
    stress_reason="",
):
    m30 = metrics.get(30, {})
    m60 = metrics.get(60, {})
    stress = stress_metrics or empty_stress_metrics()
    strict = stress.get("strict_maker", {})
    taker = stress.get("taker_like", {})
    return {
        "symbol": source["symbol"],
        "asset": source["asset"],
        "monitor_group": source["monitor_group"],
        "strategy": source["strategy"],
        "side": source["side"],
        "role": source["role"],
        "status": status,
        "default_action": source["default_action"],
        "rule_passed": passed,
        "stress_passed": stress_passed,
        "paper_checked": "",
        "paper_signals": "",
        "paper_filled": "",
        "paper_fill_rate_pct": "",
        "paper_accepted": "",
        "paper_return_sum_pct": "",
        "paper_profit_factor": "",
        "paper_expectancy_pct": "",
        "reason": reason,
        "return_30d_pct": m30.get("return_pct", ""),
        "pf_30d": m30.get("profit_factor", ""),
        "dd_30d_pct": m30.get("max_dd_pct", ""),
        "trades_30d": m30.get("trades", ""),
        "win_30d_pct": m30.get("win_rate_pct", ""),
        "expectancy_30d_pct": m30.get("expectancy_pct", ""),
        "return_60d_pct": m60.get("return_pct", ""),
        "pf_60d": m60.get("profit_factor", ""),
        "dd_60d_pct": m60.get("max_dd_pct", ""),
        "trades_60d": m60.get("trades", ""),
        "win_60d_pct": m60.get("win_rate_pct", ""),
        "expectancy_60d_pct": m60.get("expectancy_pct", ""),
        "strict_return_30d_pct": strict.get("return_pct", ""),
        "strict_pf_30d": strict.get("profit_factor", ""),
        "strict_dd_30d_pct": strict.get("max_dd_pct", ""),
        "strict_trades_30d": strict.get("trades", ""),
        "taker_return_30d_pct": taker.get("return_pct", ""),
        "taker_pf_30d": taker.get("profit_factor", ""),
        "taker_dd_30d_pct": taker.get("max_dd_pct", ""),
        "taker_trades_30d": taker.get("trades", ""),
        "stress_reason": stress_reason,
        "health_rule": source["health_rule"],
        "kill_rule": source["kill_rule"],
        "notes": source["notes"],
    }


def status_from_rule(row, passed):
    if not passed:
        return "OFF"
    if row["default_action"] == "paper_trade" and row["role"] not in {"secondary_strategy"}:
        return "TRADE"
    return "WATCH"


def apply_stress_to_status(base_status, stress_passed, health_reason, stress_reason):
    if base_status == "TRADE" and not stress_passed:
        return "WATCH", f"{health_reason} | stress failed: {stress_reason}"
    if base_status == "TRADE" and stress_passed:
        return "TRADE", f"{health_reason} | stress passed"
    if base_status == "WATCH" and stress_passed:
        return "WATCH", f"{health_reason} | stress passed"
    if base_status == "WATCH" and not stress_passed:
        return "WATCH", f"{health_reason} | stress weak: {stress_reason}"
    return base_status, health_reason


def load_paper_overrides(path):
    if not path:
        return {}
    full_path = os.path.join(ROOT, path)
    if not os.path.exists(full_path):
        return {}
    overrides = {}
    for row in read_csv(full_path):
        overrides[(row.get("asset"), row.get("strategy"))] = row
    return overrides


def paper_number(row, key, default=0.0):
    try:
        value = row.get(key, "")
        return default if value == "" else float(value)
    except (TypeError, ValueError):
        return default


def apply_paper_override(output, paper_overrides, min_return, min_pf, min_accepted):
    paper = paper_overrides.get((output["asset"], output["strategy"]))
    if paper is None:
        return output

    accepted = int(paper_number(paper, "accepted", 0))
    paper_return = paper_number(paper, "accepted_return_sum_pct", 0.0)
    paper_pf = paper_number(paper, "accepted_profit_factor", 0.0)
    paper_fill = paper_number(paper, "fill_rate_pct", 0.0)
    output["paper_checked"] = True
    output["paper_signals"] = int(paper_number(paper, "signals", 0))
    output["paper_filled"] = int(paper_number(paper, "filled", 0))
    output["paper_fill_rate_pct"] = paper_fill
    output["paper_accepted"] = accepted
    output["paper_return_sum_pct"] = paper_return
    output["paper_profit_factor"] = paper_pf
    output["paper_expectancy_pct"] = paper_number(paper, "accepted_expectancy_pct", 0.0)

    failed = []
    if accepted < min_accepted:
        failed.append(f"paper accepted {accepted} < {min_accepted}")
    if paper_return <= min_return:
        failed.append(f"paper return {fmt_pct(paper_return)} <= {min_return:.2f}%")
    if paper_pf < min_pf:
        failed.append(f"paper PF {fmt_num(paper_pf)} < {min_pf:.2f}")

    if failed and output["status"] == "TRADE":
        output["status"] = "WATCH"
        output["reason"] = f"{output['reason']} | paper weak: {'; '.join(failed)}"
    elif not failed and output["status"] == "TRADE":
        output["reason"] = f"{output['reason']} | paper passed"
    elif failed:
        output["reason"] = f"{output['reason']} | paper weak: {'; '.join(failed)}"
    else:
        output["reason"] = f"{output['reason']} | paper passed"
    return output


def evaluate_cashflow(row, produced):
    if row["symbol"] == "GALAUSDT+SPELLUSDT":
        keys = [("GALAUSDT", "Минутка 11.2"), ("SPELLUSDT", "SPELL SHORT Best")]
    elif row["symbol"] == "ONEUSDT+SPELLUSDT":
        keys = [("ONEUSDT", "Минутка 11.2"), ("SPELLUSDT", "SPELL SHORT Best")]
    else:
        keys = []
    statuses = [produced.get(key, {}).get("status") for key in keys]
    if statuses and all(status == "TRADE" for status in statuses):
        status = "TRADE" if row["default_action"] == "paper_trade" else "WATCH"
        reason = "constituent strategies are TRADE"
        passed = True
    elif statuses and all(status in {"TRADE", "WATCH"} for status in statuses):
        status = "WATCH"
        reason = f"constituent strategies are mixed: {statuses}"
        passed = True
    else:
        status = "OFF"
        reason = f"constituent strategies are not healthy: {statuses}"
        passed = False
    return row_from_metrics(row, empty_metrics(), passed, reason, status)


def evaluate_wave(row):
    status = "WATCH" if row["default_action"] != "observe_only" else "OFF"
    reason = "requires separate hot/wave trigger; no always-on trade"
    return row_from_metrics(row, empty_metrics(), False, reason, status)


def save_report(path, rows, generated_at):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Operational Daily Monitor",
        "",
        f"Generated: {generated_at}",
        "",
        "| Status | Symbol | Group | Strategy | 30d | PF30 | DD30 | Stress taker 30d | Paper 7d | Paper PF | Reason |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    order = {"TRADE": 0, "WATCH": 1, "OFF": 2, "ERROR": 3}
    for row in sorted(rows, key=lambda item: (order.get(item["status"], 9), item["monitor_group"], item["asset"])):
        lines.append(
            f"| {row['status']} | {row['symbol']} | {row['monitor_group']} | {row['strategy']} | "
            f"{fmt_pct(row['return_30d_pct'])} | {fmt_num(row['pf_30d'])} | {fmt_num(row['dd_30d_pct'])}% | "
            f"{fmt_pct(row['taker_return_30d_pct'])} | {fmt_pct(row.get('paper_return_sum_pct', ''))} | "
            f"{fmt_num(row.get('paper_profit_factor', ''))} | {row['reason']} |"
        )
    lines.extend(
        [
            "",
            "## How To Read",
            "",
            "- TRADE: свежий health-check, stress и доступный paper-журнал не сломали стратегию.",
            "- WATCH: стратегия интересная, но ее нельзя включать автоматически, если stress или paper слабые.",
            "- OFF: свежие условия не проходят или нужен отдельный hot/wave trigger.",
            "",
            "Wave-монеты здесь не являются always-on. Для них нужен отдельный запуск hot/wave scanner.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Build daily operational strategy monitor.")
    parser.add_argument("--universe", default="data/operational_monitor_universe_2026-05-04.csv")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--stress-window", type=int, default=30)
    parser.add_argument("--stress-min-pf", type=float, default=1.0)
    parser.add_argument("--stress-max-dd", type=float, default=25.0)
    parser.add_argument("--stress-min-trades", type=int, default=3)
    parser.add_argument("--skip-stress", action="store_true")
    parser.add_argument("--paper-summary", default="")
    parser.add_argument("--paper-min-return", type=float, default=0.0)
    parser.add_argument("--paper-min-pf", type=float, default=1.0)
    parser.add_argument("--paper-min-accepted", type=int, default=5)
    parser.add_argument("--skip-paper-override", action="store_true")
    parser.add_argument("--save", default=f"data/operational_daily_monitor_v2_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/operational-daily-monitor-v2-{today}.md")
    args = parser.parse_args()

    universe = read_csv(os.path.join(ROOT, args.universe))

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)
    global DYDX_TUNE, DYDX_PROTECTION
    if any(source["strategy"] == "DYDX Pullback SHORT x2 Protected" for source in universe):
        DYDX_TUNE = load_module("dydx_pullback_short_tune", DYDX_TUNE_PATH)
        DYDX_PROTECTION = load_module("dydx_pullback_short_leverage_protection", DYDX_PROTECTION_PATH)

    cache = {}
    rows = []
    produced = {}
    generated_at = datetime.now(timezone.utc).isoformat()
    paper_path = args.paper_summary or latest_existing("data/paper_execution_summary_*.csv")
    paper_overrides = {} if args.skip_paper_override else load_paper_overrides(os.path.relpath(paper_path, ROOT) if paper_path else "")

    for index, source in enumerate(universe, start=1):
        print(f"[{index}/{len(universe)}] {source['asset']} {source['strategy']}...", flush=True)
        try:
            group = source["monitor_group"]
            if group == "best_strategy":
                metrics = evaluate_best_strategy(bt, reinvest, multi, cf, source, cache, args.days, args.warmup_days)
                rule = parse_health_rule(source["health_rule"])
                passed, reason = passes_rule(rule, metrics)
                status = status_from_rule(source, passed)
                stress_metrics = empty_stress_metrics()
                stress_passed = ""
                stress_reason = ""
                if not args.skip_stress:
                    stress_metrics = evaluate_best_stress(
                        bt,
                        reinvest,
                        multi,
                        cf,
                        source,
                        cache,
                        args.stress_window,
                        args.days,
                        args.warmup_days,
                    )
                    stress_passed, stress_reason = passes_stress(
                        stress_metrics,
                        min_pf=args.stress_min_pf,
                        max_dd=args.stress_max_dd,
                        min_trades=args.stress_min_trades,
                    )
                    status, reason = apply_stress_to_status(status, stress_passed, reason, stress_reason)
                output = row_from_metrics(
                    source,
                    metrics,
                    passed and (stress_passed if stress_passed != "" else True),
                    reason,
                    status,
                    stress_metrics,
                    stress_passed,
                    stress_reason,
                )
            elif group == "regime_monitor":
                metrics = evaluate_regime(bt, reinvest, multi, cf, rif, source, cache, args.days, args.warmup_days)
                health = {
                    period: {
                        "return_pct": metrics[period]["return_pct"],
                        "profit_factor": metrics[period]["profit_factor"],
                        "max_dd_pct": metrics[period]["max_dd_pct"],
                        "trades": metrics[period]["trades"],
                    }
                    for period in HEALTH_WINDOWS
                }
                passed, reason = rif.passes_gate("health30_60", health)
                status = "TRADE" if passed and source["role"] == "regime_core" else ("WATCH" if passed else "OFF")
                stress_metrics = empty_stress_metrics()
                stress_passed = ""
                stress_reason = ""
                if not args.skip_stress:
                    stress_metrics = evaluate_regime_stress(
                        bt,
                        reinvest,
                        multi,
                        cf,
                        rif,
                        source,
                        cache,
                        args.stress_window,
                        args.days,
                        args.warmup_days,
                    )
                    stress_passed, stress_reason = passes_stress(
                        stress_metrics,
                        min_pf=args.stress_min_pf,
                        max_dd=args.stress_max_dd,
                        min_trades=args.stress_min_trades,
                    )
                    status, reason = apply_stress_to_status(status, stress_passed, reason, stress_reason)
                output = row_from_metrics(
                    source,
                    metrics,
                    passed and (stress_passed if stress_passed != "" else True),
                    reason,
                    status,
                    stress_metrics,
                    stress_passed,
                    stress_reason,
                )
            elif group == "cashflow":
                output = evaluate_cashflow(source, produced)
            elif group == "wave_monitor":
                output = evaluate_wave(source)
            else:
                output = row_from_metrics(source, empty_metrics(), False, f"unknown group: {group}", "ERROR")
        except Exception as exc:
            output = row_from_metrics(source, empty_metrics(), False, str(exc), "ERROR")
        if source["monitor_group"] in {"best_strategy", "regime_monitor"} and output["status"] != "ERROR":
            output = apply_paper_override(
                output,
                paper_overrides,
                args.paper_min_return,
                args.paper_min_pf,
                args.paper_min_accepted,
            )
        rows.append(output)
        produced[(source["symbol"], source["strategy"])] = output

    fields = [
        "symbol",
        "asset",
        "monitor_group",
        "strategy",
        "side",
        "role",
        "status",
        "default_action",
        "rule_passed",
        "stress_passed",
        "paper_checked",
        "paper_signals",
        "paper_filled",
        "paper_fill_rate_pct",
        "paper_accepted",
        "paper_return_sum_pct",
        "paper_profit_factor",
        "paper_expectancy_pct",
        "reason",
        "return_30d_pct",
        "pf_30d",
        "dd_30d_pct",
        "trades_30d",
        "win_30d_pct",
        "expectancy_30d_pct",
        "return_60d_pct",
        "pf_60d",
        "dd_60d_pct",
        "trades_60d",
        "win_60d_pct",
        "expectancy_60d_pct",
        "strict_return_30d_pct",
        "strict_pf_30d",
        "strict_dd_30d_pct",
        "strict_trades_30d",
        "taker_return_30d_pct",
        "taker_pf_30d",
        "taker_dd_30d_pct",
        "taker_trades_30d",
        "stress_reason",
        "health_rule",
        "kill_rule",
        "notes",
    ]
    save_csv(os.path.join(ROOT, args.save), rows, fields)
    save_report(os.path.join(ROOT, args.save_report), rows, generated_at)
    print(f"saved csv: {args.save}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
