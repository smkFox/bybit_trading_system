# Project Roadmap

## How to use this file

This file tracks the implementation state of the project.

The project context and architectural principles are stored in:

```text
context.md
```

This roadmap contains:

* current phase;
* completed work;
* active task;
* next tasks;
* decisions that affect implementation;
* known problems;
* deferred ideas.

The agent should update this file after every meaningful completed task.

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
Phase 1 — Data foundation
```

## Current objective

Create a reliable minimal Data Layer for ETHUSDT candles from Bybit.

## Current active task

```text
Verify public Bybit API connectivity and inspect a real candle response.
```

## Current constraints

* Keep implementation simple.
* Use real Bybit data.
* Do not implement strategy or backtest yet.
* Do not design the complete future database yet.
* Do not use API keys for public market data.
* Use UTC for all market timestamps.
* Use SQLite as local storage.
* Use pandas only where it is useful.
* Initial timeframes: 15 minutes and 1 hour.
* Initial symbol: ETHUSDT perpetual futures.

---

# Phase 0 — Environment and project setup

## Goal

Prepare a minimal Python development environment.

## Tasks

* [x] Install VS Code.
* [x] Install or verify Python.
* [x] Create the project folder.
* [x] Create a virtual environment.
* [x] Select the virtual environment in VS Code.
* [ ] Create `.gitignore`.
* [ ] Create a private Git repository.
* [ ] Add initial dependency configuration.
* [ ] Add a minimal README.
* [ ] Add `context.md`.
* [ ] Add `roadmap.md`.

## Completion criteria

The project can be opened in VS Code, Python uses the local virtual environment, and project context is stored in the repository.

---

# Phase 1 — Data foundation

## Goal

Create a reliable source of historical and current closed ETHUSDT candles.

## 1.1 Verify Bybit connectivity

### Tasks

* [ ] Identify the public Bybit endpoint for perpetual kline data.
* [ ] Send a minimal request without API keys.
* [ ] Request a small ETHUSDT candle sample.
* [ ] Print the raw response.
* [ ] Confirm whether access works from the current network.
* [ ] Record any VPN or regional-access requirement.
* [ ] Confirm the requested market category and symbol.

### Questions to answer

* Does Bybit respond successfully?
* What is the response structure?
* Are numeric fields returned as strings?
* In which order are candles returned?
* How is candle time represented?
* Does the response include the currently open candle?
* What pagination or request limits apply?

### Completion criteria

A small script successfully retrieves and displays real ETHUSDT candles.

---

## 1.2 Inspect and normalize candle data

### Tasks

* [ ] Decide which returned fields are required.
* [ ] Convert timestamps to UTC.
* [ ] Convert prices and volumes to numeric values.
* [ ] Sort candles in chronological order.
* [ ] Separate closed candles from the currently open candle.
* [ ] Define a simple internal candle representation.

### Expected candle fields

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

This list may be adjusted after inspecting the real response.

### Completion criteria

The application can transform a real Bybit response into a clean chronological candle collection.

---

## 1.3 Design the initial SQLite schema

### Tasks

* [ ] Define the `market_candles` table.
* [ ] Define field types.
* [ ] Define the unique candle key.
* [ ] Decide how timestamps are stored.
* [ ] Add minimal database initialization.
* [ ] Avoid unrelated future tables.

### Expected unique key

```text
symbol + timeframe + open_time
```

### Completion criteria

The database can be initialized repeatedly without errors.

---

## 1.4 Save and read a small real sample

### Tasks

* [ ] Save downloaded candles to SQLite.
* [ ] Read them back by symbol and timeframe.
* [ ] Read a selected date range.
* [ ] Confirm chronological ordering.
* [ ] Repeat insertion and confirm that duplicates are not created.
* [ ] Print a simple summary.

### Completion criteria

A real downloaded sample survives a save/read cycle without data loss or duplication.

---

## 1.5 Historical range downloader

### Tasks

* [ ] Accept symbol, timeframe, start, and end parameters.
* [ ] Split the requested period into API-sized requests.
* [ ] Continue until the full period is retrieved.
* [ ] Save results incrementally.
* [ ] Avoid duplicate rows.
* [ ] Log progress simply.
* [ ] Handle temporary request errors.
* [ ] Allow safe restart after interruption.

### Initial target

```text
ETHUSDT
15m
1h
2023-01-01 through the latest available closed candle
```

A shorter test range should be used first.

### Completion criteria

A requested historical range is downloaded once and can be reused locally.

---

## 1.6 Incremental updater

### Tasks

* [ ] Read the latest stored candle time.
* [ ] Calculate the missing range.
* [ ] Request only missing or overlapping recent candles.
* [ ] Store only closed candles.
* [ ] Avoid duplicates.
* [ ] Report whether new candles were added.
* [ ] Support both 15m and 1h.

### Intended behavior

```text
Program starts
    ↓
Find latest stored candle
    ↓
Download missing closed candles
    ↓
Save them
    ↓
Data is synchronized
```

### Completion criteria

After the database is initialized, future runs download only new candles.

---

## 1.7 Data access for analysis

### Tasks

* [ ] Load a selected candle range into pandas.
* [ ] Return correct datetime and numeric types.
* [ ] Support symbol and timeframe filters.
* [ ] Return data in chronological order.
* [ ] Avoid loading the entire database when only a limited period is needed.

### Completion criteria

Research code can request a period without knowing Bybit API or SQLite implementation details.

---

## Phase 1 completion criteria

Phase 1 is complete when:

* Bybit connectivity is verified;
* historical candles can be downloaded;
* closed candles are stored in SQLite;
* duplicates are prevented;
* requested periods can be loaded;
* new candles can be incrementally added;
* the module has a simple documented interface.

---

# Phase 2 — Market analysis

## Goal

Determine the market regime using real stored data.

## 2.1 Indicator calculation

* [ ] Load a real historical period.
* [ ] Calculate required EMA values.
* [ ] Calculate ATR if required.
* [ ] Keep calculations in memory.
* [ ] Avoid storing every indicator version in SQLite.

## 2.2 Trend or regime definition

* [ ] Define the first explicit trend rules.
* [ ] Support `UPTREND`.
* [ ] Support `DOWNTREND`.
* [ ] Support `SIDEWAYS`.
* [ ] Support `UNKNOWN` when history is insufficient.
* [ ] Keep parameters configurable.

## 2.3 Real-data review

* [ ] Run regime detection on selected historical periods.
* [ ] Export or display results.
* [ ] Compare several sections with a chart.
* [ ] Record weaknesses of the first trend definition.
* [ ] Adjust rules only after explaining the reason.

## 2.4 Timeframe alignment

* [ ] Associate the last closed 1h regime with each 15m candle.
* [ ] Ensure the current incomplete 1h candle is never used.
* [ ] Produce one analysis-ready DataFrame.

## Phase 2 completion criteria

For any requested historical period, the system can assign a market regime to each relevant 15-minute candle using only information available at that time.

---

# Phase 3 — First strategy

## Goal

Implement the first transparent strategy.

## Initial strategy

```text
Trend Pullback
```

## Tasks

* [ ] Define exact Long conditions.
* [ ] Define exact Short conditions.
* [ ] Define no-trade conditions.
* [ ] Define configurable parameters.
* [ ] Define stop-loss calculation.
* [ ] Define take-profit calculation.
* [ ] Return a clear signal result.
* [ ] Include a reason for each signal.
* [ ] Keep the strategy independent of Bybit and SQLite.

## Initial regime behavior

```text
UPTREND → Long opportunities
DOWNTREND → Short opportunities
SIDEWAYS → No trade
UNKNOWN → No trade
```

## Phase 3 completion criteria

The strategy receives prepared market data and returns reproducible `LONG`, `SHORT`, or `NO_SIGNAL` decisions.

---

# Phase 4 — Backtest

## Goal

Simulate the strategy on historical candles.

## Tasks

* [ ] Process candles sequentially.
* [ ] Enter only after a completed signal candle.
* [ ] Simulate stop-loss and take-profit.
* [ ] Define behavior when both are touched in one candle.
* [ ] Include trading fees.
* [ ] Include configurable slippage.
* [ ] Calculate position size from risk.
* [ ] Record every simulated trade.
* [ ] Calculate key metrics.
* [ ] Run a short real-data period first.
* [ ] Review selected trades manually.
* [ ] Run a longer historical period.

## Initial metrics

```text
trade count
win rate
net profit
fees
average trade
profit factor
maximum drawdown
maximum losing streak
Long result
Short result
```

## Phase 4 completion criteria

One fixed strategy configuration can be run on a requested historical period and produce a reproducible trade list and summary.

---

# Phase 5 — Parameter research and validation

## Goal

Find stable configurations without fitting historical noise.

## 5.1 Parameter search

* [ ] Define a limited meaningful parameter range.
* [ ] Avoid huge blind grids.
* [ ] Run one backtest per configuration.
* [ ] Save summary metrics.
* [ ] Save full trades only for selected runs.
* [ ] Measure execution time.

## 5.2 Candidate selection

* [ ] Exclude configurations with too few trades.
* [ ] Review net result after fees.
* [ ] Review drawdown.
* [ ] Review consistency across subperiods.
* [ ] Compare neighboring parameter values.
* [ ] Select several candidates rather than one maximum result.

## 5.3 Validation

Planned dataset roles:

```text
2023–2024 → development
2025 → validation
2026 → out-of-sample
```

Tasks:

* [ ] Freeze candidate parameters.
* [ ] Run validation period.
* [ ] Reject or retain candidates.
* [ ] Freeze final candidate.
* [ ] Run out-of-sample period.
* [ ] Document the decision.

## Phase 5 completion criteria

At least one configuration has passed development, validation, and out-of-sample evaluation without parameter changes between those stages.

---

# Phase 6 — Demo trading

## Goal

Run the approved strategy on current data without real funds.

## Tasks

* [ ] Configure Bybit demo access.
* [ ] Store credentials securely.
* [ ] Synchronize candles at startup.
* [ ] React to each new closed 15m candle.
* [ ] Update the 1h regime when required.
* [ ] Use the active approved configuration.
* [ ] Check whether a position is already open.
* [ ] Calculate risk and size.
* [ ] Submit demo orders.
* [ ] Track order status.
* [ ] Store demo trades.
* [ ] Handle restart and recovery.
* [ ] Prevent historical signals from becoming delayed orders.

## Phase 6 completion criteria

The system can operate continuously in demo mode and produce decisions consistent with the backtest strategy.

---

# Phase 7 — Monitoring and strategy lifecycle

## Goal

Observe production behavior without continuous retuning.

## Tasks

* [ ] Define active configuration storage.
* [ ] Define candidate configuration storage.
* [ ] Add paused state.
* [ ] Record strategy changes.
* [ ] Monitor data freshness.
* [ ] Monitor API failures.
* [ ] Monitor current drawdown.
* [ ] Monitor rolling trade performance.
* [ ] Add basic strategy-health states.
* [ ] Add notifications if needed.

Possible health states:

```text
GREEN
YELLOW
RED
```

These states should control risk or pause behavior, not automatically optimize parameters.

## Phase 7 completion criteria

The system can identify technical or performance problems and pause trading safely.

---

# Phase 8 — Parallel research

## Goal

Allow research while demo or live trading continues.

## Principles

* Trading keeps using the active fixed configuration.
* Research works on a snapshot or selected database range.
* Research has lower priority than trading.
* Heavy research is scheduled rather than continuous.
* Research produces candidates only.
* Candidate activation is a separate controlled decision.

## Tasks

* [ ] Define manual research execution.
* [ ] Add optional scheduled research.
* [ ] Prevent research from blocking trading.
* [ ] Store candidate results.
* [ ] Compare champion and challengers.
* [ ] Define promotion criteria.
* [ ] Require demo validation before live promotion.

## Phase 8 completion criteria

Research can produce new candidates without modifying or interrupting the active strategy.

---

# Phase 9 — Additional strategies

## Goal

Introduce new strategies only after the first complete cycle works.

Potential research directions:

```text
breakout
range trading
volatility expansion
time-of-day filters
session filters
regime-specific strategies
```

Each new strategy must pass the same process:

```text
hypothesis
→ implementation
→ backtest
→ validation
→ demo
→ approval
```

Automatic switching between strategies is deferred until there is sufficient evidence that multiple independently validated strategies are useful.

---

# Phase 10 — Live trading

## Goal

Use real funds only after stable demo operation.

## Preconditions

* [ ] Data synchronization is stable.
* [ ] Strategy behavior matches backtest assumptions.
* [ ] Demo execution is stable.
* [ ] Risk limits are implemented.
* [ ] Recovery after restart is tested.
* [ ] Monitoring is active.
* [ ] Emergency pause is available.
* [ ] Initial capital and maximum loss are explicitly defined.

## Initial live restrictions

```text
one symbol
one active strategy
small capital
low fixed risk
no automatic strategy replacement
manual supervision
```

## Phase 10 completion criteria

The system trades a small controlled live allocation with documented risk and recovery procedures.

---

# Deferred ideas

The following ideas are intentionally deferred:

* [–] Machine learning.
* [–] Neural networks.
* [–] Tick-level data.
* [–] Order book analysis.
* [–] Multiple exchanges.
* [–] Large multi-symbol portfolio.
* [–] Cloud deployment.
* [–] Distributed backtesting.
* [–] Fully autonomous strategy replacement.
* [–] Continuous parameter optimization.
* [–] Complex web dashboard.
* [–] High-frequency execution.

These items should not be implemented unless the roadmap is explicitly revised.

---

# Decision log

Add important decisions below.

## Decision 001 — System instead of a single bot

The project will be built as separate data, research, strategy, backtest, decision, trading, and monitoring responsibilities.

Reason:

The system must support reproducible research and controlled strategy changes without mixing experimentation with live execution.

## Decision 002 — Research does not directly control trading

The active trading configuration remains fixed until a candidate has completed validation and approval.

Reason:

Automatic retuning based on recent data would create overfitting and unstable behavior.

## Decision 003 — Start with real data

Development begins by verifying Bybit connectivity and inspecting real candle responses.

Reason:

The storage format and download logic should be based on the actual API response rather than imagined data structures.

## Decision 004 — Local and simple first

Initial implementation uses Python, SQLite, and pandas on the current laptop.

Reason:

The planned candle-based workload does not require institutional infrastructure.

---

# Work log

Add completed work in reverse chronological order.

## YYYY-MM-DD

### Completed

* Example completed task.

### Changed

* Example changed decision.

### Verified

* Example command or result.

### Next

* Example next task.

### Problems

* Example known problem.
