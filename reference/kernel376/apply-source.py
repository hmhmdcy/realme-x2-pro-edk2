from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'session-validation.json').read_text())['passed'];state=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
for name in state['changed']:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-ipe-session376'],check=True,capture_output=True)
for name in state['changed']:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check'],check=True);subprocess.run(['git','-C',str(source),'add','--',*[str(relative/n) for n in state['changed']]],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: add A5 IPE RT and non-RT session lifecycle'],capture_output=True,check=True)
blob=(P.parent/'kernel366/boot-test-private.dtbo').read_bytes();(build/relative/'camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel375/live-overlay-state-private.json').read_bytes())
(HERE/'build-intree.py').write_text((HERE.parent/'kernel375/build-intree.py').read_text().replace('stage=375','stage=376'))
state.update(commit=git('rev-parse','HEAD'),branch='samurai-a5-ipe-session376',source=str(source),applied=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
