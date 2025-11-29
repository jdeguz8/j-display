from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import os
import sqlite3

from .dbcm import DBCM

# ---------- DB LOCATION (shared by CLI + EXE) ----------

def get_default_db_path() -> Path:
    """
    Shared DB location for both:
      - python cli.py   (source)
      - J-Display.exe   (packaged)
    On Windows:  C:\\Users\\<you>\\AppData\\Local\\J-Display\\weather.sqlite3
    """
    local = os.getenv("LOCALAPPDATA")
    if local:
        base = Path(local) / "J-Display"
    else:
        base = Path.home() / ".jdisplay"

    base.mkdir(parents=True, exist_ok=True)
    return base / "weather.sqlite3"


# ---------- DB OPERATIONS ----------

class DBOperations:
    """High-level operations for the weather SQLite database."""

    def __init__(self, location: str = "Winnipeg", db_path: Path | None = None):
        self.location = location
        self.db_path: Path = Path(db_path) if db_path else get_default_db_path()
        # Always make sure schema exists
        self.initialize_db()

    def initialize_db(self) -> None:
        """Create the weather table if it does not already exist."""
        with DBCM(self.db_path) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS weather (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_date TEXT    NOT NULL,
                    location    TEXT    NOT NULL,
                    min_temp    REAL,
                    max_temp    REAL,
                    avg_temp    REAL,
                    UNIQUE(sample_date, location)
                );
                """
            )

    def save_data(
        self,
        data: Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]]
    ) -> int:
        """
        Insert weather rows; returns the number of NEW rows.
        Existing rows (same date+location) are ignored.
        """
        self.initialize_db()
        rows: List[Tuple[str, str, Optional[float], Optional[float], Optional[float]]] = []
        for d, (mn, mx, av) in data.items():
            rows.append((d, self.location, mn, mx, av))

        with DBCM(self.db_path) as cur:
            cur.executemany(
                """
                INSERT OR IGNORE INTO weather
                    (sample_date, location, min_temp, max_temp, avg_temp)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            return cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0

    def fetch_data(self, y1: int, y2: int):
        """
        Return all rows with sample_date in [y1..y2] (inclusive),
        sorted by date.
        """
        self.initialize_db()
        try:
            with DBCM(self.db_path) as cur:
                cur.execute(
                    """
                    SELECT sample_date, min_temp, max_temp, avg_temp
                    FROM weather
                    WHERE substr(sample_date, 1, 4) BETWEEN ? AND ?
                    ORDER BY sample_date
                    """,
                    (str(y1), str(y2)),
                )
                return cur.fetchall()
        except sqlite3.OperationalError as e:
            # Belt-and-suspenders: if somehow the table still doesn't exist, create then retry once.
            if "no such table: weather" in str(e).lower():
                self.initialize_db()
                with DBCM(self.db_path) as cur:
                    cur.execute(
                        """
                        SELECT sample_date, min_temp, max_temp, avg_temp
                        FROM weather
                        WHERE substr(sample_date, 1, 4) BETWEEN ? AND ?
                        ORDER BY sample_date
                        """,
                        (str(y1), str(y2)),
                    )
                    return cur.fetchall()
            raise
