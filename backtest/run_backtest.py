import math
from datetime import datetime
from functools import partial

from backtest.engine import (
    BacktestConfig,
    InstrumentConstraints,
    run_backtest,
)
from market_data.data_access import load_candles_dataframe
from strategies.donchian_breakout.strategy import (
    StrategyConfig,
    evaluate_donchian_breakout,
    prepare_market_data,
)
from strategies.timeframes import aggregate_closed_1h_to_4h


START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
END = datetime.fromisoformat("2024-12-31T23:00:00+00:00")


def _format_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _quality_constraints() -> InstrumentConstraints:
    return InstrumentConstraints(
        min_order_qty=0.00000001,
        qty_step=0.00000001,
        min_notional=0.00000001,
        max_market_order_qty=1_000_000.0,
        tick_size=0.01,
        observed_at="QUALITY_MODE_WITHOUT_SIZE_LIMITS",
    )


def _print_result(label: str, result) -> None:
    print(f"{label}:")
    for name, value in result.summary().items():
        print(f"{name}: {_format_value(value)}")
    for year in (2023, 2024):
        trades = [
            trade for trade in result.trades if trade.entry_time.year == year
        ]
        net_values = [trade.net_pnl for trade in trades]
        profit = sum(value for value in net_values if value > 0)
        loss = abs(sum(value for value in net_values if value < 0))
        profit_factor = (
            profit / loss
            if loss > 0
            else (math.inf if profit > 0 else None)
        )
        total_net_r = sum(
            trade.net_pnl / trade.risk_budget for trade in trades
        )
        print(
            f"year_{year}: trades={len(trades)}, "
            f"net_pnl={sum(net_values):.6f}, "
            f"net_r={total_net_r:.6f}, "
            f"profit_factor={_format_value(profit_factor)}"
        )


def main() -> None:
    strategy_config = StrategyConfig()
    candles_1h = load_candles_dataframe(
        strategy_config.symbol,
        "1h",
        START,
        END,
    )
    candles_4h = aggregate_closed_1h_to_4h(candles_1h)
    prepared = prepare_market_data(candles_4h, strategy_config)
    evaluator = partial(
        evaluate_donchian_breakout,
        config=strategy_config,
    )

    quality_config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        leverage=100.0,
        instrument=_quality_constraints(),
    )
    real_config = BacktestConfig(
        starting_balance=10.0,
        risk_fraction=0.05,
        leverage=3.0,
    )

    print("Donchian Breakout frozen development configuration")
    print(f"Period: {START} -> {END}")
    print(
        "Parameters: "
        f"entry={strategy_config.entry_channel_period}, "
        f"exit={strategy_config.exit_channel_period}, "
        f"ATR={strategy_config.atr_period}, "
        f"stop={strategy_config.stop_atr_multiplier} ATR, "
        "Long-only, no TP"
    )
    print("Costs: taker=0.055% per fill, slippage=0.050% per fill")
    print("Funding: 0.010% cost per crossed 8h interval")
    print(f"Prepared candles: 1h={len(candles_1h)}, 4h={len(candles_4h)}")

    quality_result = run_backtest(prepared, evaluator, quality_config)
    real_result = run_backtest(prepared, evaluator, real_config)
    _print_result("Quality mode — 1000 USDT, 1% risk, size filters neutralized", quality_result)
    _print_result("Executable mode — 10 USDT, 5% risk, 3x", real_result)


if __name__ == "__main__":
    main()
