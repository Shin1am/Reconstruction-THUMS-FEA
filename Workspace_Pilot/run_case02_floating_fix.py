import os,json,traceback,contextlib,io,time
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['MPLBACKEND']='Agg';os.environ['MPLCONFIGDIR']=str(root/'.mplconfig')
os.environ['HEAD_MODEL_BASE_DIR']=str(root/'project')
p=json.loads((root/'CPD_TPS_case02_floating_fix.ipynb').read_text())
ns={};out=root/'pilot_case02_floating_fix';out.mkdir(exist_ok=True)
log=open(out/'run.log','w',buffering=1)
for i,c in enumerate(p['cells']):
 if c['cell_type']!='code':continue
 s=''.join(c['source'])
 s=s.replace('Data/outputs/cpd_tps_case02_head_neck', 'Data/outputs/cpd_tps_case02_head_neck_rerun')
 s=s.replace('N_LANDMARKS_FIXED  = 2000','N_LANDMARKS_FIXED  = 500').replace('N_LANDMARKS_MOVING = 2000','N_LANDMARKS_MOVING = 500').replace('CPD_MAX_ITER = 100','CPD_MAX_ITER = 30').replace('N_FINAL_TPS_CONTROLS = 2000','N_FINAL_TPS_CONTROLS = 500')
 c['source']=s.splitlines(True)
 print('Running cell',i+1,flush=True)
 buf=io.StringIO()
 try:
  with contextlib.redirect_stdout(buf):exec(compile(s,f'cell_{i+1}','exec'),ns)
  if 'plt' in ns:
   plt=ns['plt']
   for j in plt.get_fignums():plt.figure(j).savefig(out/f'cell_{i+1}_{j}.png',dpi=110)
   plt.close('all')
  text=buf.getvalue();log.write(text);c['outputs']=[{'output_type':'stream','name':'stdout','text':text.splitlines(True)}];c['execution_count']=i+1
 except Exception:
  text=buf.getvalue()+traceback.format_exc();log.write(text);print(text,flush=True);raise
else:
 print('COMPLETED',flush=True)
 baseline=json.loads((root/'pilot_case02/baseline_qa.json').read_text())
 final=ns['result']
 comparison={'baseline_suspect':baseline['n_inverted'],'final_suspect':final['n_inverted'],'new_flagged_ids':len(set(final['bad_eids'])-set(baseline['bad_eids'])),'cleared_flagged_ids':len(set(baseline['bad_eids'])-set(final['bad_eids'])),'note':'Heuristic per-part volume-sign checks; not full Jacobian or solver validation.'}
 (out/'qa_comparison.json').write_text(json.dumps(comparison,indent=2))
 ns['summary_df'].to_csv(out/'metrics.csv',index=False)
 (out/'qa.json').write_text(json.dumps(ns['result'],default=lambda x:int(x),indent=2))
(root/'CPD_TPS_case02_floating_fix_executed.ipynb').write_text(json.dumps(p,indent=1,ensure_ascii=False))
