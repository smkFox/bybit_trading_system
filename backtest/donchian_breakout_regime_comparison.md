# Donchian Breakout v1.1 versus v2 EMA regime

## Scope

One fixed v2 was tested without a parameter sweep:

```text
Bull:    EMA50 > EMA200 and close > EMA50; allow Long only
Bear:    EMA50 < EMA200 and close < EMA50; allow Short only
Neutral: block new entries
```

Both versions use the same closed 4h candles, Donchian `40/20`, ATR14,
`1.5 ATR` stop, execution assumptions, and costs. November–December 2022 data
is used only to warm EMA200 before 2023. The comparison command is:

```bash
python -m backtest.run_regime_comparison
```

## Signal-quality comparison

Size filters are neutralized with 1000 USDT starting balance and 1% risk.

| Period | Version | Return | Trades | PF | Drawdown | Long net | Short net |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023–2024 | v1.1 | +50.17% | 40 | 2.471 | 9.58% | +501.69 | — |
| 2023–2024 | v2 | +25.04% | 47 | 1.590 | 12.40% | +311.87 | -61.46 |
| 2025 | v1.1 | +14.51% | 19 | 2.000 | 4.56% | +145.08 | — |
| 2025 | v2 | +7.74% | 27 | 1.366 | 9.31% | +176.81 | -99.38 |
| 2026 through July 30 | v1.1 | -7.09% | 13 | 0.288 | 8.85% | -70.94 | — |
| 2026 through July 30 | v2 | +2.66% | 16 | 1.203 | 8.71% | -90.57 | +117.21 |

## Same-balance executable comparison

Both versions receive the same account balance at the start of each period,
with 5% risk and 3x leverage.

| Period and start | v1.1 ending / return | v2 ending / return |
|---|---:|---:|
| 2023–2024, 10 USDT | 33.518294 / +235.18% | 15.214207 / +52.14% |
| 2025, 33.133903 USDT | 50.585451 / +52.67% | 40.971150 / +23.65% |
| 2026, 50.585451 USDT | 37.235865 / -26.39% | 50.471359 / -0.23% |

The quality mode is the primary strategy comparison. Small-account executable
results are affected by the 0.01 ETH quantity step and rejected entries.

## Continuous 10 USDT account

```text
v1.1: 10.000000 -> 33.518294 -> 50.969842 -> 37.119779 USDT
v2:   10.000000 -> 15.214207 -> 25.631526 -> 29.211220 USDT
```

The v1.1 development balance differs slightly from the previously recorded
33.133903 USDT because this direct comparison gives both versions the same
pre-2023 indicator warm-up and therefore exposes all 2023 candles to both.

## Interpretation

The regime hypothesis explains part of the 2026 failure: v2 Short trades were
profitable in 2026 and nearly removed the executable loss. However, the exact
same Short rules lost money in both 2023–2024 and 2025. Compared with v1.1,
v2 also reduced profit factor, increased drawdown, and lengthened losing
streaks during development.

The fixed v2 is therefore not a robust improvement and is not approved for
demo. Its 2026 improvement must not be used alone to select it. The experiment
does support retaining market regime as a research direction, but not this
exact EMA50/EMA200 implementation as the trading candidate.
