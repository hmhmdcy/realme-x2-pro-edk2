"""Commit only the validated dequeueability correction before building it."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'adapter-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a])
state=json.loads((HERE/'source-state.json').read_text());relative='drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c'
assert git('rev-parse','HEAD').decode().strip()==state['parent'] and git('branch','--show-current').decode().strip()==state['branch']
assert git('diff','--name-only').decode().splitlines()==[relative]
assert (source/relative).read_bytes()==(host.PRIVATE/'camss-icp-a5-m2m.c.proposed').read_bytes()
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',relative],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: keep quiesced IPE error buffers dequeueable','--',relative],check=True)
state.update(commit=git('rev-parse','HEAD').decode().strip(),changed=[relative],committed=True,adapter_committed=True,
    kernel_unchanged_from417=False,source_preparation_only=False,current419_error_buffer_hardware_verified=False,
    source_hashes=[dict(path=relative,sha256=hashlib.sha256((source/relative).read_bytes()).hexdigest())])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
assert not git('status','--porcelain');print(json.dumps(state,indent=2))
script=(HERE.parent/'kernel417/build-intree.py').read_text().replace('stage=417','stage=419')
(HERE/'build-intree.py').write_text(script)
