from pathlib import Path
import os
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np,pyvista as pv,json
from scipy.spatial import cKDTree
z=np.load(r/'alignment_case02/stage_cache.npz');ct=z['target']+z['c_fixed'];paths=['cpd_tps_case02_floating_fix','cpd_tps_case02_oriented'];f,axs=plt.subplots(2,2,figsize=(12,11),layout='constrained');rows=[]
for col,path in enumerate(paths):
 m=pv.read(r/'project/Data/outputs'/path/'Head_V6_skin_registered_fixed.vtu');s=m.extract_cells(np.flatnonzero(np.isin(m.cell_data['part_id'],[88000221,88000222,88000223,88000229,88000230,88000231]))).extract_surface(algorithm='dataset_surface').triangulate();p=s.points;faces=s.faces.reshape(-1,4)[:,1:];e=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);# display right lateral half to reduce projection overlap
 visible=np.ones(len(e), dtype=bool);seg=p[e[visible]][:,:,[1,2]]
 ax=axs[0,col];ax.scatter(ct[:,1],ct[:,2],s=.4,color='#cccccc',alpha=.3);ax.add_collection(LineCollection(seg,colors='#126b93',linewidths=.22,alpha=.65));ax.autoscale();ax.set_title(['Before: one-way refinement','After: corrected orientation + bidirectional fit'][col])
 d=cKDTree(p).query(ct)[0];ax=axs[1,col];sc=ax.scatter(ct[:,1],ct[:,2],c=d,s=1.5,cmap='turbo',vmin=0,vmax=25);ax.set_title('CT to FE coverage error')
 for ax in axs[:,col]:ax.set_aspect('equal');ax.set_xlabel('Y (LPS mm)');ax.set_ylabel('Z (LPS mm)')
 mask=ct[:,1]>130;rows.append(dict(method=path,posterior_mean=float(d[mask].mean()),posterior_p95=float(np.percentile(d[mask],95)),posterior_percent_within_5mm=float(100*np.mean(d[mask]<5))))
f.colorbar(sc,ax=axs[1,:],label='CT to FE nearest-vertex distance (mm)');f.savefig(r/'alignment_case02/oriented_before_after.png',dpi=150);(r/'alignment_case02/oriented_coverage_metrics.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
