from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .engine import EvalResult


@dataclass(frozen=True)
class StoredEval:
    id: int
    opening_id: int
    depth: int
    score_cp: int | None
    mate_in: int | None
    bestmove_uci: str | None
    pv_uci: str | None


def store_evaluation(conn: sqlite3.Connection, opening_id: int, result: EvalResult) -> StoredEval:
    cur = conn.execute(
        """
        INSERT INTO evaluations (opening_id, depth, multipv, score_cp, mate_in, bestmove_uci, pv_uci)
        VALUES (?, ?, 1, ?, ?, ?, ?)
        RETURNING id, opening_id, depth, score_cp, mate_in, bestmove_uci, pv_uci
        """,
        (
            opening_id,
            result.depth,
            result.score_cp,
            result.mate_in,
            result.bestmove_uci,
            result.pv_uci,
        ),
    )
    row = cur.fetchone()
    assert row is not None
    return StoredEval(
        id=row["id"],
        opening_id=row["opening_id"],
        depth=row["depth"],
        score_cp=row["score_cp"],
        mate_in=row["mate_in"],
        bestmove_uci=row["bestmove_uci"],
        pv_uci=row["pv_uci"],
    )


def latest_evaluation(conn: sqlite3.Connection, opening_id: int) -> StoredEval | None:
    cur = conn.execute(
        """
        SELECT id, opening_id, depth, score_cp, mate_in, bestmove_uci, pv_uci
        FROM evaluations
        WHERE opening_id = ?
        ORDER BY analyzed_at DESC, id DESC
        LIMIT 1
        """,
        (opening_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return StoredEval(
        id=row["id"],
        opening_id=row["opening_id"],
        depth=row["depth"],
        score_cp=row["score_cp"],
        mate_in=row["mate_in"],
        bestmove_uci=row["bestmove_uci"],
        pv_uci=row["pv_uci"],
    )
