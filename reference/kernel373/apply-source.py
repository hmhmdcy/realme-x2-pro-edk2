from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['order','lifecycle']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
assert (source/state['relative']).read_bytes()==(P/'boot-before.c').read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-hfi-reset-order373'],capture_output=True,check=True)
(source/state['relative']).write_bytes((P/'boot-proposed.c').read_bytes());subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',state['relative']],check=True);subprocess.run(['git','-C',str(source),'commit','-m','media: camss: program and verify HFI parameters after A5 CPU reset'],capture_output=True,check=True)
(HERE/'camss-icp-a5-boot-test.c').write_bytes((source/relative/'camss-icp-a5-boot-test.c').read_bytes())
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel372/live-overlay-state-private.json').read_bytes())
blob=(P.parent/'kernel366/boot-test-private.dtbo').read_bytes();(build/relative/'camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
(HERE/'build-intree.py').write_text((HERE.parent/'kernel372/build-intree.py').read_text().replace('stage=372','stage=373'))
state.update(commit=git('rev-parse','HEAD'),branch='samurai-a5-hfi-reset-order373',applied=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
