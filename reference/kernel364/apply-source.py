"""Apply only after the pinned363 build is complete and its kernel is verified."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel364')
assert json.loads((HERE.parent/'kernel363/postboot-validation.json').read_text())['new_boot_verified']
assert json.loads((HERE.parent/'kernel363/boot-candidate-build-validation.json').read_text())['terminal']
assert json.loads((HERE/'start-regression-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';name='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'
parent='ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==parent
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
assert (source/name).read_bytes()==(HERE.parent/'kernel356/kernel/camss-icp-a5-boot.c').read_bytes()
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-exact-ready364'],check=True,capture_output=True)
subprocess.run(['git','-C',str(source),'apply','--check',str(HERE/'exact-hfi-ready.patch')],check=True,capture_output=True)
subprocess.run(['git','-C',str(source),'apply',str(HERE/'exact-hfi-ready.patch')],check=True,capture_output=True)
assert (source/name).read_bytes()==(P/'boot-proposed.c').read_bytes()
subprocess.run(['git','-C',str(source),'add','--',name],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: wait for exact A5 HFI initialization success'],check=True,capture_output=True)
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
report=dict(stage=364,source=str(source),parent=parent,commit=commit,branch='samurai-a5-exact-ready364',changed=[name],
    sha256=hashlib.sha256((source/name).read_bytes()).hexdigest(),applied=True,installed=False,firmware_boot_verified=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
