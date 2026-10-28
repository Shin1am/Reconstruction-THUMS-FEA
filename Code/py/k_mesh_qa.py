"""
Pre-solve mesh quality gate for warped LS-DYNA .k files.

Run this immediately after your TPS/CPD deformation step, before sending
the file to the LS-DYNA solver. Checks for the failure modes that a
surface-driven warp commonly introduces into volumetric skull/brain elements:

  1. Negative/zero Jacobian (inverted tets/hexes) -> guaranteed solver crash
  2. Extreme aspect ratio -> timestep collapse, even if it doesn't crash
  3. Duplicate/coincident nodes introduced by the warp field

Usage:
    python k_mesh_qa.py baseline_head.k
    python k_mesh_qa.py warped_head.k --compare baseline_head.k
"""
import re
import os
import sys
import numpy as np
from collections import defaultdict


def split_fields(line, n_fields, width=8):
    """Parse a line of integer fields that may be comma-delimited,
    space-delimited, OR jammed fixed-width with no delimiter at all
    (legacy LS-DYNA convention, e.g. THUMS element cards: I8 per field,
    no separator). Tries delimited first, falls back to fixed-width."""
    if "," in line:
        parts = line.split(",")
        try:
            return [int(p) for p in parts]
        except ValueError:
            pass
    parts = line.split()
    if len(parts) >= n_fields:
        try:
            return [int(p) for p in parts]
        except ValueError:
            pass
    # Fixed-width fallback: no delimiter at all, chunk into `width`-char fields
    stripped = line.rstrip()
    if len(stripped) >= n_fields * width and len(stripped) % width == 0:
        try:
            return [int(stripped[i:i + width]) for i in range(0, len(stripped), width)]
        except ValueError:
            return None
    return None


def parse_k_file(path, _visited=None, _base_dir=None):
    """Minimal *NODE / *ELEMENT_SOLID parser for LS-DYNA keyword files.
    Follows *INCLUDE cards recursively, since master files (e.g. THUMS
    main_*.k) typically contain no mesh data themselves -- just pointers
    to part/node/element sub-files."""
    import os

    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))

    real_path = os.path.abspath(path)
    if real_path in _visited:
        return {}, {}, {}
    _visited.add(real_path)

    nodes = {}      # nid -> (x, y, z)
    elems_solid = {}  # eid -> (pid, n1..n8)
    elems_shell = {}  # eid -> (pid, n1..n4)

    section = None
    pending_include = False
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("*"):
                kw = line.strip().upper()
                if kw.startswith("*INCLUDE_TRANSFORM") or kw.startswith("*INCLUDE_STAMPED"):
                    section = None
                    pending_include = "skip"  # transform includes need offset handling, skip for QA
                elif kw.startswith("*INCLUDE"):
                    section = None
                    pending_include = True
                elif kw.startswith("*NODE"):
                    section = "NODE"
                    pending_include = False
                elif kw.startswith("*ELEMENT_SOLID"):
                    section = "ELEMENT_SOLID"
                    pending_include = False
                elif kw.startswith("*ELEMENT_SHELL"):
                    section = "ELEMENT_SHELL"
                    pending_include = False
                elif kw.startswith("*ELEMENT_TSHELL"):
                    section = "ELEMENT_SOLID"  # thick shells: treat geometry like 8-node solid for volume proxy
                    pending_include = False
                else:
                    section = None
                    pending_include = False
                continue
            if line.startswith("$"):
                continue  # comment

            if pending_include == True:
                inc_name = line.strip().strip('"')
                inc_path = inc_name if os.path.isabs(inc_name) else os.path.join(_base_dir, inc_name)
                if os.path.exists(inc_path):
                    n2, e2, s2 = parse_k_file(inc_path, _visited, _base_dir)
                    nodes.update(n2)
                    elems_solid.update(e2)
                    elems_shell.update(s2)
                else:
                    print(f"  ⚠ *INCLUDE target not found: {inc_path}")
                pending_include = False
                continue

            if section == "NODE":
                # Fixed-width or free-field; LS-DYNA allows both. Try split first.
                parts = line.split(",") if "," in line else line.split()
                if len(parts) < 4:
                    continue
                try:
                    nid = int(parts[0])
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    nodes[nid] = (x, y, z)
                except ValueError:
                    continue

            elif section == "ELEMENT_SOLID":
                vals = split_fields(line, n_fields=10, width=8)  # EID,PID,N1..N8
                if vals is None or len(vals) < 3:
                    continue
                eid, pid = vals[0], vals[1]
                conn = vals[2:]
                # 8-node hex (pad/repeat for degenerate tet-as-hex), or 4-node tet
                elems_solid[eid] = (pid, conn)

            elif section == "ELEMENT_SHELL":
                vals = split_fields(line, n_fields=6, width=8)  # EID,PID,N1..N4
                if vals is None or len(vals) < 3:
                    continue
                eid, pid = vals[0], vals[1]
                conn = vals[2:6]  # tri (3 nodes, last repeated) or quad (4 nodes)
                elems_shell[eid] = (pid, conn)

    return nodes, elems_solid, elems_shell


def hex_jacobian_signed_volume(coords):
    """
    Approximate signed volume for an 8-node hex using the scalar triple
    product of the diagonal vectors at the centroid. Sufficient as a
    cheap inversion detector (sign flip = inverted element), not a
    replacement for full Gauss-point Jacobian eval in the solver itself.
    """
    coords = np.array(coords)
    centroid = coords.mean(axis=0)
    vol = 0.0
    # Standard hex face decomposition into 6 tets from centroid (cheap proxy)
    faces = [
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)
    ]
    for f in faces:
        a, b, c, d = [coords[i] for i in f]
        # split quad face into two tris, accumulate tet volume w.r.t. centroid
        for tri in [(a, b, c), (a, c, d)]:
            v1, v2, v3 = [p - centroid for p in tri]
            vol += np.dot(v1, np.cross(v2, v3)) / 6.0
    return vol


def tet_signed_volume(coords):
    coords = np.array(coords)
    v1 = coords[1] - coords[0]
    v2 = coords[2] - coords[0]
    v3 = coords[3] - coords[0]
    return np.dot(v1, np.cross(v2, v3)) / 6.0


def quad_or_tri_area(coords):
    """Signed area magnitude via shoelace cross-product (3 or 4 node shell)."""
    coords = np.array(coords)
    if len(coords) == 4 and np.allclose(coords[2], coords[3]):
        coords = coords[:3]
    centroid = coords.mean(axis=0)
    area = 0.0
    n = len(coords)
    normal_accum = np.zeros(3)
    for i in range(n):
        a, b = coords[i] - centroid, coords[(i + 1) % n] - centroid
        normal_accum += np.cross(a, b)
    return np.linalg.norm(normal_accum) / 2.0


def check_shells(nodes, elems_shell, label=""):
    if not elems_shell:
        return
    print(f"\n  --- Shell elements: {len(elems_shell)} ---")
    zero_area = 0
    areas = []
    bad_eids = []
    for eid, (pid, conn) in elems_shell.items():
        coords = [nodes[n] for n in conn if n in nodes]
        if len(coords) < 3:
            continue
        a = quad_or_tri_area(coords)
        areas.append(a)
        if a < 1e-9:
            zero_area += 1
            bad_eids.append(eid)
    if areas:
        areas = np.array(areas)
        print(f"  Zero/near-zero area shells: {zero_area}")
        print(f"  Area stats -> min: {areas.min():.6e}, median: {np.median(areas):.6e}, max: {areas.max():.6e}")
        if bad_eids:
            print(f"  ⚠ Degenerate shell IDs (first 20): {bad_eids[:20]}")
            print("  -> Common on skull cortical bone after surface warps; check TPS control density there.")


def check_mesh(nodes, elems, label="", elems_shell=None):
    print(f"\n{'='*60}\nMESH QA: {label}\n{'='*60}")
    print(f"  Nodes   : {len(nodes)}")
    print(f"  Elements (solid/tshell): {len(elems)}")
    if elems_shell:
        print(f"  Elements (shell)       : {len(elems_shell)}")

    n_inverted = 0
    n_degenerate = 0
    bad_eids = []
    volumes = []
    signed_volumes = []
    eid_list = []
    pid_list = []

    for eid, (pid, conn) in elems.items():
        try:
            coords = [nodes[n] for n in conn if n in nodes]
        except KeyError:
            continue
        if len(coords) < 4:
            continue

        if len(coords) == 8:
            vol = hex_jacobian_signed_volume(coords)
        elif len(coords) == 4:
            vol = tet_signed_volume(coords)
        else:
            continue

        signed_volumes.append(vol)
        eid_list.append(eid)
        pid_list.append(pid)
        volumes.append(abs(vol))

    # Per-PART sign consistency check: different parts/components may use
    # different node-winding conventions (common when a full-body model
    # assembles meshes from different sources, e.g. skeletal vs soft tissue
    # built/exported by different tools). A whole-mesh majority vote produces
    # false positives in that case, so vote per PID instead.
    signed_volumes = np.array(signed_volumes)
    by_pid = defaultdict(list)  # pid -> list of (idx, vol)
    for idx, pid in enumerate(pid_list):
        by_pid[pid].append((idx, signed_volumes[idx]))

    pid_flip_count = 0
    if len(signed_volumes):
        for pid, items in by_pid.items():
            vols = np.array([v for _, v in items])
            n_pos = int((vols > 0).sum())
            n_neg = int((vols < 0).sum())
            majority_positive = n_pos >= n_neg
            minority_in_part = min(n_pos, n_neg)
            if minority_in_part / len(vols) > 0.05:
                pid_flip_count += 1
            for idx, vol in items:
                eid = eid_list[idx]
                is_minority_sign = (vol <= 0) if majority_positive else (vol >= 0)
                if abs(vol) < 1e-9:
                    n_degenerate += 1
                    bad_eids.append(eid)
                elif is_minority_sign:
                    n_inverted += 1
                    bad_eids.append(eid)

        if pid_flip_count:
            print(f"\n  NOTE: {pid_flip_count} of {len(by_pid)} parts show a mixed sign split")
            print("  internally (checked per-PID, not whole-mesh) -- flagging only the")
            print("  minority winding within each part as suspect.")

    volumes = np.array(volumes)
    print(f"\n  Inverted elements (negative volume): {n_inverted}")
    print(f"  Near-zero volume (degenerate)       : {n_degenerate}")
    if len(volumes):
        print(f"  Volume stats -> min: {volumes.min():.6e}, "
              f"median: {np.median(volumes):.6e}, max: {volumes.max():.6e}")
        ratio = volumes.max() / max(volumes.min(), 1e-12)
        print(f"  Max/min volume ratio (proxy for aspect distortion): {ratio:.2e}")
        if ratio > 1e4:
            print("  ⚠ WARNING: high volume ratio -> expect LS-DYNA timestep collapse")

    if bad_eids:
        print(f"\n  ⚠ FAILING ELEMENT IDs (first 20): {bad_eids[:20]}")
        print("  -> These WILL crash or stall the LS-DYNA solver.")
        print("  -> Trace back to source vertices in your TPS/CPD warp field;")
        print("     likely cause: warp control points too sparse near this region,")
        print("     or skull/brain boundary folded during the deformation.")
    else:
        print("\n  ✓ No inverted/degenerate elements detected — solver-safe.")

    # duplicate node check (common artifact of CPD warps applied per-vertex
    # without preserving topology/connectivity constraints)
    coords_arr = np.array(list(nodes.values()))
    _, counts = np.unique(np.round(coords_arr, decimals=6), axis=0, return_counts=True)
    dup_count = int((counts > 1).sum())
    if dup_count:
        print(f"\n  ⚠ {dup_count} coincident node clusters detected "
              f"(tolerance 1e-6) — check warp field continuity.")

    if elems_shell:
        check_shells(nodes, elems_shell, label)

    return {"n_inverted": n_inverted, "n_degenerate": n_degenerate, "bad_eids": bad_eids}


def extract_head_parts(nodes, elems, head_part_ids):
    """Extract elements belonging to head_part_ids (skull + brain PIDs from
    THUMS part table), plus only the nodes those elements reference."""
    kept_elems = {eid: v for eid, v in elems.items() if v[0] in head_part_ids}
    used_nodes = set()
    for _, (pid, conn) in kept_elems.items():
        used_nodes.update(conn)
    kept_nodes = {nid: c for nid, c in nodes.items() if nid in used_nodes}
    return kept_nodes, kept_elems


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    nodes, elems, elems_shell = parse_k_file(path)
    result = check_mesh(nodes, elems, label=path, elems_shell=elems_shell)

    if "--compare" in sys.argv:
        cmp_path = sys.argv[sys.argv.index("--compare") + 1]
        nodes2, elems2, elems_shell2 = parse_k_file(cmp_path)
        result2 = check_mesh(nodes2, elems2, label=cmp_path, elems_shell=elems_shell2)

        print(f"\n{'='*60}\nDELTA SUMMARY ({path} vs {cmp_path})\n{'='*60}")
        print(f"  Δ inverted elements : {result['n_inverted'] - result2['n_inverted']:+d}")
        print(f"  Δ degenerate elements: {result['n_degenerate'] - result2['n_degenerate']:+d}")
        newly_bad = set(result["bad_eids"]) - set(result2["bad_eids"])
        if newly_bad:
            print(f"  New failures introduced by warp: {sorted(newly_bad)[:20]}")

    sys.exit(0 if result["n_inverted"] == 0 and result["n_degenerate"] == 0 else 1)


if __name__ == "__main__":
    main()