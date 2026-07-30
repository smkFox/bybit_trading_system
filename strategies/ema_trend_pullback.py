import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class Action(str, Enum):
    NO_ACTION = "NO_ACTION"
    OPEN_POSITION = "OPEN_POSITION"
    HOLD_POSITION = "HOLD_POSITION"
    CLOSE_POSITION = "CLOSE_POSITION"


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Reason(str, Enum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    TREND_NOT_PERMITTED = "TREND_NOT_PERMITTED"
    PULLBACK_NOT_FOUND = "PULLBACK_NOT_FOUND"
    CONFIRMATION_NOT_FOUND = "CONFIRMATION_NOT_FOUND"
    LONG_SETUP_CONFIRMED = "LONG_SETUP_CONFIRMED"
    SHORT_SETUP_CONFIRMED = "SHORT_SETUP_CONFIRMED"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    MAX_HOLDING_TIME = "MAX_HOLDING_TIME"


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = "ema_trend_pullback"
    strategy_version: str = "1.0.0"
    symbol: str = "ETHUSDT"
    signal_timeframe: str = "15m"
    pullback_ema_period: int = 20
    atr_period: int = 14
    trend_fast_ema_period: int = 50
    trend_slow_ema_period: int = 200
    stop_atr_multiplier: float = 1.5
    take_profit_r_multiple: float = 2.0
    maximum_holding_candles: int = 32


@dataclass(frozen=True)
class PositionState:
    side: Side
    entry_time: datetime
    holding_candles: int


@dataclass(frozen=True)
class StrategyDecision:
    decision_id: str
    strategy_id: str
    strategy_version: str
    symbol: str
    signal_timeframe: str
    signal_candle_open_time: datetime
    decision_time: datetime
    execute_at: datetime
    action: Action
    side: Side | None
    reason: Reason
    entry_timing: str | None
    stop_distance: float | None
    take_profit_r_multiple: float | None
    supporting_values: dict[str, Any]


REQUIRED_ROW_FIELDS = {
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "decision_time",
    "signal_ema",
    "signal_atr",
    "trend_open_time",
    "trend_available_time",
    "trend_close",
    "trend_fast_ema",
    "trend_slow_ema",
}
INDICATOR_FIELDS = (
    "signal_ema",
    "signal_atr",
    "trend_close",
    "trend_fast_ema",
    "trend_slow_ema",
)
ENTRY_TIMING = "IMMEDIATELY_AFTER_SIGNAL_CLOSE"
SIGNAL_DURATION = pd.Timedelta(minutes=15)


def _validate_config(config: StrategyConfig) -> None:
    integer_values = (
        config.pullback_ema_period,
        config.atr_period,
        config.trend_fast_ema_period,
        config.trend_slow_ema_period,
        config.maximum_holding_candles,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in integer_values
    ):
        raise TypeError("Strategy periods and holding candles must be integers.")
    if any(value < 1 for value in integer_values):
        raise ValueError("Strategy periods and holding candles must be positive.")
    if config.stop_atr_multiplier <= 0 or config.take_profit_r_multiple <= 0:
        raise ValueError("Stop and take-profit multipliers must be positive.")


def _validate_rows(
    pullback_row: pd.Series,
    confirmation_row: pd.Series,
) -> None:
    if not isinstance(pullback_row, pd.Series) or not isinstance(
        confirmation_row,
        pd.Series,
    ):
        raise TypeError("Strategy rows must be pandas Series.")

    for name, row in (
        ("pullback_row", pullback_row),
        ("confirmation_row", confirmation_row),
    ):
        missing = sorted(REQUIRED_ROW_FIELDS - set(row.index))
        if missing:
            raise ValueError(f"{name} is missing fields: {', '.join(missing)}")

    pullback_time = pd.Timestamp(pullback_row["open_time"])
    confirmation_time = pd.Timestamp(confirmation_row["open_time"])
    if confirmation_time - pullback_time != SIGNAL_DURATION:
        raise ValueError("Strategy rows must be consecutive 15m candles.")

    decision_time = pd.Timestamp(confirmation_row["decision_time"])
    if decision_time != confirmation_time + SIGNAL_DURATION:
        raise ValueError("Confirmation decision time is inconsistent.")

    trend_available_time = confirmation_row["trend_available_time"]
    if not pd.isna(trend_available_time):
        if pd.Timestamp(trend_available_time) > decision_time:
            raise ValueError("Strategy input contains a future 1h candle.")


def _decision_id(
    config: StrategyConfig,
    signal_time: datetime,
    action: Action,
) -> str:
    source = "|".join(
        (
            config.strategy_id,
            config.strategy_version,
            config.symbol,
            config.signal_timeframe,
            pd.Timestamp(signal_time).isoformat(),
            action.value,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _supporting_values(
    pullback_row: pd.Series,
    confirmation_row: pd.Series,
    position_state: PositionState | None,
) -> dict[str, Any]:
    return {
        "trend_candle_open_time": confirmation_row["trend_open_time"],
        "trend_close": confirmation_row["trend_close"],
        "trend_fast_ema": confirmation_row["trend_fast_ema"],
        "trend_slow_ema": confirmation_row["trend_slow_ema"],
        "pullback_candle_open_time": pullback_row["open_time"],
        "pullback_open": pullback_row["open"],
        "pullback_high": pullback_row["high"],
        "pullback_low": pullback_row["low"],
        "pullback_close": pullback_row["close"],
        "pullback_ema": pullback_row["signal_ema"],
        "confirmation_candle_open_time": confirmation_row["open_time"],
        "confirmation_close": confirmation_row["close"],
        "confirmation_ema": confirmation_row["signal_ema"],
        "confirmation_atr": confirmation_row["signal_atr"],
        "position_holding_candles": (
            position_state.holding_candles if position_state else None
        ),
    }


def _build_decision(
    *,
    config: StrategyConfig,
    confirmation_row: pd.Series,
    action: Action,
    side: Side | None,
    reason: Reason,
    supporting_values: dict[str, Any],
    stop_distance: float | None = None,
) -> StrategyDecision:
    signal_time = pd.Timestamp(confirmation_row["open_time"])
    decision_time = pd.Timestamp(confirmation_row["decision_time"])
    is_open = action is Action.OPEN_POSITION
    return StrategyDecision(
        decision_id=_decision_id(config, signal_time, action),
        strategy_id=config.strategy_id,
        strategy_version=config.strategy_version,
        symbol=config.symbol,
        signal_timeframe=config.signal_timeframe,
        signal_candle_open_time=signal_time,
        decision_time=decision_time,
        execute_at=decision_time,
        action=action,
        side=side,
        reason=reason,
        entry_timing=ENTRY_TIMING if is_open else None,
        stop_distance=stop_distance if is_open else None,
        take_profit_r_multiple=(
            config.take_profit_r_multiple if is_open else None
        ),
        supporting_values=supporting_values,
    )


def evaluate_ema_trend_pullback(
    pullback_row: pd.Series,
    confirmation_row: pd.Series,
    position_state: PositionState | None = None,
    config: StrategyConfig = StrategyConfig(),
) -> StrategyDecision:
    """Return one deterministic decision from two closed 15m rows."""
    _validate_config(config)
    _validate_rows(pullback_row, confirmation_row)
    supporting = _supporting_values(
        pullback_row,
        confirmation_row,
        position_state,
    )

    if position_state is not None:
        if position_state.holding_candles < 1:
            raise ValueError("Position holding candles must be positive.")
        if position_state.holding_candles >= config.maximum_holding_candles:
            return _build_decision(
                config=config,
                confirmation_row=confirmation_row,
                action=Action.CLOSE_POSITION,
                side=position_state.side,
                reason=Reason.MAX_HOLDING_TIME,
                supporting_values=supporting,
            )
        return _build_decision(
            config=config,
            confirmation_row=confirmation_row,
            action=Action.HOLD_POSITION,
            side=position_state.side,
            reason=Reason.POSITION_ACTIVE,
            supporting_values=supporting,
        )

    required_values = [
        pullback_row["signal_ema"],
        *(confirmation_row[field] for field in INDICATOR_FIELDS),
    ]
    if any(pd.isna(value) for value in required_values):
        return _build_decision(
            config=config,
            confirmation_row=confirmation_row,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.INSUFFICIENT_HISTORY,
            supporting_values=supporting,
        )
    if not all(math.isfinite(float(value)) for value in required_values):
        raise ValueError("Strategy input contains non-finite indicator values.")

    trend_close = float(confirmation_row["trend_close"])
    trend_fast = float(confirmation_row["trend_fast_ema"])
    trend_slow = float(confirmation_row["trend_slow_ema"])
    long_permitted = trend_fast > trend_slow and trend_close > trend_fast
    short_permitted = trend_fast < trend_slow and trend_close < trend_fast
    if not long_permitted and not short_permitted:
        return _build_decision(
            config=config,
            confirmation_row=confirmation_row,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.TREND_NOT_PERMITTED,
            supporting_values=supporting,
        )

    pullback_ema = float(pullback_row["signal_ema"])
    if long_permitted:
        pullback_found = (
            float(pullback_row["open"]) > pullback_ema
            and float(pullback_row["low"]) <= pullback_ema
            and float(pullback_row["close"]) >= pullback_ema
        )
        confirmation_found = (
            float(confirmation_row["close"]) > float(pullback_row["high"])
            and float(confirmation_row["close"])
            > float(confirmation_row["signal_ema"])
        )
        side = Side.LONG
        reason = Reason.LONG_SETUP_CONFIRMED
    else:
        pullback_found = (
            float(pullback_row["open"]) < pullback_ema
            and float(pullback_row["high"]) >= pullback_ema
            and float(pullback_row["close"]) <= pullback_ema
        )
        confirmation_found = (
            float(confirmation_row["close"]) < float(pullback_row["low"])
            and float(confirmation_row["close"])
            < float(confirmation_row["signal_ema"])
        )
        side = Side.SHORT
        reason = Reason.SHORT_SETUP_CONFIRMED

    if not pullback_found:
        return _build_decision(
            config=config,
            confirmation_row=confirmation_row,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.PULLBACK_NOT_FOUND,
            supporting_values=supporting,
        )
    if not confirmation_found:
        return _build_decision(
            config=config,
            confirmation_row=confirmation_row,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.CONFIRMATION_NOT_FOUND,
            supporting_values=supporting,
        )

    stop_distance = (
        float(confirmation_row["signal_atr"]) * config.stop_atr_multiplier
    )
    return _build_decision(
        config=config,
        confirmation_row=confirmation_row,
        action=Action.OPEN_POSITION,
        side=side,
        reason=reason,
        supporting_values=supporting,
        stop_distance=stop_distance,
    )
