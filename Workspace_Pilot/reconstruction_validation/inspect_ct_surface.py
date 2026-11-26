from pathlib import Path
import os
r=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import numpy as np, pyvista as pv, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
root=r/'synthetic_case02';case=r.parent/'project/Data/HaN-Seg/GT/usable/case_02/stl'
ct=pv.read(case/'case_02_skin_head_neck.stl').triangulate().clean()
sam=pv.read(root/'sam_body/validation/similarity.vtp').triangulate()
roi_sam=pv.read(root/'sam_body/validation/area_roi/similarity_sam_roi_heatmap.vtp').triangulate()
roi_ct=ct.clip(normal=(0,0,1),origin=(0,0,-895),invert=False).triangulate()
fig=plt.figure(figsize=(15,10),layout='constrained')
views=[(ct,'CT mesh used as “ground truth”'),(sam,'SAM head after similarity alignment'),(roi_sam,'SAM comparison ROI: Z ≥ −895 mm')]
for i,(m,title) in enumerate(views,1):
 ax=fig.add_subplot(2,3,i,projection='3d');faces=m.faces.reshape(-1,4)[:,1:];v=m.points;tri=v[faces]
 ax.add_collection3d(Poly3DCollection(tri,facecolor=['#8faabd','#d88a6e','#d88a6e'][i-1],edgecolor='none',alpha=.82))
 ax.set_xlim(-100,100);ax.set_ylim(-50,200);ax.set_zlim(-950,-660);ax.set_box_aspect((200,250,290));ax.view_init(elev=8,azim=-90);ax.set_title(title);ax.set_xlabel('X');ax.set_ylabel('Y');ax.set_zlabel('Z')
 e=m.extract_feature_edges(boundary_edges=True,feature_edges=False,manifold_edges=False,non_manifold_edges=False)
 if e.n_points:
  p=e.points;ax.scatter(p[::max(1,len(p)//800),0],p[::max(1,len(p)//800),1],p[::max(1,len(p)//800),2],c='red',s=2)
 ax.text2D(.02,.02,f'boundary vertices: {e.n_points}',transform=ax.transAxes,color='red')
# Section profiles at x=0 and selected axial slices; dashed cut plane shown explicitly.
for i,(z,title) in enumerate([(-895,'Axial ROI boundary Z=−895'),(-850,'Axial section Z=−850'),(-800,'Axial section Z=−800')],4):
 ax=fig.add_subplot(2,3,i)
 for mesh,color,label in [(ct,'#555555','CT'),(sam,'#187a9c','SAM')]:
  cut=mesh.slice(normal=(0,0,1),origin=(0,0,z));conn=cut.lines;j=0;first=True
  while j<len(conn):
   n=conn[j];q=cut.points[conn[j+1:j+n+1]];ax.plot(q[:,0],q[:,1],color=color,lw=1,label=label if first else None);first=False;j+=n+1
 ax.set_aspect('equal');ax.set_xlim(-100,100);ax.set_ylim(-60,200);ax.set_title(title);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.legend()
fig.suptitle('Surface audit | red marks open mesh boundaries | CT and SAM shown as triangular surfaces')
out=root/'surface_audit.png';fig.savefig(out,dpi=160);print(out)
for name,m in [('CT_reference',ct),('CT_roi',roi_ct),('SAM',sam),('SAM_roi',roi_sam)]:
 e=m.extract_feature_edges(boundary_edges=True,feature_edges=False,manifold_edges=False,non_manifold_edges=False)
 print(name,'bounds',m.bounds,'points',m.n_points,'triangles',m.n_cells,'boundary points',e.n_points,'boundary bounds',e.bounds if e.n_points else None)
