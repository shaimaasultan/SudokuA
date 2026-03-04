# sudoku/visual/tk_visual.py

import time
import tkinter as tk
from .visual_hooks import VisualHooks
from .colors import generate_digit_colors
from .symbols import digit_to_symbol


class TkVisual(VisualHooks):
    def __init__(self, root: tk.Tk, canvas: tk.Canvas, size: int, cell_size: int = 50):
        self.root = root
        self.canvas = canvas
        self.size = size
        self.cell_size = cell_size

        # generate colors for all digits 1..size
        self.digit_colors = generate_digit_colors(size)

        self.rects: dict[tuple[int, int], int] = {}
        self.texts: dict[tuple[int, int], int] = {}
        self.original_cells: set[tuple[int, int]] = set()
        self.batch_mode = False

        self._build_grid()

    def _build_grid(self):
        N = self.size
        cs = self.cell_size
        for r in range(N):
            for c in range(N):
                x1 = c * cs
                y1 = r * cs
                x2 = x1 + cs
                y2 = y1 + cs
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="black",
                    width=1,
                    fill="white",
                )
                txt = self.canvas.create_text(
                    x1 + cs / 2,
                    y1 + cs / 2,
                    text="",
                    font=("Arial", int(cs * 0.5)),
                )
                self.rects[(r, c)] = rect
                self.texts[(r, c)] = txt

        box = int(self.size ** 0.5)
        for i in range(self.size + 1):
            w = 3 if i % box == 0 else 1
            # vertical
            self.canvas.create_line(
                i * cs, 0, i * cs, N * cs,
                width=w
            )
            # horizontal
            self.canvas.create_line(
                0, i * cs, N * cs, i * cs,
                width=w
            )

    def _refresh(self):
        if self.batch_mode:
            return
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            # Window was probably closed
            pass

    def _safe_canvas_call(self, func, *args, **kwargs):
        """Safely call a canvas method, catching TclErrors."""
        try:
            return func(*args, **kwargs)
        except tk.TclError:
            return None

    def _set_cell(self, r: int, c: int, d: int, fill: str, outline: str, width: int, italic: bool = False):
        rect = self.rects.get((r, c))
        txt = self.texts.get((r, c))
        if rect is None or txt is None:
            return

        self._safe_canvas_call(self.canvas.itemconfig, rect, fill=fill, outline=outline, width=width)
        font_style = "italic" if italic else "normal"
        symbol = digit_to_symbol(d)
        self._safe_canvas_call(self.canvas.itemconfig, txt, text=symbol, font=("Arial", int(self.cell_size * 0.5), font_style))

        self._refresh()

    def _flash_cell(self, r: int, c: int, color: str, duration_ms: int = 150):
        rect = self.rects.get((r, c))
        if rect is None:
            return
            
        old_fill = self._safe_canvas_call(self.canvas.itemcget, rect, "fill")
        if old_fill is None: return
        
        self._safe_canvas_call(self.canvas.itemconfig, rect, fill=color)
        self._refresh()
        
        def reset():
            self._safe_canvas_call(self.canvas.itemconfig, rect, fill=old_fill)
            
        self.root.after(duration_ms, reset)
        self._refresh()

    def mark_forced(self, r: int, c: int, d: int) -> None:
        if (r, c) in self.original_cells:
            # Original cells stay gray
            self._set_cell(r, c, d, fill="#e0e0e0", outline="#333333", width=2, italic=False)
            return
            
        color = self.digit_colors.get(d, "#000000")
        self._set_cell(r, c, d, fill=color, outline="black", width=2, italic=False)
        self._flash_cell(r, c, "#ffffff", duration_ms=80)

    def mark_guess(self, r: int, c: int, d: int) -> None:
        if (r, c) in self.original_cells: return
        color = self.digit_colors.get(d, "#000000")
        self._set_cell(r, c, d, fill=color, outline="gold", width=3, italic=True)
        time.sleep(0.05)
        self._refresh()

    def mark_contradiction_cell(self, r: int, c: int) -> None:
        rect = self.rects.get((r, c))
        if rect is None: return
        
        old_outline = self._safe_canvas_call(self.canvas.itemcget, rect, "outline")
        old_width = self._safe_canvas_call(self.canvas.itemcget, rect, "width")
        if old_outline is None: return

        self._safe_canvas_call(self.canvas.itemconfig, rect, outline="red", width=4)
        self._refresh()
        time.sleep(0.15)
        self._safe_canvas_call(self.canvas.itemconfig, rect, outline=old_outline, width=old_width)
        self._refresh()
    
    def mark_digit_branch(self, d: int, r: int, c: int):
        rect = self.rects.get((r, c))
        if rect is None: return
        old = self._safe_canvas_call(self.canvas.itemcget, rect, "fill")
        if old is None: return
        self._safe_canvas_call(self.canvas.itemconfig, rect, fill="#00ffff")  # cyan
        self._refresh()
        self.root.after(120, lambda: self._safe_canvas_call(self.canvas.itemconfig, rect, fill=old))
        self._refresh()

    def mark_cell_fallback(self, r: int, c: int, allowed: list):
        rect = self.rects.get((r, c))
        if rect is None: return
        old = self._safe_canvas_call(self.canvas.itemcget, rect, "fill")
        if old is None: return
        self._safe_canvas_call(self.canvas.itemconfig, rect, fill="#ff00ff")  # magenta
        self._refresh()
        self.root.after(120, lambda: self._safe_canvas_call(self.canvas.itemconfig, rect, fill=old))
        self._refresh()

    def mark_cell_heat(self, r: int, c: int, heat_score: float) -> None:
        """Color cell background based on conflict heat (Reverted)."""
        pass


    def start_batch(self) -> None:
        self.batch_mode = True

    def end_batch(self) -> None:
        self.batch_mode = False
        self._refresh()

