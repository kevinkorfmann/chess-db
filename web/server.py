"""Simple web server for browsing chess openings."""

from __future__ import annotations

from pathlib import Path

import chess
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chess_db.config import get_settings
from chess_db.db import Db, init_db
from chess_db.engine import evaluate_position, resolve_stockfish_path
from chess_db.evals import latest_evaluation
from chess_db.study import get_notes, pick_quiz_openings


class EvalRequest(BaseModel):
    fen: str


class EvalResponse(BaseModel):
    score_cp: int | None
    mate_in: int | None
    depth: int


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
async def api_openings(
    prefix: str | None = None,
    q: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """List openings, optionally filtered by name prefix or substring query."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        if q:
            rows = conn.execute(
                "SELECT id, name, moves_san FROM openings WHERE name LIKE ? ORDER BY name ASC LIMIT ?",
                (f"%{q}%", limit),
            ).fetchall()
        elif prefix:
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


@app.get("/api/health")
async def api_health() -> dict:
    """Health check; verifies API is reachable."""
    return {"status": "ok"}


@app.post("/api/eval", response_model=EvalResponse | None)
async def api_eval(req: EvalRequest, depth: int = 10) -> EvalResponse | None:
    """Evaluate a position with Stockfish. Returns None if Stockfish is not available."""
    try:
        settings = get_settings()
        stockfish_path = resolve_stockfish_path(settings.stockfish_path)
    except FileNotFoundError:
        return None
    try:
        board = chess.Board(req.fen)
    except ValueError:
        return None
    try:
        result = evaluate_position(board, depth=depth, stockfish_path=stockfish_path)
    except Exception:
        return None
    return EvalResponse(
        score_cp=result.score_cp,
        mate_in=result.mate_in,
        depth=result.depth,
    )


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
