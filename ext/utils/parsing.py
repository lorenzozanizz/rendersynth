""" Parsing utilities for I/O operations involving the pipeline like
parsing floats, lists, etc...
"""

from typing import Any, List, Optional

def parse_floats(text: Any) -> Optional[List[float]]:
    """Parse a comma-separated number list; None if anything is malformed."""
    out: List[float] = []
    for tok in str(text).split(','):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(float(tok))
        except ValueError:
            return None
    return out or None
