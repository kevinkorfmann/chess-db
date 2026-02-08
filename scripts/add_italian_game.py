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


# Italian Game lines.
ITALIAN_LINES: list[tuple[str, str]] = [
    (
        "Italian Game #01 - Rook Gambit",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1",
    ),
    (
        "Italian Game #02 - Queen's Assault",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4",
    ),
    (
        "Italian Game #03 - Pawn Phalanx",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb6 7. e5 Ng4 8. h3 Nh6 9. d5 Na5 10. Bg5 f6 11. exf6",
    ),
    (
        "Italian Game #04 - Pinning Pressure",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Ba5 12. Qa4 O-O 13. d5 Ne5 14. Nxe5 dxe5 15. Qxa5",
    ),
    (
        "Italian Game #05 - Queen Skewer",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Bb4 12. Bxb4 Nxb4 13. Qe1+ Qe7 14. Qxb4",
    ),
    (
        "Italian Game #06 - Checkmate Chase",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nde4 17. Nd2 d6 18. Nxe4 Nxe4 19. Re8#",
    ),
    (
        "Italian Game #07 - Solid Setup",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 d6 8. O-O",
    ),
    (
        "Italian Game #08 - Blunder Bounty",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 Qxd1+ 12. Nxd1 bxc6 13. Rxe7",
    ),
    (
        "Italian Game #09 - Sacrificial Storm",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ c6 15. Nxf7 Kxf7 16. Qf3+ Kg8 17. Rae1 cxb5 18. Rxe7",
    ),
    (
        "Italian Game #10 - Rook Rampage",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nfe4 17. Re1 f6 18. Re7 Nf5 19. Re8+ Kf7 20. Rxh8 Nxh6 21. Rxe4",
    ),
    (
        "Italian Game #11 - Suffocation Mate",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Kf8 15. Qh5 g6 16. Qf3 hxg5 17. Qf6 Rh4 18. Rxh4 gxh4 19. Re1 Bd7 20. Rxe7 Qxe7 21. Qh8#",
    ),
    (
        "Italian Game #12 - Tempo Taker",
        "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 Bd7 5. Nc3 exd4 6. Nxd4 Nxd4 7. Bxd7+ Qxd7 8. Qxd4 Nf6 9. Bg5 Be7 10. O-O-O",
    ),
    (
        "Italian Game #13 - Queen's Siege",
        "1. e4 e5 2. Nf3 d6 3. d4 exd4 4. Nxd4 Nf6 5. Nc3 Be7 6. Bf4 O-O 7. Qd2 a6 8. O-O-O",
    ),
    (
        "Italian Game #14 - Central Lock",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 d6 5. d5",
    ),
    (
        "Italian Game #15 - Royal Pin",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qa5 9. Nxe4 Be6 10. Neg5 O-O-O 11. Nxe6 fxe6 12. Rxe6 Bd6 13. Bg5 Rde8 14. Qe2",
    ),
    (
        "Italian Game #16 - Pawn Crunch",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 bxc6 12. Qxd8 Bxd8 13. Rc4",
    ),
    (
        "Italian Game #17 - Pinpoint Attack",
        "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 exd4 5. Qxd4 Bd7 6. Bxc6 Bxc6 7. Nc3 Nf6 8. Bg5 Be7 9. O-O-O",
    ),
    (
        "Italian Game #18 - Rook Bazooka",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Bd7 15. Qe2 hxg5 16. Re1 O-O 17. Rxe7 Bxb5 18. Qxb5",
    ),
    (
        "Italian Game #19 - Central Clamp",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qh5 9. Nxe4 Be6 10. Bg5 Bd6 11. Nxd6+ cxd6 12. Bf4 Qd5 13. c3",
    ),
    (
        "Italian Game #20 - King Hunt",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 O-O 14. Nxh7 Kxh7 15. Qh5+ Kg8 16. Rh4",
    ),
    (
        "Italian Game #21 - Tempo Fork",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 O-O 12. Qxc4 Nd6 13. Qb3",
    ),
    (
        "Italian Game #22 - Overload Assault",
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nf6 8. e5 Ne4 9. O-O Nxc3 10. bxc3 Bxc3 11. Qb3 Bxa1 12. Bxf7+ Kf8 13. Ba3+ d6 14. exd6 cxd6 15. Bg6 Qf6 16. Bxd6+ Ne7 17. Re1",
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

