#!/usr/bin/env python3
"""Current hot-coin scanner for the 1m wave strategy family.

This scanner is different from the historical explosion report:

1. It looks for coins that are hot right now.
2. It checks whether the current 1m LONG/SHORT family is already making money.
3. It ranks candidates by realistic execution first, not by paper return.

The default universe is the project universe we already researched. Use
`--universe binance` to scan all current Binance Futures USDT perpetuals.
"""

import argparse
import csv
import importlib.util
import json
import math
import os
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
SCREEN_PATH = os.path.join(ROOT, "scripts", "screen_new_binance_candidates.py")
EXPLOSION_PATH = os.path.join(ROOT, "scripts", "explosion_wave_scan.py")

INITIAL_BALANCE = 1000.0
BINANCE_FUTURES_EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"


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


def load_binance_usdt_perps():
    request = urllib.request.Request(
        BINANCE_FUTURES_EXCHANGE_INFO,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    symbols = []
    for item in payload.get("symbols", []):
        if (
            item.get("contractType") == "PERPETUAL"
            and item.get("quoteAsset") == "USDT"
            and item.get("status") == "TRADING"
        ):
            symbols.append(item["symbol"])
    return sorted(symbols)


def unique(items):
    return list(dict.fromkeys(items))


def coin_from_symbol(symbol):
    for prefix in ("1000000", "1000"):
        if symbol.startswith(prefix):
            return symbol[len(prefix) :].replace("USDT", "")
    return symbol.replace("USDT", "")


def window_rows(candles, days):
    bars = days * 1440
    return candles[-bars:] if len(candles) >= bars else []


def range_pct(rows):
    if not rows:
        return 0.0
    high = max(row["high"] for row in rows)
    low = min(row["low"] for row in rows)
    return (high / low - 1.0) * 100.0 if low else 0.0


def return_pct(rows):
    if not rows:
        return 0.0
    start = rows[0]["open"]
    end = rows[-1]["close"]
    return (end / start - 1.0) * 100.0 if start else 0.0


def quote_volume(rows):
    return sum(row["volume"] * row["close"] for row in rows)


def avg_daily_quote_volume(rows):
    if not rows:
        return 0.0
    days = max(len(rows) / 1440.0, 1.0)
    return quote_volume(rows) / days


def previous_rows(candles, recent_days, baseline_days):
    recent_bars = recent_days * 1440
    baseline_bars = baseline_days * 1440
    if len(candles) <= recent_bars:
        return []
    start = max(0, len(candles) - recent_bars - baseline_bars)
    end = len(candles) - recent_bars
    return candles[start:end]


def safe_ratio(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def market_metrics(symbol, candles, baseline_days):
    rows1 = window_rows(candles, 1)
    rows3 = window_rows(candles, 3)
    rows7 = window_rows(candles, 7)
    rows14 = window_rows(candles, 14)
    rows30 = window_rows(candles, 30)
    prev7 = previous_rows(candles, 7, baseline_days)
    prev14 = previous_rows(candles, 14, baseline_days)

    vol7 = avg_daily_quote_volume(rows7)
    prev_vol7 = avg_daily_quote_volume(prev7)
    vol14 = avg_daily_quote_volume(rows14)
    prev_vol14 = avg_daily_quote_volume(prev14)

    ret3 = return_pct(rows3)
    ret7 = return_pct(rows7)
    ret14 = return_pct(rows14)
    rng3 = range_pct(rows3)
    rng7 = range_pct(rows7)
    rng14 = range_pct(rows14)
    vol_ratio7 = safe_ratio(vol7, prev_vol7)
    vol_ratio14 = safe_ratio(vol14, prev_vol14)

    # Score is intentionally rough. It finds attention-worthy regimes; strategy
    # validation below decides whether we should trade.
    move_points = min(35.0, max(abs(ret3) / 15.0, abs(ret7) / 25.0, abs(ret14) / 35.0) * 20.0)
    range_points = min(35.0, max(rng3 / 30.0, rng7 / 50.0, rng14 / 75.0) * 20.0)
    volume_points = min(30.0, max(vol_ratio7, vol_ratio14) / 2.5 * 30.0)
    hot_score = move_points + range_points + volume_points

    hot_reasons = []
    if abs(ret3) >= 12.0:
        hot_reasons.append("3d move")
    if abs(ret7) >= 20.0:
        hot_reasons.append("7d move")
    if rng3 >= 25.0:
        hot_reasons.append("3d range")
    if rng7 >= 45.0:
        hot_reasons.append("7d range")
    if vol_ratio7 >= 2.0 or vol_ratio14 >= 2.0:
        hot_reasons.append("volume spike")

    return {
        "symbol": symbol,
        "coin": coin_from_symbol(symbol),
        "data_start": candles[0]["open_time"] if candles else "",
        "data_end": candles[-1]["close_time"] if candles else "",
        "return_1d_pct": return_pct(rows1),
        "return_3d_pct": ret3,
        "return_7d_pct": ret7,
        "return_14d_pct": ret14,
        "return_30d_pct": return_pct(rows30),
        "range_3d_pct": rng3,
        "range_7d_pct": rng7,
        "range_14d_pct": rng14,
        "quote_volume_7d_avg": vol7,
        "quote_volume_14d_avg": vol14,
        "volume_ratio_7d": vol_ratio7,
        "volume_ratio_14d": vol_ratio14,
        "hot_score": hot_score,
        "hot_reasons": ";".join(hot_reasons),
        "is_hot": bool(hot_reasons),
    }


def make_strategy_variants(screen):
    variants = [dict(row) for row in screen.candidate_variants()]
    # Add the DENT/CHR-style micro TP family. It is dangerous, but useful for
    # detecting paper-only traps and strict-fill failures.
    for threshold in (40, 50, 60):
        for regime in ("base", "wide"):
            for direction in ("short", "long"):
                variants.append(
                    {
                        "direction": direction,
                        "threshold": threshold if direction == "short" else max(50, threshold),
                        "regime": regime,
                        "position_pct": 1.0,
                        "tp_pct": 0.0035,
                        "sl_pct": 0.04,
                        "time_stop_min": 60 if direction == "short" else 90,
                    }
                )
    deduped = []
    seen = set()
    for item in variants:
        key = (
            item["direction"],
            item["threshold"],
            item["regime"],
            item["tp_pct"],
            item["sl_pct"],
            item["time_stop_min"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def make_args(multi, reinvest, cf, variant):
    spec = {
        "coin": coin_from_symbol(variant["symbol"]),
        "symbol": variant["symbol"],
        "kind": "single",
        **variant,
    }
    return cf.make_single_args(multi, reinvest, spec)


def run_variant(bt, reinvest, multi, cf, candles, variant, fee_pct, slippage_pct, entry_mode, limit_offset):
    rows = [dict(row) for row in candles]
    cf.apply_single_signals(rows, variant["direction"], variant["threshold"], variant["regime"])
    args = make_args(multi, reinvest, cf, variant)
    args.fee_pct = fee_pct
    args.slippage_pct = slippage_pct
    args.entry_mode = entry_mode
    args.limit_entry_offset_pct = limit_offset
    args.limit_entry_timeout_min = 1
    trades, equity, _ = bt.run_backtest(rows, args)
    return bt.summarize_trades(trades, INITIAL_BALANCE, equity)


def best_recent_strategy(bt, reinvest, multi, cf, candles, symbol, variants, select_days):
    select_rows = window_rows(candles, select_days)
    best = None
    symbol_variants = [{**variant, "symbol": symbol} for variant in variants]
    for variant in symbol_variants:
        base = run_variant(
            bt,
            reinvest,
            multi,
            cf,
            select_rows,
            variant,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_offset=0.0,
        )
        strict = run_variant(
            bt,
            reinvest,
            multi,
            cf,
            select_rows,
            variant,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_offset=0.0005,
        )
        row = {
            **variant,
            "select_days": select_days,
            "base_return_pct": base["total_return_pct"],
            "base_trades": base["total_trades"],
            "base_profit_factor": base["profit_factor"],
            "base_max_dd_pct": base["max_drawdown_pct"],
            "strict_return_pct": strict["total_return_pct"],
            "strict_trades": strict["total_trades"],
            "strict_profit_factor": strict["profit_factor"],
            "strict_max_dd_pct": strict["max_drawdown_pct"],
        }
        if best is None or (
            row["strict_return_pct"],
            row["strict_profit_factor"],
            row["base_return_pct"],
            -row["strict_max_dd_pct"],
        ) > (
            best["strict_return_pct"],
            best["strict_profit_factor"],
            best["base_return_pct"],
            -best["strict_max_dd_pct"],
        ):
            best = row
    return best


def validate_variant_windows(bt, reinvest, multi, cf, candles, variant, windows):
    output = {}
    for days in windows:
        rows = window_rows(candles, days)
        if not rows:
            continue
        base = run_variant(
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
        strict = run_variant(
            bt,
            reinvest,
            multi,
            cf,
            rows,
            variant,
            fee_pct=0.0002,
            slippage_pct=0.0,
            entry_mode="maker_limit",
            limit_offset=0.0005,
        )
        taker = run_variant(
            bt,
            reinvest,
            multi,
            cf,
            rows,
            variant,
            fee_pct=0.0004,
            slippage_pct=0.0002,
            entry_mode="next_open",
            limit_offset=0.0,
        )
        output[days] = {
            "base": base,
            "strict": strict,
            "taker": taker,
        }
    return output


def decision(row):
    if not row.get("is_hot"):
        return "cold"
    if row["strict_return_7d_pct"] >= 5.0 and row["strict_pf_7d"] >= 1.10 and row["strict_trades_7d"] >= 8:
        if row["strict_return_14d_pct"] > 0 and row["strict_return_30d_pct"] > -5.0:
            return "ready"
        return "hot_watch"
    if row["base_return_7d_pct"] >= 5.0 and row["strict_return_7d_pct"] <= 0:
        return "paper_trap"
    if row["strict_return_7d_pct"] > 0:
        return "watch"
    return "skip"


def strategy_row(metrics, best, validations):
    row = {
        **metrics,
        "direction": best["direction"],
        "threshold": best["threshold"],
        "regime": best["regime"],
        "tp_pct": best["tp_pct"],
        "sl_pct": best["sl_pct"],
        "time_stop_min": best["time_stop_min"],
    }
    for days in (7, 14, 30):
        validation = validations.get(days, {})
        for scenario in ("base", "strict", "taker"):
            summary = validation.get(scenario, {})
            prefix = f"{scenario}_{days}d"
            row[f"{prefix}_return_pct"] = summary.get("total_return_pct", 0.0)
            row[f"{prefix}_trades"] = summary.get("total_trades", 0)
            row[f"{prefix}_pf"] = summary.get("profit_factor", 0.0)
            row[f"{prefix}_dd_pct"] = summary.get("max_drawdown_pct", 0.0)
    row["base_return_7d_pct"] = row["base_7d_return_pct"]
    row["strict_return_7d_pct"] = row["strict_7d_return_pct"]
    row["strict_pf_7d"] = row["strict_7d_pf"]
    row["strict_trades_7d"] = row["strict_7d_trades"]
    row["strict_return_14d_pct"] = row["strict_14d_return_pct"]
    row["strict_return_30d_pct"] = row["strict_30d_return_pct"]
    row["decision"] = decision(row)
    return row


def fmt_pct(value):
    return f"{float(value):+.2f}%"


def fmt_plain_pct(value):
    return f"{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if value == math.inf else f"{value:.2f}"


def setup_text(row):
    return (
        f"{row['direction']} th{row['threshold']} {row['regime']} "
        f"TP {float(row['tp_pct']) * 100:.2f}% T{row['time_stop_min']}"
    )


def save_report(path, rows, market_rows, diagnostics):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = sorted(
        rows,
        key=lambda row: (
            {"ready": 5, "hot_watch": 4, "watch": 3, "paper_trap": 2, "skip": 1, "cold": 0}.get(row["decision"], 0),
            row["strict_return_7d_pct"],
            row["hot_score"],
        ),
        reverse=True,
    )
    counts = Counter(row["decision"] for row in rows)
    hot_market = [row for row in market_rows if row.get("is_hot")]
    errors = [row for row in diagnostics if row["status"] != "ok"]

    lines = [
        "# Hot Coin Wave Scanner",
        "",
        "Назначение: найти монеты, которые ожили прямо сейчас, и проверить, дает ли наша минутная семья стратегий плюс с realistic maker-fill.",
        "",
        "Решения:",
        "",
        "- `ready` — монета горячая, strict maker на 7d дает хороший плюс, 14d/30d не разваливаются.",
        "- `hot_watch` — текущий импульс есть, 7d выглядит хорошо, но старшие короткие окна слабее.",
        "- `watch` — strict maker в плюсе, но сигнал пока слабый.",
        "- `paper_trap` — база красивая, strict maker ломается.",
        "- `skip` — монета горячая, но стратегия не показывает edge.",
        "",
        "## Decision Counts",
        "",
        "| Decision | Count |",
        "|---|---:|",
    ]
    for key in ("ready", "hot_watch", "watch", "paper_trap", "skip", "cold"):
        lines.append(f"| {key} | {counts[key]} |")

    lines.extend(
        [
            "",
            "## Action List",
            "",
            "| Symbol | Decision | Hot score | Reasons | 7d move | 7d range | Vol x | Setup | Strict 7d | Strict 14d | Strict 30d | Base 7d | Taker 7d |",
            "|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows[:60]:
        lines.append(
            f"| {row['symbol']} | {row['decision']} | {float(row['hot_score']):.1f} | "
            f"{row['hot_reasons']} | {fmt_pct(row['return_7d_pct'])} | "
            f"{fmt_plain_pct(row['range_7d_pct'])} | {float(row['volume_ratio_7d']):.2f}x | "
            f"{setup_text(row)} | {fmt_pct(row['strict_7d_return_pct'])} / PF {fmt_pf(row['strict_7d_pf'])} | "
            f"{fmt_pct(row['strict_14d_return_pct'])} | {fmt_pct(row['strict_30d_return_pct'])} | "
            f"{fmt_pct(row['base_7d_return_pct'])} | {fmt_pct(row['taker_7d_return_pct'])} |"
        )

    lines.extend(
        [
            "",
            "## Hot Market Only",
            "",
            "| Symbol | Hot score | Reasons | 3d move | 7d move | 7d range | Vol x | Avg quote volume 7d |",
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(hot_market, key=lambda item: float(item["hot_score"]), reverse=True)[:80]:
        lines.append(
            f"| {row['symbol']} | {float(row['hot_score']):.1f} | {row['hot_reasons']} | "
            f"{fmt_pct(row['return_3d_pct'])} | {fmt_pct(row['return_7d_pct'])} | "
            f"{fmt_plain_pct(row['range_7d_pct'])} | {float(row['volume_ratio_7d']):.2f}x | "
            f"${float(row['quote_volume_7d_avg']):,.0f} |"
        )

    if errors:
        lines.extend(
            [
                "",
                "## Data Errors",
                "",
                "| Symbol | Error |",
                "|---|---|",
            ]
        )
        for row in errors:
            lines.append(f"| {row['symbol']} | {row['error']} |")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def market_fields_for_checkpoint():
    return [
        "symbol",
        "coin",
        "data_start",
        "data_end",
        "return_1d_pct",
        "return_3d_pct",
        "return_7d_pct",
        "return_14d_pct",
        "return_30d_pct",
        "range_3d_pct",
        "range_7d_pct",
        "range_14d_pct",
        "quote_volume_7d_avg",
        "quote_volume_14d_avg",
        "volume_ratio_7d",
        "volume_ratio_14d",
        "hot_score",
        "hot_reasons",
        "is_hot",
    ]


def summary_fields_for_checkpoint():
    return [
        *market_fields_for_checkpoint(),
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "base_7d_return_pct",
        "base_7d_trades",
        "base_7d_pf",
        "base_7d_dd_pct",
        "strict_7d_return_pct",
        "strict_7d_trades",
        "strict_7d_pf",
        "strict_7d_dd_pct",
        "taker_7d_return_pct",
        "taker_7d_trades",
        "taker_7d_pf",
        "taker_7d_dd_pct",
        "base_14d_return_pct",
        "strict_14d_return_pct",
        "taker_14d_return_pct",
        "base_30d_return_pct",
        "strict_30d_return_pct",
        "taker_30d_return_pct",
        "decision",
    ]


def main():
    parser = argparse.ArgumentParser(description="Current hot coin wave scanner.")
    parser.add_argument("--universe", choices=["project", "binance"], default="project")
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--symbols-file", default=None, help="One futures symbol per line.")
    parser.add_argument("--days", type=int, default=45)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--baseline-days", type=int, default=30)
    parser.add_argument("--select-days", type=int, default=7)
    parser.add_argument("--strategy-windows", nargs="*", type=int, default=[7, 14, 30])
    parser.add_argument("--max-strategy-candidates", type=int, default=40)
    parser.add_argument("--min-quote-volume", type=float, default=500_000.0)
    parser.add_argument("--save-market", default="data/hot_coin_wave_market.csv")
    parser.add_argument("--save-summary", default="data/hot_coin_wave_scan_summary.csv")
    parser.add_argument("--save-diagnostics", default="data/hot_coin_wave_scan_diagnostics.csv")
    parser.add_argument("--save-report", default="strategies/hot-coin-wave-scanner-current.md")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--market-workers", type=int, default=12)
    parser.add_argument("--archive-end-day", default=None, help="Fixed Binance archive end day, YYYY-MM-DD.")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    screen = load_module("screen_new_binance_candidates", SCREEN_PATH)
    explosion = load_module("explosion_wave_scan", EXPLOSION_PATH)

    if args.symbols_file:
        with open(args.symbols_file, encoding="utf-8") as handle:
            symbols = unique(
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            )
    elif args.symbols:
        symbols = unique(args.symbols)
    elif args.universe == "binance":
        symbols = load_binance_usdt_perps()
    else:
        symbols = unique(explosion.DEFAULT_SYMBOLS)

    if args.archive_end_day:
        fixed_end_day = date.fromisoformat(args.archive_end_day)
        multi.latest_archive_day = lambda _symbol: fixed_end_day

    variants = make_strategy_variants(screen)
    market_rows = []
    diagnostics = []

    market_fetch_days = max(args.days, args.baseline_days + 14)

    def process_market_symbol(symbol):
        try:
            candles, _, _ = multi.fetch_klines_fast(symbol, market_fetch_days, 0)
            if len(candles) < market_fetch_days * 1440:
                raise RuntimeError(f"not enough candles: {len(candles)}")
            row = market_metrics(symbol, candles[-market_fetch_days * 1440 :], args.baseline_days)
            if row["quote_volume_7d_avg"] < args.min_quote_volume:
                row["is_hot"] = False
                row["hot_reasons"] = (row["hot_reasons"] + ";low liquidity").strip(";")
            return row, {"symbol": symbol, "status": "ok", "error": ""}
        except Exception as exc:
            return None, {"symbol": symbol, "status": "error", "error": str(exc)}

    with ThreadPoolExecutor(max_workers=max(1, args.market_workers)) as executor:
        futures = {executor.submit(process_market_symbol, symbol): symbol for symbol in symbols}
        for index, future in enumerate(as_completed(futures), start=1):
            symbol = futures[future]
            row, diagnostic = future.result()
            diagnostics.append(diagnostic)
            if row:
                market_rows.append(row)
            status = diagnostic["status"]
            suffix = f" hot={row['hot_score']:.1f}" if row else f" error={diagnostic['error']}"
            print(f"[market {index}/{len(symbols)}] {symbol} {status}{suffix}", flush=True)
            if args.checkpoint_every > 0 and index % args.checkpoint_every == 0:
                save_csv(os.path.join(ROOT, args.save_market), market_rows, market_fields_for_checkpoint())
                save_csv(
                    os.path.join(ROOT, args.save_diagnostics),
                    diagnostics,
                    ["symbol", "status", "error"],
                )

    hot_rows = [row for row in market_rows if row["is_hot"]]
    hot_rows.sort(key=lambda row: row["hot_score"], reverse=True)
    strategy_targets = hot_rows[: args.max_strategy_candidates]

    summary_rows = []
    for index, metrics in enumerate(strategy_targets, start=1):
        symbol = metrics["symbol"]
        print(f"[strategy {index}/{len(strategy_targets)}] {symbol}", flush=True)
        candles, _, _ = multi.fetch_klines_fast(symbol, args.days, args.warmup_days)
        if len(candles) < args.days * 1440:
            raise RuntimeError(f"not enough strategy candles for {symbol}: {len(candles)}")
        base_args = multi.make_strategy_args(reinvest, "7.3", symbol)
        bt.add_indicators_and_signals(candles, base_args)
        candles = candles[-args.days * 1440 :]
        best = best_recent_strategy(
            bt,
            reinvest,
            multi,
            cf,
            candles,
            symbol,
            variants,
            args.select_days,
        )
        validations = validate_variant_windows(
            bt,
            reinvest,
            multi,
            cf,
            candles,
            best,
            args.strategy_windows,
        )
        row = strategy_row(metrics, best, validations)
        summary_rows.append(row)
        if args.checkpoint_every > 0 and index % args.checkpoint_every == 0:
            save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields_for_checkpoint())
        print(
            f"  {row['decision']} hot={row['hot_score']:.1f} "
            f"strict7={row['strict_7d_return_pct']:+.2f}% "
            f"base7={row['base_7d_return_pct']:+.2f}% {setup_text(row)}",
            flush=True,
        )

    market_fields = [
        "symbol",
        "coin",
        "data_start",
        "data_end",
        "return_1d_pct",
        "return_3d_pct",
        "return_7d_pct",
        "return_14d_pct",
        "return_30d_pct",
        "range_3d_pct",
        "range_7d_pct",
        "range_14d_pct",
        "quote_volume_7d_avg",
        "quote_volume_14d_avg",
        "volume_ratio_7d",
        "volume_ratio_14d",
        "hot_score",
        "hot_reasons",
        "is_hot",
    ]
    summary_fields = [
        *market_fields,
        "direction",
        "threshold",
        "regime",
        "tp_pct",
        "sl_pct",
        "time_stop_min",
        "base_7d_return_pct",
        "base_7d_trades",
        "base_7d_pf",
        "base_7d_dd_pct",
        "strict_7d_return_pct",
        "strict_7d_trades",
        "strict_7d_pf",
        "strict_7d_dd_pct",
        "taker_7d_return_pct",
        "taker_7d_trades",
        "taker_7d_pf",
        "taker_7d_dd_pct",
        "base_14d_return_pct",
        "strict_14d_return_pct",
        "taker_14d_return_pct",
        "base_30d_return_pct",
        "strict_30d_return_pct",
        "taker_30d_return_pct",
        "decision",
    ]
    save_csv(os.path.join(ROOT, args.save_market), market_rows, market_fields)
    save_csv(os.path.join(ROOT, args.save_summary), summary_rows, summary_fields)
    save_csv(os.path.join(ROOT, args.save_diagnostics), diagnostics, ["symbol", "status", "error"])
    save_report(os.path.join(ROOT, args.save_report), summary_rows, market_rows, diagnostics)

    print(f"hot market rows: {len(hot_rows)}")
    print(f"strategy rows: {len(summary_rows)}")
    print(f"saved market: {os.path.join(ROOT, args.save_market)}")
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
