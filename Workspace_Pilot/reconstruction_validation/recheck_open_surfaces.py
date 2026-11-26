"""Re-score existing CT and SAM open surfaces above shared geometric cut planes."""
from pathlib import Path
import os,json
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import numpy as np,pyvista as pv
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
root=r/'synthetic_case02';base=root/'sam_body/validation'
ct=pv.read(r.parent/'project/Data/HaN-Seg/GT/usable/case_02/stl/case_02_skin_surface.stl').triangulate().clean()
sam=pv.read(base/'similarity.vtp').triangulate().clean()
N=50000;seeds=(2026,2027)
def crop(m,z): return m.clip(normal=(0,0,1),origin=(0,0,z),invert=False).triangulate().clean()
def sample(m,seed):
 tri=m.points[m.faces.reshape(-1,4)[:,1:]];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
 rng=np.random.default_rng(seed);t=tri[rng.choice(len(tri),N,p=area/area.sum())];u=np.sqrt(rng.random(N));v=rng.random(N)
 return (1-u[:,None])*t[:,0]+(u*(1-v))[:,None]*t[:,1]+(u*v)[:,None]*t[:,2]
def metrics(a,b):
 return {'mean_symmetric_mm':float((a.mean()+b.mean())/2),'rmse_symmetric_mm':float(np.sqrt(((a*a).mean()+(b*b).mean())/2)),'chamfer_L1_sum_mm':float(a.mean()+b.mean()),'hd95_max_directional_mm':float(max(np.percentile(a,95),np.percentile(b,95))),'SAM_to_CT_mean_mm':float(a.mean()),'CT_to_SAM_mean_mm':float(b.mean())}
def boundary(m):
 e=m.extract_feature_edges(boundary_edges=True,feature_edges=False,manifold_edges=False,non_manifold_edges=False);return int(e.n_points),list(e.bounds) if e.n_points else None
report={'source':'Original case_02_skin_surface.stl, before neck/head cropping','alignment':'Frozen original similarity transform; no refit','surface_sampling':'Area-uniform Monte Carlo; 50000 samples per surface; two seeds','ROI':'Matched horizontal truncation plane z >= cutoff in LPS mm; no caps included in score','scores':{},'mesh_boundary_vertices':{'source_full_ct':boundary(ct),'full_sam_cut':boundary(sam)},'limitations':['Original CT volume/segmentation mask is absent, so voxel segmentation and extraction cannot be audited','Head/neck cut plane is geometric, not an anatomical neck boundary','Mesh boundary edges remain outside the scoring region; no artificial cap contributes to metrics','SAM surface retains its original open crop boundary','Similarity scale was fit using the CT surface; use rigid scores for scale-free evaluation']}
for z in [-895,-890,-885]:
 c,s=crop(ct,z),crop(sam,z);runs=[]
 for seed in seeds:
  pc,ps=sample(c,seed),sample(s,seed+100);treec=cKDTree(pc);trees=cKDTree(ps);dc=trees.query(pc)[0];ds=treec.query(ps)[0]
  runs.append({'seed':seed,**metrics(ds,dc)})
 report['scores'][str(z)]={'CT_boundary_vertices':boundary(c),'SAM_boundary_vertices':boundary(s),'runs':runs}
# use primary crop -895 for contour overlays and full CT-neck views
c,s=crop(ct,-895),crop(sam,-895)
fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained')
for ax,m,title,color in [(axs[0,0],ct,'Original CT skin surface','#8faabd'),(axs[0,1],sam,'SAM aligned head','#d88a6e'),(axs[0,2],c,'CT scored surface (z ≥ −895)','#8faabd')]:
 v=m.points;tri=v[m.faces.reshape(-1,4)[:,1:]];ax.add_collection(__import__('matplotlib').collections.PolyCollection(tri[:,:,[1,2]],facecolors=color,edgecolors='none',alpha=.85));ax.autoscale();ax.set_aspect('equal');ax.set_xlim(-50,200);ax.set_ylim(-940,-670);ax.set_xlabel('Y LPS (mm)');ax.set_ylabel('Z LPS (mm)');ax.set_title(title)
for ax,z in zip(axs[1],[-895,-850,-800]):
 for m,col,label in [(ct,'#555555','CT original'),(sam,'#187a9c','SAM')]:
  cut=m.slice(normal=(0,0,1),origin=(0,0,z));conn=cut.lines;i=0;first=True
  while i<len(conn):
   n=conn[i];q=cut.points[conn[i+1:i+n+1]];ax.plot(q[:,0],q[:,1],color=col,label=label if first else None);i+=n+1;first=False
 ax.set_aspect('equal');ax.set_xlim(-100,100);ax.set_ylim(-50,200);ax.set_title(f'Cross section Z={z} mm');ax.set_xlabel('X LPS (mm)');ax.set_ylabel('Y LPS (mm)');ax.legend()
fig.suptitle('Open CT and SAM surfaces | no cap faces scored | visual cut-plane audit');out=root/'open_surface_recheck.png';fig.savefig(out,dpi=150)
(base/'open_surface_metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));print(out)
