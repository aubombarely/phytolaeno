"""Parsing helpers for structured text fields in the benchmark data."""
import re


def parse_busco(raw: str) -> dict:
    """Parse 'C:98.1%[S:76.0%,D:22.1%],F:1.2%,M:0.7%' into numeric fields."""
    if not raw or str(raw).strip() in ("", "nan"):
        return {}
    m = re.search(
        r"C:([\d.]+)%\[S:([\d.]+)%,D:([\d.]+)%\],F:([\d.]+)%,M:([\d.]+)%",
        str(raw),
    )
    if not m:
        return {}
    return {
        "complete":    float(m.group(1)),
        "single":      float(m.group(2)),
        "duplicated":  float(m.group(3)),
        "fragmented":  float(m.group(4)),
        "missing":     float(m.group(5)),
    }


def parse_earlgrey(raw: str) -> dict:
    """Parse 'DNA:7.80%;RC:2.32%;LTR:34.86%;...' into a dict of floats."""
    if not raw or str(raw).strip() in ("", "nan"):
        return {}
    result = {}
    for part in str(raw).split(";"):
        part = part.strip()
        if ":" in part:
            k, _, v = part.partition(":")
            try:
                result[k.strip()] = float(v.strip().rstrip("%"))
            except ValueError:
                pass
    return result


def extract_tool_info(methodology: str) -> tuple[str, str]:
    """Return (tool_name, tool_version) from an Annotation_Methodology string."""
    if not methodology or str(methodology).strip() in ("", "nan"):
        return "Unknown", ""
    s = str(methodology)
    # Pattern: "AbI: TOOLNAME vX.Y.Z"
    m = re.match(r"AbI:\s*([A-Za-z0-9_+\-]+)[\s,;].*?[vV]([\d.]+)", s)
    if m:
        return m.group(1).rstrip(",.;"), m.group(2)
    m = re.match(r"AbI:\s*([A-Za-z0-9_+\-]+)", s)
    if m:
        return m.group(1).rstrip(",.;"), ""
    return s.split()[0].rstrip(",.;"), ""


def safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if str(val).strip() == "nan" else f
    except (TypeError, ValueError):
        return None


def safe_int(val) -> int | None:
    try:
        f = float(val)
        return None if str(val).strip() == "nan" else int(f)
    except (TypeError, ValueError):
        return None
