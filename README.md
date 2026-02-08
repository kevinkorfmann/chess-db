# Chess DB

Store chess openings and **train them from memory** -- with **Stockfish evaluation** so you don't learn bad lines.

---

## What it does

| Feature | Description |
|---------|-------------|
| **Store** | SAN move sequences, validated on insert |
| **Evaluate** | Stockfish (UCI) scores every position -- skip bad lines |
| **Learn** | Study sheets, decision trees, spaced-repetition quizzes |
| **Browse** | Interactive web board with move-by-move navigation |

---

## Quickstart

```bash
uv sync
uv run chess-db init
```

### Load openings

Two Stockfish-generated repertoires ship in `scripts/`:

| Opening | Lines | Variants |
|---------|------:|----------|
| **Italian Game** | 300 | Anti-Italian, Giuoco Piano, Hungarian, Semi-Italian, Two Knights |
| **Scotch Game** | 300 | Classical, Counter, Gambit Decline, Main Line, Queen Attack, Schmidt, Steinitz |

```bash
uv run python scripts/add_italian.py
uv run python scripts/add_scotch.py
```

Each line is 10 moves deep, tagged by Stockfish evaluation:
`Winning` / `Clear Edge` / `Slight Edge` / `Equal` / `Tough` / `Difficult`

### Study & train

```bash
# study sheet (chunk=2 => one White + one Black move per line)
uv run chess-db learn --prefix "Italian" --limit 10 --chunk 2 --depth 10

# decision tree
uv run chess-db tree --prefix "Scotch Game" --levels 3

# quiz
uv run chess-db quiz --prefix "Italian" --tokens 8

# spaced-repetition review
uv run chess-db due --prefix "Scotch Game"
```

![Terminal demo: learn (didactic)](docs/learn-didactic-demo.svg)

[View SVG directly](docs/learn-didactic-demo.svg) -- some editors block SVG images in markdown preview.

---

## Web interface

Browse openings with an interactive chess board:

```bash
# kill any existing server on port 8080
lsof -ti:8080 | xargs kill

uv run chess-db serve
```

Then open http://127.0.0.1:8080

![Web interface: animated board](docs/web-board-demo.svg)

[View SVG directly](docs/web-board-demo.svg)

**Board features:**
- File/rank coordinates with flip support
- Click an opening in the sidebar to load it
- Step through moves: **Prev** / **Next** or **First** / **Last**
- **Flip** to view from Black's perspective
- **Keyboard**: `Left`/`Right` arrows, `Home`/`End`, `F` flip, `J`/`K` prev/next opening, `Ctrl+K` search
- **Filter** by name, then **Refresh** after loading new openings
- **Stockfish eval** (optional): toggle to show evaluation after each move

---

## Setup

### Prerequisites

- **Python** 3.11+
- **Stockfish** engine binary (recommended)

```bash
# macOS
brew install stockfish
```

### Install

```bash
uv sync
uv run chess-db --help
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHESS_DB_PATH` | `./data/chess_db.sqlite3` | Database file |
| `STOCKFISH_PATH` | `stockfish` (on `PATH`) | Stockfish binary |

```bash
export STOCKFISH_PATH="/opt/homebrew/bin/stockfish"
export CHESS_DB_PATH="data/chess_db.sqlite3"
```

---

## CLI reference

### Store & evaluate

```bash
uv run chess-db add "Italian Game" --moves "e4 e5 Nf3 Nc6 Bc4"
uv run chess-db list
uv run chess-db eval "Italian Game" --depth 14
```

![Terminal demo: eval](docs/eval-demo.svg)

[View SVG directly](docs/eval-demo.svg)

### Learn workflow

1. **Decision tree** -- see what branches from the shared start:

```bash
uv run chess-db tree --prefix "Scotch Game" --levels 3
```

2. **Study sheet** -- lines split into chunks for rehearsal:

```bash
uv run chess-db learn --prefix "Scotch Game" --limit 10 --chunk 2
```

3. **Quiz** -- opening name -> type the first N SAN tokens:

```bash
uv run chess-db quiz --prefix "Scotch Game" --tokens 8
```

4. **Daily review** -- spaced repetition:

```bash
uv run chess-db due --prefix "Scotch Game"
```

### Stockfish eval in learn

`learn` will (if Stockfish is available) print the **final eval** and highlight the **critical move** (largest eval swing):

```bash
# with eval
uv run chess-db learn --prefix "Italian" --limit 10 --chunk 2 --depth 10 --swing-cp 120

# instant (skip eval)
uv run chess-db learn --prefix "Italian" --limit 10 --chunk 2 --no-eval
```

![Terminal demo: learn + eval](docs/learn-demo.svg)

[View SVG directly](docs/learn-demo.svg)

### Notes / mnemonics

Attach a 1-line plan visible during `show` and after quizzes:

```bash
uv run chess-db note "Scotch Game - Main Line" \
  --text "Default: ...Bc5 -> Be3, c3, Bc4, O-O. Development + central pressure."
uv run chess-db show "Scotch Game - Main Line"
```

---

## Import your own lines

Import from a TSV file (one line per opening as `<name><TAB><pgn moves>`):

```bash
uv run python scripts/import_openings_tsv.py path/to/openings.tsv
```

---

## How lines are generated

Lines are created by playing random Stockfish games from a fixed opening position.
At each move Stockfish returns the top-4 candidates and one is picked at random
(weighted toward the best move). 300 games per opening, 10 moves deep.

See [`scripts/GENERATION_STRATEGY.md`](scripts/GENERATION_STRATEGY.md) for full details.
