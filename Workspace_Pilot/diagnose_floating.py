import os,json
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['MPLBACKEND']='Agg';os.environ['MPLCONFIGDIR']=str(root/'.mplconfig');os.environ['HEAD_MODEL_BASE_DIR']=str(root/'project')
import numpy as np
from scipy.spatial import cKDTree
n=json.loads((root/'CPD_TPS_HaNSeg_case02_head_neck_rerun_executed.ipynb').read_text());ns={}
for i,c in enumerate(n['cells']):
 if c['cell_type']!='code' or i>=36:continue
 exec(compile(''.join(c['source']),f'cell{i}','exec'),ns)
 if 'plt' in ns:ns['plt'].close('all')
p=ns['nm_surf_final_cs'];src=ns['nm_surf_pca'];tgt=ns['nf_c'];world=ns['c_fixed']
stages={k:ns[k] for k in ['nm_surf_pca','nm_surf_warped_cs','nm_surf_icp_cs','nm_surf_final_cs']}
from scipy.interpolate import RBFInterpolator
for controls in [500,1000,2000]:
 idx=ns['farthest_point_sampling'](src,controls)
 f=RBFInterpolator(src[idx],p[idx],kernel='thin_plate_spline',smoothing=ns['TPS_SMOOTHING'])
 stages[f'final_TPS_{controls}']=f(src)
np.savez(root/'alignment_case02/stage_cache.npz',**stages,src=src,target=tgt,c_fixed=world,node_ids=ns['skin_surf_node_ids'],all_src=ns['nm_all_pca'])
# Track exactly the originally floating posterior exported nodes.
old=stages['final_TPS_500']+world
mask=(old[:,1]>190)&(old[:,2]>-800)
rows=[]
for name,v in stages.items():
 d=cKDTree(tgt).query(v)[0];w=v+world
 row=dict(stage=name,mean=float(d.mean()),posterior_floating=int(((w[:,1]>190)&(w[:,2]>-800)).sum()),tracked_mean=float(d[mask].mean()),tracked_max=float(d[mask].max()))
 rows.append(row)
print('DIAGNOSTICS',json.dumps(rows,indent=2))
(root/'alignment_case02/stage_diagnostics.json').write_text(json.dumps(rows,indent=2))
