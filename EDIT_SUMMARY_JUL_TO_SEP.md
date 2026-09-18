# Edit & Fix Timeline — July 2026 to Present (2026-09-16)

Source: Obsidian vault `2d-3d-regis/` (`Services/*.md`, `architecture.md`). Compiled from the two notes that carry dated log entries — `Skin-Only SyNRA Registration.md` and `CPD-TPS Skin-Driven Pipeline.md`.

## Which file is your latest active work

**`New_version/Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_v2.ipynb`**
Last modified **2026-07-14 07:45**, and it's the most recently touched real code/notebook file on disk (everything since then — `architecture.md`, the CPD-TPS vault note — was written 2026-09-10 as a *retrospective* summary of this same notebook run, not new code work). This is what you were fixing when you last stopped: the pipeline runs end-to-end but **fails mesh QA** (7,334 inverted solid elements at the skull/brain boundary), so the output isn't FEA-safe yet.

## Timeline

### 2026-07-09 — SyNRA path, solid-fill bug found and fixed
- Working on `Skin_Only_SyNRA_Registration.ipynb`. Cell 5/5b/6 were failing: registration ran but transform-direction check errored, and recomputed Dice/IoU came back at **0.297** (target ≥0.85) — registration hadn't converged.
- Root-caused to two separate bugs:
  1. **Mislabeled skin-part files.** `K_to_VTK_Converter.ipynb` Cell 3 had an off-by-one in `*PART` title attribution, so 8 files claimed to be `head_skin_*` were actually `face_skin_*` (face-only, ~114×153×158mm bbox vs a full-head ~250×211×346mm target — a face patch can't Dice-match a full head, explaining the near-zero score).
  2. **No solid-fill during voxelization.** `voxelize_to_ants()` only splatted points + Gaussian blur, no `binary_fill_holes` — caused a ~24x intensity-scale mismatch between fixed/moving volumes that starved the SyN optimizer, and made Dice unreliable on thin unfilled shells.
- Fixed by rewriting Cell 4's voxelization to splat → dilate → fill-holes (matching a collaborator's working notebook pattern), and expanding the skin-part file list from 8 to the correct 24 PIDs.
- Fix applied but **not yet run** at end of session (an ~11–25 min rerun, non-deterministic due to unseeded `np.random` in `densify_surface_points`).

### 2026-07-10 — SyNRA path, fix verified, new bug found, still failing
- Reran from Cell 4 onward (twice, for reproducibility — results were stable despite the RNG).
- **Dice/IoU jumped to 0.84/0.73** (MARGINAL band) — confirmed the solid-fill fix was real.
- New Cell 7b (surface-gap KDTree check, added this session) **FAILed**: 18.95mm mean vs a 5.0mm gate.
- Found and partially fixed a second bug: `apply_transforms_to_points()` needs ITK **LPS** coordinates, but the skin VTUs (from Slicer3D) were in **RAS** — an X/Y sign flip was missing. Fixing it improved the gap to **15.32mm mean** — still ~3x over the gate.
- Per your instruction, old Cell 6 was **not deleted** — commented out in place and replaced with a new "Cell 6-fix" cell, so the fix history stays visible in the notebook.
- **Session ended with SyNRA still failing** (15.32mm vs 5.0mm) and not proceeding past Cell 7b.

### 2026-07-10 to 2026-07-14 — pivot from SyNRA to CPD/TPS
- Work shifted away from ANTsPy/SyNRA (dense voxel-intensity matching) to **CPD (Coherent Point Drift) + TPS (Thin Plate Spline)**, driven by sparse landmark correspondences instead — judged a better fit since the actual input (video-derived landmarks) is sparse, not a dense intensity volume.
- Three CPD/TPS notebooks exist, most recent first:
  - `CPD_TPS_Skin_Only_Pipeline_v2.ipynb` — **active**, whole-head propagation from skin-only landmarks, applied to all 179,676 nodes. Last run 2026-07-13/14.
  - `CPD_TPS_Landmark_Registration.ipynb` — full skull+brain registration (ported from a collaborator's Mac).
  - `CPD_TPS_Skin_Only_Registration.ipynb` — simplified skin/skull-surface-only version, internal parts left at template coordinates.
- New supporting scripts written: `vtu_to_k.py` (writes registered `.vtu` node coordinates back into a `.k` file, patching only the `*NODE` block), `fcsv_to_npy.py` (converts Slicer3D `.fcsv` landmark exports to `.npy`, with RAS/LPS auto-detection built in this time — proactively avoiding the same bug class hit in the SyNRA path).

### 2026-07-13/14 — CPD/TPS pipeline run (current state, unresolved)
- Ran the full `CPD_TPS_Skin_Only_Pipeline_v2.ipynb` (37 cells, stages: center → landmark-seeded rigid align → PCA pre-align → rigid CPD → affine CPD → non-rigid CPD → TPS propagation to whole head → ICP refinement → confidence-damped blend → validation → save → QA).
- **Surface fit is good and monotonically improved through the pipeline**: mean residual dropped from 17.4mm (stage 0) to **3.907mm** at the final confidence-blend stage.
- One persistent outlier stuck at 66.9mm max residual from stage 3 through stage 6, only resolved by the final blend reverting it — flagged as worth investigating (possibly a mislabeled landmark correspondence).
- **Mesh QA FAILS**: `k_mesh_qa.py` found **7,334 inverted solid elements** (negative volume) at the skull/brain boundary, with a max/min volume ratio of 1.1e7 — flagged as certain to crash or stall LS-DYNA. Root cause suspected: the TPS propagation stage has no cavity-constraint / signed-distance-function correction to stop the warp from folding internal layers into each other (this was a known, explicitly unimplemented gap left as a markdown placeholder in the notebook, cell 25).
- Minor cosmetic bug also noted: cell 32 throws `NameError: name 'summary_df' is not defined` (duplicate/reordered display cell, doesn't affect written output).
- **This is where things currently stand — output (`Head_V6_skin_registered_v2.k` / `_v3.vtu`) is blocked from any downstream/LS-DYNA use until the inversion failure is fixed.**

### 2026-09-10 — vault reconstruction (no new code work)
- After a ~1 month gap with no vault updates, `architecture.md` and the `CPD-TPS Skin-Driven Pipeline.md` note were rewritten from the raw notebook/output artifacts on disk to catch the vault up to the 2026-07-13/14 run. No notebook re-run or new fixes happened in this pass — it's documentation only.
- Recommended next step carried into today: trace the 7,334 failing element IDs (starting with `88058794`) back to their PID/physical region, then either implement the missing cavity-constraint/SDF correction (notebook cell 25) or increase `TPS_SMOOTHING` (cell 24) to reduce local warp sharpness near the skull/brain boundary — re-running only from cell 23 onward (TPS propagation → QA), not the full pipeline.

## Bottom line
You're mid-fix on **`CPD_TPS_Skin_Only_Pipeline_v2.ipynb`**. Surface registration works; the volumetric mesh QA gate (7,334 inverted elements at the skull/brain boundary) is the open blocker, and the next concrete step is implementing the not-yet-built cavity-constraint/SDF correction at cell 25, or loosening `TPS_SMOOTHING` at cell 24, then re-running from cell 23 onward.
