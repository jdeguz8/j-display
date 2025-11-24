# jdisplay/db_operations.py
from pathlib import Path
from .dbcm import DBCM

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = APP_ROOT / "weather.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS weather(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sample_date TEXT NOT NULL,
  location    TEXT NOT NULL,
  min_temp REAL, max_temp REAL, avg_temp REAL,
  UNIQUE(sample_date, location)
);
"""

class DBOperations:
    def __init__(self, db_path: str | Path = DEFAULT_DB, location="Winnipeg"):
        self.db_path = Path(db_path)  # absolute path (DEFAULT_DB already absolute)
        self.location = location

    def initialize_db(self):
        with DBCM(self.db_path) as cur:
            cur.execute(SCHEMA)

    def save_data(self, rows: dict[str, tuple[float|None,float|None,float|None]]) -> int:
        inserted = 0
        with DBCM(self.db_path) as cur:
            for d, (mn, mx, av) in rows.items():
                cur.execute("""INSERT OR IGNORE INTO weather(sample_date,location,min_temp,max_temp,avg_temp)
                               VALUES(?,?,?,?,?)""", (d, self.location, mn, mx, av))
                inserted += (cur.rowcount or 0)
        return inserted

    def fetch_data(self, y1: int, y2: int):
        with DBCM(self.db_path) as cur:
            cur.execute("""SELECT sample_date,min_temp,max_temp,avg_temp
                           FROM weather
                           WHERE location=? AND CAST(substr(sample_date,1,4) AS INT) BETWEEN ? AND ?
                           ORDER BY sample_date""", (self.location, y1, y2))
            return cur.fetchall()
