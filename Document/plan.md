# Plan — Skin-Only SyNRA Registration, Applied Back to Full Head_V6

Date: 2026-07-08
Related vault note: [[Skin-Only SyNRA Registration]] (Services/)

**Status: implemented.** `Code/Skin_Only_SyNRA_Registration.ipynb` (10 cells) built per
the plan below. Not yet run against real data — the "Open items" checklist at the bottom
tracks what's been coded vs. what still needs to be exercised/tuned once run.

## Goal

Currently `VTU_to_VTU_SyNRA_Registration.ipynb` registers the **entire** `Head_V6.vtu`
(skull + brain + meninges + skin, all tissue layers combined) against the target
`ImageToStl.com_head_voxels_transform_2.vtu` (a pure closed triangulated skin surface —
confirmed 405,210 pts / 816,040 tri cells, no solid fill). Registering the whole
multi-tissue volume against a skin-only target is noisy: internal structures add no
correspondence signal and can distort the voxelized binary mask SyN is matching against.

Instead: compute the SyNRA warp from the **skin surface only**, then apply that one
warp to the full `Head_V6.k` node set. This is exactly the project's documented
"unified transformation" principle (architecture.md) — one warp, computed once from the
external head shape, applied to every anatomical layer so they deform together.

## Steps

### 1. Build the skin-only MOVING mesh
Head_V6's skin is 8 parts (PIDs 88000167/170/221/224/227/229/232/235 —
`head_skin_right/left`, `head_skin_out/in_r`, `head_skin2_in_r`, `head_skin_out/in_l`,
`head_skin2_in_l` — outer + inner shell per hemisphere). These are already exported
individually at `Data/outputs/vtk_export/parts/part_88000*_head_skin_*.vtu`.
Merge the 8 with `pv.merge()` (or PyVista `append_polydata`) into one `head_skin.vtu`.
**No need to convert `Head_V6_head_skin.k` through K_to_VTK_Converter** — the part-level
VTUs already exist and share node coordinates with `Head_V6.vtu`, so reuse them instead
of re-running the converter.

### 2. Register skin → target with SyNRA
FIXED = `ImageToStl.com_head_voxels_transform_2.vtu`, MOVING = merged `head_skin.vtu`.
Same `voxelize_to_ants` / `ants.registration(type_of_transform='SyNRA', ...)` cells as
today, but:
- Check `auto_rescale`'s printed scale factor first. If it reports "Units match" (scale
  ≈ 1.0), skip rescaling — simplifies step 4 and removes a failure mode (see below).
- Skin is a thin shell, not a solid blob: watch that `sigma`/margin in `voxelize_to_ants`
  doesn't over-blur the two close-together inner/outer surfaces into one blob. May need
  to drop `VOXEL_SIZE_MM` (finer) rather than raise blur to get clean SyN gradients.
- Tuning knobs, in order of effect: `flow_sigma` (lower = tighter local fit, more risk of
  self-intersection/element inversion downstream), `reg_iterations` (raise coarse-level
  count if not converging), `aff_iterations`/`aff_sampling` for the affine pre-stage.

### 3. Fine-tuning / "good enough" gate — two criteria, not one
- **Surface match**: Dice/IoU from the existing Cell 4b overlay (target ≥ 0.85, per the
  notebook's own PASS threshold).
- **Solid mesh validity** (the actual binding constraint for LS-DYNA): after applying the
  warp to the *full* `Head_V6.k` (step 4), run `k_mesh_qa.py --compare` against the
  original `Head_V6.k`. Zero negative/inverted Jacobians is non-negotiable — a tighter
  `flow_sigma` that improves skin Dice but folds internal hex elements is a regression,
  not an improvement. Treat these two checks as a joint pass/fail, not just Dice alone.

### 4. Apply the warp back to the full baseline model
**Critical correctness point, verify before trusting output:** `ants.apply_transforms_to_points()`
uses the *opposite* direction from `ants.apply_transforms()` on images — `fwdtransforms`
warps the moving *image* onto the fixed image, but applied to *points* it maps
fixed-space → moving-space. The existing Cell 5 code applies `fwdtransforms` with
`whichtoinvert=[False]*n` directly to points; this needs to be verified empirically for
the skin-only case (check that warped skin centroid/bounds land on the FIXED target, not
drift away from it) before reusing the same call pattern for the full head.

**Do not recompute scale/centroid from the full model.** If step 2 needed rescaling,
reuse the *exact* `scale_factor` and `c` (moving centroid) computed from the skin pass
when un-scaling the full-head result. Recomputing these from `Head_V6.k`'s full point
cloud will shift skull/brain relative to skin and silently break inter-tissue alignment.
If step 2 skipped rescaling (units already matched), this whole failure mode disappears.

**Apply directly to `.k`, skip VTU round-trip on the output side.** No need to convert
`Head_V6.k` to VTU for this step — `apply_transforms_to_points` only needs an (N,3)
array. Reuse the `parse_k_file()` / `raw_lines` / `node_line_indices` pattern already
built in `CT_MRI_Registration_K_Mesh.ipynb` (Cell 3 parses, Cell 9 writes back): parse
all nodes from `Head_V6.k` (every tissue, not just skin), pass them through the same
`result['fwdtransforms']` computed in step 2, write a new `Head_V6_registered.k` with
only the `*NODE` coordinates replaced. This also closes the gap the vault note already
flags — `k_mesh_qa` doesn't parse `.vtu`, so writing back to `.k` is what unlocks proper
QA validation (step 3's gate) instead of relying only on the notebook's own Cell 6 checks.

## Open items / things to verify while implementing
- [x] Confirm `apply_transforms_to_points` direction empirically (see step 4) before
      trusting any full-head output. — Cell 6 of the new notebook does this at runtime
      (compares fwd vs inv transform centroid distance, picks the winner automatically).
- [x] Check whether skin-only voxelization needs a different `VOXEL_SIZE_MM`/`sigma`
      than the current 1.0mm/2.0 defaults tuned for the full solid mesh. — set to
      0.75mm / sigma=1.5 in the new notebook's Cell 4; may need further tuning once run.
- [x] Build the `.k` node-coordinate-writeback cell (port from `CT_MRI_Registration_K_Mesh.ipynb`
      Cell 9) into a new cell in the SyNRA notebook, or a new small notebook variant. —
      ported into Cells 8-9 of `Skin_Only_SyNRA_Registration.ipynb`.
- [x] Run `k_mesh_qa.py --compare Head_V6.k Head_V6_registered.k` once produced. — wired
      up as Cell 10, run automatically via `subprocess` at the end of the notebook.
- [ ] Actually execute the notebook against real data and check both gates pass.
- [ ] If Metric 2 (k_mesh_qa) fails, iterate `flow_sigma` upward (smoother warp) and
      re-run from Cell 5 — Cell 10's printed guidance says this explicitly.

## Why this instead of the current whole-mesh approach
- Cleaner correspondence: skin vs skin, not skin vs skin+skull+brain+meninges blob.
- Matches the project's own "unified transformation" design principle already stated in
  architecture.md — the warp is meant to be computed once from the external head shape.
- Unlocks `k_mesh_qa` validation on the final artifact, which the current SyNRA notebook
  can't do because it only ever produces `.vtu` output.
