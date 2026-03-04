# sudoku/gui_main.py

import sys
import tkinter as tk
from .solver import SudokuSolver
from .visual.tk_visual import TkVisual
from .visual.symbols import digit_to_symbol
from .examples.puzzles import example_puzzle_n9, example_puzzle_n16, example_puzzle_n25, example_puzzle_n36
from .visual.visual_hooks import VisualHooks

def main():
    sys.setrecursionlimit(5000)
    root = tk.Tk()
    root.title("Advanced Layer Sudoku Solver")
    root.configure(bg="#1e1e1e")

    # App state
    state = {
        "size": 9,
        "puzzle": example_puzzle_n9(),
        "visual": None,
        "solver": None,
        "canvas": None
    }

    header = tk.Frame(root, bg="#2d2d2d", pady=10)
    header.pack(fill="x")

    tk.Label(header, text="Select Size:", fg="white", bg="#2d2d2d", font=("Arial", 12, "bold")).pack(side="left", padx=10)

    # UI Elements references for updates
    ui_refs = {
        "status_label": None,
        "density_slider": None
    }

    def load_preset(size, density=None):
        if density is None and ui_refs["density_slider"]:
            density = ui_refs["density_slider"].get() / 100.0
        elif density is None:
            density = 0.5

        state["size"] = size
        if size == 9:
            state["puzzle"] = example_puzzle_n9(density)
        elif size == 16:
            state["puzzle"] = example_puzzle_n16(density)
        elif size == 25:
            state["puzzle"] = example_puzzle_n25(density)
        elif size == 36:
            state["puzzle"] = example_puzzle_n36(density)
        
        if ui_refs["status_label"]:
            ui_refs["status_label"].config(text="READY", fg="#888888")
        setup_board()

    # Size buttons
    for s in [9, 16, 25, 36]:
        btn = tk.Button(header, text=f"{s}x{s}", command=lambda size=s: load_preset(size),
                        bg="#3d3d3d", fg="white", relief="flat", padx=10)
        btn.pack(side="left", padx=5)

    # Density Slider
    tk.Label(header, text="Density:", fg="white", bg="#2d2d2d", font=("Arial", 10)).pack(side="left", padx=(20, 5))
    density_slider = tk.Scale(header, from_=10, to=90, orient="horizontal", bg="#2d2d2d", fg="white", 
                              highlightthickness=0, length=150, relief="flat")
    density_slider.set(50)
    density_slider.pack(side="left", padx=5)
    ui_refs["density_slider"] = density_slider

    # New Grid button
    new_btn = tk.Button(header, text="[ NEW GRID ]", command=lambda: load_preset(state["size"]),
                        bg="#1a1a1a", fg="#00ff00", relief="flat", font=("Arial", 10, "bold"), padx=10)
    new_btn.pack(side="left", padx=10)

    board_container = tk.Frame(root, bg="#1e1e1e", padx=20, pady=20)
    board_container.pack()

    def setup_board():
        if state["canvas"]:
            state["canvas"].destroy()
        
        size = state["size"]
        max_board_pixels = 700
        cell_size = max(18, max_board_pixels // size)

        canvas = tk.Canvas(board_container, width=size * cell_size, height=size * cell_size, 
                           bg="#ffffff", highlightthickness=0)
        canvas.pack()
        state["canvas"] = canvas

        visual = TkVisual(root, canvas, size=size, cell_size=cell_size)
        state["visual"] = visual
        state["solver"] = SudokuSolver(size=size, visual=visual)

        puzzle = state["puzzle"]
        for r in range(size):
            for c in range(size):
                v = puzzle[r][c]
                if v != 0:
                    visual.original_cells.add((r, c))
                    rect = visual.rects[(r, c)]
                    txt = visual.texts[(r, c)]
                    canvas.itemconfig(rect, fill="#e0e0e0", outline="#333333", width=2)
                    symbol = digit_to_symbol(v)
                    canvas.itemconfig(txt, text=symbol, font=("Arial", int(cell_size * 0.5), "bold"), fill="#1a1a1a")

    def run_solver():
        if not state["solver"]: return
        ui_refs["status_label"].config(text="SOLVING...", fg="#FFC107")
        root.update()
        
        solution = state["solver"].solve(state["puzzle"])
        solve_time = state["solver"].last_solve_time

        if solution is None:
            print("No solution found in this branch. Backtracking...")
            solution = state["solver"].backtrack_and_continue()
            # If backtrack find solution, we don't have a fresh timer for it easily 
            # without more changes, but let's stick to the main solve timer.

        if not solution:
            print("Puzzle is unsolvable.")
            ui_refs["status_label"].config(text=f"UNSOLVABLE ({solve_time:.3f}s)", fg="#F44336")
        else:
            print("Solved.")
            ui_refs["status_label"].config(text=f"SOLVED! ({solve_time:.3f}s)", fg="#4CAF50")
            # --- FORCE FINAL RENDER ---
            for r in range(state["size"]):
                for c in range(state["size"]):
                    v = solution.get(r, c)
                    # Use mark_forced to fill in the final digits with color
                    state["visual"].mark_forced(r, c, v)

    footer = tk.Frame(root, bg="#2d2d2d", pady=10)
    footer.pack(fill="x")

    # Status Label
    status_label = tk.Label(footer, text="READY", fg="#888888", bg="#2d2d2d", font=("Arial", 14, "bold"))
    status_label.pack(side="top", pady=5)
    ui_refs["status_label"] = status_label

    solve_btn = tk.Button(footer, text="SOLVE PUZZLE", command=run_solver,
                          bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), 
                          relief="flat", padx=20, pady=5)
    solve_btn.pack(side="top")

    setup_board()
    root.mainloop()


if __name__ == "__main__":
    main()
