from datetime import datetime, timezone

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from market_data.data_access import load_candles_dataframe
from strategies.indicators import calculate_atr, calculate_ema


def check_known_ema_values() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="close")
    expected = pd.Series(
        [float("nan"), float("nan"), 2.25, 3.125, 4.0625],
        name="ema_3",
    )

    actual = calculate_ema(close, period=3)
    assert_series_equal(actual, expected, check_exact=False, rtol=1e-12)


def check_known_atr_values() -> None:
    candles = pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 15.0, 14.0],
            "low": [8.0, 9.0, 8.0, 11.0, 10.0],
            "close": [9.0, 10.0, 10.0, 12.0, 11.0],
        }
    )
    expected = pd.Series(
        [
            float("nan"),
            float("nan"),
            8.0 / 3.0,
            31.0 / 9.0,
            98.0 / 27.0,
        ],
        name="atr_3",
    )

    actual = calculate_atr(candles, period=3)
    assert_series_equal(actual, expected, check_exact=False, rtol=1e-12)


def check_warm_up_and_input_immutability() -> None:
    close = pd.Series([10.0, 11.0, 12.0], name="close")
    short_ema = calculate_ema(close, period=5)
    if not short_ema.isna().all():
        raise AssertionError("EMA returned a value before warm-up completed.")

    candles = pd.DataFrame(
        {
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.0, 11.0, 12.0],
        }
    )
    original = candles.copy(deep=True)
    short_atr = calculate_atr(candles, period=5)
    if not short_atr.isna().all():
        raise AssertionError("ATR returned a value before warm-up completed.")
    assert_frame_equal(candles, original)


def check_no_look_ahead() -> None:
    candles = pd.DataFrame(
        {
            "high": [float(value + 2) for value in range(1, 21)],
            "low": [float(value) for value in range(1, 21)],
            "close": [float(value + 1) for value in range(1, 21)],
        }
    )
    changed_future = candles.copy(deep=True)
    changed_future.loc[17:, ["high", "low", "close"]] += 1000.0

    original_ema = calculate_ema(candles["close"], period=3)
    changed_ema = calculate_ema(changed_future["close"], period=3)
    assert_series_equal(original_ema.iloc[:17], changed_ema.iloc[:17])

    original_atr = calculate_atr(candles, period=3)
    changed_atr = calculate_atr(changed_future, period=3)
    assert_series_equal(original_atr.iloc[:17], changed_atr.iloc[:17])


def check_invalid_inputs() -> None:
    try:
        calculate_ema(pd.Series([1.0, 2.0]), period=0)
    except ValueError:
        pass
    else:
        raise AssertionError("EMA accepted a non-positive period.")

    try:
        calculate_atr(pd.DataFrame({"high": [1.0]}), period=14)
    except ValueError:
        pass
    else:
        raise AssertionError("ATR accepted missing candle columns.")

    invalid_candle = pd.DataFrame(
        {"high": [1.0], "low": [2.0], "close": [1.5]}
    )
    try:
        calculate_atr(invalid_candle, period=1)
    except ValueError:
        pass
    else:
        raise AssertionError("ATR accepted a candle with high below low.")


def check_real_development_data() -> tuple[int, int]:
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 15, tzinfo=timezone.utc)
    candles_15m = load_candles_dataframe("ETHUSDT", "15m", start, end)
    candles_1h = load_candles_dataframe("ETHUSDT", "1h", start, end)

    if len(candles_15m) < 20 or len(candles_1h) < 200:
        raise AssertionError("Stored development range is too short for warm-up.")

    ema_20 = calculate_ema(candles_15m["close"], period=20)
    atr_14 = calculate_atr(candles_15m, period=14)
    ema_50 = calculate_ema(candles_1h["close"], period=50)
    ema_200 = calculate_ema(candles_1h["close"], period=200)

    expected_first_positions = (
        (ema_20, 19),
        (atr_14, 13),
        (ema_50, 49),
        (ema_200, 199),
    )
    for indicator, expected_position in expected_first_positions:
        if indicator.first_valid_index() != expected_position:
            raise AssertionError(
                f"{indicator.name} warm-up ended at "
                f"{indicator.first_valid_index()}, expected {expected_position}."
            )

    assert_series_equal(ema_20, calculate_ema(candles_15m["close"], 20))
    assert_series_equal(atr_14, calculate_atr(candles_15m, 14))
    assert_series_equal(ema_50, calculate_ema(candles_1h["close"], 50))
    assert_series_equal(ema_200, calculate_ema(candles_1h["close"], 200))
    return len(candles_15m), len(candles_1h)


def main() -> None:
    check_known_ema_values()
    check_known_atr_values()
    check_warm_up_and_input_immutability()
    check_no_look_ahead()
    check_invalid_inputs()
    count_15m, count_1h = check_real_development_data()

    print("Indicator checks passed:")
    print("Known EMA values: True")
    print("Known Wilder ATR values: True")
    print("Warm-up behavior: True")
    print("Input DataFrame unchanged: True")
    print("No look-ahead: True")
    print("Invalid input handling: True")
    print(f"Real 2023 development candles: 15m={count_15m}, 1h={count_1h}")


if __name__ == "__main__":
    main()
