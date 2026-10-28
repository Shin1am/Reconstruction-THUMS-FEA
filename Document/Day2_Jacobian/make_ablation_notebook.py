"""A1 ablation: same pipeline, but skip the direct overwrite of the 6,182 skin nodes.

Only one line of the frozen notebook's save cell is removed; every parameter and
earlier stage is unchanged. Output goes to a scratch folder.
"""
import json
import sys

src, dst = sys.argv[1:3]
OVERWRITE = "updated_coords.update({int(nid): xyz for nid, xyz in zip(skin_surf_node_ids, skin_world_coords)})"
nb = json.load(open(src))
hits = 0
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        text = "".join(cell["source"])
        if OVERWRITE in text:
            text = text.replace(OVERWRITE, "# ABLATION A1: skin overwrite removed")
            cell["source"] = text.splitlines(keepends=True)
            hits += 1
assert hits == 1, f"expected exactly one overwrite line, found {hits}"
json.dump(nb, open(dst, "w"), indent=1)
print("patched", dst)
