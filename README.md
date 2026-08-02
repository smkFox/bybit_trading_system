# Bybit Trading System

Local research and trading-system project for Bybit USDT perpetual futures.
The project currently has no strategy approved for demo or live trading.
Research commands read public market data and never place exchange orders.

## Current state

The latest fixed candidate, BTC-confirmed ETH Shock Mean Reversion v1, failed
its 2023–2024 development gate. It was deliberately stopped before testing
2025–2026. Its code remains temporarily available so the rejection is exactly
reproducible; it is not an active trading configuration.

Previously rejected EMA and Donchian implementations have been removed from
the active tree. Their history remains available in Git, with the final
Donchian state preserved at commit `2e7c03d`.

## Project structure

```text
market_data/                                  Bybit data, SQLite, and access
strategies/models.py                          Shared decision models
strategies/indicators.py                      Shared Wilder ATR
strategies/btc_eth_shock_mean_reversion/      Latest rejected candidate
backtest/engine.py                            Shared execution simulator
backtest/run_shock_mean_reversion_development.py
data/                                         Local SQLite data, excluded from Git
context.md                                    Stable project principles
roadmap.md                                    Current plan and decision history
```

## Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Market data

Inspect a public Bybit candle response:

```bash
python -m market_data.check_bybit_api
```

Initialize and verify local storage:

```bash
python -m market_data.database
python -m market_data.check_candle_storage
```

Download or safely resume a range:

```bash
python -m market_data.download_history \
  ETHUSDT \
  15m \
  2023-01-01T00:00:00+00:00 \
  2025-01-01T00:00:00+00:00
```

Update stored closed candles:

```bash
python -m market_data.update_candles ETHUSDT 15m
```

The database is stored at `data/market_data.sqlite3`. The unique key
`symbol + timeframe + open_time` makes repeated downloads idempotent.

## Latest candidate reproduction

The fixed rules are documented in
`strategies/btc_eth_shock_mean_reversion/specification.md`.

Run its checks and the 2023–2024 development test:

```bash
python -m strategies.check_indicators
python -m strategies.btc_eth_shock_mean_reversion.check_strategy
python -m backtest.check_engine
python -m backtest.run_shock_mean_reversion_development
```

The signal-quality run produced 284 trades, `-36.14%` return, profit factor
`0.31`, and `36.23%` maximum closed-equity drawdown. Both years and both trade
directions lost money. The complete recorded result is in
`backtest/btc_eth_shock_mean_reversion_development.md`.

The backtest includes a 0.055% taker fee, 0.050% adverse slippage per fill,
and a conservative 0.010% funding cost per crossed 8-hour interval. It writes
no backtest results to the market-data database and sends no Bybit orders.
