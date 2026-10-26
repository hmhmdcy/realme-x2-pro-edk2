from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['firmware-mapping','lifecycle','snapshot']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
for name,digest in state['proposed_sha256'].items():assert hashlib.sha256((P/(name+'.proposed')).read_bytes()).hexdigest()==digest
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-quiesced-failure370'],capture_output=True,check=True)
for relative in state['changed']:(source/relative).write_bytes((P/(Path(relative).name+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*state['changed']],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: retain quiesced failed A5 RAM until owner teardown'],capture_output=True,check=True)
blob=(P.parent/'kernel366/boot-test-private.dtbo').read_bytes()
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel366/live-overlay-state-private.json').read_bytes())
(build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
s=(HERE.parent/'kernel369/build-intree.py').read_text().replace('stage=369','stage=370')
(HERE/'build-intree.py').write_text(s)
state.update(commit=git('rev-parse','HEAD'),branch='samurai-a5-quiesced-failure370',applied=True,installed=False,firmware_cpu_started=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
