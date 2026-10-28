# Pipeline Changelog

Running log of every edit made to the registration notebooks in this folder,
newest first. Updated every time a change is made — including fixes that
turned out to be wrong, so the reasoning trail stays intact.

---

## 2026-07-13 — Tried and reverted: per-node bone-thickness stretch cap

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, geometry-loading + save-outputs cells

**Goal:** fix the inversion increase (7,611 → 7,788) that came with widening
`ICP_MAX_CORR_DIST_MM` to 50mm (previous entry) — some external-surface nodes
now move up to 50mm while their frozen, dura-facing partner (sharing a solid
element, across the bone's own thickness) stays at exactly 0mm, stretching
the element until it inverts. Confirmed via direct measurement: 5,260 solid
elements have this exact frozen-node + far-moved-node pattern, concentrated
in `temporal`, `occipital`, `sphenoid`, `frontal` (the thinnest-walled
bones in this template).

**What was built:** for every node sharing a solid/shell element with a
frozen node, recorded that frozen neighbor and their original (undeformed)
distance apart (`nearest_frozen_neighbor`, `nearest_frozen_dist`). At
save-time, capped each such node's final distance from its frozen neighbor
at `MAX_STRETCH_RATIO x` (3.0) that original distance.

**Result: made it worse.** Inverted elements **7,788 → 9,116** — a bigger
regression than the problem it was meant to fix — with zero accuracy benefit
(Hausdorff unchanged at 40.319mm, since the cap only ever touches internal
nodes, never the external surface the validation metrics measure).

**Root cause of the failure, confirmed by direct measurement:** checked how
many of the mixed frozen/non-frozen solid elements have *more than one*
distinct frozen node — **95.5% do** (5,008 of 5,242). The cap treated every
non-frozen node independently, snapping each one toward whichever single
frozen node happened to be nearest to *it*. When a hex element has an entire
frozen face (e.g. 4 nodes) and an entire moving face (4 nodes), each of
those 4 moving nodes could get pulled toward a *different* one of the 4
frozen anchors — turning what was a smooth, coherent parallel stretch (which
TPS produces naturally) into a skewed, twisted shape. That's a worse failure
mode than an uncapped stretch, which at least keeps the whole face moving
together consistently.

**Reverted in full** — both cells restored to their pre-cap state (confirmed
by re-running: back to Hausdorff 40.319mm, 7,788 inversions, matching the
prior entry exactly).

**What a correct version would need to do differently:** treat the
*element's whole frozen face* as a single anchor (e.g. its centroid, or a
best-fit plane), not each frozen node independently — so all of an element's
moving-face nodes get capped consistently relative to the same reference,
preserving the coherent stretch direction TPS already produced instead of
distorting it further. Not attempted yet.

---

## 2026-07-13 — Root-caused and fixed the top-of-head "surplus": Stage 6 ICP's own outlier-rejection cutoff was the culprit, not CPD or data quality

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, config cell (`ICP_MAX_CORR_DIST_MM`)

**User request:** stop attributing the persistent top-of-head spike to
"get better SAM3D data" and actually find the mechanism in the pipeline
itself. Ran four diagnostics in sequence, each ruling out the previous
hypothesis with real numbers instead of guessing:

1. **Hypothesis: weak TPS landmark support (extrapolation).** Checked
   distance from worst-residual dense points to their nearest FPS control
   point. Correlation with residual was only 0.39, and the worst points
   weren't even far from a control point (min 1.5mm). **Ruled out.**
2. **Hypothesis: CPD assigned wrong correspondence to specific landmarks.**
   Found the ~38 landmarks nearest the bad region *did* have much worse CPD
   fit (25mm vs 9.6mm median elsewhere) — a real lead. Checked direction
   agreement with spatial neighbors to look for a "pointing the wrong way"
   landmark; came back 1.00 (perfect agreement) everywhere, including the
   bad cluster — but this turned out to be an uninformative test (bulk
   rigid+affine motion dominates the total displacement vector, swamping
   any local disagreement signal).
3. **Hypothesis: Deformable CPD is what corrupts these landmarks.** Checked
   their fit quality after Affine CPD alone vs. after Deformable CPD —
   nearly identical (25.18mm → 24.99mm). They were *already* bad before
   Deformable CPD touched them. **Ruled out** as a Stage-4-specific bug.
4. **Hypothesis: Deformable CPD's regularization (`alpha`/`beta`) is too
   stiff to let it locally fix this cluster.** Re-ran Deformable CPD on the
   identical input across 6 alpha/beta combinations spanning the default
   down to very loose. Median barely moved (24.99mm → 23.81mm) and the
   **max residual was bit-for-bit identical (42.87mm) in every single
   configuration.** That invariance is the tell: CPD had already converged
   to the best correspondence available to it; no amount of retuning changes
   that. **Ruled out.**

**Actual root cause:** re-examined Stage 6.5's own earlier diagnostic output
— the worst 1% of dense-surface points sit **~44.6mm** (median) from their
true nearest subject point after TPS. Stage 6's non-rigid ICP is supposed to
correct exactly this kind of residual using the *full* dense subject cloud
(bypassing the sparse 2,000-point CPD landmark subset entirely) — but
`ICP_MAX_CORR_DIST_MM = 15.0` explicitly **discards any correspondence
farther than 15mm as a suspected outlier**. That safety valve — meant to stop
ICP from chasing scan noise — was silently and permanently locking out the
one correction this region actually needed, every single run, regardless of
any other tuning. TPS's coherent (not torn) propagation of this excluded
region is exactly why Stage 6.4's local-outlier cap always fired on zero
points: the region was internally smooth, just globally wrong, and nothing
downstream was able to reach it once ICP wrote if off.

**Fix:** raised `ICP_MAX_CORR_DIST_MM` from 15mm to 50mm. Safe specifically
*because* `head_surface.vtu` is clean re-exported geometry with no scan
noise — there's nothing spurious to chase at that distance. This tolerance
should be revisited downward once real (noisier) SAM3D subject data replaces
this same-frame validation dataset, where a large cutoff really could start
pulling toward wrong/noisy points.

**Result (full pipeline re-run):**
- Stage 6 (ICP) mean residual: 13.4mm → **1.35mm**
- Final Hausdorff: 57.44mm → **40.32mm** (30% further reduction)
- Final mean error: 7.40mm → **6.30mm**

**Trade-off, not fully free:** inverted elements increased slightly, 7,611 →
**7,788** (+177) — the corrected region now moves substantially further than
before, and some of its solid-bone elements weren't fully accounted for by
the existing frozen-boundary logic at that larger displacement. Net
assessment: a real, mechanism-level fix for the reported visual defect, at a
small, known cost to an already-open mesh-quality issue — not a full
resolution of either.

---

## 2026-07-13 — Wired the cleaned `head_surface.vtu` in as `SUBJECT_LANDMARKS_PATH` directly (not just the `.key` fallback)

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, config + loader cells

**Context:** the config cell already had `SUBJECT_LANDMARKS_PATH` pointing at
`/Volumes/Extreme SSD/Head_model/head_surface.vtu` (the cleaned `.vtu` export
from the previous session — see the entry above this one). But
`load_subject_landmarks()`'s primary branch only ever handled `.npy` or
delimited text via `np.loadtxt` — this is the exact bug already documented
lower in this changelog ("Swapped fallback subject data"): pointing
`SUBJECT_LANDMARKS_PATH` at a `.vtu` file skips the fallback path entirely and
tries to parse binary/XML `.vtu` content as plain numeric text
(`could not convert string '<?xml' to float64`). It hadn't actually been run
since that path was set, so this would have crashed on the next execution.

**Fix:** generalized `load_subject_landmarks()`'s primary branch to handle
mesh formats (`.vtu`, `.vtk`, `.stl`, `.ply`, `.obj`, `.k`/`.key`) via the
same `pv.read()` / `parse_k_file()` logic the fallback path already used —
factored into a shared `_load_mesh_points()` helper used by both branches.
Mesh formats now load at **full point density** (6,182 points from
`head_surface.vtu`, not subsampled to 3,000 like the old fallback did) —
Stage 0.5's farthest-point sampling already handles the CPD landmark subset,
so the dense ICP/blend/validation stages benefit from the extra coverage
directly.

**Result (full pipeline re-run, 0 execution errors):**
- Mean surface error: 8.71mm → **7.40mm**
- Final Hausdorff: 61.95mm → **57.44mm**
- Inverted elements: 7,698 → **7,611**
- Affine CPD still regresses vs. rigid on this dataset (Hausdorff 59.87mm →
  100.51mm before the guard fires) and falls back to rigid, consistent with
  every run so far — this is a property of the sparse 2,000-point landmark
  subset, not something the cleaned mesh input changes.

**Still the same underlying caveat as always:** `head_surface.vtu` is a
cleaned re-export of `head_surface.key`, which is still the template's own
skin surface (see "Swapped fallback subject data" entry below) — this run
validates the pipeline end-to-end on cleaner input, it is not yet a real
independent-subject registration result.

---

## 2026-07-10 — Tried and reverted: final geometric (Laplacian) smoothing pass

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`

**User-reported symptom (after the Affine regression-guard fix below):**
top-of-head lump reduced but still visibly present, plus a rough/faceted
look and a seam-like ridge near the jaw boundary in the rendered mesh.

**Hypothesis:** Stage 6.5's confidence blend decides each point's position
*independently* — it never looks at the resulting shape, only each point's
own distance to the nearest subject point. So even a defensible per-point
choice can leave a rough surface.

**Attempt 1 (reverted): uniform mesh-topology Laplacian smoothing**, added
as a new Stage 6.6, using `skull_surf`'s real triangle connectivity (not a
spatial k-NN proxy). Made every metric worse: mean residual 8.71mm →
10.31mm, max 61.95mm → 65.38mm, inverted elements 7,698 → 7,784. Blind
smoothing drags well-registered points toward their badly-registered
neighbors near the reverted/blended boundary, spreading error around
instead of removing it.

**Attempt 2 (also reverted): weighted by Stage 6.5's own confidence
field** (`1 - coverage_conf` as the smoothing weight, so trusted points stay
put and only reverted/uncertain-boundary points get pulled toward their
neighborhood average). Still regressed every metric, and inversions got
*worse* than attempt 1: mean 8.71mm → 9.41mm, inverted elements 7,698 →
7,838.

**Why both failed — a structural reason, not a tuning problem:** an earlier
fix in this same notebook (see "Root-cause fix: only the outer shell was
warped" below) established that the bone's external surface and its
internal/solid layers must move as a single coherent TPS field, or the
solid elements they share stretch and invert. Smoothing *only* the external
layer (which is all Stage 6.6 had access to) breaks that coherence again —
reintroducing the exact failure mode that fix was written to prevent. A
correct version would need to smooth the full skull volume (external +
internal + solid) in lockstep, which is a materially bigger change than a
"final polish" stage, not attempted here.

**Resolution:** reverted Stage 6.6 entirely (both cells deleted); Stage 7
and the save-outputs cell point back to `nm_surf_final_cs` (Stage 6.5's
direct output). The visible roughness is real and unresolved — the
practical path to actually fixing it is real SAM3D subject data (removes
the source of the low-confidence boundary region this roughness clusters
around), not a post-hoc smoothing pass on the current same-frame fallback
data.

---

## 2026-07-10 — Diagnosed and reduced the "surplus above the head" spike; root cause was Affine CPD, not the SAM3D `.npy` fallback

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`

**User-reported symptom:** rendered mesh (3D Slicer) showed a purple mass
poking above/through the tan subject-skin surface at the top of the skull,
plus a flared yellow region near the jaw/neck. User asked whether this was
caused by the missing `Data/subject_landmarks.npy` (real SAM3D output not
wired in yet, so the notebook falls back to `head_surface.key`).

**Partial yes, but not the direct mechanism.** `head_surface.key` is not
independent subject data — per the 2026-07-10 "Swapped fallback subject
data" entry below, its node coordinates are an *exact* match to the
template's own skin PIDs. So there genuinely is a correspondence gap (no
real SAM3D landmarks yet), but the visible spike itself turned out to be an
**algorithmic regression in Stage 3 (Affine CPD)**, not a missing/sparse
correspondence problem:

- **Diagnosis attempt 1 (wrong): absolute displacement cap.** Hypothesized
  a single point tearing away from an unconstrained warp. Added a flat
  `MAX_DISPLACEMENT_MM` cap (Stage 6.4) — this clamped 9,885 of 10,029
  points (98.6%), because the *legitimate* global rigid+affine correction
  already moves nearly every point more than the chosen threshold. An
  absolute mm cap can't distinguish "the whole surface needed a big pose
  correction" from "one point flew off on its own." Inverted elements barely
  moved (7,764 → 7,828).
- **Diagnosis attempt 2 (better, ruled out the hypothesis): local-outlier
  cap.** Replaced the absolute cap with one relative to each point's k-NN
  neighborhood mean displacement — this targets genuine single-point tears
  (the actual mechanism behind the earlier "rod through the ear" bug).
  It fired on **zero points**. This proved the spike is a *coherent region*
  moving together incorrectly, not a point torn from smooth neighbors —
  ruling out sparsity/tearing as the cause.
- **Root cause found:** the validation table showed Affine CPD (Stage 3)
  landmark Hausdorff was *worse* than Rigid CPD (Stage 2) alone — 52.2mm →
  75.7mm (varies by FPS-subsample seed; 59.0mm → 91.5mm on the run that
  fixed this) — even after the existing singular-value clamp
  (`AFFINE_SINGULAR_VALUE_CLAMP`). The clamp bounds *how implausible* the
  transform can be, but never checked whether it actually **improved** the
  fit versus rigid alone. That corrupted global alignment then propagated
  unchecked through deformable CPD → TPS → ICP → confidence blend, landing
  as the coherent purple region seen in the render.

**Fix:** added a regression guard right after the existing SVD clamp in the
Stage 3 cell — compute landmark Hausdorff for both `TY_rigid` and the
clamped affine candidate, and fall back to `TY_rigid` outright if affine is
worse. Kept Stage 6.4's local-outlier cap in the pipeline as a defense-in-depth
safeguard for future data (didn't fire here, but targets the tearing failure
mode this notebook has hit before).

**Result:** on this run, affine was worse and got skipped — Stages 2-4 now
all report Hausdorff 48.86mm (previously regressed to 75.7mm at stage 3-4).
Final blended Hausdorff: 65.51mm → **61.95mm**. Inverted elements: 7,764 →
**7,698**.

**Still open:** the spike is reduced, not eliminated — Affine CPD is
unconstrained-in-direction and can still overfit the sparse 2,000-point
landmark subset even when it's the better of the two candidates on a given
run; the real fix is real SAM3D subject data, which will give a much
better-conditioned correspondence set than the current same-frame
`head_surface.key` fallback. `MAX_DISPLACEMENT_MM`/Stage 6.4 remains
unused on this dataset but should stay in as a guard once real subject data
(with genuine coverage gaps, unlike the fallback) is wired in.

---

## 2026-07-10 — `CPD_TPS_Landmark_Registration.ipynb` rewritten: full skull+brain warp restored, with every bug fix from this session

**File:** `CPD_TPS_Landmark_Registration.ipynb` (full rewrite, per user request)

This notebook predated all of the debugging in this changelog (no PCA
pre-align, raw `88000001-88000099` PID range including jaw/teeth, no affine
clamp, no confidence-damped blend, TPS control points fit on the *unfiltered*
skull range). Rewrote it from scratch, reusing the validated architecture
from `CPD_TPS_Skin_Only_Registration.ipynb` with one deliberate structural
difference: **TPS (Stage 5) is evaluated on the entire mesh (all 179,676
nodes) instead of only the skull bone volume** -- restoring the original
project goal of a single warp field applied to skull and brain together,
rather than leaving the brain untouched.

**Why no "frozen boundary" step is needed here, unlike the skin-only
notebook:** freezing the brain at the skull boundary was only necessary
*because* the skin-only notebook deliberately keeps the brain motionless --
any skull node touching brain had to freeze too, or the shared element
tears. Here, since the smooth TPS field is evaluated everywhere, nothing is
left behind at zero displacement while its neighbor moves, so that specific
tearing mechanism doesn't apply. Only the external head/face surface gets
extra local refinement (ICP + confidence blend) on top of the same smooth
baseline everything else uses.

**Result (0 execution errors):**
- Mean surface error: 18.02mm -> 8.90mm (50.6% reduction) -- identical to the
  skin-only notebook's registration accuracy, since both are driven by the
  same head/face landmarks.
- Hausdorff: 65.51mm.
- Newly-introduced inverted elements (vs. untouched-template baseline):
  **3,513** -- notably higher than the skin-only version's 1,454. This is an
  expected tradeoff, not a new bug: warping the brain's internal structure
  (gray/white matter boundaries, ventricles, meninges layers) via a smooth
  but non-volume-preserving field introduces some local distortion there
  that the skin-only version avoids entirely by never moving the brain.
  "Skull and brain move together" and "brain mesh never gets locally
  distorted" are in direct tension; this notebook chooses the former,
  per the user's explicit request to restore that scope.

**Output:** `Data/outputs/cpd_tps_full_registration/Head_V6_full_registered.vtu`,
`validation_summary_full.csv`.

---

## 2026-07-10 — Scope narrowed to head + face bones; jaw/teeth excluded (fixes the "hanging down into the neck" artifact)

**Files:** `CPD_TPS_Skin_Only_Registration.ipynb`, `CPD_TPS_Skin_Only_Pipeline_v2.ipynb` (kept in sync)

**Problem reported:** rendered result showed a purple mass hanging down past
the chin into what looked like a spurious "neck" region, and face features
weren't registering sensibly ("can't recognize the organs in the face").

**Cause:** the external-PID filter (previous fix) still matched *any*
`_external_`-named part across the whole `88000001-88000099` range, which
includes `mandible` (lower jaw), `teeth-lwr/upr`, `alveolar`, and `palatine`.
None of these have a usable outer-skin correspondence — the jaw hangs below
where face skin actually ends, and teeth/alveolar sit inside the mouth with
no skin counterpart at all. Registering these against the skin surface
produced exactly the hanging-down artifact.

**Fix:** added `HEAD_FACE_INCLUDE_PREFIXES` — restricts both the
registration-driving surface and the full warp candidate set to braincase
bones (`frontal`, `parietal`, `temporal`, `occipital`, `sphenoid`, `ethmoid`)
plus mid-face bones with a real skin counterpart (`lacrimal`, `nasal`,
`zygomatic`, `maxilla`). Explicitly excludes `mandible`, `palatine`,
`teeth-*`, `alveolar`, and the unlabeled `str1-7`/`ng-str*` jaw-adjacent
parts — these are now frozen at their original position, same treatment as
the brain. The frozen-boundary-node logic (previous entry) was generalized
to freeze any head/face node touching *any* excluded tissue, not just brain
— so the braincase/face boundary with jaw is now handled the same principled
way as the skull/brain boundary.

**Result — improved on both axes simultaneously:**
- Mean surface error: 15.77mm → **8.90mm** (50.6% reduction, previously only 9%)
- Newly-introduced inverted elements (vs. untouched-template baseline):
  1,705 → **1,454**

**Also fixed while syncing this into `v2`:** found and fixed a pre-existing,
unrelated bug in `v2`'s config cell — `SUBJECT_LANDMARKS_PATH` was
accidentally set to an existing `.vtu` file path (a leftover from an earlier
copy/paste) instead of the intended placeholder `Data/subject_landmarks.npy`,
so it skipped the fallback entirely and tried to parse VTU/XML content as
plain numeric text (`could not convert string '<?xml' to float64`). Fixed to
match `v1`.

**Still open:** the 1,454 newly-introduced inversions and the ~65mm
Hausdorff worst-case gap are not resolved by this fix — same underlying
issues as before (temporal/sphenoid internal-subdivision gap, CPD/affine
instability, and testing against the template's own skin rather than real
subject data). This fix improves the *scope* of what's being registered, not
the registration algorithm's own accuracy.

---

## 2026-07-10 — New notebook: `CPD_TPS_Skin_Only_Pipeline_v2.ipynb`

**File:** `CPD_TPS_Skin_Only_Pipeline_v2.ipynb` (new)

Per user request, built a clean-rewrite notebook whose structure and markdown
follow the reviewed pipeline diagram (Stage 0 → 0.5 → 1 → 2 → 3 → 4 → 5 →
[cavity-constraint explicitly marked removed] → 6 → 6.5 → 7 → save → QA)
one-to-one, rather than requiring the reader to cross-reference this
changelog to understand why Stages 0.5 and 6.5 exist. Not a re-derivation:
the underlying math, PID-based external-surface extraction, full-skull-volume
warp + frozen-boundary-node handling, and confidence-damped blend are copied
unchanged from the validated `CPD_TPS_Skin_Only_Registration.ipynb` (v1) —
only the markdown narrative and cell ordering changed, plus a distinct output
filename (`Head_V6_skin_registered_v2.vtu`, `validation_summary_v2.csv`) so
running v2 doesn't overwrite v1's outputs. All code-cell outputs/execution
counts cleared (not yet re-run in this session).

**Explicit deviations from the diagram, called out in the v2 intro cell so
they don't read as silent scope creep:**
- Stage 0.5 (farthest-point landmark subsampling) — needed to keep CPD's
  O(N·M) cost tractable; diagram doesn't show it but Stage 4/5 depend on it.
- Stage 6.5 (confidence-damped blend, do-no-harm safeguard) — kept rather
  than dropped to match the diagram literally, since removing it would
  reintroduce the two blend bugs documented further down this changelog.
- Full skull bone volume + frozen boundary nodes (see entry below this one)
  — kept for the same reason; the diagram's "Stage 5" box undersells this,
  since evaluating TPS on the external surface alone was the direct cause of
  ~2,000 newly-inverted elements before this fix existed.

---

## 2026-07-10 — Root-cause fix: only the outer shell was warped, not the whole bone volume (this is what caused the spike/rod artifact in the rendered mesh)

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`

**How this was found:** user reported the rendered result showed a jagged
purple spike at the top of the skull and a thin rod-like protrusion poking
through the ear. Initial hypothesis (mesh too sparse) was wrong. Instead of
guessing, ran `k_mesh_qa.py`'s own baseline-comparison logic (which the
notebook's QA cell had never actually used until now) — comparing the
registered mesh's inverted-element set against the **untouched template's own
baseline** inverted-element set, not the raw absolute count.

**Important correction to earlier reporting:** the untouched `Head_V6.k`
template already has ~7,117 elements flagged as "inverted" by `k_mesh_qa`'s
per-PID majority-sign heuristic — this matches the tool's own documented
baseline for full-body THUMS (~0.5%, known winding-convention artifact, not a
real solver-breaking defect). Every previous changelog entry that reported
"8,600+ inverted elements" as if caused by registration was wrong to present
it that way — the true pipeline-introduced count was always the *delta*
against this baseline, which is what should have been reported from the
start.

**Actual root cause of the spike artifact:** verified that the solid bone
volume elements (e.g. `frontal_r`) share 100% of their outer-face nodes with
the external shell part (`frontal_external_r`) and 100% of their inner-face
nodes with the internal shell part (`frontal_internal_r`) — same hex mesh
representing bone thickness, opposite faces tagged as different parts. The
notebook was only ever warping the external-face nodes (from the `_external_`
PID fix), leaving the internal face completely fixed — stretching every bone
element between old (fixed) and new (moved) positions into a spike or
self-intersection. Confirmed via delta: 2,089 newly-introduced inversions,
concentrated almost entirely in solid bone PIDs (`frontal_r`, `parietal_r`,
`temporal_r`, `occipital_r`, left+right), not the ear/mastoid region
originally guessed.

**First fix attempt:** propagate the TPS warp to the *entire* skull bone
volume (external shell + internal shell + solid), not just the external
surface, driven by the same external-surface correspondence. **This made it
worse** (5,365 newly-introduced inversions) — moving the skull's *internal*-
facing nodes now tore the brain/meninges elements attached to them instead
(`Superior_Sagittal_Sinus`, `CSF_Cerebrum`, `CSF_Cerebellum` all appeared in
the newly-broken list). This is the real, structural boundary of the "brain
untouched" simplification: the skull's innermost surface shares nodes with
dura/CSF/sinus tissue at the skull-brain interface.

**Working fix:** freeze any skull node that is *also* referenced by a
non-skull element (computed via a full `parse_k_file` pass over every
element in the template, not just the skull-PID subset) — these boundary
nodes keep their original coordinate untouched, exactly like the brain.
Only nodes that are exclusively skull tissue (not shared with anything
outside the skull PID range) actually get warped. Result: full skull volume
has 22,660 candidate nodes, 15,407 frozen at the skull/brain interface,
7,253 actually warped. Newly-introduced inversions dropped to 1,705 (down
from 2,089 in the very first fix, and far down from 5,365 in the failed
full-volume attempt).

**Remaining, still open:** 1,705 newly-introduced inversions, now
concentrated most heavily in `temporal_r/l` (401+208) and `sphenoid_r/l`
(187+150) — these bones likely have additional internal subdivisions beyond
the simple external/internal shell pair (e.g. `temporal_shell` as a further
separate part) that aren't yet accounted for by the frozen-boundary logic,
or these are simply the bones where the underlying CPD/affine warp itself is
least stable (see the earlier affine singular-value blowup, also worst on
temporal/sphenoid-adjacent landmarks). Next step if this needs to go to
zero: apply the same "freeze if shared with a part outside the immediately
warped set" logic *within* the skull PID range too (i.e. check for
additional undocumented internal subdivisions), or trace the specific
`temporal_r`/`sphenoid_r` failing element IDs back to their node
displacement to see if it's a localized CPD/TPS control-point sparsity issue
in that specific region.

---

## 2026-07-10 — Fix: Stage 6.5 safeguard was reverting to a *worse* position

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`

**Bug found:** the "confidence-damped blend" safeguard (added earlier the same
day, see below) compared a warped point's residual distance to a fixed
threshold and reverted to the point's *original, unwarped* position whenever
that threshold was exceeded — without ever checking whether the original
position was actually farther from the subject surface. For the hardest
points (near the ear/mastoid region), the original position's error was
66–83mm, actually *worse* than what TPS had already achieved (64.6mm) —
so the "safeguard" was undoing real improvement.

**Fix:** rewrote `coverage_damped_blend()` to compare the residual **at the
warped position** against the residual **at the original position** directly,
and blend toward whichever is actually closer (linear ramp across a 10mm
transition zone), instead of thresholding on the warped residual alone. Added
an explicit assertion (`d_blended_mm.max() <= max(d_orig_mm.max(),
d_warped_mm.max())`) so this class of regression fails loudly in the notebook
itself if it recurs.

**Result after fix:** final Hausdorff 72.4mm (previously regressed to 83.4mm
with the buggy version; TPS-only stage was 64.6mm). Do-no-harm property now
holds by construction.

---

## 2026-07-10 — Fix: unconstrained affine CPD was blowing up

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, Stage 3 cell

**Problem found:** after restricting the registration target to only the true
external skull surface (see next entry), the affine CPD stage started
producing an implausible transform — up to 41% anisotropic scale plus heavy
shear (singular values `[1.444, 0.929, 0.922]`) — causing Hausdorff distance
to spike to 137–168mm at that stage. Root cause: affine CPD is unconstrained
and can overfit noise/sparsity in the landmark subset, especially once the
target point cloud got smaller and more localized after the PID fix.

**Fix:** clamp the singular values of the recovered affine matrix `B` to
`[0.8, 1.25]` via SVD before applying the transform (`AFFINE_SINGULAR_VALUE_CLAMP`
config constant). Keeps the transform close to a similarity transform while
still allowing modest anisotropy.

**Result:** raw singular value 1.444 clamped to 1.25; stage-3 Hausdorff still
not great (137mm) but bounded rather than unbounded — later stages (TPS,
confidence blend) are what actually recover a reasonable result.

---

## 2026-07-10 — Root-cause fix: internal skull-base parts were being registered against skin

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, "Load template geometry" cell

**Problem found (this is the actual cause of the "sticking out, not
overlapping" artifact reported by the user):** the skull-surface extraction
used a blanket PID range (`88000001`–`88000099`, "facial/cranial bone")
established earlier in this project. That range includes deep, internal
skull-base parts — e.g. `sphenoid_internal_r/l` — that border the brain/dura,
not the scalp. Diagnosed by checking the worst-residual nodes after
`extract_surface()`: the top offenders sat exactly on the sagittal midline
(y≈0) at ~74mm from the nearest skin point, all belonging to `sphenoid_r`/
`sphenoid_internal_r` (confirmed via the template's own `$HMNAME COMPS`
part-name comments). `pyvista`'s `extract_surface()` can't distinguish "true
external boundary" from "internal cavity boundary of this cell subset" — it
returns both as surface faces once brain cells are excluded from the
selection, so any subset that borders excluded internal tissue looks like
part of the "outer surface" to the algorithm even though anatomically it
faces inward.

**Fix:** the template already labels this distinction at the part-name level
(`frontal_external_r` vs. `frontal_internal_r`, etc., via `$HMNAME` comments).
Added `parse_external_pids()`, which scans those comments and keeps only PIDs
whose name contains `_external_`, instead of a blanket numeric PID range.
Reduced the registered skull surface from 21,655 points (mixed internal +
external) down to 10,452 points (external-only, 22 parts).

**Verified impact on raw (pre-registration) alignment:** mean nearest-neighbor
distance from skull-surface to skin dropped from 16.9mm to a comparable range
with the worst offenders removed; median distance dropped substantially
(median 13.4mm → single digits in later runs) since the ~74mm sphenoid
outliers no longer contaminate the metric.

**Caveat, not yet resolved:** removing the internal parts did **not** fully
fix the visual "sticking out" problem end-to-end — the affine/CPD stages
became *more* unstable on the smaller, more localized point set (see next
entry above), and a real residual gap (Hausdorff ~64–72mm) persists in some
region even after registration. This looks like a genuine hard-to-register
area (see "Known open issue" below), not a remaining PID-selection bug.

---

## 2026-07-10 — Swapped fallback subject data to `head_surface.key`

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, config + loader cells

Replaced the placeholder fallback (`ImageToStl.com_head_voxels_transform_2.vtu`,
a random subsample of a large unrelated head-shape mesh) with
`/Volumes/Extreme SSD/Head_model/head_surface.key` — a real outer-head-skin-only
LS-DYNA keyword mesh (6,182 nodes), per user request. Updated
`load_subject_landmarks()` to parse `.k`/`.key` files via
`k_mesh_qa.parse_k_file()` in addition to the existing `.vtu` path via `pyvista`.

**Important finding surfaced by this swap:** `head_surface.key`'s bounding box
and node coordinates are an *exact* match (0.0mm difference) to the template's
own skin-tissue part IDs (`88000167–172`, `88000219–236`). This is not
independent subject data — it's a re-export of the same `Head_V6` template's
own skin surface. Useful as a same-coordinate-frame sanity check (true
answer should be small, physiological soft-tissue-thickness offsets only,
not a real subject registration problem), but **not a substitute for real
SAM3D subject data** once that's available. Flagged inline in the notebook.

---

## 2026-07-10 — Changed final output format from `.k` patch to `.vtu`

**File:** `CPD_TPS_Skin_Only_Registration.ipynb`, "Save outputs" + QA cells

Per user request, replaced the `.k` text-patching writer (`patch_k_file()`,
which rewrote only the matching `*NODE` lines in a copy of `Head_V6.k`) with
a `pyvista`-based `.vtu` writer: copies the in-memory `template_mesh` (already
loaded from `Head_V6.vtu`), overwrites only the skull-surface point
coordinates via the `node_id` → point-index map, and saves with
`mesh.save()`. The QA cell was updated to match — instead of re-parsing a
written `.k` file, it now reuses the *original* `.k`'s element connectivity
(topology is unchanged either way) with the *updated* node coordinates
in-memory, avoiding an unnecessary file round-trip.

---

## 2026-07-09 — Initial notebooks created

- **`CPD_TPS_Landmark_Registration.ipynb`** — first working prototype: full
  pipeline (center+resize → PCA pre-align → rigid/affine/non-rigid CPD → TPS
  propagated to the *entire* dense mesh, skull **and** brain together).
  Executed end-to-end successfully; ~12.6% reduction in mean surface error
  over the full pipeline on placeholder data.
- **`CPD_TPS_Skin_Only_Registration.ipynb`** — simplified variant per user
  request: registers the outer skull/skin surface only; brain and all other
  internal parts are explicitly left untouched at their original template
  coordinates. Added Stage 6 (lightweight non-rigid ICP refinement) and
  Stage 7 (NN/Chamfer/Hausdorff validation + `k_mesh_qa.py` integration).
  Both notebooks confirmed to run cleanly (0 errors) on this MacBook M2
  (arm64) with native `pyvista`/`vtk`/`pycpd` wheels — no Rosetta needed.

---

## Known open issue (as of 2026-07-10, unresolved)

Even after all fixes above, the final registered mesh still has:
- **Hausdorff distance ~64–72mm** in the worst-covered region (likely
  ear/mastoid/skull-base area, where the external skull surface and
  `head_surface.key`'s coverage genuinely diverge or the CPD/affine fit is
  hardest).
- **~8,700 inverted elements** flagged by `k_mesh_qa.py` — this mesh would
  crash or stall an LS-DYNA solve as-is and should **not** be treated as
  solver-ready output yet.

This is a real, unresolved registration-quality limitation, not a code bug —
the do-no-harm safeguard (Stage 6.5) guarantees the output is never worse
than doing nothing, but "no worse than nothing" is not the same as "good."
Next things worth trying, in rough priority order:
1. Get real SAM3D subject landmarks instead of `head_surface.key` (which, as
   noted above, is the template's own skin — not an independent registration
   problem, so it can't validate whether the pipeline generalizes).
2. Investigate whether the persistent large-residual region corresponds to a
   genuine subject/template coverage gap (crop the skull surface to match)
   or a CPD hyperparameter issue (`CPD_ALPHA`/`CPD_BETA` retuning for the
   smaller, external-only point set).
3. Investigate the ~8,700 inverted elements directly — trace a handful of the
   flagged element IDs back to their node warp displacement to see if they
   cluster in the same region as the residual-error hot spot (would confirm
   it's the same root cause) or are scattered (would suggest a separate
   local mesh-density issue, e.g. TPS control points too sparse there).
