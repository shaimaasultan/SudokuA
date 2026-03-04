import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sudoku.solver import SudokuSolver
from sudoku.model.grid import Grid

def main():
    print("Testing Phase 1 Implementation...")
    
    # A simple valid 9x9 puzzle
    puzzle = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]
    
    print("Testing with 9x9 puzzle...")
    solver = SudokuSolver(size=9)
    
    try:
        solution = solver.solve(puzzle)
        if solution:
            print("✓ Solution found!")
            print(f"Solve time: {solver.last_solve_time:.4f}s")
        else:
            print("✗ No solution found!")
    except Exception as e:
        print(f"✗ Error during solving: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 16x16
    print("\n" + "="*50)
    print("Testing with 16x16 puzzle...")
    
    # A simple 16x16 puzzle (mostly empty for quick testing)
    puzzle_16 = [[0] * 16 for _ in range(16)]
    puzzle_16[0][0] = 1
    puzzle_16[1][1] = 2
    puzzle_16[2][2] = 3
    
    solver16 = SudokuSolver(size=16)
    try:
        print("Attempting to solve 16x16 (will take longer)...")
        solution = solver16.solve(puzzle_16)
        if solution:
            print("✓ Solution found!")
            print(f"Solve time: {solver16.last_solve_time:.4f}s")
        else:
            print("✗ No solution found!")
    except Exception as e:
        print(f"✗ Error during solving: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
