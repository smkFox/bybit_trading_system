import zlib
from datetime import datetime

import numpy as np
import pandas as pd

from market_data.data_access import (
    load_candles_dataframe,
    load_funding_rates_dataframe,
    load_open_interest_dataframe,
)
from research import analyze_sol_behavior as behavior


DATA_START = datetime.fromisoformat("2022-12-01T00:00:00+00:00")
ANALYSIS_END = datetime.fromisoformat("2024-12-31T23:45:00+00:00")
FAST_EMA_HOURS = 50
SLOW_EMA_HOURS = 200
HOLDING_CANDLES = 16
FUNDING_LOOKBACK_EVENTS = 90


def _prepare_data(
    candles: pd.DataFrame,
    open_interest: pd.DataFrame,
    funding_rates: pd.DataFrame,
) -> pd.DataFrame:
    data = behavior._prepare_data(candles)
    data["decision_time"] = data["open_time"] + pd.Timedelta(minutes=15)

    hourly = data.loc[
        data["open_time"].dt.minute.eq(45), ["open_time", "close"]
    ].copy()
    hourly["trend_available_time"] = hourly["open_time"] + pd.Timedelta(minutes=15)
    hourly["ema_fast"] = hourly["close"].ewm(
        span=FAST_EMA_HOURS,
        adjust=False,
        min_periods=FAST_EMA_HOURS,
    ).mean()
    hourly["ema_slow"] = hourly["close"].ewm(
        span=SLOW_EMA_HOURS,
        adjust=False,
        min_periods=SLOW_EMA_HOURS,
    ).mean()
    hourly["trend"] = pd.Series("SIDEWAYS", index=hourly.index, dtype="string")
    hourly.loc[
        (hourly["close"] > hourly["ema_fast"])
        & (hourly["ema_fast"] > hourly["ema_slow"]),
        "trend",
    ] = "UP"
    hourly.loc[
        (hourly["close"] < hourly["ema_fast"])
        & (hourly["ema_fast"] < hourly["ema_slow"]),
        "trend",
    ] = "DOWN"
    data = pd.merge_asof(
        data.sort_values("decision_time"),
        hourly[
            ["trend_available_time", "trend", "ema_fast", "ema_slow"]
        ].sort_values("trend_available_time"),
        left_on="decision_time",
        right_on="trend_available_time",
        direction="backward",
        allow_exact_matches=True,
    )

    oi = open_interest.copy(deep=True).sort_values("timestamp")
    oi["oi_available_time"] = oi["timestamp"] + pd.Timedelta(minutes=15)
    oi_by_time = oi.set_index("timestamp")["open_interest"]
    oi["previous_open_interest"] = oi_by_time.reindex(
        oi["timestamp"] - pd.Timedelta(minutes=15)
    ).to_numpy()
    data = pd.merge_asof(
        data.sort_values("decision_time"),
        oi[
            [
                "timestamp",
                "oi_available_time",
                "open_interest",
                "previous_open_interest",
            ]
        ].sort_values("oi_available_time"),
        left_on="decision_time",
        right_on="oi_available_time",
        direction="backward",
        allow_exact_matches=True,
    )
    data["oi_exact"] = data["timestamp"].eq(data["open_time"])
    data["oi_not_rising"] = (
        data["oi_exact"]
        & data["previous_open_interest"].notna()
        & (data["open_interest"] <= data["previous_open_interest"])
    )

    funding = funding_rates.copy(deep=True).sort_values("timestamp")
    funding["funding_low"] = (
        funding["funding_rate"]
        .rolling(FUNDING_LOOKBACK_EVENTS, min_periods=FUNDING_LOOKBACK_EVENTS)
        .quantile(0.10)
        .shift(1)
    )
    funding["funding_high"] = (
        funding["funding_rate"]
        .rolling(FUNDING_LOOKBACK_EVENTS, min_periods=FUNDING_LOOKBACK_EVENTS)
        .quantile(0.90)
        .shift(1)
    )
    funding = funding.rename(columns={"timestamp": "funding_timestamp"})
    data = pd.merge_asof(
        data.sort_values("decision_time"),
        funding[
            ["funding_timestamp", "funding_rate", "funding_low", "funding_high"]
        ].sort_values("funding_timestamp"),
        left_on="decision_time",
        right_on="funding_timestamp",
        direction="backward",
        allow_exact_matches=True,
    )
    data["funding_bucket"] = pd.Series("NORMAL", index=data.index, dtype="string")
    data.loc[data["funding_rate"] <= data["funding_low"], "funding_bucket"] = (
        "NEGATIVE_EXTREME"
    )
    data.loc[data["funding_rate"] >= data["funding_high"], "funding_bucket"] = (
        "POSITIVE_EXTREME"
    )
    data.loc[
        data[["funding_rate", "funding_low", "funding_high"]].isna().any(axis=1),
        "funding_bucket",
    ] = "UNAVAILABLE"

    countertrend_impulse = data["impulse_1_volume_low"]
    data["trend_pullback"] = countertrend_impulse & (
        (data["trend"].eq("UP") & data["direction"].eq(-1))
        | (data["trend"].eq("DOWN") & data["direction"].eq(1))
    )
    data["trend_side"] = pd.Series(0, index=data.index, dtype="int8")
    data.loc[data["trend_pullback"] & data["trend"].eq("UP"), "trend_side"] = 1
    data.loc[data["trend_pullback"] & data["trend"].eq("DOWN"), "trend_side"] = -1
    return data.sort_values("open_time").reset_index(drop=True)


def _event_indices(data: pd.DataFrame, year: int, use_oi_filter: bool) -> np.ndarray:
    final_signal_time = pd.Timestamp(f"{year}-12-31 19:45:00", tz="UTC")
    mask = (
        data["trend_pullback"]
        & data["open_time"].dt.year.eq(year)
        & data["open_time"].le(final_signal_time)
    )
    if use_oi_filter:
        mask &= data["oi_not_rising"]
    return behavior._decluster_indices(mask)


def _matched_random_indices(
    data: pd.DataFrame,
    event_indices: np.ndarray,
    label: str,
    year: int,
) -> np.ndarray:
    seed = zlib.crc32(f"{label}|{year}".encode("utf-8"))
    generator = np.random.default_rng(seed)
    final_signal_time = pd.Timestamp(f"{year}-12-31 19:45:00", tz="UTC")
    eligible = data.loc[
        data["open_time"].dt.year.eq(year)
        & data["open_time"].le(final_signal_time)
        & data["volatility_regime"].notna()
        & data["trend"].isin(["UP", "DOWN"])
    ]
    pools = {
        key: group.index.to_numpy(dtype="int64")
        for key, group in eligible.groupby(
            ["session", "volatility_regime", "trend"], observed=True
        )
    }
    selected = []
    for event_index in event_indices:
        event = data.iloc[event_index]
        candidates = pools.get(
            (event["session"], event["volatility_regime"], event["trend"]),
            np.asarray([], dtype="int64"),
        )
        if len(candidates) == 0:
            raise ValueError("No matched random candle is available.")
        selected.append(int(generator.choice(candidates)))
    return np.asarray(selected, dtype="int64")


def _profit_factor(values: np.ndarray) -> float:
    profit = values[values > 0].sum()
    loss = abs(values[values < 0].sum())
    return float(profit / loss) if loss > 0 else float("inf")


def analyze_variants(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant, use_oi_filter in (("BASE", False), ("OI_NOT_RISING", True)):
        for year in (2023, 2024):
            indices = _event_indices(data, year, use_oi_filter)
            random_indices = _matched_random_indices(data, indices, variant, year)
            values = behavior._returns_for_indices(
                data, indices, HOLDING_CANDLES, "REVERSAL"
            )
            random_values = behavior._returns_for_indices(
                data,
                random_indices,
                HOLDING_CANDLES,
                "REVERSAL",
                indices,
            )
            sides = data["trend_side"].iloc[indices].to_numpy(dtype="int8")
            for direction, side in (("ALL", None), ("LONG", 1), ("SHORT", -1)):
                selected = np.ones(len(values), dtype=bool) if side is None else sides == side
                selected_values = values[selected]
                selected_random = random_values[selected]
                metrics = behavior._metrics(selected_values)
                rows.append(
                    {
                        "variant": variant,
                        "year": year,
                        "direction": direction,
                        "events": len(selected_values),
                        **metrics,
                        "profit_factor": _profit_factor(selected_values),
                        "edge_vs_random": float(
                            selected_values.mean() - selected_random.mean()
                        ) if len(selected_values) else float("nan"),
                    }
                )
    return pd.DataFrame(rows)


def analyze_funding(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in (2023, 2024):
        indices = _event_indices(data, year, use_oi_filter=False)
        values = behavior._returns_for_indices(
            data, indices, HOLDING_CANDLES, "REVERSAL"
        )
        sides = data["trend_side"].iloc[indices].to_numpy(dtype="int8")
        buckets = data["funding_bucket"].iloc[indices].to_numpy()
        for direction, side in (("LONG", 1), ("SHORT", -1)):
            for bucket in ("NEGATIVE_EXTREME", "NORMAL", "POSITIVE_EXTREME"):
                selected = (sides == side) & (buckets == bucket)
                selected_values = values[selected]
                rows.append(
                    {
                        "year": year,
                        "direction": direction,
                        "funding_bucket": bucket,
                        "events": len(selected_values),
                        "mean_net": (
                            float(selected_values.mean())
                            if len(selected_values)
                            else float("nan")
                        ),
                    }
                )
    return pd.DataFrame(rows)


def analyze_paths(data: pd.DataFrame) -> pd.DataFrame:
    def path_values(
        price_indices: np.ndarray,
        side_source_indices: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        mfe_values = []
        mae_values = []
        sides = data["trend_side"].iloc[side_source_indices].to_numpy(dtype="int8")
        for price_index, side in zip(price_indices, sides, strict=True):
            entry = float(data.iloc[price_index + 1]["open"])
            future = data.iloc[
                price_index + 1 : price_index + HOLDING_CANDLES + 1
            ]
            if side > 0:
                favorable = (future["high"].to_numpy() / entry - 1) * 100
                adverse = (1 - future["low"].to_numpy() / entry) * 100
            else:
                favorable = (1 - future["low"].to_numpy() / entry) * 100
                adverse = (future["high"].to_numpy() / entry - 1) * 100
            mfe_values.append(max(0.0, float(favorable.max())))
            mae_values.append(max(0.0, float(adverse.max())))
        return np.asarray(mfe_values), np.asarray(mae_values)

    rows = []
    for variant, use_oi_filter in (("BASE", False), ("OI_NOT_RISING", True)):
        for year in (2023, 2024):
            indices = _event_indices(data, year, use_oi_filter)
            random_indices = _matched_random_indices(
                data, indices, f"path|{variant}", year
            )
            sides = data["trend_side"].iloc[indices].to_numpy(dtype="int8")
            mfe, mae = path_values(indices, indices)
            random_mfe, _ = path_values(random_indices, indices)
            for direction, side in (("ALL", None), ("LONG", 1), ("SHORT", -1)):
                selected = np.ones(len(indices), dtype=bool) if side is None else sides == side
                rows.append(
                    {
                        "variant": variant,
                        "year": year,
                        "direction": direction,
                        "events": int(selected.sum()),
                        "median_mfe": float(np.median(mfe[selected])),
                        "median_mae": float(np.median(mae[selected])),
                        "random_median_mfe": float(
                            np.median(random_mfe[selected])
                        ),
                        "mfe_edge_vs_random": float(
                            np.median(mfe[selected])
                            - np.median(random_mfe[selected])
                        ),
                        "mfe_above_cost_percent": float(
                            (mfe[selected] > behavior.ROUND_TRIP_COST_PERCENT).mean()
                            * 100
                        ),
                    }
                )
    return pd.DataFrame(rows)


def trend_distribution(data: pd.DataFrame) -> pd.DataFrame:
    analysis = data.loc[data["open_time"].dt.year.isin([2023, 2024])]
    counts = (
        analysis.groupby([analysis["open_time"].dt.year, "trend"], observed=True)
        .size()
        .rename("candles")
        .reset_index()
        .rename(columns={"open_time": "year"})
    )
    counts["percent"] = counts["candles"] / counts.groupby("year")[
        "candles"
    ].transform("sum") * 100
    return counts


def main() -> None:
    candles = load_candles_dataframe("SOLUSDT", "15m", DATA_START, ANALYSIS_END)
    open_interest = load_open_interest_dataframe(
        "SOLUSDT", "15m", DATA_START, ANALYSIS_END
    )
    funding = load_funding_rates_dataframe(
        "SOLUSDT", DATA_START, ANALYSIS_END
    )
    data = _prepare_data(candles, open_interest, funding)
    if len(open_interest) != len(candles) or not data["oi_exact"].all():
        raise ValueError("SOL Open Interest does not exactly cover all candles.")

    print("SOL Trend-Aligned Low-Volume Pullback analysis")
    print(
        f"Data: candles={len(candles)}, OI={len(open_interest)}, "
        f"funding={len(funding)}, gaps=0"
    )
    print(
        "Fixed rules: 1h EMA50/EMA200 trend; counter-trend 15m body >= 1 ATR; "
        "volume < prior20 median; next-open entry; fixed 4h exit; 0.220% cost"
    )
    print("\nTrend distribution")
    print(trend_distribution(data).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nBase versus one OI filter")
    print(analyze_variants(data).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nFour-hour path diagnostics")
    print(analyze_paths(data).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nFunding diagnostic only")
    print(analyze_funding(data).to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
