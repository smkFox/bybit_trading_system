import argparse
import sqlite3
import sys
from collections.abc import Callable
from datetime import datetime

import requests

from .bybit_derivatives_data import (
    FUNDING_RATE_LIMIT,
    OPEN_INTEREST_LIMIT,
    OPEN_INTEREST_TIMEFRAMES,
    fetch_funding_rate_payload,
    fetch_open_interest_payload,
    normalize_funding_rates,
    normalize_open_interest,
)
from .database import initialize_database, save_funding_rates, save_open_interest
from .download_history import parse_utc_datetime
from .time_utils import datetime_to_milliseconds, milliseconds_to_datetime


def _download_backward(
    *,
    start_time: datetime,
    end_time: datetime,
    fetch: Callable[[datetime], dict],
    normalize: Callable[[dict], list[dict]],
    save: Callable[[list[dict]], int],
) -> dict[str, int]:
    start_ms = datetime_to_milliseconds(start_time)
    end_ms = datetime_to_milliseconds(end_time)
    if start_ms > end_ms:
        raise ValueError("Start time must not be later than end time.")

    cursor_end_ms = end_ms
    pages = received = inserted_total = 0
    while cursor_end_ms >= start_ms:
        pages += 1
        payload = fetch(milliseconds_to_datetime(cursor_end_ms))
        observations = normalize(payload)
        if not observations:
            break
        page = [
            observation
            for observation in observations
            if start_time <= observation["timestamp"] <= end_time
        ]
        inserted = save(page)
        received += len(observations)
        inserted_total += inserted
        oldest = min(observation["timestamp"] for observation in observations)
        newest = max(observation["timestamp"] for observation in observations)
        print(
            f"Page {pages}: {oldest.isoformat()} -> {newest.isoformat()}, "
            f"received={len(observations)}, inserted={inserted}"
        )
        oldest_ms = datetime_to_milliseconds(oldest)
        if oldest_ms <= start_ms:
            break
        next_cursor = oldest_ms - 1
        if next_cursor >= cursor_end_ms:
            raise ValueError("Historical download cursor did not move backward.")
        cursor_end_ms = next_cursor

    summary = {"pages": pages, "received": received, "inserted": inserted_total}
    print(
        f"Download complete: pages={pages}, received={received}, "
        f"inserted={inserted_total}"
    )
    return summary


def download_open_interest(
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
) -> dict[str, int]:
    if timeframe not in OPEN_INTEREST_TIMEFRAMES:
        raise ValueError(f"Unsupported Open Interest timeframe: {timeframe}.")
    initialize_database()
    return _download_backward(
        start_time=start_time,
        end_time=end_time,
        fetch=lambda cursor: fetch_open_interest_payload(
            symbol, timeframe, OPEN_INTEREST_LIMIT, start_time, cursor
        ),
        normalize=lambda payload: normalize_open_interest(payload, timeframe),
        save=save_open_interest,
    )


def download_funding_rates(
    symbol: str,
    start_time: datetime,
    end_time: datetime,
) -> dict[str, int]:
    initialize_database()
    return _download_backward(
        start_time=start_time,
        end_time=end_time,
        fetch=lambda cursor: fetch_funding_rate_payload(
            symbol, FUNDING_RATE_LIMIT, start_time, cursor
        ),
        normalize=lambda payload: normalize_funding_rates(payload, symbol),
        save=save_funding_rates,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Bybit Open Interest or Funding Rate history."
    )
    subparsers = parser.add_subparsers(dest="dataset", required=True)

    open_interest = subparsers.add_parser("open-interest")
    open_interest.add_argument("symbol")
    open_interest.add_argument("timeframe", choices=OPEN_INTEREST_TIMEFRAMES)
    open_interest.add_argument("start", type=parse_utc_datetime)
    open_interest.add_argument("end", type=parse_utc_datetime)

    funding = subparsers.add_parser("funding")
    funding.add_argument("symbol")
    funding.add_argument("start", type=parse_utc_datetime)
    funding.add_argument("end", type=parse_utc_datetime)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.dataset == "open-interest":
        download_open_interest(
            arguments.symbol.upper(),
            arguments.timeframe,
            arguments.start,
            arguments.end,
        )
    else:
        download_funding_rates(
            arguments.symbol.upper(),
            arguments.start,
            arguments.end,
        )


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Derivatives history download failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
