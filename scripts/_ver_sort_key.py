"""Firmware version sort key — used to order Excel sheet names as version numbers.

Rules:
  - sheet* / Sheet1 / Sheet2 → baseline (排序最前，idx 0)
  - launcher_V3 / V5版本 / V8 → 按 V 后面的数字升序 (idx 1)
  - 其它（任意名字）→ 中间 (idx 2)
  - 含"压测" → 最后 (idx 3)

Usage:
    versions = sorted(set_of_versions, key=lambda v: _ver_sort_key(v, 0))
"""
import re


def _ver_sort_key(name, idx=0):
    """Return a tuple (group, num, original_idx) for sorting."""
    n = name or ""
    m = re.search(r"(?:launcher_V|V)(\d+)(?:版本)?", n)
    if m:
        return (1, int(m.group(1)), idx)
    if re.match(r"^sheet\d*$", n.strip(), re.I):
        return (0, 0, idx)
    if "压测" in n:
        return (3, 0, idx)
    return (2, 0, idx)


def _norm_version_name(name):
    """Rename default Excel sheet names (Sheet1/Sheet2...) to readable versions."""
    if not name:
        return name
    m = re.match(r"^sheet(\d+)$", str(name).strip(), re.I)
    if m:
        return f"V{m.group(1)}版本"
    return name


if __name__ == "__main__":
    # Demo / self-test
    samples = ["Sheet1", "Sheet2", "V3", "V5", "V8", "V1版本",
               "更新so库+launcher_V3+APP_V6", "更新so库+launcher_V10+BTapk+APP_V8",
               "V8压测", "(未指定)", ""]
    sorted_names = sorted(set(samples), key=lambda v: _ver_sort_key(v, 0))
    print("Original:", samples)
    print("Sorted:  ", sorted_names)
    print("Normalized demo: Sheet1 ->", _norm_version_name("Sheet1"))