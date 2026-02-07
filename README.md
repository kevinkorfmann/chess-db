 ## chess-db
 Save chess openings and evaluate them with Stockfish so you don’t learn nonsense lines.
 
 ### Prereqs
 - **Python**: 3.11+
 - **Stockfish engine binary** (UCI)
   - macOS (Homebrew):
 
 ```bash
 brew install stockfish
 ```
 
 ### Setup (uv)
 From the repo root:
 
 ```bash
 uv sync
 ```
 
 Run the CLI:
 
 ```bash
 uv run chess-db --help
 ```
 
 ### Stockfish path
 By default the app looks for `stockfish` on your `PATH`.
 
 If needed, set:
 - **`STOCKFISH_PATH`**: full path to the Stockfish binary
 
 Example:
 
 ```bash
 export STOCKFISH_PATH="/opt/homebrew/bin/stockfish"
 ```
 
 ### Where data is stored
 - Default DB: `./data/chess_db.sqlite3`
 - Override with `CHESS_DB_PATH`
 
 ### Quick start
 Add an opening by name + moves (SAN, space-separated):
 
 ```bash
 uv run chess-db add "Italian Game" --moves "e4 e5 Nf3 Nc6 Bc4"
 ```
 
 List:
 
 ```bash
 uv run chess-db list
 ```
 
 Evaluate the final position of an opening:
 
 ```bash
 uv run chess-db eval "Italian Game" --depth 14
 ```
 
 Evaluate all openings and store results:
 
 ```bash
 uv run chess-db eval-all --depth 14
 ```

### Learn / memorize (spaced repetition)
Create daily review cards automatically (it seeds on first use) and see what's due:

```bash
uv run chess-db due --prefix "Scotch Game"
```

Quiz yourself (opening name → type first N SAN tokens). Use `--dry-run` to see answers.

```bash
uv run chess-db quiz --prefix "Scotch Game" --tokens 8
```

Add a mnemonic / plan to show during `show` and after a quiz:

```bash
uv run chess-db note "Scotch Game - Scotch Standard" --text "Default: ...Bc5 -> Be3, c3, Bc4, O-O. Play for development + central pressure."
```
