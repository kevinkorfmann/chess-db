from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class Opening:
    id: int
    name: str
    moves_san: str


def _parse_moves_san(moves_san: str) -> list[str]:
    moves = [m.strip() for m in moves_san.split() if m.strip()]
    if not moves:
        raise ValueError("No moves provided.")
    return moves


def opening_final_board(moves_san: str) -> chess.Board:
    board = chess.Board()
    for token in _parse_moves_san(moves_san):
        try:
            move = board.parse_san(token)
        except ValueError as e:
            raise ValueError(f"Invalid SAN move '{token}' at ply {board.ply() + 1}.") from e
        board.push(move)
    return board


def add_opening(conn: sqlite3.Connection, name: str, moves_san: str) -> Opening:
    # Validate moves early so we don't store garbage.
    opening_final_board(moves_san)

    cur = conn.execute(
        "INSERT INTO openings (name, moves_san) VALUES (?, ?) RETURNING id, name, moves_san",
        (name, moves_san.strip()),
    )
    row = cur.fetchone()
    assert row is not None
    return Opening(id=row["id"], name=row["name"], moves_san=row["moves_san"])


def get_opening_by_name(conn: sqlite3.Connection, name: str) -> Opening | None:
    cur = conn.execute("SELECT id, name, moves_san FROM openings WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is None:
        return None
    return Opening(id=row["id"], name=row["name"], moves_san=row["moves_san"])


def list_openings(conn: sqlite3.Connection) -> list[Opening]:
    cur = conn.execute("SELECT id, name, moves_san FROM openings ORDER BY name ASC")
    rows = cur.fetchall()
    return [Opening(id=r["id"], name=r["name"], moves_san=r["moves_san"]) for r in rows]
