from pathlib import Path
import sys,os,argparse
parser=argparse.ArgumentParser()
parser.add_argument("--views", nargs="+", default=["front"], choices=["front","oblique_left","oblique_right"])
args=parser.parse_args()
r=Path(__file__).resolve().parent
os.environ['TORCH_HOME']=str(r/'.torch_cache')
os.environ['XDG_CACHE_HOME']=str(r/'.cache')
os.environ['MPLCONFIGDIR']=str(r/'.mplconfig');sys.path.insert(0,str(r/'sam-3d-body'))
import numpy as np,torch,trimesh
from sam_3d_body.build_models import load_sam_3d_body
from sam_3d_body.sam_3d_body_estimator import SAM3DBodyEstimator
ck=r/'checkpoints/sam-3d-body-dinov3'
model,cfg=load_sam_3d_body(str(ck/'model.ckpt'),device='cpu',mhr_path=str(ck/'assets/mhr_model.pt'))
est=SAM3DBodyEstimator(model,cfg)
for view in args.views:
 print('START',view,flush=True)
 outputs=est.process_one_image(str(r/'synthetic_case02'/f'{view}.png'),bboxes=np.array([[120,70,650,700]],dtype=float),inference_type='body')
 out=r/'synthetic_case02/sam_body'
 if view != 'front': out=out/view
 out.mkdir(exist_ok=True)
 for i,o in enumerate(outputs):
  np.savez(out/f'prediction_{i}.npz',**{k:v for k,v in o.items() if isinstance(v,np.ndarray)})
  if 'pred_vertices' in o:trimesh.Trimesh(o['pred_vertices'],est.faces,process=False).export(out/f'body_{i}.ply')
 print('INFERENCE COMPLETE',view,flush=True)
