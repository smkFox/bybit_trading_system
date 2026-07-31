# Project Roadmap

## Status notation

```text
[ ] Not started
[~] In progress
[x] Completed
[!] Blocked
[-] Deferred
```

The stable project rules are in `context.md`. Current commands and structure
are in `README.md`. Code and the database schema remain the implementation
source of truth.

---

# Current state

## Current phase

```text
Phase 2 — Donchian Breakout development
```

## Current objective

Determine whether Donchian Breakout v1 has sufficiently strong and stable
positive expectancy on 2023–2024 to justify a limited parameter review and a
later frozen validation run.

## Current active task

```text
Review the unchanged 20/10, ATR14, 2 ATR baseline by year and direction.
```

## Immediate path

* [x] Build and verify the reusable market-data foundation.
* [x] Reject EMA Trend Pullback after its complete development test.
* [x] Separate shared strategy models and the backtest engine from a concrete
  strategy.
* [x] Implement and test Donchian Breakout v1.
* [x] Run its unchanged 2023–2024 baseline in diagnostic and 10 USDT modes.
* [~] Decide whether a small, predefined development comparison is justified.
* [ ] Freeze or reject the strategy.
* [ ] Run 2025 validation only after the freeze.
* [ ] Run 2026 out-of-sample only if validation permits it.
* [ ] Run the frozen strategy in Bybit Demo Trading.
* [ ] Add operational safety and Telegram reporting.
* [ ] Make a separate manual decision about controlled live trading.

## Current constraints

* Exchange: Bybit.
* Market: USDT perpetual futures.
* Symbol: `ETHUSDT`.
* Stored source candles: `1h`.
* Derived strategy candles: `4h` aligned to UTC.
* Development data: 2023-01-01 through 2024-12-31 only.
* Validation and out-of-sample data must remain unseen until configuration
  freeze.
* Initial executable account: 10 USDT.
* Baseline leverage: 3x.
* 5x remains a future manually approved maximum, never an automatic choice.
* Current aggressive development scenario: 5% risk per trade.
* Only fully closed candles may create decisions.
* At most one position may be open.
* Backtest, demo, and live must call the same strategy implementation.
* Profit is the objective, not a guaranteed outcome.

---

# Phase 0 — Environment and project setup

Status: [x] Completed

* [x] Create the project and local Python environment.
* [x] Configure Git and source exclusions.
* [x] Add dependency and environment checks.
* [x] Add stable context, roadmap, and README files.
* [x] Establish a simple local project structure.

---

# Phase 1 — Data foundation

Status: [x] Completed on 2026-07-27

## Implemented

* [x] Public Bybit linear-candle client.
* [x] UTC normalization and closed-candle filtering.
* [x] OHLC and interval validation.
* [x] SQLite schema with `symbol + timeframe + open_time` uniqueness.
* [x] Idempotent save and chronological range reads.
* [x] Restartable historical downloader with missing-range detection.
* [x] Incremental updater for configured timeframes.
* [x] pandas data-access interface independent of API and SQLite details.
* [x] Complete ETHUSDT 15m and 1h history from 2023-01-01.
* [x] Gap, duplicate, alignment, OHLC, and SQLite integrity checks.

## Verified snapshot on 2026-07-27

```text
15m candles: 125,141
1h candles:   31,285
gaps:         0
duplicates:   0
invalid OHLC: 0
SQLite:       ok
```

---

# Rejected strategy record

## EMA Trend Pullback v1

Status: [x] Rejected on 2026-07-30

Reason:

* the unchanged baseline lost 37.33% in the 10 USDT scenario;
* all 27 predefined stop, target, and holding variants had negative complete
  signal-flow expectancy;
* apparent profits on the small executable subset did not scale to the full
  signal set;
* the implementation, reports, and strategy-specific checks were removed from
  the active tree after rejection and remain recoverable through Git history.

---

# Phase 2 — Donchian Breakout development

Status: [~] In progress

## Goal

Test one transparent higher-timeframe trend-following hypothesis without
automatic optimization or access to validation data.

## 2.1 Project reorganization

* [x] Move shared `Action`, `Side`, position state, and decision models to
  `strategies/models.py`.
* [x] Keep shared ATR in `strategies/indicators.py`.
* [x] Add reusable closed 1h to 4h aggregation in
  `strategies/timeframes.py`.
* [x] Make the backtest engine consume a strategy evaluator rather than import
  a concrete strategy.
* [x] Support strategies without a fixed take profit.
* [x] Support strategy-directed exits at the next candle open.
* [x] Place all Donchian-specific files under
  `strategies/donchian_breakout/`.
* [x] Remove rejected EMA-specific code, checks, reports, and commands.

## 2.2 Frozen baseline specification

* [x] Use closed, UTC-aligned 4h candles derived from stored 1h candles.
* [x] Use the previous 20 candles for Long and Short entry channels.
* [x] Use the previous 10 candles for position exit channels.
* [x] Exclude the current candle from every channel.
* [x] Use Wilder ATR14 and an initial 2 ATR protective stop.
* [x] Use no fixed take profit and no maximum holding time.
* [x] Allow one position and disable pyramiding and same-decision reversal.
* [x] Enter and exit at the next 4h open after the closed-candle decision.
* [x] Record the exact rules in `specification.md`.

## 2.3 Implementation checks

* [x] Verify known 1h-to-4h OHLCV aggregation.
* [x] Reject gaps and exclude an incomplete final 4h candle.
* [x] Verify UTC 4h boundaries on real development data.
* [x] Verify ATR warm-up and deterministic values.
* [x] Verify shifted entry and exit channels without look-ahead.
* [x] Verify Long, Short, Hold, Close, and No Action decisions.
* [x] Verify deterministic decision IDs.
* [x] Verify next-candle entries and strategy exits.
* [x] Verify protective stops, optional take profit, fees, and input
  immutability.

## 2.4 Unchanged baseline

* [x] Run 2023–2024 diagnostic quality mode with 1% risk and size filters
  neutralized.
* [x] Run 2023–2024 executable mode with 10 USDT, 5% risk, and 3x leverage.
* [x] Include fees, adverse slippage, conservative funding, and current
  instrument constraints.
* [x] Record combined, yearly, Long, Short, drawdown, and rejection results.
* [x] Do not inspect 2025 or 2026.

### Baseline result

```text
Diagnostic full signal flow:
  return:             +12.73%
  trades:             110
  profit factor:      1.195
  maximum drawdown:   13.70%
  2023 net:           -3.86 USDT, PF 0.989
  2024 net:           +131.14 USDT, PF 1.420
  Long net:           +166.11 USDT
  Short net:          -38.83 USDT

Executable 10 USDT / 5% / 3x:
  return:             +11.57%
  trades:             37
  rejected entries:   234
  profit factor:      1.109
  maximum drawdown:   48.13%
  2024 trades:        0
```

## 2.5 Limited development decision

* [~] Decide whether the positive but concentrated baseline justifies a small
  predefined comparison.
* [ ] Define alternatives before running them.
* [ ] Keep the comparison limited and explain every changed parameter.
* [ ] Compare combined results, both years, Long/Short, trade count, costs,
  drawdown, and neighboring-value stability.
* [ ] Do not add filters merely to explain individual losing trades.
* [ ] Freeze one configuration or reject the strategy.
* [ ] Do not inspect 2025 or 2026 before the freeze.

## Completion criteria

* [ ] One reproducible Donchian configuration is frozen, or the strategy is
  explicitly rejected.
* [ ] The decision is based on net expectancy, yearly and directional
  stability, drawdown, and executable feasibility.

---

# Phase 3 — Validation and out-of-sample

Status: [ ] Not started

```text
Development:   2023-01-01 through 2024-12-31
Validation:    2025-01-01 through 2025-12-31
Out-of-sample: 2026-01-01 through the latest closed candle
```

* [ ] Confirm that strategy code and parameters are frozen.
* [ ] Run 2025 once and do not tune from its result.
* [ ] Apply predefined approval or rejection criteria.
* [ ] Run 2026 only if the process still permits it.
* [ ] Do not tune from the 2026 result.
* [ ] Approve for demo or reject.

---

# Phase 4 — Bybit Demo Trading

Status: [ ] Not started

* [ ] Configure demo credentials outside source control.
* [ ] Synchronize current closed source candles at startup.
* [ ] Run the frozen strategy on each new closed decision candle.
* [ ] Use the shared sizing, rounding, costs, and constraints.
* [ ] Submit and track demo orders and protective stops.
* [ ] Persist decisions, orders, fills, positions, and errors.
* [ ] Reconcile local and exchange state after startup and failures.
* [ ] Prevent duplicate orders for one decision.
* [ ] Add persistent pause and emergency-stop behavior.
* [ ] Compare modeled and actual fills, fees, funding, and timing.

---

# Phase 5 — Monitoring and Telegram

Status: [ ] Not started

Telegram remains a read-only notification and text-dashboard channel.

* [ ] Report system start, stop, pause, and critical errors.
* [ ] Report stale data and API failures.
* [ ] Report order and position lifecycle events.
* [ ] Show completed trades, current exposure, realized and unrealized PnL,
  fees, funding, drawdown, status, and latest data time.
* [ ] Ensure monitoring failure cannot silently authorize trading.

---

# Phase 6 — Small controlled live trading

Status: [ ] Not started

Live activation always requires a separate manual decision after successful
validation, out-of-sample testing, demo operation, reconciliation, and safety
checks.

Initial restrictions remain one symbol, one frozen strategy, 3x leverage,
explicit risk limits, no automatic optimization, no automatic strategy
replacement, and no capital increase without a separate review.

---

# Deferred scope

* [-] Automatic strategy selection.
* [-] Multiple live strategies or exchanges.
* [-] Machine learning.
* [-] Tick or order-book research.
* [-] High-frequency trading.
* [-] Cloud or distributed infrastructure.
* [-] Complex graphical dashboard.
* [-] Continuous parameter optimization.

---

# Decision log

* [x] Keep the system local and transparent.
* [x] Use real stored data and realistic execution assumptions.
* [x] Keep research separate from demo and live order placement.
* [x] Use one strategy implementation in backtest, demo, and live.
* [x] Keep 2025 and 2026 unseen during development.
* [x] Use 3x as baseline leverage; reserve 5x for a separate manual decision.
* [x] Use Telegram as read-only reporting before live trading.
* [x] Reject strategies whose apparent small-account profit does not represent
  scalable signal expectancy.
* [x] Remove rejected strategy code from the active tree while retaining Git
  history and a concise roadmap record.

---

# Work log

## 2026-07-30

* [x] Rejected EMA Trend Pullback v1 after its unchanged baseline and 27 fixed
  development variants failed the complete signal-quality test.
* [x] Reorganized shared strategy models, indicators, timeframes, and the
  strategy-independent backtest engine.
* [x] Removed EMA-specific active code, checks, reports, and commands.
* [x] Froze and implemented Donchian Breakout v1.
* [x] Added closed 1h-to-4h aggregation and no-look-ahead channel checks.
* [x] Added shared engine support for optional take profit and strategy exits.
* [x] Ran the unchanged Donchian baseline on 2023–2024 only.
* [x] Recorded positive complete expectancy together with its concentration in
  2024 and Long trades and the 10 USDT execution limitations.

## 2026-07-27

* [x] Completed the market-data foundation and verified the stored ETHUSDT
  history.

## Next task

* [~] Agree on whether to run a small predefined Donchian development
  comparison or reject the baseline as insufficiently stable.
