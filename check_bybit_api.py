import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from time_utils import datetime_to_milliseconds, milliseconds_to_datetime


API_URL = "https://api.bybit.com/v5/market/kline"
SYMBOL = "ETHUSDT"
CATEGORY = "linear"
TIMEFRAME = "15m"
CANDLE_LIMIT = 5
MAX_CANDLE_LIMIT = 1000
REQUEST_TIMEOUT_SECONDS = 10
MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
RETRYABLE_BYBIT_CODES = {429, 10000, 10006, 10016}
TIMEFRAMES = {
    "15m": {"api_interval": "15", "minutes": 15},
    "1h": {"api_interval": "60", "minutes": 60},
}


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
    symbol: str = SYMBOL,
    timeframe: str = TIMEFRAME,
    limit: int = CANDLE_LIMIT,
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
    timeframe: str = TIMEFRAME,
) -> list[dict]:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("Current time must include a timezone.")

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
        interval_minutes = TIMEFRAMES[timeframe]["minutes"]
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


def print_candle_table(candles: list[dict]) -> None:
    print("Normalized closed candles:")
    print(
        f"{'symbol':<9} {'timeframe':<10} {'open_time (UTC)':<27} "
        f"{'open':>10} {'high':>10} {'low':>10} {'close':>10} "
        f"{'volume':>12} {'turnover':>16}"
    )

    for candle in candles:
        print(
            f"{candle['symbol']:<9} "
            f"{candle['timeframe']:<10} "
            f"{candle['open_time'].isoformat():<27} "
            f"{candle['open']:>10.2f} "
            f"{candle['high']:>10.2f} "
            f"{candle['low']:>10.2f} "
            f"{candle['close']:>10.2f} "
            f"{candle['volume']:>12.2f} "
            f"{candle['turnover']:>16.4f}"
        )


def main() -> None:
    request_params = build_candle_request_params(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        limit=CANDLE_LIMIT,
    )
    print(f"Request: GET {API_URL}")
    print(f"Parameters: {request_params}")

    try:
        payload = fetch_candle_payload()
    except (requests.RequestException, ValueError) as error:
        print(f"Bybit request failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("Raw JSON response:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    raw_candles = payload.get("result", {}).get("list", [])
    if not raw_candles:
        print("Bybit returned no candles.", file=sys.stderr)
        raise SystemExit(1)

    start_times = [int(candle[0]) for candle in raw_candles]
    newest_start = milliseconds_to_datetime(start_times[0])
    newest_close = newest_start + timedelta(
        minutes=TIMEFRAMES[TIMEFRAME]["minutes"]
    )
    now = datetime.now(timezone.utc)

    print("Inspection summary:")
    print(f"Returned category: {payload['result'].get('category')}")
    print(f"Returned symbol: {payload['result'].get('symbol')}")
    print(f"Candle count: {len(raw_candles)}")
    print(
        "Values are strings: "
        f"{all(isinstance(value, str) for value in raw_candles[0])}"
    )
    print(f"Newest-first order: {start_times == sorted(start_times, reverse=True)}")
    print(f"Newest candle start (UTC): {newest_start.isoformat()}")
    print(f"Newest candle is closed: {now >= newest_close}")

    try:
        candles = normalize_candles(payload, now)
    except (TypeError, ValueError) as error:
        print(f"Candle normalization failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Open candles excluded: {len(raw_candles) - len(candles)}")
    print_candle_table(candles)


if __name__ == "__main__":
    main()
