from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((HERE.parent/'kernel375/source-state.json').read_text())['commit']
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']:
 (P/(name+'.before')).write_bytes((source/relative/name).read_bytes())
elf=P.parent/'kernel352/CAMERA_ICP.elf-private'
q=subprocess.run(['arm-linux-gnueabi-objdump','-d','-m','armv7','--start-address=0x1c470','--stop-address=0x1c854',str(elf)],capture_output=True,check=True);(P/'create-handler-private.asm').write_bytes(q.stdout)
q=subprocess.run(['arm-linux-gnueabi-objdump','-d','-m','armv7','--start-address=0x1e9d2','--stop-address=0x1ecd6',str(elf)],capture_output=True,check=True);(P/'session-callbacks-private.asm').write_bytes(q.stdout)
(HERE/'source-before.json').write_text(json.dumps(dict(stage=376,parent=parent,source=str(source),clean=True),indent=2)+'\n')
print('Verified source375 and retained targeted original create/destroy instruction windows privately.')
