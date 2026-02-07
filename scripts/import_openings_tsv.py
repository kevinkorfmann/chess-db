from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

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


def iter_rows(tsv_path: Path) -> list[tuple[str, str]]:
    """
    TSV format:
      - Blank lines and lines starting with # are ignored.
      - Each non-empty line is either:
          <name>\\t<pgn-moves>
        or:
          <pgn-moves>    (name will be auto-generated)
    """
    rows: list[tuple[str, str]] = []
    auto_i = 1
    for raw in tsv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if "\t" in line:
            name, pgn = line.split("\t", 1)
            name = name.strip()
            pgn = pgn.strip()
            if not name:
                name = f"Imported line {auto_i}"
                auto_i += 1
            rows.append((name, pgn))
        else:
            rows.append((f"Imported line {auto_i}", line))
            auto_i += 1
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import openings from a TSV file: <name>\\t<PGN moves> per line."
    )
    ap.add_argument(
        "tsv_path",
        type=Path,
        help="Path to TSV file (UTF-8). Each line: <name>\\t<PGN moves>.",
    )
    ap.add_argument(
        "--name-prefix",
        default="",
        help="Optional prefix added to every imported opening name (e.g. 'Scotch Game - ').",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate SAN, but do not insert into the database.",
    )
    args = ap.parse_args()

    settings = get_settings()
    db = Db(settings.db_path)
    init_db(db)

    rows = iter_rows(args.tsv_path)
    if not rows:
        raise SystemExit(f"No importable lines found in {args.tsv_path}")

    added = 0
    skipped = 0
    failed = 0

    with db.connect() as conn:
        for name, pgn in rows:
            full_name = f"{args.name_prefix}{name}".strip()
            moves_san = sanitize_pgn_moves(pgn)

            try:
                if args.dry_run:
                    # Validate only (same validation as add_opening).
                    from chess_db.openings import opening_final_board

                    opening_final_board(moves_san)
                else:
                    add_opening(conn, name=full_name, moves_san=moves_san)
            except sqlite3.IntegrityError:
                skipped += 1
                print(f"SKIP (already exists): {full_name}")
            except Exception as e:  # noqa: BLE001 - CLI-like script
                failed += 1
                print(f"FAIL: {full_name}: {e}")
            else:
                added += 1
                msg = "OK (validated):" if args.dry_run else "ADDED:"
                print(f"{msg} {full_name}")

    print()
    print(f"Done. added={added} skipped={skipped} failed={failed} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()

