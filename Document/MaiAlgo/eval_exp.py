"""[MaiAlgo copy] Interior check: warped THUMS structures vs HaN-Seg GT surfaces (same LPS frame).
Compares three states of the SAME template: init (axis map + centroid), similarity (rigid CPD incl. scale), registered.
Usage: python eval_interior.py out_dir case_id
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfg import DATA_ROOT
import pyvista as pv
from scipy.spatial import cKDTree

OUT, CASE = sys.argv[1], sys.argv[2]   # OUT = absolute run folder
BASE = DATA_ROOT
GT = os.path.join(BASE, 'Data/HaN-Seg/GT/usable', CASE, 'stl', CASE + '_')

names = {}
for line in open(os.path.join(BASE, 'Data/Ls_dyna_model/Head_V6.k'), errors='ignore'):
    if line.startswith('$HMNAME COMPS'):
        m = re.match(r'\$HMNAME COMPS\s*(\d+)(.*)', line.strip())
        if m:
            names[int(m.group(1))] = m.group(2).strip()

CRANIAL = ('frontal', 'parietal', 'temporal', 'occipital')
ext = [p for p, n in names.items() if '_external_' in n and n.startswith(CRANIAL) and 88000001 <= p <= 88000099]
inn = [p for p, n in names.items() if '_internal_' in n and n.startswith(CRANIAL) and 88000001 <= p <= 88000099]
brain = list(range(88000100, 88000104)) + list(range(88000120, 88000124))   # cerebrum + cerebellum (GT 'brain' excludes the stem)
stem = [88000104, 88000105, 88000124, 88000125]
eyes = list(range(88000173, 88000217))
STRUCT = {  # name: (template pids, gt stl)
    'skull_outer': (ext, 'outer_table_surface'),
    'skull_inner': (inn, 'inner_table_surface'),
    'brain': (brain, 'brain'),
    'brainstem': (stem, 'brainstem_OAR'),
    'eyes': (eyes, 'eyes_OAR'),
}
print({k: len(v[0]) for k, v in STRUCT.items()})

tmpl = pv.read(os.path.join(BASE, 'Data/mesh_model/Head_V6.vtu'))
pid = tmpl.cell_data['part_id']
reg = pv.read(os.path.join(OUT, 'Head_V6_registered.vtu'))
states = {
    'init (axis map only)': np.load(os.path.join(OUT, 'coords_init.npy')),
    'similarity (rigid CPD)': np.load(os.path.join(OUT, 'coords_similarity.npy')),
    'baseline registered': np.asarray(reg.points, dtype=np.float64),
}


def surface_pts(coords, pids):
    m = tmpl.copy()
    m.points = coords
    s = m.extract_cells(np.where(np.isin(pid, pids))[0]).extract_surface(algorithm='dataset_surface').triangulate()
    s = s.clean()
    V = np.asarray(s.points, dtype=np.float64)
    F = np.asarray(s.faces).reshape(-1, 4)[:, 1:]
    A = V[F]
    area = 0.5 * np.linalg.norm(np.cross(A[:, 1] - A[:, 0], A[:, 2] - A[:, 0]), axis=1)
    rng = np.random.default_rng(0)
    n = 150000  # area-weighted samples on the triangles, so vertex spacing is not the error floor
    tri = rng.choice(len(F), n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    S = A[tri, 0] + u[:, None] * (A[tri, 1] - A[tri, 0]) + v[:, None] * (A[tri, 2] - A[tri, 0])
    return np.vstack([V, S])


rows = []
for sname, coords in states.items():
    for k, (pids_, gt_name) in STRUCT.items():
        T = surface_pts(coords, pids_)
        pass
        G = np.asarray(pv.read(GT + gt_name + '.stl').points, dtype=np.float64)
        d_t2g = cKDTree(G).query(T)[0]
        d_g2t = cKDTree(T).query(G)[0]
        rows.append(dict(state=sname, structure=k, mean_T2G=d_t2g.mean(), mean_G2T=d_g2t.mean(),
                         mean_sym=0.5 * (d_t2g.mean() + d_g2t.mean()),
                         hd95=max(np.percentile(d_t2g, 95), np.percentile(d_g2t, 95)),
                         centroid_offset=np.linalg.norm(T.mean(0) - G.mean(0)),
                         extent_ratio_z=np.ptp(T[:, 2]) / np.ptp(G[:, 2])))
df = pd.DataFrame(rows).round(2)
df.to_csv(os.environ.get('EVAL_CSV', os.path.join(OUT, 'interior_vs_gt.csv')), index=False)
print(df.to_string(index=False))
