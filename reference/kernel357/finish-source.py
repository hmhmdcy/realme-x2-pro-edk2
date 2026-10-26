from pathlib import Path
import hashlib, importlib.util, json, subprocess

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel357')
for name in ['node-lifetime-validation.json','kernel-build-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';name='drivers/iommu/of_iommu.c'
state=json.loads((HERE/'source-state.json').read_text());parent=state['parent']
assert (source/name).read_bytes()==(HERE/'of_iommu-after.c').read_bytes()
subprocess.run(['git','-C',str(source),'add','--',name],check=True)
subprocess.run(['git','-C',str(source),'diff','--cached','--check'],check=True)
pending=subprocess.check_output(['git','-C',str(source),'diff','--cached','--name-only'],text=True).splitlines()
if pending:
    assert pending==[name]
    q=subprocess.run(['git','-C',str(source),'commit','-m','iommu/of: release reservation target node references'],capture_output=True)
    (P/'source-commit.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
patch=subprocess.check_output(['git','-C',str(source),'diff',parent,commit,'--',name])
(HERE/'iommu-node-lifetime.patch').write_bytes(patch)
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True)
state.update(commit=commit,tracked_clean=True,file=name,sha256=hashlib.sha256((source/name).read_bytes()).hexdigest(),
    installed=False,kernel_runtime_fix_verified=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(commit=commit,patch_bytes=len(patch),tracked_clean=True),indent=2))
