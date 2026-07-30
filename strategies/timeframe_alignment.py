import pandas as pd

from strategies.indicators import calculate_atr, calculate_ema


SIGNAL_REQUIRED_COLUMNS = ("open_time", "high", "low", "close")
TREND_REQUIRED_COLUMNS = ("open_time", "close")
SIGNAL_DURATION = pd.Timedelta(minutes=15)
TREND_DURATION = pd.Timedelta(hours=1)


def _require_columns(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...],
    name: str,
) -> None:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            f"{name} is missing required columns: "
            + ", ".join(missing_columns)
        )


def align_timeframes(
    candles_15m: pd.DataFrame,
    candles_1h: pd.DataFrame,
    *,
    pullback_ema_period: int = 20,
    atr_period: int = 14,
    trend_fast_ema_period: int = 50,
    trend_slow_ema_period: int = 200,
) -> pd.DataFrame:
    """Attach the latest available closed 1h candle to every closed 15m candle."""
    _require_columns(candles_15m, SIGNAL_REQUIRED_COLUMNS, "candles_15m")
    _require_columns(candles_1h, TREND_REQUIRED_COLUMNS, "candles_1h")

    signal = candles_15m.copy(deep=True)
    trend = candles_1h.copy(deep=True)
    signal = signal.sort_values("open_time").reset_index(drop=True)
    trend = trend.sort_values("open_time").reset_index(drop=True)

    signal["decision_time"] = signal["open_time"] + SIGNAL_DURATION
    signal["signal_ema"] = calculate_ema(
        signal["close"],
        period=pullback_ema_period,
    )
    signal["signal_atr"] = calculate_atr(signal, period=atr_period)

    trend_fast_ema = calculate_ema(
        trend["close"],
        period=trend_fast_ema_period,
    )
    trend_slow_ema = calculate_ema(
        trend["close"],
        period=trend_slow_ema_period,
    )
    available_trend = pd.DataFrame(
        {
            "trend_open_time": trend["open_time"],
            "trend_available_time": trend["open_time"] + TREND_DURATION,
            "trend_close": trend["close"].astype("float64", copy=False),
            "trend_fast_ema": trend_fast_ema,
            "trend_slow_ema": trend_slow_ema,
        }
    )

    return pd.merge_asof(
        signal,
        available_trend,
        left_on="decision_time",
        right_on="trend_available_time",
        direction="backward",
        allow_exact_matches=True,
    )
