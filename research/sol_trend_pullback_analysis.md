# SOL Trend-Aligned Low-Volume Pullback Analysis

## Decision

Reject this hypothesis. A fixed 1h trend filter did not turn the previously
observed low-volume reversal into a stable symmetric Long/Short effect. The one
predeclared Open Interest filter improved 2024 but failed in 2023 and left too
few observations. Funding produced only small, inconsistent diagnostic groups.

Do not optimize the exit and do not open 2025–2026 for this rule.

## Fixed experiment

* Instrument: Bybit `SOLUSDT` USDT perpetual.
* Data: 73,152 consecutive closed 15m candles and 73,152 exact 15m Open Interest
  observations from 2022-12-01 through 2024-12-31.
* Funding: 2,460 settled observations in the same stored period.
* Trend: fully closed 1h data; Up when `close > EMA50 > EMA200`, Down when
  `close < EMA50 < EMA200`, otherwise Sideways.
* Signal: a closed 15m counter-trend candle with body at least `1 ATR14` and
  volume below the median of the previous 20 closed 15m candles.
* Entry: next 15m Open.
* Exit: Close after four hours.
* Cost: `0.220%` per round trip.
* Event separation: eight hours, matching the preceding behavior analysis.
* Random control: same year, UTC session, rolling volatility regime, trend,
  and trade direction.
* OI variant: the exact OI observation for the signal interval must be no
  greater than the preceding exact 15m observation.
* Funding: diagnostic only; causal 10th and 90th percentiles of the preceding
  90 settled observations. It never filters an entry in this experiment.

The hourly state becomes available only when its hour has closed. An OI value
becomes available only after its 15m interval. Missing observations would block
the OI condition rather than being filled; this dataset has exact OI coverage.

## Trend coverage

The bullish annual return did not prevent the fixed rule from finding many
local downtrends:

| Year | Up | Down | Sideways |
|---|---:|---:|---:|
| 2023 | 38.98% | 28.33% | 32.68% |
| 2024 | 34.86% | 30.82% | 34.32% |

Therefore, the negative Short result cannot be explained only by an absence of
locally falling periods.

## Base trend-aligned result

| Year | Direction | Events | Mean net | Trimmed mean | Profit factor | Edge vs random |
|---|---|---:|---:|---:|---:|---:|
| 2023 | All | 57 | -0.1923% | -0.2511% | 0.7061 | -0.1519% |
| 2023 | Long | 26 | -0.1293% | -0.2584% | 0.8242 | -0.6247% |
| 2023 | Short | 31 | -0.2452% | -0.3486% | 0.5820 | +0.2447% |
| 2024 | All | 74 | +0.0145% | -0.0550% | 1.0243 | +0.2154% |
| 2024 | Long | 35 | +0.3323% | +0.2118% | 1.9328 | +0.3780% |
| 2024 | Short | 39 | -0.2708% | -0.4118% | 0.6665 | +0.0694% |

The complete result loses in 2023 and is approximately flat in 2024. Shorts
lose in both years. The remaining positive 2024 Long effect is the same bullish
directional dependence seen in the preceding analysis, not a symmetric rule.

## One fixed OI filter

| Year | Direction | Events | Mean net | Trimmed mean | Profit factor | Edge vs random |
|---|---|---:|---:|---:|---:|---:|
| 2023 | All | 26 | -0.1730% | -0.3039% | 0.7447 | -0.8198% |
| 2023 | Long | 12 | -0.1660% | -0.4627% | 0.7983 | -1.2979% |
| 2023 | Short | 14 | -0.1791% | -0.4126% | 0.6765 | -0.4100% |
| 2024 | All | 26 | +0.1837% | -0.0123% | 1.3130 | +0.6829% |
| 2024 | Long | 11 | +0.2774% | +0.0206% | 1.5707 | +0.2847% |
| 2024 | Short | 15 | +0.1150% | -0.2400% | 1.1740 | +0.9750% |

Non-rising OI does not identify exhaustion reliably. Its attractive 2024 mean
depends on a few better outcomes: the trimmed result is negative, 2023 loses,
and only 26 events remain in each year.

## Path diagnostics

Across the four hours after entry, many signals move far enough in the intended
direction to exceed the cost reserve. That alone is not an edge on a volatile
instrument. Median maximum favorable excursion (MFE) was compared with matched
random entries:

| Variant/year/direction | Median MFE | Median MAE | MFE edge vs random |
|---|---:|---:|---:|
| Base 2023 Long | 1.3576% | 0.9048% | +0.1028% |
| Base 2023 Short | 0.7017% | 0.6703% | +0.0289% |
| Base 2024 Long | 1.3096% | 0.7404% | +0.3493% |
| Base 2024 Short | 1.0356% | 1.0941% | -0.4850% |
| OI 2023 Long | 1.0258% | 1.1459% | -0.3996% |
| OI 2023 Short | 0.6835% | 0.7921% | +0.2874% |
| OI 2024 Long | 1.2518% | 1.0204% | +0.1226% |
| OI 2024 Short | 0.8673% | 1.1762% | -0.6445% |

The path advantage changes sign by year and direction. This does not support
searching for a take-profit or trailing distance to rescue the entry.

## Funding diagnostic

Extreme funding groups contain only 3–18 events per year and direction. The
apparent positive Long result under extremely negative funding has only five
events in 2023 and three in 2024. Short results are inconsistent, while the
three 2024 Shorts under extremely positive funding average `-1.9168%`.

These groups are too small to define or validate a funding rule. Treating them
as entry conditions would be fitting noise.

## What was learned

1. A standard causal EMA50/EMA200 regime filter detects substantial local Up,
   Down, and Sideways periods, but does not make this pullback symmetric.
2. A low-volume `1 ATR` counter-trend candle is not a reliable exhaustion event.
3. Falling or unchanged 15m OI is not sufficient confirmation of exhaustion.
4. Large favorable movement after an entry is common on SOL and must beat a
   matched random baseline before it is considered signal quality.
5. Neither the fixed exit nor trailing should be optimized for an entry whose
   underlying edge is inconsistent.

