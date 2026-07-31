import hashlib
import math
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from strategies.indicators import calculate_atr, calculate_ema
from strategies.models import Action, PositionState, Side, StrategyDecision


TIMEFRAME_DURATIONS = {
    "15m": pd.Timedelta(minutes=15),
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
}
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
    "trend_ema_fast",
    "trend_ema_slow",
    "market_regime",
}


class Reason(str, Enum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    NO_BREAKOUT = "NO_BREAKOUT"
    LONG_BREAKOUT = "LONG_BREAKOUT"
    SHORT_BREAKOUT = "SHORT_BREAKOUT"
    SHORT_ENTRIES_DISABLED = "SHORT_ENTRIES_DISABLED"
    ENTRY_BLOCKED_BY_REGIME = "ENTRY_BLOCKED_BY_REGIME"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    LONG_EXIT_CHANNEL = "LONG_EXIT_CHANNEL"
    SHORT_EXIT_CHANNEL = "SHORT_EXIT_CHANNEL"


class MarketRegime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = "donchian_breakout"
    strategy_version: str = "1.1.0"
    symbol: str = "ETHUSDT"
    signal_timeframe: str = "4h"
    entry_channel_period: int = 40
    exit_channel_period: int = 20
    atr_period: int = 14
    stop_atr_multiplier: float = 1.5
    allow_short_entries: bool = False
    trend_filter_enabled: bool = False
    trend_timeframe: str = "4h"
    trend_ema_fast_period: int = 50
    trend_ema_slow_period: int = 200


def _validate_config(config: StrategyConfig) -> None:
    periods = (
        config.entry_channel_period,
        config.exit_channel_period,
        config.atr_period,
        config.trend_ema_fast_period,
        config.trend_ema_slow_period,
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
    if config.signal_timeframe not in TIMEFRAME_DURATIONS:
        raise ValueError("Unsupported signal timeframe.")
    if config.trend_timeframe not in TIMEFRAME_DURATIONS:
        raise ValueError("Unsupported trend timeframe.")
    if config.trend_ema_fast_period >= config.trend_ema_slow_period:
        raise ValueError("Fast trend EMA must be shorter than slow trend EMA.")
    if not isinstance(config.allow_short_entries, bool):
        raise TypeError("allow_short_entries must be a boolean.")
    if not isinstance(config.trend_filter_enabled, bool):
        raise TypeError("trend_filter_enabled must be a boolean.")


def _prepare_market_regime(
    candles: pd.DataFrame,
    timeframe: str,
    config: StrategyConfig,
) -> pd.DataFrame:
    required = {"symbol", "timeframe", "open_time", "close"}
    missing = sorted(required - set(candles.columns))
    if missing:
        raise ValueError(
            "Trend candles are missing required columns: " + ", ".join(missing)
        )
    source = candles.copy(deep=True).sort_values("open_time").reset_index(
        drop=True
    )
    if source.empty:
        raise ValueError("Trend candles must not be empty.")
    if source["symbol"].nunique() != 1 or source.iloc[0]["symbol"] != config.symbol:
        raise ValueError("Trend candles have an unexpected symbol.")
    if source["timeframe"].nunique() != 1 or source.iloc[0]["timeframe"] != timeframe:
        raise ValueError("Trend candles have an unexpected timeframe.")

    source["trend_available_time"] = pd.to_datetime(
        source["open_time"],
        utc=True,
    ) + TIMEFRAME_DURATIONS[timeframe]
    source["trend_ema_fast"] = calculate_ema(
        source["close"],
        config.trend_ema_fast_period,
    )
    source["trend_ema_slow"] = calculate_ema(
        source["close"],
        config.trend_ema_slow_period,
    )
    trend_ready = source[["trend_ema_fast", "trend_ema_slow"]].notna().all(
        axis=1
    )
    bullish = (
        (source["trend_ema_fast"] > source["trend_ema_slow"])
        & (source["close"] > source["trend_ema_fast"])
    )
    bearish = (
        (source["trend_ema_fast"] < source["trend_ema_slow"])
        & (source["close"] < source["trend_ema_fast"])
    )
    source["market_regime"] = pd.Series(
        pd.NA,
        index=source.index,
        dtype="string",
    )
    source.loc[trend_ready, "market_regime"] = MarketRegime.NEUTRAL.value
    source.loc[trend_ready & bullish, "market_regime"] = MarketRegime.BULL.value
    source.loc[trend_ready & bearish, "market_regime"] = MarketRegime.BEAR.value
    return source[
        [
            "trend_available_time",
            "trend_ema_fast",
            "trend_ema_slow",
            "market_regime",
        ]
    ]


def prepare_market_data(
    candles: pd.DataFrame,
    config: StrategyConfig = StrategyConfig(),
    trend_candles: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Prepare closed signal candles and attach the latest closed trend."""
    _validate_config(config)
    if not isinstance(candles, pd.DataFrame):
        raise TypeError("candles must be a pandas DataFrame.")
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
        raise ValueError(
            "candles is missing required columns: " + ", ".join(missing)
        )

    prepared = candles.copy(deep=True)
    prepared = prepared.sort_values("open_time").reset_index(drop=True)
    if prepared.empty:
        raise ValueError("candles must not be empty.")
    if (
        prepared["symbol"].nunique() != 1
        or prepared.iloc[0]["symbol"] != config.symbol
        or prepared["timeframe"].nunique() != 1
        or prepared.iloc[0]["timeframe"] != config.signal_timeframe
    ):
        raise ValueError("Signal candles have an unexpected market identity.")
    expected_decision_time = pd.to_datetime(
        prepared["open_time"],
        utc=True,
    ) + TIMEFRAME_DURATIONS[config.signal_timeframe]
    if "decision_time" in prepared.columns:
        actual_decision_time = pd.to_datetime(
            prepared["decision_time"],
            utc=True,
        )
        if not actual_decision_time.equals(expected_decision_time):
            raise ValueError("Signal candle decision times are inconsistent.")
    prepared["decision_time"] = expected_decision_time
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

    if trend_candles is None:
        if config.trend_timeframe != config.signal_timeframe:
            raise ValueError("Separate trend candles are required.")
        trend_source = prepared
    else:
        if not isinstance(trend_candles, pd.DataFrame):
            raise TypeError("trend_candles must be a pandas DataFrame.")
        trend_source = trend_candles
    regime = _prepare_market_regime(
        trend_source,
        config.trend_timeframe,
        config,
    )
    prepared = pd.merge_asof(
        prepared.sort_values("decision_time"),
        regime.sort_values("trend_available_time"),
        left_on="decision_time",
        right_on="trend_available_time",
        direction="backward",
        allow_exact_matches=True,
    )
    return prepared.drop(columns="trend_available_time").reset_index(drop=True)


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
    if (
        row["symbol"] != config.symbol
        or row["timeframe"] != config.signal_timeframe
    ):
        raise ValueError("Strategy row has an unexpected market identity.")
    open_time = pd.Timestamp(row["open_time"])
    expected_decision_time = (
        open_time + TIMEFRAME_DURATIONS[config.signal_timeframe]
    )
    if pd.Timestamp(row["decision_time"]) != expected_decision_time:
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
        entry_timing=(
            f"NEXT_{config.signal_timeframe.upper()}_OPEN"
            if action is Action.OPEN_POSITION
            else None
        ),
        stop_distance=stop_distance,
        take_profit_r_multiple=None,
        supporting_values={
            "close": row["close"],
            "entry_channel_high": row["entry_channel_high"],
            "entry_channel_low": row["entry_channel_low"],
            "exit_channel_high": row["exit_channel_high"],
            "exit_channel_low": row["exit_channel_low"],
            "atr": row["signal_atr"],
            "trend_ema_fast": row["trend_ema_fast"],
            "trend_ema_slow": row["trend_ema_slow"],
            "market_regime": row["market_regime"],
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
    """Return one deterministic decision from a closed prepared candle."""
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
    if config.trend_filter_enabled:
        required_entry += (
            row["trend_ema_fast"],
            row["trend_ema_slow"],
        )
    required_values = required_entry + (
        (row["market_regime"],) if config.trend_filter_enabled else ()
    )
    if any(pd.isna(value) for value in required_values):
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
        if not config.allow_short_entries:
            return _build_decision(
                row=row,
                config=config,
                action=Action.NO_ACTION,
                side=None,
                reason=Reason.SHORT_ENTRIES_DISABLED,
            )
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

    if config.trend_filter_enabled:
        regime = MarketRegime(str(row["market_regime"]))
        allowed_regime = (
            MarketRegime.BULL if side is Side.LONG else MarketRegime.BEAR
        )
        if regime is not allowed_regime:
            return _build_decision(
                row=row,
                config=config,
                action=Action.NO_ACTION,
                side=None,
                reason=Reason.ENTRY_BLOCKED_BY_REGIME,
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
