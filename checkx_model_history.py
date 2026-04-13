"""Historique persistant des puzzles Check X générés."""
import os
import json
import hashlib
import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "checkx_history.json"


def _flat_values(values):
    return "".join(str(cell) if cell not in (None, 0) else "_" for row in values for cell in row)


def _flat_blacks(blacks):
    return "".join("1" if b else "0" for row in blacks for b in row)


def puzzle_hash(solution, blacks):
    s = _flat_values(solution) + "|" + _flat_blacks(blacks)
    return hashlib.sha256(s.encode()).hexdigest()


def get_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def is_unique(solution, blacks):
    return puzzle_hash(solution, blacks) not in get_history()


def add_to_history(solution, blacks, metadata=None):
    h = get_history()
    h[puzzle_hash(solution, blacks)] = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": metadata or {},
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(h, f, indent=2)
