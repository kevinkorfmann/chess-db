#!/usr/bin/env python3
"""
Generate Scotch Game lines by playing many random Stockfish games.

Same strategy as generate_italian_lines.py — see GENERATION_STRATEGY.md.
Start: 1. e4 e5 2. Nf3 Nc6 3. d4
"""

from __future__ import annotations

import chess
import chess.engine
import json
import random
import sys

STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
DEPTH = 10
NUM_GAMES = 300
TARGET_PLY = 20
TOP_N = 4

random.seed(42)

# Scotch Game branches: after 1.e4 e5 2.Nf3 Nc6 3.d4
STARTS = [
    # 3...exd4 (main)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4"],
    # 3...exd4 4.Nxd4 Bc5 (Classical)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4", "f8c5"],
    # 3...exd4 4.Nxd4 Nf6 (Schmidt)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4", "g8f6"],
    # 3...exd4 4.Nxd4 Qf6 (rare but tricky)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "f3d4", "d8f6"],
    # 3...d6 (Steinitz-like)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "d7d6"],
    # 3...Nf6 (counter-attack)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "g8f6"],
    # 3...d5 (Scotch Gambit decline)
    ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "d7d5"],
]

START_WEIGHTS = [30, 20, 15, 10, 10, 10, 5]

BRANCH_NAMES = {
    "exd4": "Scotch Main",
    "Bc5": "Scotch Classical",
    "Nf6": "Scotch Schmidt",
    "Qf6": "Scotch Queen",
    "d6": "Scotch Steinitz",
    "d5": "Scotch Counter",
}


def play_one_game(engine: chess.engine.SimpleEngine) -> list[str] | None:
    start = random.choices(STARTS, weights=START_WEIGHTS, k=1)[0]
    board = chess.Board()
    moves_uci: list[str] = []

    for uci in start:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            return None
        board.push(move)
        moves_uci.append(uci)

    while len(moves_uci) < TARGET_PLY and not board.is_game_over():
        try:
            results = engine.analyse(
                board,
                chess.engine.Limit(depth=DEPTH),
                multipv=min(TOP_N, len(list(board.legal_moves))),
            )
        except Exception:
            break

        if not results:
            break

        candidates = []
        for r in results:
            if "pv" in r and r["pv"]:
                candidates.append(r["pv"][0])

        if not candidates:
            break

        weights = [2 ** (len(candidates) - i - 1) for i in range(len(candidates))]
        move = random.choices(candidates, weights=weights, k=1)[0]
        moves_uci.append(move.uci())
        board.push(move)

    return moves_uci if len(moves_uci) >= 10 else None


def uci_to_san(moves_uci: list[str]) -> str:
    board = chess.Board()
    parts = []
    for uci in moves_uci:
        move = chess.Move.from_uci(uci)
        if board.turn == chess.WHITE:
            parts.append(f"{board.fullmove_number}. {board.san(move)}")
        else:
            parts.append(board.san(move))
        board.push(move)
    return " ".join(parts)


def evaluate_line(engine: chess.engine.SimpleEngine, moves_uci: list[str]) -> int:
    board = chess.Board()
    for uci in moves_uci:
        board.push(chess.Move.from_uci(uci))
    info = engine.analyse(board, chess.engine.Limit(depth=DEPTH))
    score = info["score"].white()
    return score.score(mate_score=10000) or 0


def detect_branch(pgn: str) -> str:
    """Detect Scotch branch from PGN moves."""
    tokens = pgn.split()
    # tokens: 1. e4 e5 2. Nf3 Nc6 3. d4 <Black's 3rd>
    # indices: 0  1   2  3   4    5  6   7   8
    if len(tokens) < 9:
        return "Scotch"

    black_3 = tokens[8]  # Black's reply to 3.d4

    if black_3 == "exd4":
        # Check what happens after 4.Nxd4
        # tokens: ... 3. d4 exd4 4. Nxd4 <Black's 4th>
        if len(tokens) >= 14:
            black_4 = tokens[13]
            if black_4 == "Bc5":
                return "Scotch Classical"
            elif black_4 == "Nf6":
                return "Scotch Schmidt"
            elif black_4 == "Qf6":
                return "Scotch Queen"
            elif black_4 == "Qh4":
                return "Scotch Queen"
        return "Scotch Main"
    elif black_3 == "d6":
        return "Scotch Steinitz"
    elif black_3 == "Nf6":
        return "Scotch Counter"
    elif black_3 == "d5":
        return "Scotch Counter"
    else:
        return "Scotch"


def main() -> None:
    print(f"Playing {NUM_GAMES} random Scotch games (depth={DEPTH}, ply={TARGET_PLY})...", file=sys.stderr)

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    engine.configure({"Threads": 4, "Hash": 128})

    all_games: list[list[str]] = []
    for i in range(NUM_GAMES):
        if (i + 1) % 50 == 0:
            print(f"  Game {i + 1}/{NUM_GAMES}...", file=sys.stderr)
        result = play_one_game(engine)
        if result:
            all_games.append(result)

    print(f"  Played {len(all_games)} valid games", file=sys.stderr)

    seen: set[str] = set()
    unique: list[list[str]] = []
    for game in all_games:
        key = " ".join(game)
        if key not in seen:
            seen.add(key)
            unique.append(game)

    print(f"  {len(unique)} unique lines after dedup", file=sys.stderr)

    print("  Evaluating lines...", file=sys.stderr)
    evals: list[int] = []
    for game in unique:
        cp = evaluate_line(engine, game)
        evals.append(cp)

    engine.quit()

    # Sort by similarity
    indexed = list(zip(unique, evals))
    indexed.sort(key=lambda x: tuple(x[0]))

    # Convert to SAN, detect branch, tag eval
    named: list[tuple[str, str]] = []
    for i, (game, cp) in enumerate(indexed, 1):
        san = uci_to_san(game)
        branch = detect_branch(san)

        if cp > 300:
            tag = "Winning"
        elif cp > 150:
            tag = "Clear Edge"
        elif cp > 50:
            tag = "Slight Edge"
        elif cp > -50:
            tag = "Equal"
        elif cp > -150:
            tag = "Tough"
        else:
            tag = "Difficult"

        name = f"Scotch #{i:03d} - {branch} {tag}"
        named.append((name, san))

    print(json.dumps(named, indent=2))

    # Stats
    branches: dict[str, int] = {}
    for name, _ in named:
        b = name.split(" - ")[1].rsplit(" ", 1)[0] if " - " in name else "?"
        # handle two-word eval tags
        for t in ["Slight Edge", "Clear Edge"]:
            if name.endswith(t):
                b = name.split(" - ")[1][:-len(t)].strip()
                break
        branches[b] = branches.get(b, 0) + 1

    print(f"\nDone: {len(named)} lines", file=sys.stderr)
    print("By branch:", file=sys.stderr)
    for k, v in sorted(branches.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()
