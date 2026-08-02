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
    "open",
    "high",
    "low",
    "close",
    "decision_time",
    "current_residual_z",
    "shock_residual_z",
    "shock_beta",
    "shock_atr",
    "entry_side",
}


class Reason(str, Enum):
    NO_CONFIRMED_SHOCK = "NO_CONFIRMED_SHOCK"
    NEGATIVE_SHOCK_CONFIRMED = "NEGATIVE_SHOCK_CONFIRMED"
    POSITIVE_SHOCK_CONFIRMED = "POSITIVE_SHOCK_CONFIRMED"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    RESIDUAL_NORMALIZED = "RESIDUAL_NORMALIZED"
    MAXIMUM_HOLDING_TIME = "MAXIMUM_HOLDING_TIME"


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = "btc_eth_shock_mean_reversion"
    strategy_version: str = "1.0.0"
    traded_symbol: str = "ETHUSDT"
    context_symbol: str = "BTCUSDT"
    signal_timeframe: str = "15m"
    relationship_timeframe: str = "1h"
    relationship_period: int = 168
    residual_z_period: int = 168
    shock_z_threshold: float = 2.5
    normalized_z_threshold: float = 0.5
    atr_period: int = 14
    stop_atr_multiplier: float = 1.5
    confirmation_candles: int = 4
    maximum_holding_candles: int = 32


def _validate_config(config: StrategyConfig) -> None:
    periods = (
        config.relationship_period,
        config.residual_z_period,
        config.atr_period,
        config.confirmation_candles,
        config.maximum_holding_candles,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in periods
    ):
        raise TypeError("Strategy periods must be integers.")
    if any(value < 1 for value in periods):
        raise ValueError("Strategy periods must be positive.")
    if config.signal_timeframe != "15m":
        raise ValueError("The fixed signal timeframe must be 15m.")
    if config.relationship_timeframe != "1h":
        raise ValueError("The fixed relationship timeframe must be 1h.")
    if config.shock_z_threshold <= 0:
        raise ValueError("Shock Z-score threshold must be positive.")
    if not 0 <= config.normalized_z_threshold < config.shock_z_threshold:
        raise ValueError("Normalized Z-score threshold is invalid.")
    if config.stop_atr_multiplier <= 0:
        raise ValueError("ATR stop multiplier must be positive.")


def _validate_candles(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    interval: pd.Timedelta,
) -> pd.DataFrame:
    if not isinstance(candles, pd.DataFrame):
        raise TypeError("Candles must be a pandas DataFrame.")
    required = {
        "symbol",
        "timeframe",
        "open_time",
        "open",
        "high",
        "low",
        "close",
    }
    missing = sorted(required - set(candles.columns))
    if missing:
        raise ValueError("Candles are missing fields: " + ", ".join(missing))

    validated = candles.copy(deep=True).sort_values("open_time").reset_index(
        drop=True
    )
    if validated.empty:
        raise ValueError("Candles must not be empty.")
    if (
        validated["symbol"].nunique() != 1
        or validated.iloc[0]["symbol"] != symbol
        or validated["timeframe"].nunique() != 1
        or validated.iloc[0]["timeframe"] != timeframe
    ):
        raise ValueError("Candles have an unexpected market identity.")
    validated["open_time"] = pd.to_datetime(
        validated["open_time"],
        utc=True,
    )
    if validated["open_time"].duplicated().any():
        raise ValueError("Candles contain duplicate timestamps.")
    if len(validated) > 1:
        differences = validated["open_time"].diff().iloc[1:]
        if not (differences == interval).all():
            raise ValueError("Candles must be consecutive without gaps.")
    return validated


def prepare_hourly_relationship(
    eth_1h: pd.DataFrame,
    btc_1h: pd.DataFrame,
    config: StrategyConfig = StrategyConfig(),
) -> pd.DataFrame:
    """Calculate causal rolling BTC beta, ETH residual, Z-score, and ATR."""
    _validate_config(config)
    eth = _validate_candles(
        eth_1h,
        config.traded_symbol,
        "1h",
        ONE_HOUR,
    )
    btc = _validate_candles(
        btc_1h,
        config.context_symbol,
        "1h",
        ONE_HOUR,
    )
    if not eth["open_time"].equals(btc["open_time"]):
        raise ValueError("BTC and ETH hourly timestamps do not match exactly.")

    hourly = eth[
        ["open_time", "open", "high", "low", "close"]
    ].copy()
    hourly = hourly.rename(
        columns={
            "open": "eth_open",
            "high": "eth_high",
            "low": "eth_low",
            "close": "eth_close",
        }
    )
    hourly["btc_close"] = btc["close"].to_numpy()
    hourly["hour_decision_time"] = hourly["open_time"] + ONE_HOUR
    hourly["eth_return"] = (
        hourly["eth_close"] / hourly["eth_close"].shift(1)
    ).map(math.log)
    hourly["btc_return"] = (
        hourly["btc_close"] / hourly["btc_close"].shift(1)
    ).map(math.log)

    rolling_covariance = hourly["eth_return"].rolling(
        config.relationship_period,
        min_periods=config.relationship_period,
    ).cov(hourly["btc_return"])
    rolling_variance = hourly["btc_return"].rolling(
        config.relationship_period,
        min_periods=config.relationship_period,
    ).var()
    hourly["beta"] = rolling_covariance.shift(1) / rolling_variance.shift(1)
    hourly["residual"] = (
        hourly["eth_return"] - hourly["beta"] * hourly["btc_return"]
    )
    residual_mean = hourly["residual"].rolling(
        config.residual_z_period,
        min_periods=config.residual_z_period,
    ).mean().shift(1)
    residual_deviation = hourly["residual"].rolling(
        config.residual_z_period,
        min_periods=config.residual_z_period,
    ).std().shift(1)
    hourly["residual_z"] = (
        (hourly["residual"] - residual_mean) / residual_deviation
    )
    hourly["hourly_atr"] = calculate_atr(eth, config.atr_period)
    hourly["shock_side"] = pd.Series(
        pd.NA,
        index=hourly.index,
        dtype="string",
    )
    hourly.loc[
        hourly["residual_z"] <= -config.shock_z_threshold,
        "shock_side",
    ] = Side.LONG.value
    hourly.loc[
        hourly["residual_z"] >= config.shock_z_threshold,
        "shock_side",
    ] = Side.SHORT.value
    return hourly


def prepare_market_data(
    eth_1h: pd.DataFrame,
    btc_1h: pd.DataFrame,
    eth_15m: pd.DataFrame,
    config: StrategyConfig = StrategyConfig(),
) -> pd.DataFrame:
    """Attach hourly shocks to their four causal 15m confirmation candles."""
    hourly = prepare_hourly_relationship(eth_1h, btc_1h, config)
    signal = _validate_candles(
        eth_15m,
        config.traded_symbol,
        "15m",
        FIFTEEN_MINUTES,
    )
    signal["decision_time"] = signal["open_time"] + FIFTEEN_MINUTES
    signal["previous_15m_high"] = signal["high"].shift(1)
    signal["previous_15m_low"] = signal["low"].shift(1)

    shock_fields = hourly[
        [
            "hour_decision_time",
            "shock_side",
            "residual_z",
            "beta",
            "hourly_atr",
        ]
    ].rename(
        columns={
            "residual_z": "shock_residual_z",
            "beta": "shock_beta",
            "hourly_atr": "shock_atr",
        }
    )
    prepared = pd.merge_asof(
        signal.sort_values("open_time"),
        shock_fields.sort_values("hour_decision_time"),
        left_on="open_time",
        right_on="hour_decision_time",
        direction="backward",
        allow_exact_matches=True,
    )
    candle_age = (
        (prepared["open_time"] - prepared["hour_decision_time"])
        / FIFTEEN_MINUTES
    )
    in_confirmation_window = (
        (candle_age >= 0) & (candle_age < config.confirmation_candles)
    )
    long_confirmation = (
        (prepared["shock_side"] == Side.LONG.value)
        & (prepared["close"] > prepared["previous_15m_high"])
    )
    short_confirmation = (
        (prepared["shock_side"] == Side.SHORT.value)
        & (prepared["close"] < prepared["previous_15m_low"])
    )
    raw_confirmation = in_confirmation_window & (
        long_confirmation | short_confirmation
    )
    confirmation_number = raw_confirmation.groupby(
        prepared["hour_decision_time"]
    ).cumsum()
    first_confirmation = raw_confirmation & (confirmation_number == 1)
    prepared["entry_side"] = pd.Series(
        pd.NA,
        index=prepared.index,
        dtype="string",
    )
    prepared.loc[
        first_confirmation & long_confirmation,
        "entry_side",
    ] = Side.LONG.value
    prepared.loc[
        first_confirmation & short_confirmation,
        "entry_side",
    ] = Side.SHORT.value

    state_fields = hourly[
        ["hour_decision_time", "residual_z"]
    ].rename(
        columns={
            "hour_decision_time": "state_decision_time",
            "residual_z": "current_residual_z",
        }
    )
    prepared = pd.merge_asof(
        prepared.sort_values("decision_time"),
        state_fields.sort_values("state_decision_time"),
        left_on="decision_time",
        right_on="state_decision_time",
        direction="backward",
        allow_exact_matches=True,
    )
    return prepared.reset_index(drop=True)


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
        symbol=config.traded_symbol,
        signal_timeframe=config.signal_timeframe,
        signal_candle_open_time=signal_time,
        decision_time=decision_time,
        execute_at=decision_time,
        action=action,
        side=side,
        reason=reason.value,
        entry_timing=(
            "NEXT_15M_OPEN" if action is Action.OPEN_POSITION else None
        ),
        stop_distance=stop_distance,
        take_profit_r_multiple=None,
        supporting_values={
            "current_residual_z": row["current_residual_z"],
            "shock_residual_z": row["shock_residual_z"],
            "shock_beta": row["shock_beta"],
            "shock_atr": row["shock_atr"],
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
    if row["symbol"] != config.traded_symbol or row["timeframe"] != "15m":
        raise ValueError("Strategy row has an unexpected market identity.")
    if pd.Timestamp(row["decision_time"]) != (
        pd.Timestamp(row["open_time"]) + FIFTEEN_MINUTES
    ):
        raise ValueError("Strategy decision time is inconsistent.")

    if position_state is not None:
        if position_state.holding_candles < 1:
            raise ValueError("Position holding candles must be positive.")
        residual_z = row["current_residual_z"]
        normalized = (
            not pd.isna(residual_z)
            and (
                float(residual_z) >= -config.normalized_z_threshold
                if position_state.side is Side.LONG
                else float(residual_z) <= config.normalized_z_threshold
            )
        )
        if normalized:
            return _build_decision(
                row,
                config,
                Action.CLOSE_POSITION,
                position_state.side,
                Reason.RESIDUAL_NORMALIZED,
                position_state=position_state,
            )
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

    entry_side = row["entry_side"]
    if pd.isna(entry_side):
        return _build_decision(
            row,
            config,
            Action.NO_ACTION,
            None,
            Reason.NO_CONFIRMED_SHOCK,
        )
    side = Side(str(entry_side))
    shock_atr = float(row["shock_atr"])
    if not math.isfinite(shock_atr) or shock_atr <= 0:
        raise ValueError("Confirmed shock has invalid ATR.")
    reason = (
        Reason.NEGATIVE_SHOCK_CONFIRMED
        if side is Side.LONG
        else Reason.POSITIVE_SHOCK_CONFIRMED
    )
    return _build_decision(
        row,
        config,
        Action.OPEN_POSITION,
        side,
        reason,
        stop_distance=shock_atr * config.stop_atr_multiplier,
    )
