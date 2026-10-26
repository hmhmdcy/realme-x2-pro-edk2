from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
assert json.loads((HERE/'final-state-validation.json').read_text())['passed']
repo=Path('/home/cy122/edk2-samurai/repo');prefix='Platform/Realme/sm8150/'
relatives=['reference/kernel374','reference/kernel375','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']
paths=[p for folder in [HERE.parent/'kernel374',HERE] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[ROOT/r for r in relatives[2:]]
for p in paths:
 assert p.suffix in {'.py','.md','.json','.c','.patch'} and 'private' not in p.name.lower()
 if p.suffix=='.py':compile(p.read_text(),str(p),'exec')
 if p.suffix=='.json':json.loads(p.read_text())
 if p.suffix!='.patch':p.write_text(p.read_text().rstrip()+'\n')
 dest=repo/prefix/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a],text=True).strip()
assert not git('diff','--cached','--name-only'),'Preserve unrelated staged changes'
subprocess.run(['git','-C',str(repo),'add','--',*[prefix+r for r in relatives]],check=True)
names=git('diff','--cached','--name-only').splitlines();assert names and all(any(n==prefix+r or n.startswith(prefix+r+'/') for r in relatives) for n in names)
subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--','.',':(exclude)**/*.patch'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-m','camera: verify OEM A5 HFI lifecycle with cooperative shutdown'],check=True,capture_output=True)
report=dict(stage=375,commit=git('rev-parse','HEAD'),public_files=len(names),source_tree_clean=True,
 actual_full_hfi_lifecycle_verified=True,ipe_image_processing_verified=False,current_boot_guard_stage=374,normal_camera_baseline_passed=True,goal_status='active')
(P/'public-checkpoint-commit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
