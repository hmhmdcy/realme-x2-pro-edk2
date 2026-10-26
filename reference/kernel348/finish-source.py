from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
state=json.loads((HERE/'source-state.json').read_text());tree=Path(state['source'])
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0 and not build['diagnostics']
for name in ['register-validation.json','pattern-r1-image-validation.json','pattern-r1-capture-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
assert '0 errors, 0 warnings' in Path('/mnt/e/edk2-samurai-out/kernel348/checkpatch-final.log').read_text()
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
names=state['changed_sources'];subprocess.run(['git','-C',str(tree),'add',*names],check=True)
subprocess.run(['git','-C',str(tree),'commit','-m','media: camss: support segmented IFE Gamma parameters on VFE175'],check=True)
commit=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','-C',str(tree),'diff','HEAD'])
state.update(commit=commit,tracked_clean=True,source_sha256={n:hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in names},
 built=True,temporary_hardware_tested=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=348,commit=commit,tracked_clean=True,built=True,temporary_hardware_tested=True,installed=False)))
