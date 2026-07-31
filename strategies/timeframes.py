import pandas as pd


REQUIRED_COLUMNS = (
    "symbol",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
)
ONE_HOUR = pd.Timedelta(hours=1)
FOUR_HOURS = pd.Timedelta(hours=4)


def aggregate_closed_1h_to_4h(candles_1h: pd.DataFrame) -> pd.DataFrame:
    """Build aligned, fully closed UTC 4h candles from consecutive 1h data."""
    if not isinstance(candles_1h, pd.DataFrame):
        raise TypeError("candles_1h must be a pandas DataFrame.")
    missing = [
        column for column in REQUIRED_COLUMNS if column not in candles_1h.columns
    ]
    if missing:
        raise ValueError(
            "candles_1h is missing required columns: " + ", ".join(missing)
        )
    if candles_1h.empty:
        raise ValueError("candles_1h must not be empty.")

    source = candles_1h.copy(deep=True)
    source = source.sort_values("open_time").reset_index(drop=True)
    source["open_time"] = pd.to_datetime(source["open_time"], utc=True)
    if source["symbol"].nunique() != 1:
        raise ValueError("candles_1h must contain exactly one symbol.")
    if source["open_time"].duplicated().any():
        raise ValueError("candles_1h contains duplicate timestamps.")
    if source.iloc[0]["open_time"].hour % 4 != 0:
        raise ValueError("The first 1h candle must start on a UTC 4h boundary.")
    if len(source) > 1:
        differences = source["open_time"].diff().iloc[1:]
        if not (differences == ONE_HOUR).all():
            raise ValueError("candles_1h must be consecutive without gaps.")

    indexed = source.set_index("open_time")
    grouped = indexed.resample(
        "4h",
        origin="epoch",
        label="left",
        closed="left",
    )
    aggregated = grouped.agg(
        symbol=("symbol", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        turnover=("turnover", "sum"),
        source_candles=("close", "size"),
    ).reset_index()

    incomplete = aggregated["source_candles"] != 4
    if incomplete.any():
        incomplete_indexes = aggregated.index[incomplete].tolist()
        allowed_final = [len(aggregated) - 1]
        if incomplete_indexes != allowed_final:
            raise ValueError("Only the final 4h candle may be incomplete.")
        aggregated = aggregated.loc[~incomplete].copy()
    if aggregated.empty:
        raise ValueError("No complete 4h candles are available.")

    aggregated.insert(1, "timeframe", "4h")
    aggregated["decision_time"] = aggregated["open_time"] + FOUR_HOURS
    return aggregated.drop(columns="source_candles").reset_index(drop=True)
