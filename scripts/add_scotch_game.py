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


SCOTCH_LINES: list[tuple[str, str]] = [
    ("Scotch Game - Bishop Snare", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nf6 6. Nxc6 bxc6 7. Bxc5"),
    ("Scotch Game - E-Pawn Thrust", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 c5 6. Qe3 Nf6 7. e5"),
    ("Scotch Game - Queen's Fork", "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe4 5. Bc4 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4"),
    ("Scotch Game - Pawn Gift", "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Nd4 5. Nxd4 exd4 6. Qxd4"),
    ("Scotch Game - Knightmare Post", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bc5 6. Qe2 Bb6 7. N1c3 a6 8. Nd5 Qd8 9. Nxb6 cxb6 10. Nd6+ Kf8 11. Bf4"),
    ("Scotch Game - D-File Assault", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Nf6 7. Bg5 Be7 8. O-O-O O-O 9. e5 dxe5 10. Qxe5 Qe8 11. Qxc7 Be6 12. Bb5 Qc8 13. Qxe7"),
    ("Scotch Game - Knight's Decree", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Ng8 7. Nc3 d6 8. Bf4 dxe5 9. Qxe5+ Qe7 10. Nb5 Qxe5+ 11. Bxe5"),
    ("Scotch Game - Double Sac Attack", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Qe7 8. O-O Nd5 9. Nd2 O-O 10. Ne4 Bb6 11. c4 Nb4 12. Nf6+ gxf6 13. Bxh7+ Kxh7 14. Qh5+ Kg8 15. Qg4+ Kh7 16. Qh4+ Kg8 17. Bh6 Qxe5 18. Qg4+ Qg5 19. Bxg5"),
    ("Scotch Game - C7 Crush", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Ng8 7. Nc3 d6 8. Bf4 dxe5 9. Qxe5+ Be7 10. Nb5"),
    ("Scotch Game - Rook Snatch", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 Ng8 8. Nc3 d6 9. Nd5 Qd7 10. exd6 Bxd6 11. Qxg7"),
    ("Scotch Game - Pawn Plunder", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Nf6 7. Bg5 Be7 8. O-O-O O-O 9. e5 dxe5 10. Qxe5 Qe8 11. Qxc7 Be6 12. Bb5 Rc8 13. Qxb7 Rb8 14. Bxe8 Rxb7 15. Ba4"),
    ("Scotch Game - Endgame Edge", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nxd4 6. Bxd4 Bxd4 7. Qxd4 Qf6 8. e5 Qb6 9. Qxb6 axb6 10. Nc3 Ne7 11. O-O-O O-O 12. Bc4"),
    ("Scotch Game - Poisoned Pawn Gambit", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qe6 7. Bc4 Qg6 8. Nc3 Qxg2 9. Bd5 Qg6 10. Bd2"),
    ("Scotch Game - Bishop Skewer", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 Ng8 8. Nc3 d6 9. Nd5 Qd7 10. exd6 Qxd6 11. Bf4 Qe6+ 12. Be2"),
    ("Scotch Game - F7 Assault", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qe6 7. Bc4 Qb6 8. Qf4"),
    ("Scotch Game - Center Seize", "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Nce7 5. c4 Nf6 6. Nc3"),
    ("Scotch Game - Castle Denial", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 g6 9. Bh6 d6 10. Qa4 Bd7 11. O-O"),
    ("Scotch Game - Castle Denied", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 dxc6 6. Qxd8+ Kxd8 7. f3"),
    ("Scotch Game - Structure Break", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O Ne5 9. Be2 d5 10. f4 Nc4 11. Bxc4 dxc4 12. Nd2"),
    ("Scotch Game - Center Clamp", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qb6 7. Be3 Qxd4 8. Bxd4"),
    ("Scotch Game - F-Pawn Strike", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O Ne5 9. Be2 d6 10. f4"),
    ("Scotch Game - Gambit Trap", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 Ne5 8. Be2 d5 9. O-O dxe4 10. Nb5 Bd6 11. Bc5 O-O 12. Nxd6 cxd6 13. Qxd6 Qxd6 14. Bxd6"),
    ("Scotch Game - Scotch Standard", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 d6 8. O-O"),
    ("Scotch Game - Knight Hop", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bc5 6. Qe2 Bb6 7. N1c3 Nge7 8. Be3"),
    ("Scotch Game - Kingside Storm", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O d6 9. Nxc6 Nxc6 10. Bxc5 dxc5 11. f4 Be6 12. e5 Qe7 13. Bxe6 Qxe6 14. Nd2"),
    ("Scotch Game - Relentless Attack", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O d6 9. Nxc6 Nxc6 10. Bxc5 dxc5 11. f4 Be6 12. e5 Qg6 13. Bd3 Bf5 14. Bxf5 Qxf5 15. Nd2"),
    ("Scotch Game - Solid Schmidt", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 d5 7. exd5 cxd5 8. O-O Be7 9. c4"),
]


def main() -> None:
    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    added = 0
    skipped = 0
    failed = 0

    with db.connect() as conn:
        for name, pgn in SCOTCH_LINES:
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

