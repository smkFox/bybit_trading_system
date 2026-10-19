# Project Context

## Purpose

Build a transparent Bybit USDT perpetual-futures trading system whose behavior
can be reproduced from stored public market data. Profit is an objective, not a
guarantee.

## Current implementation boundary

Only the market-data foundation exists in the active codebase:

* public Bybit clients;
* closed-candle normalization in UTC;
* restartable historical downloads;
* incremental candle updates;
* SQLite storage;
* pandas data access;
* optional Open Interest and Funding Rate downloads.

There is currently no indicator, strategy, backtest, order execution, or
Telegram implementation. Rejected historical work is available only through
Git history and must not be silently restored.

## Current dataset and hypothesis

The local database contains consecutive `SOLUSDT` USDT perpetual 1h candles
from `2022-01-01 00:00 UTC` through `2026-10-19 03:00 UTC`.

The next proposed hypothesis uses only a locally calculated KDJ indicator for
entries and exits. Its exact causal formula, thresholds, entry timing, reversal
behavior, position sizing, leverage, stop, costs, and test boundaries must be
agreed before implementation.

The proposed starting balance is 100 USDT. Leverage around 20x and account risk
up to 20% per trade are research proposals, not approved live settings.

## Data invariants

* Store timestamps in UTC.
* Use only fully closed candles for decisions.
* Process candles chronologically.
* Never expose future candles to historical calculations.
* Report gaps, duplicates, invalid OHLC values, and unaligned timestamps.
* Repeated downloads must not create duplicates.
* The natural candle key is `symbol + timeframe + open_time`.
* API-specific response details remain inside `market_data/`.
* Reproducible indicators are calculated in memory, not stored as raw market
  data.

## Research invariants

Before testing any strategy, freeze:

* the formula and all initial values;
* causal entry and exit conditions;
* execution timing;
* position sizing and margin mode;
* leverage and stop interpretation;
* commissions, slippage, funding, and liquidation behavior;
* development and untouched validation periods;
* pass, fail, and insufficient-evidence criteria.

Changing parameters after seeing a result creates a new experiment. A
profitable historical run does not authorize demo or live trading.

## Safety boundary

No current module can place an order. API keys, private endpoints, demo trading,
live trading, and Telegram control are outside the current implementation.
