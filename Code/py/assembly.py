"""
Assemble final LS-DYNA impact simulation file from components.
Combines: head geometry + BC nodes + control cards → one clean .k file

Usage:
    python assemble_impact.py Head_V6_right_hemi.k

This script:
  1. Reads Head_V6_right_hemi.k (geometry + materials)
  2. Extracts BC nodes from skull base connector parts
  3. Appends impact control cards (termination, timestep, load, output)
  4. Writes Head_V6_impact_baseline.k — ready to solve

After warp, run same script on warped_Head_V6_right_hemi.k to get
Head_V6_impact_warped.k — solve both, compare results.
"""

import os, sys, io

# ── IMPACT PARAMETERS (adjust to match your target impact scenario) ───────────
TERMINATION_TIME  = 1.0e-2   # 10ms — covers full primary impact event
TIMESTEP_SAFETY   = 0.90     # 90% of stable timestep (standard explicit)
INITIAL_VELOCITY  = -5000.0  # mm/s in Y direction (-5 m/s downward)
                              # Adjust sign/direction after checking coordinate
                              # system in LS-PrePost (which axis is superior?)
D3PLOT_INTERVAL   = 1.0e-4   # write results every 0.1ms = 100 frames total
HISTORY_INTERVAL  = 1.0e-5   # energy/node histories every 0.01ms

# ── BC PIDS: skull base connectors R (cut-plane attachment) ──────────────────
BC_PIDS = {
    88000042, 88000043, 88000044, 88000045, 88000046,  # str1-str5 R
    88000047, 88000048, 88000049, 88000050, 88000051,  # str5_shell,str6_shell,str7,ng-str,ng-str2 R
    88000257, 88000259,                                  # Str_Shell_External_R, Str_Shell_Internal_R
}
BC_SET_ID = 99999001


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


def extract_bc_nodes_from_file(path, target_pids,
                                _visited=None, _base_dir=None):
    if _visited is None:
        _visited = set()
    if _base_dir is None:
        _base_dir = os.path.dirname(os.path.abspath(path))
    real = os.path.abspath(path)
    if real in _visited:
        return set()
    _visited.add(real)

    bc_nodes = set()
    section = None
    pending_include = False

    with open(path, "r", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("*"):
                kw = line.strip().upper()
                if kw.startswith("*INCLUDE_TRANSFORM"):
                    section = None; pending_include = "skip"
                elif kw.startswith("*INCLUDE"):
                    section = None; pending_include = True
                elif any(kw.startswith(x) for x in
                         ("*ELEMENT_SOLID","*ELEMENT_SHELL",
                          "*ELEMENT_BEAM","*ELEMENT_DISC")):
                    section = "ELEM"
                else:
                    section = None
                continue
            if line.startswith("$") or not line.strip():
                continue
            if pending_include == True:
                inc_name = line.strip().strip('"')
                inc_path = (inc_name if os.path.isabs(inc_name)
                            else os.path.join(_base_dir, inc_name))
                if os.path.exists(inc_path):
                    bc_nodes.update(extract_bc_nodes_from_file(
                        inc_path, target_pids, _visited, _base_dir))
                pending_include = False
                continue
            if section == "ELEM":
                vals = split_fields(line, 3, 8)
                if vals and len(vals) >= 3 and vals[1] in target_pids:
                    bc_nodes.update(v for v in vals[2:] if v > 0)
    return bc_nodes


def read_geometry_block(path):
    """Read source .k file, strip *END, return as string."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # Remove trailing *END so we can append more cards
    lines = content.rstrip().split("\n")
    while lines and lines[-1].strip().upper() in ("*END", ""):
        lines.pop()
    return "\n".join(lines) + "\n"


def build_bc_block(bc_nodes):
    """Build *SET_NODE_LIST + *BOUNDARY_SPC_SET text block."""
    nodes = sorted(bc_nodes)
    out = io.StringIO()
    out.write("$\n$ --- BOUNDARY CONDITIONS (neck cut plane) ---\n")
    out.write(f"$ {len(nodes)} nodes from skull base connector PIDs\n$\n")
    out.write("*SET_NODE_LIST\n")
    out.write(f"$ SID\n")
    out.write(f"{BC_SET_ID}\n")
    for i in range(0, len(nodes), 8):
        chunk = nodes[i:i+8]
        out.write(",".join(str(n) for n in chunk) + "\n")
    out.write("$\n*BOUNDARY_SPC_SET\n")
    out.write("$ NSID,CID,DOFX,DOFY,DOFZ,DOFRX,DOFRY,DOFRZ\n")
    out.write(f"{BC_SET_ID},0,1,1,1,1,1,1\n")
    return out.getvalue()


def build_control_block(label="baseline"):
    """Build simulation control cards."""
    out = io.StringIO()
    out.write(f"$\n$ --- SIMULATION CONTROL ({label}) ---\n$\n")

    out.write("*CONTROL_TERMINATION\n")
    out.write("$ ENDTIM,ENDCYC,DTMIN,ENDENG,ENDMAS\n")
    out.write(f"{TERMINATION_TIME:.4E},0,0.0,0.0,0.0\n")

    out.write("*CONTROL_TIMESTEP\n")
    out.write("$ DTINIT,TSSFAC,ISDO,TSLIMT,DT2MS\n")
    out.write(f"0.0,{TIMESTEP_SAFETY:.2f},0,0.0,0.0\n")

    out.write("*CONTROL_BULK_VISCOSITY\n")
    out.write("$ Q1,Q2\n")
    out.write("1.5,0.06\n")

    out.write("*CONTROL_ENERGY\n")
    out.write("$ HGEN,RWEN,SLNTEN,RYLEN\n")
    out.write("2,2,2,2\n")

    out.write("*DATABASE_BINARY_D3PLOT\n")
    out.write("$ DT\n")
    out.write(f"{D3PLOT_INTERVAL:.4E}\n")

    # DATABASE_EXTENT_BINARY: use minimal safe card — just strain flag
    # The full 8-field version causes format errors in some LS-DYNA versions
    out.write("*DATABASE_EXTENT_BINARY\n")
    out.write("$ NEIPH,NEIPS,MAXINT,STRFLG\n")
    out.write("0,1,3,1\n")

    out.write("*DATABASE_GLSTAT\n")
    out.write("$ DT\n")
    out.write(f"{HISTORY_INTERVAL:.4E}\n")

    out.write("*DATABASE_MATSUM\n")
    out.write("$ DT\n")
    out.write(f"{HISTORY_INTERVAL:.4E}\n")

    # Initial velocity - entire model
    out.write("$\n$ --- IMPACT LOAD ---\n")
    out.write("$ Initial velocity applied to all unconstrained nodes\n")
    out.write(f"$ Velocity: {INITIAL_VELOCITY} mm/s in Y ({INITIAL_VELOCITY/1000:.1f} m/s)\n")
    out.write("$ CHECK AXIS IN LS-PREPOST: View > Coordinate Axes\n")
    out.write("$ If Z is vertical, change VY to VZ below\n$\n")
    out.write("*INITIAL_VELOCITY_GENERATION\n")
    out.write("$ ID,STYP,OMEGA,VX,VY,VZ,IVATN,ICID\n")
    out.write(f"1,2,0.0,0.0,{INITIAL_VELOCITY:.1f},0.0,0,0\n")

    return out.getvalue()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_k = sys.argv[1]
    label = "warped" if "warp" in input_k.lower() else "baseline"
    base = os.path.splitext(input_k)[0]
    output_k = base.replace("_right_hemi", "") + f"_impact_{label}.k"

    print(f"\nInput  : {input_k}")
    print(f"Label  : {label}")
    print(f"Output : {output_k}\n")

    # 1. Read geometry
    print("Reading geometry block...")
    geom = read_geometry_block(input_k)
    print(f"  {len(geom.splitlines())} lines of geometry/material data\n")

    # 2. Extract BC nodes
    print("Extracting skull base BC nodes...")
    bc_nodes = extract_bc_nodes_from_file(input_k, BC_PIDS)
    if not bc_nodes:
        print("  ⚠ No BC nodes found in this file!")
        print("  The str1-str7 parts may have been excluded from extraction.")
        print("  Check: python list_parts.py your_file.k str")
        print("  Proceeding without BC — model will be unconstrained (rigid body motion possible)")
    else:
        print(f"  Found {len(bc_nodes)} boundary nodes\n")

    # 3. Build output
    print("Assembling impact simulation file...")
    with open(output_k, "w", encoding="utf-8") as f:
        f.write(geom)
        if bc_nodes:
            f.write(build_bc_block(bc_nodes))
        f.write(build_control_block(label))
        f.write("*END\n")

    print(f"\n  Written: {output_k}")
    print(f"\n-----------------------------------------------------")
    print(f"IMPORTANT: Before solving, open in LS-PrePost and check:")
    print(f"  1. Coordinate axes (View menu) - confirm Y is superior/inferior")
    print(f"     If Z is vertical in your model, change VZ={INITIAL_VELOCITY} in the file")
    print(f"  2. BC nodes highlighted correctly (skull base, not brain)")
    print(f"-----------------------------------------------------")
    print(f"\nSolve command (from {os.path.dirname(os.path.abspath(output_k))}):")
    solver = ("C:\\Program Files\\LS-DYNA Suite R16.1 Student\\lsdyna\\"
              "ls-dyna_smp_d_R16.1_180-gd50332dbe5_winx64_ifort190_sse2_studentversion.exe")
    fname = os.path.basename(output_k)
    print(f'  "{solver}" --% i={fname} ncpu=4 memory=600m')
    print(f"\nAfter solve, check in LS-PrePost:")
    print(f"  1. File > Open > LS-DYNA Binary Plot > d3plot")
    print(f"  2. Fringe > Element > Strain > Max Principal  (brain MPS)")
    print(f"  3. Post > History > glstat > hourglass/internal energy ratio")
    print(f"     (must stay < 0.10 = 10% throughout simulation) 2")


if __name__ == "__main__":
    main()