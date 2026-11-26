# HaN-Seg case_02 pilot

Completed on 2026-10-29. Run from the workspace with `.venv/bin/python run_case02.py`.
Inputs: project/Data/Ls_dyna_model/Head_V6.k; project/Data/mesh_model/Head_V6.vtu; case_02 LPS-mm skin point cloud.
Template K and VTU have 179676 matching node IDs and identical coordinates.
Pilot settings: 500 CPD points per side, 30 iterations per CPD stage, 500 final TPS controls. No manually matched subject landmarks. PCA initialization. Full supplied target surface including neck/shoulder region; no anatomy validation.

Final exported skin nearest-point mean: 5.277 mm; RMS: 9.759 mm; HD95: 34.890 mm. These are geometric point-set agreement metrics, not internal anatomical accuracy. Early sparse and later dense metrics use different sample sets.
Final TPS fit RMS relative to refined skin: 9.001 mm; the sparse final controls lose detail.
QA flags: baseline 7117 suspect + 4 degenerate; final 17370 suspect + 0 degenerate. Newly flagged IDs: 10711; cleared: 462. QA is approximate per-part signed-volume voting, NOT a full Jacobian check or proof of inversion/solver readiness.

Result is a diagnostic pilot, NOT simulation-ready. Next: restrict corresponding head coverage, establish anatomical orientation/landmark alignment, assess final TPS approximation, then use mesh-aware deformation constraints and internal anatomy evaluation.
