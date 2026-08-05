from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from market_data.data_access import load_candles_dataframe
from strategies.indicators import calculate_atr


DATA_START = datetime.fromisoformat("2022-12-30T00:00:00+00:00")
ANALYSIS_START = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
ANALYSIS_END = datetime.fromisoformat("2024-12-31T23:45:00+00:00")
LEVERAGE = 3.0
TAKER_FEE_RATE = 0.00055
SLIPPAGE_RATE = 0.00050
FUNDING_RESERVE_RATE = 0.00010
ROUND_TRIP_COST_RATE = (
    2 * TAKER_FEE_RATE + 2 * SLIPPAGE_RATE + FUNDING_RESERVE_RATE
)
STOP_PERCENTS = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
ACCOUNT_CONFIGS = (
    (10.0, 0.05),
    (10.0, 0.10),
    (50.0, 0.05),
    (50.0, 0.10),
)


@dataclass(frozen=True)
class InstrumentSnapshot:
    symbol: str
    current_price: float
    min_order_qty: float
    qty_step: float
    min_notional: float
    observed_at: str = "2026-08-05"


INSTRUMENTS = (
    InstrumentSnapshot("ETHUSDT", 1873.63, 0.01, 0.01, 5.0),
    InstrumentSnapshot("SOLUSDT", 73.86, 0.1, 0.1, 5.0),
)


def _effective_minimum_quantity(
    prices: pd.Series,
    instrument: InstrumentSnapshot,
) -> pd.Series:
    notional_quantity = (
        np.ceil(
            (instrument.min_notional / prices.to_numpy() - 1e-12)
            / instrument.qty_step
        )
        * instrument.qty_step
    )
    values = np.maximum(instrument.min_order_qty, notional_quantity)
    return pd.Series(values, index=prices.index, dtype="float64")


def _market_metrics(candles: pd.DataFrame) -> dict[str, float | int]:
    data = candles.copy(deep=True)
    data["atr_percent"] = calculate_atr(data, 14) / data["close"] * 100
    data = data.loc[data["open_time"] >= ANALYSIS_START].reset_index(drop=True)
    metrics: dict[str, float | int] = {
        "candles": len(data),
        "gaps": int((data["open_time"].diff().dropna() != pd.Timedelta(minutes=15)).sum()),
        "minimum_price": float(data["close"].min()),
        "maximum_price": float(data["close"].max()),
        "median_price": float(data["close"].median()),
        "median_atr_percent": float(data["atr_percent"].median()),
        "p75_atr_percent": float(data["atr_percent"].quantile(0.75)),
        "p90_atr_percent": float(data["atr_percent"].quantile(0.90)),
        "median_turnover": float(data["turnover"].median()),
        "p10_turnover": float(data["turnover"].quantile(0.10)),
    }
    for label, candles_forward in (("15m", 1), ("1h", 4), ("4h", 16), ("8h", 32)):
        absolute_return = (
            data["close"].shift(-candles_forward) / data["close"] - 1
        ).abs() * 100
        metrics[f"median_move_{label}"] = float(absolute_return.median())
        metrics[f"p75_move_{label}"] = float(absolute_return.quantile(0.75))
    return metrics


def _feasibility_rows(
    candles: pd.DataFrame,
    instrument: InstrumentSnapshot,
) -> list[dict[str, float | str]]:
    data = candles.loc[candles["open_time"] >= ANALYSIS_START].reset_index(drop=True)
    prices = data["close"]
    minimum_quantity = _effective_minimum_quantity(prices, instrument)
    minimum_notional = minimum_quantity * prices
    cash_required = minimum_notional * (1 / LEVERAGE + ROUND_TRIP_COST_RATE)
    rows = []
    for capital, risk_fraction in ACCOUNT_CONFIGS:
        risk_budget = capital * risk_fraction
        for stop_percent in STOP_PERCENTS:
            minimum_loss = minimum_notional * (
                stop_percent / 100 + ROUND_TRIP_COST_RATE
            )
            feasible = (minimum_loss <= risk_budget) & (cash_required <= capital)
            rows.append(
                {
                    "symbol": instrument.symbol,
                    "capital": capital,
                    "risk_percent": risk_fraction * 100,
                    "stop_percent": stop_percent,
                    "feasible_percent": float(feasible.mean() * 100),
                    "risk_blocked_percent": float((minimum_loss > risk_budget).mean() * 100),
                    "margin_blocked_percent": float((cash_required > capital).mean() * 100),
                }
            )
    return rows


def _current_rows(instrument: InstrumentSnapshot) -> list[dict[str, float | str]]:
    price = pd.Series([instrument.current_price])
    quantity = float(_effective_minimum_quantity(price, instrument).iloc[0])
    notional = quantity * instrument.current_price
    margin_and_reserve = notional * (1 / LEVERAGE + ROUND_TRIP_COST_RATE)
    rows = []
    for stop_percent in STOP_PERCENTS:
        loss = notional * (stop_percent / 100 + ROUND_TRIP_COST_RATE)
        rows.append(
            {
                "symbol": instrument.symbol,
                "stop_percent": stop_percent,
                "quantity": quantity,
                "notional": notional,
                "margin_and_reserve": margin_and_reserve,
                "minimum_loss": loss,
            }
        )
    return rows


def _print_table(dataframe: pd.DataFrame) -> None:
    print(dataframe.to_string(index=False, float_format=lambda value: f"{value:.4f}"))


def main() -> None:
    candles_by_symbol = {
        instrument.symbol: load_candles_dataframe(
            instrument.symbol,
            "15m",
            DATA_START,
            ANALYSIS_END,
        )
        for instrument in INSTRUMENTS
    }
    market_rows = []
    feasibility_rows = []
    current_rows = []
    for instrument in INSTRUMENTS:
        candles = candles_by_symbol[instrument.symbol]
        metrics = _market_metrics(candles)
        market_rows.append({"symbol": instrument.symbol, **metrics})
        feasibility_rows.extend(_feasibility_rows(candles, instrument))
        current_rows.extend(_current_rows(instrument))

    market = pd.DataFrame(market_rows)
    feasibility = pd.DataFrame(feasibility_rows)
    current = pd.DataFrame(current_rows)

    print("Instrument feasibility analysis")
    print(f"Period: {ANALYSIS_START} -> {ANALYSIS_END}")
    print(f"Leverage: {LEVERAGE:.0f}x")
    print(f"Conservative round-trip cost reserve: {ROUND_TRIP_COST_RATE * 100:.3f}%")
    print("Instrument constraints observed: 2026-08-05")
    print("\nMarket characteristics")
    _print_table(market)
    print("\nCurrent minimum position")
    _print_table(current)
    print("\nHistorical execution feasibility")
    _print_table(feasibility)


if __name__ == "__main__":
    main()
