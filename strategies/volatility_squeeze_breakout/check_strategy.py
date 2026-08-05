from dataclasses import replace

import pandas as pd

from strategies.models import Action, Side
from strategies.volatility_squeeze_breakout.strategy import (
    StrategyConfig,
    evaluate_strategy,
    prepare_market_data,
)


def _config() -> StrategyConfig:
    return replace(
        StrategyConfig(),
        atr_period=1,
        squeeze_lookback_hours=3,
        range_hours=2,
        setup_candles=4,
        volume_lookback_candles=2,
        oi_lookback_candles=4,
        funding_lookback_events=3,
        maximum_holding_candles=4,
    )


def _hourly() -> pd.DataFrame:
    start = pd.Timestamp("2022-12-31 17:00:00", tz="UTC")
    rows = []
    for index in range(8):
        compressed = index == 7
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "open_time": start + pd.Timedelta(hours=index),
                "open": 100.0,
                "high": 100.5 if compressed else 105.0,
                "low": 99.5 if compressed else 95.0,
                "close": 100.0,
                "volume": 10.0,
                "turnover": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def _signal() -> pd.DataFrame:
    setup_time = pd.Timestamp("2023-01-01 01:00:00", tz="UTC")
    rows = []
    prices = (
        (100.0, 101.0, 99.0, 100.0, 1.0),
        (100.0, 101.0, 99.0, 100.0, 1.0),
        (100.0, 107.0, 99.5, 106.0, 2.0),
        (106.0, 107.0, 105.0, 106.5, 1.0),
        (106.5, 107.0, 105.5, 106.0, 1.0),
    )
    for index, (open_price, high, low, close, volume) in enumerate(prices):
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "15m",
                "open_time": setup_time - pd.Timedelta(minutes=30)
                + pd.Timedelta(minutes=15 * index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "turnover": close * volume,
            }
        )
    return pd.DataFrame(rows)


def _open_interest() -> pd.DataFrame:
    setup_time = pd.Timestamp("2023-01-01 01:00:00", tz="UTC")
    rows = []
    for index, value in enumerate((100.0, 101.0, 102.0, 103.0, 105.0)):
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "15m",
                "timestamp": setup_time - pd.Timedelta(hours=1)
                + pd.Timedelta(minutes=15 * index),
                "open_interest": value,
            }
        )
    return pd.DataFrame(rows)


def _funding() -> pd.DataFrame:
    setup_time = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    return pd.DataFrame(
        [
            {
                "symbol": "ETHUSDT",
                "timestamp": setup_time - pd.Timedelta(hours=8 * (4 - index)),
                "funding_rate": 0.0001,
            }
            for index in range(5)
        ]
    )


def check_causal_alignment_and_signal() -> None:
    config = _config()
    prepared = prepare_market_data(
        _hourly(),
        _signal(),
        _open_interest(),
        _funding(),
        config,
    )
    rows_with_oi = prepared.loc[prepared["oi_available_time"].notna()]
    if not (rows_with_oi["oi_available_time"] <= rows_with_oi["decision_time"]).all():
        raise AssertionError("Strategy used unavailable Open Interest.")
    rows_with_funding = prepared.loc[prepared["funding_timestamp"].notna()]
    if not (
        rows_with_funding["funding_timestamp"]
        <= rows_with_funding["decision_time"]
    ).all():
        raise AssertionError("Strategy used unsettled Funding Rate.")
    rows_with_setup = prepared.loc[prepared["setup_time"].notna()]
    if not (rows_with_setup["setup_time"] <= rows_with_setup["open_time"]).all():
        raise AssertionError("Strategy used a future squeeze setup.")

    entries = prepared.loc[prepared["entry_side"].notna()]
    if len(entries) != 1 or entries.iloc[0]["entry_side"] != Side.LONG.value:
        raise AssertionError("Known confirmed breakout did not create one Long.")
    decision = evaluate_strategy(entries.iloc[0], config=config)
    if (
        decision.action is not Action.OPEN_POSITION
        or decision.side is not Side.LONG
        or decision.execute_at != entries.iloc[0]["decision_time"]
        or decision.take_profit_r_multiple != 2.0
    ):
        raise AssertionError("Confirmed breakout decision is incorrect.")


def check_open_interest_is_required() -> None:
    config = _config()
    falling = _open_interest()
    falling.loc[falling.index[-1], "open_interest"] = 99.0
    prepared = prepare_market_data(
        _hourly(),
        _signal(),
        falling,
        _funding(),
        config,
    )
    if prepared["entry_side"].notna().any():
        raise AssertionError("Breakout entered without rising Open Interest.")


def main() -> None:
    check_causal_alignment_and_signal()
    check_open_interest_is_required()
    print("Volatility Squeeze Breakout checks passed:")
    print("Only available setup, Open Interest, and Funding Rate used: True")
    print("Confirmed breakout creates one next-open decision: True")
    print("Breakout without rising Open Interest is blocked: True")


if __name__ == "__main__":
    main()
