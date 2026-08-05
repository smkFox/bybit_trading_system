import math
from datetime import datetime
from functools import partial

from backtest.engine import BacktestConfig, InstrumentConstraints, run_backtest
from market_data.data_access import (
    load_candles_dataframe,
    load_funding_rates_dataframe,
    load_open_interest_dataframe,
)
from strategies.volatility_squeeze_breakout.strategy import (
    StrategyConfig,
    evaluate_strategy,
    prepare_market_data,
)


WARMUP_START = datetime.fromisoformat("2022-12-01T00:00:00+00:00")
DEVELOPMENT_START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
HOURLY_END = datetime.fromisoformat("2024-12-31T23:00:00+00:00")
SIGNAL_END = datetime.fromisoformat("2024-12-31T23:45:00+00:00")


def _quality_constraints() -> InstrumentConstraints:
    return InstrumentConstraints(
        min_order_qty=0.00000001,
        qty_step=0.00000001,
        min_notional=0.00000001,
        max_market_order_qty=1_000_000.0,
        tick_size=0.01,
        observed_at="QUALITY_MODE_WITHOUT_SIZE_LIMITS",
    )


def _format(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _profit_factor(values: list[float]) -> float | None:
    profit = sum(value for value in values if value > 0)
    loss = abs(sum(value for value in values if value < 0))
    if loss > 0:
        return profit / loss
    if profit > 0:
        return math.inf
    return None


def _year_metrics(result, year: int) -> dict[str, float | int | None]:
    trades = [trade for trade in result.trades if trade.entry_time.year == year]
    values = [trade.net_pnl for trade in trades]
    return {
        "trades": len(trades),
        "net_pnl": sum(values),
        "profit_factor": _profit_factor(values),
    }


def _print_result(label: str, result) -> None:
    summary = result.summary()
    fields = (
        "starting_balance",
        "ending_balance",
        "return_percent",
        "entry_signals",
        "trade_count",
        "rejected_entries",
        "long_trades",
        "long_net_pnl",
        "short_trades",
        "short_net_pnl",
        "win_rate_percent",
        "profit_factor",
        "closed_equity_max_drawdown_percent",
        "longest_losing_streak",
        "total_fees",
        "total_funding",
        "stop_loss_exits",
        "take_profit_exits",
        "strategy_exits",
        "end_of_data_exits",
    )
    print(label)
    for field in fields:
        print(f"  {field}: {_format(summary[field])}")
    for year in (2023, 2024):
        metrics = _year_metrics(result, year)
        print(
            f"  year_{year}: trades={metrics['trades']}, "
            f"net_pnl={metrics['net_pnl']:.6f}, "
            f"profit_factor={_format(metrics['profit_factor'])}"
        )


def _development_gate(result) -> dict[str, bool]:
    summary = result.summary()
    year_2023 = _year_metrics(result, 2023)
    year_2024 = _year_metrics(result, 2024)
    return {
        "positive_2023": year_2023["net_pnl"] > 0,
        "positive_2024": year_2024["net_pnl"] > 0,
        "profit_factor_at_least_1_2": (
            summary["profit_factor"] is not None
            and summary["profit_factor"] >= 1.2
        ),
        "drawdown_at_most_20_percent": (
            summary["closed_equity_max_drawdown_percent"] <= 20
        ),
        "at_least_30_trades": summary["trade_count"] >= 30,
        "at_least_10_trades_each_year": (
            year_2023["trades"] >= 10 and year_2024["trades"] >= 10
        ),
        "long_expectancy_not_negative": (
            summary["long_trades"] > 0 and summary["long_net_pnl"] >= 0
        ),
        "short_expectancy_not_negative": (
            summary["short_trades"] > 0 and summary["short_net_pnl"] >= 0
        ),
        "clean_end_boundary": summary["end_of_data_exits"] == 0,
    }


def main() -> None:
    config = StrategyConfig()
    candles_1h = load_candles_dataframe(
        config.symbol, "1h", WARMUP_START, HOURLY_END
    )
    candles_15m = load_candles_dataframe(
        config.symbol, "15m", WARMUP_START, SIGNAL_END
    )
    open_interest = load_open_interest_dataframe(
        config.symbol, "15m", WARMUP_START, SIGNAL_END
    )
    funding = load_funding_rates_dataframe(
        config.symbol, WARMUP_START, SIGNAL_END
    )
    prepared = prepare_market_data(
        candles_1h, candles_15m, open_interest, funding, config
    )
    development = prepared.loc[
        prepared["open_time"] >= DEVELOPMENT_START
    ].reset_index(drop=True)
    evaluator = partial(evaluate_strategy, config=config)

    quality_result = run_backtest(
        development,
        evaluator,
        BacktestConfig(
            starting_balance=1000.0,
            risk_fraction=0.01,
            leverage=100.0,
            instrument=_quality_constraints(),
        ),
    )
    executable_result = run_backtest(
        development,
        evaluator,
        BacktestConfig(
            starting_balance=10.0,
            risk_fraction=0.05,
            leverage=3.0,
        ),
    )

    print("Volatility Squeeze Breakout v1 development")
    print(f"Period: {DEVELOPMENT_START} -> {development.iloc[-1]['decision_time']}")
    print(
        f"Data: 1h={len(candles_1h)}, 15m={len(candles_15m)}, "
        f"OI 15m={len(open_interest)}, funding={len(funding)}, "
        f"development 15m={len(development)}"
    )
    print(
        "Parameters: ATR14/close <= prior 720h p20, range=4h, setup=4h, "
        "volume>1.5x prior20 median, rising OI, funding prior90 p10/p90, "
        "stop=1.5 ATR15m, target=2R, max=8h"
    )
    print("Costs: taker=0.055% and adverse slippage=0.050% per fill")
    print("Funding cost model: conservative 0.010% per crossed 8h interval")
    _print_result("Signal quality — 1000 USDT / 1% risk", quality_result)
    _print_result("Executable — 10 USDT / 5% risk / 3x", executable_result)

    gate = _development_gate(quality_result)
    print("Development gate")
    for name, passed in gate.items():
        print(f"  {name}: {passed}")
    print(f"Decision: {'PROCEED' if all(gate.values()) else 'REJECT_AND_STOP'}")


if __name__ == "__main__":
    main()
