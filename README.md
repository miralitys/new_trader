# New Trader Paper Dashboard

Paper-only crypto strategy monitor for Render.

## Render Web Service

Build command:

```bash
python3 -m venv .venv && .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install -r requirements.txt
```

Start command:

```bash
.venv/bin/python scripts/paper_trade_server.py --host 0.0.0.0 --port $PORT --interval-sec 120 --days 1 --warmup-days 10 --market data_api_spot --entry-mode maker_limit --modules RIF --monitor-universe modules --monitor-every-cycles 15
```

The service never sends exchange orders and does not need API keys. It only
downloads public market data, runs paper execution checks, and exposes a small
dashboard. The Render web service runs the live paper loop and stores state in
Postgres when `DATABASE_URL` is present.

`--modules RIF` keeps the live paper-execution journal focused on RIF only. With
`--monitor-universe modules`, the dashboard's operational board also checks only
the strategies mapped to the selected module, so Render does not waste cycles on
the full fixed strategy universe from `data/operational_monitor_universe_2026-05-04.csv`.
The server also has RIF-only mode enabled by default, so an old Render Start
Command cannot accidentally re-enable the removed modules. Set
`PAPER_RIF_ONLY=0` only if you intentionally want to restore the broader monitor.
The heavier operational monitor runs every 15 paper cycles by default, while
manual "Run Once" always refreshes it immediately.

## Persistent State

Create a Render Postgres database in the same region as the web service and add
its internal database URL as the web service environment variable
`DATABASE_URL`. The dashboard will then show `Storage: postgres` and keep the
paper ledger after restarts and redeploys.

If `DATABASE_URL` is missing or unavailable, the service falls back to
`data/paper_live/state.json`. That is useful locally, but Render's filesystem is
ephemeral, so this mode should not be used for long-term history.

## Dashboard Password

Add this Render environment variable to protect the public dashboard:

```bash
PAPER_DASHBOARD_PASSWORD=your-strong-password
```

When the variable is present, the dashboard and API actions require login. If it
is missing, the dashboard stays open.

## Notes

- If Render blocks Binance global endpoints with HTTP 451, keep
  `--market data_api_spot`.
- For very small instances, add `--skip-monitor` and reduce `--warmup-days`.
- Use Pro or higher if the dashboard should run continuously with the monitor
  enabled.
