from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    stockfish_path: str | None


def get_settings() -> Settings:
    db_path = Path(os.environ.get("CHESS_DB_PATH", "data/chess_db.sqlite3"))
    stockfish_path = os.environ.get("STOCKFISH_PATH")
    return Settings(db_path=db_path, stockfish_path=stockfish_path)
