"""Add the bounded internal CC packet encoder; runtime remains the deployed395 core."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['colour-validation.json','enable-abi-validation.json','routing-validation.json']:assert json.loads((HERE/name).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='3a793050772b5e23d22ce9a82dc8ba23000dddb0'
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-colour396'],check=True,capture_output=True)
base='drivers/media/platform/qcom/camss/';paths=[base+'Makefile',base+'camss-icp-a5-colour.c',base+'camss-icp-a5-colour.h']
for short,filename in [('colour-codec.c','camss-icp-a5-colour.c'),('colour-codec.h','camss-icp-a5-colour.h')]:
 target=source/base/filename;assert not target.exists();target.write_bytes((HERE/short).read_bytes())
makefile=source/base/'Makefile';data=makefile.read_text();assert data.count('qcom-camss-icp-a5-core-y += camss-icp-a5-dma.o')==1
makefile.write_text(data.replace('qcom-camss-icp-a5-core-y += camss-icp-a5-dma.o','qcom-camss-icp-a5-core-y += camss-icp-a5-dma.o\nqcom-camss-icp-a5-core-y += camss-icp-a5-colour.o'))
subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
(HERE/'colour-codec.patch').write_bytes(subprocess.check_output(['git','-C',str(source),'diff','--cached','--',*paths]))
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: add bounded IPE post-LTM colour command encoder','--',*paths],check=True,capture_output=True)
assert not git('status','--porcelain')
report=dict(stage=396,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,clean=True,installed=False,runtime_callers_added=False,existing_frame_and_adapter_abi_unchanged=True,arbitrary_userspace_cdm_input_added=False,codec_sha256=hashlib.sha256((source/base/'camss-icp-a5-colour.c').read_bytes()).hexdigest())
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n')
build=(HERE.parent/'kernel395/build-intree.py').read_text().replace('stage=395','stage=396').replace('"""Build the adapter plus the matching standard m2m helper, restoring outputs."""','"""Build the new internal colour encoder in the core, restoring shared outputs."""')
(HERE/'build-intree.py').write_text(build);print(json.dumps(report,indent=2))
