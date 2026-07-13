"""
Head_V6.k Right-Hemisphere Extractor
======================================
Extracts right-side skull + brain + essential meninges only.
Target: under 128K elements for LS-DYNA Student R16.1 cap.

Strategy:
  - Keep ALL right-side brain (white/gray matter, cerebellum, brainstem)
  - Keep ALL right-side CSF layers
  - Keep RIGHT cranial vault bones only (no facial skeleton)
  - Keep bilateral midline structures (falx, superior sagittal sinus)
    since these are structurally shared — dropping them creates
    an open boundary that can cause contact instability
  - Drop: all _L / _l parts, eyes, face muscles, jaw, skin, str connectors
  - Fix: delete the 4 known degenerate elements in CSF_Stem_R/L

Usage:
    python extract_right_hemi.py Head_V6.k
    python extract_right_hemi.py Head_V6.k --output my_output.k
"""

import os, sys
from collections import defaultdict

# ── RIGHT HEMISPHERE PID SET ─────────────────────────────────────────────────

# Cranial vault R only (no facial skeleton — lacrimal/nasal/zygomatic/
# maxilla/mandible/palatine/teeth/alveolar/str connectors all dropped)
SKULL_VAULT_R = [
    88000001, 88000002, 88000003,          # frontal R (spon, external, internal)
    88000004, 88000005, 88000006,          # parietal R
    88000007, 88000008, 88000009, 88000010,# temporal R
    88000011, 88000012, 88000013,          # occipital R
    88000014, 88000015, 88000016,          # sphenoid R
    88000017, 88000018, 88000019, 88000020,# ethmoid R
]

# Brain parenchyma R (solid elements)
BRAIN_R = [
    88000100, 88000101,  # White/Gray Matter Cerebrum R
    88000102, 88000103,  # White/Gray Matter Cerebellum R
    88000104, 88000105,  # White/Gray Matter Stem R
]

# CSF layers R (solid elements)
CSF_R = [
    88000106,            # CSF_Cerebrum_R
    88000107,            # CSF_Cerebellum_R
    88000109,            # CSF_Stem_R  (contains 2 degenerate elements — will be deleted)
    88000242, 88000243,  # CSF_Cerebrum2_R, CSF_Cerebrum3_R
    88000244,            # CSF_Stem2_R
    88000252,            # CSF_Cerebrum4_R
    88000254,            # CSF_Cerebellum2_R
    88000246, 88000247,  # Lateral_Ventricle_R, 3rd_Ventricle_R
]

# Meninges R (shell elements)
MENINGES_R = [
    88000110, 88000111, 88000112,          # Pia R (cerebrum, cerebellum, sagittal)
    88000113, 88000114,                    # Arachnoid R (cerebrum, cerebellum)
    88000115,                              # Medulla_Surface_R
    88000116,                              # Tentorium_R
    88000117, 88000118,                    # Dura_Shell_R, Dura_Internal_R
    88000119,                              # Arachnoid_Stem_R
]

# Midline bilateral structures — keep both sides since they're shared anatomy
# dropping these creates open boundaries at the interhemispheric fissure
MIDLINE = [
    88000140,            # Falx
    88000141,            # Superior_Sagittal_Sinus
    # Note: Dura_hole (88000142) skipped — it's a contact-only null part,
    # not structural, safe to exclude
]

# ── COMBINED TARGET SET ──────────────────────────────────────────────────────
TARGET_PIDS = set(SKULL_VAULT_R + BRAIN_R + CSF_R + MENINGES_R + MIDLINE)

# ── KNOWN DEGENERATE ELEMENTS TO DELETE ─────────────────────────────────────
# These 4 elements in CSF_Stem_R/L have volume ~4.6e-14 (truly collapsed)
# and will crash LS-DYNA immediately. Delete them before solve.
# CSF_Stem_L (88000129) is dropped entirely since we're right-hemi-only,
# so only the _R degenerate elements need explicit deletion here.
DEGENERATE_EIDS = {88074992, 88075010}  # CSF_Stem_R degenerate pair
# (88171465, 88171483 are CSF_Stem_L — excluded by PID filter anyway)


# ── PARSER ───────────────────────────────────────────────────────────────────

def split_fields(line, n_fields, width=8):
    """Handles comma, space, and fixed-width I8 (THUMS) formats."""
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


def parse_full_k(path, _visited=None, _base_dir=None):
    """Full keyword parser following *INCLUDE chains."""
    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))

    real = os.path.abspath(path)
    if real in _visited:
        return {}
    _visited.add(real)

    data = {
        "nodes":      {},   # nid -> raw_line
        "node_coords":{},   # nid -> (x,y,z)
        "elems_solid":{},   # eid -> (pid, raw_line)
        "elems_shell":{},   # eid -> (pid, raw_line)
        "elems_beam": {},
        "elems_disc": {},
        "parts":      {},   # pid -> (kw_line, [data_lines])
        "sections":   {},   # secid -> (kw, lines)
        "mats":       {},   # mid -> (kw, lines)
        "eos":        {},
        "hourglass":  {},
        "define":     {},   # lcid -> (kw, lines) — *DEFINE_CURVE, *DEFINE_TABLE etc
        "raw_blocks": [],   # [(kw, lines)] for everything else
    }

    section = None
    pending_include = False
    current_part_kw = None
    current_part_lines = []
    current_kw = None
    current_lines = []
    current_id = None

    def flush_generic():
        nonlocal current_kw, current_lines
        if current_kw and current_lines:
            data["raw_blocks"].append((current_kw, list(current_lines)))
        current_kw = None
        current_lines = []

    with open(path, "r", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if line.startswith("*"):
                flush_generic()
                kw = line.strip().upper()

                if kw.startswith("*INCLUDE_TRANSFORM") or kw.startswith("*INCLUDE_STAMPED"):
                    section = None; pending_include = "skip"
                elif kw.startswith("*INCLUDE"):
                    section = None; pending_include = True
                elif kw == "*NODE":
                    section = "NODE"
                elif kw.startswith("*ELEMENT_SOLID") or kw.startswith("*ELEMENT_TSHELL"):
                    section = "SOLID"
                elif kw.startswith("*ELEMENT_SHELL"):
                    section = "SHELL"
                elif kw.startswith("*ELEMENT_BEAM"):
                    section = "BEAM"
                elif kw.startswith("*ELEMENT_DISCRETE"):
                    section = "DISC"
                elif kw.startswith("*PART"):
                    section = "PART"
                    current_part_kw = line.strip()
                    current_part_lines = []
                elif kw.startswith("*SECTION"):
                    section = "SECTION"; current_kw = line.strip()
                    current_lines = []; current_id = None
                elif kw.startswith("*MAT") or kw.startswith("*MATERIAL"):
                    section = "MAT"; current_kw = line.strip()
                    current_lines = []; current_id = None
                elif kw.startswith("*EOS"):
                    section = "EOS"; current_kw = line.strip()
                    current_lines = []; current_id = None
                elif kw.startswith("*HOURGLASS"):
                    section = "HG"; current_kw = line.strip()
                    current_lines = []; current_id = None
                elif kw.startswith("*DEFINE"):
                    section = "DEFINE"; current_kw = line.strip()
                    current_lines = []; current_id = None
                else:
                    section = "GENERIC"; current_kw = line.strip()
                    current_lines = []
                continue

            if line.startswith("$"):
                if section == "PART":
                    current_part_lines.append(line)
                elif section == "GENERIC":
                    current_lines.append(line)
                continue

            # include resolution
            if pending_include == True:
                inc_name = line.strip().strip('"')
                inc_path = (inc_name if os.path.isabs(inc_name)
                            else os.path.join(_base_dir, inc_name))
                if os.path.exists(inc_path):
                    sub = parse_full_k(inc_path, _visited, _base_dir)
                    for k in ("nodes","node_coords","elems_solid","elems_shell",
                              "elems_beam","elems_disc","parts","sections",
                              "mats","eos","hourglass","define"):
                        data[k].update(sub.get(k, {}))
                    data["raw_blocks"].extend(sub.get("raw_blocks", []))
                else:
                    print(f"  ⚠ include not found: {inc_path}")
                pending_include = False
                continue

            if not line.strip():
                continue

            # data sections
            if section == "NODE":
                vals = line.split(",") if "," in line else line.split()
                try:
                    nid = int(vals[0])
                    x, y, z = float(vals[1]), float(vals[2]), float(vals[3])
                    data["nodes"][nid] = line
                    data["node_coords"][nid] = (x, y, z)
                except (ValueError, IndexError):
                    pass

            elif section == "SOLID":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    data["elems_solid"][vals[0]] = (vals[1], line)

            elif section == "SHELL":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    data["elems_shell"][vals[0]] = (vals[1], line)

            elif section == "BEAM":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    data["elems_beam"][vals[0]] = (vals[1], line)

            elif section == "DISC":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3:
                    data["elems_disc"][vals[0]] = (vals[1], line)

            elif section == "PART":
                current_part_lines.append(line)
                data_lines = [l for l in current_part_lines if not l.startswith("$")]
                if len(data_lines) == 2:
                    try:
                        vals = (data_lines[1].split(",") if "," in data_lines[1]
                                else data_lines[1].split())
                        pid = int(vals[0])
                        data["parts"][pid] = (current_part_kw, list(current_part_lines))
                    except (ValueError, IndexError):
                        pass
                    section = None

            elif section in ("SECTION","MAT","EOS","HG","DEFINE"):
                current_lines.append(line)
                if current_id is None:
                    try:
                        vals = line.split(",") if "," in line else line.split()
                        current_id = int(vals[0])
                        target = {"SECTION":"sections","MAT":"mats",
                                  "EOS":"eos","HG":"hourglass",
                                  "DEFINE":"define"}[section]
                        data[target][current_id] = (current_kw, current_lines)
                    except (ValueError, IndexError):
                        pass

            elif section == "GENERIC":
                current_lines.append(line)

    flush_generic()
    return data


# ── EXTRACTOR ────────────────────────────────────────────────────────────────

def extract_and_write(data, target_pids, degenerate_eids, output_path):
    target_pids = set(target_pids)
    degenerate_eids = set(degenerate_eids)

    # filter elements
    kept_solid = {eid: v for eid, v in data["elems_solid"].items()
                  if v[0] in target_pids and eid not in degenerate_eids}
    kept_shell = {eid: v for eid, v in data["elems_shell"].items()
                  if v[0] in target_pids}
    kept_beam  = {eid: v for eid, v in data["elems_beam"].items()
                  if v[0] in target_pids}
    kept_disc  = {eid: v for eid, v in data["elems_disc"].items()
                  if v[0] in target_pids}

    total_elems = len(kept_solid) + len(kept_shell) + len(kept_beam) + len(kept_disc)

    # collect referenced nodes
    used_nids = set()
    for eid, (pid, raw) in {**kept_solid, **kept_shell,
                             **kept_beam, **kept_disc}.items():
        vals = split_fields(raw, 3, 8)
        if vals:
            used_nids.update(v for v in vals[2:] if v > 0)
    kept_nodes = {nid: data["nodes"][nid] for nid in used_nids
                  if nid in data["nodes"]}

    # collect parts and their referenced MAT/SEC/EOS/HG
    kept_parts = {pid: data["parts"][pid] for pid in target_pids
                  if pid in data["parts"]}
    needed_sec, needed_mat, needed_eos, needed_hg = set(), set(), set(), set()
    for pid, (kw, part_lines) in kept_parts.items():
        dl = [l for l in part_lines if not l.startswith("$")]
        if len(dl) >= 2:
            vals = dl[1].split(",") if "," in dl[1] else dl[1].split()
            try:
                if len(vals) > 1 and int(vals[1]) > 0: needed_sec.add(int(vals[1]))
                if len(vals) > 2 and int(vals[2]) > 0: needed_mat.add(int(vals[2]))
                if len(vals) > 3 and int(vals[3]) > 0: needed_eos.add(int(vals[3]))
                if len(vals) > 5 and int(vals[5]) > 0: needed_hg.add(int(vals[5]))
            except (ValueError, IndexError):
                pass

    # print summary
    print(f"\n  Parts kept     : {len(kept_parts)}")
    print(f"  Nodes kept     : {len(kept_nodes):,}")
    print(f"  Solid elements : {len(kept_solid):,}")
    print(f"  Shell elements : {len(kept_shell):,}")
    print(f"  Total elements : {total_elems:,}")
    print(f"  Deleted degen  : {len(degenerate_eids)} (CSF_Stem_R collapsed elements)")

    if total_elems > 128000:
        print(f"\n  ⚠ Still over cap ({total_elems:,} > 128,000)")
        print("  -> Ask professor for a coarser mesh version.")
    elif total_elems > 110000:
        print(f"\n  ⚠ Close to cap — leave headroom for contact segments at solve time")
    else:
        print(f"\n  ✓ Under 128K cap with {128000 - total_elems:,} elements headroom")

    # write output
    with open(output_path, "w") as f:
        f.write("*KEYWORD\n")
        f.write("$\n")
        f.write("$ Head_V6.k — Right hemisphere only\n")
        f.write("$ Skull: cranial vault R (frontal/parietal/temporal/occipital/sphenoid/ethmoid)\n")
        f.write("$ Brain: white+gray matter R (cerebrum, cerebellum, brainstem)\n")
        f.write("$ CSF+meninges: R side + bilateral midline (falx, sagittal sinus)\n")
        f.write(f"$ Parts: {len(kept_parts)}  Nodes: {len(kept_nodes):,}  "
                f"Elements: {total_elems:,}\n")
        f.write("$ Degenerate elements deleted: CSF_Stem_R EIDs 88074992, 88075010\n")
        f.write("$\n")

        # nodes
        f.write("*NODE\n")
        for nid in sorted(kept_nodes):
            line = kept_nodes[nid]
            f.write(line if line.endswith("\n") else line + "\n")

        # solid elements
        if kept_solid:
            f.write("*ELEMENT_SOLID\n")
            for eid in sorted(kept_solid):
                line = kept_solid[eid][1]
                f.write(line if line.endswith("\n") else line + "\n")

        # shell elements
        if kept_shell:
            f.write("*ELEMENT_SHELL\n")
            for eid in sorted(kept_shell):
                line = kept_shell[eid][1]
                f.write(line if line.endswith("\n") else line + "\n")

        if kept_beam:
            f.write("*ELEMENT_BEAM\n")
            for eid in sorted(kept_beam):
                line = kept_beam[eid][1]
                f.write(line if line.endswith("\n") else line + "\n")

        if kept_disc:
            f.write("*ELEMENT_DISCRETE\n")
            for eid in sorted(kept_disc):
                line = kept_disc[eid][1]
                f.write(line if line.endswith("\n") else line + "\n")

        # parts
        for pid in sorted(kept_parts):
            kw, lines = kept_parts[pid]
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")

        # define curves/tables — copy ALL (load curves referenced by MAT cards)
        define_written = set()
        for did, (kw, lines) in data["define"].items():
            if did in define_written:
                continue
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")
            define_written.add(did)

        # sections — copy ALL (THUMS uses PID-matching IDs, selective
        # filtering is fragile; copying all is safe and adds negligible size)
        sections_written = set()
        for sid, (kw, lines) in data["sections"].items():
            if sid in sections_written:
                continue
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")
            sections_written.add(sid)

        # materials — copy ALL (THUMS MAT IDs match PIDs,
        # cross-referencing makes selective collection unreliable)
        mat_written = set()
        for mid, (kw, lines) in data["mats"].items():
            if mid in mat_written:
                continue
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")
            mat_written.add(mid)

        # EOS — copy ALL (small cards, safe to include all)
        eos_written = set()
        for eid2, (kw, lines) in data["eos"].items():
            if eid2 in eos_written:
                continue
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")
            eos_written.add(eid2)

        # hourglass — copy ALL (small cards, THUMS uses PID-matching IDs)
        hg_written = set()
        for hid, (kw, lines) in data["hourglass"].items():
            if hid in hg_written:
                continue
            f.write(kw + "\n")
            for l in lines:
                f.write(l if l.endswith("\n") else l + "\n")
            hg_written.add(hid)

        f.write("*END\n")

    print(f"\n  Written: {output_path}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_k = sys.argv[1]
    out_arg = next((sys.argv[i+1] for i, a in enumerate(sys.argv)
                    if a == "--output" and i+1 < len(sys.argv)), None)
    output_k = out_arg or (os.path.splitext(input_k)[0] + "_right_hemi.k")

    print(f"\nInput : {input_k}")
    print(f"Output: {output_k}")
    print(f"Target PIDs: {len(TARGET_PIDS)}")
    print(f"  Skull vault R   : {len(SKULL_VAULT_R)} parts")
    print(f"  Brain R         : {len(BRAIN_R)} parts")
    print(f"  CSF R           : {len(CSF_R)} parts")
    print(f"  Meninges R      : {len(MENINGES_R)} parts")
    print(f"  Midline bilateral: {len(MIDLINE)} parts")
    print(f"  Degenerate EIDs to delete: {sorted(DEGENERATE_EIDS)}\n")

    print("Parsing keyword file (following *INCLUDEs)...")
    data = parse_full_k(input_k)
    print(f"Loaded: {len(data['nodes']):,} nodes, "
          f"{len(data['elems_solid']):,} solids, "
          f"{len(data['elems_shell']):,} shells, "
          f"{len(data['parts'])} parts\n")

    print("Extracting right hemisphere...")
    extract_and_write(data, TARGET_PIDS, DEGENERATE_EIDS, output_k)

    print(f"\nNext steps:")
    print(f"  1. QA check  : python k_mesh_qa.py \"{output_k}\"")
    print(f"  2. Solve test: cd to output folder, run LS-DYNA on the output file")
    print(f"  3. If solve passes: this is your BASELINE")
    print(f"  4. Apply warp, re-extract right hemi, re-solve: WARPED result")
    print(f"  5. Compare strain fields in LS-PrePost: baseline vs warped")


if __name__ == "__main__":
    main()