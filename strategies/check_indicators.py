from datetime import datetime, timezone

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from market_data.data_access import load_candles_dataframe
from strategies.indicators import calculate_atr


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
    assert_series_equal(
        calculate_atr(candles, period=3),
        expected,
        check_exact=False,
        rtol=1e-12,
    )


def check_warm_up_and_input_immutability() -> None:
    candles = pd.DataFrame(
        {
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.0, 11.0, 12.0],
        }
    )
    original = candles.copy(deep=True)
    if not calculate_atr(candles, period=5).isna().all():
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
    original = calculate_atr(candles, period=3)
    changed = calculate_atr(changed_future, period=3)
    assert_series_equal(original.iloc[:17], changed.iloc[:17])


def check_invalid_inputs() -> None:
    try:
        calculate_atr(pd.DataFrame({"high": [1.0]}), period=14)
    except ValueError:
        pass
    else:
        raise AssertionError("ATR accepted missing candle columns.")

    invalid = pd.DataFrame(
        {"high": [1.0], "low": [2.0], "close": [1.5]}
    )
    try:
        calculate_atr(invalid, period=1)
    except ValueError:
        pass
    else:
        raise AssertionError("ATR accepted high below low.")


def check_real_development_data() -> int:
    candles = load_candles_dataframe(
        "ETHUSDT",
        "1h",
        datetime(2023, 1, 1, tzinfo=timezone.utc),
        datetime(2023, 1, 15, tzinfo=timezone.utc),
    )
    atr = calculate_atr(candles, 14)
    if atr.first_valid_index() != 13:
        raise AssertionError("Real-data ATR warm-up ended unexpectedly.")
    assert_series_equal(atr, calculate_atr(candles, 14))
    return len(candles)


def main() -> None:
    check_known_atr_values()
    check_warm_up_and_input_immutability()
    check_no_look_ahead()
    check_invalid_inputs()
    real_count = check_real_development_data()
    print("Indicator checks passed:")
    print("Known Wilder ATR values: True")
    print("Warm-up behavior: True")
    print("Input DataFrame unchanged: True")
    print("No look-ahead: True")
    print("Invalid input handling: True")
    print(f"Real 2023 1h candles: {real_count}")


if __name__ == "__main__":
    main()
