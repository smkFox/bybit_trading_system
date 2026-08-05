from dataclasses import dataclass
from datetime import datetime
from math import floor

import numpy as np
import pandas as pd

from market_data.data_access import load_candles_dataframe


DATA_START = datetime.fromisoformat("2022-12-31T00:00:00+00:00")
ANALYSIS_END = datetime.fromisoformat("2024-12-31T23:55:00+00:00")
PROFILE_BINS = 100
VALUE_AREA_FRACTION = 0.70
TAPE_SPEED_LOOKBACK = 12
STOP_PERCENTS = (1.0, 2.0)
SOURCE_COST_PERCENT = 0.14
CONSERVATIVE_COST_PERCENT = 0.22


@dataclass(frozen=True)
class Profile:
    anchor: float
    step: float
    poc: float
    vah: float
    val: float


@dataclass(frozen=True)
class Signal:
    index: int
    side: int
    target: float


@dataclass(frozen=True)
class Trade:
    year: int
    side: int
    gross_percent: float
    exit_reason: str


def _add_volume(
    volumes: dict[int, float],
    low: float,
    high: float,
    volume: float,
    anchor: float,
    step: float,
) -> None:
    if high == low:
        bin_index = floor((low - anchor) / step)
        volumes[bin_index] = volumes.get(bin_index, 0.0) + volume
        return

    first = floor((low - anchor) / step)
    last = floor((high - anchor) / step)
    price_range = high - low
    for bin_index in range(first, last + 1):
        bin_low = anchor + bin_index * step
        bin_high = bin_low + step
        overlap = min(high, bin_high) - max(low, bin_low)
        if overlap > 0:
            share = volume * overlap / price_range
            volumes[bin_index] = volumes.get(bin_index, 0.0) + share


def _completed_profile(day: pd.DataFrame) -> Profile:
    anchor = float(day["low"].min())
    high = float(day["high"].max())
    step = (high - anchor) / PROFILE_BINS
    if step <= 0:
        raise ValueError("A daily profile requires a positive price range.")

    profile: dict[int, float] = {}
    for candle in day.itertuples(index=False):
        _add_volume(
            profile,
            float(candle.low),
            float(candle.high),
            float(candle.volume),
            anchor,
            step,
        )
    volumes = np.asarray([profile.get(index, 0.0) for index in range(PROFILE_BINS)])
    poc_index = int(np.argmax(volumes))
    included = volumes[poc_index]
    target = volumes.sum() * VALUE_AREA_FRACTION
    lower = upper = poc_index
    while included < target and (lower > 0 or upper < PROFILE_BINS - 1):
        lower_volume = volumes[lower - 1] if lower > 0 else -1.0
        upper_volume = volumes[upper + 1] if upper < PROFILE_BINS - 1 else -1.0
        if upper_volume > lower_volume:
            upper += 1
            included += volumes[upper]
        else:
            lower -= 1
            included += volumes[lower]
    center = lambda index: anchor + (index + 0.5) * step
    return Profile(
        anchor=anchor,
        step=step,
        poc=center(poc_index),
        vah=center(upper),
        val=center(lower),
    )


def _developing_poc(volumes: dict[int, float], profile: Profile) -> float:
    maximum = max(volumes.values())
    candidates = [index for index, value in volumes.items() if value == maximum]
    poc_index = min(
        candidates,
        key=lambda index: abs(
            profile.anchor + (index + 0.5) * profile.step - profile.poc
        ),
    )
    return profile.anchor + (poc_index + 0.5) * profile.step


def _prepare_candles(candles: pd.DataFrame) -> pd.DataFrame:
    data = candles.copy(deep=True).sort_values("open_time").reset_index(drop=True)
    if len(data) < 2 or (
        data["open_time"].diff().iloc[1:] != pd.Timedelta(minutes=5)
    ).any():
        raise ValueError("SOL 5m candles must be consecutive without gaps.")
    data["day"] = data["open_time"].dt.floor("D")
    data["signed_tape_speed"] = (
        data["volume"] * (data["close"] - data["open"]) / data["open"]
    )
    data["tape_speed_threshold"] = (
        data["signed_tape_speed"]
        .abs()
        .rolling(TAPE_SPEED_LOOKBACK, min_periods=TAPE_SPEED_LOOKBACK)
        .median()
        .shift(1)
    )
    return data


def _signals(data: pd.DataFrame) -> list[Signal]:
    grouped = {day: frame for day, frame in data.groupby("day", sort=True)}
    profiles = {day: _completed_profile(frame) for day, frame in grouped.items()}
    signals = []
    days = sorted(grouped)
    for day_position in range(1, len(days)):
        day = days[day_position]
        if day.year not in (2023, 2024):
            continue
        previous_profile = profiles[days[day_position - 1]]
        developing: dict[int, float] = {}
        day_frame = grouped[day]
        final_index = int(day_frame.index[-1])
        for candle in day_frame.itertuples():
            _add_volume(
                developing,
                float(candle.low),
                float(candle.high),
                float(candle.volume),
                previous_profile.anchor,
                previous_profile.step,
            )
            if candle.Index == final_index or pd.isna(candle.tape_speed_threshold):
                continue
            target = _developing_poc(developing, previous_profile)
            long_signal = (
                candle.low < previous_profile.val
                and candle.close >= previous_profile.val
                and candle.signed_tape_speed > candle.tape_speed_threshold
            )
            short_signal = (
                candle.high > previous_profile.vah
                and candle.close <= previous_profile.vah
                and candle.signed_tape_speed < -candle.tape_speed_threshold
            )
            if long_signal != short_signal:
                signals.append(
                    Signal(candle.Index, 1 if long_signal else -1, target)
                )
    return signals


def _simulate(data: pd.DataFrame, signals: list[Signal], stop_percent: float) -> list[Trade]:
    trades = []
    by_day: dict[pd.Timestamp, list[Signal]] = {}
    for signal in signals:
        by_day.setdefault(data.iloc[signal.index]["day"], []).append(signal)

    for day, day_signals in by_day.items():
        day_end_index = int(data.index[data["day"].eq(day)][-1])
        next_allowed_signal = -1
        for signal in day_signals:
            if signal.index < next_allowed_signal:
                continue
            entry_index = signal.index + 1
            entry = float(data.iloc[entry_index]["open"])
            if (signal.side > 0 and signal.target <= entry) or (
                signal.side < 0 and signal.target >= entry
            ):
                continue
            stop = entry * (1 - signal.side * stop_percent / 100)
            exit_price = float(data.iloc[day_end_index]["close"])
            exit_reason = "END_OF_DAY"
            exit_index = day_end_index
            for candle_index in range(entry_index, day_end_index + 1):
                candle = data.iloc[candle_index]
                candle_open = float(candle["open"])
                if signal.side > 0:
                    if candle_open <= stop:
                        exit_price, exit_reason = candle_open, "STOP"
                        exit_index = candle_index
                        break
                    if float(candle["low"]) <= stop:
                        exit_price, exit_reason = stop, "STOP"
                        exit_index = candle_index
                        break
                    if candle_open >= signal.target or float(candle["high"]) >= signal.target:
                        exit_price, exit_reason = signal.target, "TARGET"
                        exit_index = candle_index
                        break
                else:
                    if candle_open >= stop:
                        exit_price, exit_reason = candle_open, "STOP"
                        exit_index = candle_index
                        break
                    if float(candle["high"]) >= stop:
                        exit_price, exit_reason = stop, "STOP"
                        exit_index = candle_index
                        break
                    if candle_open <= signal.target or float(candle["low"]) <= signal.target:
                        exit_price, exit_reason = signal.target, "TARGET"
                        exit_index = candle_index
                        break
            gross = signal.side * (exit_price / entry - 1) * 100
            trades.append(Trade(day.year, signal.side, gross, exit_reason))
            next_allowed_signal = exit_index + 1
    return trades


def _profit_factor(values: np.ndarray) -> float:
    profit = values[values > 0].sum()
    loss = abs(values[values < 0].sum())
    return float(profit / loss) if loss > 0 else float("inf")


def _summaries(trades: list[Trade]) -> pd.DataFrame:
    rows = []
    for cost_label, cost in (
        ("SOURCE_0.14", SOURCE_COST_PERCENT),
        ("CONSERVATIVE_0.22", CONSERVATIVE_COST_PERCENT),
    ):
        for year in (2023, 2024):
            for direction, side in (("ALL", None), ("LONG", 1), ("SHORT", -1)):
                selected = [
                    trade
                    for trade in trades
                    if trade.year == year and (side is None or trade.side == side)
                ]
                values = np.asarray(
                    [trade.gross_percent - cost for trade in selected],
                    dtype="float64",
                )
                if len(values):
                    upper = np.quantile(values, 0.99)
                    trimmed = values[values <= upper]
                    reasons = {
                        reason: sum(trade.exit_reason == reason for trade in selected)
                        for reason in ("TARGET", "STOP", "END_OF_DAY")
                    }
                    rows.append(
                        {
                            "cost": cost_label,
                            "year": year,
                            "direction": direction,
                            "trades": len(values),
                            "mean_net": float(values.mean()),
                            "median_net": float(np.median(values)),
                            "trimmed_mean_net": float(trimmed.mean()),
                            "win_rate": float((values > 0).mean() * 100),
                            "profit_factor": _profit_factor(values),
                            **reasons,
                        }
                    )
    return pd.DataFrame(rows)


def main() -> None:
    candles = load_candles_dataframe("SOLUSDT", "5m", DATA_START, ANALYSIS_END)
    data = _prepare_candles(candles)
    signals = _signals(data)
    print("SOL Classical Volume Profile Mean Reversion analysis")
    print(f"Data: {len(data)} consecutive closed 5m candles, gaps=0")
    print(
        "Fixed rules: prior UTC-day 100-bin/70% profile; VAH/VAL rejection; "
        "signed volume-weighted return > prior12 median; next-open entry; "
        "causal developing POC target; UTC-day exit"
    )
    print(f"Raw signals: {len(signals)}")
    for stop_percent in STOP_PERCENTS:
        trades = _simulate(data, signals, stop_percent)
        print(f"\nStop: {stop_percent:.1f}%")
        print(
            _summaries(trades).to_string(
                index=False, float_format=lambda value: f"{value:.4f}"
            )
        )


if __name__ == "__main__":
    main()
