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


ITALIAN_LINES: list[tuple[str, str]] = [
    # Base lines (Italian Game)
    ("Italian Game #01 - Pawn Wall", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb6 7. e5 Ng4 8. h3 Nh6 9. d5 Na5 10. Bg5 f6 11. exf6"),
    ("Italian Game #02 - Smother Mate", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Kf8 15. Qh5 g6 16. Qf3 hxg5 17. Qf6 Rh4 18. Rxh4 gxh4 19. Re1 Bd7 20. Rxe7 Qxe7 21. Qh8#"),
    ("Italian Game #03 - Central Seal", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 d6 5. d5"),
    ("Italian Game #04 - Royal Hunt", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 O-O 14. Nxh7 Kxh7 15. Qh5+ Kg8 16. Rh4"),
    ("Italian Game #05 - Tower Bazooka", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Bd7 15. Qe2 hxg5 16. Re1 O-O 17. Rxe7 Bxb5 18. Qxb5"),
    ("Italian Game #06 - Overload Strike", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nf6 8. e5 Ne4 9. O-O Nxc3 10. bxc3 Bxc3 11. Qb3 Bxa1 12. Bxf7+ Kf8 13. Ba3+ d6 14. exd6 cxd6 15. Bg6 Qf6 16. Bxd6+ Ne7 17. Re1"),
    ("Italian Game #07 - Pinpoint Strike", "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 exd4 5. Qxd4 Bd7 6. Bxc6 Bxc6 7. Nc3 Nf6 8. Bg5 Be7 9. O-O-O"),
    ("Italian Game #08 - Royal Siege", "1. e4 e5 2. Nf3 d6 3. d4 exd4 4. Nxd4 Nf6 5. Nc3 Be7 6. Bf4 O-O 7. Qd2 a6 8. O-O-O"),
    ("Italian Game #09 - Mate Chase", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nde4 17. Nd2 d6 18. Nxe4 Nxe4 19. Re8#"),
    ("Italian Game #10 - Solid Structure", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 d6 8. O-O"),
    ("Italian Game #11 - Sacrifice Storm", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ c6 15. Nxf7 Kxf7 16. Qf3+ Kg8 17. Rae1 cxb5 18. Rxe7"),
    ("Italian Game #12 - Tower Sacrifice", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1"),
    ("Italian Game #13 - Pawn Crush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 bxc6 12. Qxd8 Bxd8 13. Rc4"),
    ("Italian Game #14 - Blunder Prize", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 Qxd1+ 12. Nxd1 bxc6 13. Rxe7"),
    ("Italian Game #15 - Tempo Prong", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 O-O 12. Qxc4 Nd6 13. Qb3"),
    ("Italian Game #16 - Central Grip", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qh5 9. Nxe4 Be6 10. Bg5 Bd6 11. Nxd6+ cxd6 12. Bf4 Qd5 13. c3"),
    ("Italian Game #17 - Pin Pressure", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Ba5 12. Qa4 O-O 13. d5 Ne5 14. Nxe5 dxe5 15. Qxa5"),
    ("Italian Game #18 - Tempo Grab", "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 Bd7 5. Nc3 exd4 6. Nxd4 Nxd4 7. Bxd7+ Qxd7 8. Qxd4 Nf6 9. Bg5 Be7 10. O-O-O"),
    ("Italian Game #19 - King Pin", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qa5 9. Nxe4 Be6 10. Neg5 O-O-O 11. Nxe6 fxe6 12. Rxe6 Bd6 13. Bg5 Rde8 14. Qe2"),
    ("Italian Game #20 - Royal Skewer", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Bb4 12. Bxb4 Nxb4 13. Qe1+ Qe7 14. Qxb4"),
    ("Italian Game #21 - Tower Rampage", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nfe4 17. Re1 f6 18. Re7 Nf5 19. Re8+ Kf7 20. Rxh8 Nxh6 21. Rxe4"),
    ("Italian Game #22 - Royal Assault", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4"),
    # Extended lines (Italian Extended)
    ("Italian Extended #01 - 🎯 5 Spear", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Nxd4 6. Qxd4 Nf6 7. e5 c5 8. Qf4"),
    ("Italian Extended #02 - 📖 7 Checkmate", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Bc5 6. Qd5 Bxf2+ 7. Kf1 f5 8. Qf7#"),
    ("Italian Extended #03 - 🎯 acrificial Storm", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ c6 15. Nxf7 Kxf7 16. Qf3+ Kg8 17. Rae1 cxb5 18. Rxe7"),
    ("Italian Extended #04 - 📖 ook Bait", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1 d6 15. Qe1+ Kd7 16. Qe4"),
    ("Italian Extended #05 - 📖 hilidor Squeeze", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 c6 8. Be3 Nd7 9. O-O-O"),
    ("Italian Extended #06 - 📖 7 Guillotine", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Bc5 6. Qd5 Nxf2 7. Qxf7#"),
    ("Italian Extended #07 - 🎯 lunder Bounty", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 Qxd1+ 12. Nxd1 bxc6 13. Rxe7"),
    ("Italian Extended #08 - 📖 ueen Ambush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Bb4+ 5. c3 Ba5 6. dxe5 Nxe4 7. Qd5 O-O 8. Qxe4"),
    ("Italian Extended #09 - 🎯 heckmate Chase", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nde4 17. Nd2 d6 18. Nxe4 Nxe4 19. Re8#"),
    ("Italian Extended #10 - 🎯 ingside Launch", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb6 7. e5 Qe7 8. O-O"),
    ("Italian Extended #11 - 🎯 inpoint Attack", "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 exd4 5. Qxd4 Bd7 6. Bxc6 Bxc6 7. Nc3 Nf6 8. Bg5 Be7 9. O-O-O"),
    ("Italian Extended #12 - 📖 ueen Laser", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 f5 7. Bg5 Be7 8. Bxe7 Qxe7 9. Nbd2"),
    ("Italian Extended #13 - 🎯 astle Blockade", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1 d6 15. Qe1+ Be6 16. d5"),
    ("Italian Extended #14 - 📖 7 Hammer", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ng8 7. Ng5 Nh6 8. Re1 O-O 9. Qd3 d5 10. Qxh7#"),
    ("Italian Extended #15 - 📖 5 Punch", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 d5 7. exf6 dxc4 8. Re1+"),
    ("Italian Extended #16 - 📖 7 Ambush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 Nf6 5. Nxe5 Nxe5 6. dxe5 Nxe4 7. Bxf7+ Kxf7 8. Qd5+ Ke8 9. Qxe4 Qe7 10. Nc3 d6 11. Nd5"),
    ("Italian Extended #17 - 🎯 oyal Pin", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qa5 9. Nxe4 Be6 10. Neg5 O-O-O 11. Nxe6 fxe6 12. Rxe6 Bd6 13. Bg5 Rde8 14. Qe2"),
    ("Italian Extended #18 - 🎯 talian King Hunt", "1. e4 e5 2. Nf3 f6 3. Nxe5 fxe5 4. Qh5+ Ke7 5. Qxe5+ Kf7 6. Bc4+ Kg6 7. Qf5+ Kh6 8. h4 g6 9. d3+ Kg7 10. Qf7#"),
    ("Italian Extended #19 - 🎯 olid Setup", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 d6 8. O-O"),
    ("Italian Extended #20 - 📖 ook Raid", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Nf6 8. Bg5 Be7 9. Rd1 Qc8 10. Nd5 Nxd5 11. Qxd5 Bxg5 12. Qxa8"),
    ("Italian Extended #21 - 📖 night Snack", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ne4 7. Qe2 Ng5 8. Nxg5"),
    ("Italian Extended #22 - 📖 ueen Knight Mate", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 f6 5. Nh4 exd4 6. Qh5+ Ke7 7. Nf5#"),
    ("Italian Extended #23 - 🎯 7 Battery", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Bc5 8. Bc4"),
    ("Italian Extended #24 - 📖 ueen Raid", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1 Re8 15. d5 d6 16. Qxg7 Bf5 17. Qg5+"),
    ("Italian Extended #25 - 📖 ook Heist", "1. e4 e5 2. Nf3 f6 3. Nxe5 fxe5 4. Qh5+ g6 5. Qxe5+ Be7 6. Qxh8"),
    ("Italian Extended #26 - 🎯 ueen Heist", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 Nc6 7. Qxb7"),
    ("Italian Extended #27 - 🎯 ook Bazooka", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Bd7 15. Qe2 hxg5 16. Re1 O-O 17. Rxe7 Bxb5 18. Qxb5"),
    ("Italian Extended #28 - 🎯 awn Phalanx", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb6 7. e5 Ng4 8. h3 Nh6 9. d5 Na5 10. Bg5 f6 11. exf6"),
    ("Italian Extended #29 - 📖 7 Thunder", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ne4 7. Qe2 d5 8. exd6 Bf5 9. Nbd2 O-O 10. Nxe4 Re8 11. Bxf7+ Kxf7 12. Qc4+ Kf8 13. dxc7"),
    ("Italian Extended #30 - 📖 ing Hunt", "1. e4 e5 2. Nf3 f6 3. Nxe5 fxe5 4. Qh5+ g6 5. Qxe5+ Kf7 6. Bc4+"),
    ("Italian Extended #31 - 🎯 astle Strike", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Nxd4 6. Qxd4 Nf6 7. e5 Qe7 8. O-O"),
    ("Italian Extended #32 - 📖 nnamed Line", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 c6 8. Be3 Nf6 9. Bc4 Qc7 10. O-O-O Bd6 11. Bxf7+ Qxf7 12. Qxf7+"),
    ("Italian Extended #33 - 🎯 astle Blocker", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Ba5 12. Qa4 O-O 13. d5 Bb6 14. dxc6 bxc6 15. Bd3"),
    ("Italian Extended #34 - 📖 6 Hook", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ng4 7. Bf4 O-O 8. h3 Nh6 9. Bxh6 gxh6 10. c3 dxc3 11. Nxc3"),
    ("Italian Extended #35 - 📖 empo Fork", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 O-O 12. Qxc4 Nd6 13. Qb3"),
    ("Italian Extended #36 - 🎯 verload Assault", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 h6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nf6 8. e5 Ne4 9. O-O Nxc3 10. bxc3 Bxc3 11. Qb3 Bxa1 12. Bxf7+ Kf8 13. Ba3+ d6 14. exd6 cxd6 15. Bg6 Qf6 16. Bxd6+ Ne7 17. Re1"),
    ("Italian Extended #37 - 🎯 awn Crunch", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qd8 9. Rxe4+ Be7 10. Nxd4 O-O 11. Nxc6 bxc6 12. Qxd8 Bxd8 13. Rc4"),
    ("Italian Extended #38 - 🎯 entral Lock", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 d6 5. d5"),
    ("Italian Extended #39 - 🎯 entral Clamp", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Nxe4 6. Re1 d5 7. Bxd5 Qxd5 8. Nc3 Qh5 9. Nxe4 Be6 10. Bg5 Bd6 11. Nxd6+ cxd6 12. Bf4 Qd5 13. c3"),
    ("Italian Extended #40 - 📖 hilidor Crusher", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Nf6 8. Bg5 Be7 9. Rd1 Nbd7 10. Bxf6 Bxf6 11. Bb5 O-O 12. Bxd7 Qe7 13. Nd5"),
    ("Italian Extended #41 - 🎯 hilidor Bust", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 dxe5 5. Qxd8+ Kxd8 6. Nxe5"),
    ("Italian Extended #42 - 📖 ueen Sprint", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 f6 5. Nh4 Nxd4 6. Qh5+ Ke7 7. Qf7+ Kd6 8. Qd5+ Ke7 9. Ng6+"),
    ("Italian Extended #43 - 🎯 inning Pressure", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Ba5 12. Qa4 O-O 13. d5 Ne5 14. Nxe5 dxe5 15. Qxa5"),
    ("Italian Extended #44 - 📖 astle Blockade", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1 d6 15. Qe1+ Kf8 16. Qa5 b6 17. Qd5"),
    ("Italian Extended #45 - 🎯 ueen's Siege", "1. e4 e5 2. Nf3 d6 3. d4 exd4 4. Nxd4 Nf6 5. Nc3 Be7 6. Bf4 O-O 7. Qd2 a6 8. O-O-O"),
    ("Italian Extended #46 - 📖 astle Lock", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 Bxa1 11. Re1+ Ne7 12. Bxe7 Qxe7 13. Rxe7+ Kxe7 14. Qxa1 Re8 15. d5 Kf8 16. d6 cxd6 17. Qd1 Rb8 18. Qxd6+"),
    ("Italian Extended #47 - 📖 ueen Squeeze", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Nc6 8. Bb5 Qd6 9. Bg5"),
    ("Italian Extended #48 - 📖 ouble Pin Squeeze", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Nc6 8. Bb5 Ne7 9. Bg5 f6 10. Rd1 Qc8 11. Qc4"),
    ("Italian Extended #49 - 📖 7 Squeeze", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 b6 7. Nc3 Nf6 8. Bg5 h6 9. Bc4"),
    ("Italian Extended #50 - 📖 enter Break", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 d5 5. exd5"),
    ("Italian Extended #51 - 📖 7 Fork", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Be7 6. Qd5"),
    ("Italian Extended #52 - 📖 7 Smash", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O d5 6. exd5 Nxd5 7. Ng5 Be7 8. Nxf7 Kxf7 9. Qf3+ Ke6 10. Re1+ Kd6 11. Qxd5#"),
    ("Italian Extended #53 - 📖 7 Crush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Nxd4 6. Qxd4 b6 7. Qd5 c6 8. Qxf7#"),
    ("Italian Extended #54 - 🎯 uffocation Mate", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 h6 14. Bb5+ Kf8 15. Qh5 g6 16. Qf3 hxg5 17. Qf6 Rh4 18. Rxh4 gxh4 19. Re1 Bd7 20. Rxe7 Qxe7 21. Qh8#"),
    ("Italian Extended #55 - 🎯 7 Squeeze", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ng8 7. Ng5 d5 8. exd6"),
    ("Italian Extended #56 - 🎯 ook Robbery", "1. e4 e5 2. Nf3 f6 3. Nxe5 fxe5 4. Qh5+ g6 5. Qxe5+ Qe7 6. Qxh8 Qxe4+ 7. Kd1"),
    ("Italian Extended #57 - 🎯 ueen's Assault", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 Nxe4 5. dxe5 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4"),
    ("Italian Extended #58 - 📖 ueen Bait", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ng8 7. Ng5 Nh6 8. Re1 O-O 9. Qd3 g6 10. Qh3 Kg7 11. Qxh6+ Kxh6 12. Nxf7+ Kg7 13. Bh6+ Kg8 14. Nxd8+ Kh8 15. Nf7+ Kg8 16. Nd6+"),
    ("Italian Extended #59 - 🎯 ishop Ambush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bxd4 7. Nxd4"),
    ("Italian Extended #60 - 🎯 ing Hunt", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 12. Bg5 Bxg5 13. Nxg5 O-O 14. Nxh7 Kxh7 15. Qh5+ Kg8 16. Rh4"),
    ("Italian Extended #61 - 🎯 ueen Slide", "1. e4 e5 2. Nf3 Nc6 3. Bc4 h6 4. d4 exd4 5. Nxd4 Nxd4 6. Qxd4 c5 7. Qd3"),
    ("Italian Extended #62 - 📖 7 Crush", "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Qb3 Qc8 7. Bc4"),
    ("Italian Extended #63 - 📖 ack Rank Crush", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Ng8 7. Ng5 Nh6 8. Re1 O-O 9. Qd3 g6 10. Qh3 Kg7 11. Qxh6+ Kxh6 12. Nxf7+ Kg7 13. Bh6+ Kg8 14. Nxd8+ d5 15. exd6+ Kh8 16. Nf7+ Rxf7 17. Re8+"),
    ("Italian Extended #64 - 🎯 ook Rampage", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Ne5 10. bxc3 Nxc4 11. Qd4 Ncd6 12. Qxg7 Qf6 13. Qxf6 Nxf6 14. Re1+ Kf8 15. Bh6+ Kg8 16. Re5 Nfe4 17. Re1 f6 18. Re7 Nf5 19. Re8+ Kf7 20. Rxh8 Nxh6 21. Rxe4"),
    ("Italian Extended #65 - 🎯 ueen Skewer", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Nxc3 9. bxc3 Bxc3 10. Ba3 d6 11. Rc1 Bb4 12. Bxb4 Nxb4 13. Qe1+ Qe7 14. Qxb4"),
    ("Italian Extended #66 - 🎯 7 Fork", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4 5. O-O Bc5 6. e5 Nh5 7. Ng5"),
    ("Italian Extended #67 - 📖 ing Hunt", "1. e4 e5 2. Nf3 f6 3. Nxe5 fxe5 4. Qh5+ Ke7 5. Qxe5+ Kf7 6. Bc4+ Kg6 7. Qf5+ Kh6 8. h4 Qf6 9. d4+ g5 10. hxg5+ Kg7 11. gxf6+"),
    ("Italian Extended #68 - 🎯 empo Taker", "1. e4 e5 2. Nf3 d6 3. d4 Nc6 4. Bb5 Bd7 5. Nc3 exd4 6. Nxd4 Nxd4 7. Bxd7+ Qxd7 8. Qxd4 Nf6 9. Bg5 Be7 10. O-O-O"),
]


def main() -> None:
    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    if not ITALIAN_LINES:
        raise SystemExit("No lines configured in scripts/add_italian.py.")

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
