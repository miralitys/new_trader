# New Trader Paper Dashboard

Paper-only crypto strategy monitor for Render.

## Render Web Service

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python3 scripts/paper_trade_server.py --host 0.0.0.0 --port $PORT --interval-sec 60 --days 1 --warmup-days 10 --market data_api_spot --entry-mode maker_limit --modules ANKR RIF GALA_73 GALA_10 GALA_112 SPELL
```

The service never sends exchange orders and does not need API keys. It only
downloads public market data, runs paper execution checks, and exposes a small
dashboard.

## Notes

- Render's default filesystem is ephemeral, so long-term paper history should
  eventually move to Postgres.
- Free web services can sleep after inactivity. Use Starter or higher for a
  dashboard that should stay responsive.
