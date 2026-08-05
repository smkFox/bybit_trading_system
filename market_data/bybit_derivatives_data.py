import math
import time
from datetime import datetime

import requests

from .time_utils import datetime_to_milliseconds, milliseconds_to_datetime


CATEGORY = "linear"
OPEN_INTEREST_URL = "https://api.bybit.com/v5/market/open-interest"
FUNDING_RATE_URL = "https://api.bybit.com/v5/market/funding/history"
OPEN_INTEREST_LIMIT = 200
FUNDING_RATE_LIMIT = 200
REQUEST_TIMEOUT_SECONDS = 10
MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
RETRYABLE_BYBIT_CODES = {429, 10000, 10006, 10016}
OPEN_INTEREST_TIMEFRAMES = {
    "15m": "15min",
    "1h": "1h",
}


def _fetch_payload(url: str, params: dict) -> dict:
    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
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


def fetch_open_interest_payload(
    symbol: str,
    timeframe: str,
    limit: int = OPEN_INTEREST_LIMIT,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    if timeframe not in OPEN_INTEREST_TIMEFRAMES:
        raise ValueError(f"Unsupported Open Interest timeframe: {timeframe}.")
    if not 1 <= limit <= OPEN_INTEREST_LIMIT:
        raise ValueError(f"Open Interest limit must be between 1 and {OPEN_INTEREST_LIMIT}.")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise ValueError("Start time must not be later than end time.")

    params = {
        "category": CATEGORY,
        "symbol": symbol.upper(),
        "intervalTime": OPEN_INTEREST_TIMEFRAMES[timeframe],
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = datetime_to_milliseconds(start_time)
    if end_time is not None:
        params["endTime"] = datetime_to_milliseconds(end_time)
    return _fetch_payload(OPEN_INTEREST_URL, params)


def fetch_funding_rate_payload(
    symbol: str,
    limit: int = FUNDING_RATE_LIMIT,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    if not 1 <= limit <= FUNDING_RATE_LIMIT:
        raise ValueError(f"Funding Rate limit must be between 1 and {FUNDING_RATE_LIMIT}.")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise ValueError("Start time must not be later than end time.")

    params = {
        "category": CATEGORY,
        "symbol": symbol.upper(),
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = datetime_to_milliseconds(start_time)
    if end_time is not None:
        params["endTime"] = datetime_to_milliseconds(end_time)
    return _fetch_payload(FUNDING_RATE_URL, params)


def normalize_open_interest(payload: dict, timeframe: str) -> list[dict]:
    if timeframe not in OPEN_INTEREST_TIMEFRAMES:
        raise ValueError(f"Unsupported Open Interest timeframe: {timeframe}.")
    result = payload.get("result", {})
    symbol = result.get("symbol")
    raw_observations = result.get("list", [])
    if not symbol:
        raise ValueError("Bybit Open Interest response has no symbol.")

    normalized = []
    seen_timestamps = set()
    for raw in raw_observations:
        timestamp = milliseconds_to_datetime(int(raw["timestamp"]))
        value = float(raw["openInterest"])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid Open Interest at {timestamp.isoformat()}.")
        if timestamp in seen_timestamps:
            raise ValueError(f"Duplicate Open Interest at {timestamp.isoformat()}.")
        seen_timestamps.add(timestamp)
        normalized.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": timestamp,
                "open_interest": value,
            }
        )
    normalized.sort(key=lambda observation: observation["timestamp"])
    return normalized


def normalize_funding_rates(payload: dict, symbol: str) -> list[dict]:
    raw_observations = payload.get("result", {}).get("list", [])
    normalized = []
    seen_timestamps = set()
    expected_symbol = symbol.upper()
    for raw in raw_observations:
        if raw.get("symbol") != expected_symbol:
            raise ValueError("Bybit Funding Rate response has an unexpected symbol.")
        timestamp = milliseconds_to_datetime(int(raw["fundingRateTimestamp"]))
        value = float(raw["fundingRate"])
        if not math.isfinite(value):
            raise ValueError(f"Invalid Funding Rate at {timestamp.isoformat()}.")
        if timestamp in seen_timestamps:
            raise ValueError(f"Duplicate Funding Rate at {timestamp.isoformat()}.")
        seen_timestamps.add(timestamp)
        normalized.append(
            {
                "symbol": expected_symbol,
                "timestamp": timestamp,
                "funding_rate": value,
            }
        )
    normalized.sort(key=lambda observation: observation["timestamp"])
    return normalized
