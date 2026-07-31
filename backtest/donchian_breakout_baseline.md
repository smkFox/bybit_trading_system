# Donchian Breakout v1 — 2023–2024 baseline

## Status

This is the unchanged first run of the candidate strategy. It does not approve
demo or live trading. No 2025 or 2026 data was inspected.

## Reproduction

```bash
python -m backtest.run_backtest
```

## Frozen baseline

```text
timeframe:       4h derived from closed 1h candles
entry channel:   20 previous candles
exit channel:    10 previous candles
ATR:             Wilder 14
initial stop:    2 ATR
fixed TP:        none
```

Both modes use 0.055% taker fee and 0.05% adverse slippage per fill. Funding is
modeled as a conservative 0.01% cost per crossed 8-hour interval.

## Diagnostic signal-quality mode

Size and margin filters are neutralized to evaluate the complete strategy
flow. The 100x diagnostic leverage is used only to prevent a margin filter; it
is not a proposed trading setting.

```text
starting balance:       1000.000000 USDT
risk per trade:         1%
ending balance:         1127.278056 USDT
net return:             +12.727806%
trades:                 110
profit factor:          1.195223
total net R:            14.793242
maximum drawdown:       13.698894%
longest losing streak:  8
LONG net PnL:           +166.109533 USDT
SHORT net PnL:          -38.831477 USDT
fees:                   40.048751 USDT
funding:                48.520803 USDT
```

Year by entry timestamp:

```text
2023: 53 trades, -3.859639 USDT, PF 0.988648
2024: 57 trades, +131.137695 USDT, PF 1.420352
```

## Executable 10 USDT mode

```text
starting balance:       10.000000 USDT
risk per trade:         5%
leverage:               3x
ending balance:         11.156673 USDT
net return:             +11.566734%
executed trades:        37
rejected entries:       234
profit factor:          1.109161
maximum drawdown:       48.132475%
LONG net PnL:           +4.200771 USDT
SHORT net PnL:          -3.044097 USDT
```

All 37 trades were entered in 2023. No 2024 signal was executable with the
10 USDT balance, 3x leverage, 5% risk limit, and current ETHUSDT constraints.

## Baseline interpretation

This hypothesis is materially stronger than the rejected EMA pullback: its
complete signal flow is positive after modeled costs. It is not ready to
freeze because the result is concentrated in 2024 and in Long trades, the
Short side is negative, the executable account cannot trade in 2024, and the
5% risk scenario has a 48% closed-equity drawdown.

The next decision is a limited development review, not validation or demo.
