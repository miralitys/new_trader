#!/usr/bin/env python3
"""Stress the 36-month 5% cashflow high-risk candidate."""

import argparse
import csv
import hashlib
import importlib.util
import io
import math
import os
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHLY_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_search.py")
FUNDING_ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"

BASE_FEE_PCT = 0.0002
INITIAL_BALANCE = 1000.0

WEIGHTS = {"GALA": 0.40, "SPELL": 0.60}
SCALE = 6.0
MONTHLY_LOSS_STOP = 0.30
TARGET_BALANCE = 1050.0


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def month_iter_dt(start_month, end_month):
    year, month = [int(part) for part in start_month.split("-")]
    end_year, end_m = [int(part) for part in end_month.split("-")]
    while (year, month) <= (end_year, end_m):
        yield datetime(year, month, 1, tzinfo=timezone.utc)
        month += 1
        if month == 13:
            year += 1
            month = 1


def next_month(value):
    if value.month == 12:
        return datetime(value.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(value.year, value.month + 1, 1, tzinfo=timezone.utc)


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def embedded_exposure(trade):
    """Approximate exposure already embedded in raw_return_pct.

    SPELL best is a 100% short module. GALA 11.2 rows are already scaled by
    their own internal module exposure, so extra execution cost must be smaller
    than a full-notional cost.
    """
    if trade["coin"] == "SPELL":
        return 1.0
    if trade["coin"] == "GALA":
        if trade.get("direction") == "long":
            return 0.18
        return 0.36
    return 1.0


def deterministic_fraction(*parts):
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def funding_archive_url(symbol, month):
    month_text = f"{month.year:04d}-{month.month:02d}"
    return f"{FUNDING_ARCHIVE_BASE}/{symbol}/{symbol}-fundingRate-{month_text}.zip"


def fetch_funding_rates(symbol, start_month, end_month, cache_dir):
    cache_path = os.path.join(cache_dir, f"{symbol}_funding_{start_month}_{end_month}.csv")
    if os.path.exists(cache_path):
        rows = []
        with open(cache_path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "funding_time_ms": int(row["funding_time_ms"]),
                        "funding_time": row["funding_time"],
                        "funding_rate": float(row["funding_rate"]),
                    }
                )
        return rows

    rows = []
    for month in month_iter_dt(start_month, end_month):
        url = funding_archive_url(symbol, month)
        request = urllib.request.Request(url, headers={"User-Agent": "cashflow-stress/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
            if not csv_names:
                continue
            with archive.open(csv_names[0]) as handle:
                text = io.TextIOWrapper(handle, encoding="utf-8")
                reader = csv.DictReader(text)
                for item in reader:
                    funding_ms = int(item["calc_time"])
                    rows.append(
                        {
                            "funding_time_ms": funding_ms,
                            "funding_time": datetime.fromtimestamp(funding_ms / 1000, tz=timezone.utc).isoformat(),
                            "funding_rate": float(item["last_funding_rate"]),
                        }
                    )
        time.sleep(0.05)

    rows.sort(key=lambda row: row["funding_time_ms"])
    save_csv(cache_path, rows, ["funding_time_ms", "funding_time", "funding_rate"])
    return rows


def funding_adjustment_pct(trade, funding_by_symbol):
    symbol = trade["symbol"]
    if symbol not in funding_by_symbol:
        return 0.0, 0, 0.0
    entry_ms = int(parse_time(trade["entry_time"]).timestamp() * 1000)
    exit_ms = int(parse_time(trade["exit_time"]).timestamp() * 1000)
    rates = [
        row["funding_rate"]
        for row in funding_by_symbol[symbol]
        if entry_ms <= row["funding_time_ms"] <= exit_ms
    ]
    rate_sum = sum(rates)
    exposure = embedded_exposure(trade)
    if trade.get("direction") == "long":
        return -exposure * rate_sum * 100.0, len(rates), rate_sum
    return exposure * rate_sum * 100.0, len(rates), rate_sum


def stressed_trade(trade, scenario, funding_by_symbol):
    row = dict(trade)
    raw_return = float(row["raw_return_pct"])
    exposure = embedded_exposure(row)

    extra_fee = max(0.0, scenario["fee_pct"] - BASE_FEE_PCT)
    extra_cost_pct = exposure * 2.0 * (extra_fee + scenario["slippage_pct"]) * 100.0
    funding_pct = 0.0
    funding_events = 0
    funding_rate_sum = 0.0
    if scenario["include_funding"]:
        funding_pct, funding_events, funding_rate_sum = funding_adjustment_pct(row, funding_by_symbol)

    adjusted = raw_return - extra_cost_pct + funding_pct
    if scenario["skip_winner_pct"] > 0 and adjusted > 0:
        if deterministic_fraction(row["coin"], row["entry_time"], row["exit_time"], scenario["name"]) < scenario["skip_winner_pct"]:
            return None

    row["raw_return_pct"] = adjusted
    row["base_raw_return_pct"] = raw_return
    row["extra_execution_cost_pct"] = extra_cost_pct
    row["funding_return_pct"] = funding_pct
    row["funding_events"] = funding_events
    row["funding_rate_sum"] = funding_rate_sum
    return row


def load_selected_trades(path, start_month, end_month):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["coin"] not in WEIGHTS:
                continue
            month = row["exit_time"][:7]
            if start_month <= month <= end_month:
                row["month"] = month
                rows.append(row)
    rows.sort(key=lambda item: (item["exit_time"], item["entry_time"], item["coin"]))
    return rows


def run_scenario(monthly, base_trades, months, scenario, funding_by_symbol):
    adjusted = []
    skipped_for_fill = 0
    total_extra_cost = 0.0
    total_funding = 0.0
    total_funding_events = 0
    for trade in base_trades:
        item = stressed_trade(trade, scenario, funding_by_symbol)
        if item is None:
            skipped_for_fill += 1
            continue
        total_extra_cost += item["extra_execution_cost_pct"]
        total_funding += item["funding_return_pct"]
        total_funding_events += item["funding_events"]
        adjusted.append(item)

    rows_by_month_coin = monthly.index_trades_by_month_coin(adjusted)
    rows_by_month = monthly.candidate_rows_by_month(rows_by_month_coin, months, WEIGHTS)
    result = monthly.simulate(rows_by_month, months, WEIGHTS, MONTHLY_LOSS_STOP, TARGET_BALANCE, SCALE)
    summary = {
        "scenario": scenario["name"],
        "fee_pct": scenario["fee_pct"],
        "slippage_pct": scenario["slippage_pct"],
        "include_funding": scenario["include_funding"],
        "skip_winner_pct": scenario["skip_winner_pct"],
        "months": len(months),
        **{key: value for key, value in result.items() if key != "monthly"},
        "skipped_for_fill": skipped_for_fill,
        "input_trades_after_stress": len(adjusted),
        "sum_raw_extra_execution_cost_pct": total_extra_cost,
        "sum_raw_funding_return_pct": total_funding,
        "funding_events": total_funding_events,
    }
    monthly_rows = []
    for row in result["monthly"]:
        monthly_rows.append({"scenario": scenario["name"], **row})
    return summary, monthly_rows


def liquidation_summary():
    spell_exposure = WEIGHTS["SPELL"] * SCALE * 1.0
    gala_short_exposure = WEIGHTS["GALA"] * SCALE * 0.36
    gala_long_exposure = WEIGHTS["GALA"] * SCALE * 0.18
    maintenance = 0.005

    def distance(exposure):
        if exposure <= 0:
            return math.inf
        return max(0.0, (1.0 / exposure - maintenance) * 100.0)

    isolated_6x_distance = max(0.0, (1.0 / 6.0 - maintenance) * 100.0)
    return {
        "spell_effective_exposure_x": spell_exposure,
        "gala_short_effective_exposure_x": gala_short_exposure,
        "gala_long_effective_exposure_x": gala_long_exposure,
        "spell_cross_equivalent_liq_distance_pct": distance(spell_exposure),
        "gala_short_cross_equivalent_liq_distance_pct": distance(gala_short_exposure),
        "gala_long_cross_equivalent_liq_distance_pct": distance(gala_long_exposure),
        "isolated_6x_approx_liq_distance_pct": isolated_6x_distance,
    }


def write_report(path, summaries, monthly_rows, liq, summary_csv, monthly_csv):
    lines = [
        "# Monthly Cashflow 5% 36M Stress",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Strategy: `GALA 40% / SPELL 60%`, scale `6x`, monthly target `$50`, monthly loss stop `30%`.",
        "",
        "The base trade pool already includes maker fee `0.02%` per side and zero slippage. Stress scenarios subtract extra cost from the raw trade return before portfolio weights and scale are applied.",
        "",
        "## Stress Summary",
        "",
        "| Scenario | $50+ Months | Net | MaxDD | PF | Worst Month | Trades | Fill Skips | Funding |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['scenario']}` | {row['cash_hits']}/{row['months']} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | "
            f"{fmt_money(row['worst_month_pnl'])} | {row['trades']} | {row['skipped_for_fill']} | "
            f"{fmt_pct(row['sum_raw_funding_return_pct'])} |"
        )

    lines.extend(
        [
            "",
            "## Liquidation / Margin Approximation",
            "",
            "| Item | Value |",
            "|---|---:|",
            f"| SPELL effective exposure | `{liq['spell_effective_exposure_x']:.2f}x` |",
            f"| GALA short effective exposure | `{liq['gala_short_effective_exposure_x']:.2f}x` |",
            f"| GALA long effective exposure | `{liq['gala_long_effective_exposure_x']:.2f}x` |",
            f"| SPELL cross-equivalent liquidation distance | `{liq['spell_cross_equivalent_liq_distance_pct']:.2f}%` |",
            f"| Isolated 6x approximate liquidation distance | `{liq['isolated_6x_approx_liq_distance_pct']:.2f}%` |",
            "",
            "Interpretation: if this is traded as isolated `6x`, a roughly `16%` adverse move can become dangerous before stop execution. If traded cross with effective SPELL exposure around `3.6x`, the rough distance is wider, around `27%`, but the whole account is at risk.",
            "",
            "## Monthly For Base Scenario",
            "",
            "| Month | PnL | Withdrawal | Stop | Trades | Top Coins |",
            "|---|---:|---:|---|---:|---|",
        ]
    )
    for row in monthly_rows:
        if row["scenario"] != "base_fee002_slip0":
            continue
        lines.append(
            f"| {row['month']} | {fmt_money(row['month_pnl'])} | {fmt_money(row['withdrawal'])} | "
            f"{row['stop_reason']} | {row['trades']} | `{row['top_coins']}` |"
        )

    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{summary_csv}`",
            f"- Monthly CSV: `{monthly_csv}`",
            "",
        ]
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Stress high-risk 5% monthly cashflow strategy.")
    parser.add_argument("--trades-path", default="data/cashflow_portfolio_best_plus_rif_movr_interval_trades_35m.csv")
    parser.add_argument("--start-month", default="2023-05")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--save-summary", default=f"data/monthly_cashflow_5pct_36m_highrisk_stress_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/monthly_cashflow_5pct_36m_highrisk_stress_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/monthly-cashflow-5pct-36m-stress-{today}.md")
    args = parser.parse_args()

    monthly = load_module("monthly_cashflow_search", MONTHLY_PATH)
    months = list(monthly.month_iter(args.start_month, args.end_month))
    base_trades = load_selected_trades(os.path.join(ROOT, args.trades_path), args.start_month, args.end_month)

    funding_by_symbol = {}
    cache_dir = os.path.join(ROOT, "data", "funding_cache")
    for symbol in ("GALAUSDT", "SPELLUSDT"):
        funding_by_symbol[symbol] = fetch_funding_rates(symbol, args.start_month, args.end_month, cache_dir)

    scenarios = [
        {"name": "base_fee002_slip0", "fee_pct": 0.0002, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "base_plus_funding", "fee_pct": 0.0002, "slippage_pct": 0.0, "include_funding": True, "skip_winner_pct": 0.0},
        {"name": "fee0025_slip0", "fee_pct": 0.00025, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "fee003_slip0", "fee_pct": 0.0003, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "fee004_slip0", "fee_pct": 0.0004, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "fee004_slip0005", "fee_pct": 0.0004, "slippage_pct": 0.00005, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "fee004_slip001", "fee_pct": 0.0004, "slippage_pct": 0.0001, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "taker_like_fee004_slip002", "fee_pct": 0.0004, "slippage_pct": 0.0002, "include_funding": False, "skip_winner_pct": 0.0},
        {"name": "fee004_slip001_plus_funding", "fee_pct": 0.0004, "slippage_pct": 0.0001, "include_funding": True, "skip_winner_pct": 0.0},
        {"name": "miss_5pct_winners", "fee_pct": 0.0002, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.05},
        {"name": "miss_10pct_winners", "fee_pct": 0.0002, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.10},
        {"name": "miss_20pct_winners", "fee_pct": 0.0002, "slippage_pct": 0.0, "include_funding": False, "skip_winner_pct": 0.20},
    ]

    summaries = []
    all_monthly = []
    for scenario in scenarios:
        summary, scenario_monthly = run_scenario(monthly, base_trades, months, scenario, funding_by_symbol)
        summaries.append(summary)
        all_monthly.extend(scenario_monthly)

    summary_fields = [
        "scenario",
        "fee_pct",
        "slippage_pct",
        "include_funding",
        "skip_winner_pct",
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
        "skipped_for_fill",
        "input_trades_after_stress",
        "sum_raw_extra_execution_cost_pct",
        "sum_raw_funding_return_pct",
        "funding_events",
    ]
    monthly_fields = [
        "scenario",
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
        "top_coins",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), summaries, summary_fields)
    save_csv(os.path.join(ROOT, args.save_monthly), all_monthly, monthly_fields)
    liq = liquidation_summary()
    write_report(os.path.join(ROOT, args.save_report), summaries, all_monthly, liq, args.save_summary, args.save_monthly)

    print("scenario,cash_hits,net,dd,pf,worst,trades,fill_skips,funding")
    for row in summaries:
        print(
            f"{row['scenario']},{row['cash_hits']}/{row['months']},{row['net_result']:.2f},"
            f"{row['max_drawdown_pct']:.2f},{fmt_pf(row['profit_factor'])},{row['worst_month_pnl']:.2f},"
            f"{row['trades']},{row['skipped_for_fill']},{row['sum_raw_funding_return_pct']:.4f}"
        )
    print(f"saved summary: {args.save_summary}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
