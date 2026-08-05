import math
import time
from datetime import datetime, timedelta

import requests

from .time_utils import datetime_to_milliseconds, milliseconds_to_datetime


API_URL = "https://api.bybit.com/v5/market/kline"
CATEGORY = "linear"
MAX_CANDLE_LIMIT = 1000
REQUEST_TIMEOUT_SECONDS = 10
MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
RETRYABLE_BYBIT_CODES = {429, 10000, 10006, 10016}
TIMEFRAMES = {
    "5m": {"api_interval": "5", "minutes": 5},
    "15m": {"api_interval": "15", "minutes": 15},
    "1h": {"api_interval": "60", "minutes": 60},
}


def get_timeframe_minutes(timeframe: str) -> int:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")
    return TIMEFRAMES[timeframe]["minutes"]


def get_latest_closed_candle_time(
    timeframe: str,
    current_time: datetime,
) -> datetime:
    interval_ms = get_timeframe_minutes(timeframe) * 60 * 1000
    current_ms = datetime_to_milliseconds(current_time)
    current_candle_start_ms = current_ms - (current_ms % interval_ms)
    return milliseconds_to_datetime(current_candle_start_ms - interval_ms)


def build_candle_request_params(
    symbol: str,
    timeframe: str,
    limit: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")
    if not 1 <= limit <= MAX_CANDLE_LIMIT:
        raise ValueError(f"Candle limit must be between 1 and {MAX_CANDLE_LIMIT}.")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise ValueError("Start time must not be later than end time.")

    params = {
        "category": CATEGORY,
        "symbol": symbol.upper(),
        "interval": TIMEFRAMES[timeframe]["api_interval"],
        "limit": limit,
    }
    if start_time is not None:
        params["start"] = datetime_to_milliseconds(start_time)
    if end_time is not None:
        params["end"] = datetime_to_milliseconds(end_time)

    return params


def fetch_candle_payload(
    symbol: str,
    timeframe: str,
    limit: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    params = build_candle_request_params(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )

    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.ConnectionError, requests.Timeout):
            if attempt == MAX_REQUEST_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SECONDS * attempt)
            continue

        if response.status_code in RETRYABLE_HTTP_STATUS_CODES:
            if attempt == MAX_REQUEST_ATTEMPTS:
                response.raise_for_status()
            time.sleep(RETRY_DELAY_SECONDS * attempt)
            continue

        response.raise_for_status()
        payload = response.json()
        return_code = payload.get("retCode")

        if return_code == 0:
            return payload
        if return_code in RETRYABLE_BYBIT_CODES and attempt < MAX_REQUEST_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS * attempt)
            continue

        raise ValueError(
            f"Bybit API error {return_code}: "
            f"{payload.get('retMsg', 'unknown error')}"
        )

    raise RuntimeError("Bybit request attempts ended unexpectedly.")


def normalize_candles(
    payload: dict,
    current_time: datetime,
    timeframe: str,
) -> list[dict]:
    interval_minutes = get_timeframe_minutes(timeframe)
    datetime_to_milliseconds(current_time)

    result = payload.get("result", {})
    symbol = result.get("symbol")
    raw_candles = result.get("list", [])

    if not symbol:
        raise ValueError("Bybit response does not contain a symbol.")
    if not raw_candles:
        raise ValueError("Bybit response does not contain candles.")

    normalized_candles = []
    seen_open_times = set()

    for raw_candle in raw_candles:
        if len(raw_candle) != 7:
            raise ValueError(
                f"Expected 7 candle values, received {len(raw_candle)}."
            )

        open_time = milliseconds_to_datetime(int(raw_candle[0]))
        open_price = float(raw_candle[1])
        high_price = float(raw_candle[2])
        low_price = float(raw_candle[3])
        close_price = float(raw_candle[4])
        volume = float(raw_candle[5])
        turnover = float(raw_candle[6])

        numeric_values = (
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            turnover,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise ValueError(f"Candle at {open_time.isoformat()} has non-finite values.")
        if low_price > high_price:
            raise ValueError(f"Candle at {open_time.isoformat()} has low above high.")
        if low_price > min(open_price, close_price):
            raise ValueError(f"Candle at {open_time.isoformat()} has invalid low price.")
        if max(open_price, close_price) > high_price:
            raise ValueError(f"Candle at {open_time.isoformat()} has invalid high price.")
        if volume < 0 or turnover < 0:
            raise ValueError(f"Candle at {open_time.isoformat()} has negative volume.")
        if open_time in seen_open_times:
            raise ValueError(f"Duplicate candle at {open_time.isoformat()}.")

        seen_open_times.add(open_time)
        close_time = open_time + timedelta(minutes=interval_minutes)
        if close_time > current_time:
            continue

        normalized_candles.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "open_time": open_time,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "turnover": turnover,
            }
        )

    normalized_candles.sort(key=lambda candle: candle["open_time"])
    return normalized_candles
