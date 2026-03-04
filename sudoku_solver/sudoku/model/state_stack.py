# sudoku/model/state_stack.py

from copy import deepcopy
from typing import Any, List


class StateStack:
    """
    Simple stack for storing solver states (grid + layers + any metadata).
    """

    def __init__(self):
        self._stack: List[Any] = []

    def push(self, state: Any) -> None:
        self._stack.append(deepcopy(state))

    def pop(self) -> Any:
        if not self._stack:
            raise RuntimeError("State stack underflow.")
        return self._stack.pop()

    def is_empty(self) -> bool:
        return not self._stack
