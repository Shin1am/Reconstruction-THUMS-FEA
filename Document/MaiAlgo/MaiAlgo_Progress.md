# MaiAlgo — progress log

Running log for the algorithm work done with Claude. Newest entries go at the bottom. Frozen baselines (Day1, Day2) and the Day3 run are left as they are; new work goes in this folder.

Last updated: 2026-11-17 (section 18)

## Folder layout (reorganised 2026-11-24)

```
Document/MaiAlgo/
  MaiAlgo_Progress.md, MaiAlgo_Notebook_Guide.md
  code/      early experiment scripts (run_exp.py, run_all.sh, eval_exp.py, aggregate.py, jacobian_diagnostic.py, cfg.py, jobs.txt); the current pipeline is the notebook in Code/notebook/CPS_Pipeline/
  logs/      run logs of those scripts
  output/    experiment outputs, one out_<case>_<name>/ folder each (git-ignored): baselines and G2_skinlm_nose of cases 02/03/05/08/12, out_slicer_case_02, out_tmp_batch (per-case data of the 40-case run)
  results/   case_csv/ (per-case tables), 40case_before_nosefix/, 40case_nosefix/ (tables, pictures, mesh quality; slicer_scenes/*.mrb are not committed)
```
Older entries below name paths as they were then: `out_*` folders now live in `output/`, `results_40case` is `results/40case_before_nosefix`, `results_40case_nosefix` is `results/40case_nosefix`, `results_case_NN.csv` is in `results/case_csv/`, `log_*.txt` in `logs/`. About 100 experiment output folders (X/Y/Z/S/T series, C/D eyes runs, ARAP variants, G1/G2c, temporary batch copies) were deleted on 2026-11-24; their numbers are in this log.

---

## 1. Where the project stood (from the existing markdown files)

- Goal: warp the THUMS AM50 head (skull, brain, meninges, skin) to a subject's skin using **one** warp field, then export FEA-ready geometry for LS-DYNA.
- History: SimpleITK registration → ANTsPy SyNRA (abandoned: 15.3 mm surface gap against a 5 mm gate) → **CPD + TPS skin-driven pipeline (active)**.
- Day 1 (frozen baseline, self-test on the template's own skin): mean 3.907 mm, Hausdorff 49.029 mm.
- Day 2 (per-corner Jacobian): the old `k_mesh_qa` over-flagged. True failures: template 4, registered 742 (739 caused by the warp). The cause is Stage 6 non-rigid ICP, and almost all of it is in the thin skin layers.
- Caveat noted in the files: the Day 1/2 "subject" was never independent, so the interior was never validated.

## 2. Research check (web search, 2026-10-27)

Confirmed or found:
- BCPD (Hirose, TPAMI Feb 2020), BCPD++ (Dec 2020), geodesic BCPD (2022). Code on GitHub.
- Li 2021 and Li et al. 2023 (image-registration morphing of head models and THUMS). Tizzard & Bayford 2007 (elastic warping of a head FE mesh). Aigerman & Lipman (injective bounded-distortion maps in 3D).
- FLAME models only the hairless cranium (i3DMM paper).
- No paper found that links a FLAME/face-scan fit to a THUMS skull+brain mesh.

Retracted: my earlier claim that Kleiven-group work uses Kriging was not supported by anything I found.

## 3. Ideas discussed (not yet implemented)

1. Keep TPS as the base warp. Treat the ICP residual as a separate field and spread it inward through the skin thickness (Laplace/biharmonic solve on the tet mesh).
2. Elastic FE morph: skin displacement as boundary condition, load steps, Jacobian check each step (Tizzard-style; LS-DYNA could do the solve).
3. Per-node line search on the elements that fail.
4. Inversion-free projection (Aigerman & Lipman).
5. BCPD as a front end.

Your 4-step plan (align → skin point-cloud match → learn skin→interior regression → apply and fine-tune) was assessed: steps 1, 2 and 4 are sound. Step 3 (training) is not needed yet and is data-starved with one template. A learned correction only makes sense later, as a residual on top of the propagated field, using the HaN-Seg subjects.

## 3b. Data found

`Data/HaN-Seg/GT/` holds ground truth you generated: 20 usable cases and 2 not usable (case_15, case_19). Each usable case has skin, outer and inner skull table, skull cranium, brain, CSF shell, dura, ventricles and facial bone surfaces. All are in LPS mm in the CT frame. The cerebrum, cerebellum, dura, falx and tentorium labels are marked "approx" (derived, not expert-labelled).

## 4. Step 1 result: unchanged baseline on case_02

Run on 2026-10-27/28. Files live in `Document/Day3_Case02_Baseline/` (script, CSVs, meshes, write-up). They are not modified by this log.

- The registration stages are copied verbatim from the frozen notebook. A run on the old fallback subject reproduces Day 1 exactly (3.907 / 49.029).
- Adaptations, I/O only: the landmark seed was replaced by a fixed axis map (THUMS X=ant, Y=left, Z=up → LPS), and the neck cutoff by an automatic shoulder crop (z ≥ −925).

| Measure | case_02 result |
|---|---|
| Skin mean / Hausdorff | 3.51 mm / 52.3 mm |
| Skull outer vs GT (rigid+scale → registered) | 13.9 → 10.9 mm |
| Skull inner vs GT | 13.4 → 11.8 mm |
| Brain vs GT | 11.9 → 11.7 mm |
| Eyes vs GT | 24.5 → 2.4 mm |
| Z-extent of registered structures vs GT | 1.30–1.64× (stretched) |
| Failing solid elements | 4 → 3,594 (Day 1 self-test: 742) |

Reading: the skin fits well but the interior is barely better than rigid+scale and is vertically stretched. Failures concentrate in the cerebellum, occipital and skin. A rigid+scale-only control has 0 new failures, so the frame change is not the cause. The neck-cut level is the main suspect and is **not yet tested**.

## 5. Environment

- No system Python was on the PATH. I built a venv at `C:\Users\Acer\AppData\Local\Temp\rv` (Python 3.12, numpy 2.x, scipy, pandas, pyvista 0.49, pycpd 2.5.4, matplotlib, nibabel). It is outside the project. Day 1 used pycpd 2.0.0 and the legacy run still matched.
- Git: this folder was not a repository. On 2026-10-28 I ran `git init` (default branch `main`), extended `.gitignore`, made one initial commit (126 files, `.git` is 167 MB), and created and checked out the branch **`TryAlgoMai`**. All work from here goes on that branch. Git needed `-c safe.directory=...` on each command because the D: drive does not record ownership; I did not change your global git config.
- `.gitignore` now also excludes: `resultBaseline/`, `FE_data/`, `kfile/`, `ls_folder/`, `*.zip`, `*.nrrd`, `*.mp4`, `*.vtp`, `*.ply`, `*.npy`, `._*`, and per-run output folders under `Document/` (`out_*/`, `rerun/`, `ablation/`). `Data/`, `outputs/` and mesh/volume formats were already ignored.

## 6. Open items

- [x] Git repo initialized and `TryAlgoMai` branch created (2026-10-28).
- [ ] Test the neck-cut hypothesis (crop template and subject to the same head region).
- [ ] Repeat on 3–4 more cases to see the spread.
- [ ] Then test one change at a time against the Day 3 numbers: no ICP, ICP residual smoothed through the thickness, elastic option.
- [ ] Optional: synthetic known-warp self-test.

---

## 7. Experiments 1–2 on case_02 (2026-10-29): CPD outlier weight, no-ICP, eye-anchored start

Code: `run_exp.py` (copy of the Day 3 runner with switches), `eval_exp.py`, `jacobian_diagnostic.py` (copy), `aggregate.py`. Results table: `results_case_02.csv`. Run folders `out_*` are git-ignored. Day 3 files were not touched.

Evaluation fix: the GT "brain" excludes the brainstem, so the brain is now compared **without** the THUMS stem parts (PIDs 88000104/105/124/125), and the stem is compared separately with `brainstem_OAR`. The baseline was re-evaluated with this fix (`out_baseline_ref/`), so the first row below differs slightly from Day 3 for the brain.

Diagnostic that led here: after the rigid+scale step the THUMS eyes sit 38 mm below the GT eyes, and the baseline pulls the lower half of the brain down 20–25 mm. The start is poor, and skin alone cannot say where the neck ends.

| Run | Change vs baseline | skin mean | skin Haus. | skull out | skull in | brain | stem | eyes | brain z-ext | failing solids |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 baseline | none (Day 3) | 3.51 | 52.3 | 10.9 | 11.8 | 11.8 | 23.2 | 2.4 | 1.30 | 3,594 |
| A | CPD `w = 0.2` | 2.46 | 215.7 | 70.9 | 80.3 | 82.7 | 111.7 | 37.0 | 0.19 | 96,815 |
| B | no ICP | 6.16 | 56.7 | 14.0 | 13.4 | 12.1 | 26.0 | 7.2 | 1.24 | 2,091 |
| C | eye-anchored start + eye-matched crop | 3.40 | 37.9 | 7.4 | 7.8 | 9.1 | 11.7 | 4.7 | 1.12 | 888 |
| D | C + CPD `w = 0.2` | 3.13 | 82.5 | 5.8 | 6.1 | 9.4 | 9.4 | 1.7 | 0.79 | 822 |

Rigid+scale-only control: skull 13.9 / 13.4, brain 12.1, stem 14.8, eyes 24.5 mm.

Findings:
1. **A is a collapse, not a result.** With the centroid start, `w = 0.2` makes rigid CPD shrink the template to scale 0.067. Its skin mean (2.46 mm) looks the best of all runs, yet the interior is destroyed. Skin mean error alone is not a safe score.
2. **The starting alignment matters most.** C (eye-anchored start, crop at the template's own distance below the eyes) beats the baseline on every interior measure: skull 10.9 → 7.4 mm, brainstem 23.2 → 11.7, brain z-stretch 1.30 → 1.12, failing solids 3,594 → 888, and skin Hausdorff 52 → 38. This is the neck/start hypothesis, now supported on one case.
3. **`w > 0` helps only from a good start.** D improves the skull (5.8 / 6.1 mm) and eyes (1.7 mm), but the skin Hausdorff rises to 82.5 mm (the subject-side coverage gap grows) and the brain is compressed to 0.79 of GT height.
4. **ICP is not the whole story on a real subject.** Removing it (B) cuts failures from 3,594 to 2,091 but does not fix them, and costs skin accuracy. The Day 2 conclusion (ICP is the cause) held on the self-test only partly.
5. Still unfixed: 800–900 failing solids even in the best runs, versus 4 in the template.

Caveats: one subject; C and D change the start **and** the crop together (not separated); the eye anchor uses the GT eye centroid, i.e. extra landmark information the baseline did not have (the Day 1 baseline did use 10 landmarks); GT cerebrum/cerebellum/dura are "approx" labels.

Next: separate start vs crop (C1 / C2), repeat C and D on 3–4 more cases, then test the ARAP / deformation-graph propagation against run C.

---

## 8. Move to the G: clone; steps 1-3 (2026-10-29)

**Setup.** Work now lives in the `Reconstruction-THUMS-FEA` clone on `TryAlgoMai` (merged `origin/main`, no conflicts; nothing pushed). Data root is one constant in `cfg.py` (`BIODAT_ROOT` env var, default `G:/My Drive/BioDat_Yusuke_lab`); run folders `out_*` stay here and are git-ignored. `aggregate.py` takes the baseline from `out_<case>_baseline`. `run_all.sh <case> <name> [flags]` does run + interior eval + Jacobian; `jobs.txt` is the queue used below. A fresh baseline on case_02 reproduces Day 3 exactly (3,594 failing). Venv: `C:\Users\Acer\AppData\Local\Temp\rv`. From now on new code goes into cells at the end of `Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb`, not new `.py` files.

### Step 1 - start vs crop (case_02)

| Run | start | crop | skin mean | skin Haus. | skull out | skull in | brain | stem | eyes | brain z | failing |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | centroid | auto | 3.51 | 52.3 | 10.9 | 11.8 | 11.8 | 23.2 | 2.4 | 1.30 | 3,594 |
| C1 | eyes | auto | 3.37 | 67.5 | 7.2 | 8.5 | 10.0 | 9.5 | 2.6 | 1.24 | 18,131 |
| C2 | centroid | eyes | 3.90 | 55.1 | 9.6 | 9.2 | 9.9 | 14.9 | 8.0 | 1.17 | 797 |
| C | eyes | eyes | 3.40 | 37.9 | 7.4 | 7.8 | 9.1 | 11.7 | 4.7 | 1.12 | 888 |

Reading: both changes help, differently. The eye-anchored **start** gives most of the skull/brainstem gain; the eye-matched **crop** gives the lowest failing-solid count. Only the combination (C) is good on both. C1's 18,131 failures are unexplained (rigid CPD scale and affine SVs are identical to the baseline; only the origin differs), so failures look fragile to small start changes.

### Step 2 - spread over cases (baseline / C / D; mean_sym mm; failing = failing solids)

| case | run | scale | skin mean | skin Haus. | skull out | skull in | brain | stem | eyes | brain z | failing |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 03 | baseline | 0.96 | 3.18 | 51.0 | 10.7 | 11.8 | 11.5 | 19.8 | 6.6 | 1.18 | 1,388 |
| 03 | C | 0.98 | 3.85 | 66.7 | 10.4 | 8.2 | 9.5 | 14.0 | 51.1 | 0.99 | 2,733 |
| 03 | D | 0.94 | 6.82 | 99.7 | 6.6 | 6.7 | 9.2 | 4.7 | 7.2 | 0.90 | 810 |
| 05 | baseline | 0.97 | 3.34 | 59.9 | 11.4 | 11.7 | 11.3 | 22.1 | 4.1 | 1.31 | 2,557 |
| 05 | C | 0.95 | 2.73 | 48.3 | 6.1 | 7.2 | 8.4 | 11.1 | 2.5 | 1.24 | 4,659 |
| 05 | D | 0.08 | 10.85 | 103.5 | 23.5 | 31.8 | 41.5 | 64.4 | 16.7 | 0.63 | 87,054 |
| 08 | baseline | 1.01 | 3.51 | 51.7 | 14.4 | 15.3 | 13.5 | 33.5 | 2.7 | 1.18 | 1,388 |
| 08 | C | 1.00 | 3.02 | 41.9 | 8.3 | 8.0 | 8.6 | 11.3 | 3.3 | 1.03 | 990 |
| 08 | D | 0.62 | 7.69 | 87.4 | 10.2 | 10.5 | 12.9 | 20.0 | 18.6 | 0.77 | 30,730 |
| 12 | baseline | 1.00 | 4.14 | 63.1 | 12.2 | 10.4 | 11.2 | 14.5 | 86.6 | 1.07 | 1,148 |
| 12 | C | 0.96 | 2.79 | 49.9 | 5.0 | 5.1 | 8.2 | 8.2 | 3.1 | 0.96 | 1,407 |
| 12 | D | 0.41 | 6.50 | 109.2 | 16.3 | 16.8 | 17.9 | 43.3 | 17.0 | 0.74 | 59,169 |

case_02 (re-run here): C as in step 1; D 3.13 / 82.5 / 5.8 / 6.1 / 9.4 / 9.4 / 1.7 / 0.79 / 822. Full per-case tables: `results_case_*.csv`.

Reading:
1. **C beats the baseline on skull, brain and brainstem in all 5 cases** (skull ~11-14 -> 5-10 mm, brainstem 14-33 -> 8-14 mm), except case_03 where the skull-outer gain is small and the eye error jumps to 51 mm.
2. **Failing solids do not follow**: C lowers them on case_02 and case_08, raises them on case_03 (x2), case_05 (x1.8) and case_12 (x1.2). Mesh validity is not solved by a better start.
3. **D (CPD w=0.2) is not safe**: the template collapses (rigid scale 0.08-0.62) on 3 of 4 new cases, even from the eye-anchored start. Do not use w>0 without a scale constraint on the rigid stage. D only works on case_02/case_03.
4. Baseline eyes error is erratic (case_12: 86.6 mm), a sign of a wrong rigid start in the baseline.

### Step 3 - skin-driven ARAP propagation (case_02, on top of run C)

Method (notebook cells): keep run C's final skin nodes as fixed boundary; rest shape = template after one global affine fit to the skin; edge-graph ARAP (uniform-ish 1/length weights, hex 12 edges, 30 local-global iterations, initial guess = C's TPS interior); nodes not connected to the skin through the mesh (eyes, 4,886 nodes) keep the run's coordinates.

| Run | skin mean | skin Haus. | skull out | skull in | brain | stem | eyes | brain z | failing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C (TPS interior) | 3.40 | 37.9 | 7.40 | 7.76 | 9.07 | 11.70 | 4.69 | 1.12 | 888 |
| C + ARAP | 3.40 | 37.9 | 7.34 | 7.30 | 8.42 | 9.85 | 4.69 | 1.09 | 820 |

Reading: ARAP is a small gain over TPS on the interior (brain -0.65 mm, stem -1.9 mm, skull-inner -0.5 mm; failing 888 -> 820) and moves solid nodes by 7.8 mm on average. It does not touch the real bottleneck: 798 of the 815 newly failing elements touch the skin nodes that the pipeline overwrites with the ICP/blend positions, and ARAP holds those fixed. Volume ratios of valid elements stay 0.72-1.37 (1%-99%).

Caveats: ARAP tested on one case only; the first ARAP attempt left the eyes 762 mm away until the unreachable-node rule was added (fixed). Proximal/Tikhonov term and a robust (Welsch) boundary loss from the survey are not implemented yet.

### Next
1. Fix the boundary: smooth or relax the overwritten skin nodes (e.g. ARAP with soft skin constraints, or ICP residual smoothed through thickness) and re-measure failing solids.
2. ARAP on case_03/05/08/12; add `prox > 0` and compare.
3. Understand C1's 18k failures and case_03's eye error (51 mm).

---

## 9. Notebook rewrite and research-plan mapping (2026-10-30)

**Notebook.** `Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb` was rewritten from the first cell: 23 cells (3 MB -> 24 KB), one step per cell, short titles only; all explanations moved to `MaiAlgo_Notebook_Guide.md`. It uses the HaN-Seg subject and the G: data root, has the CPD fixes as switches (`INIT`, `CROP`, `CPD_W`, `USE_ICP`), and includes the interior-vs-GT check, the Jacobian check, ARAP and the results table as cells. The old landmark / SAM3D cells are removed (original kept in `CPD_TPS_Skin_Only_Pipeline_v2.ipynb`).

**Verification.** A full pass of the notebook cells on case_02 (`INIT='eyes', CROP='eyes'`, run name `C_nb`) reproduces the script run C exactly, and its ARAP stage reproduces `C_eyes_arap`:

| Run | skin mean | skin Haus. | skull out | skull in | brain | stem | eyes | failing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C (script) | 3.40 | 37.85 | 7.40 | 7.76 | 9.07 | 11.70 | 4.69 | 888 |
| C_nb (notebook) | 3.40 | 37.85 | 7.40 | 7.76 | 9.07 | 11.70 | 4.69 | 888 |
| C + ARAP (script) | 3.40 | 37.85 | 7.34 | 7.30 | 8.42 | 9.85 | 4.69 | 820 |
| C_nb + ARAP (notebook) | 3.40 | 37.85 | 7.34 | 7.30 | 8.42 | 9.85 | 4.69 | 820 |

Environment: conda env `2d_3d_regis` (Python 3.10) lacked only `pycpd`; installed `pycpd 2.0.0` (pip has nothing newer for 3.10; the numbers above come from the temporary venv with pycpd 2.5.4, so a run in the conda env may differ slightly).

**Mapping to the research plan (Stage 1 / C1 / C2 / C3).** Naming warning: the run labels "C1" and "C2" in section 8 step 1 mean *start* and *crop* splits, not the plan's stages C1/C2.
- Everything in this log so far is the plan's **C2** setup: only the subject skin drives the registration, the GT interior is used for scoring only. (One deviation from strict C2: the eye-anchored start uses the GT eye centroid.) The numbers in sections 7-8 are therefore C2 numbers.
- **C1** (complete head model, best case) is not done. Proposed design: a separate notebook `02_C1_full_head_registration_baseline.ipynb`; same CPD/TPS/ARAP stack but driven by all GT surfaces (skin, outer/inner skull table, brain, brainstem, eyes), each THUMS structure matched to its own GT structure, scored with the same interior and Jacobian cells. Fit and score on the same surfaces gives a ceiling, not a prediction error; add a hold-out variant (e.g. fit skin + skull, score brain) as a middle point.
- **C3** (SAM 3D skin as input) and **Stage 1** (SAM 3D vs CT skin) are not started.

### Next
1. Build C1 as above; decide whether to rename the current notebook to the C2 notebook and drop the GT-eye anchor so C2 is strictly skin-only.
2. ARAP boundary fix (relax overwritten skin nodes) and ARAP on the other four cases.
3. C1 start-effect puzzle (18k failing) and case_03 eye error.

---

## 10. Research plan status (Stage 1 / C1 / C2 / C3) and hand-over to another PC (2026-10-30)

### 10.1 Plan (from the research workflow) and status

Goal: separate the error of the 2D-to-3D external reconstruction from the error of the FE registration algorithm. Planned notebooks: `01_validate_2D_to_3D_reconstruction.ipynb`, `02_C1_full_head_registration_baseline.ipynb`, `03_C2_external_only_CT_registration.ipynb`, `04_C3_reconstructed_head_registration.ipynb`.

| Stage | Input to the algorithm | Compared with | Status |
|---|---|---|---|
| 1 | SAM 3D mesh from a 2D photo | skin surface from the same subject's CT/MRI | **Not started.** Needs a dataset with photo + CT/MRI of the same subject (HaN-Seg has CT/MRI only, no photos). |
| C1 | complete 3D head (all GT surfaces: skin, outer/inner skull table, brain, brainstem, eyes, ...) | GT structures; ceiling for C2/C3 | **Not started.** Design below. |
| C2 | external-only skin from CT/MRI (GT interior hidden) | GT interior, and the C1 baseline | **Done for the algorithm on 5 cases** (sections 7-9). Current notebook = C2. One deviation to remove: the eye-anchored start uses the GT eye centroid. |
| C3 | external-only skin reconstructed by SAM 3D | GT interior, and C1 | **Not started.** Needs Stage 1 output. |

Decision rule from the plan: C3 good -> pipeline works; C2 good but C3 poor -> reconstruction is the weak part; both poor -> the registration algorithm or its inputs need work.

### 10.2 C1 design (proposed, not built)

1. New notebook `02_C1_full_head_registration_baseline.ipynb` with the same cells as the current notebook, except the driving data.
2. Driving data: for every THUMS structure take the matching GT surface (skin <-> `skin_surface`, outer/inner skull parts <-> `outer_table_surface` / `inner_table_surface`, cerebrum + cerebellum <-> `brain`, stem parts <-> `brainstem_OAR`, eyes <-> `eyes_OAR`; other GT surfaces listed in `Data/HaN-Seg/GT/README.md`). Fit a single warp (CPD+TPS on the stacked, structure-labelled point sets, or per-structure CPD followed by one TPS), then ARAP for the remaining interior.
3. Scoring: same interior-vs-GT and Jacobian cells as C2 so the numbers are directly comparable.
4. Caveat: fit and score on the same surfaces gives a ceiling (how well the model can deform), not a prediction error. Add a hold-out variant (fit skin + skull, score brain) as a middle point between C1 and C2.
5. Template-to-GT correspondence needs care: GT "brain" excludes the stem; GT cerebrum/cerebellum/dura/falx/tentorium are "approx" (derived, not expert-labelled).

### 10.3 C2 clean-up still to do

- Remove the GT-eye anchor (use a skin-only start, e.g. centroid start with the eye-matched crop replaced by something skin-only such as a chin / vertex / nose-tip based crop) so C2 is strictly external-only; re-measure.
- Boundary fix for failing solids (798 of 815 newly failing touch the overwritten skin nodes); ARAP on case_03/05/08/12; understand the 18k failures of "eyes start + auto crop" (section 8, step 1) and the 51 mm eye error on case_03; CPD `w > 0` only with a scale constraint.
- Optional: rename the current notebook to `03_C2_external_only_CT_registration.ipynb`.

### 10.4 Moving to another PC - checklist

1. `git clone https://github.com/Shin1am/Reconstruction-THUMS-FEA.git`, then `git checkout TryAlgoMai` (all work is there; `main` has other contributors' PRs and was merged into this branch). Pull before starting.
2. Data is not in git. Needed from Google Drive `BioDat_Yusuke_lab/Data`: `mesh_model/Head_V6.vtu`, `Ls_dyna_model/Head_V6.k`, `HaN-Seg/GT/usable/<case>/stl/*.stl` (40 usable cases; QA in `HaN-Seg/GT/qa_summary.csv`). Point the code at it with the environment variable `BIODAT_ROOT` (folder that contains `Data/`); default is `G:/My Drive/BioDat_Yusuke_lab`. The notebook cell 0 reads `DATA_ROOT`; the scripts read `Document/MaiAlgo/cfg.py`. Check the Drive files open (sync can be offline/slow) before a long run.
3. Python: conda env with numpy, scipy, pandas, pyvista, matplotlib, ipykernel, `pycpd` (2.0.0 via pip on Python 3.10; 2.5.4 on 3.12 was used for the logged numbers). Notebook kernel name expected: `2d_3d_regis`. Set `PYTHONUTF8=1` for the scripts on Windows.
4. Open `Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb`, set `CASE`, `NAME`, switches in cell 0, run top to bottom (about 10 min per case). Presets: baseline = `INIT='centroid', CROP='auto', CPD_W=0`; run C = `INIT='eyes', CROP='eyes'`; D = C + `CPD_W=0.2`.
5. Run outputs `Document/MaiAlgo/out_<case>_<name>/` are git-ignored and are NOT in the repo; regenerate them (the results CSVs and this log hold the numbers). Batch of the five-case study: the 14 runs listed in `jobs.txt`, run with `run_all.sh` (script versions of the same steps).
6. Do not edit `Document/Day1_Baseline`, `Day2_Jacobian`, `Day3_Case02_Baseline`. New work and notes go in `Document/MaiAlgo/`; update this log after each experiment.
7. Git quirks seen on the D: / G: machines: if git reports "dubious ownership", pass `-c safe.directory=...` per command instead of changing global config. In the working tree of the first PC the old `Code/ipynb/*` notebooks show as deleted (a manual move into `Code/notebook/`); that was never committed.
8. Open items for the other PC: build C1 (10.2), make C2 strictly skin-only (10.3), find a photo+CT dataset for Stage 1 and C3.

---

## 11. Making C1 and C2 different and valuable (discussion, 2026-10-30; nothing implemented)

**Problem.** The current code drives the registration with the skin only. Run through it, "C1" would give the same numbers as C2. C1 only means something if the algorithm can also take the internal structures as input. Open question for the user: is C1 (a) an oracle where the same warp also sees the internal structures (recommended: gives a ceiling for C2/C3, but is not a deployable algorithm) or (b) the same skin-only algorithm on a clean full model (then C1 and C2 are one experiment)? To be decided; this section assumes (a).

**What must stay identical between C1 and C2:** template, warp family and regularisation (CPD -> TPS -> ARAP), start alignment (no GT-derived anchor in either; the current GT-eye anchor must go), scoring (interior vs GT + Jacobians). Suggested code shape: one `register(template, targets)` where `targets` maps structure name to points; C1 passes all structures, C2 passes only the skin. Tune hyper-parameters once, not per condition.

**Ideas, in suggested order**
1. **Information ladder.** Same warp, increasing observations: skin only (C2) -> + outer skull -> + both skull tables -> + brain -> everything (C1). Error per rung shows which internal structure is worth measuring or predicting; C1 and C2 become the two ends of a curve. The "fit skin + skull, score brain" rung is a true held-out test.
2. **Learned skin -> interior prior (main contribution).** Run C1 on all 40 usable HaN-Seg cases; every output is the THUMS head warped to that subject with identical topology. Build a statistical model (e.g. PCA of node displacements). C2 predicts the model coefficients from the skin alone (ridge / PLS), tested leave-one-subject-out; C3 uses the same predictor with a SAM 3D skin. Error split: C1 residual = what the model cannot represent; C2 - C1 = what the skin cannot tell; C3 - C2 = reconstruction error. Build the model in warp space and finish with ARAP so elements stay valid (warping alone leaves about 800 failing solids, section 8).
3. **Structural priors for C2.** Skin-to-skull soft-tissue thickness maps learned from the 40 subjects, brain nested inside the inner skull with a CSF gap, no surface crossing. Barely active in C1, informative in C2.
4. **Uncertainty.** Sample the regression posterior to get several plausible interiors and a per-region spread, so FE users know where the predicted interior can be trusted.

**Cautions.** Idea 2 needs a clean C1 on all 40 cases first. 40 cases is the full sample, so use leave-one-out and expect no separate final test set. GT cerebrum / cerebellum / dura / falx / tentorium are "approx" labels, which limits how far the brain-side error can be trusted.

**Suggested next steps:** settle the (a)/(b) question; make C2 strictly skin-only; build `register(template, targets)` and the ladder (idea 1) on case_02 and the four other cases; then C1 on all 40 cases as input to idea 2.

---

## 12. Decisions: C1 oracle, weighted prediction + observation, conditional-Gaussian prior (discussion, 2026-11-01; nothing implemented)

**Decisions**
1. **C1 is an oracle (option a).** The same warp also sees the subject's internal structures (skull tables, brain, brainstem, eyes). Fit and score on the same surfaces give a ceiling (can the template and warp represent this head?), not a prediction error. C2 - C1 = what the skin cannot tell; C3 - C2 = reconstruction error. Not a deployable algorithm.
2. **One algorithm, not two.** `register(template, targets)`: the objective is a sum of one data term per structure present in `targets`, plus the regulariser (TPS -> ARAP). C1 passes all structures, C2 only the skin, ladder rungs add one at a time. Hyper-parameters, start alignment and scoring are fixed across conditions. Each structure's term is normalised by its point count so the skin is not drowned out in C1.
3. **Prediction + observation fusion.** Interior position = weighted combination of `p_pred` (predicted from skin) and `p_obs` (observed internal structure, if present): `p = (w_pred*p_pred + w_obs*p_obs) / (w_pred + w_obs)`. `w_obs = 0` gives C2, large `w_obs` gives C1, partial data (e.g. skull but no brain) is conditioned on what exists. Preferred weights: inverse variance (prior variance from leave-one-out error; observation variance from segmentation noise, higher for the "approx" labels cerebrum / cerebellum / dura / falx / tentorium). Do not score a structure against the same observation that was fused; report held-out structures only.
4. **Prior = conditional Gaussian on C1 warps.** Options compared for building `p_pred`: multi-atlas assembly, statistical shape model, joint conditional Gaussian, thickness regression, deep learning (needs far more than 40 cases), literature soft-tissue thickness tables, covariate regression (age / sex / head size). Chosen: conditional Gaussian; multi-atlas kept as the comparison baseline (it reuses the same C1 runs).

**Plan (nothing edited yet)**
- Phase 0, prerequisites: remove the GT-eye anchor (skin-only start, e.g. centroid + chin / vertex / nose-tip crop) and re-measure case_02 and the four other cases; fix the ARAP skin-boundary problem (relax the overwritten skin nodes) so C1 outputs are valid meshes.
- Phase 1, C1 engine: label THUMS parts by structure; build `register(template, targets)` with per-structure normalised weights; run C1 on case_02 (check ceiling and failing solids), then on all 40 usable cases. Gate: fix bad C1 cases before they enter the model.
- Phase 2, conditional Gaussian: per case vectors of skin (`x`) and interior (`y`) displacements after removing rigid + scale; joint Gaussian with low-rank (probabilistic) PCA; `E[y|x]` is `p_pred`, the conditional covariance gives the weight; observed structures enter as a weighted data term; finish with ARAP to restore element validity.
- Phase 3, evaluation: leave-one-subject-out (including choice of modes and regularisation); held-out structures only (skull, brain, brainstem, eyes) plus failing solids; compare current C2 (TPS / ARAP), conditional Gaussian from skin, a mean-shape control, and the C1 ceiling; `w_obs` sweep and information ladder; check that predicted uncertainty matches real error.
- Deliverables: C1 notebook (`02_...`) and model notebook (`03_...`) in the cell-per-step style, guide notes in `MaiAlgo_Notebook_Guide.md`, results CSVs per case and method, this log updated after each experiment.

**Risks.** Only 40 cases (few reliable modes, regression toward the mean; the mean-shape control shows it); "approx" GT labels limit brain-side trust; C1 quality sets the ceiling; a predicted field can still fold elements, so the ARAP finish and failing-solid count are reported at every stage.

**Open questions.** (1) Model all nodes or only key-structure surface nodes (surface-only is far smaller; ARAP fills the volume)? (2) Do Phase 0 first (recommended, avoids re-running C1) or build Phase 1 on the current code?

---

## 13. Phase 0 results: skin-only C2 start and ARAP skin boundary (2026-11-01)

**Housekeeping.** `TryAlgoMai` fast-forwarded to `Maialgo` 6ccbab3; a `main` merge by another PC had reverted the G:-path script edits, restored in 6ba43f0. Notebook changes: new switches `INIT = centroid | skinlm | eyes`, `CROP = nose | vertex | auto | eyes` (env-var overridable for batch runs), faster ARAP (sparse incidence products instead of `np.add.at`; one sparse LU shared by all boundary variants), and boundary variants. Details in `MaiAlgo_Notebook_Guide.md`. mm = symmetric mean distance to GT; "fail" = failing solid elements (template has 4).

### 13.1 Removing the GT-eye anchor (C2-strict start)

| Variant | start | crop | result on case_02 / case_03 |
|---|---|---|---|
| E1 | centroid | vertex height | skull 15.8 / 20.2, fail 4,175 / 32,718 (worse than baseline) |
| E2 | vertex + nose-tip landmarks | vertex height | skull 14.8 / 14.7, fail 12,188 / 37,073 (worse) |
| G1 | centroid | nose tip | skull 10.1 / 11.3, about the baseline |
| **G2** | **vertex + nose-tip landmarks** | **nose tip** | **skull 8.9 / 7.1**, close to or better than run C |

Reasons: both heads span about 250 mm vertex-to-scan-bottom (template 252 mm, subjects 249-251 mm), so a vertex-height crop removes almost nothing and the neck below the face still disagrees. What made run C work was cutting the subject at a facial landmark; the nose tip (about 30 mm below the eyes) is the skin-only equivalent (cut within 6 mm of the eye-based cut on case_02). The skin-landmark start puts the eye centroids 15-27 mm apart before CPD, against 60-80 mm for the centroid start. **G2 uses no GT-derived information** and is the C2-strict reference from here on.

### 13.2 G2 against baseline and run C (5 cases, before ARAP)

| case | run | skin mean | skull out | skull in | brain | stem | eyes | fail |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 02 | baseline | 3.51 | 10.9 | 11.8 | 11.8 | 23.2 | 2.4 | 3,594 |
| 02 | C (GT eyes) | 3.40 | 7.4 | 7.8 | 9.1 | 11.7 | 4.7 | 888 |
| 02 | **G2** | 3.49 | 8.9 | 8.1 | 8.9 | 12.2 | 7.9 | 738 |
| 03 | baseline | 3.18 | 10.7 | 11.8 | 11.5 | 19.8 | 6.6 | 1,388 |
| 03 | C | 3.85 | 10.4 | 8.2 | 9.5 | 14.0 | 51.1 | 2,733 |
| 03 | **G2** | 3.01 | 7.1 | 7.2 | 8.9 | 7.6 | 6.0 | 11,095 |
| 05 | baseline | 3.34 | 11.4 | 11.7 | 11.3 | 22.1 | 4.1 | 2,557 |
| 05 | C | 2.73 | 6.1 | 7.2 | 8.4 | 11.1 | 2.5 | 4,659 |
| 05 | **G2** | 2.86 | 5.7 | 5.8 | 7.5 | 7.1 | 2.7 | 913 |
| 08 | baseline | 3.51 | 14.4 | 15.3 | 13.5 | 33.5 | 2.7 | 1,388 |
| 08 | C | 3.02 | 8.3 | 8.0 | 8.6 | 11.3 | 3.3 | 990 |
| 08 | **G2** | 3.27 | 8.8 | 7.7 | 8.7 | 9.5 | 7.0 | 739 |
| 12 | baseline | 4.14 | 12.2 | 10.4 | 11.2 | 14.5 | 86.6 | 1,148 |
| 12 | C | 2.79 | 5.0 | 5.1 | 8.2 | 8.2 | 3.1 | 1,407 |
| 12 | **G2** | 3.25 | 5.4 | 5.4 | 7.8 | 9.3 | 4.8 | 870 |

G2 beats the baseline on skull, brain and brainstem in all five cases (skull 5-9 mm against 11-14 mm) and matches run C without any GT-derived start. Its failing-solid counts are below the baseline's in four of five cases (case_03 is the exception: 11,095). The eye error is larger than run C's in some cases (case_02: 7.9 against 4.7).

### 13.3 ARAP skin-boundary fix (G2 start; `arap` = full skin residual, `a05` = ICP/blend residual halved toward the TPS skin, `sm` = skin displacement smoothed over 30 neighbours x3)

| case | G2 (TPS interior) | ARAP raw | ARAP a05 | ARAP sm |
|---|---|---|---|---|
| 02 | fail 738 · skull 8.9/8.1 · brain 8.9 · skin 3.49 | 744 · 8.6/8.2 · 8.8 · 3.49 | 34 · 9.3/8.9 · 9.3 · 4.37 | **6** · 8.7/8.2 · 8.8 · 4.22 |
| 03 | 11,095 · 7.1/7.2 · 8.9 · 3.01 | 1,310 · 9.5/10.5 · 10.7 · 3.01 | 178 · 10.9/11.8 · 11.6 · 4.62 | **100** · 9.8/10.7 · 10.8 · 3.99 |
| 05 | 913 · 5.7/5.8 · 7.5 · 2.86 | 946 · 5.7/5.7 · 7.5 · 2.86 | 38 · 6.2/6.4 · 7.9 · 3.66 | **5** · 5.7/5.8 · 7.5 · 3.75 |
| 08 | 739 · 8.8/7.7 · 8.7 · 3.27 | 716 · 8.7/7.9 · 8.5 · 3.27 | 38 · 9.3/8.6 · 8.9 · 4.07 | **4** · 8.7/8.0 · 8.5 · 3.99 |
| 12 | 870 · 5.4/5.4 · 7.8 · 3.25 | 774 · 4.5/4.1 · 7.2 · 3.25 | 54 · 5.1/4.8 · 7.6 · 3.85 | **4** · 4.5/4.2 · 7.2 · 3.95 |

(Format: failing solids · skull outer/inner mm · brain mm · skin mean mm. Full tables: `results_case_*.csv`.)

Findings
1. **The failing solids come from the rough skin boundary, not from the interior solve.** Smoothing the skin displacement before ARAP takes failing solids from about 700-900 to 4-6 on four cases (and from 11,095 to 100 on case_03) at a skin cost of 0.7-1.1 mm mean, with interior accuracy unchanged. Halving the ICP residual is weaker (34-178). This resolves the open item from section 8 (798 of 815 newly failing elements touched the overwritten skin nodes).
2. **ARAP also improves the interior slightly where TPS was already good** (case_12: skull 5.4 -> 4.5 mm, brainstem 9.3 -> 4.2 mm; case_05: brainstem 7.1 -> 6.4; case_02: brainstem 12.2 -> 11.6).
3. **Exception: case_03.** ARAP raises the interior error (skull 7.1 -> 9.5 mm, brainstem 7.6 -> 14.9 mm) while repairing the mesh. The TPS interior there was accurate but folded the mesh (11,095 failures); the ARAP result is valid but loses that accuracy. Reason not yet understood; the affine rest shape may fit that head poorly.
4. After the smoothing fix the mesh-validity gap is mostly closed (about 5 failing against 4 in the template), so the interior error is now the main remaining quantity for C1 / C2 comparisons.

### 13.4 Status of Phase 0 and next
Done: skin-only start and crop (G2), failing-solid fix (ARAP `sm`). Not done: the case_03 ARAP regression; GT-eye run C kept only as reference (it is not C2-strict). A C2 reference per case is now `G2 + ARAP sm` (skin mean 3.8-4.2 mm).
Next: Phase 1 (C1 engine: `register(template, targets)` with per-structure weights, C1 on case_02 first, then all 40 cases). Before that, decide whether to spend time on case_03 (check the affine rest fit and the skin-landmark detection) since it will show up again in the 40 cases.


## 14. Phase 1: C1 engine (2026-11-14)

Notebook cells 11-12 (`register(targets, start)`) added to `CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb`; description in `MaiAlgo_Notebook_Guide.md`. Start = the G2 result of the same notebook run (skin landmarks + nose crop, CPD, TPS/ICP, skin only). Mean symmetric distance to GT (mm), failing = failing solid elements (template 4).

**Dataset check.** HaN-Seg is head-and-neck cancer radiotherapy patients; the brain is normal (README only warns that tumour distortion of the neck is not checked). NMDID (CT only, no segmentations, access by committee) and Harvard-Oxford (atlas space, no subject skin) were looked at and not adopted.

**Engine.** Per observed structure: nearest-GT pull (+ reverse GT-to-node pull, 25 mm clip), displacement low-passed over 20 neighbours, 1000 control nodes (brain 300), one thin-plate-spline update per iteration with per-point smoothing `lam * n_ctrl / n_used` (equal weight per structure), lam schedule stiff -> flexible, 2 inner iterations. About 40-200 s per run.

### 14.1 case_02 (start G2, 8.9 / 8.1 / 8.9 / 12.2 / 7.9 mm, failing 738)

| run | skull out | skull in | brain | stem | eyes | failing |
|---|---|---|---|---|---|---|
| all, lam 1e3..0.1, no low-pass | 2.05 | 1.18 | 3.48 | 1.29 | 1.31 | 50,734 |
| + soft ARAP finish mu 0.3 / 3 / 30 | 2.63 / 2.15 / 2.05 | 1.72 / 1.22 / 1.18 | 4.11 / 3.56 / 3.50 | 4.68 / 1.98 / 1.37 | 2.13 / 1.52 / 1.34 | 11,677 / 25,429 / 30,540 |
| low-pass 20, floor 10 | 2.66 | 1.39 | 3.74 | 3.43 | 2.72 | 11,981 |
| low-pass 20, floor 1e2 | 3.09 | 1.59 | 3.95 | 4.15 | 3.16 | 5,046 |
| low-pass 20, floor 1e3 | 4.14 | 2.49 | 4.72 | 5.07 | 3.51 | 1,061 |
| low-pass 20, floor 1e4 | 4.39 | 3.29 | 5.53 | 6.24 | 4.16 | 742 |
| ladder: skin only | 9.44 | 8.65 | 9.13 | 13.72 | 8.18 | 744 |
| ladder: skin + both skull tables | 2.35 | 1.29 | 5.23 | 8.64 | 6.14 | 2,493 |

### 14.2 case_05, notebook run end to end (`results_c1_case_05.csv`)

| run | skull out | skull in | brain | stem | eyes | failing |
|---|---|---|---|---|---|---|
| c1_stiff | 2.68 | 1.72 | 3.82 | 3.93 | 0.66 | 1,116 |
| c1_mid | 2.28 | 1.30 | 3.23 | 3.00 | 0.55 | 4,957 |
| c1_fit | 2.07 | 1.18 | 3.12 | 2.41 | 0.51 | 13,162 |
| l_skin | 5.74 | 5.84 | 7.46 | 6.64 | 3.07 | 926 |
| l_skin_skull | 1.96 | 1.12 | 4.88 | 4.74 | 4.22 | 1,228 |

### 14.3 Findings

1. The warp family can represent both heads: with all structures observed, every structure is 1-4 mm from GT on both cases (start 8-12 mm). This is the C1 ceiling (fit and score on the same surfaces).
2. Accuracy and mesh validity trade off through one stiffness parameter. Failures are almost all brain parts (white/grey matter, cerebellum): the template brain has folds, the GT brain surface is smoother, so a node-wise nearest pull collapses the folds. Low-passing the pull and fewer brain control points helped (50k -> 12k at the same floor); stiffer final stage gives ~1k failing (case_02 floor 1e3) at 4-5 mm brain/stem. A soft-ARAP finish did not beat this (12k-30k failing).
3. Information ladder (case_02 / case_05): skin only leaves the brain at 9.1 / 7.5 mm; adding the skull tables brings brain to 5.2 / 4.9 mm and brainstem to 8.6 / 4.7 mm; adding brain and brainstem brings them to 3-4 mm. The skull tables carry most of the information about where the brain is, so predicting the skull from the skin is the first thing the prior has to do.
4. Mesh-validity gate for the prior: use `c1_stiff` fields (about 1k failing) for learning; `c1_fit` is the accuracy ceiling only.
5. Housekeeping: the temp venv `rv` was cleaned; scripts now run in the conda env `2d_3d_regis` (python 3.10, pycpd 2.0.0).

Next: C1 on all 40 usable cases (about 10 min per case on this PC, mostly CPD; cell 10 about 250 s), gate the bad ones, then Phase 2 (conditional Gaussian skin -> interior displacement). Case_03 ARAP regression still open.


### 14.4 Skin roughness found in the first C1 version, and the fix (2026-11-17)

Slicer showed jagged skin in the skin+skull and C1 outputs. Measured skin roughness (distance of each skin node to the mean of its neighbours), case_02:

| result | mean | nodes > 5 mm | max |
|---|---|---|---|
| original template | 0.62 | 19 | 6.8 |
| skin only (G2 + ARAP `_sm`) | 0.67 | 18 | 7.5 |
| first C1 versions | 2.26-2.52 | 332-504 | 21-48 |
| start skin of the engine (`coords_reg`, TPS + ICP + blend) | 2.14 | 241 | 13.2 |

The roughness was already in the start skin: the TPS/ICP/blend skin is rough, and the skin-only result looked smooth only because the ARAP boundary smoothing was applied to it. (My first reading, that the C1 pulls created it, was wrong.)

Tests on case_02 (mean symmetric distance to GT, mm):

| variant | skull out | skull in | brain | stem | eyes | failing | roughness | skin mean |
|---|---|---|---|---|---|---|---|---|
| old stiff (skin driven by the engine) | 4.14 | 2.49 | 4.72 | 5.07 | 3.51 | 1,061 | 2.26 | 1.53 |
| + no pulls near the neck cut | 4.12 | 2.49 | 4.72 | 5.07 | 3.51 | 1,059 | 2.28 | 1.69 |
| + edge-graph diffusion of the field, 10 / 30 steps | 4.02 / 4.15 | 2.93 / 3.12 | 4.83 / 5.06 | 6.02 / 6.90 | 3.89 / 4.41 | 4,699 / 4,203 | 2.15 / 2.14 | 2.48 / 3.23 |
| diffusion 30 steps, floor 1e2 | 3.50 | 2.38 | 4.50 | 6.94 | 3.79 | 11,814 | 2.14 | 3.31 |
| **smoothed skin held fixed, interior only, stiff (`c1_stiff`)** | 3.17 | 2.19 | 4.58 | 5.04 | 3.55 | **303** | **0.67** | 2.14 |
| **same, floor 1e2 (`c1_mid`)** | 2.69 | 1.48 | 3.60 | 4.10 | 3.25 | 3,076 | 0.67 | 2.14 |

Ladder with the same setup (`results_c1_case_02.csv`): `l_skin` 8.88 / 8.10 / 8.92 / 12.21 / 7.92 mm, 130 failing; `l_skin_skull` 2.44 / 1.39 / 5.34 / 7.95 / 6.46, 471 failing.

Findings: (1) the smooth deformation that helps is the skin smoothing, not diffusion of the whole field (diffusion made interior and validity worse); (2) holding the smoothed skin and fitting only the interior gives the template's own roughness, about 3.5 times fewer failing solids and a better interior than the old C1 stiff; (3) the cost is skin accuracy, mean 2.14 mm (HD95 11.2) instead of 1.5. Notebook cells 11-12 now implement this. The case_05 numbers in 14.2 are from the first engine version (skin driven by the engine) and need a re-run.


### 14.5 Brainstem and eye volume collapse (case_02, 2026-11-17)

Diagnosis (case_02, C1 stiff before the fix): brainstem volume 5.0 mL (GT 20, template 15.7), only 54 of 1,682 elements inverted, i.e. real compression: height 46.6 -> 34.4 mm, centroid still 17 mm off; eyes squashed vertically (41.7 -> 21.7 mm, GT 32). Cause: nearest-point pulls collapse small structures and the stiff spline cannot correct them locally.

Fix, tested one change at a time (all stiff, failing solids in brackets): per-structure affine targets for brainstem and eyes (a first version had a translation bug after clamping the scale) -> brainstem 5.0 -> 1.5 mm, volume 22.6 mL, no inverted elements, eyes 3.6 -> 0.8 mm, but failing 303 -> 1,508-1,818; similarity instead of affine: no better (2,066); untangling (Laplacian relaxation of free nodes) hardly helped (1,818 -> 1,617). The remaining failures sit 25-31 mm around the brainstem: the GT brain surface contains the brainstem (100% of GT brainstem vertices are inside it) but the template brain does not (12% of the warped brainstem nodes inside the template brain), so the brain term squeezes the cerebrum into the repositioned brainstem. Excluding the zone around the brainstem from the brain term: 10 / 15 / 20 / 25 mm -> failing 1,105 / 711 / 525 / 333, brain 5.0 / 5.2 / 5.2 / 5.3 mm. Chosen: affine targets + 25 mm exclusion (notebook cells 11-12).

Final case_02 (`c1_stiff` / `c1_mid`): skull outer 2.90 / 2.45, inner 2.00 / 1.39, brain 5.31 / 4.88, brainstem 1.48 / 1.35, eyes 0.79 / 0.83 mm, failing 333 / 2,230 (template 4), skin roughness 0.67. Dice: brain 0.92 / 0.93, brainstem 0.83 / 0.84 (was 0.33), eyes 0.80 / 0.78 (hull-based per eye; the nested eye shells break an inside/outside test). Brain surface distance is inflated by internal template surfaces; skull-inner Dice not computed (open shell). Skin-only reference for the same case: brain Dice 0.79, brainstem 0.18, eyes 0.22.


### 14.6 Remaining failing solids: skin layer fixed (case_02, 2026-11-17)

Where the 333 of `c1_stiff` were: 258 touch the skin (head_skin left/right 141, face_skin 113), 75 elsewhere (temporal bones 47). The skin elements are stretched, not squeezed: scalp thickness is fine (result 6.0 mm, GT 7.2, template 6.8, nothing under 2 mm), but a through-thickness edge of 6.5 mm in the template is 36.9 mm in the result. Cause: the start's interior came from a TPS through the unsmoothed skin, while the skin put back was the smoothed one, so skin and interior disagreed by several mm at sharp features.

Tried and rejected (case_02): carry the skin correction inward with a depth fade (6 / 12 / 20 / 35 mm): skull outer 4.2-7.7 mm, failing 810-3,836 (worse); skin as a zero-displacement data term (weights 1 / 5 / 25): skull outer 4.2-4.4, failing 320-303 (no real gain); Laplacian untangling on the final result: 107 -> 328 / 401 (worse).

Kept: rebuild the interior of the start from the smoothed skin (one TPS through the smooth skin, smoothing 1e-3) before the engine runs. Results (stiff / mid): skull outer 2.86 / 2.40, inner 1.96 / 1.35, brain 5.14 / 4.73, brainstem 1.49 / 1.32, eyes 0.68 / 0.73 mm; failing **107 / 1,254** (was 333 / 2,230); of the 107 only 27 touch the skin. The start alone (`l_skin`) has 4 failing, like the template. Ladder with the same start: `l_skin` 9.05 / 8.35 / 8.86 / 13.04 / 7.04 mm, 4 failing; `l_skin_skull` 2.40 / 1.37 / 5.23 / 7.82 / 5.60, 163 failing.

What is left in the 107: temporal bones (60) with both faces fixed by the skull targets (the GT temporal bone is thinner than the template's element thickness in places, a data conflict), face skin 27, a few small parts. Not fixable by relaxing free nodes.


## 15. 40 cases: C1 on every case, skin -> skull -> brain model, leave-one-out registration (2026-11-17)

**Run.** All 40 usable cases through cells 0-12 (skin-only start, stiff C1; about 200 s per case, four in parallel). From the C1 fits: fixed template nodes per structure, all cases aligned by their skin only (generalised Procrustes), reduced-rank ridge regression skin -> skull (stage 1) and skull -> brain, brainstem, eyes (stage 2, trained on the true skull), also joint skin -> everything and the mean shape. Leave one subject out; each prediction is registered into the template (known-correspondence pulls, one stiff TPS, smooth skin kept) and scored against the real GT. A first model selection used a closed-form leave-one-out that is degenerate for near-exact fits (it always chose the least regularised model, and chain and joint came out identical); it was replaced by explicit leave-one-out refits (ranks 12-24, ridge 0.01-0.1).

**Node error of the prediction against the C1 targets (mm, leave-one-out, 40 cases).** chain: skull outer 4.91, inner 4.71, brain 4.63, brainstem 5.47, eyes 9.31; joint 4.94 / 4.73 / 4.69 / 5.62 / 9.55; mean shape 8.21 / 7.73 / 6.96 / 7.00 / 20.56. Brain, brainstem, eyes from the TRUE skull: 3.58 / 4.32 / 4.97.

**Scores against the real GT after registration (mean over cases).** Mean symmetric distance in mm, TRE = mean distance of six centroid landmarks, HD95 in mm.

| | skin only (C2) | mean shape | joint | **chain** | C1 oracle |
|---|---|---|---|---|---|
| skull outer / inner | 8.82 / 8.07 | 6.44 / 6.13 | 4.55 / 4.04 | **4.52 / 4.03** | 3.02 / 2.13 |
| brain | 9.22 | 8.37 | 6.83 | **6.83** | 5.45 |
| brainstem | 10.19 | 3.35 | 2.81 | **2.75** | 1.46 |
| eyes | 14.69 | 14.47 | 5.26 | **4.92** | 0.87 |
| TRE (6 centroids) | 18.95 | 15.03 | 8.44 | **8.28** | 4.24 |
| Dice brain / brainstem / eyes | 0.79 / 0.21 / 0.36 | 0.82 / 0.65 / 0.25 | 0.87 / 0.69 / 0.52 | **0.87 / 0.70 / 0.52** | 0.91 / 0.84 / 0.80 |
| HD95 skull outer / inner | 32.8 / 30.7 | 20.2 / 19.0 | 15.6 / 12.7 | **15.4 / 12.5** | 13.1 / 9.1 |
| HD95 brainstem / eyes | 28.2 / 24.6 | 9.8 / 22.6 | 8.1 / 10.6 | **8.0 / 10.4** | 4.9 / 3.1 |
| failing solids, mean (median) | 249 (4) | 609 (46) | 1,399 (175) | **1,548 (158)** | 2,368 (138) |

Without the five pose outliers (cases 07, 27, 30, 34, 41; 35 cases) the chain gives skull 3.96 / 3.42, brain 6.47, brainstem 2.58, eyes 3.12 mm, TRE 7.16, Dice 0.88 / 0.71 / 0.56, failing 529 (C2: 8.04 / 7.38, 8.69, 9.97, 7.10, TRE 15.85, Dice 0.80 / 0.22 / 0.40; C1 oracle 2.92 / 1.96, 5.38, 1.44, 0.76, TRE 4.11, Dice 0.92 / 0.84 / 0.81). Skin mean 2.18 mm (HD95 19.3) for all methods (1.94 / 16.5 without the outliers), because the smooth skin is kept.

**Findings.** (1) The prediction beats both the skin-only start and the mean shape on every structure, and in no case is it worse than the skin-only start (average of the five structure distances). (2) The skull is predicted to about 4.5 mm (from 8-9 mm), brain Dice 0.87 against 0.79; the brainstem is mostly a stable position (the mean shape already gives 3.35 mm), the eyes are the structure where the skin helps most (14.5 -> 4.9 mm). (3) Chain and joint are almost the same; the chain is slightly better for eyes and brainstem. (4) The remaining gap to the C1 oracle is about 1.5-2 mm for the skull and 0.2-0.3 Dice for brainstem and eyes. (5) The worst cases are the head-tipped pose outliers (34: 15.5 mm average, brain Dice 0.64; 30: 11.5, 0.75; 07: 10.9; 27) and case_37 (6.3, 11,299 failing solids); even their C1 oracle is poor because the nose-tip start fails there. The two best cases are 23 and 16 (3.3 mm average, brain Dice 0.90), then 31, 05, 38, 42. (6) Mesh validity is the weak point: predicted meshes fail more often than the skin-only start (median 158 against 4); several cases are large (37, 34, 30, 07).

**Caveats.** The prediction targets are the C1 fits, not the raw GT, so the scores include the C1 residual (oracle TRE 4.2 mm); GT brain-side surfaces are approximate; brain surface distance is inflated by internal template surfaces, use the brain Dice; eye Dice is hull-based per eye; linear model, 39 training cases per fold, training included the five pose outliers (a training set without them was not run); one run of leave-one-out, no uncertainty weighting yet; the 25 mm / 0.8-1.25 settings of C1 were tuned on case_02.

**Kept** (`Document/MaiAlgo/results_40case/`): four overlap pictures (best1 case_23, best2 case_16, worst1 case_34, worst2 case_30; skin only, prediction and C1 oracle against GT), `summary_means.csv`, `per_case_scores.csv`, `direct_prediction_errors.csv`, and four Slicer scenes (`slicer_scenes/*.mrb`, about 25 MB each, not committed): ground truth (blue), prediction (orange), skin only (green), C1 oracle (purple), skull inner, brain, brainstem and eyes as separate models, ground truth and prediction visible by default. **Deleted:** the temporary per-case results (`out_tmp_batch`, the per-case working folders). Code: notebook cells 11-14 (the batch step is cells 0-12 per case, see the guide).

## 16. Head-tipped start fixed (2026-11-17)

**Cause.** In the five pose outliers (07, 27, 30, 34, 41) the head is tipped back with the chin forward, so the most anterior skin point (the start landmark and the nose crop) is the chin, 157-194 mm below the vertex (normal heads: 95-139 mm). The start and the crop were wrong, the rigid CPD ended 14-60 deg away, and skin-only TRE was 41-53 mm (normal about 19). A pose search by trimmed rigid ICP on the skin was tried and dropped: a round cranium leaves the pitch free (its pose differed from the skull pose by 17-50 deg in all cases).

**Fix (cells 2, 6, 8).** `NOSE_WIN` (env `MAI_NOSEWIN`, default 145 mm): the subject nose tip is the most anterior point within 145 mm below the vertex. Skin only; only the five outliers get a different nose (their nose lands 83-106 mm below the vertex; case_07 at 83 mm is the highest, check it by eye).

**Result** (mean symmetric distance, mm; old -> new; 3 controls unchanged to 0.1-0.2 mm). Skin only, skull outer: 07 12.2 -> 4.2, 27 10.1 -> 7.5, 30 15.6 -> 7.4, 34 19.3 -> 9.1, 41 14.3 -> 5.4; eyes 78-90 -> 3-13 (34 still 13.1). C1 oracle, skull outer / inner: 07 3.3/2.7 -> 2.7/1.6, 27 3.4/2.2 -> 2.9/1.8, 30 3.4/3.1 -> 2.5/1.8, 34 5.1/5.3 -> 3.1/2.0, 41 3.4/3.1 -> 2.6/1.7; eyes 0.6-0.7 everywhere. Controls 02, 05, 23 identical. Failing solids not compared yet.

**Not done.** The other 35 cases were not re-run (their nose is unchanged by construction); the skin -> skull -> brain model and its leave-one-out scores (section 15) still contain the old outlier fits and must be re-run to update. A run of 4 cases needs `OMP_NUM_THREADS=3` (and MKL/OPENBLAS) per process; without it four processes slowed each other to about 50 min per case.

## 17. 40 cases re-run with the nose-window start (2026-11-24)

**Run.** All 40 cases again (cells 0-12, `MAI_NOSEWIN=145`), model and leave-one-out registration as in section 15 (results in `results/40case_nosefix/`; section 15 files in `results_40case/` are the run before the fix). Three cases (11, 12, 13) crashed on first read and cases 10 and 14 gave wrong fits (case 14 had read a skin file of 23,349 points instead of 40,194): Google Drive reads were flaky; re-running those five gave the old values, then model and scoring were redone. A run of 4 cases needs `OMP_NUM_THREADS=3` per process.

**Scores, mean over 40 cases** (mm; Dice; failing = solid elements with a non-positive corner Jacobian). Section 15 value in brackets for the chain.

| | skin only | mean shape | joint | **chain** | C1 oracle |
|---|---|---|---|---|---|
| skull outer / inner | 7.88 / 7.23 | 4.74 / 4.27 | 4.19 / 3.66 | **4.18 / 3.64** (4.52 / 4.03) | 2.90 / 1.94 |
| brain | 8.61 | 7.10 | 6.67 | **6.66** (6.83) | 5.37 |
| brainstem | 9.50 | 2.93 | 2.52 | **2.53** (2.75) | 1.43 |
| eyes | 7.05 | 5.18 | 4.67 | **4.62** (4.92) | 0.75 |
| TRE (6 centroids) | 15.47 | 8.82 | 7.79 | **7.73** (8.28) | 4.08 |
| Dice brain / brainstem / eyes | 0.81 / 0.25 / 0.39 | 0.86 / 0.68 / 0.50 | 0.88 / 0.72 / 0.55 | **0.88 / 0.72 / 0.55** | 0.92 / 0.84 / 0.81 |
| failing solids, mean (median) | 67 (4) | 199 (32) | 221 (65) | **358 (66)** (1,548 (158)) | 579 (94) |

Without case_37 (see below): chain skull 3.89 / 3.34, brain 6.42, brainstem 2.47, eyes 3.01, TRE 6.91, Dice 0.88 / 0.72 / 0.57, failing 124 (mean shape: 4.42 / 3.94, 6.86, 2.86, 3.65, TRE 7.95, Dice 0.87 / 0.68 / 0.51). Skin mean 1.94 mm, HD95 16.1 (smooth skin kept, same for all methods). The five formerly tipped cases (07, 27, 30, 34, 41): chain skull outer 3.94, TRE 8.0, brain Dice 0.87 (skin only 6.78, TRE 12.8).

**Findings.** (1) The fix removes the pose outliers: no head is at 10-15 mm any more except case_37; the mean number of failing elements fell from 1,548 to 358 because the outlier fits were the large ones. (2) The mean shape improved even more (skull 6.4 -> 4.7, TRE 15.0 -> 8.8): with the outliers fixed the C1 fits of all cases are closer, so the gain of the skin-based prediction over the mean shape is now smaller (chain TRE 7.73 against 8.82; skull 4.18 against 4.74; eyes 4.62 against 5.18, brain Dice 0.88 against 0.86). The skin carries information, but not much beyond the mean in this data. (3) Chain and joint are the same within noise. (4) Best cases by the five-structure average: 40 (3.21), 02, 14, 05; two cases are worse than skin only: 07 (4.63 against 4.26) and 37.

**Remaining failure: case_37.** Skin-only TRE 40.8 mm, eyes 72 mm, 460 failing elements; its nose is a normal one (131 mm below the vertex) so the nose window does not change it; its C1 oracle is fine (TRE 5.7) but with 14,080 failing elements. It is a sixth start failure of a different kind (pose or head shape); the chain gives skull about 24 mm average, 9,454 failing elements. Not analysed yet.

**Caveats.** As section 15 (targets are the C1 fits; 39 training cases per fold; one leave-one-out run; settings tuned on case_02). The best/worst pictures and Slicer scenes in `results_40case/` belong to the run before the fix and were not redone. The temporary per-case data stays in `out_tmp_batch` (git-ignored).

## 18. Pictures, scenes and mesh quality of the nose-window run (2026-11-24)

**Pictures and scenes** (`results/40case_nosefix/`): best 1 case_40 (five-structure average 3.21 mm), best 2 case_02 (3.26), worst 1 case_37 (23.9; the template sits about 40 deg out of place, the skin-only start fails), worst 2 case_34 (4.94); PNG per case (skin only, prediction, C1 oracle; blue = GT, orange = result) and `slicer_scenes/*.mrb` (about 24 MB each, not committed; same layout and colours as section 15; best1 reloaded and checked). The scenes in `results_40case/` are from the run before the fix.

**Mesh quality of the predicted (chain) meshes** (`mesh_quality_chain.csv`; 176,441 solids; failing = a corner scaled Jacobian <= 0): the template has 4 failing and 1,076 elements below 0.2. Predicted meshes: 0 of 40 have no failing element; 6 have 10 or fewer, 25 have 100 or fewer, one (case_37) has more than 1,000 (9,454). Median 66 (0.04 % of the elements), mean 358; elements below 0.2 median 3,113 (template 1,076); 34 % of the failing elements touch a skin node. The template itself contains zero-length edges, so no time-step ratio was computed.

**Simulation ready? No.** Not yet checked or done: element inversion has to be zero (or at the template's 4), no contact or penetration check between parts, no export to a `.k` file with the original materials, sections and boundary conditions, no LS-DYNA run to normal termination.
