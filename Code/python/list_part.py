"""
Extract all *PART entries (PID + name) from a THUMS LS-DYNA keyword file,
following *INCLUDE chains automatically.

Usage:
    python list_parts.py main_THUMS_AM50_V41.k
    python list_parts.py main_THUMS_AM50_V41.k skull
    python list_parts.py main_THUMS_AM50_V41.k skull brain dura csf
"""
import os, sys

def parse_parts(path, _visited=None, _base_dir=None):
    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))

    real_path = os.path.abspath(path)
    if real_path in _visited:
        return []
    _visited.add(real_path)

    parts = []   # list of (pid, name, source_file)
    section = None
    pending_include = False
    pending_part_header = False
    current_pid = None
    current_name = None

    with open(path, "r", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")

            # --- keyword detection ---
            if line.startswith("*"):
                kw = line.strip().upper()
                pending_part_header = False

                if kw.startswith("*INCLUDE_TRANSFORM") or kw.startswith("*INCLUDE_STAMPED"):
                    section = None
                    pending_include = "skip"
                elif kw.startswith("*INCLUDE"):
                    section = None
                    pending_include = True
                elif kw == "*PART" or kw == "*PART_INERTIA":
                    section = "PART"
                    pending_part_header = True  # next non-comment line = title
                    current_pid = None
                    current_name = None
                else:
                    section = None
                continue

            # --- comment lines ---
            if line.startswith("$"):
                # HyperMesh embeds names in comments like:
                # $HMNAME COMPS 88000100 White_Matter_Cerebrum_R
                if "HMNAME" in line.upper() and "COMPS" in line.upper():
                    tokens = line.split()
                    # format: $HMNAME COMPS <PID><name> or $HMNAME COMPS <PID> <name>
                    try:
                        # handle both fused "88000100White_Matter" and spaced versions
                        pid_raw = tokens[2] if len(tokens) > 2 else ""
                        # extract leading digits as PID, rest as name
                        digits = ""
                        remainder = pid_raw
                        for i, c in enumerate(pid_raw):
                            if c.isdigit():
                                digits += c
                            else:
                                remainder = pid_raw[i:]
                                break
                        else:
                            remainder = tokens[3] if len(tokens) > 3 else ""
                        if digits:
                            current_pid = int(digits)
                            current_name = remainder.strip() or (tokens[3] if len(tokens) > 3 else "")
                    except (ValueError, IndexError):
                        pass
                continue

            # --- include resolution ---
            if pending_include == True:
                inc_name = line.strip().strip('"')
                inc_path = inc_name if os.path.isabs(inc_name) else os.path.join(_base_dir, inc_name)
                if os.path.exists(inc_path):
                    sub = parse_parts(inc_path, _visited, _base_dir)
                    parts.extend(sub)
                else:
                    print(f"  ⚠ include not found: {inc_path}")
                pending_include = False
                continue

            # --- part card parsing ---
            if section == "PART":
                stripped = line.strip()
                if not stripped:
                    continue

                if pending_part_header:
                    # First data line after *PART = title (free text, may be blank)
                    if current_name is None:
                        current_name = stripped
                    pending_part_header = False
                else:
                    # Second data line = PID, SECID, MID, ...
                    vals = line.split(",") if "," in line else line.split()
                    try:
                        pid_from_card = int(vals[0])
                        # prefer HyperMesh comment name if already captured for this PID
                        name = current_name if current_name else f"PART_{pid_from_card}"
                        parts.append((pid_from_card, name, os.path.basename(path)))
                        current_pid = None
                        current_name = None
                    except (ValueError, IndexError):
                        pass
                    section = None  # reset after reading the PID line

    return parts


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    filters = [f.lower() for f in sys.argv[2:]]  # optional keyword filters

    print(f"Parsing: {path}\n")
    parts = parse_parts(path)

    # deduplicate by PID (keep last seen — include order matches keyword priority)
    seen = {}
    for pid, name, src in parts:
        seen[pid] = (name, src)

    # sort by PID
    sorted_parts = sorted(seen.items())

    if filters:
        print(f"Filtering for: {filters}\n")
        matched = [(pid, name, src) for pid, (name, src) in sorted_parts
                   if any(f in name.lower() for f in filters)]
        print(f"{'PID':<12} {'Name':<45} Source")
        print("-" * 80)
        for pid, name, src in matched:
            print(f"{pid:<12} {name:<45} {src}")
        print(f"\n{len(matched)} matching parts found")
        print("\nAll PIDs (for copy-paste into extraction script):")
        print([pid for pid, _, _ in matched])
    else:
        print(f"{'PID':<12} {'Name':<45} Source")
        print("-" * 80)
        for pid, (name, src) in sorted_parts:
            print(f"{pid:<12} {name:<45} {src}")
        print(f"\n{len(sorted_parts)} total parts found")


if __name__ == "__main__":
    main()