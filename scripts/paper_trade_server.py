#!/usr/bin/env python3
"""Local paper-trade monitor server.

This server is intentionally paper-only. It never sends exchange orders and it
does not need API keys. It repeatedly runs the existing paper execution journal
and operational monitor, stores a deduplicated paper ledger, and exposes a tiny
local dashboard/API for live observation.
"""

import argparse
import csv
import hashlib
import hmac
import html
import importlib
import json
import math
import os
import subprocess
import sys
import threading
import time
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "paper_live"
LOG_DIR = ROOT / "logs"
STATE_PATH = DATA_DIR / "state.json"
STATE_ID = os.environ.get("PAPER_STATE_ID", "default")
AUTH_COOKIE = "paper_dashboard_auth"
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


def dashboard_password():
    return os.environ.get("PAPER_DASHBOARD_PASSWORD") or os.environ.get("DASHBOARD_PASSWORD") or ""


def dashboard_token(password):
    return hmac.new(password.encode("utf-8"), b"paper-dashboard-session", hashlib.sha256).hexdigest()


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


def nullable_float(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


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


def default_state(args):
    return {
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "paper_only",
        "market": args.market,
        "modules": list(args.modules),
        "interval_sec": args.interval_sec,
        "last_run_at": "",
        "last_error": "",
        "storage_backend": "local_json",
        "storage_error": "",
        "last_cycle": {},
        "ledger_summary": {},
        "ledger": [],
        "seen_trade_keys": [],
    }


class LocalStateStore:
    backend = "local_json"

    def load(self, default):
        return load_json(STATE_PATH, default)

    def save(self, payload):
        save_json(STATE_PATH, payload)

    def record_trades(self, rows):
        return None


class PostgresStateStore:
    backend = "postgres"

    def __init__(self, database_url, state_id=STATE_ID):
        self.driver, self.db_module = self.import_driver()
        self.database_url = database_url
        self.state_id = state_id
        self.init_schema()

    def import_driver(self):
        try:
            return "psycopg", importlib.import_module("psycopg")
        except ImportError:
            pass
        try:
            return "psycopg2", importlib.import_module("psycopg2")
        except ImportError:
            raise ImportError("No Postgres driver installed. Run pip install -r requirements.txt inside the app virtualenv.")

    def connect(self):
        if self.driver == "psycopg":
            return self.db_module.connect(self.database_url, autocommit=True)
        conn = self.db_module.connect(self.database_url)
        conn.autocommit = True
        return conn

    def init_schema(self):
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paper_trade_state (
                        id text PRIMARY KEY,
                        payload jsonb NOT NULL,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paper_trade_trades (
                        trade_key text PRIMARY KEY,
                        recorded_at timestamptz NOT NULL,
                        asset text,
                        symbol text,
                        strategy text,
                        module text,
                        direction text,
                        net_return_pct double precision,
                        portfolio_return_pct double precision,
                        row_json jsonb NOT NULL
                    )
                    """
                )

    def load(self, default):
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM paper_trade_state WHERE id = %s", (self.state_id,))
                row = cur.fetchone()
        if not row:
            return default
        payload = row[0]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def save(self, payload):
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO paper_trade_state (id, payload, updated_at)
                    VALUES (%s, %s::jsonb, now())
                    ON CONFLICT (id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                    """,
                    (self.state_id, json.dumps(payload, ensure_ascii=False)),
                )

    def record_trades(self, rows):
        if not rows:
            return None
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                for row in rows:
                    trade_id = row.get("paper_trade_key") or trade_key(row)
                    cur.execute(
                        """
                        INSERT INTO paper_trade_trades (
                            trade_key,
                            recorded_at,
                            asset,
                            symbol,
                            strategy,
                            module,
                            direction,
                            net_return_pct,
                            portfolio_return_pct,
                            row_json
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (trade_key) DO NOTHING
                        """,
                        (
                            trade_id,
                            row.get("recorded_at") or utc_now(),
                            row.get("asset"),
                            row.get("symbol"),
                            row.get("strategy"),
                            row.get("module"),
                            row.get("direction"),
                            nullable_float(row.get("net_return_pct")),
                            nullable_float(row.get("portfolio_return_pct")),
                            json.dumps(row, ensure_ascii=False),
                        ),
                    )
        return None


def make_state_store():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        try:
            return PostgresStateStore(database_url), ""
        except Exception as exc:
            return LocalStateStore(), f"Postgres disabled, using local JSON: {exc}"
    return LocalStateStore(), ""


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
        self.auth_password = dashboard_password()
        self.auth_token = dashboard_token(self.auth_password) if self.auth_password else ""
        self.store, storage_error = make_state_store()
        self.state = self.store.load(default_state(args))
        self.state["mode"] = "paper_only"
        self.state["market"] = args.market
        self.state["modules"] = list(args.modules)
        self.state["interval_sec"] = args.interval_sec
        self.state["monitor_enabled"] = not args.skip_monitor
        self.state["storage_backend"] = self.store.backend
        self.state["storage_error"] = storage_error
        self.state["auth_enabled"] = bool(self.auth_password)
        self.worker = threading.Thread(target=self.worker_loop, name="paper-trade-loop", daemon=True)
        self.save_state()

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
            self.save_state()

    def save_state(self):
        self.state["storage_backend"] = self.store.backend
        self.state["auth_enabled"] = bool(self.auth_password)
        try:
            self.store.save(self.state)
        except Exception as exc:
            self.state["storage_error"] = f"State save failed, local JSON fallback used: {exc}"
            save_json(STATE_PATH, self.state)

    def record_trades(self, rows):
        try:
            self.store.record_trades(rows)
        except Exception as exc:
            self.state["storage_error"] = f"Trade archive save failed: {exc}"

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
            self.save_state()

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
            "--days",
            str(self.args.monitor_days),
            "--stress-window",
            str(self.args.monitor_stress_window),
            "--save",
            monitor_rel,
            "--save-report",
            monitor_report_rel,
        ]
        if self.args.monitor_skip_stress:
            monitor_cmd.append("--skip-stress")

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

            if not self.args.skip_monitor:
                cycle["monitor"] = self.run_subprocess(monitor_cmd)
                if cycle["monitor"]["returncode"] != 0:
                    raise RuntimeError(cycle["monitor"]["output"])

            journal_rows = read_csv(ROOT / journal_rel)
            summary_rows = read_csv(ROOT / summary_rel)
            monitor_rows = read_csv(ROOT / monitor_rel) if not self.args.skip_monitor else []
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
                self.record_trades(new_rows)
                self.save_state()
            return {"status": "ok", "new_trades": cycle["new_trades"]}
        except Exception as exc:
            with self.lock:
                cycle["finished_at"] = utc_now()
                cycle["error"] = str(exc)[-6000:]
                self.state["last_error"] = cycle["error"]
                self.state["last_cycle"] = cycle
                self.state["updated_at"] = utc_now()
                self.save_state()
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

        def is_authenticated(self):
            if not app.auth_password:
                return True
            raw_cookie = self.headers.get("Cookie", "")
            cookies = {}
            for part in raw_cookie.split(";"):
                if "=" not in part:
                    continue
                key, value = part.strip().split("=", 1)
                cookies[key] = value
            return hmac.compare_digest(cookies.get(AUTH_COOKIE, ""), app.auth_token)

        def require_auth(self, json_response=False):
            if self.is_authenticated():
                return True
            if json_response:
                self.send_json({"error": "auth required"}, status=401)
            else:
                self.send_html(render_login(), status=200)
            return False

        def read_form(self):
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(min(length, 16384)).decode("utf-8")
            return parse_qs(body)

        def send_redirect(self, location, headers=None):
            self.send_response(303)
            self.send_header("Location", location)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()

        def send_json(self, payload, status=200, headers=None):
            body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def send_html(self, body, status=200, headers=None):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/healthz":
                self.send_json({"ok": True})
                return
            if path == "/api/state":
                if not self.require_auth(json_response=True):
                    return
                self.send_json(app.snapshot())
                return
            if path == "/api/run-once":
                if not self.require_auth(json_response=True):
                    return
                threading.Thread(target=app.run_cycle, kwargs={"manual": True}, daemon=True).start()
                self.send_json({"status": "started"})
                return
            if path == "/":
                if not self.require_auth():
                    return
                self.send_html(render_dashboard(app.snapshot()))
                return
            self.send_json({"error": "not found"}, status=404)

        def do_HEAD(self):
            path = urlparse(self.path).path
            if path in {"/", "/api/state", "/healthz"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8" if path == "/" else "application/json; charset=utf-8")
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/login":
                form = self.read_form()
                password = form.get("password", [""])[0]
                if app.auth_password and hmac.compare_digest(password, app.auth_password):
                    self.send_redirect(
                        "/",
                        headers={
                            "Set-Cookie": f"{AUTH_COOKIE}={app.auth_token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000"
                        },
                    )
                    return
                self.send_html(render_login("Неверный пароль"), status=401)
                return
            if path == "/api/logout":
                self.send_redirect(
                    "/",
                    headers={"Set-Cookie": f"{AUTH_COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"},
                )
                return
            if path == "/api/start":
                if not self.require_auth(json_response=True):
                    return
                app.set_running(True)
                self.send_json({"running": True})
                return
            if path == "/api/stop":
                if not self.require_auth(json_response=True):
                    return
                app.set_running(False)
                self.send_json({"running": False})
                return
            if path == "/api/run-once":
                if not self.require_auth(json_response=True):
                    return
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


def tone_class(value):
    text = str(value or "").strip().lower()
    if text in {"trade", "running", "yes", "filled", "accepted", "ok", "postgres", "enabled"}:
        return "success"
    if text in {"watch", "already_running"}:
        return "warning"
    if text in {"off", "stopped", "no", "error", "rejected", "local_json", "disabled"}:
        return "danger"
    return "secondary"


def numeric_tone(value):
    parsed = nullable_float(value)
    if parsed is None or parsed == 0:
        return "muted-value"
    return "positive" if parsed > 0 else "negative"


def render_badge(value, tone=None):
    label = html.escape(str(value if value not in (None, "") else "none"))
    badge_tone = tone or tone_class(value)
    return f'<span class="badge {badge_tone}">{label}</span>'


def render_cell(column, value):
    if column in {"status", "direction", "order_status", "portfolio_status", "storage_backend"}:
        return render_badge(value)
    if column in {
        "paper_return_sum_pct",
        "accepted_return_sum_pct",
        "net_return_pct",
        "portfolio_return_pct",
        "accepted_profit_factor",
        "paper_profit_factor",
        "fill_rate_pct",
    }:
        return f'<span class="{numeric_tone(value)}">{html.escape(str(value if value not in (None, "") else "0"))}</span>'
    if column == "reason":
        return f'<span class="reason">{html.escape(str(value or ""))}</span>'
    return html.escape(str(value if value is not None else ""))


def render_table(rows, columns, limit=20):
    rows = rows[:limit]
    if not rows:
        return '<div class="empty-state">No rows yet.</div>'
    header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{render_cell(col, row.get(col, ''))}</td>" for col in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f'<div class="table-shell"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def render_metric(label, value, tone=None, detail=""):
    badge = render_badge(value, tone) if tone else html.escape(str(value))
    detail_html = f'<div class="metric-detail">{html.escape(str(detail))}</div>' if detail else ""
    return f"""<section class="metric-card">
      <div class="metric-label">{html.escape(label)}</div>
      <div class="metric-value">{badge}</div>
      {detail_html}
    </section>"""


def render_login(error=""):
    style = """
    :root {
      --background: hsl(222.2 84% 4.9%);
      --foreground: hsl(210 40% 98%);
      --card: hsl(222.2 84% 4.9%);
      --card-foreground: hsl(210 40% 98%);
      --muted: hsl(217.2 32.6% 17.5%);
      --muted-foreground: hsl(215 20.2% 65.1%);
      --border: hsl(217.2 32.6% 17.5%);
      --input: hsl(217.2 32.6% 17.5%);
      --primary: hsl(210 40% 98%);
      --primary-foreground: hsl(222.2 47.4% 11.2%);
      --destructive: hsl(0 62.8% 30.6%);
      --ring: hsl(212.7 26.8% 83.9%);
    }
    * { box-sizing: border-box; }
    body {
      min-height: 100svh;
      margin: 0;
      display: grid;
      place-items: center;
      background: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }
    main {
      width: min(420px, calc(100vw - 32px));
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      box-shadow: 0 18px 60px rgb(0 0 0 / 0.35);
    }
    .login-header { padding: 24px 24px 0; }
    .login-body { padding: 24px; }
    .eyebrow { color: var(--muted-foreground); font-size: 12px; font-weight: 600; text-transform: uppercase; }
    h1 { margin: 8px 0 8px; font-size: 26px; line-height: 1.1; font-weight: 700; }
    p { margin: 0; color: var(--muted-foreground); line-height: 1.5; }
    label { display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; }
    input {
      width: 100%;
      height: 42px;
      border: 1px solid var(--input);
      border-radius: 6px;
      background: transparent;
      color: var(--foreground);
      padding: 0 12px;
      font-size: 14px;
      outline: none;
    }
    input:focus { border-color: var(--ring); box-shadow: 0 0 0 3px rgb(148 163 184 / 0.2); }
    button {
      width: 100%;
      height: 42px;
      margin-top: 14px;
      border: 0;
      border-radius: 6px;
      background: var(--primary);
      color: var(--primary-foreground);
      font-weight: 600;
      cursor: pointer;
    }
    .error { margin-top: 12px; color: hsl(0 84.2% 60.2%); font-size: 13px; }
    """
    error_html = f"<div class=\"error\">{html.escape(error)}</div>" if error else ""
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Paper Trade Login</title>
  <style>{style}</style>
</head>
<body>
  <main>
    <div class="login-header">
      <div class="eyebrow">Paper dashboard</div>
      <h1>Вход в панель</h1>
      <p>Доступ к live-монитору стратегий защищен паролем.</p>
    </div>
    <div class="login-body">
      <form method="post" action="/api/login">
        <label for="password">Пароль</label>
        <input id="password" name="password" type="password" autocomplete="current-password" autofocus>
        <button type="submit">Войти</button>
      </form>
      {error_html}
    </div>
  </main>
</body>
</html>"""


def render_dashboard(state):
    ledger = list(reversed(state.get("ledger", [])))
    monitor = state.get("latest_monitor", [])
    summary = state.get("latest_summary", [])
    ledger_summary = state.get("ledger_summary", {})
    status = "RUNNING" if state.get("running") else "STOPPED"
    in_cycle = "yes" if state.get("in_cycle") else "no"
    last_error = state.get("last_error") or ""
    storage_error = state.get("storage_error") or ""
    last_run = state.get("last_run_at") or "not yet"
    modules = state.get("modules", [])
    modules_html = "".join(render_badge(module, "secondary") for module in modules)
    metrics_html = "\n".join(
        [
            render_metric("Status", status, tone_class(status), "server loop"),
            render_metric("In cycle", in_cycle, tone_class(in_cycle), "current run"),
            render_metric("Storage", state.get("storage_backend", "local_json"), tone_class(state.get("storage_backend")), "persistence"),
            render_metric("Auth", "enabled" if state.get("auth_enabled") else "disabled", tone_class("enabled" if state.get("auth_enabled") else "disabled"), "access"),
            render_metric("Ledger return", f"{ledger_summary.get('portfolio_return_sum_pct', 0.0)}%", None, "paper ledger"),
            render_metric("Accepted trades", ledger_summary.get("accepted_trades", 0), None, "deduplicated"),
            render_metric("Win rate", f"{ledger_summary.get('win_rate_pct', 0.0)}%", None, "accepted trades"),
            render_metric("Latest summary", len(summary), None, "strategy rows"),
        ]
    )
    style = """
    :root {
      --background: hsl(222.2 84% 4.9%);
      --foreground: hsl(210 40% 98%);
      --card: hsl(222.2 84% 4.9%);
      --card-foreground: hsl(210 40% 98%);
      --muted: hsl(217.2 32.6% 17.5%);
      --muted-foreground: hsl(215 20.2% 65.1%);
      --popover: hsl(222.2 84% 4.9%);
      --popover-foreground: hsl(210 40% 98%);
      --primary: hsl(210 40% 98%);
      --primary-foreground: hsl(222.2 47.4% 11.2%);
      --secondary: hsl(217.2 32.6% 17.5%);
      --secondary-foreground: hsl(210 40% 98%);
      --destructive: hsl(0 62.8% 30.6%);
      --destructive-foreground: hsl(210 40% 98%);
      --border: hsl(217.2 32.6% 17.5%);
      --input: hsl(217.2 32.6% 17.5%);
      --ring: hsl(212.7 26.8% 83.9%);
      --success: hsl(142.1 70.6% 45.3%);
      --warning: hsl(47.9 95.8% 53.1%);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }
    a { color: inherit; }
    .shell { min-height: 100svh; padding: 24px; }
    .workspace { max-width: 1440px; margin: 0 auto; }
    .topbar {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }
    .brand { display: grid; gap: 8px; }
    .eyebrow { color: var(--muted-foreground); font-size: 12px; font-weight: 600; text-transform: uppercase; }
    h1 { margin: 0; font-size: 30px; line-height: 1.15; font-weight: 700; }
    h2 { margin: 0; font-size: 18px; line-height: 1.2; font-weight: 650; }
    p { margin: 0; color: var(--muted-foreground); line-height: 1.5; }
    .actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
    button, .button-link {
      height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      border: 1px solid var(--border);
      padding: 0 12px;
      background: transparent;
      color: var(--foreground);
      font-size: 14px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
    }
    button.primary { background: var(--primary); color: var(--primary-foreground); border-color: var(--primary); }
    button.destructive { background: var(--destructive); color: var(--destructive-foreground); border-color: var(--destructive); }
    button.secondary, .button-link { background: var(--secondary); color: var(--secondary-foreground); }
    button:hover, .button-link:hover { opacity: 0.9; }
    .section { padding: 22px 0; border-bottom: 1px solid var(--border); }
    .section-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
    .section-copy { color: var(--muted-foreground); font-size: 13px; }
    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .metric-card {
      min-height: 112px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
    }
    .metric-label { color: var(--muted-foreground); font-size: 12px; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 24px; line-height: 1; font-weight: 700; word-break: break-word; }
    .metric-detail { color: var(--muted-foreground); font-size: 12px; }
    .module-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      border-radius: 999px;
      border: 1px solid var(--border);
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }
    .badge.success { border-color: rgb(34 197 94 / 0.35); background: rgb(34 197 94 / 0.12); color: hsl(142.1 76.2% 73.1%); }
    .badge.warning { border-color: rgb(250 204 21 / 0.35); background: rgb(250 204 21 / 0.12); color: hsl(47.9 95.8% 73.1%); }
    .badge.danger { border-color: rgb(248 113 113 / 0.35); background: rgb(248 113 113 / 0.12); color: hsl(0 93.5% 81.8%); }
    .badge.secondary { background: var(--secondary); color: var(--secondary-foreground); }
    .table-shell {
      width: 100%;
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { height: 42px; padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
    th { color: var(--muted-foreground); font-size: 12px; font-weight: 650; text-transform: uppercase; background: var(--muted); }
    tr:last-child td { border-bottom: 0; }
    tbody tr:hover { background: rgb(148 163 184 / 0.06); }
    .empty-state {
      min-height: 96px;
      display: grid;
      place-items: center;
      border: 1px dashed var(--border);
      border-radius: 8px;
      color: var(--muted-foreground);
      background: rgb(148 163 184 / 0.03);
    }
    .reason { color: var(--muted-foreground); }
    .positive { color: hsl(142.1 76.2% 73.1%); font-weight: 650; }
    .negative { color: hsl(0 93.5% 81.8%); font-weight: 650; }
    .muted-value { color: var(--muted-foreground); }
    pre {
      margin: 0;
      white-space: pre-wrap;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      color: var(--muted-foreground);
      padding: 14px;
      font-size: 13px;
      line-height: 1.45;
    }
    @media (max-width: 760px) {
      .shell { padding: 16px; }
      .topbar, .section-header { align-items: stretch; flex-direction: column; }
      .actions { justify-content: flex-start; }
      h1 { font-size: 26px; }
    }
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
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Paper Trade Server</title>
  <style>{style}</style>
  <script>{script}</script>
</head>
<body>
  <main class="shell">
    <div class="workspace">
      <header class="topbar">
        <div class="brand">
          <div class="eyebrow">Paper trade server</div>
          <h1>Live strategy monitor</h1>
          <p>Paper-only монитор. Биржевые ордера и API-ключи не используются.</p>
        </div>
        <div class="actions">
          <button class="primary" onclick="post('/api/start')">Start</button>
          <button class="destructive" onclick="post('/api/stop')">Stop</button>
          <button class="secondary" onclick="post('/api/run-once')">Run Once</button>
          <form method="post" action="/api/logout" style="display:inline"><button class="secondary" type="submit">Logout</button></form>
          <a class="button-link" href="/api/state">JSON</a>
        </div>
      </header>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Overview</h2>
            <p class="section-copy">Market: {html.escape(str(state.get('market', '')))}. Last run: {html.escape(str(last_run))}.</p>
          </div>
          <div class="module-row">{modules_html}</div>
        </div>
        <div class="metrics-grid">
          {metrics_html}
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Latest accepted paper trades</h2>
            <p class="section-copy">Последние зачтенные paper-сделки из общего ledger.</p>
          </div>
        </div>
        {render_table(ledger, ['recorded_at', 'asset', 'symbol', 'strategy', 'module', 'direction', 'entry', 'exit', 'reason', 'net_return_pct', 'portfolio_return_pct'], 30)}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Latest monitor</h2>
            <p class="section-copy">Операционный статус стратегий после последнего цикла.</p>
          </div>
        </div>
        {render_table(monitor, ['symbol', 'asset', 'strategy', 'status', 'paper_return_sum_pct', 'paper_profit_factor', 'reason'], 30)}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Latest summary</h2>
            <p class="section-copy">Сигналы, исполнения и принятые сделки по модулям.</p>
          </div>
        </div>
        {render_table(summary, ['asset', 'strategy', 'signals', 'filled', 'accepted', 'fill_rate_pct', 'accepted_return_sum_pct', 'accepted_profit_factor'], 30)}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Diagnostics</h2>
            <p class="section-copy">Ошибки последнего цикла и состояния хранилища.</p>
          </div>
        </div>
        <div class="metrics-grid">
          <div>
            <h2>Last error</h2>
            <pre>{html.escape(last_error) if last_error else 'None'}</pre>
          </div>
          <div>
            <h2>Storage error</h2>
            <pre>{html.escape(storage_error) if storage_error else 'None'}</pre>
          </div>
        </div>
      </section>
    </div>
  </main>
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
    parser.add_argument("--skip-monitor", action="store_true")
    parser.add_argument("--monitor-days", type=int, default=7)
    parser.add_argument("--monitor-stress-window", type=int, default=7)
    parser.add_argument("--monitor-skip-stress", action="store_true")
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
