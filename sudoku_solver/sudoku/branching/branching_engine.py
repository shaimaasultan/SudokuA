import random
from typing import Tuple
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
        self.restart_threshold = grid.size ** 2  # Balanced threshold
        self.try_counts: dict[tuple[int, int, int], int] = {}
        self.solver = None  # Will be set by SudokuSolver
    # ------------------------------------------------------------------ #
    # Top-level search
    # ------------------------------------------------------------------ #

    def solve_with_branching(self) -> bool:
        """
        Recursive search entry using bitmask-optimized heuristics.
        Prioritizes cells with exactly 2 candidates (degree 2).
        Otherwise chooses the cell with the fewest candidates (MRV).
        Uses Max Degree as a tie-breaker.
        """
        # Check for stop request
        if self.solver and self.solver.stop_requested:
            return False
        
        if self.is_solved():
            return True

        # Find best cells to branch on
        min_candidates = self.grid.size + 1
        mrv_cells = []
        degree_2_cells = []

        for r, c in self.grid.iter_cells():
            if not self.grid.is_empty(r, c):
                continue
            
            mask = self.layers.get_allowed_mask(r, c)
            count = bin(mask).count('1')
            
            if count == 0:
                return False # Contradiction
            
            if count == 2:
                degree_2_cells.append((r, c, mask))
            
            if count < min_candidates:
                min_candidates = count
                mrv_cells = [(r, c, mask)]
            elif count == min_candidates:
                mrv_cells.append((r, c, mask))

        # Branching node visited
        self.nodes_visited += 1
        if self.nodes_visited > self.restart_threshold:
            raise SearchRestart("Restarting search to explore new paths...")

        # 1. Determine target cells based on priority (Degree-2 first, else MRV)
        targets = degree_2_cells if degree_2_cells else mrv_cells
        
        # 2. Tie-break using Conflict Heat + Max Degree
        best_cell = None
        max_priority = -1
        
        for r, c, mask in targets:
            # Heat: sum of previous failures for allowed digits in this cell
            # This "colors" the cell as a high-conflict area.
            heat = sum(self.try_counts.get((r, c, d), 0) for d in self._mask_to_list(mask))
            deg = self.layers.get_cell_degree(r, c)
            
            # Combine Heat and Degree into a single priority score
            # Heat is most important (resolve bottlenecks), then Degree (pruning power)
            priority = (heat * 200) + deg
            
            if priority > max_priority:
                max_priority = priority
                best_cell = (r, c, mask)
            elif priority == max_priority:
                # Still tied? Small random jitter
                if random.random() < 0.2:
                    best_cell = (r, c, mask)

        if not best_cell:
            return False

        r, c, mask = best_cell
        allowed = self._mask_to_list(mask)
        random.shuffle(allowed)
        
        # Priority visual feedback
        if degree_2_cells and best_cell in degree_2_cells:
            self.visual.mark_digit_branch(allowed[0], r, c)
        else:
            self.visual.mark_cell_fallback(r, c, allowed)

        return self.try_all_options(r, c, allowed)

    def try_all_options(self, r: int, c: int, digits: list[int]) -> bool:
        """Sequential backtracking: try all given digits for cell (r, c)."""
        for d in digits:
            # Check for stop request
            if self.solver and self.solver.stop_requested:
                return False
            
            # 1. Stagnation Detection: Track how many times (r, c, d) is tried
            key = (r, c, d)
            self.try_counts[key] = self.try_counts.get(key, 0) + 1
            
            # If we've tried this specific digit in this cell many times,
            # or if many cells are repeating, restart.
            # adaptive limit: N/2 for individual cells, 3*N for global stagnant pairs.
            if self.try_counts[key] > max(10, self.grid.size // 2):
                raise SearchRestart(f"Stagnation at ({r}, {c}) for digit {d}")

            # Global stagnation: if we have more than a few 'hot' pairs
            hot_pairs = sum(1 for count in self.try_counts.values() if count > 5)
            if hot_pairs > max(20, self.grid.size):
                 raise SearchRestart("Global search stagnation detected.")

            # Save state
            new_grid = self.grid.clone()
            state = {
                "grid": new_grid,
                "layers": self.layers.clone(new_grid),
            }
            self.state_stack.push(state)

            # Apply guess
            self.grid.set(r, c, d)
            self.layers.rebuild_all_layers()

            success = False
            try:
                self.propagator.run_propagation(self.solver)
                if self.is_solved():
                    success = True
                else:
                    success = self.solve_with_branching()
            except Contradiction:
                success = False

            if success:
                return True

            # Backtrack
            prev = self.state_stack.pop()
            self.grid = prev["grid"]
            self.layers = prev["layers"]
            self.propagator.grid = self.grid
            self.propagator.layers = self.layers
            
            # Record this failure (optional, but helps consistency)
            self.layers.forbid_choice(d, r, c)
        
        return False

    def _mask_to_list(self, mask: int) -> list[int]:
        res = []
        curr = mask
        while curr:
            bit = curr & -curr
            res.append(bit.bit_length())
            curr &= ~bit
        return res

    def is_solved(self) -> bool:
        for r, c in self.grid.iter_cells():
            if self.grid.is_empty(r, c):
                return False
        return True

    def backtrack_and_continue(self) -> bool:
        """
        Backtracking is now integrated into sequential try_all_options,
        but this method might still be used by the orchestrator.
        """
        if self.state_stack.is_empty():
            return False
        # (This remains as a fallback or if the user wants to resume from a pause)
        return False # Relying on recursion now.
