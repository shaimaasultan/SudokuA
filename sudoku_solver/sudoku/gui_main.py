# sudoku/gui_main.py

import sys
import tkinter as tk
import threading
from .solver import SudokuSolver
from .visual.tk_visual import TkVisual
from .visual.symbols import digit_to_symbol
from .examples.puzzles import example_puzzle_n9, example_puzzle_n16, example_puzzle_n25, example_puzzle_n36, example_puzzle_n49
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
        "canvas": None,
        "window_open": True,
        "solver_thread": None,
        "solving": False
    }

    header = tk.Frame(root, bg="#2d2d2d", pady=10)
    header.pack(fill="x")

    tk.Label(header, text="Select Size:", fg="white", bg="#2d2d2d", font=("Arial", 12, "bold")).pack(side="left", padx=10)

    # UI Elements references for updates
    ui_refs = {
        "status_label": None,
        "density_slider": None,
        "size_buttons": [],
        "new_grid_btn": None,
        "stop_btn": None,
        "solve_btn": None
    }

    def load_preset(size, density=None):
        if state["solving"]:
            return  # Don't allow loading while solving
        
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
        elif size == 49:
            state["puzzle"] = example_puzzle_n49(density)
        
        if ui_refs["status_label"]:
            ui_refs["status_label"].config(text="READY", fg="#888888")
        setup_board()

    def stop_solver():
        """Stop the current solver and reload the grid"""
        if state["solving"] and state["solver"]:
            state["solver"].stop_requested = True
            print("STOP: Solver interrupted by user.")
            # Wait briefly for the solver thread to detect the stop flag
            # and exit gracefully (max 100ms)
            for _ in range(10):
                if not state["solving"]:
                    break
                root.after(10)
        
        # Reload the board
        if ui_refs["status_label"]:
            ui_refs["status_label"].config(text="READY", fg="#888888")
        setup_board()
        
        # Re-enable all buttons
        set_buttons_enabled(True)

    def set_buttons_enabled(enabled: bool):
        """Enable or disable all control buttons (except STOP which is always enabled)"""
        state_str = "normal" if enabled else "disabled"
        for btn in ui_refs["size_buttons"]:
            btn.config(state=state_str)
        if ui_refs["new_grid_btn"]:
            ui_refs["new_grid_btn"].config(state=state_str)
        if ui_refs["solve_btn"]:
            ui_refs["solve_btn"].config(state=state_str)
        # Keep STOP button always enabled
        if ui_refs["stop_btn"]:
            ui_refs["stop_btn"].config(state="normal")

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

    def run_solver_thread():
        """Run solver in background thread"""
        if not state["solver"] or state["solving"]:
            return
        
        state["solving"] = True
        
        # Disable buttons from main thread
        root.after(0, lambda: set_buttons_enabled(False))
        root.after(0, lambda: ui_refs["status_label"].config(text="SOLVING...", fg="#FFC107"))
        
        solution = state["solver"].solve(state["puzzle"])
        solve_time = state["solver"].last_solve_time

        if not state["window_open"] or state["solver"].stop_requested:
            state["solving"] = False
            return

        if solution is None:
            solution = state["solver"].backtrack_and_continue()

        if not state["window_open"] or state["solver"].stop_requested:
            state["solving"] = False
            return

        # Update GUI safely from background thread using root.after()
        if not solution:
            print("Puzzle is unsolvable.")
            if state["window_open"] and not state["solver"].stop_requested:
                root.after(0, lambda: ui_refs["status_label"].config(text=f"UNSOLVABLE ({solve_time:.3f}s)", fg="#F44336"))
        else:
            print("Solved.")
            if state["window_open"] and not state["solver"].stop_requested:
                root.after(0, lambda: ui_refs["status_label"].config(text=f"SOLVED! ({solve_time:.3f}s)", fg="#4CAF50"))
                for r in range(state["size"]):
                    for c in range(state["size"]):
                        v = solution.get(r, c)
                        state["visual"].mark_forced(r, c, v)
        
        state["solving"] = False
        
        # Re-enable buttons from main thread
        if state["window_open"]:
            root.after(0, lambda: set_buttons_enabled(True))

    def run_solver():
        """Trigger solver in background thread"""
        if state["solving"]:
            return
        
        if state["solver"]:
            state["solver"].stop_requested = False  # Reset stop flag
        state["solver_thread"] = threading.Thread(target=run_solver_thread, daemon=True)
        state["solver_thread"].start()

    # Size buttons
    for s in [9, 16, 25, 36, 49]:
        btn = tk.Button(header, text=f"{s}x{s}", command=lambda size=s: load_preset(size),
                        bg="#3d3d3d", fg="white", relief="flat", padx=10)
        btn.pack(side="left", padx=5)
        ui_refs["size_buttons"].append(btn)

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
    ui_refs["new_grid_btn"] = new_btn

    # Stop button - stops solver and reloads current puzzle
    stop_btn = tk.Button(header, text="[ STOP ]", command=stop_solver,
                         bg="#1a1a1a", fg="#FF6B6B", relief="flat", font=("Arial", 10, "bold"), padx=10)
    stop_btn.pack(side="left", padx=5)
    ui_refs["stop_btn"] = stop_btn

    # Status Label
    status_label = tk.Label(header, text="READY", fg="#888888", bg="#2d2d2d", font=("Arial", 11, "bold"))
    status_label.pack(side="left", padx=20)
    ui_refs["status_label"] = status_label

    # Solve button
    solve_btn = tk.Button(header, text="[ SOLVE PUZZLE ]", command=run_solver,
                          bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), 
                          relief="flat", padx=15, pady=2)
    solve_btn.pack(side="left", padx=10)
    ui_refs["solve_btn"] = solve_btn

    board_container = tk.Frame(root, bg="#1e1e1e", padx=20, pady=20)
    board_container.pack()

    def on_closing():
        """Handle window close event"""
        state["window_open"] = False
        root.destroy()

    # Set window close handler
    root.protocol("WM_DELETE_WINDOW", on_closing)

    setup_board()
    root.mainloop()


if __name__ == "__main__":
    main()
