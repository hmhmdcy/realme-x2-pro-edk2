from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['firmware-sfr-validation.json','start-regression-validation.json','diagnostic-regression-validation.json','stop-regression-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
proposal=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative=proposal['changed'][0]
git=lambda *args:subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
assert git('rev-parse','HEAD')==proposal['parent'] and not git('status','--porcelain')
assert (source/relative).read_bytes()==(P/'boot-before-private.c').read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-terminal-sfr368'],check=True,capture_output=True)
subprocess.run(['git','-C',str(source),'apply','--check',str(HERE/'a5-terminal-sfr.patch')],check=True,capture_output=True)
subprocess.run(['git','-C',str(source),'apply',str(HERE/'a5-terminal-sfr.patch')],check=True,capture_output=True)
assert (source/relative).read_bytes()==(P/'boot-proposed.c').read_bytes()
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',relative],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: preserve A5 SFR faults and retire DMA before power-down'],check=True,capture_output=True)
d=dict(proposal,commit=git('rev-parse','HEAD'),branch='samurai-a5-terminal-sfr368',applied=True,installed=False,
    sha256=hashlib.sha256((source/relative).read_bytes()).hexdigest(),hardware_boot_verified=False)
(HERE/'source-state.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
