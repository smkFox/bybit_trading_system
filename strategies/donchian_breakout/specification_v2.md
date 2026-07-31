# Donchian Breakout v2 — EMA market regime experiment

## Fixed comparison scope

Version 2 changes only permission to open a new position. Donchian channels,
ATR protection, exits, execution, risk, and modeled costs remain unchanged.
No EMA variants are tested.

```text
strategy version:       2.0.0
signal timeframe:       closed 4h
entry channel:          previous 40 candles
exit channel:           previous 20 candles
ATR:                    Wilder 14
initial stop:           1.5 ATR
fixed take profit:      none
trend EMA fast:         50
trend EMA slow:         200
```

EMA uses `adjust=False` and produces no value before its complete-period
warm-up. All regime values come from the same fully closed 4h signal candle.

## Market regime

```text
Bull:
  EMA50 > EMA200 and close > EMA50
  only Long entries are allowed

Bear:
  EMA50 < EMA200 and close < EMA50
  only Short entries are allowed

Neutral:
  every other complete combination
  no new entries are allowed
```

Long and Short entries still require their corresponding 40-candle Donchian
breakout. A decision is executed at the next 4h open.

The regime does not close an existing position. Open positions retain the
original 20-candle channel exit and protective stop. One-position,
no-pyramiding, and no-immediate-reversal rules remain unchanged.

## Comparison status

This exact version was compared once with v1.1 on 2023–2024, 2025, and the
already viewed part of 2026. It improved 2026 but degraded 2023–2025 and is not
approved as a replacement for v1.1 or for demo trading.
