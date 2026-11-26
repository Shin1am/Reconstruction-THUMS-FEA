from pathlib import Path
import os,json
root=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(root/'.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd,pyvista as pv
from scipy.spatial import cKDTree
out=root/'alignment_case02';out.mkdir(exist_ok=True)
base=root/'project/Data'
m=pv.read(base/'outputs/cpd_tps_case02_head_neck_rerun/Head_V6_skin_registered_fixed.vtu')
t=pv.read(base/'mesh_model/Head_V6.vtu')
pids=[88000221,88000222,88000223,88000229,88000230,88000231]
def skin(mesh):
 return mesh.extract_cells(np.flatnonzero(np.isin(mesh.cell_data['part_id'],pids))).extract_surface(algorithm='dataset_surface').triangulate()
s=skin(m); original=skin(t)
ct=pv.read(base/'HaN-Seg/GT/usable/case_02/stl/case_02_skin_head_neck.stl')
a=np.asarray(s.points);b=np.asarray(ct.points)
da=cKDTree(b).query(a)[0];db=cKDTree(a).query(b)[0]
s.point_data['nearest_CT_vertex_mm']=da;ct.point_data['nearest_FE_vertex_mm']=db
s.save(out/'FE_skin_error.vtp');ct.save(out/'CT_skin_error.vtp')
# Original oblique head-only cut is used solely to label upper-neck ROI.
def head(p):return p[:,2]>=-912+.28*(p[:,1]+20)
rows=[]
for name,ma,mb in [('all',np.ones(len(a),bool),np.ones(len(b),bool)),('head',head(a),head(b)),('upper_neck',~head(a),~head(b))]:
 x,y=da[ma],db[mb]
 rows.append(dict(region=name,n_FE=len(x),n_CT=len(y),FE_to_CT_mean_mm=x.mean() if len(x) else None,FE_to_CT_RMSE_mm=np.sqrt(np.mean(x*x)) if len(x) else None,CT_to_FE_mean_mm=y.mean() if len(y) else None,HD95_mm=max(np.percentile(x,95),np.percentile(y,95)) if len(x) and len(y) else None))
pd.DataFrame(rows).to_csv(out/'regional_metrics.csv',index=False)
views=[(0,2,'Front: X-Z'),(1,2,'Side: Y-Z'),(0,1,'Top: X-Y')]
f,axs=plt.subplots(2,3,figsize=(16,11),layout='constrained')
for col,(i,j,title) in enumerate(views):
 ax=axs[0,col];ax.scatter(b[:,i],b[:,j],s=.6,c='#e16c62',alpha=.3,label='CT skin');ax.scatter(a[:,i],a[:,j],s=1,c='#137aab',alpha=.5,label='Exported FE skin');ax.legend(markerscale=5);ax.set_title(title)
 ax=axs[1,col];sc=ax.scatter(a[:,i],a[:,j],c=da,s=3,cmap='turbo',vmin=0,vmax=40);ax.set_title('FE to CT nearest-vertex error')
 for ax in axs[:,col]:ax.set_aspect('equal');ax.set_xlabel('XYZ'[i]+' (LPS mm)');ax.set_ylabel('XYZ'[j]+' (LPS mm)')
f.colorbar(sc,ax=axs[1,:],label='Distance (mm); values above 40 clipped in color only');f.savefig(out/'overlay_heatmap.png',dpi=150);plt.close(f)
f,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for ax,(i,j,title) in zip(axs,views):
 sc=ax.scatter(b[:,i],b[:,j],c=db,s=1,cmap='turbo',vmin=0,vmax=40);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[i]+' (LPS mm)');ax.set_ylabel('XYZ'[j]+' (LPS mm)')
f.colorbar(sc,ax=axs,label='CT to FE nearest-vertex distance (mm)');f.savefig(out/'reverse_heatmap.png',dpi=150);plt.close(f)
# Audit seed availability and actual PCA rotation recorded in the executed run.
n=json.loads((root/'CPD_TPS_HaNSeg_case02_head_neck_rerun_executed.ipynb').read_text())
log='\n'.join(''.join(o.get('text',[])) for c in n['cells'] for o in c.get('outputs',[]) if o.get('output_type')=='stream')
(out/'executed_output.txt').write_text(log)
audit={'template_bounds':np.array(original.bounds).tolist(),'CT_bounds_LPS_mm':np.array(ct.bounds).tolist(),'FE_bounds_LPS_mm':np.array(s.bounds).tolist(),'matched_landmarks_available':(base/'landmarks_matched/template_landmarks_matched.npy').exists() and (base/'landmarks_matched/subject_landmarks_matched.npy').exists(),'note':'PCA and nearest-surface error cannot prove anatomical correspondence or left/right identity. No anatomical landmarks have been fabricated. Regions follow the old oblique crop; not anatomical segmentation. Metrics are vertex-sampled, bidirectional whole-surface nearest-neighbor distances grouped by source ROI.'}
(out/'alignment_audit.json').write_text(json.dumps(audit,indent=2))
print(pd.DataFrame(rows).to_string(index=False))
print(json.dumps(audit,indent=2))
