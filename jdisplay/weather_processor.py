from __future__ import annotations
from pathlib import Path
from typing import Optional

from .db_operations import DBOperations
from .plot_operations import PlotOps

def _ask_int(prompt: str, lo: int | None = None, hi: int | None = None) -> int:
    while True:
        try:
            v = int(input(prompt).strip())
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                print(f"Enter a value between {lo} and {hi}.")
                continue
            return v
        except ValueError:
            print("Please enter a valid integer.")

def _ensure_rows(db: DBOperations, y1: int, y2: int):
    rows = db.fetch_data(y1, y2)
    if not rows:
        print("No rows found in this range. Seed data with the CLI first (Option 1/2/3).")
    return rows

def main():
    db = DBOperations()  # uses absolute path set in your updated db_operations.py
    db.initialize_db()
    plots = PlotOps()

    print("J-Display |Plots & Menu")
    while True:
        print("\nMenu:")
        print("1) Boxplot: pick a year range (e.g., 2024..2025)")
        print("2) Line plot: pick a year + month")
        print("3) Save BOTH plots (no GUI) for quick dashboard import")
        print("4) Show last 10 DB rows")
        print("0) Exit")
        ch = input("Select: ").strip()

        if ch == "1":
            y1 = _ask_int("From year: ", 1900, 2100)
            y2 = _ask_int("To year:   ", 1900, 2100)
            if y2 < y1:
                y1, y2 = y2, y1
            rows = _ensure_rows(db, y1, y2)
            if rows:
                plots.boxplot_by_month(rows, show=True, save=False)

        elif ch == "2":
            y = _ask_int("Year (YYYY): ", 1900, 2100)
            m = _ask_int("Month (1-12): ", 1, 12)
            rows = _ensure_rows(db, y, y)
            if rows:
                plots.line_for_month(rows, y, m, show=True, save=False)

        elif ch == "3":
            # non-interactive save so you can drop images into the Pi dashboard
            y1 = _ask_int("Boxplot range start year: ", 1900, 2100)
            y2 = _ask_int("Boxplot range end year:   ", 1900, 2100)
            if y2 < y1:
                y1, y2 = y2, y1
            by_rows = _ensure_rows(db, y1, y2)
            if by_rows:
                plots.boxplot_by_month(by_rows, show=False, save=True, fname=f"box_{y1}-{y2}.png")

            y = _ask_int("Line plot year (YYYY): ", 1900, 2100)
            m = _ask_int("Line plot month (1-12): ", 1, 12)
            ln_rows = _ensure_rows(db, y, y)
            if ln_rows:
                plots.line_for_month(ln_rows, y, m, show=False, save=True)

        elif ch == "4":
            rows = db.fetch_data(1900, 9999)
            tail = rows[-10:] if rows else []
            if not tail:
                print("No rows in DB yet.")
            else:
                print("Last 10 rows (date, min, max, avg):")
                for r in tail:
                    print(r)

        elif ch == "0":
            break

        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
