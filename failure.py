"""Failure comparison for chronologically ordered SLIP samples."""

from math import isfinite


def parse_values(text):
    """Read decimal-point values separated by commas or whitespace."""
    tokens = text.replace(",", " ").split()
    if not tokens:
        raise ValueError("Enter at least one parameter value.")
    values = []
    for token in tokens:
        try:
            value = float(token)
        except ValueError:
            raise ValueError(f"Invalid parameter value: {token}") from None
        if not isfinite(value):
            raise ValueError(f"Value must be finite: {token}")
        values.append(value)
    return values


def first_failure(results):
    """Return the first FS <= 1 row and crossing estimate in seconds."""
    previous = None
    for row in results:
        if row["FS"] <= 1:
            if previous is None:
                return row, None
            fraction = (previous["FS"] - 1) / (previous["FS"] - row["FS"])
            crossing = previous["time_s"] + fraction * (
                row["time_s"] - previous["time_s"]
            )
            return row, crossing
        previous = row
    return None, None
