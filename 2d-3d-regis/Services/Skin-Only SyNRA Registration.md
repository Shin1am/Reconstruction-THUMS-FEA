---
tags: [service, notebook, decision, registration]
---

# Skin-Only SyNRA Registration

**Status (2026-07-10):** Solid-fill fix (2026-07-09) confirmed real — Dice/IoU jumped
0.1788→0.84 (MARGINAL). But the new Cell 7b surface-gap check (run for the first
time) FAILs: 18.95mm mean vs 5.0mm gate. A second, independent bug found and
partially fixed this session (RAS/LPS point-transform convention) improved it to
15.32mm mean — still FAILs, ~3x over. **Not yet a working pipeline; do not proceed
to Cell 8 (full `Head_V6.k` apply).** See
[[#2026-07-10 — solid-fill fix run, new bug found and partially fixed]] below.
`Code/Skin_Only_SyNRA_Registration.ipynb`. See `plan.md` at project root for the
design rationale.
**Supersedes (for the registration-compute step only):** the whole-mesh approach in
[[VTU-VTU SyNRA Registration]], which registers all of `Head_V6.vtu` (skull+brain+meninges+skin)
against the target skin surface.

## Decision

Compute the SyNRA warp from the **skin surface only** (`Head_V6`'s 8 skin PIDs, merged),
registered against `ImageToStl.com_head_voxels_transform_2.vtu` — confirmed a pure closed
triangulated skin shell (405,210 pts / 816,040 tri cells, no solid fill). Then apply that
one computed transform to the **full** `Head_V6.k` node set (every tissue layer), not just
the skin nodes.

This is a direct instance of the "unified transformation" principle already stated in
[[Architecture]]: one warp/displacement field, computed once from the external head shape,
applied simultaneously to every anatomical component so they deform together and stay
anatomically aligned.

## Why not register the whole mesh (current notebook behaviour)

Voxelizing the full multi-tissue `Head_V6.vtu` against a skin-only target adds internal
structure (skull, brain, meninges) as registration noise — those layers contribute no
correspondence signal for matching an external skin envelope, and can distort the binary
mask that SyN's `meansquares` metric is matching against.

## Key implementation risks identified

1. **Point-transform direction.** `ants.apply_transforms_to_points()` maps in the
   *opposite* direction from `ants.apply_transforms()` on images — must verify empirically
   (warped skin centroid/bounds should land on the FIXED target) before trusting output;
   the notebook's existing Dice/IoU check validates the image-domain warp, not the
   point-domain application.
2. **Scale/centroid consistency.** If `auto_rescale` triggers a unit correction during the
   skin-only pass, the *same* `scale_factor`/centroid must be reused when un-scaling the
   full `Head_V6.k` result — recomputing from the full point cloud would shift skull/brain
   relative to skin. Skipped entirely if units already match (scale ≈ 1.0).
3. **Tuning gate is two-part, not just Dice.** Skin-surface Dice/IoU (≥0.85 target) *and*
   zero negative Jacobians in the full solid mesh after warp application, checked via
   [[k_mesh_qa]]. A `flow_sigma` tight enough to nail skin overlap but that folds internal
   hex elements is a regression.

## No `.k`→`.vtu` conversion needed for the skin input

`Head_V6`'s 8 skin-part VTUs already exist at `Data/outputs/vtk_export/parts/part_88000*_head_skin_*.vtu`
(from a prior [[K to VTK Converter]] run) — merge those rather than re-running the
converter on `Head_V6_head_skin.k`.

## No `.k`→`.vtu` conversion needed for the output side either

`ants.apply_transforms_to_points()` only needs an (N,3) coordinate array. Applying the
skin-derived transform to the full baseline model can go straight `.k` node coords → warp
→ `.k` node coords, reusing the `parse_k_file()` / raw-lines round-trip pattern already
built in [[CT-MRI Registration - K-Mesh]] (its Cell 9), instead of going through VTU.
This also closes a validation gap [[VTU-VTU SyNRA Registration]] already notes: `k_mesh_qa`
doesn't parse `.vtu`, so writing back to `.k` is what unlocks the shared QA gate for this
result.

## Notebook structure (`Code/Skin_Only_SyNRA_Registration.ipynb`)

| Cell | Stage |
|---|---|
| 1 | Install |
| 2 | Config (paths, `VOXEL_SIZE_MM=0.75`, tighter than whole-mesh's 1.0mm) |
| 3 | Merge the 8 skin-part VTUs into one MOVING mesh |
| 4 | Load fixed target + voxelize both (`sigma=1.5`, tighter than whole-mesh's 2.0) |
| 5 | ANTsPy SyNRA registration, skin vs skin (`flow_sigma=2.5` vs whole-mesh's 3.0) |
| 5b | **Metric 1** — image-domain Dice/IoU (target ≥0.85) |
| 6 | Empirical fwd/inv transform-direction check (picks whichever reduces centroid distance to target) |
| 7 | Apply verified transform to skin nodes only → `head_skin_synra_registered.vtu` (visual QA) |
| 8 | Parse full `Head_V6.k`, apply the *same* transform + *same* scale/centroid anchor to every node |
| 9 | Write `Head_V6_registered.k` (only `*NODE` cards replaced, rest preserved verbatim) |
| 10 | **Metric 2** — `k_mesh_qa.py --compare` against the pre-warp baseline (zero inverted/degenerate elements required) |

Output: `Code/outputs/skin_only_synra/Head_V6_registered.k` plus intermediate `.nii.gz`/`.vtu`/PNG diagnostics.

## Validation metrics used, and why

- **Dice/IoU (image domain, Cell 5b)** — direct measure of whether the skin surface
  itself converged onto the target shape. Bounded [0,1], resolution/unit independent.
  This is *necessary but not sufficient*: it only ever sees the skin voxel volume, never
  the skull/brain/meninges elements that get carried along by the same warp in Cell 8.
- **`k_mesh_qa.py --compare` (mesh domain, Cell 10)** — the actual LS-DYNA solver-safety
  gate: negative/zero-Jacobian solid elements, duplicate nodes, extreme aspect ratio,
  checked per-PID and diffed against the pre-warp baseline so only *newly introduced*
  failures are flagged. This is the binding constraint — a warp that improves Dice but
  folds an internal hex element is a regression, not a win. Both gates must pass; Dice
  alone was judged insufficient because it cannot see internal-tissue failure modes.

## Dependencies

- [[K to VTK Converter]] — already supplied the 8 skin-part VTUs being reused here
- [[CT-MRI Registration - K-Mesh]] — supplies the `.k` parse/write-back pattern to port over
- [[k_mesh_qa]] — the joint validation gate (Dice + zero inversions)

## Used by / feeds into

- Produces `Head_V6_registered.k`, a drop-in replacement candidate for `Head_V6.k` as
  FEA-ready geometry, once QA passes.

## 2026-07-09 investigation — Cell 5/5b/6 failure

**Symptom:** Cell 5 (SyNRA registration) ran to completion (~11 min), but Cell 6's
transform-direction check raised `RuntimeError: Neither transform direction reduces
centroid distance to the fixed target` — both `fwdtransforms` and `invtransforms`
pushed the warped skin centroid to ~122mm from the fixed target, *worse* than the
~61mm pre-warp distance. VS Code crashed during a later rerun attempt (before Cell
5b's Dice/IoU had been computed), so the actual registration quality was unknown
going into this session.

**What I checked (no rerun needed):** the two 200MB `.nii.gz` voxel volumes from
the prior run were still on disk. Recomputed Cell 5b's Dice/IoU directly from them:

- **Dice = 0.297, IoU = 0.175** — far below the 0.85 gate. The registration itself
  did not converge; this is not just a Cell 6 point-transform-direction bug.
- Warped skin volume has ~2.2x the voxel count of the fixed target (7.6M vs 3.4M),
  i.e. the moving mesh is coming out oversized relative to target, not just
  offset.

**Re-checked the premise from last session** (that the scale reduction wasn't
needed since inputs were manually pre-aligned/scaled): recomputed `auto_rescale`'s
inputs directly from the source VTUs (no notebook rerun). Per-axis scale needed
came out `[2.19, 1.37, 2.19]` — anisotropic, not close to 1.0. User confirmed the
scale-up in Slicer3D was **intentional** (target deliberately made bigger than the
FEA model, since the goal is to warp the model out to the true skin surface) and,
separately, confirmed by eye in Slicer3D that there's no visible flip/rotation
(skull top matches model top). An initial PCA-based rotation hypothesis was raised
and **retracted** — the skin mesh's top two principal-axis eigenvalues (48.2,
42.6) are too close together for PCA eigenvector *direction* to be reliable there
(near-degenerate eigenvalues let two axes rotate freely against each other without
changing the shape), so that check couldn't actually distinguish rotation from no
rotation. Don't reuse that PCA-cross-correlation method on meshes with close
eigenvalues.

**Root cause — confirmed, not a scale/rotation issue at all:** the moving mesh is
missing most of the real head-skin coverage, due to a labeling bug in
`Code/K_to_VTK_Converter.ipynb` (Cell 3, the `*PART` keyword branch). LS-DYNA
`*PART` cards are formatted `title line` → `pid,secid,mid` line. The parser hits
the title line first; at that point `data['parts']` already holds the *previous*
part (not yet the current one), so the `except` fallback's
`last_pid = list(data['parts'].keys())[-1]` writes the current title onto the
**previous** part's dict entry instead of its own. Every exported
`part_<pid>_<title>.vtu` filename's title suffix therefore actually belongs to the
*next* part in the `.k` file's `*PART` sequence — verified against the user's
ground-truth PID table from `Head_V6_head_skin.k` (22/23 skin PIDs match a uniform
+1 shift exactly; the one non-match, PID 88000172, is expected since that's where
a non-skin part — `choro_r` — sits between two skin PIDs in the real file). The
underlying per-element `part_id` used to select geometry is unaffected (parsed
separately, correctly) — only the cosmetic name suffix is shifted.

Consequence: `SKIN_PART_FILES` in this notebook's Cell 2 (8 files, all named
`..._head_skin_*.vtu`) was selected by trusting those mislabeled names. Because of
the +1 shift, the **actual geometry** in all 8 of those files is really the 8
`face_skin_*` parts (right/left × out/in/in2, no `head_skin_*`/scalp coverage, no
`nose_in_shell_*`, no `_cr`/`_cl` center-strip parts) — confirmed against the
user's real PID table below.

| Notebook's file (misleading name) | Real PID | Real part (per `Head_V6_head_skin.k`) |
|---|---|---|
| `part_88000167_head_skin_right.vtu` | 88000167 | `face_skin_right` |
| `part_88000170_head_skin_left.vtu` | 88000170 | `face_skin_left` |
| `part_88000221_head_skin_out_r.vtu` | 88000221 | `face_skin_out_r` |
| `part_88000224_head_skin_in_r.vtu` | 88000224 | `face_skin_in_r` |
| `part_88000227_head_skin2_in_r.vtu` | 88000227 | `face_skin2_in_r` |
| `part_88000229_head_skin_out_l.vtu` | 88000229 | `face_skin_out_l` |
| `part_88000232_head_skin_in_l.vtu` | 88000232 | `face_skin_in_l` |
| `part_88000235_head_skin2_in_l.vtu` | 88000235 | `face_skin2_in_l` |

So the "skin-only moving mesh" being registered in Cell 5 is **face-only**
(bbox `[114.5, 153.2, 158.3]` mm — consistent with a face, too small for a full
head), registered against a **full-head** fixed target (bbox
`[250.4, 210.6, 346.1]` mm). No amount of scale/rotation correction fixes that —
a face patch cannot Dice-match a whole-head shape, which is the real reason Dice
came out to 0.297. The full real skin envelope needs all 24 PIDs in
`Head_V6_head_skin.k` (face + head/scalp + nose, both hemispheres, per the table
the user supplied 2026-07-09), not just 8.

**Fix needed (two parts, not yet applied):**
1. `K_to_VTK_Converter.ipynb` Cell 3, `*PART` branch — fix the title/PID
   attribution off-by-one (attach the title to the part card that follows it, not
   `last_pid`), then re-run the converter so `parts/*.vtu` filenames are
   trustworthy.
2. `Skin_Only_SyNRA_Registration.ipynb` Cell 2 — expand `SKIN_PART_FILES` from 8
   entries to all 24 real skin PIDs (by PID number, not by trusting the current
   mislabeled filenames), so the moving mesh actually covers the full head skin
   envelope before Cell 5 is rerun.

**Not yet done:** neither fix has been applied yet; Cell 5 has not been rerun
since this diagnosis (would cost ~11 min and, per `densify_surface_points`'s
unseeded `np.random`, isn't even bit-for-bit reproducible run to run) — rerunning
now, before fixing the PID selection, would just reproduce Dice ≈ 0.3.

## 2026-07-09 (evening, cont.) — root cause found via comparison against friend's `VTU_TwoStage_Registration_v3_3.ipynb`, fix applied but not yet run

After the 24-part coverage fix (previous section) made Dice *worse* (0.1788 vs
0.297), compared this notebook's Cell 4 voxelization against a friend's working
notebook (`Code/VTU_TwoStage_Registration_v3_3.ipynb` — runs on their Mac, paths
under `/Volumes/Extreme SSD/...`, registers THUMS skull+brain to a personalized
head shape and reports a healthy ~0.6mm mean gap).

**Root cause (confirmed):** this notebook's `voxelize_to_ants()` only splatted
points and Gaussian-blurred (`sigma=1.5`), with **no solid fill**. The friend's
`nodes_to_ants_volume()` splats, dilates, then `binary_fill_holes` on all 3 axes
(majority-vote combine) — always solid. Two consequences of the missing fill:

1. **Intensity-scale mismatch starved the optimizer.** After blur-only
   voxelization, the dense fixed target (405k pts) peaked at ~0.24 while the
   sparse moving skin (splatted + blurred) peaked at ~0.01 — confirmed in the
   notebook's own Cell 4 comment. `ants.registration(..., syn_metric=
   'meansquares', ...)` in Cell 5 runs on these **raw, un-normalized** volumes
   (only normalized afterward for the Dice/display step) — a ~24x intensity gap
   left almost no gradient signal on the moving side for SyN to act on.
2. **Thin unfilled shells make Dice near-zero-tolerance.** Solid-filled volumes
   (friend's approach) have large interior overlap even with a few mm of surface
   offset, so Dice stays forgiving/high. Two thin blurred shells barely touching
   scores near zero even for a reasonable surface fit — consistent with the
   observed 0.1788.

Solid-filling does **not** turn this into a volume-matching problem instead of a
surface one: `meansquares` gradient is zero deep inside (1 vs 1) and zero deep
outside (0 vs 0) regardless of fill — only the boundary disagreement carries
signal, fill or no fill. Filling just fixes the intensity-scale bug and gives
Dice a sane, comparable denominator. It also incidentally resolves the 24-part
mesh's inner/outer skin double-layer ambiguity (flagged as an open candidate
cause in the previous session) — the outer shell's fill absorbs that gap into
one solid head volume, comparable to the fixed target (itself solid, voxel-
derived STL per its filename).

**Fix applied to `Code/Skin_Only_SyNRA_Registration.ipynb` 2026-07-09 (NOT yet
run):**
- Cell 4's `voxelize_to_ants()` rewritten: splat → `binary_dilation` (2 iters) →
  `binary_fill_holes` on all 3 axes, majority-vote combine — same pattern as the
  friend's `nodes_to_ants_volume()`. Applied to both `fixed_ants` and
  `moving_ants`. Density oversampling (`densify_surface_points`, unchanged) still
  runs first since the skin mesh itself is sparse (~5mm vertex spacing).
- New Cell 7b added (surface-to-surface KDTree gap, mirrors the friend's skull
  `Gap to head target: mean/max` check) — because solid-volume Dice alone is
  forgiving of a uniform few-mm surface offset; this catches that a stricter way.
  Threshold: mean gap < 5.0mm (rough scalp-thickness tolerance).

**Not yet done:** Cell 5 has not been rerun with this fix (would cost ~11-25
min, non-deterministic per `densify_surface_points`'s unseeded `np.random`).
Next session: rerun from Cell 4 onward, check Cell 5b Dice (expect much closer
to the friend's healthy range) and the new Cell 7b surface gap, then proceed to
Cell 8-10 (full-head apply + `k_mesh_qa.py` gate) only if both pass.

## 2026-07-10 — solid-fill fix run, new bug found and partially fixed

**What was run:** Cell 4 onward (through Cell 7b), executed twice out-of-band via
`nbclient` (not interactively in Jupyter) to get a reproducibility check, since
`densify_surface_points` uses unseeded `np.random`. Both runs landed on nearly
identical numbers, so the pipeline is stable despite the RNG.

**Metric 1 (Cell 5b, Dice/IoU, image domain):**

| Run | Dice | IoU | Verdict |
|---|---|---|---|
| 1 | 0.8427 | 0.7281 | MARGINAL (0.70–0.85 band) |
| 2 | 0.8425 | 0.7278 | MARGINAL |

Huge jump from the pre-fix 0.1788/0.0982, confirming the 2026-07-09 solid-fill
root cause was real. **But this number alone is misleading** — solid-fill Dice
is forgiving of a uniform offset (large interior overlap dominates the score),
exactly the caveat already written into this note above. It is not sufficient
evidence the registration converged; Cell 7b is the real check.

**Metric 1b (Cell 7b, KDTree surface gap) — new cell, run for the first time:**
run 2 (the complete one, with Cell 7b included): **mean 18.95mm, median 17.99mm,
max 53.86mm, p95 42.58mm** against a 5.0mm threshold → **FAIL**, ~4x over.
Friend's equivalent skull check is ~0.6mm for comparison.

**New bug found and diagnosed (not by rerunning — by consulting `advisor()` and
replaying the already-computed ANTs transform files out-of-notebook, no
26-min re-registration needed):** Cell 6's `transform_points()` passed raw mesh
node coordinates straight into `ants.apply_transforms_to_points()`. That ANTs
API expects **ITK LPS** convention; the skin-part VTUs are exported from
Slicer3D, which uses **RAS**. Evidence that nailed this down:
- The mesh-node centroid barely moved under **any** of the 4 valid
  `{fwdtransforms, invtransforms} × {whichtoinvert combos}` (2 more combos threw
  `Cannot invert ... because it is not a matrix` — warp fields can't take
  `whichtoinvert=True`) — all landed at 46.8–46.9mm vs. a 47.30mm starting
  distance, i.e. no real convergence in *any* direction/inversion choice.
- Meanwhile the *image*-domain intensity centroid (computed independently from
  the voxelized `.nii.gz` files) genuinely closed from 32.64mm → 14.44mm, and
  Cell 7's own printed skin-node displacement was a real mean 22.5mm/max
  46.3mm — so points were clearly moving, just not converging on the target.
  That combination (real per-point motion, no net convergence, direction-
  independent) is the signature of a coordinate-convention bug, not a
  fwd/inv direction bug (which is what Cell 6's own docstring assumed the
  failure mode would be).
- Fix: flip X/Y sign around the `apply_transforms_to_points` call (RAS→LPS in,
  LPS→RAS out; Z is shared between the two conventions). Verified against the
  existing run's transform files: **centroid distance 47.30mm → 24.15mm**
  (fwd and inv candidates now converge to the *same* value, confirming
  direction genuinely doesn't matter once the coordinate space is right).
  Full downstream replay (Cell 6→7→7b logic): **surface gap 18.95mm → 15.32mm
  mean** (median 14.01, max 41.50, p95 33.84).

**Still FAILS the 5.0mm gate after the fix (15.32mm, ~3x over).** The RAS/LPS
bug was real and worth fixing, but is not the whole story. Candidates for next
session, not yet investigated:
- `auto_rescale()`'s per-axis scale factor may itself still be off — worth
  reprinting/re-checking against the RAS/LPS-corrected point transform.
- The underlying SyN registration itself only reached MARGINAL Dice (not
  PASS) — a point-transform fix cannot compensate for residual image-domain
  misalignment the registration itself didn't resolve. Cell 5b's own
  MARGINAL-branch suggestion (raise `reg_iterations`, lower `flow_sigma`
  further) has not been tried.
- Do not proceed to Cell 8 (full `Head_V6.k` apply) until Cell 7b passes —
  Cell 8 reuses the same `transform_points()`, so it was equally broken
  before this session's fix and is still unvalidated after it.

**Notebook changes (2026-07-10):** per user instruction, the old Cell 6 code
cell was **not deleted** — every line commented out in place (marked
`[SUPERSEDED 2026-07-10]`) and a new "Cell 6-fix" markdown+code cell pair
inserted immediately after it with the RAS/LPS-corrected `transform_points()`.
Downstream cells (7, 7b, 8) are unchanged and pick up the fixed function
automatically since they call it by name, not by cell reference.

**Also note (process, not a bug):** the two out-of-band `nbclient` runs this
session wrote outputs to `New_version/New_version/outputs/skin_only_synra/`
(project root) instead of `Code/outputs/skin_only_synra/`, because `OUTPUT_DIR`
in Cell 2 is the relative path `'outputs/skin_only_synra'` and the runner
script's cwd was the project root, not `Code/`. Running the notebook normally
from Jupyter (cwd = `Code/`) will not have this problem; only the artifacts
from *this session's* out-of-band runs live in the wrong place. See
`outputs/skin_only_synra/*` (project root) for those files if reproducing the
diagnostic without rerunning.

[[Architecture|← Back to Architecture]] · [[VTU-VTU SyNRA Registration|Related: whole-mesh SyNRA notebook]]
