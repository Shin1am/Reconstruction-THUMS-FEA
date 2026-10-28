"""Compare QA-flagged elements: unwarped template vs. the registered v3 output.

Read-only. Uses the original element connectivity with each mesh's node
coordinates, exactly as the notebook's QA cell does.
"""
import io
import sys
from contextlib import redirect_stdout

import numpy as np
import pyvista as pv

ROOT = "/Volumes/Extreme SSD/2d_3d_regis dataset/New_version"
sys.path.insert(0, f"{ROOT}/Code/python")
from k_mesh_qa import parse_k_file, check_mesh

nodes0, solids, shells = parse_k_file(f"{ROOT}/Data/Ls_dyna_model/Head_V6.k")

reg = pv.read(f"{ROOT}/Data/outputs/cpd_tps_skin_registration/Head_V6_skin_registered_v3.vtu")
node_ids = np.asarray(reg.point_data["node_id"])
nodes1 = dict(nodes0)
nodes1.update({int(n): xyz for n, xyz in zip(node_ids, np.asarray(reg.points))})

with redirect_stdout(io.StringIO()):
    r0 = check_mesh(nodes0, solids, label="template", elems_shell=shells)
    r1 = check_mesh(nodes1, solids, label="registered_v3", elems_shell=shells)

b0, b1 = set(r0["bad_eids"]), set(r1["bad_eids"])
print(f"template   flagged: {len(b0):,}  (inverted {r0['n_inverted']:,}, degenerate {r0['n_degenerate']:,})")
print(f"registered flagged: {len(b1):,}  (inverted {r1['n_inverted']:,}, degenerate {r1['n_degenerate']:,})")
print(f"flagged in BOTH           : {len(b0 & b1):,}")
print(f"flagged only in template  : {len(b0 - b1):,}  (registration un-flagged these)")
print(f"flagged only in registered: {len(b1 - b0):,}  (newly flagged after registration)")
print(f"share of registered flags already present in template: {100*len(b0 & b1)/len(b1):.1f}%")
print(f"total solid elements: {len(solids):,}")
print(f"registered inverted rate: {100*r1['n_inverted']/len(solids):.3f}%  | template: {100*r0['n_inverted']/len(solids):.3f}%")
