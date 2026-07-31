import math
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

import pandas as pd

from backtest.engine import BacktestConfig, InstrumentConstraints, run_backtest
from market_data.data_access import load_candles_dataframe
from strategies.donchian_breakout.strategy import (
    MarketRegime,
    StrategyConfig,
    evaluate_donchian_breakout,
    prepare_market_data,
)
from strategies.timeframes import aggregate_closed_1h_to_4h


@dataclass(frozen=True)
class ComparisonPeriod:
    label: str
    load_start: datetime
    result_start: datetime
    result_end: datetime
    executable_starting_balance: float


def _quality_constraints() -> InstrumentConstraints:
    return InstrumentConstraints(
        min_order_qty=0.00000001,
        qty_step=0.00000001,
        min_notional=0.00000001,
        max_market_order_qty=1_000_000.0,
        tick_size=0.01,
        observed_at="QUALITY_MODE_WITHOUT_SIZE_LIMITS",
    )


def _profit_factor(values: list[float]) -> float | None:
    profit = sum(value for value in values if value > 0)
    loss = abs(sum(value for value in values if value < 0))
    if loss > 0:
        return profit / loss
    if profit > 0:
        return math.inf
    return None


def _format(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _print_result(label: str, result, years: tuple[int, ...]) -> None:
    summary = result.summary()
    fields = (
        "starting_balance",
        "ending_balance",
        "return_percent",
        "trade_count",
        "rejected_entries",
        "long_trades",
        "long_net_pnl",
        "short_trades",
        "short_net_pnl",
        "profit_factor",
        "closed_equity_max_drawdown_percent",
        "longest_losing_streak",
        "total_fees",
        "total_funding",
        "end_of_data_exits",
    )
    print(label)
    for field in fields:
        print(f"  {field}: {_format(summary[field])}")
    for year in years:
        trades = [
            trade for trade in result.trades if trade.entry_time.year == year
        ]
        net_values = [trade.net_pnl for trade in trades]
        print(
            f"  year_{year}: trades={len(trades)}, "
            f"net_pnl={sum(net_values):.6f}, "
            f"profit_factor={_format(_profit_factor(net_values))}"
        )


def _print_regime_counts(prepared: pd.DataFrame) -> None:
    counts = prepared["market_regime"].value_counts()
    long_breakouts = prepared["close"] > prepared["entry_channel_high"]
    short_breakouts = prepared["close"] < prepared["entry_channel_low"]
    blocked_long = long_breakouts & (
        prepared["market_regime"] != MarketRegime.BULL.value
    )
    blocked_short = short_breakouts & (
        prepared["market_regime"] != MarketRegime.BEAR.value
    )
    print(
        "Regimes: "
        f"Bull={counts.get(MarketRegime.BULL.value, 0)}, "
        f"Bear={counts.get(MarketRegime.BEAR.value, 0)}, "
        f"Neutral={counts.get(MarketRegime.NEUTRAL.value, 0)}"
    )
    print(
        "Raw breakout candles: "
        f"Long={int(long_breakouts.sum())}, "
        f"Long blocked={int(blocked_long.sum())}, "
        f"Short={int(short_breakouts.sum())}, "
        f"Short blocked={int(blocked_short.sum())}"
    )


def _prepare_period(
    period: ComparisonPeriod,
    strategy_config: StrategyConfig,
) -> pd.DataFrame:
    candles_1h = load_candles_dataframe(
        strategy_config.symbol,
        "1h",
        period.load_start,
        period.result_end,
    )
    candles_4h = aggregate_closed_1h_to_4h(candles_1h)
    prepared = prepare_market_data(candles_4h, strategy_config)
    return prepared.loc[
        prepared["open_time"] >= period.result_start
    ].reset_index(drop=True)


def main() -> None:
    now = datetime.now(timezone.utc)
    periods = (
        ComparisonPeriod(
            label="Development 2023-2024",
            load_start=datetime.fromisoformat("2022-11-01T00:00:00+00:00"),
            result_start=datetime.fromisoformat("2023-01-01T00:00:00+00:00"),
            result_end=datetime.fromisoformat("2024-12-31T23:00:00+00:00"),
            executable_starting_balance=10.0,
        ),
        ComparisonPeriod(
            label="Comparison 2025",
            load_start=datetime.fromisoformat("2024-09-01T00:00:00+00:00"),
            result_start=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            result_end=datetime.fromisoformat("2025-12-31T23:00:00+00:00"),
            executable_starting_balance=33.133903,
        ),
        ComparisonPeriod(
            label="Diagnostic 2026",
            load_start=datetime.fromisoformat("2025-09-01T00:00:00+00:00"),
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
    evaluators = (
        (
            "v1.1 Long-only",
            partial(evaluate_donchian_breakout, config=v1_config),
        ),
        (
            "v2 EMA50/EMA200 regime",
            partial(evaluate_donchian_breakout, config=v2_config),
        ),
    )

    prepared_periods: dict[str, pd.DataFrame] = {}
    for period in periods:
        prepared = _prepare_period(period, v2_config)
        prepared_periods[period.label] = prepared
        years = tuple(
            range(period.result_start.year, period.result_end.year + 1)
        )
        print(f"\n{period.label}")
        print(
            f"Period: {period.result_start} -> "
            f"{prepared.iloc[-1]['decision_time']}"
        )
        print(f"Closed 4h candles: {len(prepared)}")
        _print_regime_counts(prepared)

        for strategy_label, evaluator in evaluators:
            quality_result = run_backtest(
                prepared,
                evaluator,
                BacktestConfig(
                    starting_balance=1000.0,
                    risk_fraction=0.01,
                    leverage=100.0,
                    instrument=_quality_constraints(),
                ),
            )
            executable_result = run_backtest(
                prepared,
                evaluator,
                BacktestConfig(
                    starting_balance=period.executable_starting_balance,
                    risk_fraction=0.05,
                    leverage=3.0,
                ),
            )
            _print_result(
                f"{strategy_label} — quality 1000 USDT / 1%",
                quality_result,
                years,
            )
            _print_result(
                f"{strategy_label} — executable 5% / 3x",
                executable_result,
                years,
            )

    print("\nContinuous executable account — 10 USDT / 5% / 3x")
    for strategy_label, evaluator in evaluators:
        balance = 10.0
        print(strategy_label)
        for period in periods:
            result = run_backtest(
                prepared_periods[period.label],
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
                    f"{strategy_label} has no clean boundary after "
                    f"{period.label}."
                )
            balance = float(summary["ending_balance"])


if __name__ == "__main__":
    main()
