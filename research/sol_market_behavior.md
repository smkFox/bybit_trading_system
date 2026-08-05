# SOLUSDT 15m Market-Behavior Analysis

## Decision

The tested price, volume, volatility, session, and candle-streak effects do not
form a standalone strategy. None remained profitable after the conservative
`0.220%` round-trip cost in both 2023 and 2024.

One effect was sufficiently coherent to define a follow-up hypothesis:
**a trend-aligned entry after a low-volume counter-trend impulse**. The fixed
follow-up analysis subsequently rejected it; see
`research/sol_trend_pullback_analysis.md`.

Trailing stop is not included in that initial hypothesis. The three tested
versions all lost money.

## Data and method

* Instrument: Bybit `SOLUSDT` USDT perpetual.
* Source: 73,152 consecutive closed 15-minute candles from 2022-12-01 through
  2024-12-31; December 2022 is warm-up.
* Discovery year: 2023.
* Unchanged confirmation of each selected horizon: 2024.
* Entry: next 15-minute candle open after a closed signal candle.
* Holding horizons checked: 15m, 30m, 1h, 2h, 4h, and 8h.
* Cost: `0.220%` per round trip, representing taker fees and adverse slippage.
* Nearby events were separated by an eight-hour cooldown.
* Each effect was compared with random timestamps matched by year, UTC session,
  and rolling volatility regime while preserving the signal's trade direction.
* A result also had to remain positive after removing its best 1% of outcomes.

The tested event families were candle bodies of `0.5`, `1`, `1.5`, and `2 ATR`;
volume buckets; causal rolling volatility regimes; UTC sessions; and runs of
two, three, or four same-direction candles. Both continuation and reversal were
checked.

## Market observations

| Observation | 2023 | 2024 |
|---|---:|---:|
| Closed 15m candles | 35,040 | 35,136 |
| Buy-and-hold price change | +921.91% | +85.81% |
| Median ATR14 as percentage of price | 0.6225% | 0.6370% |
| Median absolute candle body | 0.2264% | 0.2482% |

These are two strongly bullish years. They can reveal a possible Long pullback
effect, but they cannot demonstrate that the corresponding Short logic works in
a bearish market.

## Broad result

No event/style pair passed the basic research gate. The closest complete
Long-and-Short result was reversal after a candle body of at least `1 ATR` whose
volume was below the preceding 20-candle median. Its best 2023 holding horizon
was four hours and was then used unchanged in 2024.

| Year | Events | Mean net return/trade | Mean without best 1% | Edge vs matched random |
|---|---:|---:|---:|---:|
| 2023 | 160 | -0.1001% | -0.1659% | +0.1635% |
| 2024 | 205 | -0.0092% | -0.1094% | +0.2618% |

The positive relative edge is not enough: after costs, the complete rule still
loses money.

Splitting this exploratory result by trade direction explains why it was close:

| Year | Direction | Events | Mean net return/trade | Mean without best 1% | Profit factor |
|---|---|---:|---:|---:|---:|
| 2023 | Long after a down impulse | 69 | +0.1074% | +0.0512% | 1.2278 |
| 2023 | Short after an up impulse | 91 | -0.2574% | -0.3212% | 0.6239 |
| 2024 | Long after a down impulse | 98 | +0.2454% | +0.1668% | 1.4602 |
| 2024 | Short after an up impulse | 107 | -0.2425% | -0.3387% | 0.7075 |

This is evidence for buying a quiet pullback while the market is rising, not
evidence that every sharp move reverses. Because this directional split was
examined after the broad result and both years were bullish, it is hypothesis
generation rather than validation.

## Trailing-stop diagnostic

For the closest broad effect, a causal trailing exit was checked with an initial
stop of `1`, `1.5`, or `2 ATR`, activation after `+1R`, and an eight-hour maximum
holding time. The trail calculated from a candle became active only on the next
candle, avoiding unknowable intrabar ordering.

| Trail distance | 2023 mean | 2023 PF | 2024 mean | 2024 PF |
|---|---:|---:|---:|---:|
| 1 ATR | -0.2755% | 0.4474 | -0.1736% | 0.6426 |
| 1.5 ATR | -0.2693% | 0.5483 | -0.0447% | 0.9245 |
| 2 ATR | -0.3200% | 0.5737 | -0.1085% | 0.8527 |

All variants lost in both years. Fifteen-minute noise removes trades before the
occasional large move compensates for stops and costs. Trailing remains a
possible future exit tool, but this analysis gives no reason to make it part of
candidate v1.

## Possible candidate principles

The follow-up hypothesis was **Trend-Aligned Low-Volume Pullback**:

1. Classify the higher-timeframe trend using only fully closed 1h data.
2. In an uptrend, allow only Long entries; in a downtrend, allow only Short
   entries; in a sideways state, do not enter.
3. On 15m, wait for a closed counter-trend impulse whose body is large relative
   to current ATR but whose volume is weak relative to recent 15m volume.
4. Enter on the next 15m candle, so the signal uses no future information.
5. Place an exchange-side ATR-based protective stop with the entry order.
6. Start with a simple rule-based or time-based exit. Do not add trailing unless
   a later, separately defined exit comparison supports it.
7. Apply the confirmed `50 USDT / 5% risk / 3x` configuration only to position
   sizing. Capital, risk, and leverage do not create the statistical edge.

The follow-up fixed EMA50/EMA200 trend, retained the impulse, volume, and
four-hour exit rules, and checked one non-rising-OI filter. It lost in 2023,
Shorts lost in both years, and OI did not produce a robust improvement. It is
not a candidate for a full backtest; 2025 remains unopened for this rule.
