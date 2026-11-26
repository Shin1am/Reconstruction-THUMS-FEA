from pathlib import Path
import os,json
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np,pyvista as pv
p=r/'synthetic_case02/sam_body';m=pv.read(p/'body_0.ply');v=np.asarray(m.points);faces=m.faces.reshape(-1,4)[:,1:]
print('vertices',len(v),'triangles',len(faces),'finite',np.isfinite(v).all(),'bounds',m.bounds)
z=np.load(p/'prediction_0.npz');print({k:z[k].shape for k in z.files})
f,axs=plt.subplots(1,3,figsize=(14,8))
for ax,(i,j,k,title) in zip(axs,[(0,1,2,'XY projection'),(2,1,0,'ZY projection'),(0,2,1,'XZ projection')]):
 tri=v[faces];order=np.argsort(tri[:,:,k].mean(1));norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12);shade=.3+.6*np.abs(norm[:,k]);ax.add_collection(PolyCollection(tri[order][:,:,[i,j]],facecolors=plt.cm.Blues(shade[order]),edgecolors='#203040',linewidths=.04));ax.autoscale();ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[i]+' (raw model units)');ax.set_ylabel('XYZ'[j]+' (raw model units)');ax.invert_yaxis() if j==1 else None
f.suptitle('SAM 3D Body: unmodified output from CT-rendered head-only input');f.tight_layout();f.savefig(p/'mesh_inspection.png',dpi=140)
