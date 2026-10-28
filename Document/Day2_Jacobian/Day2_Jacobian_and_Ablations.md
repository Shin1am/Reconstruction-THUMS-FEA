# Day 2 — Jacobian check and ablations

**Question:** TPS and surface refinement impose no Jacobian or collision constraint. Which step actually breaks elements?
**Method:** per-corner Jacobian check (`jacobian_diagnostic.py`), then three one-line ablations of the frozen baseline notebook, each run end-to-end in a scratch folder (baseline files untouched).

## 1. Corrected mesh-quality numbers

The old `k_mesh_qa.py` counts (7,117 template / 7,334 registered) over-flag: one centroid test per element plus a "minority winding per part" rule, and 12,757 of the 176,441 solids are tets/wedges stored as collapsed hexes. The new check tests every non-degenerate corner of every element and compares template to registered by sign change, so winding convention does not matter.

| | Template | Baseline registered |
|---|---:|---:|
| Failing solids (any corner Jacobian ≤ 0) | **4** (0.002%) | **742** (0.42%) |
| Caused by the warp | – | **739** |
| Valid but poor (0 < min scaled Jacobian < 0.1) | 164 | 594 |

Baseline failures by part: head_skin_left 381, head_skin_right 309, face_skin_right 27, face_skin_left 15, occipital_l 6, temporal_r 1. None are at the skull/brain boundary.

## 2. Ablations

| Run | Skin positions propagated to the mesh | Skin mean error | Skin Hausdorff | Failing | Newly failing | Valid but poor |
|---|---|---:|---:|---:|---:|---:|
| Baseline | Stage 6.5 (ICP + blend), skin nodes overwritten | 3.907 mm | 49.029 mm | 742 | 739 | 594 |
| **A1** | same, **no overwrite** of skin nodes | 3.907 mm | 49.029 mm | 741 | 738 | 594 |
| **A2** | Stage 5 only (TPS from CPD, **no ICP, no blend**) | 7.730 mm | 66.946 mm | **3** | **0** | 248 |
| **A3** | Stage 6 (**ICP, no blend**) | 4.276 mm | 66.946 mm | 872 | 869 | 647 |

Accuracy columns are the matching rows of `validation_summary_v2.csv` (Stage 6.5, 5, 6).

## 3. What the ablations show

- **The overwrite is not the cause (A1).** Removing it moves the skin nodes by at most 0.004 mm, because the final TPS already passes through those 6,182 points. Failures: 742 → 741.
- **Stage 6 non-rigid ICP is the cause (A2 vs A3).** Without ICP the warp creates **zero** failing elements; with ICP alone it creates 869.
- **The blend helps a little but does not fix it.** ICP alone: 869 new failures; ICP + blend: 739.
- **It is an accuracy-versus-validity trade-off.** Dropping ICP removes the failures but halves the skin accuracy (mean 3.9 → 7.7 mm). Without ICP the deformation is also nearly uniform (element volumes scale 1.62–1.65×, versus 0.69–2.4× at the 1st–99th percentile in the baseline).
- **Where it fails.** 99% of the new failures are in the four skin parts, in the thin solid layers whose outer nodes carry the ICP displacement.

Not yet tested: *why* ICP breaks those elements. A likely reason is that its per-point pulls are rough at the scale of the skin thickness, while the inner nodes follow the smoother TPS field.

## 4. Caveats

- Jacobian only: tissue overlap (brain/skull) still needs a separate distance check.
- Each ablation is one run of one subject and one template.
- The Hausdorff figures for A2/A3 are the dense-skin Stage 5/6 values from the same run, not remeasured after writing the mesh.

## 5. Files

| File | Purpose |
|---|---|
| `jacobian_diagnostic.py`, `Jacobian_Diagnostic.ipynb` | The check (also copied, executed, to `~/Desktop/CPD_TPS_Skin_Only_Pipeline_v2.ipynb`) |
| `jacobian_per_part.csv`, `jacobian_newly_failing_elements.csv`, `jacobian_overview.png`, `jacobian_summary.json`, `run_output.txt` | Baseline results |
| `make_ablation_notebook.py` / `_A2.py` / `_A3.py` | One-line patches of the frozen notebook |
| `ablation/A1…`, `A2…`, `A3…` | Executed notebooks, output meshes and Jacobian results for each run |

Re-run an ablation: `JAC_REGISTERED=<mesh.vtu> JAC_OUT=<dir> python3 jacobian_diagnostic.py`.
