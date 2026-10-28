"""A3 ablation: propagate the Stage-6 skin (after ICP, before the blend) instead of the refined skin.

In the save cell only the target skin positions change: nm_surf_final_cs -> nm_surf_icp_cs
(both for the 5b TPS fit and for the skin-node write). Everything before it is unchanged.
"""
import json
import sys

src, dst = sys.argv[1:3]
nb = json.load(open(src))
hits = 0
for cell in nb["cells"]:
    text = "".join(cell["source"]) if cell["cell_type"] == "code" else ""
    if "tps_final = RBFInterpolator" in text:
        assert text.count("nm_surf_final_cs") == 2, text.count("nm_surf_final_cs")
        cell["source"] = text.replace("nm_surf_final_cs", "nm_surf_icp_cs").splitlines(keepends=True)
        hits += 1
assert hits == 1
json.dump(nb, open(dst, "w"), indent=1)
print("patched", dst)
