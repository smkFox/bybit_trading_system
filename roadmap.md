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
Phase 3 — Validation and out-of-sample completed
```

## Current objective

Select a new strategy family after the controlled Donchian v1.1, v2, and v3
comparisons failed to produce robust multi-regime expectancy.

## Current active task

```text
Review the Donchian family rejection and choose the next hypothesis without
further channel, EMA, stop, or timeframe tuning.
```

## Immediate path

* [x] Build and verify the reusable market-data foundation.
* [x] Reject EMA Trend Pullback after its complete development test.
* [x] Separate shared strategy models and the backtest engine from a concrete
  strategy.
* [x] Implement and test Donchian Breakout v1.
* [x] Run its unchanged 2023–2024 baseline in diagnostic and 10 USDT modes.
* [x] Run the small, predefined development comparison.
* [x] Review its stable parameter region without selecting maximum return
  automatically.
* [x] Freeze `40/20`, `1.5 ATR`, Long-only as Donchian Breakout v1.1.
* [x] Run 2025 validation once after the freeze without tuning.
* [x] Run the frozen strategy unchanged on 2026 out-of-sample data.
* [x] Test one fixed EMA50/EMA200 Long/Short/Neutral regime without a sweep.
* [x] Reject that exact v2 as a robust replacement after direct comparison.
* [x] Test one fixed v3 with closed 1h regime and 15m signals.
* [x] Reject v3 after its complete Long and Short flows lost in every period.
* [x] Stop further Donchian parameter and timeframe adjustment.
* [-] Run this strategy in Bybit Demo Trading; v1.1 was not approved.
* [ ] Add operational safety and Telegram reporting.
* [ ] Make a separate manual decision about controlled live trading.

## Current constraints

* Exchange: Bybit.
* Market: USDT perpetual futures.
* Symbol: `ETHUSDT`.
* Stored source candles: `15m` and `1h`.
* Tested strategy candles: derived UTC `4h` and direct `15m` with closed `1h`
  regime.
* Development data: 2023-01-01 through 2024-12-31 only.
* The already viewed 2025 and 2026 periods cannot be reused as unseen
  validation for a new strategy.
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

Status: [x] Completed on 2026-07-30

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

* [x] Decide that the positive but concentrated baseline justifies one small
  predefined comparison.
* [x] Define alternatives before running them.
* [x] Keep the comparison limited to five channel pairs, three ATR stops, and
  Long/Short versus Long-only.
* [x] Compare combined results, both years, Long/Short, trade count, costs,
  drawdown, and neighboring-value stability.
* [x] Do not add filters merely to explain individual losing trades.
* [x] Run all 30 variants on 2023–2024 only and save the complete table.
* [x] Review the stable Long-only region around 40–55 entry, 20 exit, and
  1.5–2 ATR stop.
* [x] Freeze `40/20`, `1.5 ATR`, Long-only as version 1.1.0.
* [x] Do not inspect 2025 or 2026 before the freeze.

### Fixed comparison result

```text
variants tested:                     30
positive complete-flow variants:    30
positive in both 2023 and 2024:      11 (all Long-only)

40/20, 1.5 ATR, Long-only:
  diagnostic return:                +47.60%
  diagnostic profit factor:         2.420
  diagnostic maximum drawdown:      9.58%
  diagnostic trades:                40
  executable 10 USDT ending balance: 33.13 USDT
  executable return:                +231.34%
  executable profit factor:         2.443
  executable maximum drawdown:      31.07%

Neighboring Long-only variants:
  40/20, 2.0 ATR: diagnostic +31.03%, executable +205.73%
  55/20, 1.5 ATR: diagnostic +34.32%, executable +191.40%
  55/20, 2.0 ATR: diagnostic +27.62%, executable +214.32%
```

## Completion criteria

* [x] One reproducible Donchian configuration is frozen.
* [x] The decision is based on net expectancy, yearly and directional
  stability, drawdown, and executable feasibility.

---

# Phase 3 — Validation and out-of-sample

Status: [x] Completed on 2026-07-30

```text
Development:   2023-01-01 through 2024-12-31
Validation:    2025-01-01 through 2025-12-31
Out-of-sample: 2026-01-01 through the latest closed candle
```

* [x] Confirm that strategy code and parameters are frozen.
* [x] Run 2025 once and do not tune from its result.
* [x] Record positive net expectancy after modeled costs in both validation
  modes.
* [x] Record the limited sample of 19 trades as a remaining uncertainty.
* [x] Decide that the validation result permits the 2026 out-of-sample run.
* [x] Run the frozen strategy through the latest closed 2026 candle.
* [x] Do not tune from the 2026 result.
* [x] Reject Donchian Breakout v1.1 for demo in its current form.

### 2025 validation result

```text
Signal quality, 1% risk:
  return:             +14.51%
  trades:             19
  profit factor:      2.000
  maximum drawdown:   4.56%

Executable continuation, 5% risk and 3x:
  starting balance:   33.133903 USDT
  ending balance:     50.585451 USDT
  return:             +52.67%
  trades:             19
  rejected entries:   0
  profit factor:      1.807
  maximum drawdown:   15.74%
```

### 2026 out-of-sample result

```text
Signal quality, 1% risk:
  ending balance:      929.058015 USDT
  return:              -7.09%
  trades:              13
  profit factor:       0.288
  maximum drawdown:    8.85%

Executable continuation, 5% risk and 3x:
  starting balance:    50.585451 USDT
  ending balance:      37.235865 USDT
  return:              -26.39%
  trades:              13
  rejected entries:    0
  profit factor:       0.314
  maximum drawdown:    32.82%
```

The unchanged strategy failed the independent 2026 period in both modes and
is not approved for demo. No 2026-based parameter tuning is permitted.

## 3.1 Fixed EMA market-regime experiment

Status: [x] Completed on 2026-07-30

* [x] Keep Donchian `40/20`, ATR14, `1.5 ATR` stop, timeframe, exits, costs,
  risk, and leverage unchanged.
* [x] Define Bull as `EMA50 > EMA200` and close above EMA50.
* [x] Define Bear as `EMA50 < EMA200` and close below EMA50.
* [x] Block new entries in Neutral and leave open-position exits unchanged.
* [x] Allow Long only in Bull and Short only in Bear.
* [x] Add pre-2023 EMA200 warm-up without using it as a result period.
* [x] Compare v1.1 and v2 on identical candles and execution assumptions.
* [x] Run no EMA, channel, stop, or timeframe parameter sweep.

### Result

```text
Signal quality:
                  v1.1             v2
2023–2024:        +50.17%          +25.04%
2025:             +14.51%           +7.74%
2026 to Jul 30:    -7.09%           +2.66%

Continuous executable 10 USDT account:
v1.1: 10.000000 -> 33.518294 -> 50.969842 -> 37.119779 USDT
v2:   10.000000 -> 15.214207 -> 25.631526 -> 29.211220 USDT
```

The filter found the useful 2026 Short direction, but v2 Shorts lost money in
2023–2024 and 2025. The exact v2 reduced development profit factor, increased
drawdown and losing streak, and ended the continuous comparison below v1.1.
It is not approved as a robust replacement or for demo.

## 3.2 Fixed 15m / 1h timeframe experiment

Status: [x] Completed on 2026-07-30

* [x] Keep numeric EMA `50/200`, Donchian `40/20`, ATR14, and `1.5 ATR` stop.
* [x] Determine Bull, Bear, and Neutral from the latest fully closed 1h candle.
* [x] Generate Donchian decisions from fully closed 15m candles.
* [x] Prove that a 15m decision cannot see a still-open 1h candle.
* [x] Execute accepted decisions at the next 15m open.
* [x] Keep costs, risk, leverage, exits, and one-position rules unchanged.
* [x] Run one configuration without a timeframe or parameter sweep.

### Result

```text
Complete signal quality:
                    v1.1        v2          v3
2023–2024:          +50.17%     +25.04%     -90.70%
2025:               +14.51%      +7.74%     -29.98%
2026 to Jul 30:      -7.09%      +2.66%     -40.60%

v3 continuous executable account:
10.000000 -> 6.661137 -> 8.939352 -> 5.817767 USDT
```

Version 3 produced 691 development trades, a `0.528` profit factor, and a
`91.90%` quality-mode drawdown. Its Long and Short flows were negative in all
three periods. The apparent small-account profit in 2025 came from a
non-scalable subset after 735 rejected entries while the complete flow lost
29.98%.

Version 3 and the Donchian family are not approved for demo. Further parameter
or timeframe tuning is stopped under the agreed process.

---

# Phase 4 — Bybit Demo Trading

Status: [!] Blocked until a strategy passes out-of-sample testing

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
* [x] Do not approve a strategy for demo when its unchanged out-of-sample
  signal expectancy is negative.
* [x] Treat improvement in the already viewed 2026 period as insufficient when
  the same fixed change degrades development and 2025.
* [x] Stop a strategy family when its slower candidate fails out-of-sample, its
  regime variant is not robust, and its fixed faster variant loses across all
  tested periods.

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
* [x] Ran the agreed 30-variant Donchian comparison without changing fixed
  costs, timeframe, ATR period, or execution rules.
* [x] Recorded that all 30 complete flows were positive and that all 11
  variants positive in both years were Long-only.
* [x] Identified a neighboring stable region around 40–55 entry, 20 exit, and
  1.5–2 ATR stop without automatically freezing the highest-return row.
* [x] Froze `40/20`, `1.5 ATR`, Long-only as Donchian Breakout v1.1 before
  loading 2025.
* [x] Ran 2025 validation once with no parameter changes.
* [x] Recorded `+14.51%` signal-quality validation and executable capital
  growth from `33.133903` to `50.585451 USDT` across 19 trades.
* [x] Updated stored ETHUSDT 1h data through the candle closing at
  `2026-07-31 00:00 UTC` with no gaps introduced.
* [x] Ran frozen Donchian Breakout v1.1 unchanged on 2026 out-of-sample data.
* [x] Recorded `-7.09%` signal quality and executable capital decline from
  `50.585451` to `37.235865 USDT` across 13 trades.
* [x] Rejected Donchian Breakout v1.1 for demo without tuning it from the 2026
  result.
* [x] Added one fixed Donchian v2 EMA50/EMA200 market-regime filter and its
  warm-up, classification, entry-gating, and no-look-ahead checks.
* [x] Compared v1.1 and v2 without a parameter sweep on 2023–2024, 2025, and
  the already viewed part of 2026.
* [x] Recorded that v2 changed 2026 signal quality from `-7.09%` to `+2.66%`
  but reduced 2023–2024 from `+50.17%` to `+25.04%` and 2025 from `+14.51%`
  to `+7.74%`.
* [x] Did not approve the exact v2 as a robust replacement or for demo.
* [x] Implemented fixed v3 with closed 1h EMA regime and 15m Donchian signals.
* [x] Added exact hour-close alignment and multi-timeframe no-look-ahead checks.
* [x] Recorded v3 complete-flow returns of `-90.70%`, `-29.98%`, and `-40.60%`
  for 2023–2024, 2025, and the tested part of 2026.
* [x] Rejected v3 and stopped further Donchian tuning for the current project.

## 2026-07-27

* [x] Completed the market-data foundation and verified the stored ETHUSDT
  history.

## Next task

* [~] Select a different strategy family without further fitting Donchian to
  the already viewed historical periods.
