# ETHUSDT vs SOLUSDT execution feasibility

## Scope and conclusion

This analysis does not test a trading strategy or estimate profit. It compares
whether a valid minimum Bybit order can fit the account's risk and margin
limits, and whether ordinary market movement is large relative to modeled
costs.

Recommended configuration for the next research cycle:

```text
instrument:       SOLUSDT perpetual
starting capital: 50 USDT
risk limit:       5% of current balance per trade
leverage:         3x
```

`SOLUSDT / 10 USDT / 5% / 3x` is technically usable as a lower-capital
alternative. Raising risk to 10% is not needed: 50 USDT at 5% already makes
every tested stop from 0.5% through 5% executable for both instruments over
the historical price range, while retaining the lower drawdown rate.

## Inputs

* Market data: closed Bybit 15m candles from 2023-01-01 through
  2024-12-31, with 70,176 candles and no gaps for each instrument.
* Instrument limits: public Bybit snapshot observed on 2026-08-05.
* Leverage: 3x.
* Conservative round-trip reserve: 0.220%, comprising two taker fees, adverse
  slippage on both fills, and one funding reserve.
* Stop distances checked: 0.5%, 1%, 1.5%, 2%, 3%, and 5%.
* A candle is executable when the smallest valid order satisfies both the risk
  budget and total capital requirement. The effective minimum quantity also
  satisfies the 5 USDT minimum notional.

Current Bybit snapshot:

| Instrument | Price | Min quantity | Quantity step | Min notional |
|---|---:|---:|---:|---:|
| ETHUSDT | 1,873.63 | 0.01 ETH | 0.01 | 5 USDT |
| SOLUSDT | 73.86 | 0.1 SOL | 0.1 | 5 USDT |

## Market characteristics

| Metric | ETHUSDT | SOLUSDT |
|---|---:|---:|
| Median 15m ATR14 | 0.352% | 0.632% |
| 75th percentile 15m ATR14 | 0.482% | 0.853% |
| Median absolute 15m move | 0.123% | 0.237% |
| Median absolute 1h move | 0.228% | 0.447% |
| Median absolute 4h move | 0.469% | 0.903% |
| Median absolute 8h move | 0.694% | 1.314% |
| Median 15m turnover | 10.79M USDT | 5.69M USDT |
| 10th percentile 15m turnover | 2.75M USDT | 0.84M USDT |

Both markets have far more turnover than a 10–50 USDT account requires. ETH
is more liquid, but SOL's typical movement is approximately twice as large
relative to the same percentage-based cost model. On a 15m horizon, median ETH
movement is below the 0.220% modeled round trip, while SOL is only slightly
above it. A future signal must therefore demonstrate a conditional advantage;
ordinary movement alone is not enough, especially for ETH at 15m.

## Current minimum order

| Instrument | Notional | Margin and reserve at 3x | Loss at 1% stop | Loss at 2% stop | Loss at 3% stop | Loss at 5% stop |
|---|---:|---:|---:|---:|---:|---:|
| ETHUSDT | 18.74 | 6.29 | 0.23 | 0.42 | 0.60 | 0.98 |
| SOLUSDT | 7.39 | 2.48 | 0.09 | 0.16 | 0.24 | 0.39 |

With a 10 USDT account and 5% risk, the budget is 0.50 USDT. At the current
snapshot ETH fits only up to approximately a 2.4% stop, while SOL fits up to
approximately 6.5%. SOL also leaves substantially more free margin.

## Historical executable share

The table shows the share of all 2023–2024 candles on which at least the
smallest valid order fits. This is an execution-capability measure, not a trade
frequency or profitability estimate.

### Risk 5%

| Instrument | Capital | 0.5% stop | 1% | 1.5% | 2% | 3% | 5% |
|---|---:|---:|---:|---:|---:|---:|---:|
| ETHUSDT | 10 | 72.03% | 72.03% | 70.17% | 48.89% | 4.15% | 0.00% |
| SOLUSDT | 10 | 100.00% | 100.00% | 100.00% | 96.66% | 78.20% | 50.89% |
| ETHUSDT | 50 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| SOLUSDT | 50 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |

The 10 USDT ETH result deteriorates as price rises. At a 1%, 2%, and 3% stop,
respectively:

| Instrument | Year | 1% stop | 2% stop | 3% stop |
|---|---:|---:|---:|---:|
| ETHUSDT | 2023 | 100.00% | 95.68% | 8.30% |
| ETHUSDT | 2024 | 44.13% | 2.23% | 0.00% |
| SOLUSDT | 2023 | 100.00% | 100.00% | 100.00% |
| SOLUSDT | 2024 | 100.00% | 93.33% | 56.46% |

### Effect of raising risk to 10% with 10 USDT

| Instrument | 0.5% stop | 1% | 1.5% | 2% | 3% | 5% |
|---|---:|---:|---:|---:|---:|---:|---:|
| ETHUSDT | 72.03% | 72.03% | 72.03% | 72.03% | 72.03% | 40.08% |
| SOLUSDT | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 92.64% |

ETH remains blocked on 27.97% of historical candles by capital/margin even
after risk is doubled. Risk cannot solve that constraint. SOL gains some
wide-stop availability, but the improvement is unnecessary if capital is
50 USDT.

## Decision rationale

SOLUSDT is the better primary instrument for a small account because:

* its current minimum position uses about 2.48 USDT instead of ETH's 6.29 USDT;
* it allows wider stops without violating a 5% risk budget;
* it remained executable much more often across both development years;
* its typical movement is larger relative to the same modeled costs;
* its recorded turnover is ample for the intended order size.

Using 50 USDT rather than 10 USDT gives enough sizing room to avoid designing
a strategy around exchange minimums. It does not improve expectancy by itself,
but it permits the future strategy's risk rules to be tested and executed
honestly.

The current backtest engine calculates a full risk-sized quantity and rejects
it when margin is insufficient. A real order can instead be capped by both the
risk limit and available-margin limit, accepting less than 5% risk when
necessary. That sizing behavior should be corrected only after the instrument
configuration is confirmed and before another executable strategy test.
