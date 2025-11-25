from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import calendar, datetime as dt

from .config import load_config, save_config
from .db_operations import DBOperations
from .plot_operations import PlotOps

# Pillow to display PNG plots
try:
    from PIL import Image, ImageTk
except Exception as e:
    raise RuntimeError("Install Pillow: pip install pillow") from e

class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J-Display")
        self.geometry("1280x800")
        self.resizable(True, True)

        self.cfg = load_config()
        self.theme = self.cfg["app"]["theme"]
        self.clock_24h = bool(self.cfg["app"]["clock_24h"])
        self.plots_dir = Path(self.cfg["app"]["plots_dir"])
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        # theme
        self._apply_theme()

        # layout
        self.top = ttk.Frame(self)
        self.top.pack(side=tk.TOP, fill=tk.X)

        self.main = ttk.Frame(self)
        self.main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.bottom = ttk.Frame(self)
        self.bottom.pack(side=tk.BOTTOM, fill=tk.X)

        # top bar: clock + theme toggle + settings
        self.clock_lbl = ttk.Label(self.top, font=("Segoe UI", 18, "bold"))
        self.clock_lbl.pack(side=tk.LEFT, padx=10, pady=8)

        ttk.Button(self.top, text="Theme", command=self.toggle_theme).pack(side=tk.RIGHT, padx=8)
        ttk.Button(self.top, text="Settings", command=self.open_settings).pack(side=tk.RIGHT, padx=8)

        # main area: two views
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

        # bottom bar: switch + refresh
        ttk.Button(self.bottom, text="Switch View", command=self.switch_view).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(self.bottom, text="Refresh Plots", command=self.refresh_plots).pack(side=tk.LEFT, padx=8, pady=8)

        # start on calendar
        self._show_calendar()

        # clock updater
        self.after(200, self._tick)

    # --- theme ---
    def _apply_theme(self):
        bg = "#0f172a" if self.theme == "dark" else "#f3f4f6"
        fg = "#e5e7eb" if self.theme == "dark" else "#111827"
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
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

    # --- clock ---
    def _tick(self):
        now = dt.datetime.now()
        if self.clock_24h:
            s = now.strftime("%Y-%m-%d  %H:%M:%S")
        else:
            s = now.strftime("%Y-%m-%d  %I:%M:%S %p")
        self.clock_lbl.config(text=s)
        self.after(1000, self._tick)

    # --- calendar view ---
    def _build_calendar(self):
        # simple month grid
        for w in self.calendar_fr.winfo_children():
            w.destroy()
        today = dt.date.today()
        year, month = today.year, today.month

        header = ttk.Label(self.calendar_fr, text=f"{calendar.month_name[month]} {year}", font=("Segoe UI", 20, "bold"))
        header.pack(pady=10)

        grid = ttk.Frame(self.calendar_fr)
        grid.pack(expand=True)

        days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        for i, d in enumerate(days):
            ttk.Label(grid, text=d, font=("Segoe UI", 12, "bold")).grid(row=0, column=i, padx=6, pady=6, sticky="nsew")

        cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        for r, week in enumerate(cal, start=1):
            for c, day in enumerate(week):
                txt = "" if day == 0 else str(day)
                ttk.Label(grid, text=txt, font=("Segoe UI", 12)).grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

    # --- plots view ---
    def _load_img_or_text(self, label: ttk.Label, path: Path, fallback: str):
        for child in label.winfo_children():
            child.destroy()
        if path.exists():
            img = Image.open(path)
            # preserve aspect, fit height
            img.thumbnail((600, 600))
            label.img = ImageTk.PhotoImage(img)  # keep ref
            label.config(image=label.img, text="")
        else:
            label.config(image="", text=fallback)

    def _show_plots(self):
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

    # --- refresh plots: generate stable PNGs then reload
    def refresh_plots(self):
        try:
            db = DBOperations()
            rows = db.fetch_data(1900, 9999)
            if not rows:
                messagebox.showwarning("No data", "Database is empty. Use CLI to scrape first.")
                return

            # Save box: use all rows (group by month)
            PlotOps(self.plots_dir).boxplot_by_month(rows, show=False, save=True, fname="box_latest.png")

            # Save line: use latest month present
            latest = max(r[0] for r in rows)  # sample_date
            y, m = int(latest[:4]), int(latest[5:7])
            PlotOps(self.plots_dir).line_for_month(rows, y, m, show=False, save=True)
            # rename to stable name
            src = self.plots_dir / f"line_{y}-{m:02d}.png"
            dst = self.plots_dir / "line_latest.png"
            if src.exists():
                dst.write_bytes(src.read_bytes())

            messagebox.showinfo("Plots", f"Updated plots in {self.plots_dir}")
            if self.view == "plots":
                self._show_plots()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_settings(self):
            """Simple modal to edit a few config fields, then persist to config.toml."""
            win = tk.Toplevel(self)
            win.title("Settings")
            win.transient(self)
            win.grab_set()  # modal
            win.geometry("420x260")

            app = self.cfg["app"]

            # fields
            tk.Label(win, text="Location:").grid(row=0, column=0, sticky="e", padx=8, pady=8)
            loc_var = tk.StringVar(value=str(app.get("location", "Winnipeg")))
            tk.Entry(win, textvariable=loc_var, width=28).grid(row=0, column=1, sticky="w", padx=8, pady=8)

            tk.Label(win, text="Station ID:").grid(row=1, column=0, sticky="e", padx=8, pady=8)
            sid_var = tk.StringVar(value=str(app.get("station_id", 27174)))
            tk.Entry(win, textvariable=sid_var, width=28).grid(row=1, column=1, sticky="w", padx=8, pady=8)

            tk.Label(win, text="Plots directory:").grid(row=2, column=0, sticky="e", padx=8, pady=8)
            pdir_var = tk.StringVar(value=str(self.plots_dir))
            ent_pdir = tk.Entry(win, textvariable=pdir_var, width=28)
            ent_pdir.grid(row=2, column=1, sticky="w", padx=8, pady=8)

            def browse_pdir():
                path = filedialog.askdirectory(title="Select plots directory")
                if path:
                    pdir_var.set(path)
            ttk.Button(win, text="Browse…", command=browse_pdir).grid(row=2, column=2, padx=6)

            tk.Label(win, text="24-hour clock:").grid(row=3, column=0, sticky="e", padx=8, pady=8)
            c24_var = tk.BooleanVar(value=bool(app.get("clock_24h", True)))
            ttk.Checkbutton(win, variable=c24_var).grid(row=3, column=1, sticky="w", padx=8, pady=8)

            tk.Label(win, text="Theme:").grid(row=4, column=0, sticky="e", padx=8, pady=8)
            theme_var = tk.StringVar(value=str(app.get("theme", "dark")))
            ttk.Combobox(win, textvariable=theme_var, values=["dark", "light"], width=10, state="readonly").grid(row=4, column=1, sticky="w", padx=8, pady=8)

            def save_and_close():
                # persist to config + apply in-app
                try:
                    app["location"] = loc_var.get().strip() or "Winnipeg"
                    app["station_id"] = int(sid_var.get().strip() or "27174")
                    app["clock_24h"] = bool(c24_var.get())
                    app["theme"] = theme_var.get().strip() or "dark"
                    app["plots_dir"] = pdir_var.get().strip() or str(self.plots_dir)

                    save_config(self.cfg)

                    # reflect changes in running app
                    self.clock_24h = app["clock_24h"]
                    self.theme = app["theme"]
                    self._apply_theme()
                    self.plots_dir = Path(app["plots_dir"])
                    self.plots_dir.mkdir(parents=True, exist_ok=True)
                    messagebox.showinfo("Settings", "Saved. Some changes may take effect immediately.")
                    win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            btns = ttk.Frame(win)
            btns.grid(row=5, column=0, columnspan=3, pady=12)
            ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=8)
            ttk.Button(btns, text="Save", command=save_and_close).pack(side=tk.RIGHT, padx=8)

def main():
    app = Dashboard()
    app.mainloop()

if __name__ == "__main__":
    main()
