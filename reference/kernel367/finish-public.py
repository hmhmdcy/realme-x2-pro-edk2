"""Commit only the public files belonging to this completed checkpoint."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];repo=Path('/home/cy122/edk2-samurai/repo');prefix='Platform/Realme/sm8150/'
assert json.loads((HERE/'final-state-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==json.loads((HERE.parent/'kernel365/source-state.json').read_text())['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
relatives=['reference/kernel'+str(n) for n in range(363,368)]
relatives+=['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
 'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md',
 'archive/NEXT-SESSION-through362-2026-10-20.md','archive/camera-deployment-lock-through362-2026-10-20.json','archive/camera-source-lock-through362-2026-10-20.json']
already=git('diff','--cached','--name-only').splitlines()
assert all(any(n==prefix+p or n.startswith(prefix+p+'/') for p in relatives) for n in already),'Preserve unrelated staged changes'
shutil.copyfile(Path(__file__),repo/prefix/'reference/kernel367/finish-public.py')
capture=ROOT/'reference/kernel366/capture-eud.ps1';capture.write_text(capture.read_text().rstrip()+'\n')
shutil.copyfile(capture,repo/prefix/'reference/kernel366/capture-eud.ps1')
for relative in relatives[:5]:
 for p in (ROOT/relative).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts:continue
  assert p.suffix in {'.py','.md','.json','.patch','.c','.ps1'},p
  assert 'private' not in p.name.lower(),p
subprocess.run(['git','-C',str(repo),'add','--',*[prefix+p for p in relatives]],check=True)
names=git('diff','--cached','--name-only').splitlines();assert names
assert all(any(n==prefix+p or n.startswith(prefix+p+'/') for p in relatives) for n in names)
# Nested unified patches contain a leading context marker before source tabs;
# their source diffs were checked in prepare-source, not as prose indentation.
subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--','.',':(exclude)**/*.patch'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-m','camera: deploy unified kernel and static ICP board DT, preserve HFI timeout and recovered baseline'],check=True,capture_output=True)
report=dict(stage=367,commit=git('rev-parse','HEAD'),public_files=len(names),source_tree_clean=True,unrelated_work_preserved=True,goal_status='active')
(host.PRIVATE/'public-checkpoint-commit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
