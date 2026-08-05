import sqlite3
from datetime import datetime
from pathlib import Path

from .time_utils import datetime_to_milliseconds, milliseconds_to_datetime


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite3"
)

CREATE_MARKET_CANDLES_TABLE = """
CREATE TABLE IF NOT EXISTS market_candles (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open_time INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    turnover REAL NOT NULL,
    PRIMARY KEY (symbol, timeframe, open_time)
)
"""

CREATE_OPEN_INTEREST_TABLE = """
CREATE TABLE IF NOT EXISTS open_interest (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open_interest REAL NOT NULL,
    PRIMARY KEY (symbol, timeframe, timestamp)
)
"""

CREATE_FUNDING_RATES_TABLE = """
CREATE TABLE IF NOT EXISTS funding_rates (
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    funding_rate REAL NOT NULL,
    PRIMARY KEY (symbol, timestamp)
)
"""


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(CREATE_MARKET_CANDLES_TABLE)
        connection.execute(CREATE_OPEN_INTEREST_TABLE)
        connection.execute(CREATE_FUNDING_RATES_TABLE)


def save_candles(
    candles: list[dict],
    database_path: Path = DATABASE_PATH,
) -> int:
    rows = [
        (
            candle["symbol"],
            candle["timeframe"],
            datetime_to_milliseconds(candle["open_time"]),
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
            candle["turnover"],
        )
        for candle in candles
    ]

    with sqlite3.connect(database_path) as connection:
        before_changes = connection.total_changes
        connection.executemany(
            """
            INSERT INTO market_candles (
                symbol,
                timeframe,
                open_time,
                open,
                high,
                low,
                close,
                volume,
                turnover
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, timeframe, open_time) DO NOTHING
            """,
            rows,
        )
        return connection.total_changes - before_changes


def get_latest_candle_time(
    symbol: str,
    timeframe: str,
    database_path: Path = DATABASE_PATH,
) -> datetime | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT MAX(open_time)
            FROM market_candles
            WHERE symbol = ? AND timeframe = ?
            """,
            (symbol, timeframe),
        ).fetchone()

    if row[0] is None:
        return None
    return milliseconds_to_datetime(row[0])


def save_open_interest(
    observations: list[dict],
    database_path: Path = DATABASE_PATH,
) -> int:
    rows = [
        (
            observation["symbol"],
            observation["timeframe"],
            datetime_to_milliseconds(observation["timestamp"]),
            observation["open_interest"],
        )
        for observation in observations
    ]
    with sqlite3.connect(database_path) as connection:
        before_changes = connection.total_changes
        connection.executemany(
            """
            INSERT INTO open_interest (
                symbol, timeframe, timestamp, open_interest
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
            """,
            rows,
        )
        return connection.total_changes - before_changes


def save_funding_rates(
    observations: list[dict],
    database_path: Path = DATABASE_PATH,
) -> int:
    rows = [
        (
            observation["symbol"],
            datetime_to_milliseconds(observation["timestamp"]),
            observation["funding_rate"],
        )
        for observation in observations
    ]
    with sqlite3.connect(database_path) as connection:
        before_changes = connection.total_changes
        connection.executemany(
            """
            INSERT INTO funding_rates (symbol, timestamp, funding_rate)
            VALUES (?, ?, ?)
            ON CONFLICT (symbol, timestamp) DO NOTHING
            """,
            rows,
        )
        return connection.total_changes - before_changes


def read_candles(
    symbol: str,
    timeframe: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    database_path: Path = DATABASE_PATH,
) -> list[dict]:
    conditions = ["symbol = ?", "timeframe = ?"]
    parameters: list = [symbol, timeframe]

    if start_time is not None:
        conditions.append("open_time >= ?")
        parameters.append(datetime_to_milliseconds(start_time))
    if end_time is not None:
        conditions.append("open_time <= ?")
        parameters.append(datetime_to_milliseconds(end_time))

    query = f"""
        SELECT
            symbol,
            timeframe,
            open_time,
            open,
            high,
            low,
            close,
            volume,
            turnover
        FROM market_candles
        WHERE {' AND '.join(conditions)}
        ORDER BY open_time ASC
    """

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()

    return [
        {
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "open_time": milliseconds_to_datetime(row["open_time"]),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "turnover": row["turnover"],
        }
        for row in rows
    ]


def read_open_interest(
    symbol: str,
    timeframe: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    database_path: Path = DATABASE_PATH,
) -> list[dict]:
    conditions = ["symbol = ?", "timeframe = ?"]
    parameters: list = [symbol, timeframe]
    if start_time is not None:
        conditions.append("timestamp >= ?")
        parameters.append(datetime_to_milliseconds(start_time))
    if end_time is not None:
        conditions.append("timestamp <= ?")
        parameters.append(datetime_to_milliseconds(end_time))

    query = f"""
        SELECT symbol, timeframe, timestamp, open_interest
        FROM open_interest
        WHERE {' AND '.join(conditions)}
        ORDER BY timestamp ASC
    """
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
    return [
        {
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "timestamp": milliseconds_to_datetime(row["timestamp"]),
            "open_interest": row["open_interest"],
        }
        for row in rows
    ]


def read_funding_rates(
    symbol: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    database_path: Path = DATABASE_PATH,
) -> list[dict]:
    conditions = ["symbol = ?"]
    parameters: list = [symbol]
    if start_time is not None:
        conditions.append("timestamp >= ?")
        parameters.append(datetime_to_milliseconds(start_time))
    if end_time is not None:
        conditions.append("timestamp <= ?")
        parameters.append(datetime_to_milliseconds(end_time))

    query = f"""
        SELECT symbol, timestamp, funding_rate
        FROM funding_rates
        WHERE {' AND '.join(conditions)}
        ORDER BY timestamp ASC
    """
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
    return [
        {
            "symbol": row["symbol"],
            "timestamp": milliseconds_to_datetime(row["timestamp"]),
            "funding_rate": row["funding_rate"],
        }
        for row in rows
    ]


def main() -> None:
    initialize_database()
    print(f"Database initialized: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
