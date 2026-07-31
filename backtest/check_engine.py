from dataclasses import replace

import pandas as pd

from backtest.engine import BacktestConfig, ExitReason, run_backtest
from strategies.models import (
    Action,
    PositionState,
    Side,
    StrategyDecision,
)


def _candles(*, stop_hit: bool = False) -> pd.DataFrame:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rows = []
    commands = ("OPEN", "HOLD", "CLOSE", "NONE", "NONE")
    for index, command in enumerate(commands):
        open_time = start + pd.Timedelta(hours=4 * index)
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "open_time": open_time,
                "open": 100.0 if index < 2 else (102.0 if index == 2 else 107.0),
                "high": 104.0 if index < 2 else 109.0,
                "low": 94.0 if stop_hit and index == 1 else 96.0,
                "close": 102.0 if index < 2 else 108.0,
                "decision_time": open_time + pd.Timedelta(hours=4),
                "command": command,
            }
        )
    return pd.DataFrame(rows)


def _decision(
    row: pd.Series,
    position: PositionState | None,
) -> StrategyDecision:
    command = row["command"]
    if position is None and command == "OPEN":
        action = Action.OPEN_POSITION
        side = Side.LONG
        stop_distance = 5.0
    elif position is not None and command == "CLOSE":
        action = Action.CLOSE_POSITION
        side = position.side
        stop_distance = None
    elif position is not None:
        action = Action.HOLD_POSITION
        side = position.side
        stop_distance = None
    else:
        action = Action.NO_ACTION
        side = None
        stop_distance = None
    return StrategyDecision(
        decision_id=f"decision-{row['open_time'].isoformat()}-{action.value}",
        strategy_id="engine_check",
        strategy_version="1.0.0",
        symbol="ETHUSDT",
        signal_timeframe="4h",
        signal_candle_open_time=row["open_time"],
        decision_time=row["decision_time"],
        execute_at=row["decision_time"],
        action=action,
        side=side,
        reason=command,
        entry_timing="NEXT_4H_OPEN" if action is Action.OPEN_POSITION else None,
        stop_distance=stop_distance,
        take_profit_r_multiple=None,
        supporting_values={},
    )


def check_strategy_exit() -> None:
    config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        taker_fee_rate=0.0,
        slippage_rate=0.0,
        funding_rate_per_interval=0.0,
    )
    result = run_backtest(_candles(), _decision, config)
    if len(result.trades) != 1:
        raise AssertionError("Expected exactly one strategy-exit trade.")
    trade = result.trades[0]
    expected_entry = pd.Timestamp("2023-01-01 04:00:00", tz="UTC")
    expected_exit = pd.Timestamp("2023-01-01 12:00:00", tz="UTC")
    if trade.entry_time != expected_entry:
        raise AssertionError("Engine did not enter at the next candle open.")
    if trade.exit_time != expected_exit:
        raise AssertionError("Engine did not exit at the next candle open.")
    if trade.exit_reason is not ExitReason.STRATEGY_EXIT:
        raise AssertionError("Strategy exit reason was not recorded.")
    if trade.take_profit is not None:
        raise AssertionError("Engine created an unrequested take profit.")


def check_stop_and_costs() -> None:
    no_cost_config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        taker_fee_rate=0.0,
        slippage_rate=0.0,
        funding_rate_per_interval=0.0,
    )
    stop_result = run_backtest(
        _candles(stop_hit=True),
        _decision,
        no_cost_config,
    )
    if stop_result.trades[0].exit_reason is not ExitReason.STOP_LOSS:
        raise AssertionError("Protective stop was not executed.")

    fee_result = run_backtest(
        _candles(),
        _decision,
        replace(no_cost_config, taker_fee_rate=0.001),
    )
    trade = fee_result.trades[0]
    if trade.fees <= 0 or trade.net_pnl >= trade.gross_pnl:
        raise AssertionError("Trading fees were not deducted.")


def main() -> None:
    check_strategy_exit()
    check_stop_and_costs()
    print("Backtest engine checks passed:")
    print("Entry at next candle open: True")
    print("Protective stop execution: True")
    print("Strategy exit at next candle open: True")
    print("Optional take profit: True")
    print("Trading fees deducted: True")


if __name__ == "__main__":
    main()
