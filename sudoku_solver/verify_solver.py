import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sudoku.solver import SudokuSolver
from sudoku.examples.puzzles import _generate_dynamic_puzzle
from sudoku.examples.puzzles import example_puzzle_n9

def main():
    print("Testing Sudoku Solver with New Logic...")
    size = 36
    solver = SudokuSolver(size=size)
    
    # Generate a puzzle
    puzzle_values = _generate_dynamic_puzzle(size, 6, 0.5)
    print(f"Initial Puzzle ({size}x{size}, density 50%):")
    for row in puzzle_values:
        print(" ".join(str(v) if v != 0 else "." for v in row[:20]) + " ..." if len(row) > 20 else " ".join(str(v) if v != 0 else "." for v in row))
    
    solution = solver.solve(puzzle_values)
    
    if solution:
        print("\nSolution Found:")
        print(solution)
        print(f"\nSolve Time: {solver.last_solve_time:.4f}s")
    else:
        print("\nNo Solution Found.")

if __name__ == "__main__":
    main()
