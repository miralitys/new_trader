#!/usr/bin/env python3
"""Stage 3 forward paper monitor for strategy validation.

The monitor is deliberately paper-only. It stores strategy registrations,
incoming signals, skipped reasons, paper trades, trade events and computed
metrics. If DATABASE_URL is configured it mirrors the same state into Postgres;
otherwise it uses a local JSON file.
"""

import csv
import importlib
import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


KLINE_ENDPOINTS = {
    "futures_global": "https://fapi.binance.com/fapi/v1/klines",
    "spot_global": "https://api.binance.com/api/v3/klines",
    "data_api_spot": "https://data-api.binance.vision/api/v3/klines",
    "spot_us": "https://api.binance.us/api/v3/klines",
}
INTERVAL_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
}
DEFAULT_CONFIG = {
    "trading_mode": "paper",
    "initial_equity": 1000.0,
    "fee_pct": 0.0004,
    "slippage_pct": 0.0002,
    "max_open_positions": 5,
    "max_same_direction_positions": 3,
    "max_positions_per_coin": 1,
    "max_daily_loss_pct": 0.01,
    "max_weekly_loss_pct": 0.03,
    "core_risk_per_trade": 0.0025,
    "liquidity_risk_per_trade": 0.001,
    "watch_risk_per_trade": 0.0,
    "min_forward_trades_to_evaluate": 30,
    "min_portfolio_trades_to_evaluate": 100,
    "max_spread": 0.0015,
    "min_liquidity": 20000.0,
    "funding_danger_threshold": 0.0010,
    "time_stop_minutes": 24 * 60,
    "max_notional_pct": 1.0,
    "signal_runner_enabled": True,
    "signal_runner_market": "data_api_spot",
    "signal_runner_include_watch": False,
    "signal_runner_limit": 260,
    "signal_runner_min_bars": 220,
    "signal_runner_user_agent": "stage3-forward-monitor/1.0",
}

TRADE_ENABLED_STATUSES = {"core", "liquidity_risk"}
REGISTRY_STATUSES = {"core", "liquidity_risk", "watch", "disabled"}
SIGNAL_FIELDS = (
    "coin",
    "strategy",
    "timeframe",
    "direction",
    "signal_time",
    "candle_close_time",
    "entry_price",
    "stop_price",
    "take_profit_price",
    "market_regime",
    "indicators_snapshot",
    "spread",
    "volume",
    "funding",
    "expected_R",
)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def safe_float(value, default=0.0):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def json_value(value, default=None):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return default
    return default


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


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_symbol(value):
    text = str(value or "").strip().upper()
    if not text:
        return ""
    return text if text.endswith("USDT") else f"{text}USDT"


def normalize_direction(value):
    text = str(value or "").strip().lower()
    if text in {"buy", "long", "l"}:
        return "long"
    if text in {"sell", "short", "s"}:
        return "short"
    return text


def normalize_timeframe(value):
    return str(value or "").strip().lower()


def timeframe_minutes(value):
    return INTERVAL_MINUTES.get(normalize_timeframe(value), 0)


def registry_key(coin, strategy, timeframe):
    return "|".join([normalize_symbol(coin), str(strategy or "").strip(), normalize_timeframe(timeframe)])


def id_from_key(prefix, key):
    clean = "".join(ch if ch.isalnum() else "_" for ch in key).strip("_").lower()
    return f"{prefix}_{clean[:180]}"


def now_id(prefix):
    return f"{prefix}_{int(time.time() * 1000)}"


def profit_factor_value(wins, losses):
    win_sum = sum(wins)
    loss_sum = abs(sum(losses))
    if loss_sum > 0:
        return win_sum / loss_sum
    if win_sum > 0:
        return "∞"
    return 0.0


def default_state(config):
    now = utc_now()
    initial = safe_float(config.get("initial_equity"), 1000.0)
    return {
        "created_at": now,
        "updated_at": now,
        "config": dict(config),
        "registry": [],
        "signals": [],
        "paper_trades": [],
        "trade_events": [],
        "daily_metrics": [],
        "strategy_metrics": [],
        "generated_signal_keys": [],
        "runner": {
            "enabled": bool(config.get("signal_runner_enabled", True)),
            "market": config.get("signal_runner_market", "data_api_spot"),
            "last_run_at": "",
            "last_error": "",
            "last_summary": {},
            "cycles": 0,
        },
        "portfolio_state": {
            "id": "default",
            "trading_mode": config.get("trading_mode", "paper"),
            "starting_equity": initial,
            "current_equity": initial,
            "open_positions": 0,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "updated_at": now,
        },
        "storage_backend": "local_json",
        "storage_error": "",
    }


class Stage3ForwardMonitor:
    def __init__(self, root, data_dir, state_path, registry_source, config=None, database_url=""):
        self.root = Path(root)
        self.data_dir = Path(data_dir)
        self.state_path = Path(state_path)
        self.registry_source = Path(registry_source)
        self.config = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self.database_url = (database_url or "").strip()
        self.lock = threading.RLock()
        self.driver = None
        self.db_module = None
        self.storage_error = ""
        if self.database_url:
            try:
                self.driver, self.db_module = self.import_driver()
                self.init_schema()
            except Exception as exc:
                self.driver = None
                self.db_module = None
                self.storage_error = f"Postgres disabled for Stage 3, using local JSON: {exc}"

        self.state = self.load_state()
        self.state["config"] = dict(self.config)
        self.state["storage_backend"] = "postgres" if self.driver else "local_json"
        self.state["storage_error"] = self.storage_error
        self.state.setdefault("generated_signal_keys", [])
        self.state.setdefault(
            "runner",
            {
                "enabled": bool(self.config.get("signal_runner_enabled", True)),
                "market": self.config.get("signal_runner_market", "data_api_spot"),
                "last_run_at": "",
                "last_error": "",
                "last_summary": {},
                "cycles": 0,
            },
        )
        self.ensure_portfolio_state()
        self.seed_registry()
        self.save_state()

    def import_driver(self):
        try:
            return "psycopg", importlib.import_module("psycopg")
        except ImportError:
            pass
        try:
            return "psycopg2", importlib.import_module("psycopg2")
        except ImportError:
            raise ImportError("No Postgres driver installed.")

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
                    CREATE TABLE IF NOT EXISTS strategy_registry (
                        id text PRIMARY KEY,
                        coin text NOT NULL,
                        strategy text NOT NULL,
                        timeframe text NOT NULL,
                        status text NOT NULL,
                        direction text,
                        market_regime text,
                        risk_config jsonb NOT NULL DEFAULT '{}'::jsonb,
                        metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                        enabled boolean NOT NULL DEFAULT true,
                        created_at timestamptz NOT NULL DEFAULT now(),
                        updated_at timestamptz NOT NULL DEFAULT now(),
                        UNIQUE (coin, strategy, timeframe)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS signals (
                        id text PRIMARY KEY,
                        received_at timestamptz NOT NULL DEFAULT now(),
                        coin text NOT NULL,
                        strategy text NOT NULL,
                        timeframe text NOT NULL,
                        direction text NOT NULL,
                        signal_time timestamptz,
                        candle_close_time timestamptz,
                        entry_price double precision,
                        stop_price double precision,
                        take_profit_price double precision,
                        market_regime text,
                        indicators_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
                        spread double precision,
                        volume double precision,
                        funding double precision,
                        expected_r double precision,
                        status text NOT NULL,
                        skip_reason text,
                        raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paper_trades (
                        id text PRIMARY KEY,
                        source_signal_id text,
                        coin text NOT NULL,
                        strategy text NOT NULL,
                        timeframe text NOT NULL,
                        direction text NOT NULL,
                        status text NOT NULL,
                        entry_time timestamptz,
                        exit_time timestamptz,
                        entry_price double precision,
                        stop_price double precision,
                        take_profit_price double precision,
                        exit_price double precision,
                        qty double precision,
                        notional double precision,
                        risk_amount double precision,
                        risk_pct double precision,
                        fee_pct double precision,
                        slippage_pct double precision,
                        funding double precision,
                        gross_pnl double precision,
                        fees double precision,
                        slippage_cost double precision,
                        funding_pnl double precision,
                        net_pnl double precision,
                        net_pnl_pct double precision,
                        r_multiple double precision,
                        exit_reason text,
                        duration_min double precision,
                        equity_before double precision,
                        equity_after double precision,
                        metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                        created_at timestamptz NOT NULL DEFAULT now(),
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trade_events (
                        id text PRIMARY KEY,
                        trade_id text,
                        signal_id text,
                        event_time timestamptz NOT NULL DEFAULT now(),
                        event_type text NOT NULL,
                        event_json jsonb NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_metrics (
                        metric_date date PRIMARY KEY,
                        total_signals integer NOT NULL DEFAULT 0,
                        skipped_signals integer NOT NULL DEFAULT 0,
                        opened_trades integer NOT NULL DEFAULT 0,
                        closed_trades integer NOT NULL DEFAULT 0,
                        net_pnl double precision NOT NULL DEFAULT 0,
                        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_metrics (
                        id text PRIMARY KEY,
                        coin text,
                        strategy text,
                        timeframe text,
                        direction text,
                        regime text,
                        total_signals integer NOT NULL DEFAULT 0,
                        skipped_signals integer NOT NULL DEFAULT 0,
                        opened_trades integer NOT NULL DEFAULT 0,
                        closed_trades integer NOT NULL DEFAULT 0,
                        win_rate double precision,
                        net_pnl double precision,
                        profit_factor double precision,
                        max_dd_pct double precision,
                        average_r double precision,
                        longest_losing_streak integer,
                        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_state (
                        id text PRIMARY KEY,
                        trading_mode text NOT NULL,
                        current_equity double precision NOT NULL,
                        starting_equity double precision NOT NULL,
                        open_positions integer NOT NULL DEFAULT 0,
                        daily_pnl double precision NOT NULL DEFAULT 0,
                        weekly_pnl double precision NOT NULL DEFAULT 0,
                        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )

    def fetch_dicts(self, query, params=None):
        if not self.driver:
            return []
        with closing(self.connect()) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                rows = cur.fetchall()
                names = [desc[0] for desc in cur.description]
        return [dict(zip(names, row)) for row in rows]

    def load_state(self):
        state = default_state(self.config)
        if self.driver:
            try:
                registry = self.fetch_dicts(
                    """
                    SELECT id, coin, strategy, timeframe, status, direction, market_regime,
                           risk_config, metadata, enabled, created_at, updated_at
                    FROM strategy_registry
                    ORDER BY coin, strategy, timeframe
                    """
                )
                signals = self.fetch_dicts(
                    """
                    SELECT id, received_at, coin, strategy, timeframe, direction, signal_time,
                           candle_close_time, entry_price, stop_price, take_profit_price,
                           market_regime, indicators_snapshot, spread, volume, funding,
                           expected_r, status, skip_reason, raw_payload
                    FROM signals
                    ORDER BY received_at DESC
                    LIMIT 1000
                    """
                )
                trades = self.fetch_dicts(
                    """
                    SELECT *
                    FROM paper_trades
                    ORDER BY created_at DESC
                    LIMIT 1000
                    """
                )
                events = self.fetch_dicts(
                    """
                    SELECT id, trade_id, signal_id, event_time, event_type, event_json
                    FROM trade_events
                    ORDER BY event_time DESC
                    LIMIT 1000
                    """
                )
                portfolio = self.fetch_dicts(
                    """
                    SELECT id, trading_mode, current_equity, starting_equity, open_positions,
                           daily_pnl, weekly_pnl, payload, updated_at
                    FROM portfolio_state
                    WHERE id = 'default'
                    LIMIT 1
                    """
                )
                if registry:
                    state["registry"] = [self.normalize_db_row(row) for row in registry]
                if signals:
                    state["signals"] = [self.normalize_db_row(row) for row in signals]
                if trades:
                    state["paper_trades"] = [self.normalize_db_row(row) for row in trades]
                if events:
                    state["trade_events"] = [self.normalize_db_row(row) for row in events]
                if portfolio:
                    state["portfolio_state"] = self.normalize_db_row(portfolio[0])
                return state
            except Exception as exc:
                self.storage_error = f"Stage 3 DB load failed, using local JSON: {exc}"
        local = load_json(self.state_path, state)
        if not isinstance(local, dict):
            return state
        return local

    def normalize_db_row(self, row):
        item = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                item[key] = value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
            elif key in {"risk_config", "metadata", "indicators_snapshot", "raw_payload", "event_json", "payload"}:
                item[key] = json_value(value, {})
            else:
                item[key] = value
        return item

    def ensure_portfolio_state(self):
        portfolio = self.state.get("portfolio_state") or {}
        initial = safe_float(self.config.get("initial_equity"), 1000.0)
        current = safe_float(portfolio.get("current_equity"), initial)
        portfolio.update(
            {
                "id": portfolio.get("id") or "default",
                "trading_mode": self.config.get("trading_mode", "paper"),
                "starting_equity": safe_float(portfolio.get("starting_equity"), initial),
                "current_equity": current or initial,
                "open_positions": len(self.open_trades()),
                "daily_pnl": self.period_pnl(days=1),
                "weekly_pnl": self.period_pnl(days=7),
                "updated_at": utc_now(),
            }
        )
        self.state["portfolio_state"] = portfolio
        self.mirror_portfolio_state(portfolio)

    def seed_registry(self):
        registry = self.state.get("registry") or []
        existing = {registry_key(row.get("coin"), row.get("strategy"), row.get("timeframe")) for row in registry}
        rows = read_csv(self.registry_source)
        if not rows:
            return
        added = []
        for row in rows:
            coin = normalize_symbol(row.get("symbol"))
            strategy = str(row.get("strategy") or "").strip()
            timeframe = normalize_timeframe(row.get("timeframe"))
            if not coin or not strategy or not timeframe:
                continue
            key = registry_key(coin, strategy, timeframe)
            if key in existing:
                continue
            status = self.status_from_stage2_row(row)
            metadata = {
                "stage2_decision": row.get("decision", ""),
                "tier": row.get("tier", ""),
                "variant": row.get("variant", ""),
                "score": safe_float(row.get("score")),
                "trades": safe_int(row.get("trades")),
                "return_pct": safe_float(row.get("return_pct")),
                "pf": safe_float(row.get("pf")),
                "max_dd_pct": safe_float(row.get("max_dd_pct")),
                "win_rate_pct": safe_float(row.get("win_rate_pct")),
                "liquidity_label": row.get("liquidity_label", ""),
                "avg_minute_quote_volume": safe_float(row.get("avg_minute_quote_volume")),
                "walk_forward_status": row.get("walk_forward_status", ""),
                "allowed_regimes": ["any"],
            }
            item = {
                "id": id_from_key("sr", key),
                "coin": coin,
                "strategy": strategy,
                "timeframe": timeframe,
                "status": status,
                "direction": self.direction_from_strategy(strategy),
                "market_regime": "any",
                "risk_config": dict(self.config),
                "metadata": metadata,
                "enabled": status != "disabled",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            added.append(item)
            existing.add(key)
        if added:
            self.state["registry"] = sorted(registry + added, key=lambda item: (item["coin"], item["strategy"], item["timeframe"]))
            self.mirror_registry(added)

    def status_from_stage2_row(self, row):
        decision = str(row.get("decision") or "").upper()
        liquidity = str(row.get("liquidity_label") or "").lower()
        if decision == "TRADE_CANDIDATE":
            return "core" if liquidity in {"strong", "high"} else "liquidity_risk"
        if decision.startswith("WATCH"):
            return "watch"
        return "disabled"

    def direction_from_strategy(self, strategy):
        text = str(strategy or "").lower()
        if "weakness" in text or "short" in text:
            return "short"
        if "strength" in text or "long" in text:
            return "long"
        return "both"

    def save_state(self):
        self.state["updated_at"] = utc_now()
        self.state["storage_backend"] = "postgres" if self.driver else "local_json"
        self.state["storage_error"] = self.storage_error
        save_json(self.state_path, self.state)

    def registry_lookup(self):
        return {
            registry_key(row.get("coin"), row.get("strategy"), row.get("timeframe")): row
            for row in self.state.get("registry", [])
        }

    def open_trades(self):
        return [row for row in self.state.get("paper_trades", []) if str(row.get("status")).upper() == "OPEN"]

    def closed_trades(self):
        return [row for row in self.state.get("paper_trades", []) if str(row.get("status")).upper() == "CLOSED"]

    def period_pnl(self, days):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        total = 0.0
        for trade in self.closed_trades():
            exit_time = parse_datetime(trade.get("exit_time"))
            if exit_time and exit_time >= cutoff:
                total += safe_float(trade.get("net_pnl"))
        return total

    def ingest_signals(self, payload):
        signals = payload if isinstance(payload, list) else [payload]
        results = []
        with self.lock:
            for item in signals:
                result = self.ingest_signal(item if isinstance(item, dict) else {})
                results.append(result)
            self.ensure_portfolio_state()
            self.refresh_metrics()
            self.save_state()
        return {"status": "ok", "received": len(results), "results": results}

    def ingest_signal(self, payload):
        signal = self.normalize_signal(payload)
        missing = [field for field in SIGNAL_FIELDS if field not in signal or signal[field] in (None, "")]
        if missing:
            signal["status"] = "SKIPPED"
            signal["skip_reason"] = "missing_fields:" + ",".join(missing)
            self.record_signal(signal)
            return {"signal_id": signal["id"], "status": "SKIPPED", "reason": signal["skip_reason"]}

        validation_reason = self.validate_signal(signal)
        if validation_reason:
            signal["status"] = "SKIPPED"
            signal["skip_reason"] = validation_reason
            self.record_signal(signal)
            return {"signal_id": signal["id"], "status": "SKIPPED", "reason": validation_reason}

        trade, skip_reason = self.create_paper_trade(signal)
        if skip_reason:
            signal["status"] = "SKIPPED"
            signal["skip_reason"] = skip_reason
            self.record_signal(signal)
            return {"signal_id": signal["id"], "status": "SKIPPED", "reason": skip_reason}

        signal["status"] = "OPENED"
        signal["skip_reason"] = ""
        self.record_signal(signal)
        self.state["paper_trades"].insert(0, trade)
        self.record_event(trade["id"], signal["id"], "OPEN", {"trade": trade})
        self.mirror_trade(trade)
        return {"signal_id": signal["id"], "trade_id": trade["id"], "status": "OPENED"}

    def normalize_signal(self, payload):
        raw = dict(payload or {})
        snapshot = raw.get("indicators_snapshot", {})
        if isinstance(snapshot, str):
            snapshot = json_value(snapshot, {"raw": snapshot})
        signal_id = str(raw.get("id") or raw.get("signal_id") or now_id("sig"))
        return {
            "id": signal_id,
            "received_at": utc_now(),
            "coin": normalize_symbol(raw.get("coin") or raw.get("symbol")),
            "strategy": str(raw.get("strategy") or "").strip(),
            "timeframe": normalize_timeframe(raw.get("timeframe")),
            "direction": normalize_direction(raw.get("direction")),
            "signal_time": (parse_datetime(raw.get("signal_time")) or datetime.now(timezone.utc)).isoformat(),
            "candle_close_time": (parse_datetime(raw.get("candle_close_time")) or parse_datetime(raw.get("signal_time")) or datetime.now(timezone.utc)).isoformat(),
            "entry_price": safe_float(raw.get("entry_price")),
            "stop_price": safe_float(raw.get("stop_price")),
            "take_profit_price": safe_float(raw.get("take_profit_price")),
            "market_regime": str(raw.get("market_regime") or "unknown").strip().lower(),
            "indicators_snapshot": snapshot if isinstance(snapshot, dict) else {},
            "spread": safe_float(raw.get("spread")),
            "volume": safe_float(raw.get("volume")),
            "funding": safe_float(raw.get("funding")),
            "expected_R": safe_float(raw.get("expected_R") or raw.get("expected_r")),
            "status": "RECEIVED",
            "skip_reason": "",
            "raw_payload": raw,
        }

    def validate_signal(self, signal):
        if self.config.get("trading_mode") != "paper":
            return "trading_mode_not_paper"
        direction = signal.get("direction")
        if direction not in {"long", "short"}:
            return "invalid_direction"

        registry = self.registry_lookup().get(registry_key(signal["coin"], signal["strategy"], signal["timeframe"]))
        if not registry or not registry.get("enabled", True):
            return "not_enabled"
        status = str(registry.get("status") or "").lower()
        if status == "watch":
            return "watch_only"
        if status not in TRADE_ENABLED_STATUSES:
            return f"registry_status_{status or 'missing'}"

        max_per_coin = safe_int(self.config.get("max_positions_per_coin"), 1)
        coin_positions = [trade for trade in self.open_trades() if trade.get("coin") == signal["coin"]]
        if max_per_coin > 0 and len(coin_positions) >= max_per_coin:
            return "max_positions_per_coin"
        max_open = safe_int(self.config.get("max_open_positions"), 5)
        if len(self.open_trades()) >= max_open:
            return "max_open_positions"
        max_same = safe_int(self.config.get("max_same_direction_positions"), 3)
        same_direction = [trade for trade in self.open_trades() if trade.get("direction") == direction]
        if len(same_direction) >= max_same:
            return "max_same_direction_positions"

        daily_limit = safe_float(self.config.get("max_daily_loss_pct"), 0.01)
        weekly_limit = safe_float(self.config.get("max_weekly_loss_pct"), 0.03)
        if self.period_pnl_ratio(days=1) <= -abs(daily_limit):
            return "daily_loss_limit"
        if self.period_pnl_ratio(days=7) <= -abs(weekly_limit):
            return "weekly_loss_limit"

        if safe_float(signal.get("spread")) > safe_float(self.config.get("max_spread"), 0.0015):
            return "spread_above_limit"
        if safe_float(signal.get("volume")) < safe_float(self.config.get("min_liquidity"), 20000.0):
            return "liquidity_below_min"
        if abs(safe_float(signal.get("funding"))) > safe_float(self.config.get("funding_danger_threshold"), 0.001):
            return "funding_danger"
        if not self.regime_allowed(registry, signal.get("market_regime")):
            return "regime_not_allowed"
        return ""

    def period_pnl_ratio(self, days):
        starting = safe_float(self.state.get("portfolio_state", {}).get("starting_equity"), self.config.get("initial_equity"))
        if not starting:
            return 0.0
        return self.period_pnl(days) / starting

    def period_pnl_pct(self, days):
        return self.period_pnl_ratio(days) * 100.0

    def regime_allowed(self, registry, regime):
        metadata = registry.get("metadata") or {}
        allowed = [str(item).lower() for item in metadata.get("allowed_regimes", ["any"])]
        if not regime or "any" in allowed:
            return True
        return str(regime).lower() in allowed

    def risk_pct_for_signal(self, signal):
        registry = self.registry_lookup().get(registry_key(signal["coin"], signal["strategy"], signal["timeframe"])) or {}
        status = str(registry.get("status") or "").lower()
        if status == "core":
            return safe_float(self.config.get("core_risk_per_trade"), safe_float(self.config.get("risk_pct"), 0.0025))
        if status == "liquidity_risk":
            return safe_float(self.config.get("liquidity_risk_per_trade"), safe_float(self.config.get("risk_pct"), 0.001))
        if status == "watch":
            return safe_float(self.config.get("watch_risk_per_trade"), 0.0)
        return safe_float(self.config.get("risk_pct"), 0.0)

    def create_paper_trade(self, signal):
        direction = signal["direction"]
        entry = safe_float(signal.get("entry_price"))
        stop = safe_float(signal.get("stop_price"))
        take_profit = safe_float(signal.get("take_profit_price"))
        if entry <= 0 or stop <= 0 or take_profit <= 0:
            return None, "invalid_prices"
        slippage_pct = safe_float(self.config.get("slippage_pct"), 0.0002)
        slipped_entry = entry * (1.0 + slippage_pct) if direction == "long" else entry * (1.0 - slippage_pct)
        if direction == "long" and not (stop < slipped_entry < take_profit):
            return None, "invalid_long_brackets"
        if direction == "short" and not (take_profit < slipped_entry < stop):
            return None, "invalid_short_brackets"

        portfolio = self.state.get("portfolio_state", {})
        equity_before = safe_float(portfolio.get("current_equity"), self.config.get("initial_equity"))
        risk_pct = self.risk_pct_for_signal(signal)
        risk_amount = max(0.0, equity_before * risk_pct)
        stop_distance = abs(slipped_entry - stop)
        if stop_distance <= 0 or risk_amount <= 0:
            return None, "invalid_position_risk"
        qty = risk_amount / stop_distance
        max_notional = equity_before * safe_float(self.config.get("max_notional_pct"), 1.0)
        notional = qty * slipped_entry
        if max_notional > 0 and notional > max_notional:
            qty = max_notional / slipped_entry
            notional = max_notional
            risk_amount = stop_distance * qty
        if qty <= 0:
            return None, "position_size_zero"

        trade_id = now_id("ptrade")
        trade = {
            "id": trade_id,
            "source_signal_id": signal["id"],
            "coin": signal["coin"],
            "strategy": signal["strategy"],
            "timeframe": signal["timeframe"],
            "direction": direction,
            "status": "OPEN",
            "entry_time": signal.get("candle_close_time") or signal.get("signal_time") or utc_now(),
            "exit_time": "",
            "entry_price": slipped_entry,
            "stop_price": stop,
            "take_profit_price": take_profit,
            "exit_price": None,
            "qty": qty,
            "notional": notional,
            "risk_amount": risk_amount,
            "risk_pct": risk_pct,
            "fee_pct": safe_float(self.config.get("fee_pct"), 0.0004),
            "slippage_pct": slippage_pct,
            "funding": safe_float(signal.get("funding")),
            "gross_pnl": None,
            "fees": None,
            "slippage_cost": notional * slippage_pct,
            "funding_pnl": None,
            "net_pnl": None,
            "net_pnl_pct": None,
            "r_multiple": None,
            "exit_reason": "",
            "duration_min": None,
            "equity_before": equity_before,
            "equity_after": None,
            "market_regime": signal.get("market_regime", "unknown"),
            "metadata": {
                "entry_price_raw": entry,
                "indicators_snapshot": signal.get("indicators_snapshot", {}),
                "expected_R": signal.get("expected_R"),
            },
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        return trade, ""

    def update_prices(self, payload):
        updates = payload if isinstance(payload, list) else [payload]
        closed = []
        with self.lock:
            for update in updates:
                if not isinstance(update, dict):
                    continue
                closed.extend(self.process_price_update(update))
            self.ensure_portfolio_state()
            self.refresh_metrics()
            self.save_state()
        return {"status": "ok", "updates": len(updates), "closed_trades": closed}

    def process_price_update(self, update):
        coin = normalize_symbol(update.get("coin") or update.get("symbol"))
        high = safe_float(update.get("high") or update.get("price"))
        low = safe_float(update.get("low") or update.get("price"))
        close = safe_float(update.get("close") or update.get("price"))
        event_time = (
            parse_datetime(update.get("candle_close_time"))
            or parse_datetime(update.get("time"))
            or parse_datetime(update.get("timestamp"))
            or datetime.now(timezone.utc)
        )
        if not coin or high <= 0 or low <= 0 or close <= 0:
            return []

        closed = []
        for trade in list(self.open_trades()):
            if trade.get("coin") != coin:
                continue
            exit_reason = ""
            exit_price_raw = None
            direction = trade.get("direction")
            stop = safe_float(trade.get("stop_price"))
            take_profit = safe_float(trade.get("take_profit_price"))
            if direction == "long":
                stop_hit = low <= stop
                tp_hit = high >= take_profit
                if stop_hit:
                    exit_reason = "stop_loss"
                    exit_price_raw = stop
                elif tp_hit:
                    exit_reason = "take_profit"
                    exit_price_raw = take_profit
            else:
                stop_hit = high >= stop
                tp_hit = low <= take_profit
                if stop_hit:
                    exit_reason = "stop_loss"
                    exit_price_raw = stop
                elif tp_hit:
                    exit_reason = "take_profit"
                    exit_price_raw = take_profit

            if not exit_reason and self.time_stop_hit(trade, event_time):
                exit_reason = "time_stop"
                exit_price_raw = close
            if not exit_reason:
                continue

            funding = safe_float(update.get("funding"), safe_float(trade.get("funding")))
            closed_trade = self.close_trade(trade, exit_price_raw, event_time, exit_reason, funding)
            closed.append({"trade_id": closed_trade["id"], "exit_reason": exit_reason, "net_pnl": closed_trade["net_pnl"]})
        return closed

    def time_stop_hit(self, trade, event_time):
        entry_time = parse_datetime(trade.get("entry_time"))
        if not entry_time:
            return False
        limit = safe_int(self.config.get("time_stop_minutes"), 24 * 60)
        return event_time >= entry_time + timedelta(minutes=limit)

    def close_trade(self, trade, exit_price_raw, exit_time, exit_reason, funding):
        slippage_pct = safe_float(trade.get("slippage_pct"))
        fee_pct = safe_float(trade.get("fee_pct"))
        qty = safe_float(trade.get("qty"))
        entry = safe_float(trade.get("entry_price"))
        direction = trade.get("direction")
        exit_price = exit_price_raw * (1.0 - slippage_pct) if direction == "long" else exit_price_raw * (1.0 + slippage_pct)
        gross = (exit_price - entry) * qty if direction == "long" else (entry - exit_price) * qty
        entry_notional = entry * qty
        exit_notional = exit_price * qty
        fees = (entry_notional + exit_notional) * fee_pct
        entry_time = parse_datetime(trade.get("entry_time")) or exit_time
        duration_hours = max((exit_time - entry_time).total_seconds() / 3600.0, 0.0)
        funding_periods = duration_hours / 8.0
        funding_pnl = (-entry_notional * funding * funding_periods) if direction == "long" else (entry_notional * funding * funding_periods)
        slippage_cost = entry_notional * slippage_pct + exit_notional * slippage_pct
        net = gross - fees + funding_pnl
        equity_before = safe_float(trade.get("equity_before"), self.state.get("portfolio_state", {}).get("current_equity"))
        current_equity = safe_float(self.state.get("portfolio_state", {}).get("current_equity"), equity_before)
        equity_after = current_equity + net
        risk_amount = safe_float(trade.get("risk_amount"))
        closed = dict(trade)
        closed.update(
            {
                "status": "CLOSED",
                "exit_time": exit_time.replace(microsecond=0).isoformat(),
                "exit_price": exit_price,
                "gross_pnl": gross,
                "fees": fees,
                "slippage_cost": slippage_cost,
                "funding_pnl": funding_pnl,
                "net_pnl": net,
                "net_pnl_pct": (net / equity_before * 100.0) if equity_before else 0.0,
                "r_multiple": (net / risk_amount) if risk_amount else 0.0,
                "exit_reason": exit_reason,
                "duration_min": duration_hours * 60.0,
                "equity_after": equity_after,
                "updated_at": utc_now(),
            }
        )
        self.state["paper_trades"] = [closed if row.get("id") == trade.get("id") else row for row in self.state.get("paper_trades", [])]
        self.state["portfolio_state"]["current_equity"] = equity_after
        self.record_event(closed["id"], closed.get("source_signal_id"), "CLOSE", {"trade": closed, "exit_price_raw": exit_price_raw})
        self.mirror_trade(closed)
        return closed

    def record_signal(self, signal):
        self.state["signals"].insert(0, signal)
        self.state["signals"] = self.state["signals"][:1000]
        self.mirror_signal(signal)

    def record_event(self, trade_id, signal_id, event_type, payload):
        event = {
            "id": now_id("event"),
            "trade_id": trade_id,
            "signal_id": signal_id,
            "event_time": utc_now(),
            "event_type": event_type,
            "event_json": payload,
        }
        self.state["trade_events"].insert(0, event)
        self.state["trade_events"] = self.state["trade_events"][:1000]
        self.mirror_event(event)

    def refresh_metrics(self):
        performance = self.compute_performance()
        today = datetime.now(timezone.utc).date().isoformat()
        daily = {
            "metric_date": today,
            "total_signals": performance["summary"]["total_signals"],
            "skipped_signals": performance["summary"]["skipped_signals"],
            "opened_trades": performance["summary"]["opened_trades"],
            "closed_trades": performance["summary"]["closed_trades"],
            "net_pnl": performance["summary"]["net_pnl"],
            "payload": performance,
            "updated_at": utc_now(),
        }
        self.state["daily_metrics"] = [daily]
        self.state["strategy_metrics"] = performance["groups"]
        self.mirror_daily_metrics(daily)
        self.mirror_strategy_metrics(performance["groups"])

    def compute_performance(self):
        signals = self.state.get("signals", [])
        trades = self.state.get("paper_trades", [])
        closed = [row for row in trades if str(row.get("status")).upper() == "CLOSED"]
        skipped = [row for row in signals if str(row.get("status")).upper() == "SKIPPED"]
        net_values = [safe_float(row.get("net_pnl")) for row in closed]
        wins = [value for value in net_values if value > 0]
        losses = [value for value in net_values if value < 0]
        pf = profit_factor_value(wins, losses)
        avg_r_values = [safe_float(row.get("r_multiple")) for row in closed]
        summary = {
            "total_signals": len(signals),
            "skipped_signals": len(skipped),
            "opened_trades": len(trades),
            "closed_trades": len(closed),
            "win_rate_pct": (len(wins) / len(closed) * 100.0) if closed else 0.0,
            "net_pnl": sum(net_values),
            "profit_factor": pf,
            "max_dd_pct": self.max_drawdown_pct(closed),
            "average_R": (sum(avg_r_values) / len(avg_r_values)) if avg_r_values else 0.0,
            "longest_losing_streak": self.longest_losing_streak(closed),
            "skipped_by_reason": self.count_by(skipped, "skip_reason"),
        }
        groups = []
        for fields in (
            ("strategy",),
            ("coin",),
            ("timeframe",),
            ("direction",),
            ("market_regime",),
            ("strategy", "coin", "timeframe", "direction", "market_regime"),
        ):
            groups.extend(self.group_metrics(signals, trades, fields))
        return {"summary": summary, "groups": groups}

    def group_metrics(self, signals, trades, fields):
        buckets = {}
        for signal in signals:
            key = tuple(str(signal.get(field, "")) for field in fields)
            item = buckets.setdefault(key, {"fields": fields, "signals": [], "trades": []})
            item["signals"].append(signal)
        for trade in trades:
            key = tuple(str(trade.get(field, "")) for field in fields)
            item = buckets.setdefault(key, {"fields": fields, "signals": [], "trades": []})
            item["trades"].append(trade)

        rows = []
        for key, item in buckets.items():
            closed = [row for row in item["trades"] if str(row.get("status")).upper() == "CLOSED"]
            skipped = [row for row in item["signals"] if str(row.get("status")).upper() == "SKIPPED"]
            net_values = [safe_float(row.get("net_pnl")) for row in closed]
            wins = [value for value in net_values if value > 0]
            losses = [value for value in net_values if value < 0]
            pf = profit_factor_value(wins, losses)
            r_values = [safe_float(row.get("r_multiple")) for row in closed]
            row = {
                "id": id_from_key("sm", "|".join(fields) + "|" + "|".join(key)),
                "group_by": "+".join(fields),
                "coin": "",
                "strategy": "",
                "timeframe": "",
                "direction": "",
                "regime": "",
                "total_signals": len(item["signals"]),
                "skipped_signals": len(skipped),
                "opened_trades": len(item["trades"]),
                "closed_trades": len(closed),
                "win_rate": (len(wins) / len(closed) * 100.0) if closed else 0.0,
                "net_pnl": sum(net_values),
                "profit_factor": pf,
                "max_dd_pct": self.max_drawdown_pct(closed),
                "average_r": (sum(r_values) / len(r_values)) if r_values else 0.0,
                "longest_losing_streak": self.longest_losing_streak(closed),
                "payload": {"fields": list(fields), "values": list(key)},
                "updated_at": utc_now(),
            }
            for field, value in zip(fields, key):
                if field == "market_regime":
                    row["regime"] = value
                elif field in row:
                    row[field] = value
            rows.append(row)
        return sorted(rows, key=lambda row: (row["closed_trades"], row["net_pnl"]), reverse=True)

    def max_drawdown_pct(self, closed_trades):
        if not closed_trades:
            return 0.0
        starting = safe_float(self.state.get("portfolio_state", {}).get("starting_equity"), self.config.get("initial_equity"))
        equity = starting
        peak = starting
        max_dd = 0.0
        for trade in sorted(closed_trades, key=lambda row: str(row.get("exit_time") or "")):
            equity += safe_float(trade.get("net_pnl"))
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak * 100.0)
        return max_dd

    def longest_losing_streak(self, closed_trades):
        streak = 0
        longest = 0
        for trade in sorted(closed_trades, key=lambda row: str(row.get("exit_time") or "")):
            if safe_float(trade.get("net_pnl")) < 0:
                streak += 1
                longest = max(longest, streak)
            else:
                streak = 0
        return longest

    def count_by(self, rows, field):
        counts = {}
        for row in rows:
            key = str(row.get(field) or "unknown")
            counts[key] = counts.get(key, 0) + 1
        return counts

    def snapshot(self):
        with self.lock:
            self.ensure_portfolio_state()
            performance = self.compute_performance()
            registry = list(self.state.get("registry", []))
            signals = list(self.state.get("signals", []))
            trades = list(self.state.get("paper_trades", []))
            counts = self.count_by(registry, "status")
            return {
                "config": dict(self.config),
                "registry_counts": counts,
                "registry": registry,
                "signals": signals,
                "skipped_signals": [row for row in signals if str(row.get("status")).upper() == "SKIPPED"],
                "open_trades": [row for row in trades if str(row.get("status")).upper() == "OPEN"],
                "closed_trades": [row for row in trades if str(row.get("status")).upper() == "CLOSED"],
                "trade_events": list(self.state.get("trade_events", [])),
                "portfolio_state": dict(self.state.get("portfolio_state", {})),
                "performance": performance,
                "runner": dict(self.state.get("runner", {})),
                "storage_backend": self.state.get("storage_backend", "local_json"),
                "storage_error": self.state.get("storage_error", ""),
                "updated_at": self.state.get("updated_at", ""),
            }

    def active_strategies(self):
        with self.lock:
            return [row for row in self.state.get("registry", []) if row.get("status") in TRADE_ENABLED_STATUSES]

    def reject_real_order(self, payload=None):
        return {
            "status": "rejected",
            "reason": "paper_only_real_order_execution_disabled",
            "trading_mode": self.config.get("trading_mode", "paper"),
            "payload_received": bool(payload),
        }

    def run_signal_cycle(self, market=None, include_watch=None, limit=None):
        """Fetch latest candles, generate Stage 3 signals, and update open paper trades."""
        started_at = utc_now()
        market = market or self.config.get("signal_runner_market", "data_api_spot")
        include_watch = bool(self.config.get("signal_runner_include_watch", False) if include_watch is None else include_watch)
        limit = safe_int(limit or self.config.get("signal_runner_limit"), 260)
        summary = {
            "started_at": started_at,
            "market": market,
            "include_watch": include_watch,
            "pairs_checked": 0,
            "candles_fetched": 0,
            "price_updates": 0,
            "signals_generated": 0,
            "signals_opened": 0,
            "signals_skipped": 0,
            "duplicates_skipped": 0,
            "unsupported": 0,
            "errors": [],
        }
        if not self.config.get("signal_runner_enabled", True):
            summary["status"] = "disabled"
            self.update_runner(summary)
            return summary

        with self.lock:
            registry_rows = self.runner_registry_rows(include_watch=include_watch)
            open_rows = list(self.open_trades())

        fetch_keys = {(row["coin"], row["timeframe"]) for row in registry_rows}
        fetch_keys.update((row["coin"], row.get("timeframe") or "1h") for row in open_rows)
        candle_cache = {}

        for coin, timeframe in sorted(fetch_keys):
            if timeframe_minutes(timeframe) <= 0:
                summary["unsupported"] += 1
                continue
            try:
                candles = self.fetch_latest_candles(market, coin, timeframe, limit=limit)
                if candles:
                    candle_cache[(coin, timeframe)] = candles
                    summary["candles_fetched"] += len(candles)
                    latest = candles[-1]
                    price_result = self.update_prices(
                        {
                            "coin": coin,
                            "timeframe": timeframe,
                            "candle_close_time": latest["close_time"],
                            "high": latest["high"],
                            "low": latest["low"],
                            "close": latest["close"],
                            "volume": latest.get("quote_volume") or latest["volume"] * latest["close"],
                        }
                    )
                    summary["price_updates"] += safe_int(price_result.get("updates"))
            except Exception as exc:
                summary["errors"].append({"coin": coin, "timeframe": timeframe, "error": str(exc)[:240]})

        signals = []
        emitted = set(self.state.get("generated_signal_keys", []))
        for row in registry_rows:
            summary["pairs_checked"] += 1
            key = (row.get("coin"), row.get("timeframe"))
            candles = candle_cache.get(key)
            if not candles:
                continue
            try:
                signal = self.generate_signal_for_registry(row, candles)
            except Exception as exc:
                summary["errors"].append(
                    {"coin": row.get("coin"), "timeframe": row.get("timeframe"), "strategy": row.get("strategy"), "error": str(exc)[:240]}
                )
                continue
            if not signal:
                continue
            signal_key = registry_key(signal["coin"], signal["strategy"], signal["timeframe"]) + "|" + signal["candle_close_time"]
            if signal_key in emitted:
                summary["duplicates_skipped"] += 1
                continue
            emitted.add(signal_key)
            signals.append(signal)

        if signals:
            result = self.ingest_signals(signals)
            summary["signals_generated"] = len(signals)
            for item in result.get("results", []):
                if item.get("status") == "OPENED":
                    summary["signals_opened"] += 1
                elif item.get("status") == "SKIPPED":
                    summary["signals_skipped"] += 1

        self.state["generated_signal_keys"] = list(emitted)[-5000:]
        summary["status"] = "ok" if not summary["errors"] else "partial"
        summary["finished_at"] = utc_now()
        self.update_runner(summary)
        self.save_state()
        return summary

    def update_runner(self, summary):
        runner = self.state.setdefault("runner", {})
        runner["enabled"] = bool(self.config.get("signal_runner_enabled", True))
        runner["market"] = summary.get("market") or self.config.get("signal_runner_market", "data_api_spot")
        runner["last_run_at"] = summary.get("finished_at") or utc_now()
        runner["last_error"] = "; ".join(item.get("error", "") for item in summary.get("errors", [])[:3])
        runner["last_summary"] = summary
        runner["cycles"] = safe_int(runner.get("cycles")) + 1

    def runner_registry_rows(self, include_watch=False):
        statuses = set(TRADE_ENABLED_STATUSES)
        if include_watch:
            statuses.add("watch")
        rows = [
            row
            for row in self.state.get("registry", [])
            if row.get("enabled", True)
            and str(row.get("status", "")).lower() in statuses
            and timeframe_minutes(row.get("timeframe")) > 0
        ]
        return sorted(rows, key=lambda row: (row.get("coin", ""), row.get("timeframe", ""), row.get("strategy", "")))

    def request_json(self, url, params, retries=2):
        query = urllib.parse.urlencode(params)
        full_url = f"{url}?{query}"
        headers = {"User-Agent": str(self.config.get("signal_runner_user_agent") or "stage3-forward-monitor/1.0")}
        last_error = None
        for attempt in range(retries):
            try:
                request = urllib.request.Request(full_url, headers=headers)
                with urllib.request.urlopen(request, timeout=12) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read().decode("utf-8")
                except Exception:
                    body = str(exc)
                last_error = f"HTTP {exc.code}: {body[:240]}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < retries - 1:
                time.sleep(0.25 * (attempt + 1))
        raise RuntimeError(f"Binance kline request failed: {last_error}")

    def fetch_latest_candles(self, market, coin, timeframe, limit=260):
        endpoint = KLINE_ENDPOINTS.get(market)
        if not endpoint:
            raise ValueError(f"Unsupported Stage 3 kline market: {market}")
        payload = self.request_json(
            endpoint,
            {"symbol": normalize_symbol(coin), "interval": normalize_timeframe(timeframe), "limit": max(50, min(limit, 1000))},
        )
        if isinstance(payload, dict):
            raise RuntimeError(f"Binance API error: {payload}")
        now_ms = int(time.time() * 1000)
        candles = []
        for item in payload:
            close_time_ms = int(item[6])
            if close_time_ms > now_ms:
                continue
            candles.append(
                {
                    "open_time_ms": int(item[0]),
                    "close_time_ms": close_time_ms,
                    "open_time": datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc).isoformat(),
                    "close_time": datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc).isoformat(),
                    "open": safe_float(item[1]),
                    "high": safe_float(item[2]),
                    "low": safe_float(item[3]),
                    "close": safe_float(item[4]),
                    "volume": safe_float(item[5]),
                    "quote_volume": safe_float(item[7]) if len(item) > 7 else 0.0,
                }
            )
        min_bars = safe_int(self.config.get("signal_runner_min_bars"), 220)
        if len(candles) < min_bars:
            raise RuntimeError(f"not enough closed candles: {len(candles)} < {min_bars}")
        return candles

    def generate_signal_for_registry(self, registry_row, candles):
        indicators = self.calculate_indicators(candles)
        if not indicators:
            return None
        decision = self.strategy_decision(registry_row, indicators)
        if not decision:
            return None
        direction = decision["direction"]
        latest = candles[-1]
        entry = latest["close"]
        atr = max(safe_float(indicators.get("atr14")), entry * 0.006)
        stop_distance = max(atr * 1.25, entry * 0.004)
        target_distance = stop_distance * 1.8
        if direction == "long":
            stop = entry - stop_distance
            take_profit = entry + target_distance
        else:
            stop = entry + stop_distance
            take_profit = entry - target_distance
        if stop <= 0 or take_profit <= 0:
            return None
        quote_volume = latest.get("quote_volume") or latest["volume"] * entry
        spread_estimate = min(max(((latest["high"] - latest["low"]) / entry) * 0.03, 0.0001), 0.0012)
        expected_r = abs(take_profit - entry) / abs(entry - stop) if entry != stop else 0.0
        return {
            "id": id_from_key("sig", registry_key(registry_row["coin"], registry_row["strategy"], registry_row["timeframe"]) + "|" + latest["close_time"]),
            "coin": registry_row["coin"],
            "strategy": registry_row["strategy"],
            "timeframe": registry_row["timeframe"],
            "direction": direction,
            "signal_time": latest["close_time"],
            "candle_close_time": latest["close_time"],
            "entry_price": entry,
            "stop_price": stop,
            "take_profit_price": take_profit,
            "market_regime": indicators.get("market_regime", "unknown"),
            "indicators_snapshot": {**indicators, "decision_reason": decision.get("reason", "")},
            "spread": spread_estimate,
            "volume": quote_volume,
            "funding": 0.0,
            "expected_R": expected_r,
        }

    def calculate_indicators(self, candles):
        closes = [row["close"] for row in candles]
        highs = [row["high"] for row in candles]
        lows = [row["low"] for row in candles]
        opens = [row["open"] for row in candles]
        volumes = [row.get("quote_volume") or row["volume"] * row["close"] for row in candles]
        if len(closes) < 220:
            return {}
        ema20 = self.ema(closes, 20)
        ema50 = self.ema(closes, 50)
        ema200 = self.ema(closes, 200)
        atr14 = self.atr(highs, lows, closes, 14)
        rsi14 = self.rsi(closes, 14)
        adx = self.adx(highs, lows, closes, 14)
        sma_vol20 = sum(volumes[-20:]) / 20.0
        recent_high20 = max(highs[-21:-1])
        recent_low20 = min(lows[-21:-1])
        latest_range = max(highs[-1] - lows[-1], closes[-1] * 0.0001)
        body_ratio = abs(closes[-1] - opens[-1]) / latest_range
        sma20 = sum(closes[-20:]) / 20.0
        variance = sum((value - sma20) ** 2 for value in closes[-20:]) / 20.0
        std20 = math.sqrt(variance)
        bb_upper = sma20 + std20 * 2.0
        bb_lower = sma20 - std20 * 2.0
        atr_pct = atr14 / closes[-1] if closes[-1] else 0.0
        return_24h = closes[-1] / closes[-25] - 1.0 if len(closes) > 25 and closes[-25] else 0.0
        if ema50 > ema200 * 1.003:
            market_regime = "bull"
        elif ema50 < ema200 * 0.997:
            market_regime = "bear"
        else:
            market_regime = "sideways"
        if atr_pct > 0.035:
            market_regime = f"{market_regime}_high_vol"
        return {
            "close": closes[-1],
            "open": opens[-1],
            "high": highs[-1],
            "low": lows[-1],
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "atr14": atr14,
            "atr_pct": atr_pct,
            "rsi14": rsi14,
            "adx14": adx["adx"],
            "plus_di14": adx["plus_di"],
            "minus_di14": adx["minus_di"],
            "volume": volumes[-1],
            "volume_sma20": sma_vol20,
            "recent_high20": recent_high20,
            "recent_low20": recent_low20,
            "body_ratio": body_ratio,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_mid": sma20,
            "return_24h": return_24h,
            "green": closes[-1] > opens[-1],
            "red": closes[-1] < opens[-1],
            "market_regime": market_regime,
        }

    def strategy_decision(self, registry_row, ind):
        strategy = str(registry_row.get("strategy", "")).lower()
        allowed = str(registry_row.get("direction") or "both").lower()
        close = ind["close"]
        trend_long = close > ind["ema200"] and ind["ema50"] > ind["ema200"]
        trend_short = close < ind["ema200"] and ind["ema50"] < ind["ema200"]
        break_long = close > ind["recent_high20"] and ind["volume"] > ind["volume_sma20"] * 1.15
        break_short = close < ind["recent_low20"] and ind["volume"] > ind["volume_sma20"] * 1.15
        volume_spike = ind["volume"] > ind["volume_sma20"] * 1.6
        strong_body = ind["body_ratio"] > 0.52

        def choose(direction, condition, reason):
            if condition and allowed in {direction, "both", ""}:
                return {"direction": direction, "reason": reason}
            return None

        if "relative weakness" in strategy:
            return choose("short", trend_short and (break_short or ind["return_24h"] < -0.018) and ind["red"], "relative_weakness_short")
        if "ema 50/200" in strategy:
            return choose("long", trend_long and (break_long or (close > ind["ema20"] and ind["green"])), "ema_trend_long") or choose(
                "short", trend_short and (break_short or (close < ind["ema20"] and ind["red"])), "ema_trend_short"
            )
        if "trend pullback" in strategy:
            return choose("long", trend_long and ind["low"] <= ind["ema50"] * 1.006 and close > ind["ema20"] and 38 <= ind["rsi14"] <= 62 and ind["green"], "trend_pullback_long") or choose(
                "short", trend_short and ind["high"] >= ind["ema50"] * 0.994 and close < ind["ema20"] and 38 <= ind["rsi14"] <= 66 and ind["red"], "trend_pullback_short"
            )
        if "rsi pullback" in strategy:
            return choose("long", trend_long and 40 <= ind["rsi14"] <= 58 and close > ind["ema20"] and ind["green"], "rsi_pullback_long") or choose(
                "short", trend_short and 45 <= ind["rsi14"] <= 66 and close < ind["ema20"] and ind["red"], "rsi_pullback_short"
            )
        if "supertrend" in strategy:
            return choose("long", trend_long and close > ind["ema20"] and ind["green"] and ind["adx14"] >= 17, "supertrend_proxy_long") or choose(
                "short", trend_short and close < ind["ema20"] and ind["red"] and ind["adx14"] >= 17, "supertrend_proxy_short"
            )
        if "adx trend" in strategy:
            return choose("long", trend_long and ind["adx14"] >= 20 and ind["plus_di14"] > ind["minus_di14"], "adx_trend_long") or choose(
                "short", trend_short and ind["adx14"] >= 20 and ind["minus_di14"] > ind["plus_di14"], "adx_trend_short"
            )
        if "bollinger band trend ride" in strategy:
            return choose("long", trend_long and close >= ind["bb_upper"] * 0.995 and ind["green"], "bb_trend_ride_long") or choose(
                "short", trend_short and close <= ind["bb_lower"] * 1.005 and ind["red"], "bb_trend_ride_short"
            )
        if "volume spike" in strategy:
            return choose("long", volume_spike and strong_body and break_long and ind["green"], "volume_spike_long") or choose(
                "short", volume_spike and strong_body and break_short and ind["red"], "volume_spike_short"
            )
        if "support / resistance break" in strategy:
            return choose("long", break_long and close > ind["ema50"], "support_resistance_break_long") or choose(
                "short", break_short and close < ind["ema50"], "support_resistance_break_short"
            )
        if "funding squeeze" in strategy:
            return None
        return None

    def ema(self, values, period):
        alpha = 2.0 / (period + 1.0)
        current = values[0]
        for value in values[1:]:
            current = value * alpha + current * (1.0 - alpha)
        return current

    def rsi(self, closes, period):
        if len(closes) <= period:
            return 50.0
        gains = []
        losses = []
        for idx in range(len(closes) - period, len(closes)):
            change = closes[idx] - closes[idx - 1]
            gains.append(max(change, 0.0))
            losses.append(abs(min(change, 0.0)))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def atr(self, highs, lows, closes, period):
        if len(closes) <= period:
            return 0.0
        trs = []
        for idx in range(len(closes) - period, len(closes)):
            previous_close = closes[idx - 1]
            trs.append(max(highs[idx] - lows[idx], abs(highs[idx] - previous_close), abs(lows[idx] - previous_close)))
        return sum(trs) / period

    def adx(self, highs, lows, closes, period):
        if len(closes) <= period + 1:
            return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}
        plus_dm = []
        minus_dm = []
        trs = []
        start = len(closes) - period
        for idx in range(start, len(closes)):
            up_move = highs[idx] - highs[idx - 1]
            down_move = lows[idx - 1] - lows[idx]
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
            previous_close = closes[idx - 1]
            trs.append(max(highs[idx] - lows[idx], abs(highs[idx] - previous_close), abs(lows[idx] - previous_close)))
        tr_sum = sum(trs)
        if tr_sum <= 0:
            return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}
        plus_di = 100.0 * sum(plus_dm) / tr_sum
        minus_di = 100.0 * sum(minus_dm) / tr_sum
        denominator = plus_di + minus_di
        adx_value = 100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0
        return {"adx": adx_value, "plus_di": plus_di, "minus_di": minus_di}

    def mirror_registry(self, rows):
        if not self.driver or not rows:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    for row in rows:
                        cur.execute(
                            """
                            INSERT INTO strategy_registry (
                                id, coin, strategy, timeframe, status, direction, market_regime,
                                risk_config, metadata, enabled, created_at, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                            ON CONFLICT (coin, strategy, timeframe)
                            DO UPDATE SET
                                status = EXCLUDED.status,
                                direction = EXCLUDED.direction,
                                market_regime = EXCLUDED.market_regime,
                                risk_config = EXCLUDED.risk_config,
                                metadata = EXCLUDED.metadata,
                                enabled = EXCLUDED.enabled,
                                updated_at = now()
                            """,
                            (
                                row["id"],
                                row["coin"],
                                row["strategy"],
                                row["timeframe"],
                                row["status"],
                                row.get("direction"),
                                row.get("market_regime"),
                                json.dumps(row.get("risk_config", {}), ensure_ascii=False),
                                json.dumps(row.get("metadata", {}), ensure_ascii=False),
                                bool(row.get("enabled", True)),
                                row.get("created_at") or utc_now(),
                                row.get("updated_at") or utc_now(),
                            ),
                        )
        except Exception as exc:
            self.storage_error = f"Stage 3 registry mirror failed: {exc}"

    def mirror_signal(self, row):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO signals (
                            id, received_at, coin, strategy, timeframe, direction, signal_time,
                            candle_close_time, entry_price, stop_price, take_profit_price,
                            market_regime, indicators_snapshot, spread, volume, funding,
                            expected_r, status, skip_reason, raw_payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s::jsonb, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (id)
                        DO UPDATE SET status = EXCLUDED.status, skip_reason = EXCLUDED.skip_reason
                        """,
                        (
                            row["id"],
                            row.get("received_at") or utc_now(),
                            row["coin"],
                            row["strategy"],
                            row["timeframe"],
                            row["direction"],
                            row.get("signal_time"),
                            row.get("candle_close_time"),
                            safe_float(row.get("entry_price")),
                            safe_float(row.get("stop_price")),
                            safe_float(row.get("take_profit_price")),
                            row.get("market_regime"),
                            json.dumps(row.get("indicators_snapshot", {}), ensure_ascii=False),
                            safe_float(row.get("spread")),
                            safe_float(row.get("volume")),
                            safe_float(row.get("funding")),
                            safe_float(row.get("expected_R")),
                            row.get("status", "RECEIVED"),
                            row.get("skip_reason", ""),
                            json.dumps(row.get("raw_payload", {}), ensure_ascii=False),
                        ),
                    )
        except Exception as exc:
            self.storage_error = f"Stage 3 signal mirror failed: {exc}"

    def mirror_trade(self, row):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO paper_trades (
                            id, source_signal_id, coin, strategy, timeframe, direction, status,
                            entry_time, exit_time, entry_price, stop_price, take_profit_price,
                            exit_price, qty, notional, risk_amount, risk_pct, fee_pct, slippage_pct,
                            funding, gross_pnl, fees, slippage_cost, funding_pnl, net_pnl,
                            net_pnl_pct, r_multiple, exit_reason, duration_min, equity_before,
                            equity_after, metadata, created_at, updated_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                            %s, %s
                        )
                        ON CONFLICT (id)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            exit_time = EXCLUDED.exit_time,
                            exit_price = EXCLUDED.exit_price,
                            gross_pnl = EXCLUDED.gross_pnl,
                            fees = EXCLUDED.fees,
                            slippage_cost = EXCLUDED.slippage_cost,
                            funding_pnl = EXCLUDED.funding_pnl,
                            net_pnl = EXCLUDED.net_pnl,
                            net_pnl_pct = EXCLUDED.net_pnl_pct,
                            r_multiple = EXCLUDED.r_multiple,
                            exit_reason = EXCLUDED.exit_reason,
                            duration_min = EXCLUDED.duration_min,
                            equity_after = EXCLUDED.equity_after,
                            metadata = EXCLUDED.metadata,
                            updated_at = now()
                        """,
                        (
                            row["id"],
                            row.get("source_signal_id"),
                            row["coin"],
                            row["strategy"],
                            row["timeframe"],
                            row["direction"],
                            row.get("status"),
                            row.get("entry_time"),
                            row.get("exit_time") or None,
                            safe_float(row.get("entry_price")),
                            safe_float(row.get("stop_price")),
                            safe_float(row.get("take_profit_price")),
                            safe_float(row.get("exit_price")) if row.get("exit_price") not in (None, "") else None,
                            safe_float(row.get("qty")),
                            safe_float(row.get("notional")),
                            safe_float(row.get("risk_amount")),
                            safe_float(row.get("risk_pct")),
                            safe_float(row.get("fee_pct")),
                            safe_float(row.get("slippage_pct")),
                            safe_float(row.get("funding")),
                            safe_float(row.get("gross_pnl")) if row.get("gross_pnl") not in (None, "") else None,
                            safe_float(row.get("fees")) if row.get("fees") not in (None, "") else None,
                            safe_float(row.get("slippage_cost")) if row.get("slippage_cost") not in (None, "") else None,
                            safe_float(row.get("funding_pnl")) if row.get("funding_pnl") not in (None, "") else None,
                            safe_float(row.get("net_pnl")) if row.get("net_pnl") not in (None, "") else None,
                            safe_float(row.get("net_pnl_pct")) if row.get("net_pnl_pct") not in (None, "") else None,
                            safe_float(row.get("r_multiple")) if row.get("r_multiple") not in (None, "") else None,
                            row.get("exit_reason"),
                            safe_float(row.get("duration_min")) if row.get("duration_min") not in (None, "") else None,
                            safe_float(row.get("equity_before")),
                            safe_float(row.get("equity_after")) if row.get("equity_after") not in (None, "") else None,
                            json.dumps(row.get("metadata", {}), ensure_ascii=False),
                            row.get("created_at") or utc_now(),
                            row.get("updated_at") or utc_now(),
                        ),
                    )
        except Exception as exc:
            self.storage_error = f"Stage 3 trade mirror failed: {exc}"

    def mirror_event(self, row):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trade_events (id, trade_id, signal_id, event_time, event_type, event_json)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            row["id"],
                            row.get("trade_id"),
                            row.get("signal_id"),
                            row.get("event_time") or utc_now(),
                            row.get("event_type"),
                            json.dumps(row.get("event_json", {}), ensure_ascii=False),
                        ),
                    )
        except Exception as exc:
            self.storage_error = f"Stage 3 event mirror failed: {exc}"

    def mirror_portfolio_state(self, row):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO portfolio_state (
                            id, trading_mode, current_equity, starting_equity, open_positions,
                            daily_pnl, weekly_pnl, payload, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            trading_mode = EXCLUDED.trading_mode,
                            current_equity = EXCLUDED.current_equity,
                            starting_equity = EXCLUDED.starting_equity,
                            open_positions = EXCLUDED.open_positions,
                            daily_pnl = EXCLUDED.daily_pnl,
                            weekly_pnl = EXCLUDED.weekly_pnl,
                            payload = EXCLUDED.payload,
                            updated_at = now()
                        """,
                        (
                            row.get("id", "default"),
                            row.get("trading_mode", "paper"),
                            safe_float(row.get("current_equity")),
                            safe_float(row.get("starting_equity")),
                            safe_int(row.get("open_positions")),
                            safe_float(row.get("daily_pnl")),
                            safe_float(row.get("weekly_pnl")),
                            json.dumps(row, ensure_ascii=False),
                            row.get("updated_at") or utc_now(),
                        ),
                    )
        except Exception as exc:
            self.storage_error = f"Stage 3 portfolio mirror failed: {exc}"

    def mirror_daily_metrics(self, row):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO daily_metrics (
                            metric_date, total_signals, skipped_signals, opened_trades,
                            closed_trades, net_pnl, payload, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (metric_date)
                        DO UPDATE SET
                            total_signals = EXCLUDED.total_signals,
                            skipped_signals = EXCLUDED.skipped_signals,
                            opened_trades = EXCLUDED.opened_trades,
                            closed_trades = EXCLUDED.closed_trades,
                            net_pnl = EXCLUDED.net_pnl,
                            payload = EXCLUDED.payload,
                            updated_at = now()
                        """,
                        (
                            row["metric_date"],
                            safe_int(row.get("total_signals")),
                            safe_int(row.get("skipped_signals")),
                            safe_int(row.get("opened_trades")),
                            safe_int(row.get("closed_trades")),
                            safe_float(row.get("net_pnl")),
                            json.dumps(row.get("payload", {}), ensure_ascii=False),
                            row.get("updated_at") or utc_now(),
                        ),
                    )
        except Exception as exc:
            self.storage_error = f"Stage 3 daily metrics mirror failed: {exc}"

    def mirror_strategy_metrics(self, rows):
        if not self.driver:
            return
        try:
            with closing(self.connect()) as conn:
                with conn.cursor() as cur:
                    for row in rows:
                        cur.execute(
                            """
                            INSERT INTO strategy_metrics (
                                id, coin, strategy, timeframe, direction, regime,
                                total_signals, skipped_signals, opened_trades, closed_trades,
                                win_rate, net_pnl, profit_factor, max_dd_pct, average_r,
                                longest_losing_streak, payload, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                            ON CONFLICT (id)
                            DO UPDATE SET
                                total_signals = EXCLUDED.total_signals,
                                skipped_signals = EXCLUDED.skipped_signals,
                                opened_trades = EXCLUDED.opened_trades,
                                closed_trades = EXCLUDED.closed_trades,
                                win_rate = EXCLUDED.win_rate,
                                net_pnl = EXCLUDED.net_pnl,
                                profit_factor = EXCLUDED.profit_factor,
                                max_dd_pct = EXCLUDED.max_dd_pct,
                                average_r = EXCLUDED.average_r,
                                longest_losing_streak = EXCLUDED.longest_losing_streak,
                                payload = EXCLUDED.payload,
                                updated_at = now()
                            """,
                            (
                                row["id"],
                                row.get("coin"),
                                row.get("strategy"),
                                row.get("timeframe"),
                                row.get("direction"),
                                row.get("regime"),
                                safe_int(row.get("total_signals")),
                                safe_int(row.get("skipped_signals")),
                                safe_int(row.get("opened_trades")),
                                safe_int(row.get("closed_trades")),
                                safe_float(row.get("win_rate")),
                                safe_float(row.get("net_pnl")),
                                safe_float(row.get("profit_factor")) if str(row.get("profit_factor")) != "∞" else None,
                                safe_float(row.get("max_dd_pct")),
                                safe_float(row.get("average_r")),
                                safe_int(row.get("longest_losing_streak")),
                                json.dumps(row.get("payload", {}), ensure_ascii=False),
                                row.get("updated_at") or utc_now(),
                            ),
                        )
        except Exception as exc:
            self.storage_error = f"Stage 3 strategy metrics mirror failed: {exc}"
