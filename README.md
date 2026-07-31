# Bybit Trading System

Local research and trading-system project for Bybit USDT perpetual futures.
The tested Donchian Breakout family on `ETHUSDT` is not approved; the project
currently has no demo candidate. Research never places exchange orders.

## Project structure

```text
market_data/                    Bybit market data, SQLite, and data access
strategies/models.py            Shared trading-decision model
strategies/indicators.py        Shared Wilder ATR and EMA
strategies/timeframes.py        Closed 1h to 4h aggregation
strategies/donchian_breakout/   Current strategy code, specification, checks
backtest/                       Shared execution simulator and baseline runner
data/                           Local runtime data and SQLite database
context.md                      Stable project principles
roadmap.md                      Current plan, status, and decisions
```

## Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Data commands

Inspect a small public Bybit response:

```bash
python -m market_data.check_bybit_api
```

Initialize SQLite:

```bash
python -m market_data.database
```

Download or safely resume a historical range:

```bash
python -m market_data.download_history \
  ETHUSDT \
  1h \
  2023-01-01T00:00:00+00:00 \
  2026-01-01T00:00:00+00:00
```

Update stored closed candles:

```bash
python -m market_data.update_candles ETHUSDT 1h
```

The database is stored at `data/market_data.sqlite3` and excluded from Git.
The unique key `symbol + timeframe + open_time` prevents duplicates.

## Tested strategy family

The frozen v1.1 specification is:

```text
strategies/donchian_breakout/specification.md
```

Frozen rules:

```text
4h candles derived from stored closed 1h candles
40-candle entry channel
20-candle exit channel
Wilder ATR14
1.5 ATR initial stop
Long-only
no fixed take profit
one position and no pyramiding
```

This strategy passed its 2025 historical validation but failed its unchanged
2026 out-of-sample run. It is not approved for demo or live trading.

The fixed v2 EMA50/EMA200 market-regime experiment is documented in
`strategies/donchian_breakout/specification_v2.md`. It improved the 2026
diagnostic result but degraded 2023–2025 and is also not approved for demo.

The fixed v3 experiment moved signals to `15m` with the regime on closed `1h`.
Its complete signal flow lost money in every tested period, so the Donchian
family is no longer the active candidate for demo.

## Checks

```bash
python -m strategies.check_indicators
python -m strategies.check_timeframes
python -m strategies.donchian_breakout.check_strategy
python -m backtest.check_engine
```

The checks cover ATR and EMA values and warm-up, closed 4h aggregation, UTC
boundaries, gaps, shifted Donchian channels, exact closed-1h to 15m alignment,
no look-ahead, deterministic decisions, next-candle execution, protective
stops, optional take profit, strategy exits, and fees.

## Baseline backtest

```bash
python -m backtest.run_backtest
```

The command uses only 2023–2024 and prints two simulations:

1. diagnostic signal quality with 1% risk and execution-size filters
   neutralized;
2. executable `10 USDT / 5% risk / 3x` with current ETHUSDT constraints.

Both include a 0.055% taker fee, 0.05% adverse slippage per fill, and a
conservative 0.01% funding cost per crossed 8-hour interval. The current
instrument limits were observed on 2026-07-30 and are not historical metadata.

The recorded result and its limitations are in
`backtest/donchian_breakout_baseline.md`. Backtesting does not write results to
the market-data database and never sends orders to Bybit.

## Fixed development comparison

Run the agreed 30 variants on 2023–2024:

```bash
python -m strategies.donchian_breakout.run_development_tests
```

The matrix contains five predefined entry/exit channel pairs, three ATR-stop
multipliers, and `LONG_SHORT` versus `LONG_ONLY`. All other strategy and
execution assumptions remain fixed. The command writes
`donchian_breakout_development_tests.xlsx` in the project root with the full
comparison and assumptions; it does not rank or select a configuration.

## Frozen validation

The selected configuration is `40/20`, `1.5 ATR`, Long-only. Reproduce its
one-time 2025 validation with:

```bash
python -m backtest.run_validation
```

The executable validation continues from the exact 33.133903 USDT development
ending balance. The recorded result is in
`backtest/donchian_breakout_validation_2025.md`. This command does not load or
test 2026 data and does not change the frozen configuration.

## Frozen out-of-sample run

After updating the stored closed candles, reproduce the unchanged 2026 run:

```bash
python -m market_data.update_candles ETHUSDT 1h
python -m backtest.run_out_of_sample
```

The executable account continues through the exact development and validation
ending balances. The recorded result and rejection decision are in
`backtest/donchian_breakout_out_of_sample_2026.md`.

## Fixed market-regime comparison

Compare v1.1 Long-only with the single agreed v2 EMA50/EMA200 regime:

```bash
python -m backtest.run_regime_comparison
```

The command runs no parameter sweep. Its complete recorded comparison is in
`backtest/donchian_breakout_regime_comparison.md`.

## Fixed timeframe comparison

Compare v1.1, v2, and the agreed v3 `15m` signals with closed `1h` regime:

```bash
python -m backtest.run_timeframe_comparison
```

The v3 rules are in
`strategies/donchian_breakout/specification_v3.md`. The complete result and
rejection decision are in
`backtest/donchian_breakout_timeframe_comparison.md`.
