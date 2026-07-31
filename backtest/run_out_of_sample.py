import math
from datetime import datetime, timedelta, timezone
from functools import partial

from backtest.engine import BacktestConfig, run_backtest
from backtest.run_validation import _prepare_period, _quality_constraints
from strategies.donchian_breakout.strategy import (
    StrategyConfig,
    evaluate_donchian_breakout,
)


DEVELOPMENT_START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
DEVELOPMENT_END = datetime.fromisoformat("2024-12-31T23:00:00+00:00")
VALIDATION_WARMUP_START = datetime.fromisoformat("2024-09-01T00:00:00+00:00")
VALIDATION_START = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
VALIDATION_END = datetime.fromisoformat("2025-12-31T23:00:00+00:00")
OOS_WARMUP_START = datetime.fromisoformat("2025-09-01T00:00:00+00:00")
OOS_START = datetime.fromisoformat("2026-01-01T00:00:00+00:00")


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


def _require_clean_boundary(label: str, result) -> float:
    summary = result.summary()
    if summary["end_of_data_exits"] != 0:
        raise RuntimeError(
            f"{label} ended with an open position; the next period cannot "
            "start from a clean account boundary."
        )
    return float(summary["ending_balance"])


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
    development_result = run_backtest(
        development,
        evaluator,
        BacktestConfig(
            starting_balance=10.0,
            risk_fraction=0.05,
            leverage=3.0,
        ),
    )
    validation_starting_balance = _require_clean_boundary(
        "Development",
        development_result,
    )

    validation = _prepare_period(
        strategy_config,
        VALIDATION_WARMUP_START,
        VALIDATION_END,
        VALIDATION_START,
    )
    validation_result = run_backtest(
        validation,
        evaluator,
        BacktestConfig(
            starting_balance=validation_starting_balance,
            risk_fraction=0.05,
            leverage=3.0,
        ),
    )
    oos_starting_balance = _require_clean_boundary(
        "Validation",
        validation_result,
    )

    oos = _prepare_period(
        strategy_config,
        OOS_WARMUP_START,
        datetime.now(timezone.utc),
        OOS_START,
    )
    if oos.empty:
        raise RuntimeError("No closed 4h candles are available for 2026.")

    quality_result = run_backtest(
        oos,
        evaluator,
        BacktestConfig(
            starting_balance=1000.0,
            risk_fraction=0.01,
            leverage=100.0,
            instrument=_quality_constraints(),
        ),
    )
    continuation_result = run_backtest(
        oos,
        evaluator,
        BacktestConfig(
            starting_balance=oos_starting_balance,
            risk_fraction=0.05,
            leverage=3.0,
        ),
    )

    print("Donchian Breakout v1.1 frozen 2026 out-of-sample")
    print(
        "Parameters: entry=40, exit=20, ATR=14, "
        "stop=1.5 ATR, Long-only, no TP"
    )
    print("Costs: taker=0.055% per fill, slippage=0.050% per fill")
    print("Funding: 0.010% cost per crossed 8h interval")
    last_closed_time = oos.iloc[-1]["open_time"] + timedelta(hours=4)
    print(f"Period: {OOS_START} -> {last_closed_time}")
    print(f"Out-of-sample candles: 4h={len(oos)}")
    print(
        "Continuous executable balance: "
        f"10.000000 -> {validation_starting_balance:.6f} -> "
        f"{oos_starting_balance:.6f} USDT"
    )
    _print_result(
        "Out-of-sample signal quality — 1000 USDT, 1% risk",
        quality_result,
    )
    _print_result(
        "Executable continuation — 5% risk, 3x",
        continuation_result,
    )


if __name__ == "__main__":
    main()
