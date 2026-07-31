# Bybit Trading System

Local research and trading-system project for Bybit USDT perpetual futures.
The current candidate is Donchian Breakout v1 on `ETHUSDT`. Research never
places exchange orders.

## Project structure

```text
market_data/                    Bybit market data, SQLite, and data access
strategies/models.py            Shared trading-decision model
strategies/indicators.py        Shared Wilder ATR
strategies/timeframes.py        Closed 1h to 4h aggregation
strategies/donchian_breakout/   Current strategy code, specification, checks
backtest/                       Shared execution simulator and baseline runner
data/                           Local runtime data and SQLite database
context.md                      Stable project principles
roadmap.md                      Current plan, status, and decisions
```

## Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Data commands

Inspect a small public Bybit response:

```bash
python -m market_data.check_bybit_api
```

Initialize SQLite:

```bash
python -m market_data.database
```

Download or safely resume a historical range:

```bash
python -m market_data.download_history \
  ETHUSDT \
  1h \
  2023-01-01T00:00:00+00:00 \
  2026-01-01T00:00:00+00:00
```

Update stored closed candles:

```bash
python -m market_data.update_candles ETHUSDT 1h
```

The database is stored at `data/market_data.sqlite3` and excluded from Git.
The unique key `symbol + timeframe + open_time` prevents duplicates.

## Current strategy

The frozen candidate specification is:

```text
strategies/donchian_breakout/specification.md
```

Baseline rules:

```text
4h candles derived from stored closed 1h candles
20-candle entry channel
10-candle exit channel
Wilder ATR14
2 ATR initial stop
no fixed take profit
one position and no pyramiding
```

This is a historical candidate, not an approved demo or live strategy.

## Checks

```bash
python -m strategies.check_indicators
python -m strategies.check_timeframes
python -m strategies.donchian_breakout.check_strategy
python -m backtest.check_engine
```

The checks cover ATR values and warm-up, closed 4h aggregation, UTC boundaries,
gaps, shifted Donchian channels, no look-ahead, deterministic decisions,
next-candle execution, protective stops, optional take profit, strategy exits,
and fees.

## Baseline backtest

```bash
python -m backtest.run_backtest
```

The command uses only 2023–2024 and prints two simulations:

1. diagnostic signal quality with 1% risk and execution-size filters
   neutralized;
2. executable `10 USDT / 5% risk / 3x` with current ETHUSDT constraints.

Both include a 0.055% taker fee, 0.05% adverse slippage per fill, and a
conservative 0.01% funding cost per crossed 8-hour interval. The current
instrument limits were observed on 2026-07-30 and are not historical metadata.

The recorded result and its limitations are in
`backtest/donchian_breakout_baseline.md`. Backtesting does not write results to
the market-data database and never sends orders to Bybit.
