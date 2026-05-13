#!/usr/bin/env python3
"""Create a paper execution journal for the current core/watch strategies.

The daily monitor tells us which strategies look healthy. This script goes one
level deeper: for every historical signal in the chosen window it records the
limit order, whether price actually touched it, and the resulting paper exit.
Run it daily to compare theoretical backtests with realistic maker-limit fills.
"""

import argparse
import csv
import importlib.util
import math
import os
import sys
from collections import Counter, defaultdict
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
DEFAULT_MODULES = ("ANKR", "RIF", "GALA_73", "GALA_112", "SPELL", "DYDX_X2")
AVAILABLE_MODULES = ("ANKR", "RIF", "GALA_73", "GALA_10", "GALA_112", "SPELL", "DYDX_X2")
DYDX_TUNE = None
DYDX_PROTECTION = None


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


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def apply_execution(args, entry_mode, fee_pct, slippage_pct, limit_offset, timeout_min):
    args.entry_mode = entry_mode
    args.fee_pct = fee_pct
    args.slippage_pct = slippage_pct
    args.limit_entry_offset_pct = limit_offset
    args.limit_entry_timeout_min = timeout_min
    return args


def spec_by_symbol(cf, symbol):
    for spec in cf.BEST_SPECS:
        if spec["symbol"] == symbol and spec["kind"] == "single":
            return dict(spec)
    raise RuntimeError(f"Best spec not found for {symbol}")


def fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market):
    if market == "futures_archive":
        candles, _, _ = multi.fetch_klines_fast(symbol, days, warmup_days)
    else:
        candles = bt.fetch_klines(market, symbol, days + warmup_days, "1m")
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    indicator_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    bt.add_indicators_and_signals(candles, indicator_args)
    bars = days * bt.candles_per_day("1m")
    return candles[-bars:]


def tp_sl_levels(direction, entry, args):
    if direction == "long":
        return entry * (1.0 + args.long_tp_pct), entry * (1.0 - args.long_sl_pct)
    return entry * (1.0 - args.short_tp_pct), entry * (1.0 + args.short_sl_pct)


def journal_loop(bt, candles, args, meta, portfolio_weight=1.0):
    """Run a backtest-like loop and record filled and unfilled entry attempts."""
    rows = []
    equity = args.initial_balance
    index = 0
    attempt_number = 0

    while index < len(candles) - 1:
        direction = bt.pick_signal(candles[index], args.direction)
        if direction is None:
            index += 1
            continue

        attempt_number += 1
        signal_row = candles[index]
        order_start_idx = index + 1
        order_row = candles[order_start_idx]
        entry_info, waited_until_idx = bt.find_entry_fill(candles, index, direction, args)
        limit_price = (
            bt.limit_entry_price(direction, order_row["open"], args.limit_entry_offset_pct)
            if args.entry_mode == "maker_limit"
            else ""
        )
        base = {
            **meta,
            "attempt_number": attempt_number,
            "direction": direction,
            "entry_mode": args.entry_mode,
            "fee_pct": args.fee_pct,
            "slippage_pct": args.slippage_pct,
            "limit_entry_offset_pct": args.limit_entry_offset_pct,
            "limit_entry_timeout_min": args.limit_entry_timeout_min,
            "signal_idx": index,
            "signal_time": signal_row["close_time"],
            "signal_close": signal_row["close"],
            "order_start_time": order_row["open_time"],
            "order_open": order_row["open"],
            "limit_price": limit_price,
            "long_score": signal_row.get("long_score", ""),
            "short_score": signal_row.get("short_score", ""),
            "atr_pct": signal_row.get("atr_pct", ""),
            "return_7d": signal_row.get("return_7d", ""),
            "dist_ema200": signal_row.get("dist_ema200", ""),
            "portfolio_weight": portfolio_weight,
            "portfolio_status": "candidate",
        }

        if entry_info is None:
            waited_row = candles[waited_until_idx]
            rows.append(
                {
                    **base,
                    "order_status": "unfilled",
                    "portfolio_status": "unfilled",
                    "fill_time": "",
                    "fill_delay_min": "",
                    "entry": "",
                    "tp_level": "",
                    "sl_level": "",
                    "exit_time": "",
                    "exit": "",
                    "reason": "unfilled_entry",
                    "duration_min": "",
                    "net_return_pct": "",
                    "portfolio_return_pct": "",
                    "pnl": "",
                    "equity_after": equity,
                    "waited_until_time": waited_row["close_time"],
                }
            )
            index = waited_until_idx + 1
            continue

        trade = bt.simulate_trade(candles, entry_info, direction, equity, args)
        tp_level, sl_level = tp_sl_levels(direction, trade["entry"], args)
        equity = trade["equity_after"]
        portfolio_return_pct = trade["net_return_pct"] * portfolio_weight
        rows.append(
                {
                    **base,
                    "order_status": "filled",
                    "portfolio_status": "accepted",
                    "fill_time": trade["entry_time"],
                "fill_delay_min": trade["fill_delay_min"],
                "entry": trade["entry"],
                "tp_level": tp_level,
                "sl_level": sl_level,
                "exit_time": trade["exit_time"],
                "exit": trade["exit"],
                "reason": trade["reason"],
                "duration_min": trade["duration_min"],
                "net_return_pct": trade["net_return_pct"],
                "portfolio_return_pct": portfolio_return_pct,
                "pnl": trade["pnl"],
                "equity_after": equity,
                "waited_until_time": "",
                "exit_idx": trade["exit_idx"],
            }
        )
        index = trade["exit_idx"] + 1

    return rows


def make_single_args(multi, reinvest, cf, spec, execution):
    args = cf.make_single_args(multi, reinvest, spec)
    return apply_execution(args, **execution)


def build_single_journal(bt, reinvest, multi, cf, symbol, asset, strategy_name, days, warmup_days, execution, market):
    candles = fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market)
    spec = spec_by_symbol(cf, symbol)
    rows = [dict(row) for row in candles]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = make_single_args(multi, reinvest, cf, spec, execution)
    meta = {
        "asset": asset,
        "symbol": symbol,
        "strategy": strategy_name,
        "module": strategy_name,
    }
    return journal_loop(bt, rows, args, meta)


def dydx_df_from_candles(candles):
    df = DYDX_TUNE.pd.DataFrame(
        candles,
        columns=["open_time_ms", "open", "high", "low", "close", "volume"],
    )
    df["open_time_ms"] = df["open_time_ms"].astype("int64")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = df[column].astype("float64")
    return df.sort_values("open_time_ms").drop_duplicates("open_time_ms").reset_index(drop=True)


def build_dydx_x2_journal(bt, reinvest, multi, days, warmup_days, execution, market):
    symbol = "DYDXUSDT"
    if market == "futures_archive":
        candles, _, _ = multi.fetch_klines_fast(symbol, days, max(warmup_days, 60))
    else:
        candles = bt.fetch_klines(market, symbol, days + max(warmup_days, 60), "1m")
    if not candles:
        raise RuntimeError(f"no candles for {symbol}")
    df = dydx_df_from_candles(candles)
    df = DYDX_TUNE.add_closed_htf(DYDX_TUNE.add_closed_htf(DYDX_TUNE.add_indicators(df), 60), 240)
    signal = DYDX_TUNE.signal_for(df, DYDX_PROTECTION.VARIANT)
    bars = days * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-bars:]]
    tail_signal = signal[-bars:]
    for row, is_signal in zip(rows, tail_signal):
        row["long_signal"] = False
        row["short_signal"] = bool(is_signal)
        row["long_score"] = 0
        row["short_score"] = 100 if is_signal else 0
    args = multi.make_strategy_args(reinvest, "7.3", symbol)
    apply_execution(args, **execution)
    args.direction = "short"
    args.position_pct = 1.30
    args.short_tp_pct = 0.008
    args.short_sl_pct = 0.030
    args.short_time_stop_min = 180
    args.time_stop_min = 180
    meta = {
        "asset": "DYDX",
        "symbol": symbol,
        "strategy": "DYDX Pullback SHORT x2 Protected",
        "module": "DYDX_X2",
    }
    return journal_loop(bt, rows, args, meta)


def build_rif_journal(bt, reinvest, multi, cf, rif, days, warmup_days, execution, market):
    symbol = "RIFUSDT"
    candles = fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market)
    spec = rif.spec_from_shortlist(STRICT_SHORTLIST_PATH, symbol)
    rows = [dict(row) for row in candles]
    cf.apply_single_signals(rows, spec["direction"], spec["threshold"], spec["regime"])
    args = make_single_args(multi, reinvest, cf, spec, execution)
    meta = {
        "asset": "RIF",
        "symbol": symbol,
        "strategy": "RIF Regime Monitor",
        "module": "RIF fixed setup",
    }
    return journal_loop(bt, rows, args, meta)


def build_gala_112_journal(bt, reinvest, multi, days, warmup_days, execution, market):
    symbol = "GALAUSDT"
    candles = fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market)
    all_rows = []

    short_rows = [dict(row) for row in candles]
    multi.apply_strategy_signals(short_rows, "7.3")
    short_args = multi.make_strategy_args(reinvest, "7.3", symbol)
    apply_execution(short_args, **execution)
    all_rows.extend(
        journal_loop(
            bt,
            short_rows,
            short_args,
            {
                "asset": "GALA",
                "symbol": symbol,
                "strategy": "Минутка 11.2",
                "module": "7.3 short x1.5",
            },
            portfolio_weight=1.5 * 0.9,
        )
    )

    long_rows = [dict(row) for row in candles]
    multi.apply_strategy_signals(long_rows, "10")
    long_args = multi.make_strategy_args(reinvest, "10", symbol)
    apply_execution(long_args, **execution)
    all_rows.extend(
        journal_loop(
            bt,
            long_rows,
            long_args,
            {
                "asset": "GALA",
                "symbol": symbol,
                "strategy": "Минутка 11.2",
                "module": "10 long",
            },
            portfolio_weight=0.9,
        )
    )

    open_until = None
    for row in sorted(
        all_rows,
        key=lambda item: (
            parse_time(item["order_start_time"]),
            parse_time(item["signal_time"]),
            item["module"],
        ),
    ):
        if row["order_status"] != "filled":
            row["portfolio_status"] = "unfilled"
            continue
        entry_time = parse_time(row["fill_time"])
        if open_until is not None and entry_time < open_until:
            row["portfolio_status"] = "skipped_overlap"
            continue
        row["portfolio_status"] = "accepted"
        open_until = parse_time(row["exit_time"])
    return all_rows


def build_gala_template_journal(bt, reinvest, multi, template, days, warmup_days, execution, market):
    symbol = "GALAUSDT"
    candles = fetch_candles(bt, reinvest, multi, symbol, days, warmup_days, market)
    rows = [dict(row) for row in candles]
    multi.apply_strategy_signals(rows, template)
    args = multi.make_strategy_args(reinvest, template, symbol)
    apply_execution(args, **execution)
    if template == "7.3":
        strategy = "Минутка 7.3"
        module = "7.3 short"
    else:
        strategy = "Минутка 10"
        module = "10 long"
    return journal_loop(
        bt,
        rows,
        args,
        {
            "asset": "GALA",
            "symbol": symbol,
            "strategy": strategy,
            "module": module,
        },
    )


def summarize_rows(rows, expected=None):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["asset"], row["strategy"])].append(row)
    expected = expected or []
    for asset, strategy in expected:
        grouped.setdefault((asset, strategy), [])

    output = []
    for (asset, strategy), items in sorted(grouped.items()):
        signals = len(items)
        filled = [row for row in items if row["order_status"] == "filled"]
        unfilled = [row for row in items if row["order_status"] == "unfilled"]
        accepted = [
            row
            for row in filled
            if row["portfolio_status"] in {"candidate", "accepted"}
        ]
        returns = [float(row["portfolio_return_pct"] or row["net_return_pct"] or 0.0) for row in accepted]
        wins = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        gross_wins = sum(wins)
        gross_losses = abs(sum(losses))
        output.append(
            {
                "asset": asset,
                "strategy": strategy,
                "signals": signals,
                "filled": len(filled),
                "unfilled": len(unfilled),
                "accepted": len(accepted),
                "skipped_overlap": sum(1 for row in items if row["portfolio_status"] == "skipped_overlap"),
                "fill_rate_pct": len(filled) / signals * 100.0 if signals else 0.0,
                "accepted_win_rate_pct": len(wins) / len(accepted) * 100.0 if accepted else 0.0,
                "accepted_return_sum_pct": sum(returns),
                "accepted_expectancy_pct": sum(returns) / len(accepted) if accepted else 0.0,
                "accepted_profit_factor": gross_wins / gross_losses if gross_losses else (math.inf if gross_wins else 0.0),
                "exit_reasons": ";".join(
                    f"{key}={value}"
                    for key, value in Counter(row["reason"] for row in accepted).most_common()
                ),
            }
        )
    return output


def expected_entries(modules):
    entries = []
    for module in modules:
        if module == "ANKR":
            entries.append(("ANKR", "ANKR LONG Best"))
        elif module == "GALA_73":
            entries.append(("GALA", "Минутка 7.3"))
        elif module == "GALA_10":
            entries.append(("GALA", "Минутка 10"))
        elif module == "RIF":
            entries.append(("RIF", "RIF Regime Monitor"))
        elif module == "GALA_112":
            entries.append(("GALA", "Минутка 11.2"))
        elif module == "SPELL":
            entries.append(("SPELL", "SPELL SHORT Best"))
        elif module == "DYDX_X2":
            entries.append(("DYDX", "DYDX Pullback SHORT x2 Protected"))
    return entries


def save_report(path, summary_rows, journal_path, summary_path, days, generated_at):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Paper Execution Journal",
        "",
        f"Generated: {generated_at}",
        f"Window: last {days} days",
        "",
        "| Asset | Strategy | Signals | Filled | Fill % | Accepted | Return Sum | PF | Expectancy | Exit Reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['asset']} | {row['strategy']} | {row['signals']} | {row['filled']} | "
            f"{row['fill_rate_pct']:.2f}% | {row['accepted']} | "
            f"{fmt_pct(row['accepted_return_sum_pct'])} | {fmt_num(row['accepted_profit_factor'])} | "
            f"{fmt_pct(row['accepted_expectancy_pct'])} | {row['exit_reasons']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Journal CSV: `{journal_path}`",
            f"- Summary CSV: `{summary_path}`",
            "",
            "## How To Use",
            "",
            "- `filled` показывает, сколько лимитных входов реально было бы исполнено по свечам.",
            "- `unfilled` значит, что цена не вернулась к нашей лимитке за заданный timeout.",
            "- Для GALA 11.2 `accepted` учитывает правило одной открытой позиции; остальные заполненные сделки могут быть `skipped_overlap`.",
            "- Это исторический paper-журнал. Для настоящего live-paper его надо запускать регулярно и сравнивать с реальными стаканами/ордерами.",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Build paper execution journal for selected strategies.")
    parser.add_argument("--modules", nargs="*", default=list(DEFAULT_MODULES), choices=list(AVAILABLE_MODULES))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--market", choices=["futures_archive", "futures_global", "data_api_spot"], default="futures_archive")
    parser.add_argument("--entry-mode", choices=["maker_limit", "next_open"], default="maker_limit")
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--save-journal", default=f"data/paper_execution_journal_{today}.csv")
    parser.add_argument("--save-summary", default=f"data/paper_execution_summary_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/paper-execution-journal-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    rif = load_module("rif_regime_monitor", RIF_PATH)
    global DYDX_TUNE, DYDX_PROTECTION
    DYDX_TUNE = load_module("dydx_pullback_short_tune", DYDX_TUNE_PATH)
    DYDX_PROTECTION = load_module("dydx_pullback_short_leverage_protection", DYDX_PROTECTION_PATH)

    execution = {
        "entry_mode": args.entry_mode,
        "fee_pct": args.fee_pct,
        "slippage_pct": args.slippage_pct,
        "limit_offset": args.limit_entry_offset_pct,
        "timeout_min": args.limit_entry_timeout_min,
    }

    journal = []
    for module in args.modules:
        print(f"building journal: {module}", flush=True)
        if module == "ANKR":
            journal.extend(
                build_single_journal(
                    bt,
                    reinvest,
                    multi,
                    cf,
                    "ANKRUSDT",
                    "ANKR",
                    "ANKR LONG Best",
                    args.days,
                    args.warmup_days,
                    execution,
                    args.market,
                )
            )
        elif module == "SPELL":
            journal.extend(
                build_single_journal(
                    bt,
                    reinvest,
                    multi,
                    cf,
                    "SPELLUSDT",
                    "SPELL",
                    "SPELL SHORT Best",
                    args.days,
                    args.warmup_days,
                    execution,
                    args.market,
                )
            )
        elif module == "RIF":
            journal.extend(build_rif_journal(bt, reinvest, multi, cf, rif, args.days, args.warmup_days, execution, args.market))
        elif module == "GALA_73":
            journal.extend(build_gala_template_journal(bt, reinvest, multi, "7.3", args.days, args.warmup_days, execution, args.market))
        elif module == "GALA_10":
            journal.extend(build_gala_template_journal(bt, reinvest, multi, "10", args.days, args.warmup_days, execution, args.market))
        elif module == "GALA_112":
            journal.extend(build_gala_112_journal(bt, reinvest, multi, args.days, args.warmup_days, execution, args.market))
        elif module == "DYDX_X2":
            journal.extend(build_dydx_x2_journal(bt, reinvest, multi, args.days, args.warmup_days, execution, args.market))

    journal.sort(key=lambda row: (row["symbol"], parse_time(row["order_start_time"]), row["module"]))
    summary = summarize_rows(journal, expected_entries(args.modules))

    journal_fields = [
        "asset",
        "symbol",
        "strategy",
        "module",
        "portfolio_status",
        "attempt_number",
        "direction",
        "entry_mode",
        "fee_pct",
        "slippage_pct",
        "limit_entry_offset_pct",
        "limit_entry_timeout_min",
        "signal_idx",
        "signal_time",
        "signal_close",
        "order_start_time",
        "order_open",
        "limit_price",
        "order_status",
        "fill_time",
        "fill_delay_min",
        "entry",
        "tp_level",
        "sl_level",
        "exit_time",
        "exit",
        "reason",
        "duration_min",
        "net_return_pct",
        "portfolio_return_pct",
        "pnl",
        "equity_after",
        "waited_until_time",
        "long_score",
        "short_score",
        "atr_pct",
        "return_7d",
        "dist_ema200",
        "portfolio_weight",
    ]
    summary_fields = [
        "asset",
        "strategy",
        "signals",
        "filled",
        "unfilled",
        "accepted",
        "skipped_overlap",
        "fill_rate_pct",
        "accepted_win_rate_pct",
        "accepted_return_sum_pct",
        "accepted_expectancy_pct",
        "accepted_profit_factor",
        "exit_reasons",
    ]
    save_csv(os.path.join(ROOT, args.save_journal), journal, journal_fields)
    save_csv(os.path.join(ROOT, args.save_summary), summary, summary_fields)
    save_report(args.save_report, summary, args.save_journal, args.save_summary, args.days, datetime.now(timezone.utc).isoformat())
    print(f"saved journal: {args.save_journal}")
    print(f"saved summary: {args.save_summary}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
