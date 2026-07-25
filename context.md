# Project Context

## 1. Project overview

The project originally started as an idea for a cryptocurrency trading bot.

During planning, the scope evolved into a small research and trading system that can:

* collect and store market data;
* analyze historical market behavior;
* determine the current market regime;
* run trading strategies;
* backtest strategies on historical data;
* compare strategy parameters;
* select an approved configuration;
* trade in demo mode and, later, live mode;
* monitor whether the active strategy continues to behave within expected limits.

The project is not intended to become a high-frequency trading platform, institutional trading system, or fully autonomous AI trader.

The first target instrument is:

* Exchange: Bybit
* Market: USDT perpetual futures
* Symbol: ETHUSDT
* Main signal timeframe: 15 minutes
* Higher timeframe for market regime: 1 hour
* Profit and loss currency: USDT

The first strategy under consideration is Trend Pullback.

---

## 2. Main project goal

The main goal is to build a transparent system in which every trading decision can be explained and reproduced.

The intended process is:

```text
Market data
    ↓
Market analysis
    ↓
Strategy
    ↓
Backtest
    ↓
Validation
    ↓
Demo trading
    ↓
Live trading
```

The system should make it possible to answer:

* What data was used?
* Which market regime was detected?
* Which strategy was active?
* Which parameters were used?
* Why was a signal generated?
* How was the position size calculated?
* Why was the trade closed?
* How did the strategy perform historically?
* Is the current configuration still behaving as expected?

---

## 3. Scope principles

The project must remain appropriate for a personal system running on a normal laptop.

The system is designed around:

* one exchange initially;
* one trading symbol initially;
* a small number of strategies;
* candle-based trading rather than high-frequency data;
* research performed periodically rather than continuously;
* simple local storage;
* transparent Python code;
* manual approval of important strategy changes.

The following are not current goals:

* high-frequency trading;
* order book microstructure research;
* machine learning;
* neural networks;
* tick-level data processing;
* distributed computing;
* cloud infrastructure;
* automatic deployment;
* automatic strategy replacement without validation;
* large-scale portfolio management;
* support for many exchanges and hundreds of symbols.

These features must not be implemented merely as preparation for a hypothetical future.

---

## 4. Development principles

### KISS

Keep the implementation as simple as possible.

Prefer:

* plain Python functions;
* small focused modules;
* pandas for analysis;
* SQLite for local persistence;
* configuration files for parameters;
* direct and readable control flow.

Avoid unnecessary:

* design patterns;
* service layers;
* interfaces with only one implementation;
* abstract base classes without a current need;
* dependency injection frameworks;
* repository frameworks;
* generic plugin systems;
* complex event systems;
* premature concurrency;
* premature optimization.

A new abstraction should be introduced only when existing code has demonstrated a real need for it.

### DRY

Shared logic must have one source of truth.

In particular:

* the same strategy logic should be used by backtest, demo, and live trading;
* the same market-data client should support historical and incremental downloads;
* indicators should not be implemented separately in different modules;
* active configuration should be read from one defined source;
* fee and risk calculations should not be duplicated.

DRY does not mean creating a universal abstraction before duplication exists.

### YAGNI

Do not implement functionality only because it may be useful someday.

Before adding a feature, determine:

1. What current problem does it solve?
2. Which existing phase requires it?
3. What is the simplest implementation?
4. Can it be postponed without blocking current work?

If a feature is only a future idea, document it but do not implement it.

---

## 5. Communication and decision rules

All significant changes must be explained before implementation.

For each new module, table, dependency, abstraction, or process, describe:

* what problem it solves;
* why it is needed now;
* what data it receives;
* what result it returns;
* which other modules depend on it;
* what simpler alternatives were considered;
* what is intentionally excluded.

The project must not silently drift into a different architecture.

When a proposed change increases complexity, stop and discuss it before implementation.

The agent must clearly distinguish:

* current requirements;
* assumptions;
* future ideas;
* optional improvements;
* confirmed decisions.

The agent should not treat a future possibility as a current requirement.

---

## 6. System layers

The system is divided into logical layers. These are responsibility boundaries, not a requirement to create deep class hierarchies.

### 6.1 Data Layer

Responsible for market data and persistence.

Responsibilities:

* verify public Bybit connectivity;
* download historical candles;
* incrementally download new closed candles;
* store candles in SQLite;
* avoid duplicates;
* retrieve requested ranges;
* provide data to research and trading processes.

The Data Layer does not determine trends or generate trading signals.

### 6.2 Research Layer

Responsible for historical analysis.

Responsibilities:

* load selected historical periods;
* calculate indicators;
* examine market regimes;
* run strategy experiments;
* compare results;
* investigate weaknesses;
* produce strategy candidates.

The Research Layer never sends real orders.

### 6.3 Strategy Layer

Responsible for trading rules.

A strategy receives prepared market data and configuration parameters.

It returns a decision such as:

```text
LONG
SHORT
NO_SIGNAL
```

It may also return:

* reason for the signal;
* stop-loss level;
* take-profit level;
* supporting values.

The Strategy Layer does not communicate directly with Bybit or SQLite.

### 6.4 Backtest Layer

Responsible for simulating historical trading.

Responsibilities:

* apply a strategy sequentially to historical candles;
* simulate entries and exits;
* apply fees and slippage assumptions;
* calculate position results;
* produce a list of trades;
* calculate performance metrics.

Backtest must use the same strategy rules that will later be used in demo and live trading.

### 6.5 Decision Layer

Responsible for approved production state.

Responsibilities:

* identify the active strategy;
* identify the active parameter configuration;
* store strategy status;
* determine whether trading is allowed;
* distinguish active configurations from research candidates.

Possible statuses may include:

```text
research
candidate
active_demo
active_live
paused
rejected
archived
```

The first version may use fewer statuses.

The Decision Layer must not replace an active configuration merely because another configuration recently performed better.

### 6.6 Trading Layer

Responsible for demo and live execution.

Responsibilities:

* react to a new closed candle;
* use the active approved strategy;
* check whether trading is allowed;
* calculate risk and position size;
* submit orders;
* check order results;
* record trades and errors.

Demo trading must be implemented before live trading.

### 6.7 Monitoring Layer

Responsible for system health.

Responsibilities may include:

* API connectivity;
* arrival of new candles;
* missing data;
* failed orders;
* open positions;
* current drawdown;
* strategy health;
* system errors.

Telegram or other notifications may be added later, but they are not part of the initial foundation.

---

## 7. Research and trading separation

Research and trading are separate processes.

The trading process uses a fixed approved configuration.

The research process may:

* test other parameters;
* test other strategies;
* analyze recent degradation;
* create challenger configurations.

Research must not directly alter the currently active strategy.

The lifecycle is:

```text
Active configuration
        ↓
Research produces candidate
        ↓
Historical validation
        ↓
Out-of-sample validation
        ↓
Demo validation
        ↓
Manual or explicitly controlled approval
        ↓
Candidate becomes active
```

Changing only parameters of the same strategy is still a strategy configuration change and must be validated.

---

## 8. Strategy switching

The long-term system may support different strategies for different market regimes or trading sessions.

For example:

```text
Strong trend → Trend Pullback
Sideways market → No trading
High-volatility breakout → Breakout strategy
```

However, the first version must not automatically switch among many strategies.

Initial behavior:

```text
UPTREND → consider Long Trend Pullback
DOWNTREND → consider Short Trend Pullback
SIDEWAYS → no trade
```

Strategy selection based on time of day, market regime, or volatility may be researched later.

Such selection must be supported by historical evidence and validation. It must not be added only to keep the system trading continuously.

The system is allowed to remain out of the market.

Continuous operation does not mean continuous trading.

---

## 9. Research schedule

Research does not need to run continuously in the background.

It may run:

* manually;
* weekly;
* monthly;
* after enough new trades;
* after a strategy health warning;
* when investigating a specific hypothesis.

Trading should remain lightweight and stable.

Heavy parameter searches should run separately from live execution and should not interfere with receiving candles or managing positions.

---

## 10. Hardware constraints

The current laptop is sufficient for the intended first version.

Reasonable workloads include:

* storing several years of 15-minute and 1-hour ETHUSDT candles;
* pandas calculations;
* SQLite queries;
* backtesting one strategy;
* testing a moderate number of parameter combinations;
* running a lightweight demo or live process.

The project must avoid designs that assume:

* massive parallel optimization;
* tick-level datasets;
* thousands of symbols;
* continuous machine learning;
* large in-memory datasets without need;
* heavy research running at the same priority as live trading.

If research becomes slow, first simplify the experiment:

* reduce parameter combinations;
* narrow the hypothesis;
* cache reusable calculations;
* run research outside trading hours;
* profile the actual bottleneck.

Do not add distributed or cloud architecture without evidence that local execution is insufficient.

---

## 11. Data principles

Raw market candles are the main source data.

Permanent storage should contain data that is difficult or important to reproduce:

* market candles;
* approved strategy configurations;
* important backtest results;
* demo trades;
* live trades;
* system decisions;
* relevant errors and health records.

Temporary calculations should normally remain in memory:

* EMA columns;
* ATR columns;
* temporary DataFrames;
* intermediate optimization values;
* debug output.

Indicators should not be permanently stored for every possible parameter combination.

Time should be stored consistently in UTC.

Trading decisions must use only information available at that moment.

Only closed candles should be used for initial strategy decisions.

---

## 12. Database principles

SQLite is the initial database.

The database schema should be designed incrementally.

Do not create all possible future tables at the beginning.

The first schema should support the current phase.

Tables should be added when the corresponding module is implemented.

The first likely table is:

```text
market_candles
```

Future tables may include:

```text
strategies
strategy_configs
backtest_runs
backtest_metrics
backtest_trades
demo_trades
live_trades
strategy_health
```

These names are planning references, not a requirement to create all tables immediately.

---

## 13. Validation philosophy

Historical data is separated by purpose.

Example:

```text
2023–2024 → development and research
2025 → validation
2026 → out-of-sample evaluation
```

Exact date boundaries may be adjusted later.

A validation period must not be repeatedly used to tune parameters while still being described as independent validation.

The system should prefer:

* stable parameter regions;
* reasonable trade counts;
* acceptable drawdown;
* performance after fees;
* consistency across periods.

It should not select a configuration only because it has the highest historical profit.

---

## 14. Initial implementation direction

Development starts with the foundation:

```text
1. Verify Bybit public API connectivity.
2. Inspect a real candle response.
3. Decide which fields are needed.
4. Design the initial SQLite candle table.
5. Save a small real sample.
6. Read the saved sample.
7. Add historical range downloading.
8. Add incremental candle updates.
```

Only after the Data Layer is usable should development proceed to:

```text
market regime
strategy
backtest
parameter research
demo trading
monitoring
```

---

## 15. Agent working rules

Before writing code, the agent should:

1. Read this file.
2. Read the current roadmap.
3. Identify the active phase and task.
4. Inspect existing code before creating new abstractions.
5. Explain any architectural change.
6. Implement only the current agreed scope.
7. Run relevant checks.
8. Update the roadmap after completing work.
9. Record important decisions that affect future tasks.

The agent must not:

* implement future layers without request;
* silently redesign the project;
* duplicate existing logic;
* create abstractions only for architectural appearance;
* introduce major dependencies without explanation;
* automatically change approved trading behavior;
* claim completion if verification has not been performed.

---

## 16. Definition of success

The first successful version is not a perfectly autonomous trading system.

The initial success criteria are:

* reliable collection of ETHUSDT candles;
* reproducible historical analysis;
* understandable market-regime classification;
* one transparent strategy;
* a backtest with realistic fees and risk;
* documented experiment results;
* a validated candidate;
* stable demo trading;
* clear separation between research and execution.

Live trading is a later milestone, not the starting point.
