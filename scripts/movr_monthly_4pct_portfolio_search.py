#!/usr/bin/env python3
"""Search a 4% monthly cashflow portfolio around MOVR monthly-protected."""

import argparse
import csv
import importlib.util
import itertools
import math
import os
from collections import Counter, defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
INTERVAL_PATH = os.path.join(ROOT, "scripts", "rif_interval_windows_check.py")
ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")
MONTHLY_PATH = os.path.join(ROOT, "scripts", "rif_movr_monthly_positive_search.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")

INITIAL_BALANCE = 1000.0

MOVR_VARIANT = {
    "direction": "long",
    "threshold": 60,
    "regime": "base",
    "volume_multiplier": 1.5,
    "atr_min_pct": 0.0015,
    "atr_max_pct": 0.050,
    "tp_pct": 0.020,
    "sl_pct": 0.050,
    "time_stop_min": 1440,
    "weekly_loss_stop_pct": 0.02,
    "monthly_profit_target_pct": 0.01,
    "monthly_loss_stop_pct": 0.02,
}


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


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value):
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.2f}%"


def fmt_money(value):
    return f"${float(value):.2f}"


def fmt_pf(value):
    value = float(value)
    return "inf" if math.isinf(value) else f"{value:.2f}"


def day_start_ms(day):
    return int(datetime.combine(day, dt_time.min, tzinfo=timezone.utc).timestamp() * 1000)


def day_end_ms(day):
    return int(datetime.combine(day, dt_time.max, tzinfo=timezone.utc).timestamp() * 1000)


def load_existing_best_trades(path, start_month, end_month, coins):
    rows = []
    selected = set(coins)
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            month = row["exit_time"][:7]
            if month < start_month or month > end_month:
                continue
            if row["coin"] not in selected:
                continue
            rows.append(
                {
                    "coin": row["coin"],
                    "symbol": row["symbol"],
                    "strategy": row["strategy"],
                    "entry_time": row["entry_time"],
                    "exit_time": row["exit_time"],
                    "entry_dt": parse_time(row["entry_time"]),
                    "exit_dt": parse_time(row["exit_time"]),
                    "reason": row["reason"],
                    "raw_return_pct": float(row["raw_return_pct"]),
                }
            )
    return rows


def build_movr_trades(bt, interval_mod, adapt, monthly, reinvest, multi, archive_end_day, days, warmup_days):
    end_day = date.fromisoformat(archive_end_day)
    start_day = end_day - timedelta(days=days - 1)
    candles, _, _ = interval_mod.fetch_archive_klines("MOVRUSDT", "1h", days + warmup_days, archive_end_day)
    indicator_args = multi.make_strategy_args(reinvest, "10", "MOVRUSDT")
    indicator_args.interval = "1h"
    indicator_args.atr_max_pct = 0.050
    bt.add_indicators_and_signals(candles, indicator_args)
    rows = [dict(row) for row in candles if day_start_ms(start_day) <= row["open_time_ms"] <= day_end_ms(end_day)]
    adapt.apply_variant_signals(rows, MOVR_VARIANT)
    args = adapt.make_args(multi, reinvest, MOVR_VARIANT, "MOVRUSDT", "1h")
    args.initial_balance = INITIAL_BALANCE
    trades, _, _ = monthly.run_backtest_month_controls(bt, rows, args, MOVR_VARIANT)
    output = []
    for trade in trades:
        output.append(
            {
                "coin": "MOVR",
                "symbol": "MOVRUSDT",
                "strategy": "MOVR 1h Monthly Protected",
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "entry_dt": parse_time(trade["entry_time"]),
                "exit_dt": parse_time(trade["exit_time"]),
                "reason": trade["reason"],
                "raw_return_pct": float(trade["net_return_pct"]),
            }
        )
    return output


def candidate_weights(coins):
    coins = sorted(set(coins))
    candidates = {}
    for coin in coins:
        candidates[f"{coin}_100"] = {coin: 1.0}

    # MOVR must stay in the portfolio because the task starts from MOVR.
    others = [coin for coin in coins if coin != "MOVR"]
    for other in others:
        for movr_w in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            candidates[f"MOVR{int(movr_w*100)}_{other}{int((1-movr_w)*100)}"] = {
                "MOVR": movr_w,
                other: 1.0 - movr_w,
            }

    for a, b in itertools.combinations(others, 2):
        for movr_w in (0.2, 0.3, 0.4, 0.5, 0.6):
            rest = 1.0 - movr_w
            for split in (0.25, 0.5, 0.75):
                weights = {"MOVR": movr_w, a: rest * split, b: rest * (1.0 - split)}
                name = f"MOVR{int(movr_w*100)}_{a}{int(rest*split*100)}_{b}{int(rest*(1-split)*100)}"
                candidates[name] = weights

    presets = {
        "MOVR40_SPELL40_GALA20": {"MOVR": 0.4, "SPELL": 0.4, "GALA": 0.2},
        "MOVR30_SPELL50_GALA20": {"MOVR": 0.3, "SPELL": 0.5, "GALA": 0.2},
        "MOVR30_SPELL40_CHZ30": {"MOVR": 0.3, "SPELL": 0.4, "CHZ": 0.3},
        "MOVR30_SPELL40_ANKR30": {"MOVR": 0.3, "SPELL": 0.4, "ANKR": 0.3},
        "MOVR20_SPELL60_GALA20": {"MOVR": 0.2, "SPELL": 0.6, "GALA": 0.2},
    }
    for name, weights in presets.items():
        if all(coin in coins for coin in weights):
            candidates[name] = weights
    return candidates


def format_weights(weights):
    return ";".join(f"{coin}:{weight:.2f}" for coin, weight in sorted(weights.items()))


def profit_factor(pnls):
    wins = sum(value for value in pnls if value > 0)
    losses = abs(sum(value for value in pnls if value < 0))
    if losses == 0:
        return math.inf if wins > 0 else 0.0
    return wins / losses


def max_drawdown(points):
    peak = points[0] if points else INITIAL_BALANCE
    max_dd = 0.0
    for point in points:
        peak = max(peak, point)
        if peak:
            max_dd = max(max_dd, (peak - point) / peak * 100.0)
    return max_dd


def simulate(trades, months, weights, scale, target_pct, loss_stop_pct):
    selected = set(weights)
    by_month = defaultdict(list)
    for trade in trades:
        if trade["coin"] in selected:
            by_month[trade["exit_time"][:7]].append(trade)

    equity = INITIAL_BALANCE
    cash_withdrawn = 0.0
    equity_points = [equity]
    all_pnls = []
    monthly = []
    skipped = 0
    taken = 0

    for month in months:
        month_trades = sorted(by_month.get(month, []), key=lambda item: (item["exit_dt"], item["entry_dt"], item["coin"]))
        start_equity = equity
        target_balance = start_equity * (1.0 + target_pct)
        loss_floor = start_equity * (1.0 - loss_stop_pct) if loss_stop_pct is not None else -math.inf
        stop_time = None
        stop_reason = "month_end"
        month_pnls = []
        reasons = Counter()
        coins = Counter()

        for trade in month_trades:
            if stop_time is not None and trade["entry_dt"] >= stop_time:
                skipped += 1
                continue
            before = equity
            ret = (trade["raw_return_pct"] / 100.0) * weights[trade["coin"]] * scale
            equity *= 1.0 + ret
            pnl = equity - before
            month_pnls.append(pnl)
            all_pnls.append(pnl)
            equity_points.append(equity)
            taken += 1
            reasons[trade["reason"]] += 1
            coins[trade["coin"]] += 1
            if equity >= target_balance:
                stop_time = trade["exit_dt"]
                stop_reason = "profit_target"
            elif equity <= loss_floor:
                stop_time = trade["exit_dt"]
                stop_reason = "loss_stop"

        end_before_withdraw = equity
        month_pnl = end_before_withdraw - start_equity
        withdrawal = 0.0
        if equity > INITIAL_BALANCE:
            withdrawal = equity - INITIAL_BALANCE
            cash_withdrawn += withdrawal
            equity = INITIAL_BALANCE
            equity_points.append(equity)

        monthly.append(
            {
                "month": month,
                "start_balance": start_equity,
                "month_pnl": month_pnl,
                "month_return_pct": month_pnl / start_equity * 100.0 if start_equity else 0.0,
                "withdrawal": withdrawal,
                "end_before_withdraw": end_before_withdraw,
                "end_after_withdraw": equity,
                "stop_reason": stop_reason,
                "trades": len(month_pnls),
                "skipped_trades": max(0, len(month_trades) - len(month_pnls)),
                "win_rate_pct": sum(1 for pnl in month_pnls if pnl > 0) / len(month_pnls) * 100.0 if month_pnls else 0.0,
                "profit_factor": profit_factor(month_pnls),
                "take_profit": reasons["take_profit"],
                "time_stop": reasons["time_stop"],
                "stop_loss": reasons["stop_loss"],
                "top_coins": repr(coins.most_common(5)),
            }
        )

    cash_target = INITIAL_BALANCE * target_pct
    return {
        "weights": format_weights(weights),
        "scale": scale,
        "target_pct": target_pct,
        "loss_stop_pct": loss_stop_pct,
        "months": len(months),
        "cash_hits": sum(1 for row in monthly if row["withdrawal"] >= cash_target),
        "withdrawal_months": sum(1 for row in monthly if row["withdrawal"] > 0),
        "positive_months": sum(1 for row in monthly if row["month_pnl"] > 0),
        "negative_months": sum(1 for row in monthly if row["month_pnl"] < 0),
        "zero_months": sum(1 for row in monthly if abs(row["month_pnl"]) < 1e-9),
        "cash_withdrawn": cash_withdrawn,
        "final_balance": equity,
        "net_result": cash_withdrawn + equity - INITIAL_BALANCE,
        "net_result_pct": (cash_withdrawn + equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100.0,
        "max_drawdown_pct": max_drawdown(equity_points),
        "profit_factor": profit_factor(all_pnls),
        "win_rate_pct": sum(1 for pnl in all_pnls if pnl > 0) / len(all_pnls) * 100.0 if all_pnls else 0.0,
        "worst_month_pnl": min((row["month_pnl"] for row in monthly), default=0.0),
        "best_month_pnl": max((row["month_pnl"] for row in monthly), default=0.0),
        "trades": taken,
        "skipped_trades": skipped,
        "monthly": monthly,
    }


def write_report(path, results, monthly_rows, summary_path, monthly_path):
    lines = [
        "# MOVR 4% Monthly Portfolio Search",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Цель: собрать портфель вокруг `MOVR 1h LONG Monthly Protected`, который ближе всего подходит к cashflow-цели `$40+` в месяц от стартовых `$1000`.",
        "",
        "Важно: это research/in-sample поиск по последним полным месяцам `2025-06` - `2026-04`. Неполные майские куски не используются для критерия 4%.",
        "",
        "| Rank | Weights | Scale | Hits $40+ | Positive | Negative | Net | MaxDD | PF | Worst month | Trades |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(results[:20], start=1):
        lines.append(
            f"| {index} | `{row['weights']}` | {row['scale']:.2f} | {row['cash_hits']}/{row['months']} | "
            f"{row['positive_months']}/{row['months']} | {row['negative_months']} | {fmt_money(row['net_result'])} | "
            f"{fmt_pct(row['max_drawdown_pct'])} | {fmt_pf(row['profit_factor'])} | {fmt_money(row['worst_month_pnl'])} | {row['trades']} |"
        )

    if results:
        best = results[0]
        lines.extend(
            [
                "",
                "## Best Monthly Detail",
                "",
                f"Weights: `{best['weights']}`",
                f"Scale: `{best['scale']:.2f}`",
                "",
                "| Month | PnL | Return | Withdrawal | End balance | Stop | Trades | Top coins |",
                "|---|---:|---:|---:|---:|---|---:|---|",
            ]
        )
        for row in monthly_rows:
            if row["rank"] != 1:
                continue
            lines.append(
                f"| {row['month']} | {fmt_money(row['month_pnl'])} | {fmt_pct(row['month_return_pct'])} | "
                f"{fmt_money(row['withdrawal'])} | {fmt_money(row['end_after_withdraw'])} | "
                f"{row['stop_reason']} | {row['trades']} | `{row['top_coins']}` |"
            )
    lines.extend(["", "## Files", "", f"- Summary CSV: `{summary_path}`", f"- Monthly CSV: `{monthly_path}`", ""])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Search MOVR-centered 4% monthly cashflow portfolios.")
    parser.add_argument("--archive-end-day", default="2026-05-03")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--start-month", default="2025-06")
    parser.add_argument("--end-month", default="2026-04")
    parser.add_argument("--best-trades", default="data/cashflow_portfolio_best_trades_24m.csv")
    parser.add_argument("--coins", nargs="*", default=["GALA", "CHZ", "ANKR", "MANA", "SPELL", "JASMY", "SHIB"])
    parser.add_argument("--save-summary", default=f"data/movr_monthly_4pct_portfolio_summary_{today}.csv")
    parser.add_argument("--save-monthly", default=f"data/movr_monthly_4pct_portfolio_monthly_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/movr-monthly-4pct-portfolio-search-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    interval_mod = load_module("rif_interval_windows_check", INTERVAL_PATH)
    adapt = load_module("rif_interval_adaptation_search", ADAPT_PATH)
    monthly = load_module("rif_movr_monthly_positive_search", MONTHLY_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)

    months = list(month_iter(args.start_month, args.end_month))
    trades = load_existing_best_trades(os.path.join(ROOT, args.best_trades), args.start_month, args.end_month, args.coins)
    trades.extend(build_movr_trades(bt, interval_mod, adapt, monthly, reinvest, multi, args.archive_end_day, args.days, args.warmup_days))
    trades = [trade for trade in trades if args.start_month <= trade["exit_time"][:7] <= args.end_month]

    coins = sorted({trade["coin"] for trade in trades})
    weight_sets = candidate_weights(coins)
    results = []
    for name, weights in weight_sets.items():
        if "MOVR" not in weights:
            continue
        for scale in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0):
            for loss_stop in (0.02, 0.03, 0.04, 0.06):
                row = simulate(trades, months, weights, scale, 0.04, loss_stop)
                row["portfolio"] = name
                results.append(row)
    results.sort(
        key=lambda row: (
            row["cash_hits"],
            row["positive_months"],
            -row["negative_months"],
            row["net_result"],
            -row["max_drawdown_pct"],
        ),
        reverse=True,
    )

    summary_fields = [
        "portfolio",
        "weights",
        "scale",
        "target_pct",
        "loss_stop_pct",
        "months",
        "cash_hits",
        "withdrawal_months",
        "positive_months",
        "negative_months",
        "zero_months",
        "cash_withdrawn",
        "final_balance",
        "net_result",
        "net_result_pct",
        "max_drawdown_pct",
        "profit_factor",
        "win_rate_pct",
        "worst_month_pnl",
        "best_month_pnl",
        "trades",
        "skipped_trades",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), results, summary_fields)

    monthly_rows = []
    for rank, result in enumerate(results[:20], start=1):
        for month_row in result["monthly"]:
            item = dict(month_row)
            item.update(
                {
                    "rank": rank,
                    "portfolio": result["portfolio"],
                    "weights": result["weights"],
                    "scale": result["scale"],
                    "loss_stop_pct": result["loss_stop_pct"],
                }
            )
            monthly_rows.append(item)
    monthly_fields = [
        "rank",
        "portfolio",
        "weights",
        "scale",
        "loss_stop_pct",
        "month",
        "start_balance",
        "month_pnl",
        "month_return_pct",
        "withdrawal",
        "end_before_withdraw",
        "end_after_withdraw",
        "stop_reason",
        "trades",
        "skipped_trades",
        "win_rate_pct",
        "profit_factor",
        "take_profit",
        "time_stop",
        "stop_loss",
        "top_coins",
    ]
    save_csv(os.path.join(ROOT, args.save_monthly), monthly_rows, monthly_fields)
    write_report(os.path.join(ROOT, args.save_report), results, monthly_rows, args.save_summary, args.save_monthly)

    print(f"saved summary: {args.save_summary}")
    print(f"saved monthly: {args.save_monthly}")
    print(f"saved report: {args.save_report}")
    for row in results[:10]:
        print(
            f"{row['weights']} scale={row['scale']:.2f} hits={row['cash_hits']}/{row['months']} "
            f"pos={row['positive_months']} neg={row['negative_months']} net={row['net_result']:.2f} "
            f"dd={row['max_drawdown_pct']:.2f} pf={fmt_pf(row['profit_factor'])}"
        )


if __name__ == "__main__":
    main()
