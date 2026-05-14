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
import re
import subprocess
import sys
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "paper_live"
LOG_DIR = ROOT / "logs"
STATE_PATH = DATA_DIR / "state.json"
STATE_ID = os.environ.get("PAPER_STATE_ID", "default")
AUTH_COOKIE = "paper_dashboard_auth"
MAX_LEDGER_ROWS = 1000
DISPLAY_TZ_NAME = os.environ.get("PAPER_DASHBOARD_TIMEZONE", "America/Chicago")
try:
    DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
except Exception:
    DISPLAY_TZ_NAME = "America/Chicago"
    DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
DEFAULT_MODULES = ("RIF",)
RIF_ONLY_MODE = os.environ.get("PAPER_RIF_ONLY", "1").strip().lower() not in {"0", "false", "no", "off"}
RIF_STRATEGY = "RIF Regime Monitor"
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


def display_time(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(DISPLAY_TZ).strftime("%d.%m.%Y %H:%M:%S %Z")


def display_time_minute(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(DISPLAY_TZ).strftime("%d.%m.%Y %H:%M %Z")


def parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_time_column(column):
    return column.endswith("_at") or column.endswith("_time") or column in {"time", "recorded_at"}


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


def is_rif_row(row):
    asset = str(row.get("asset", "")).upper()
    symbol = str(row.get("symbol", "")).upper()
    strategy = str(row.get("strategy", ""))
    module = str(row.get("module", "")).upper()
    return asset == "RIF" or symbol == "RIFUSDT" or strategy == RIF_STRATEGY or module == "RIF"


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
        "monitor_universe": getattr(args, "monitor_universe", "all"),
        "monitor_every_cycles": getattr(args, "monitor_every_cycles", 15),
        "monitor_strategy_count": 0,
        "interval_sec": args.interval_sec,
        "last_run_at": "",
        "last_monitor_run_at": "",
        "last_error": "",
        "storage_backend": "local_json",
        "storage_error": "",
        "last_cycle": {},
        "auto_cycle_count": 0,
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

    def purge_non_rif_history(self):
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

    def purge_non_rif_history(self):
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM paper_trade_trades
                    WHERE COALESCE(asset, '') <> 'RIF'
                      AND COALESCE(symbol, '') <> 'RIFUSDT'
                      AND COALESCE(strategy, '') <> %s
                      AND COALESCE(module, '') <> 'RIF'
                    """,
                    (RIF_STRATEGY,),
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


def sanitize_rif_only_state(state):
    state["modules"] = ["RIF"]
    state["monitor_universe"] = "modules"

    ledger = [row for row in state.get("ledger", []) if is_rif_row(row)]
    state["ledger"] = ledger[-MAX_LEDGER_ROWS:]
    state["seen_trade_keys"] = [row.get("paper_trade_key") or trade_key(row) for row in state["ledger"]]
    state["ledger_summary"] = summarize_ledger(state["ledger"])

    for key in ("latest_summary", "latest_monitor"):
        if isinstance(state.get(key), list):
            state[key] = [row for row in state[key] if is_rif_row(row)]

    state["monitor_strategy_count"] = len(state.get("latest_monitor", []))
    state["updated_at"] = utc_now()
    return state


def write_module_universe(modules, path, mode="all"):
    source_path = ROOT / "data" / "operational_monitor_universe_2026-05-04.csv"
    rows = read_csv(source_path)
    if not rows:
        raise RuntimeError(f"Monitor universe is empty or missing: {source_path}")

    if mode == "all":
        selected = rows
    else:
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
        self.state["monitor_universe"] = args.monitor_universe
        self.state["monitor_every_cycles"] = args.monitor_every_cycles
        self.state["interval_sec"] = args.interval_sec
        self.state["monitor_enabled"] = not args.skip_monitor
        self.state["auto_cycle_count"] = int(self.state.get("auto_cycle_count") or 0)
        self.state["storage_backend"] = self.store.backend
        self.state["storage_error"] = storage_error
        self.state["auth_enabled"] = bool(self.auth_password)
        if RIF_ONLY_MODE:
            self.state = sanitize_rif_only_state(self.state)
            try:
                self.store.purge_non_rif_history()
            except Exception as exc:
                self.state["storage_error"] = f"RIF-only history purge failed: {exc}"
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
            if manual:
                auto_cycle_number = self.state.get("auto_cycle_count", 0)
            else:
                auto_cycle_number = int(self.state.get("auto_cycle_count") or 0) + 1
                self.state["auto_cycle_count"] = auto_cycle_number
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

        monitor_every = max(1, int(self.args.monitor_every_cycles or 1))
        run_monitor = (
            not self.args.skip_monitor
            and (manual or auto_cycle_number == 1 or auto_cycle_number % monitor_every == 0)
        )

        cycle = {
            "started_at": utc_now(),
            "manual": manual,
            "auto_cycle_number": auto_cycle_number,
            "monitor_due": run_monitor,
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
            cycle["journal"] = self.run_subprocess(journal_cmd)
            if cycle["journal"]["returncode"] != 0:
                raise RuntimeError(cycle["journal"]["output"])

            if run_monitor:
                write_module_universe(self.args.modules, ROOT / universe_rel, self.args.monitor_universe)
                cycle["monitor"] = self.run_subprocess(monitor_cmd)
                if cycle["monitor"]["returncode"] != 0:
                    raise RuntimeError(cycle["monitor"]["output"])
            else:
                cycle["monitor"] = {
                    "skipped": True,
                    "reason": f"Operational monitor runs every {monitor_every} paper cycles.",
                }

            journal_rows = read_csv(ROOT / journal_rel)
            summary_rows = read_csv(ROOT / summary_rel)
            if run_monitor:
                monitor_rows = read_csv(ROOT / monitor_rel)
            else:
                with self.lock:
                    monitor_rows = list(self.state.get("latest_monitor", []))
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
                now = utc_now()
                self.state["latest_monitor"] = monitor_rows
                self.state["monitor_strategy_count"] = len(monitor_rows)
                self.state["last_run_at"] = now
                if run_monitor:
                    self.state["last_monitor_run_at"] = now
                self.state["updated_at"] = now
                cycle["new_trades"] = len(new_rows)
                cycle["finished_at"] = now
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
            parsed_url = urlparse(self.path)
            path = parsed_url.path
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
                query = parse_qs(parsed_url.query)
                self.send_html(render_dashboard(app.snapshot(), query.get("status", ["ALL"])[0]))
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


PCT_COLUMNS = {
    "paper_return_sum_pct",
    "accepted_return_sum_pct",
    "net_return_pct",
    "portfolio_return_pct",
    "return_30d_pct",
    "return_60d_pct",
    "strict_return_30d_pct",
    "taker_return_30d_pct",
    "accepted_expectancy_pct",
    "paper_expectancy_pct",
    "expectancy_30d_pct",
    "expectancy_60d_pct",
    "win_30d_pct",
    "win_60d_pct",
    "fill_rate_pct",
    "dd_30d_pct",
    "dd_60d_pct",
    "strict_dd_30d_pct",
    "taker_dd_30d_pct",
}
PF_COLUMNS = {"accepted_profit_factor", "paper_profit_factor", "pf_30d", "pf_60d", "strict_pf_30d", "taker_pf_30d"}
COLUMN_LABELS = {
    "asset": "Монета",
    "symbol": "Пара",
    "strategy": "Стратегия",
    "side": "Сторона",
    "status": "Статус",
    "signals": "Сигн.",
    "filled": "Исп.",
    "accepted": "Прин.",
    "fill_rate_pct": "Fill",
    "accepted_return_sum_pct": "Paper",
    "accepted_profit_factor": "PF",
    "return_30d_pct": "30d",
    "pf_30d": "30d PF",
    "dd_30d_pct": "30d DD",
    "trades_30d": "30d сделок",
    "reason": "Причина",
    "paper_return_sum_pct": "Paper",
    "paper_profit_factor": "PF",
    "recorded_at": "Время",
    "module": "Модуль",
    "direction": "Сторона",
    "entry": "Вход",
    "exit": "Выход",
    "net_return_pct": "Сделка",
    "portfolio_return_pct": "Портфель",
    "last_trade_time": "Последняя",
    "off_summary": "Почему OFF",
    "recovery_hint": "Что улучшить",
}
STATUS_FILTERS = ("ALL", "TRADE", "WATCH", "OFF")


def column_label(column):
    return COLUMN_LABELS.get(column, column)


def format_decimal(value, decimals=2, suffix=""):
    parsed = nullable_float(value)
    if parsed is None:
        return str(value if value not in (None, "") else "0")
    return f"{parsed:.{decimals}f}{suffix}"


def render_badge(value, tone=None):
    label = html.escape(str(value if value not in (None, "") else "none"))
    badge_tone = tone or tone_class(value)
    return f'<span class="badge {badge_tone}">{label}</span>'


def render_cell(column, value):
    if is_time_column(column):
        return html.escape(display_time(value))
    if column in {"status", "side", "direction", "order_status", "portfolio_status", "storage_backend"}:
        return render_badge(value)
    if column in {"reason", "stress_reason", "notes", "off_summary", "recovery_hint"}:
        full = str(value or "")
        short = full if len(full) <= 130 else full[:127] + "..."
        return f'<span class="reason" title="{html.escape(full)}">{html.escape(short)}</span>'
    if column in {"dd_30d_pct", "dd_60d_pct", "strict_dd_30d_pct", "taker_dd_30d_pct"}:
        parsed = nullable_float(value)
        tone = "negative" if parsed and parsed > 0 else "muted-value"
        return f'<span class="{tone}">{html.escape(format_decimal(value, 2, "%"))}</span>'
    if column in PF_COLUMNS:
        if str(value).strip().lower() in {"inf", "infinity", "∞"}:
            return '<span class="positive">∞</span>'
        parsed = nullable_float(value)
        if parsed is None or parsed == 0:
            tone = "muted-value"
        elif parsed >= 1:
            tone = "positive"
        else:
            tone = "negative"
        return f'<span class="{tone}">{html.escape(format_decimal(value, 2))}</span>'
    if column in PCT_COLUMNS:
        return f'<span class="{numeric_tone(value)}">{html.escape(format_decimal(value, 2, "%"))}</span>'
    return html.escape(str(value if value is not None else ""))


def render_table(rows, columns, limit=20, class_name=""):
    rows = rows[:limit]
    if not rows:
        return '<div class="empty-state">No rows yet.</div>'
    header = "".join(f"<th>{html.escape(column_label(col))}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{render_cell(col, row.get(col, ''))}</td>" for col in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    shell_class = f"table-shell {class_name}".strip()
    return f'<div class="{shell_class}"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def render_metric(label, value, tone=None, detail=""):
    badge = render_badge(value, tone) if tone else html.escape(str(value))
    value_class = "metric-value compact" if len(str(value)) > 18 else "metric-value"
    detail_html = f'<div class="metric-detail">{html.escape(str(detail))}</div>' if detail else ""
    return f"""<section class="metric-card">
      <div class="metric-label">{html.escape(label)}</div>
      <div class="{value_class}">{badge}</div>
      {detail_html}
    </section>"""


def strategy_key(row):
    return (
        str(row.get("asset") or row.get("symbol") or "").strip(),
        str(row.get("strategy") or "").strip(),
    )


def value_or_fallback(value, fallback=""):
    return value if value not in (None, "") else fallback


def build_strategy_board(summary_rows, monitor_rows):
    board = {}

    for row in monitor_rows:
        key = strategy_key(row)
        if not key[1]:
            continue
        board[key] = {
            "asset": row.get("asset") or key[0],
            "symbol": row.get("symbol", ""),
            "strategy": row.get("strategy", ""),
            "side": row.get("side", ""),
            "status": row.get("status", ""),
            "signals": row.get("paper_signals", ""),
            "filled": row.get("paper_filled", ""),
            "accepted": row.get("paper_accepted", ""),
            "fill_rate_pct": row.get("paper_fill_rate_pct", ""),
            "accepted_return_sum_pct": row.get("paper_return_sum_pct", ""),
            "accepted_profit_factor": row.get("paper_profit_factor", ""),
            "return_30d_pct": row.get("return_30d_pct", ""),
            "pf_30d": row.get("pf_30d", ""),
            "dd_30d_pct": row.get("dd_30d_pct", ""),
            "trades_30d": row.get("trades_30d", ""),
            "reason": row.get("reason", ""),
        }

    for row in summary_rows:
        key = strategy_key(row)
        if not key[1]:
            continue
        item = board.setdefault(
            key,
            {
                "asset": row.get("asset") or key[0],
                "symbol": row.get("symbol", ""),
                "strategy": row.get("strategy", ""),
                "side": row.get("direction", ""),
                "status": "PAPER",
                "signals": "",
                "filled": "",
                "accepted": "",
                "fill_rate_pct": "",
                "accepted_return_sum_pct": "",
                "accepted_profit_factor": "",
                "return_30d_pct": "",
                "pf_30d": "",
                "dd_30d_pct": "",
                "trades_30d": "",
                "reason": "",
            },
        )
        item["signals"] = value_or_fallback(row.get("signals"), item.get("signals", ""))
        item["filled"] = value_or_fallback(row.get("filled"), item.get("filled", ""))
        item["accepted"] = value_or_fallback(row.get("accepted"), item.get("accepted", ""))
        item["fill_rate_pct"] = value_or_fallback(row.get("fill_rate_pct"), item.get("fill_rate_pct", ""))
        item["accepted_return_sum_pct"] = value_or_fallback(
            row.get("accepted_return_sum_pct"), item.get("accepted_return_sum_pct", "")
        )
        item["accepted_profit_factor"] = value_or_fallback(
            row.get("accepted_profit_factor"), item.get("accepted_profit_factor", "")
        )

    status_order = {"TRADE": 0, "WATCH": 1, "PAPER": 2, "OFF": 3, "ERROR": 4}
    return sorted(
        board.values(),
        key=lambda row: (
            status_order.get(str(row.get("status", "")).upper(), 5),
            str(row.get("asset", "")),
            str(row.get("strategy", "")),
        ),
    )


def normalize_status_filter(value):
    status = str(value or "ALL").upper()
    return status if status in STATUS_FILTERS else "ALL"


def count_by_status(rows):
    counts = {status: 0 for status in STATUS_FILTERS}
    counts["ALL"] = len(rows)
    for row in rows:
        status = str(row.get("status", "")).upper()
        if status in counts:
            counts[status] += 1
    return counts


def trade_event_time(row):
    for key in ("exit_time", "recorded_at", "fill_time", "order_start_time", "signal_time"):
        parsed = parse_datetime(row.get(key))
        if parsed:
            return parsed
    return None


def recent_accepted_ledger_rows(ledger, hours=24):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    rows = []
    for row in ledger:
        if row.get("portfolio_status") != "accepted":
            continue
        event_time = trade_event_time(row)
        if not event_time or event_time < cutoff or event_time > now + timedelta(minutes=5):
            continue
        enriched = dict(row)
        enriched["_event_time"] = event_time
        rows.append(enriched)
    return sorted(rows, key=lambda row: row["_event_time"])


def profit_factor_from_returns(returns):
    wins = sum(value for value in returns if value > 0)
    losses = abs(sum(value for value in returns if value < 0))
    if losses > 0:
        return round(wins / losses, 4)
    if wins > 0:
        return "∞"
    return 0.0


def aggregate_ledger_by_strategy(rows, strategy_board):
    lookup = {strategy_key(row): row for row in strategy_board}
    buckets = {}
    for row in rows:
        key = strategy_key(row)
        item = buckets.setdefault(
            key,
            {
                "asset": row.get("asset") or key[0],
                "symbol": row.get("symbol", ""),
                "strategy": row.get("strategy", ""),
                "side": row.get("direction", ""),
                "status": lookup.get(key, {}).get("status", "PAPER"),
                "accepted": 0,
                "accepted_return_sum_pct": 0.0,
                "accepted_profit_factor": 0.0,
                "_returns": [],
                "_last_time": "",
            },
        )
        value = safe_float(row.get("portfolio_return_pct") or row.get("net_return_pct"))
        item["accepted"] += 1
        item["accepted_return_sum_pct"] += value
        item["_returns"].append(value)
        item["_last_time"] = row.get("exit_time") or row.get("recorded_at") or item["_last_time"]

    result = []
    for item in buckets.values():
        returns = item.pop("_returns")
        item["accepted_return_sum_pct"] = round(item["accepted_return_sum_pct"], 4)
        item["accepted_profit_factor"] = profit_factor_from_returns(returns)
        item["last_trade_time"] = item.pop("_last_time")
        result.append(item)

    return sorted(
        result,
        key=lambda row: (
            safe_float(row.get("accepted_return_sum_pct")),
            safe_float(row.get("accepted")),
        ),
        reverse=True,
    )


def unique_ordered(items):
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def translate_off_reason(row):
    reason = str(row.get("reason") or "")
    lower = reason.lower()
    points = []
    hints = []

    match = re.search(r"(?:paper\s+)?return\s+([+-]?[0-9.]+)%?\s*<=\s*([+-]?[0-9.]+)", reason, flags=re.IGNORECASE)
    if match:
        value = match.group(1)
        points.append(f"доходность не положительная: {value}%")
        hints.append("дождаться положительной доходности")

    match = re.search(r"\bpf\s+([0-9.]+)\s*<\s*([0-9.]+)", reason, flags=re.IGNORECASE)
    if match:
        points.append(f"PF слабый: {match.group(1)} < {match.group(2)}")
        hints.append("подождать, пока PF станет выше фильтра")

    match = re.search(r"paper accepted\s+(\d+)\s*<\s*(\d+)", reason, flags=re.IGNORECASE)
    if match:
        points.append(f"мало paper-сделок: {match.group(1)} из {match.group(2)}")
        hints.append("дождаться большего числа зачтенных paper-сделок")

    match = re.search(r"\btrades\s+(\d+)\s*<\s*(\d+)", reason, flags=re.IGNORECASE)
    if match:
        points.append(f"мало сделок в истории: {match.group(1)} из {match.group(2)}")
        hints.append("набрать больше сделок в окне проверки")

    if "paper weak" in lower and not any("paper" in point for point in points):
        points.append("слабая свежая paper-проверка")
        hints.append("проверить следующий цикл paper-торговли")

    if "health" in lower and "30d" in lower:
        points.append("30d здоровье слабое")
        hints.append("дождаться восстановления 30d/60d показателей")

    if "stress" in lower and ("fail" in lower or "failed" in lower):
        points.append("не прошла стресс исполнения")
        hints.append("не включать без улучшения исполнения")

    if "dd" in lower or "drawdown" in lower:
        points.append("просадка выше фильтра")
        hints.append("дождаться снижения просадки")

    if not points:
        points.append("не прошла текущие фильтры монитора")
        if reason:
            hints.append("посмотреть полную причину в Strategy board")
        else:
            hints.append("дождаться нового цикла с данными")

    return " · ".join(unique_ordered(points)[:3]), " · ".join(unique_ordered(hints)[:2])


def build_off_reason_rows(strategy_board):
    rows = []
    for row in strategy_board:
        if str(row.get("status", "")).upper() != "OFF":
            continue
        summary, hint = translate_off_reason(row)
        item = dict(row)
        item["off_summary"] = summary
        item["recovery_hint"] = hint
        rows.append(item)
    return sorted(
        rows,
        key=lambda row: (
            safe_float(row.get("accepted_return_sum_pct")),
            safe_float(row.get("return_30d_pct")),
            -safe_float(row.get("dd_30d_pct")),
        ),
        reverse=True,
    )


def recent_accepted_ledger_rows_by_days(ledger, days=7):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    rows = []
    for row in ledger:
        if row.get("portfolio_status") != "accepted":
            continue
        event_time = trade_event_time(row)
        if not event_time or event_time < cutoff or event_time > now + timedelta(minutes=5):
            continue
        enriched = dict(row)
        enriched["_event_time"] = event_time
        rows.append(enriched)
    return sorted(rows, key=lambda row: row["_event_time"])


def last_display_dates(days=7):
    today = datetime.now(DISPLAY_TZ).date()
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def build_daily_history_rows(ledger_rows, best_now_rows, days=7):
    day_keys = last_display_dates(days)
    day_key_set = set(day_keys)
    rows_by_key = {}
    for row in best_now_rows:
        key = strategy_key(row)
        rows_by_key[key] = {
            "asset": row.get("asset", ""),
            "strategy": row.get("strategy", ""),
            "status": row.get("status", ""),
            "total_7d_pct": 0.0,
            "trades_7d": 0,
            "days": {day: {"return": 0.0, "trades": 0} for day in day_keys},
        }

    if not rows_by_key:
        return [], day_keys

    for row in recent_accepted_ledger_rows_by_days(ledger_rows, days=days):
        key = strategy_key(row)
        if key not in rows_by_key:
            continue
        event_time = row.get("_event_time") or trade_event_time(row)
        if not event_time:
            continue
        day = event_time.astimezone(DISPLAY_TZ).date()
        if day not in day_key_set:
            continue
        value = safe_float(row.get("portfolio_return_pct") or row.get("net_return_pct"))
        item = rows_by_key[key]
        item["total_7d_pct"] += value
        item["trades_7d"] += 1
        item["days"][day]["return"] += value
        item["days"][day]["trades"] += 1

    return sorted(
        rows_by_key.values(),
        key=lambda row: (
            safe_float(row.get("total_7d_pct")),
            safe_float(row.get("trades_7d")),
        ),
        reverse=True,
    ), day_keys


def render_daily_history_table(rows, day_keys):
    if not rows:
        return '<div class="empty-state">Нет TRADE/WATCH стратегий для 7-дневной истории.</div>'
    header_cells = [
        "Монета",
        "Стратегия",
        "Статус",
        "7d PnL",
        "Сделок",
        *[day.strftime("%d.%m") for day in day_keys],
    ]
    header = "".join(f"<th>{html.escape(label)}</th>" for label in header_cells)
    body_rows = []
    for row in rows:
        cells = [
            html.escape(str(row.get("asset", ""))),
            html.escape(str(row.get("strategy", ""))),
            render_badge(row.get("status", "")),
            f'<span class="{numeric_tone(row.get("total_7d_pct"))}">{html.escape(format_decimal(row.get("total_7d_pct"), 2, "%"))}</span>',
            html.escape(str(row.get("trades_7d", 0))),
        ]
        for day in day_keys:
            day_data = row["days"][day]
            if day_data["trades"] == 0:
                cells.append('<span class="muted-value">—</span>')
            else:
                cells.append(
                    f'<span class="{numeric_tone(day_data["return"])}">{html.escape(format_decimal(day_data["return"], 2, "%"))}</span>'
                    f'<span class="day-trades">{day_data["trades"]}</span>'
                )
        body_rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return f'<div class="table-shell daily-history"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def sorted_today_rows(strategy_board):
    rows = [
        row
        for row in strategy_board
        if safe_float(row.get("signals")) > 0 or safe_float(row.get("accepted")) > 0
    ]
    return sorted(
        rows,
        key=lambda row: (
            safe_float(row.get("accepted_return_sum_pct")),
            safe_float(row.get("accepted")),
            safe_float(row.get("signals")),
            safe_float(row.get("return_30d_pct")),
        ),
        reverse=True,
    )


def render_pnl_chart(rows):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    events = []
    cumulative = 0.0
    for row in sorted(rows, key=lambda item: item.get("_event_time") or cutoff):
        event_time = row.get("_event_time") or trade_event_time(row)
        if not event_time:
            continue
        cumulative += safe_float(row.get("portfolio_return_pct") or row.get("net_return_pct"))
        events.append((event_time, cumulative))

    if not events:
        return '<div class="empty-state chart-empty">За последние 24 часа зачтенных paper-сделок нет.</div>'

    width = 1000
    height = 240
    pad_x = 28
    pad_y = 24
    values = [0.0] + [value for _, value in events]
    min_y = min(values)
    max_y = max(values)
    if min_y == max_y:
        min_y -= 1.0
        max_y += 1.0
    padding = (max_y - min_y) * 0.12
    min_y -= padding
    max_y += padding
    span_seconds = max((now - cutoff).total_seconds(), 1)

    def x_pos(moment):
        ratio = (moment - cutoff).total_seconds() / span_seconds
        ratio = max(0.0, min(1.0, ratio))
        return pad_x + ratio * (width - pad_x * 2)

    def y_pos(value):
        ratio = (value - min_y) / (max_y - min_y)
        return height - pad_y - ratio * (height - pad_y * 2)

    points = [(pad_x, y_pos(0.0))] + [(x_pos(moment), y_pos(value)) for moment, value in events]
    point_attr = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    zero_y = y_pos(0.0)
    area_points = f"{pad_x:.2f},{zero_y:.2f} {point_attr} {points[-1][0]:.2f},{zero_y:.2f}"
    final_value = events[-1][1]
    line_class = "positive-line" if final_value >= 0 else "negative-line"
    area_class = "positive-area" if final_value >= 0 else "negative-area"
    circles = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4"></circle>'
        for x, y in points[1:][-18:]
    )
    return f"""
        <div class="chart-card">
          <div class="chart-meta">
            <span>Старт: {html.escape(display_time(cutoff.isoformat()))}</span>
            <strong class="{numeric_tone(final_value)}">{html.escape(format_decimal(final_value, 2, "%"))}</strong>
            <span>Сейчас: {html.escape(display_time(now.isoformat()))}</span>
          </div>
          <svg class="pnl-chart" viewBox="0 0 {width} {height}" role="img" aria-label="PnL за последние 24 часа">
            <line class="zero-line" x1="{pad_x}" x2="{width - pad_x}" y1="{zero_y:.2f}" y2="{zero_y:.2f}"></line>
            <polyline class="{area_class}" points="{area_points}"></polyline>
            <polyline class="{line_class}" points="{point_attr}"></polyline>
            <g class="{line_class}">{circles}</g>
          </svg>
        </div>
    """


def sorted_best_now_rows(strategy_board):
    rows = [row for row in strategy_board if str(row.get("status", "")).upper() in {"TRADE", "WATCH"}]
    status_order = {"TRADE": 0, "WATCH": 1}
    return sorted(
        rows,
        key=lambda row: (
            status_order.get(str(row.get("status", "")).upper(), 2),
            -safe_float(row.get("accepted_return_sum_pct")),
            -safe_float(row.get("return_30d_pct")),
            -safe_float(row.get("pf_30d")),
            safe_float(row.get("dd_30d_pct")),
        ),
    )


def filter_strategy_rows(rows, status_filter):
    if status_filter == "ALL":
        return rows
    return [row for row in rows if str(row.get("status", "")).upper() == status_filter]


def render_status_filters(status_filter, counts):
    tone_by_status = {"ALL": "secondary", "TRADE": "success", "WATCH": "warning", "OFF": "danger"}
    links = []
    for status in STATUS_FILTERS:
        active = " active" if status == status_filter else ""
        links.append(
            f'<a class="filter-pill {tone_by_status.get(status, "secondary")}{active}" '
            f'href="/?status={status}">{status}<span>{counts.get(status, 0)}</span></a>'
        )
    return f'<nav class="filter-row" aria-label="Strategy status filters">{"".join(links)}</nav>'


def best_today_summary(today_rows):
    if not today_rows:
        return "нет", "сигналов не было"
    best = today_rows[0]
    asset = best.get("asset") or best.get("symbol") or "-"
    strategy = best.get("strategy") or "-"
    result = format_decimal(best.get("accepted_return_sum_pct"), 2, "%")
    return str(asset), f"{strategy} / {result}"


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


def render_dashboard(state, status_filter="ALL"):
    ledger_rows = state.get("ledger", [])
    ledger = list(reversed(ledger_rows))
    monitor = state.get("latest_monitor", [])
    summary = state.get("latest_summary", [])
    strategy_board = build_strategy_board(summary, monitor)
    status_filter = normalize_status_filter(status_filter)
    status_counts = count_by_status(strategy_board)
    today_ledger_rows = recent_accepted_ledger_rows(ledger_rows, hours=24)
    today_rows = aggregate_ledger_by_strategy(today_ledger_rows, strategy_board)
    best_now_rows = sorted_best_now_rows(strategy_board)
    off_reason_rows = build_off_reason_rows(strategy_board)
    daily_history_rows, daily_history_days = build_daily_history_rows(ledger_rows, best_now_rows, days=7)
    daily_history_html = render_daily_history_table(daily_history_rows, daily_history_days)
    filtered_strategy_board = filter_strategy_rows(strategy_board, status_filter)
    ledger_summary = state.get("ledger_summary", {})
    today_pnl = sum(safe_float(row.get("portfolio_return_pct") or row.get("net_return_pct")) for row in today_ledger_rows)
    today_trades = len(today_ledger_rows)
    best_today_value, best_today_detail = best_today_summary(today_rows)
    pnl_chart_html = render_pnl_chart(today_ledger_rows)
    last_error = state.get("last_error") or ""
    storage_error = state.get("storage_error") or ""
    last_run = display_time(state.get("last_run_at")) if state.get("last_run_at") else "not yet"
    modules = state.get("modules", [])
    modules_html = "".join(render_badge(module, "secondary") for module in modules)
    monitor_count = int(state.get("monitor_strategy_count") or len(strategy_board))
    paper_module_count = len(modules)
    monitor_every = max(1, int(state.get("monitor_every_cycles") or 1))
    last_monitor_raw = state.get("last_monitor_run_at") or (state.get("last_run_at") if monitor else "")
    last_monitor_run = display_time_minute(last_monitor_raw) if last_monitor_raw else "ещё не было"
    stopped_alert_html = ""
    if not state.get("running"):
        stopped_alert_html = f"""
      <section class="status-alert">
        <div>
          <div class="status-alert-title">Монитор остановлен</div>
          <p>Paper-проверка сейчас не выполняется. Последний запуск: {html.escape(str(last_run))}.</p>
        </div>
        <button class="primary" onclick="post('/api/start')">Запустить</button>
      </section>
"""
    cycle_alert_html = ""
    if state.get("in_cycle"):
        cycle_alert_html = """
      <section class="cycle-alert">
        <div>
          <div class="cycle-alert-title">Идет обновление данных</div>
          <p>Сервер сейчас проверяет стратегии. Таблицы обновятся после завершения цикла.</p>
        </div>
      </section>
"""
    metrics_html = "\n".join(
        [
            render_metric("Стратегий в мониторинге", monitor_count, None, "полный список"),
            render_metric("Paper-модулей", paper_module_count, None, "реально исполняются"),
            render_metric("Полный монитор", last_monitor_run, None, f"раз в {monitor_every} циклов"),
            render_metric("TRADE", status_counts.get("TRADE", 0), "success", "можно рассматривать"),
            render_metric("WATCH", status_counts.get("WATCH", 0), "warning", "наблюдаем"),
            render_metric("OFF", status_counts.get("OFF", 0), "danger", "выключено"),
            render_metric("Сегодня PnL", format_decimal(today_pnl, 2, "%"), None, "paper 24h"),
            render_metric("Сегодня сделок", today_trades, None, "accepted"),
            render_metric("Лучший сегодня", best_today_value, None, best_today_detail),
        ]
    )
    ledger_metrics_html = "\n".join(
        [
            render_metric("Ledger return", f"{ledger_summary.get('portfolio_return_sum_pct', 0.0)}%", None, "paper ledger"),
            render_metric("Accepted trades", ledger_summary.get("accepted_trades", 0), None, "deduplicated"),
            render_metric("Win rate", f"{ledger_summary.get('win_rate_pct', 0.0)}%", None, "accepted trades"),
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
    .status-alert {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-top: 18px;
      border: 1px solid rgb(248 113 113 / 0.38);
      border-radius: 8px;
      background: rgb(248 113 113 / 0.12);
      padding: 16px;
    }
    .status-alert-title {
      margin-bottom: 4px;
      color: hsl(0 93.5% 81.8%);
      font-size: 18px;
      font-weight: 750;
    }
    .cycle-alert {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-top: 18px;
      border: 1px solid rgb(250 204 21 / 0.28);
      border-radius: 8px;
      background: rgb(250 204 21 / 0.08);
      padding: 14px 16px;
    }
    .cycle-alert-title {
      margin-bottom: 4px;
      color: hsl(47.9 95.8% 73.1%);
      font-size: 16px;
      font-weight: 750;
    }
    .section { padding: 22px 0; border-bottom: 1px solid var(--border); }
    .section-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
    .section-copy { color: var(--muted-foreground); font-size: 13px; }
    .filter-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .filter-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      height: 34px;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 0 12px;
      color: var(--muted-foreground);
      text-decoration: none;
      font-size: 12px;
      font-weight: 700;
    }
    .filter-pill span {
      min-width: 22px;
      height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: rgb(148 163 184 / 0.12);
      color: var(--foreground);
    }
    .filter-pill.success.active, .filter-pill.success:hover { border-color: rgb(34 197 94 / 0.4); background: rgb(34 197 94 / 0.12); color: hsl(142.1 76.2% 73.1%); }
    .filter-pill.warning.active, .filter-pill.warning:hover { border-color: rgb(250 204 21 / 0.4); background: rgb(250 204 21 / 0.12); color: hsl(47.9 95.8% 73.1%); }
    .filter-pill.danger.active, .filter-pill.danger:hover { border-color: rgb(248 113 113 / 0.4); background: rgb(248 113 113 / 0.12); color: hsl(0 93.5% 81.8%); }
    .filter-pill.secondary.active, .filter-pill.secondary:hover { background: var(--secondary); color: var(--secondary-foreground); }
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
    .metric-value.compact { font-size: 18px; line-height: 1.25; }
    .metric-detail { color: var(--muted-foreground); font-size: 12px; }
    .ledger-metrics { margin-bottom: 12px; }
    .chart-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      padding: 14px;
    }
    .chart-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      color: var(--muted-foreground);
      font-size: 12px;
    }
    .chart-meta strong {
      color: var(--foreground);
      font-size: 22px;
      line-height: 1;
    }
    .pnl-chart {
      width: 100%;
      height: 220px;
      display: block;
      overflow: visible;
    }
    .pnl-chart .zero-line {
      stroke: rgb(148 163 184 / 0.22);
      stroke-width: 2;
      stroke-dasharray: 7 7;
    }
    .pnl-chart .positive-line,
    .pnl-chart .negative-line {
      fill: none;
      stroke-width: 4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .pnl-chart .positive-line {
      color: hsl(142.1 76.2% 73.1%);
      stroke: hsl(142.1 76.2% 73.1%);
    }
    .pnl-chart .negative-line {
      color: hsl(0 93.5% 81.8%);
      stroke: hsl(0 93.5% 81.8%);
    }
    .pnl-chart .positive-area,
    .pnl-chart .negative-area {
      stroke: none;
      opacity: 0.14;
    }
    .pnl-chart .positive-area {
      fill: hsl(142.1 76.2% 73.1%);
    }
    .pnl-chart .negative-area {
      fill: hsl(0 93.5% 81.8%);
    }
    .pnl-chart circle {
      fill: var(--background);
      stroke: currentColor;
      stroke-width: 3;
    }
    .chart-empty {
      min-height: 180px;
    }
    .table-gap {
      height: 12px;
    }
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
    .today-board table { min-width: 860px; table-layout: fixed; }
    .best-now table { min-width: 1040px; table-layout: fixed; }
    .today-board th, .today-board td, .best-now th, .best-now td { white-space: nowrap; }
    .off-reasons table { min-width: 920px; table-layout: fixed; }
    .off-reasons th, .off-reasons td { white-space: nowrap; }
    .off-reasons th:nth-child(1), .off-reasons td:nth-child(1) { width: 82px; }
    .off-reasons th:nth-child(2), .off-reasons td:nth-child(2) { width: 210px; }
    .off-reasons th:nth-child(3), .off-reasons td:nth-child(3) { width: 360px; }
    .off-reasons th:nth-child(4), .off-reasons td:nth-child(4) { width: 320px; }
    .daily-history table { min-width: 1120px; table-layout: fixed; }
    .daily-history th, .daily-history td { white-space: nowrap; }
    .daily-history th:nth-child(1), .daily-history td:nth-child(1) { width: 78px; }
    .daily-history th:nth-child(2), .daily-history td:nth-child(2) { width: 210px; }
    .daily-history th:nth-child(3), .daily-history td:nth-child(3) { width: 86px; }
    .daily-history th:nth-child(4), .daily-history td:nth-child(4) { width: 86px; }
    .daily-history th:nth-child(5), .daily-history td:nth-child(5) { width: 72px; }
    .day-trades {
      margin-left: 6px;
      color: var(--muted-foreground);
      font-size: 11px;
      font-weight: 600;
    }
    .strategy-board table { min-width: 1180px; table-layout: fixed; }
    .strategy-board th, .strategy-board td { white-space: nowrap; }
    .strategy-board th:nth-child(1), .strategy-board td:nth-child(1) { width: 72px; }
    .strategy-board th:nth-child(2), .strategy-board td:nth-child(2) { width: 170px; }
    .strategy-board th:nth-child(3), .strategy-board td:nth-child(3) { width: 78px; }
    .strategy-board th:nth-child(4), .strategy-board td:nth-child(4) { width: 82px; }
    .strategy-board th:nth-child(5), .strategy-board td:nth-child(5) { width: 72px; }
    .strategy-board th:nth-child(6), .strategy-board td:nth-child(6) { width: 72px; }
    .strategy-board th:nth-child(7), .strategy-board td:nth-child(7) { width: 86px; }
    .strategy-board th:nth-child(8), .strategy-board td:nth-child(8) { width: 76px; }
    .strategy-board th:nth-child(9), .strategy-board td:nth-child(9) { width: 86px; }
    .strategy-board th:nth-child(10), .strategy-board td:nth-child(10) { width: 76px; }
    .strategy-board th:nth-child(11), .strategy-board td:nth-child(11) { width: 82px; }
    .strategy-board th:nth-child(12), .strategy-board td:nth-child(12) { width: 96px; }
    .strategy-board th:nth-child(13), .strategy-board td:nth-child(13) { width: 260px; }
    .empty-state {
      min-height: 96px;
      display: grid;
      place-items: center;
      border: 1px dashed var(--border);
      border-radius: 8px;
      color: var(--muted-foreground);
      background: rgb(148 163 184 / 0.03);
    }
    .reason {
      display: block;
      max-width: 100%;
      overflow: hidden;
      color: var(--muted-foreground);
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .positive { color: hsl(142.1 76.2% 73.1%); font-weight: 650; }
    .negative { color: hsl(0 93.5% 81.8%); font-weight: 650; }
    .muted-value { color: var(--muted-foreground); }
    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      color: var(--muted-foreground);
      padding: 14px;
      font-size: 13px;
      line-height: 1.45;
    }
    .diagnostics-grid {
      display: grid;
      grid-template-columns: minmax(240px, 0.75fr) minmax(320px, 1.25fr) minmax(260px, 1fr);
      gap: 12px;
      align-items: start;
    }
    .diagnostic-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      padding: 14px;
    }
    .diagnostic-card h3 {
      margin: 0 0 10px;
      color: var(--foreground);
      font-size: 14px;
      line-height: 1.2;
      font-weight: 700;
    }
    .diagnostic-lines {
      display: grid;
      gap: 10px;
    }
    .diagnostic-line {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted-foreground);
      font-size: 13px;
    }
    .diagnostic-line span:first-child {
      font-weight: 650;
      text-transform: uppercase;
    }
    .diagnostic-card pre {
      max-height: 220px;
      overflow: auto;
    }
    @media (max-width: 760px) {
      .shell { padding: 16px; }
      .topbar, .status-alert, .cycle-alert, .section-header { align-items: stretch; flex-direction: column; }
      .actions { justify-content: flex-start; }
      h1 { font-size: 26px; }
      .diagnostics-grid { grid-template-columns: 1fr; }
      .chart-meta { align-items: flex-start; flex-direction: column; }
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
      {stopped_alert_html}
      {cycle_alert_html}

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
            <h2>Сегодня, 24 часа</h2>
            <p class="section-copy">Только реальные зачтенные paper-сделки из ledger, закрытые за последние 24 часа.</p>
          </div>
        </div>
        {pnl_chart_html}
        <div class="table-gap"></div>
        {render_table(today_rows, ['asset', 'strategy', 'side', 'status', 'accepted', 'accepted_return_sum_pct', 'accepted_profit_factor', 'last_trade_time'], 20, 'today-board')}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Лучшие сейчас</h2>
            <p class="section-copy">Только TRADE/WATCH, отсортировано по текущему paper-результату, 30d доходности и PF.</p>
          </div>
        </div>
        {render_table(best_now_rows, ['asset', 'strategy', 'side', 'status', 'accepted_return_sum_pct', 'accepted_profit_factor', 'return_30d_pct', 'pf_30d', 'dd_30d_pct', 'trades_30d', 'reason'], 12, 'best-now')}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Почему OFF</h2>
            <p class="section-copy">Короткий перевод причин отключения. Стратегия продолжает мониториться и может вернуться в WATCH/TRADE.</p>
          </div>
        </div>
        {render_table(off_reason_rows, ['asset', 'strategy', 'off_summary', 'recovery_hint'], 30, 'off-reasons')}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>История 7 дней</h2>
            <p class="section-copy">Дневной paper-PnL по текущим TRADE/WATCH стратегиям. Маленькое число рядом с днем — количество сделок.</p>
          </div>
        </div>
        {daily_history_html}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Strategy board</h2>
            <p class="section-copy">Полная таблица стратегий. Фильтр: {html.escape(status_filter)}.</p>
          </div>
          {render_status_filters(status_filter, status_counts)}
        </div>
        {render_table(filtered_strategy_board, ['asset', 'strategy', 'side', 'status', 'signals', 'accepted', 'accepted_return_sum_pct', 'accepted_profit_factor', 'return_30d_pct', 'pf_30d', 'dd_30d_pct', 'trades_30d', 'reason'], 50, 'strategy-board')}
      </section>

      <section class="section">
        <div class="section-header">
          <div>
            <h2>Latest accepted paper trades</h2>
            <p class="section-copy">Накопительная история paper-ledger и последние зачтенные сделки.</p>
          </div>
        </div>
        <div class="metrics-grid ledger-metrics">
          {ledger_metrics_html}
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
        <div class="diagnostics-grid">
          <section class="diagnostic-card">
            <h3>Система</h3>
            <div class="diagnostic-lines">
              <div class="diagnostic-line">
                <span>Storage</span>
                {render_badge(state.get("storage_backend", "local_json"), tone_class(state.get("storage_backend")))}
              </div>
              <div class="diagnostic-line">
                <span>Auth</span>
                {render_badge("enabled" if state.get("auth_enabled") else "disabled", tone_class("enabled" if state.get("auth_enabled") else "disabled"))}
              </div>
            </div>
          </section>
          <section class="diagnostic-card">
            <h3>Last error</h3>
            <pre>{html.escape(last_error) if last_error else 'None'}</pre>
          </section>
          <section class="diagnostic-card">
            <h3>Storage error</h3>
            <pre>{html.escape(storage_error) if storage_error else 'None'}</pre>
          </section>
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
    parser.add_argument(
        "--monitor-universe",
        choices=["all", "modules"],
        default="all",
        help="Use all fixed strategies in the operational monitor, or only the selected paper modules.",
    )
    parser.add_argument(
        "--monitor-every-cycles",
        type=int,
        default=15,
        help="Run the heavier operational monitor every N paper cycles; manual Run Once always runs it.",
    )
    parser.add_argument("--monitor-days", type=int, default=7)
    parser.add_argument("--monitor-stress-window", type=int, default=7)
    parser.add_argument("--monitor-skip-stress", action="store_true")
    args = parser.parse_args()
    if RIF_ONLY_MODE:
        args.modules = ["RIF"]
        args.monitor_universe = "modules"
    return args


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
