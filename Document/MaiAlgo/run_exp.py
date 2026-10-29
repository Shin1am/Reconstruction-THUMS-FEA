"""Day 3 / step 1 -- run the UNCHANGED frozen baseline (CPD + TPS skin-driven) on a real subject (HaN-Seg GT).

The registration stages are copied verbatim from
Document/Day1_Baseline/frozen/CPD_TPS_Skin_Only_Pipeline_v2.ipynb.
Only the I/O plumbing differs:
  mode=legacy : original fallback subject + 10 matched landmarks (reproduction check of Day 1)
  mode=case   : subject = GT/usable/<case>/stl/<case>_skin_surface.stl (LPS mm)
                - Stage 0.5b Kabsch seed (10 hand-picked landmark pairs, not available for this subject)
                  is replaced by a fixed axis-convention rotation THUMS(X=ant,Y=left,Z=up) -> LPS-like(x=left,y=-ant,z=up)
                - NECK_Z_CUTOFF (subject shoulders) is replaced by an automatic shoulder crop
MaiAlgo experiment runner (copy of Day3 run_case.py with switchable options; Day3 files are untouched).
Usage: python run_exp.py <case_id> <exp_name> [--w 0.2] [--no-icp] [--init eyes] [--crop eyes]
"""
import argparse
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfg import DATA_ROOT
import pyvista as pv
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from pycpd import AffineRegistration, DeformableRegistration, RigidRegistration

ap = argparse.ArgumentParser()
ap.add_argument('case')
ap.add_argument('name')
ap.add_argument('--w', type=float, default=0.0, help='CPD outlier weight (all three CPD stages)')
ap.add_argument('--no-icp', action='store_true', help='skip Stage 6 ICP (blend then runs on the TPS result)')
ap.add_argument('--init', choices=['centroid', 'eyes'], default='centroid')
ap.add_argument('--crop', choices=['auto', 'eyes'], default='auto')
A = ap.parse_args()
MODE, CASE = 'case', A.case
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, f'out_{CASE}_{A.name}')
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DIR = DATA_ROOT
TEMPLATE_K = os.path.join(BASE_DIR, 'Data/Ls_dyna_model/Head_V6.k')
TEMPLATE_VTU = os.path.join(BASE_DIR, 'Data/mesh_model/Head_V6.vtu')
FALLBACK_SUBJECT_FILE = os.path.join(BASE_DIR, 'Data/mesh_model/ImageToStl.com_head_voxels_transform_2.vtu')
N_FALLBACK_SAMPLES = 3000
NECK_Z_CUTOFF = 515.0
TEMPLATE_MATCHED_LANDMARKS_PATH = os.path.join(BASE_DIR, 'Data/landmarks_matched/template_landmarks_matched.npy')
SUBJECT_MATCHED_LANDMARKS_PATH = os.path.join(BASE_DIR, 'Data/landmarks_matched/subject_landmarks_matched.npy')
GT_DIR = os.path.join(BASE_DIR, 'Data/HaN-Seg/GT/usable', CASE, 'stl')

SKIN_PID_MIN, SKIN_PID_MAX = 88000160, 88000240
N_LANDMARKS_FIXED = 2000
N_LANDMARKS_MOVING = 2000
CPD_ALPHA, CPD_BETA, CPD_MAX_ITER, CPD_TOL = 2.0, 2.0, 100, 1e-6
TPS_SMOOTHING = 1e-3
ICP_ITERS, ICP_MAX_CORR_DIST_MM, ICP_STEP, ICP_SMOOTH_NEIGHBORS = 10, 15.0, 0.5, 8
AFFINE_SINGULAR_VALUE_CLAMP = (0.8, 1.25)
BLEND_TRANSITION_MM, CONF_SMOOTH_NEIGHBORS, CONF_SMOOTH_ITERS = 10.0, 8, 3

# THUMS (X=anterior, Y=left, Z=up)  ->  subject LPS (x=left, y=posterior, z=up): proper rotation, det=+1
AXIS_MAP = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], float)

np.random.seed(0)
timings = {}
t_all = time.time()


def tick(name, t0):
    timings[name] = round(time.time() - t0, 2)
    print(f'[{name}] {timings[name]}s', flush=True)


# ---------------------------------------------------------------- template (verbatim from Cell 6)
def parse_part_names(k_path):
    names = {}
    with open(k_path, errors='ignore') as f:
        for line in f:
            if line.startswith('$HMNAME COMPS'):
                m = re.match(r'\$HMNAME COMPS\s*(\d+)(.*)', line.strip())
                if m:
                    names[int(m.group(1))] = m.group(2).strip()
    return names


t0 = time.time()
PART_NAMES = parse_part_names(TEMPLATE_K)
SKIN_EXTERNAL_PIDS = [pid for pid in range(SKIN_PID_MIN, SKIN_PID_MAX + 1) if '_out_' in PART_NAMES.get(pid, '')]
template_mesh = pv.read(TEMPLATE_VTU)
pids = template_mesh.cell_data['part_id']
skin_cells = np.where(np.isin(pids, SKIN_EXTERNAL_PIDS))[0]
skin_surf = template_mesh.extract_cells(skin_cells).extract_surface(algorithm='dataset_surface').triangulate()
skin_surf_node_ids = np.asarray(skin_surf.point_data['node_id'])
skin_surf_pts0 = np.asarray(skin_surf.points, dtype=np.float64)
all_node_ids = np.asarray(template_mesh.point_data['node_id'])
all_pts0 = np.asarray(template_mesh.points, dtype=np.float64)
print(f'Template: {template_mesh.n_points:,} pts; skin PIDs {SKIN_EXTERNAL_PIDS}; skin surface {skin_surf.n_points:,} pts')
tick('load_template', t0)

# ---------------------------------------------------------------- subject
t0 = time.time()
if MODE == 'legacy':
    fb_pts = np.asarray(pv.read(FALLBACK_SUBJECT_FILE).points, dtype=np.float64)
    fb_pts = fb_pts[fb_pts[:, 2] >= NECK_Z_CUTOFF]
    idx = np.random.choice(len(fb_pts), min(N_FALLBACK_SAMPLES, len(fb_pts)), replace=False)
    subject_pts = fb_pts[idx]
else:
    fb_pts = np.asarray(pv.read(os.path.join(GT_DIR, f'{CASE}_skin_surface.stl')).points, dtype=np.float64)
    gt_eyes_c = np.asarray(pv.read(os.path.join(GT_DIR, f'{CASE}_eyes_OAR.stl')).points, dtype=np.float64).mean(0)
    n0 = len(fb_pts)
    if A.crop == 'eyes':
        # same window below the eye line as the template skin (template skin bottom is D mm under its eyes)
        _eyes_t = np.unique(np.where(np.isin(pids, list(range(88000173, 88000217))))[0])
        _ec = template_mesh.extract_cells(_eyes_t)
        t_eye_z = (np.asarray(_ec.points) @ AXIS_MAP.T)[:, 2].mean()
        D = t_eye_z - (skin_surf_pts0 @ AXIS_MAP.T)[:, 2].min()
        z_cut = gt_eyes_c[2] - D
        print(f'eye-matched crop: template skin bottom is {D:.1f} mm below eyes -> subject z >= {z_cut:.1f}')
    else:
        # shoulder crop: raise the cut until the remaining head+neck is no wider than 110 mm half-width
        zs = np.sort(np.unique(np.round(fb_pts[:, 2], 0)))
        for z_cut in zs:
            keep = fb_pts[fb_pts[:, 2] >= z_cut]
            if np.abs(keep[:, 0] - np.median(keep[:, 0])).max() <= 110.0:
                break
    fb_pts = fb_pts[fb_pts[:, 2] >= z_cut]
    print(f'Subject skin STL: {n0:,} pts -> shoulder crop z >= {z_cut:.0f}: {len(fb_pts):,} pts')
    idx = np.random.choice(len(fb_pts), min(N_FALLBACK_SAMPLES, len(fb_pts)), replace=False)
    subject_pts = fb_pts[idx]
    skin_surf_pts0 = skin_surf_pts0 @ AXIS_MAP.T
    all_pts0 = all_pts0 @ AXIS_MAP.T
print(f'Subject point set: {subject_pts.shape}')
tick('load_subject', t0)

# ---------------------------------------------------------------- Stage 0 (verbatim Cell 10)
def center_only(fixed_pts, moving_pts):
    c_fixed = fixed_pts.mean(0)
    c_moving = moving_pts.mean(0)
    scale = 1.0
    return fixed_pts - c_fixed, (moving_pts - c_moving) * scale, dict(c_fixed=c_fixed, c_moving=c_moving, scale=scale)


t0 = time.time()
nf_c, nm_surf_cs, norm_params = center_only(subject_pts, skin_surf_pts0)
c_fixed, c_moving, scale = norm_params['c_fixed'], norm_params['c_moving'], norm_params['scale']
if MODE == 'case' and A.init == 'eyes':
    # anchor both clouds on the eye centroids instead of their own centroids (landmark-style seed)
    _eyes_t = np.where(np.isin(pids, list(range(88000173, 88000217))))[0]
    _ec = np.asarray(template_mesh.extract_cells(_eyes_t).points) @ AXIS_MAP.T
    c_moving = _ec.mean(0)
    c_fixed = gt_eyes_c
    nf_c = subject_pts - c_fixed
    nm_surf_cs = (skin_surf_pts0 - c_moving) * scale
    print('init: eye-anchored; centroid offset moved from', norm_params['c_fixed'].round(1), 'to', c_fixed.round(1))
nm_all_cs = (all_pts0 - c_moving) * scale
tick('stage0_center', t0)


# ---------------------------------------------------------------- Stage 0.5b (verbatim Cell 12; legacy only)
def kabsch_rotation(P, Q):
    Pc = P - P.mean(0)
    Qc = Q - Q.mean(0)
    U, S, Vt = np.linalg.svd(Pc.T @ Qc)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T


t0 = time.time()
if MODE == 'legacy':
    tmpl_lm_cs = (np.load(TEMPLATE_MATCHED_LANDMARKS_PATH) - c_moving) * scale
    subj_lm_cs = np.load(SUBJECT_MATCHED_LANDMARKS_PATH) - c_fixed
    R_seed = kabsch_rotation(tmpl_lm_cs, subj_lm_cs)
    nm_surf_cs = nm_surf_cs @ R_seed.T
    nm_all_cs = nm_all_cs @ R_seed.T
landmark_seed_applied = True   # legacy: Kabsch seed; case: axis map (applied before centering)
tick('stage0.5b_seed', t0)


# ---------------------------------------------------------------- Stage 0.5 FPS (verbatim Cell 14)
def farthest_point_sampling(points, n_samples, seed=0):
    rng = np.random.default_rng(seed)
    n = len(points)
    n_samples = min(n_samples, n)
    selected = np.empty(n_samples, dtype=np.int64)
    selected[0] = rng.integers(n)
    dist = np.linalg.norm(points - points[selected[0]], axis=1)
    for k in range(1, n_samples):
        selected[k] = np.argmax(dist)
        dist = np.minimum(dist, np.linalg.norm(points - points[selected[k]], axis=1))
    return selected


t0 = time.time()
fixed_lm = nf_c[farthest_point_sampling(nf_c, N_LANDMARKS_FIXED)]
moving_lm = nm_surf_cs[farthest_point_sampling(nm_surf_cs, N_LANDMARKS_MOVING)]
tick('stage0.5_fps', t0)

# Stage 1 PCA skipped (seed applied) -> identity, as in the baseline
R_pca = np.eye(3)
moving_lm_pca = moving_lm @ R_pca.T
nm_surf_pca = nm_surf_cs @ R_pca.T
nm_all_pca = nm_all_cs @ R_pca.T

# ---------------------------------------------------------------- Stages 2-4 (verbatim Cells 18-22)
t0 = time.time()
rigid_reg = RigidRegistration(X=fixed_lm, Y=moving_lm_pca, w=A.w, max_iterations=CPD_MAX_ITER, tolerance=CPD_TOL)
TY_rigid, (s_r, R_r, t_r) = rigid_reg.register()
print(f'Rigid scale {s_r:.4f}, t {np.round(t_r, 2)}')
tick('stage2_rigid_cpd', t0)

t0 = time.time()
affine_reg = AffineRegistration(X=fixed_lm, Y=TY_rigid, w=A.w, max_iterations=CPD_MAX_ITER, tolerance=CPD_TOL)
_, (B_a, t_a) = affine_reg.register()
U, S, Vt = np.linalg.svd(B_a)
S_clamped = np.clip(S, *AFFINE_SINGULAR_VALUE_CLAMP)
TY_affine = TY_rigid @ (U @ np.diag(S_clamped) @ Vt) + t_a
print(f'Affine SV raw {np.round(S, 3)} -> clamped {np.round(S_clamped, 3)}')
tick('stage3_affine_cpd', t0)

t0 = time.time()
deformable_reg = DeformableRegistration(X=fixed_lm, Y=TY_affine, alpha=CPD_ALPHA, beta=CPD_BETA, w=A.w,
                                        max_iterations=CPD_MAX_ITER, tolerance=CPD_TOL)
TY_cpd, (G, W) = deformable_reg.register()
tick('stage4_deformable_cpd', t0)

# ---------------------------------------------------------------- Stage 5 TPS (verbatim Cell 24)
t0 = time.time()
tps = RBFInterpolator(moving_lm, TY_cpd, kernel='thin_plate_spline', smoothing=TPS_SMOOTHING)
nm_surf_warped_cs = tps(nm_surf_pca)
tick('stage5_tps', t0)


# ---------------------------------------------------------------- Stage 6 ICP (verbatim Cell 27)
def graph_smooth(vectors, points, k=8, iters=1):
    tree = cKDTree(points)
    _, idx = tree.query(points, k=k + 1)
    smoothed = vectors.copy()
    for _ in range(iters):
        smoothed = smoothed[idx].mean(axis=1)
    return smoothed


def nonrigid_icp_refine(source_pts, target_pts, iters, max_corr_dist_mm, step, scale, k_smooth):
    pts = source_pts.copy()
    tree_t = cKDTree(target_pts)
    for it in range(iters):
        d, nn_idx = tree_t.query(pts)
        pull = target_pts[nn_idx] - pts
        valid = (d / scale) < max_corr_dist_mm
        pull[~valid] = 0.0
        pts = pts + step * graph_smooth(pull, pts, k=k_smooth)
    return pts


t0 = time.time()
if A.no_icp:
    nm_surf_icp_cs = nm_surf_warped_cs.copy()
else:
    nm_surf_icp_cs = nonrigid_icp_refine(nm_surf_warped_cs, nf_c, ICP_ITERS, ICP_MAX_CORR_DIST_MM, ICP_STEP, scale,
                                         ICP_SMOOTH_NEIGHBORS)
tick('stage6_icp', t0)


# ---------------------------------------------------------------- Stage 6.5 blend (verbatim Cell 29)
def coverage_damped_blend(original_pts, warped_pts, target_pts, scale, transition_mm=BLEND_TRANSITION_MM,
                          smooth_k=CONF_SMOOTH_NEIGHBORS, smooth_iters=CONF_SMOOTH_ITERS):
    tree_t = cKDTree(target_pts)
    d_orig_mm = tree_t.query(original_pts)[0] / scale
    d_warped_mm = tree_t.query(warped_pts)[0] / scale
    confidence_raw = np.clip((d_orig_mm - d_warped_mm) / transition_mm + 0.5, 0.0, 1.0)
    _, knn_idx = cKDTree(warped_pts).query(warped_pts, k=smooth_k + 1)
    confidence = confidence_raw.copy()
    for _ in range(smooth_iters):
        confidence = confidence[knn_idx].mean(axis=1)
    blended = original_pts + confidence[:, None] * (warped_pts - original_pts)
    return blended, confidence


t0 = time.time()
nm_surf_final_cs, coverage_conf = coverage_damped_blend(nm_surf_pca, nm_surf_icp_cs, nf_c, scale)
print(f'blend: kept {(coverage_conf >= 0.999).sum()}, reverted {(coverage_conf <= 0.001).sum()} / {len(coverage_conf)}')
tick('stage6.5_blend', t0)


# ---------------------------------------------------------------- Stage 7 validation (verbatim Cell 31)
def surface_agreement(source_pts, target_pts, scale):
    d_s2t = cKDTree(target_pts).query(source_pts)[0] / scale
    d_t2s = cKDTree(source_pts).query(target_pts)[0] / scale
    return dict(mean=d_s2t.mean(), median=np.median(d_s2t), rms=np.sqrt((d_s2t ** 2).mean()), max=d_s2t.max(),
                chamfer=d_s2t.mean() + d_t2s.mean(), hausdorff=max(d_s2t.max(), d_t2s.max()))


rows = []
for stage, pts in [('0. Center', moving_lm), ('1. PCA (skipped)', moving_lm_pca), ('2. Rigid CPD', TY_rigid),
                   ('3. Affine CPD', TY_affine), ('4. Non-rigid CPD', TY_cpd),
                   ('5. TPS (dense surface)', nm_surf_warped_cs), ('6. Non-rigid ICP', nm_surf_icp_cs),
                   ('6.5 Confidence blend (final)', nm_surf_final_cs)]:
    rows.append(dict(stage=stage, **surface_agreement(pts, nf_c, scale)))
summary_df = pd.DataFrame(rows).round(3)
print(summary_df.to_string(index=False))
summary_df.to_csv(os.path.join(OUTPUT_DIR, 'validation_summary.csv'), index=False)


# ---------------------------------------------------------------- Stage 5b + write (verbatim Cell 34)
def to_world(pts_cs_pca):
    return ((pts_cs_pca @ np.linalg.inv(R_pca).T) / scale) + c_fixed


t0 = time.time()
tps_final = RBFInterpolator(nm_surf_pca, nm_surf_final_cs, kernel='thin_plate_spline', smoothing=TPS_SMOOTHING)
all_final_cs = tps_final(nm_all_pca)
final_world_coords = to_world(all_final_cs)
skin_world_coords = to_world(nm_surf_final_cs)
updated = {int(n): xyz for n, xyz in zip(all_node_ids, final_world_coords)}
updated.update({int(n): xyz for n, xyz in zip(skin_surf_node_ids, skin_world_coords)})
node_id_to_idx = {int(n): i for i, n in enumerate(template_mesh.point_data['node_id'])}
final_mesh = template_mesh.copy()
new_points = final_mesh.points.copy()
for nid, xyz in updated.items():
    new_points[node_id_to_idx[nid]] = xyz
final_mesh.points = new_points
OUTPUT_VTU = os.path.join(OUTPUT_DIR, 'Head_V6_registered.vtu')
final_mesh.save(OUTPUT_VTU)
print('Wrote', OUTPUT_VTU)
tick('stage5b_write', t0)

# ---------------------------------------------------------------- control meshes (same subject frame) for interior eval
def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    Sc, Dc = src - mu_s, dst - mu_d
    U_, S_, Vt_ = np.linalg.svd(Dc.T @ Sc / len(src))
    d = np.sign(np.linalg.det(U_) * np.linalg.det(Vt_))
    D = np.diag([1, 1, d])
    R = U_ @ D @ Vt_
    s = np.trace(np.diag(S_) @ D) / Sc.var(0).sum()
    t = mu_d - s * R @ mu_s
    return s, R, t


s_u, R_u, t_u = umeyama(moving_lm_pca, TY_rigid)
coords_init = to_world(nm_all_pca)
coords_sim = to_world(s_u * nm_all_pca @ R_u.T + t_u)

meta = dict(mode=MODE, case=CASE, args=vars(A), timings=timings, total_s=round(time.time() - t_all, 1),
            rigid_scale=float(s_r), n_subject_pts=int(len(subject_pts)),
            final=summary_df.iloc[-1].to_dict(), first=summary_df.iloc[0].to_dict())
if MODE == 'case':
    meta['shoulder_crop_z'] = float(z_cut)
json.dump(meta, open(os.path.join(OUTPUT_DIR, 'run_meta.json'), 'w'), indent=1, default=float)
np.save(os.path.join(OUTPUT_DIR, 'coords_init.npy'), coords_init)
np.save(os.path.join(OUTPUT_DIR, 'coords_similarity.npy'), coords_sim)
np.save(os.path.join(OUTPUT_DIR, 'coords_registered.npy'), final_world_coords)
np.save(os.path.join(OUTPUT_DIR, 'subject_pts_sample.npy'), subject_pts)
print('done', meta['total_s'], 's')
