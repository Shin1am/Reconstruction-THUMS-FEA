# MaiAlgo — progress log

Running log for the algorithm work done with Claude. Newest entries go at the bottom. Frozen baselines (Day1, Day2) and the Day3 run are left as they are; new work goes in this folder.

Last updated: 2026-10-30 (section 11)

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
