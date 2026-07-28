import sqlite3
import sys
from datetime import datetime, timezone

import requests

from .bybit_market_data import fetch_candle_payload, normalize_candles
from .database import initialize_database, read_candles, save_candles


SYMBOL = "ETHUSDT"
TIMEFRAME = "15m"
CANDLE_LIMIT = 5


def main() -> None:
    initialize_database()

    payload = fetch_candle_payload(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
    raw_candle_count = len(payload["result"]["list"])
    candles = normalize_candles(
        payload,
        datetime.now(timezone.utc),
        TIMEFRAME,
    )
    if not candles:
        raise ValueError("Bybit returned no closed candles to store.")

    inserted_first = save_candles(candles)
    inserted_second = save_candles(candles)

    stored_candles = read_candles(SYMBOL, TIMEFRAME)
    range_candles = read_candles(
        SYMBOL,
        TIMEFRAME,
        start_time=candles[0]["open_time"],
        end_time=candles[-1]["open_time"],
    )

    if range_candles != candles:
        raise ValueError("Stored candles differ from normalized Bybit candles.")
    if stored_candles != sorted(
        stored_candles,
        key=lambda candle: candle["open_time"],
    ):
        raise ValueError("Stored candles are not in chronological order.")
    if inserted_second != 0:
        raise ValueError("Repeated insertion created duplicate candles.")

    print("Candle storage check:")
    print(f"Received from Bybit: {raw_candle_count}")
    print(f"Closed candles: {len(candles)}")
    print(f"Inserted on first attempt: {inserted_first}")
    print(f"Inserted on repeated attempt: {inserted_second}")
    print(f"Stored for {SYMBOL} {TIMEFRAME}: {len(stored_candles)}")
    print(f"Read from selected range: {len(range_candles)}")
    print("Values preserved: True")
    print("Chronological order: True")
    print("Duplicates created: False")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Candle storage check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
