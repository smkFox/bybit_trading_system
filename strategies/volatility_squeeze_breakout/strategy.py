import hashlib
import math
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from strategies.indicators import calculate_atr
from strategies.models import Action, PositionState, Side, StrategyDecision


ONE_HOUR = pd.Timedelta(hours=1)
FIFTEEN_MINUTES = pd.Timedelta(minutes=15)
REQUIRED_DECISION_FIELDS = {
    "symbol",
    "timeframe",
    "open_time",
    "decision_time",
    "entry_side",
    "signal_atr",
    "setup_time",
    "range_high",
    "range_low",
    "volume_ratio",
    "open_interest",
    "open_interest_1h_ago",
    "funding_rate",
}


class Reason(str, Enum):
    NO_CONFIRMED_BREAKOUT = "NO_CONFIRMED_BREAKOUT"
    LONG_BREAKOUT_CONFIRMED = "LONG_BREAKOUT_CONFIRMED"
    SHORT_BREAKOUT_CONFIRMED = "SHORT_BREAKOUT_CONFIRMED"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    MAXIMUM_HOLDING_TIME = "MAXIMUM_HOLDING_TIME"


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = "volatility_squeeze_breakout"
    strategy_version: str = "1.0.0"
    symbol: str = "ETHUSDT"
    signal_timeframe: str = "15m"
    state_timeframe: str = "1h"
    atr_period: int = 14
    squeeze_lookback_hours: int = 720
    squeeze_quantile: float = 0.20
    range_hours: int = 4
    setup_candles: int = 16
    volume_lookback_candles: int = 20
    volume_multiplier: float = 1.5
    oi_lookback_candles: int = 4
    funding_lookback_events: int = 90
    funding_lower_quantile: float = 0.10
    funding_upper_quantile: float = 0.90
    stop_atr_multiplier: float = 1.5
    take_profit_r_multiple: float = 2.0
    maximum_holding_candles: int = 32


def _validate_config(config: StrategyConfig) -> None:
    integer_values = (
        config.atr_period,
        config.squeeze_lookback_hours,
        config.range_hours,
        config.setup_candles,
        config.volume_lookback_candles,
        config.oi_lookback_candles,
        config.funding_lookback_events,
        config.maximum_holding_candles,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in integer_values):
        raise TypeError("Strategy periods must be integers.")
    if any(value < 1 for value in integer_values):
        raise ValueError("Strategy periods must be positive.")
    if config.signal_timeframe != "15m" or config.state_timeframe != "1h":
        raise ValueError("The fixed strategy timeframes are 15m and 1h.")
    if not 0 < config.squeeze_quantile < 1:
        raise ValueError("Squeeze quantile must be between zero and one.")
    if not 0 <= config.funding_lower_quantile < config.funding_upper_quantile <= 1:
        raise ValueError("Funding quantiles are invalid.")
    if config.volume_multiplier <= 0 or config.stop_atr_multiplier <= 0:
        raise ValueError("Strategy multipliers must be positive.")
    if config.take_profit_r_multiple <= 0:
        raise ValueError("Take-profit multiple must be positive.")


def _validate_candles(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    interval: pd.Timedelta,
) -> pd.DataFrame:
    required = {
        "symbol", "timeframe", "open_time", "open", "high", "low",
        "close", "volume",
    }
    if not isinstance(candles, pd.DataFrame):
        raise TypeError("Candles must be a pandas DataFrame.")
    missing = sorted(required - set(candles.columns))
    if missing:
        raise ValueError("Candles are missing fields: " + ", ".join(missing))
    validated = candles.copy(deep=True).sort_values("open_time").reset_index(drop=True)
    if validated.empty:
        raise ValueError("Candles must not be empty.")
    if (
        validated["symbol"].nunique() != 1
        or validated.iloc[0]["symbol"] != symbol
        or validated["timeframe"].nunique() != 1
        or validated.iloc[0]["timeframe"] != timeframe
    ):
        raise ValueError("Candles have an unexpected market identity.")
    validated["open_time"] = pd.to_datetime(validated["open_time"], utc=True)
    if validated["open_time"].duplicated().any():
        raise ValueError("Candles contain duplicate timestamps.")
    if len(validated) > 1 and not (validated["open_time"].diff().iloc[1:] == interval).all():
        raise ValueError("Candles must be consecutive without gaps.")
    return validated


def _validate_open_interest(
    observations: pd.DataFrame,
    config: StrategyConfig,
) -> pd.DataFrame:
    required = {"symbol", "timeframe", "timestamp", "open_interest"}
    if not isinstance(observations, pd.DataFrame):
        raise TypeError("Open Interest must be a pandas DataFrame.")
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError("Open Interest is missing fields: " + ", ".join(missing))
    validated = observations.copy(deep=True).sort_values("timestamp").reset_index(drop=True)
    if validated.empty:
        raise ValueError("Open Interest must not be empty.")
    if (
        validated["symbol"].nunique() != 1
        or validated.iloc[0]["symbol"] != config.symbol
        or validated["timeframe"].nunique() != 1
        or validated.iloc[0]["timeframe"] != "15m"
    ):
        raise ValueError("Open Interest has an unexpected market identity.")
    validated["timestamp"] = pd.to_datetime(validated["timestamp"], utc=True)
    if validated["timestamp"].duplicated().any():
        raise ValueError("Open Interest contains duplicate timestamps.")
    if (validated["open_interest"] < 0).any():
        raise ValueError("Open Interest must not be negative.")
    return validated


def _validate_funding(
    observations: pd.DataFrame,
    config: StrategyConfig,
) -> pd.DataFrame:
    required = {"symbol", "timestamp", "funding_rate"}
    if not isinstance(observations, pd.DataFrame):
        raise TypeError("Funding Rate must be a pandas DataFrame.")
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError("Funding Rate is missing fields: " + ", ".join(missing))
    validated = observations.copy(deep=True).sort_values("timestamp").reset_index(drop=True)
    if validated.empty:
        raise ValueError("Funding Rate must not be empty.")
    if validated["symbol"].nunique() != 1 or validated.iloc[0]["symbol"] != config.symbol:
        raise ValueError("Funding Rate has an unexpected symbol.")
    validated["timestamp"] = pd.to_datetime(validated["timestamp"], utc=True)
    if validated["timestamp"].duplicated().any():
        raise ValueError("Funding Rate contains duplicate timestamps.")
    return validated


def prepare_market_data(
    candles_1h: pd.DataFrame,
    candles_15m: pd.DataFrame,
    open_interest: pd.DataFrame,
    funding_rates: pd.DataFrame,
    config: StrategyConfig = StrategyConfig(),
) -> pd.DataFrame:
    """Build causal squeeze, breakout, volume, OI, and funding fields."""
    _validate_config(config)
    hourly = _validate_candles(
        candles_1h, config.symbol, config.state_timeframe, ONE_HOUR
    )
    signal = _validate_candles(
        candles_15m, config.symbol, config.signal_timeframe, FIFTEEN_MINUTES
    )
    oi = _validate_open_interest(open_interest, config)
    funding = _validate_funding(funding_rates, config)

    hourly["hour_decision_time"] = hourly["open_time"] + ONE_HOUR
    hourly["relative_atr"] = calculate_atr(hourly, config.atr_period) / hourly["close"]
    hourly["squeeze_threshold"] = (
        hourly["relative_atr"]
        .rolling(
            config.squeeze_lookback_hours,
            min_periods=config.squeeze_lookback_hours,
        )
        .quantile(config.squeeze_quantile)
        .shift(1)
    )
    hourly["range_high"] = hourly["high"].rolling(
        config.range_hours, min_periods=config.range_hours
    ).max()
    hourly["range_low"] = hourly["low"].rolling(
        config.range_hours, min_periods=config.range_hours
    ).min()
    squeeze = hourly.loc[
        hourly["relative_atr"] <= hourly["squeeze_threshold"],
        [
            "hour_decision_time", "relative_atr", "squeeze_threshold",
            "range_high", "range_low",
        ],
    ].rename(columns={"hour_decision_time": "setup_time"})

    signal["decision_time"] = signal["open_time"] + FIFTEEN_MINUTES
    signal["signal_atr"] = calculate_atr(signal, config.atr_period)
    signal["prior_volume_median"] = signal["volume"].rolling(
        config.volume_lookback_candles,
        min_periods=config.volume_lookback_candles,
    ).median().shift(1)
    signal["volume_ratio"] = signal["volume"] / signal["prior_volume_median"]
    prepared = pd.merge_asof(
        signal.sort_values("open_time"),
        squeeze.sort_values("setup_time"),
        left_on="open_time",
        right_on="setup_time",
        direction="backward",
        allow_exact_matches=True,
    )
    setup_age = (prepared["open_time"] - prepared["setup_time"]) / FIFTEEN_MINUTES
    prepared["setup_active"] = (setup_age >= 0) & (setup_age < config.setup_candles)

    oi["oi_available_time"] = oi["timestamp"] + FIFTEEN_MINUTES
    oi_by_time = oi.set_index("timestamp")["open_interest"]
    oi["previous_open_interest"] = oi_by_time.reindex(
        oi["timestamp"] - FIFTEEN_MINUTES
    ).to_numpy()
    oi["open_interest_1h_ago"] = oi_by_time.reindex(
        oi["timestamp"] - FIFTEEN_MINUTES * config.oi_lookback_candles
    ).to_numpy()
    prepared = pd.merge_asof(
        prepared.sort_values("decision_time"),
        oi[
            [
                "timestamp", "oi_available_time", "open_interest",
                "previous_open_interest", "open_interest_1h_ago",
            ]
        ].sort_values("oi_available_time"),
        left_on="decision_time",
        right_on="oi_available_time",
        direction="backward",
        allow_exact_matches=True,
    )

    funding["funding_lower_threshold"] = (
        funding["funding_rate"]
        .rolling(
            config.funding_lookback_events,
            min_periods=config.funding_lookback_events,
        )
        .quantile(config.funding_lower_quantile)
        .shift(1)
    )
    funding["funding_upper_threshold"] = (
        funding["funding_rate"]
        .rolling(
            config.funding_lookback_events,
            min_periods=config.funding_lookback_events,
        )
        .quantile(config.funding_upper_quantile)
        .shift(1)
    )
    funding = funding.rename(columns={"timestamp": "funding_timestamp"})
    prepared = pd.merge_asof(
        prepared.sort_values("decision_time"),
        funding[
            [
                "funding_timestamp", "funding_rate",
                "funding_lower_threshold", "funding_upper_threshold",
            ]
        ].sort_values("funding_timestamp"),
        left_on="decision_time",
        right_on="funding_timestamp",
        direction="backward",
        allow_exact_matches=True,
    )

    volume_confirmed = prepared["volume_ratio"] > config.volume_multiplier
    oi_confirmed = (
        (prepared["open_interest"] > prepared["previous_open_interest"])
        & (prepared["open_interest"] > prepared["open_interest_1h_ago"])
    )
    long_breakout = prepared["close"] > prepared["range_high"]
    short_breakout = prepared["close"] < prepared["range_low"]
    long_funding_allowed = (
        prepared["funding_rate"] <= prepared["funding_upper_threshold"]
    )
    short_funding_allowed = (
        prepared["funding_rate"] >= prepared["funding_lower_threshold"]
    )
    raw_long = (
        prepared["setup_active"] & long_breakout & volume_confirmed
        & oi_confirmed & long_funding_allowed
    )
    raw_short = (
        prepared["setup_active"] & short_breakout & volume_confirmed
        & oi_confirmed & short_funding_allowed
    )
    raw_entry = raw_long | raw_short
    entry_number = raw_entry.groupby(prepared["setup_time"]).cumsum()
    first_entry = raw_entry & (entry_number == 1)
    prepared["entry_side"] = pd.Series(pd.NA, index=prepared.index, dtype="string")
    prepared.loc[first_entry & raw_long, "entry_side"] = Side.LONG.value
    prepared.loc[first_entry & raw_short, "entry_side"] = Side.SHORT.value
    return prepared.sort_values("open_time").reset_index(drop=True)


def _decision_id(
    config: StrategyConfig,
    signal_time: pd.Timestamp,
    action: Action,
    side: Side | None,
) -> str:
    source = "|".join(
        (
            config.strategy_id,
            config.strategy_version,
            signal_time.isoformat(),
            action.value,
            side.value if side else "NONE",
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _build_decision(
    row: pd.Series,
    config: StrategyConfig,
    action: Action,
    side: Side | None,
    reason: Reason,
    stop_distance: float | None = None,
    position_state: PositionState | None = None,
) -> StrategyDecision:
    signal_time = pd.Timestamp(row["open_time"])
    decision_time = pd.Timestamp(row["decision_time"])
    return StrategyDecision(
        decision_id=_decision_id(config, signal_time, action, side),
        strategy_id=config.strategy_id,
        strategy_version=config.strategy_version,
        symbol=config.symbol,
        signal_timeframe=config.signal_timeframe,
        signal_candle_open_time=signal_time,
        decision_time=decision_time,
        execute_at=decision_time,
        action=action,
        side=side,
        reason=reason.value,
        entry_timing="NEXT_15M_OPEN" if action is Action.OPEN_POSITION else None,
        stop_distance=stop_distance,
        take_profit_r_multiple=(
            config.take_profit_r_multiple
            if action is Action.OPEN_POSITION
            else None
        ),
        supporting_values={
            "setup_time": row["setup_time"],
            "range_high": row["range_high"],
            "range_low": row["range_low"],
            "volume_ratio": row["volume_ratio"],
            "open_interest": row["open_interest"],
            "open_interest_1h_ago": row["open_interest_1h_ago"],
            "funding_rate": row["funding_rate"],
            "position_holding_candles": (
                position_state.holding_candles if position_state else None
            ),
        },
    )


def evaluate_strategy(
    row: pd.Series,
    position_state: PositionState | None = None,
    config: StrategyConfig = StrategyConfig(),
) -> StrategyDecision:
    """Return one deterministic decision from a prepared closed 15m candle."""
    _validate_config(config)
    if not isinstance(row, pd.Series):
        raise TypeError("Strategy row must be a pandas Series.")
    missing = sorted(REQUIRED_DECISION_FIELDS - set(row.index))
    if missing:
        raise ValueError("Strategy row is missing fields: " + ", ".join(missing))
    if row["symbol"] != config.symbol or row["timeframe"] != config.signal_timeframe:
        raise ValueError("Strategy row has an unexpected market identity.")
    if pd.Timestamp(row["decision_time"]) != pd.Timestamp(row["open_time"]) + FIFTEEN_MINUTES:
        raise ValueError("Strategy decision time is inconsistent.")

    if position_state is not None:
        if position_state.holding_candles >= config.maximum_holding_candles:
            return _build_decision(
                row,
                config,
                Action.CLOSE_POSITION,
                position_state.side,
                Reason.MAXIMUM_HOLDING_TIME,
                position_state=position_state,
            )
        return _build_decision(
            row,
            config,
            Action.HOLD_POSITION,
            position_state.side,
            Reason.POSITION_ACTIVE,
            position_state=position_state,
        )

    if pd.isna(row["entry_side"]):
        return _build_decision(
            row, config, Action.NO_ACTION, None, Reason.NO_CONFIRMED_BREAKOUT
        )
    side = Side(str(row["entry_side"]))
    signal_atr = float(row["signal_atr"])
    if not math.isfinite(signal_atr) or signal_atr <= 0:
        raise ValueError("Confirmed breakout has invalid ATR.")
    reason = (
        Reason.LONG_BREAKOUT_CONFIRMED
        if side is Side.LONG
        else Reason.SHORT_BREAKOUT_CONFIRMED
    )
    return _build_decision(
        row,
        config,
        Action.OPEN_POSITION,
        side,
        reason,
        stop_distance=signal_atr * config.stop_atr_multiplier,
    )
