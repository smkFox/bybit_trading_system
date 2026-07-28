from datetime import datetime

import pandas as pd

from .database import read_candles
from .time_utils import datetime_to_milliseconds


CANDLE_COLUMNS = [
    "symbol",
    "timeframe",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]
NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]


def load_candles_dataframe(
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
) -> pd.DataFrame:
    """Load one UTC candle range into a chronological pandas DataFrame."""
    start_ms = datetime_to_milliseconds(start_time)
    end_ms = datetime_to_milliseconds(end_time)
    if start_ms > end_ms:
        raise ValueError("Start time must not be later than end time.")

    candles = read_candles(
        symbol=symbol.upper(),
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
    )
    dataframe = pd.DataFrame(candles, columns=CANDLE_COLUMNS)

    dataframe["symbol"] = dataframe["symbol"].astype("string")
    dataframe["timeframe"] = dataframe["timeframe"].astype("string")
    dataframe["open_time"] = pd.to_datetime(dataframe["open_time"], utc=True)
    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(dataframe[column]).astype("float64")

    return dataframe.sort_values("open_time").reset_index(drop=True)
