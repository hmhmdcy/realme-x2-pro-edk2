from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE;repo=Path('/home/cy122/edk2-samurai/repo');prefix='Platform/Realme/sm8150/'
assert json.loads((HERE/'final-state-validation.json').read_text())['passed']
assert not json.loads((HERE/'boot-runtime-r1-validation.json').read_text())['firmware_handshake_passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
relatives=['reference/kernel369','reference/kernel368/source-state.json','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[ROOT/r for r in relatives[1:]]
for p in paths:
 assert p.suffix in {'.py','.md','.json','.c','.patch'} and 'private' not in p.name.lower()
 if p.suffix!='.patch':p.write_text(p.read_text().rstrip()+'\n')
 dest=repo/prefix/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
assert not git('diff','--cached','--name-only'),'Preserve unrelated staged changes'
subprocess.run(['git','-C',str(repo),'add','--',*[prefix+r for r in relatives]],check=True)
names=git('diff','--cached','--name-only').splitlines();assert names and all(any(n==prefix+r or n.startswith(prefix+r+'/') for r in relatives) for n in names)
subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--','.',':(exclude)**/*.patch'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-m','camera: preserve real A5 fault dump and verify recovered multi-camera baseline'],check=True,capture_output=True)
report=dict(stage=369,commit=git('rev-parse','HEAD'),public_files=len(names),source_tree_clean=True,
    actual_devcoredump_recovered=True,firmware_handshake_verified=False,device_baseline_recovered=True,
    no_permanent_icp_installation=True,goal_status='active')
(P/'public-checkpoint-commit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
