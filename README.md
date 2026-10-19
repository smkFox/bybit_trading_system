# Bybit Trading System

Clean market-data foundation for a future Bybit USDT perpetual-futures trading
system. No strategy, backtest, or trading implementation is currently present.
Rejected work remains recoverable from Git history.

## Project structure

```text
market_data/              Bybit public-data clients, SQLite storage, and access
data/                     Local SQLite data, excluded from Git
context.md                Stable project principles
roadmap.md                Current status and next steps
```

## Environment

Create the project-local environment and install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

VS Code is configured to use `.venv/bin/python` and to activate this
environment in new integrated terminals.

Verify the active interpreter:

```bash
python -c "import sys; print(sys.executable)"
```

The printed path must end with:

```text
bybit_trading_system/.venv/bin/python
```

## Local database

The database is not stored in Git. Initialize a clean SQLite database with:

```bash
python -m market_data.database
```

It will be created at `data/market_data.sqlite3` with separate tables for
candles, Open Interest, and Funding Rates.

Check the public Bybit candle endpoint:

```bash
python -m market_data.check_bybit_api
```

The current dataset is hourly SOLUSDT history from 2022 through the latest
closed 2026 candle. Downloads are restartable and idempotent:

```bash
python -m market_data.download_history \
  SOLUSDT 1h \
  2022-01-01T00:00:00+00:00 \
  2026-10-19T03:00:00+00:00
```

Open Interest and Funding Rate download support remains available, but those
datasets are not required by the current KDJ-only hypothesis:

```bash
python -m market_data.download_derivatives_history \
  open-interest SOLUSDT 1h \
  2023-01-01T00:00:00+00:00 \
  2024-12-31T23:00:00+00:00

python -m market_data.download_derivatives_history \
  funding SOLUSDT \
  2023-01-01T00:00:00+00:00 \
  2024-12-31T23:59:59+00:00
```

KDJ is not supplied by the Bybit kline endpoint. If the hypothesis is approved,
it will be calculated locally and causally from stored hourly High, Low, and
Close values.
