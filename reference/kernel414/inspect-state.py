"""Verify maintained kernel identity without opening a phone transaction."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel413/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=414,source_unchanged_from413=True,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
manifest=json.loads((HERE.parent/'kernel413/primary-sources.json').read_text())
manifest.update(stage=414,retained_from_stage=413)
(HERE/'primary-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
for start,end in [(0x4ab450,0x4acc98),(0x383cdc,0x384048)]:
    q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)],capture_output=True,check=True)
    (P/('tree-'+hex(start)+'-private.asm')).write_bytes(q.stdout)
print('Maintained406 kernel clean/unchanged; original interpolation windows retained privately.')
