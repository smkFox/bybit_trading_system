import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from enum import Enum

import pandas as pd

from strategies.ema_trend_pullback import (
    Action,
    PositionState,
    Side,
    StrategyConfig,
    evaluate_ema_trend_pullback,
)


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_EXIT = "TIME_EXIT"
    END_OF_DATA = "END_OF_DATA"


class RejectionReason(str, Enum):
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    BELOW_MINIMUM_NOTIONAL = "BELOW_MINIMUM_NOTIONAL"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    INVALID_QUANTITY = "INVALID_QUANTITY"


@dataclass(frozen=True)
class InstrumentConstraints:
    min_order_qty: float = 0.01
    qty_step: float = 0.01
    min_notional: float = 5.0
    max_market_order_qty: float = 2000.0
    tick_size: float = 0.01
    observed_at: str = "2026-07-30"


@dataclass(frozen=True)
class BacktestConfig:
    starting_balance: float = 10.0
    risk_fraction: float = 0.01
    leverage: float = 3.0
    taker_fee_rate: float = 0.00055
    slippage_rate: float = 0.0005
    funding_rate_per_interval: float = 0.0001
    funding_interval_hours: int = 8
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    instrument: InstrumentConstraints = field(
        default_factory=InstrumentConstraints
    )


@dataclass
class OpenPosition:
    side: Side
    quantity: float
    entry_time: datetime
    entry_index: int
    entry_price: float
    entry_notional: float
    entry_fee: float
    margin: float
    stop_loss: float
    take_profit: float
    risk_budget: float
    decision_id: str


@dataclass(frozen=True)
class Trade:
    side: Side
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    notional: float
    margin: float
    stop_loss: float
    take_profit: float
    exit_reason: ExitReason
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    balance_after: float
    decision_id: str


@dataclass(frozen=True)
class RejectedEntry:
    decision_time: datetime
    side: Side
    reason: RejectionReason
    raw_quantity: float
    risk_budget: float
    expected_entry_price: float
    decision_id: str


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list[Trade]
    rejected_entries: list[RejectedEntry]
    entry_signals: int

    def summary(self) -> dict[str, float | int | str | None]:
        starting = self.config.starting_balance
        ending = (
            self.trades[-1].balance_after if self.trades else starting
        )
        net_results = [trade.net_pnl for trade in self.trades]
        wins = [value for value in net_results if value > 0]
        losses = [value for value in net_results if value < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (math.inf if gross_profit > 0 else None)
        )

        peak = starting
        maximum_drawdown = 0.0
        for trade in self.trades:
            peak = max(peak, trade.balance_after)
            if peak > 0:
                drawdown = (peak - trade.balance_after) / peak
                maximum_drawdown = max(maximum_drawdown, drawdown)

        longest_losing_streak = 0
        current_losing_streak = 0
        for value in net_results:
            if value < 0:
                current_losing_streak += 1
                longest_losing_streak = max(
                    longest_losing_streak,
                    current_losing_streak,
                )
            else:
                current_losing_streak = 0

        rejection_counts = Counter(
            rejection.reason.value for rejection in self.rejected_entries
        )
        exit_counts = Counter(trade.exit_reason.value for trade in self.trades)
        long_trades = [trade for trade in self.trades if trade.side is Side.LONG]
        short_trades = [
            trade for trade in self.trades if trade.side is Side.SHORT
        ]

        return {
            "starting_balance": starting,
            "ending_balance": ending,
            "gross_pnl": sum(trade.gross_pnl for trade in self.trades),
            "net_pnl": ending - starting,
            "return_percent": ((ending / starting) - 1) * 100,
            "entry_signals": self.entry_signals,
            "trade_count": len(self.trades),
            "rejected_entries": len(self.rejected_entries),
            "long_trades": len(long_trades),
            "short_trades": len(short_trades),
            "long_net_pnl": sum(trade.net_pnl for trade in long_trades),
            "short_net_pnl": sum(trade.net_pnl for trade in short_trades),
            "win_rate_percent": (
                len(wins) / len(self.trades) * 100
                if self.trades
                else None
            ),
            "average_trade": (
                sum(net_results) / len(net_results) if net_results else None
            ),
            "expectancy": (
                sum(net_results) / len(net_results) if net_results else None
            ),
            "profit_factor": profit_factor,
            "closed_equity_max_drawdown_percent": maximum_drawdown * 100,
            "longest_losing_streak": longest_losing_streak,
            "total_fees": sum(trade.fees for trade in self.trades),
            "total_funding": sum(trade.funding for trade in self.trades),
            "stop_loss_exits": exit_counts[ExitReason.STOP_LOSS.value],
            "take_profit_exits": exit_counts[ExitReason.TAKE_PROFIT.value],
            "time_exits": exit_counts[ExitReason.TIME_EXIT.value],
            "end_of_data_exits": exit_counts[ExitReason.END_OF_DATA.value],
            "risk_rejections": rejection_counts[
                RejectionReason.RISK_LIMIT_EXCEEDED.value
            ],
            "notional_rejections": rejection_counts[
                RejectionReason.BELOW_MINIMUM_NOTIONAL.value
            ],
            "margin_rejections": rejection_counts[
                RejectionReason.INSUFFICIENT_MARGIN.value
            ],
            "quantity_rejections": rejection_counts[
                RejectionReason.INVALID_QUANTITY.value
            ],
            "instrument_constraints_observed_at": (
                self.config.instrument.observed_at
            ),
        }


def _validate_config(config: BacktestConfig) -> None:
    if config.starting_balance <= 0:
        raise ValueError("Starting balance must be positive.")
    if not 0 < config.risk_fraction <= 1:
        raise ValueError("Risk fraction must be between 0 and 1.")
    if config.leverage < 1:
        raise ValueError("Leverage must be at least 1.")
    if config.taker_fee_rate < 0 or config.slippage_rate < 0:
        raise ValueError("Fees and slippage must not be negative.")
    if config.funding_rate_per_interval < 0:
        raise ValueError("Funding rate must not be negative.")
    if config.funding_interval_hours < 1:
        raise ValueError("Funding interval must be positive.")

    instrument = config.instrument
    positive_constraints = (
        instrument.min_order_qty,
        instrument.qty_step,
        instrument.min_notional,
        instrument.max_market_order_qty,
        instrument.tick_size,
    )
    if any(value <= 0 for value in positive_constraints):
        raise ValueError("Instrument constraints must be positive.")


def _round_to_step(value: float, step: float, rounding: str) -> float:
    decimal_value = Decimal(str(value))
    decimal_step = Decimal(str(step))
    rounding_mode = ROUND_FLOOR if rounding == "floor" else ROUND_CEILING
    steps = (decimal_value / decimal_step).to_integral_value(
        rounding=rounding_mode
    )
    return float(steps * decimal_step)


def _entry_fill_price(
    market_price: float,
    side: Side,
    config: BacktestConfig,
) -> float:
    multiplier = (
        1 + config.slippage_rate
        if side is Side.LONG
        else 1 - config.slippage_rate
    )
    raw_price = market_price * multiplier
    rounding = "ceil" if side is Side.LONG else "floor"
    return _round_to_step(raw_price, config.instrument.tick_size, rounding)


def _exit_fill_price(
    market_price: float,
    side: Side,
    config: BacktestConfig,
) -> float:
    multiplier = (
        1 - config.slippage_rate
        if side is Side.LONG
        else 1 + config.slippage_rate
    )
    raw_price = market_price * multiplier
    rounding = "floor" if side is Side.LONG else "ceil"
    return _round_to_step(raw_price, config.instrument.tick_size, rounding)


def _protective_prices(
    entry_price: float,
    stop_distance: float,
    take_profit_multiple: float,
    side: Side,
    tick_size: float,
) -> tuple[float, float]:
    if side is Side.LONG:
        stop = _round_to_step(
            entry_price - stop_distance,
            tick_size,
            "floor",
        )
        target = _round_to_step(
            entry_price + stop_distance * take_profit_multiple,
            tick_size,
            "floor",
        )
    else:
        stop = _round_to_step(
            entry_price + stop_distance,
            tick_size,
            "ceil",
        )
        target = _round_to_step(
            entry_price - stop_distance * take_profit_multiple,
            tick_size,
            "ceil",
        )
    if stop <= 0 or target <= 0:
        raise ValueError("Protective prices must be positive.")
    return stop, target


def _estimated_stop_loss_per_unit(
    entry_price: float,
    stop_loss: float,
    side: Side,
    config: BacktestConfig,
) -> float:
    stop_fill = _exit_fill_price(stop_loss, side, config)
    gross_loss = abs(entry_price - stop_fill)
    fees = (
        entry_price * config.taker_fee_rate
        + stop_fill * config.taker_fee_rate
    )
    conservative_funding = (
        entry_price * config.funding_rate_per_interval
    )
    return gross_loss + fees + conservative_funding


def _attempt_entry(
    *,
    decision,
    next_row: pd.Series,
    next_index: int,
    balance: float,
    config: BacktestConfig,
) -> tuple[OpenPosition | None, RejectedEntry | None]:
    side = decision.side
    if side is None or decision.stop_distance is None:
        raise ValueError("Open decision is missing side or stop distance.")

    expected_entry = _entry_fill_price(float(next_row["open"]), side, config)
    stop_loss, take_profit = _protective_prices(
        entry_price=expected_entry,
        stop_distance=decision.stop_distance,
        take_profit_multiple=decision.take_profit_r_multiple,
        side=side,
        tick_size=config.instrument.tick_size,
    )
    risk_budget = balance * config.risk_fraction
    risk_per_unit = _estimated_stop_loss_per_unit(
        expected_entry,
        stop_loss,
        side,
        config,
    )
    raw_quantity = risk_budget / risk_per_unit
    quantity = _round_to_step(
        raw_quantity,
        config.instrument.qty_step,
        "floor",
    )

    def rejection(reason: RejectionReason) -> RejectedEntry:
        return RejectedEntry(
            decision_time=decision.decision_time,
            side=side,
            reason=reason,
            raw_quantity=raw_quantity,
            risk_budget=risk_budget,
            expected_entry_price=expected_entry,
            decision_id=decision.decision_id,
        )

    if quantity < config.instrument.min_order_qty:
        return None, rejection(RejectionReason.RISK_LIMIT_EXCEEDED)
    if quantity > config.instrument.max_market_order_qty:
        return None, rejection(RejectionReason.INVALID_QUANTITY)

    notional = quantity * expected_entry
    if notional < config.instrument.min_notional:
        return None, rejection(RejectionReason.BELOW_MINIMUM_NOTIONAL)

    stop_fill = _exit_fill_price(stop_loss, side, config)
    all_in_stop_loss = (
        abs(expected_entry - stop_fill) * quantity
        + expected_entry * quantity * config.taker_fee_rate
        + stop_fill * quantity * config.taker_fee_rate
        + notional * config.funding_rate_per_interval
    )
    if all_in_stop_loss > risk_budget + 1e-12:
        return None, rejection(RejectionReason.RISK_LIMIT_EXCEEDED)

    entry_fee = notional * config.taker_fee_rate
    estimated_close_fee = notional * config.taker_fee_rate
    funding_reserve = notional * config.funding_rate_per_interval
    margin = notional / config.leverage
    if margin + entry_fee + estimated_close_fee + funding_reserve > balance:
        return None, rejection(RejectionReason.INSUFFICIENT_MARGIN)

    return (
        OpenPosition(
            side=side,
            quantity=quantity,
            entry_time=next_row["open_time"],
            entry_index=next_index,
            entry_price=expected_entry,
            entry_notional=notional,
            entry_fee=entry_fee,
            margin=margin,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_budget=risk_budget,
            decision_id=decision.decision_id,
        ),
        None,
    )


def _price_exit(
    position: OpenPosition,
    candle: pd.Series,
) -> tuple[ExitReason, float] | None:
    candle_open = float(candle["open"])
    candle_high = float(candle["high"])
    candle_low = float(candle["low"])

    if position.side is Side.LONG:
        if candle_open <= position.stop_loss:
            return ExitReason.STOP_LOSS, candle_open
        if candle_open >= position.take_profit:
            return ExitReason.TAKE_PROFIT, candle_open
        stop_hit = candle_low <= position.stop_loss
        target_hit = candle_high >= position.take_profit
    else:
        if candle_open >= position.stop_loss:
            return ExitReason.STOP_LOSS, candle_open
        if candle_open <= position.take_profit:
            return ExitReason.TAKE_PROFIT, candle_open
        stop_hit = candle_high >= position.stop_loss
        target_hit = candle_low <= position.take_profit

    if stop_hit:
        return ExitReason.STOP_LOSS, position.stop_loss
    if target_hit:
        return ExitReason.TAKE_PROFIT, position.take_profit
    return None


def _funding_events(
    entry_time: datetime,
    exit_time: datetime,
    interval_hours: int,
) -> int:
    interval_seconds = interval_hours * 60 * 60
    entry_slot = int(pd.Timestamp(entry_time).timestamp()) // interval_seconds
    exit_slot = int(pd.Timestamp(exit_time).timestamp()) // interval_seconds
    return max(0, exit_slot - entry_slot)


def _close_position(
    *,
    position: OpenPosition,
    market_exit_price: float,
    exit_time: datetime,
    exit_reason: ExitReason,
    balance: float,
    config: BacktestConfig,
) -> tuple[Trade, float]:
    exit_price = _exit_fill_price(
        market_exit_price,
        position.side,
        config,
    )
    exit_notional = position.quantity * exit_price
    if position.side is Side.LONG:
        gross_pnl = (
            exit_price - position.entry_price
        ) * position.quantity
    else:
        gross_pnl = (
            position.entry_price - exit_price
        ) * position.quantity

    exit_fee = exit_notional * config.taker_fee_rate
    funding_count = _funding_events(
        position.entry_time,
        exit_time,
        config.funding_interval_hours,
    )
    funding = (
        position.entry_notional
        * config.funding_rate_per_interval
        * funding_count
    )
    fees = position.entry_fee + exit_fee
    net_pnl = gross_pnl - fees - funding
    balance_after = balance + net_pnl

    return (
        Trade(
            side=position.side,
            entry_time=position.entry_time,
            exit_time=exit_time,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            notional=position.entry_notional,
            margin=position.margin,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            fees=fees,
            funding=funding,
            net_pnl=net_pnl,
            balance_after=balance_after,
            decision_id=position.decision_id,
        ),
        balance_after,
    )


def run_backtest(
    prepared_candles: pd.DataFrame,
    config: BacktestConfig = BacktestConfig(),
) -> BacktestResult:
    """Run one sequential, one-position EMA Trend Pullback backtest."""
    _validate_config(config)
    if not isinstance(prepared_candles, pd.DataFrame):
        raise TypeError("prepared_candles must be a pandas DataFrame.")
    if len(prepared_candles) < 3:
        raise ValueError("Backtest requires at least three prepared candles.")

    candles = prepared_candles.sort_values("open_time").reset_index(drop=True)
    balance = config.starting_balance
    position: OpenPosition | None = None
    trades: list[Trade] = []
    rejected_entries: list[RejectedEntry] = []
    entry_signals = 0

    for index in range(1, len(candles)):
        pullback_row = candles.iloc[index - 1]
        confirmation_row = candles.iloc[index]

        if position is not None:
            price_exit = _price_exit(position, confirmation_row)
            if price_exit is not None:
                exit_reason, market_price = price_exit
                trade, balance = _close_position(
                    position=position,
                    market_exit_price=market_price,
                    exit_time=confirmation_row["decision_time"],
                    exit_reason=exit_reason,
                    balance=balance,
                    config=config,
                )
                trades.append(trade)
                position = None

        if position is not None:
            holding_candles = index - position.entry_index + 1
            position_state = PositionState(
                side=position.side,
                entry_time=position.entry_time,
                holding_candles=holding_candles,
            )
            decision = evaluate_ema_trend_pullback(
                pullback_row,
                confirmation_row,
                position_state,
                config.strategy,
            )
            if (
                decision.action is Action.CLOSE_POSITION
                and index + 1 < len(candles)
            ):
                next_row = candles.iloc[index + 1]
                trade, balance = _close_position(
                    position=position,
                    market_exit_price=float(next_row["open"]),
                    exit_time=next_row["open_time"],
                    exit_reason=ExitReason.TIME_EXIT,
                    balance=balance,
                    config=config,
                )
                trades.append(trade)
                position = None
            continue

        if index + 1 >= len(candles):
            continue

        decision = evaluate_ema_trend_pullback(
            pullback_row,
            confirmation_row,
            None,
            config.strategy,
        )
        if decision.action is not Action.OPEN_POSITION:
            continue

        entry_signals += 1
        position, rejection = _attempt_entry(
            decision=decision,
            next_row=candles.iloc[index + 1],
            next_index=index + 1,
            balance=balance,
            config=config,
        )
        if rejection is not None:
            rejected_entries.append(rejection)

    if position is not None:
        final_candle = candles.iloc[-1]
        trade, balance = _close_position(
            position=position,
            market_exit_price=float(final_candle["close"]),
            exit_time=final_candle["decision_time"],
            exit_reason=ExitReason.END_OF_DATA,
            balance=balance,
            config=config,
        )
        trades.append(trade)

    return BacktestResult(
        config=config,
        trades=trades,
        rejected_entries=rejected_entries,
        entry_signals=entry_signals,
    )
