# SOL Classical Volume Profile Mean Reversion Analysis

## Decision

Reject the tested classical interpretation. It loses after both the source's
stated `0.14%` round-trip cost and the project's conservative `0.22%` cost in
2023 and 2024, for Longs and Shorts separately, with both predeclared stop
distances.

Do not tune profile resolution, Tape Speed, stops, or exits, and do not open
2025–2026 for this version.

## Source limitation

The July 2026 SSRN preprint *Volume Profile Mean Reversion Strategy with Tape
Speed Confirmation for Cryptocurrency Futures Markets* reports a five-year
SOL/USDT 5m Binance study and claims profit factors above 2.5 for 1%–2% stops.
Only its abstract was accessible: SSRN blocked automated PDF retrieval, while
OpenAlex had no cached full text, references, or citations. Therefore this is
not presented as an exact replication of the author's proprietary details.

The experiment tests a fixed, transparent classical interpretation of the
published abstract. Every approximation is stated below.

## Data

* Bybit `SOLUSDT` USDT perpetual.
* 210,816 consecutive closed 5m candles with no gaps.
* 2022-12-31 supplies the first prior-day profile.
* Development periods: 2023 and 2024 only.
* 2025–2026 remain unopened.

## Fixed rules

### Volume Profile

For each completed UTC day:

* divide its full High–Low range into 100 equal price bins;
* distribute each 5m candle's volume uniformly across the price-bin portions
  intersected by that candle's High–Low range;
* define POC as the highest-volume bin;
* expand contiguously from POC toward the larger adjacent volume until 70% of
  daily volume is included;
* the resulting boundaries are prior-day VAH and VAL.

This is a candle-based approximation. It does not claim knowledge of the true
trade-by-trade volume distribution inside each candle.

### Tape Speed

The explicit proxy for volume-weighted price momentum is:

```text
signed_tape_speed = volume × (close - open) / open
```

Its magnitude must exceed the median absolute value of the preceding 12 closed
5m candles. The current candle is excluded from its threshold.

### Entry and target

* Long: a closed 5m candle trades below prior VAL, closes back at or above VAL,
  and has positive confirmed Tape Speed.
* Short: the symmetric rejection above prior VAH with negative confirmed Tape
  Speed.
* Enter at the next 5m Open.
* The target is the developing current-day POC known at the signal close.
* Current-day bins use the prior-day grid size and anchor, so no future current-
  day range is used.
* Skip an entry if the fixed POC target is not profitable from the actual next
  Open.
* Only one position may be active.
* Close any remaining position at the final UTC-day Close.

### Risk and execution

Two source-motivated stop distances were declared before the run:

* 1% from entry;
* 2% from entry.

If Stop and Target both occur inside one candle, Stop wins. Adverse gaps through
Stop fill at the candle Open. Results are shown with:

* `0.14%`: the paper abstract's maker, taker, and slippage total;
* `0.22%`: the project's conservative taker and slippage reserve.

## Results at source cost

### 1% stop

| Year | Direction | Trades | Mean net | Trimmed mean | Profit factor |
|---|---|---:|---:|---:|---:|
| 2023 | All | 519 | -0.1809% | -0.2200% | 0.6001 |
| 2023 | Long | 285 | -0.1742% | -0.2106% | 0.6084 |
| 2023 | Short | 234 | -0.1892% | -0.2306% | 0.5905 |
| 2024 | All | 537 | -0.1456% | -0.1923% | 0.6615 |
| 2024 | Long | 276 | -0.1523% | -0.2048% | 0.6705 |
| 2024 | Short | 261 | -0.1385% | -0.1766% | 0.6504 |

### 2% stop

| Year | Direction | Trades | Mean net | Trimmed mean | Profit factor |
|---|---|---:|---:|---:|---:|
| 2023 | All | 452 | -0.1696% | -0.2074% | 0.6744 |
| 2023 | Long | 246 | -0.0817% | -0.1212% | 0.8140 |
| 2023 | Short | 206 | -0.2746% | -0.3230% | 0.5560 |
| 2024 | All | 489 | -0.1323% | -0.1793% | 0.7359 |
| 2024 | Long | 250 | -0.1553% | -0.2129% | 0.7174 |
| 2024 | Short | 239 | -0.1083% | -0.1537% | 0.7595 |

The 2% version has a positive median before conservative costs because many
small POC targets are reached, but its losing tail is much larger. Mean return,
trimmed mean, and profit factor all reject profitability.

## Results at conservative cost

Combined mean net return per trade:

| Stop | 2023 | 2024 | Profit factor range |
|---|---:|---:|---:|
| 1% | -0.2609% | -0.2256% | 0.4774–0.5271 |
| 2% | -0.2496% | -0.2123% | 0.5533–0.6067 |

The source-cost result already fails, so the conservative result is not the
cause of rejection.

## Interpretation

1. Prior-day VAH/VAL re-entry plus this causal Tape Speed proxy does not create
   positive expectancy on Bybit SOLUSDT.
2. Wider stops increase target hit rate but expose a larger loss tail; they do
   not repair the entry.
3. The failure is consistent across years and directions and does not depend on
   the project's higher cost reserve.
4. Differences from the preprint may come from unavailable formulas, Binance
   versus Bybit data, profile construction, execution assumptions, or a flaw in
   the published result. Without full methodology, choosing among these stories
   would be speculation.
5. Because this transparent version fails broadly, parameter fitting would not
   be justified. The `50 USDT / 5% / 3x` account simulation is unnecessary: it
   cannot turn negative signal expectancy positive.

