#!/usr/bin/env python3
"""Daily PnL breakdown for the fixed strategy shortlist.

The output answers: "if this strategy was active each day, what did it make
that day from a fresh $1000 starting balance?"

This is a reporting script, not an optimizer. It uses fixed strategy definitions
from the existing project scripts and writes both a detailed CSV and a compact
Markdown matrix.
"""

import argparse
import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_PATH = os.path.join(ROOT, "scripts", "gala_mb_backtest.py")
REINVEST_PATH = os.path.join(ROOT, "scripts", "reinvest_winning_strategies.py")
MULTI_PATH = os.path.join(ROOT, "scripts", "multi_coin_gala_strategy_check.py")
CF_PATH = os.path.join(ROOT, "scripts", "cashflow_portfolio.py")
PAPER_PATH = os.path.join(ROOT, "scripts", "paper_execution_journal.py")
STRICT_PATH = os.path.join(ROOT, "scripts", "daily_strict_survivor_check.py")
CASHFLOW12_PATH = os.path.join(ROOT, "scripts", "monthly_cashflow_5pct_fresh_strict_check.py")
CASHFLOW3_PATH = os.path.join(ROOT, "scripts", "cashflow3_fresh_strict_check.py")
RIF_ADAPT_PATH = os.path.join(ROOT, "scripts", "rif_interval_adaptation_search.py")

INITIAL_BALANCE = 1000.0


DETAIL_FIELDS = [
    "day",
    "strategy",
    "group",
    "market",
    "source",
    "signals",
    "filled",
    "unfilled",
    "trades",
    "return_pct",
    "pnl_usd",
    "final_equity",
    "profit_factor",
    "win_rate_pct",
    "expectancy_pct",
    "exit_reasons",
    "note",
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
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def row_exit_time(row):
    return (
        parse_time(row.get("exit_time"))
        or parse_time(row.get("waited_until_time"))
        or parse_time(row.get("order_start_time"))
        or parse_time(row.get("signal_time"))
    )


def row_day(row):
    ts = row_exit_time(row)
    return ts.date().isoformat() if ts else ""


def accepted_rows(rows):
    return [
        row
        for row in rows
        if row.get("order_status") == "filled"
        and row.get("portfolio_status") in {"candidate", "accepted"}
    ]


def profit_factor(values):
    gross_win = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    if gross_loss:
        return gross_win / gross_loss
    return math.inf if gross_win else 0.0


def fmt_pct(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    if math.isinf(value):
        return "inf"
    return f"{value:+.2f}%"


def fmt_usd(value):
    if value in ("", None):
        return "n/a"
    return f"${float(value):+.2f}"


def fmt_num(value):
    if value in ("", None):
        return "n/a"
    value = float(value)
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def fixed_days_from_archive(multi, symbol, days, warmup_days):
    candles, _, _ = multi.fetch_klines_fast(symbol, days, warmup_days)
    tail = candles[-days * 1440 :]
    return sorted({row["open_time"][:10] for row in tail})


def summarize_trade_rows(rows, days, strategy, group, market, source, note="", transform=None, stop=None):
    transform = transform or (lambda row: float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0))
    by_day = defaultdict(list)
    all_attempts = defaultdict(list)
    for row in rows:
        day = row_day(row)
        if day:
            all_attempts[day].append(row)
        if row in accepted_rows([row]):
            by_day[day].append(row)

    output = []
    for day in days:
        attempts = all_attempts.get(day, [])
        accepted = sorted(by_day.get(day, []), key=lambda item: (row_exit_time(item), parse_time(item.get("fill_time")) or row_exit_time(item)))
        equity = INITIAL_BALANCE
        pnls = []
        returns = []
        reasons = Counter()
        stopped = False
        skipped_after_stop = 0

        for row in accepted:
            if stopped:
                skipped_after_stop += 1
                continue
            ret_pct = transform(row)
            before = equity
            equity *= 1.0 + ret_pct / 100.0
            pnl = equity - before
            pnls.append(pnl)
            returns.append(ret_pct)
            reasons[row.get("reason", "")] += 1
            if stop:
                target_cash = stop.get("target_cash")
                loss_stop_pct = stop.get("loss_stop_pct")
                if target_cash is not None and equity >= INITIAL_BALANCE + target_cash:
                    stopped = True
                if loss_stop_pct is not None and equity <= INITIAL_BALANCE * (1.0 - loss_stop_pct):
                    stopped = True

        wins = [pnl for pnl in pnls if pnl > 0]
        daily_note = note
        if skipped_after_stop:
            daily_note = f"{daily_note}; skipped_after_stop={skipped_after_stop}" if daily_note else f"skipped_after_stop={skipped_after_stop}"
        output.append(
            {
                "day": day,
                "strategy": strategy,
                "group": group,
                "market": market,
                "source": source,
                "signals": len(attempts),
                "filled": sum(1 for row in attempts if row.get("order_status") == "filled"),
                "unfilled": sum(1 for row in attempts if row.get("order_status") == "unfilled"),
                "trades": len(pnls),
                "return_pct": (equity / INITIAL_BALANCE - 1.0) * 100.0,
                "pnl_usd": equity - INITIAL_BALANCE,
                "final_equity": equity,
                "profit_factor": profit_factor(pnls),
                "win_rate_pct": len(wins) / len(pnls) * 100.0 if pnls else 0.0,
                "expectancy_pct": sum(returns) / len(returns) if returns else 0.0,
                "exit_reasons": ";".join(f"{key}={value}" for key, value in reasons.most_common() if key),
                "note": daily_note,
            }
        )
    return output


def enforce_max_trades_per_asset(rows, max_trades):
    if max_trades is None:
        return rows
    counts = Counter()
    output = []
    for row in sorted(rows, key=lambda item: (row_exit_time(item), parse_time(item.get("fill_time")) or row_exit_time(item), item.get("asset", ""))):
        if row.get("portfolio_status") not in {"candidate", "accepted"}:
            output.append(row)
            continue
        day = row_day(row)
        key = (row.get("asset"), day)
        if counts[key] >= max_trades:
            skipped = dict(row)
            skipped["portfolio_status"] = "skipped_max_trades_day"
            output.append(skipped)
            continue
        counts[key] += 1
        output.append(row)
    return output


def build_core_paper(bt, reinvest, multi, cf, paper, rif, days, warmup_days, market):
    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "limit_offset": 0.0005,
        "timeout_min": 1,
    }
    return {
        "ANKR LONG Best": paper.build_single_journal(bt, reinvest, multi, cf, "ANKRUSDT", "ANKR", "ANKR LONG Best", days, warmup_days, execution, market),
        "RIF Regime Monitor": paper.build_rif_journal(bt, reinvest, multi, cf, rif, days, warmup_days, execution, market),
        "GALA 7.3": paper.build_gala_template_journal(bt, reinvest, multi, "7.3", days, warmup_days, execution, market),
        "GALA 10": paper.build_gala_template_journal(bt, reinvest, multi, "10", days, warmup_days, execution, market),
        "GALA 11.2": paper.build_gala_112_journal(bt, reinvest, multi, days, warmup_days, execution, market),
        "SPELL SHORT Best": paper.build_single_journal(bt, reinvest, multi, cf, "SPELLUSDT", "SPELL", "SPELL SHORT Best", days, warmup_days, execution, market),
    }


def build_strict(strict, tweak, bt, reinvest, multi, cf, paper, days, warmup_days, market):
    output = {}
    for variant in strict.STRICT_SURVIVORS:
        candles = strict.fetch_candles(bt, reinvest, multi, tweak, variant["symbol"], days, warmup_days, market)
        rows = strict.run_variant(tweak, bt, reinvest, multi, cf, paper, candles, variant)
        output[variant["strategy"]] = rows
    return output


def build_cashflow12(cf12, paper, bt, reinvest, multi, cf, days, warmup_days, market, candidate_key):
    candidate = cf12.CANDIDATES[candidate_key]
    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "limit_offset": 0.0005,
        "timeout_min": 1,
    }
    return candidate, cf12.build_period_journal(paper, bt, reinvest, multi, cf, days, warmup_days, execution, market, candidate)


def build_cashflow3(cf3, paper, bt, reinvest, multi, cf, adapt, days, warmup_days, market):
    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "limit_offset": 0.0005,
        "timeout_min": 1,
    }
    rows = []
    rows.extend(cf3.build_one_112_journal(bt, reinvest, multi, paper, market, days, warmup_days, execution))
    rows.extend(cf3.build_rif_5m_journal(bt, reinvest, multi, paper, adapt, market, days, warmup_days, execution))
    rows.extend(cf3.build_spell_journal(bt, reinvest, multi, cf, paper, market, days, warmup_days, execution))
    return rows


def build_chz_mana_rif_spell(cf3, paper, bt, reinvest, multi, cf, adapt, days, warmup_days, market):
    execution = {
        "entry_mode": "maker_limit",
        "fee_pct": 0.0002,
        "slippage_pct": 0.0,
        "limit_offset": 0.0005,
        "timeout_min": 1,
    }
    rows = []
    rows.extend(paper.build_single_journal(bt, reinvest, multi, cf, "CHZUSDT", "CHZ", "CHZ LONG Best", days, warmup_days, execution, market))
    rows.extend(paper.build_single_journal(bt, reinvest, multi, cf, "MANAUSDT", "MANA", "MANA LONG Best", days, warmup_days, execution, market))
    rows.extend(cf3.build_rif_5m_journal(bt, reinvest, multi, paper, adapt, market, days, warmup_days, execution))
    rows.extend(paper.build_single_journal(bt, reinvest, multi, cf, "SPELLUSDT", "SPELL", "SPELL SHORT Best", days, warmup_days, execution, market))
    return rows


def cashflow_transform(weights, scale):
    return lambda row: float(row.get("portfolio_return_pct") or row.get("net_return_pct") or 0.0) * weights.get(row["asset"], 0.0) * scale


def write_report(path, rows, days, generated_at, csv_path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    days_count = len(days)
    by_strategy = defaultdict(dict)
    totals = {}
    for row in rows:
        by_strategy[row["strategy"]][row["day"]] = row
    for strategy, day_map in by_strategy.items():
        totals[strategy] = sum(float(day_map.get(day, {}).get("pnl_usd") or 0.0) for day in days)

    lines = [
        f"# Daily Strategy {days_count}d PnL",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Каждый день считается отдельно от стартовых `$1000`. Значение в ячейке: `return / $PnL / trades`.",
        f"Основной источник: Binance Futures archive, последние {days_count} полных UTC-дней.",
        "",
        "| Strategy | " + " | ".join(days) + " | Итого |",
        "|---|" + "|".join("---:" for _ in days) + "|---:|",
    ]
    order = [
        "ANKR LONG Best",
        "RIF Regime Monitor",
        "GALA 7.3",
        "GALA 10",
        "GALA 11.2",
        "SPELL SHORT Best",
        "CHZ LONG strict",
        "ANKR LONG strict",
        "GALA 7.3 strict",
        "GALA 11.2 strict",
        "GALA20/SPELL80",
        "CHZ10/SHIB10/SPELL80",
        "ONE/RIF/SPELL",
        "ONE/RIF/SPELL max50",
        "ONE/RIF/SPELL max100",
        "CHZ/MANA/RIF/SPELL 4%",
    ]
    for strategy in order:
        day_map = by_strategy.get(strategy, {})
        cells = []
        for day in days:
            row = day_map.get(day)
            if not row:
                cells.append("n/a")
            else:
                cells.append(f"{fmt_pct(row['return_pct'])} / {fmt_usd(row['pnl_usd'])} / {row['trades']}")
        lines.append(f"| {strategy} | " + " | ".join(cells) + f" | {fmt_usd(totals.get(strategy, 0.0))} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `$PnL` считается от `$1000` на начало каждого дня, не как единый недельный compounding.",
            "- `max50/max100` рассчитаны на свежем ONE/RIF/SPELL trade-set с дневным лимитом сделок на монету.",
            "- `CHZ/MANA/RIF/SPELL 4%` рассчитана как свежая дневная версия: CHZ/MANA/RIF/SPELL, scale 8, daily loss stop 5%, max 50 сделок на монету в день.",
            f"- Detail CSV: `{csv_path}`",
        ]
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description="Build daily PnL table for fixed strategies over the last N complete archive days.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--market", default="futures_archive", choices=["futures_archive"])
    parser.add_argument("--save", default=f"data/daily_strategy_7d_pnl_{today}.csv")
    parser.add_argument("--save-report", default=f"strategies/daily-strategy-7d-pnl-{today}.md")
    args = parser.parse_args()

    bt = load_module("gala_mb_backtest", BT_PATH)
    reinvest = load_module("reinvest_winning_strategies", REINVEST_PATH)
    multi = load_module("multi_coin_gala_strategy_check", MULTI_PATH)
    cf = load_module("cashflow_portfolio", CF_PATH)
    paper = load_module("paper_execution_journal", PAPER_PATH)
    rif = load_module("rif_regime_monitor", os.path.join(ROOT, "scripts", "rif_regime_monitor.py"))
    strict = load_module("daily_strict_survivor_check", STRICT_PATH)
    tweak = load_module("shortlist_24h_tweak_search", os.path.join(ROOT, "scripts", "shortlist_24h_tweak_search.py"))
    cf12 = load_module("monthly_cashflow_5pct_fresh_strict_check", CASHFLOW12_PATH)
    cf3 = load_module("cashflow3_fresh_strict_check", CASHFLOW3_PATH)
    adapt = load_module("rif_interval_adaptation_search", RIF_ADAPT_PATH)

    days = fixed_days_from_archive(multi, "GALAUSDT", args.days, args.warmup_days)
    rows = []

    core = build_core_paper(bt, reinvest, multi, cf, paper, rif, args.days, args.warmup_days, args.market)
    for strategy, journal_rows in core.items():
        rows.extend(
            summarize_trade_rows(
                journal_rows,
                days,
                strategy,
                "core_paper",
                args.market,
                "maker-limit paper execution",
            )
        )

    strict_rows = build_strict(strict, tweak, bt, reinvest, multi, cf, paper, args.days, args.warmup_days, args.market)
    for strategy, journal_rows in strict_rows.items():
        rows.extend(
            summarize_trade_rows(
                journal_rows,
                days,
                strategy,
                "strict",
                args.market,
                "fixed strict maker-limit variant",
            )
        )

    candidate1, cf1_rows = build_cashflow12(cf12, paper, bt, reinvest, multi, cf, args.days, args.warmup_days, args.market, "gala20_spell80")
    rows.extend(
        summarize_trade_rows(
            cf1_rows,
            days,
            "GALA20/SPELL80",
            "cashflow",
            args.market,
            "fresh maker-limit portfolio",
            transform=cashflow_transform(candidate1["weights"], candidate1["scale"]),
            stop={"target_cash": 50.0, "loss_stop_pct": candidate1["loss_stop_pct"]},
        )
    )

    candidate2, cf2_rows = build_cashflow12(cf12, paper, bt, reinvest, multi, cf, args.days, args.warmup_days, args.market, "chz10_shib10_spell80")
    rows.extend(
        summarize_trade_rows(
            cf2_rows,
            days,
            "CHZ10/SHIB10/SPELL80",
            "cashflow",
            args.market,
            "fresh maker-limit portfolio",
            transform=cashflow_transform(candidate2["weights"], candidate2["scale"]),
            stop={"target_cash": 50.0, "loss_stop_pct": candidate2["loss_stop_pct"]},
        )
    )

    cf3_rows = build_cashflow3(cf3, paper, bt, reinvest, multi, cf, adapt, args.days, args.warmup_days, args.market)
    rows.extend(
        summarize_trade_rows(
            cf3_rows,
            days,
            "ONE/RIF/SPELL",
            "cashflow",
            args.market,
            "fresh maker-limit portfolio",
            transform=cashflow_transform({"ONE": 0.12, "RIF": 0.12, "SPELL": 0.75}, 5.5),
            stop={"target_cash": 100.0, "loss_stop_pct": 0.35},
        )
    )
    for label, max_trades in [("ONE/RIF/SPELL max50", 50), ("ONE/RIF/SPELL max100", 100)]:
        capped = enforce_max_trades_per_asset(cf3_rows, max_trades)
        rows.extend(
            summarize_trade_rows(
                capped,
                days,
                label,
                "post_only_fresh",
                args.market,
                "fresh approximation of post-only v2",
                transform=cashflow_transform({"ONE": 0.10, "RIF": 0.10, "SPELL": 0.80}, 10.0),
                stop={"target_cash": 100.0, "loss_stop_pct": 0.50},
            )
        )

    cmrs_rows = build_chz_mana_rif_spell(cf3, paper, bt, reinvest, multi, cf, adapt, args.days, args.warmup_days, args.market)
    cmrs_rows = enforce_max_trades_per_asset(cmrs_rows, 50)
    rows.extend(
        summarize_trade_rows(
            cmrs_rows,
            days,
            "CHZ/MANA/RIF/SPELL 4%",
            "post_only_fresh",
            args.market,
            "fresh approximation of exact-best post-only portfolio",
            transform=cashflow_transform({"CHZ": 0.10, "MANA": 0.10, "RIF": 0.20, "SPELL": 0.60}, 8.0),
            stop={"target_cash": 40.0, "loss_stop_pct": 0.05},
        )
    )

    save_csv(os.path.join(ROOT, args.save), rows, DETAIL_FIELDS)
    write_report(os.path.join(ROOT, args.save_report), rows, days, datetime.now(timezone.utc).isoformat(), args.save)
    print(f"saved detail: {args.save}")
    print(f"saved report: {args.save_report}")


if __name__ == "__main__":
    main()
