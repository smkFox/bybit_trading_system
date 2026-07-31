# Donchian Breakout v1

## Status and scope

This document freezes the first baseline hypothesis for historical testing. It
does not approve demo or live trading and does not claim profitability.

```text
strategy_id:             donchian_breakout
strategy_version:        1.0.0
market:                  Bybit linear USDT perpetual
symbol:                  ETHUSDT
signal timeframe:        4h
development data:        2023-01-01 through 2024-12-31 UTC
entry channel:           20 candles
exit channel:            10 candles
ATR:                     Wilder 14
initial stop:            2 ATR
fixed take profit:       none
maximum holding time:    none
simultaneous positions:  one
pyramiding:              disabled
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
closed candle close > highest high of the previous 20 closed candles
```

Short entry:

```text
closed candle close < lowest low of the previous 20 closed candles
```

Equality is not a breakout. Missing warm-up values produce no action.

## Initial protection

ATR14 is fixed from the signal candle. The stop is finalized from the actual
entry fill:

```text
Long:  stop = fill - 2 * ATR14
Short: stop = fill + 2 * ATR14
```

There is no fixed take profit and no pyramiding.

## Strategy exit

Long exit decision:

```text
closed candle close < lowest low of the previous 10 closed candles
```

Short exit decision:

```text
closed candle close > highest high of the previous 10 closed candles
```

The exit is executed at the next 4h open. The protective stop remains active
inside every candle. An opposite breakout does not reverse a position in the
same decision.

## Baseline evaluation

The unchanged baseline is tested twice on 2023–2024:

1. diagnostic signal quality: 1% risk with size and margin filters neutralized;
2. executable scenario: 10 USDT, 5% risk, 3x leverage, current ETHUSDT limits.

Both runs include taker fees, adverse slippage, and the conservative funding
assumption already used by the shared backtest engine. No 2025 or 2026 data may
be inspected before a configuration is frozen.
