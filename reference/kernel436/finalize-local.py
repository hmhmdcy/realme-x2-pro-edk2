"""Recover missing435 public files and save436 without changing unrelated work."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
tree=storage.candidate()/'src/libcamera-v0.7.2'
assert json.loads((HERE/'hardware-validation.json').read_text())['passed']
for row in json.loads((HERE/'source-state.json').read_text())['source_hashes']:
 assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='efd01b4cf0bbbbf966730c53cf381908408c7a27'
selected=[p.relative_to(ROOT) for stage in ['kernel435','kernel436'] for p in (ROOT/'reference'/stage).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected+=[Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through434-2026-10-22.md','archive/NEXT-SESSION-through435-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
selected=sorted(set(selected));paths=[str(Path('Platform/Realme/sm8150')/p) for p in selected]
spec=importlib.util.spec_from_file_location('docs436',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
 if rel.suffix=='.py':
  code=(ROOT/rel).read_text(encoding='utf-8-sig')
  if rel.name in ['auto-capture-body.py','replay-body.py']:code='try:\n'+code+'\nexcept BaseException:pass\n'
  ast.parse(code)
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/name).stat().st_size<=check.load_manifest(ROOT)['size_limits'][name]
exclude=['.',*[':(exclude)'+p for p in paths]]
index_before=git('diff','--cached','--binary','--',*exclude)
work_before=git('diff','--binary','--',*exclude)
others_before=set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'))-{p.encode() for p in paths}
for rel in selected:
 dest=mirror/rel;dest.parent.mkdir(parents=True,exist_ok=True);data=export.public_bytes(ROOT,rel);dest.write_bytes(data);assert dest.read_bytes()==data
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: restore stock main BLS before automatic tone and audit same-frame inputs','--',*paths],check=True)
assert git('diff','--cached','--binary','--',*exclude)==index_before
assert git('diff','--binary','--',*exclude)==work_before
assert set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'))-{p.encode() for p in paths}==others_before
assert not git('diff','HEAD','--',*paths)
subprocess.run(['sync'],check=True)
r=dict(stage=436,local_commit=git('rev-parse','HEAD').decode().strip(),public_files=len(paths),recovered435_public_files=True,
 unrelated_index_worktree_and_untracked_paths_preserved=True,public_export_used=True,private_coefficients_and_pixels_not_exported=True,pushed=False,installed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
