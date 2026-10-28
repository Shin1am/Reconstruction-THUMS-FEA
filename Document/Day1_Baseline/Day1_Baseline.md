# Day 1 — Baseline Lock: CPD + TPS Skin-Driven Registration

**Locked:** 2026-10-19 · **Algorithms changed:** none · **Purpose:** reference point for judging every later improvement.

The baseline was re-run from scratch on this Mac and reproduced the saved results **exactly** (all registration metrics identical to 3 decimals, same 7,334 inverted elements; largest difference in any output node coordinate: 2.5e-8).

---

## 1. At a glance

| Item | Baseline value |
|---|---|
| Hausdorff distance, before → after | **67.395 mm → 49.029 mm** (−27.3%) |
| Mean surface error, before → after | 17.435 mm → 3.907 mm (−77.6%) |
| Chamfer distance, before → after | 39.416 mm → 8.090 mm (−79.5%) |
| Inverted solid elements (registered mesh) | **7,334 of 176,441 = 4.157%** |
| Inverted solid elements (original template, no registration) | **7,117 of 176,441 = 4.034%** |
| Runtime, fresh run (M3, 8 GB) | **113.6 s** wall clock (110.9 s summed over cells) |
| Reproducible? | Yes — identical metrics on a fresh run, different Python/NumPy than the original |

> **Correction added in Day 2:** the 7,334 / 7,117 counts come from `k_mesh_qa.py`, which over-flags (it uses one centroid test per element and a "minority winding per part" rule). A per-corner Jacobian check (`../Day2_Jacobian/`) finds only **4** failing elements in the template and **742** in the registered mesh (739 caused by the warp). Keep 7,334 as the baseline *for that checker*; it is not a count of truly inverted elements. See [Section 4](#4-mesh-quality).

---

## 2. What was locked

| Role | File |
|---|---|
| **Baseline notebook (frozen, read-only)** | `frozen/CPD_TPS_Skin_Only_Pipeline_v2.ipynb` — copy of `Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_v2.ipynb` (saved 2026-07-14 07:45) |
| QA script used | `frozen/k_mesh_qa.py` |
| Reference metrics | `frozen/validation_summary_v2.csv` |

**Three copies of this notebook name exist. Only one is the baseline:**

| Location | State | Use? |
|---|---|---|
| `Code/notebook/CPS_Pipeline/…_v2.ipynb` | Whole-head propagation, outputs match the 67.4 → 49.0 / 7,334 figures | **Baseline** |
| `Code/ipynb/…_v2.ipynb` | Older skull-surface-only version (brain not warped). Different results: Hausdorff 68.6 → 65.5 mm, 7,764 inverted, 4 degenerate | Superseded — do not compare against it |
| `~/Desktop/…_v2.ipynb` | **Empty** (0 cells, 239 bytes, modified 2026-10-19 22:59) | Nothing to recover there |

---

## 3. Registration results

Source: `validation_summary_v2.csv` (all distances in mm; scale is fixed at 1.0).

| Stage | Mean | Median | RMS | Max | Chamfer | **Hausdorff** |
|---|---:|---:|---:|---:|---:|---:|
| 0. Center (+ landmark seed) | 17.435 | 12.502 | 21.775 | 52.916 | 39.416 | **67.395** |
| 1. PCA pre-align (skipped) | 17.435 | 12.502 | 21.775 | 52.916 | 39.416 | 67.395 |
| 2. Rigid CPD | 8.443 | 7.025 | 10.751 | 49.554 | 17.851 | 72.475 |
| 3. Affine CPD | 9.613 | 6.869 | 14.225 | 66.946 | 17.656 | 66.946 |
| 4. Non-rigid CPD | 9.587 | 6.847 | 14.206 | 66.946 | 17.570 | 66.946 |
| 5. TPS (dense surface) | 7.730 | 6.618 | 10.218 | 66.946 | 14.899 | 66.946 |
| 6. Non-rigid ICP | 4.276 | 3.195 | 7.827 | 66.946 | 8.270 | 66.946 |
| 6.5 Confidence blend (**final**) | **3.907** | **3.323** | **5.187** | **36.466** | **8.090** | **49.029** |

### How to read this table

- **"Before registration" (67.395) is not truly raw.** Stage 0's row is measured after the Stage 0.5b landmark rotation, because the rotation is applied to the template before the table is built. Stage 1 equals Stage 0 because PCA was skipped.
- **Stages 0–4 and 5–6.5 use different point sets.** Stages 0–4 measure the 2,000 sampled template points; Stages 5–6.5 measure all 6,182 dense skin points. Rows are not strictly like-for-like.
- **Hausdorff barely moves until the last stage.** It sits at 66.946 from Stage 3 through Stage 6, then drops to 49.029 only at the confidence blend. Mean error improves steadily; Hausdorff does not. Rigid CPD actually *raised* it (67.395 → 72.475).
- **The final 49.029 mm comes from the subject side, not the template side.** The code defines `max` as source→target only (36.466 mm) and Hausdorff as the larger of both directions. So the 49.029 is a subject point with no nearby template point (a coverage gap), which deforming the template cannot fix by itself.
- **The subject point set is a random 3,000-point sample** of the voxel head scan, so all numbers depend on `np.random.seed(0)` (see Section 7).

Stage 6.5 detail (6,182 dense skin points): warp kept in full 3,299 · reverted 71 · partially blended 2,812. Mean residual original 18.64 → warped 4.28 → blended 3.91 mm; max 53.26 → 66.95 → 36.47 mm.

---

## 4. Mesh quality

Measured with `k_mesh_qa.check_mesh` on the written mesh `Head_V6_skin_registered_v3.vtu` (original element connectivity, updated node coordinates).

| | Registered mesh | Original template (control) |
|---|---:|---:|
| Nodes | 179,676 | 179,676 |
| Solid elements | 176,441 | 176,441 |
| Shell elements | 80,130 | 80,130 |
| **Inverted solids** | **7,334 (4.157%)** | **7,117 (4.034%)** |
| Degenerate (near-zero volume) | 0 | 4 |
| Max / min volume ratio | 1.11e+07 | 6.38e+14 |
| Parts with mixed sign split | 43 of 83 | 41 of 83 |
| Zero-area shells | 0 | 0 |

**Overlap between the two flagged sets** (`qa_overlap.py`):

| | Elements |
|---|---:|
| Flagged in both template and registered | 6,883 |
| Flagged only in the template (registration un-flagged them) | 238 |
| Flagged only in the registered mesh (new after registration) | 451 |
| Share of registered flags already present in the template | **93.9%** |

> **Superseded interpretation (Day 2):** the paragraph below describes what the old checker reports. The corrected per-corner Jacobian check shows the template is essentially clean (4 failing of 176,441) and the warp creates 739 failing elements, 99% of them in the four skin parts. Ablations show the cause is the Stage 6 ICP refinement, not the skin-node overwrite. Details: `Document/Day2_Jacobian/Day2_Jacobian_and_Ablations.md`.

**What this means (old checker).** The checker flags the *minority winding within each part*. The original template already has 41 of 83 parts with mixed signs, and the first 20 failing element IDs are identical before and after registration (88058794, 88064519, 88064524, …). Most of the 7,334 therefore reflect the source mesh, not the warp. The registration adds roughly 451 newly flagged elements and removes 238. The cause of the template's own flags (genuine bad elements versus mixed node ordering inside parts) has **not** been investigated yet.

First 20 failing IDs (registered): `88058794 88064519 88064524 88064533 88064549 88064552 88064581 88064627 88064641 88064644 88064699 88064715 88064716 88064760 88065277 88065280 88065295 88067836 88067837 88067838`

---

## 5. Parameters by stage

**Input data**

| Item | Value |
|---|---|
| Template | `Data/Ls_dyna_model/Head_V6.k` and `Data/mesh_model/Head_V6.vtu` — 179,676 points, 256,571 cells |
| Skin driving surface | Parts whose `$HMNAME COMPS` name contains `_out_`, PIDs 88000160–88000240 → 6 PIDs `[88000221, 88000222, 88000223, 88000229, 88000230, 88000231]`, **6,182 points** |
| Subject | Fallback surface `Data/mesh_model/ImageToStl.com_head_voxels_transform_2.vtu` (SAM3D landmarks `subject_landmarks.npy` do **not** exist yet) |
| Subject filtering | 405,210 points → keep Z ≥ 515.0 (`NECK_Z_CUTOFF`) → 374,115 → random sample of **3,000** |
| Matched landmarks | 10 pairs picked in Slicer3D: `template_landmarks_matched.npy`, `subject_landmarks_matched.npy` |

| Stage | Settings | Recorded result |
|---|---|---|
| **0 Center** | Subtract centroids; `scale = 1.0` (auto-rescale removed) | Centroid subject [−155.9, 3.0, 662.2]; template [−179.6, 0.0, 690.0] |
| **0.5b Kabsch seed** | SVD Procrustes on the 10 pairs; rotation applied to skin surface **and** whole mesh | Notebook's landmark residual 31.23 → 48.41 (rose; see Section 9) |
| **0.5 FPS** | `N_LANDMARKS_FIXED = 2000`, `N_LANDMARKS_MOVING = 2000`, `default_rng(seed=0)` | 2,000 + 2,000 points |
| **1 PCA** | 4 sign combinations, `eval_stride=5` — **skipped**, `landmark_seed_applied = True`, `R_pca = identity` | — |
| **2 Rigid CPD** | pycpd 2.0.0 `RigidRegistration`, `max_iterations=100`, `tolerance=1e-6`; library defaults `w=0`, `sigma2` auto | s = 1.1503; t = [−3.89, 1.72, 27.89]; R = [[0.976, −0.091, −0.200], [0.081, 0.995, −0.058], [0.204, 0.040, 0.978]] |
| **3 Affine CPD** | `AffineRegistration`, same iteration/tolerance; singular values clamped to `(0.8, 1.25)` | Raw SV [1.268, 0.967, 0.885] → clamped [1.25, 0.967, 0.885]; t = [−1.34, 0.02, −5.77] |
| **4 Deformable CPD** | `DeformableRegistration`, `alpha=2.0`, `beta=2.0`, `max_iterations=100`, `tolerance=1e-6` | Convergence plot only |
| **5 TPS** | `RBFInterpolator(moving_lm → TY_cpd)`, `kernel='thin_plate_spline'`, `smoothing=1e-3`, global (`neighbors=None`), default degree | Evaluated on 6,182 skin points and all 179,676 nodes |
| **6 Non-rigid ICP** | `ICP_ITERS=10`, `ICP_MAX_CORR_DIST_MM=15.0`, `ICP_STEP=0.5`, `ICP_SMOOTH_NEIGHBORS=8` (1 smoothing pass) | Mean 7.730 → 4.276 |
| **6.5 Confidence blend** | `BLEND_TRANSITION_MM=10.0`, `CONF_SMOOTH_NEIGHBORS=8`, `CONF_SMOOTH_ITERS=3` | See Section 3 |
| **5b TPS rebuild + propagate** | Refit TPS from `nm_surf_pca → nm_surf_final_cs` (same kernel/smoothing), apply to all nodes; the 6,182 skin nodes then overwritten with their directly computed positions; map back with inverse PCA rotation (identity), ÷ scale, + subject centroid | `Head_V6_skin_registered_v3.vtu` |

---

## 6. Runtime

Fresh run, `jupyter nbconvert --execute`, Apple M3, 8 GB RAM, macOS 14.6.
**Wall clock 113.6 s** (CPU time 529 s — NumPy/SciPy use several threads).

| Stage | Seconds (fresh run) | Seconds saved in notebook* |
|---|---:|---:|
| Setup / imports | 1.92 | 2.13 |
| Load template + skin surface | 0.28 | 0.92 |
| Load subject point set | 0.23 | 0.02 |
| 0 Center | 0.31 | 0.31 |
| 0.5b Kabsch seed | 0.34 | — |
| 0.5 Farthest-point sampling | 0.42 | 0.53 |
| 1 PCA (skipped) | 0.29 | 0.20 |
| 2 Rigid CPD | 13.27 | 10.94 |
| 3 Affine CPD | 14.51 | 12.18 |
| **4 Deformable CPD** | **25.45** | 29.00 |
| 5 TPS | 4.45 | 1.20 |
| 6 Non-rigid ICP | 0.32 | 0.50 |
| 6.5 Confidence blend | 0.40 | 0.29 |
| 7 Validation table + plot | 0.15 | 0.13 |
| 5b TPS rebuild + write `.vtu` | 18.22 | 0.76 |
| QA (`k_mesh_qa`) | 30.37 | 29.05 |
| **Total (sum of cells)** | **110.9** | 88.2 |

\*The timings stored in the saved notebook carry 2026-07-10 timestamps, while the code was last edited 2026-07-13/14 (execution counts are also out of order: #2, #40–56, #3). Treat them as indicative only; the fresh-run column is the authoritative timing.

The three slowest steps are QA (27%), deformable CPD (23%) and the final write (16%).

---

## 7. Environment, seeds, reproduction

| | Original run | Fresh verification run |
|---|---|---|
| Machine | Linux (path `/home/asusry7/…`) | MacBook Air, Apple M3, 8 GB, macOS 14.6 |
| Python | 3.10.20 (kernel `2d_3d_regis`) | 3.13.9 (`/opt/homebrew/anaconda3`) |
| NumPy | 2.2.5 | 2.3.5 |
| PyVista | 0.48.4 | 0.48.4 |
| Other libraries | — | SciPy 1.16.3 · pycpd 2.0.0 · VTK 9.6.2 · pandas 2.3.3 · matplotlib 3.10.6 |

Full list: `environment_requirements.txt`. The results did not change across the Python/NumPy difference.

**Random seeds**
- `np.random.seed(0)` (setup cell) drives the 3,000-point subject sample.
- Farthest-point sampling uses `np.random.default_rng(seed=0)`.
- Nothing after the subject sampling consumes the global RNG for computation (later `np.random.choice` calls only subsample points for plots), and pycpd is deterministic. Run the cells in order from a fresh kernel.

**Reproduce**

```bash
bash "/Volumes/Extreme SSD/2d_3d_regis dataset/New_version/Document/Day1_Baseline/run_baseline.sh"
/opt/homebrew/anaconda3/bin/python3 "/Volumes/Extreme SSD/2d_3d_regis dataset/New_version/Document/Day1_Baseline/extract_metrics.py"
```

`run_baseline.sh` makes a scratch copy of the frozen notebook, changing only three I/O items (`BASE_DIR`, `OUTPUT_DIR`, and the `!pip install` line), executes it, and writes everything under `rerun/` so the original outputs are never overwritten. `extract_metrics.py` prints per-stage timing, diffs the fresh metrics against `frozen/validation_summary_v2.csv`, and writes `baseline_metrics.json`.

To run it by hand instead: open the frozen notebook, point `BASE_DIR` at `…/New_version`, and Run All with a Python 3.10+ kernel that has numpy, scipy, pyvista, pycpd, pandas and matplotlib.

---

## 8. Input and output fingerprints (SHA-256)

Full list in `checksums.sha256`.

| File | SHA-256 (first 16) |
|---|---|
| `frozen/CPD_TPS_Skin_Only_Pipeline_v2.ipynb` | `2e482a39ab21989e` |
| `Data/Ls_dyna_model/Head_V6.k` | `ae394a6c12184685` |
| `Data/mesh_model/Head_V6.vtu` | `0afd2c0ffe8355fb` |
| `Data/mesh_model/ImageToStl.com_head_voxels_transform_2.vtu` | `2209252fba9b9717` |
| `Data/landmarks_matched/template_landmarks_matched.npy` | `9d1fc76231c61761` |
| `Data/landmarks_matched/subject_landmarks_matched.npy` | `36ec2669435da126` |
| Original output `Head_V6_skin_registered_v3.vtu` | `108322f28dc4d458` |

The fresh run's `.vtu` has a different hash because of floating-point noise (largest per-node difference 2.5e-8 on 172,751 nodes); node IDs, cell data and metrics are identical.

---

## 9. Observations for later days (recorded, not acted on)

These are findings from the baseline run. None was changed.

1. **The old checker over-flags** (Section 4). Resolved in Day 2: the template flags were checker artifacts, and the true warp-caused failures are 739 elements concentrated in the skin parts.
2. **The matched landmarks appear to be in an X-mirrored frame.** Landmark X ranges are +24…+193, while the meshes sit at X ≈ −283…−24. With X flipped, 10 of 10 subject landmarks fall inside the subject mesh's bounding box (0 of 10 as-is); the template's landmarks go 0 → 5 of 10. This looks like a RAS-versus-LPS sign convention mismatch, the same class of problem logged in the SyNRA work. Not yet confirmed.
3. **The Kabsch "residual got worse" (31.23 → 48.41) is partly a metric artifact.** The residual is computed without re-centering the landmark clouds, which sit roughly +255 mm from the surface centroids in X. Re-centering each cloud first gives 12.03 → 10.76 mm (a modest improvement). Combined with item 2, the seed rotation deserves a check before trusting it.
4. **The Hausdorff ceiling is a coverage gap.** The final 49.029 mm is the subject→template direction; template→subject max is 36.466 mm.
5. **Stage 5 TPS is fitted on 2,000 control points only**, then evaluated on the dense skin and the whole mesh; the skin-surface Hausdorff does not improve through Stages 3–6 and is rescued only by the blend.

---

## 10. Files in this folder

| File | What it is |
|---|---|
| `Day1_Baseline.md` | This document |
| `baseline_metrics.json` | Machine-readable metrics, per-stage timing, QA numbers, diff vs reference |
| `checksums.sha256` | SHA-256 of code, inputs and outputs |
| `environment_requirements.txt` | Library versions of the verification run |
| `frozen/` | Read-only copies of the baseline notebook, `k_mesh_qa.py`, reference CSV |
| `run_baseline.sh`, `make_scratch_notebook.py`, `extract_metrics.py` | Re-run and compare tooling |
| `qa_template_control.py`, `qa_overlap.py` | Control QA on the unwarped template, and flagged-element overlap |
| `rerun/` | Fresh-run notebook, outputs, logs, QA text |
