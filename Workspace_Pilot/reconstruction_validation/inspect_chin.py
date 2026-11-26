from pathlib import Path
import os
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import pyvista as pv, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
case=r.parent/'project/Data/HaN-Seg/GT/usable/case_02/stl'
ct=pv.read(case/'case_02_skin_surface.stl').triangulate().clean();cth=pv.read(case/'case_02_skin_head_neck.stl').triangulate().clean();sam=pv.read(r/'synthetic_case02/sam_body/validation/similarity.vtp').triangulate().clean()
# physical anterior is minimum LPS Y; focus face/chin Z band.
fig,axs=plt.subplots(2,2,figsize=(12,11),layout='constrained')
for ax,items,title,axes in [(axs[0,0],[(ct,'#555','CT original') ,(sam,'#187a9c','SAM')],'Side profile (Y-Z)',(1,2)),(axs[0,1],[(cth,'#555','CT cropped'),(sam,'#187a9c','SAM')],'Side profile in previous CT crop',(1,2)),(axs[1,0],[(ct,'#555','CT original') ,(sam,'#187a9c','SAM')],'Front projection (X-Z)',(0,2)),(axs[1,1],[(ct,'#555','CT original') ,(sam,'#187a9c','SAM')],'Oblique view is not used to infer chin contour',(1,2))]:
 for mesh,color,label in items:
  v=mesh.points;f=mesh.faces.reshape(-1,4)[:,1:];cent=v[f].mean(1);sel=(cent[:,2]>-895)&(cent[:,2]<-800)&(cent[:,1]<35)
  tri=v[f[sel]]
  if len(tri):ax.add_collection(PolyCollection(tri[:,:,axes],facecolors=color,edgecolors='none',alpha=.55,label=label))
 ax.autoscale();ax.set_aspect('equal');ax.set_xlim(-80 if axes[0]==0 else -55,90 if axes[0]==0 else 100);ax.set_ylim(-900,-790);ax.set_title(title);ax.set_xlabel('X (mm)' if axes[0]==0 else 'Y LPS (mm)');ax.set_ylabel('Z LPS (mm)');ax.legend()
fig.suptitle('Chin shape audit | CT full surface compared with aligned SAM | face ROI Y<35 mm')
out=r/'synthetic_case02/chin_audit.png';fig.savefig(out,dpi=150)
for name,m in [('CT full',ct),('CT head-neck',cth),('SAM',sam)]:
 q=m.points[(m.points[:,1]<5)&(m.points[:,2]<-850)&(m.points[:,2]>-910)]
 print(name,'face/chin bounds X,Y,Z',q.min(0),q.max(0),'vertices',len(q))
print(out)
