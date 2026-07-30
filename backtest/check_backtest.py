from dataclasses import replace

import pandas as pd

from backtest.engine import (
    BacktestConfig,
    ExitReason,
    run_backtest,
)
from strategies.ema_trend_pullback import (
    Action,
    PositionState,
    Reason,
    Side,
    evaluate_ema_trend_pullback,
)


def _strategy_row(
    open_time: str,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
    signal_ema: float,
    signal_atr: float,
    trend_close: float,
    trend_fast: float,
    trend_slow: float,
) -> pd.Series:
    timestamp = pd.Timestamp(open_time, tz="UTC")
    decision_time = timestamp + pd.Timedelta(minutes=15)
    return pd.Series(
        {
            "symbol": "ETHUSDT",
            "timeframe": "15m",
            "open_time": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "decision_time": decision_time,
            "signal_ema": signal_ema,
            "signal_atr": signal_atr,
            "trend_open_time": timestamp.floor("h") - pd.Timedelta(hours=1),
            "trend_available_time": timestamp.floor("h"),
            "trend_close": trend_close,
            "trend_fast_ema": trend_fast,
            "trend_slow_ema": trend_slow,
        }
    )


def check_strategy_decisions() -> None:
    long_pullback = _strategy_row(
        "2023-01-01 10:00:00",
        open_price=101.0,
        high=102.0,
        low=99.0,
        close=100.0,
        signal_ema=100.0,
        signal_atr=2.0,
        trend_close=120.0,
        trend_fast=110.0,
        trend_slow=100.0,
    )
    long_confirmation = _strategy_row(
        "2023-01-01 10:15:00",
        open_price=102.0,
        high=104.0,
        low=101.0,
        close=103.0,
        signal_ema=100.0,
        signal_atr=2.0,
        trend_close=120.0,
        trend_fast=110.0,
        trend_slow=100.0,
    )
    long_decision = evaluate_ema_trend_pullback(
        long_pullback,
        long_confirmation,
    )
    repeated_long = evaluate_ema_trend_pullback(
        long_pullback,
        long_confirmation,
    )
    if (
        long_decision.action is not Action.OPEN_POSITION
        or long_decision.side is not Side.LONG
        or long_decision.reason is not Reason.LONG_SETUP_CONFIRMED
        or long_decision.stop_distance != 3.0
    ):
        raise AssertionError("Expected Long decision was not produced.")
    if long_decision.decision_id != repeated_long.decision_id:
        raise AssertionError("Strategy decision ID is not deterministic.")

    short_pullback = _strategy_row(
        "2023-01-01 11:00:00",
        open_price=99.0,
        high=101.0,
        low=98.0,
        close=100.0,
        signal_ema=100.0,
        signal_atr=2.0,
        trend_close=80.0,
        trend_fast=90.0,
        trend_slow=100.0,
    )
    short_confirmation = _strategy_row(
        "2023-01-01 11:15:00",
        open_price=98.0,
        high=99.0,
        low=96.0,
        close=97.0,
        signal_ema=100.0,
        signal_atr=2.0,
        trend_close=80.0,
        trend_fast=90.0,
        trend_slow=100.0,
    )
    short_decision = evaluate_ema_trend_pullback(
        short_pullback,
        short_confirmation,
    )
    if (
        short_decision.action is not Action.OPEN_POSITION
        or short_decision.side is not Side.SHORT
        or short_decision.reason is not Reason.SHORT_SETUP_CONFIRMED
    ):
        raise AssertionError("Expected Short decision was not produced.")

    hold_state = PositionState(
        side=Side.LONG,
        entry_time=long_confirmation["decision_time"],
        holding_candles=31,
    )
    close_state = replace(hold_state, holding_candles=32)
    hold_decision = evaluate_ema_trend_pullback(
        long_pullback,
        long_confirmation,
        hold_state,
    )
    close_decision = evaluate_ema_trend_pullback(
        long_pullback,
        long_confirmation,
        close_state,
    )
    if hold_decision.action is not Action.HOLD_POSITION:
        raise AssertionError("Open position was not held.")
    if close_decision.action is not Action.CLOSE_POSITION:
        raise AssertionError("Maximum holding time did not close the position.")

    neutral_confirmation = long_confirmation.copy()
    neutral_confirmation["trend_close"] = 100.0
    neutral_confirmation["trend_fast_ema"] = 100.0
    neutral_confirmation["trend_slow_ema"] = 100.0
    no_action = evaluate_ema_trend_pullback(
        long_pullback,
        neutral_confirmation,
    )
    if (
        no_action.action is not Action.NO_ACTION
        or no_action.reason is not Reason.TREND_NOT_PERMITTED
    ):
        raise AssertionError("Neutral trend did not produce no action.")

    warmup_confirmation = long_confirmation.copy()
    warmup_confirmation["trend_slow_ema"] = float("nan")
    warmup = evaluate_ema_trend_pullback(
        long_pullback,
        warmup_confirmation,
    )
    if (
        warmup.action is not Action.NO_ACTION
        or warmup.reason is not Reason.INSUFFICIENT_HISTORY
    ):
        raise AssertionError("Indicator warm-up did not produce no action.")


def _engine_candles(*, touch_stop_and_target: bool) -> pd.DataFrame:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rows = []
    for index in range(8):
        open_time = start + pd.Timedelta(minutes=15 * index)
        row = {
            "symbol": "ETHUSDT",
            "timeframe": "15m",
            "open_time": open_time,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "decision_time": open_time + pd.Timedelta(minutes=15),
            "signal_ema": 100.0,
            "signal_atr": 2.0,
            "trend_open_time": start - pd.Timedelta(hours=1),
            "trend_available_time": start,
            "trend_close": 100.0,
            "trend_fast_ema": 100.0,
            "trend_slow_ema": 100.0,
        }
        rows.append(row)

    rows[1].update(
        {"open": 101.0, "high": 102.0, "low": 99.0, "close": 100.0}
    )
    rows[2].update(
        {
            "open": 102.0,
            "high": 104.0,
            "low": 101.0,
            "close": 103.0,
            "trend_close": 120.0,
            "trend_fast_ema": 110.0,
            "trend_slow_ema": 100.0,
        }
    )
    rows[3].update(
        {
            "open": 104.0,
            "high": 111.0,
            "low": 100.0 if touch_stop_and_target else 103.0,
            "close": 108.0,
        }
    )
    return pd.DataFrame(rows)


def check_sequential_engine() -> None:
    base_config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        taker_fee_rate=0.0,
        slippage_rate=0.0,
        funding_rate_per_interval=0.0,
    )
    target_result = run_backtest(
        _engine_candles(touch_stop_and_target=False),
        base_config,
    )
    if len(target_result.trades) != 1:
        raise AssertionError("Expected exactly one synthetic trade.")
    target_trade = target_result.trades[0]
    expected_entry_time = pd.Timestamp(
        "2023-01-01 00:45:00",
        tz="UTC",
    )
    if target_trade.entry_time != expected_entry_time:
        raise AssertionError("Trade did not enter on the next candle.")
    if target_trade.exit_reason is not ExitReason.TAKE_PROFIT:
        raise AssertionError("Synthetic target was not executed.")

    collision_result = run_backtest(
        _engine_candles(touch_stop_and_target=True),
        base_config,
    )
    if collision_result.trades[0].exit_reason is not ExitReason.STOP_LOSS:
        raise AssertionError("Same-candle SL/TP did not resolve to stop-loss.")

    fee_config = replace(base_config, taker_fee_rate=0.001)
    fee_result = run_backtest(
        _engine_candles(touch_stop_and_target=False),
        fee_config,
    )
    fee_trade = fee_result.trades[0]
    if fee_trade.fees <= 0 or fee_trade.net_pnl >= fee_trade.gross_pnl:
        raise AssertionError("Trading fees were not deducted.")


def main() -> None:
    check_strategy_decisions()
    check_sequential_engine()

    print("Strategy and backtest checks passed:")
    print("Long decision: True")
    print("Short decision: True")
    print("Deterministic decision ID: True")
    print("No-action and warm-up decisions: True")
    print("Hold and time-exit decisions: True")
    print("Entry on next candle: True")
    print("Take-profit execution: True")
    print("Same-candle SL/TP resolves to stop-loss: True")
    print("Trading fees deducted: True")


if __name__ == "__main__":
    main()
