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

-- Optional training data: free-form notes per opening
CREATE TABLE IF NOT EXISTS opening_notes (
  opening_id INTEGER PRIMARY KEY,
  notes TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(opening_id) REFERENCES openings(id) ON DELETE CASCADE
);

-- Spaced repetition card state (one row per opening)
CREATE TABLE IF NOT EXISTS study_cards (
  opening_id INTEGER PRIMARY KEY,
  ease REAL NOT NULL DEFAULT 2.5,          -- SM-2 ease factor
  interval_days INTEGER NOT NULL DEFAULT 0,
  due_date TEXT NOT NULL DEFAULT (date('now')), -- YYYY-MM-DD
  reps INTEGER NOT NULL DEFAULT 0,
  lapses INTEGER NOT NULL DEFAULT 0,
  last_grade INTEGER,
  last_reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(opening_id) REFERENCES openings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_study_cards_due_date ON study_cards(due_date);

-- Review log (optional, for progress tracking)
CREATE TABLE IF NOT EXISTS study_reviews (
  id INTEGER PRIMARY KEY,
  opening_id INTEGER NOT NULL,
  reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
  grade INTEGER NOT NULL,                 -- 0..5
  prompt_mode TEXT NOT NULL,              -- e.g. 'name_to_moves'
  prompt TEXT,
  typed_moves TEXT,
  correct_tokens INTEGER,
  target_tokens INTEGER,
  FOREIGN KEY(opening_id) REFERENCES openings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_study_reviews_opening_id ON study_reviews(opening_id);
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
