"""Fixed-alignment, shared geometric ROI, area-uniform bidirectional validation."""
from pathlib import Path
import os, json, argparse
parser=argparse.ArgumentParser();parser.add_argument("--view",default="front",choices=["front","oblique_left","oblique_right"]);args=parser.parse_args()
r = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(r / '.mplconfig')
import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
base = r / 'synthetic_case02/sam_body'
if args.view != 'front': base = base / args.view
src = base / 'validation'
out = src / 'area_roi'; out.mkdir(exist_ok=True)
N = 50000

def crop(m, z):
    return m.clip(normal=(0,0,1), origin=(0,0,z), invert=False).triangulate().clean()

def sample(m, seed):
    tri = m.points[m.faces.reshape(-1,4)[:,1:]]
    areas = np.linalg.norm(np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]),axis=1)/2
    rng = np.random.default_rng(seed)
    t = tri[rng.choice(len(tri), N, p=areas/areas.sum())]
    u = np.sqrt(rng.random(N)); v = rng.random(N)
    return (1-u[:,None])*t[:,0] + (u*(1-v))[:,None]*t[:,1] + (u*v)[:,None]*t[:,2]

def distance(points, target):
    _, near = target.find_closest_cell(points, return_closest_point=True)
    return np.linalg.norm(points-near, axis=1)

def metrics(a,b):
    return dict(mean_symmetric_mm=float((a.mean()+b.mean())/2),
        rmse_symmetric_mm=float(np.sqrt(((a*a).mean()+(b*b).mean())/2)),
        chamfer_L1_sum_mm=float(a.mean()+b.mean()),
        hd95_max_directional_mm=float(max(np.percentile(a,95),np.percentile(b,95))),
        sam_to_ct_mean_mm=float(a.mean()), ct_to_sam_mean_mm=float(b.mean()))

ct = pv.read(r/'synthetic_case02/CT_skin_ground_truth.vtp')
prior = json.loads((src/'metrics.json').read_text())
report = {'protocol': {'samples_per_surface': N, 'seeds': [2026,2027],
    'roi': 'Z >= cutoff in CT coordinates; no artificial cap faces',
    'primary_cutoff_mm': -895, 'sensitivity_cutoffs_mm': [-890,-885],
    'alignment': 'Previously saved rigid/similarity transforms frozen; no refit',
    'distance': 'Area-uniform sampled points to exact target triangles, both directions',
    'chamfer_definition': 'Sum of directional mean unsigned distances (mm)',
    'hd95_definition': 'Maximum of directional 95th percentiles (mm)'}, 'results': {},
    'limitations': ['Synthetic CT-rendered input, not independent real-photo validation',
    'Geometric shared ROI excludes lower chin/neck; not landmark-defined full-head anatomy',
    'Fixed original alignment was vertex-based ICP with unmatched original crops',
    'Rigid units assume meters; similarity scale fitted using CT and does not validate absolute size',
    'Monte Carlo surface integration; repeat seeds quantify sampling sensitivity',
    'No nonrigid deformation or mesh densification performed']}
for mode in ['rigid_assuming_meters','similarity']:
    sam = pv.read(src/(mode+'.vtp'))
    report['results'][mode] = {'uniform_scale_relative_to_assumed_meters':prior[mode]['uniform_scale_relative_to_assumed_meters'], 'cutoffs':{}}
    for z in [-895,-890,-885]:
        a,b = crop(sam,z),crop(ct,z)
        assert a.n_cells and b.n_cells
        runs=[]
        for seed in [2026,2027]:
            pa,pb = sample(a,seed),sample(b,seed+100)
            da,db = distance(pa,b),distance(pb,a)
            assert np.isfinite(da).all() and np.isfinite(db).all()
            runs.append({'seed':seed, **metrics(da,db)})
        report['results'][mode]['cutoffs'][str(z)] = runs
        if z != -895: continue
        for mesh,target,name in [(a,b,'sam'),(b,a,'ct')]:
            mesh['distance_mm'] = distance(mesh.points,target)
            mesh.save(out/f'{mode}_{name}_roi_heatmap.vtp')
        fig,axs=plt.subplots(2,2,figsize=(11,10),layout='constrained')
        for row,(mesh,target,label) in enumerate([(a,b,'SAM → CT'),(b,a,'CT → SAM')]):
            tri = mesh.points[mesh.faces.reshape(-1,4)[:,1:]]
            colors = distance(tri.mean(axis=1),target)
            for col,(axes,depth,title) in enumerate([((0,2),1,'Front'),((1,2),0,'Side')]):
                ax=axs[row,col]; order=np.argsort(tri[:,:,depth].mean(axis=1))
                if col == 0: order = order[::-1]  # Anterior is negative CT Y.
                coll=PolyCollection(tri[order][:,:,axes],array=colors[order],cmap='turbo',clim=(0,25),edgecolors='none')
                ax.add_collection(coll); ax.autoscale_view(); ax.set_aspect('equal')
                ax.set_xlabel('XYZ'[axes[0]]+' (mm)');ax.set_ylabel('Z (mm)');ax.set_title(label+' | '+title)
        fig.colorbar(coll,ax=axs.ravel().tolist(),label='Unsigned triangle-centroid distance (mm); saturated at 25')
        fig.suptitle(args.view+' | '+mode+' | shared ROI Z ≥ −895 mm\nSynthetic pilot; frozen alignment; area-uniform metrics')
        fig.savefig(out/(mode+'_heatmap.png'),dpi=150);plt.close(fig)
(out/'metrics.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report['results'],indent=2))
