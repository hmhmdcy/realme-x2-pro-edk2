"""Check maintained source identity and inspect retained TMC11 target generation."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel412/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=413,source_unchanged_from412=True,tmc11_generation_pending=True,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
manifest=json.loads((HERE.parent/'kernel412/primary-sources.json').read_text());manifest['stage']=413;manifest['retained_from_stage']=412
(HERE/'primary-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
for start,end in [(0x383a00,0x384ed0),(0x384ed0,0x386000),(0x3814c0,0x381800)]:
    q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)],capture_output=True,check=True)
    (P/('generation-'+hex(start)+'-private.asm')).write_bytes(q.stdout)
print('Maintained kernel unchanged;bounded target TMC11 windows retained.')
