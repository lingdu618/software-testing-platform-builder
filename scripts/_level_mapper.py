"""Robust level mapper for ZenTao bug fields (severity / pri).

ZenTao may return these fields as int / str / str with whitespace / out-of-range.
This module normalizes them to 1-4 ints and maps to platform-internal codes.

Usage:
    from level_mapper import _level, _map_level
    severity = _map_level(bug_dict.get("severity"), SEV, SEV_CODES, "major")
"""

def _level(raw):
    """Return int 1-4, or None if invalid / empty / bool."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    # ZenTao custom levels may exceed 1-4; clamp to nearest valid level.
    return min(4, max(1, n))


def _map_level(raw, table, code_set, default):
    """Map a ZenTao level to a platform code.

    table: dict[int, str] mapping 1-4 to internal codes
    code_set: set[str] of valid internal codes (for pass-through)
    default: fallback if raw is invalid AND not a known internal code
    """
    lv = _level(raw)
    if lv is not None:
        return table[lv]
    # Already in internal encoding (e.g. re-import)
    s = str(raw).strip().lower()
    return s if s in code_set else default


if __name__ == "__main__":
    SEV = {1: "fatal", 2: "serious", 3: "major", 4: "minor"}
    SEV_CODES = {"fatal", "serious", "major", "minor", "suggestion"}
    tests = [1, "2", " 3 ", 4, 5, 6, None, "", "fatal", "unknown", True, False]
    for t in tests:
        print(f"  {t!r:10s} -> {_map_level(t, SEV, SEV_CODES, 'major')}")