import time
from .model.grid import Grid
from .layers.layer_manager import LayerManager
from .propagation.propagator import Propagator, Contradiction
from .branching.branching_engine import BranchingEngine, SearchRestart
from .visual.visual_hooks import VisualHooks


class SudokuSolver:
    """
    High-level orchestrator:
    - builds grid and layers
    - runs propagation
    - then branching
    """

    def __init__(self, size: int = 9, visual: VisualHooks | None = None):
        self.size = size
        self.visual = visual or VisualHooks()
        self.last_solve_time = 0.0
        self.stop_requested = False  # Flag to signal solver to stop

    def solve(self, values) -> Grid | None:
        start_time = time.perf_counter()
        
        grid = Grid(self.size, values)
        layers = LayerManager(grid)
        propagator = Propagator(grid, layers, self.visual)
        self.branching_engine = BranchingEngine(grid, layers, propagator, self.visual)
        self.branching_engine.solver = self  # Pass solver reference for stop checking

        # Initial propagation
        layers.rebuild_all_layers()
        try:
            propagator.run_propagation(self)
        except Contradiction:
            self.last_solve_time = time.perf_counter() - start_time
            return None

        if self.stop_requested:
            self.last_solve_time = time.perf_counter() - start_time
            return None

        # Branching search with restarts
        max_restarts = 5
        solution_found = False
        for attempt in range(max_restarts):
            if self.stop_requested:
                self.last_solve_time = time.perf_counter() - start_time
                return None
            
            try:
                ok = self.branching_engine.solve_with_branching()
                if ok:
                    solution_found = True
                    break
                else:
                    self.last_solve_time = time.perf_counter() - start_time
                    return None
            except SearchRestart:
                if self.stop_requested:
                    self.last_solve_time = time.perf_counter() - start_time
                    return None
                
                # Re-init engine components to restart fresh with new random seeds
                print(f"Restarting search (attempt {attempt + 1})...")
                grid = Grid(self.size, values)
                layers = LayerManager(grid)
                propagator = Propagator(grid, layers, self.visual)
                self.branching_engine = BranchingEngine(grid, layers, propagator, self.visual)
                self.branching_engine.solver = self
                layers.rebuild_all_layers()
                try:
                    propagator.run_propagation(self)
                except Contradiction:
                    self.last_solve_time = time.perf_counter() - start_time
                    return None
        
        self.last_solve_time = time.perf_counter() - start_time
        
        if not solution_found or not self.branching_engine.is_solved():
            return None

        return self.branching_engine.grid

    def backtrack_and_continue(self):
        """
        Called when the current branch reports 'no solution'.
        Attempts to backtrack to the previous decision point and continue.
        Returns a solution grid or None if the entire search space is exhausted.
        """
        try:
            res = self.branching_engine.backtrack_and_continue()
            if res is True:
                return self.branching_engine.grid
            return None
        except Exception:
            return None
