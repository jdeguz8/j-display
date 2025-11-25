# jdisplay/config.py
from __future__ import annotations
from pathlib import Path
import datetime as _dt

# Use TOML for human-friendly config.
# Python 3.11+ has tomllib for reading. We'll write TOML ourselves (tiny).
try:
    import tomllib  # py311+
except ModuleNotFoundError:  # py310 fallback if ever needed
    tomllib = None

APP_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = APP_ROOT / "config.toml"

DEFAULT = {
    "app": {
        "location": "Winnipeg",
        "station_id": 27174,
        "clock_24h": True,
        "theme": "dark",  # "dark" | "light"
        "plots_dir": str((APP_ROOT / "plots").as_posix()),
        "refresh_minutes": 60,
    }
}

def _to_toml(d: dict, indent: int = 0) -> str:
    lines: list[str] = []
    for k, v in d.items():
        if isinstance(v, dict):
            if indent == 0:
                lines.append(f"[{k}]")
            else:
                lines.append(f"[{'.'.join(['app'])}]")  # flat one section for simplicity
            for kk, vv in v.items():
                if isinstance(vv, bool):
                    val = "true" if vv else "false"
                elif isinstance(vv, (int, float)):
                    val = str(vv)
                else:
                    s = str(vv).replace("\\", "/")
                    val = f"\"{s}\""
                lines.append(f"{kk} = {val}")
        else:
            # not expected in this tiny schema
            pass
    return "\n".join(lines) + "\n"

def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(_to_toml(cfg), encoding="utf-8")

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT)
        return DEFAULT.copy()
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if tomllib:
        data = tomllib.loads(text)
    else:
        # extremely small/naive reader for our keys if tomllib is unavailable
        data = DEFAULT.copy()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if "=" in line:
                k, v = [p.strip() for p in line.split("=", 1)]
                if v.lower() in ("true", "false"):
                    vv = v.lower() == "true"
                elif v.isdigit():
                    vv = int(v)
                elif v.replace(".", "", 1).isdigit():
                    vv = float(v)
                else:
                    vv = v.strip("\"'")
                data["app"][k] = vv
    # ensure required keys exist
    merged = DEFAULT.copy()
    merged["app"].update(data.get("app", {}))
    return merged
