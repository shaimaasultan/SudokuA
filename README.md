# 🧩 Sudoku Solver

A high-performance, multi-size Sudoku solver with a real-time Tkinter GUI. Supports **9×9**, **16×16**, **25×25**, **36×36**, and **49×49** puzzles using advanced constraint propagation and intelligent backtracking search.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## ✨ Features

- **Multi-size support** — Solve puzzles from standard 9×9 up to massive 49×49 grids
- **Interactive GUI** — Real-time visualization of the solving process with color-coded feedback
- **Advanced constraint propagation** — Naked singles, hidden singles, pointing pairs, naked pairs/triples, hidden pairs, and simple coloring (X-chains)
- **Intelligent search** — MRV (Minimum Remaining Values) heuristic with LCV (Least Constraining Value) digit ordering
- **Stagnation detection** — Automatic restarts with decay when search gets stuck
- **Random puzzle generation** — Built-in generator with adjustable clue density (10%–90%)
- **Bitmask engine** — O(1) candidate lookups using bitwise operations over NumPy arrays

---

## 📸 How It Works

The solver follows a multi-phase pipeline:

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────┐
│  Parse Grid │────▶│ Build Bitmask    │────▶│   Constraint     │────▶│  Search  │
│  (N×N)      │     │ Candidate Layers │     │   Propagation    │     │  (MRV +  │
│             │     │                  │     │  (6 techniques)  │     │   LCV)   │
└─────────────┘     └──────────────────┘     └──────────────────┘     └──────────┘
                                                                           │
                                                                    ┌──────┴───────┐
                                                                    │  Stagnation  │
                                                                    │  Detection & │
                                                                    │  Restart     │
                                                                    └──────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **NumPy**

```bash
pip install numpy
```

### Run the GUI

```bash
# From the sudoku_solver directory
python -m sudoku.gui_main
```

Or use the provided batch file (Windows):

```bash
run_sudoku.bat
```

### Run from CLI

```bash
python -m sudoku.main
```

---

## 🖥️ GUI Controls

| Control | Description |
|---------|-------------|
| **Size buttons** (9, 16, 25, 36, 49) | Select puzzle grid size |
| **Density slider** (10%–90%) | Control clue density — lower = harder |
| **NEW GRID** | Generate a new random puzzle |
| **SOLVE PUZZLE** | Start solving with real-time visualization |
| **STOP** | Gracefully interrupt the solver |

### Visual Feedback

| Color | Meaning |
|-------|---------|
| Gray background | Original clue (given) |
| Digit color + white flash | Forced move (propagation) |
| Gold border + italic | Guess (branching) |
| Red border flash | Contradiction detected |
| Cyan flash | Branch cell selected |
| Magenta flash | Cell fallback |

---

## 🏗️ Project Structure

```
sudoku_solver/
├── sudoku/
│   ├── main.py                  # CLI entry point
│   ├── gui_main.py              # Tkinter GUI application
│   ├── solver.py                # High-level solver orchestrator
│   ├── model/
│   │   ├── grid.py              # N×N grid (NumPy-backed)
│   │   └── state_stack.py       # LIFO state stack for backtracking
│   ├── layers/
│   │   └── layer_manager.py     # Bitmask-based candidate tracking
│   ├── propagation/
│   │   └── propagator.py        # Constraint propagation engine
│   ├── branching/
│   │   └── branching_engine.py  # MRV + LCV search with restarts
│   ├── examples/
│   │   └── puzzles.py           # Random puzzle generator
│   └── visual/
│       ├── tk_visual.py         # Tkinter canvas renderer
│       ├── visual_hooks.py      # Abstract visualization interface
│       ├── colors.py            # HSV-based digit color generation
│       └── symbols.py           # Digit-to-symbol mapping (1-9, A-Z, a-z)
├── test_all.py                  # Multi-seed test suite (9×9, 16×16, 25×25)
├── test_25x25.py                # 25×25 performance analysis
├── verify_solver.py             # Solver verification (36×36)
└── analysis.txt                 # Performance analysis notes
```

---

## 🔬 Algorithms & Techniques

### Constraint Propagation

The propagator applies techniques in order of increasing complexity:

1. **Full House** — A unit (row/col/box) with exactly 1 empty cell
2. **Naked Singles** — A cell with exactly 1 remaining candidate
3. **Hidden Singles** — A digit that can only go in 1 cell within a unit
4. **Pointing Pairs** — Candidates confined to a single row/col within a box
5. **Naked Pairs / Triples** — 2–3 cells sharing the same 2–3 candidates
6. **Hidden Pairs** — 2 digits appearing in exactly 2 cells of a unit
7. **Simple Coloring** — X-chain analysis using conjugate pairs

### Search Strategy

When propagation alone can't solve the puzzle, the branching engine uses:

- **MRV (Minimum Remaining Values)** — Pick the cell with the fewest candidates
- **Degree heuristic** — Break MRV ties by choosing the most constrained cell
- **Heat-based tie-breaking** — Prioritize cells that have caused fewer failures
- **LCV (Least Constraining Value)** — Try digits that eliminate the fewest candidates from peers
- **Stagnation detection** — Automatically restart search with decayed failure counts if stuck

### Bitmask Candidate Tracking

Candidates are tracked using 64-bit integer bitmasks per row, column, and box. A cell's allowed values are computed in O(1):

```
allowed = full_mask & ~(row_mask | col_mask | box_mask | manual_mask)
```

---

## 🧪 Running Tests

```bash
# Run multi-seed tests across sizes
python test_all.py

# Run 25×25 performance analysis
python test_25x25.py

# Verify solver on a random 36×36 puzzle
python verify_solver.py
```

---

## 📊 Performance

Benchmarks on 25×25 puzzles at 50% clue density (10 random seeds):

| Metric | Value |
|--------|-------|
| **Fastest solve** | ~0.4s |
| **Average solve** | ~36s |
| **Slowest solve** | ~198s |

**Key finding:** Performance is primarily driven by **clue distribution across boxes**, not total clue count. Puzzles with evenly distributed clues (min ≥ 10 per box) solve dramatically faster than those with sparse boxes (min ≤ 6).

---

## 🔢 Supported Puzzle Sizes

| Size | Box Size | Symbols Used | Default Density |
|------|----------|-------------|-----------------|
| 9×9 | 3×3 | 1–9 | 45% |
| 16×16 | 4×4 | 1–9, A–G | 50% |
| 25×25 | 5×5 | 1–9, A–P | 55% |
| 36×36 | 6×6 | 1–9, A–Z, a | 60% |
| 49×49 | 7×7 | 1–9, A–Z, a–n | 65% |

---

## 📝 Usage Example

```python
from sudoku import SudokuSolver

# Define a 9×9 puzzle (0 = empty)
puzzle = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]

solver = SudokuSolver(size=9)
solution = solver.solve(puzzle)

if solution:
    print(solution)
    print(f"Solved in {solver.last_solve_time:.3f}s")
else:
    print("No solution found.")
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

