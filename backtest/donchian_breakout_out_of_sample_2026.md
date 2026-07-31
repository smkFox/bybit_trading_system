# Donchian Breakout v1.1 — 2026 out-of-sample

## Status

The frozen `40/20`, `1.5 ATR`, Long-only configuration was run unchanged from
2026-01-01 through the latest complete 4h candle available on
2026-07-31 00:00 UTC. No parameters or execution assumptions were changed
after the 2025 validation.

```bash
python -m market_data.update_candles ETHUSDT 1h
python -m backtest.run_out_of_sample
```

## Signal-quality result

```text
starting balance:       1000.000000 USDT
risk per trade:         1%
ending balance:         929.058015 USDT
return:                 -7.094199%
trades:                 13
profit factor:          0.287563
total net R:            -7.284736
maximum drawdown:       8.845272%
longest losing streak:  10
fees:                   5.030297 USDT
funding:                5.112031 USDT
```

## Executable continuation

The account path is reproduced without rounded intermediate balances:

```text
2023 start:             10.000000 USDT
2025 start:             33.133903 USDT
2026 start:             50.585451 USDT
2026 ending balance:    37.235865 USDT
2026 return:            -26.390169%
trades:                 13
rejected entries:       0
profit factor:          0.314207
maximum drawdown:       32.823375%
longest losing streak:  10
fees:                   0.999236 USDT
funding:                1.111650 USDT
```

Both modes recorded 10 stop exits and 3 strategy exits. Neither mode had an
open position forced closed at the end of the available data.

## Decision

The independent signal-quality result is negative, so the loss is not caused
by the 10 USDT order-size constraints. Donchian Breakout v1.1 is not approved
for demo trading in its current form. The frozen result must not be repaired
by selecting new parameters from the 2026 sample.
