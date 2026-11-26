from pathlib import Path
import numpy as np,pyvista as pv,json
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix,diags
from scipy.interpolate import RBFInterpolator
r=Path(__file__).resolve().parent;z=np.load(r/'alignment_case02/stage_cache.npz');src=z['src'];target=z['target'];pts=z['nm_surf_warped_cs'].copy();ref=pts.copy();n=len(pts)
m=pv.read(r/'project/Data/mesh_model/Head_V6.vtu');s=m.extract_cells(np.flatnonzero(np.isin(m.cell_data['part_id'],[88000221,88000222,88000223,88000229,88000230,88000231]))).extract_surface(algorithm='dataset_surface').triangulate();assert np.array_equal(s['node_id'],z['node_ids'])
f=s.faces.reshape(-1,4)[:,1:];e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);e=np.concatenate([e,e[:,::-1]]);A=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(n,n)).tocsr();A.data[:]=1;A=diags(1/np.maximum(np.asarray(A.sum(1)).ravel(),1))@A
tree=cKDTree(target)
for it in range(100):
 gate=45-25*min(it/80,1);d,nn=tree.query(pts);forward=target[nn]-pts;forward[d>gate]=0
 rd,ri=cKDTree(pts).query(target);valid=rd<gate;counts=np.bincount(ri[valid],minlength=n);rev=np.zeros_like(pts)
 for j in range(3):rev[:,j]=np.bincount(ri[valid],weights=(target[valid,j]-pts[ri[valid],j]),minlength=n)/np.maximum(counts,1)
 pull=.5*forward+.5*rev;pull=.7*pull+.3*(A@pull);pull[d>gate]=0
 # Penalize local changes in displacement on FE edges, rather than joining spatially close unrelated points.
 u=pts-ref;pull+=.15*((A@u)-u)
 delta=.45*pull;delta*=np.minimum(1.,.75/np.maximum(np.linalg.norm(delta,axis=1),1e-12))[:,None];pts+=delta
idx=np.load(r/'alignment_case02/fix_trial.npz')['control_idx'];tps=RBFInterpolator(src[idx],pts[idx],kernel='thin_plate_spline',smoothing=1e-3);skin=tps(src);d=tree.query(skin)[0];rev=cKDTree(skin).query(target)[0];posterior=(target+z['c_fixed'])[:,1]>130
print(json.dumps({'mean':float(d.mean()),'rms':float(np.sqrt(np.mean(d*d))),'hd95':float(max(np.percentile(d,95),np.percentile(rev,95))),'posterior_CT_to_FE_mean':float(rev[posterior].mean()),'posterior_CT_to_FE_p95':float(np.percentile(rev[posterior],95))},indent=2))
np.savez(r/'alignment_case02/coverage_trial.npz',refined=pts,skin=skin)
