# Bybit Trading System

Local research and trading-system project for Bybit USDT perpetual futures.
The project currently has no strategy approved for demo or live trading.
Research commands use public market data and never place exchange orders.

## Current state

Volatility Squeeze Breakout v1 failed its fixed 2023–2024 development gate and
was stopped before 2025–2026. Its code remains temporarily available so the
rejection is reproducible; it is not an active trading configuration.

`SOLUSDT / 50 USDT / 5% risk / 3x` is confirmed for the current research cycle.
SOL market-behavior analysis found no standalone profitable effect. Its
trend-aligned low-volume pullback follow-up and one OI filter also failed, so no
strategy is approved.

A fixed classical Volume Profile/Tape Speed interpretation inspired by a
SOL-specific SSRN preprint also lost in both development years and directions.

Earlier rejected implementations are recoverable from Git. The BTC/ETH Shock
Mean Reversion checkpoint is `a7bb35f`; the earlier Donchian checkpoint is
`2e7c03d`.

## Project structure

```text
market_data/                              Bybit data, SQLite, and access
research/                                 Focused market and execution analysis
strategies/models.py                      Shared decision models
strategies/indicators.py                  Shared Wilder ATR
strategies/volatility_squeeze_breakout/   Latest rejected candidate
backtest/engine.py                        Shared execution simulator
backtest/run_squeeze_breakout_development.py
data/                                     Local SQLite data, excluded from Git
context.md                                Stable project principles
roadmap.md                                Current plan and decision history
```

## Setup

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Market data

Initialize and verify candle storage:

```bash
python -m market_data.database
python -m market_data.check_candle_storage
```

Download or safely resume candles:

```bash
python -m market_data.download_history \
  ETHUSDT 15m \
  2023-01-01T00:00:00+00:00 \
  2024-12-31T23:45:00+00:00
```

Download Open Interest or Funding Rate history:

```bash
python -m market_data.download_derivatives_history \
  open-interest ETHUSDT 15m \
  2022-12-01T00:00:00+00:00 \
  2024-12-31T23:45:00+00:00

python -m market_data.download_derivatives_history \
  funding ETHUSDT \
  2022-12-01T00:00:00+00:00 \
  2024-12-31T23:59:59+00:00
```

Candles, OI, and funding use separate SQLite tables and natural unique keys.
Repeated downloads are idempotent. The database is
`data/market_data.sqlite3` and is excluded from Git.

## Latest candidate reproduction

The frozen rules are in
`strategies/volatility_squeeze_breakout/specification.md`.

```bash
python -m strategies.check_indicators
python -m strategies.volatility_squeeze_breakout.check_strategy
python -m backtest.check_engine
python -m backtest.run_squeeze_breakout_development
```

The complete signal flow produced 496 trades, `-86.21%` return, profit factor
`0.39`, and `86.62%` maximum closed-equity drawdown. Both years and both trade
directions lost money. The exact result is in
`backtest/volatility_squeeze_breakout_development.md`.

The simulator includes 0.055% taker fees, 0.050% adverse slippage per fill,
and a conservative 0.010% funding cost per crossed 8-hour interval. Actual
historical funding is used by this candidate as an entry guard; the execution
cost model remains conservative and direction-independent.

## Instrument feasibility

Reproduce the non-strategy comparison of ETHUSDT and SOLUSDT:

```bash
python -m research.analyze_instrument_feasibility
```

The recorded analysis is in `research/instrument_feasibility.md`. It recommends
`SOLUSDT / 50 USDT / 5% risk / 3x`, which is now confirmed for research.

Reproduce the SOL market-behavior analysis:

```bash
python -m research.analyze_sol_behavior
```

The interpretation and candidate principles are recorded in
`research/sol_market_behavior.md`. This analysis does not approve a strategy for
demo or live trading.

Reproduce the fixed trend and derivatives follow-up:

```bash
python -m research.analyze_sol_trend_pullback
```

The exact result and rejection decision are in
`research/sol_trend_pullback_analysis.md`. The test uses SOL OI and funding only
through 2024 and does not open later periods.

Reproduce the classical 5m Volume Profile analysis:

```bash
python -m research.analyze_sol_volume_profile
```

The exact assumptions, source limitations, and rejection are recorded in
`research/sol_volume_profile_analysis.md`.
