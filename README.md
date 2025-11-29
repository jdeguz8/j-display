# J-Display

J-Display is a Python-based weather dashboard designed as a capstone project for **ADEV-3005 – Programming in Python**.  

It:

- Scrapes **daily temperature data** from Environment Canada (Winnipeg station by default)
- Stores it in a local **SQLite** database
- Generates **boxplots** and **line plots** using Matplotlib
- Displays a desktop **dashboard UI** (Tkinter) with:
  - Digital clock (12/24h)
  - Calendar view
  - Current / latest weather summary
  - Plot view (monthly line chart + yearly boxplot)
  - Dark / light theme toggle
  - Settings overlay (location, station ID, plots directory, etc.)

The goal is to simulate a **smart display / smart mirror** running on a 15" portable USB-C monitor or Raspberry Pi setup.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Data Source](#data-source)
- [Installation](#installation)
- [Usage](#usage)
  - [1. CLI Scraper (Milestone 1)](#1-cli-scraper-milestone-1)
  - [2. Plotting / Menu (Milestone 2)](#2-plotting--menu-milestone-2)
  - [3. Dashboard UI (Milestone 3)](#3-dashboard-ui-milestone-3)
- [Configuration](#configuration)
- [Database Schema](#database-schema)
- [Packaging / Executable](#packaging--executable)
- [Error Handling, Logging & Code Quality](#error-handling-logging--code-quality)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Features

### Weather Data

- Scrapes daily **min / max / mean temperature** for Winnipeg (or another station)
- Uses Environment Canada’s **CSV bulk endpoint** (same as the “Download Data” button)
- Handles missing values (`NA`) and converts them to `None`
- Stores data in a **normalized SQLite table** with unique `(sample_date, location)` rows

### Plots

- **Boxplot**:
  - Distribution of daily mean temperatures grouped by month (1–12)
- **Line plot**:
  - Daily mean temperatures for a selected year + month
- Plots are saved as PNGs into a configurable `plots` directory

### Dashboard

- Tkinter GUI (designed for a 1280×800 15" display)
- Views:
  - **Calendar view**
    - Month grid
    - Header showing current date + latest weather summary:
      - `Today: 1.2°C avg, 3.0° high, -1.0° low`
      - Or fallback to the most recent date with data
  - **Plots view**
    - Left: boxplot (`box_latest.png`)
    - Right: line plot for selected year/month (`line_latest.png`)
- Controls:
  - Dark / light theme toggle
  - Settings dialog:
    - Location label (for DB)
    - Station ID (Environment Canada station)
    - Plots directory
    - 12/24h clock
    - Theme preference
  - Bottom bar:
    - Switch View (Calendar ↔ Plots)
    - Refresh Plots
    - Update Data (scrapes + writes to DB)
    - Year / month selector for line plot

---

## Project Structure

```
j-display/
├─ jdisplay/
│  ├─ __init__.py
│  ├─ cli.py                # CLI menu for scraping / DB seeding (Milestone 1)
│  ├─ weather_processor.py  # CLI menu for plotting (Milestone 2)
│  ├─ dashboard.py          # Tkinter dashboard UI (Milestone 3)
│  ├─ scrape_weather.py     # WeatherScraper: fetches CSV from Environment Canada
│  ├─ dbcm.py               # DBCM: SQLite context manager
│  ├─ db_operations.py      # DBOperations: handles schema + inserts + queries
│  ├─ plot_operations.py    # PlotOps: Matplotlib plotting helpers
│  ├─ config.py             # Load/save config.toml
│  ├─ logging_conf.py       # Logging configuration
│  └─ html_probe.py         # Small HTML probe helper (optional / debug)
├─ config.toml              # App configuration file
├─ LICENSE.txt
├─ J-Display.spec           # PyInstaller spec file (for building EXE)
├─ run_dashboard.py         # Thin wrapper script for PyInstaller entrypoint
└─ README.md                # This file
``` 
> **Note**  
> The SQLite database is stored in a user-local directory, e.g. on Windows:  
> `C:\Users\<user>\AppData\Local\J-Display\weather.sqlite3`

---

## Data Source

**Environment Canada – Historical climate data**

- Data is fetched via the bulk CSV endpoint:  
  `https://climate.weather.gc.ca/climate_data/bulk_data_e.html`
- Configurable via **Station ID**:
  - Default: `27174` (Winnipeg)
- The project is **read-only** with respect to Environment Canada (no data is pushed back).

---

## Installation

### Requirements

- **Python 3.12+** (project was developed and tested with Python 3.12 / 3.13)
- **OS**: Windows (tested)
- **Libraries**:
  - `matplotlib`
  - `pillow`
  - `pylint` (optional, for style checks)
  - Standard library modules only otherwise

### Steps

#### 1. Clone the repository

```
git clone https://github.com/<your-username>/j-display.git
cd j-display
```

### 2. Create and activate a virtual environment
```
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# If execution policy blocks it, start a virtualenv-friendly shell or temporarily adjust policy.
```

### 3. Install dependencies
```
pip install matplotlib pillow pylint
```
## Future Enhancements

Some ideas for future versions of J-Display:

-  Multi-city / multi-station support (user can switch between locations)
-  Additional metrics (precipitation, wind, etc.)
-  Raspberry Pi deployment:
-  Auto-start dashboard on boot
-  Integrate physical buttons to switch views or update data
-  More UI widgets:
-  Weekly forecast panel
-  Weather alerts banner
-  Integration with an online calendar or task list.

