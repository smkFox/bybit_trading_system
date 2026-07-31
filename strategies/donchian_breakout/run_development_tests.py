import math
from dataclasses import replace
from datetime import datetime
from functools import partial
from pathlib import Path

import pandas as pd

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
OUTPUT_PATH = Path.cwd() / "donchian_breakout_development_tests.xlsx"

CHANNEL_PAIRS = (
    (20, 10),
    (40, 10),
    (40, 20),
    (55, 10),
    (55, 20),
)
STOP_ATR_MULTIPLIERS = (1.5, 2.0, 2.5)
DIRECTION_MODES = (
    ("LONG_SHORT", True),
    ("LONG_ONLY", False),
)


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


def _year_metrics(result, year: int) -> dict[str, float | int | None]:
    trades = [trade for trade in result.trades if trade.entry_time.year == year]
    net_values = [trade.net_pnl for trade in trades]
    return {
        "trades": len(trades),
        "net_pnl": sum(net_values),
        "net_r": sum(
            trade.net_pnl / trade.risk_budget for trade in trades
        ),
        "profit_factor": _profit_factor(net_values),
    }


def _result_metrics(prefix: str, result) -> dict[str, object]:
    summary = result.summary()
    values: dict[str, object] = {
        f"{prefix}_entry_signals": summary["entry_signals"],
        f"{prefix}_trades": summary["trade_count"],
        f"{prefix}_rejected": summary["rejected_entries"],
        f"{prefix}_ending_balance": summary["ending_balance"],
        f"{prefix}_net_pnl": summary["net_pnl"],
        f"{prefix}_return_percent": summary["return_percent"],
        f"{prefix}_total_net_r": summary["total_net_r"],
        f"{prefix}_average_net_r": summary["average_net_r"],
        f"{prefix}_profit_factor": summary["profit_factor"],
        f"{prefix}_win_rate_percent": summary["win_rate_percent"],
        f"{prefix}_max_drawdown_percent": (
            summary["closed_equity_max_drawdown_percent"]
        ),
        f"{prefix}_longest_losing_streak": (
            summary["longest_losing_streak"]
        ),
        f"{prefix}_long_trades": summary["long_trades"],
        f"{prefix}_long_net_pnl": summary["long_net_pnl"],
        f"{prefix}_short_trades": summary["short_trades"],
        f"{prefix}_short_net_pnl": summary["short_net_pnl"],
        f"{prefix}_fees": summary["total_fees"],
        f"{prefix}_funding": summary["total_funding"],
        f"{prefix}_risk_rejections": summary["risk_rejections"],
        f"{prefix}_margin_rejections": summary["margin_rejections"],
    }
    for year in (2023, 2024):
        year_values = _year_metrics(result, year)
        for name, value in year_values.items():
            values[f"{prefix}_{year}_{name}"] = value
    return values


def _assumptions() -> pd.DataFrame:
    return pd.DataFrame(
        (
            ("development_period", "2023-01-01 through 2024-12-31 UTC"),
            ("signal_timeframe", "4h from four consecutive closed 1h candles"),
            ("atr_period", "14"),
            ("fixed_take_profit", "none"),
            ("maximum_holding_time", "none"),
            ("pyramiding", "disabled"),
            ("simultaneous_positions", "one"),
            ("taker_fee_per_fill", "0.055%"),
            ("adverse_slippage_per_fill", "0.050%"),
            ("funding_cost_per_8h", "0.010%"),
            ("quality_mode", "1000 USDT, 1% risk, size filters neutralized"),
            ("executable_mode", "10 USDT, 5% risk, 3x leverage"),
            ("validation_data_used", "no"),
        ),
        columns=("assumption", "value"),
    )


def main() -> None:
    base_strategy = StrategyConfig()
    candles_1h = load_candles_dataframe(
        base_strategy.symbol,
        "1h",
        START,
        END,
    )
    candles_4h = aggregate_closed_1h_to_4h(candles_1h)
    prepared_by_channels: dict[tuple[int, int], pd.DataFrame] = {}
    for entry_period, exit_period in CHANNEL_PAIRS:
        preparation_config = replace(
            base_strategy,
            entry_channel_period=entry_period,
            exit_channel_period=exit_period,
        )
        prepared_by_channels[(entry_period, exit_period)] = prepare_market_data(
            candles_4h,
            preparation_config,
        )

    quality_config = BacktestConfig(
        starting_balance=1000.0,
        risk_fraction=0.01,
        leverage=100.0,
        instrument=_quality_constraints(),
    )
    executable_config = BacktestConfig(
        starting_balance=10.0,
        risk_fraction=0.05,
        leverage=3.0,
    )

    rows: list[dict[str, object]] = []
    variant_id = 0
    for entry_period, exit_period in CHANNEL_PAIRS:
        prepared = prepared_by_channels[(entry_period, exit_period)]
        for stop_multiplier in STOP_ATR_MULTIPLIERS:
            for direction_name, allow_short in DIRECTION_MODES:
                variant_id += 1
                strategy_config = replace(
                    base_strategy,
                    entry_channel_period=entry_period,
                    exit_channel_period=exit_period,
                    stop_atr_multiplier=stop_multiplier,
                    allow_short_entries=allow_short,
                )
                evaluator = partial(
                    evaluate_donchian_breakout,
                    config=strategy_config,
                )
                quality_result = run_backtest(
                    prepared,
                    evaluator,
                    quality_config,
                )
                executable_result = run_backtest(
                    prepared,
                    evaluator,
                    executable_config,
                )
                row: dict[str, object] = {
                    "variant_id": variant_id,
                    "entry_channel": entry_period,
                    "exit_channel": exit_period,
                    "stop_atr_multiplier": stop_multiplier,
                    "direction": direction_name,
                }
                row.update(_result_metrics("quality", quality_result))
                row.update(_result_metrics("executable", executable_result))
                rows.append(row)
                print(
                    f"[{variant_id:02d}/30] "
                    f"{entry_period}/{exit_period}, "
                    f"stop={stop_multiplier:.1f} ATR, {direction_name}: "
                    f"quality={row['quality_return_percent']:.2f}%, "
                    f"executable={row['executable_return_percent']:.2f}%"
                )

    table = pd.DataFrame(rows)
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        table.to_excel(writer, sheet_name="comparison", index=False)
        _assumptions().to_excel(writer, sheet_name="assumptions", index=False)
    print(f"Saved {len(table)} variants to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
