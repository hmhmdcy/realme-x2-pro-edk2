from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'stop-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='64aaf4f78c05f0912e658780294fbded531d87ce'
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';path=source/relative;assert path.read_bytes()==(P/'camss-icp-a5-boot.c.before').read_bytes()
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-a5-reset-pulse395'],check=True,capture_output=True);path.write_bytes((P/'camss-icp-a5-boot.c.proposed').read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check','--',relative],check=True);subprocess.run(['git','-C',str(source),'add','--',relative],check=True);subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: release forced A5 reset before DMA retirement','--',relative],check=True,capture_output=True)
assert not git('status','--porcelain')
r=dict(stage=395,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=[relative],source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),clean=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n')
build=(HERE.parent/'kernel393/build-intree.py').read_text().replace('stage=393','stage=395');a=build.index('modules=[camss/');b=build.index('\ncommand=',a);build=build[:a]+"modules=[camss/'qcom-camss-icp-a5-core.ko']\nruntime_modules=set(modules)"+build[b:];build=build.replace('only_changed_core_adapter_pair_selected_for_deployment=True','only_core_changed_adapter_abi_unchanged=True');(HERE/'build-intree.py').write_text(build)
test=(HERE.parent/'kernel394/prepare-test-core.py').read_text().replace('stage=394','stage=395').replace("=='64aaf4f78c05f0912e658780294fbded531d87ce'","==json.loads((HERE/'source-state.json').read_text())['commit']").replace('camss-icp-a5-boot.c.before','camss-icp-a5-boot.c.normal').replace('proposal-validation.json','test-proposal-validation.json')
(HERE/'prepare-test-core.py').write_text(test)
print(json.dumps(r))
