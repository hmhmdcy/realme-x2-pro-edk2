"""Commit only the built and hardware-tested typed request candidate."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['intree-build','params','pixels']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *args:subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==state['parent']
assert git('branch','--show-current').decode().strip()==state['branch']
assert set(line[3:] for line in git('status','--porcelain').decode().splitlines())==set(state['changed'])
assert (source/state['changed'][-1]).read_bytes()==(HERE/'qcom-ipe-a5.h').read_bytes()
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*state['changed']],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: attach typed IPE IQ to per-frame media requests','--',*state['changed']],check=True)
state.update(commit=git('rev-parse','HEAD').decode().strip(),committed=True,phone_accessed=True,installed=False,
    last_device_evidence_stage=417,media_request_iq_hardware_verified=True,product_libcamera_request_integrated=False,
    fixed_diagnostic_payloads_only=True,known_runtime_r2_warning_taint=512,full_goal_kept_active=True)
state['source_hashes']=[]
for rel in state['changed']:
    data=(source/rel).read_bytes();(P/Path(rel).name).write_bytes(data)
    state['source_hashes'].append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest()))
(HERE/'request-iq.patch').write_bytes(git('diff',state['parent'],'HEAD','--',*state['changed']))
assert not git('status','--porcelain')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
