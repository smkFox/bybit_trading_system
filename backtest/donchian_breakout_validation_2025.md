# Donchian Breakout v1.1 — 2025 validation

## Status

The frozen `40/20`, `1.5 ATR`, Long-only configuration was run once on 2025.
No parameters or execution assumptions were changed after viewing the result.

```bash
python -m backtest.run_validation
```

## Signal-quality validation

```text
starting balance:       1000.000000 USDT
risk per trade:         1%
ending balance:         1145.075926 USDT
return:                 +14.507593%
trades:                 19
profit factor:          2.000112
total net R:            14.899304
maximum drawdown:       4.560355%
longest losing streak:  5
fees:                   7.652268 USDT
funding:                10.628820 USDT
```

## Executable continuation

The 2025 account starts with the exact 33.133903 USDT produced by the frozen
executable development path. Development ended without an open position.

```text
starting balance:       33.133903 USDT
risk per trade:         5%
leverage:               3x
ending balance:         50.585451 USDT
return:                 +52.669761%
trades:                 19
rejected entries:       0
profit factor:          1.806656
maximum drawdown:       15.743498%
longest losing streak:  5
fees:                   1.159417 USDT
funding:                1.592235 USDT
```

## Interpretation

The frozen strategy passed the 2025 validation with positive net expectancy
after modeled costs in both modes. The sample contains only 19 trades, so this
is encouraging evidence rather than proof of future profitability. The
strategy remains unchanged pending a separate decision about the 2026
out-of-sample run.
