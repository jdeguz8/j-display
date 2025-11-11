from jdisplay.logging_conf import setup_logging
from jdisplay.db_operations import DBOperations
from jdisplay.scrape_weather import WeatherScraper
from jdisplay.dbcm import DBCM
from datetime import date

def main():
    setup_logging()
    db = DBOperations(location="Winnipeg")
    db.initialize_db()
    s = WeatherScraper()

    while True:
        print("\nJ-Display")
        print("1) Fetch LAST _ months")
        print("2) Fetch a SPECIFIC RANGE (YYYY-MM to YYYY-MM)")
        print("3) Fetch a SINGLE MONTH (YYYY-MM)")
        print("4) Fetch ALL history (backwards until unavailable)")
        print("5) Delete all rows for this location")
        print("0) Exit")
        ch = input("Select: ").strip()

        if ch == "1":
            n = int(input("How many months (e.g., 6 or 12)? "))
            data = s.scrape_last_months(n, start=date.today())
            added = db.save_data({k: (v.mn, v.mx, v.av) for k, v in data.items()})
            print(f"Inserted {added} rows (last {n} months).")

        elif ch == "2":
            y1 = int(input("Newer year  (YYYY): "))
            m1 = int(input("Newer month (1-12): "))
            y2 = int(input("Older year  (YYYY): "))
            m2 = int(input("Older month (1-12): "))
            data = s.scrape_range(y1, m1, y2, m2)
            added = db.save_data({k: (v.mn, v.mx, v.av) for k, v in data.items()})
            print(f"Inserted {added} rows for {y2}-{m2:02d} .. {y1}-{m1:02d}.")

        elif ch == "3":
            y = int(input("Year (YYYY): "))
            m = int(input("Month (1-12): "))
            data = s.scrape_range(y, m, y, m)
            added = db.save_data({k: (v.mn, v.mx, v.av) for k, v in data.items()})
            print(f"Inserted {added} rows for {y}-{m:02d}.")

        elif ch == "4":
            data = s.scrape_backwards()
            added = db.save_data({k: (v.mn, v.mx, v.av) for k, v in data.items()})
            print(f"Inserted {added} rows (full history).")

        elif ch == "5":
            confirm = input("Type 'YES' to delete this location's rows: ")
            if confirm == "YES":
                with DBCM("weather.sqlite3") as cur:
                    cur.execute("DELETE FROM weather WHERE location=?", (db.location,))
                print("Purged.")
            else:
                print("Cancelled.")

        elif ch == "0":
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
