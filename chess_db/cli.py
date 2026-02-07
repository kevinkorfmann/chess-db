from __future__ import annotations

import contextlib
import math

import chess
import chess.engine
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from .config import get_settings
from .db import Db, init_db
from .engine import evaluate_position, resolve_stockfish_path
from .evals import latest_evaluation, store_evaluation
from .openings import add_opening, get_opening_by_name, list_openings, opening_final_board
from .study import (
    apply_grade,
    check_typed_moves,
    ensure_cards_for_prefix,
    get_notes,
    pick_quiz_openings,
    set_notes,
)
from .teach import Line, branch_by_token, longest_common_prefix


app = typer.Typer(add_completion=False, help="Store chess openings and evaluate them with Stockfish.")
console = Console()


def _db() -> Db:
    s = get_settings()
    return Db(s.db_path)


@app.command()
def init() -> None:
    """Initialize the SQLite database."""
    db = _db()
    init_db(db)
    console.print(f"[green]Initialized[/green] {db.path}")


@app.command()
def add(name: str, moves: str = typer.Option(..., "--moves", help="SAN moves, space-separated")) -> None:
    """Add an opening (validates SAN moves before saving)."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        opening = add_opening(conn, name=name, moves_san=moves)
    console.print(f"[green]Added[/green] {opening.name}")


@app.command("list")
def list_cmd() -> None:
    """List stored openings."""
    db = _db()
    init_db(db)
    with db.connect() as conn:
        openings = list_openings(conn)

    table = Table(title="Openings")
    table.add_column("Name", style="bold")
    table.add_column("Moves (SAN)")
    for o in openings:
        table.add_row(o.name, o.moves_san)

    console.print(table)


def _format_score(score_cp: int | None, mate_in: int | None) -> str:
    if mate_in is not None:
        return f"M{mate_in}"
    if score_cp is None:
        return "?"
    return f"{score_cp / 100:.2f}"


def _format_cp(cp: int) -> str:
    # Always show sign, in pawns.
    return f"{cp / 100:+.2f}"


def _analyse_white_pov(engine: chess.engine.SimpleEngine, board: chess.Board, *, depth: int) -> tuple[int, str]:
    """
    Returns (numeric_value, display_string) from White's POV.
    numeric_value is centipawns, or +/-100000 for mate.
    """
    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)
    if isinstance(info, list):
        # python-chess may return a 1-element list when multipv is set.
        info = info[0] if info else {}
    score = info.get("score")
    if score is None:
        return 0, "?"

    pov = score.pov(chess.WHITE)
    mate = pov.mate()
    if mate is not None:
        numeric = 100000 if mate > 0 else -100000
        return numeric, f"M{mate}"

    cp = pov.score(mate_score=100000)
    if cp is None:
        return 0, "?"
    cp_i = int(cp)
    return cp_i, _format_cp(cp_i)


def _chunk_display_tokens(tokens: list[str], *, chunk: int) -> list[str]:
    out: list[str] = []
    for i in range(0, len(tokens), chunk):
        out.append(" ".join(tokens[i : i + chunk]))
    return out


@app.command()
def eval(
    name: str,
    depth: int = typer.Option(14, "--depth", min=1, max=99),
) -> None:
    """Evaluate one opening and store the result."""
    settings = get_settings()
    stockfish_path = resolve_stockfish_path(settings.stockfish_path)

    db = Db(settings.db_path)
    init_db(db)

    with db.connect() as conn:
        opening = get_opening_by_name(conn, name)
        if opening is None:
            raise typer.BadParameter(f"No opening named '{name}'.")

        board = opening_final_board(opening.moves_san)
        result = evaluate_position(board, depth=depth, stockfish_path=stockfish_path)
        stored = store_evaluation(conn, opening_id=opening.id, result=result)

    console.print(
        f"[bold]{opening.name}[/bold] @ depth {stored.depth}: "
        f"[cyan]{_format_score(stored.score_cp, stored.mate_in)}[/cyan]"
    )
    if stored.bestmove_uci:
        console.print(f"bestmove: {stored.bestmove_uci}")
    if stored.pv_uci:
        console.print(f"pv: {stored.pv_uci}")


@app.command("eval-all")
def eval_all(
    depth: int = typer.Option(14, "--depth", min=1, max=99),
) -> None:
    """Evaluate all openings and store results."""
    settings = get_settings()
    stockfish_path = resolve_stockfish_path(settings.stockfish_path)

    db = Db(settings.db_path)
    init_db(db)

    with db.connect() as conn:
        openings = list_openings(conn)
        if not openings:
            console.print("[yellow]No openings stored yet.[/yellow]")
            raise typer.Exit(code=0)

        table = Table(title=f"Evaluations (depth {depth})")
        table.add_column("Opening", style="bold")
        table.add_column("Score", style="cyan")
        table.add_column("Bestmove")

        for o in openings:
            board = opening_final_board(o.moves_san)
            result = evaluate_position(board, depth=depth, stockfish_path=stockfish_path)
            stored = store_evaluation(conn, opening_id=o.id, result=result)
            table.add_row(
                o.name,
                _format_score(stored.score_cp, stored.mate_in),
                stored.bestmove_uci or "",
            )

    console.print(table)


@app.command()
def show(name: str) -> None:
    """Show an opening and its latest stored evaluation (if any)."""
    db = _db()
    init_db(db)

    with db.connect() as conn:
        opening = get_opening_by_name(conn, name)
        if opening is None:
            raise typer.BadParameter(f"No opening named '{name}'.")
        latest = latest_evaluation(conn, opening.id)
        notes = get_notes(conn, opening.id)

    console.print(f"[bold]{opening.name}[/bold]")
    console.print(opening.moves_san)
    board = opening_final_board(opening.moves_san)
    console.print(f"FEN: {board.fen()}")
    if notes:
        console.print("\n[bold]Notes[/bold]")
        console.print(notes)
    if latest:
        console.print(
            f"Latest eval @ depth {latest.depth}: "
            f"[cyan]{_format_score(latest.score_cp, latest.mate_in)}[/cyan]"
        )


@app.command()
def note(
    name: str,
    text: str = typer.Option(..., "--text", help="Notes/mnemonic for this opening"),
) -> None:
    """Attach notes (mnemonics, triggers, plans) to an opening."""
    db = _db()
    init_db(db)

    with db.connect() as conn:
        opening = get_opening_by_name(conn, name)
        if opening is None:
            raise typer.BadParameter(f"No opening named '{name}'.")
        set_notes(conn, opening.id, text.strip())

    console.print(f"[green]Saved notes[/green] for [bold]{opening.name}[/bold]")


@app.command()
def due(
    prefix: str = typer.Option("Scotch Game", "--prefix", help="Filter by opening name prefix"),
    limit: int = typer.Option(20, "--limit", min=1, max=200),
) -> None:
    """Show what you should review today (spaced repetition)."""
    import datetime as _dt

    today = _dt.date.today().isoformat()
    db = _db()
    init_db(db)

    with db.connect() as conn:
        ensure_cards_for_prefix(conn, prefix=prefix)
        rows = pick_quiz_openings(conn, prefix=prefix, limit=limit)

    due_rows = [r for r in rows if r.due_date <= today]
    if not due_rows:
        console.print(f"[green]Nothing due today[/green] for prefix '{prefix}'.")
        return

    table = Table(title=f"Due today (prefix: {prefix})")
    table.add_column("Opening", style="bold")
    table.add_column("Due")
    for r in due_rows:
        table.add_row(r.name, r.due_date)
    console.print(table)


@app.command()
def quiz(
    prefix: str = typer.Option("Scotch Game", "--prefix", help="Filter by opening name prefix"),
    limit: int = typer.Option(10, "--limit", min=1, max=200),
    tokens: int = typer.Option(10, "--tokens", min=2, max=60, help="How many SAN tokens to recall"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show answers without prompting or scheduling"),
) -> None:
    """
    Quiz yourself: given an opening name, type the first N SAN tokens.
    Then rate your recall (0..5) to schedule the next review.
    """
    db = _db()
    init_db(db)

    with db.connect() as conn:
        created = ensure_cards_for_prefix(conn, prefix=prefix)
        openings = pick_quiz_openings(conn, prefix=prefix, limit=limit)

    if created:
        console.print(f"[dim]Created {created} study cards.[/dim]")

    if not openings:
        console.print(f"[yellow]No openings found[/yellow] for prefix '{prefix}'.")
        return

    for o in openings:
        target = " ".join(o.moves_san.split()[:tokens])
        console.print(f"\n[bold]{o.name}[/bold]  [dim](due {o.due_date})[/dim]")

        if dry_run:
            console.print(f"[cyan]Answer[/cyan]: {target}")
            continue

        typed = typer.prompt(f"Type first {tokens} moves (SAN tokens)", default="", show_default=False)
        check = check_typed_moves(moves_san=o.moves_san, typed=typed, tokens=tokens)

        if check.fully_correct:
            console.print(f"[green]Correct[/green] ({check.correct_tokens}/{check.target_tokens})")
        else:
            console.print(f"[yellow]Partial[/yellow] ({check.correct_tokens}/{check.target_tokens})")
            console.print(f"[cyan]Answer[/cyan]: {' '.join(check.target)}")

        grade_raw = typer.prompt("Grade your recall (0..5)", default="4")
        try:
            grade_i = int(str(grade_raw).strip())
        except ValueError as e:
            raise typer.BadParameter("Grade must be an integer 0..5") from e

        with db.connect() as conn:
            apply_grade(
                conn,
                opening_id=o.id,
                grade=grade_i,
                prompt_mode="name_to_moves",
                prompt=o.name,
                typed_moves=typed,
                correct_tokens=check.correct_tokens,
                target_tokens=check.target_tokens,
            )
            notes = get_notes(conn, o.id)

        if notes:
            console.print("[dim]Note:[/dim] " + notes)


@app.command()
def learn(
    prefix: str = typer.Option("Scotch Game", "--prefix", help="Filter by opening name prefix"),
    limit: int = typer.Option(20, "--limit", min=1, max=200),
    chunk: int = typer.Option(8, "--chunk", min=4, max=20, help="Tokens per chunk to memorize"),
    eval: bool = typer.Option(True, "--eval/--no-eval", help="Show Stockfish eval + critical swing"),
    depth: int = typer.Option(10, "--depth", min=1, max=30, help="Stockfish depth for learn evals"),
    swing_cp: int = typer.Option(
        120, "--swing-cp", min=10, max=2000, help="Highlight swings >= this (centipawns)"
    ),
) -> None:
    """
    Print a study sheet: each opening split into small chunks you can rehearse.
    Use this BEFORE quizzing.
    """
    db = _db()
    init_db(db)

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT name, moves_san FROM openings WHERE name LIKE ? ORDER BY name ASC LIMIT ?",
            (f"{prefix}%", limit),
        ).fetchall()

    if not rows:
        console.print(f"[yellow]No openings found[/yellow] for prefix '{prefix}'.")
        return

    engine: chess.engine.SimpleEngine | None = None
    if eval:
        settings = get_settings()
        try:
            stockfish_path = resolve_stockfish_path(settings.stockfish_path)
            engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        except FileNotFoundError as e:
            console.print(f"[yellow]Stockfish not available[/yellow]: {e}")
            console.print("[dim]Continuing without eval. Install Stockfish or set STOCKFISH_PATH.[/dim]")
            engine = None

    try:
        for r in rows:
            name = r["name"]
            moves_san = r["moves_san"]
            toks = [t for t in moves_san.split() if t.strip()]

            critical_idx: int | None = None
            final_eval_str: str | None = None
            critical_msg: str | None = None

            if engine is not None:
                board = chess.Board()
                numeric_prev, disp_prev = _analyse_white_pov(engine, board, depth=depth)
                best_abs = -math.inf
                best_idx: int | None = None
                best_before = disp_prev
                best_after = disp_prev
                best_delta = 0

                for idx, san in enumerate(toks):
                    move = board.parse_san(san)
                    board.push(move)
                    numeric_now, disp_now = _analyse_white_pov(engine, board, depth=depth)
                    delta = numeric_now - numeric_prev
                    abs_delta = abs(delta)
                    if abs_delta > best_abs:
                        best_abs = abs_delta
                        best_idx = idx
                        best_before = disp_prev
                        best_after = disp_now
                        best_delta = delta

                    numeric_prev, disp_prev = numeric_now, disp_now

                final_eval_str = disp_prev
                if best_idx is not None:
                    critical_idx = best_idx
                    ply = critical_idx + 1
                    side = "White" if (critical_idx % 2) == 0 else "Black"
                    delta_pawns = abs(best_delta) / 100.0
                    is_sudden = best_abs >= swing_cp
                    tag = "[bold red]CRITICAL[/bold red]" if is_sudden else "[yellow]Largest swing[/yellow]"
                    critical_msg = (
                        f"{tag}: ply {ply} ({side}) "
                        f"[bold]{escape(toks[critical_idx])}[/bold]  "
                        f"{best_before} → {best_after}  [dim](Δ {delta_pawns:.2f})[/dim]"
                    )

            display_tokens: list[str] = []
            for i, t in enumerate(toks):
                tok = escape(t)
                if critical_idx is not None and i == critical_idx:
                    tok = f"[bold reverse red]{tok}[/bold reverse red]"
                else:
                    tok = f"[white]{tok}[/white]"
                display_tokens.append(tok)

            console.print(f"\n[bold]{name}[/bold]")
            for i, ch in enumerate(_chunk_display_tokens(display_tokens, chunk=chunk), start=1):
                console.print(f"[dim]{i:02d}[/dim]  {ch}")

            if engine is not None and final_eval_str is not None:
                console.print(f"[dim]Final eval (Stockfish d{depth}, White POV)[/dim]: [cyan]{final_eval_str}[/cyan]")
            if critical_msg:
                console.print(critical_msg)
    finally:
        with contextlib.suppress(Exception):
            if engine is not None:
                engine.quit()


@app.command()
def tree(
    prefix: str = typer.Option("Scotch Game", "--prefix", help="Filter by opening name prefix"),
    limit: int = typer.Option(200, "--limit", min=1, max=1000),
    levels: int = typer.Option(3, "--levels", min=1, max=6, help="How many branching levels to show"),
) -> None:
    """
    Show the branching structure: common prefix, then what the next move usually is.
    This helps you memorize as a decision tree (if they play X, respond with Y).
    """
    db = _db()
    init_db(db)

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT name, moves_san FROM openings WHERE name LIKE ? ORDER BY name ASC LIMIT ?",
            (f"{prefix}%", limit),
        ).fetchall()

    lines = [Line(name=r["name"], moves_san=r["moves_san"]) for r in rows]
    if not lines:
        console.print(f"[yellow]No openings found[/yellow] for prefix '{prefix}'.")
        return

    seqs = [ln.tokens for ln in lines]
    lcp = longest_common_prefix(seqs)
    console.print(f"[bold]Common start[/bold] ({len(lcp)} tokens)")
    console.print(" ".join(lcp) if lcp else "[dim](none)[/dim]")

    def _recurse(sub: list[Line], idx: int, depth: int, indent: str) -> None:
        if depth <= 0:
            return
        branches = branch_by_token(sub, idx)
        for br in branches:
            ex = ", ".join(br.example_names)
            console.print(f"{indent}[cyan]{br.token}[/cyan]  [dim]({br.count})[/dim]  {ex}")
            if br.token != "<END>" and depth > 1 and br.count > 1:
                nxt = [ln for ln in sub if (ln.tokens[idx] if idx < len(ln.tokens) else "<END>") == br.token]
                _recurse(nxt, idx + 1, depth - 1, indent + "  ")

    console.print("\n[bold]Next branches[/bold]")
    _recurse(lines, len(lcp), levels, indent="- ")


if __name__ == "__main__":
    app()
