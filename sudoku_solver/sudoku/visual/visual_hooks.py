# sudoku/visual/visual_hooks.py

class VisualHooks:
    """
    Hook class for visualization.
    Default implementation is no-op.
    Subclass this to provide GUI or CLI feedback.
    """

    def mark_forced(self, r: int, c: int, d: int) -> None:
        pass

    def mark_guess(self, r: int, c: int, d: int) -> None:
        pass

    def mark_contradiction_cell(self, r: int, c: int) -> None:
        pass

    def mark_digit_branch(self, d: int, r: int, c: int):
        pass

    def mark_cell_fallback(self, r: int, c: int, allowed):
        pass
    def start_batch(self) -> None:
        pass

    def mark_cell_heat(self, r: int, c: int, heat_score: float) -> None:
        pass

    def end_batch(self) -> None:
        pass
