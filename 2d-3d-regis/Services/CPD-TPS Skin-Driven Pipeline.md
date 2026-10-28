---
tags: [service, notebook, decision, registration]
---

# CPD-TPS Skin-Driven Pipeline

**Status (2026-07-14, reconstructed 2026-09-10 after a ~1 month gap — no vault
updates were made during that period, this note fills the gap from the raw
notebook/output artifacts on disk):** Pipeline runs end-to-end and surface fit
is reasonable (3.9mm mean residual, final stage), but **fails the volumetric
mesh-QA gate** — 7,334 inverted solid elements — so the output is **not yet
FEA-safe**. Do not hand `Head_V6_skin_registered_v2.k` / `_v3.vtu` to LS-DYNA
or any downstream stage until this is resolved.

**Supersedes (as the active registration approach):**
[[Skin-Only SyNRA Registration]] — that ANTsPy/SyNRA path was abandoned after
its surface-gap check kept failing (15.32mm vs a 5.0mm gate, see that note's
2026-07-10 log) even after a confirmed RAS/LPS point-transform fix. Work
shifted to CPD (Coherent Point Drift) + TPS (Thin Plate Spline) instead,
driven by sparse anatomical landmark correspondence rather than dense
voxel-intensity SyN matching — consistent with the original registration-method
debate already logged in the [[PROJECT_HANDOFF]] (landmark input is sparse,
not a dense intensity volume, so SyN's core strength was never well-matched
to this problem; see `Document/PROJECT_HANDOFF.md` → "Registration method (not
yet finalized)").

## Decision

Compute a single CPD (rigid → affine → non-rigid) + TPS warp field from
**landmark correspondences on the head/skin surface**, then propagate that
field to the **entire** `Head_V6` mesh (skull + brain + meninges + skin) in
one shot — the same "unified transformation" principle as the SyNRA note,
just driven by sparse landmarks instead of dense voxel intensity.

Three notebooks exist for this, at increasing scope, most-recent first:

| Notebook | Scope | Origin | Last modified |
|---|---|---|---|
| `CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_v2.ipynb` | **Active.** Full whole-head propagation (skin-driven, applied to all 179,676 nodes) | This machine (Linux) | 2026-07-14 07:45 |
| `CPS_Pipeline/CPD_TPS_Landmark_Registration.ipynb` | Full skull+brain registration, "restores the original full-pipeline scope" | Ported from a collaborator's MacBook M2/VSCode setup (arm64 native wheels noted in Cell 1) | 2026-07-10 14:47 |
| `CPS_Pipeline/CPD_TPS_Skin_Only_Registration.ipynb` | Simplified: registers outer skull/skin surface only, brain/internal parts left at template coordinates | Same Mac/M2 origin | 2026-07-10 14:47 |

This note documents `CPD_TPS_Skin_Only_Pipeline_v2.ipynb` specifically, since
it's the one that was actually run most recently and has real output/QA
results to evaluate.

## Notebook structure (`CPD_TPS_Skin_Only_Pipeline_v2.ipynb`, "Whole-Head Pipeline — Skin-Driven Registration")

37 cells total. Stage-by-stage:

| Stage | Cell(s) | What it does |
|---|---|---|
| Setup / Config | 0–4 | `pip install pycpd pyvista numpy scipy matplotlib pandas`; `BASE_DIR = /home/asusry7/Desktop/New_version/New_version` |
| Load geometry | 5–6 | Loads template + extracts skin driving surface from `Head_V6` |
| Load subject landmarks | 7–8 | `load_subject_landmarks()` — reads SAM3D-derived landmarks, with a placeholder fallback if unavailable |
| Stage 0 — Center only | 9–10 | `center_only()`, no auto-rescale |
| Stage 0.5b — Landmark-seeded rigid alignment | 11–12 | Kabsch/Procrustes rotation from landmark pairs |
| Stage 0.5 — Landmark subsampling | 13–14 | Farthest-point sampling to thin dense correspondences |
| Stage 1 — PCA coarse pre-alignment | 15–16 | `pca_axes()` |
| Stage 2 — Rigid CPD | 17–18 | `pycpd.RigidRegistration` |
| Stage 3 — Affine CPD | 19–20 | `pycpd`, with `AFFINE_SINGULAR_VALUE_CLAMP = (0.8, 1.25)` guarding against implausible shear/scale |
| Stage 4 — Non-rigid (deformable) CPD | 21–22 | Deformable CPD pass, tracks `cpd_errors` |
| Stage 5 — TPS propagation | 23–24 | `scipy.interpolate.RBFInterpolator(..., kernel='thin_plate_spline')` — pushes the skin-only CPD field onto the **whole head** (all tissue layers), not just skin nodes |
| [Not implemented] | 25 | Markdown placeholder: cavity-constraint / signed-distance-function correction — flagged as a known gap, no code |
| Stage 6 — Non-rigid ICP refinement | 26–27 | Lightweight ICP pass + `graph_smooth()` (k=8 neighbor smoothing) |
| Stage 6.5 — Confidence-damped blend | 28–29 | "Do-no-harm" safeguard: blends warped vs. original per-point based on a confidence score, `BLEND_TRANSITION_MM = 10.0` |
| Stage 7 — Validation & summary | 30–32 | `surface_agreement()` metrics, printed as a `pandas` table + plot |
| Save outputs | 33–34 | `to_world()` coordinate un-transform, writes `.vtu` |
| QA | 35–36 | Calls `Code/python/k_mesh_qa.py` via `subprocess` on the written mesh |

## Run results (2026-07-13/14, the most recent execution)

### Validation summary (`Data/outputs/cpd_tps_skin_registration/validation_summary_v2.csv`)

| Stage | mean (mm) | median | rms | max | chamfer | hausdorff |
|---|---|---|---|---|---|---|
| 0. Center+resize | 17.435 | 12.502 | 21.775 | 52.916 | 39.416 | 67.395 |
| 1. PCA pre-align | 17.435 | 12.502 | 21.775 | 52.916 | 39.416 | 67.395 |
| 2. Rigid CPD | 8.443 | 7.025 | 10.751 | 49.554 | 17.851 | 72.475 |
| 3. Affine CPD | 9.613 | 6.869 | 14.225 | 66.946 | 17.656 | 66.946 |
| 4. Non-rigid CPD | 9.587 | 6.847 | 14.206 | 66.946 | 17.570 | 66.946 |
| 5. TPS (dense surface) | 7.730 | 6.618 | 10.218 | 66.946 | 14.899 | 66.946 |
| 6. Non-rigid ICP | 4.276 | 3.195 | 7.827 | 66.946 | 8.270 | 66.946 |
| **6.5 Confidence blend (final)** | **3.907** | **3.323** | **5.187** | **36.466** | **8.090** | **49.029** |

Monotonic improvement in mean/median through the pipeline. Note the `max`
residual gets *stuck* at 66.946mm from stage 3 (Affine CPD) through stage 6 —
one or more outlier points aren't improving at all until the confidence blend
finally pulls max down to 36.5mm by reverting those points toward the
original. Worth identifying which physical landmark/region that persistent
66.9mm outlier corresponds to — it survived four different registration
stages unchanged, which is a strong signal of either a mislabeled
correspondence pair or a genuinely hard-to-reach anatomical region (ear? chin?
back of skull?) rather than a registration-quality issue.

Cell 29 (confidence blend) printed:
```
Warp kept in full (warp was better)  : 3,299 / 6,182 points
Reverted to original (original was better): 71 / 6,182 points
Partially blended                     : 2,812 / 6,182 points
Confidence changed by smoothing -- mean 0.046, max 0.802, 1,033 points shifted by >0.1
Do-no-harm check -- mean residual: original=18.64mm  warped=4.28mm  blended=3.91mm
                     max residual : original=53.26mm  warped=66.95mm  blended=36.47mm
```

### Output artifacts (`Data/outputs/cpd_tps_skin_registration/`)

- `Head_V6_skin_registered_v1.vtu` (9.7MB, earlier run)
- `Head_V6_skin_registered_v2.vtu` (11.5MB) + `Head_V6_skin_registered_v2.k` (32MB — written via the new `vtu_to_k.py` node-writeback script)
- `Head_V6_skin_registered_v3.vtu` (10.6MB, latest — "Nodes to update: 179,676 (whole head model), 6,182 of which overwritten with the skin-specific refined result")
- `validation_summary_v2.csv` (above)

Also `outputs/picture/AfterStage0.png` through `AfterStage6.5.png`, plus
`CompareB4&After.png` and `ResultValidation.png` — per-stage visual diagnostics
at the project root `outputs/picture/`.

### Mesh QA result — **FAIL, this is the current blocker**

Cell 36 ran `k_mesh_qa.py` on `Head_V6_skin_registered_v3.vtu`:

```
Node count  -> original: 179,676, updated: 179,676
Solid elems : 176,441   Shell elems: 80,130  (topology unchanged)

NOTE: 43 of 83 parts show a mixed sign split internally (checked per-PID,
not whole-mesh) -- flagging only the minority winding within each part as
suspect.

Inverted elements (negative volume): 7334
Near-zero volume (degenerate)       : 0
Volume stats -> min: 1.115542e-04, median: 6.082558, max: 1233.841
Max/min volume ratio (proxy for aspect distortion): 1.11e+07
⚠ WARNING: high volume ratio -> expect LS-DYNA timestep collapse

⚠ FAILING ELEMENT IDs (first 20): [88058794, 88064519, 88064524, 88064533,
88064549, 88064552, 88064581, 88064627, 88064641, 88064644, 88064699,
88064715, 88064716, 88064760, 88065277, 88065280, 88065295, 88067836,
88067837, 88067838]
-> These WILL crash or stall the LS-DYNA solver.
-> Trace back to source vertices in your TPS/CPD warp field; likely cause:
   warp control points too sparse near this region, or skull/brain boundary
   folded during the deformation.

Shell elements: 80130 -- Zero/near-zero area shells: 0
All updated nodes actually differ from original: True
```

**Interpretation:** the surface-level fit is good (3.9mm mean, comparable to
what the SyNRA note was chasing and failing to reach), but the TPS
propagation into the *interior* of the mesh (skull → brain boundary) folds
176,441 solid elements at 7,334 locations badly enough that the solver would
crash or stall. This is the same class of failure the [[k_mesh_qa]] note
warns about — a warp that looks good on a surface/Dice metric but is not
validated at the volumetric-mesh level is not actually done. The known gap
flagged in the notebook itself (Stage "[Not implemented]" cavity-constraint /
SDF correction, cell 25) is the most likely fix target: without it, nothing
in the pipeline explicitly prevents the TPS field from pushing an interior
node through a neighboring layer's boundary.

**Secondary, non-blocking issue:** Cell 32 throws
`NameError: name 'summary_df' is not defined` — a duplicate/reordered display
cell, cosmetic only, does not affect the written output.

## Key implementation risks / open items (carried over, still true here)

1. **Interior-fold risk is real and unmitigated.** Nothing in stages 0–6.5
   enforces that skull and brain layers don't cross each other after the
   warp — only the confidence blend (6.5) checks "do no harm" against the
   *pre-warp point*, not against *neighboring-layer geometry*. This is
   almost certainly why QA fails.
2. **The stuck 66.9mm max-residual outlier (stages 3–6)** should be
   identified before spending more tuning time elsewhere — could indicate a
   bad landmark correspondence rather than a warp-quality problem.
3. **`densify_surface_points`/CPD stages likely still use unseeded
   `np.random`** (same caveat as the old SyNRA note) — re-running is not
   bit-for-bit reproducible; confirm before treating small metric deltas
   between runs as meaningful.
4. **Vault lag:** this note was written 2026-09-10, ~2 months after the
   underlying run (2026-07-13/14). No notebook work happened in the vault's
   knowledge during that gap — verify current notebook state before
   resuming, in case anything changed outside git-tracked history (this repo
   has no `.git`, so there is no commit trail to diff against).

## Dependencies

- [[k_mesh_qa]] — the volumetric QA gate that caught this failure
- `Code/python/vtu_to_k.py` — new script (not yet documented as its own
  Service note) that writes registered `.vtu` node coordinates back into a
  `.k` file, patching only the `*NODE` block byte-for-byte otherwise
- `Code/python/fcsv_to_npy.py` — new script converting Slicer3D `.fcsv`
  landmark exports to `.npy`, with RAS/LPS auto-detection from the file's own
  header (same coordinate-convention concern the SyNRA note hit, but handled
  proactively here)
- `Data/landmarks_matched/{template,subject}_landmarks_matched.npy` — matched
  landmark pairs feeding the CPD stages

## Used by / feeds into

- Nothing downstream yet — blocked on the mesh-QA inversion failure above.
  Once solid, `Head_V6_skin_registered_v2.k` (or a corrected successor) is
  the FEA-ready candidate, same role `Head_V6_registered.k` was meant to
  play in the [[Skin-Only SyNRA Registration]] plan.

## Recommended next step

Trace the 7,334 failing element IDs (start with `88058794`) back to their PID
and physical region — likely the skull/brain boundary given `k_mesh_qa`'s own
hint. Then either (a) implement the "[Not implemented]" cavity-constraint/SDF
correction (cell 25) to explicitly stop the TPS field from letting internal
layers cross, or (b) increase `TPS_SMOOTHING` (cell 24) to reduce local warp
sharpness near that boundary, at the cost of some surface-fit accuracy.
Re-run only cells 23 onward (TPS propagation → QA) rather than the full
pipeline, once the fix is in.

[[Architecture|← Back to Architecture]] · [[Skin-Only SyNRA Registration|Related: superseded SyNRA approach]] · [[k_mesh_qa|QA gate that caught the current failure]]
