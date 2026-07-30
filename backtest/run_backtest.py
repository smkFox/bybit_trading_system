import argparse
import math
from datetime import datetime, timezone

from backtest.engine import BacktestConfig, run_backtest
from market_data.data_access import load_candles_dataframe
from strategies.timeframe_alignment import align_timeframes


DEFAULT_START = "2023-01-01T00:00:00+00:00"
DEFAULT_END = "2024-12-31T23:45:00+00:00"


def _parse_utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("Datetime must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _format_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _print_trade(label: str, trade) -> None:
    print(
        f"{label}: {trade.side.value} "
        f"{trade.entry_time.isoformat()} -> {trade.exit_time.isoformat()}, "
        f"entry={trade.entry_price:.2f}, exit={trade.exit_price:.2f}, "
        f"qty={trade.quantity:.4f}, net={trade.net_pnl:.6f}, "
        f"reason={trade.exit_reason.value}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the EMA Trend Pullback sequential backtest."
    )
    parser.add_argument(
        "--start",
        type=_parse_utc_datetime,
        default=_parse_utc_datetime(DEFAULT_START),
    )
    parser.add_argument(
        "--end",
        type=_parse_utc_datetime,
        default=_parse_utc_datetime(DEFAULT_END),
    )
    parser.add_argument(
        "--risk-percent",
        type=float,
        default=1.0,
        help="Maximum all-in loss budget per trade as account percent.",
    )
    parser.add_argument(
        "--slippage-percent",
        type=float,
        default=0.05,
        help="Adverse slippage applied to every market fill.",
    )
    parser.add_argument(
        "--funding-percent",
        type=float,
        default=0.01,
        help="Conservative cost per crossed 8-hour funding interval.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.start >= arguments.end:
        raise ValueError("Backtest start must be earlier than end.")

    config = BacktestConfig(
        risk_fraction=arguments.risk_percent / 100,
        slippage_rate=arguments.slippage_percent / 100,
        funding_rate_per_interval=arguments.funding_percent / 100,
    )
    candles_15m = load_candles_dataframe(
        config.strategy.symbol,
        "15m",
        arguments.start,
        arguments.end,
    )
    candles_1h = load_candles_dataframe(
        config.strategy.symbol,
        "1h",
        arguments.start,
        arguments.end,
    )
    prepared = align_timeframes(
        candles_15m,
        candles_1h,
        pullback_ema_period=config.strategy.pullback_ema_period,
        atr_period=config.strategy.atr_period,
        trend_fast_ema_period=config.strategy.trend_fast_ema_period,
        trend_slow_ema_period=config.strategy.trend_slow_ema_period,
    )

    print("Baseline assumptions:")
    print(f"Period: {arguments.start.isoformat()} -> {arguments.end.isoformat()}")
    print(f"Starting balance: {config.starting_balance:.2f} USDT")
    print(f"Risk per trade: {config.risk_fraction * 100:.2f}%")
    print(f"Leverage: {config.leverage:.2f}x")
    print(f"Taker fee per fill: {config.taker_fee_rate * 100:.3f}%")
    print(f"Slippage per fill: {config.slippage_rate * 100:.3f}%")
    print(
        "Funding assumption: "
        f"{config.funding_rate_per_interval * 100:.3f}% cost "
        f"per {config.funding_interval_hours}h interval"
    )
    print(
        "Current ETHUSDT constraints "
        f"(observed {config.instrument.observed_at}): "
        f"min_qty={config.instrument.min_order_qty}, "
        f"qty_step={config.instrument.qty_step}, "
        f"min_notional={config.instrument.min_notional}, "
        f"tick_size={config.instrument.tick_size}"
    )

    result = run_backtest(prepared, config)
    print("Backtest summary:")
    for name, value in result.summary().items():
        print(f"{name}: {_format_value(value)}")

    if result.trades:
        print("Trade samples:")
        sample = result.trades[:3]
        if len(result.trades) > 6:
            sample += result.trades[-3:]
        elif len(result.trades) > 3:
            sample += result.trades[3:]
        for number, trade in enumerate(sample, start=1):
            _print_trade(f"trade_{number}", trade)


if __name__ == "__main__":
    main()
