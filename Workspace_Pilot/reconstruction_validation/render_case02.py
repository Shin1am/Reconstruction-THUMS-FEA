from pathlib import Path
import os,json
r=Path(__file__).resolve().parents[1];os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np,pyvista as pv
out=r/'reconstruction_validation/synthetic_case02';out.mkdir(exist_ok=True)
src=r/'project/Data/HaN-Seg/GT/usable/case_02/stl/case_02_skin_head_neck.stl'
m=pv.read(src).clean().triangulate();m.save(out/'CT_skin_ground_truth.vtp');faces=m.faces.reshape(-1,4)[:,1:];v=m.points;c=np.array([v[:,0].mean(),70.,-800.]);records=[]
for name,yaw in [('front',0),('oblique_left',35),('oblique_right',-35)]:
 a=np.deg2rad(yaw);right=np.array([np.cos(a),np.sin(a),0]);toward=np.array([np.sin(a),-np.cos(a),0]);p=v-c;x=p@right;y=p[:,2];depth=p@toward
 tri=np.stack([x,y],axis=1)[faces];z=depth[faces].mean(1);order=np.argsort(z)
 normals=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]]);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
 light=toward+np.array([-.3,0,.7]);light/=np.linalg.norm(light);shade=.3+.6*np.abs(normals@light);colors=np.repeat(shade[:,None],3,axis=1)
 for mask in [False,True]:
  f=plt.figure(figsize=(7.68,7.68),dpi=100);ax=f.add_axes([0,0,1,1]);f.patch.set_facecolor('black' if mask else 'white');ax.set_facecolor('black' if mask else 'white')
  ax.add_collection(PolyCollection(tri[order],facecolors='white' if mask else colors[order],edgecolors='none',antialiaseds=False));ax.set_xlim(-145,145);ax.set_ylim(-145,145);ax.set_aspect('equal');ax.axis('off');f.savefig(out/(name+('_mask' if mask else '')+'.png'),dpi=100);plt.close(f)
 records.append(dict(name=name,yaw_degrees=yaw,projection='orthographic',center_LPS_mm=c.tolist(),right=right.tolist(),toward_camera=toward.tolist(),vertical=[0,0,1],field_width_mm=290,image_pixels=768))
(out/'manifest.json').write_text(json.dumps(dict(experiment='CT-derived synthetic-input pilot; NOT independent photographic validation',subject='HaN-Seg case_02',source=str(src),units='mm',views=records,renderer='software triangle painter; grayscale two-sided lighting, no texture',SAM3D_status='not run; no installed model/inference backend'),indent=2));print('Rendered three views and masks')
