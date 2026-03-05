# sudoku/propagation/propagator.py

from dataclasses import dataclass
from typing import List
from itertools import combinations
import numpy as np
from ..model.grid import Grid
from ..layers.layer_manager import LayerManager
from ..visual.visual_hooks import VisualHooks


class Contradiction(Exception):
    pass


@dataclass
class ForcedMove:
    row: int
    col: int
    digit: int


class Propagator:
    """
    Handles logical propagation on layers:
    - rebuild layers
    - find forced moves
    - apply them
    - detect contradictions
    """

    def __init__(self, grid: Grid, layers: LayerManager, visual: VisualHooks):
        self.grid = grid
        self.layers = layers
        self.visual = visual

    def rebuild_all_layers(self) -> None:
        self.layers.rebuild_all_layers()

    def run_propagation(self, solver=None) -> None:
        """
        Repeatedly apply forced moves and advanced pruning until no more exist 
        or a contradiction is found.
        """
        self.visual.start_batch()
        try:
            while True:
                # Check for stop request
                if solver and solver.stop_requested:
                    return
                
                # 1. Independent "Signal" check (Full House)
                # This is extremely fast now with bitmasks.
                found_full_house = self.apply_full_house_signal()
                if found_full_house:
                    self.check_for_contradictions()
                    continue
                
                # 2. Standard forced moves (naked/hidden singles) - Optimized with bitmasks
                forced = self.find_forced_moves()
                if forced:
                    self.apply_forced_moves(forced)
                    self.check_for_contradictions()
                    continue
                
                # 3. Advanced Pruning (short-circuit: restart loop on first success)
                if (self.apply_pointing_pairs()
                    or self.apply_naked_pairs()
                    or self.apply_naked_triples()
                    or self.apply_hidden_pairs()
                    or self.apply_simple_coloring()):
                    self.check_for_contradictions()
                    continue
                
                self.check_for_contradictions()
                return
        finally:
            self.visual.end_batch()

    def apply_pointing_pairs(self) -> bool:
        """
        Pointing Pairs/Triples logic:
        If all candidates for a digit d in box B are confined to a single row/col,
        then d can be removed from that row/col elsewhere.
        Returns True if any pruning occurred.
        """
        N = self.grid.size
        box_size = self.grid.box_size
        bs_cols = N // box_size
        any_pruned = False

        # Single N×N pass: build per-digit, per-box candidate lists
        # box_d_cells[box_id][digit] = list of (r, c)
        box_d_cells = [[[] for _ in range(N + 1)] for _ in range(N)]

        all_masks = self.layers.get_all_allowed_masks().tolist()
        for r in range(N):
            for c in range(N):
                mask = all_masks[r][c]
                if not mask: continue
                b = (r // box_size) * bs_cols + (c // box_size)
                curr = mask
                while curr:
                    bit = curr & -curr
                    box_d_cells[b][bit.bit_length()].append((r, c))
                    curr &= ~bit

        for bi in range(N):
            br = (bi // bs_cols) * box_size
            bc = (bi % bs_cols) * box_size
            for d in range(1, N + 1):
                candidates = box_d_cells[bi][d]
                if not candidates:
                    continue

                # Check Row alignment
                first_r = candidates[0][0]
                if all(r == first_r for r, c in candidates):
                    for col in range(N):
                        if bc <= col < bc + box_size:
                            continue
                        if self.layers.is_digit_possible_at(d, first_r, col):
                            self.layers.forbid_choice(d, first_r, col)
                            any_pruned = True

                # Check Col alignment
                first_c = candidates[0][1]
                if all(c == first_c for r, c in candidates):
                    for row in range(N):
                        if br <= row < br + box_size:
                            continue
                        if self.layers.is_digit_possible_at(d, row, first_c):
                            self.layers.forbid_choice(d, row, first_c)
                            any_pruned = True

        return any_pruned

    def _collect_unit_cells(self):
        """Shared N×N scan for naked pairs and naked triples."""
        N = self.grid.size
        box_size = self.grid.box_size
        bs_cols = N // box_size
        row_cells = [[] for _ in range(N)]
        col_cells = [[] for _ in range(N)]
        box_cells = [[] for _ in range(N)]
        all_masks = self.layers.get_all_allowed_masks().tolist()
        for r in range(N):
            for c in range(N):
                mask = all_masks[r][c]
                if not mask: continue
                b = (r // box_size) * bs_cols + (c // box_size)
                entry = (mask, r, c)
                row_cells[r].append(entry)
                col_cells[c].append(entry)
                box_cells[b].append(entry)
        return row_cells, col_cells, box_cells

    def apply_naked_pairs(self) -> bool:
        """
        Naked Pairs: Two cells in same unit have same TWO candidates.
        Remove those candidates from other cells in unit.
        """
        any_pruned = False
        N = self.grid.size
        row_cells, col_cells, box_cells = self._collect_unit_cells()

        for i in range(N):
            for unit_cells in (row_cells[i], col_cells[i], box_cells[i]):
                # Find naked pairs
                masks = {}
                for mask, r, c in unit_cells:
                    if mask.bit_count() == 2:
                        if mask not in masks: masks[mask] = []
                        masks[mask].append((r, c))

                for mask, pair_cells in masks.items():
                    if len(pair_cells) == 2:
                        pair_set = set(pair_cells)
                        for m2, rr, cc in unit_cells:
                            if (rr, cc) in pair_set: continue
                            if m2 & mask:
                                m = mask
                                while m:
                                    bit = m & -m
                                    d = bit.bit_length()
                                    if self.layers.is_digit_possible_at(d, rr, cc):
                                        self.layers.forbid_choice(d, rr, cc)
                                        any_pruned = True
                                    m &= ~bit
        return any_pruned

    def apply_naked_triples(self) -> bool:
        """
        Naked Triples: Three cells in same unit have exactly THREE candidates among them.
        Remove those candidates from other cells in unit.
        """
        any_pruned = False
        N = self.grid.size
        row_cells, col_cells, box_cells = self._collect_unit_cells()

        for i in range(N):
            for unit_cells in (row_cells[i], col_cells[i], box_cells[i]):
                # Identify cells with 2 or 3 candidates
                triples = [(mask, (r, c)) for mask, r, c in unit_cells
                           if 2 <= mask.bit_count() <= 3]

                for combo in combinations(triples, 3):
                    m0, m1, m2 = combo[0][0], combo[1][0], combo[2][0]
                    union_mask = m0 | m1 | m2
                    if union_mask.bit_count() == 3:
                        triple_cells = {combo[0][1], combo[1][1], combo[2][1]}
                        for mask, rr, cc in unit_cells:
                            if (rr, cc) in triple_cells: continue
                            if mask & union_mask:
                                m = union_mask
                                while m:
                                    bit = m & -m
                                    d = bit.bit_length()
                                    if self.layers.is_digit_possible_at(d, rr, cc):
                                        self.layers.forbid_choice(d, rr, cc)
                                        any_pruned = True
                                    m &= ~bit
        return any_pruned

    def apply_hidden_pairs(self) -> bool:
        """
        Hidden Pairs: Two digits only appear in the SAME two cells in a unit.
        Remove all OTHER candidates from those two cells.
        """
        any_pruned = False
        N = self.grid.size
        box_size = self.grid.box_size
        bs_cols = N // box_size

        # Single N×N pass: build digit->cells for all rows, cols, boxes
        row_d2c = [[[] for _ in range(N + 1)] for _ in range(N)]  # row_d2c[row][digit] = cells
        col_d2c = [[[] for _ in range(N + 1)] for _ in range(N)]
        box_d2c = [[[] for _ in range(N + 1)] for _ in range(N)]

        all_masks = self.layers.get_all_allowed_masks().tolist()
        for r in range(N):
            for c in range(N):
                mask = all_masks[r][c]
                if not mask: continue
                b = (r // box_size) * bs_cols + (c // box_size)
                curr = mask
                while curr:
                    bit = curr & -curr
                    d = bit.bit_length()
                    cell = (r, c)
                    row_d2c[r][d].append(cell)
                    col_d2c[c][d].append(cell)
                    box_d2c[b][d].append(cell)
                    curr &= ~bit

        # Process all units in one loop
        for i in range(N):
            for d2c in (row_d2c[i], col_d2c[i], box_d2c[i]):
                pairs = {d: tuple(sorted(cells)) for d in range(1, N + 1)
                         if len((cells := d2c[d])) == 2}

                rev = {}
                for d, cells in pairs.items():
                    if cells not in rev: rev[cells] = []
                    rev[cells].append(d)

                for cells, digits in rev.items():
                    if len(digits) == 2:
                        mask_to_keep = (1 << (digits[0] - 1)) | (1 << (digits[1] - 1))
                        for rr, cc in cells:
                            to_remove = self.layers.get_allowed_mask(rr, cc) & ~mask_to_keep
                            if to_remove:
                                any_pruned = True
                                m = to_remove
                                while m:
                                    bit = m & -m
                                    self.layers.forbid_choice(bit.bit_length(), rr, cc)
                                    m &= ~bit
        return any_pruned

    def apply_simple_coloring(self) -> bool:
        """
        Simple Coloring (X-Chains for a single digit):
        Builds chains of conjugate pairs (units where a digit only has 2 candidates).
        Rule 1: If two cells of same color share a unit, that color is invalid.
        Rule 2: If a cell sees both colors of a chain, that digit is impossible there.
        """
        any_pruned = False
        N = self.grid.size
        bs = self.grid.box_size
        bs_cols = N // bs

        # Single N×N pass to build per-digit row/col/box lists for all digits
        all_row = [[[] for _ in range(N)] for _ in range(N + 1)]
        all_col = [[[] for _ in range(N)] for _ in range(N + 1)]
        all_box = [[[] for _ in range(N)] for _ in range(N + 1)]
        all_possible = [[] for _ in range(N + 1)]

        all_masks = self.layers.get_all_allowed_masks().tolist()
        for r in range(N):
            for c in range(N):
                mask = all_masks[r][c]
                if not mask: continue
                b = (r // bs) * bs_cols + (c // bs)
                curr = mask
                while curr:
                    bit = curr & -curr
                    d = bit.bit_length()
                    cell = (r, c)
                    all_row[d][r].append(cell)
                    all_col[d][c].append(cell)
                    all_box[d][b].append(cell)
                    all_possible[d].append(cell)
                    curr &= ~bit

        for d in range(1, N + 1):
            row_cells = all_row[d]
            col_cells = all_col[d]
            box_cells = all_box[d]
            possible_cells = all_possible[d]

            adj = {}
            for unit_list in (row_cells, col_cells, box_cells):
                for candidates in unit_list:
                    if len(candidates) == 2:
                        u, v = candidates
                        adj.setdefault(u, []).append(v)
                        adj.setdefault(v, []).append(u)
            
            if not adj: continue
            
            visited = {}
            for start_cell in adj:
                if start_cell in visited: continue
                component = []
                queue = [(start_cell, 0)]
                visited[start_cell] = 0
                idx = 0
                while idx < len(queue):
                    u, color = queue[idx]; idx += 1
                    component.append((u, color))
                    for v in adj[u]:
                        if v not in visited:
                            visited[v] = 1 - color
                            queue.append((v, 1 - color))
                
                color_groups = [[], []]
                for cell, color in component: color_groups[color].append(cell)
                
                # Build unit sets for both colors in one pass (serves Rule 1 + Rule 2)
                seen_rows = [set(), set()]
                seen_cols = [set(), set()]
                seen_boxes = [set(), set()]
                invalid_color = -1
                for color in (0, 1):
                    for cr, cc in color_groups[color]:
                        box_id = (cr // bs) * bs_cols + (cc // bs)
                        if invalid_color == -1:
                            if cr in seen_rows[color] or cc in seen_cols[color] or box_id in seen_boxes[color]:
                                invalid_color = color
                        seen_rows[color].add(cr)
                        seen_cols[color].add(cc)
                        seen_boxes[color].add(box_id)
                
                if invalid_color != -1:
                    for r, c in color_groups[invalid_color]:
                        self.layers.forbid_choice(d, r, c)
                        any_pruned = True
                    continue

                # Rule 2: Two Colors (sets already built above)
                in_component = {cell for cell, _ in component}
                for r, c in possible_cells:
                    if (r, c) in in_component:
                        continue
                    box_id = (r // bs) * bs_cols + (c // bs)
                    sees0 = r in seen_rows[0] or c in seen_cols[0] or box_id in seen_boxes[0]
                    sees1 = r in seen_rows[1] or c in seen_cols[1] or box_id in seen_boxes[1]
                    if sees0 and sees1:
                        self.layers.forbid_choice(d, r, c)
                        any_pruned = True
        return any_pruned


    def apply_full_house_signal(self) -> bool:
        """
        Independent signal that looks for any unit with exactly one empty cell.
        Uses bitmasks to quickly find the missing digit.
        """
        N = self.grid.size
        full_mask = (1 << N) - 1
        box_size = self.grid.box_size
        bs_cols = N // box_size
        moves = []

        # Vectorized empty counting
        empty = (self.grid.values == 0)
        row_cnt = empty.sum(axis=1)
        col_cnt = empty.sum(axis=0)
        box_cnt = empty.reshape(box_size, box_size, box_size, box_size).sum(axis=(1, 3)).ravel()

        for i in range(N):
            if row_cnt[i] == 1:
                row_unocc = int(full_mask & ~self.layers.row_masks[i])
                if row_unocc and (row_unocc & (row_unocc - 1)) == 0:
                    c = int(np.argmax(empty[i, :]))
                    moves.append((i, c, row_unocc.bit_length()))

            if col_cnt[i] == 1:
                col_unocc = int(full_mask & ~self.layers.col_masks[i])
                if col_unocc and (col_unocc & (col_unocc - 1)) == 0:
                    r = int(np.argmax(empty[:, i]))
                    moves.append((r, i, col_unocc.bit_length()))

            if box_cnt[i] == 1:
                box_unocc = int(full_mask & ~self.layers.box_masks[i])
                if box_unocc and (box_unocc & (box_unocc - 1)) == 0:
                    br = (i // bs_cols) * box_size
                    bc = (i % bs_cols) * box_size
                    idx = np.argwhere(empty[br:br+box_size, bc:bc+box_size])[0]
                    moves.append((br + int(idx[0]), bc + int(idx[1]), box_unocc.bit_length()))

        if not moves:
            return False

        applied = False
        for r, c, d in moves:
            if self.grid.is_empty(r, c):
                self.grid.set(r, c, d)
                self.layers._update_masks(r, c, d, True)
                self.visual.mark_forced(r, c, d)
                applied = True
        return applied

    def find_forced_moves(self) -> List[ForcedMove]:
        """
        Find forced moves in parallel using bitmask logic.
        O(N^2) complexity.
        """
        naked: List[ForcedMove] = []
        N = self.grid.size
        box_size = self.grid.box_size
        bs_cols = N // box_size

        # Naked singles + hidden singles data in a single N×N pass
        row_once = [0] * N
        row_multiple = [0] * N
        row_cell = [{} for _ in range(N)]
        col_once = [0] * N
        col_multiple = [0] * N
        col_cell = [{} for _ in range(N)]
        box_once = [0] * N
        box_multiple = [0] * N
        box_cell = [{} for _ in range(N)]

        all_masks = self.layers.get_all_allowed_masks().tolist()
        for r in range(N):
            for c in range(N):
                mask = all_masks[r][c]
                if not mask: continue
                # Naked single check
                if (mask & (mask - 1)) == 0:
                    naked.append(ForcedMove(r, c, mask.bit_length()))
                # Hidden singles accumulation
                b = (r // box_size) * bs_cols + (c // box_size)
                curr = mask
                while curr:
                    bit = curr & -curr
                    d = bit.bit_length()
                    if bit & row_once[r]:
                        row_multiple[r] |= bit
                    else:
                        row_once[r] |= bit
                        row_cell[r][d] = c
                    if bit & col_once[c]:
                        col_multiple[c] |= bit
                    else:
                        col_once[c] |= bit
                        col_cell[c][d] = r
                    if bit & box_once[b]:
                        box_multiple[b] |= bit
                    else:
                        box_once[b] |= bit
                        box_cell[b][d] = (r, c)
                    curr &= ~bit

        if naked: return self._deduplicate(naked)

        # Extract hidden singles
        forced: List[ForcedMove] = []
        for i in range(N):
            singles = row_once[i] & ~row_multiple[i]
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                forced.append(ForcedMove(i, row_cell[i][d], d))
                singles &= ~bit

            singles = col_once[i] & ~col_multiple[i]
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                forced.append(ForcedMove(col_cell[i][d], i, d))
                singles &= ~bit

            singles = box_once[i] & ~box_multiple[i]
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                rr, cc = box_cell[i][d]
                forced.append(ForcedMove(rr, cc, d))
                singles &= ~bit

        return self._deduplicate(forced)

    def _deduplicate(self, forced: List[ForcedMove]) -> List[ForcedMove]:
        unique = {}
        for mv in forced:
            unique[(mv.row, mv.col)] = mv
        return list(unique.values())

    def apply_forced_moves(self, moves: List[ForcedMove]) -> None:
        if not moves: return
        for mv in moves:
            if self.grid.is_empty(mv.row, mv.col):
                self.grid.set(mv.row, mv.col, mv.digit)
                self.layers._update_masks(mv.row, mv.col, mv.digit, True)
                self.visual.mark_forced(mv.row, mv.col, mv.digit)

    def check_for_contradictions(self) -> None:
        """
        Vectorized contradiction check using numpy.
        """
        masks = self.layers.get_all_allowed_masks()
        N = self.grid.size
        full_mask = np.int64((1 << N) - 1)
        empty = (self.grid.values == 0)

        # Zero-candidate check
        zero = np.argwhere(empty & (masks == 0))
        if len(zero):
            r, c = int(zero[0, 0]), int(zero[0, 1])
            self.visual.mark_contradiction_cell(r, c)
            raise Contradiction(f"Cell ({r},{c}) has no allowed digits.")

        # Row unions
        row_union = np.bitwise_or.reduce(masks, axis=1)
        bad_rows = (row_union | self.layers.row_masks) != full_mask
        if np.any(bad_rows):
            raise Contradiction(f"Row {int(np.argmax(bad_rows))} is missing some digits.")

        # Col unions
        col_union = np.bitwise_or.reduce(masks, axis=0)
        bad_cols = (col_union | self.layers.col_masks) != full_mask
        if np.any(bad_cols):
            raise Contradiction(f"Col {int(np.argmax(bad_cols))} is missing some digits.")

        # Box unions via reshape
        bs = self.grid.box_size
        step1 = np.bitwise_or.reduce(masks.reshape(bs, bs, bs, bs), axis=3)
        box_union = np.bitwise_or.reduce(step1, axis=1).ravel()
        bad_boxes = (box_union | self.layers.box_masks) != full_mask
        if np.any(bad_boxes):
            raise Contradiction(f"Box {int(np.argmax(bad_boxes))} is missing some digits.")

    