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


DEVELOPMENT_START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
DEVELOPMENT_END = datetime.fromisoformat("2024-12-31T23:00:00+00:00")
WARMUP_START = datetime.fromisoformat("2024-09-01T00:00:00+00:00")
VALIDATION_START = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
VALIDATION_END = datetime.fromisoformat("2025-12-31T23:00:00+00:00")


def _quality_constraints() -> InstrumentConstraints:
    return InstrumentConstraints(
        min_order_qty=0.00000001,
        qty_step=0.00000001,
        min_notional=0.00000001,
        max_market_order_qty=1_000_000.0,
        tick_size=0.01,
        observed_at="QUALITY_MODE_WITHOUT_SIZE_LIMITS",
    )


def _prepare_period(
    strategy_config: StrategyConfig,
    load_start: datetime,
    load_end: datetime,
    result_start: datetime,
):
    candles_1h = load_candles_dataframe(
        strategy_config.symbol,
        "1h",
        load_start,
        load_end,
    )
    candles_4h = aggregate_closed_1h_to_4h(candles_1h)
    prepared = prepare_market_data(candles_4h, strategy_config)
    return prepared.loc[prepared["open_time"] >= result_start].reset_index(
        drop=True
    )


def _format_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _print_result(label: str, result) -> None:
    print(f"{label}:")
    for name, value in result.summary().items():
        print(f"{name}: {_format_value(value)}")


def main() -> None:
    strategy_config = StrategyConfig()
    evaluator = partial(
        evaluate_donchian_breakout,
        config=strategy_config,
    )

    development = _prepare_period(
        strategy_config,
        DEVELOPMENT_START,
        DEVELOPMENT_END,
        DEVELOPMENT_START,
    )
    development_config = BacktestConfig(
        starting_balance=10.0,
        risk_fraction=0.05,
        leverage=3.0,
    )
    development_result = run_backtest(
        development,
        evaluator,
        development_config,
    )
    development_summary = development_result.summary()
    if development_summary["end_of_data_exits"] != 0:
        raise RuntimeError(
            "Development ended with an open position; validation cannot start "
            "from a clean account boundary."
        )
    continuation_balance = float(development_summary["ending_balance"])

    validation = _prepare_period(
        strategy_config,
        WARMUP_START,
        VALIDATION_END,
        VALIDATION_START,
    )
    quality_config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        leverage=100.0,
        instrument=_quality_constraints(),
    )
    continuation_config = BacktestConfig(
        starting_balance=continuation_balance,
        risk_fraction=0.05,
        leverage=3.0,
    )

    quality_result = run_backtest(validation, evaluator, quality_config)
    continuation_result = run_backtest(
        validation,
        evaluator,
        continuation_config,
    )

    print("Donchian Breakout v1.1 frozen 2025 validation")
    print(
        "Parameters: entry=40, exit=20, ATR=14, "
        "stop=1.5 ATR, Long-only, no TP"
    )
    print("Costs: taker=0.055% per fill, slippage=0.050% per fill")
    print("Funding: 0.010% cost per crossed 8h interval")
    print(f"Validation candles: 4h={len(validation)}")
    print(f"Continuation balance at 2025 start: {continuation_balance:.6f} USDT")
    _print_result("Validation signal quality — 1000 USDT, 1% risk", quality_result)
    _print_result(
        "Executable continuation — 5% risk, 3x",
        continuation_result,
    )


if __name__ == "__main__":
    main()
