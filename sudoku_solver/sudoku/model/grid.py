# sudoku/model/grid.py

import numpy as np
from typing import List, Optional


class Grid:
    """
    Represents an N x N Sudoku grid.
    Values are integers in [0, N], where 0 means empty.
    """

    def __init__(self, size: int, values: Optional[List[List[int]]] = None):
        self.size = size
        self.box_size = int(size ** 0.5)
        if self.box_size * self.box_size != size:
            raise ValueError("Grid size must be a perfect square (e.g., 9, 16, 25).")

        if values is None:
            self.values = np.zeros((size, size), dtype=int)
        else:
            if len(values) != size or any(len(row) != size for row in values):
                raise ValueError("Values must be an N x N matrix.")
            self.values = np.array(values, dtype=int)

    def clone(self) -> "Grid":
        new_grid = Grid(self.size)
        new_grid.values = self.values.copy()
        return new_grid

    def get(self, r: int, c: int) -> int:
        return int(self.values[r, c])

    def set(self, r: int, c: int, v: int) -> None:
        self.values[r, c] = v

    def is_empty(self, r: int, c: int) -> bool:
        return self.values[r, c] == 0

    def iter_cells(self):
        for r in range(self.size):
            for c in range(self.size):
                yield r, c

    def row_indices(self, r: int):
        return [(r, c) for c in range(self.size)]

    def col_indices(self, c: int):
        return [(r, c) for r in range(self.size)]

    def box_indices(self, r: int, c: int):
        br = (r // self.box_size) * self.box_size
        bc = (c // self.box_size) * self.box_size
        return [
            (br + dr, bc + dc)
            for dr in range(self.box_size)
            for dc in range(self.box_size)
        ]

    def __str__(self) -> str:
        lines = []
        for r in range(self.size):
            line = " ".join(str(v) if v != 0 else "." for v in self.values[r])
            lines.append(line)
        return "\n".join(lines)
