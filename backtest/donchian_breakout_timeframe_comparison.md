# Donchian Breakout v1.1, v2, and v3 timeframe comparison

## Compared versions

```text
v1.1: closed 4h Donchian 40/20, Long-only
v2:   closed 4h Donchian 40/20 with 4h EMA50/EMA200 regime
v3:   closed 15m Donchian 40/20 with closed 1h EMA50/EMA200 regime
```

ATR14, `1.5 ATR` stop, costs, risk, leverage, one-position rules, and lack of
a fixed take profit are unchanged. No timeframe, EMA, channel, or stop variants
were tested.

```bash
python -m backtest.run_timeframe_comparison
```

## Complete signal-quality results

| Period | Version | Return | Trades | PF | Drawdown | Long net | Short net |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023–2024 | v1.1 | +50.17% | 40 | 2.471 | 9.58% | +501.69 | — |
| 2023–2024 | v2 | +25.04% | 47 | 1.590 | 12.40% | +311.87 | -61.46 |
| 2023–2024 | v3 | -90.70% | 691 | 0.528 | 91.90% | -359.59 | -547.38 |
| 2025 | v1.1 | +14.51% | 19 | 2.000 | 4.56% | +145.08 | — |
| 2025 | v2 | +7.74% | 27 | 1.366 | 9.31% | +176.81 | -99.38 |
| 2025 | v3 | -29.98% | 333 | 0.869 | 40.55% | -100.86 | -198.93 |
| 2026 through Jul 30 | v1.1 | -7.09% | 13 | 0.288 | 8.85% | -70.94 | — |
| 2026 through Jul 30 | v2 | +2.66% | 16 | 1.203 | 8.71% | -90.57 | +117.21 |
| 2026 through Jul 30 | v3 | -40.60% | 196 | 0.664 | 42.44% | -192.56 | -213.49 |

Version 3 fees were `410.15 USDT` in 2023–2024, `369.77 USDT` in 2025, and
`223.29 USDT` in the tested part of 2026. Its gross PnL before fees and funding
was already negative in 2023–2024 and 2026. In 2025 it was positive before
costs but too small to survive realistic execution expenses.

## Executable account

With fixed comparison balances, v3 produced:

```text
2023–2024: 10.000000 -> 6.661137 USDT, 27 trades, 1434 rejected entries
2025:      33.133903 -> 45.299608 USDT, 44 trades, 735 rejected entries
2026:      50.585451 -> 34.658023 USDT, 18 trades, 389 rejected entries
```

The apparent executable profit in 2025 is not scalable strategy expectancy:
the complete 333-trade signal flow lost 29.98%, while the small account traded
only a constrained subset after 735 rejections.

Continuous executable paths from 10 USDT were:

```text
v1.1: 10.000000 -> 33.518294 -> 50.969842 -> 37.119779 USDT
v2:   10.000000 -> 15.214207 -> 25.631526 -> 29.211220 USDT
v3:   10.000000 ->  6.661137 ->  8.939352 ->  5.817767 USDT
```

## Decision

Moving the fixed numeric periods to 15m created frequent noisy breakouts that
did not survive costs or produce positive gross expectancy consistently. Both
Long and Short flows were negative in every tested period. Version 3 is
rejected.

Together, v1.1 failed the independent 2026 period, v2 improved only the
already viewed 2026 regime while degrading earlier periods, and v3 failed all
periods. Further Donchian timeframe or parameter adjustment is not justified
under the agreed controlled process. The family is not approved for demo.
