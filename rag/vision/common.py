"""Shared helpers for the vision component (StatsBomb open data)."""
import json
import pathlib
import time
import unicodedata
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "statsbomb"
INTERIM = ROOT / "data" / "interim"
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPETITIONS = [(43, 106, "FIFA World Cup 2022"), (55, 282, "UEFA Euro 2024"),
                (1267, 107, "Africa Cup of Nations 2023"), (223, 282, "Copa America 2024")]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ").replace("'", " ").strip()


def season_of(date: str) -> str:
    """Season label by start year, same rule as sql/03 (July to June)."""
    y, m = int(date[:4]), int(date[5:7])
    s = y if m >= 7 else y - 1
    return f"{s}/{(s + 1) % 100:02d}"


def get_json(path: str):
    """Download one StatsBomb open data file (cached in data/raw/statsbomb)."""
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / path.replace("/", "__")
    if p.exists():
        return json.loads(p.read_text())
    for _ in range(4):
        try:
            b = urllib.request.urlopen(f"{BASE}/{path}", timeout=90).read()
            p.write_bytes(b)
            return json.loads(b)
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"could not download {path}")
