"""
THUMS AM50 V4.1 Head-Only Extractor
====================================
Reads the full-body THUMS keyword file (following all *INCLUDEs),
filters to head-only parts by PID, and writes a self-contained
head_only.k ready for LS-DYNA Student (<128K node cap).

Usage:
    python extract_head.py main_THUMS_AM50_V41.k
    python extract_head.py main_THUMS_AM50_V41.k --minimal
    python extract_head.py main_THUMS_AM50_V41.k --output my_head.k

Modes:
    default  : skull + brain + meninges/CSF + head skin + connectors
    --minimal: skull + brain + meninges/CSF only (safest for 128K cap)
    --skin: head skin only(excludes connectors)
"""

import os, sys
from collections import defaultdict

# ── HEAD PID DEFINITIONS (THUMS AM50 V4.1 Pedestrian) ───────────────────────

# Skull cranial vault + facial skeleton
# Naming: <bone>_r/_l (diploë solid), <bone>_external/_internal (cortical shells)
# _shell variants = additional null/contact shells on temporal/zygomatic
SKULL_CRANIAL_R = list(range(88000001, 88000052))
SKULL_CRANIAL_L = list(range(88000052, 88000100))
SKULL_ALL = SKULL_CRANIAL_R + SKULL_CRANIAL_L

# Brain parenchyma (solid elements — white/gray matter, cerebellum, brainstem)
BRAIN = [
    88000100, 88000101, 88000102, 88000103, 88000104, 88000105,  # R
    88000120, 88000121, 88000122, 88000123, 88000124, 88000125,  # L
]

# Meninges + CSF + ventricular system (mix of shells and solids)
MENINGES_CSF = [
    # CSF layers R
    88000106, 88000107, 88000109,
    88000242, 88000243, 88000244, 88000252, 88000254,
    # CSF layers L
    88000126, 88000127, 88000129,
    88000245, 88000248, 88000249, 88000253, 88000255,
    # Ventricles
    88000246, 88000247, 88000250, 88000251,
    # Pia R/L
    88000110, 88000111, 88000112,
    88000130, 88000131, 88000132,
    # Arachnoid + Medulla surface R/L
    88000113, 88000114, 88000115,
    88000133, 88000134, 88000135,
    # Tentorium + Dura R/L
    88000116, 88000117, 88000118, 88000119,
    88000136, 88000137, 88000138, 88000139,
    # Falx, Superior Sagittal Sinus, Dura_hole
    88000140, 88000141, 88000142,
]

# Head/face skin (external surface — useful for warp registration)
HEAD_SKIN = [
    88000167, 88000168, 88000169, 88000170, 88000171, 88000172,
    88000219, 88000220,
    88000221, 88000222, 88000223, 88000224, 88000225, 88000226,
    88000227, 88000228, 88000229, 88000230, 88000231, 88000232,
    88000233, 88000234, 88000235, 88000236,
]

# Skull base connectors (str1-7, ng-str) — structural links to cervical spine
# keep for boundary condition integrity at neck cut plane
SKULL_BASE = [
    88000042, 88000043, 88000044, 88000045, 88000046, 88000047,
    88000048, 88000049, 88000050, 88000051,   # R
    88000091, 88000092, 88000093, 88000094, 88000095, 88000096,
    88000097, 88000098, 88000099,              # L
    88000257, 88000258, 88000259, 88000260,   # Str_Shell External/Internal R/L
]

# Face muscles, jaw ligaments, eye muscles (high node count, not needed for
# skull-brain coupled deformation analysis — drop in minimal mode)
FACE_SOFT = list(range(88000143, 88000167))

# Detailed eyeball anatomy (optional)
EYES = list(range(88000173, 88000217))

# Optic nerves (optional)
OPTIC = [88000263, 88000264]

# Cover element (contact/null)
COVER = [88000217]

# ── MODE SELECTION ───────────────────────────────────────────────────────────
MINIMAL_PIDS = set(SKULL_ALL + BRAIN + MENINGES_CSF)

FULL_HEAD_PIDS = set(
    SKULL_ALL + BRAIN + MENINGES_CSF +
    HEAD_SKIN + SKULL_BASE + COVER + OPTIC
    # deliberately excludes FACE_SOFT and EYES to stay under 128K cap
    # add them back here if node count permits after initial QA run
)

SKIN_PIDS = set(HEAD_SKIN)


# ── PARSER ───────────────────────────────────────────────────────────────────

def split_fields(line, n_fields, width=8):
    """Handles comma-delimited, space-delimited, and fixed-width (THUMS I8) formats."""
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
    stripped = line.rstrip()
    if len(stripped) >= n_fields * width and len(stripped) % width == 0:
        try:
            return [int(stripped[i:i+width]) for i in range(0, len(stripped), width)]
        except ValueError:
            return None
    return None


def parse_full_k(path, _visited=None, _base_dir=None):
    """
    Full-fidelity keyword parser: reads nodes, all element types,
    parts, sections, materials, and raw keyword blocks.
    Follows *INCLUDE chains. Returns a structured data dict.
    """
    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))

    real_path = os.path.abspath(path)
    if real_path in _visited:
        return {}
    _visited.add(real_path)

    data = {
        "nodes":         {},   # nid -> "raw_line" (preserve original format)
        "node_coords":   {},   # nid -> (x,y,z) for coord access
        "elems_solid":   {},   # eid -> (pid, raw_line)
        "elems_shell":   {},   # eid -> (pid, raw_line)
        "elems_beam":    {},   # eid -> (pid, raw_line)
        "elems_discrete":{},   # eid -> (pid, raw_line)
        "elems_seatbelt":{},   # eid -> (pid, raw_line)
        "parts":         {},   # pid -> raw_lines (the 2-line *PART block)
        "sections":      {},   # secid -> raw_lines
        "mats":          {},   # mid -> raw_lines
        "eos":           {},   # eosid -> raw_lines
        "hourglass":     {},   # hgid -> raw_lines
        "raw_blocks":    [],   # [(keyword_line, [data_lines])] for everything else
        "include_order": [],   # ordered list of source files for reconstruction
    }

    section = None
    pending_include = False
    current_block_kw = None
    current_block_lines = []
    current_part_lines = []
    current_part_kw = None
    current_generic_id = None

    def flush_generic():
        nonlocal current_block_kw, current_block_lines
        if current_block_kw and current_block_lines:
            data["raw_blocks"].append((current_block_kw, list(current_block_lines)))
        current_block_kw = None
        current_block_lines = []

    data["include_order"].append(os.path.abspath(path))

    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        i += 1

        if line.startswith("*"):
            flush_generic()
            kw = line.strip().upper()

            if kw.startswith("*INCLUDE_TRANSFORM") or kw.startswith("*INCLUDE_STAMPED"):
                section = None
                pending_include = "skip"

            elif kw.startswith("*INCLUDE"):
                section = None
                pending_include = True

            elif kw == "*NODE":
                section = "NODE"

            elif kw.startswith("*ELEMENT_SOLID"):
                section = "ELEMENT_SOLID"

            elif kw.startswith("*ELEMENT_SHELL_THICKNESS"):
                section = "ELEMENT_SHELL_THICKNESS"

            elif kw.startswith("*ELEMENT_SHELL"):
                section = "ELEMENT_SHELL"

            elif kw.startswith("*ELEMENT_BEAM"):
                section = "ELEMENT_BEAM"

            elif kw.startswith("*ELEMENT_DISCRETE"):
                section = "ELEMENT_DISCRETE"

            elif kw.startswith("*ELEMENT_SEATBELT"):
                section = "ELEMENT_SEATBELT"

            elif kw.startswith("*PART"):
                section = "PART"
                current_part_kw = line.strip()
                current_part_lines = []

            elif kw.startswith("*SECTION"):
                section = "SECTION"
                current_block_kw = line.strip()
                current_block_lines = []
                current_generic_id = None

            elif kw.startswith("*MAT") or kw.startswith("*MATERIAL"):
                section = "MAT"
                current_block_kw = line.strip()
                current_block_lines = []
                current_generic_id = None

            elif kw.startswith("*EOS"):
                section = "EOS"
                current_block_kw = line.strip()
                current_block_lines = []
                current_generic_id = None

            elif kw.startswith("*HOURGLASS"):
                section = "HOURGLASS"
                current_block_kw = line.strip()
                current_block_lines = []
                current_generic_id = None

            elif kw == "*END":
                section = None

            else:
                section = "GENERIC"
                current_block_kw = line.strip()
                current_block_lines = []

            continue

        if line.startswith("$"):
            # preserve comments inside current block
            if section in ("PART",):
                current_part_lines.append(line)
            elif section == "GENERIC":
                current_block_lines.append(line)
            continue

        # ── include resolution ───────────────────────────────────────────────
        if pending_include == True:
            inc_name = line.strip().strip('"')
            inc_path = (inc_name if os.path.isabs(inc_name)
                        else os.path.join(_base_dir, inc_name))
            if os.path.exists(inc_path):
                sub = parse_full_k(inc_path, _visited, _base_dir)
                for key in ("nodes", "node_coords", "elems_solid", "elems_shell",
                            "elems_beam", "elems_discrete", "elems_seatbelt",
                            "parts", "sections", "mats", "eos", "hourglass"):
                    data[key].update(sub.get(key, {}))
                data["raw_blocks"].extend(sub.get("raw_blocks", []))
                data["include_order"].extend(sub.get("include_order", []))
            else:
                print(f"  ⚠ include not found: {inc_path}")
            pending_include = False
            continue

        # ── data line parsing ────────────────────────────────────────────────
        stripped = line.strip()
        if not stripped:
            continue

        if section == "NODE":
            # Parse coords for node-filtering, preserve raw line for output
            vals = line.split(",") if "," in line else line.split()
            try:
                nid = int(vals[0])
                x, y, z = float(vals[1]), float(vals[2]), float(vals[3])
                data["nodes"][nid] = line  # raw line preserved for output
                data["node_coords"][nid] = (x, y, z)
            except (ValueError, IndexError):
                pass

        elif section == "ELEMENT_SOLID":
            vals = split_fields(line, 3, 8)
            if vals and len(vals) >= 3:
                eid, pid = vals[0], vals[1]
                data["elems_solid"][eid] = (pid, line)

        elif section in ("ELEMENT_SHELL", "ELEMENT_SHELL_THICKNESS"):
            vals = split_fields(line, 3, 8)
            if vals and len(vals) >= 3:
                eid, pid = vals[0], vals[1]
                data["elems_shell"][eid] = (pid, line)

        elif section == "ELEMENT_BEAM":
            vals = split_fields(line, 3, 8)
            if vals and len(vals) >= 3:
                eid, pid = vals[0], vals[1]
                data["elems_beam"][eid] = (pid, line)

        elif section == "ELEMENT_DISCRETE":
            vals = split_fields(line, 3, 8)
            if vals and len(vals) >= 3:
                eid, pid = vals[0], vals[1]
                data["elems_discrete"][eid] = (pid, line)

        elif section == "ELEMENT_SEATBELT":
            vals = split_fields(line, 3, 8)
            if vals and len(vals) >= 3:
                eid, pid = vals[0], vals[1]
                data["elems_seatbelt"][eid] = (pid, line)

        elif section == "PART":
            current_part_lines.append(line)
            # Second non-comment data line = PID card
            data_lines = [l for l in current_part_lines if not l.startswith("$")]
            if len(data_lines) == 2:
                try:
                    vals = data_lines[1].split(",") if "," in data_lines[1] else data_lines[1].split()
                    pid = int(vals[0])
                    data["parts"][pid] = (current_part_kw, list(current_part_lines))
                except (ValueError, IndexError):
                    pass
                section = None

        elif section in ("SECTION", "MAT", "EOS", "HOURGLASS"):
            current_block_lines.append(line)
            # First data line usually contains the ID in field 0
            data_lines = [l for l in current_block_lines if not l.startswith("$")]
            if len(data_lines) == 1 and current_generic_id is None:
                try:
                    vals = line.split(",") if "," in line else line.split()
                    current_generic_id = int(vals[0])
                    target = {"SECTION": "sections", "MAT": "mats",
                              "EOS": "eos", "HOURGLASS": "hourglass"}[section]
                    data[target][current_generic_id] = (current_block_kw, current_block_lines)
                except (ValueError, IndexError):
                    pass

        elif section == "GENERIC":
            current_block_lines.append(line)

    flush_generic()
    return data


# ── EXTRACTOR ────────────────────────────────────────────────────────────────

def extract_head(data, target_pids, output_path):
    """
    Filter data to target_pids and write a self-contained head_only.k.
    Collects all referenced section/mat/eos/hourglass IDs automatically
    so the output file has all required card definitions.
    """
    target_pids = set(target_pids)

    # ── collect elements belonging to target PIDs ────────────────────────────
    kept_solid    = {eid: v for eid, v in data["elems_solid"].items()    if v[0] in target_pids}
    kept_shell    = {eid: v for eid, v in data["elems_shell"].items()    if v[0] in target_pids}
    kept_beam     = {eid: v for eid, v in data["elems_beam"].items()     if v[0] in target_pids}
    kept_discrete = {eid: v for eid, v in data["elems_discrete"].items() if v[0] in target_pids}

    print(f"  Solid elements kept  : {len(kept_solid)}")
    print(f"  Shell elements kept  : {len(kept_shell)}")
    print(f"  Beam elements kept   : {len(kept_beam)}")
    print(f"  Discrete elements kept: {len(kept_discrete)}")

    # ── collect nodes referenced by kept elements ────────────────────────────
    used_nids = set()
    for eid, (pid, raw) in {**kept_solid, **kept_shell, **kept_beam, **kept_discrete}.items():
        vals = split_fields(raw, 3, 8)
        if vals:
            used_nids.update(v for v in vals[2:] if v > 0)

    kept_nodes = {nid: data["nodes"][nid] for nid in used_nids if nid in data["nodes"]}
    print(f"  Nodes kept           : {len(kept_nodes)}")

    if len(kept_nodes) > 128000:
        print(f"\n  ⚠ WARNING: {len(kept_nodes)} nodes exceeds LS-DYNA Student 128K cap!")
        print("  Re-run with --minimal flag to reduce scope.")
    elif len(kept_nodes) > 110000:
        print(f"\n  ⚠ CAUTION: {len(kept_nodes)} nodes is close to 128K cap.")
        print("  Contact definitions add nodes at solve time — leave headroom.")
    else:
        print(f"\n  ✓ Node count {len(kept_nodes)} is under 128K cap.")

    # ── collect parts (and their referenced section/mat/eos/hg IDs) ─────────
    kept_parts = {pid: data["parts"][pid] for pid in target_pids if pid in data["parts"]}
    missing_pids = target_pids - set(kept_parts.keys())
    if missing_pids:
        print(f"  ⚠ {len(missing_pids)} PIDs not found in *PART cards: "
              f"{sorted(missing_pids)[:10]}")

    # collect sec/mat/eos/hg IDs referenced by kept parts
    needed_secids, needed_mids, needed_eosids, needed_hgids = set(), set(), set(), set()
    for pid, (kw, part_lines) in kept_parts.items():
        data_lines = [l for l in part_lines if not l.startswith("$")]
        if len(data_lines) >= 2:
            vals = data_lines[1].split(",") if "," in data_lines[1] else data_lines[1].split()
            try:
                if len(vals) > 1 and int(vals[1]) > 0: needed_secids.add(int(vals[1]))
                if len(vals) > 2 and int(vals[2]) > 0: needed_mids.add(int(vals[2]))
                if len(vals) > 3 and int(vals[3]) > 0: needed_eosids.add(int(vals[3]))
                if len(vals) > 5 and int(vals[5]) > 0: needed_hgids.add(int(vals[5]))
            except (ValueError, IndexError):
                pass

    # ── write output .k ──────────────────────────────────────────────────────
    with open(output_path, "w") as f:
        f.write("*KEYWORD\n")
        f.write("$\n$ Head-only extract from THUMS AM50 V4.1 Pedestrian\n")
        f.write(f"$ Parts: {len(kept_parts)}  Nodes: {len(kept_nodes)}\n")
        f.write(f"$ Solid: {len(kept_solid)}  Shell: {len(kept_shell)}\n$\n")

        # NODES
        f.write("*NODE\n")
        for nid in sorted(kept_nodes):
            f.write(kept_nodes[nid] + "\n" if not kept_nodes[nid].endswith("\n")
                    else kept_nodes[nid])

        # ELEMENTS
        if kept_solid:
            f.write("*ELEMENT_SOLID\n")
            for eid in sorted(kept_solid):
                raw = kept_solid[eid][1]
                f.write(raw + "\n" if not raw.endswith("\n") else raw)

        if kept_shell:
            f.write("*ELEMENT_SHELL\n")
            for eid in sorted(kept_shell):
                raw = kept_shell[eid][1]
                f.write(raw + "\n" if not raw.endswith("\n") else raw)

        if kept_beam:
            f.write("*ELEMENT_BEAM\n")
            for eid in sorted(kept_beam):
                raw = kept_beam[eid][1]
                f.write(raw + "\n" if not raw.endswith("\n") else raw)

        if kept_discrete:
            f.write("*ELEMENT_DISCRETE\n")
            for eid in sorted(kept_discrete):
                raw = kept_discrete[eid][1]
                f.write(raw + "\n" if not raw.endswith("\n") else raw)

        # PARTS
        for pid in sorted(kept_parts):
            kw, part_lines = kept_parts[pid]
            f.write(kw + "\n")
            for l in part_lines:
                f.write(l + "\n" if not l.endswith("\n") else l)

        # SECTIONS
        for secid in sorted(needed_secids):
            if secid in data["sections"]:
                kw, sec_lines = data["sections"][secid]
                f.write(kw + "\n")
                for l in sec_lines:
                    f.write(l + "\n" if not l.endswith("\n") else l)

        # MATERIALS
        for mid in sorted(needed_mids):
            if mid in data["mats"]:
                kw, mat_lines = data["mats"][mid]
                f.write(kw + "\n")
                for l in mat_lines:
                    f.write(l + "\n" if not l.endswith("\n") else l)

        # EOS
        for eosid in sorted(needed_eosids):
            if eosid in data["eos"]:
                kw, eos_lines = data["eos"][eosid]
                f.write(kw + "\n")
                for l in eos_lines:
                    f.write(l + "\n" if not l.endswith("\n") else l)

        # HOURGLASS
        for hgid in sorted(needed_hgids):
            if hgid in data["hourglass"]:
                kw, hg_lines = data["hourglass"][hgid]
                f.write(kw + "\n")
                for l in hg_lines:
                    f.write(l + "\n" if not l.endswith("\n") else l)

        f.write("*END\n")

    print(f"\n  Output written: {output_path}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_k = sys.argv[1]
    minimal  = "--minimal" in sys.argv
    skin= "--skin" in sys.argv
    out_arg  = next((sys.argv[i+1] for i, a in enumerate(sys.argv)
                     if a == "--output" and i+1 < len(sys.argv)), None)
    if out_arg:
        output_k = out_arg
    else:
        base = os.path.splitext(input_k)[0]
    

    if minimal:
        print("⚠ WARNING: Minimal mode excludes head skin and connectors.")
        print("  Use only if node count exceeds 128K cap.")
        mode_label = "MINIMAL (skull+brain+meninges)"
        target_pids = MINIMAL_PIDS
        suffix = "_head_minimal.k"
        output_k = base + suffix
    elif skin:
        print("⚠ WARNING: Skin mode includes only head skin for registration.")
        mode_label = "SKIN (skin)"
        target_pids = SKIN_PIDS
        suffix = "_head_skin.k"
        output_k = base + suffix
    else:
        print("⚠ WARNING: Full mode includes all head components.")
        mode_label = "FULL HEAD (skull+brain+meninges+skin)"
        target_pids = FULL_HEAD_PIDS
        suffix = "_head_full.k"
        output_k = base + suffix
    

    print(f"\nParsing: {input_k}")
    print(f"Mode   : {mode_label}")
    print(f"PIDs   : {len(target_pids)} target parts\n")

    data = parse_full_k(input_k)
    print(f"Loaded : {len(data['nodes'])} nodes, "
          f"{len(data['elems_solid'])} solids, "
          f"{len(data['elems_shell'])} shells across "
          f"{len(data['parts'])} parts\n")

    print("Extracting head subset...")
    extract_head(data, target_pids, output_k)
    print("\nNext step: run k_mesh_qa.py on the output to verify quality + node count.")
    print(f"  python k_mesh_qa.py \"{output_k}\"")


if __name__ == "__main__":
    main()