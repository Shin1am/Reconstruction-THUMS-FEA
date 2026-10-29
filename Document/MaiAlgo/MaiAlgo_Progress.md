# MaiAlgo — progress log

Running log for the algorithm work done with Claude. Newest entries go at the bottom. Frozen baselines (Day1, Day2) and the Day3 run are left as they are; new work goes in this folder.

Last updated: 2026-10-28

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
