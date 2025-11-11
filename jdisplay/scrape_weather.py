from __future__ import annotations
"""
Scrape daily Winnipeg weather (min/max/mean) from Environment Canada using the CSV endpoint.

Public API:
- WeatherScraper.scrape_backwards(start: date|None, progress=None) -> dict[str, Day]
- WeatherScraper.scrape_last_months(months: int, start: date|None, progress=None) -> dict[str, Day]
- WeatherScraper.scrape_range(y1, m1, y2, m2, progress=None) -> dict[str, Day]

Notes:
- Uses bulk CSV endpoint (no JavaScript required).
- Safely handles 'NA'/empty cells -> None.
"""

from dataclasses import dataclass
from datetime import date
import csv
import io
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

# Station config: Winnipeg (The Forks A / long-running station). Adjust if needed.
STATION_ID = 27174    # you can make this configurable later
TIMEFRAME  = 2        # 2 = daily data

# CSV endpoint (documented by EC’s site via the “Download Data” button)
CSV_BASE = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"

@dataclass(frozen=True)
class Day:
    mn: float | None
    mx: float | None
    av: float | None


class WeatherScraper:
    """
    Fetches month CSVs and returns a dict keyed by 'YYYY-MM-DD' -> Day(min, max, avg).
    """
    def __init__(self, pause_s: float = 0.35, user_agent: str | None = None):
        self.pause_s = pause_s
        self.user_agent = user_agent or "J-Display/1.0 (+educational project)"

    # ------------------ public methods ------------------

    def scrape_backwards(self, start: date | None = None, progress=None) -> dict[str, Day]:
        """
        From 'start' month (or today) go backwards until the CSV returns no rows.
        """
        if start is None:
            today = date.today()
            y, m = today.year, today.month
        else:
            y, m = start.year, start.month

        results: dict[str, Day] = {}
        while True:
            rows = self._fetch_month_csv(y, m, progress)
            if not rows:
                break
            results.update(self._parse_month_rows(rows, y, m))
            # step back one month
            m -= 1
            if m == 0:
                m = 12
                y -= 1
            time.sleep(self.pause_s)
        return results

    def scrape_last_months(self, months: int, start: date | None = None, progress=None) -> dict[str, Day]:
        """
        Collect only the last N months (great for demos).
        """
        if months <= 0:
            return {}

        if start is None:
            start = date.today()
        y, m = start.year, start.month

        remaining = months
        out: dict[str, Day] = {}
        while remaining > 0:
            rows = self._fetch_month_csv(y, m, progress)
            if not rows:
                break
            out.update(self._parse_month_rows(rows, y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
            remaining -= 1
            time.sleep(self.pause_s)
        return out

    def scrape_range(self, y1: int, m1: int, y2: int, m2: int, progress=None) -> dict[str, Day]:
        """
        Collect a specific range from (y1,m1) down to (y2,m2), inclusive, moving backwards.
        Order is normalized so we always go from newer -> older.
        """
        assert 1 <= m1 <= 12 and 1 <= m2 <= 12
        start_newer = (y1, m1) if (y1, m1) >= (y2, m2) else (y2, m2)
        end_older   = (y2, m2) if (y1, m1) >= (y2, m2) else (y1, m1)

        y, m = start_newer
        out: dict[str, Day] = {}
        while (y, m) >= end_older:
            rows = self._fetch_month_csv(y, m, progress)
            if not rows:
                break
            out.update(self._parse_month_rows(rows, y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
            time.sleep(self.pause_s)
        return out

    # ------------------ internal helpers ------------------

    def _fetch_month_csv(self, y: int, m: int, progress=None) -> list[dict] | None:
        """
        Download a single month as CSV and return a list of dict rows.
        Returns None on 404 / network error; returns [] if CSV is empty for that month.
        """
        params = {
            "format": "csv",
            "stationID": str(STATION_ID),
            "Year": str(y),
            "Month": str(m),
            "Day": "1",
            "timeframe": str(TIMEFRAME),
            "submit": " Download Data"
        }
        url = f"{CSV_BASE}?{urllib.parse.urlencode(params)}"

        if callable(progress):
            try:
                progress(f"Fetching {y:04d}-{m:02d} …")
            except Exception:
                pass

        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log.exception("HTTP %s for %04d-%02d", e.code, y, m)
            return None
        except Exception:
            log.exception("Fetch failed %04d-%02d", y, m)
            return None

        # Decode to text and feed into csv.DictReader
        try:
            text = raw.decode("utf-8", errors="ignore")
            # Some responses include a leading UTF-8 BOM or comments; DictReader can handle it.
            buf = io.StringIO(text)
            reader = csv.DictReader(buf)
            rows = [row for row in reader]
            return rows
        except Exception:
            log.exception("CSV parse failed %04d-%02d", y, m)
            return []

    def _parse_month_rows(self, rows: list[dict], y: int, m: int) -> dict[str, Day]:
        """
        Extract min/max/mean for each day from the CSV rows.
        Expected headers include:
          'Date/Time', 'Max Temp (°C)', 'Min Temp (°C)', 'Mean Temp (°C)'
        """
        results: dict[str, Day] = {}
        day_rows = 0
        matched = 0

        # Header names can vary a bit; be defensive:
        def pick(*candidates: str) -> str | None:
            lower_map = {k.lower(): k for k in rows[0].keys()} if rows else {}
            for c in candidates:
                if c.lower() in lower_map:
                    return lower_map[c.lower()]
            return None

        col_date = pick("Date/Time", "Date", "Local Date")
        col_max  = pick("Max Temp (°C)", "Max Temp (Â°C)", "Max Temp (C)")
        col_min  = pick("Min Temp (°C)", "Min Temp (Â°C)", "Min Temp (C)")
        col_mean = pick("Mean Temp (°C)", "Mean Temp (Â°C)", "Mean Temp (C)")

        for row in rows:
            # Many CSVs include summary/footer lines; ensure we're in the target month.
            dstr = (row.get(col_date) or "").strip() if col_date else ""
            # Accept formats like '2025-11-09' or '2025-11-09 00:00'
            if len(dstr) < 10 or dstr[:7] != f"{y:04d}-{m:02d}":
                continue
            day_rows += 1
            dkey = dstr[:10]  # YYYY-MM-DD

            def as_num(val: str | None) -> float | None:
                if val is None:
                    return None
                s = val.strip()
                if not s or s.upper() == "NA":
                    return None
                try:
                    return float(s)
                except ValueError:
                    return None

            mx = as_num(row.get(col_max))  if col_max  else None
            mn = as_num(row.get(col_min))  if col_min  else None
            av = as_num(row.get(col_mean)) if col_mean else None
            if any(v is not None for v in (mn, mx, av)):
                matched += 1
            results[dkey] = Day(mn, mx, av)

        log.info("Parsed %04d-%02d (CSV): day_rows=%d matched=%d", y, m, day_rows, matched)
        return results
