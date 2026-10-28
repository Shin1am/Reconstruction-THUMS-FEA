"""Control measurement: run the same mesh-QA on the UNWARPED template Head_V6.k.

Shows how many elements the QA checker already flags before any registration,
so the 7,334 inverted elements after registration can be read against it.
"""
import sys

ROOT = "/Volumes/Extreme SSD/2d_3d_regis dataset/New_version"
sys.path.insert(0, f"{ROOT}/Code/python")
from k_mesh_qa import parse_k_file, check_mesh

nodes, solids, shells = parse_k_file(f"{ROOT}/Data/Ls_dyna_model/Head_V6.k")
print(f"nodes={len(nodes):,} solids={len(solids):,} shells={len(shells):,}")
check_mesh(nodes, solids, label="TEMPLATE Head_V6.k (unwarped control)", elems_shell=shells)
