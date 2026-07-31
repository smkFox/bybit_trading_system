from datetime import datetime, timezone

import pandas as pd
from pandas.testing import assert_frame_equal

from market_data.data_access import load_candles_dataframe
from strategies.timeframes import aggregate_closed_1h_to_4h


def _synthetic_candles(count: int) -> pd.DataFrame:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rows = []
    for index in range(count):
        price = 100.0 + index
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "open_time": start + pd.Timedelta(hours=index),
                "open": price,
                "high": price + 2.0,
                "low": price - 1.0,
                "close": price + 1.0,
                "volume": 10.0,
                "turnover": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def check_known_aggregation() -> None:
    source = _synthetic_candles(10)
    original = source.copy(deep=True)
    actual = aggregate_closed_1h_to_4h(source)
    assert_frame_equal(source, original)
    if len(actual) != 2:
        raise AssertionError("Incomplete final 4h candle was not excluded.")
    first = actual.iloc[0]
    if (
        first["open"] != 100.0
        or first["high"] != 105.0
        or first["low"] != 99.0
        or first["close"] != 104.0
        or first["volume"] != 40.0
        or first["turnover"] != 4000.0
    ):
        raise AssertionError("Known 4h OHLCV aggregation is incorrect.")
    if first["decision_time"] != first["open_time"] + pd.Timedelta(hours=4):
        raise AssertionError("4h decision time is incorrect.")


def check_gap_rejected() -> None:
    source = _synthetic_candles(8).drop(index=3).reset_index(drop=True)
    try:
        aggregate_closed_1h_to_4h(source)
    except ValueError:
        pass
    else:
        raise AssertionError("A gap in 1h input was accepted.")


def check_real_development_data() -> tuple[int, int]:
    source = load_candles_dataframe(
        "ETHUSDT",
        "1h",
        datetime(2023, 1, 1, tzinfo=timezone.utc),
        datetime(2023, 1, 7, 23, tzinfo=timezone.utc),
    )
    candles_4h = aggregate_closed_1h_to_4h(source)
    if len(candles_4h) != 42:
        raise AssertionError("Real 1h range did not produce 42 complete 4h candles.")
    if not (candles_4h["open_time"].dt.hour % 4 == 0).all():
        raise AssertionError("Real 4h candles are not UTC-aligned.")
    return len(source), len(candles_4h)


def main() -> None:
    check_known_aggregation()
    check_gap_rejected()
    source_count, result_count = check_real_development_data()
    print("Timeframe checks passed:")
    print("Known OHLCV aggregation: True")
    print("Incomplete final candle excluded: True")
    print("Input immutability: True")
    print("Gap rejection: True")
    print(f"Real development candles: 1h={source_count}, 4h={result_count}")


if __name__ == "__main__":
    main()
