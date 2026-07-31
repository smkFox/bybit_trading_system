import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from strategies.donchian_breakout.strategy import (
    Reason,
    evaluate_donchian_breakout,
    prepare_market_data,
)
from strategies.models import Action, PositionState, Side


def _row(
    *,
    close: float,
    entry_high: float = 120.0,
    entry_low: float = 80.0,
    exit_high: float = 110.0,
    exit_low: float = 90.0,
    atr: float = 5.0,
) -> pd.Series:
    open_time = pd.Timestamp("2023-02-01 08:00:00", tz="UTC")
    return pd.Series(
        {
            "symbol": "ETHUSDT",
            "timeframe": "4h",
            "open_time": open_time,
            "open": 100.0,
            "high": max(121.0, close),
            "low": min(79.0, close),
            "close": close,
            "decision_time": open_time + pd.Timedelta(hours=4),
            "entry_channel_high": entry_high,
            "entry_channel_low": entry_low,
            "exit_channel_high": exit_high,
            "exit_channel_low": exit_low,
            "signal_atr": atr,
        }
    )


def check_decisions() -> None:
    long_decision = evaluate_donchian_breakout(_row(close=121.0))
    repeated = evaluate_donchian_breakout(_row(close=121.0))
    if (
        long_decision.action is not Action.OPEN_POSITION
        or long_decision.side is not Side.LONG
        or long_decision.reason != Reason.LONG_BREAKOUT.value
        or long_decision.stop_distance != 10.0
        or long_decision.take_profit_r_multiple is not None
    ):
        raise AssertionError("Expected Long breakout was not produced.")
    if long_decision.decision_id != repeated.decision_id:
        raise AssertionError("Decision ID is not deterministic.")

    short_decision = evaluate_donchian_breakout(_row(close=79.0))
    if (
        short_decision.action is not Action.OPEN_POSITION
        or short_decision.side is not Side.SHORT
        or short_decision.reason != Reason.SHORT_BREAKOUT.value
    ):
        raise AssertionError("Expected Short breakout was not produced.")

    position = PositionState(
        side=Side.LONG,
        entry_time=long_decision.execute_at,
        holding_candles=3,
    )
    hold = evaluate_donchian_breakout(_row(close=100.0), position)
    close = evaluate_donchian_breakout(_row(close=89.0), position)
    if hold.action is not Action.HOLD_POSITION:
        raise AssertionError("Long position was not held inside exit channel.")
    if (
        close.action is not Action.CLOSE_POSITION
        or close.reason != Reason.LONG_EXIT_CHANNEL.value
    ):
        raise AssertionError("Long exit-channel decision was not produced.")

    warmup = evaluate_donchian_breakout(
        _row(close=100.0, entry_high=float("nan"))
    )
    if (
        warmup.action is not Action.NO_ACTION
        or warmup.reason != Reason.INSUFFICIENT_HISTORY.value
    ):
        raise AssertionError("Warm-up did not produce no action.")


def check_shifted_channels_and_no_look_ahead() -> None:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rows = []
    for index in range(30):
        price = 100.0 + index
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "open_time": start + pd.Timedelta(hours=4 * index),
                "open": price,
                "high": price + 2.0,
                "low": price - 2.0,
                "close": price + 1.0,
                "decision_time": (
                    start + pd.Timedelta(hours=4 * (index + 1))
                ),
            }
        )
    candles = pd.DataFrame(rows)
    original = candles.copy(deep=True)
    prepared = prepare_market_data(candles)
    assert_frame_equal(candles, original)
    expected_entry_high = candles.loc[:19, "high"].max()
    if prepared.loc[20, "entry_channel_high"] != expected_entry_high:
        raise AssertionError("Current candle leaked into the entry channel.")

    changed_future = candles.copy(deep=True)
    changed_future.loc[25:, ["high", "low", "close"]] += 1000.0
    changed = prepare_market_data(changed_future)
    columns = [
        "entry_channel_high",
        "entry_channel_low",
        "exit_channel_high",
        "exit_channel_low",
        "signal_atr",
    ]
    for column in columns:
        assert_series_equal(
            prepared.loc[:24, column],
            changed.loc[:24, column],
        )


def main() -> None:
    check_decisions()
    check_shifted_channels_and_no_look_ahead()
    print("Donchian Breakout checks passed:")
    print("Long and Short entry decisions: True")
    print("Hold and channel-exit decisions: True")
    print("No fixed take profit: True")
    print("Deterministic decision ID: True")
    print("Warm-up behavior: True")
    print("Shifted channels: True")
    print("No look-ahead: True")
    print("Input immutability: True")


if __name__ == "__main__":
    main()
