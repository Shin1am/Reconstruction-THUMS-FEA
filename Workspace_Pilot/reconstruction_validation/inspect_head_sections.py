from pathlib import Path
import os
r=Path(__file__).resolve().parent;os.environ['MPLCONFIGDIR']=str(r/'.mplconfig')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np,pyvista as pv
out=r/'synthetic_case02/sam_body/validation';a=pv.read(out/'similarity.vtp').triangulate();b=pv.read(r/'synthetic_case02/CT_skin_ground_truth.vtp').triangulate()
f,axs=plt.subplots(2,3,figsize=(15,10),layout='constrained')
for ax,mesh,title in zip(axs[0,:2],[b,a],['CT reference: solid triangles','SAM head: solid triangles']):
 v=mesh.points;tri=v[mesh.faces.reshape(-1,4)[:,1:]];order=np.argsort(tri[:,:,0].mean(1));n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12);c=.3+.6*np.abs(n[:,0]);ax.add_collection(PolyCollection(tri[order][:,:,[1,2]],facecolors=plt.cm.Blues(c[order]),edgecolors='none'));ax.set_xlim(-55,205);ax.set_ylim(-945,-675);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)')
def lines(ax,mesh,normal,origin,axes,color,label):
 cut=mesh.slice(normal=normal,origin=origin);conn=cut.lines;start=0;first=True
 while start<len(conn):
  k=conn[start];ids=conn[start+1:start+k+1];q=cut.points[ids];ax.plot(q[:,axes[0]],q[:,axes[1]],color=color,lw=1,label=label if first else None);first=False;start+=k+1
for ax,normal,origin,axes,title in [(axs[0,2],(1,0,0),(0,0,0),(1,2),'Sagittal section X=0 mm')]+[(axs[1,i],(0,0,1),(0,0,z),(0,1),f'Axial section Z={z} mm') for i,z in enumerate([-720,-780,-840])]:
 lines(ax,b,normal,origin,axes,'#555555','CT');lines(ax,a,normal,origin,axes,'#d24b27','SAM');ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[axes[0]]+' (mm)');ax.set_ylabel('XYZ'[axes[1]]+' (mm)');ax.legend()
f.suptitle('Actual triangle surfaces and intersections — similarity alignment only');f.savefig(out/'solid_and_sections.png',dpi=140)
print('SAM boundary edges',a.extract_feature_edges(boundary_edges=True,feature_edges=False,manifold_edges=False,non_manifold_edges=False).n_cells)
