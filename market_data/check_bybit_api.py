import json
import sys
from datetime import datetime, timedelta, timezone

import requests

from .bybit_market_data import (
    API_URL,
    build_candle_request_params,
    fetch_candle_payload,
    get_timeframe_minutes,
    normalize_candles,
)
from .time_utils import milliseconds_to_datetime


SYMBOL = "ETHUSDT"
TIMEFRAME = "15m"
CANDLE_LIMIT = 5


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
        payload = fetch_candle_payload(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            limit=CANDLE_LIMIT,
        )
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
        minutes=get_timeframe_minutes(TIMEFRAME)
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
        candles = normalize_candles(payload, now, TIMEFRAME)
    except (TypeError, ValueError) as error:
        print(f"Candle normalization failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Open candles excluded: {len(raw_candles) - len(candles)}")
    print_candle_table(candles)


if __name__ == "__main__":
    main()
