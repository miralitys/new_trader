#!/usr/bin/env python3
"""Find explosive coin months and test whether our 1m family could catch them.

The goal is not to pick a permanent coin. The goal is to identify regime
changes: months where a coin suddenly became active, and whether the current
score-based LONG/SHORT family had a profitable route inside that regime.
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
SCREEN_PATH = os.path.join(ROOT, "scripts", "screen_new_binance_candidates.py")

INITIAL_BALANCE = 1000.0
MIN_MONTH_DAYS = 20


DEFAULT_SYMBOLS = [
    # Original / accepted / rejected universe.
    "GALAUSDT",
    "DOGEUSDT",
    "1000SHIBUSDT",
    "1000PEPEUSDT",
    "1000FLOKIUSDT",
    "1000BONKUSDT",
    "JASMYUSDT",
    "CHZUSDT",
    "ALPINEUSDT",
    "SANDUSDT",
    "MANAUSDT",
    "APEUSDT",
    "ENJUSDT",
    "IOTXUSDT",
    "ANKRUSDT",
    "AMPUSDT",
    "SPELLUSDT",
    "LRCUSDT",
    "COTIUSDT",
    "ZILUSDT",
    "ONEUSDT",
    "AXLUSDT",
    # New user-requested batch.
    "NFPUSDT",
    "RDNTUSDT",
    "TRUUSDT",
    "HIFIUSDT",
    "OXTUSDT",
    "HOOKUSDT",
    "MDTUSDT",
    "IDEXUSDT",
    "NTRNUSDT",
    "LEVERUSDT",
    "AMBUSDT",
    "COMBOUSDT",
    "DENTUSDT",
    "SXPUSDT",
    "MAVUSDT",
    "USTCUSDT",
    "LITUSDT",
    "MOVRUSDT",
    "BAKEUSDT",
    "CHRUSDT",
    # Extra Binance queue / wishlist symbols already touched in this project.
    "1000LUNCUSDT",
    "XVGUSDT",
    "REZUSDT",
    "BBUSDT",
    "AIUSDT",
    "ZENUSDT",
    "KNCUSDT",
    "ORDIUSDT",
    "RLCUSDT",
    "BATUSDT",
    "API3USDT",
    # Extra symbols from the 2026-05-04 screenshot watch queue.
    "DYDXUSDT",
    "INJUSDT",
    "ICPUSDT",
    "AXSUSDT",
    "TRBUSDT",
    "ONDOUSDT",
    "IOTAUSDT",
    "NOTUSDT",
    "FILUSDT",
    "NEOUSDT",
    "HYPEUSDT",
    "STRKUSDT",
    "SLPUSDT",
    "MINAUSDT",
    "RVNUSDT",
    "RUNEUSDT",
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


def coin_from_symbol(symbol):
    for prefix in ("1000000", "1000"):
        if symbol.startswith(prefix):
            return symbol[len(prefix) :].replace("USDT", "")
    return symbol.replace("USDT", "")


def split_by_month(candles):
    months = defaultdict(list)
    for row in candles:
        months[row["open_time"][:7]].append(row)
    return dict(sorted(months.items()))


def month_stats(month, rows, prev_rows):
    open_price = rows[0]["open"]
    close_price = rows[-1]["close"]
    high = max(row["high"] for row in rows)
    low = min(row["low"] for row in rows)
    volume = sum(row["volume"] for row in rows)
    prev_volume = sum(row["volume"] for row in prev_rows) if prev_rows else 0.0
    prev_days = max(1.0, len(prev_rows) / 1440.0) if prev_rows else 0.0
    days = max(1.0, len(rows) / 1440.0)
    volume_ratio = (
        (volume / days) / (prev_volume / prev_days)
        if prev_volume > 0 and prev_days > 0
        else 0.0
    )
    price_return_pct = (close_price / open_price - 1.0) * 100.0 if open_price else 0.0
    range_pct = (high / low - 1.0) * 100.0 if low else 0.0
    explosion_score = max(
        abs(price_return_pct) / 35.0,
        range_pct / 75.0,
        volume_ratio / 2.5 if volume_ratio else 0.0,
    )
    is_explosion = (
        abs(price_return_pct) >= 35.0
        or range_pct >= 75.0
        or volume_ratio >= 2.5
    )
    return {
        "month": month,
        "days": days,
        "open": open_price,
        "close": close_price,
        "high": high,
        "low": low,
        "price_return_pct": price_return_pct,
        "range_pct": range_pct,
        "volume": volume,
        "volume_ratio_prev": volume_ratio,
        "explosion_score": explosion_score,
        "is_explosion": is_explosion,
    }


def find_explosion_months(candles):
    months = split_by_month(candles)
    rows = []
    previous_complete_rows = []
    for month, month_rows in months.items():
        days = len(month_rows) / 1440.0
        if days < MIN_MONTH_DAYS:
            continue
        stats = month_stats(month, month_rows, previous_complete_rows[-90 * 1440 :])
        rows.append(stats)
        previous_complete_rows.extend(month_rows)
    return rows


def make_args(multi, reinvest, cf, variant):
    spec = {
        "coin": coin_from_symbol(variant["symbol"]),
        "symbol": variant["symbol"],
        "kind": "single",
        **variant,
    }
    return cf.make_single_args(multi, reinvest, spec)


def run_variant_on_rows(bt, reinvest, multi, cf, rows, variant, fee_pct, slippage_pct, entry_mode, limit_offset):
    candles = [dict(row) for row in rows]
    cf.apply_single_signals(
        candles,
        variant["direction"],
        variant["threshold"],
        variant["regime"],
    )
    args = make_args(multi, reinvest, cf, variant)
    args.fee_pct = fee_pct
    args.slippage_pct = slippage_pct
    args.entry_mode = entry_mode
    args.limit_entry_offset_pct = limit_offset
    args.limit_entry_timeout_min = 1
    trades, equity, _ = bt.run_backtest(candles, args)
    return trades, bt.summarize_trades(trades, INITIAL_BALANCE, equity)


def best_month_strategy(bt, reinvest, multi, cf, rows, variants):
    best = None
    for variant in variants:
        trades, summary = run_variant_on_rows(
            bt,
            reinvest,
            multi,
            cf,
            rows,
            variant,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_offset=0.0,
        )
        candidate = {
            **variant,
            "trades": summary["total_trades"],
            "return_pct": summary["total_return_pct"],
            "win_rate_pct": summary["win_rate_pct"],
            "profit_factor": summary["profit_factor"],
            "max_dd_pct": summary["max_drawdown_pct"],
            "expectancy_pct": summary["expectancy_pct"],
        }
        if best is None or (
            candidate["return_pct"],
            candidate["profit_factor"],
            -candidate["max_dd_pct"],
        ) > (
            best["return_pct"],
            best["profit_factor"],
            -best["max_dd_pct"],
        ):
            best = candidate

    _, strict = run_variant_on_rows(
        bt,
        reinvest,
        multi,
        cf,
        rows,
        best,
        fee_pct=0.0002,
        slippage_pct=0.0,
        entry_mode="maker_limit",
        limit_offset=0.0005,
    )
    _, taker = run_variant_on_rows(
        bt,
        reinvest,
        multi,
        cf,
        rows,
        best,
        fee_pct=0.0004,
        slippage_pct=0.0002,
        entry_mode="next_open",
        limit_offset=0.0,
    )
    best["strict_return_pct"] = strict["total_return_pct"]
    best["strict_profit_factor"] = strict["profit_factor"]
    best["strict_trades"] = strict["total_trades"]
    best["taker_return_pct"] = taker["total_return_pct"]
    best["taker_profit_factor"] = taker["profit_factor"]
    best["taker_trades"] = taker["total_trades"]
    return best


def catch_status(row):
    ret = row["strategy_return_pct"]
    strict_ret = row["strict_return_pct"]
    strict_pf = row["strict_profit_factor"]
    if ret >= 25.0 and strict_ret > 0 and strict_pf >= 1.0:
        return "caught_realistic"
    if ret >= 25.0:
        return "paper_only"
    if ret > 0:
        return "weak_catch"
    return "not_caught"


def fmt_pct(value):
    return f"{float(value):+.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if value == math.inf else f"{value:.2f}"


def save_report(path, month_rows, catch_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    top_explosions = sorted(
        [row for row in month_rows if row["is_explosion"]],
        key=lambda row: row["explosion_score"],
        reverse=True,
    )
    top_catches = sorted(
        catch_rows,
        key=lambda row: row["strategy_return_pct"],
        reverse=True,
    )
    by_status = defaultdict(int)
    for row in catch_rows:
        by_status[row["catch_status"]] += 1

    lines = [
        "# Explosion Wave Scan",
        "",
        "Идея: найти месяцы, когда монета резко оживала, и проверить, могла ли наша семья 1m LONG/SHORT стратегий поймать этот режим.",
        "",
        "Взрывной месяц считается так: `abs(price return) >= 35%` или `месячный range >= 75%` или `объем/день >= 2.5x` к предыдущим ~90 дням.",
        "",
        "Важно: `paper_only` значит, что базовый maker-тест поймал волну, но strict maker-fill уже не подтвердил реалистичность.",
        "",
        "## Status Breakdown",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status in ("caught_realistic", "paper_only", "weak_catch", "not_caught"):
        lines.append(f"| {status} | {by_status[status]} |")

    lines.extend(
        [
            "",
            "## Top Strategy Catches",
            "",
            "| Symbol | Month | Market move | Range | Volume x | Best setup | Base return | Strict return | Taker-like | Status |",
            "|---|---|---:|---:|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in top_catches[:40]:
        setup = (
            f"{row['direction']} th{row['threshold']} {row['regime']} "
            f"TP {float(row['tp_pct']) * 100:.2f}% T{row['time_stop_min']}"
        )
        lines.append(
            f"| {row['symbol']} | {row['month']} | {fmt_pct(row['price_return_pct'])} | "
            f"{float(row['range_pct']):.2f}% | {float(row['volume_ratio_prev']):.2f}x | "
            f"{setup} | {fmt_pct(row['strategy_return_pct'])} | "
            f"{fmt_pct(row['strict_return_pct'])} | {fmt_pct(row['taker_return_pct'])} | "
            f"{row['catch_status']} |"
        )

    lines.extend(
        [
            "",
            "## Top Market Explosions",
            "",
            "| Symbol | Month | Market move | Range | Volume x | Score | Caught? |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    catch_lookup = {(row["symbol"], row["month"]): row for row in catch_rows}
    for row in top_explosions[:60]:
        caught = catch_lookup.get((row["symbol"], row["month"]), {})
        lines.append(
            f"| {row['symbol']} | {row['month']} | {fmt_pct(row['price_return_pct'])} | "
            f"{float(row['range_pct']):.2f}% | {float(row['volume_ratio_prev']):.2f}x | "
            f"{float(row['explosion_score']):.2f} | {caught.get('catch_status', 'not_tested')} |"
        )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Scan explosive months and strategy catches.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--warmup-days", type=int, default=7)
    parser.add_argument("--save-months", default="data/explosion_wave_months.csv")
    parser.add_argument("--save-catches", default="data/explosion_wave_catches.csv")
    parser.add_argument("--save-report", default="strategies/explosion-wave-scan.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    screen = load_module("screen_new_binance_candidates", SCREEN_PATH)

    variants = []
    for variant in screen.candidate_variants():
        variants.append(dict(variant))
    for extra_tp in (0.0035,):
        for threshold in (40, 50, 60):
            for regime in ("base", "wide"):
                variants.append(
                    {
                        "direction": "short",
                        "threshold": threshold,
                        "regime": regime,
                        "position_pct": 1.0,
                        "tp_pct": extra_tp,
                        "sl_pct": 0.04,
                        "time_stop_min": 60,
                    }
                )

    month_output = []
    catch_output = []
    diagnostics = []
    for index, symbol in enumerate(dict.fromkeys(args.symbols), start=1):
        print(f"[{index}/{len(args.symbols)}] {symbol}", flush=True)
        try:
            candles, _, _ = multi.fetch_klines_fast(symbol, args.days, args.warmup_days)
            base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
            bt.add_indicators_and_signals(candles, base_args)
            test_candles = candles[-args.days * bt.candles_per_day("1m") :]
            monthly = find_explosion_months(test_candles)
            by_month = split_by_month(test_candles)
            for row in monthly:
                row = {"symbol": symbol, "coin": coin_from_symbol(symbol), **row}
                month_output.append(row)

            explosions = [row for row in monthly if row["is_explosion"]]
            print(f"  explosion months={len(explosions)}", flush=True)
            for row in explosions:
                month_rows = by_month[row["month"]]
                symbol_variants = [{**variant, "symbol": symbol} for variant in variants]
                best = best_month_strategy(bt, reinvest, multi, cf, month_rows, symbol_variants)
                output = {
                    "symbol": symbol,
                    "coin": coin_from_symbol(symbol),
                    **row,
                    "direction": best["direction"],
                    "threshold": best["threshold"],
                    "regime": best["regime"],
                    "tp_pct": best["tp_pct"],
                    "sl_pct": best["sl_pct"],
                    "time_stop_min": best["time_stop_min"],
                    "strategy_trades": best["trades"],
                    "strategy_return_pct": best["return_pct"],
                    "strategy_win_rate_pct": best["win_rate_pct"],
                    "strategy_profit_factor": best["profit_factor"],
                    "strategy_max_dd_pct": best["max_dd_pct"],
                    "strategy_expectancy_pct": best["expectancy_pct"],
                    "strict_return_pct": best["strict_return_pct"],
                    "strict_profit_factor": best["strict_profit_factor"],
                    "strict_trades": best["strict_trades"],
                    "taker_return_pct": best["taker_return_pct"],
                    "taker_profit_factor": best["taker_profit_factor"],
                    "taker_trades": best["taker_trades"],
                }
                output["catch_status"] = catch_status(output)
                catch_output.append(output)
                print(
                    f"    {row['month']} market={row['price_return_pct']:+.1f}% "
                    f"range={row['range_pct']:.1f}% volx={row['volume_ratio_prev']:.1f} "
                    f"best={output['strategy_return_pct']:+.1f}% {output['catch_status']}",
                    flush=True,
                )
            diagnostics.append({"symbol": symbol, "status": "ok", "error": ""})
        except Exception as exc:
            diagnostics.append({"symbol": symbol, "status": "error", "error": str(exc)})
            print(f"  error: {exc}", flush=True)

    month_fields = [
        "symbol",
        "coin",
        "month",
        "days",
        "open",
        "close",
        "high",
        "low",
        "price_return_pct",
        "range_pct",
        "volume",
        "volume_ratio_prev",
        "explosion_score",
        "is_explosion",
    ]
    catch_fields = [
        "symbol",
        "coin",
        "month",
        "days",
        "price_return_pct",
        "range_pct",
        "volume_ratio_prev",
        "explosion_score",
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "strategy_trades",
        "strategy_return_pct",
        "strategy_win_rate_pct",
        "strategy_profit_factor",
        "strategy_max_dd_pct",
        "strategy_expectancy_pct",
        "strict_return_pct",
        "strict_profit_factor",
        "strict_trades",
        "taker_return_pct",
        "taker_profit_factor",
        "taker_trades",
        "catch_status",
    ]
    save_csv(os.path.join(ROOT, args.save_months), month_output, month_fields)
    save_csv(os.path.join(ROOT, args.save_catches), catch_output, catch_fields)
    save_csv(
        os.path.join(ROOT, "data", "explosion_wave_diagnostics.csv"),
        diagnostics,
        ["symbol", "status", "error"],
    )
    save_report(os.path.join(ROOT, args.save_report), month_output, catch_output)
    print(f"saved months: {os.path.join(ROOT, args.save_months)}")
    print(f"saved catches: {os.path.join(ROOT, args.save_catches)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
