#!/usr/bin/env python3
"""
Generate Italian Game lines by playing many random Stockfish games.

Strategy:
1. Start from 1.e4 e5 2.Nf3 Nc6 3.Bc4 + a random Black reply
2. Each move: pick randomly from the top-N Stockfish moves (weighted by rank)
3. Play until target depth
4. Collect all games, deduplicate, sort by move similarity
5. Output as add_italian.py
"""

from __future__ import annotations

import chess
import chess.engine
import json
import random
import sys

STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
DEPTH = 10          # Stockfish search depth (fast)
NUM_GAMES = 300     # number of random games to play
TARGET_PLY = 20     # play each game to ~10 full moves
TOP_N = 4           # pick from top-N moves each turn

random.seed(42)

# Italian Game branches: after 1.e4 e5 2.Nf3 Nc6 3.Bc4
STARTS = [
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"],  # Giuoco Piano
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"],  # Two Knights
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8e7"],  # Hungarian
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "d7d6"],  # Semi-Italian
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "h7h6"],  # Anti-Italian
]

# Weights: prefer the main lines (Giuoco Piano & Two Knights)
START_WEIGHTS = [40, 35, 10, 10, 5]


def play_one_game(engine: chess.engine.SimpleEngine) -> list[str] | None:
    """Play one random game from a random Italian start, return UCI moves."""
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

        # Collect candidate moves
        candidates = []
        for r in results:
            if "pv" in r and r["pv"]:
                candidates.append(r["pv"][0])

        if not candidates:
            break

        # Weighted random: strongly prefer top moves
        # weights: [8, 4, 2, 1] for rank 1,2,3,4
        weights = [2 ** (len(candidates) - i - 1) for i in range(len(candidates))]
        move = random.choices(candidates, weights=weights, k=1)[0]

        moves_uci.append(move.uci())
        board.push(move)

    if len(moves_uci) < 10:
        return None

    return moves_uci


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
    """Get eval in centipawns at the end of the line."""
    board = chess.Board()
    for uci in moves_uci:
        board.push(chess.Move.from_uci(uci))
    info = engine.analyse(board, chess.engine.Limit(depth=DEPTH))
    score = info["score"].white()
    return score.score(mate_score=10000) or 0


def main() -> None:
    print(f"Playing {NUM_GAMES} random Italian games (depth={DEPTH}, ply={TARGET_PLY})...", file=sys.stderr)

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    engine.configure({"Threads": 4, "Hash": 128})

    # Play games
    all_games: list[list[str]] = []
    for i in range(NUM_GAMES):
        if (i + 1) % 50 == 0:
            print(f"  Game {i + 1}/{NUM_GAMES}...", file=sys.stderr)
        result = play_one_game(engine)
        if result:
            all_games.append(result)

    print(f"  Played {len(all_games)} valid games", file=sys.stderr)

    # Deduplicate by exact move sequence
    seen: set[str] = set()
    unique: list[list[str]] = []
    for game in all_games:
        key = " ".join(game)
        if key not in seen:
            seen.add(key)
            unique.append(game)

    print(f"  {len(unique)} unique lines after dedup", file=sys.stderr)

    # Evaluate each line
    print("  Evaluating lines...", file=sys.stderr)
    evals: list[int] = []
    for game in unique:
        cp = evaluate_line(engine, game)
        evals.append(cp)

    engine.quit()

    # Sort by similarity (shared move prefix)
    indexed = list(zip(unique, evals))
    indexed.sort(key=lambda x: tuple(x[0]))

    # Convert to SAN and build output
    lines: list[tuple[str, str, int]] = []
    for game, cp in indexed:
        san = uci_to_san(game)
        lines.append((san, cp, len(game)))

    # Name them
    named: list[tuple[str, str]] = []
    for i, (san, cp, length) in enumerate(lines, 1):
        # Simple descriptive name based on eval
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

        # Add flavor from the opening branch
        tokens = san.split()
        # Detect 3rd move for Black (after 3.Bc4)
        if len(tokens) >= 6:
            black_3 = tokens[5]  # e.g. Bc5, Nf6, Be7, d6, h6
            if black_3 == "Bc5":
                flavor = "Giuoco Piano"
            elif black_3 == "Nf6":
                flavor = "Two Knights"
            elif black_3 == "Be7":
                flavor = "Hungarian"
            elif black_3 == "d6":
                flavor = "Semi-Italian"
            elif black_3 == "h6":
                flavor = "Anti-Italian"
            else:
                flavor = "Italian"
        else:
            flavor = "Italian"

        name = f"Italian #{i:02d} - {flavor} {tag}"
        named.append((name, san))

    # Output JSON
    print(json.dumps(named, indent=2))
    print(f"\nDone: {len(named)} lines generated", file=sys.stderr)


if __name__ == "__main__":
    main()
