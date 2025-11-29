"""Tkinter dashboard application for the J-Display project."""

from __future__ import annotations

import calendar
import datetime as dt
from datetime import date
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .config import load_config, save_config
from .db_operations import DBOperations
from .plot_operations import PlotOps
from .scrape_weather import WeatherScraper

# Pillow to display PNG plots
try:
    from PIL import Image, ImageTk
except Exception as e:
    raise RuntimeError("Install Pillow: pip install pillow") from e

"""Main Tkinter window: calendar + plots + settings."""
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J-Display")
        self.geometry("1280x800")
        self.resizable(True, True)

        # ---- config & theme ----
        self.cfg = load_config()
        app_cfg = self.cfg["app"]

        self.theme = app_cfg.get("theme", "dark")
        self.clock_24h = bool(app_cfg.get("clock_24h", True))
        self.location = app_cfg.get("location", "Winnipeg")
        self.station_id = int(app_cfg.get("station_id", 27174))

        self.plots_dir = Path(app_cfg.get("plots_dir", "plots"))
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        # Plot helper (writes PNGs into plots_dir)
        self.plot_ops = PlotOps(out_dir=self.plots_dir)

        self._apply_theme()

        # ---- layout frames ----
        self.top = ttk.Frame(self)
        self.top.pack(side=tk.TOP, fill=tk.X)

        self.main = ttk.Frame(self)
        self.main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.bottom = ttk.Frame(self)
        self.bottom.pack(side=tk.BOTTOM, fill=tk.X)

        # ---- top bar: clock + theme + settings ----
        self.clock_lbl = ttk.Label(self.top, font=("Segoe UI", 18, "bold"))
        self.clock_lbl.pack(side=tk.LEFT, padx=10, pady=8)

        ttk.Button(self.top, text="Theme", command=self.toggle_theme).pack(
            side=tk.RIGHT, padx=8
        )
        ttk.Button(self.top, text="Settings", command=self.open_settings).pack(
            side=tk.RIGHT, padx=8
        )

        # ---- main: calendar vs plots ----
        self.view = "calendar"  # or "plots"
        self.calendar_fr = ttk.Frame(self.main)
        self.plots_fr = ttk.Frame(self.main)

        for f in (self.calendar_fr, self.plots_fr):
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        # calendar view
        self._build_calendar()

        # plots view
        self.plot_box_lbl = ttk.Label(self.plots_fr)
        self.plot_line_lbl = ttk.Label(self.plots_fr)
        self.plot_box_lbl.pack(side=tk.LEFT, expand=True, padx=8, pady=8)
        self.plot_line_lbl.pack(side=tk.RIGHT, expand=True, padx=8, pady=8)

        # ---- bottom bar: controls ----
        ttk.Button(self.bottom, text="Switch View", command=self.switch_view).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Button(self.bottom, text="Refresh Plots", command=self.refresh_plots).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Button(self.bottom, text="Update Data", command=self.update_data).pack(
            side=tk.LEFT, padx=8, pady=8
        )

        self._init_month_selector()
        self._load_available_years_and_default()

        # start on calendar
        self._show_calendar()

        # clock updater
        self.after(200, self._tick)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    """Apply the current light/dark theme to widgets."""
    def _apply_theme(self):
        bg = "#0f172a" if self.theme == "dark" else "#f3f4f6"
        fg = "#e5e7eb" if self.theme == "dark" else "#111827"
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=bg, foreground=fg)
        style.configure("TButton", padding=8)
        style.configure("TLabel", background=bg, foreground=fg)
        self.configure(bg=bg)

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.cfg["app"]["theme"] = self.theme
        save_config(self.cfg)
        self._apply_theme()

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def _tick(self):
        now = dt.datetime.now()
        if self.clock_24h:
            s = now.strftime("%Y-%m-%d  %H:%M:%S")
        else:
            s = now.strftime("%Y-%m-%d  %I:%M:%S %p")
        self.clock_lbl.config(text=s)
        self.after(1000, self._tick)

    # ------------------------------------------------------------------
    # Calendar view
    # ------------------------------------------------------------------
    """Render the month grid and the 'today' summary label."""    
    def _build_calendar(self):
        # simple month grid
        for w in self.calendar_fr.winfo_children():
            w.destroy()
        today = dt.date.today()
        year, month = today.year, today.month

        # Header frame: month/year + current weather
        header_fr = ttk.Frame(self.calendar_fr)
        header_fr.pack(pady=10, fill=tk.X)

        header = ttk.Label(
            header_fr,
            text=f"{calendar.month_name[month]} {year}",
            font=("Segoe UI", 20, "bold"),
        )
        header.pack(side=tk.LEFT, padx=(10, 16))

        # label that will show "Today: -5.0°C avg, 0.0° high, -10.0° low"
        self.current_weather_lbl = ttk.Label(
            header_fr,
            font=("Segoe UI", 12),
        )
        self.current_weather_lbl.pack(side=tk.LEFT, padx=8)

        # calendar grid below
        grid = ttk.Frame(self.calendar_fr)
        grid.pack(expand=True)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, d in enumerate(days):
            ttk.Label(grid, text=d, font=("Segoe UI", 12, "bold")).grid(
                row=0, column=i, padx=6, pady=6, sticky="nsew"
            )

        cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        for r, week in enumerate(cal, start=1):
            for c, day in enumerate(week):
                txt = "" if day == 0 else str(day)
                ttk.Label(grid, text=txt, font=("Segoe UI", 12)).grid(
                    row=r, column=c, padx=6, pady=6, sticky="nsew"
                )

        # populate the "current weather" text
        self._update_current_weather()

    def _update_current_weather(self):
        """Show today's (or latest) weather from the DB on the calendar view."""
        today = date.today()
        today_iso = today.isoformat()

        try:
            db = DBOperations(location=self.location)
            rows = db.fetch_data(1900, 9999)
        except Exception as e:
            print("current weather lookup failed:", e)
            if hasattr(self, "current_weather_lbl"):
                self.current_weather_lbl.config(text="Today: no data (DB error)")
            return

        if not rows:
            if hasattr(self, "current_weather_lbl"):
                self.current_weather_lbl.config(
                    text="Today: no data yet (use Update Data)"
                )
            return

        # rows: (sample_date, min_temp, max_temp, avg_temp)
        # keep only rows that actually have at least one numeric value
        valid_rows = [
            r for r in rows
            if any(v is not None for v in (r[1], r[2], r[3]))
        ]

        if not valid_rows:
            if hasattr(self, "current_weather_lbl"):
                self.current_weather_lbl.config(
                    text="Today: no temp data (all values are missing)"
                )
            return

        # Map by date string
        by_date = {r[0]: r for r in valid_rows}
        dates_sorted = sorted(by_date.keys())

        # 1) Prefer *today* if we have real data for today
        if today_iso in by_date:
            target_date = today_iso
            label_prefix = "Today"
        else:
            # 2) Otherwise, pick latest date <= today, or just latest overall
            candidates = [d for d in dates_sorted if d <= today_iso]
            if candidates:
                target_date = candidates[-1]
            else:
                target_date = dates_sorted[-1]
            label_prefix = f"Latest ({target_date})"

        _, mn, mx, av = by_date[target_date]

        parts = []
        if av is not None:
            parts.append(f"{av:.1f}°C avg")
        if mx is not None:
            parts.append(f"{mx:.1f}° high")
        if mn is not None:
            parts.append(f"{mn:.1f}° low")

        text = (
            f"{label_prefix}: " + ", ".join(parts)
            if parts
            else f"{label_prefix}: no temp data"
        )

        if hasattr(self, "current_weather_lbl"):
            self.current_weather_lbl.config(text=text)


    # ------------------------------------------------------------------
    # Plots view helpers
    # ------------------------------------------------------------------
    def _load_img_or_text(self, label: ttk.Label, path: Path, fallback: str):
        if path.exists():
            img = Image.open(path)
            img.thumbnail((600, 600))
            label.img = ImageTk.PhotoImage(img)  # keep ref
            label.config(image=label.img, text="")
        else:
            label.config(image="", text=fallback)

    def _show_plots(self):
        self._load_available_years_and_default()
        self.calendar_fr.lower()
        self.plots_fr.lift()
        box = self.plots_dir / "box_latest.png"
        line = self.plots_dir / "line_latest.png"
        self._load_img_or_text(self.plot_box_lbl, box, "box_latest.png not found")
        self._load_img_or_text(self.plot_line_lbl, line, "line_latest.png not found")

    def _show_calendar(self):
        self.plots_fr.lower()
        self.calendar_fr.lift()

    def switch_view(self):
        self.view = "plots" if self.view == "calendar" else "calendar"
        if self.view == "plots":
            self._show_plots()
        else:
            self._show_calendar()

    # ------------------------------------------------------------------
    # Plots: generate PNGs and reload
    # ------------------------------------------------------------------
    """Regenerate PNG plots from the DB and reload them into the UI."""
    def refresh_plots(self, silent: bool = False):
        """Read DB, generate latest box/line plots, and reload images."""
        try:
            db = DBOperations(location=self.location)
            rows = db.fetch_data(1900, 9999)
        except sqlite3.OperationalError as e:
            if not silent:
                messagebox.showwarning(
                    "Database not initialized",
                    "The weather table doesn't exist yet.\n\n"
                    "Use 'Update Data' or run the CLI scraper once.",
                )
            print("refresh_plots: DB not ready:", e)
            return
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"DB error: {e}")
            print("refresh_plots: unexpected DB error:", e)
            return

        if not rows:
            if not silent:
                messagebox.showwarning(
                    "No data", "Database is empty. Use 'Update Data' first."
                )
            return

        # Determine year/month to plot
        dates = [r[0] for r in rows]  # sample_date
        latest = max(dates)
        latest_y, latest_m = int(latest[:4]), int(latest[5:7])

        try:
            y_sel = int(self.year_var.get()) if self.year_var.get() else latest_y
        except ValueError:
            y_sel = latest_y

        try:
            m_sel = int(self.month_var.get()) if self.month_var.get() else latest_m
        except ValueError:
            m_sel = latest_m

        # Generate plots into plots_dir
        self.plot_ops.boxplot_by_month(
            rows, show=False, save=True, fname="box_latest.png"
        )
        # line_for_month saves as line_YYYY-MM.png by design; then we rename to line_latest.png
        self.plot_ops.line_for_month(rows, y_sel, m_sel, show=False, save=True)
        src_line = self.plots_dir / f"line_{y_sel}-{m_sel:02d}.png"
        dest_line = self.plots_dir / "line_latest.png"
        if src_line.exists():
            try:
                src_line.replace(dest_line)
            except Exception:
                pass

        # If user is on plots view, reload the images
        if self.view == "plots":
            self._show_plots()
        self._update_current_weather()

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------
    def open_settings(self):
        """Simple modal to edit a few config fields, then persist to config.toml."""
        win = tk.Toplevel(self)
        win.title("Settings")
        win.transient(self)
        win.grab_set()  # modal
        win.geometry("420x260")

        app = self.cfg["app"]

        tk.Label(win, text="Location:").grid(
            row=0, column=0, sticky="e", padx=8, pady=8
        )
        loc_var = tk.StringVar(value=str(app.get("location", "Winnipeg")))
        tk.Entry(win, textvariable=loc_var, width=28).grid(
            row=0, column=1, sticky="w", padx=8, pady=8
        )

        tk.Label(win, text="Station ID:").grid(
            row=1, column=0, sticky="e", padx=8, pady=8
        )
        sid_var = tk.StringVar(value=str(app.get("station_id", 27174)))
        tk.Entry(win, textvariable=sid_var, width=28).grid(
            row=1, column=1, sticky="w", padx=8, pady=8
        )

        tk.Label(win, text="Plots directory:").grid(
            row=2, column=0, sticky="e", padx=8, pady=8
        )
        pdir_var = tk.StringVar(value=str(self.plots_dir))
        ent_pdir = tk.Entry(win, textvariable=pdir_var, width=28)
        ent_pdir.grid(row=2, column=1, sticky="w", padx=8, pady=8)

        def browse_pdir():
            path = filedialog.askdirectory(title="Select plots directory")
            if path:
                pdir_var.set(path)

        ttk.Button(win, text="Browse…", command=browse_pdir).grid(
            row=2, column=2, padx=6
        )

        tk.Label(win, text="24-hour clock:").grid(
            row=3, column=0, sticky="e", padx=8, pady=8
        )
        c24_var = tk.BooleanVar(value=bool(app.get("clock_24h", True)))
        ttk.Checkbutton(win, variable=c24_var).grid(
            row=3, column=1, sticky="w", padx=8, pady=8
        )

        tk.Label(win, text="Theme:").grid(
            row=4, column=0, sticky="e", padx=8, pady=8
        )
        theme_var = tk.StringVar(value=str(app.get("theme", "dark")))
        ttk.Combobox(
            win,
            textvariable=theme_var,
            values=["dark", "light"],
            width=10,
            state="readonly",
        ).grid(row=4, column=1, sticky="w", padx=8, pady=8)

        def save_and_close():
            try:
                app["location"] = loc_var.get().strip() or "Winnipeg"
                app["station_id"] = int(sid_var.get().strip() or "27174")
                app["clock_24h"] = bool(c24_var.get())
                app["theme"] = theme_var.get().strip() or "dark"
                app["plots_dir"] = pdir_var.get().strip() or str(self.plots_dir)

                save_config(self.cfg)

                # reflect changes in running app
                self.location = app["location"]
                self.station_id = app["station_id"]
                self.clock_24h = app["clock_24h"]
                self.theme = app["theme"]
                self._apply_theme()
                self.plots_dir = Path(app["plots_dir"])
                self.plots_dir.mkdir(parents=True, exist_ok=True)
                self.plot_ops = PlotOps(out_dir=self.plots_dir)

                messagebox.showinfo(
                    "Settings", "Saved. Some changes may take effect immediately."
                )
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btns = ttk.Frame(win)
        btns.grid(row=5, column=0, columnspan=3, pady=12)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(
            side=tk.RIGHT, padx=8
        )
        ttk.Button(btns, text="Save", command=save_and_close).pack(
            side=tk.RIGHT, padx=8
        )

    # ------------------------------------------------------------------
    # Plots month selector (year + month)
    # ------------------------------------------------------------------
    def _init_month_selector(self):
        """Create year/month selectors on the bottom bar."""
        self.sel_fr = ttk.Frame(self.bottom)
        self.sel_fr.pack(side=tk.RIGHT, padx=8, pady=8)

        ttk.Label(self.sel_fr, text="Year:").pack(side=tk.LEFT, padx=(0, 4))
        self.year_var = tk.StringVar()
        self.year_cb = ttk.Combobox(
            self.sel_fr, textvariable=self.year_var, state="readonly", width=6
        )
        self.year_cb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(self.sel_fr, text="Month:").pack(side=tk.LEFT, padx=(0, 4))
        self.month_var = tk.StringVar()
        self.month_cb = ttk.Combobox(
            self.sel_fr,
            textvariable=self.month_var,
            state="readonly",
            width=4,
            values=[f"{m:02d}" for m in range(1, 13)],
        )
        self.month_cb.pack(side=tk.LEFT)

        def _on_change(_evt=None):
            self.refresh_plots(silent=True)
            if self.view == "plots":
                self._show_plots()

        self.year_cb.bind("<<ComboboxSelected>>", _on_change)
        self.month_cb.bind("<<ComboboxSelected>>", _on_change)

    def _load_available_years_and_default(self):
        """Populate year list from DB and select latest year/month as defaults."""
        try:
            db = DBOperations(location=self.location)
            rows = db.fetch_data(1900, 9999)
        except sqlite3.OperationalError as e:
            print(
                "DB not ready yet (no table). Start CLI or use Update Data to scrape data first.",
                e,
            )
            self.year_cb["values"] = []
            self.year_var.set("")
            self.month_var.set("")
            return
        except Exception as e:
            print("Unexpected DB error in _load_available_years_and_default:", e)
            self.year_cb["values"] = []
            self.year_var.set("")
            self.month_var.set("")
            return

        if not rows:
            self.year_cb["values"] = []
            self.year_var.set("")
            self.month_var.set("")
            return

        dates = [r[0] for r in rows]
        latest = max(dates)
        y_latest, m_latest = int(latest[:4]), int(latest[5:7])

        years = sorted({int(d[:4]) for d in dates}, reverse=True)
        self.year_cb["values"] = [str(y) for y in years]

        if not self.year_var.get():
            self.year_var.set(str(y_latest))
        if not self.month_var.get():
            self.month_var.set(f"{m_latest:02d}")

    # ------------------------------------------------------------------
    # Update data (scraper inside dashboard)
    # ------------------------------------------------------------------
    """Fetch new data via WeatherScraper and update DB + UI."""
    def update_data(self):
        """Seed or update the weather DB, then refresh plots."""
        try:
            # Reload config in case it changed on disk
            self.cfg = load_config()
            app_cfg = self.cfg["app"]
            self.location = app_cfg.get("location", "Winnipeg")
            self.station_id = int(app_cfg.get("station_id", 27174))

            db = DBOperations(location=self.location)
            scraper = WeatherScraper(station_id=self.station_id)

            # Check if DB already has data
            existing = db.fetch_data(1900, 9999)
            if not existing:
                # First-time seed: pick a full year so plots look good
                mode = "Seeded year 2024."
                data = scraper.scrape_range(2024, 1, 2024, 12)
            else:
                mode = "Updated last 2 months."
                data = scraper.scrape_last_months(2, start=date.today())

            added = db.save_data({k: (v.mn, v.mx, v.av) for k, v in data.items()})
            msg = f"{mode}\nInserted {added} new row(s)."
            messagebox.showinfo("Update Data", msg)

            # Refresh selectors + plots so UI reflects new data
            self._load_available_years_and_default()
            self.refresh_plots(silent=True)
            self._update_current_weather()
            if self.view != "plots":
                self.switch_view()

        except Exception as e:
            messagebox.showerror("Update failed", str(e))
            print("update_data error:", e)


def main():
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
