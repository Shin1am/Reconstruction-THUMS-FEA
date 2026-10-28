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
