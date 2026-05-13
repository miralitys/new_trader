#!/usr/bin/env python3
"""Test GALA winners with higher-timeframe regime filters.

The entry remains on 1m. A higher timeframe only says whether the corresponding
direction is allowed. The higher-timeframe candle must be closed before the 1m
signal candle is allowed to use it.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0
BASELINE = "1m_only"
SYNTHETIC_INTERVALS_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "1h": 60,
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


def value_in_range(value, min_value=None, max_value=None):
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def clone_args(args):
    return argparse.Namespace(**vars(args))


def interval_minutes(interval):
    if interval not in SYNTHETIC_INTERVALS_MINUTES:
        raise ValueError(f"Unsupported MTF interval: {interval}")
    return SYNTHETIC_INTERVALS_MINUTES[interval]


def interval_ms(interval):
    return interval_minutes(interval) * 60_000


def resample_candles(bt, candles, interval):
    if interval == "1m":
        return [dict(row) for row in candles]

    group_ms = interval_ms(interval)
    needed = interval_minutes(interval)
    groups = []
    current = None

    for row in candles:
        bucket = (row["open_time_ms"] // group_ms) * group_ms
        if current is None or current["open_time_ms"] != bucket:
            if current is not None and current["_count"] == needed:
                current.pop("_count", None)
                groups.append(current)
            current = {
                "open_time_ms": bucket,
                "close_time_ms": bucket + group_ms - 1,
                "open_time": bt.utc_ms_to_iso(bucket),
                "close_time": bt.utc_ms_to_iso(bucket + group_ms - 1),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "_count": 1,
            }
            continue

        current["high"] = max(current["high"], row["high"])
        current["low"] = min(current["low"], row["low"])
        current["close"] = row["close"]
        current["volume"] += row["volume"]
        current["_count"] += 1

    if current is not None and current["_count"] == needed:
        current.pop("_count", None)
        groups.append(current)

    return groups


def higher_tf_bias(row, direction):
    atr_ok = value_in_range(row.get("atr_pct"), 0.0020, None)
    dist_ok = value_in_range(row.get("dist_ema200"), -0.030, 0.030)
    ret_ok = value_in_range(row.get("return_7d"), -0.50, 0.30)
    if not (atr_ok and dist_ok and ret_ok):
        return False

    ema20 = row.get("ema20")
    ema50 = row.get("ema50")
    ema200 = row.get("ema200")
    if ema20 is None or ema50 is None or ema200 is None:
        return False

    if direction == "short":
        return (
            row["close"] < ema200
            or ema20 < ema50
            or row.get("short_score", 0.0) >= 40
        )

    if direction == "long":
        if row["close"] > ema20 * 1.020:
            return False
        return (
            row["close"] > ema200
            or ema20 > ema50
            or row.get("long_score", 0.0) >= 50
        )

    raise ValueError(direction)


def build_htf_permissions(bt, candles, base_args, interval):
    htf = resample_candles(bt, candles, interval)
    htf_args = clone_args(base_args)
    htf_args.interval = interval
    bt.add_indicators_and_signals(htf, htf_args)

    output = []
    for row in htf:
        output.append(
            {
                "close_time_ms": row["close_time_ms"],
                "long_allowed": higher_tf_bias(row, "long"),
                "short_allowed": higher_tf_bias(row, "short"),
            }
        )
    return output


def apply_htf_filter(rows, permissions):
    perm_idx = 0
    latest = None
    total = 0
    long_blocked = 0
    short_blocked = 0

    for row in rows:
        while perm_idx < len(permissions) and permissions[perm_idx]["close_time_ms"] <= row["close_time_ms"]:
            latest = permissions[perm_idx]
            perm_idx += 1

        if row.get("long_signal"):
            total += 1
            if latest is None or not latest["long_allowed"]:
                row["long_signal"] = False
                long_blocked += 1
        if row.get("short_signal"):
            total += 1
            if latest is None or not latest["short_allowed"]:
                row["short_signal"] = False
                short_blocked += 1

    return {
        "mtf_candidate_signals": total,
        "mtf_long_blocked": long_blocked,
        "mtf_short_blocked": short_blocked,
        "mtf_blocked_total": long_blocked + short_blocked,
    }


def base_strategy_signals(multi, rows, strategy):
    multi.apply_strategy_signals(rows, strategy)


def run_single(bt, reinvest, multi, candles, strategy, days, interval, permissions):
    needed = days * bt.candles_per_day("1m")
    rows = [dict(row) for row in candles[-needed:]]
    base_strategy_signals(multi, rows, strategy)
    mtf_stats = Counter()
    if permissions is not None:
        mtf_stats.update(apply_htf_filter(rows, permissions))

    args = multi.make_strategy_args(reinvest, strategy, "GALAUSDT")
    trades, equity, stats = bt.run_backtest(rows, args)
    summary = bt.summarize_trades(trades, INITIAL_BALANCE, equity)
    stats.update(mtf_stats)
    return trades, equity, summary, stats


def build_112_portfolio(multi, short_trades, long_trades):
    return multi.build_112_portfolio(short_trades, long_trades)


def summary_row(strategy, interval, days, summary, stats, data_start, data_end, candles_count):
    reasons = summary.get("exit_reasons", Counter())
    return {
        "strategy": strategy,
        "htf": interval,
        "period": f"{days}d",
        "days": days,
        "candles": candles_count,
        "data_start": data_start,
        "data_end": data_end,
        "trades": summary["total_trades"],
        "return_pct": summary["total_return_pct"],
        "win_rate_pct": summary["win_rate_pct"],
        "profit_factor": summary["profit_factor"],
        "max_dd_pct": summary["max_drawdown_pct"],
        "avg_win_pct": summary.get("avg_win_pct", 0.0),
        "avg_loss_pct": summary.get("avg_loss_pct", 0.0),
        "expectancy_pct": summary.get("expectancy_pct", 0.0),
        "final_equity": summary["final_equity"],
        "take_profit": reasons["take_profit"],
        "stop_loss": reasons["stop_loss"],
        "time_stop": reasons["time_stop"],
        "end_of_data": reasons["end_of_data"],
        "mtf_candidate_signals": stats.get("mtf_candidate_signals", 0),
        "mtf_blocked_total": stats.get("mtf_blocked_total", 0),
        "mtf_long_blocked": stats.get("mtf_long_blocked", 0),
        "mtf_short_blocked": stats.get("mtf_short_blocked", 0),
    }


def fmt_pct(value):
    return f"{value:+.2f}%"


def fmt_pf(value):
    return "inf" if value == math.inf else f"{value:.2f}"


def save_markdown(path, rows, intervals, periods):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    by_key = {(row["strategy"], row["htf"], row["days"]): row for row in rows}
    lines = [
        "# GALA MTF Regime Test",
        "",
        "Статус: исследовательский тест, не новая зафиксированная стратегия.",
        "",
        "Старший таймфрейм используется только как фильтр режима. Вход остается на `1m`.",
        "Сигнал старшего таймфрейма берется только после закрытия его свечи.",
        "",
        "Проверенные старшие таймфреймы: `5m`, `15m`, `30m`, `1h`.",
        "База сравнения: `1m_only` без старшего фильтра.",
        "",
        "## Методология",
        "",
        "- `Минутка 7.3`: базовый SHORT-сигнал 1m + разрешение SHORT на старшем ТФ.",
        "- `Минутка 10`: базовый LONG-сигнал 1m + разрешение LONG на старшем ТФ.",
        "- `Минутка 11.2`: отдельно фильтруются LONG 10 и SHORT 7.3, потом применяется правило `max open = 1`.",
        "- TP/SL/комиссии/размеры позиций не оптимизировались.",
        "",
    ]

    for strategy in ("7.3", "10", "11.2"):
        lines.extend(
            [
                f"## {strategy} — 365d / 730d",
                "",
                "| HTF | 365d Return | 365d DD | 365d PF | 365d Trades | 730d Return | 730d DD | 730d PF | 730d Trades |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for interval in [BASELINE] + intervals:
            row365 = by_key.get((strategy, interval, 365))
            row730 = by_key.get((strategy, interval, 730))
            if not row365 or not row730:
                continue
            lines.append(
                f"| {interval} | {fmt_pct(row365['return_pct'])} | {row365['max_dd_pct']:.2f}% | "
                f"{fmt_pf(row365['profit_factor'])} | {row365['trades']} | "
                f"{fmt_pct(row730['return_pct'])} | {row730['max_dd_pct']:.2f}% | "
                f"{fmt_pf(row730['profit_factor'])} | {row730['trades']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Все окна",
            "",
            "| Strategy | HTF | 7d | 30d | 60d | 90d | 180d | 365d | 730d | Worst DD |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for strategy in ("7.3", "10", "11.2"):
        for interval in [BASELINE] + intervals:
            values = []
            dds = []
            for period in periods:
                row = by_key.get((strategy, interval, period))
                if row:
                    values.append(fmt_pct(row["return_pct"]))
                    dds.append(row["max_dd_pct"])
                else:
                    values.append("-")
            worst_dd = max(dds) if dds else 0.0
            lines.append(
                f"| {strategy} | {interval} | "
                + " | ".join(values)
                + f" | {worst_dd:.2f}% |"
            )

    lines.extend(
        [
            "",
            "## Предварительный вывод",
            "",
            "Этот файл отвечает на вопрос, улучшает ли старший таймфрейм уже найденные GALA-модули.",
            "Фиксировать новую стратегию можно только если MTF-версия лучше базы на `365d` и `730d` одновременно: выше PF, ниже MaxDD и без провала доходности.",
        ]
    )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="GALA higher-timeframe regime test.")
    parser.add_argument("--symbol", default="GALAUSDT")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--htfs", nargs="*", default=["3m", "5m", "10m", "15m", "30m", "1h"])
    parser.add_argument("--periods", nargs="*", type=int, default=[7, 30, 60, 90, 180, 365, 730])
    parser.add_argument("--save-summary", default="data/gala_mtf_regime_summary.csv")
    parser.add_argument("--save-report", default="strategies/GALA/gala-mtf-regime-test.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    print(
        f"fetching {args.symbol} days={args.days} warmup={args.warmup_days}",
        flush=True,
    )
    candles, _, _ = multi.fetch_klines_fast(args.symbol, args.days, args.warmup_days)
    base_args = multi.make_strategy_args(reinvest, "7.3", args.symbol)
    bt.add_indicators_and_signals(candles, base_args)
    test_bars = args.days * bt.candles_per_day("1m")
    test_candles = candles[-test_bars:]
    print(
        f"candles={len(test_candles)} start={test_candles[0]['open_time']} "
        f"end={test_candles[-1]['close_time']}",
        flush=True,
    )

    permissions = {}
    for interval in args.htfs:
        print(f"building htf permissions {interval}", flush=True)
        permissions[interval] = build_htf_permissions(bt, candles, base_args, interval)

    rows = []
    data_start = test_candles[0]["open_time"]
    data_end = test_candles[-1]["close_time"]
    all_intervals = [BASELINE] + args.htfs

    for interval in all_intervals:
        active_permissions = None if interval == BASELINE else permissions[interval]
        for period in args.periods:
            if period > args.days:
                continue
            print(f"run {interval} {period}d", flush=True)
            short_trades, _, short_summary, short_stats = run_single(
                bt, reinvest, multi, test_candles, "7.3", period, interval, active_permissions
            )
            rows.append(
                summary_row("7.3", interval, period, short_summary, short_stats, data_start, data_end, len(test_candles))
            )

            long_trades, _, long_summary, long_stats = run_single(
                bt, reinvest, multi, test_candles, "10", period, interval, active_permissions
            )
            rows.append(
                summary_row("10", interval, period, long_summary, long_stats, data_start, data_end, len(test_candles))
            )

            portfolio_trades, portfolio_equity, portfolio_summary = build_112_portfolio(
                multi, short_trades, long_trades
            )
            portfolio_stats = Counter()
            portfolio_stats.update(short_stats)
            portfolio_stats.update(long_stats)
            rows.append(
                summary_row("11.2", interval, period, portfolio_summary, portfolio_stats, data_start, data_end, len(test_candles))
            )

    fields = [
        "strategy",
        "htf",
        "period",
        "days",
        "candles",
        "data_start",
        "data_end",
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
        "end_of_data",
        "mtf_candidate_signals",
        "mtf_blocked_total",
        "mtf_long_blocked",
        "mtf_short_blocked",
    ]
    summary_path = os.path.join(ROOT, args.save_summary)
    report_path = os.path.join(ROOT, args.save_report)
    save_csv(summary_path, rows, fields)
    save_markdown(report_path, rows, args.htfs, args.periods)
    print(f"saved summary: {summary_path}")
    print(f"saved report: {report_path}")


if __name__ == "__main__":
    main()
