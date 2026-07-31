from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Action(str, Enum):
    NO_ACTION = "NO_ACTION"
    OPEN_POSITION = "OPEN_POSITION"
    HOLD_POSITION = "HOLD_POSITION"
    CLOSE_POSITION = "CLOSE_POSITION"


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


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
    reason: str
    entry_timing: str | None
    stop_distance: float | None
    take_profit_r_multiple: float | None
    supporting_values: dict[str, Any]
