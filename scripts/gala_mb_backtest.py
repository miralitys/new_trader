#!/usr/bin/env python3
"""Approximate GALAUSDT mb-score backtest.

This is intentionally not the original mb80/mb40/smart logic. It implements a
deterministic approximation with explicit scores, filters, TP/SL, fees, and
slippage so runs can be reproduced and compared.
"""

import argparse
import csv
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, time as dt_time, timedelta, timezone


MARKETS = {
    "futures_global": "https://fapi.binance.com/fapi/v1/klines",
    "spot_global": "https://api.binance.com/api/v3/klines",
    "data_api_spot": "https://data-api.binance.vision/api/v3/klines",
    "spot_us": "https://api.binance.us/api/v3/klines",
}
ARCHIVE_MARKETS = {
    "futures_archive": "https://data.binance.vision/data/futures/um/daily/klines",
    "spot_archive": "https://data.binance.vision/data/spot/daily/klines",
}

INTERVALS_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "1h": 60,
}
BINANCE_LIMIT = 1000


def utc_ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def interval_minutes(interval):
    if interval not in INTERVALS_MINUTES:
        raise ValueError(f"Unsupported interval: {interval}")
    return INTERVALS_MINUTES[interval]


def interval_ms(interval):
    return interval_minutes(interval) * 60_000


def candles_per_day(interval):
    return (24 * 60) // interval_minutes(interval)


def minute_count_to_bars(minutes, interval):
    return max(1, math.ceil(minutes / interval_minutes(interval)))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backtest approximate GALAUSDT mb80/mb40 strategy."
    )
    parser.add_argument(
        "--market",
        choices=list(MARKETS.keys()) + list(ARCHIVE_MARKETS.keys()),
        default="futures_global",
    )
    parser.add_argument("--symbol", default="GALAUSDT")
    parser.add_argument("--interval", choices=list(INTERVALS_MINUTES.keys()), default="1m")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--warmup-days", type=int, default=0)
    parser.add_argument("--direction", choices=["both", "long", "short"], default="both")
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--position-pct", type=float, default=1.0)
    parser.add_argument("--fee-pct", type=float, default=0.0004)
    parser.add_argument("--slippage-pct", type=float, default=0.0002)
    parser.add_argument("--entry-mode", choices=["next_open", "maker_limit"], default="next_open")
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=5)
    parser.add_argument("--long-tp-pct", type=float, default=0.004)
    parser.add_argument("--long-sl-pct", type=float, default=0.003)
    parser.add_argument("--short-tp-pct", type=float, default=0.003)
    parser.add_argument("--short-sl-pct", type=float, default=0.003)
    parser.add_argument("--time-stop-min", type=int, default=10)
    parser.add_argument("--long-time-stop-min", type=int, default=None)
    parser.add_argument("--short-time-stop-min", type=int, default=None)
    parser.add_argument("--daily-loss-stop-pct", type=float, default=None)
    parser.add_argument("--weekly-loss-stop-pct", type=float, default=None)
    parser.add_argument("--filter-atr-min-pct", type=float, default=None)
    parser.add_argument("--filter-atr-max-pct", type=float, default=None)
    parser.add_argument("--filter-dist-ema200-min", type=float, default=None)
    parser.add_argument("--filter-dist-ema200-max", type=float, default=None)
    parser.add_argument("--filter-return-1d-min", type=float, default=None)
    parser.add_argument("--filter-return-1d-max", type=float, default=None)
    parser.add_argument("--filter-return-7d-min", type=float, default=None)
    parser.add_argument("--filter-return-7d-max", type=float, default=None)
    parser.add_argument("--save-candles", default="data/gala_candles.csv")
    parser.add_argument("--save-trades", default="data/gala_trades.csv")
    parser.add_argument("--save-equity", default="data/gala_equity.csv")
    parser.add_argument("--long-threshold", type=float, default=80.0)
    parser.add_argument("--short-threshold", type=float, default=40.0)
    parser.add_argument("--volume-multiplier", type=float, default=1.5)
    parser.add_argument("--atr-min-pct", type=float, default=0.0015)
    parser.add_argument("--atr-max-pct", type=float, default=0.0120)
    return parser.parse_args()


def request_json(url, params, retries=3):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    headers = {"User-Agent": "gala-mb-backtest/1.0"}
    request = urllib.request.Request(full_url, headers=headers)

    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = str(exc)
            last_error = f"HTTP {exc.code}: {body}"
        except Exception as exc:
            last_error = str(exc)

        if attempt < retries - 1:
            time.sleep(0.5 * (attempt + 1))

    raise RuntimeError(f"Binance request failed: {last_error}")


def fetch_klines(market, symbol, days, interval):
    if market in ARCHIVE_MARKETS:
        return fetch_archive_klines(market, symbol, days, interval)

    if days <= 0:
        raise ValueError("--days must be positive")

    endpoint = MARKETS[market]
    current_interval_ms = interval_ms(interval)
    now_ms = int(time.time() * 1000)
    last_closed_open_ms = (now_ms // current_interval_ms) * current_interval_ms - current_interval_ms
    candle_count = days * candles_per_day(interval)
    start_ms = last_closed_open_ms - (candle_count - 1) * current_interval_ms
    end_ms = last_closed_open_ms + current_interval_ms - 1

    rows = []
    current_start = start_ms
    seen_open_times = set()

    while current_start <= end_ms:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ms,
            "limit": BINANCE_LIMIT,
        }
        payload = request_json(endpoint, params)

        if isinstance(payload, dict):
            raise RuntimeError(f"Binance API error: {payload}")
        if not payload:
            break

        last_open_time = None
        for item in payload:
            open_time = int(item[0])
            if open_time in seen_open_times:
                continue
            seen_open_times.add(open_time)
            rows.append(
                {
                    "open_time_ms": open_time,
                    "close_time_ms": int(item[6]),
                    "open_time": utc_ms_to_iso(open_time),
                    "close_time": utc_ms_to_iso(int(item[6])),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                }
            )
            last_open_time = open_time

        if last_open_time is None:
            break

        current_start = last_open_time + current_interval_ms
        if len(payload) < BINANCE_LIMIT:
            break
        time.sleep(0.03)

    rows.sort(key=lambda row: row["open_time_ms"])
    return [row for row in rows if start_ms <= row["open_time_ms"] <= last_closed_open_ms]


def archive_zip_url(market, symbol, day, interval):
    base = ARCHIVE_MARKETS[market]
    day_text = day.isoformat()
    symbol = symbol.upper()
    return f"{base}/{symbol}/{interval}/{symbol}-{interval}-{day_text}.zip"


def archive_url_exists(url):
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "gala-mb-backtest/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def latest_archive_day(market, symbol, interval):
    today = datetime.now(timezone.utc).date()
    for offset in range(0, 10):
        day = today - timedelta(days=offset)
        if archive_url_exists(archive_zip_url(market, symbol, day, interval)):
            return day
    raise RuntimeError(f"No recent archive files found for {symbol.upper()} on {market}.")


def fetch_archive_day(market, symbol, day, interval):
    url = archive_zip_url(market, symbol, day, interval)
    request = urllib.request.Request(url, headers={"User-Agent": "gala-mb-backtest/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise

    rows = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_names:
            return rows
        with archive.open(csv_names[0]) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8")
            reader = csv.reader(text)
            for item in reader:
                if not item or not item[0].isdigit():
                    continue
                open_time = int(item[0])
                close_time = int(item[6])
                rows.append(
                    {
                        "open_time_ms": open_time,
                        "close_time_ms": close_time,
                        "open_time": utc_ms_to_iso(open_time),
                        "close_time": utc_ms_to_iso(close_time),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
    return rows


def fetch_archive_klines(market, symbol, days, interval):
    if days <= 0:
        raise ValueError("--days must be positive")

    end_day = latest_archive_day(market, symbol, interval)
    start_day = end_day - timedelta(days=days - 1)
    start_dt = datetime.combine(start_day, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_day, dt_time.max, tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rows = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        rows.extend(fetch_archive_day(market, symbol, day, interval))
        time.sleep(0.02)

    rows.sort(key=lambda row: row["open_time_ms"])
    return [row for row in rows if start_ms <= row["open_time_ms"] <= end_ms]


def rolling_sma(values, period):
    output = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= period:
            running -= values[index - period]
        if index >= period - 1:
            output[index] = running / period
    return output


def ema(values, period):
    output = [None] * len(values)
    if len(values) < period:
        return output

    first = sum(values[:period]) / period
    output[period - 1] = first
    alpha = 2.0 / (period + 1.0)
    previous = first

    for index in range(period, len(values)):
        previous = values[index] * alpha + previous * (1.0 - alpha)
        output[index] = previous

    return output


def rsi(values, period=14):
    output = [None] * len(values)
    if len(values) <= period:
        return output

    gains = []
    losses = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    output[period] = rsi_from_avgs(avg_gain, avg_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        output[index] = rsi_from_avgs(avg_gain, avg_loss)

    return output


def rsi_from_avgs(avg_gain, avg_loss):
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def atr(highs, lows, closes, period=14):
    output = [None] * len(closes)
    if len(closes) < period:
        return output

    true_ranges = []
    for index in range(len(closes)):
        if index == 0:
            true_ranges.append(highs[index] - lows[index])
        else:
            true_ranges.append(
                max(
                    highs[index] - lows[index],
                    abs(highs[index] - closes[index - 1]),
                    abs(lows[index] - closes[index - 1]),
                )
            )

    first = sum(true_ranges[:period]) / period
    output[period - 1] = first
    previous = first

    for index in range(period, len(closes)):
        previous = (previous * (period - 1) + true_ranges[index]) / period
        output[index] = previous

    return output


def previous_rolling_extreme(values, period, fn):
    output = [None] * len(values)
    for index in range(period, len(values)):
        output[index] = fn(values[index - period : index])
    return output


def trailing_return(values, period):
    output = [None] * len(values)
    for index in range(period, len(values)):
        previous = values[index - period]
        if previous:
            output[index] = values[index] / previous - 1.0
    return output


def value_in_optional_range(value, min_value, max_value):
    if min_value is None and max_value is None:
        return True
    if value is None:
        return False
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def regime_filter_passed(row, args):
    dist_ema200 = row.get("dist_ema200")
    return_1d = row.get("return_1d")
    return_7d = row.get("return_7d")

    return (
        value_in_optional_range(row.get("atr_pct"), args.filter_atr_min_pct, args.filter_atr_max_pct)
        and value_in_optional_range(
            dist_ema200, args.filter_dist_ema200_min, args.filter_dist_ema200_max
        )
        and value_in_optional_range(return_1d, args.filter_return_1d_min, args.filter_return_1d_max)
        and value_in_optional_range(return_7d, args.filter_return_7d_min, args.filter_return_7d_max)
    )


def add_indicators_and_signals(candles, args):
    opens = [row["open"] for row in candles]
    highs = [row["high"] for row in candles]
    lows = [row["low"] for row in candles]
    closes = [row["close"] for row in candles]
    volumes = [row["volume"] for row in candles]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    volume_sma20 = rolling_sma(volumes, 20)
    recent_high20 = previous_rolling_extreme(highs, 20, max)
    recent_low20 = previous_rolling_extreme(lows, 20, min)
    per_day = candles_per_day(args.interval)
    return_1d = trailing_return(closes, per_day)
    return_7d = trailing_return(closes, 7 * per_day)

    for index, row in enumerate(candles):
        candle_range = row["high"] - row["low"]
        body = abs(row["close"] - row["open"])
        if candle_range > 0:
            body_ratio = body / candle_range
            upper_wick_ratio = (row["high"] - max(row["open"], row["close"])) / candle_range
            lower_wick_ratio = (min(row["open"], row["close"]) - row["low"]) / candle_range
        else:
            body_ratio = 0.0
            upper_wick_ratio = 0.0
            lower_wick_ratio = 0.0

        row["ema20"] = ema20[index]
        row["ema50"] = ema50[index]
        row["ema200"] = ema200[index]
        row["rsi14"] = rsi14[index]
        row["atr14"] = atr14[index]
        row["atr_pct"] = atr14[index] / row["close"] if atr14[index] is not None else None
        row["volume_sma20"] = volume_sma20[index]
        row["recent_high20"] = recent_high20[index]
        row["recent_low20"] = recent_low20[index]
        row["dist_ema200"] = (
            row["close"] / ema200[index] - 1.0 if ema200[index] is not None and ema200[index] else None
        )
        row["return_1d"] = return_1d[index]
        row["return_7d"] = return_7d[index]
        row["body_ratio"] = body_ratio
        row["upper_wick_ratio"] = upper_wick_ratio
        row["lower_wick_ratio"] = lower_wick_ratio

        long_score = 0.0
        if row["ema200"] is not None and row["ema20"] is not None and row["ema50"] is not None:
            if row["close"] > row["ema200"] and row["ema20"] > row["ema50"]:
                long_score += 25.0
        if row["recent_high20"] is not None and row["close"] > row["recent_high20"]:
            long_score += 25.0
        if row["volume_sma20"] is not None:
            if row["volume"] > row["volume_sma20"] * args.volume_multiplier:
                long_score += 20.0
        if row["atr_pct"] is not None and args.atr_min_pct <= row["atr_pct"] <= args.atr_max_pct:
            long_score += 15.0
        if body_ratio > 0.60 and row["close"] > row["open"]:
            long_score += 15.0

        smart_long_filter = True
        if row["ema20"] is None or row["close"] > row["ema20"] * 1.010:
            smart_long_filter = False
        if upper_wick_ratio > 0.35:
            smart_long_filter = False

        short_score = 0.0
        if row["ema200"] is not None and row["ema20"] is not None and row["ema50"] is not None:
            if row["close"] < row["ema200"] and row["ema20"] < row["ema50"]:
                short_score += 25.0
        if row["recent_low20"] is not None and row["close"] < row["recent_low20"]:
            short_score += 25.0
        if row["volume_sma20"] is not None:
            if row["volume"] > row["volume_sma20"] * args.volume_multiplier:
                short_score += 20.0
        if row["atr_pct"] is not None and args.atr_min_pct <= row["atr_pct"] <= args.atr_max_pct:
            short_score += 15.0
        if body_ratio > 0.60 and row["close"] < row["open"]:
            short_score += 15.0

        row["long_score"] = long_score
        row["short_score"] = short_score
        row["smart_long_filter"] = smart_long_filter
        regime_passed = regime_filter_passed(row, args)
        row["regime_filter_passed"] = regime_passed
        row["long_signal"] = long_score >= args.long_threshold and smart_long_filter and regime_passed
        row["short_signal"] = short_score >= args.short_threshold and regime_passed

    return candles


def pick_signal(row, direction):
    candidates = []
    if direction in ("both", "long") and row["long_signal"]:
        candidates.append((row["long_score"], "long"))
    if direction in ("both", "short") and row["short_signal"]:
        candidates.append((row["short_score"], "short"))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def apply_exit_slippage(direction, price, slippage_pct):
    if direction == "long":
        return price * (1.0 - slippage_pct)
    return price * (1.0 + slippage_pct)


def apply_entry_slippage(direction, price, slippage_pct):
    if direction == "long":
        return price * (1.0 + slippage_pct)
    return price * (1.0 - slippage_pct)


def limit_entry_price(direction, reference_price, offset_pct):
    if direction == "long":
        return reference_price * (1.0 - offset_pct)
    return reference_price * (1.0 + offset_pct)


def find_entry_fill(candles, signal_idx, direction, args):
    order_start_idx = signal_idx + 1
    if order_start_idx >= len(candles):
        return None, order_start_idx

    order_row = candles[order_start_idx]
    signal_row = candles[signal_idx]

    if args.entry_mode == "next_open":
        entry_ideal = order_row["open"]
        return (
            {
                "signal_idx": signal_idx,
                "signal_time": signal_row["close_time"],
                "order_start_idx": order_start_idx,
                "order_start_time": order_row["open_time"],
                "entry_idx": order_start_idx,
                "entry_time": order_row["open_time"],
                "entry_ideal": entry_ideal,
                "entry_fill": apply_entry_slippage(direction, entry_ideal, args.slippage_pct),
                "limit_price": None,
                "fill_delay_min": 0,
            },
            order_start_idx,
        )

    limit_price = limit_entry_price(direction, order_row["open"], args.limit_entry_offset_pct)
    timeout_bars = minute_count_to_bars(max(1, args.limit_entry_timeout_min), args.interval)
    last_wait_idx = min(len(candles) - 1, order_start_idx + timeout_bars - 1)

    for index in range(order_start_idx, last_wait_idx + 1):
        row = candles[index]
        if direction == "long":
            filled = row["low"] <= limit_price
        else:
            filled = row["high"] >= limit_price

        if filled:
            return (
                {
                    "signal_idx": signal_idx,
                    "signal_time": signal_row["close_time"],
                    "order_start_idx": order_start_idx,
                    "order_start_time": order_row["open_time"],
                    "entry_idx": index,
                    "entry_time": row["open_time"],
                    "entry_ideal": limit_price,
                    "entry_fill": limit_price,
                    "limit_price": limit_price,
                    "fill_delay_min": (index - order_start_idx) * interval_minutes(args.interval),
                },
                last_wait_idx,
            )

    return None, last_wait_idx


def simulate_trade(candles, entry_info, direction, equity_before, args):
    entry_idx = entry_info["entry_idx"]
    entry_row = candles[entry_idx]
    entry_ideal = entry_info["entry_ideal"]
    entry_fill = entry_info["entry_fill"]

    if direction == "long":
        tp_level = entry_fill * (1.0 + args.long_tp_pct)
        sl_level = entry_fill * (1.0 - args.long_sl_pct)
        time_stop_min = args.long_time_stop_min or args.time_stop_min
    else:
        tp_level = entry_fill * (1.0 - args.short_tp_pct)
        sl_level = entry_fill * (1.0 + args.short_sl_pct)
        time_stop_min = args.short_time_stop_min or args.time_stop_min

    exit_idx = len(candles) - 1
    exit_ideal = candles[-1]["close"]
    exit_fill = apply_exit_slippage(direction, exit_ideal, args.slippage_pct)
    reason = "end_of_data"

    for index in range(entry_idx, len(candles)):
        row = candles[index]
        elapsed_min = (index - entry_idx + 1) * interval_minutes(args.interval)

        if direction == "long":
            stop_hit = row["low"] <= sl_level
            target_hit = row["high"] >= tp_level
        else:
            stop_hit = row["high"] >= sl_level
            target_hit = row["low"] <= tp_level

        if args.entry_mode == "maker_limit" and index == entry_idx:
            # The candle only tells us that the limit price was touched; it does
            # not tell us whether the target came before or after that touch.
            # Counting same-candle TP would be optimistic, so only SL is allowed.
            target_hit = False

        if stop_hit:
            exit_idx = index
            exit_ideal = sl_level
            exit_fill = apply_exit_slippage(direction, exit_ideal, args.slippage_pct)
            reason = "stop_loss"
            break

        if target_hit:
            exit_idx = index
            exit_ideal = tp_level
            exit_fill = apply_exit_slippage(direction, exit_ideal, args.slippage_pct)
            reason = "take_profit"
            break

        if elapsed_min >= time_stop_min:
            exit_idx = index
            exit_ideal = row["close"]
            exit_fill = apply_exit_slippage(direction, exit_ideal, args.slippage_pct)
            reason = "time_stop"
            break

    position_notional = equity_before * args.position_pct
    quantity = position_notional / entry_fill if entry_fill > 0 else 0.0

    if direction == "long":
        gross_pnl = (exit_fill - entry_fill) * quantity
    else:
        gross_pnl = (entry_fill - exit_fill) * quantity

    exit_notional = quantity * exit_fill
    fee_paid = (position_notional * args.fee_pct) + (exit_notional * args.fee_pct)
    net_pnl = gross_pnl - fee_paid
    equity_after = equity_before + net_pnl

    gross_return_pct = (gross_pnl / equity_before * 100.0) if equity_before else 0.0
    net_return_pct = (net_pnl / equity_before * 100.0) if equity_before else 0.0
    fee_assumed_pct = (fee_paid / equity_before * 100.0) if equity_before else 0.0
    slippage_sides = 1.0 if args.entry_mode == "maker_limit" else 2.0
    slippage_assumed_pct = args.position_pct * args.slippage_pct * slippage_sides * 100.0

    duration_min = (exit_idx - entry_idx + 1) * interval_minutes(args.interval)
    exit_time_ms = candles[exit_idx]["close_time_ms"]

    return {
        "direction": direction,
        "entry_mode": args.entry_mode,
        "signal_time": entry_info["signal_time"],
        "order_start_time": entry_info["order_start_time"],
        "entry_time": entry_info["entry_time"],
        "exit_time": utc_ms_to_iso(exit_time_ms),
        "entry": entry_fill,
        "exit": exit_fill,
        "entry_ideal": entry_ideal,
        "exit_ideal": exit_ideal,
        "limit_price": entry_info["limit_price"],
        "fill_delay_min": entry_info["fill_delay_min"],
        "reason": reason,
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "pnl": net_pnl,
        "duration_min": duration_min,
        "equity_before": equity_before,
        "equity_after": equity_after,
        "fee_paid": fee_paid,
        "fee_assumed_pct": fee_assumed_pct,
        "slippage_assumed_pct": slippage_assumed_pct,
        "exit_idx": exit_idx,
    }


def run_backtest(candles, args):
    trades = []
    equity = args.initial_balance
    equity_curve = []
    stats = Counter()
    killed_days = set()
    killed_weeks = set()
    day_start_equity = {}
    week_start_equity = {}
    week_peak_equity = {}

    if candles:
        equity_curve.append({"time": candles[0]["open_time"], "equity": equity})

    index = 0
    while index < len(candles) - 1:
        signal_day = candles[index]["open_time"][:10]
        signal_week = iso_week_key(candles[index]["open_time"])
        if signal_day not in day_start_equity:
            day_start_equity[signal_day] = equity
        if signal_week not in week_start_equity:
            week_start_equity[signal_week] = equity
            week_peak_equity[signal_week] = equity
        week_peak_equity[signal_week] = max(week_peak_equity[signal_week], equity)

        if signal_day in killed_days:
            stats["daily_loss_stop_skipped_candles"] += 1
            index += 1
            continue
        if signal_week in killed_weeks:
            stats["weekly_loss_stop_skipped_candles"] += 1
            index += 1
            continue

        direction = pick_signal(candles[index], args.direction)
        if direction is None:
            index += 1
            continue

        stats["entry_signals"] += 1
        stats[f"{direction}_entry_signals"] += 1
        entry_info, waited_until_idx = find_entry_fill(candles, index, direction, args)
        if entry_info is None:
            stats["unfilled_entry_orders"] += 1
            stats[f"{direction}_unfilled_entry_orders"] += 1
            index = waited_until_idx + 1
            continue

        stats["filled_entry_orders"] += 1
        stats[f"{direction}_filled_entry_orders"] += 1
        trade = simulate_trade(candles, entry_info, direction, equity, args)
        equity = trade["equity_after"]
        trades.append(trade)
        equity_curve.append({"time": trade["exit_time"], "equity": equity})

        exit_day = trade["exit_time"][:10]
        if exit_day not in day_start_equity:
            day_start_equity[exit_day] = trade["equity_before"]

        if args.daily_loss_stop_pct is not None and args.daily_loss_stop_pct > 0:
            daily_return = equity / day_start_equity[exit_day] - 1.0
            if daily_return <= -args.daily_loss_stop_pct and exit_day not in killed_days:
                killed_days.add(exit_day)
                stats["daily_loss_stop_events"] += 1
                stats[f"{direction}_daily_loss_stop_events"] += 1

        weekly_loss_stop_pct = getattr(args, "weekly_loss_stop_pct", None)
        exit_week = iso_week_key(trade["exit_time"])
        if exit_week not in week_start_equity:
            week_start_equity[exit_week] = trade["equity_before"]
            week_peak_equity[exit_week] = trade["equity_before"]
        week_peak_equity[exit_week] = max(week_peak_equity[exit_week], trade["equity_before"])
        if weekly_loss_stop_pct is not None and weekly_loss_stop_pct > 0:
            weekly_drawdown = equity / week_peak_equity[exit_week] - 1.0
            if weekly_drawdown <= -weekly_loss_stop_pct and exit_week not in killed_weeks:
                killed_weeks.add(exit_week)
                stats["weekly_loss_stop_events"] += 1
                stats[f"{direction}_weekly_loss_stop_events"] += 1
        week_peak_equity[exit_week] = max(week_peak_equity[exit_week], equity)

        index = trade["exit_idx"] + 1

    return trades, equity_curve, stats


def iso_week_key(value):
    date_value = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    year, week, _ = date_value.isocalendar()
    return f"{year}-W{week:02d}"


def max_drawdown_pct(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]["equity"]
    max_drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = (peak - equity) / peak * 100.0
            max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def profit_factor(trades):
    wins = sum(trade["pnl"] for trade in trades if trade["pnl"] > 0)
    losses = sum(trade["pnl"] for trade in trades if trade["pnl"] < 0)
    if losses == 0:
        return math.inf if wins > 0 else 0.0
    return wins / abs(losses)


def summarize_trades(trades, initial_balance, equity_curve):
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_balance
    total_trades = len(trades)
    winning_returns = [trade["net_return_pct"] for trade in trades if trade["net_return_pct"] > 0]
    losing_returns = [trade["net_return_pct"] for trade in trades if trade["net_return_pct"] < 0]

    total_return_pct = (final_equity / initial_balance - 1.0) * 100.0 if initial_balance else 0.0
    win_rate_pct = len(winning_returns) / total_trades * 100.0 if total_trades else 0.0
    avg_win_pct = sum(winning_returns) / len(winning_returns) if winning_returns else 0.0
    avg_loss_pct = sum(losing_returns) / len(losing_returns) if losing_returns else 0.0
    expectancy_pct = (
        sum(trade["net_return_pct"] for trade in trades) / total_trades if total_trades else 0.0
    )
    total_fees_pct = sum(trade["fee_assumed_pct"] for trade in trades)
    total_slippage_pct = sum(trade["slippage_assumed_pct"] for trade in trades)

    return {
        "total_trades": total_trades,
        "total_return_pct": total_return_pct,
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor(trades),
        "max_drawdown_pct": max_drawdown_pct(equity_curve),
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "expectancy_pct": expectancy_pct,
        "total_fees_pct": total_fees_pct,
        "total_slippage_pct": total_slippage_pct,
        "exit_reasons": Counter(trade["reason"] for trade in trades),
        "final_equity": final_equity,
    }


def summarize_direction(trades, initial_balance):
    output = {}
    for direction in ("long", "short"):
        direction_trades = [trade for trade in trades if trade["direction"] == direction]
        equity_curve = [{"time": "initial", "equity": initial_balance}]
        running = initial_balance
        for trade in direction_trades:
            running += trade["pnl"]
            equity_curve.append({"time": trade["exit_time"], "equity": running})
        summary = summarize_trades(direction_trades, initial_balance, equity_curve)
        summary["pnl"] = sum(trade["pnl"] for trade in direction_trades)
        summary["return_contribution_pct"] = (
            summary["pnl"] / initial_balance * 100.0 if initial_balance else 0.0
        )
        output[direction] = summary
    return output


def format_pct(value):
    return f"{value:.4f}%"


def format_float(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, str):
        return value
    return f"{value:.10g}"


def format_pf(value):
    if value == math.inf:
        return "inf"
    return f"{value:.4f}"


def save_csv(path, rows, fields):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: format_float(row.get(field)) for field in fields})


def print_summary(args, candles, trades, equity_curve, stats=None):
    stats = stats or Counter()
    overall = summarize_trades(trades, args.initial_balance, equity_curve)
    by_direction = summarize_direction(trades, args.initial_balance)

    print("=== GALA MB Approx Backtest ===")
    print(f"market: {args.market}")
    print(f"symbol: {args.symbol.upper()}")
    print(f"interval: {args.interval}")
    print(f"direction: {args.direction}")
    print(f"entry mode: {args.entry_mode}")
    if args.entry_mode == "maker_limit":
        print(f"limit entry offset %: {format_pct(args.limit_entry_offset_pct * 100.0)}")
        print(f"limit entry timeout min: {args.limit_entry_timeout_min}")
    if args.daily_loss_stop_pct is not None and args.daily_loss_stop_pct > 0:
        print(f"daily loss stop %: {format_pct(args.daily_loss_stop_pct * 100.0)}")
    active_filters = [
        args.filter_atr_min_pct is not None,
        args.filter_atr_max_pct is not None,
        args.filter_dist_ema200_min is not None,
        args.filter_dist_ema200_max is not None,
        args.filter_return_1d_min is not None,
        args.filter_return_1d_max is not None,
        args.filter_return_7d_min is not None,
        args.filter_return_7d_max is not None,
    ]
    if any(active_filters):
        print("regime filters:")
        print(
            "  atr pct: "
            f"{args.filter_atr_min_pct if args.filter_atr_min_pct is not None else '-inf'} .. "
            f"{args.filter_atr_max_pct if args.filter_atr_max_pct is not None else 'inf'}"
        )
        print(
            "  dist ema200: "
            f"{args.filter_dist_ema200_min if args.filter_dist_ema200_min is not None else '-inf'} .. "
            f"{args.filter_dist_ema200_max if args.filter_dist_ema200_max is not None else 'inf'}"
        )
        print(
            "  return 1d: "
            f"{args.filter_return_1d_min if args.filter_return_1d_min is not None else '-inf'} .. "
            f"{args.filter_return_1d_max if args.filter_return_1d_max is not None else 'inf'}"
        )
        print(
            "  return 7d: "
            f"{args.filter_return_7d_min if args.filter_return_7d_min is not None else '-inf'} .. "
            f"{args.filter_return_7d_max if args.filter_return_7d_max is not None else 'inf'}"
        )
    print(f"downloaded candles count: {len(candles)}")
    if candles:
        print(f"data start time: {candles[0]['open_time']}")
        print(f"data end time: {candles[-1]['close_time']}")
    else:
        print("data start time: n/a")
        print("data end time: n/a")
    print("")
    print(f"total trades: {overall['total_trades']}")
    print(f"total return %: {format_pct(overall['total_return_pct'])}")
    print(f"win rate %: {format_pct(overall['win_rate_pct'])}")
    print(f"profit factor: {format_pf(overall['profit_factor'])}")
    print(f"max drawdown %: {format_pct(overall['max_drawdown_pct'])}")
    print(f"avg win %: {format_pct(overall['avg_win_pct'])}")
    print(f"avg loss %: {format_pct(overall['avg_loss_pct'])}")
    print(f"expectancy per trade %: {format_pct(overall['expectancy_pct'])}")
    print(f"total fees assumed %: {format_pct(overall['total_fees_pct'])}")
    print(f"total slippage assumed %: {format_pct(overall['total_slippage_pct'])}")
    print(f"final equity: {overall['final_equity']:.4f}")
    print("")

    if stats:
        print("entry order breakdown:")
        print(f"  signals checked: {stats.get('entry_signals', 0)}")
        print(f"  filled entry orders: {stats.get('filled_entry_orders', 0)}")
        print(f"  unfilled entry orders: {stats.get('unfilled_entry_orders', 0)}")
        if args.daily_loss_stop_pct is not None and args.daily_loss_stop_pct > 0:
            print(f"  daily loss stop events: {stats.get('daily_loss_stop_events', 0)}")
            print(
                f"  skipped candles after daily stop: "
                f"{stats.get('daily_loss_stop_skipped_candles', 0)}"
            )
        if getattr(args, "weekly_loss_stop_pct", None) is not None and args.weekly_loss_stop_pct > 0:
            print(f"  weekly loss stop events: {stats.get('weekly_loss_stop_events', 0)}")
            print(
                f"  skipped candles after weekly stop: "
                f"{stats.get('weekly_loss_stop_skipped_candles', 0)}"
            )
        for direction in ("long", "short"):
            direction_signals = stats.get(f"{direction}_entry_signals", 0)
            if direction_signals:
                print(
                    f"  {direction}: {stats.get(f'{direction}_filled_entry_orders', 0)} filled / "
                    f"{stats.get(f'{direction}_unfilled_entry_orders', 0)} unfilled"
                )
        print("")

    if overall["exit_reasons"]:
        print("exit reasons breakdown:")
        for reason, count in overall["exit_reasons"].most_common():
            print(f"  {reason}: {count}")
    else:
        print("exit reasons breakdown: none")
    print("")

    print("metrics grouped by direction:")
    header = (
        "direction | trades | total pnl | return contrib % | win rate % | "
        "profit factor | max dd % | avg win % | avg loss % | expectancy %"
    )
    print(header)
    print("-" * len(header))
    for direction in ("long", "short"):
        summary = by_direction[direction]
        print(
            f"{direction} | "
            f"{summary['total_trades']} | "
            f"{summary['pnl']:.4f} | "
            f"{summary['return_contribution_pct']:.4f}% | "
            f"{summary['win_rate_pct']:.4f}% | "
            f"{format_pf(summary['profit_factor'])} | "
            f"{summary['max_drawdown_pct']:.4f}% | "
            f"{summary['avg_win_pct']:.4f}% | "
            f"{summary['avg_loss_pct']:.4f}% | "
            f"{summary['expectancy_pct']:.4f}%"
        )
    print("")
    print(f"saved candles: {args.save_candles}")
    print(f"saved trades: {args.save_trades}")
    print(f"saved equity: {args.save_equity}")


def main():
    args = parse_args()

    fetch_days = args.days + max(0, args.warmup_days)
    candles = fetch_klines(args.market, args.symbol, fetch_days, args.interval)
    if not candles:
        raise RuntimeError("No candles downloaded.")

    add_indicators_and_signals(candles, args)
    if args.warmup_days > 0:
        backtest_candle_count = args.days * candles_per_day(args.interval)
        candles = candles[-backtest_candle_count:]
    trades, equity_curve, stats = run_backtest(candles, args)

    candle_fields = [
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ema20",
        "ema50",
        "ema200",
        "rsi14",
        "atr14",
        "atr_pct",
        "volume_sma20",
        "recent_high20",
        "recent_low20",
        "dist_ema200",
        "return_1d",
        "return_7d",
        "body_ratio",
        "upper_wick_ratio",
        "lower_wick_ratio",
        "long_score",
        "short_score",
        "smart_long_filter",
        "regime_filter_passed",
        "long_signal",
        "short_signal",
    ]
    trade_fields = [
        "direction",
        "entry_mode",
        "signal_time",
        "order_start_time",
        "entry_time",
        "exit_time",
        "entry",
        "exit",
        "limit_price",
        "fill_delay_min",
        "reason",
        "gross_return_pct",
        "net_return_pct",
        "pnl",
        "duration_min",
        "equity_after",
    ]
    equity_fields = ["time", "equity"]

    save_csv(args.save_candles, candles, candle_fields)
    save_csv(args.save_trades, trades, trade_fields)
    save_csv(args.save_equity, equity_curve, equity_fields)

    print_summary(args, candles, trades, equity_curve, stats)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
