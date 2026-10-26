"""Verify unchanged kernel and retain only relevant target binding windows."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel415/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=416,source_unchanged_from415=True,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=416,retained_manifests=['../kernel415/primary-sources.json','../kernel412/primary-sources.json','../kernel410/primary-sources.json'],
    no_new_source_download=True,target_hal_retained_from281=True,newer_source_not_assumed_target_layout=True),indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
for start,end in [(0x2cf504,0x2cf514),(0x2cfa70,0x2cfaa0),(0x2d6564,0x2d6590),
                  (0x2d7a60,0x2d7a90),(0x377120,0x3771b8),(0x383728,0x383cdc),(0x38565c,0x3856a4)]:
    raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)])
    (P/('verified-'+hex(start)+'-private.asm')).write_bytes(raw)
print('Kernel406 clean/unchanged; exact target binding and Execute windows retained privately.')
