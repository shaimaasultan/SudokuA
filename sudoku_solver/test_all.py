import random, time
from sudoku.solver import SudokuSolver
from sudoku.examples.puzzles import example_puzzle_n9, example_puzzle_n16, example_puzzle_n25

for seed in [42, 123, 999, 7, 2026]:
    print(f"\n--- seed={seed} ---")
    for name, gen, size in [('9x9', example_puzzle_n9, 9), ('16x16', example_puzzle_n16, 16), ('25x25', example_puzzle_n25, 25)]:
        random.seed(seed)
        p = gen()
        s = SudokuSolver(size)
        t0 = time.perf_counter()
        result = s.solve(p)
        t1 = time.perf_counter()
        status = "SOLVED" if result else "FAILED"
        print(f"  {name}: {status} in {t1-t0:.3f}s")
