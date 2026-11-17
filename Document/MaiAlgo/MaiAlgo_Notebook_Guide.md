# MaiAlgo notebook guide

Notebook: `Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb` (rewritten 2026-10-30; the original v2 notebook is untouched in `CPD_TPS_Skin_Only_Pipeline_v2.ipynb`). Run the cells top to bottom; every cell is one step. All explanations live here, the notebook keeps only short titles.

Results and findings are in `MaiAlgo_Progress.md`. Run outputs go to `Document/MaiAlgo/out_<CASE>_<NAME>/` (git-ignored).

## Cells

| # | Cell | What it does |
|---|---|---|
| 0 | Config | Imports and all switches (see below). Data root is `G:/My Drive/BioDat_Yusuke_lab` (env var `BIODAT_ROOT` overrides). Subject = HaN-Seg `GT/usable/<CASE>/stl/<CASE>_*.stl` (LPS mm). |
| 1 | Template | Reads `Head_V6.vtu` / `Head_V6.k`, finds the outer-skin parts (PIDs 88000160-88000240 with `_out_` in the name), extracts the skin surface, applies the axis map THUMS (X=ant, Y=left, Z=up) to LPS-like, computes the template eye centroid (PIDs 88000173-88000216). |
| 2 | Subject | Loads the subject skin and eye surfaces, crops the neck/shoulders, samples 3,000 points. |
| 3 | Start + landmarks | Centres both clouds (on their centroids or on the eye centroids), farthest-point-samples 2,000 landmarks per cloud. |
| 4 | CPD | Rigid, affine (singular values clamped to 0.8-1.25), deformable CPD (alpha = beta = 2) with outlier weight `CPD_W`. |
| 5 | TPS, ICP, blend | TPS through the CPD landmarks onto the dense template skin, optional non-rigid ICP (10 iterations, 15 mm, step 0.5), coverage-damped blend back to the unwarped skin where ICP did not help. |
| 6 | Skin check + write | Skin distance table per stage, then one TPS through the final skin moves all nodes; the outer-skin nodes are overwritten by their own final positions. Saves `Head_V6_registered.vtu`, `coords_*.npy`, `run_meta.json`, `validation_summary.csv`. Also saves two controls in the same frame: `coords_init` (axis map only) and `coords_similarity` (rigid CPD with scale only). |
| 7 | Interior vs GT | Samples 150k area-weighted points on each THUMS structure and compares it with the GT surface (symmetric mean distance, HD95, centroid offset, z-extent ratio). Structures: outer and inner skull table, brain (cerebrum + cerebellum, without the stem), brainstem, eyes. |
| 8 | Jacobians | Scaled Jacobian at each hex corner (collapsed corners skipped). An element fails when its smallest corner is <= 0. Reports failing in the template, failing after the warp, newly failing. |
| 9 | ARAP | Replaces the TPS interior by an As-Rigid-As-Possible solve on the element edge graph; then repeats cells 7 and 8 on `out_<CASE>_<NAME>_arap`. |
| 10 | Results table | Collects every `out_<CASE>_*` folder into one table and writes `results_<CASE>.csv`. |

## Config switches

| Name | Values | Meaning |
|---|---|---|
| `CASE` | `case_01` ... `case_42` | Usable HaN-Seg case. |
| `NAME` | any string | Output folder suffix. Use `baseline` for the reference run of a case. |
| `INIT` | `centroid` / `skinlm` / `eyes` | Start alignment. `centroid` centres both clouds on their centroids. `skinlm` anchors on the midpoint of two skin-only landmarks (vertex = highest point, nose tip = most anterior point). `eyes` anchors on the eye centroids and uses GT eyes, so it is **not** C2-strict. |
| `CROP` | `nose` / `vertex` / `auto` / `eyes` | Subject crop. `nose` (default) cuts the subject the same distance below the nose tip as the template skin ends below its own nose tip (skin-only analogue of the eye crop). `vertex` cuts both clouds at the same height below the vertex (near no-op: both heads span about 250 mm). `auto` raises the cut until the half-width is <= 110 mm. `eyes` uses GT eyes (not C2-strict). |
| `CPD_W` | 0 ... 1 | CPD outlier weight. 0 = baseline. 0.2 collapses the template on most cases (see progress log section 8). |
| `USE_ICP` | bool | Stage 5 ICP on or off. |
| `ARAP_ITERS`, `ARAP_PROX` | int, float | Local-global iterations; proximal term (Tikhonov) pulling free nodes towards the previous iterate. |

Run presets: baseline = `INIT='centroid', CROP='auto'`; run C = `INIT='eyes', CROP='eyes'` (uses GT eyes); run D = run C with `CPD_W=0.2`; **G2 (C2-strict, skin only) = `INIT='skinlm', CROP='nose'`**; G1 = `INIT='centroid', CROP='nose'`. The same switches can be set from environment variables (`MAI_CASE`, `MAI_NAME`, `MAI_INIT`, `MAI_CROP`, `MAI_W`, `MAI_ICP`, `MAI_ARAP`) for batch runs.

## ARAP details

- Boundary: the run's final outer-skin positions are fixed.
- Rest shape: the template after one global affine fit to the skin (ARAP is isometric and cannot rescale).
- Graph: unique edges of the hex (12) and shell quad (4) elements; collapsed hexes give self edges that are dropped. Weight = 1 / rest edge length.
- Local step: closest rotation per node by SVD of the edge covariance; global step: sparse Laplacian solve, factorised once.
- Nodes in a graph component with no skin node (the 4,886 eye nodes) cannot be driven and keep the run's coordinates.
- Boundary variants (`ARAP_CONFIGS`, tag -> (alpha, smooth_k, smooth_iters)): `''` keeps the run's skin; `_a05` shrinks the ICP/blend residual to 0.5 toward the TPS skin; `_sm` smooths the skin displacement (relative to the affine rest shape) over its 30 nearest skin neighbours, 3 times. The sparse factorisation is shared by all variants, so each extra variant costs one solve. Output folders: `out_<case>_<name>_arap`, `_arap_a05`, `_arap_sm`. The skin numbers of these folders are recomputed from the actual boundary used.
- Not implemented yet: robust (Welsch / Geman-McClure) boundary loss, soft skin constraints.

## Notes

- `run_exp.py`, `eval_exp.py`, `jacobian_diagnostic.py`, `aggregate.py`, `run_all.sh` in this folder are the earlier script versions of the same steps (used for the batch runs in the progress log). The notebook reproduces them.
- Python: venv `C:\Users\Acer\AppData\Local\Temp\rv` (numpy, scipy, pandas, pyvista, pycpd 2.5.4).
- One full pass of cells 0-9 takes roughly 10 minutes (deformable CPD about 100 s, ARAP about 5 min).

## Cells 11-12: C1 engine

| # | Cell | What it does |
|---|---|---|
| 11 | Engine | `STRUCT_IDX` maps each structure (skin, skull outer/inner, brain, brainstem, eyes) to its template surface nodes; `GT_ALL` holds the subject GT points. `smooth_skin(coords)` smooths the skin displacement (relative to the template after one affine fit) over its 30 nearest skin nodes, 3 passes, the same recipe as the ARAP `_sm` boundary, and then rebuilds the whole interior of the start from that smooth skin (one TPS through it) so the skin layer is not stretched between a smoothed skin and an interior that followed the unsmoothed one. `register(targets, start, lambdas, n_ctrl)` runs a TPS non-rigid ICP with one data term per structure in `targets`: nearest-GT pull plus reverse GT-to-node pull (25 mm clip), each pull averaged over 20 neighbours, `n_ctrl` control nodes per structure, smoothing `lam * n_ctrl / n_used` so every structure has equal total weight. Brainstem and eyes are not pulled by nearest points (that squashes them); each is pulled to its own affine fit (`fit_affine`: trimmed bidirectional ICP, scale clamped to 0.8-1.25; the two eyes are fitted separately). The GT brain surface contains the brainstem while the template brain does not, so the brain term ignores everything within `STEM_EXCL` = 25 mm of the brainstem. `lambdas` goes stiff to flexible; the last value is the stiffness floor. |
| 12 | Run C1 | The skin of `coords_reg` is smoothed (`smooth_skin`) and then held fixed: the skin is already fitted, the engine moves the interior only. Runs `c1_stiff` (floor 1e3, valid mesh) and `c1_mid` (floors 1e3, 1e2, more accurate, more failing solids), saves each as `out_<CASE>_<NAME>_<tag>`, scores interior vs GT and failing solids, writes `results_c1_<CASE>.csv`. `MAI_LADDER=1` adds `l_skin` (smooth skin + TPS interior, nothing else observed) and `l_skin_skull` (skin + both skull tables observed). C2 = `l_skin`, C1 = `c1_stiff` / `c1_mid`. |

Run cells 0-8 first (they define `coords_reg`, `STRUCT`, `GT_PTS`, `save_run`, `eval_interior`, `jacobian_check`). The ARAP cell (9) is not needed for C1. Env vars for a batch run: `MAI_CASE`, `MAI_NAME`, `MAI_INIT=skinlm`, `MAI_CROP=nose`, `MAI_ARAP=0`, `MAI_LADDER`. Tried and dropped: edge-graph diffusion of the whole displacement field (worse accuracy and more failing solids, see progress log 14.4).
