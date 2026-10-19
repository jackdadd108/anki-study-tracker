#!/usr/bin/env python3
"""Start a fresh checkout without overwriting existing local study data."""
import json
import runpy
from pathlib import Path

root = Path(__file__).resolve().parent
try:
    with (root / "data.json").open("x") as handle:
        json.dump({"decks": [], "cards": [], "attempts": [], "daily_completions": []}, handle)
except FileExistsError:
    pass
(root / "static" / "media").mkdir(exist_ok=True)
runpy.run_path(str(root / "server.py"), run_name="__main__")
