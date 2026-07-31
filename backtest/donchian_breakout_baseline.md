# Donchian Breakout v1.1 — frozen development result

## Status

This configuration was selected and frozen on 2023–2024 before the 2025
validation data was opened.

```text
entry channel:  40
exit channel:   20
ATR:            Wilder 14
initial stop:   1.5 ATR
direction:      Long only
fixed TP:       none
```

## Reproduction

```bash
python -m backtest.run_backtest
```

## Diagnostic signal quality

```text
starting balance:       1000.000000 USDT
risk per trade:         1%
ending balance:         1476.032888 USDT
return:                 +47.603289%
trades:                 40
profit factor:          2.420269
maximum drawdown:       9.577529%
longest losing streak:  6
2023 net PnL:           +79.317490 USDT
2024 net PnL:           +396.715398 USDT
```

## Executable development path

```text
starting balance:       10.000000 USDT
risk per trade:         5%
leverage:               3x
ending balance:         33.133903 USDT
return:                 +231.339031%
trades:                 36
rejected entries:       10
profit factor:          2.443119
maximum drawdown:       31.067108%
2023 net PnL:           +1.759875 USDT
2024 net PnL:           +21.374028 USDT
```

Both modes include the fixed fee, slippage, and conservative funding
assumptions. No position remained open at the development/validation boundary.
