from dataclasses import replace

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from strategies.donchian_breakout.strategy import (
    MarketRegime,
    Reason,
    StrategyConfig,
    TIMEFRAME_DURATIONS,
    evaluate_donchian_breakout,
    prepare_market_data,
)
from strategies.models import Action, PositionState, Side


def _row(
    *,
    close: float,
    entry_high: float = 120.0,
    entry_low: float = 80.0,
    exit_high: float = 110.0,
    exit_low: float = 90.0,
    atr: float = 5.0,
    trend_ema_fast: float = 110.0,
    trend_ema_slow: float = 100.0,
    market_regime: str = MarketRegime.BULL.value,
    timeframe: str = "4h",
) -> pd.Series:
    open_time = pd.Timestamp("2023-02-01 08:00:00", tz="UTC")
    return pd.Series(
        {
            "symbol": "ETHUSDT",
            "timeframe": timeframe,
            "open_time": open_time,
            "open": 100.0,
            "high": max(121.0, close),
            "low": min(79.0, close),
            "close": close,
            "decision_time": open_time + TIMEFRAME_DURATIONS[timeframe],
            "entry_channel_high": entry_high,
            "entry_channel_low": entry_low,
            "exit_channel_high": exit_high,
            "exit_channel_low": exit_low,
            "signal_atr": atr,
            "trend_ema_fast": trend_ema_fast,
            "trend_ema_slow": trend_ema_slow,
            "market_regime": market_regime,
        }
    )


def check_decisions() -> None:
    long_decision = evaluate_donchian_breakout(_row(close=121.0))
    repeated = evaluate_donchian_breakout(_row(close=121.0))
    if (
        long_decision.action is not Action.OPEN_POSITION
        or long_decision.side is not Side.LONG
        or long_decision.reason != Reason.LONG_BREAKOUT.value
        or long_decision.stop_distance != 7.5
        or long_decision.take_profit_r_multiple is not None
    ):
        raise AssertionError("Expected Long breakout was not produced.")
    if long_decision.decision_id != repeated.decision_id:
        raise AssertionError("Decision ID is not deterministic.")

    short_enabled_config = replace(
        StrategyConfig(),
        allow_short_entries=True,
    )
    short_decision = evaluate_donchian_breakout(
        _row(close=79.0),
        config=short_enabled_config,
    )
    if (
        short_decision.action is not Action.OPEN_POSITION
        or short_decision.side is not Side.SHORT
        or short_decision.reason != Reason.SHORT_BREAKOUT.value
    ):
        raise AssertionError("Expected Short breakout was not produced.")
    short_disabled = evaluate_donchian_breakout(
        _row(close=79.0),
        config=StrategyConfig(),
    )
    if (
        short_disabled.action is not Action.NO_ACTION
        or short_disabled.reason != Reason.SHORT_ENTRIES_DISABLED.value
    ):
        raise AssertionError("Long-only mode accepted a Short entry.")

    trend_config = replace(
        StrategyConfig(),
        strategy_version="2.0.0",
        allow_short_entries=True,
        trend_filter_enabled=True,
    )
    trend_long = evaluate_donchian_breakout(
        _row(close=121.0),
        config=trend_config,
    )
    trend_short = evaluate_donchian_breakout(
        _row(
            close=79.0,
            trend_ema_fast=90.0,
            trend_ema_slow=100.0,
            market_regime=MarketRegime.BEAR.value,
        ),
        config=trend_config,
    )
    blocked_long = evaluate_donchian_breakout(
        _row(
            close=121.0,
            trend_ema_fast=130.0,
            trend_ema_slow=100.0,
            market_regime=MarketRegime.NEUTRAL.value,
        ),
        config=trend_config,
    )
    if (
        trend_long.action is not Action.OPEN_POSITION
        or trend_long.side is not Side.LONG
        or trend_short.action is not Action.OPEN_POSITION
        or trend_short.side is not Side.SHORT
    ):
        raise AssertionError("Trend filter rejected an aligned breakout.")
    if (
        blocked_long.action is not Action.NO_ACTION
        or blocked_long.reason != Reason.ENTRY_BLOCKED_BY_REGIME.value
    ):
        raise AssertionError("Trend filter accepted a misaligned breakout.")

    v3_config = replace(
        trend_config,
        strategy_version="3.0.0",
        signal_timeframe="15m",
        trend_timeframe="1h",
    )
    v3_long = evaluate_donchian_breakout(
        _row(close=121.0, timeframe="15m"),
        config=v3_config,
    )
    if (
        v3_long.action is not Action.OPEN_POSITION
        or v3_long.entry_timing != "NEXT_15M_OPEN"
    ):
        raise AssertionError("15m strategy entry timing is incorrect.")

    position = PositionState(
        side=Side.LONG,
        entry_time=long_decision.execute_at,
        holding_candles=3,
    )
    hold = evaluate_donchian_breakout(_row(close=100.0), position)
    close = evaluate_donchian_breakout(_row(close=89.0), position)
    if hold.action is not Action.HOLD_POSITION:
        raise AssertionError("Long position was not held inside exit channel.")
    if (
        close.action is not Action.CLOSE_POSITION
        or close.reason != Reason.LONG_EXIT_CHANNEL.value
    ):
        raise AssertionError("Long exit-channel decision was not produced.")

    warmup = evaluate_donchian_breakout(
        _row(close=100.0, entry_high=float("nan"))
    )
    if (
        warmup.action is not Action.NO_ACTION
        or warmup.reason != Reason.INSUFFICIENT_HISTORY.value
    ):
        raise AssertionError("Warm-up did not produce no action.")


def check_shifted_channels_and_no_look_ahead() -> None:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rows = []
    for index in range(50):
        price = 100.0 + index
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "open_time": start + pd.Timedelta(hours=4 * index),
                "open": price,
                "high": price + 2.0,
                "low": price - 2.0,
                "close": price + 1.0,
                "decision_time": (
                    start + pd.Timedelta(hours=4 * (index + 1))
                ),
            }
        )
    candles = pd.DataFrame(rows)
    original = candles.copy(deep=True)
    prepared = prepare_market_data(candles)
    assert_frame_equal(candles, original)
    expected_entry_high = candles.loc[:39, "high"].max()
    if prepared.loc[40, "entry_channel_high"] != expected_entry_high:
        raise AssertionError("Current candle leaked into the entry channel.")

    changed_future = candles.copy(deep=True)
    changed_future.loc[45:, ["high", "low", "close"]] += 1000.0
    changed = prepare_market_data(changed_future)
    columns = [
        "entry_channel_high",
        "entry_channel_low",
        "exit_channel_high",
        "exit_channel_low",
        "signal_atr",
    ]
    for column in columns:
        assert_series_equal(
            prepared.loc[:44, column],
            changed.loc[:44, column],
        )


def check_market_regimes() -> None:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    rising = [100.0 + index * 0.5 for index in range(220)]
    falling = [rising[-1] - (index + 1) * 0.5 for index in range(220)]
    closes = rising + falling
    rows = []
    for index, close in enumerate(closes):
        rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "open_time": start + pd.Timedelta(hours=4 * index),
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "decision_time": start + pd.Timedelta(hours=4 * (index + 1)),
            }
        )
    prepared = prepare_market_data(pd.DataFrame(rows))
    if prepared.loc[:198, "market_regime"].notna().any():
        raise AssertionError("Trend regime appeared before EMA200 warm-up.")
    if prepared.loc[199, "market_regime"] != MarketRegime.BULL.value:
        raise AssertionError("Rising market was not classified as Bull.")
    observed = set(prepared["market_regime"].dropna())
    if observed != {regime.value for regime in MarketRegime}:
        raise AssertionError("Bull, Bear, and Neutral regimes were not found.")


def check_15m_signal_uses_only_closed_1h_regime() -> None:
    start = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    trend_rows = []
    for index in range(205):
        close = 100.0 + index
        trend_rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "open_time": start + pd.Timedelta(hours=index),
                "close": close,
            }
        )
    signal_rows = []
    signal_start = start + pd.Timedelta(hours=198)
    for index in range(12):
        close = 300.0 + index
        signal_rows.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": "15m",
                "open_time": signal_start + pd.Timedelta(minutes=15 * index),
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
            }
        )
    config = StrategyConfig(
        strategy_version="3.0.0",
        signal_timeframe="15m",
        trend_timeframe="1h",
        allow_short_entries=True,
        trend_filter_enabled=True,
    )
    signals = pd.DataFrame(signal_rows)
    trend = pd.DataFrame(trend_rows)
    prepared = prepare_market_data(signals, config, trend)
    before_hour_close = prepared.loc[
        prepared["decision_time"] == start + pd.Timedelta(hours=199, minutes=45)
    ].iloc[0]
    at_hour_close = prepared.loc[
        prepared["decision_time"] == start + pd.Timedelta(hours=200)
    ].iloc[0]
    if not pd.isna(before_hour_close["market_regime"]):
        raise AssertionError("15m signal saw the still-open 1h candle.")
    if at_hour_close["market_regime"] != MarketRegime.BULL.value:
        raise AssertionError("15m signal did not receive the newly closed hour.")

    changed_trend = trend.copy(deep=True)
    changed_trend.loc[200:, "close"] += 1000.0
    changed = prepare_market_data(signals, config, changed_trend)
    assert_series_equal(
        prepared.loc[:7, "market_regime"],
        changed.loc[:7, "market_regime"],
    )


def main() -> None:
    check_decisions()
    check_shifted_channels_and_no_look_ahead()
    check_market_regimes()
    check_15m_signal_uses_only_closed_1h_regime()
    print("Donchian Breakout checks passed:")
    print("Long and Short entry decisions: True")
    print("Long-only direction mode: True")
    print("EMA50/EMA200 entry regime: True")
    print("Trend warm-up and Bull/Bear/Neutral classification: True")
    print("Closed 1h regime aligned to 15m without look-ahead: True")
    print("Hold and channel-exit decisions: True")
    print("No fixed take profit: True")
    print("Deterministic decision ID: True")
    print("Warm-up behavior: True")
    print("Shifted channels: True")
    print("No look-ahead: True")
    print("Input immutability: True")


if __name__ == "__main__":
    main()
