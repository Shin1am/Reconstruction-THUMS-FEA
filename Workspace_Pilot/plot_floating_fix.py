from pathlib import Path
import os
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pyvista as pv
from scipy.spatial import cKDTree
z=np.load(r/'alignment_case02/stage_cache.npz');ct=z['target']+z['c_fixed'];old=z['final_TPS_500']+z['c_fixed']
m=pv.read(r/'project/Data/outputs/cpd_tps_case02_floating_fix/Head_V6_skin_registered_fixed.vtu');lookup={int(n):i for i,n in enumerate(m['node_id'])};new=np.array([m.points[lookup[int(n)]] for n in z['node_ids']])
f,axs=plt.subplots(2,2,figsize=(12,10),layout='constrained')
for row,(p,name) in enumerate([(old,'Before'),(new,'After: coarse-to-fine ICP')]):
 d=cKDTree(ct).query(p)[0]
 for col,(i,j,title) in enumerate([(1,2,'Side'),(0,2,'Front')]):
  ax=axs[row,col];ax.scatter(ct[:,i],ct[:,j],s=.6,c='#cccccc',alpha=.4);sc=ax.scatter(p[:,i],p[:,j],c=d,s=3,cmap='turbo',vmin=0,vmax=40);ax.set_aspect('equal');ax.set_title(name+' / '+title);ax.set_xlabel('XYZ'[i]+' (LPS mm)');ax.set_ylabel('XYZ'[j]+' (LPS mm)')
f.colorbar(sc,ax=axs,label='FE to CT nearest-vertex distance (mm; color clipped at 40)');f.savefig(r/'alignment_case02/floating_before_after.png',dpi=140)
print('Floating posterior nodes before/after:',int(((old[:,1]>190)&(old[:,2]>-800)).sum()),int(((new[:,1]>190)&(new[:,2]>-800)).sum()))
