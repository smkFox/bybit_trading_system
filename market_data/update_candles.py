import argparse
import sqlite3
import sys
from datetime import datetime, timezone

import requests

from .bybit_market_data import TIMEFRAMES, get_latest_closed_candle_time
from .database import get_latest_candle_time, initialize_database
from .download_history import download_historical_candles


def update_candles(
    symbol: str,
    timeframe: str,
    current_time: datetime | None = None,
) -> dict:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")

    symbol = symbol.upper()
    now = current_time or datetime.now(timezone.utc)
    latest_closed = get_latest_closed_candle_time(timeframe, now)

    initialize_database()
    latest_stored = get_latest_candle_time(symbol, timeframe)
    if latest_stored is None:
        raise ValueError(
            f"No stored candles for {symbol} {timeframe}. "
            "Run python -m market_data.download_history first."
        )

    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Latest stored: {latest_stored.isoformat()}")
    print(f"Latest closed: {latest_closed.isoformat()}")

    if latest_stored >= latest_closed:
        print("Database is already up to date.")
        print("New candles inserted: 0")
        return {
            "inserted": 0,
            "latest_stored": latest_stored,
            "latest_closed": latest_closed,
            "up_to_date": True,
        }

    download_summary = download_historical_candles(
        symbol=symbol,
        timeframe=timeframe,
        start_time=latest_stored,
        end_time=latest_closed,
    )
    updated_latest = get_latest_candle_time(symbol, timeframe)
    up_to_date = updated_latest is not None and updated_latest >= latest_closed
    if not up_to_date:
        raise ValueError(
            f"Update ended at {updated_latest}; expected {latest_closed.isoformat()}."
        )

    print(f"New candles inserted: {download_summary['inserted']}")
    print("Database is up to date: True")
    return {
        "inserted": download_summary["inserted"],
        "latest_stored": updated_latest,
        "latest_closed": latest_closed,
        "up_to_date": True,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download missing closed Bybit candles into SQLite."
    )
    parser.add_argument("symbol", help="Bybit symbol, for example ETHUSDT.")
    parser.add_argument("timeframe", choices=TIMEFRAMES, help="Candle timeframe.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    update_candles(arguments.symbol, arguments.timeframe)


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Candle update failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
