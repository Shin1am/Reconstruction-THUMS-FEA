# MaiAlgo — progress log

Running log for the algorithm work done with Claude. Newest entries go at the bottom. Frozen baselines (Day1, Day2) and the Day3 run are left as they are; new work goes in this folder.

Last updated: 2026-10-29 (section 8)

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
