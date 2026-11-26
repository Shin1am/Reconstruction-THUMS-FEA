from pathlib import Path
import os,json
os.environ['MPLCONFIGDIR']=str(Path.cwd()/'.mplconfig')
import numpy as np,pyvista as pv,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
folder=root/'project/Data/HaN-Seg/GT/usable/case_02'
m=pv.read(folder/'stl/case_02_skin_surface.stl')
# Editable oblique plane in original LPS mm: z >= -912 + 0.28*(y+20).
origin=(0.,-20.,-912.);normal=(0.,-.28,1.)
head=m.clip(normal=normal,origin=origin,invert=False).triangulate().clean()
head.save(folder/'stl/case_02_skin_head_only.stl')
np.save(folder/'case_02_skin_head_only_LPS_mm.npy',np.asarray(head.points,dtype=float))
(folder/'head_crop.json').write_text(json.dumps({'origin_LPS_mm':origin,'normal':normal,'keep':'positive half-space','method':'visual approximate oblique crop; not anatomical segmentation','capped':False,'original_points':m.n_points,'head_points':head.n_points},indent=2))
f,axs=plt.subplots(1,2,figsize=(12,7))
for ax,k,name in zip(axs,[0,1],['Front projection','Side projection']):
 ax.scatter(m.points[:,k],m.points[:,2],s=.3,c='#d5d8dc',label='Removed / original')
 ax.scatter(head.points[:,k],head.points[:,2],s=.3,c='#187a9c',label='Head retained')
 ax.set_aspect('equal');ax.set_title(name);ax.set_xlabel(('X' if k==0 else 'Y')+' (LPS mm)');ax.set_ylabel('Z (mm)');ax.legend(markerscale=8)
f.tight_layout();f.savefig(root/'pilot_case02/head_only_preview.png',dpi=140)
p=json.loads((root/'CPD_TPS_HaNSeg_case02.ipynb').read_text())
for c in p['cells']:
 s=''.join(c['source']).replace('case_02_skin_points_LPS_mm.npy','case_02_skin_head_only_LPS_mm.npy').replace("'Data/outputs/cpd_tps_skin_registration'","'Data/outputs/cpd_tps_case02_head_only'")
 c['source']=s.splitlines(True)
 if c['cell_type']=='code':c['outputs']=[];c['execution_count']=None
p['cells'][0]['source']=['# HaN-Seg case_02: head-only target\n','Uses visually selected oblique crop of subject skin (LPS mm), open at the neck. No artificial closing cap is used for registration. Template FE topology unchanged. This new target configuration has not yet been run.\n']
(root/'CPD_TPS_HaNSeg_case02_head_only.ipynb').write_text(json.dumps(p,ensure_ascii=False,indent=1))
print('Original:',m.n_points,'Head:',head.n_points,'triangles:',head.n_cells)
assert head.n_points>1000
assert np.min((head.points-np.array(origin))@np.array(normal))>-.001
print('Crop half-space check PASS')
