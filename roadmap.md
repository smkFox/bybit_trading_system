# Project Roadmap

## Status notation

* `[x]` complete;
* `[~]` current;
* `[ ]` not started or blocked by an earlier phase.

# Current state

## Current phase

Strategy selection. The reusable data and backtest foundation is ready, but no
tested strategy is approved for demo or live trading.

## Current objective

Select a materially different, explicit strategy hypothesis. Do not tune the
rejected BTC/ETH shock candidate from its known 2023–2024 losses, and do not
open 2025–2026 for that candidate.

## Immediate path

* [x] Build and verify the market-data foundation.
* [x] Build reusable strategy models, indicators, and a backtest engine.
* [x] Reject EMA Trend Pullback after its development test.
* [x] Reject the Donchian family after development, validation, and fixed
  follow-up experiments.
* [x] Implement BTC-confirmed ETH Shock Mean Reversion v1 with fixed rules.
* [x] Test it on 2023–2024 only and reject it at the development gate.
* [~] Discuss and define a different hypothesis before writing more strategy
  code or loading additional validation data.
* [ ] Freeze a candidate only after it passes its development gate.
* [ ] Validate the frozen candidate on untouched data.
* [ ] Run controlled Bybit demo trading.
* [ ] Add operational safety and Telegram reporting.
* [ ] Make a separate manual decision about small live trading.

## Current constraints

* Trade only Bybit USDT perpetual futures in the initial cycle.
* Use `ETHUSDT` as the traded instrument unless a new hypothesis explicitly
  changes the scope.
* BTC may be used only as an explicitly specified context input.
* Use closed candles and causal calculations with no future data.
* Include fees, slippage, funding, exchange constraints, and rejected orders.
* Use 3x as baseline leverage. Any use of 5x requires a separate decision.
* Evaluate the complete signal flow, not only trades affordable by a 10 USDT
  account.
* Keep research separate from demo and live order placement.
* Do not imply guaranteed daily or monthly profit.

# Phase 0 — Environment and project setup

* [x] Create the project and local Python environment.
* [x] Configure Git and source exclusions.
* [x] Add dependency and environment checks.
* [x] Add context, roadmap, and README files.
* [x] Establish the simple local project structure.

# Phase 1 — Market-data foundation

* [x] Add the public Bybit linear-candle client.
* [x] Normalize timestamps to UTC and retain only closed candles.
* [x] Validate OHLC values, intervals, ordering, gaps, and duplicates.
* [x] Add SQLite storage keyed by `symbol + timeframe + open_time`.
* [x] Make historical downloads restartable and idempotent.
* [x] Add incremental closed-candle updates.
* [x] Add a pandas data-access boundary independent of API details.
* [x] Load ETHUSDT 15m and 1h history required by completed research.
* [x] Load BTCUSDT 1h only through 2024 for the latest development test.

# Phase 2 — Strategy development

## Shared foundation

* [x] Keep shared decisions and position state in `strategies/models.py`.
* [x] Keep reusable Wilder ATR in `strategies/indicators.py`.
* [x] Make `backtest/engine.py` accept a strategy evaluator.
* [x] Support next-candle execution, protective stops, strategy exits,
  optional take profit, maximum holding time, costs, and exchange constraints.
* [x] Check determinism, input immutability, and no look-ahead behavior.

## Development gate for a candidate

A candidate must define its rules and parameters before the run. Its primary
test is the complete signal-quality flow with order-size limits neutralized;
the 10 USDT run separately shows immediate executability.

Unless a hypothesis justifies different limits before testing, require:

* positive net PnL in both development years;
* combined profit factor of at least 1.2;
* maximum closed-equity drawdown of at most 20%;
* at least 30 total trades and 10 in each year;
* no materially unsupported trade direction;
* clean time boundaries and no forced end-of-data result distortion.

Failure means rejection. Do not inspect later periods merely to find a better
story, and do not change parameters after the result without defining a new,
independently justified experiment.

## Rejected strategy record

### EMA Trend Pullback v1

* [x] Tested 27 predefined variants on 2023–2024.
* [x] Rejected because complete signal flow remained unprofitable and the
  small-account result was caused by ignoring unaffordable signals.
* [x] Removed strategy-specific files from the active tree.

### Donchian Breakout family

* [x] Developed and compared fixed channel/ATR variants on 2023–2024.
* [x] Froze `40/20`, `1.5 ATR`, Long-only before opening 2025.
* [x] Recorded positive but sparse 2025 validation with 19 trades.
* [x] Rejected the unchanged version after a negative 2026 out-of-sample run.
* [x] Tested one fixed EMA50/EMA200 regime variant without a sweep; it improved
  viewed 2026 but degraded earlier periods and was not robust.
* [x] Tested one fixed 15m/1h version; complete flow lost in every period.
* [x] Stopped further Donchian fitting and removed active files.

The complete pre-removal implementation and reports remain recoverable at Git
commit `2e7c03d`.

### BTC-confirmed ETH Shock Mean Reversion v1

* [x] Freeze ETH 15m entries, BTC/ETH 1h relationship, rolling beta/Z windows
  of 168 hours, `|Z| >= 2.5` shock, four-candle confirmation, ATR14 `1.5` stop,
  normalization boundary `0.5`, and 8-hour maximum holding time.
* [x] Prove causal hourly relationship calculations and exact 15m alignment.
* [x] Run only 2023–2024 before opening validation periods.
* [x] Record 284 signal-quality trades, `-36.136766%` return, `0.312324` profit
  factor, and `36.225080%` maximum drawdown.
* [x] Record losses in 2023, 2024, Long trades, and Short trades.
* [x] Reject and stop. Do not test this version on 2025–2026.

The fixed specification and exact result remain in the active tree only for
reproducibility while the next hypothesis is selected.

# Phase 3 — Frozen validation

Blocked until a new candidate passes development.

* [ ] Freeze strategy code, parameters, data boundaries, and acceptance rules.
* [ ] Run once on untouched validation data.
* [ ] Reject without tuning if the predeclared gate fails.
* [ ] Open the final out-of-sample period only when validation permits it.

# Phase 4 — Bybit demo trading

Blocked until one frozen strategy passes validation.

* [ ] Configure credentials outside source control.
* [ ] Synchronize closed candles and exchange state at startup.
* [ ] Generate one deterministic decision per new closed decision candle.
* [ ] Size, round, submit, and track orders and exchange-side protective stops.
* [ ] Persist decisions, orders, fills, positions, and errors.
* [ ] Reconcile state after restarts and prevent duplicate orders.
* [ ] Add pause and emergency-stop behavior.

# Phase 5 — Telegram monitoring

* [ ] Report startup, shutdown, pause, stale data, and critical errors.
* [ ] Report order and position lifecycle events.
* [ ] Show trade count, open exposure, realized/unrealized PnL, fees, and
  current equity as a read-only text dashboard.
* [ ] Ensure notification failures never authorize trading.

# Phase 6 — Small controlled live trading

Requires a separate manual decision after successful demo evidence. Capital,
risk, loss limits, withdrawal expectations, and emergency procedures must be
agreed explicitly before any live order is possible.

# Deferred scope

* automatic strategy selection;
* automatic parameter adaptation;
* multiple traded instruments;
* 5x leverage;
* Telegram commands that change trading state;
* cloud deployment and high availability;
* income withdrawals.

# Decision log

* [x] Keep the system local, transparent, and reproducible.
* [x] Use real stored data and realistic execution assumptions.
* [x] Keep one implementation for backtest, demo, and eventual live use.
* [x] Keep validation periods unseen until a candidate passes development.
* [x] Remove rejected implementations from active development while retaining
  reproducible evidence and Git history.
* [x] Treat both Long and Short behavior as evidence, not assume one direction
  is profitable because the overall result happens to be positive.
* [x] Stop the BTC/ETH shock candidate immediately after its broad 2023–2024
  gate failure; do not load or test its 2025–2026 context data.

# Work log

## 2026-07-31

* [x] Removed the rejected Donchian implementation and reports after checkpoint
  commit `2e7c03d`.
* [x] Added only the BTCUSDT 1h development data needed through 2024.
* [x] Implemented and checked BTC-confirmed ETH Shock Mean Reversion v1.
* [x] Ran the fixed 2023–2024 development test.
* [x] Rejected the candidate because both years and both directions lost money,
  with profit factor far below 1 and drawdown above the gate.
* [x] Stopped before any 2025–2026 test or parameter adjustment.

## Next task

* [~] Agree on a materially different strategy hypothesis and its development
  rules before implementation.
