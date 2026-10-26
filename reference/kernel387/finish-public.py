"""Save own source and sanitized evidence in the existing local repository."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
kernel=mount.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'],text=True).strip()
for leaf in ['current-state','pipeline','ipe','cancel','attempts']:
 assert json.loads((HERE/(leaf+'-validation.json')).read_text())['passed']
repo=Path('/home/cy122/edk2-samurai/repo');prefix='Platform/Realme/sm8150/'
relatives=['reference/kernel387','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md','archive/NEXT-SESSION-through386-2026-10-21.md']
git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a],text=True).strip()
assert not git('diff','--cached','--name-only'),'Preserve unrelated staged changes'
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[ROOT/r for r in relatives[1:]]
for p in paths:
 assert p.suffix in {'.py','.md','.json','.c','.cpp','.h','.patch'} and 'private' not in p.name.lower()
 if p.suffix=='.py':compile(p.read_text(),str(p),'exec')
 if p.suffix=='.json':json.loads(p.read_text())
 if p.suffix!='.patch':p.write_text(p.read_text().rstrip()+'\n')
 dest=repo/prefix/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
subprocess.run(['git','-C',str(repo),'add','--',*[prefix+r for r in relatives]],check=True)
names=git('diff','--cached','--name-only').splitlines();assert names and all(any(n==prefix+r or n.startswith(prefix+r+'/') for r in relatives) for n in names)
# The full pipeline snapshot retains the unchanged r29 whitespace; final
# functional changes are separately reviewable in camss-ipe-pipeline.patch.
subprocess.run(['git','-C',str(repo),'diff','--cached','--check','--','.',':(exclude)**/*.patch',':(exclude)'+prefix+'reference/kernel387/camss-vfe-after.cpp'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-m','camera: connect four libcamera sensors to native IPE and verify 82 frames'],check=True,capture_output=True)
report=dict(stage=387,commit=git('rev-parse','HEAD'),public_files=len(names),kernel_source_clean=True,ipe_libcamera_candidate_hardware_verified=True,final_run_ipe_completed=82,
 raw_pair_and_original_timestamp_verified=True,raw_only_no_ipe=True,isolated_ipa_control_regression=True,zero_copy=False,permanently_installed=False,
 raw_firmware_logs_calibration_images_and_cdm_not_published=True,goal_status='active')
(P/'public-checkpoint-commit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
