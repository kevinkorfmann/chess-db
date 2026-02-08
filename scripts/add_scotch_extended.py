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


# Paste your Scotch Extended lines here as (name, pgn_moves).
# Example:
# ("Scotch Extended - Line 01", "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 ..."),
SCOTCH_EXTENDED_LINES: list[tuple[str, str]] = [
    (
        "Scotch Extended #01 - Knight Hunt",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 c5 7. Qe3 Nd5 8. Qf3",
    ),
    (
        "Scotch Extended #02 - Knight Hunt",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 c5 6. Qe3 Nf6 7. e5 Nd5 8. Qf3",
    ),
    (
        "Scotch Extended #03 - Pawn Uppercut",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 c5 8. exf6",
    ),
    ("Scotch Extended #04 - Knight Kick", "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Na5 5. b4"),
    (
        "Scotch Extended #05 - D Pawn Damage",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bd6 6. Nxd6+ Qxd6 7. Qxd6 cxd6 8. Bf4",
    ),
    (
        "Scotch Extended #06 - Queen Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Bb4+ 4. c3 Ba5 5. d5 Nce7 6. Nxe5 d6 7. Qa4+",
    ),
    (
        "Scotch Extended #07 - G8 Snatch",
        "1. e4 e5 2. Nf3 Nc6 3. d4 f6 4. Bc4 exd4 5. O-O Bc5 6. c3 dxc3 7. Bxg8",
    ),
    (
        "Scotch Extended #08 - C7 Fork Trap",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bd6 6. Nxd6+ cxd6 7. Nc3 Nge7 8. Be3 O-O 9. Qd2",
    ),
    (
        "Scotch Extended #09 - Queen Steamroll",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 Nh5 8. g4 c5 9. Qd5",
    ),
    (
        "Scotch Extended #10 - Queen Kick",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Qe5 6. N1c3 a6 7. f4",
    ),
    (
        "Scotch Extended #11 - G Pawn Ambush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Nh5 7. g4 c5 8. Qd5 Qa5+ 9. Nc3",
    ),
    (
        "Scotch Extended #12 - En Passant Squeeze",
        "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Nd4 5. Nxd4 exd4 6. Qxd4 c5 7. dxc6 bxc6 8. Nc3 c5 9. Bb5+ Bd7 10. Qd3",
    ),
    (
        "Scotch Extended #13 - Unnamed Line",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 b6 6. Nc3 Bc5 7. Qxg7 Qh4 8. Qxh8",
    ),
    (
        "Scotch Extended #14 - Queen Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe5 5. Nxe5 Nxe4 6. Qd5",
    ),
    (
        "Scotch Extended #15 - D File Ambush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Nf6 7. Bg5 Be7 8. O-O-O O-O 9. e5 dxe5 10. Qxe5 Qe8 11. Qxc7 h6 12. Bxh6 gxh6 13. Bb5 Bd7 14. Bxd7 Nxd7 15. Qxd7 Qxd7 16. Rxd7",
    ),
    (
        "Scotch Extended #16 - D-File Assault",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Nf6 7. Bg5 Be7 8. O-O-O O-O 9. e5 dxe5 10. Qxe5 Qe8 11. Qxc7 Be6 12. Bb5 Qc8 13. Qxe7",
    ),
    (
        "Scotch Extended #17 - F7 Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe4 5. Bc4 h6 6. Qd5",
    ),
    (
        "Scotch Extended #18 - Knight's Decree",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Ng8 7. Nc3 d6 8. Bf4 dxe5 9. Qxe5+ Qe7 10. Nb5 Qxe5+ 11. Bxe5",
    ),
    (
        "Scotch Extended #19 - C7 Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qh4 5. Nc3 Bb4 6. Be2 Qxe4 7. Nb5 Ba5 8. Nxc7+",
    ),
    (
        "Scotch Extended #20 - Queen Spear",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Nh5 7. g4 c5 8. Qd5 Nf4 9. Bxf4 Qa5+ 10. Nc3",
    ),
    (
        "Scotch Extended #21 - Knight Harvest",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 d6 8. exf6 gxf6 9. Nc3",
    ),
    (
        "Scotch Extended #22 - Queen Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe4 5. Bc4 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4 Bb6 9. Nc3 d6 10. Bd3 g6 11. Bg5 Qe8 12. Nd5",
    ),
    (
        "Scotch Extended #23 - Bishop Bounty",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nf6 6. Nxc6 bxc6 7. Bxc5 Nxe4 8. Qe2 d5 9. f3 Qh4+ 10. g3",
    ),
    (
        "Scotch Extended #24 - Poisoned B Pawn",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 c5 6. Qe3 Qa5+ 7. Bd2 Qb6 8. Nc3 Qxb2 9. Rb1 Qxc2 10. Bd3",
    ),
    (
        "Scotch Extended #25 - Queen Heist",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nf6 6. Nxc6 dxc6 7. Qxd8+ Kxd8 8. Bxc5 Nxe4 9. Bd4 f6 10. Nc3",
    ),
    (
        "Scotch Extended #26 - F7 Finish",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe4 5. Bc4 Bc5 6. Qd5 Nxf2 7. Qxf7#",
    ),
    (
        "Scotch Extended #27 - Central Queen",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Be6 7. Bf4",
    ),
    (
        "Scotch Extended #28 - Queenless Crush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 d6 6. Nxc6 bxc6 7. Bxc5 dxc5 8. Qxd8+ Kxd8 9. Nd2 Nf6 10. O-O-O Ke7 11. Nb3",
    ),
    (
        "Scotch Extended #29 - C7 Crusher",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bc5 6. Qe2 Bb6 7. N1c3 a6 8. Nd5 Qe5 9. f4",
    ),
    (
        "Scotch Extended #30 - Queen Fork",
        "1. e4 e5 2. Nf3 Nc6 3. d4 Nf6 4. dxe5 Nxe4 5. Bc4 Bc5 6. Qd5 Bxf2+ 7. Kf1 O-O 8. Qxe4 Bb6 9. Nc3 Re8 10. Bg5 Ne7 11. Bd3",
    ),
    (
        "Scotch Extended #31 - Unnamed Line",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 c5 7. Qe3 Ng4 8. Qe4 d6 9. exd6+ Be6 10. Bb5+ Qd7 11. Bxd7+ Kxd7 12. Qxb7+ Kxd6 13. Bf4+",
    ),
    (
        "Scotch Extended #32 - F7 Ambush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 f6 4. Bc4 exd4 5. O-O Ne5 6. Nxe5 fxe5 7. Qh5+",
    ),
    (
        "Scotch Extended #33 - Queen Heist",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Ng8 7. Nc3 b6 8. Bc4 Bc5 9. Qd5 Qe7 10. Qxa8 Qxe5+ 11. Qe4",
    ),
    (
        "Scotch Extended #34 - Queen Bait",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nge7 6. Nxc6 Bxe3 7. Nxd8",
    ),
    (
        "Scotch Extended #35 - F7 Crush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bc5 6. Qe2 Bb6 7. N1c3 a6 8. Nd5 Qd8 9. Nxb6 cxb6 10. Nd6+ Kf8 11. Bf4 Nge7 12. Qc4",
    ),
    (
        "Scotch Extended #36 - Queen Ambush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nf6 6. Nxc6 Bxe3 7. Nxd8 Bxf2+ 8. Kxf2 Nxe4+ 9. Kg1",
    ),
    (
        "Scotch Extended #37 - Queen Net",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Qe7 8. O-O Nd5 9. Nd2 O-O 10. Ne4 Bb6 11. c4 Nb4 12. Nf6+ gxf6 13. Bxh7+ Kxh7 14. Qh5+ Kg8 15. Qg4+ Kh7 16. Qh4+ Kg8 17. Bh6 Qxe5 18. Qg4+ Qg5 19. Bxg5 fxg5 20. Qxg5+ Kh7 21. Rae1",
    ),
    (
        "Scotch Extended #38 - C7 Crush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Ng8 7. Nc3 d6 8. Bf4 dxe5 9. Qxe5+ Be7 10. Nb5",
    ),
    (
        "Scotch Extended #39 - Rook Snatch",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 Ng8 8. Nc3 d6 9. Nd5 Qd7 10. exd6 Bxd6 11. Qxg7",
    ),
    (
        "Scotch Extended #40 - Unnamed Line",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Qe7 8. O-O Nd5 9. Nd2 O-O 10. Ne4 Bb6 11. c4 Nb4 12. Nf6+ gxf6 13. Bxh7+ Kxh7 14. Qh5+ Kg8 15. Qg4+ Kh7 16. Qh4+ Kg8 17. g4",
    ),
    (
        "Scotch Extended #41 - Pawn Plunder",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 d6 6. Nc3 Nf6 7. Bg5 Be7 8. O-O-O O-O 9. e5 dxe5 10. Qxe5 Qe8 11. Qxc7 Be6 12. Bb5 Rc8 13. Qxb7 Rb8 14. Bxe8 Rxb7 15. Ba4",
    ),
    (
        "Scotch Extended #42 - Endgame Edge",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Nxd4 6. Bxd4 Bxd4 7. Qxd4 Qf6 8. e5 Qb6 9. Qxb6 axb6 10. Nc3 Ne7 11. O-O-O O-O 12. Bc4",
    ),
    (
        "Scotch Extended #43 - Poisoned Pawn Gambit",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qe6 7. Bc4 Qg6 8. Nc3 Qxg2 9. Bd5 Qg6 10. Bd2",
    ),
    (
        "Scotch Extended #44 - Center Scoop",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 O-O 9. Bh6 g6 10. Bxf8 Qxf8 11. O-O d6 12. Qf3 dxe5 13. Nc3 Nf4 14. Qxc6",
    ),
    (
        "Scotch Extended #45 - Bishop Skewer",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Nf6 6. e5 Qe7 7. Be3 Ng8 8. Nc3 d6 9. Nd5 Qd7 10. exd6 Qxd6 11. Bf4 Qe6+ 12. Be2",
    ),
    (
        "Scotch Extended #46 - F7 Assault",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qe6 7. Bc4 Qb6 8. Qf4",
    ),
    (
        "Scotch Extended #47 - Knight Net",
        "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Nb4 5. Be3 Nf6 6. h3 Nxe4 7. c3 Nxd5 8. Qxd5",
    ),
    (
        "Scotch Extended #48 - Castle Lock",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 g6 9. Bh6 d6 10. Qa4 Bd7 11. O-O Nb6 12. Qf4",
    ),
    ("Scotch Extended #49 - Center Seize", "1. e4 e5 2. Nf3 Nc6 3. d4 d6 4. d5 Nce7 5. c4 Nf6 6. Nc3"),
    (
        "Scotch Extended #50 - Center Heist",
        "1. e4 e5 2. Nf3 Nc6 3. d4 d5 4. Nxe5 Nxe5 5. dxe5",
    ),
    (
        "Scotch Extended #51 - Castle Crusher",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 g6 9. Bh6 d6 10. Qa4 Bd7 11. O-O dxe5 12. Bg7 Rg8 13. Bxe5 Qg5 14. Re1",
    ),
    (
        "Scotch Extended #52 - Unnamed Line",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 O-O 9. Bh6 g6 10. Bxf8 Qxf8 11. O-O d6 12. Qf3 dxe5 13. Nc3 Be6 14. Bc4",
    ),
    (
        "Scotch Extended #53 - Rook Heist",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Nd5 8. Qg4 O-O 9. Bh6 g6 10. Bxf8 Qxf8 11. O-O d6 12. Qf3 dxe5 13. Nc3 Nxc3 14. Qxc6",
    ),
    (
        "Scotch Extended #54 - Castle Denied",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 dxc6 6. Qxd8+ Kxd8 7. f3",
    ),
    ("Scotch Extended #55 - Center Snatch", "1. e4 e5 2. Nf3 Nc6 3. d4 Nxd4 4. Nxe5"),
    (
        "Scotch Extended #56 - Structure Break",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O Ne5 9. Be2 d5 10. f4 Nc4 11. Bxc4 dxc4 12. Nd2",
    ),
    (
        "Scotch Extended #57 - Center Clamp",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. e5 Qb6 7. Be3 Qxd4 8. Bxd4",
    ),
    (
        "Scotch Extended #58 - F-Pawn Strike",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O Ne5 9. Be2 d6 10. f4",
    ),
    (
        "Scotch Extended #59 - Gambit Trap",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 Ne5 8. Be2 d5 9. O-O dxe4 10. Nb5 Bd6 11. Bc5 O-O 12. Nxd6 cxd6 13. Qxd6 Qxd6 14. Bxd6",
    ),
    (
        "Scotch Extended #60 - Scotch Standard",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 d6 8. O-O",
    ),
    (
        "Scotch Extended #61 - Knight Hop",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Qf6 5. Nb5 Bc5 6. Qe2 Bb6 7. N1c3 Nge7 8. Be3",
    ),
    (
        "Scotch Extended #62 - Kingside Storm",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O d6 9. Nxc6 Nxc6 10. Bxc5 dxc5 11. f4 Be6 12. e5 Qe7 13. Bxe6 Qxe6 14. Nd2",
    ),
    (
        "Scotch Extended #63 - Relentless Attack",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Bc5 5. Be3 Qf6 6. c3 Nge7 7. Bc4 O-O 8. O-O d6 9. Nxc6 Nxc6 10. Bxc5 dxc5 11. f4 Be6 12. e5 Qg6 13. Bd3 Bf5 14. Bxf5 Qxf5 15. Nd2",
    ),
    (
        "Scotch Extended #64 - Solid Schmidt",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 d5 7. exd5 cxd5 8. O-O Be7 9. c4",
    ),
    (
        "Scotch Extended #65 - H7 Crush",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Qe7 8. O-O Nd5 9. Nd2 O-O 10. Ne4 Bb6 11. c4 Nb4 12. Nf6+ Kh8 13. Qh5",
    ),
    (
        "Scotch Extended #66 - H File Hunt",
        "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nf6 5. Nxc6 bxc6 6. Bd3 Bc5 7. e5 Qe7 8. O-O Nd5 9. Nd2 O-O 10. Ne4 Bb6 11. c4 Nb4 12. Nf6+ gxf6 13. Bxh7+ Kxh7 14. Qh5+ Kg7 15. Bh6+",
    ),
]


def main() -> None:
    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    if not SCOTCH_EXTENDED_LINES:
        raise SystemExit(
            "No lines configured. Paste (name, pgn) pairs into SCOTCH_EXTENDED_LINES in "
            "scripts/add_scotch_extended.py."
        )

    added = 0
    skipped = 0
    failed = 0

    with db.connect() as conn:
        for name, pgn in SCOTCH_EXTENDED_LINES:
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

