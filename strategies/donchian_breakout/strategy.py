import hashlib
import math
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from strategies.indicators import calculate_atr
from strategies.models import Action, PositionState, Side, StrategyDecision


FOUR_HOURS = pd.Timedelta(hours=4)
ENTRY_TIMING = "NEXT_4H_OPEN"
REQUIRED_ROW_FIELDS = {
    "symbol",
    "timeframe",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "decision_time",
    "entry_channel_high",
    "entry_channel_low",
    "exit_channel_high",
    "exit_channel_low",
    "signal_atr",
}


class Reason(str, Enum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    NO_BREAKOUT = "NO_BREAKOUT"
    LONG_BREAKOUT = "LONG_BREAKOUT"
    SHORT_BREAKOUT = "SHORT_BREAKOUT"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    LONG_EXIT_CHANNEL = "LONG_EXIT_CHANNEL"
    SHORT_EXIT_CHANNEL = "SHORT_EXIT_CHANNEL"


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = "donchian_breakout"
    strategy_version: str = "1.0.0"
    symbol: str = "ETHUSDT"
    signal_timeframe: str = "4h"
    entry_channel_period: int = 20
    exit_channel_period: int = 10
    atr_period: int = 14
    stop_atr_multiplier: float = 2.0


def _validate_config(config: StrategyConfig) -> None:
    periods = (
        config.entry_channel_period,
        config.exit_channel_period,
        config.atr_period,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in periods
    ):
        raise TypeError("Strategy periods must be integers.")
    if any(value < 1 for value in periods):
        raise ValueError("Strategy periods must be positive.")
    if config.exit_channel_period >= config.entry_channel_period:
        raise ValueError("Exit channel must be shorter than entry channel.")
    if config.stop_atr_multiplier <= 0:
        raise ValueError("ATR stop multiplier must be positive.")


def prepare_market_data(
    candles_4h: pd.DataFrame,
    config: StrategyConfig = StrategyConfig(),
) -> pd.DataFrame:
    """Add shifted Donchian channels and ATR to closed 4h candles."""
    _validate_config(config)
    if not isinstance(candles_4h, pd.DataFrame):
        raise TypeError("candles_4h must be a pandas DataFrame.")
    required = {
        "symbol",
        "timeframe",
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "decision_time",
    }
    missing = sorted(required - set(candles_4h.columns))
    if missing:
        raise ValueError(
            "candles_4h is missing required columns: " + ", ".join(missing)
        )

    prepared = candles_4h.copy(deep=True)
    prepared = prepared.sort_values("open_time").reset_index(drop=True)
    previous_high = prepared["high"].shift(1)
    previous_low = prepared["low"].shift(1)
    prepared["entry_channel_high"] = previous_high.rolling(
        config.entry_channel_period,
        min_periods=config.entry_channel_period,
    ).max()
    prepared["entry_channel_low"] = previous_low.rolling(
        config.entry_channel_period,
        min_periods=config.entry_channel_period,
    ).min()
    prepared["exit_channel_high"] = previous_high.rolling(
        config.exit_channel_period,
        min_periods=config.exit_channel_period,
    ).max()
    prepared["exit_channel_low"] = previous_low.rolling(
        config.exit_channel_period,
        min_periods=config.exit_channel_period,
    ).min()
    prepared["signal_atr"] = calculate_atr(
        prepared,
        config.atr_period,
    )
    return prepared


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
            config.symbol,
            config.signal_timeframe,
            signal_time.isoformat(),
            action.value,
            side.value if side is not None else "NONE",
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _validate_row(row: pd.Series, config: StrategyConfig) -> None:
    if not isinstance(row, pd.Series):
        raise TypeError("Strategy row must be a pandas Series.")
    missing = sorted(REQUIRED_ROW_FIELDS - set(row.index))
    if missing:
        raise ValueError("Strategy row is missing fields: " + ", ".join(missing))
    if row["symbol"] != config.symbol or row["timeframe"] != "4h":
        raise ValueError("Strategy row has an unexpected market identity.")
    open_time = pd.Timestamp(row["open_time"])
    if pd.Timestamp(row["decision_time"]) != open_time + FOUR_HOURS:
        raise ValueError("Strategy decision time is inconsistent.")


def _build_decision(
    *,
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
        entry_timing=ENTRY_TIMING if action is Action.OPEN_POSITION else None,
        stop_distance=stop_distance,
        take_profit_r_multiple=None,
        supporting_values={
            "close": row["close"],
            "entry_channel_high": row["entry_channel_high"],
            "entry_channel_low": row["entry_channel_low"],
            "exit_channel_high": row["exit_channel_high"],
            "exit_channel_low": row["exit_channel_low"],
            "atr": row["signal_atr"],
            "position_holding_candles": (
                position_state.holding_candles if position_state else None
            ),
        },
    )


def evaluate_donchian_breakout(
    row: pd.Series,
    position_state: PositionState | None = None,
    config: StrategyConfig = StrategyConfig(),
) -> StrategyDecision:
    """Return one deterministic decision from a closed prepared 4h candle."""
    _validate_config(config)
    _validate_row(row, config)
    close = float(row["close"])

    if position_state is not None:
        if position_state.holding_candles < 1:
            raise ValueError("Position holding candles must be positive.")
        required_exit = (
            row["exit_channel_low"]
            if position_state.side is Side.LONG
            else row["exit_channel_high"]
        )
        if pd.isna(required_exit):
            return _build_decision(
                row=row,
                config=config,
                action=Action.HOLD_POSITION,
                side=position_state.side,
                reason=Reason.INSUFFICIENT_HISTORY,
                position_state=position_state,
            )
        if not math.isfinite(float(required_exit)):
            raise ValueError("Exit channel contains a non-finite value.")

        should_close = (
            close < float(required_exit)
            if position_state.side is Side.LONG
            else close > float(required_exit)
        )
        if should_close:
            reason = (
                Reason.LONG_EXIT_CHANNEL
                if position_state.side is Side.LONG
                else Reason.SHORT_EXIT_CHANNEL
            )
            return _build_decision(
                row=row,
                config=config,
                action=Action.CLOSE_POSITION,
                side=position_state.side,
                reason=reason,
                position_state=position_state,
            )
        return _build_decision(
            row=row,
            config=config,
            action=Action.HOLD_POSITION,
            side=position_state.side,
            reason=Reason.POSITION_ACTIVE,
            position_state=position_state,
        )

    required_entry = (
        row["entry_channel_high"],
        row["entry_channel_low"],
        row["signal_atr"],
    )
    if any(pd.isna(value) for value in required_entry):
        return _build_decision(
            row=row,
            config=config,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.INSUFFICIENT_HISTORY,
        )
    if not all(math.isfinite(float(value)) for value in required_entry):
        raise ValueError("Entry input contains a non-finite value.")

    if close > float(row["entry_channel_high"]):
        side = Side.LONG
        reason = Reason.LONG_BREAKOUT
    elif close < float(row["entry_channel_low"]):
        side = Side.SHORT
        reason = Reason.SHORT_BREAKOUT
    else:
        return _build_decision(
            row=row,
            config=config,
            action=Action.NO_ACTION,
            side=None,
            reason=Reason.NO_BREAKOUT,
        )

    stop_distance = float(row["signal_atr"]) * config.stop_atr_multiplier
    return _build_decision(
        row=row,
        config=config,
        action=Action.OPEN_POSITION,
        side=side,
        reason=reason,
        stop_distance=stop_distance,
    )
