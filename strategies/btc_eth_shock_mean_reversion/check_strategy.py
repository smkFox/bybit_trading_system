import math
from dataclasses import replace

import pandas as pd
from pandas.testing import assert_frame_equal

from strategies.btc_eth_shock_mean_reversion.strategy import (
    Reason,
    StrategyConfig,
    evaluate_strategy,
    prepare_hourly_relationship,
    prepare_market_data,
)
from strategies.models import Action, PositionState, Side


def _hourly_candles(
    symbol: str,
    returns: list[float],
) -> pd.DataFrame:
    start = pd.Timestamp("2022-11-01 00:00:00", tz="UTC")
    prices = [100.0]
    for value in returns[1:]:
        prices.append(prices[-1] * math.exp(value))
    rows = []
    for index, close in enumerate(prices):
        rows.append(
            {
                "symbol": symbol,
                "timeframe": "1h",
                "open_time": start + pd.Timedelta(hours=index),
                "open": close,
                "high": close * 1.001,
                "low": close * 0.999,
                "close": close,
                "volume": 1.0,
                "turnover": close,
            }
        )
    return pd.DataFrame(rows)
def _relationship_inputs(shock: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    btc_returns = [
        0.001 if index % 3 == 0 else (-0.0008 if index % 3 == 1 else 0.0003)
        for index in range(400)
    ]
    residuals = [
        ((index % 7) - 3) * 0.00008 for index in range(400)
    ]
    residuals[-1] = shock
    eth_returns = [
        1.5 * btc_return + residual
        for btc_return, residual in zip(btc_returns, residuals, strict=True)
    ]
    return (
        _hourly_candles("ETHUSDT", eth_returns),
        _hourly_candles("BTCUSDT", btc_returns),
    )


def check_relationship_and_no_look_ahead() -> None:
    eth, btc = _relationship_inputs(shock=-0.02)
    original_eth = eth.copy(deep=True)
    original_btc = btc.copy(deep=True)
    relationship = prepare_hourly_relationship(eth, btc)
    assert_frame_equal(eth, original_eth)
    assert_frame_equal(btc, original_btc)
    final = relationship.iloc[-1]
    if not 1.4 < final["beta"] < 1.6:
        raise AssertionError("Rolling BTC beta is outside the expected range.")
    if final["residual_z"] > -2.5 or final["shock_side"] != Side.LONG.value:
        raise AssertionError("Known negative ETH residual did not create Long shock.")

    changed_eth = eth.copy(deep=True)
    changed_eth.loc[390:, "close"] *= 1.2
    changed = prepare_hourly_relationship(changed_eth, btc)
    columns = ["beta", "residual", "residual_z", "shock_side"]
    assert_frame_equal(
        relationship.loc[:389, columns],
        changed.loc[:389, columns],
    )


def check_15m_confirmation() -> None:
    eth, btc = _relationship_inputs(shock=-0.02)
    relationship = prepare_hourly_relationship(eth, btc)
    shock_time = relationship.iloc[-1]["hour_decision_time"]
    start = shock_time - pd.Timedelta(minutes=15)
    prices = (
        (100.0, 101.0, 98.0, 99.0),
        (99.0, 100.0, 98.0, 99.0),
        (99.0, 102.0, 99.0, 101.0),
        (101.0, 103.0, 100.0, 102.0),
        (102.0, 104.0, 101.0, 103.0),
        (103.0, 105.0, 102.0, 104.0),
    )
    rows = []
    for index, (open_price, high, low, close) in enumerate(prices):
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "15m",
                "open_time": start + pd.Timedelta(minutes=15 * index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1.0,
                "turnover": close,
            }
        )
    prepared = prepare_market_data(eth, btc, pd.DataFrame(rows))
    confirmations = prepared.loc[prepared["entry_side"].notna()]
    if len(confirmations) != 1:
        raise AssertionError("One hourly shock produced multiple confirmations.")
    confirmation = confirmations.iloc[0]
    if (
        confirmation["entry_side"] != Side.LONG.value
        or confirmation["open_time"] != shock_time + pd.Timedelta(minutes=15)
    ):
        raise AssertionError("Long shock was confirmed on the wrong 15m candle.")


def _decision_row(
    *,
    entry_side: str | object = pd.NA,
    current_z: float = -2.8,
    shock_z: float = -3.0,
) -> pd.Series:
    open_time = pd.Timestamp("2023-01-10 12:00:00", tz="UTC")
    return pd.Series(
        {
            "symbol": "ETHUSDT",
            "timeframe": "15m",
            "open_time": open_time,
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 101.0,
            "decision_time": open_time + pd.Timedelta(minutes=15),
            "current_residual_z": current_z,
            "shock_residual_z": shock_z,
            "shock_beta": 1.5,
            "shock_atr": 4.0,
            "entry_side": entry_side,
        }
    )


def check_decisions() -> None:
    long_entry = evaluate_strategy(
        _decision_row(entry_side=Side.LONG.value)
    )
    short_entry = evaluate_strategy(
        _decision_row(
            entry_side=Side.SHORT.value,
            current_z=2.8,
            shock_z=3.0,
        )
    )
    if (
        long_entry.action is not Action.OPEN_POSITION
        or long_entry.side is not Side.LONG
        or long_entry.stop_distance != 6.0
        or short_entry.side is not Side.SHORT
    ):
        raise AssertionError("Confirmed shock did not create the expected entry.")

    position = PositionState(
        side=Side.LONG,
        entry_time=long_entry.execute_at,
        holding_candles=3,
    )
    normalized = evaluate_strategy(
        _decision_row(current_z=-0.4),
        position,
    )
    maximum = evaluate_strategy(
        _decision_row(current_z=-1.0),
        replace(position, holding_candles=32),
    )
    if (
        normalized.action is not Action.CLOSE_POSITION
        or normalized.reason != Reason.RESIDUAL_NORMALIZED.value
        or maximum.reason != Reason.MAXIMUM_HOLDING_TIME.value
    ):
        raise AssertionError("Mean-reversion exit rules are incorrect.")


def main() -> None:
    check_relationship_and_no_look_ahead()
    check_15m_confirmation()
    check_decisions()
    print("BTC/ETH Shock Mean Reversion checks passed:")
    print("Rolling beta and residual Z-score: True")
    print("Relationship inputs immutable: True")
    print("No look-ahead in hourly relationship: True")
    print("One causal 15m confirmation per shock: True")
    print("Long and Short entries: True")
    print("Normalization and maximum-holding exits: True")


if __name__ == "__main__":
    main()
