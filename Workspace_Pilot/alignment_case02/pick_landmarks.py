"""Run with ../.venv/bin/python pick_landmarks.py from this folder.
Pick the SAME anatomical location in template (left) then CT (right), repeat.
Right-click a visible surface point in either panel. Close window when done.
At least four non-coplanar corresponding pairs are recommended. Picks are
saved in a pending folder; inspect them before enabling in registration.
"""
from pathlib import Path
import numpy as np,pyvista as pv
root=Path(__file__).resolve().parents[1];base=root/'project/Data'
out=root/'alignment_case02/landmarks_pending';out.mkdir(exist_ok=True)
m=pv.read(base/'mesh_model/Head_V6.vtu')
pids=[88000221,88000222,88000223,88000229,88000230,88000231]
s=m.extract_cells(np.flatnonzero(np.isin(m.cell_data['part_id'],pids))).extract_surface(algorithm='dataset_surface').triangulate()
ct=pv.read(base/'HaN-Seg/GT/usable/case_02/stl/case_02_skin_head_neck.stl')
p=pv.Plotter(shape=(1,2));picked=[[],[]]
for side,mesh in enumerate([s,ct]):
 p.subplot(0,side);p.add_mesh(mesh,color='lightblue',opacity=1);p.add_axes();p.add_text(('Template original' if side==0 else 'CT LPS mm')+'\nRight-click matching anatomical points in identical order',font_size=10)
def callback(point):
 side=p.renderers.active_index
 if side not in (0,1):return
 picked[side].append(np.asarray(point).tolist())
 p.add_points(np.array([point]),color='red',point_size=14,render_points_as_spheres=True)
 p.add_point_labels(np.array([point]),[str(len(picked[side]))],font_size=15)
 for i,name in enumerate(['template_landmarks_matched','subject_landmarks_matched']):np.save(out/(name+'.npy'),np.array(picked[i],dtype=float).reshape(-1,3))
 print('Template / CT counts:',*[len(x) for x in picked],flush=True)
p.enable_surface_point_picking(callback=callback,left_clicking=False,show_message=False,show_point=False)
p.show()
if len(picked[0])!=len(picked[1]):print('INCOMPLETE: point counts differ. Do not use these files.')
print('Pending picks saved to',out)
