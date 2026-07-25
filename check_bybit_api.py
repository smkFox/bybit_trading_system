import json
import sys
from datetime import datetime, timedelta, timezone

import requests


API_URL = "https://api.bybit.com/v5/market/kline"
SYMBOL = "ETHUSDT"
CATEGORY = "linear"
INTERVAL = "15"
INTERVAL_MINUTES = 15
CANDLE_LIMIT = 5
REQUEST_TIMEOUT_SECONDS = 10


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

    candles = payload.get("result", {}).get("list", [])
    if not candles:
        print("Bybit returned no candles.", file=sys.stderr)
        raise SystemExit(1)

    start_times = [int(candle[0]) for candle in candles]
    newest_start = datetime.fromtimestamp(start_times[0] / 1000, tz=timezone.utc)
    newest_close = newest_start + timedelta(minutes=INTERVAL_MINUTES)
    now = datetime.now(timezone.utc)

    print("Inspection summary:")
    print(f"Returned category: {payload['result'].get('category')}")
    print(f"Returned symbol: {payload['result'].get('symbol')}")
    print(f"Candle count: {len(candles)}")
    print(f"Values are strings: {all(isinstance(value, str) for value in candles[0])}")
    print(f"Newest-first order: {start_times == sorted(start_times, reverse=True)}")
    print(f"Newest candle start (UTC): {newest_start.isoformat()}")
    print(f"Newest candle is closed: {now >= newest_close}")


if __name__ == "__main__":
    main()
