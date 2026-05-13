#!/usr/bin/env python3
"""Local paper-trade monitor server.

This server is intentionally paper-only. It never sends exchange orders and it
does not need API keys. It repeatedly runs the existing paper execution journal
and operational monitor, stores a deduplicated paper ledger, and exposes a tiny
local dashboard/API for live observation.
"""

import argparse
import csv
import html
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "paper_live"
LOG_DIR = ROOT / "logs"
STATE_PATH = DATA_DIR / "state.json"
MAX_LEDGER_ROWS = 1000
DEFAULT_MODULES = ("RIF", "GALA_10", "GALA_112", "ANKR", "SPELL", "DYDX_X2")
MODULE_STRATEGIES = {
    "ANKR": {"ANKR LONG Best"},
    "RIF": {"RIF Regime Monitor"},
    "GALA_73": {"Минутка 7.3"},
    "GALA_10": {"Минутка 10"},
    "GALA_112": {"Минутка 11.2"},
    "SPELL": {"SPELL SHORT Best"},
    "DYDX_X2": {"DYDX Pullback SHORT x2 Protected"},
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compact_timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def trade_key(row):
    parts = [
        row.get("symbol", ""),
        row.get("module", ""),
        row.get("strategy", ""),
        row.get("signal_time", ""),
        row.get("order_start_time", ""),
        row.get("fill_time", ""),
        row.get("exit_time", ""),
        str(row.get("entry", "")),
        str(row.get("exit", "")),
    ]
    return "|".join(parts)


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return default


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def summarize_ledger(ledger):
    accepted = [row for row in ledger if row.get("portfolio_status") == "accepted"]
    total_return = sum(safe_float(row.get("portfolio_return_pct") or row.get("net_return_pct")) for row in accepted)
    wins = [row for row in accepted if safe_float(row.get("net_return_pct")) > 0]
    losses = [row for row in accepted if safe_float(row.get("net_return_pct")) < 0]
    return {
        "accepted_trades": len(accepted),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round((len(wins) / len(accepted) * 100.0), 2) if accepted else 0.0,
        "portfolio_return_sum_pct": round(total_return, 4),
    }


def write_module_universe(modules, path):
    source_path = ROOT / "data" / "operational_monitor_universe_2026-05-04.csv"
    rows = read_csv(source_path)
    wanted = set()
    for module in modules:
        wanted.update(MODULE_STRATEGIES.get(module, set()))
    selected = [row for row in rows if row.get("strategy") in wanted]
    if not selected:
        selected = rows
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(selected)


class PaperTradeApp:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.running = not args.no_autostart
        self.in_cycle = False
        self.stop_event = threading.Event()
        self.state = load_json(
            STATE_PATH,
            {
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "mode": "paper_only",
                "market": args.market,
                "modules": list(args.modules),
                "interval_sec": args.interval_sec,
                "last_run_at": "",
                "last_error": "",
                "last_cycle": {},
                "ledger_summary": {},
                "ledger": [],
                "seen_trade_keys": [],
            },
        )
        self.state["mode"] = "paper_only"
        self.state["market"] = args.market
        self.state["modules"] = list(args.modules)
        self.state["interval_sec"] = args.interval_sec
        self.worker = threading.Thread(target=self.worker_loop, name="paper-trade-loop", daemon=True)

    def start(self):
        self.worker.start()

    def snapshot(self):
        with self.lock:
            payload = dict(self.state)
            payload["running"] = self.running
            payload["in_cycle"] = self.in_cycle
            return payload

    def set_running(self, value):
        with self.lock:
            self.running = value
            self.state["updated_at"] = utc_now()
            save_json(STATE_PATH, self.state)

    def run_subprocess(self, command):
        started = time.time()
        proc = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        duration = round(time.time() - started, 2)
        return {
            "command": command,
            "returncode": proc.returncode,
            "duration_sec": duration,
            "output": proc.stdout[-6000:],
        }

    def run_cycle(self, manual=False):
        with self.lock:
            if self.in_cycle:
                return {"status": "already_running"}
            self.in_cycle = True
            self.state["last_error"] = ""
            save_json(STATE_PATH, self.state)

        stamp = compact_timestamp()
        journal_rel = f"data/paper_live/journal_{stamp}.csv"
        summary_rel = f"data/paper_live/summary_{stamp}.csv"
        report_rel = f"strategies/paper-live-journal-{stamp}.md"
        monitor_rel = f"data/paper_live/monitor_{stamp}.csv"
        monitor_report_rel = f"strategies/paper-live-monitor-{stamp}.md"
        universe_rel = f"data/paper_live/universe_{stamp}.csv"

        journal_cmd = [
            sys.executable,
            "scripts/paper_execution_journal.py",
            "--modules",
            *self.args.modules,
            "--days",
            str(self.args.days),
            "--warmup-days",
            str(self.args.warmup_days),
            "--market",
            self.args.market,
            "--entry-mode",
            self.args.entry_mode,
            "--limit-entry-offset-pct",
            str(self.args.limit_entry_offset_pct),
            "--limit-entry-timeout-min",
            str(self.args.limit_entry_timeout_min),
            "--fee-pct",
            str(self.args.fee_pct),
            "--slippage-pct",
            str(self.args.slippage_pct),
            "--save-journal",
            journal_rel,
            "--save-summary",
            summary_rel,
            "--save-report",
            report_rel,
        ]
        monitor_cmd = [
            sys.executable,
            "scripts/operational_daily_monitor.py",
            "--universe",
            universe_rel,
            "--paper-summary",
            summary_rel,
            "--save",
            monitor_rel,
            "--save-report",
            monitor_report_rel,
        ]

        cycle = {
            "started_at": utc_now(),
            "manual": manual,
            "journal_path": journal_rel,
            "summary_path": summary_rel,
            "monitor_path": monitor_rel,
            "journal": {},
            "monitor": {},
            "new_trades": 0,
        }

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            write_module_universe(self.args.modules, ROOT / universe_rel)
            cycle["journal"] = self.run_subprocess(journal_cmd)
            if cycle["journal"]["returncode"] != 0:
                raise RuntimeError(cycle["journal"]["output"])

            cycle["monitor"] = self.run_subprocess(monitor_cmd)
            if cycle["monitor"]["returncode"] != 0:
                raise RuntimeError(cycle["monitor"]["output"])

            journal_rows = read_csv(ROOT / journal_rel)
            summary_rows = read_csv(ROOT / summary_rel)
            monitor_rows = read_csv(ROOT / monitor_rel)
            filled = [
                row
                for row in journal_rows
                if row.get("order_status") == "filled" and row.get("portfolio_status") == "accepted"
            ]

            with self.lock:
                seen = set(self.state.get("seen_trade_keys", []))
                ledger = list(self.state.get("ledger", []))
                new_rows = []
                for row in filled:
                    key = trade_key(row)
                    if key in seen:
                        continue
                    seen.add(key)
                    row = dict(row)
                    row["paper_trade_key"] = key
                    row["recorded_at"] = utc_now()
                    new_rows.append(row)

                ledger.extend(new_rows)
                ledger = ledger[-MAX_LEDGER_ROWS:]
                self.state["seen_trade_keys"] = list(seen)[-MAX_LEDGER_ROWS * 2 :]
                self.state["ledger"] = ledger
                self.state["ledger_summary"] = summarize_ledger(ledger)
                self.state["latest_summary"] = summary_rows
                self.state["latest_monitor"] = monitor_rows
                self.state["last_run_at"] = utc_now()
                self.state["updated_at"] = utc_now()
                cycle["new_trades"] = len(new_rows)
                cycle["finished_at"] = utc_now()
                self.state["last_cycle"] = cycle
                save_json(STATE_PATH, self.state)
            return {"status": "ok", "new_trades": cycle["new_trades"]}
        except Exception as exc:
            with self.lock:
                cycle["finished_at"] = utc_now()
                cycle["error"] = str(exc)[-6000:]
                self.state["last_error"] = cycle["error"]
                self.state["last_cycle"] = cycle
                self.state["updated_at"] = utc_now()
                save_json(STATE_PATH, self.state)
            return {"status": "error", "error": str(exc)}
        finally:
            with self.lock:
                self.in_cycle = False

    def worker_loop(self):
        while not self.stop_event.is_set():
            should_run = False
            with self.lock:
                should_run = self.running and not self.in_cycle
            if should_run:
                self.run_cycle(manual=False)
            self.stop_event.wait(self.args.interval_sec)


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PaperTradeServer/1.0"

        def send_json(self, payload, status=200):
            body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_html(self, body, status=200):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/state":
                self.send_json(app.snapshot())
                return
            if path == "/api/run-once":
                threading.Thread(target=app.run_cycle, kwargs={"manual": True}, daemon=True).start()
                self.send_json({"status": "started"})
                return
            if path == "/":
                self.send_html(render_dashboard(app.snapshot()))
                return
            self.send_json({"error": "not found"}, status=404)

        def do_HEAD(self):
            path = urlparse(self.path).path
            if path in {"/", "/api/state"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8" if path == "/" else "application/json; charset=utf-8")
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/start":
                app.set_running(True)
                self.send_json({"running": True})
                return
            if path == "/api/stop":
                app.set_running(False)
                self.send_json({"running": False})
                return
            if path == "/api/run-once":
                threading.Thread(target=app.run_cycle, kwargs={"manual": True}, daemon=True).start()
                self.send_json({"status": "started"})
                return
            self.send_json({"error": "not found"}, status=404)

        def log_message(self, fmt, *args):
            line = f"{utc_now()} {self.address_string()} {fmt % args}\n"
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with (LOG_DIR / "paper_trade_server_access.log").open("a", encoding="utf-8") as handle:
                handle.write(line)

    return Handler


def render_table(rows, columns, limit=20):
    rows = rows[:limit]
    if not rows:
        return "<p>No rows yet.</p>"
    header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_dashboard(state):
    ledger = list(reversed(state.get("ledger", [])))
    monitor = state.get("latest_monitor", [])
    summary = state.get("latest_summary", [])
    ledger_summary = state.get("ledger_summary", {})
    status = "RUNNING" if state.get("running") else "STOPPED"
    in_cycle = "yes" if state.get("in_cycle") else "no"
    last_error = state.get("last_error") or ""
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px; background: #0f1419; color: #e6edf3; }
    h1, h2 { margin-bottom: 8px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 18px 0; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; }
    .muted { color: #8b949e; }
    button { background: #238636; color: white; border: 0; padding: 9px 12px; border-radius: 6px; margin-right: 8px; cursor: pointer; }
    button.stop { background: #da3633; }
    button.run { background: #1f6feb; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 12px 0 24px; }
    th, td { border: 1px solid #30363d; padding: 6px 8px; text-align: left; }
    th { background: #21262d; }
    pre { white-space: pre-wrap; background: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; }
    """
    script = """
    async function post(path) {
      await fetch(path, {method: 'POST'});
      setTimeout(() => location.reload(), 500);
    }
    setTimeout(() => location.reload(), 30000);
    """
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Paper Trade Server</title>
  <style>{style}</style>
  <script>{script}</script>
</head>
<body>
  <h1>Paper Trade Server</h1>
  <p class="muted">Paper-only local monitor. No exchange orders. No API keys.</p>
  <p>
    <button onclick="post('/api/start')">Start</button>
    <button class="stop" onclick="post('/api/stop')">Stop</button>
    <button class="run" onclick="post('/api/run-once')">Run Once</button>
    <a class="muted" href="/api/state">JSON state</a>
  </p>
  <div class="grid">
    <div class="card"><strong>Status</strong><br>{html.escape(status)}</div>
    <div class="card"><strong>In Cycle</strong><br>{html.escape(in_cycle)}</div>
    <div class="card"><strong>Market</strong><br>{html.escape(str(state.get('market', '')))}</div>
    <div class="card"><strong>Modules</strong><br>{html.escape(', '.join(state.get('modules', [])))}</div>
    <div class="card"><strong>Last Run</strong><br>{html.escape(str(state.get('last_run_at', '')))}</div>
    <div class="card"><strong>Ledger Return</strong><br>{html.escape(str(ledger_summary.get('portfolio_return_sum_pct', 0.0)))}%</div>
    <div class="card"><strong>Accepted Trades</strong><br>{html.escape(str(ledger_summary.get('accepted_trades', 0)))}</div>
    <div class="card"><strong>Win Rate</strong><br>{html.escape(str(ledger_summary.get('win_rate_pct', 0.0)))}%</div>
  </div>
  <h2>Latest Accepted Paper Trades</h2>
  {render_table(ledger, ['recorded_at', 'asset', 'symbol', 'strategy', 'module', 'direction', 'entry', 'exit', 'reason', 'net_return_pct', 'portfolio_return_pct'], 30)}
  <h2>Latest Monitor</h2>
  {render_table(monitor, ['symbol', 'asset', 'strategy', 'status', 'paper_return_sum_pct', 'paper_profit_factor', 'reason'], 30)}
  <h2>Latest Summary</h2>
  {render_table(summary, ['asset', 'strategy', 'signals', 'filled', 'accepted', 'fill_rate_pct', 'accepted_return_sum_pct', 'accepted_profit_factor'], 30)}
  <h2>Last Error</h2>
  <pre>{html.escape(last_error) if last_error else 'None'}</pre>
</body>
</html>"""


def parse_args():
    parser = argparse.ArgumentParser(description="Run a local paper-only trade monitor server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--modules", nargs="*", default=list(DEFAULT_MODULES))
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--market", choices=["futures_archive", "futures_global", "data_api_spot"], default="data_api_spot")
    parser.add_argument("--entry-mode", choices=["maker_limit", "next_open"], default="maker_limit")
    parser.add_argument("--limit-entry-offset-pct", type=float, default=0.0005)
    parser.add_argument("--limit-entry-timeout-min", type=int, default=1)
    parser.add_argument("--fee-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--no-autostart", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    app = PaperTradeApp(args)
    app.start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"Paper trade server running at http://{args.host}:{args.port}")
    print("Mode: paper-only. No exchange orders. No API keys.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop_event.set()
        server.server_close()


if __name__ == "__main__":
    main()
