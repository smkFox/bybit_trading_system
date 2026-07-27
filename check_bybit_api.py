import json
import math
import sys
from datetime import datetime, timedelta, timezone

import requests


API_URL = "https://api.bybit.com/v5/market/kline"
SYMBOL = "ETHUSDT"
CATEGORY = "linear"
INTERVAL = "15"
INTERVAL_MINUTES = 15
TIMEFRAME = "15m"
CANDLE_LIMIT = 5
REQUEST_TIMEOUT_SECONDS = 10


def normalize_candles(
    payload: dict,
    current_time: datetime,
) -> list[dict]:
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

        open_time = datetime.fromtimestamp(
            int(raw_candle[0]) / 1000,
            tz=timezone.utc,
        )
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
        close_time = open_time + timedelta(minutes=INTERVAL_MINUTES)
        if close_time > current_time:
            continue

        normalized_candles.append(
            {
                "symbol": symbol,
                "timeframe": TIMEFRAME,
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
    params = {
        "category": CATEGORY,
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": CANDLE_LIMIT,
    }

    print(f"Request: GET {API_URL}")
    print(f"Parameters: {params}")

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"HTTP status: {response.status_code}")
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(f"Bybit request failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("Raw JSON response:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if payload.get("retCode") != 0:
        print(
            f"Bybit API error: {payload.get('retMsg', 'unknown error')}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    raw_candles = payload.get("result", {}).get("list", [])
    if not raw_candles:
        print("Bybit returned no candles.", file=sys.stderr)
        raise SystemExit(1)

    start_times = [int(candle[0]) for candle in raw_candles]
    newest_start = datetime.fromtimestamp(start_times[0] / 1000, tz=timezone.utc)
    newest_close = newest_start + timedelta(minutes=INTERVAL_MINUTES)
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
