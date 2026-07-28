# Project Roadmap

## How to use this file

This file tracks the implementation state of the project.

The stable project context and architectural principles are stored in
`context.md`. Current setup and usage instructions are stored in `README.md`.
The existing code and database schema remain the source of truth for what is
actually implemented.

This roadmap contains:

* the current phase and active task;
* completed work;
* planned work;
* completion criteria;
* decisions that affect implementation;
* deferred ideas;
* the work log.

The roadmap should be updated after every meaningful completed task.

Statuses:

```text
[ ] Not started
[~] In progress
[x] Completed
[!] Blocked
[-] Deferred
```

---

# Current project state

## Current phase

```text
Phase 2 — First strategy
```

## Current objective

Define and implement the first transparent strategy hypothesis,
**EMA Trend Pullback**, and prepare it for a realistic sequential backtest.

## Current active task

```text
Define and freeze the concrete trading-decision model.
```

## Immediate path

* [x] Define one conventional and explainable strategy.
* [ ] Implement only the indicators required by that strategy.
* [ ] Implement one deterministic trading-decision path.
* [ ] Backtest it with realistic costs and Bybit constraints.
* [ ] Make only limited, explainable adjustments on development data.
* [ ] Freeze the configuration and run validation and out-of-sample tests.
* [ ] Run the same strategy in Bybit Demo Trading.
* [ ] Add required safety, monitoring, and Telegram reporting.
* [ ] Make a separate decision about small controlled live trading.

## Current constraints

* Keep the implementation simple and local.
* Use real stored Bybit data.
* Initial exchange: Bybit.
* Initial market: USDT perpetual futures.
* Initial symbol: `ETHUSDT`.
* Signal timeframe: `15m`.
* Trend timeframe: `1h`.
* Use UTC for all market timestamps.
* Use only fully closed candles.
* Start with one strategy and one approved configuration.
* Treat the trend filter as part of EMA Trend Pullback, not as a separate
  universal market-analysis framework.
* Do not build a generic strategy engine before it is needed.
* Backtest, demo, and live must use the same strategy implementation and
  decision model.
* Strategy development and review may use only 2023–2024 data.
* Do not inspect 2025 or 2026 results while changing strategy rules or
  parameters.
* An initial 10 USDT account must be evaluated against actual Bybit execution
  constraints.
* Profit is an objective, not a guaranteed daily or monthly outcome.

---

# Phase 0 — Environment and project setup

Status: [x] Completed

## Goal

Prepare a minimal and reproducible Python development environment.

## Tasks

* [x] Install VS Code.
* [x] Install or verify Python.
* [x] Create the project folder.
* [x] Create a virtual environment.
* [x] Select the virtual environment in VS Code.
* [x] Create `.gitignore`.
* [x] Create a private Git repository.
* [x] Add initial dependency configuration.
* [x] Add an environment check.
* [x] Add `context.md`.
* [x] Add `roadmap.md`.
* [x] Define the initial local project structure.

## Completion criteria

* [x] The project opens correctly in VS Code.
* [x] Python uses the local virtual environment.
* [x] Dependencies can be installed from the dependency file.
* [x] The environment check runs successfully.
* [x] Project context is stored in the repository.

---

# Phase 1 — Data foundation

Status: [x] Completed on 2026-07-27

## Goal

Create a reliable local source of historical and current closed ETHUSDT
candles.

## 1.1 Verify Bybit connectivity

### Tasks

* [x] Identify the public Bybit endpoint for perpetual kline data.
* [x] Send a minimal request without API keys.
* [x] Request a small ETHUSDT candle sample.
* [x] Print and inspect the raw response.
* [x] Confirm that access works from the current network.
* [x] Confirm the requested market category and symbol.
* [x] Document response ordering, timestamp format, numeric strings, current
  candle behavior, and request limits.

### Completion criteria

* [x] A small script successfully retrieves and displays real ETHUSDT candles.

---

## 1.2 Inspect and normalize candle data

### Tasks

* [x] Select the required response fields.
* [x] Convert timestamps to UTC.
* [x] Convert prices and volumes to numeric values.
* [x] Sort candles in chronological order.
* [x] Separate closed candles from the currently open candle.
* [x] Define one internal candle representation.
* [x] Validate OHLC relationships and interval alignment.

### Stored candle fields

```text
symbol
timeframe
open_time
open
high
low
close
volume
turnover
```

### Completion criteria

* [x] A real Bybit response can be transformed into a clean chronological
  candle collection.
* [x] Invalid candles fail validation with an explicit error.

---

## 1.3 Design the initial SQLite schema

### Tasks

* [x] Define the `market_candles` table.
* [x] Define field types.
* [x] Define the unique candle key.
* [x] Decide how timestamps are stored.
* [x] Add minimal database initialization.
* [x] Avoid unrelated future tables.

### Unique candle key

```text
symbol + timeframe + open_time
```

### Completion criteria

* [x] The database can be initialized repeatedly without errors.
* [x] Duplicate candles cannot create duplicate records.

---

## 1.4 Save and read a small real sample

### Tasks

* [x] Save downloaded candles to SQLite.
* [x] Read candles by symbol and timeframe.
* [x] Read a selected date range.
* [x] Confirm chronological ordering.
* [x] Repeat insertion and confirm that duplicates are not created.
* [x] Print a simple summary.

### Completion criteria

* [x] A real sample survives a save/read cycle without data loss or
  duplication.

---

## 1.5 Historical range downloader

### Tasks

* [x] Accept symbol, timeframe, start, and end parameters.
* [x] Split the requested period into API-sized requests.
* [x] Continue until the complete period is retrieved.
* [x] Save results incrementally.
* [x] Avoid duplicate rows.
* [x] Log progress simply.
* [x] Handle temporary request errors.
* [x] Allow safe restart after interruption.
* [x] Detect missing ranges.
* [x] Fill only the detected missing ranges.

### Initial target

```text
ETHUSDT
15m
1h
2023-01-01 through the latest available closed candle
```

### Completion criteria

* [x] A requested historical range is downloaded once and can be reused
  locally.
* [x] An interrupted or repeated run does not corrupt the dataset.

---

## 1.6 Incremental updater

### Tasks

* [x] Read the latest stored candle time.
* [x] Calculate the missing range.
* [x] Request only missing or overlapping recent candles.
* [x] Store only closed candles.
* [x] Avoid duplicates.
* [x] Report whether new candles were added.
* [x] Support both 15m and 1h.
* [x] Update all configured intervals through one reusable path.

### Intended behavior

```text
Program starts
    ↓
Find latest stored candle
    ↓
Download missing closed candles
    ↓
Validate and save them
    ↓
Data is synchronized
```

### Completion criteria

* [x] Future runs download only new or explicitly missing closed candles.

---

## 1.7 Data access for analysis

### Tasks

* [x] Load a selected candle range into pandas.
* [x] Return correct datetime and numeric types.
* [x] Support symbol and timeframe filters.
* [x] Return data in chronological order.
* [x] Avoid loading the entire database when only a limited period is needed.
* [x] Keep research code independent of Bybit and SQLite details.

### Completion criteria

* [x] Strategy and research code can request a period through one documented
  read interface.

---

## 1.8 Final data-layer verification

### Tasks

* [x] Download the complete 15m history.
* [x] Download the complete 1h history.
* [x] Check for missing candles.
* [x] Check for duplicate candles.
* [x] Check OHLC validity.
* [x] Check timestamp alignment.
* [x] Run SQLite integrity check.
* [x] Measure full pandas loading time.
* [x] Document the implemented commands in `README.md`.

### Verified data snapshot

```text
Market: linear ETHUSDT

15m:
  candles: 125,141
  first:   2023-01-01 00:00 UTC
  last:    2026-07-27 13:00 UTC

1h:
  candles: 31,285
  first:   2023-01-01 00:00 UTC
  last:    2026-07-27 12:00 UTC

gaps:                 0
duplicates:           0
invalid OHLC rows:    0
unaligned timestamps: 0
SQLite integrity:     ok
database size:        18,157,568 bytes
15m pandas load:      1.204 seconds
1h pandas load:       0.348 seconds
```

## Phase 1 completion criteria

* [x] Bybit connectivity is verified.
* [x] Historical candles can be downloaded and resumed safely.
* [x] Closed candles are validated and stored in SQLite.
* [x] Duplicates are prevented and gaps are detectable.
* [x] Requested periods can be loaded for analysis.
* [x] New candles can be added incrementally.
* [x] The complete initial dataset passes the control review.
* [x] The data layer has a simple documented interface.

---

# Phase 2 — First strategy

Status: [~] In progress

## Goal

Produce one fully specified and reproducible EMA Trend Pullback strategy that
can be used unchanged by backtest, demo, and live trading.

EMA Trend Pullback is a conventional trend-following hypothesis. Its selection
does not assume that it is profitable. Profitability and practical feasibility
must be tested after costs and exchange constraints.

## 2.1 Freeze the first-version strategy specification

### Tasks

* [x] Define the exact 1h EMA trend-permission rules.
* [x] Define the exact 15m pullback rules.
* [x] Define the exact continuation-confirmation rules.
* [x] Define long-entry conditions.
* [x] Define short-entry conditions.
* [x] Define no-entry conditions.
* [x] Define when a decision is produced.
* [x] Define the executable entry timing and reference price.
* [x] Define stop-loss calculation.
* [x] Define take-profit calculation.
* [x] Define maximum holding time if required by the hypothesis.
* [x] Define behavior when a position is already open.
* [x] Decide whether long and short rules are symmetrical.
* [x] List every configurable parameter and its initial value.
* [x] Record a version identifier for the frozen specification.

### Completion criteria

* [x] Every entry, exit, and no-entry outcome can be derived from written rules.
* [x] No strategy-rule choice is left implicit.

---

## 2.2 Freeze the trading decision model

The strategy returns an explicit trading decision. The exact decision actions
are frozen with the first strategy specification and may later be extended
without changing the stable project context.

### Tasks

* [ ] Define the concrete decision actions needed by the first strategy.
* [ ] Include the decision timestamp.
* [ ] Include direction when applicable.
* [ ] Include the entry reference when applicable.
* [ ] Include stop-loss and take-profit when applicable.
* [ ] Include an explicit reason.
* [ ] Include supporting indicator values.
* [ ] Include the strategy configuration version.
* [ ] Ensure the same model can represent entry, management, exit, or no
  action as required by the implementation.

### Completion criteria

* [ ] Backtest, demo, and live can consume the same decision object without
  translating strategy meaning.

---

## 2.3 Implement only the required indicators

### Tasks

* [ ] Load a selected 2023–2024 development period.
* [ ] Implement the exact EMA calculations required by the specification.
* [ ] Implement ATR only if required by the specification.
* [ ] Define the warm-up period.
* [ ] Define behavior when history is insufficient.
* [ ] Keep all indicator calculations in memory.
* [ ] Do not store indicator versions in SQLite.
* [ ] Add focused checks against independently calculated expected values.

### Completion criteria

* [ ] Indicator output is deterministic and does not use future candles.
* [ ] Only indicators required by the first strategy exist.

---

## 2.4 Align 15m and 1h data without look-ahead

### Tasks

* [ ] Associate each closed 15m candle with the last fully closed 1h candle
  available at that time.
* [ ] Verify UTC boundaries.
* [ ] Ensure the currently incomplete 1h candle is never used.
* [ ] Define identical alignment behavior for backtest, demo, and live.
* [ ] Add boundary-case checks around the hourly close.

### Completion criteria

* [ ] No 15m decision can access information that was unavailable at its
  decision time.

---

## 2.5 Implement the strategy

### Tasks

* [ ] Implement one deterministic decision path.
* [ ] Keep the strategy independent of Bybit, Telegram, and SQLite.
* [ ] Pass prepared market data, position state when required, and explicit
  configuration into the strategy.
* [ ] Return the frozen trading-decision model.
* [ ] Preserve the reason and supporting values for every decision.
* [ ] Ensure identical inputs produce identical decisions.

### Completion criteria

* [ ] The implementation matches the written specification.
* [ ] The same strategy function is suitable for all execution modes.

---

## 2.6 Limited implementation review

Use only selected sections from the 2023–2024 development period.

### Tasks

* [ ] Verify representative long decisions.
* [ ] Verify representative short decisions.
* [ ] Verify representative no-entry decisions.
* [ ] Verify signal and entry timing.
* [ ] Verify 15m/1h alignment.
* [ ] Verify warm-up behavior.
* [ ] Verify that no future values are used.
* [ ] Record and correct implementation errors only.
* [ ] Do not inspect 2025 or 2026 during this review.
* [ ] Do not visually tune rules to selected profitable examples.

## Phase 2 completion criteria

* [ ] The exact first-version strategy specification is frozen.
* [ ] The concrete decision model is frozen.
* [ ] Required indicators are implemented and checked.
* [ ] Multi-timeframe alignment is verified.
* [ ] Strategy behavior is deterministic and explainable.
* [ ] The strategy is ready for a sequential backtest.

---

# Phase 3 — Realistic backtest

Status: [ ] Not started

## Goal

Determine whether the frozen first strategy has useful expectancy after
realistic execution costs and whether its trades are feasible with the planned
initial capital.

## 3.1 Sequential simulation

### Tasks

* [ ] Process candles strictly in chronological order.
* [ ] Enter only according to the frozen execution-timing rule.
* [ ] Simulate stop-loss and take-profit.
* [ ] Define conservative behavior when both levels are touched in one candle.
* [ ] Prevent overlapping positions unless the specification explicitly allows
  them.
* [ ] Implement time-based or decision-based exits only if specified.
* [ ] Record every decision, attempted order, filled trade, and exit.

---

## 3.2 Costs and 10 USDT execution feasibility

### Tasks

* [ ] Model Bybit trading fees.
* [ ] Model configurable slippage.
* [ ] Model funding when a position crosses a funding timestamp.
* [ ] Define starting capital.
* [ ] Define risk per trade.
* [ ] Calculate position size from risk and stop distance.
* [ ] Model available margin and leverage.
* [ ] Obtain current ETHUSDT instrument constraints from an authoritative Bybit
  source at implementation time.
* [ ] Enforce minimum notional and quantity.
* [ ] Enforce quantity step and price tick.
* [ ] Apply the same price and quantity rounding planned for demo and live.
* [ ] Reject unexecutable trades with an explicit reason.
* [ ] Keep the execution-constraint logic reusable outside the backtest.

---

## 3.3 Metrics and reports

### Tasks

* [ ] Calculate trade count.
* [ ] Calculate unexecutable-decision count.
* [ ] Calculate gross and net PnL.
* [ ] Calculate total fees and funding.
* [ ] Calculate win rate.
* [ ] Calculate average trade result.
* [ ] Calculate expectancy.
* [ ] Calculate profit factor.
* [ ] Calculate maximum drawdown.
* [ ] Calculate the longest losing streak.
* [ ] Calculate return on starting capital.
* [ ] Report long and short results separately.
* [ ] Save the configuration, summary, and trade list reproducibly.

---

## 3.4 Run order

### Tasks

* [ ] Run a short technical period from 2023–2024.
* [ ] Correct simulator or implementation errors only.
* [ ] Run the complete 2023–2024 development backtest.
* [ ] Review whether the number of trades is sufficient to interpret.
* [ ] Record weaknesses without looking at 2025 or 2026.

## Phase 3 completion criteria

* [ ] The backtest has no known look-ahead path.
* [ ] Results include realistic costs and exchange constraints.
* [ ] The result can be reproduced from a saved configuration.
* [ ] A clear decision is recorded: reject, adjust, or continue to validation.

---

# Phase 4 — Limited strategy adjustment

Status: [ ] Not started

## Goal

Allow a small amount of explainable development without turning the project
into open-ended parameter research.

## Tasks

* [ ] Correct any remaining logical errors.
* [ ] Define a small number of meaningful parameter alternatives.
* [ ] Explain why each alternative is being tested.
* [ ] Use only 2023–2024 development data.
* [ ] Avoid large blind parameter grids.
* [ ] Avoid adding a new filter to explain every losing trade.
* [ ] Compare net results, drawdown, trade count, and subperiod consistency.
* [ ] Compare neighboring parameter values for fragility.
* [ ] Reject the strategy if it remains clearly unsuitable.
* [ ] Select one final configuration if evidence supports continuing.
* [ ] Freeze code, parameters, costs, and execution assumptions.
* [ ] Do not inspect 2025 or 2026 before the freeze.

## Completion criteria

* [ ] One final configuration is frozen, or the strategy is explicitly
  rejected.
* [ ] The reason for the decision is documented.

---

# Phase 5 — Validation and out-of-sample test

Status: [ ] Not started

## Goal

Test the frozen strategy on data that was not used to change its rules.

## Dataset split

```text
Development:   2023-01-01 through 2024-12-31
Validation:    2025-01-01 through 2025-12-31
Out-of-sample: 2026-01-01 through the latest available closed candle
```

## Tasks

* [ ] Confirm that strategy code and parameters are frozen.
* [ ] Run the 2025 validation period once.
* [ ] Do not tune the strategy from the 2025 result.
* [ ] Record validation PnL, drawdown, trade count, losing streaks, subperiod
  behavior, and execution feasibility.
* [ ] Apply the predefined validation decision criteria.
* [ ] Run the 2026 out-of-sample period only if the process still permits it.
* [ ] Do not tune the strategy from the 2026 result.
* [ ] Document the final validation decision.

## Completion criteria

* [ ] The strategy is rejected or explicitly approved for demo.
* [ ] Approval is based on net results, risk, stability, and execution
  feasibility rather than headline profit alone.

---

# Phase 6 — Bybit Demo Trading

Status: [ ] Not started

## Goal

Run the approved strategy in real time without risking real funds.

## 6.1 Demo execution

### Tasks

* [ ] Configure Bybit Demo Trading access.
* [ ] Store API credentials outside source control.
* [ ] Synchronize closed 15m and 1h candles at startup.
* [ ] Detect each new fully closed signal candle.
* [ ] Run only the approved strategy configuration.
* [ ] Use the same decision model as the backtest.
* [ ] Use the same sizing, instrument constraints, and rounding rules.
* [ ] Submit and track demo orders.
* [ ] Store decisions, orders, fills, positions, and errors.
* [ ] Reconcile local orders and positions with Bybit.
* [ ] Prevent duplicate orders for the same decision candle.
* [ ] Handle delayed data and temporary API failures.

---

## 6.2 Minimum demo safety

### Tasks

* [ ] Add persistent error logging.
* [ ] Stop trading after repeated critical errors.
* [ ] Add a persistent manual pause.
* [ ] Add duplicate-order protection.
* [ ] Detect local/exchange position mismatch.
* [ ] Recover safely after process restart.
* [ ] Never continue trading from an unknown position state.

---

## 6.3 Demo evaluation

### Tasks

* [ ] Compare demo decision timing with backtest assumptions.
* [ ] Compare expected and actual entry prices.
* [ ] Measure actual fees, funding, and slippage.
* [ ] Record missed, rejected, duplicated, or delayed actions.
* [ ] Run for a predefined minimum time or trade count.
* [ ] Document whether the full loop behaves as expected.

## Completion criteria

* [ ] The system can run unattended in demo without losing state.
* [ ] Orders and positions reconcile correctly.
* [ ] Safety controls work under tested failure scenarios.
* [ ] Demo behavior is sufficiently consistent with modeled behavior.

---

# Phase 7 — Monitoring, safety, and Telegram

Status: [ ] Not started

## Goal

Make system state and critical failures visible before any live activation.

## 7.1 Runtime monitoring

### Tasks

* [ ] Monitor candle freshness.
* [ ] Detect candle gaps.
* [ ] Monitor Bybit API availability.
* [ ] Monitor open orders and positions.
* [ ] Detect local/exchange state mismatch.
* [ ] Track current drawdown.
* [ ] Track repeated critical errors.
* [ ] Persist pause and emergency-stop state.
* [ ] Define safe recovery behavior for each critical condition.

---

## 7.2 Telegram notifications

Telegram is initially a read-only notification channel and text dashboard. It
does not select strategies or make trading decisions.

### Tasks

* [ ] Notify on system start and stop.
* [ ] Notify when market data becomes stale.
* [ ] Notify on critical errors.
* [ ] Notify when pause or emergency stop is activated.
* [ ] Notify when an order is created, filled, cancelled, or rejected.
* [ ] Notify when a position is opened or closed.

---

## 7.3 Telegram text summary

### Tasks

* [ ] Show completed trade count.
* [ ] Show the current open position.
* [ ] Show capital currently in exposure.
* [ ] Show realized PnL.
* [ ] Show unrealized PnL.
* [ ] Show fees and funding.
* [ ] Show current drawdown.
* [ ] Show system status and last fresh-data time.

## Completion criteria

* [ ] Critical failures are visible without opening the trading process.
* [ ] The operator can determine whether the system is trading, paused, stale,
  or in an error state.
* [ ] Monitoring failure cannot silently authorize trading.

---

# Phase 8 — Small controlled live trading

Status: [ ] Not started

## Goal

Verify the complete system with the smallest explicitly approved real-money
exposure.

Live activation requires a separate manual decision. Completion of earlier
code tasks does not activate trading automatically.

## Preconditions

* [ ] Validation and out-of-sample results do not show a critical breakdown.
* [ ] Demo has run stably for the agreed minimum time or trade count.
* [ ] Real fees, funding, slippage, rounding, and instrument limits are
  confirmed.
* [ ] Duplicate protection and reconciliation are tested.
* [ ] Monitoring and Telegram reporting are operational.
* [ ] Manual pause and emergency stop are tested.
* [ ] Starting capital and maximum acceptable loss are explicitly confirmed.
* [ ] Current Bybit rules permit the intended position size and risk model.

## Initial live restrictions

* [ ] Trade only `ETHUSDT`.
* [ ] Use only the approved strategy and frozen configuration.
* [ ] Use approximately 10 USDT only if exchange constraints permit it.
* [ ] Use the smallest approved risk per trade.
* [ ] Do not optimize parameters automatically.
* [ ] Do not replace the active strategy automatically.
* [ ] Require manual approval for configuration changes.
* [ ] Revalidate material changes before returning them to live.

## Completion criteria

* [ ] The full loop behaves correctly with real executions.
* [ ] Loss and drawdown remain within the approved limits.
* [ ] Any decision to increase capital is separate, evidence-based, and
  manually approved.

---

# Later development

Status: [-] Deferred

Only after the first strategy completes the full controlled path:

* [-] Evaluate other conventional strategy hypotheses.
* [-] Compare multiple strategies under one validation protocol.
* [-] Add controlled strategy selection.
* [-] Add other trading pairs.
* [-] Add broader offline research tools.
* [-] Add session filters if justified by evidence.
* [-] Expand Telegram reporting.
* [-] Add more detailed analytics and reporting.

Every additional strategy must pass:

1. exact specification;
2. implementation without look-ahead;
3. development backtest;
4. limited adjustment;
5. configuration freeze;
6. validation and out-of-sample testing;
7. demo trading;
8. a separate live-activation decision.

---

# Explicitly deferred scope

* [-] Machine learning.
* [-] Tick-data and order-book research.
* [-] High-frequency trading.
* [-] Multi-exchange support.
* [-] A large portfolio framework.
* [-] Cloud or distributed infrastructure.
* [-] Plugin architecture.
* [-] Continuous parameter optimization.
* [-] Autonomous strategy creation or replacement.
* [-] A complex graphical dashboard.

These items must not complicate the first path from one strategy to controlled
live trading.

---

# Decision log

* [x] Keep the system local and simple while that remains sufficient.
* [x] Use real data and realistic execution assumptions.
* [x] Start with one conventional and explainable strategy.
* [x] Keep trend permission inside EMA Trend Pullback.
* [x] Let the strategy return an explicit trading decision.
* [x] Freeze the concrete decision model during strategy specification.
* [x] Use the same strategy implementation in backtest, demo, and live.
* [x] Treat backtest as the first test, not proof of future profit.
* [x] Keep validation, out-of-sample testing, and demo before live.
* [x] Use Telegram as read-only reporting before live.
* [x] Defer automatic strategy selection until multiple validated strategies
  actually exist.

---

# Work log

## 2026-07-27

* [x] Completed Phase 1.
* [x] Downloaded complete ETHUSDT 15m and 1h history from 2023-01-01.
* [x] Verified continuity, integrity, OHLC validity, and read performance.
* [x] Documented the data-layer commands.
* [x] Revised the roadmap to focus on one strategy and the shortest controlled
  route to live trading.
* [x] Deferred the general research platform and automatic strategy selection.
* [x] Froze the EMA Trend Pullback v1 baseline specification.

## Next task

* [~] Define and freeze the concrete trading-decision model.
