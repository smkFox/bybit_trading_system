# Volatility Squeeze Breakout v1

## Fixed development specification

```text
instrument:                  ETHUSDT perpetual
market-state timeframe:      closed 1h
entry timeframe:             closed 15m
relative volatility:         1h Wilder ATR14 / close
squeeze threshold:           prior 720h 20th percentile
breakout range:              latest four closed 1h candles
setup lifetime:              next 16 candles / 4h
volume confirmation:         current 15m volume > 1.5 × prior 20 median
Open Interest confirmation:  latest available OI > previous OI and OI 1h ago
Funding guard:               prior 90-event 10th/90th percentiles
entry ATR:                   Wilder ATR14 on 15m
initial stop:                1.5 ATR
take profit:                 2R / 3 ATR
maximum holding:             32 candles / 8h
simultaneous positions:      one
pyramiding:                  disabled
```

At a closed hourly candle, a squeeze is active when its `ATR14 / close` is at
or below the 20th percentile calculated from the previous 720 values. The
current value is excluded from its threshold. The range is the highest High
and lowest Low of the latest four fully closed hourly candles. This setup may
produce one entry during the next four hours.

## Entry

A closed 15m candle creates a Long candidate when its Close is above the fixed
range High, or a Short candidate when its Close is below the fixed range Low.
It is accepted only when:

* volume is greater than `1.5 ×` the median of the previous 20 closed 15m
  candles;
* the latest available 15m Open Interest value is greater than both its
  previous observation and its value one hour earlier;
* a Long's latest settled Funding Rate is not above the causal 90th percentile
  of the previous 90 settlements;
* a Short's latest settled Funding Rate is not below the causal 10th
  percentile of the previous 90 settlements.

The first accepted candle for a setup enters at the next 15m Open. A setup
expires after 16 candles. The strategy never uses an OI observation before its
15m interval has completed or a Funding Rate before its settlement timestamp.

## Exit

The initial protective stop is `1.5 ×` the 15m ATR14 fixed at the signal. The
take profit is `2R`, or twice the stop distance. If both levels occur in one
candle, the simulator chooses the stop. A remaining position closes after 32
held 15m candles at the following candle Open.

## Development boundary

Only 2023–2024 is opened. The candidate proceeds only if complete signal
quality is positive in both years, combined profit factor is at least 1.2,
closed-equity drawdown is at most 20%, at least 30 trades occur with at least
10 per year, and neither direction has negative net expectancy.
