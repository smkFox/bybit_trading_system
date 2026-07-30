# EMA Trend Pullback v1

## 1. Document status

| Field | Value |
|---|---|
| Strategy | EMA Trend Pullback |
| Version | `1.0.0` |
| Status | Specification frozen for initial implementation |
| Market | Bybit linear USDT perpetual |
| Symbol | `ETHUSDT` |
| Trend timeframe | `1h` |
| Signal timeframe | `15m` |
| Development data | 2023-01-01 through 2024-12-31 |

This document defines the initial baseline hypothesis. The parameters are
conventional starting values, not validated optimal values and not a promise of
profitability.

The strategy implementation, backtest, demo, and live trading must use the same
rules. Any material rule change creates a new strategy version and requires a
new validation cycle.

## 2. Strategy idea

The strategy trades in the direction of a trend identified on closed 1h
candles. It waits for price on the 15m timeframe to pull back to its EMA 20 and
then requires a closed confirmation candle before producing an entry intent.

The strategy may remain out of the market. Trade frequency must not be forced.

## 3. Time and candle conventions

* All timestamps use UTC.
* A candle is identified by its inclusive `open_time`.
* A candle closes at `open_time + timeframe duration`.
* Only fully closed candles may be used.
* A 15m decision is made immediately after its confirmation candle closes.
* At that decision time, the latest 1h candle whose close time is less than or
  equal to the decision time is available.
* An approved entry intent is executed as soon as practical after the signal
  closes, during the newly forming 15m candle.
* The incomplete candle is never used to create the signal.
* Backtest models the fill as the next 15m candle open plus configured
  slippage.
* Demo and live use the actual Bybit market fill after the decision.
* If no next candle exists in historical data, no backtest fill may be assumed.

## 4. Indicator definitions

### 4.1 Exponential moving average

EMA uses the candle close and the recursive definition:

```text
alpha = 2 / (period + 1)
EMA[t] = alpha * close[t] + (1 - alpha) * EMA[t - 1]
```

The implementation must be equivalent to pandas
`Series.ewm(span=period, adjust=False, min_periods=period).mean()`.
Values before `period` observations are unavailable.

Required EMAs:

| Timeframe | Period | Purpose |
|---|---:|---|
| 1h | 50 | Fast trend EMA |
| 1h | 200 | Slow trend EMA |
| 15m | 20 | Pullback EMA |

### 4.2 Average true range

ATR uses 15m candles and period 14.

```text
TR[t] = max(
    high[t] - low[t],
    abs(high[t] - close[t - 1]),
    abs(low[t] - close[t - 1])
)
```

For the first candle, where no previous close is available, true range is
`high - low`.

The first ATR is the arithmetic mean of the first 14 available true ranges.
Later values use Wilder smoothing:

```text
ATR[t] = ((ATR[t - 1] * 13) + TR[t]) / 14
```

ATR must be available on the closed confirmation candle. Otherwise no entry
intent is produced.

## 5. Trend permission on 1h

Trend permission is evaluated from the latest available fully closed 1h
candle.

### 5.1 Long permission

Long entries are permitted only when:

```text
EMA50 > EMA200
AND
close > EMA50
```

### 5.2 Short permission

Short entries are permitted only when:

```text
EMA50 < EMA200
AND
close < EMA50
```

### 5.3 No permission

No entry is permitted when:

* neither complete permission condition is true;
* either EMA is unavailable;
* any required value is missing or non-finite.

Equality does not grant permission.

## 6. Pullback and confirmation on 15m

Let:

* `P` be the closed 15m candle immediately before the confirmation candle;
* `C` be the closed 15m confirmation candle;
* `EMA20[P]` and `EMA20[C]` be the EMA values calculated on their respective
  candles.

No older candle may substitute for `P`. This keeps the first version
unambiguous and prevents an unlimited pending pullback state.

### 6.1 Long setup

The 1h long permission must be active at the close of `C`.

`P` is a valid long pullback candle when:

```text
P.open > EMA20[P]
AND
P.low <= EMA20[P]
AND
P.close >= EMA20[P]
```

`C` confirms the long setup when:

```text
C.close > P.high
AND
C.close > EMA20[C]
```

All conditions must be true to produce a long entry intent.

### 6.2 Short setup

The 1h short permission must be active at the close of `C`.

`P` is a valid short pullback candle when:

```text
P.open < EMA20[P]
AND
P.high >= EMA20[P]
AND
P.close <= EMA20[P]
```

`C` confirms the short setup when:

```text
C.close < P.low
AND
C.close < EMA20[C]
```

All conditions must be true to produce a short entry intent.

### 6.3 No-entry conditions

No entry intent is produced when any of the following is true:

* the required 1h permission is absent;
* the pullback condition is incomplete;
* the confirmation condition is incomplete;
* a required EMA or ATR value is unavailable during normal warm-up;
* either required candle is not fully closed;
* a position is already open.

Malformed candles, non-finite values after warm-up, and unsafe timeframe
alignment are input errors. They must stop decision processing rather than be
reported as an ordinary no-entry result.

## 7. Entry

* A valid setup produces an entry intent after `C` closes.
* The intended order type is a market order.
* The order is sent as soon as practical after the decision and all pre-trade
  checks complete.
* Backtest uses the next 15m open plus modeled slippage.
* Demo and live use the actual Bybit fill.
* The close of `C` must not be used as the fill price.
* An entry intent expires if execution is delayed beyond its immediately
  following 15m candle or if price moves beyond the approved execution limit.
* Position sizing, margin checks, exchange constraints, fees, and slippage are
  execution responsibilities defined in the backtest phase.

## 8. Initial protective levels

ATR is fixed from the closed confirmation candle `C`. The actual fill price
is used to calculate the levels.

### 8.1 Long

```text
risk_distance = 1.5 * ATR14[C]
stop_loss = fill_price - risk_distance
take_profit = fill_price + (2.0 * risk_distance)
```

### 8.2 Short

```text
risk_distance = 1.5 * ATR14[C]
stop_loss = fill_price + risk_distance
take_profit = fill_price - (2.0 * risk_distance)
```

The initial reward-to-risk target is therefore `2R`.

Provisional protection may be calculated from the current executable price
before order submission. The exact levels are finalized from the actual fill.
After that finalization, stop-loss and take-profit do not trail and are not
recalculated in version 1.

Price-tick rounding and behavior when both levels are reachable within one
candle belong to the shared execution model and will be frozen before the
backtest.

## 9. Position lifecycle

* At most one position may be open.
* Position scaling is disabled.
* New entry intents are ignored while a position is open.
* An opposite setup does not close or reverse an existing position.
* Normal exits are stop-loss, take-profit, and maximum holding time.
* Long and short management rules are symmetrical.

The entry candle is holding candle 1. After 32 complete 15m holding candles,
if neither stop-loss nor take-profit has closed the position, a time exit is
executed at the open of the following 15m candle.

```text
maximum complete holding candles = 32
maximum planned holding duration = 8 hours
time-exit fill reference = next 15m candle open
```

The time exit may realize either a profit or a loss. It is not a capital
guarantee.

## 10. Baseline configuration

```text
strategy_id: ema_trend_pullback
strategy_version: 1.0.0

trend_timeframe: 1h
signal_timeframe: 15m

trend_fast_ema_period: 50
trend_slow_ema_period: 200
pullback_ema_period: 20

atr_period: 14
stop_atr_multiplier: 1.5
take_profit_r_multiple: 2.0
maximum_holding_candles: 32

entry_timing: immediately_after_signal_close
backtest_fill_reference: next_15m_open_plus_slippage
demo_live_fill_reference: actual_bybit_fill
maximum_open_positions: 1
position_scaling: false
opposite_signal_reversal: false
long_short_rules: symmetrical
```

## 11. Trading decision model

The strategy returns exactly one decision after every fully closed 15m signal
candle.

### 11.1 Actions and direction

Supported actions:

```text
NO_ACTION
OPEN_POSITION
HOLD_POSITION
CLOSE_POSITION
```

Direction is represented separately:

```text
LONG
SHORT
null
```

Action semantics:

* `NO_ACTION`: no position exists and no valid entry is available;
* `OPEN_POSITION`: a complete long or short setup is confirmed;
* `HOLD_POSITION`: an existing position remains within its holding period;
* `CLOSE_POSITION`: the maximum holding period requires a time exit.

Price-based stop-loss and take-profit fills are execution events, not new
strategy decisions.

### 11.2 Decision fields

```text
decision_id
strategy_id
strategy_version

symbol
signal_timeframe
signal_candle_open_time
decision_time
execute_at

action
side
reason

entry_timing
stop_distance
take_profit_r_multiple

supporting_values
```

`decision_id` must be deterministically derived from:

```text
strategy_id
strategy_version
symbol
signal_timeframe
signal_candle_open_time
action
```

Recalculating the same candle and state must produce the same decision ID.

`execute_at` identifies the start of the newly forming 15m candle. It is an
execution target time, not a guaranteed fill price.

For `OPEN_POSITION`, `stop_distance` is `1.5 * ATR14[C]` and
`take_profit_r_multiple` is `2.0`. Absolute protective prices are not part
of the decision because they depend on the actual fill.

### 11.3 Decision reasons

```text
INSUFFICIENT_HISTORY
TREND_NOT_PERMITTED
PULLBACK_NOT_FOUND
CONFIRMATION_NOT_FOUND
LONG_SETUP_CONFIRMED
SHORT_SETUP_CONFIRMED
POSITION_ACTIVE
MAX_HOLDING_TIME
```

Evaluation order is fixed:

1. Validate market data and position state.
2. If a position has completed 32 holding candles, return
   `CLOSE_POSITION / MAX_HOLDING_TIME`.
3. If a position remains open, return
   `HOLD_POSITION / POSITION_ACTIVE`.
4. Check indicator warm-up.
5. Check 1h trend permission.
6. Check the immediately preceding 15m pullback candle.
7. Check the closed 15m confirmation candle.
8. Return the appropriate open or no-action decision.

Invalid input is an error and does not produce a normal trading decision.

### 11.4 Supporting values

When available and applicable, `supporting_values` contains:

```text
trend_candle_open_time
trend_close
trend_ema50
trend_ema200

pullback_candle_open_time
pullback_open
pullback_high
pullback_low
pullback_close
pullback_ema20

confirmation_candle_open_time
confirmation_close
confirmation_ema20
confirmation_atr14

position_holding_candles
```

The values explain the decision. They do not contain account sizing or Bybit
order state.

## 12. Pre-trade plan and execution boundary

`OPEN_POSITION` is an intent, not permission to submit an order immediately.
Before submission, Risk and Execution must build and approve one complete
pre-trade plan containing:

```text
expected executable price
maximum allowed account loss
position quantity and notional
baseline leverage and required margin
provisional stop-loss and take-profit
estimated fees, funding, and slippage
Bybit quantity and price rounding
instrument-limit checks
maximum acceptable entry delay and price deviation
```

The order is not submitted if any check fails. Execution rejection is stored
separately from the strategy decision, with a reason such as:

```text
INSUFFICIENT_MARGIN
BELOW_MINIMUM_NOTIONAL
INVALID_QUANTITY
RISK_LIMIT_EXCEEDED
PRICE_MOVED_TOO_FAR
LIQUIDATION_TOO_CLOSE
```

For an approved plan:

1. Submit the entry with provisional protection when supported.
2. Confirm the actual Bybit fill.
3. Finalize protective prices from the actual average fill.
4. Set or update full-position protection on Bybit.
5. Verify the position and protective orders.
6. If protection cannot be established, close the position safely and stop
   further trading.

Leverage, position size, margin, fees, funding, liquidation checks, exchange
rounding, and API order parameters are not strategy-decision fields.

## 13. Responsibilities deferred to later phases

The following are intentionally defined in later phases:

* account risk per trade;
* position sizing;
* leverage and margin rules;
* Bybit minimum quantity, notional, quantity step, and price tick;
* fee, funding, and slippage models;
* same-candle stop-loss/take-profit collision handling;
* order submission and reconciliation;
* Telegram reporting;
* parameter comparison and candidate promotion.

## 14. Development and change policy

* The baseline must be implemented and tested before parameters are adjusted.
* Strategy changes may use only 2023–2024 development data.
* 2025 validation and 2026 out-of-sample data must not be inspected while
  changing this version.
* A later parameter search must be limited and explainable.
* Selection must consider drawdown, expectancy, trade count, costs,
  subperiod stability, and neighboring parameter stability, not maximum profit
  alone.
* Research may create a candidate configuration but may not modify an active
  demo or live configuration automatically.
