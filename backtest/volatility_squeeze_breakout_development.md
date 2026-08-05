# Volatility Squeeze Breakout v1 — development result

## Decision

`REJECT_AND_STOP`

The fixed candidate failed its 2023–2024 development gate. It was not tested
on 2025 or 2026, and no parameter was changed after the result.

## Data

* ETHUSDT closed 1h candles: 18,288.
* ETHUSDT closed 15m candles loaded: 70,368.
* ETHUSDT 15m Open Interest observations: 73,150.
* ETHUSDT settled Funding Rate observations: 2,286.
* Development candles from 2023-01-01: 70,176.

Bybit has two isolated missing 15m OI observations in the loaded range, each
creating one 30-minute gap: before `2023-05-31 03:15 UTC` and before
`2024-08-26 12:15 UTC`. They were not filled. OI confirmation is unavailable
until its exact prior 15m and one-hour observations exist again.

## Results

| Metric | Signal quality | Executable |
|---|---:|---:|
| Starting balance | 1,000 USDT | 10 USDT |
| Risk per trade | 1% | 5% |
| Leverage | size-neutralized | 3x |
| Trades | 496 | 2 |
| Rejected entries | 0 | 548 |
| Ending balance | 137.895684 USDT | 10.099110 USDT |
| Return | -86.210432% | +0.991100% |
| Win rate | 28.629032% | 50.000000% |
| Profit factor | 0.394133 | 1.364515 |
| Maximum closed-equity drawdown | 86.620565% | 2.621688% |
| Total fees | 445.108129 USDT | 0.061126 USDT |
| Total funding | 9.885041 USDT | 0.002564 USDT |

Signal-quality detail:

| Segment | Trades | Net PnL | Profit factor |
|---|---:|---:|---:|
| 2023 | 250 | -712.725557 USDT | 0.325356 |
| 2024 | 246 | -149.378759 USDT | 0.592395 |
| Long | 290 | -515.454058 USDT | — |
| Short | 206 | -346.650258 USDT | — |

There were 345 stop exits, 131 take-profit exits, and 20 maximum-holding
exits. The complete signal flow lost `862.104316 USDT`. Removing reported fees
and funding still leaves an approximate gross loss of `407.111146 USDT`, so
execution costs are not the reason the hypothesis failed.

The small-account result is not evidence of strategy quality: only two of 550
entry signals seen while flat could satisfy current order and risk limits, and
548 were rejected. The complete signal-quality flow is the development result.

## Gate outcome

Failed:

* positive result in 2023;
* positive result in 2024;
* combined profit factor of at least 1.2;
* maximum drawdown of at most 20%;
* non-negative Long result;
* non-negative Short result.

Passed only activity and clean-boundary requirements. This broad failure does
not justify tuning or opening the 2025–2026 periods.
