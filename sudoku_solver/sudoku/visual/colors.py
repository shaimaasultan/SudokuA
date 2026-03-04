# sudoku/visual/colors.py

from math import sin, pi

def generate_digit_colors(n: int) -> dict[int, str]:
    """
    Generate n distinct-ish colors using a simple HSV-like sweep.
    Returns a dict: digit -> "#RRGGBB"
    Digits are 1..n.
    """
    colors: dict[int, str] = {}
    for d in range(1, n + 1):
        t = (d - 1) / max(1, n - 1)  # 0..1
        # Simple smooth functions for RGB in [0,1]
        r = 0.5 + 0.5 * sin(2 * pi * (t + 0.0))
        g = 0.5 + 0.5 * sin(2 * pi * (t + 1/3))
        b = 0.5 + 0.5 * sin(2 * pi * (t + 2/3))
        R = int(r * 255)
        G = int(g * 255)
        B = int(b * 255)
        colors[d] = f"#{R:02x}{G:02x}{B:02x}"
    return colors
