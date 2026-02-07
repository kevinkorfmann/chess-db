## chess-db
Store chess openings and **train them from memory**—with **Stockfish evaluation** so you don’t learn bad lines.

### What this is for
- **Store** openings as SAN move sequences (validated on insert)
- **Evaluate** the resulting positions with Stockfish (UCI)
- **Learn** openings using a built-in trainer:
  - a branching **tree** view (decision points)
  - a chunked **study sheet**
  - spaced-repetition **quizzes** and “what’s due today”

### Setup
#### Prereqs
- **Python**: 3.11+
- **Stockfish engine binary** (recommended)

macOS (Homebrew):

```bash
brew install stockfish
```

#### Install (uv)
```bash
uv sync
uv run chess-db --help
```

### Configuration
- **Database path**
  - default: `./data/chess_db.sqlite3`
  - override: `CHESS_DB_PATH`
- **Stockfish binary**
  - default: `stockfish` on `PATH`
  - override: `STOCKFISH_PATH`

Example:

```bash
export STOCKFISH_PATH="/opt/homebrew/bin/stockfish"
export CHESS_DB_PATH="data/chess_db.sqlite3"
```

### Quickstart (store + evaluate)
```bash
uv run chess-db init
uv run chess-db add "Italian Game" --moves "e4 e5 Nf3 Nc6 Bc4"
uv run chess-db list
uv run chess-db eval "Italian Game" --depth 14
```

![Terminal demo: eval](docs/eval-demo.svg)

### Learn the Scotch (recommended workflow)
1) **See the decision tree** (what branches after the shared start):

```bash
uv run chess-db tree --prefix "Scotch Game" --levels 3
```

2) **Study sheet** (lines split into chunks you can rehearse):

```bash
uv run chess-db learn --prefix "Scotch Game" --limit 10 --chunk 8
```

![Terminal demo: learn](docs/learn-demo.svg)

3) **Quiz** (opening name → type the first N SAN tokens):

```bash
uv run chess-db quiz --prefix "Scotch Game" --tokens 8
```

4) **Daily review** (spaced repetition):

```bash
uv run chess-db due --prefix "Scotch Game"
```

### Learn output: Stockfish eval + critical moment
By default, `learn` will (if Stockfish is available):
- Print the **final eval** (White POV)
- Highlight the **critical move** (largest eval swing)

Tune it:

```bash
uv run chess-db learn --prefix "Scotch Game" --limit 10 --chunk 8 --depth 10 --swing-cp 120
```

Make it instant:

```bash
uv run chess-db learn --prefix "Scotch Game" --limit 10 --chunk 8 --no-eval
```

### Notes / mnemonics (for “why”)
Attach a 1-line plan you’ll see during `show` and after quizzes:

```bash
uv run chess-db note "Scotch Game - Scotch Standard" --text "Default: ...Bc5 -> Be3, c3, Bc4, O-O. Development + central pressure."
uv run chess-db show "Scotch Game - Scotch Standard"
```

### Import scripts
Load the curated Scotch set into your local DB:

```bash
uv run python scripts/add_scotch_game.py
```
