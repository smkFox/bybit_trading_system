import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "data" / "market_data.sqlite3"

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


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(CREATE_MARKET_CANDLES_TABLE)


def main() -> None:
    initialize_database()
    print(f"Database initialized: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
