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


PONZIANI_LINES: list[tuple[str, str]] = [
    (
        "Ponziani #01 - Paralysis Trap",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb6 6. Nc3 Nf6 7. e5 Ng4 8. h3 Nh6 9. d5 Ne7 10. d6 cxd6 11. exd6 Nef5 12. Bg5 f6 13. Bxh6 Nxh6 14. Bc4",
    ),
    (
        "Ponziani #02 - Vicious Prong",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Nf6 4. d4 Nxe4 5. d5 Ne7 6. Nxe5 d6 7. Bb5+ c6 8. dxc6 bxc6 9. Nxc6 Nxc6 10. Bxc6+ Bd7 11. Bxe4",
    ),
    ("Ponziani #03 - Central Charge", "1. e4 e5 2. Nf3 Nc6 3. c3 Nf6 4. d4 exd4 5. e5 Nd5 6. cxd4"),
    (
        "Ponziani #04 - Central Bastion",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb4+ 6. Nc3 d6 7. d5 Bxc3+ 8. bxc3",
    ),
    ("Ponziani #05 - Pawn Wall", "1. e4 e5 2. Nf3 Nc6 3. c3 Nf6 4. d4 exd4 5. e5 Ng4 6. cxd4"),
    ("Ponziani #06 - Pinpoint Wall", "1. e4 e5 2. Nf3 Nc6 3. c3 Nf6 4. d4 exd4 5. e5 Qe7 6. cxd4 d6 7. Bb5"),
    (
        "Ponziani #07 - Steed's Flight",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Nf6 4. d4 Nxe4 5. d5 Ne7 6. Nxe5 d6 7. Bb5+ c6 8. dxc6 bxc6 9. Nxc6 Qb6 10. Nd4+",
    ),
    (
        "Ponziani #08 - Pawn Grip",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb4+ 6. Nc3 Nf6 7. d5 Ne7 8. Bd3",
    ),
    ("Ponziani #09 - Flank Counter", "1. e4 e5 2. Nf3 Nc6 3. c3 d6 4. d4 exd4 5. cxd4 Bg4 6. Qa4 Bxf3 7. gxf3"),
    (
        "Ponziani #10 - Steed Lockdown",
        "1. e4 e5 2. Nf3 Nc6 3. c3 d6 4. d4 Bg4 5. Qb3 Bxf3 6. gxf3 exd4 7. Qxb7 Ne5 8. f4 Nf3+ 9. Ke2 Nh4 10. Qc6+ Ke7 11. f5",
    ),
    ("Ponziani #11 - Central Stake", "1. e4 e5 2. Nf3 Nc6 3. c3 d6 4. d4 exd4 5. cxd4"),
    (
        "Ponziani #12 - Cleric's Grab",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb4+ 6. Nc3 d6 7. d5 Ne5 8. Qa4+ Bd7 9. Qxb4",
    ),
    (
        "Ponziani #13 - Steed Humiliation",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb6 6. Nc3 Nf6 7. e5 Ng4 8. h3 Nh6 9. d5 Nb4 10. Bg5 f6 11. exf6 gxf6 12. Bxh6",
    ),
    (
        "Ponziani #14 - Cleric's Raid",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb4+ 6. Nc3 Nf6 7. d5 Ne7 8. Bd3 d6 9. Qa4+ Bd7 10. Qxb4",
    ),
    (
        "Ponziani #15 - Pawn Lunge",
        "1. e4 e5 2. Nf3 Nc6 3. c3 d5 4. Qa4 dxe4 5. Nxe5 Bd7 6. Nxd7 Qxd7 7. Qxe4+ Be7 8. d4",
    ),
    (
        "Ponziani #16 - Pawn Edge",
        "1. e4 e5 2. Nf3 Nc6 3. c3 d5 4. Qa4 Bd7 5. exd5 Nd4 6. Qd1 Nxf3+ 7. Qxf3 Nf6 8. Bc4",
    ),
    ("Ponziani #17 - Royal Foray", "1. e4 e5 2. Nf3 Nc6 3. c3 d5 4. Qa4 dxe4 5. Nxe5 Qd5 6. Nxc6"),
    (
        "Ponziani #18 - Steed Purge",
        "1. e4 e5 2. Nf3 Nc6 3. c3 Bc5 4. d4 exd4 5. cxd4 Bb6 6. Nc3 Nf6 7. e5 Ng4 8. h3 Nh6 9. d5 Ne7 10. d6 Nc6 11. Bg5 f6 12. exf6 gxf6 13. Bxh6",
    ),
    (
        "Ponziani #19 - Crumbling Wall",
        "1. e4 e5 2. Nf3 Nc6 3. c3 d6 4. d4 Bg4 5. Qb3 Bxf3 6. gxf3 exd4 7. Qxb7 Nge7 8. Bb5",
    ),
]


def main() -> None:
    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    if not PONZIANI_LINES:
        raise SystemExit("No lines configured in scripts/add_ponziani.py.")

    added = 0
    skipped = 0
    failed = 0

    with db.connect() as conn:
        for name, pgn in PONZIANI_LINES:
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
