import zlib
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from market_data.data_access import load_candles_dataframe
from strategies.indicators import calculate_atr


DATA_START = datetime.fromisoformat("2022-12-01T00:00:00+00:00")
ANALYSIS_START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
ANALYSIS_END = datetime.fromisoformat("2024-12-31T23:45:00+00:00")
HORIZONS = {"15m": 1, "30m": 2, "1h": 4, "2h": 8, "4h": 16, "8h": 32}
ROUND_TRIP_COST_PERCENT = 0.220
EVENT_COOLDOWN_CANDLES = 32
MINIMUM_EVENTS_PER_YEAR = 100
TRAILING_ATR_MULTIPLIERS = (1.0, 1.5, 2.0)
CANDIDATE_HORIZON_CANDLES = 16


@dataclass(frozen=True)
class EventDefinition:
    name: str
    mask_column: str


def _prepare_data(candles: pd.DataFrame) -> pd.DataFrame:
    data = candles.copy(deep=True).sort_values("open_time").reset_index(drop=True)
    if data.empty or len(data) < 33:
        raise ValueError("SOL analysis requires consecutive 15m candles.")
    if (data["open_time"].diff().iloc[1:] != pd.Timedelta(minutes=15)).any():
        raise ValueError("SOL candles contain gaps.")

    data["atr"] = calculate_atr(data, 14)
    data["atr_percent"] = data["atr"] / data["close"] * 100
    data["body"] = data["close"] - data["open"]
    data["direction"] = np.sign(data["body"]).astype("int8")
    data["body_atr"] = data["body"].abs() / data["atr"]
    data["prior_volume_median"] = data["volume"].rolling(20).median().shift(1)
    data["volume_ratio"] = data["volume"] / data["prior_volume_median"]

    volatility_window = 30 * 24 * 4
    data["volatility_low"] = (
        data["atr_percent"]
        .rolling(volatility_window, min_periods=volatility_window)
        .quantile(1 / 3)
        .shift(1)
    )
    data["volatility_high"] = (
        data["atr_percent"]
        .rolling(volatility_window, min_periods=volatility_window)
        .quantile(2 / 3)
        .shift(1)
    )
    data["volatility_regime"] = pd.Series(pd.NA, index=data.index, dtype="string")
    data.loc[data["atr_percent"] <= data["volatility_low"], "volatility_regime"] = "LOW"
    data.loc[
        (data["atr_percent"] > data["volatility_low"])
        & (data["atr_percent"] < data["volatility_high"]),
        "volatility_regime",
    ] = "NORMAL"
    data.loc[data["atr_percent"] >= data["volatility_high"], "volatility_regime"] = "HIGH"
    data["session"] = (data["open_time"].dt.hour // 8 * 8).astype("int8")

    same_direction = data["direction"].eq(data["direction"].shift(1)) & data["direction"].ne(0)
    groups = (~same_direction).cumsum()
    data["direction_run"] = data.groupby(groups).cumcount() + 1
    data.loc[data["direction"] == 0, "direction_run"] = 0

    for threshold in (0.5, 1.0, 1.5, 2.0):
        data[f"impulse_{threshold:g}"] = data["body_atr"] >= threshold
    base = data["impulse_1"]
    data["impulse_1_volume_low"] = base & (data["volume_ratio"] < 1.0)
    data["impulse_1_volume_normal"] = base & data["volume_ratio"].between(
        1.0, 1.5, inclusive="left"
    )
    data["impulse_1_volume_high"] = base & (data["volume_ratio"] >= 1.5)
    for regime in ("LOW", "NORMAL", "HIGH"):
        data[f"impulse_1_regime_{regime.lower()}"] = base & (
            data["volatility_regime"] == regime
        )
    for session in (0, 8, 16):
        data[f"impulse_1_session_{session:02d}"] = base & (data["session"] == session)
    for run in (2, 3, 4):
        data[f"streak_{run}"] = data["direction_run"] == run
    return data


def _event_definitions() -> tuple[EventDefinition, ...]:
    names = (
        "impulse_0.5",
        "impulse_1",
        "impulse_1.5",
        "impulse_2",
        "impulse_1_volume_low",
        "impulse_1_volume_normal",
        "impulse_1_volume_high",
        "impulse_1_regime_low",
        "impulse_1_regime_normal",
        "impulse_1_regime_high",
        "impulse_1_session_00",
        "impulse_1_session_08",
        "impulse_1_session_16",
        "streak_2",
        "streak_3",
        "streak_4",
    )
    return tuple(EventDefinition(name, name) for name in names)


def _decluster_indices(mask: pd.Series) -> np.ndarray:
    selected = []
    next_allowed = 0
    for position in np.flatnonzero(mask.to_numpy(dtype=bool)):
        if position >= next_allowed:
            selected.append(position)
            next_allowed = position + EVENT_COOLDOWN_CANDLES + 1
    return np.asarray(selected, dtype="int64")


def _eligible_events(
    data: pd.DataFrame,
    definition: EventDefinition,
    year: int,
) -> np.ndarray:
    final_signal_time = pd.Timestamp(f"{year}-12-31 15:45:00", tz="UTC")
    mask = (
        data[definition.mask_column].fillna(False)
        & data["direction"].ne(0)
        & data["open_time"].dt.year.eq(year)
        & data["open_time"].le(final_signal_time)
    )
    return _decluster_indices(mask)


def _returns_for_indices(
    data: pd.DataFrame,
    price_indices: np.ndarray,
    horizon: int,
    trade_style: str,
    side_source_indices: np.ndarray | None = None,
) -> np.ndarray:
    if side_source_indices is None:
        side_source_indices = price_indices
    entry = data["open"].iloc[price_indices + 1].to_numpy(dtype="float64")
    exit_price = data["close"].iloc[price_indices + horizon].to_numpy(dtype="float64")
    event_direction = data["direction"].iloc[side_source_indices].to_numpy(
        dtype="float64"
    )
    side = event_direction if trade_style == "CONTINUATION" else -event_direction
    gross = side * (exit_price / entry - 1) * 100
    return gross - ROUND_TRIP_COST_PERCENT


def _matched_random_indices(
    data: pd.DataFrame,
    event_indices: np.ndarray,
    label: str,
    year: int,
) -> np.ndarray:
    seed = zlib.crc32(f"{label}|{year}".encode("utf-8"))
    generator = np.random.default_rng(seed)
    selected = []
    final_signal_time = pd.Timestamp(f"{year}-12-31 15:45:00", tz="UTC")
    eligible = data.loc[
        data["open_time"].dt.year.eq(year)
        & data["open_time"].le(final_signal_time)
        & data["volatility_regime"].notna()
    ]
    pools = {
        key: group.index.to_numpy(dtype="int64")
        for key, group in eligible.groupby(
            ["session", "volatility_regime"], observed=True
        )
    }
    for event_index in event_indices:
        event = data.iloc[event_index]
        candidates = pools.get(
            (event["session"], event["volatility_regime"]),
            np.asarray([], dtype="int64"),
        )
        if len(candidates) == 0:
            raise ValueError("No matched random candle is available.")
        selected.append(int(generator.choice(candidates)))
    return np.asarray(selected, dtype="int64")


def _metrics(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {
            "mean_net": float("nan"),
            "median_net": float("nan"),
            "win_rate": float("nan"),
            "trimmed_mean_net": float("nan"),
        }
    upper = np.quantile(values, 0.99)
    trimmed = values[values <= upper]
    return {
        "mean_net": float(values.mean()),
        "median_net": float(np.median(values)),
        "win_rate": float((values > 0).mean() * 100),
        "trimmed_mean_net": float(trimmed.mean()),
    }


def analyze_events(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for definition in _event_definitions():
        yearly_indices = {
            year: _eligible_events(data, definition, year)
            for year in (2023, 2024)
        }
        random_indices = {
            year: _matched_random_indices(
                data, indices, definition.name, year
            )
            for year, indices in yearly_indices.items()
        }
        for trade_style in ("CONTINUATION", "REVERSAL"):
            discovery = []
            for horizon_name, horizon in HORIZONS.items():
                values = _returns_for_indices(
                    data, yearly_indices[2023], horizon, trade_style
                )
                discovery.append((float(values.mean()), horizon_name, horizon))
            _, selected_horizon_name, selected_horizon = max(discovery)
            for year in (2023, 2024):
                values = _returns_for_indices(
                    data,
                    yearly_indices[year],
                    selected_horizon,
                    trade_style,
                )
                random_values = _returns_for_indices(
                    data,
                    random_indices[year],
                    selected_horizon,
                    trade_style,
                    yearly_indices[year],
                )
                metrics = _metrics(values)
                rows.append(
                    {
                        "event": definition.name,
                        "style": trade_style,
                        "selected_horizon": selected_horizon_name,
                        "year": year,
                        "events": len(values),
                        **metrics,
                        "random_mean_net": float(random_values.mean()),
                        "edge_vs_random": float(
                            values.mean() - random_values.mean()
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _confirmation_summary(results: pd.DataFrame) -> pd.DataFrame:
    discovery = results.loc[results["year"] == 2023].set_index(["event", "style"])
    confirmation = results.loc[results["year"] == 2024].set_index(["event", "style"])
    rows = []
    for key, first in discovery.iterrows():
        second = confirmation.loc[key]
        rows.append(
            {
                "event": key[0],
                "style": key[1],
                "horizon": first["selected_horizon"],
                "n_2023": int(first["events"]),
                "mean_2023": first["mean_net"],
                "trim_2023": first["trimmed_mean_net"],
                "edge_2023": first["edge_vs_random"],
                "n_2024": int(second["events"]),
                "mean_2024": second["mean_net"],
                "trim_2024": second["trimmed_mean_net"],
                "edge_2024": second["edge_vs_random"],
                "passes_basic_gate": (
                    first["events"] >= MINIMUM_EVENTS_PER_YEAR
                    and second["events"] >= MINIMUM_EVENTS_PER_YEAR
                    and first["mean_net"] > 0
                    and second["mean_net"] > 0
                    and first["trimmed_mean_net"] > 0
                    and second["trimmed_mean_net"] > 0
                    and first["edge_vs_random"] > 0
                    and second["edge_vs_random"] > 0
                ),
            }
        )
    summary = pd.DataFrame(rows)
    return summary.sort_values(
        ["passes_basic_gate", "mean_2024", "mean_2023"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def _excursions(
    data: pd.DataFrame,
    price_indices: np.ndarray,
    side_source_indices: np.ndarray,
    trade_style: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mfe_values = []
    mae_values = []
    giveback_values = []
    time_to_mfe_values = []
    event_direction = data["direction"].iloc[side_source_indices].to_numpy()
    sides = event_direction if trade_style == "CONTINUATION" else -event_direction
    for price_index, side in zip(price_indices, sides, strict=True):
        entry = float(data.iloc[price_index + 1]["open"])
        future = data.iloc[price_index + 1 : price_index + 33]
        if side > 0:
            favorable_path = (future["high"].to_numpy() / entry - 1) * 100
            adverse_path = (1 - future["low"].to_numpy() / entry) * 100
            final_gross = (float(future.iloc[-1]["close"]) / entry - 1) * 100
        else:
            favorable_path = (1 - future["low"].to_numpy() / entry) * 100
            adverse_path = (future["high"].to_numpy() / entry - 1) * 100
            final_gross = (1 - float(future.iloc[-1]["close"]) / entry) * 100
        maximum_favorable = max(0.0, float(favorable_path.max()))
        maximum_adverse = max(0.0, float(adverse_path.max()))
        mfe_values.append(maximum_favorable)
        mae_values.append(maximum_adverse)
        giveback_values.append(maximum_favorable - final_gross)
        time_to_mfe_values.append(int(np.argmax(favorable_path)) + 1)
    return (
        np.asarray(mfe_values),
        np.asarray(mae_values),
        np.asarray(giveback_values),
        np.asarray(time_to_mfe_values),
    )


def analyze_excursions(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for definition in _event_definitions():
        for year in (2023, 2024):
            indices = _eligible_events(data, definition, year)
            random_indices = _matched_random_indices(
                data, indices, f"excursion|{definition.name}", year
            )
            for trade_style in ("CONTINUATION", "REVERSAL"):
                mfe, mae, giveback, time_to_mfe = _excursions(
                    data, indices, indices, trade_style
                )
                random_mfe, _, _, _ = _excursions(
                    data, random_indices, indices, trade_style
                )
                rows.append(
                    {
                        "event": definition.name,
                        "style": trade_style,
                        "year": year,
                        "events": len(indices),
                        "median_mfe": float(np.median(mfe)),
                        "median_mae": float(np.median(mae)),
                        "median_giveback": float(np.median(giveback)),
                        "median_time_to_mfe_candles": float(
                            np.median(time_to_mfe)
                        ),
                        "random_median_mfe": float(np.median(random_mfe)),
                        "mfe_edge_vs_random": float(
                            np.median(mfe) - np.median(random_mfe)
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _excursion_confirmation_summary(results: pd.DataFrame) -> pd.DataFrame:
    first = results.loc[results["year"] == 2023].set_index(["event", "style"])
    second = results.loc[results["year"] == 2024].set_index(["event", "style"])
    rows = []
    for key, discovery in first.iterrows():
        confirmation = second.loc[key]
        rows.append(
            {
                "event": key[0],
                "style": key[1],
                "mfe_2023": discovery["median_mfe"],
                "mae_2023": discovery["median_mae"],
                "giveback_2023": discovery["median_giveback"],
                "mfe_edge_2023": discovery["mfe_edge_vs_random"],
                "mfe_2024": confirmation["median_mfe"],
                "mae_2024": confirmation["median_mae"],
                "giveback_2024": confirmation["median_giveback"],
                "mfe_edge_2024": confirmation["mfe_edge_vs_random"],
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["mfe_edge_2024", "mfe_edge_2023"], ascending=False
    ).reset_index(drop=True)


def _trailing_returns(
    data: pd.DataFrame,
    indices: np.ndarray,
    atr_multiplier: float,
) -> np.ndarray:
    values = []
    for signal_index in indices:
        signal = data.iloc[signal_index]
        side = -int(signal["direction"])
        entry = float(data.iloc[signal_index + 1]["open"])
        distance = float(signal["atr"]) * atr_multiplier
        stop = entry - side * distance
        favorable_extreme = entry
        activated = False
        exit_price = float(data.iloc[signal_index + 32]["close"])
        for candle_index in range(signal_index + 1, signal_index + 33):
            candle = data.iloc[candle_index]
            candle_open = float(candle["open"])
            candle_high = float(candle["high"])
            candle_low = float(candle["low"])
            if side > 0:
                if candle_open <= stop:
                    exit_price = candle_open
                    break
                if candle_low <= stop:
                    exit_price = stop
                    break
                favorable_extreme = max(favorable_extreme, candle_high)
                if favorable_extreme - entry >= distance:
                    activated = True
                if activated:
                    stop = max(stop, favorable_extreme - distance)
            else:
                if candle_open >= stop:
                    exit_price = candle_open
                    break
                if candle_high >= stop:
                    exit_price = stop
                    break
                favorable_extreme = min(favorable_extreme, candle_low)
                if entry - favorable_extreme >= distance:
                    activated = True
                if activated:
                    stop = min(stop, favorable_extreme + distance)
        gross_return = side * (exit_price / entry - 1) * 100
        values.append(gross_return - ROUND_TRIP_COST_PERCENT)
    return np.asarray(values)


def analyze_trailing_candidate(data: pd.DataFrame) -> pd.DataFrame:
    definition = EventDefinition(
        "impulse_1_volume_low", "impulse_1_volume_low"
    )
    rows = []
    for atr_multiplier in TRAILING_ATR_MULTIPLIERS:
        for year in (2023, 2024):
            indices = _eligible_events(data, definition, year)
            values = _trailing_returns(data, indices, atr_multiplier)
            profit = values[values > 0].sum()
            loss = abs(values[values < 0].sum())
            metrics = _metrics(values)
            rows.append(
                {
                    "atr_multiplier": atr_multiplier,
                    "year": year,
                    "events": len(values),
                    **metrics,
                    "profit_factor": (
                        float(profit / loss)
                        if loss > 0
                        else float("inf")
                    ),
                }
            )
    return pd.DataFrame(rows)


def analyze_candidate_directions(data: pd.DataFrame) -> pd.DataFrame:
    definition = EventDefinition(
        "impulse_1_volume_low", "impulse_1_volume_low"
    )
    rows = []
    for year in (2023, 2024):
        indices = _eligible_events(data, definition, year)
        sides = -data["direction"].iloc[indices].to_numpy(dtype="int8")
        values = _returns_for_indices(
            data, indices, CANDIDATE_HORIZON_CANDLES, "REVERSAL"
        )
        for direction, side in (("LONG", 1), ("SHORT", -1)):
            selected = values[sides == side]
            profit = selected[selected > 0].sum()
            loss = abs(selected[selected < 0].sum())
            rows.append(
                {
                    "year": year,
                    "direction": direction,
                    "events": len(selected),
                    **_metrics(selected),
                    "profit_factor": (
                        float(profit / loss) if loss > 0 else float("inf")
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    candles = load_candles_dataframe(
        "SOLUSDT", "15m", DATA_START, ANALYSIS_END
    )
    data = _prepare_data(candles)
    results = analyze_events(data)
    summary = _confirmation_summary(results)
    excursion_summary = _excursion_confirmation_summary(
        analyze_excursions(data)
    )
    direction_split = analyze_candidate_directions(data)
    trailing = analyze_trailing_candidate(data)
    print("SOL Market Behavior analysis")
    print(f"Data: {len(candles)} closed 15m candles, gaps=0")
    print(f"Discovery: 2023; unchanged confirmation: 2024")
    print(
        f"Costs: {ROUND_TRIP_COST_PERCENT:.3f}% round trip; "
        f"event cooldown: {EVENT_COOLDOWN_CANDLES} candles"
    )
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print("\nEight-hour path diagnostics")
    print(
        excursion_summary.to_string(
            index=False, float_format=lambda value: f"{value:.4f}"
        )
    )
    print("\nFour-hour low-volume reversal split by direction")
    print(
        direction_split.to_string(
            index=False, float_format=lambda value: f"{value:.4f}"
        )
    )
    print("\nCausal trailing diagnostic — low-volume >=1 ATR reversal")
    print(
        trailing.to_string(
            index=False, float_format=lambda value: f"{value:.4f}"
        )
    )


if __name__ == "__main__":
    main()
