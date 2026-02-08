"""Simple web server for browsing chess openings."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from chess_db.config import get_settings
from chess_db.db import Db, init_db
from chess_db.evals import latest_evaluation
from chess_db.study import get_notes, pick_quiz_openings


def _db() -> Db:
    settings = get_settings()
    return Db(settings.db_path)


app = FastAPI(title="Chess DB", description="Browse your chess openings")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (STATIC_DIR / "index.html").read_text()
    return HTMLResponse(html)


@app.get("/api/openings")
async def api_openings(prefix: str | None = None, limit: int = 200) -> list[dict]:
    """List openings, optionally filtered by name prefix."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        if prefix:
            rows = conn.execute(
                "SELECT id, name, moves_san FROM openings WHERE name LIKE ? ORDER BY name ASC LIMIT ?",
                (f"{prefix}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, moves_san FROM openings ORDER BY name ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "moves_san": r["moves_san"]}
            for r in rows
        ]


@app.get("/api/openings/{opening_id:int}")
async def api_opening(opening_id: int) -> dict | None:
    """Get a single opening with notes and latest evaluation."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, name, moves_san FROM openings WHERE id = ?", (opening_id,)
        ).fetchone()
        if row is None:
            return None
        notes = get_notes(conn, opening_id)
        eval_ = latest_evaluation(conn, opening_id)
    return {
        "id": row["id"],
        "name": row["name"],
        "moves_san": row["moves_san"],
        "notes": notes or "",
        "eval": (
            {
                "depth": eval_.depth,
                "score_cp": eval_.score_cp,
                "mate_in": eval_.mate_in,
                "bestmove_uci": eval_.bestmove_uci,
            }
            if eval_
            else None
        ),
    }


@app.get("/api/due")
async def api_due(prefix: str | None = None, limit: int = 20) -> list[dict]:
    """List openings due for review today."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        due = pick_quiz_openings(conn, prefix=prefix or "", limit=limit)
        return [
            {"id": d.id, "name": d.name, "moves_san": d.moves_san, "due_date": d.due_date}
            for d in due
        ]


def main() -> None:
    uvicorn.run(
        "web.server:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    main()
