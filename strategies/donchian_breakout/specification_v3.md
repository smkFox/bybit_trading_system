# Donchian Breakout v3 — 15m signals with 1h regime

## Fixed experiment

Version 3 tests one faster multi-timeframe configuration without a parameter
sweep.

```text
trend timeframe:        closed 1h
trend EMA fast:         50
trend EMA slow:         200
signal timeframe:       closed 15m
entry channel:          previous 40 signal candles
exit channel:           previous 20 signal candles
ATR:                    Wilder 14 signal candles
initial stop:            1.5 ATR
fixed take profit:       none
```

Regime rules remain identical to v2:

```text
Bull:    EMA50 > EMA200 and 1h close > EMA50; allow Long only
Bear:    EMA50 < EMA200 and 1h close < EMA50; allow Short only
Neutral: block new entries
```

Each closed 15m candle receives only the latest fully closed 1h regime. The
hour ending at 11:00 can first be used by a decision made at 11:00 and never by
an earlier 15m candle. A valid Donchian decision is executed at the next 15m
open.

The regime filters only new entries. Existing positions retain the 20-candle
exit and protective stop. One-position, no-pyramiding, no-immediate-reversal,
cost, risk, and leverage assumptions are unchanged.

## Status

This exact version was tested once on 2023–2024, 2025, and the already viewed
part of 2026. Its complete signal flow was negative in every period and in
both directions. Version 3 is rejected and is not approved for demo.
