from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

import pandas as pd

from backtest.engine import BacktestConfig, run_backtest
from backtest.run_regime_comparison import (
    _print_regime_counts,
    _print_result,
    _quality_constraints,
)
from market_data.data_access import load_candles_dataframe
from strategies.donchian_breakout.strategy import (
    StrategyConfig,
    evaluate_donchian_breakout,
    prepare_market_data,
)
from strategies.timeframes import aggregate_closed_1h_to_4h


@dataclass(frozen=True)
class ComparisonPeriod:
    label: str
    trend_load_start: datetime
    signal_15m_load_start: datetime
    result_start: datetime
    result_end: datetime
    executable_starting_balance: float


def _prepare_period(
    period: ComparisonPeriod,
    v2_config: StrategyConfig,
    v3_config: StrategyConfig,
) -> dict[str, pd.DataFrame]:
    candles_1h = load_candles_dataframe(
        v2_config.symbol,
        "1h",
        period.trend_load_start,
        period.result_end,
    )
    candles_4h = aggregate_closed_1h_to_4h(candles_1h)
    prepared_4h = prepare_market_data(candles_4h, v2_config)

    candles_15m = load_candles_dataframe(
        v3_config.symbol,
        "15m",
        period.signal_15m_load_start,
        period.result_end,
    )
    prepared_15m = prepare_market_data(
        candles_15m,
        v3_config,
        trend_candles=candles_1h,
    )
    return {
        "4h": prepared_4h.loc[
            prepared_4h["open_time"] >= period.result_start
        ].reset_index(drop=True),
        "15m": prepared_15m.loc[
            prepared_15m["open_time"] >= period.result_start
        ].reset_index(drop=True),
    }


def main() -> None:
    now = datetime.now(timezone.utc)
    periods = (
        ComparisonPeriod(
            label="Development 2023-2024",
            trend_load_start=datetime.fromisoformat(
                "2022-11-01T00:00:00+00:00"
            ),
            signal_15m_load_start=datetime.fromisoformat(
                "2022-12-30T00:00:00+00:00"
            ),
            result_start=datetime.fromisoformat("2023-01-01T00:00:00+00:00"),
            result_end=datetime.fromisoformat("2024-12-31T23:45:00+00:00"),
            executable_starting_balance=10.0,
        ),
        ComparisonPeriod(
            label="Comparison 2025",
            trend_load_start=datetime.fromisoformat(
                "2024-09-01T00:00:00+00:00"
            ),
            signal_15m_load_start=datetime.fromisoformat(
                "2024-12-30T00:00:00+00:00"
            ),
            result_start=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            result_end=datetime.fromisoformat("2025-12-31T23:45:00+00:00"),
            executable_starting_balance=33.133903,
        ),
        ComparisonPeriod(
            label="Diagnostic 2026",
            trend_load_start=datetime.fromisoformat(
                "2025-09-01T00:00:00+00:00"
            ),
            signal_15m_load_start=datetime.fromisoformat(
                "2025-12-30T00:00:00+00:00"
            ),
            result_start=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
            result_end=now,
            executable_starting_balance=50.585451,
        ),
    )
    v1_config = StrategyConfig()
    v2_config = StrategyConfig(
        strategy_version="2.0.0",
        allow_short_entries=True,
        trend_filter_enabled=True,
    )
    v3_config = StrategyConfig(
        strategy_version="3.0.0",
        signal_timeframe="15m",
        trend_timeframe="1h",
        allow_short_entries=True,
        trend_filter_enabled=True,
    )
    strategies = (
        (
            "v1.1 — 4h Long-only",
            "4h",
            partial(evaluate_donchian_breakout, config=v1_config),
        ),
        (
            "v2 — 4h with 4h EMA regime",
            "4h",
            partial(evaluate_donchian_breakout, config=v2_config),
        ),
        (
            "v3 — 15m with closed 1h EMA regime",
            "15m",
            partial(evaluate_donchian_breakout, config=v3_config),
        ),
    )

    prepared_periods: dict[str, dict[str, pd.DataFrame]] = {}
    for period in periods:
        prepared = _prepare_period(period, v2_config, v3_config)
        prepared_periods[period.label] = prepared
        years = tuple(
            range(period.result_start.year, period.result_end.year + 1)
        )
        print(f"\n{period.label}")
        print(
            f"Period: {period.result_start} -> "
            f"{prepared['15m'].iloc[-1]['decision_time']}"
        )
        print(
            f"Closed candles: 4h={len(prepared['4h'])}, "
            f"15m={len(prepared['15m'])}"
        )
        print("v3 signal-candle regime and breakout counts:")
        _print_regime_counts(prepared["15m"])

        for label, timeframe, evaluator in strategies:
            candles = prepared[timeframe]
            quality_result = run_backtest(
                candles,
                evaluator,
                BacktestConfig(
                    starting_balance=1000.0,
                    risk_fraction=0.01,
                    leverage=100.0,
                    instrument=_quality_constraints(),
                ),
            )
            executable_result = run_backtest(
                candles,
                evaluator,
                BacktestConfig(
                    starting_balance=period.executable_starting_balance,
                    risk_fraction=0.05,
                    leverage=3.0,
                ),
            )
            _print_result(f"{label} — quality 1000 USDT / 1%", quality_result, years)
            _print_result(f"{label} — executable 5% / 3x", executable_result, years)

    print("\nContinuous executable account — 10 USDT / 5% / 3x")
    for label, timeframe, evaluator in strategies:
        balance = 10.0
        print(label)
        for period in periods:
            result = run_backtest(
                prepared_periods[period.label][timeframe],
                evaluator,
                BacktestConfig(
                    starting_balance=balance,
                    risk_fraction=0.05,
                    leverage=3.0,
                ),
            )
            summary = result.summary()
            print(
                f"  {period.label}: {balance:.6f} -> "
                f"{summary['ending_balance']:.6f} USDT, "
                f"return={summary['return_percent']:.6f}%, "
                f"trades={summary['trade_count']}, "
                f"rejected={summary['rejected_entries']}"
            )
            if summary["end_of_data_exits"] != 0:
                raise RuntimeError(
                    f"{label} has no clean boundary after {period.label}."
                )
            balance = float(summary["ending_balance"])


if __name__ == "__main__":
    main()
