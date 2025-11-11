import sqlite3
from pathlib import Path

class DBCM:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        self._conn = None
        self._cur = None

    def __enter__(self):
        self._conn = sqlite3.connect(self._db_path)
        self._cur = self._conn.cursor()
        return self._cur

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._conn.commit()
        self._conn.close()
