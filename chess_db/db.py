from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS openings (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  moves_san TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evaluations (
  id INTEGER PRIMARY KEY,
  opening_id INTEGER NOT NULL,
  depth INTEGER NOT NULL,
  multipv INTEGER NOT NULL DEFAULT 1,
  score_cp INTEGER,
  mate_in INTEGER,
  bestmove_uci TEXT,
  pv_uci TEXT,
  analyzed_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(opening_id) REFERENCES openings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evaluations_opening_id ON evaluations(opening_id);
"""


@dataclass(frozen=True)
class Db:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


def init_db(db: Db) -> None:
    with db.connect() as conn:
        conn.executescript(SCHEMA)
