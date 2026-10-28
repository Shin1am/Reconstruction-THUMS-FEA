# %% [markdown]
# # Jacobian diagnostic: template vs. registered mesh
#
# Read-only. Compares per-corner element Jacobians of the original template
# (`Head_V6.k`) with the registered mesh (`Head_V6_skin_registered_v3.vtu`).
# Separates elements that were already bad in the template from elements the
# warp broke, using the *sign change* of each corner Jacobian (independent of
# winding convention).

# %%
import json
import os
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pyvista as pv

matplotlib.use("Agg") if "ipykernel" not in sys.modules else None
import matplotlib.pyplot as plt

ROOT = Path("D:/2d_3d_regis dataset/New_version")
OUT = Path(os.environ.get("JAC_OUT", ROOT / "Document" / "Day2_Jacobian"))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "Code" / "python"))
from k_mesh_qa import parse_k_file

TEMPLATE_K = ROOT / "Data/Ls_dyna_model/Head_V6.k"
REGISTERED = Path(os.environ.get("JAC_REGISTERED", ROOT / "Data/outputs/cpd_tps_skin_registration/Head_V6_skin_registered_v3.vtu"))

# %% [markdown]
# ## 1. Load template connectivity + both sets of node coordinates

# %%
nodes, solids, _ = parse_k_file(str(TEMPLATE_K))
node_ids = np.array(sorted(nodes))
X0 = np.array([nodes[n] for n in node_ids], dtype=np.float64)

reg = pv.read(str(REGISTERED))
reg_ids = np.asarray(reg.point_data["node_id"])
order = np.argsort(reg_ids)
pos = np.searchsorted(reg_ids[order], node_ids)
assert (reg_ids[order][pos] == node_ids).all(), "node id mismatch between template and registered mesh"
X1 = np.asarray(reg.points, dtype=np.float64)[order][pos]

eids = np.array(sorted(solids))
pids = np.array([solids[e][0] for e in eids])
conn_ids = np.array([solids[e][1] for e in eids])
conn = np.searchsorted(node_ids, conn_ids)
n_unique = np.array([len(set(row)) for row in conn_ids])
kind = np.where(n_unique == 8, "hex", np.where(n_unique == 4, "tet (collapsed hex)", "wedge/other (collapsed hex)"))
print(f"{len(eids):,} solids | nodes {len(node_ids):,}")
print(pd.Series(kind).value_counts().to_string())
print("max node displacement (registered - template):", np.abs(X1 - X0).max().round(2))

# %% [markdown]
# ## 2. Corner Jacobians
#
# For each hex corner, `det[e1, e2, e3]` of the three edge vectors leaving it.
# Corners that touch a repeated node (collapsed tets and wedges) are skipped,
# because their edge vectors are zero by construction. Scaled Jacobian =
# det / (|e1||e2||e3|), in [-1, 1].

# %%
CORNERS = [(0, (1, 3, 4)), (1, (2, 0, 5)), (2, (3, 1, 6)), (3, (0, 2, 7)),
           (4, (7, 5, 0)), (5, (4, 6, 1)), (6, (5, 7, 2)), (7, (6, 4, 3))]


def corner_jacobians(X):
    P = X[conn]
    det = np.zeros((len(conn), 8))
    norm = np.zeros((len(conn), 8))
    for c, (a, b, d) in CORNERS:
        e1, e2, e3 = P[:, a] - P[:, c], P[:, b] - P[:, c], P[:, d] - P[:, c]
        det[:, c] = np.einsum("ij,ij->i", e1, np.cross(e2, e3))
        norm[:, c] = np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1) * np.linalg.norm(e3, axis=1)
    return det, norm


valid = np.zeros((len(conn), 8), dtype=bool)
for c, (a, b, d) in CORNERS:
    cols = [c, a, b, d]
    ok = np.ones(len(conn), dtype=bool)
    for i in range(4):
        for j in range(i + 1, 4):
            ok &= conn_ids[:, cols[i]] != conn_ids[:, cols[j]]
    valid[:, c] = ok
print("elements with no valid corner:", int((~valid.any(1)).sum()))

det0, nrm0 = corner_jacobians(X0)
det1, nrm1 = corner_jacobians(X1)
sj0 = np.where(valid, det0 / np.maximum(nrm0, 1e-300), np.nan)
sj1 = np.where(valid, det1 / np.maximum(nrm1, 1e-300), np.nan)


def state(sj):
    lo, hi = np.nanmin(sj, axis=1), np.nanmax(sj, axis=1)
    s = np.full(len(lo), "ok", dtype=object)
    s[lo <= 0] = "degenerate (zero corner)"
    s[(lo < 0) & (hi > 0)] = "twisted (mixed signs)"
    s[hi < 0] = "reversed (all corners negative)"
    return s, lo


st0, minsj0 = state(sj0)
st1, minsj1 = state(sj1)

# %% [markdown]
# ## 3. Template vs registered, by element state

# %%
order_states = ["ok", "degenerate (zero corner)", "twisted (mixed signs)", "reversed (all corners negative)"]
table = pd.crosstab(pd.Categorical(st0, order_states), pd.Categorical(st1, order_states),
                    rownames=["template"], colnames=["registered"], dropna=False)
print(table.to_string())

fail0, fail1 = st0 != "ok", st1 != "ok"
newly = (~fail0) & fail1
fixed = fail0 & (~fail1)
flip = ((det0 * det1 < 0) & valid).any(1)
print(f"\nfailing in template     : {fail0.sum():,}  ({100*fail0.mean():.3f}%)")
print(f"failing in registered   : {fail1.sum():,}  ({100*fail1.mean():.3f}%)")
print(f"newly failing (warp)    : {newly.sum():,}")
print(f"fixed by the warp       : {fixed.sum():,}")
print(f"any corner changed sign : {flip.sum():,}")
print("\nfailing by element kind (template -> registered):")
print(pd.DataFrame({"kind": kind, "template": fail0, "registered": fail1, "newly": newly})
      .groupby("kind").sum().assign(total=pd.Series(kind).value_counts()).to_string())

# %% [markdown]
# ## 4. Where the problems are, by part

# %%
names = {}
for line in open(TEMPLATE_K, errors="ignore"):
    if line.startswith("$HMNAME COMPS"):
        m = re.match(r"\$HMNAME COMPS\s*(\d+)(.*)", line.strip())
        if m:
            names[int(m.group(1))] = m.group(2).strip().strip('"')

df = pd.DataFrame({"pid": pids, "fail_template": fail0, "fail_registered": fail1,
                   "newly_failing": newly, "fixed": fixed, "sign_flipped": flip,
                   "reversed_template": st0 == "reversed (all corners negative)"})
per_part = df.groupby("pid").agg(elements=("pid", "size"), fail_template=("fail_template", "sum"),
                                 fail_registered=("fail_registered", "sum"), newly_failing=("newly_failing", "sum"),
                                 fixed=("fixed", "sum"), reversed_template=("reversed_template", "sum")).reset_index()
per_part["name"] = per_part["pid"].map(names).fillna("?")
per_part["pct_fail_template"] = (100 * per_part.fail_template / per_part.elements).round(1)
per_part["pct_fail_registered"] = (100 * per_part.fail_registered / per_part.elements).round(1)
per_part = per_part.sort_values("fail_registered", ascending=False)
per_part.to_csv(OUT / "jacobian_per_part.csv", index=False)
cols = ["pid", "name", "elements", "fail_template", "fail_registered", "newly_failing", "fixed", "pct_fail_template", "pct_fail_registered"]
print("top 15 parts by failing elements in the registered mesh:")
print(per_part[cols].head(15).to_string(index=False))
print("\ntop 10 parts by NEWLY failing elements:")
print(per_part.sort_values("newly_failing", ascending=False)[cols].head(10).to_string(index=False))
print(f"\nparts with >50% reversed elements in the template: {(per_part.reversed_template / per_part.elements > 0.5).sum()}")
print(f"parts with any failing element: template {(per_part.fail_template > 0).sum()}, registered {(per_part.fail_registered > 0).sum()} of {len(per_part)}")

pd.DataFrame({"element_id": eids[newly], "pid": pids[newly], "part": [names.get(p, "?") for p in pids[newly]],
              "min_scaled_jacobian_template": minsj0[newly], "min_scaled_jacobian_registered": minsj1[newly]}
             ).to_csv(OUT / "jacobian_newly_failing_elements.csv", index=False)

# %% [markdown]
# ## 5. How much the warp stretches the elements that stayed valid

# %%
both_ok = (~fail0) & (~fail1)
v0 = np.nanmean(np.where(valid, det0, np.nan), axis=1)
v1 = np.nanmean(np.where(valid, det1, np.nan), axis=1)
ratio = v1[both_ok] / v0[both_ok]
q = np.quantile(ratio, [0.01, 0.05, 0.5, 0.95, 0.99])
print("element volume ratio registered/template (elements valid in both):")
print("  1%, 5%, 50%, 95%, 99% =", np.round(q, 3))
print(f"  compressed below 0.1x: {(ratio < 0.1).sum():,}   below 0.5x: {(ratio < 0.5).sum():,}   stretched above 2x: {(ratio > 2).sum():,}   above 10x: {(ratio > 10).sum():,}")
print("\nmin scaled Jacobian quantiles (all elements)   1%    5%    median")
print("  template  :", np.round(np.nanquantile(minsj0, [0.01, 0.05, 0.5]), 3))
print("  registered:", np.round(np.nanquantile(minsj1, [0.01, 0.05, 0.5]), 3))
print(f"elements with 0 < min scaled Jacobian < 0.1 (valid but poor): template {((minsj0 > 0) & (minsj0 < 0.1)).sum():,}, registered {((minsj1 > 0) & (minsj1 < 0.1)).sum():,}")

# %%
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
bins = np.linspace(-1, 1, 81)
ax[0].hist(np.clip(minsj0, -1, 1), bins=bins, alpha=0.6, label="template")
ax[0].hist(np.clip(minsj1, -1, 1), bins=bins, alpha=0.6, label="registered")
ax[0].set_yscale("log"); ax[0].set_xlabel("min scaled Jacobian per element"); ax[0].set_ylabel("elements (log)")
ax[0].axvline(0, color="k", lw=0.8); ax[0].legend(); ax[0].set_title("Element Jacobian quality")
top = per_part.head(12).iloc[::-1]
y = np.arange(len(top))
ax[1].barh(y + 0.2, top.fail_template, height=0.4, label="template")
ax[1].barh(y - 0.2, top.fail_registered, height=0.4, label="registered")
ax[1].set_yticks(y); ax[1].set_yticklabels([f"{p} {n[:22]}" for p, n in zip(top.pid, top.name)], fontsize=7)
ax[1].set_xlabel("failing elements"); ax[1].legend(); ax[1].set_title("Top 12 parts by failing elements")
plt.tight_layout(); plt.savefig(OUT / "jacobian_overview.png", dpi=130)
if "ipykernel" in sys.modules:
    plt.show()

# %%
summary = {
    "solid_elements": int(len(eids)),
    "element_kinds": pd.Series(kind).value_counts().to_dict(),
    "failing_template": int(fail0.sum()), "failing_registered": int(fail1.sum()),
    "newly_failing": int(newly.sum()), "fixed_by_warp": int(fixed.sum()), "any_corner_sign_change": int(flip.sum()),
    "template_states": pd.Series(st0).value_counts().to_dict(), "registered_states": pd.Series(st1).value_counts().to_dict(),
    "volume_ratio_quantiles_1_5_50_95_99": [float(x) for x in q],
}
json.dump(summary, open(OUT / "jacobian_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))

# %% [markdown]
# ## 6. Is it the skin refinement? Elements touching directly-overwritten skin nodes
#
# Stage 5b moves every node by one smooth TPS field, then overwrites the 6,182
# outer-skin nodes with their individually refined (ICP + blend) positions.
# If failing elements sit where those two rules meet, elements with some but
# not all nodes overwritten should fail far more often.

# %%
tmpl = pv.read(str(ROOT / "Data/mesh_model/Head_V6.vtu"))
SKIN_EXTERNAL_PIDS = [88000221, 88000222, 88000223, 88000229, 88000230, 88000231]
cells = np.where(np.isin(tmpl.cell_data["part_id"], SKIN_EXTERNAL_PIDS))[0]
overwritten_ids = np.asarray(tmpl.extract_cells(cells).extract_surface(algorithm="dataset_surface").point_data["node_id"])
is_over = np.isin(conn_ids, overwritten_ids)
n_over = np.array([len(set(r[m])) for r, m in zip(conn_ids, is_over)])
print(f"overwritten skin nodes: {len(overwritten_ids):,}")
share = pd.DataFrame({"overwritten_nodes_in_element": n_over, "newly_failing": newly})
by = share.groupby("overwritten_nodes_in_element").agg(elements=("newly_failing", "size"), newly_failing=("newly_failing", "sum"))
by["pct_newly_failing"] = (100 * by.newly_failing / by.elements).round(2)
print(by.to_string())
print(f"\nnewly failing elements touching >=1 overwritten node: {int((newly & (n_over > 0)).sum())} of {int(newly.sum())}")

disp = np.linalg.norm(X1 - X0, axis=1)
over_mask = np.isin(node_ids, overwritten_ids)
print(f"mean node displacement: overwritten skin nodes {disp[over_mask].mean():.1f} mm, all other nodes {disp[~over_mask].mean():.1f} mm")
