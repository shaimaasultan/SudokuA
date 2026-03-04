
import sys
import os
# Add the project root to sys.path
sys.path.append(os.getcwd())

from sudoku.model.grid import Grid
from sudoku.solver import SudokuSolver

def test_9x9():
    print("Testing 9x9 basic puzzle...")
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
    
    solver = SudokuSolver(size=9)
    result = solver.solve(puzzle)
    
    if result:
        print("Success! Solution found:")
        print(result)
    else:
        print("Failed to find solution.")

def test_fluid_row_col_rules():
    print("\nTesting Row/Col Fluid rules and Conflict Resolution...")
    size = 4
    # Create a 4x4 grid (box size 2)
    grid = [[0 for _ in range(size)] for _ in range(size)]
    
    solver = SudokuSolver(size=4)
    # 1. Fill some BOX duplicates
    # Box 0: (0,0), (0,1), (1,0), (1,1)
    grid[0][0] = 1
    grid[1][1] = 1 # Same box!
    
    print("Initial grid with BOX duplicates:")
    for row in grid: print(row)
    
    # Run solve. It should find a solution where all units are valid.
    result = solver.solve(grid)
    
    if result:
        print("Success! Global solution found:")
        print(result)
        # Verify box constraints
        for b in range(4):
            br = (b // 2) * 2
            bc = (b % 2) * 2
            box_vals = [result.get(br+dr, bc+dc) for dr in range(2) for dc in range(2)]
            if len(set(box_vals)) != 4 or 0 in box_vals:
                print(f"FAILED: Box {b} is invalid: {box_vals}")
            else:
                print(f"Passed: Box {b} is valid: {box_vals}")

        # Verify Row constraints
        for r in range(4):
            row_vals = [result.get(r, c) for c in range(4)]
            if len(set(row_vals)) != 4 or 0 in row_vals:
                print(f"FAILED: Row {r} is invalid: {row_vals}")
            else:
                print(f"Passed: Row {r} is valid")

        # Verify Col constraints
        for c in range(4):
            col_vals = [result.get(r, c) for r in range(4)]
            if len(set(col_vals)) != 4 or 0 in col_vals:
                print(f"FAILED: Col {c} is invalid: {col_vals}")
            else:
                print(f"Passed: Col {c} is valid")
    else:
        # Check for contradictions
        print("Failed to find solution.")

def test_conflict_resolution():
    print("\nTesting Conflict Resolution (Row/Col Fluid)...")
    size = 4
    grid = Grid(size)
    # Set (0,0) = 1
    grid.set(0, 0, 1)
    print(f"Initial: (0,0) = {grid.get(0, 0)}")
    
    # Set (0,2) = 1. This is the same row. (0,0) should become 0.
    grid.set(0, 2, 1)
    print(f"After setting (0,2)=1: (0,0)={grid.get(0, 0)}, (0,2)={grid.get(0, 2)}")
    
    if grid.get(0, 0) == 0 and grid.get(0, 2) == 1:
        print("PASSED: Row conflict resolved (cell emptied).")
    else:
        print("FAILED: Row conflict NOT resolved.")

    # Set (2,2) = 1. This is the same col as (0,2). (0,2) should become 0.
    grid.set(2, 2, 1)
    print(f"After setting (2,2)=1: (0,2)={grid.get(0, 2)}, (2,2)={grid.get(2, 2)}")
    
    if grid.get(0, 2) == 0 and grid.get(2, 2) == 1:
        print("PASSED: Col conflict resolved (cell emptied).")
    else:
        print("FAILED: Col conflict NOT resolved.")

if __name__ == "__main__":
    test_fluid_row_col_rules()
    test_conflict_resolution()
