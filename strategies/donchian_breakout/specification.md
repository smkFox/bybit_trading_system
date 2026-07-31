# Donchian Breakout v1.1

## Status and scope

This document freezes the configuration selected on 2023–2024. The unchanged
configuration completed its 2025 validation with positive net expectancy and
then failed its 2026 out-of-sample run. It is not approved for demo or live
trading and does not claim future profitability.

```text
strategy_id:             donchian_breakout
strategy_version:        1.1.0
market:                  Bybit linear USDT perpetual
symbol:                  ETHUSDT
signal timeframe:        4h
development data:        2023-01-01 through 2024-12-31 UTC
validation data:         2025-01-01 through 2025-12-31 UTC
entry channel:           40 candles
exit channel:            20 candles
ATR:                     Wilder 14
initial stop:            1.5 ATR
fixed take profit:       none
maximum holding time:    none
simultaneous positions:  one
pyramiding:              disabled
direction:               Long only
```

## Candle and execution rules

Only fully closed UTC 4h candles are used. They are aggregated from four
consecutive stored 1h candles on boundaries 00:00, 04:00, 08:00, 12:00, 16:00,
and 20:00 UTC.

Every Donchian channel excludes the current signal candle. A decision made at
the close of a 4h candle is executed at the next 4h open in the backtest plus
configured adverse slippage. Demo and live will use the actual market fill.

## Entry

Long entry:

```text
closed candle close > highest high of the previous 40 closed candles
```

Short entries are disabled in the frozen configuration.

Equality is not a breakout. Missing warm-up values produce no action.

## Initial protection

ATR14 is fixed from the signal candle. The stop is finalized from the actual
entry fill:

```text
Long: stop = fill - 1.5 * ATR14
```

There is no fixed take profit and no pyramiding.

## Strategy exit

Long exit decision:

```text
closed candle close < lowest low of the previous 20 closed candles
```

The exit is executed at the next 4h open. The protective stop remains active
inside every candle.

## Development selection

The frozen configuration was selected from the predefined 30-variant
development comparison on 2023–2024. Its recorded results were:

```text
diagnostic return:           +47.603289%
diagnostic profit factor:    2.420269
diagnostic maximum drawdown: 9.577529%
executable 10 USDT return:   +231.339031%
ending executable balance:   33.133903 USDT
```

The v1.1 parameters, costs, and execution assumptions remain frozen. Neither
the 2025 nor 2026 result may be used to retune this version. The separate v2
EMA-regime experiment is recorded in `specification_v2.md`.
