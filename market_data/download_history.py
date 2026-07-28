import argparse
import sqlite3
import sys
from datetime import datetime, timezone

import requests

from .bybit_market_data import (
    MAX_CANDLE_LIMIT,
    TIMEFRAMES,
    fetch_candle_payload,
    normalize_candles,
)
from .database import initialize_database, save_candles
from .time_utils import datetime_to_milliseconds, milliseconds_to_datetime


def download_historical_candles(
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
    page_limit: int = MAX_CANDLE_LIMIT,
) -> dict:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")

    start_ms = datetime_to_milliseconds(start_time)
    end_ms = datetime_to_milliseconds(end_time)
    if start_ms > end_ms:
        raise ValueError("Start time must not be later than end time.")
    if not 1 <= page_limit <= MAX_CANDLE_LIMIT:
        raise ValueError(
            f"Page limit must be between 1 and {MAX_CANDLE_LIMIT}."
        )

    initialize_database()
    download_started_at = datetime.now(timezone.utc)
    cursor_end_ms = end_ms
    page_number = 0
    received_total = 0
    closed_total = 0
    inserted_total = 0

    while cursor_end_ms >= start_ms:
        page_number += 1
        payload = fetch_candle_payload(
            symbol=symbol,
            timeframe=timeframe,
            limit=page_limit,
            start_time=start_time,
            end_time=milliseconds_to_datetime(cursor_end_ms),
        )
        raw_candles = payload.get("result", {}).get("list", [])
        if not raw_candles:
            break

        raw_open_times = [int(candle[0]) for candle in raw_candles]
        oldest_raw_ms = min(raw_open_times)
        newest_raw_ms = max(raw_open_times)
        if oldest_raw_ms > cursor_end_ms:
            raise ValueError("Bybit returned candles beyond the page cursor.")

        normalized = normalize_candles(
            payload,
            current_time=download_started_at,
            timeframe=timeframe,
        )
        page_candles = [
            candle
            for candle in normalized
            if start_time <= candle["open_time"] <= end_time
        ]
        inserted = save_candles(page_candles)

        received_total += len(raw_candles)
        closed_total += len(page_candles)
        inserted_total += inserted

        print(
            f"Page {page_number}: "
            f"{milliseconds_to_datetime(oldest_raw_ms).isoformat()} -> "
            f"{milliseconds_to_datetime(newest_raw_ms).isoformat()}, "
            f"received={len(raw_candles)}, "
            f"closed={len(page_candles)}, "
            f"inserted={inserted}"
        )

        if oldest_raw_ms <= start_ms:
            break

        next_cursor_end_ms = oldest_raw_ms - 1
        if next_cursor_end_ms >= cursor_end_ms:
            raise ValueError("Historical download cursor did not move backward.")
        cursor_end_ms = next_cursor_end_ms

    summary = {
        "pages": page_number,
        "received": received_total,
        "closed": closed_total,
        "inserted": inserted_total,
    }
    print(
        "Download complete: "
        f"pages={summary['pages']}, "
        f"received={summary['received']}, "
        f"closed={summary['closed']}, "
        f"inserted={summary['inserted']}"
    )
    return summary


def parse_utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            "Datetime must include a timezone, for example +00:00."
        )
    return parsed.astimezone(timezone.utc)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download closed Bybit candles into SQLite."
    )
    parser.add_argument("symbol", help="Bybit symbol, for example ETHUSDT.")
    parser.add_argument("timeframe", choices=TIMEFRAMES, help="Candle timeframe.")
    parser.add_argument("start", type=parse_utc_datetime, help="Inclusive start time.")
    parser.add_argument("end", type=parse_utc_datetime, help="Inclusive end time.")
    parser.add_argument(
        "--page-limit",
        type=int,
        default=MAX_CANDLE_LIMIT,
        help=f"Candles per request, from 1 to {MAX_CANDLE_LIMIT}.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    download_historical_candles(
        symbol=arguments.symbol.upper(),
        timeframe=arguments.timeframe,
        start_time=arguments.start,
        end_time=arguments.end,
        page_limit=arguments.page_limit,
    )


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Historical download failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
