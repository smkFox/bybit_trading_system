# BTC-confirmed ETH Shock Mean Reversion v1 — development result

## Decision

`REJECT_AND_STOP`

The fixed candidate failed its 2023–2024 development gate. It was not tested
on 2025 or 2026, and its parameters were not changed after seeing the result.

## Fixed setup

* Instrument: `ETHUSDT` perpetual.
* BTC context: `BTCUSDT` closed 1h candles.
* Entries: ETH closed 15m candles.
* Relationship windows: 168 hours for rolling beta and residual Z-score.
* Shock threshold: `|Z| >= 2.5`.
* Confirmation window: four 15m candles.
* Stop: ETH hourly ATR14 multiplied by `1.5`.
* Normalization exit: `|Z|` returns through the relevant `0.5` boundary.
* Maximum holding time: 32 candles, or 8 hours.
* Costs: 0.055% taker fee and 0.050% adverse slippage per fill.
* Funding assumption: 0.010% cost per crossed 8-hour interval.

## Results

The signal-quality run neutralizes exchange order-size limits so that every
valid signal is evaluated. The executable run applies the intended initial
capital, risk, leverage, and current instrument constraints.

| Metric | Signal quality | Executable |
|---|---:|---:|
| Starting balance | 1,000 USDT | 10 USDT |
| Risk per trade | 1% | 5% |
| Leverage | size-neutralized | 3x |
| Trades | 284 | 69 |
| Rejected entries | 0 | 216 |
| Ending balance | 638.632336 USDT | 7.425217 USDT |
| Return | -36.136766% | -25.747831% |
| Win rate | 30.633803% | 34.782609% |
| Profit factor | 0.312324 | 0.449723 |
| Maximum closed-equity drawdown | 36.225080% | 26.756103% |
| Total fees | 169.348720 USDT | 1.396123 USDT |
| Total funding | 1.676364 USDT | 0.013860 USDT |

Signal-quality detail:

| Segment | Trades | Net PnL | Profit factor |
|---|---:|---:|---:|
| 2023 | 130 | -204.388241 USDT | 0.306245 |
| 2024 | 154 | -156.979423 USDT | 0.320082 |
| Long | 128 | -133.412693 USDT | — |
| Short | 156 | -227.954971 USDT | — |

The complete signal flow lost `361.367664 USDT`. Removing reported fees and
funding still leaves an approximate gross loss of `190.342580 USDT`, so costs
are not the reason the hypothesis failed.

## Gate outcome

Failed:

* positive result in 2023;
* positive result in 2024;
* combined profit factor of at least 1.2;
* maximum drawdown of at most 20%;
* non-negative Long result;
* non-negative Short result.

Passed only the activity and clean-boundary checks: at least 30 total trades,
at least 10 trades in each year, and no forced end-of-data exit.

This is a broad failure across both years and both directions. Testing the same
candidate on 2025–2026 or tuning it from these results is not justified.
