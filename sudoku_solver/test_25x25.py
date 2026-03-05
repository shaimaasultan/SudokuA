import sys
import os
import time
import random

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sudoku.solver import SudokuSolver
from sudoku.examples.puzzles import _generate_dynamic_puzzle

def compute_row_col_empties(puzzle, size):
    """Compute number of empty cells per row and per column."""
    row_empties = []
    col_empties = [0] * size
    for r in range(size):
        empty_row = 0
        for c in range(size):
            if puzzle[r][c] == 0:
                empty_row += 1
                col_empties[c] += 1
        row_empties.append(empty_row)
    return row_empties, col_empties

def compute_box_clues(puzzle, size, box_size):
    """Compute number of clues per box."""
    clues_per_box = []
    for br in range(0, size, box_size):
        for bc in range(0, size, box_size):
            count = 0
            for r in range(br, br + box_size):
                for c in range(bc, bc + box_size):
                    if puzzle[r][c] != 0:
                        count += 1
            clues_per_box.append(count)
    return clues_per_box

def main():
    size = 36
    box_size = 6
    density = 0.5
    num_puzzles = 1

    solver = SudokuSolver(size=size)

    times = []
    stats = []

    for i in range(num_puzzles):
        print(f"\nGenerating puzzle {i+1}...")
        puzzle_values = _generate_dynamic_puzzle(size, box_size, density)
        
        # Compute stats
        total_clues = sum(1 for row in puzzle_values for v in row if v != 0)
        box_clues = compute_box_clues(puzzle_values, size, box_size)
        min_clues = min(box_clues)
        max_clues = max(box_clues)
        avg_clues = sum(box_clues) / len(box_clues)
        
        row_empties, col_empties = compute_row_col_empties(puzzle_values, size)
        min_row_empty = min(row_empties)
        max_row_empty = max(row_empties)
        avg_row_empty = sum(row_empties) / len(row_empties)
        min_col_empty = min(col_empties)
        max_col_empty = max(col_empties)
        avg_col_empty = sum(col_empties) / len(col_empties)
        
        num_rows_less_N = sum(1 for e in row_empties if e < size)
        num_cols_less_N = sum(1 for e in col_empties if e < size)
        
        print(f"Total clues: {total_clues}, Box clues: min={min_clues}, max={max_clues}, avg={avg_clues:.1f}")
        print(f"Row empties: min={min_row_empty}, max={max_row_empty}, avg={avg_row_empty:.1f}, rows with empty < {size}: {num_rows_less_N}")
        print(f"Col empties: min={min_col_empty}, max={max_col_empty}, avg={avg_col_empty:.1f}, cols with empty < {size}: {num_cols_less_N}")
        
        start_time = time.time()
        solution = solver.solve(puzzle_values)
        solve_time = time.time() - start_time
        
        if solution:
            print(f"Solved in {solve_time:.4f}s")
            times.append(solve_time)
            stats.append((min_clues, max_clues, avg_clues, total_clues, min_row_empty, max_row_empty, avg_row_empty, min_col_empty, max_col_empty, avg_col_empty, num_rows_less_N, num_cols_less_N))
        else:
            print("No solution found")
            times.append(float('inf'))
            stats.append((min_clues, max_clues, avg_clues, total_clues, min_row_empty, max_row_empty, avg_row_empty, min_col_empty, max_col_empty, avg_col_empty, num_rows_less_N, num_cols_less_N))

    print("\nSummary:")
    valid_times = [t for t in times if t != float('inf')]
    if valid_times:
        print(f"Average solve time: {sum(valid_times)/len(valid_times):.4f}s")
        print(f"Min time: {min(valid_times):.4f}s, Max time: {max(valid_times):.4f}s")
        fast_idx = times.index(min(valid_times))
        slow_idx = times.index(max(valid_times))
        print(f"Fastest puzzle stats: {stats[fast_idx]}")
        print(f"Slowest puzzle stats: {stats[slow_idx]}")
    else:
        print("No puzzles solved")

if __name__ == "__main__":
    main()