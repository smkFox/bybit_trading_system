# Project Roadmap

## Status notation

* `[x]` complete;
* `[~]` current;
* `[ ]` not started or blocked by an earlier phase.

# Current state

## Current phase

Clean data foundation and KDJ hypothesis specification.

## Current objective

Keep only the reusable Bybit market-data loader and database. Restore SOLUSDT
hourly candles from 2022 through the current closed 2026 data, then specify a
KDJ-only Long/Short hypothesis before writing strategy or backtest code.

## Immediate path

* [x] Restore the repository from GitHub.
* [x] Remove all strategy, research, backtest, report, and test artifacts from
  the active tree.
* [x] Recreate the project-local Python environment and initialize SQLite.
* [x] Verify the current public Bybit API.
* [x] Select `SOLUSDT / 1h / 2022-2026` as the next dataset.
* [x] Download and verify the required hourly candles.
* [~] Freeze the exact KDJ formula, causal entry/exit rules, execution timing,
  stop model, leverage experiment, costs, and acceptance gate.
* [ ] Freeze and test the next candidate on development data.
* [ ] Validate a successful frozen candidate on untouched data.
* [ ] Run controlled Bybit demo trading.
* [ ] Add operational safety and Telegram reporting.
* [ ] Make a separate manual decision about small live trading.

## Current constraints

* Bybit USDT perpetual futures remain the initial market.
* No strategy is active or approved.
* The proposed experiment starts with 100 USDT; leverage and stop risk remain
  unapproved until their interaction with liquidation and drawdown is defined.
* Use only closed candles and causal calculations without future data.
* Include fees, slippage, funding, exchange constraints, and rejected orders.
* Keep research separate from demo and live order placement.
* Do not imply guaranteed daily or monthly profit.

# Preserved foundation

## Market data

* [x] Public Bybit candle, Open Interest, and Funding Rate clients.
* [x] UTC normalization and closed-candle handling.
* [x] SQLite storage with natural unique keys.
* [x] Restartable and idempotent historical downloads.
* [x] Incremental candle updates.
* [x] pandas data-access boundary.

# Removed rejected work

The active tree contains no strategy, indicator, research, backtest, report, or
candidate-specific test code. It retains only the market-data foundation and
project documentation.

Nothing was erased from Git history. Earlier checkpoints and commits remain the
source for historical investigation if it is ever needed; rejected code must
not be restored into the active tree merely for convenience.

# Next development gate

Before implementing another strategy:

* state the economic or behavioral reason for the expected edge;
* define exact causal inputs and publication timing;
* freeze parameters and data boundaries before viewing results;
* define minimum sample size and neighboring-parameter robustness;
* define fees, slippage, funding, sizing, leverage, and exchange constraints;
* define pass, fail, and inconclusive decisions.

A candidate may advance only if it is profitable in every required development
period, has adequate directional and sample support, survives reasonable
neighboring parameters, and passes the predefined drawdown and profit-factor
limits.

# Later phases

## Frozen validation

* [ ] Freeze strategy code, parameters, data boundaries, and acceptance rules.
* [ ] Run once on untouched validation data.
* [ ] Reject without tuning if the gate fails.

## Bybit demo trading

* [ ] Synchronize closed candles and exchange state at startup.
* [ ] Generate one deterministic decision per decision candle.
* [ ] Size, submit, and reconcile orders and exchange-side protective stops.
* [ ] Persist decisions, fills, positions, and errors.
* [ ] Prevent duplicate orders and recover safely after restart.

## Telegram monitoring

* [ ] Report lifecycle events, stale data, and critical errors.
* [ ] Show trades, exposure, realized/unrealized PnL, fees, and equity.
* [ ] Keep Telegram read-only until a separate decision changes that boundary.

## Small controlled live trading

Requires a separate manual decision after successful demo evidence.

# Work log

## 2026-10-19

* [x] Restored the repository from GitHub at its new local path.
* [x] Removed obsolete candidate code and old research/test artifacts.
* [x] Preserved only the reusable Bybit market-data and SQLite modules.
* [x] Added workspace settings for the project-local `.venv` interpreter.
* [x] Created `.venv` with Python 3.14.4 and installed the pinned dependencies.
* [x] Initialized an empty SQLite database with candle, Open Interest, and
  Funding Rate tables.
* [x] Confirmed successful public Bybit access and closed-candle normalization.
* [x] Removed the remaining shared strategy, indicator, research, and backtest
  directories so the active code contains only the Bybit data foundation.
* [x] Loaded 42,052 consecutive SOLUSDT 1h candles from 2022-01-01 00:00 UTC
  through 2026-10-19 03:00 UTC with no gaps or duplicates.

## Next task

* [~] Freeze the causal KDJ signal and the relationship between position size,
  leverage, stop distance, and account risk before implementing the test.
