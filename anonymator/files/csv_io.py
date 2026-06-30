import csv

_CANDIDATES = [";", "|", ",", "\t"]


def sniff_delimiter(sample: str) -> str:
    """Detect CSV delimiter from a text sample.

    Strategy: for each candidate, check that it appears a consistent number of
    times on every non-empty line.  Pick the candidate with the highest
    consistent per-line count.  Falls back to ";" when nothing matches.
    """
    lines = [l for l in sample.splitlines() if l]
    if not lines:
        return ";"

    best_delim = ";"
    best_count = 0

    for delim in _CANDIDATES:
        counts = [line.count(delim) for line in lines]
        if counts and all(c == counts[0] for c in counts) and counts[0] > 0:
            if counts[0] > best_count:
                best_count = counts[0]
                best_delim = delim

    return best_delim
