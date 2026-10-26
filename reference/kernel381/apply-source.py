"""Apply the verified owned IPE transfer and prepare its temporary overlay."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['ipe-quiesce','ipe-sids','transfer','overlay','session','owner','dispatch','worker']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
for name in state['changed']:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
assert (HERE/'camss-icp-a5-boot-test.c').read_bytes()==(P/'camss-icp-a5-boot-test.c.proposed').read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-ipe-transfer381'],capture_output=True,check=True)
for name in state['changed']:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*[str(relative/n) for n in state['changed']]],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: own target IPE frame DMA through completion and engine stop'],capture_output=True,check=True)
(HERE/'build-intree.py').write_text((HERE.parent/'kernel380/build-intree.py').read_text().replace('stage=380','stage=381'))
blob=(P/'boot-test-private.dtbo').read_bytes()
(build/relative/'camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
state.update(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),source=str(source),applied=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
