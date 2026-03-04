import random

def _generate_dynamic_puzzle(size: int, box: int, density: float = 0.5):
    """
    Generates a varied, valid Sudoku puzzle of any size.
    Uses random transformations (digit permutation, row/col swaps within blocks)
    on a base valid grid to ensure variety.
    """
    # 1. Generate base valid grid using shift pattern
    base = [[0 for _ in range(size)] for _ in range(size)]
    for r in range(size):
        shift = (r * box + r // box) % size
        for c in range(size):
            base[r][c] = (shift + c) % size + 1
            
    # 2. Randomly permute digits
    digits = list(range(1, size + 1))
    random.shuffle(digits)
    mapping = {i+1: digits[i] for i in range(size)}
    for r in range(size):
        for c in range(size):
            base[r][c] = mapping[base[r][c]]
            
    # 3. Swap rows within block rows
    for b in range(box):
        rows = list(range(b * box, (b + 1) * box))
        random.shuffle(rows)
        new_block = [base[rows[i]] for i in range(box)]
        for i in range(box):
            base[b * box + i] = new_block[i]
            
    # 4. Swap columns within block columns
    for b in range(box):
        cols = list(range(b * box, (b + 1) * box))
        random.shuffle(cols)
        for r in range(size):
            row_copy = base[r][:]
            for i in range(box):
                base[r][b * box + i] = row_copy[cols[i]]

    # 5. Poke holes (clue density)
    puzzle = [[0 for _ in range(size)] for _ in range(size)]
    for r in range(size):
        for c in range(size):
            if random.random() < density:
                puzzle[r][c] = base[r][c]
                
    return puzzle

def example_puzzle_n9(density: float = 0.45):
    return _generate_dynamic_puzzle(size=9, box=3, density=density)

def example_puzzle_n16(density: float = 0.5):
    return _generate_dynamic_puzzle(size=16, box=4, density=density)

def example_puzzle_n25(density: float = 0.55):
    return _generate_dynamic_puzzle(size=25, box=5, density=density)

def example_puzzle_n36(density: float = 0.6):
    return _generate_dynamic_puzzle(size=36, box=6, density=density)

def example_puzzle_n49(density: float = 0.65):
    return _generate_dynamic_puzzle(size=49, box=7, density=density)
