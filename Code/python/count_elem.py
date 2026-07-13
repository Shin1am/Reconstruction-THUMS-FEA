"""
Element count per PID — helps identify which parts to drop to fit
under LS-DYNA Student 128K element cap.

Usage:
    python count_elements.py Head_V6.k
    python count_elements.py Head_V6.k --top 20
    python count_elements.py Head_V6.k --shells-only
"""
import os, sys
from collections import defaultdict

def split_fields(line, n_fields, width=8):
    if "," in line:
        try:
            return [int(p) for p in line.split(",")]
        except ValueError:
            pass
    parts = line.split()
    if len(parts) >= n_fields:
        try:
            return [int(p) for p in parts]
        except ValueError:
            pass
    stripped = line.rstrip()
    if len(stripped) >= n_fields * width and len(stripped) % width == 0:
        try:
            return [int(stripped[i:i+width]) for i in range(0, len(stripped), width)]
        except ValueError:
            return None
    return None


def parse_counts(path, _visited=None, _base_dir=None):
    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))
    real = os.path.abspath(path)
    if real in _visited:
        return {}, {}, {}
    _visited.add(real)

    solid_count  = defaultdict(int)   # pid -> count
    shell_count  = defaultdict(int)
    part_names   = {}                 # pid -> name

    section = None
    pending_include = False

    with open(path, "r", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("*"):
                kw = line.strip().upper()
                if kw.startswith("*INCLUDE_TRANSFORM") or kw.startswith("*INCLUDE_STAMPED"):
                    section = None
                    pending_include = "skip"
                elif kw.startswith("*INCLUDE"):
                    section = None
                    pending_include = True
                elif kw == "*NODE":
                    section = None
                elif kw.startswith("*ELEMENT_SOLID") or kw.startswith("*ELEMENT_TSHELL"):
                    section = "SOLID"
                elif kw.startswith("*ELEMENT_SHELL"):
                    section = "SHELL"
                elif kw.startswith("*ELEMENT_BEAM") or kw.startswith("*ELEMENT_DISCRETE"):
                    section = "OTHER"
                elif kw.startswith("*PART"):
                    section = "PART"
                    current_part_lines = []
                else:
                    section = None
                continue

            if line.startswith("$"):
                if "HMNAME" in line.upper() and "COMPS" in line.upper():
                    tokens = line.split()
                    try:
                        pid_raw = tokens[2] if len(tokens) > 2 else ""
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
                            part_names[int(digits)] = remainder.strip() or (
                                tokens[3] if len(tokens) > 3 else "")
                    except (ValueError, IndexError):
                        pass
                continue

            if pending_include == True:
                inc_name = line.strip().strip('"')
                inc_path = (inc_name if os.path.isabs(inc_name)
                            else os.path.join(_base_dir, inc_name))
                if os.path.exists(inc_path):
                    s, sh, pn = parse_counts(inc_path, _visited, _base_dir)
                    for pid, cnt in s.items():
                        solid_count[pid] += cnt
                    for pid, cnt in sh.items():
                        shell_count[pid] += cnt
                    part_names.update(pn)
                pending_include = False
                continue

            if section == "SOLID":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    solid_count[vals[1]] += 1

            elif section == "SHELL":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    shell_count[vals[1]] += 1

            elif section == "PART":
                if not line.strip():
                    continue
                current_part_lines.append(line)
                data_lines = [l for l in current_part_lines if not l.startswith("$")]
                if len(data_lines) == 2:
                    try:
                        vals = data_lines[1].split(",") if "," in data_lines[1] else data_lines[1].split()
                        pid = int(vals[0])
                        if pid not in part_names:
                            part_names[pid] = data_lines[0].strip()
                    except (ValueError, IndexError):
                        pass
                    section = None

    return solid_count, shell_count, part_names


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    top_n = 20
    shells_only = "--shells-only" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--top" and i+1 < len(sys.argv):
            top_n = int(sys.argv[i+1])

    print(f"\nParsing: {path}\n")
    solid_count, shell_count, part_names = parse_counts(path)

    all_pids = set(solid_count) | set(shell_count)
    rows = []
    for pid in all_pids:
        sc = solid_count.get(pid, 0)
        sh = shell_count.get(pid, 0)
        total = sc + sh
        name = part_names.get(pid, f"PID_{pid}")
        rows.append((total, sc, sh, pid, name))

    rows.sort(reverse=True)

    total_solid = sum(solid_count.values())
    total_shell = sum(shell_count.values())
    total_all   = total_solid + total_shell

    print(f"  Total solid/tshell elements : {total_solid:>8,}")
    print(f"  Total shell elements        : {total_shell:>8,}")
    print(f"  Total ALL elements          : {total_all:>8,}")
    print(f"  LS-DYNA Student cap         : {128000:>8,}")
    print(f"  Excess                      : {max(0, total_all-128000):>8,}")
    print(f"  Need to remove at least     : {max(0, total_all-110000):>8,} elements "
          f"(targeting 110K for headroom)\n")

    if shells_only:
        rows = [(t, sc, sh, pid, name) for t, sc, sh, pid, name in rows if sh > 0]
        print(f"  Showing shell-element-containing parts only\n")

    print(f"  {'PID':<12} {'Solid':>8} {'Shell':>8} {'Total':>8}  Name")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8}  {'-'*35}")
    cumulative = 0
    for total, sc, sh, pid, name in rows[:top_n]:
        cumulative += total
        print(f"  {pid:<12} {sc:>8,} {sh:>8,} {total:>8,}  {name}")
    if len(rows) > top_n:
        rest = sum(t for t, *_ in rows[top_n:])
        print(f"  {'...(rest)':12} {'':>8} {'':>8} {rest:>8,}  ({len(rows)-top_n} more parts)")

    # Identify which PIDs to drop to reach 110K
    print(f"\n  --- Drop candidates (shells first, largest first) ---")
    print(f"  Dropping these PIDs would bring total under 110K cap:\n")
    shell_rows = sorted([(sh, sc, pid, name)
                         for t, sc, sh, pid, name in rows if sh > 0],
                        reverse=True)
    budget = total_all - 110000
    print(f"  Need to cut: {budget:,} elements\n")
    print(f"  {'PID':<12} {'Shell':>8} {'Cumulative cut':>15}  Name")
    print(f"  {'-'*12} {'-'*8} {'-'*15}  {'-'*35}")
    cut_so_far = 0
    suggested_drop = []
    for sh, sc, pid, name in shell_rows:
        if cut_so_far >= budget:
            break
        cut_so_far += sh + sc
        suggested_drop.append(pid)
        marker = " ← DROP" if cut_so_far <= budget * 1.5 else ""
        print(f"  {pid:<12} {sh:>8,} {cut_so_far:>15,}  {name}{marker}")

    print(f"\n  Suggested PIDs to suppress (largest shell parts first):")
    print(f"  {suggested_drop}")
    print(f"\n  Estimated remaining elements after drop: "
          f"~{total_all - cut_so_far:,}")


if __name__ == "__main__":
    main()