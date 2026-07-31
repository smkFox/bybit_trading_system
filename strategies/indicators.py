import math

import pandas as pd


REQUIRED_ATR_COLUMNS = ("high", "low", "close")


def _validate_period(period: int) -> None:
    if isinstance(period, bool) or not isinstance(period, int):
        raise TypeError("Indicator period must be an integer.")
    if period < 1:
        raise ValueError("Indicator period must be at least 1.")


def _validated_numeric_series(values: pd.Series, name: str) -> pd.Series:
    if not isinstance(values, pd.Series):
        raise TypeError(f"{name} must be a pandas Series.")
    if pd.api.types.is_bool_dtype(values.dtype):
        raise TypeError(f"{name} must contain numeric values, not booleans.")
    if not pd.api.types.is_numeric_dtype(values.dtype):
        raise TypeError(f"{name} must contain numeric values.")

    numeric = values.astype("float64", copy=False)
    if not numeric.map(math.isfinite).all():
        raise ValueError(f"{name} must contain only finite values.")
    return numeric


def calculate_atr(candles: pd.DataFrame, period: int) -> pd.Series:
    """Return Wilder ATR without changing the input candle DataFrame."""
    _validate_period(period)
    if not isinstance(candles, pd.DataFrame):
        raise TypeError("candles must be a pandas DataFrame.")

    missing_columns = [
        column for column in REQUIRED_ATR_COLUMNS if column not in candles.columns
    ]
    if missing_columns:
        raise ValueError(
            "candles is missing required columns: "
            + ", ".join(missing_columns)
        )

    high = _validated_numeric_series(candles["high"], "high")
    low = _validated_numeric_series(candles["low"], "low")
    close = _validated_numeric_series(candles["close"], "close")
    if (high < low).any():
        raise ValueError("Candle high must not be below candle low.")

    previous_close = close.shift(1)
    true_range = pd.concat(
        (
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)

    atr = pd.Series(
        float("nan"),
        index=candles.index,
        dtype="float64",
        name=f"atr_{period}",
    )
    if len(true_range) < period:
        return atr

    atr.iloc[period - 1] = true_range.iloc[:period].mean()
    for position in range(period, len(true_range)):
        atr.iloc[position] = (
            atr.iloc[position - 1] * (period - 1)
            + true_range.iloc[position]
        ) / period

    return atr
