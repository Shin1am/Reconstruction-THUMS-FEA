from pathlib import Path
import os,json,argparse
parser=argparse.ArgumentParser();parser.add_argument("--view",default="front",choices=["front","oblique_left","oblique_right"]);args=parser.parse_args()
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import numpy as np,pyvista as pv
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=r/'synthetic_case02/sam_body'
if args.view != 'front': base=base/args.view
out=base/'validation';out.mkdir(exist_ok=True)
m=pv.read(base/'body_0.ply')
# Provisional horizontal cut above shoulders in raw camera-coordinate mesh.
front=pv.read(r/'synthetic_case02/sam_body/body_0.ply')
assert np.array_equal(m.faces,front.faces), 'Topology mismatch'
m['reference_y']=front.points[:,1]
head=m.clip_scalar(scalars='reference_y',value=-1.49,invert=True).triangulate()
head.save(out/'head_raw.ply')
# Raw camera: x right, y down, z away. Proper conversion to LPS-oriented frame.
R=np.diag([1.,-1.,-1.]);R=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
yaw={'front':0,'oblique_left':35,'oblique_right':-35}[args.view]
R=Rotation.from_euler('z',yaw,degrees=True).as_matrix()@R
a=np.asarray(head.points)@R.T*1000
ct=pv.read(r/'synthetic_case02/CT_skin_ground_truth.vtp').triangulate();b=np.asarray(ct.points)
# Metrics remain provisional: cut is geometric, no paired anatomical landmarks.
def fit(x,y,scaling=False):
 xc=x-x.mean(0);yc=y-y.mean(0);u,s,vt=np.linalg.svd(xc.T@yc);d=np.eye(3);d[-1,-1]=np.sign(np.linalg.det(u@vt));rot=u@d@vt
 scale=np.sum(s*np.diag(d))/np.sum(xc*xc) if scaling else 1.
 return scale,rot,y.mean(0)-scale*x.mean(0)@rot
results={};tree=cKDTree(b)
for mode in ['rigid_assuming_meters','similarity']:
 x=a.copy();T=np.eye(4);T[:3,:3]=1000*R
 shift=b.mean(0)-x.mean(0);x+=shift;T[:3,3]=shift
 if mode=='similarity':
  s=np.ptp(b[:,2])/np.ptp(x[:,2]);c=x.mean(0);x=(x-c)*s+c;T[:3,:3]*=s;T[:3,3]=s*T[:3,3]+(1-s)*c
 for it in range(80):
  _,idx=tree.query(x);s,rot,t=fit(x,b[idx],mode=='similarity');x=s*x@rot+t;step=np.eye(4);step[:3,:3]=s*rot.T;step[:3,3]=t;T=step@T
 h=head.copy();h.points=x;h.save(out/(mode+'.vtp'))
 # unsigned closest triangle distances using VTK locator via PyVista
 _,near=ct.find_closest_cell(x,return_closest_point=True);d=np.linalg.norm(x-near,axis=1)
 _,near=h.find_closest_cell(b,return_closest_point=True);rev=np.linalg.norm(b-near,axis=1)
 h['error_mm']=d;h.save(out/(mode+'_heatmap.vtp'))
 results[mode]=dict(mean_symmetric_mm=float((d.mean()+rev.mean())/2),rmse_symmetric_mm=float(np.sqrt(((d*d).mean()+(rev*rev).mean())/2)),chamfer_L1_sum_mm=float(d.mean()+rev.mean()),hd95_mm=float(max(np.percentile(d,95),np.percentile(rev,95))),uniform_scale_relative_to_assumed_meters=float(np.cbrt(np.linalg.det(T[:3,:3]))/1000),transform_raw_to_CT=T.tolist())
 f,axs=plt.subplots(1,2,figsize=(11,6),layout='constrained')
 for ax,(i,j,title) in zip(axs,[(0,2,'Front'),(1,2,'Side')]):
  ax.scatter(b[:,i],b[:,j],s=.4,c='lightgray');sc=ax.scatter(x[:,i],x[:,j],s=3,c=d,cmap='turbo',vmin=0,vmax=25);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[i]+' mm');ax.set_ylabel('XYZ'[j]+' mm')
 f.colorbar(sc,ax=axs,label='SAM head to CT triangle distance, mm');f.suptitle(mode+' — provisional crop and alignment');f.savefig(out/(mode+'.png'),dpi=130);plt.close(f)
results['limitations']=['Synthetic CT-rendered input; not independent photograph validation','Head cut y<-1.49 in raw coordinates is provisional and not matched anatomical ROI','Units assumed meters for rigid baseline, not independently calibrated','Vertex-weighted point-to-triangle distances; not area-weighted','No anatomical landmarks; ICP local optimum and coordinate direction require visual review','No nonrigid deformation applied']
(out/'metrics.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
