# sudoku/visual/symbols.py

def digit_to_symbol(d: int) -> str:
    """
    Map digit index (1-based) to a display symbol.
    1-9   -> "1".."9"
    10-35 -> "A".."Z"
    36-61 -> "a".."z"
    beyond -> "?"
    """
    if 1 <= d <= 9:
        return str(d)
    if 10 <= d <= 35:
        return chr(ord("A") + (d - 10))
    if 36 <= d <= 61:
        return chr(ord("a") + (d - 36))
    return str(d) if d > 0 else ""
