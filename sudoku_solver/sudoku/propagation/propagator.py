# sudoku/propagation/propagator.py

from dataclasses import dataclass
from typing import List, Tuple
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
    Handles logical propagation on layers with incremental updates:
    - Track dirty cells that changed
    - Do incremental layer rebuilds
    - Early contradiction detection
    - Lazy constraint application
    """

    def __init__(self, grid: Grid, layers: LayerManager, visual: VisualHooks):
        self.grid = grid
        self.layers = layers
        self.visual = visual
        self.dirty_cells = set()  # Track changed cells for incremental updates

    def rebuild_all_layers(self) -> None:
        self.layers.rebuild_all_layers()

    def do_incremental_update(self) -> None:
        """
        Phase 1 Optimization: Incrementally rebuild affected units.
        Only rebuilds the units affected by dirty cells, not entire grid.
        """
        if self.dirty_cells:
            self.layers.rebuild_affected_units(self.dirty_cells)
            self.dirty_cells.clear()

    def run_propagation(self, solver=None) -> None:
        """
        Repeatedly apply forced moves and advanced pruning until no more exist 
        or a contradiction is found.
        Phase 1: Uses incremental updates and early contradiction detection.
        """
        self.visual.start_batch()
        self.dirty_cells.clear()  # Start fresh
        # Initial rebuild for the starting state
        self.layers.rebuild_all_layers()
        try:
            while True:
                # Check for stop request
                if solver and solver.stop_requested:
                    return
                
                # Do incremental layer update if cells changed since last iteration
                self.do_incremental_update()
                
                # Phase 1: Early contradiction detection - check immediately
                self.check_for_contradictions()
                
                # 1. Independent "Signal" check (Full House)
                # This is extremely fast now with bitmasks.
                found_full_house = self.apply_full_house_signal()
                if found_full_house:
                    continue
                
                # 2. Standard forced moves (naked/hidden singles) - Optimized with bitmasks
                forced = self.find_forced_moves()
                if forced:
                    self.apply_forced_moves(forced)
                    # Update layers for newly assigned cells
                    self.do_incremental_update()
                    self.check_for_contradictions()  # Early detect
                    continue
                
                # 3. Advanced Pruning (only if needed)
                pruned = False
                pruned |= self.apply_pointing_pairs()
                pruned |= self.apply_naked_pairs()
                pruned |= self.apply_hidden_pairs()
                pruned |= self.apply_simple_coloring()

                if pruned:
                    self.do_incremental_update()
                    self.check_for_contradictions()  # Early detect
                    continue
                
                # No progress, we're done with propagation
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
        digits = self.layers.digits
        any_pruned = False

        for d in digits:
            for br in range(0, N, box_size):
                for bc in range(0, N, box_size):
                    # Find all candidates for digit d in this box
                    candidates = []
                    for dr in range(box_size):
                        for dc in range(box_size):
                            rr, cc = br + dr, bc + dc
                            if self.layers.is_digit_possible_at(d, rr, cc):
                                candidates.append((rr, cc))
                    
                    if not candidates:
                        continue
                    
                    # Check Row alignment
                    rows = {r for (r, c) in candidates}
                    if len(rows) == 1:
                        target_r = list(rows)[0]
                        for col in range(N):
                            if col >= bc and col < bc + box_size:
                                continue
                            if self.layers.is_digit_possible_at(d, target_r, col):
                                self.layers.forbid_choice(d, target_r, col)
                                any_pruned = True

                    # Check Col alignment
                    cols = {c for (r, c) in candidates}
                    if len(cols) == 1:
                        target_c = list(cols)[0]
                        for row in range(N):
                            if row >= br and row < br + box_size:
                                continue
                            if self.layers.is_digit_possible_at(d, row, target_c):
                                self.layers.forbid_choice(d, row, target_c)
                                any_pruned = True

        return any_pruned

    def apply_naked_pairs(self) -> bool:
        """
        Naked Pairs: Two cells in same unit have same TWO candidates.
        Remove those candidates from other cells in unit.
        """
        any_pruned = False
        N = self.grid.size
        # Row, Col, Box
        for unit_type in ['row', 'col', 'box']:
            for i in range(N):
                # Identify candidates
                masks = {} # mask -> list of (r, c)
                for j in range(N):
                    r, c = self._get_unit_coords(unit_type, i, j)
                    if not self.grid.is_empty(r, c): continue
                    mask = self.layers.get_allowed_mask(r, c)
                    if bin(mask).count('1') == 2:
                        if mask not in masks: masks[mask] = []
                        masks[mask].append((r, c))
                
                # Apply pruning
                for mask, cells in masks.items():
                    if len(cells) == 2:
                        for j in range(N):
                            rr, cc = self._get_unit_coords(unit_type, i, j)
                            if (rr, cc) in cells: continue
                            if not self.grid.is_empty(rr, cc): continue
                            if self.layers.get_allowed_mask(rr, cc) & mask:
                                # Forbid digits in mask
                                m = mask
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
        for unit_type in ['row', 'col', 'box']:
            for i in range(N):
                # Map digit -> list of cells
                digit_to_cells = {d: [] for d in range(1, N + 1)}
                for j in range(N):
                    r, c = self._get_unit_coords(unit_type, i, j)
                    if not self.grid.is_empty(r, c): continue
                    mask = self.layers.get_allowed_mask(r, c)
                    curr = mask
                    while curr:
                        bit = curr & -curr
                        d = bit.bit_length()
                        digit_to_cells[d].append((r, c))
                        curr &= ~bit
                
                # Find digits that appear in exactly 2 cells
                pairs = {d: tuple(sorted(cells)) for d, cells in digit_to_cells.items() if len(cells) == 2}
                
                # See if two digits share the same 2 cells
                rev = {} # cells -> list of digits
                for d, cells in pairs.items():
                    if cells not in rev: rev[cells] = []
                    rev[cells].append(d)
                
                for cells, digits in rev.items():
                    if len(digits) == 2:
                        # HIDDEN PAIR! Digits in 'digits' are locked in 'cells'.
                        # Remove all other digits from 'cells'.
                        mask_to_keep = 0
                        for d in digits: mask_to_keep |= (1 << (d - 1))
                        
                        for rr, cc in cells:
                            curr_mask = self.layers.get_allowed_mask(rr, cc)
                            to_remove = curr_mask & ~mask_to_keep
                            if to_remove:
                                m = to_remove
                                while m:
                                    bit = m & -m
                                    dd = bit.bit_length()
                                    if self.layers.is_digit_possible_at(dd, rr, cc):
                                        self.layers.forbid_choice(dd, rr, cc)
                                        any_pruned = True
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
        for d in range(1, N + 1):
            adj = {} # cell -> list of cells
            for unit_type in ['row', 'col', 'box']:
                for i in range(N):
                    candidates = []
                    for j in range(N):
                        r, c = self._get_unit_coords(unit_type, i, j)
                        if self.layers.is_digit_possible_at(d, r, c):
                            candidates.append((r, c))
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
                
                # Rule 1: Twice in a Unit
                invalid_color = -1
                for color in [0, 1]:
                    group = color_groups[color]
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            if self._share_unit(group[i], group[j]):
                                invalid_color = color; break
                        if invalid_color != -1: break
                
                if invalid_color != -1:
                    for r, c in color_groups[invalid_color]:
                        self.layers.forbid_choice(d, r, c)
                        any_pruned = True
                    continue

                # Rule 2: Two Colors
                in_component = {cell for cell, _ in component}
                for r in range(N):
                    for c in range(N):
                        if (r, c) in in_component or not self.layers.is_digit_possible_at(d, r, c):
                            continue
                        sees0 = any(self._share_unit((r, c), c0) for c0 in color_groups[0])
                        sees1 = any(self._share_unit((r, c), c1) for c1 in color_groups[1])
                        if sees0 and sees1:
                            self.layers.forbid_choice(d, r, c)
                            any_pruned = True
        return any_pruned

    def _share_unit(self, p1: tuple[int, int], p2: tuple[int, int]) -> bool:
        r1, c1 = p1; r2, c2 = p2
        if r1 == r2 or c1 == c2: return True
        bs = self.grid.box_size
        return (r1 // bs == r2 // bs) and (c1 // bs == c2 // bs)

    def _get_unit_coords(self, unit_type: str, idx: int, pos: int) -> tuple[int, int]:
        N = self.grid.size
        if unit_type == 'row': return idx, pos
        if unit_type == 'col': return pos, idx
        box_size = self.grid.box_size
        br = (idx // box_size) * box_size
        bc = (idx % box_size) * box_size
        return br + (pos // box_size), bc + (pos % box_size)

    def apply_full_house_signal(self) -> bool:
        """
        Independent signal that looks for any unit with exactly one empty cell.
        Uses bitmasks to quickly find the missing digit.
        """
        N = self.grid.size
        full_mask = (1 << N) - 1
        moves = []

        # Rows
        for r in range(N):
            occupied = self.layers.row_masks[r]
            unoccupied = full_mask & ~occupied
            # check if exactly one bit is set (popcount == 1)
            if unoccupied and (unoccupied & (unoccupied - 1)) == 0:
                # Find which col is empty
                empty_cols = [c for c in range(N) if self.grid.is_empty(r, c)]
                if len(empty_cols) == 1:
                    d = unoccupied.bit_length()
                    moves.append((r, empty_cols[0], d))

        # Cols
        for c in range(N):
            occupied = self.layers.col_masks[c]
            unoccupied = full_mask & ~occupied
            if unoccupied and (unoccupied & (unoccupied - 1)) == 0:
                empty_rows = [r for r in range(N) if self.grid.is_empty(r, c)]
                if len(empty_rows) == 1:
                    d = unoccupied.bit_length()
                    moves.append((empty_rows[0], c, d))

        # Boxes
        box_size = self.grid.box_size
        for b in range(N):
            occupied = self.layers.box_masks[b]
            unoccupied = full_mask & ~occupied
            if unoccupied and (unoccupied & (unoccupied - 1)) == 0:
                br = (b // box_size) * box_size
                bc = (b % box_size) * box_size
                empty_cells = [(br + dr, bc + dc) for dr in range(box_size) for dc in range(box_size) 
                                if self.grid.is_empty(br + dr, bc + dc)]
                if len(empty_cells) == 1:
                    d = unoccupied.bit_length()
                    moves.append((empty_cells[0][0], empty_cells[0][1], d))

        if not moves:
            return False

        applied = False
        for r, c, d in moves:
            if self.grid.is_empty(r, c):
                self.grid.set(r, c, d)
                self.visual.mark_forced(r, c, d)
                self.dirty_cells.add((r, c))
                applied = True
        
        # Don't rebuild here - let do_incremental_update handle it with Phase 1 optimization
        return applied

    def find_forced_moves(self) -> List[ForcedMove]:
        """
        Find forced moves in parallel using bitmask logic.
        O(N^2) complexity.
        """
        forced: List[ForcedMove] = []
        N = self.grid.size
        
        # 1. Naked Singles (Cell has only 1 allowed digit)
        for r, c in self.grid.iter_cells():
            if not self.grid.is_empty(r, c):
                continue
            mask = self.layers.get_allowed_mask(r, c)
            if mask and (mask & (mask - 1)) == 0:
                forced.append(ForcedMove(r, c, mask.bit_length()))
        
        if forced: return self._deduplicate(forced)

        # 2. Hidden Singles (Digit is allowed in only one cell in a unit)
        
        # Rows
        for r in range(N):
            once = 0
            multiple = 0
            cell_for_digit = {} # digit -> col
            for c in range(N):
                if not self.grid.is_empty(r, c): continue
                mask = self.layers.get_allowed_mask(r, c)
                curr = mask
                while curr:
                    bit = curr & -curr
                    d = bit.bit_length()
                    if bit & once:
                        multiple |= bit
                    else:
                        once |= bit
                        cell_for_digit[d] = c
                    curr &= ~bit
            
            singles = once & ~multiple
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                forced.append(ForcedMove(r, cell_for_digit[d], d))
                singles &= ~bit

        # Cols (Similar logic)
        for c in range(N):
            once = 0
            multiple = 0
            cell_for_digit = {} # digit -> row
            for r in range(N):
                if not self.grid.is_empty(r, c): continue
                mask = self.layers.get_allowed_mask(r, c)
                curr = mask
                while curr:
                    bit = curr & -curr
                    d = bit.bit_length()
                    if bit & once:
                        multiple |= bit
                    else:
                        once |= bit
                        cell_for_digit[d] = r
                    curr &= ~bit
            
            singles = once & ~multiple
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                forced.append(ForcedMove(cell_for_digit[d], c, d))
                singles &= ~bit

        # Boxes
        box_size = self.grid.box_size
        for b in range(N):
            br = (b // box_size) * box_size
            bc = (b % box_size) * box_size
            once = 0
            multiple = 0
            cell_for_digit = {} # digit -> (r, c)
            for dr in range(box_size):
                for dc in range(box_size):
                    r, c = br + dr, bc + dc
                    if not self.grid.is_empty(r, c): continue
                    mask = self.layers.get_allowed_mask(r, c)
                    curr = mask
                    while curr:
                        bit = curr & -curr
                        d = bit.bit_length()
                        if bit & once:
                            multiple |= bit
                        else:
                            once |= bit
                            cell_for_digit[d] = (r, c)
                        curr &= ~bit
            
            singles = once & ~multiple
            while singles:
                bit = singles & -singles
                d = bit.bit_length()
                rr, cc = cell_for_digit[d]
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
                self.visual.mark_forced(mv.row, mv.col, mv.digit)
                self.dirty_cells.add((mv.row, mv.col))
        # Don't rebuild here - let do_incremental_update handle it with Phase 1 optimization

    def check_for_contradictions(self) -> None:
        """
        Optimized contradiction check using bitmasks.
        """
        N = self.grid.size
        full_mask = (1 << N) - 1

        # Any empty cell with no allowed digits?
        for r, c in self.grid.iter_cells():
            if self.grid.is_empty(r, c):
                if self.layers.get_allowed_mask(r, c) == 0:
                    self.visual.mark_contradiction_cell(r, c)
                    raise Contradiction(f"Cell ({r},{c}) has no allowed digits.")

        # Any digit with no place in a unit?
        # A digit d has no place in a unit if U_allowed_mask & (1 << (d-1)) is 0 
        # for all empty cells, AND it's not already in the unit.
        
        for i in range(N):
            # Rows
            row_union = 0
            for c in range(N):
                if self.grid.is_empty(i, c):
                    row_union |= self.layers.get_allowed_mask(i, c)
            if (row_union | self.layers.row_masks[i]) != full_mask:
                raise Contradiction(f"Row {i} is missing some digits.")

            # Cols
            col_union = 0
            for r in range(N):
                if self.grid.is_empty(r, i):
                    col_union |= self.layers.get_allowed_mask(r, i)
            if (col_union | self.layers.col_masks[i]) != full_mask:
                raise Contradiction(f"Col {i} is missing some digits.")

            # Boxes
            box_union = 0
            box_size = self.grid.box_size
            br = (i // box_size) * box_size
            bc = (i % box_size) * box_size
            for dr in range(box_size):
                for dc in range(box_size):
                    if self.grid.is_empty(br+dr, bc+dc):
                        box_union |= self.layers.get_allowed_mask(br+dr, bc+dc)
            if (box_union | self.layers.box_masks[i]) != full_mask:
                raise Contradiction(f"Box {i} is missing some digits.")

    