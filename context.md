# Project Context

## 1. Purpose

Build a transparent and reproducible algorithmic trading system intended to
discover, validate and operate strategies with validated positive expectancy while
keeping risk and drawdown within explicit limits.

The long-term business objective is to produce withdrawable trading income
after sufficient capital has been accumulated. This objective does not imply
guaranteed daily or monthly profit.

Research is a tool for discovering, rejecting, validating, and improving
trading ideas. Research itself is not the final product.

Every market classification, signal, risk calculation, order, and strategy
change must be explainable and reproducible.

---

## 2. Sources of truth

This file contains stable project principles and architectural boundaries.

`roadmap.md` contains:

* the current phase;
* the active task;
* implementation status;
* deferred work;
* the decision and work logs.

`README.md` contains current setup and usage instructions.

The existing code and database schema are the source of truth for what is
actually implemented.

If these sources disagree, do not silently choose one. Inspect the current
state, explain the mismatch, and update the appropriate document only after the
intended behavior is confirmed.

---

## 3. Current scope

The initial complete trading cycle is intentionally limited to:

* exchange: Bybit;
* market: USDT perpetual futures;
* symbol: `ETHUSDT`;
* signal timeframe: `15m`;
* market-regime timeframe: `1h`;
* profit and loss currency: USDT;
* trading style: intraday and candle based;
* one transparent strategy under development and, once approved, one active
  configuration.

The roadmap identifies the current strategy hypothesis. A new strategy is not
part of the active scope merely because it may be useful later.

The system is allowed to remain out of the market. Continuous operation does
not mean continuous trading, and trade frequency must not be forced.

The project is designed for a normal laptop. It is not intended to become an
HFT platform, institutional execution system, or autonomous AI trader.

---

## 4. Core architecture

The system is divided into logical responsibility layers:

```text
Data
    ↓
Research
    ↓
Strategy
    ↓
Backtest
    ↓
Decision
    ↓
Trading
    ↓
Monitoring
```

These are responsibility boundaries. They do not require complex class
hierarchies, frameworks, services, or separate processes unless a current task
demonstrates a real need.

### 4.1 Data

Responsible for:

* downloading historical candles;
* incrementally updating closed candles;
* storing candles;
* preventing duplicates;
* loading requested ranges;
* reporting data-access errors.

The Data layer does not calculate indicators, classify regimes, generate
signals, or place orders.

### 4.2 Research

Responsible for:

* calculating indicators in memory;
* examining market regimes;
* testing explicit hypotheses;
* comparing strategies and parameters;
* investigating weaknesses;
* producing candidate configurations.

Research never places demo or live orders and never changes the active trading
configuration directly.

### 4.3 Strategy

Receives prepared market data, current position state when required, and an
explicit configuration.

It returns an explicit trading decision.

The concrete decision model is defined when the strategy is implemented. It
may represent entry, exit, position management, or no action and may include
supporting values such as a reason, stop-loss level, and take-profit level.

The same decision model and strategy implementation must be used by backtest,
demo, and live trading.

A strategy must define, as applicable:

* entry conditions;
* no-trade conditions;
* exit conditions;
* stop-loss calculation;
* take-profit calculation;
* maximum holding time, if required by the hypothesis;
* an explanation and supporting values.

The Strategy layer contains trading rules only. It does not communicate with
Bybit or SQLite.

### 4.4 Backtest

Processes historical candles sequentially and simulates:

* entries and exits;
* position sizing;
* stop loss and take profit;
* commissions;
* slippage;
* trade results and performance metrics.

Backtest, demo, and live trading must call the same strategy implementation.

### 4.5 Decision

Stores the approved production state:

* active strategy;
* active parameters;
* whether trading is allowed;
* candidate and active status;
* strategy-change history.

A candidate never becomes active merely because it recently performed better.
Promotion requires validation and manual or explicitly controlled approval.

### 4.6 Trading

Uses only the approved configuration.

Responsible for:

* startup data synchronization;
* reacting to new closed candles;
* checking whether trading is allowed;
* calculating risk and position size;
* placing and checking orders;
* recording trades and execution errors;
* restart and position recovery.

Demo trading must be stable before live trading begins.

### 4.7 Monitoring

Observes:

* data freshness and gaps;
* API connectivity and failures;
* order and position state;
* drawdown and risk limits;
* rolling strategy health;
* system errors.

Monitoring may reduce risk or pause trading according to approved rules. It
must not optimize parameters or replace strategy logic automatically.

Telegram is planned initially as a read-only notification and text-dashboard
channel for system state, trades, open exposure, profit, loss, and errors. It is
not initially a source of trading decisions or strategy changes.

---

## 5. Market-data and time invariants

Raw market candles are the primary source data.

The following rules are mandatory:

* all stored market timestamps use UTC;
* only closed candles are used for initial analysis and trading decisions;
* candles are processed chronologically;
* historical simulation never accesses future candles;
* a `1h` regime associated with a `15m` candle must use only the last closed
  `1h` candle available at that moment;
* requested database ranges are filtered before unnecessary data is loaded;
* historical and incremental downloads use the same Bybit client and
  normalization logic;
* repeated downloads must be safe and must not create duplicate candles.

The natural candle key is:

```text
symbol + timeframe + open_time
```

If data contains gaps, duplicates, invalid OHLC values, unaligned timestamps,
or an open candle where only closed candles are expected, the problem must be
reported rather than silently hidden.

---

## 6. Storage and computation policy

SQLite is the initial persistent store.

Persist data that is important, costly, or impossible to reproduce exactly,
including when the corresponding phase requires it:

* market candles;
* approved strategy configurations;
* important backtest summaries and selected trades;
* demo and live trades;
* production decisions;
* relevant errors and health records.

Normally keep reproducible temporary calculations in memory:

* EMA and ATR columns;
* temporary DataFrames;
* intermediate experiment values;
* debug output.

Do not store every indicator or parameter variation in SQLite.

The database schema evolves incrementally. Add a table only when the current
phase needs it. Do not create speculative future tables.

---

## 7. Research and validation policy

Research and production trading are independent.

The production process uses a fixed approved configuration. Research may
modify development candidates, test alternatives, and investigate degradation,
but it does not directly control production.

Candidate lifecycle:

```text
Hypothesis
    ↓
Development research
    ↓
Candidate with frozen rules and parameters
    ↓
Validation
    ↓
Out-of-sample evaluation
    ↓
Demo validation
    ↓
Manual or explicitly controlled approval
    ↓
Live
```

Historical datasets have different roles:

* development data may be reused for strategy design and tuning;
* validation data is evaluated with frozen rules and parameters;
* out-of-sample data is evaluated only after a final candidate is selected.

If logic or parameters change after validation results are observed, the result
is a new candidate and must repeat validation. A validation period repeatedly
used for tuning is no longer independent validation.

Candidate selection should prefer:

* positive results after fees and realistic slippage;
* acceptable drawdown and losing streaks;
* a reasonable number of trades;
* consistency across subperiods;
* stable neighboring parameter values;
* understandable failure modes.

Do not select a configuration only because it has the highest historical
profit.

---

## 8. Strategy selection and automation

The first complete cycle uses one strategy and one active configuration.

Future research may examine different strategies for different regimes,
volatility conditions, or sessions. This does not authorize automatic strategy
switching now.

Any future automated selection must have:

* multiple independently validated strategies;
* explicit selection rules;
* out-of-sample evidence;
* demo validation;
* risk limits and safe fallback behavior;
* an explicit roadmap decision authorizing activation.

The system must never introduce a strategy only to remain continuously in the
market.

---

## 9. Risk principles

Profitability must always be evaluated together with risk.

Before demo or live trading, explicitly define:

* capital allocated to the system;
* risk per trade;
* maximum position size and leverage;
* maximum daily and total drawdown;
* maximum concurrent exposure;
* pause and emergency-stop conditions;
* exchange minimum-order and quantity-step constraints.

The initial capital experiment may start with 10 USDT, but growing 10 USDT to
100 USDT is an aspiration, not proof by itself that a strategy is robust. A
strategy is judged by validated expectancy, drawdown, execution realism, and
survival risk rather than one short profitable run.

Risk, fee, slippage, and position-sizing calculations must each have one source
of truth and must be shared by backtest, demo, and live execution where
applicable.

---

## 10. Development principles

### KISS

Prefer:

* plain Python functions;
* small focused modules;
* direct readable control flow;
* pandas for analysis;
* SQLite for local persistence;
* configuration files for parameters when parameters appear.

Avoid unnecessary:

* design patterns;
* service and repository layers;
* abstract base classes with one implementation;
* dependency-injection frameworks;
* plugin systems;
* complex event systems;
* premature concurrency or optimization.

Introduce an abstraction only after a real current need is demonstrated.

### DRY

Shared behavior has one source of truth, especially:

* strategy rules across backtest, demo, and live;
* market-data requests and normalization;
* indicator calculations;
* active configuration;
* risk, fee, slippage, and position-sizing calculations.

DRY does not justify a universal abstraction before duplication exists.

### YAGNI

Before adding functionality, ask:

1. What current problem does it solve?
2. Which current roadmap task requires it?
3. What is the simplest implementation?
4. Can it be postponed without blocking current work?

If the answer is only "maybe later", document the idea and do not implement it.

---

## 11. Technical boundaries

Current stack:

* Python;
* SQLite;
* pandas;
* direct Bybit API access.

Current non-goals:

* high-frequency or tick-level trading;
* order-book microstructure research;
* machine learning and neural networks;
* distributed or cloud infrastructure;
* automatic deployment;
* multiple exchanges;
* a large multi-symbol portfolio;
* automatic strategy replacement;
* continuous parameter optimization;
* a complex web dashboard.

These boundaries may change only through an explicit roadmap revision. Do not
implement them as preparation for hypothetical future needs.

If performance becomes a problem, first measure the actual bottleneck and
simplify the experiment before introducing infrastructure.

---

## 12. Agent and communication rules

Before implementation:

1. Read this context.
2. Read `roadmap.md`.
3. Identify the current phase and active task.
4. Inspect existing code and the working tree.
5. Explain significant architectural changes before making them.
6. Distinguish requirements, assumptions, future ideas, and optional work.
7. Implement only the agreed current scope.

During and after implementation:

* preserve unrelated user changes;
* reuse existing logic where appropriate;
* avoid abstractions created only for appearance;
* do not add major dependencies without explanation;
* run checks proportional to the risk of the change;
* update the roadmap after meaningful completed work;
* record decisions that affect future phases;
* do not claim completion without verification.

If a proposed change materially increases complexity or alters approved trading
behavior, stop and discuss it before implementation.

Never:

* silently redesign the architecture;
* implement future roadmap phases without request;
* let research directly alter production state;
* expose credentials or store secrets in source control;
* claim or imply guaranteed trading profit.

---

## 13. Definition of success

The first successful version is not a fully autonomous trading system.

It consists of:

* reliable and validated market data;
* reproducible historical analysis;
* an understandable market-regime classification;
* one transparent strategy;
* realistic backtesting with fees, slippage, and risk;
* a candidate that passes validation and out-of-sample evaluation;
* stable demo trading;
* explicit risk and recovery controls;
* clear separation between research and execution;
* observable decisions and system health.

Live trading is a later controlled milestone, not the starting point.

---

## 14. Architecture stability

The architecture should remain stable, but it may evolve when a demonstrated
current need cannot be handled cleanly by the existing responsibilities.

When a proposed change affects multiple sections of this document,
first determine whether the existing architecture can solve the problem
with a simpler implementation.

Prefer the smallest change that preserves clear responsibility boundaries.

Extend an existing component when the new behavior belongs to the same
responsibility. Introduce a focused component only when keeping the behavior
in an existing component would blur responsibilities or create real
duplication.

After an architecture change is approved, update this document before or
together with its implementation.
