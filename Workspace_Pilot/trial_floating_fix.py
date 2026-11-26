from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
from scipy.interpolate import RBFInterpolator
r=Path(__file__).resolve().parent;z=np.load(r/'alignment_case02/stage_cache.npz');src=z['src'];target=z['target'];pts=z['nm_surf_warped_cs'].copy();tree=cKDTree(target)
for gate in np.linspace(40,15,40):
 d,nn=tree.query(pts);valid=d<gate;pull=target[nn]-pts;pull[~valid]=0
 ids=cKDTree(pts).query(pts,k=9)[1];pull=pull[ids].mean(1);pull[~valid]=0
 step=.5*pull;step*=np.minimum(1.,1.0/np.maximum(np.linalg.norm(step,axis=1),1e-12))[:,None];pts+=step
# No confidence fallback to unregistered PCA geometry: use refined correspondence.
n=1000;idx=np.empty(n,int);idx[0]=np.random.default_rng(0).integers(len(src));dist=np.linalg.norm(src-src[idx[0]],axis=1)
for k in range(1,n):idx[k]=np.argmax(dist);dist=np.minimum(dist,np.linalg.norm(src-src[idx[k]],axis=1))
f=RBFInterpolator(src[idx],pts[idx],kernel='thin_plate_spline',smoothing=1e-3);skin=f(src)
d=tree.query(skin)[0];rev=cKDTree(skin).query(target)[0];w=skin+z['c_fixed'];print(dict(mean=d.mean(),rms=np.sqrt(np.mean(d*d)),hd95=max(np.percentile(d,95),np.percentile(rev,95)),floating=int(((w[:,1]>190)&(w[:,2]>-800)).sum())))
np.savez(r/'alignment_case02/fix_trial.npz',refined=pts,skin=skin,control_idx=idx)
