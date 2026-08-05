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

Select a new, independently justified SOLUSDT market hypothesis. The classical
Volume Profile interpretation also failed in both years and directions; do not
tune it and do not open 2025–2026 for it.

## Immediate path

* [x] Build and verify the market-data foundation.
* [x] Build reusable strategy models, indicators, and a backtest engine.
* [x] Reject EMA Trend Pullback after its development test.
* [x] Reject the Donchian family after development, validation, and fixed
  follow-up experiments.
* [x] Implement BTC-confirmed ETH Shock Mean Reversion v1 with fixed rules.
* [x] Test it on 2023–2024 only and reject it at the development gate.
* [x] Implement Volatility Squeeze Breakout v1 with volume, OI, and funding.
* [x] Test it on 2023–2024 only and reject it at the development gate.
* [x] Compare ETHUSDT and SOLUSDT execution feasibility without testing a
  strategy.
* [x] Confirm `SOLUSDT / 50 USDT / 5% / 3x` as the research configuration.
* [x] Analyze SOL 15m behavior and reject unconditional continuation, reversal,
  and trailing-stop rules as standalone strategies.
* [x] Test fixed Trend-Aligned Low-Volume Pullback and one non-rising-OI filter.
* [x] Reject both after the base rule lost in 2023, Shorts lost in both years,
  and the OI result was sparse and unstable.
* [x] Test and reject a fixed classical Volume Profile/Tape Speed interpretation
  inspired by a SOL-specific preprint.
* [~] Define a different SOLUSDT hypothesis without reusing the rejected entry.
* [ ] Freeze a candidate only after it passes its development gate.
* [ ] Validate the frozen candidate on untouched data.
* [ ] Run controlled Bybit demo trading.
* [ ] Add operational safety and Telegram reporting.
* [ ] Make a separate manual decision about small live trading.

## Current constraints

* Trade only Bybit USDT perpetual futures in the initial cycle.
* Use `SOLUSDT` as the traded instrument for the current research cycle.
* Other stored symbols may be used only by an explicitly specified hypothesis.
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
* [x] Add separate Open Interest and Funding Rate tables and public download.
* [x] Load ETHUSDT OI and funding only through 2024 for development.
* [x] Load complete SOLUSDT 15m candles for 2023–2024 plus minimal warm-up.
* [x] Load matching SOLUSDT 15m OI and settled funding only through 2024.
* [x] Load consecutive SOLUSDT 5m candles for 2023–2024 plus one prior day.

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

The complete implementation and report are recoverable at Git commit
`a7bb35f` after removal from the active tree.

### Volatility Squeeze Breakout v1

* [x] Freeze 1h ATR compression, a four-hour range, 15m price/volume entry,
  rising 15m Open Interest, causal Funding Rate guard, `1.5 ATR` stop, `2R`
  target, and 8-hour maximum holding time.
* [x] Store OI and funding separately from candles and join only published
  values in memory.
* [x] Preserve two isolated missing OI observations as gaps instead of filling
  them; block OI confirmation until exact comparison timestamps exist.
* [x] Run only 2023–2024 with no parameter changes.
* [x] Record 496 signal-quality trades, `-86.210432%` return, `0.394133` profit
  factor, and `86.620565%` maximum drawdown.
* [x] Record losses in 2023, 2024, Long trades, and Short trades.
* [x] Reject and stop without testing 2025–2026.

The fixed specification and exact result remain in the active tree only for
reproducibility while the next hypothesis is selected.

### Classical Volume Profile Mean Reversion

* [x] Record that the motivating July 2026 SSRN preprint exposed only its
  abstract, not enough detail for an exact replication.
* [x] Freeze a transparent 100-bin, 70% prior-day profile, VAH/VAL rejection,
  signed volume-weighted-return confirmation, causal developing POC target,
  and UTC-day exit.
* [x] Test only the source-motivated 1% and 2% stops on Bybit 2023–2024.
* [x] Reject because both years and both directions lost even at the source's
  lower 0.14% cost estimate; profit factors remained below 0.82.
* [x] Stop without tuning or opening 2025–2026.

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
* [x] Stop Volatility Squeeze Breakout immediately after its broad 2023–2024
  gate failure; do not tune it or test it on 2025–2026.

# Work log

## 2026-08-05

* [x] Compared ETHUSDT and SOLUSDT using identical 2023–2024 candles, current
  Bybit minimums, 3x leverage, and a conservative 0.220% cost reserve.
* [x] Recorded that `10 USDT / 5%` makes ETH highly price- and stop-dependent,
  while SOL remains executable for materially wider stops.
* [x] Recorded that 50 USDT at 5% risk makes every tested 0.5%–5% stop
  executable for both instruments over the historical price range.
* [x] Proposed SOLUSDT with 50 USDT, 5% risk, and 3x leverage; no strategy was
  selected or tested.
* [x] Confirmed the proposed instrument and account configuration.
* [x] Analyzed 2023–2024 SOL 15m impulses, volume, volatility regimes, sessions,
  streaks, continuation, reversal, and causal trailing exits.
* [x] Found no profitable standalone effect after costs; identified only a new
  development hypothesis: enter a low-volume pullback in the direction of a
  separately established higher-timeframe trend.
* [x] Loaded exact SOLUSDT 15m OI and settled funding only through 2024.
* [x] Tested the hypothesis with fixed causal 1h EMA50/EMA200 regimes and a
  four-hour exit; 2023 lost and Short trades lost in both years.
* [x] Tested one predeclared non-rising-OI filter; it lost in 2023, reduced the
  sample to 26 events per year, and remained negative after trimming outliers.
* [x] Kept funding diagnostic only because extreme groups contained 3–18
  events; rejected further fitting and left 2025–2026 unopened.
* [x] Added 5m candle support and loaded 210,816 consecutive SOLUSDT candles
  from 2022-12-31 through 2024-12-31.
* [x] Tested the fixed classical Volume Profile interpretation with 1% and 2%
  stops and both 0.14% and 0.22% cost assumptions.
* [x] Rejected it after mean and trimmed returns were negative in every year,
  direction, stop, and cost group; left later periods unopened.

## 2026-08-02

* [x] Preserved the rejected BTC/ETH Shock candidate at commit `a7bb35f` and
  removed its implementation from the active tree.
* [x] Added independent SQLite storage and public Bybit download for ETHUSDT
  15m Open Interest and settled Funding Rates.
* [x] Loaded only December 2022 warm-up and 2023–2024 development data.
* [x] Implemented and minimally checked fixed Volatility Squeeze Breakout v1.
* [x] Rejected it after both years and both directions lost money in the full
  signal flow, then stopped before 2025–2026.

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

* [~] Agree on a different market hypothesis before writing another strategy.
