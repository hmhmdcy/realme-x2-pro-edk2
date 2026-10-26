from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((HERE.parent/'kernel376/source-state.json').read_text())['commit']
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c','camss-icp-a5-memory.c','camss-icp-a5.h']:
 (P/(name+'.before')).write_bytes((source/relative/name).read_bytes())
elf=P.parent/'kernel352/CAMERA_ICP.elf-private'
for name,a,b in [('config-handler',0x16534,0x17f30),('async-handler',0x1c854,0x1e8cc),('map-helper',0x10684,0x10950),('config-callback',0x1eace,0x1eaf2)]:
 q=subprocess.run(['arm-linux-gnueabi-objdump','-d','-m','armv7','--start-address='+hex(a),'--stop-address='+hex(b),str(elf)],capture_output=True,check=True);(P/(name+'-private.asm')).write_bytes(q.stdout)
for name,a,b in [('hal-config-encoder',0x2e4b88,0x2e4f00),('hal-setup',0x2cb5f8,0x2cf070),('hal-striping',0x2e4560,0x2e4b88)]:
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(P.parent/'kernel281/camera.qcom.so-private')],capture_output=True,check=True);(P/(name+'-private.asm')).write_bytes(q.stdout)
(HERE/'source-before.json').write_text(json.dumps(dict(stage=377,parent=parent,source=str(source),clean=True),indent=2)+'\n')
s=(HERE.parent/'kernel376/current-health.py').read_text().replace('stage=376','stage=377');(HERE/'current-health.py').write_text(s)
print('Verified source376 and retained targeted original IO-config/map instruction windows privately.')
