from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class DueOpening:
    id: int
    name: str
    moves_san: str
    due_date: str  # YYYY-MM-DD


def _today() -> dt.date:
    return dt.date.today()


def _iso(d: dt.date) -> str:
    return d.isoformat()


def _clamp(min_v: float, v: float, max_v: float) -> float:
    return max(min_v, min(v, max_v))


def _tokenize_moves(moves_san: str) -> list[str]:
    return [t for t in moves_san.split() if t.strip()]


def ensure_cards_for_prefix(conn: sqlite3.Connection, *, prefix: str | None = None) -> int:
    """
    Ensure every opening (optionally filtered by name prefix) has a study_card row.
    Returns number of cards created.
    """
    if prefix:
        rows = conn.execute(
            "SELECT id FROM openings WHERE name LIKE ?",
            (f"{prefix}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT id FROM openings").fetchall()

    created = 0
    for r in rows:
        opening_id = int(r["id"])
        cur = conn.execute(
            "INSERT OR IGNORE INTO study_cards (opening_id) VALUES (?)",
            (opening_id,),
        )
        created += cur.rowcount
    return created


def list_due(conn: sqlite3.Connection, *, prefix: str | None = None, limit: int = 20) -> list[DueOpening]:
    sql = """
    SELECT o.id, o.name, o.moves_san, c.due_date
    FROM openings o
    JOIN study_cards c ON c.opening_id = o.id
    WHERE c.due_date <= date('now')
    """
    params: list[object] = []
    if prefix:
        sql += " AND o.name LIKE ?"
        params.append(f"{prefix}%")
    sql += " ORDER BY c.due_date ASC, o.name ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [
        DueOpening(id=r["id"], name=r["name"], moves_san=r["moves_san"], due_date=r["due_date"])
        for r in rows
    ]


def get_notes(conn: sqlite3.Connection, opening_id: int) -> str | None:
    row = conn.execute(
        "SELECT notes FROM opening_notes WHERE opening_id = ?",
        (opening_id,),
    ).fetchone()
    return None if row is None else str(row["notes"])


def set_notes(conn: sqlite3.Connection, opening_id: int, notes: str) -> None:
    conn.execute(
        """
        INSERT INTO opening_notes (opening_id, notes, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(opening_id) DO UPDATE SET
          notes = excluded.notes,
          updated_at = datetime('now')
        """,
        (opening_id, notes),
    )


def _longest_prefix_match(a: list[str], b: list[str]) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


@dataclass(frozen=True)
class QuizCheck:
    target: list[str]
    typed: list[str]
    correct_tokens: int

    @property
    def target_tokens(self) -> int:
        return len(self.target)

    @property
    def fully_correct(self) -> bool:
        return self.correct_tokens == len(self.target)


def check_typed_moves(*, moves_san: str, typed: str, tokens: int) -> QuizCheck:
    target_all = _tokenize_moves(moves_san)
    target = target_all[:tokens]
    typed_tokens = [t for t in typed.split() if t.strip()]
    correct = _longest_prefix_match(typed_tokens, target)
    return QuizCheck(target=target, typed=typed_tokens, correct_tokens=correct)


def sm2_update(*, ease: float, interval_days: int, reps: int, lapses: int, grade: int) -> tuple[float, int, int, int]:
    """
    SM-2 style update.
    grade: 0..5
    Returns: (new_ease, new_interval_days, new_reps, new_lapses)
    """
    if grade < 0 or grade > 5:
        raise ValueError("grade must be 0..5")

    # Ease update (standard SM-2 formula)
    ef = ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    ef = _clamp(1.3, ef, 3.0)

    if grade < 3:
        # Lapse: reset
        return ef, 1, 0, lapses + 1

    new_reps = reps + 1
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(interval_days * ef))

    return ef, new_interval, new_reps, lapses


def record_review(
    conn: sqlite3.Connection,
    *,
    opening_id: int,
    grade: int,
    prompt_mode: str,
    prompt: str | None,
    typed_moves: str | None,
    correct_tokens: int | None,
    target_tokens: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO study_reviews (opening_id, grade, prompt_mode, prompt, typed_moves, correct_tokens, target_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (opening_id, grade, prompt_mode, prompt, typed_moves, correct_tokens, target_tokens),
    )


def apply_grade(
    conn: sqlite3.Connection,
    *,
    opening_id: int,
    grade: int,
    prompt_mode: str,
    prompt: str | None = None,
    typed_moves: str | None = None,
    correct_tokens: int | None = None,
    target_tokens: int | None = None,
) -> None:
    row = conn.execute(
        "SELECT ease, interval_days, reps, lapses FROM study_cards WHERE opening_id = ?",
        (opening_id,),
    ).fetchone()
    if row is None:
        conn.execute("INSERT INTO study_cards (opening_id) VALUES (?)", (opening_id,))
        row = conn.execute(
            "SELECT ease, interval_days, reps, lapses FROM study_cards WHERE opening_id = ?",
            (opening_id,),
        ).fetchone()
        assert row is not None

    ease = float(row["ease"])
    interval_days = int(row["interval_days"])
    reps = int(row["reps"])
    lapses = int(row["lapses"])

    new_ease, new_interval, new_reps, new_lapses = sm2_update(
        ease=ease, interval_days=interval_days, reps=reps, lapses=lapses, grade=grade
    )
    due = _today() + dt.timedelta(days=new_interval)

    conn.execute(
        """
        UPDATE study_cards
        SET ease = ?, interval_days = ?, reps = ?, lapses = ?,
            last_grade = ?, last_reviewed_at = datetime('now'),
            due_date = ?
        WHERE opening_id = ?
        """,
        (new_ease, new_interval, new_reps, new_lapses, grade, _iso(due), opening_id),
    )

    record_review(
        conn,
        opening_id=opening_id,
        grade=grade,
        prompt_mode=prompt_mode,
        prompt=prompt,
        typed_moves=typed_moves,
        correct_tokens=correct_tokens,
        target_tokens=target_tokens,
    )


def pick_quiz_openings(
    conn: sqlite3.Connection, *, prefix: str | None, limit: int
) -> list[DueOpening]:
    """
    Prefer due cards; if none are due, return the soonest upcoming ones.
    """
    due = list_due(conn, prefix=prefix, limit=limit)
    if due:
        return due

    sql = """
    SELECT o.id, o.name, o.moves_san, c.due_date
    FROM openings o
    JOIN study_cards c ON c.opening_id = o.id
    """
    params: list[object] = []
    if prefix:
        sql += " WHERE o.name LIKE ?"
        params.append(f"{prefix}%")
    sql += " ORDER BY c.due_date ASC, o.name ASC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [
        DueOpening(id=r["id"], name=r["name"], moves_san=r["moves_san"], due_date=r["due_date"])
        for r in rows
    ]

