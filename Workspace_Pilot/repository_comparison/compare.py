from pathlib import Path
import subprocess,json,hashlib,csv,difflib,collections,os,tempfile
root=Path(__file__).resolve().parent.parent;out=Path(__file__).resolve().parent
old=root/'reconstruction-thums-source';new=root/'Reconstruction-THUMS-FEA'
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
def tracked(repo):return git(repo,'ls-files','-z').decode().split('\0')[:-1]
def writecsv(name,rows,fields):
 with (out/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def code(p):
 d=json.loads(p.read_text());return '\n\n'.join(''.join(c['source']).rstrip() for c in d['cells'] if c['cell_type']=='code')+'\n'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=git(old,'rev-parse','HEAD').decode().strip();b=git(new,'rev-parse','HEAD').decode().strip()
(out/'upstream_name_status.txt').write_bytes(git(new,'diff','--name-status','-M',a,b))
(out/'upstream_full.patch').write_bytes(git(new,'diff','--binary','-M',a,b))
oldfiles=tracked(old);newfiles=tracked(new);rows=[];mapped=set()
for f in oldfiles:
 candidates=[f]
 if f.startswith('New_version/Code/'): candidates.append(f.removeprefix('New_version/'))
 dest=next((p for p in candidates if p in newfiles),None)
 if dest:
  mapped.add(dest);status='identical' if digest(old/f)==digest(new/dest) else 'changed'
  semantic=''
  if f.endswith('.ipynb'):semantic='same_code' if code(old/f)==code(new/dest) else 'changed_code'
  if status=='changed':
   x=(old/f).read_text(errors='replace');y=(new/dest).read_text(errors='replace')
   path=out/'mapped_diffs'/Path(f+'.diff');path.parent.mkdir(parents=True,exist_ok=True)
   path.write_text(''.join(difflib.unified_diff(x.splitlines(True),y.splitlines(True),fromfile=f,tofile=dest)))
 else:status='removed';semantic=''
 rows.append(dict(old_path=f,new_path=dest or '',status=status,notebook_code=semantic))
for f in newfiles:
 if f not in mapped:rows.append(dict(old_path='',new_path=f,status='added',notebook_code=''))
writecsv('all_upstream_files.csv',rows,['old_path','new_path','status','notebook_code'])
# Inventory all user workspace files except dependencies/caches and the two compared repositories.
exclude={'.git','.venv','.venv_sam_body','.torch_cache','.cache','.mplconfig','__pycache__','.ipynb_checkpoints','checkpoints','sam-3d-body','reconstruction-thums-source','Reconstruction-THUMS-FEA','repository_comparison'}
local=[];pairs=[];byname=collections.defaultdict(list)
for f in newfiles:byname[Path(f).name].append(f)
for directory,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in exclude]
 for name in files:
  p=Path(directory)/name
  if p.is_symlink():continue
  rel=str(p.relative_to(root));matches=byname[name]
  local.append(dict(path=rel,bytes=p.stat().st_size,remote_candidates=len(matches)))
  for dest in matches:
   same=digest(p)==digest(new/dest)
   pairs.append(dict(local_path=rel,remote_path=dest,status='identical' if same else 'different',mapping='basename_candidate_only'))
writecsv('workspace_inventory.csv',local,['path','bytes','remote_candidates'])
writecsv('workspace_name_matches.csv',pairs,['local_path','remote_path','status','mapping'])
# Local renamed CPD variants: semantic code diffs and three-way textual merge simulations.
base=old/'New_version/Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_v2.ipynb'
targets=['Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_v2.ipynb','Code/ipynb/CPD_TPS_Skin_Only_Pipeline_v2.ipynb','Document/Day1_Baseline/frozen/CPD_TPS_Skin_Only_Pipeline_v2.ipynb','Code/notebook/CPS_Pipeline/CPD_TPS_Skin_Only_Pipeline_Mai_ver.ipynb']
nbrows=[]
for p in sorted(root.glob('CPD*.ipynb')):
 for dest in targets:
  x,y,ancestor=code(p),code(new/dest),code(base)
  label=p.stem+'__'+dest.replace('/','__')
  folder=out/'notebook_code_diffs';folder.mkdir(exist_ok=True)
  (folder/(label+'.diff')).write_text(''.join(difflib.unified_diff(x.splitlines(True),y.splitlines(True),fromfile=p.name,tofile=dest)))
  with tempfile.TemporaryDirectory() as td:
   paths=[Path(td)/n for n in ['local.py','base.py','remote.py']]
   for path,s in zip(paths,[x,ancestor,y]):path.write_text(s)
   result=subprocess.run(['git','merge-file','-p',*map(str,paths)],capture_output=True)
  conflicts=sum(line.startswith(b'<<<<<<< ') for line in result.stdout.splitlines())
  if conflicts:
   folder=out/'merge_simulations';folder.mkdir(exist_ok=True);(folder/(label+'.txt')).write_bytes(result.stdout)
  nbrows.append(dict(local_path=p.name,remote_path=dest,same_code=x==y,conflict_blocks=conflicts,merge_exit=result.returncode))
writecsv('notebook_comparisons.csv',nbrows,['local_path','remote_path','same_code','conflict_blocks','merge_exit'])
# Scan tracked text for unresolved markers; only 7-character Git marker lines.
markers=[]
for f in newfiles:
 raw=(new/f).read_bytes()
 if b'\0' in raw:continue
 for n,line in enumerate(raw.decode(errors='replace').splitlines(),1):
  if line.startswith(('<<<<<<< ','>>>>>>> ')):markers.append({'path':f,'line':n})
summary={'old_commit':a,'new_commit':b,'old_clean':not git(old,'status','--porcelain').strip(),'new_clean':not git(new,'status','--porcelain').strip(),'old_is_ancestor':subprocess.run(['git','-C',str(new),'merge-base','--is-ancestor',a,b]).returncode==0,'commits_ahead':int(git(new,'rev-list','--count',a+'..'+b)),'mapped_status_counts':dict(collections.Counter(x['status'] for x in rows)),'workspace_files_inventoried':len(local),'basename_candidate_pairs':len(pairs),'notebook_comparisons':len(nbrows),'simulations_with_conflicts':sum(x['conflict_blocks']>0 for x in nbrows),'tracked_conflict_markers':markers,'excluded_directory_names':sorted(exclude)}
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
