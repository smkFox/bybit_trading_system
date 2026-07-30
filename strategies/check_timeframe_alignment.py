from datetime import datetime, timezone

import pandas as pd
from pandas.testing import assert_frame_equal

from market_data.data_access import load_candles_dataframe
from strategies.timeframe_alignment import align_timeframes


def _utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def check_hour_boundary() -> None:
    candles_15m = pd.DataFrame(
        {
            "open_time": pd.to_datetime(
                [
                    "2023-01-01 10:00:00+00:00",
                    "2023-01-01 10:15:00+00:00",
                    "2023-01-01 10:30:00+00:00",
                    "2023-01-01 10:45:00+00:00",
                ],
                utc=True,
            ),
            "open": [100.0, 101.0, 102.0, 103.0],
            "high": [102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0],
            "close": [101.0, 102.0, 103.0, 104.0],
        }
    )
    candles_1h = pd.DataFrame(
        {
            "open_time": pd.to_datetime(
                [
                    "2023-01-01 09:00:00+00:00",
                    "2023-01-01 10:00:00+00:00",
                ],
                utc=True,
            ),
            "close": [90.0, 110.0],
        }
    )
    original_15m = candles_15m.copy(deep=True)
    original_1h = candles_1h.copy(deep=True)

    aligned = align_timeframes(candles_15m, candles_1h)

    expected_trend_times = [
        _utc("2023-01-01 09:00:00"),
        _utc("2023-01-01 09:00:00"),
        _utc("2023-01-01 09:00:00"),
        _utc("2023-01-01 10:00:00"),
    ]
    if aligned["trend_open_time"].tolist() != expected_trend_times:
        raise AssertionError(
            "A 15m decision was matched to the wrong closed 1h candle."
        )

    at_1045 = aligned.loc[
        aligned["decision_time"] == _utc("2023-01-01 10:45:00")
    ].iloc[0]
    if at_1045["trend_open_time"] != _utc("2023-01-01 09:00:00"):
        raise AssertionError("The 10:45 decision used the incomplete 10:00 hour.")

    at_1100 = aligned.loc[
        aligned["decision_time"] == _utc("2023-01-01 11:00:00")
    ].iloc[0]
    if at_1100["trend_open_time"] != _utc("2023-01-01 10:00:00"):
        raise AssertionError("The 11:00 decision did not use the newly closed hour.")

    matched = aligned.dropna(subset=["trend_available_time"])
    if not (matched["trend_available_time"] <= matched["decision_time"]).all():
        raise AssertionError("Alignment used a 1h candle from the future.")

    if len(aligned) != len(candles_15m):
        raise AssertionError("Alignment changed the number of 15m rows.")

    assert_frame_equal(candles_15m, original_15m)
    assert_frame_equal(candles_1h, original_1h)


def check_real_development_data() -> tuple[int, int]:
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 15, tzinfo=timezone.utc)
    candles_15m = load_candles_dataframe("ETHUSDT", "15m", start, end)
    candles_1h = load_candles_dataframe("ETHUSDT", "1h", start, end)

    aligned = align_timeframes(candles_15m, candles_1h)
    if len(aligned) != len(candles_15m):
        raise AssertionError("Real-data alignment changed the 15m row count.")
    if not aligned["open_time"].is_monotonic_increasing:
        raise AssertionError("Real-data alignment changed chronological order.")

    matched = aligned.dropna(subset=["trend_available_time"])
    if matched.empty:
        raise AssertionError("No real 15m rows received an available 1h candle.")
    if not (matched["trend_available_time"] <= matched["decision_time"]).all():
        raise AssertionError("Real-data alignment used a future 1h candle.")
    if aligned["trend_ema_200"].notna().sum() == 0:
        raise AssertionError("Real-data alignment produced no warmed-up EMA 200.")

    return len(aligned), len(matched)


def main() -> None:
    check_hour_boundary()
    aligned_count, matched_count = check_real_development_data()

    print("Timeframe alignment checks passed:")
    print("10:45 uses the previously closed hour: True")
    print("11:00 uses the newly closed hour: True")
    print("Future 1h candles used: False")
    print("15m row count preserved: True")
    print(f"Real 2023 rows: aligned={aligned_count}, matched={matched_count}")


if __name__ == "__main__":
    main()
