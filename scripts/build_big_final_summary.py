#!/usr/bin/env python3
"""Build the final human-readable report for the big research pass."""

import argparse
import csv
import math
import os
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_csv(path):
    full_path = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(full_path):
        return []
    with open(full_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    if value == "inf":
        return math.inf
    try:
        return float(value)
    except ValueError:
        return default


def fmt_pct(value, digits=2):
    parsed = parse_float(value)
    if parsed == math.inf:
        return "inf"
    return f"{parsed:+.{digits}f}%"


def fmt_pos_pct(value, digits=2):
    parsed = parse_float(value)
    if parsed == math.inf:
        return "inf"
    return f"{parsed:.{digits}f}%"


def fmt_pf(value):
    parsed = parse_float(value)
    if parsed == math.inf:
        return "inf"
    return f"{parsed:.2f}"


def fmt_money(value):
    return f"${parse_float(value):.2f}"


def fmt_setup(row, prefix=""):
    direction = row.get(prefix + "direction", row.get("best_direction", ""))
    threshold = row.get(prefix + "threshold", row.get("best_threshold", ""))
    regime = row.get(prefix + "regime", row.get("best_regime", ""))
    tp = row.get(prefix + "tp_pct", row.get("best_tp_pct", 0.0))
    time_stop = row.get(prefix + "time_stop_min", row.get("best_time_stop_min", ""))
    return f"{direction} th{threshold} {regime} TP {parse_float(tp) * 100:.2f}% T{time_stop}"


def artifact_prefix(row):
    path = row.get("path", "")
    suffix = "_full_search_summary.csv"
    if path.endswith(suffix):
        return path[: -len(suffix)]
    return ""


def load_leader_artifact(row, suffix):
    prefix = artifact_prefix(row)
    if not prefix:
        return []
    return load_csv(prefix + suffix)


def row_by_scenario(rows):
    return {
        row["scenario"]: row
        for row in rows
        if row.get("period") == "730d"
    }


def leader_decision(stress_rows):
    by_scenario = row_by_scenario(stress_rows)
    base = by_scenario.get("base_fee002_slip0", {})
    fee003 = by_scenario.get("fee003_slip0", {})
    fee004 = by_scenario.get("fee004_slip0", {})
    strict = by_scenario.get("strict_maker_005", {})

    base_ret = parse_float(base.get("return_pct"))
    base_pf = parse_float(base.get("profit_factor"))
    fee003_ret = parse_float(fee003.get("return_pct"))
    fee004_ret = parse_float(fee004.get("return_pct"))
    strict_ret = parse_float(strict.get("return_pct"))
    strict_pf = parse_float(strict.get("profit_factor"))

    if base_ret <= 0 or base_pf < 1.0:
        return "не брать: 730d база уже слабая"
    if fee004_ret > 0 and strict_ret > 0 and strict_pf >= 1.0:
        return "watchlist: maker-исполнение держится"
    if fee003_ret > 0 and strict_ret > 0:
        return "watchlist: только дешевый maker"
    return "не брать: execution/stress ломает"


def best_mtf_rows(rows):
    ok = [row for row in rows if row.get("status", "ok") == "ok" and row.get("days") == "730"]
    by_name = defaultdict(list)
    for row in ok:
        by_name[row["name"]].append(row)
    output = []
    for name, items in by_name.items():
        best = max(
            items,
            key=lambda row: (
                parse_float(row["return_pct"]),
                parse_float(row["profit_factor"]),
                -parse_float(row["max_dd_pct"]),
            ),
        )
        output.append(best)
    output.sort(key=lambda row: parse_float(row["return_pct"]), reverse=True)
    return output


def mtf_comparison_rows(rows):
    ok = [row for row in rows if row.get("status", "ok") == "ok" and row.get("days") == "730"]
    by_name = defaultdict(list)
    for row in ok:
        by_name[row["name"]].append(row)

    output = []
    for name, items in by_name.items():
        baseline = next((row for row in items if row.get("htf") == "1m_only"), None)
        if not baseline:
            continue
        best = max(
            items,
            key=lambda row: (
                parse_float(row["return_pct"]),
                parse_float(row["profit_factor"]),
                -parse_float(row["max_dd_pct"]),
            ),
        )
        base_return = parse_float(baseline["return_pct"])
        best_return = parse_float(best["return_pct"])
        base_dd = parse_float(baseline["max_dd_pct"])
        best_dd = parse_float(best["max_dd_pct"])
        base_trades = parse_float(baseline["trades"])
        best_trades = parse_float(best["trades"])

        if best.get("htf") == "1m_only":
            verdict = "MTF не улучшил"
        elif best_return > base_return and best_dd <= base_dd:
            verdict = "лучше доходность и риск"
        elif best_return > base_return:
            verdict = "доходность выше, риск выше"
        elif best_dd < base_dd:
            verdict = "риск ниже, доходность ниже"
        else:
            verdict = "хуже базы"
        if base_trades and best_trades < base_trades * 0.35:
            verdict += "; мало сделок"

        output.append((baseline, best, verdict))

    output.sort(key=lambda item: parse_float(item[1]["return_pct"]), reverse=True)
    return output


def top_scale_one_cashflow(rows, limit=10):
    items = [row for row in rows if abs(parse_float(row.get("scale")) - 1.0) < 1e-9]
    return items[:limit]


def main():
    parser = argparse.ArgumentParser(description="Build big final summary.")
    parser.add_argument("--new-status", default="data/big_new_coin_status.csv")
    parser.add_argument("--full-status", default="data/big_new_coin_full_leader_status.csv")
    parser.add_argument("--mtf-summary", default="data/mtf_universe_summary.csv")
    parser.add_argument("--cashflow-summary", default="data/big_cashflow_with_new_leaders_summary.csv")
    parser.add_argument("--cashflow-monthly", default="data/big_cashflow_with_new_leaders_best_monthly.csv")
    parser.add_argument("--mtf-cashflow-core", default="data/mtf_cashflow_core_summary.csv")
    parser.add_argument("--save-report", default="strategies/big-final-summary-new-coins-mtf.md")
    args = parser.parse_args()

    new_status = load_csv(args.new_status)
    full_status = load_csv(args.full_status)
    mtf_summary = load_csv(args.mtf_summary)
    cashflow = load_csv(args.cashflow_summary)
    cashflow_monthly = load_csv(args.cashflow_monthly)
    mtf_cashflow_core = load_csv(args.mtf_cashflow_core)

    lines = [
        "# Big Final Summary — New Coins + MTF",
        "",
        "Дата сборки: 2026-05-04.",
        "",
        "Это большой итоговый срез: новые монеты, full-тест лидеров, 730d stress/position sweep, MTF-фильтры по рабочим/watchlist стратегиям и cashflow.",
        "",
        "Главный принцип: не выбираем по максимальной доходности. Сначала смотрим, переживает ли идея 730 дней, комиссии/исполнение, просадку и месячный cashflow.",
        "",
        "## 1. Новые монеты",
        "",
        "| Symbol | Status | Best setup | 365d | PF | MaxDD any | Windows | Note |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]

    for row in sorted(new_status, key=lambda item: (item.get("status") != "leader", item["symbol"])):
        setup = fmt_setup(row)
        lines.append(
            f"| {row['symbol']} | {row['status']} | {setup} | {fmt_pct(row.get('return_365d_pct'))} | "
            f"{fmt_pf(row.get('profit_factor_365d'))} | {fmt_pos_pct(row.get('max_dd_any_pct'))} | "
            f"{row.get('positive_windows','')}/6 | {row.get('note','')} |"
        )

    lines.extend(
        [
            "",
            "## 2. Full Search Leaders",
            "",
            "Широкий screen дал 7 лидеров. Full search улучшил некоторые настройки, но это еще не принятие в работу: ниже идет stress, и он сильно меняет картину.",
            "",
            "| Symbol | Status | Full-search setup | 365d | PF | MaxDD any | Windows |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in full_status:
        if row.get("status") != "ok":
            lines.append(f"| {row['symbol']} | {row['status']} | - | - | - | - | - |")
            continue
        setup = fmt_setup(row)
        lines.append(
            f"| {row['symbol']} | ok | {setup} | {fmt_pct(row.get('return_365d_pct'))} | "
            f"{fmt_pf(row.get('profit_factor_365d'))} | {fmt_pos_pct(row.get('max_dd_any_pct'))} | "
            f"{row.get('positive_windows','')} |"
        )

    lines.extend(
        [
            "",
            "## 3. 730d Stress По Новым Лидерам",
            "",
            "Здесь видно, где результат держится только при идеальном cheap-maker исполнении. `fee0.04` — это 0.04% maker per side; `strict maker` — лимитка засчитывается только если рынок реально вернулся к цене; `taker-like` — грубая проверка, что будет при рыночном/плохом исполнении.",
            "",
            "| Symbol | Base 730 | Fee0.03 | Fee0.04 | Strict maker | Taker-like | Decision |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in full_status:
        if row.get("status") != "ok":
            continue
        stress = row_by_scenario(load_leader_artifact(row, "_stress_730.csv"))
        base = stress.get("base_fee002_slip0", {})
        fee003 = stress.get("fee003_slip0", {})
        fee004 = stress.get("fee004_slip0", {})
        strict = stress.get("strict_maker_005", {})
        taker = stress.get("taker_like_fee004_slip002", {})
        lines.append(
            f"| {row['symbol']} | {fmt_pct(base.get('return_pct'))} / DD {fmt_pos_pct(base.get('max_dd_pct'))} / PF {fmt_pf(base.get('profit_factor'))} | "
            f"{fmt_pct(fee003.get('return_pct'))} | {fmt_pct(fee004.get('return_pct'))} | "
            f"{fmt_pct(strict.get('return_pct'))} / PF {fmt_pf(strict.get('profit_factor'))} | "
            f"{fmt_pct(taker.get('return_pct'))} | {leader_decision(list(stress.values()))} |"
        )

    lines.extend(
        [
            "",
            "## 4. Position Sweep 730d",
            "",
            "Это проверка размера позиции. Она не исправляет edge, но показывает, какой ценой покупается доходность. Если 100% позиции дает красивый return и 80-90% DD, это не рабочая устойчивость, а очень нервный режим.",
            "",
            "| Symbol | 25% pos | 50% pos | 100% pos |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in full_status:
        if row.get("status") != "ok":
            continue
        sweep = {
            f"{parse_float(item.get('position_pct')):.2f}": item
            for item in load_leader_artifact(row, "_position_sweep_730.csv")
        }
        cells = []
        for pos in ("0.25", "0.50", "1.00"):
            item = sweep.get(pos, {})
            cells.append(
                f"{fmt_pct(item.get('return_730d_pct'))} / DD {fmt_pos_pct(item.get('max_dd_730d_pct'))} / PF {fmt_pf(item.get('profit_factor_730d'))}"
            )
        lines.append(f"| {row['symbol']} | {' | '.join(cells)} |")

    lines.extend(
        [
            "",
            "## 5. MTF Universe — Best 730d Per Strategy",
            "",
            "MTF здесь не меняет стратегию, TP/SL или позицию. Старший таймфрейм только разрешает/запрещает вход, а вход остается на 1m после закрытия старшей свечи.",
            "",
            "| Strategy | Symbol | Best HTF | 730d | MaxDD | PF | Trades |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in best_mtf_rows(mtf_summary):
        lines.append(
            f"| {row['name']} | {row['symbol']} | {row['htf']} | {fmt_pct(row['return_pct'])} | "
            f"{fmt_pos_pct(row['max_dd_pct'])} | {fmt_pf(row['profit_factor'])} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## 6. MTF: 1m Only Против Лучшего Фильтра",
            "",
            "| Strategy | 1m 730d | Best MTF 730d | Verdict |",
            "|---|---:|---:|---|",
        ]
    )
    for baseline, best, verdict in mtf_comparison_rows(mtf_summary):
        base_text = (
            f"{fmt_pct(baseline.get('return_pct'))} / DD {fmt_pos_pct(baseline.get('max_dd_pct'))} / "
            f"PF {fmt_pf(baseline.get('profit_factor'))} / {baseline.get('trades')} trades"
        )
        best_text = (
            f"{best.get('htf')} {fmt_pct(best.get('return_pct'))} / DD {fmt_pos_pct(best.get('max_dd_pct'))} / "
            f"PF {fmt_pf(best.get('profit_factor'))} / {best.get('trades')} trades"
        )
        lines.append(f"| {baseline['name']} | {base_text} | {best_text} | {verdict} |")

    lines.extend(
        [
            "",
            "## 7. Cashflow",
            "",
            "Cashflow-тест: старт $1000, цель снять $40+ за месяц, если в конце месяца баланс выше $1000 — прибыль снимается, если ниже $1000 — не пополняем. Важно: `scale=2.0` — это удвоенный риск/экспозиция относительно базовых весов, его нельзя считать строгим режимом `без усиления`.",
            "",
            "| Rank | Name | Weights | Scale | Loss stop | $40+ months | Withdrawn | Final | MaxDD | PF |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(cashflow[:20], start=1):
        lines.append(
            f"| {index} | {row.get('name','')} | {row.get('weights','')} | {parse_float(row.get('scale')):.2f} | "
            f"{parse_float(row.get('loss_stop_pct')):.2f} | {row.get('cash_hits','')}/{row.get('months','')} | "
            f"${parse_float(row.get('cash_withdrawn')):.2f} | ${parse_float(row.get('final_balance')):.2f} | "
            f"{fmt_pos_pct(row.get('max_drawdown_pct'))} | {fmt_pf(row.get('profit_factor'))} |"
        )

    scale_one = top_scale_one_cashflow(cashflow)
    lines.extend(
        [
            "",
            "### Cashflow Без Усиления Scale=1.0",
            "",
            "| Rank | Name | Weights | $40+ months | Withdrawn | MaxDD | PF |",
            "|---:|---|---|---:|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(scale_one, start=1):
        lines.append(
            f"| {index} | {row.get('name','')} | {row.get('weights','')} | "
            f"{row.get('cash_hits','')}/{row.get('months','')} | {fmt_money(row.get('cash_withdrawn'))} | "
            f"{fmt_pos_pct(row.get('max_drawdown_pct'))} | {fmt_pf(row.get('profit_factor'))} |"
        )

    if cashflow_monthly:
        lines.extend(
            [
                "",
                "### Лучший Cashflow По Месяцам",
                "",
                "| Month | Start | PnL | Withdrawal | End after | Stop reason | Trades |",
                "|---|---:|---:|---:|---:|---|---:|",
            ]
        )
        for row in cashflow_monthly:
            lines.append(
                f"| {row.get('month','')} | {fmt_money(row.get('start_balance'))} | "
                f"{fmt_money(row.get('month_pnl'))} | {fmt_money(row.get('withdrawal'))} | "
                f"{fmt_money(row.get('end_after_withdraw'))} | {row.get('stop_reason','')} | {row.get('trades','')} |"
            )

    if mtf_cashflow_core:
        lines.extend(
            [
                "",
                "### MTF На Cashflow-Core Портфелях",
                "",
                "Это отдельная проверка портфелей `GALA20/SPELL80` и `ONE20/SPELL80`: MTF-фильтр применялся к компонентам, а потом портфель снова проходил monthly cashflow.",
                "",
                "| Rank | Portfolio | HTF | Scale | Loss stop | $40+ months | Withdrawn | MaxDD | PF | Compound |",
                "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for index, row in enumerate(mtf_cashflow_core[:20], start=1):
            lines.append(
                f"| {index} | {row.get('portfolio','')} | {row.get('htf','')} | "
                f"{parse_float(row.get('scale')):.2f} | {parse_float(row.get('loss_stop_pct')):.2f} | "
                f"{row.get('cash_hits','')}/{row.get('months','')} | {fmt_money(row.get('cash_withdrawn'))} | "
                f"{fmt_pos_pct(row.get('max_drawdown_pct'))} | {fmt_pf(row.get('profit_factor'))} | "
                f"{fmt_pct(row.get('compound_return_pct'))} |"
            )

    best_cashflow = cashflow[0] if cashflow else None
    lines.extend(
        [
            "",
            "## 8. Итоговый Short-List",
            "",
        ]
    )
    if best_cashflow:
        lines.append(
            f"- Cashflow-core: `{best_cashflow.get('name')}` scale `{parse_float(best_cashflow.get('scale')):.2f}`, "
            f"loss-stop `{parse_float(best_cashflow.get('loss_stop_pct')):.2f}`, "
            f"`{best_cashflow.get('cash_hits')}/{best_cashflow.get('months')}` месяцев по `$40+`, "
            f"withdrawn `{fmt_money(best_cashflow.get('cash_withdrawn'))}`, MaxDD `{fmt_pos_pct(best_cashflow.get('max_drawdown_pct'))}`."
        )
    lines.extend(
        [
            "- Compounded maker-only: GALA `7.3 + 1h`, GALA `11.2 + 1h`, SPELL `1h`, ONE `11.2 + 5m`, MOVR `5m` можно держать как кандидатов, но только после отдельного execution-контроля.",
            "- Watchlist из новых монет: MOVR — самый здоровый из новых, но fee0.04 уже уводит его в минус; NFP слабее, CHR/DENT слишком хрупкие по strict maker.",
            "- Не брать сейчас: OXT/TRU/USTC, потому что 730d база или stress уже отрицательные; CHR/DENT не брать как рабочие, несмотря на огромную бумажную доходность.",
            "- Без усиления (`scale=1.0`) cashflow-цель `$40+` не дала 24/24 месяцев: лучший scale=1 результат только 13/24. Поэтому текущий 24/24 cashflow — это режим повышенной экспозиции, а не консервативный cashflow.",
            "- Для cashflow-core MTF не улучшил ежемесячную кассу: `1m_only` остался лучшим, а 3m/10m и выше резко снизили количество месяцев `$40+`.",
            "- MTF полезен для compounded-режима и снижения просадки; для ежемесячной кассы он часто режет количество сделок и может ухудшать стабильность снятий.",
            "- `taker-like` минусовой результат означает: стратегию нельзя исполнять рыночными входами; ей нужен maker-limit и контроль факта fill.",
            "",
            "## Files",
            "",
            f"- `{args.new_status}`",
            f"- `{args.full_status}`",
            f"- `{args.mtf_summary}`",
            f"- `{args.cashflow_summary}`",
            f"- `{args.cashflow_monthly}`",
            f"- `{args.mtf_cashflow_core}`",
            "- `data/big_*_stress_730.csv`",
            "- `data/big_*_position_sweep_730.csv`",
        ]
    )

    path = os.path.join(ROOT, args.save_report)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"saved report: {path}")


if __name__ == "__main__":
    main()
