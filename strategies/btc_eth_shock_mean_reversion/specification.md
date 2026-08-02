# BTC-confirmed ETH Shock Mean Reversion v1

## Fixed development specification

```text
traded instrument:       ETHUSDT perpetual
market context:          BTCUSDT
relationship timeframe: closed 1h
entry timeframe:         closed 15m
rolling beta:            previous 168 hourly returns
residual Z-score:        previous 168 residuals
shock threshold:         |Z| >= 2.5
normalization threshold: |Z| <= 0.5 from the relevant side
ATR:                     Wilder 14 on ETH 1h
initial stop:            1.5 ATR
confirmation window:     next four 15m candles
maximum holding:         32 signal candles / 8 hours
fixed take profit:       none
simultaneous positions:  one
pyramiding:              disabled
```

Hourly log returns estimate the causal rolling relationship:

```text
beta = covariance(ETH returns, BTC returns) / variance(BTC returns)
ETH residual = ETH return - beta * BTC return
Z = (current residual - prior residual mean) / prior residual deviation
```

Both rolling beta and residual normalization exclude the current hour.

## Entry

An hourly `Z <= -2.5` creates a pending Long shock. An hourly `Z >= 2.5`
creates a pending Short shock. Only the next four 15m candles may confirm it:

```text
Long:  15m close > previous 15m high
Short: 15m close < previous 15m low
```

Only the first confirmation may enter, at the next 15m open. An unconfirmed
shock expires after four candles.

## Exit

A Long closes when residual Z reaches `-0.5` or higher. A Short closes when it
reaches `0.5` or lower. The decision executes at the next 15m open. The fixed
protective stop remains active inside every candle. Any remaining position
closes after 32 held 15m candles. No same-decision reversal is allowed.

## Development gate

Only 2023–2024 is opened initially. The candidate proceeds only if complete
signal quality is positive in both years, combined profit factor is at least
1.2, closed-equity drawdown is at most 20%, at least 30 trades occur with at
least 10 per year, and neither direction has negative net expectancy.
