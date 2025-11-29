"""Scrape daily weather (min / max / mean) from Environment Canada.

This module uses the public CSV "bulk data" endpoint that powers the
"Download Data" button on climate.weather.gc.ca.

Public API:
    - WeatherScraper.scrape_backwards(...)
    - WeatherScraper.scrape_last_months(...)
    - WeatherScraper.scrape_range(...)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

# ---------- Station / endpoint config ----------

DEFAULT_STATION_ID = 27174  # Winnipeg (long-running station)
TIMEFRAME = 2  # 2 = daily data
CSV_BASE = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"


@dataclass(frozen=True)
class Day:
    """One day's temperatures."""
    mn: Optional[float]
    mx: Optional[float]
    av: Optional[float]


class WeatherScraper:
    """Fetch monthly CSVs and expose them as a dict of date -> Day."""

    def __init__(
        self,
        station_id: int = DEFAULT_STATION_ID,
        pause_s: float = 0.4,
        user_agent: str | None = None,
    ) -> None:
        self.station_id = station_id
        self.pause_s = pause_s
        self.user_agent = user_agent or "J-Display/1.0 (+student project)"

    # ------------------ public methods ------------------

    def scrape_backwards(self, start: date | None = None, progress=None) -> dict[str, Day]:
        """From 'start' month (or today) go backwards until the CSV is empty."""
        if start is None:
            today = date.today()
            year, month = today.year, today.month
        else:
            year, month = start.year, start.month

        results: dict[str, Day] = {}
        while True:
            rows = self._fetch_month_csv(year, month, progress)
            if not rows:
                break
            results.update(self._parse_month_rows(rows, year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            time.sleep(self.pause_s)
        return results

    def scrape_last_months(
        self,
        months: int,
        start: date | None = None,
        progress=None,
    ) -> dict[str, Day]:
        """Collect only the last *months* months (nice for demos / dashboard)."""
        if months <= 0:
            return {}

        if start is None:
            start = date.today()
        year, month = start.year, start.month

        remaining = months
        out: dict[str, Day] = {}
        while remaining > 0:
            rows = self._fetch_month_csv(year, month, progress)
            if not rows:
                break
            out.update(self._parse_month_rows(rows, year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            remaining -= 1
            time.sleep(self.pause_s)
        return out

    def scrape_range(
        self,
        y1: int,
        m1: int,
        y2: int,
        m2: int,
        progress=None,
    ) -> dict[str, Day]:
        """Collect data from (y1, m1) down to (y2, m2), inclusive, going backwards."""
        assert 1 <= m1 <= 12 and 1 <= m2 <= 12
        start_newer = (y1, m1) if (y1, m1) >= (y2, m2) else (y2, m2)
        end_older = (y2, m2) if (y1, m1) >= (y2, m2) else (y1, m1)

        year, month = start_newer
        out: dict[str, Day] = {}
        while (year, month) >= end_older:
            rows = self._fetch_month_csv(year, month, progress)
            if not rows:
                break
            out.update(self._parse_month_rows(rows, year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            time.sleep(self.pause_s)
        return out

    # ------------------ internal helpers ------------------

    def _fetch_month_csv(
        self,
        year: int,
        month: int,
        progress=None,
    ) -> list[dict] | None:
        """Download a single month as CSV and return a list of dict rows."""
        params = {
            "format": "csv",
            "stationID": str(self.station_id),
            "Year": str(year),
            "Month": str(month),
            "Day": "1",
            "timeframe": str(TIMEFRAME),
            "submit": " Download Data",
        }
        url = f"{CSV_BASE}?{urllib.parse.urlencode(params)}"

        if callable(progress):
            try:
                progress(f"Fetching {year:04d}-{month:02d} …")
            except Exception:
                pass

        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                log.info("HTTP 404 for %04d-%02d (station %s)", year, month, self.station_id)
                return None
            log.exception(
                "HTTP %s for %04d-%02d (station %s)",
                exc.code,
                year,
                month,
                self.station_id,
            )
            return None
        except Exception:  
            log.exception("Fetch failed %04d-%02d (station %s)", year, month, self.station_id)
            return None

        try:
            text = raw.decode("utf-8", errors="ignore")
            buf = io.StringIO(text)
            reader = csv.DictReader(buf)
            rows = list(reader)
            return rows
        except Exception: 
            log.exception("CSV parse failed %04d-%02d (station %s)", year, month, self.station_id)
            return []

    def _parse_month_rows(
        self,
        rows: list[dict],
        year: int,
        month: int,
    ) -> dict[str, Day]:
        """Extract min / max / mean for each day from CSV rows."""
        results: dict[str, Day] = {}
        day_rows = 0
        matched = 0

        if not rows:
            return results

        def pick(*candidates: str) -> Optional[str]:
            """Return the first matching header name from the CSV, case-insensitive."""
            lower_map = {k.lower(): k for k in rows[0].keys()}
            for candidate in candidates:
                if candidate.lower() in lower_map:
                    return lower_map[candidate.lower()]
            return None

        col_date = pick("Date/Time", "Date", "Local Date")
        col_max = pick("Max Temp (°C)", "Max Temp (Â°C)", "Max Temp (C)")
        col_min = pick("Min Temp (°C)", "Min Temp (Â°C)", "Min Temp (C)")
        col_mean = pick("Mean Temp (°C)", "Mean Temp (Â°C)", "Mean Temp (C)")

        for row in rows:
            dstr = (row.get(col_date) or "").strip() if col_date else ""
            if len(dstr) < 10 or dstr[:7] != f"{year:04d}-{month:02d}":
                continue

            day_rows += 1
            dkey = dstr[:10]  # YYYY-MM-DD

            def as_num(val: Optional[str]) -> Optional[float]:
                if val is None:
                    return None
                text = val.strip()
                if not text or text.upper() == "NA":
                    return None
                try:
                    return float(text)
                except ValueError:
                    return None

            mx = as_num(row.get(col_max)) if col_max else None
            mn = as_num(row.get(col_min)) if col_min else None
            av = as_num(row.get(col_mean)) if col_mean else None

            if any(v is not None for v in (mn, mx, av)):
                matched += 1

            results[dkey] = Day(mn, mx, av)

        log.info(
            "Parsed %04d-%02d (CSV): day_rows=%d matched=%d",
            year,
            month,
            day_rows,
            matched,
        )
        return results
