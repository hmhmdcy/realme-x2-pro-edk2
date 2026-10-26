from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['serializer','transfer']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'proposal-state.json').read_text())
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
for name in state['changed']:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-ipe-native384'],capture_output=True,check=True)
for name in state['changed']:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*[str(relative/n) for n in state['changed']]],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: serialize native bypass pass and stripe geometry'],capture_output=True,check=True)
(HERE/'build-intree.py').write_text((HERE.parent/'kernel383/build-intree.py').read_text().replace('stage=383','stage=384'))
for name in ['boot-test-private.dtbo','live-overlay-state-private.json']:(P/name).write_bytes((P.parent/'kernel383'/name).read_bytes())
blob=(P/'boot-test-private.dtbo').read_bytes();(build/relative/'camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
state.update(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),source=str(source),applied=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
