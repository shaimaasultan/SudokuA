# sudoku/layers/layer_manager.py

from typing import List, Tuple
from ..model.grid import Grid


class LayerManager:
    """
    Manages one boolean layer per digit.
    layers[d][r][c] == True means digit (d+1) is allowed at (r,c).
    Digits are 1..N, but we store them 0..N-1 internally.
    """

    def __init__(self, grid: Grid, skip_rebuild: bool = False):
        self.grid = grid
        self.size = grid.size
        self.digits = list(range(1, self.size + 1))
        
        # Bitmasks for digits used in each unit
        self.row_masks = [0] * self.size
        self.col_masks = [0] * self.size
        self.box_masks = [0] * self.size
        
        # Fill counts for O(1) degree calculation
        self.row_fill_counts = [0] * self.size
        self.col_fill_counts = [0] * self.size
        self.box_fill_counts = [0] * self.size

        # Manual forbids per cell
        self.manual_masks = [[0] * self.size for _ in range(self.size)]
        
        if not skip_rebuild:
            self.rebuild_all_layers()

    def clone(self, grid: Grid = None) -> "LayerManager":
        new_grid = grid if grid is not None else self.grid.clone()
        clone = LayerManager(new_grid, skip_rebuild=True)
        clone.row_masks = self.row_masks[:]
        clone.col_masks = self.col_masks[:]
        clone.box_masks = self.box_masks[:]
        clone.row_fill_counts = self.row_fill_counts[:]
        clone.col_fill_counts = self.col_fill_counts[:]
        clone.box_fill_counts = self.box_fill_counts[:]
        clone.manual_masks = [row[:] for row in self.manual_masks]
        return clone

    def get_cell_degree(self, r: int, c: int) -> int:
        """
        O(1) degree: sum of empty cells in row, col, and box.
        Since the intersection sizes are the same for all cells, 
        this remains a perfect tie-breaker.
        """
        b = self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)
        return (3 * self.size) - (self.row_fill_counts[r] + self.col_fill_counts[c] + self.box_fill_counts[b])

    def rebuild_all_layers(self) -> None:
        self.row_masks = [0] * self.size
        self.col_masks = [0] * self.size
        self.box_masks = [0] * self.size
        self.row_fill_counts = [0] * self.size
        self.col_fill_counts = [0] * self.size
        self.box_fill_counts = [0] * self.size

        for r, c in self.grid.iter_cells():
            v = self.grid.get(r, c)
            if v != 0:
                self._update_masks(r, c, v, True)

    def _update_masks(self, r: int, c: int, v: int, set_bits: bool) -> None:
        bit = 1 << (v - 1)
        if set_bits:
            self.row_masks[r] |= bit
            self.col_masks[c] |= bit
            self.box_masks[self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)] |= bit
        else:
            self.row_masks[r] &= ~bit
            self.col_masks[c] &= ~bit
            self.box_masks[self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)] &= ~bit

    def is_forbidden(self, d: int, r: int, c: int) -> bool:
        """Combined forbidden check: Row | Col | Box | Manual | GridSet"""
        # If the cell is already set to something else, it's forbidden for d
        v = self.grid.get(r, c)
        if v != 0:
            return v != d
        
        bit = 1 << (d - 1)
        b = self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)
        
        return bool((self.row_masks[r] & bit) or 
                    (self.col_masks[c] & bit) or 
                    (self.box_masks[b] & bit) or
                    (self.manual_masks[r][c] & bit))

    def allowed_digits_at(self, r: int, c: int) -> List[int]:
        if not self.grid.is_empty(r, c):
            return []
        
        b = self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)
        combined_forbidden = (self.row_masks[r] | 
                               self.col_masks[c] | 
                               self.box_masks[b] | 
                               self.manual_masks[r][c])
        
        return [d for d in self.digits if not (combined_forbidden & (1 << (d - 1)))]

    def get_allowed_mask(self, r: int, c: int) -> int:
        """Returns a bitmask of allowed digits for cell (r, c)."""
        if not self.grid.is_empty(r, c):
            return 0
        b = self.grid.box_size * (r // self.grid.box_size) + (c // self.grid.box_size)
        combined_forbidden = (self.row_masks[r] | 
                               self.col_masks[c] | 
                               self.box_masks[b] | 
                               self.manual_masks[r][c])
        full_mask = (1 << self.size) - 1
        return full_mask & ~combined_forbidden

    def count_candidates_for_digit(self, d: int) -> int:
        count = 0
        bit = 1 << (d - 1)
        for r in range(self.size):
            # Optimization: if d is already in row r, no candidates there
            if self.row_masks[r] & bit: continue
            for c in range(self.size):
                if self.grid.is_empty(r, c) and not self.is_forbidden(d, r, c):
                    count += 1
        return count

    def units_for_digit(self, d: int) -> Tuple[int, int, int]:
        """
        Returns counts of units (rows, cols, boxes) where digit d has exactly 2 candidates.
        """
        N = self.size
        box_size = self.grid.box_size

        def count_rows_with_two():
            cnt = 0
            for r in range(N):
                k = 0
                for c in range(N):
                    if self.is_digit_possible_at(d, r, c):
                        k += 1
                        if k > 2: break
                if k == 2: cnt += 1
            return cnt

        def count_cols_with_two():
            cnt = 0
            for c in range(N):
                k = 0
                for r in range(N):
                    if self.is_digit_possible_at(d, r, c):
                        k += 1
                        if k > 2: break
                if k == 2: cnt += 1
            return cnt

        def count_boxes_with_two():
            cnt = 0
            for b in range(N):
                br = (b // box_size) * box_size
                bc = (b % box_size) * box_size
                k = 0
                for dr in range(box_size):
                    for dc in range(box_size):
                        if self.is_digit_possible_at(d, br + dr, bc + dc):
                            k += 1
                            if k > 2: break
                    if k > 2: break
                if k == 2: cnt += 1
            return cnt

        return count_rows_with_two(), count_cols_with_two(), count_boxes_with_two()

    def spatial_concentration(self, d: int) -> int:
        """
        Rough measure: number of distinct rows + cols + boxes used by digit d.
        Lower is more concentrated.
        """
        N = self.size
        box_size = self.grid.box_size
        rows = set()
        cols = set()
        boxes = set()

        for r in range(N):
            for c in range(N):
                if self.is_digit_possible_at(d, r, c):
                    rows.add(r)
                    cols.add(c)
                    boxes.add((r // box_size) * box_size + (c // box_size))

        return len(rows) + len(cols) + len(boxes)

    def is_digit_possible_at(self, d: int, r: int, c: int) -> bool:
        return self.grid.is_empty(r, c) and not self.is_forbidden(d, r, c)

    def forbid_choice(self, d: int, r: int, c: int) -> None:
        self.manual_masks[r][c] |= (1 << (d - 1))
