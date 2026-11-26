import os
from pathlib import Path
os.environ['MPLCONFIGDIR']=str(Path.cwd()/'.mplconfig')
import numpy as np,pyvista as pv,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
m=pv.read('project/Data/outputs/cpd_tps_case02_head_neck_rerun/Head_V6_skin_registered_fixed.vtu')
pids=[88000221,88000222,88000223,88000229,88000230,88000231]
s=m.extract_cells(np.flatnonzero(np.isin(m.cell_data['part_id'],pids))).extract_surface().points
p=np.load('project/Data/HaN-Seg/GT/usable/case_02/case_02_skin_head_neck_LPS_mm.npy')
f,axs=plt.subplots(1,3,figsize=(16,6))
rng=np.random.default_rng(0);p=p[rng.choice(len(p),min(8000,len(p)),False)]
for ax,(i,j,title) in zip(axs,[(0,1,'Top: X-Y'),(0,2,'Front: X-Z'),(1,2,'Side: Y-Z')]):
 ax.scatter(p[:,i],p[:,j],s=2,c='#de5d57',alpha=.35,label='Subject head target')
 ax.scatter(s[:,i],s[:,j],s=2,c='#176ba0',alpha=.45,label='Exported FE skin')
 ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[i]+' (mm)');ax.set_ylabel('XYZ'[j]+' (mm)');ax.legend(markerscale=4)
f.suptitle('Head and upper-neck pilot: actual exported skin vs subject (LPS mm)');f.tight_layout();f.savefig('pilot_case02_head_neck/exported_skin_comparison.png',dpi=140)
