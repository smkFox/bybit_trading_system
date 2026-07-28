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
* The entry intent is executable only at the open of the next 15m candle.
* If the next 15m candle is unavailable, no fill may be assumed.

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
* a required EMA or ATR value is unavailable or non-finite;
* either required candle is not fully closed;
* the 1h/15m alignment cannot be determined safely;
* a position is already open.

## 7. Entry

* A valid setup produces an entry intent after `C` closes.
* The intended order type is a market order.
* The modeled fill reference is the actual open of the next 15m candle.
* The close of `C` must not be used as the fill price.
* An entry intent expires if it cannot be executed for its immediately
  following 15m candle.
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

Stop-loss and take-profit do not trail and are not recalculated after entry in
version 1.

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

entry_timing: next_15m_open
maximum_open_positions: 1
position_scaling: false
opposite_signal_reversal: false
long_short_rules: symmetrical
```

## 11. Responsibilities outside this specification

The following are intentionally defined in later phases:

* the concrete trading-decision data model;
* account risk per trade;
* position sizing;
* leverage and margin rules;
* Bybit minimum quantity, notional, quantity step, and price tick;
* fee, funding, and slippage models;
* same-candle stop-loss/take-profit collision handling;
* order submission and reconciliation;
* Telegram reporting;
* parameter comparison and candidate promotion.

## 12. Development and change policy

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
