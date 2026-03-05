import random
import numpy as np
from ..model.grid import Grid
from ..model.state_stack import StateStack
from ..layers.layer_manager import LayerManager
from ..propagation.propagator import Propagator, Contradiction
from ..visual.visual_hooks import VisualHooks


class SearchRestart(Exception):
    """Raised when search should be restarted with a new random seed."""
    pass


class BranchingEngine:
    """
    Branching strategy:
      - primary: digit-based branching (choose digit, then cell)
      - fallback: cell-based branching (MRV on cells)
    Search is fully recursive: every guess continues with solve_with_branching().
    """

    def __init__(
        self,
        grid: Grid,
        layers: LayerManager,
        propagator: Propagator,
        visual: VisualHooks,
    ):
        self.grid = grid
        self.layers = layers
        self.propagator = propagator
        self.visual = visual
        self.state_stack = StateStack()
        self.nodes_visited = 0
        self.restart_threshold = grid.size * 1000  # Increased for larger grids
        self.try_counts: dict[tuple[int, int, int], float] = {}
        self.unit_try_counts: dict[tuple[int, int, int], float] = {}
        self.hot_pair_count = 0  # Track cells with try_count > 5 incrementally
        self.decay_factor = 0.5
        self.solver = None  # Will be set by SudokuSolver
    # ------------------------------------------------------------------ #
    # Top-level search
    # ------------------------------------------------------------------ #

    def _select_best_cell(self):
        """Find best cell using MRV (fewest candidates) with degree tiebreaker.
        MRV minimises branching factor; degree breaks ties by choosing
        the cell most connected to empty peers (max cascade on solve).
        Returns (r, c, mask) or None if no empty cell found.
        Raises Contradiction if an empty cell has 0 candidates.
        """
        N = self.grid.size
        min_count = N + 1
        mrv_cells = []

        all_masks = self.layers.get_all_allowed_masks().tolist()
        self._last_all_masks = all_masks
        for r in range(N):
            for c in range(N):
                if self.grid.values[r, c] != 0:
                    continue
                mask = all_masks[r][c]
                count = mask.bit_count()
                if count == 0:
                    raise Contradiction(f"Cell ({r},{c}) has no candidates")
                if count < min_count:
                    min_count = count
                    mrv_cells = [(r, c, mask)]
                elif count == min_count:
                    mrv_cells.append((r, c, mask))

        self.nodes_visited += 1
        if self.nodes_visited > self.restart_threshold:
            raise SearchRestart("Restarting search to explore new paths...")

        if not mrv_cells:
            return None

        best_cell = None
        max_priority = -1
        bs = self.grid.box_size

        for r, c, mask in mrv_cells:
            deg = self.layers.get_cell_degree(r, c)
            digits = self._mask_to_list(mask)
            heat = sum(self.try_counts.get((r, c, d), 0) for d in digits)
            box_id = (r // bs) * bs + (c // bs)
            unit_heat = 0
            for d in digits:
                unit_heat += self.unit_try_counts.get((0, r, d), 0)
                unit_heat += self.unit_try_counts.get((1, c, d), 0)
                unit_heat += self.unit_try_counts.get((2, box_id, d), 0)
            # Among MRV ties: degree (impact), then heat (explore failed areas)
            priority = (deg * 1000) + (heat * 200) + (unit_heat * 100)
            if priority > max_priority:
                max_priority = priority
                best_cell = (r, c, mask)

        return best_cell

    def _check_stagnation(self, r, c, d):
        """Track try count and raise SearchRestart on stagnation."""
        key = (r, c, d)
        old = self.try_counts.get(key, 0)
        new = old + 1
        self.try_counts[key] = new
        if new > max(10, self.grid.size // 2):
            raise SearchRestart(f"Stagnation at ({r}, {c}) for digit {d}")
        # Incremental hot_pair tracking: crossing the threshold of 5
        if old <= 5 < new:
            self.hot_pair_count += 1
        if self.hot_pair_count > max(20, self.grid.size):
            raise SearchRestart("Global search stagnation detected.")

    def _record_unit_failure(self, r, c, d):
        """Increment unit_try_counts after a failed guess."""
        box_id = (r // self.grid.box_size) * self.grid.box_size + (c // self.grid.box_size)
        self.unit_try_counts[(0, r, d)] = self.unit_try_counts.get((0, r, d), 0) + 1
        self.unit_try_counts[(1, c, d)] = self.unit_try_counts.get((1, c, d), 0) + 1
        self.unit_try_counts[(2, box_id, d)] = self.unit_try_counts.get((2, box_id, d), 0) + 1

    def _save_state(self):
        """Clone and push current grid/layers onto state stack."""
        new_grid = self.grid.clone()
        self.state_stack.push({"grid": new_grid, "layers": self.layers.clone(new_grid)})

    def _restore_state(self):
        """Pop and restore grid/layers from state stack."""
        prev = self.state_stack.pop()
        self.grid = prev["grid"]
        self.layers = prev["layers"]
        self.propagator.grid = self.grid
        self.propagator.layers = self.layers

    def _order_digits_lcv(self, r, c, digits, all_masks):
        """Order digits by unit-failure penalty (digits that already failed
        in the same row/col/box are tried later), then LCV (fewest
        eliminations). This avoids retrying digits that repeatedly
        conflict in the same unit while keeping all options available."""
        N = self.grid.size
        bs = self.grid.box_size
        br = (r // bs) * bs
        bc = (c // bs) * bs
        box_id = (r // bs) * bs + (c // bs)
        scored = []
        for d in digits:
            bit = 1 << (d - 1)
            eliminations = 0
            for i in range(N):
                if i != c and (all_masks[r][i] & bit):
                    eliminations += 1
                if i != r and (all_masks[i][c] & bit):
                    eliminations += 1
            for dr in range(bs):
                for dc in range(bs):
                    rr, cc = br + dr, bc + dc
                    if (rr, cc) != (r, c) and rr != r and cc != c and (all_masks[rr][cc] & bit):
                        eliminations += 1
            # Unit failure penalty: how many times this digit failed
            # in the same row, column, or box — demote repeaters
            unit_fail = (
                self.unit_try_counts.get((0, r, d), 0)
                + self.unit_try_counts.get((1, c, d), 0)
                + self.unit_try_counts.get((2, box_id, d), 0)
            )
            scored.append((unit_fail, eliminations, d))
        scored.sort()
        return [d for _, _, d in scored]

    def solve_with_branching(self) -> bool:
        """
        Iterative DFS with MRV cell selection.
        Digits ordered by unit-failure penalty + LCV: digits that already
        failed in the same row/col/box are pushed to the back of the list,
        so the next untried digit is picked first.
        """
        try:
            best_cell = self._select_best_cell()
        except Contradiction:
            return False
        if not best_cell:
            return self.is_solved()

        r, c, mask = best_cell
        allowed = self._mask_to_list(mask)
        allowed = self._order_digits_lcv(r, c, allowed, self._last_all_masks)
        self.visual.mark_cell_fallback(r, c, allowed)

        stack = [{'r': r, 'c': c, 'digits': allowed, 'idx': 0}]

        while stack:
            if self.solver and self.solver.stop_requested:
                return False

            current = stack[-1]
            r, c, digits = current['r'], current['c'], current['digits']

            if current['idx'] < len(digits):
                d = digits[current['idx']]
                current['idx'] += 1

                self._check_stagnation(r, c, d)
                self._save_state()
                self.grid.set(r, c, d)
                self.layers._update_masks(r, c, d, True)

                try:
                    self.propagator.run_propagation(self.solver)

                    best_next = self._select_best_cell()
                    if not best_next:
                        return True  # No empty cells = solved

                    rr, cc, maskk = best_next
                    allowed_next = self._mask_to_list(maskk)
                    allowed_next = self._order_digits_lcv(rr, cc, allowed_next, self._last_all_masks)
                    stack.append({'r': rr, 'c': cc, 'digits': allowed_next, 'idx': 0})

                except Contradiction:
                    self._restore_state()
                    self._record_unit_failure(r, c, d)

            else:
                stack.pop()
                if stack:
                    self._restore_state()
                    last = stack[-1]
                    d = last['digits'][last['idx'] - 1]
                    self._record_unit_failure(last['r'], last['c'], d)

        return False

    def decay_counts(self):
        hot = 0
        for key in list(self.try_counts.keys()):
            self.try_counts[key] *= self.decay_factor
            if self.try_counts[key] < 0.1:
                del self.try_counts[key]
            elif self.try_counts[key] > 5:
                hot += 1
        self.hot_pair_count = hot
        for key in list(self.unit_try_counts.keys()):
            self.unit_try_counts[key] *= self.decay_factor
            if self.unit_try_counts[key] < 0.1:
                del self.unit_try_counts[key]

    def _mask_to_list(self, mask: int) -> list[int]:
        res = []
        curr = mask
        while curr:
            bit = curr & -curr
            res.append(bit.bit_length())
            curr &= ~bit
        return res

    def is_solved(self) -> bool:
        return bool(np.all(self.grid.values != 0))

    def backtrack_and_continue(self) -> bool:
        """Stub kept for external callers (solver.py, gui_main.py)."""
        return False
