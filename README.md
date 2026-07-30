# Bybit Trading System

Current scope: a local Data Layer for closed `ETHUSDT` USDT perpetual candles
from Bybit. Supported timeframes are `15m` and `1h`. All stored timestamps use
UTC, and public candle requests do not require API keys.

## Project structure

```text
market_data/          Bybit market-data API, normalization, storage, and access
strategies/           Versioned strategy specification and decision code
backtest/             Sequential simulation, execution model, and checks
data/                 Local runtime data and SQLite database
context.md            Stable project principles
roadmap.md            Current implementation plan and status
```

## Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Data commands

Inspect a small real Bybit response:

```bash
python -m market_data.check_bybit_api
```

Initialize the SQLite database:

```bash
python -m market_data.database
```

Download an inclusive historical range:

```bash
python -m market_data.download_history \
  ETHUSDT \
  15m \
  2023-01-01T00:00:00+00:00 \
  2026-01-01T00:00:00+00:00
```

Update one timeframe to the latest closed candle:

```bash
python -m market_data.update_candles ETHUSDT 15m
python -m market_data.update_candles ETHUSDT 1h
```

The local database is stored at `data/market_data.sqlite3` and is excluded from
Git. Historical and incremental downloads can be restarted safely; the key
`symbol + timeframe + open_time` prevents duplicate candles.

## Python data access

Research code can load only the required range without knowing the SQLite
implementation:

```python
from datetime import datetime, timezone

from market_data.data_access import load_candles_dataframe


candles = load_candles_dataframe(
    symbol="ETHUSDT",
    timeframe="15m",
    start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end_time=datetime(2023, 2, 1, tzinfo=timezone.utc),
)
```

The returned pandas DataFrame is chronological, uses UTC datetime values, and
contains numeric OHLC, volume, and turnover columns.

## Strategy specification

The frozen baseline for the first strategy is:

```text
strategies/ema_trend_pullback_v1.md
```

The specification defines the strategy hypothesis only. It does not activate
trading and does not claim that the baseline parameters are profitable.

## Strategy and backtest

Run the focused deterministic checks:


```bash
python -m strategies.check_indicators
python -m strategies.check_timeframe_alignment
python -m backtest.check_backtest
```

The checks cover indicator values and warm-up, look-ahead protection, timeframe
boundaries, strategy decisions, next-candle entry, protective exits, and fees.

Run the frozen baseline on the complete 2023–2024 development period:

```bash
python -m backtest.run_backtest
```

The default run starts with 10 USDT, uses 1% risk per trade, 3x leverage,
0.055% taker fee and 0.05% adverse slippage per fill. Funding is represented by
a conservative configurable 0.01% cost for each crossed 8-hour interval. The
simulator applies the current ETHUSDT quantity, notional, and price-step
constraints recorded in the configuration; they were observed on 2026-07-30
and are not claimed to be historical constraints.

The backtest reads candles from SQLite but does not write decisions or results
to the market-data database. A concise frozen baseline report is stored in
`backtest/baseline_2023_2024.md`.
