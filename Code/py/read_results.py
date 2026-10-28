"""
Read LS-DYNA output files and print key simulation metrics.
Run from the folder containing your d3plot/messag/glstat files.

Usage:
    python read_results.py
    python read_results.py D:\2d_3d_regis dataset\results\baseline
"""
import os, sys, re

def find_file(folder, name):
    path = os.path.join(folder, name)
    return path if os.path.exists(path) else None

def read_messag(path):
    """Extract timestep size and termination reason from messag."""
    print("\n=== MESSAG (solver log) ===")
    dt_vals = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            # timestep line: "dt = 1.64E-07"
            if "time step size" in line.lower() or " dt " in line.lower():
                nums = re.findall(r"[\d.]+[Ee][+-]?\d+", line)
                if nums:
                    dt_vals.append(float(nums[0]))
            if "termination" in line.lower() or "normal" in line.lower():
                print(f"  {line.strip()}")
    if dt_vals:
        print(f"  Min timestep : {min(dt_vals):.4E} s")
        print(f"  Max timestep : {max(dt_vals):.4E} s")
        print(f"  Initial dt   : {dt_vals[0]:.4E} s  (key value for comparison)")


def read_glstat(path):
    """Parse glstat ASCII file for energy metrics."""
    print("\n=== GLSTAT (global energy history) ===")
    times, internal, hourglass = [], [], []

    with open(path, "r", errors="ignore") as f:
        content = f.read()

    # glstat format: blocks separated by "time" keyword
    blocks = re.split(r"\n\s*time\s*=", content, flags=re.IGNORECASE)
    for block in blocks[1:]:  # skip header
        lines = block.strip().split("\n")
        try:
            t = float(lines[0].strip())
            ie = he = None
            for line in lines[1:]:
                ll = line.lower()
                if "internal energy" in ll:
                    nums = re.findall(r"[+-]?[\d.]+[Ee][+-]?\d+", line)
                    if nums: ie = float(nums[0])
                if "hourglass" in ll:
                    nums = re.findall(r"[+-]?[\d.]+[Ee][+-]?\d+", line)
                    if nums: he = float(nums[0])
            if ie is not None:
                times.append(t)
                internal.append(ie)
                hourglass.append(he if he is not None else 0.0)
        except (ValueError, IndexError):
            continue

    if not times:
        print("  Could not parse glstat — may need LS-PrePost to view")
        return

    print(f"  Time steps recorded : {len(times)}")
    print(f"  End time            : {times[-1]:.4E} s")
    print(f"  Peak internal energy: {max(internal):.4E}")
    print(f"  Peak hourglass energy:{max(hourglass):.4E}")

    if max(internal) > 0:
        max_ratio = max(hourglass) / max(internal)
        print(f"  Max HG/IE ratio     : {max_ratio:.4f}  ", end="")
        if max_ratio < 0.05:
            print("(GOOD - well under 10% threshold)")
        elif max_ratio < 0.10:
            print("(OK - under 10% threshold)")
        else:
            print("(WARNING - exceeds 10% threshold, results unreliable)")
    else:
        print("  Internal energy is zero (no load applied) - expected for zero-velocity baseline")


def read_matsum(path):
    """Print per-material energy at final timestep."""
    print("\n=== MATSUM (per-material energy at end) ===")
    with open(path, "r", errors="ignore") as f:
        content = f.read()

    # Find last time block
    blocks = re.split(r"\n\s*time\s*=", content, flags=re.IGNORECASE)
    if len(blocks) < 2:
        print("  Could not parse matsum")
        return

    last_block = blocks[-1]
    lines = last_block.strip().split("\n")
    try:
        t = float(lines[0].strip())
        print(f"  Final time: {t:.4E} s")
    except ValueError:
        pass

    mat_data = []
    for line in lines[1:]:
        nums = re.findall(r"[+-]?[\d.]+[Ee][+-]?\d+", line)
        if len(nums) >= 2:
            try:
                mat_id = int(float(nums[0]))
                ie = float(nums[1])
                mat_data.append((mat_id, ie))
            except ValueError:
                continue

    # Show top 5 by internal energy
    mat_data.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"  Top parts by internal energy:")
    for mid, ie in mat_data[:5]:
        print(f"    PID {mid:>12} : IE = {ie:.4E}")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    folder = os.path.abspath(folder)
    print(f"Reading results from: {folder}")

    messag = find_file(folder, "messag")
    glstat = find_file(folder, "glstat")
    matsum = find_file(folder, "matsum")
    d3plot = find_file(folder, "d3plot")

    print(f"\nFiles found:")
    print(f"  messag : {'YES' if messag else 'NOT FOUND'}")
    print(f"  glstat : {'YES' if glstat else 'NOT FOUND'}")
    print(f"  matsum : {'YES' if matsum else 'NOT FOUND'}")
    print(f"  d3plot : {'YES' if d3plot else 'NOT FOUND'}")

    if messag: read_messag(messag)
    if glstat:  read_glstat(glstat)
    if matsum:  read_matsum(matsum)

    if d3plot:
        size_mb = os.path.getsize(d3plot) / 1e6
        print(f"\n=== D3PLOT ===")
        print(f"  File size: {size_mb:.1f} MB")
        print(f"  Open in LS-PrePost:")
        print(f"    File > Open > LS-DYNA Binary Plot > {d3plot}")
        print(f"    Post > Fringe Component > Displacement > Resultant")

    print(f"\nBaseline timestep (dt) is critical for warp validation:")
    print(f"  After warp: dt_warped must be > 0.5 x dt_baseline")
    print(f"  If dt_warped collapses, the warp introduced bad elements")


if __name__ == "__main__":
    main()