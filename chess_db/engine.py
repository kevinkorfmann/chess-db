from __future__ import annotations

import shutil
from dataclasses import dataclass

import chess
import chess.engine


@dataclass(frozen=True)
class EvalResult:
    depth: int
    score_cp: int | None
    mate_in: int | None
    bestmove_uci: str | None
    pv_uci: str | None


def resolve_stockfish_path(explicit_path: str | None) -> str:
    if explicit_path:
        return explicit_path
    found = shutil.which("stockfish")
    if not found:
        raise FileNotFoundError(
            "Stockfish binary not found on PATH. Install it (e.g. `brew install stockfish`) "
            "or set STOCKFISH_PATH."
        )
    return found


def evaluate_position(board: chess.Board, *, depth: int, stockfish_path: str) -> EvalResult:
    # One PV at fixed depth.
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)
        if isinstance(info, list):
            info = info[0] if info else {}
        score = info.get("score")
        pv = info.get("pv")
        bestmove = info.get("bestmove")

    score_cp: int | None = None
    mate_in: int | None = None
    if score is not None:
        pov = score.pov(board.turn)
        mate_in = pov.mate()
        if mate_in is None:
            score_cp = pov.score(mate_score=100000)

    pv_uci = " ".join(m.uci() for m in pv) if pv else None
    bestmove_uci = bestmove.uci() if bestmove else None

    return EvalResult(
        depth=depth,
        score_cp=score_cp,
        mate_in=mate_in,
        bestmove_uci=bestmove_uci,
        pv_uci=pv_uci,
    )
