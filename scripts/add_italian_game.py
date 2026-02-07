from __future__ import annotations

import re
import sqlite3

from chess_db.config import get_settings
from chess_db.db import Db, init_db
from chess_db.openings import add_opening


MOVE_NUMBER_RE = re.compile(r"^\d+\.(\.\.)?$")  # "12." or "12.."


def sanitize_pgn_moves(pgn: str) -> str:
    tokens: list[str] = []
    for raw in pgn.replace("\n", " ").split():
        tok = raw.strip()
        if not tok:
            continue
        if MOVE_NUMBER_RE.match(tok):
            continue
        if tok in {"1-0", "0-1", "1/2-1/2", "*"}:
            continue
        tokens.append(tok)
    return " ".join(tokens)


# Curated Italian Game set (White repertoire / common branches).
# Sources used for canonical move orders: Lichess Opening Explorer, Chess.com openings pages, Wikipedia.
ITALIAN_LINES: list[tuple[str, str]] = [
    (
        "Italian Game - Starter",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4",
    ),
    (
        "Italian Game - Giuoco Piano (Open Italian)",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3",
    ),
    (
        "Italian Game - Giuoco Pianissimo Setup",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O 7. Re1 a6 8. Bb3 Ba7 9. Nbd2",
    ),
    (
        "Italian Game - Evans Gambit Accepted",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. b4 Bxb4 5. c3 Ba5 6. d4 exd4 7. O-O d3 8. Qb3",
    ),
    (
        "Italian Game - Two Knights (Fried Liver Attack)",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7 Kxf7 7. Qf3+",
    ),
    (
        "Italian Game - Two Knights (5...Na5 sideline)",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Na5 6. Bb5+ c6 7. dxc6 bxc6 8. Ba4",
    ),
    (
        "Italian Game - Hungarian Defense",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Be7 4. d4 exd4 5. Nxd4 Nf6 6. Nc3 O-O 7. O-O",
    ),
]


def main() -> None:
    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    added = 0
    skipped = 0
    failed = 0

    with db.connect() as conn:
        for name, pgn in ITALIAN_LINES:
            moves_san = sanitize_pgn_moves(pgn)
            try:
                add_opening(conn, name=name, moves_san=moves_san)
            except sqlite3.IntegrityError:
                skipped += 1
                print(f"SKIP (already exists): {name}")
            except Exception as e:  # noqa: BLE001 - CLI-like script
                failed += 1
                print(f"FAIL: {name}: {e}")
            else:
                added += 1
                print(f"ADDED: {name}")

    print()
    print(f"Done. added={added} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()

