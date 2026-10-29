"""Collect results of the MaiAlgo experiments on one case into one table (read-only on run folders)."""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = sys.argv[1] if len(sys.argv) > 1 else 'case_02'
DAY3 = os.path.join(HERE, '..', 'Day3_Case02_Baseline', 'out_case_case_02')

runs = {'0 baseline (Day 3)': (DAY3, os.path.join(HERE, 'out_baseline_ref', 'interior_vs_gt.csv'))}
for d in sorted(os.listdir(HERE)):
    if d.startswith(f'out_{CASE}_'):
        runs[d.replace(f'out_{CASE}_', '')] = (os.path.join(HERE, d), os.path.join(HERE, d, 'interior_vs_gt.csv'))

rows = []
for name, (d, icsv) in runs.items():
    v = pd.read_csv(os.path.join(d, 'validation_summary.csv')).iloc[-1]
    meta = json.load(open(os.path.join(d, 'run_meta.json')))
    jac_dir = os.path.join(d, 'jacobian')
    jj = json.load(open(os.path.join(jac_dir, 'jacobian_summary.json'))) if os.path.exists(jac_dir) else {}
    it = pd.read_csv(icsv)
    reg = it[it.state == 'baseline registered'].set_index('structure')
    rows.append(dict(run=name, rigid_scale=round(meta['rigid_scale'], 3), skin_mean=v['mean'], skin_hd=v['hausdorff'],
                     skull_out=reg.loc['skull_outer', 'mean_sym'], skull_in=reg.loc['skull_inner', 'mean_sym'],
                     brain=reg.loc['brain', 'mean_sym'], stem=reg.loc['brainstem', 'mean_sym'],
                     eyes=reg.loc['eyes', 'mean_sym'], brain_zext=reg.loc['brain', 'extent_ratio_z'],
                     failing=jj.get('failing_registered'), newly_failing=jj.get('newly_failing')))
df = pd.DataFrame(rows).round(2)
print(df.to_string(index=False))
df.to_csv(os.path.join(HERE, f'results_{CASE}.csv'), index=False)

ref = pd.read_csv(runs['0 baseline (Day 3)'][1])
sim = ref[ref.state == 'similarity (rigid CPD)'].set_index('structure')['mean_sym'].round(2)
print('\nrigid+scale control (mean_sym):', sim.to_dict())
