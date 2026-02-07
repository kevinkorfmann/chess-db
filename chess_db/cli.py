from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .db import Db, init_db
from .engine import evaluate_position, resolve_stockfish_path
from .evals import latest_evaluation, store_evaluation
from .openings import add_opening, get_opening_by_name, list_openings, opening_final_board


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

    console.print(f"[bold]{opening.name}[/bold]")
    console.print(opening.moves_san)
    board = opening_final_board(opening.moves_san)
    console.print(f"FEN: {board.fen()}")
    if latest:
        console.print(
            f"Latest eval @ depth {latest.depth}: "
            f"[cyan]{_format_score(latest.score_cp, latest.mate_in)}[/cyan]"
        )


if __name__ == "__main__":
    app()
