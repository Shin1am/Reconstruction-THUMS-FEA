# Day 3 — Frozen baseline on a real subject (HaN-Seg GT, case_02)

**Algorithms changed:** none. Registration stages are copied verbatim from `Day1_Baseline/frozen/…v2.ipynb` (`run_case.py`).
**Faithfulness check:** `python run_case.py legacy` on the old fallback subject reproduces Day 1 exactly (mean 3.907 mm, Hausdorff 49.029 mm, 3,299 kept / 71 reverted, rigid scale 1.1503).

## Adaptations (I/O only, needed because the Day 1 inputs do not exist for case_02)
| Baseline | Here |
|---|---|
| 10 hand-picked landmark pairs → Kabsch seed | fixed axis map THUMS (X=ant, Y=left, Z=up) → LPS (x=left, y=−ant, z=up); proper rotation, det +1 |
| `NECK_Z_CUTOFF = 515` | automatic shoulder crop (z ≥ −925 for case_02; removes 4,037 of 40,146 STL points) |
| fallback scan | `GT/usable/case_02/stl/case_02_skin_surface.stl`, 3,000-point random sample (seed 0) |

## Skin fit (same metric as Day 1; template skin → 3,000 subject points)
| Stage | Mean mm | Hausdorff mm |
|---|---:|---:|
| 0 centre | 16.44 | 71.12 |
| 2 rigid CPD | 9.69 | 65.95 |
| 5 TPS | 7.45 | 52.53 |
| 6 ICP | 3.07 | 49.34 |
| 6.5 blend (final) | **3.51** | **52.33** |

Day 1 (self-test): 3.907 / 49.029.

## Interior vs GT (`eval_interior.py`; mm; THUMS surface vs GT STL, both directions)
| Structure | init | similarity only | **baseline registered** | z-extent ratio (reg.) |
|---|---:|---:|---:|---:|
| skull outer | 23.5 | 13.9 | **10.9** (HD95 46) | 1.38 |
| skull inner | 22.4 | 13.4 | **11.8** (HD95 47) | 1.33 |
| brain | 18.7 | 11.9 | **11.7** (HD95 43) | 1.30 |
| eyes | 52.9 | 24.5 | **2.4** (HD95 8) | 1.64 |

## Mesh validity (`jacobian_diagnostic.py`)
Failing solids (any corner Jacobian ≤ 0): template 4 → registered **3,594** (3,590 newly failing; Day 1 self-test: 742).
Control: the similarity-only mesh has 0 newly failing, so the frame change is not the cause.
Worst parts: cerebellum grey matter R/L (725 / 582), head skin L/R (~565 each), occipital R/L (160 / 132), cerebellar CSF.

## Reading
- Skin fit is as good as the self-test, but the interior is barely better than a rigid+scale fit (brain 11.9 → 11.7; skull 13.9 → 10.9), and every interior structure comes out 30–60 % too tall (z-extent ratio). The eyes are the one clear win.
- Failures concentrate at the bottom of the head (cerebellum, occipital), which fits a vertical stretch driven by the neck end of the skin. **Not yet tested:** the neck-cut level is a free parameter in the baseline and is the first suspect.
- GT caveat: cerebrum/cerebellum/dura labels are derived ("approx"); skull, brain and skin are the solid comparisons.

Files: `run_case.py`, `eval_interior.py`, `jacobian_diagnostic.py` (Day 2 copy, ROOT path only), `out_case_case_02/` (mesh, CSVs, `jacobian/`), `out_legacy/` (repro).
Run: Python 3.12 venv with numpy, scipy, pandas, pyvista 0.49, pycpd 2.5.4 (Day 1 used pycpd 2.0.0; the legacy run still matched).
