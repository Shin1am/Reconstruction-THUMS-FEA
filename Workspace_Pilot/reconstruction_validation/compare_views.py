from pathlib import Path
import os,json,csv
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np,pyvista as pv
base=r/'synthetic_case02/sam_body';ct=pv.read(r/'synthetic_case02/CT_skin_ground_truth.vtp')
f,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained');rows=[]
for col,view in enumerate(['front','oblique_left','oblique_right']):
 p=base if view=='front' else base/view
 data=json.loads((p/'validation/area_roi/metrics.json').read_text())
 for mode,res in data['results'].items():
  row={'view':view,'mode':mode,'scale':res['uniform_scale_relative_to_assumed_meters']}
  runs=res['cutoffs']['-895']
  for key in runs[0]:
   if key!='seed':row[key]=float(np.mean([run[key] for run in runs]))
  rows.append(row)
 m=pv.read(p/'validation/area_roi/similarity_sam_roi_heatmap.vtp')
 tri=m.points[m.faces.reshape(-1,4)[:,1:]];cent=tri.mean(1)
 _,near=ct.find_closest_cell(cent,return_closest_point=True)
 order=np.argsort(cent[:,0]);ax=axs[0,col]
 coll=PolyCollection(tri[order][:,:,[1,2]],array=np.linalg.norm(cent-near,axis=1)[order],cmap='turbo',clim=(0,25),edgecolors='none')
 ax.add_collection(coll);ax.set_xlim(-55,210);ax.set_ylim(-900,-660);ax.set_aspect('equal');ax.set_title(view);ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)')
 ax=axs[1,col]
 for mesh,color,label in [(ct,'#555555','CT'),(m,'#d24b27','SAM')]:
  cut=mesh.slice(normal=(1,0,0),origin=(0,0,0));conn=cut.lines;i=0;first=True
  while i<len(conn):
   n=conn[i];pts=cut.points[conn[i+1:i+n+1]];ax.plot(pts[:,1],pts[:,2],color=color,label=label if first else None);first=False;i+=n+1
 ax.set_xlim(-55,210);ax.set_ylim(-900,-660);ax.set_aspect('equal');ax.legend();ax.set_title('Sagittal X=0');ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)')
f.colorbar(coll,ax=axs[0].tolist(),label='SAM → CT distance (mm), capped at 25')
f.suptitle('Three independent single-image reconstructions | similarity alignment\nSynthetic CT-rendered pilot; no nonrigid deformation')
f.savefig(base/'three_view_comparison.png',dpi=140)
with (base/'three_view_metrics.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2))
