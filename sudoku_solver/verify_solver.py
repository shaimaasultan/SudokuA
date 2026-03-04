import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sudoku.solver import SudokuSolver
from sudoku.examples.puzzles import example_puzzle_n9

def main():
    print("Testing Sudoku Solver with New Logic...")
    solver = SudokuSolver(size=9)
    
    # Generate a puzzle
    puzzle_values = example_puzzle_n9(density=0.3)
    print("Initial Puzzle:")
    for row in puzzle_values:
        print(" ".join(str(v) if v != 0 else "." for v in row))
    
    solution = solver.solve(puzzle_values)
    
    if solution:
        print("\nSolution Found:")
        print(solution)
        print(f"\nSolve Time: {solver.last_solve_time:.4f}s")
    else:
        print("\nNo Solution Found.")

if __name__ == "__main__":
    main()
