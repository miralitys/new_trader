#!/usr/bin/env python3
"""Policy check for wave-monitor candidates.

Uses event-level forward returns from wave_after_hot_backtest.py and compares:

- taking every hot event;
- pausing a symbol after a losing activation;
- pausing after a losing or high-DD activation.
"""

import argparse
import csv
import math
import os
from collections import defaultdict
from datetime import date, timedelta


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SYMBOLS = ["GUAUSDT", "IRYSUSDT", "B2USDT", "MEGAUSDT", "RAVEUSDT", "RIFUSDT"]


POLICIES = [
    {"policy": "all_events", "pause_days": 0, "loss_trigger": False, "dd_trigger": None},
    {"policy": "pause_14d_after_loss", "pause_days": 14, "loss_trigger": True, "dd_trigger": None},
    {"policy": "pause_30d_after_loss_or_dd15", "pause_days": 30, "loss_trigger": True, "dd_trigger": 15.0},
    {"policy": "pause_30d_after_loss_or_dd10", "pause_days": 30, "loss_trigger": True, "dd_trigger": 10.0},
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row, key, default=None):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_day(text):
    return date.fromisoformat(text[:10])


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value):
    if value is None:
        return "n/a"
    if math.isinf(float(value)):
        return "inf"
    return f"{float(value):.2f}"


def summarize_activation_returns(returns):
    if not returns:
        return {
            "compounded_return_pct": None,
            "activation_win_rate_pct": None,
            "avg_activation_return_pct": None,
            "worst_activation_return_pct": None,
            "sequence_max_dd_pct": None,
        }
    equity = 1000.0
    peak = equity
    max_dd = 0.0
    for ret in returns:
        equity *= 1.0 + ret / 100.0
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return {
        "compounded_return_pct": (equity / 1000.0 - 1.0) * 100.0,
        "activation_win_rate_pct": sum(1 for ret in returns if ret > 0) / len(returns) * 100.0,
        "avg_activation_return_pct": sum(returns) / len(returns),
        "worst_activation_return_pct": min(returns),
        "sequence_max_dd_pct": max_dd,
    }


def run_policy(events, policy):
    taken = []
    skipped = 0
    pause_until = None
    for event in sorted(events, key=lambda row: row["event_time"]):
        event_day = parse_day(event["event_time"])
        if pause_until is not None and event_day < pause_until:
            skipped += 1
            continue
        ret = as_float(event, "return_pct")
        dd = as_float(event, "max_dd_pct", 0.0)
        if ret is None:
            continue
        taken.append(event)
        bad_loss = policy["loss_trigger"] and ret < 0
        bad_dd = policy["dd_trigger"] is not None and dd is not None and dd > policy["dd_trigger"]
        if policy["pause_days"] and (bad_loss or bad_dd):
            pause_until = event_day + timedelta(days=policy["pause_days"])
    returns = [as_float(row, "return_pct") for row in taken if as_float(row, "return_pct") is not None]
    dds = [as_float(row, "max_dd_pct") for row in taken if as_float(row, "max_dd_pct") is not None]
    summary = summarize_activation_returns(returns)
    summary.update(
        {
            "taken_events": len(taken),
            "skipped_events": skipped,
            "avg_event_dd_pct": sum(dds) / len(dds) if dds else None,
            "worst_event_dd_pct": max(dds) if dds else None,
        }
    )
    return summary


def save_report(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ranked = sorted(
        rows,
        key=lambda row: (
            row["scenario"] == "strict_maker",
            int(row["forward_days"]) == 14,
            row["policy"] == "pause_14d_after_loss",
            as_float(row, "compounded_return_pct", -999.0),
        ),
        reverse=True,
    )
    lines = [
        "# Wave Monitor Policy Check",
        "",
        "Проверка сравнивает несколько правил управления wave-включениями.",
        "",
        "- `all_events`: брать каждое hot-событие.",
        "- `pause_14d_after_loss`: если включение закрылось в минус, не брать новые события по этой монете 14 дней.",
        "- `pause_30d_after_loss_or_dd15`: пауза 30 дней после минуса или event DD больше 15%.",
        "- `pause_30d_after_loss_or_dd10`: более жесткая версия с DD больше 10%.",
        "",
        "## Main Table",
        "",
        "| Symbol | Scenario | Forward | Policy | Taken/Skipped | Compounded | Avg Event | Win | Seq DD | Worst Event | Event DD Avg/Worst |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ranked:
        if row["scenario"] != "strict_maker" or int(row["forward_days"]) not in (7, 14, 30):
            continue
        lines.append(
            f"| `{row['symbol']}` | {row['scenario']} | {row['forward_days']} | {row['policy']} | "
            f"{row['taken_events']}/{row['skipped_events']} | {fmt_pct(row['compounded_return_pct'])} | "
            f"{fmt_pct(row['avg_activation_return_pct'])} | {fmt_num(row['activation_win_rate_pct'])}% | "
            f"{fmt_num(row['sequence_max_dd_pct'])}% | {fmt_pct(row['worst_activation_return_pct'])} | "
            f"{fmt_num(row['avg_event_dd_pct'])}% / {fmt_num(row['worst_event_dd_pct'])}% |"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Check wave monitor policies.")
    parser.add_argument("--events", default="data/wave_after_hot_events_2026-05-04.csv")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--save-summary", default="data/wave_monitor_policy_check_2026-05-04.csv")
    parser.add_argument("--save-report", default="strategies/wave-monitor-policy-check-2026-05-04.md")
    args = parser.parse_args()

    events = read_csv(os.path.join(ROOT, args.events))
    selected = set(args.symbols)
    grouped = defaultdict(list)
    for row in events:
        if row["symbol"] not in selected:
            continue
        if str(row.get("valid")) != "True":
            continue
        grouped[(row["symbol"], row["scenario"], int(row["forward_days"]))].append(row)

    output = []
    for (symbol, scenario, forward_days), group in grouped.items():
        for policy in POLICIES:
            result = run_policy(group, policy)
            output.append(
                {
                    "symbol": symbol,
                    "scenario": scenario,
                    "forward_days": forward_days,
                    "policy": policy["policy"],
                    **result,
                }
            )

    fields = [
        "symbol",
        "scenario",
        "forward_days",
        "policy",
        "taken_events",
        "skipped_events",
        "compounded_return_pct",
        "activation_win_rate_pct",
        "avg_activation_return_pct",
        "worst_activation_return_pct",
        "sequence_max_dd_pct",
        "avg_event_dd_pct",
        "worst_event_dd_pct",
    ]
    save_csv(os.path.join(ROOT, args.save_summary), output, fields)
    save_report(os.path.join(ROOT, args.save_report), output)
    print(f"saved summary: {os.path.join(ROOT, args.save_summary)}")
    print(f"saved report: {os.path.join(ROOT, args.save_report)}")


if __name__ == "__main__":
    main()
