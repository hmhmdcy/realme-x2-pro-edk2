from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'memory-validation.json').read_text())['passed']
assert json.loads((HERE/'memory-runtime-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';base='drivers/media/platform/qcom/camss/'
names=['Kconfig','Makefile','camss-icp-a5.h','camss-icp-a5-core.c','camss-icp-a5-hfi.c','camss-icp-a5-fw.c','camss-icp-a5-memory.c','camss-icp-a5-memory-test.c'];paths=[base+n for n in names]
for path in (HERE/'kernel').glob('*'):
 if path.suffix in ['.c','.h']:assert path.read_bytes()==(source/base/path.name).read_bytes(),path.name
assert (HERE/'camss-icp-a5-memory-test.c').read_bytes()==(source/base/'camss-icp-a5-memory-test.c').read_bytes()
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'diff','--cached','--check'],check=True)
pending=subprocess.check_output(['git','-C',str(source),'diff','--cached','--name-only'],text=True).splitlines()
if pending:
 assert set(pending)<=set(paths)
 q=subprocess.run(['git','-C',str(source),'commit','-m','media: camss: add A5 ICP HFI, firmware and DMA alias cores'],capture_output=True);(P/'source-commit.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
patch=subprocess.check_output(['git','-C',str(source),'diff','30086bae4d60abe70784a1176bbe418434833b2f',commit,'--',*paths]);(HERE/'a5-icp-core.patch').write_bytes(patch)
status=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True);assert not status,status
state=dict(stage=354,source=str(source),branch='samurai-icp-a5-core354',commit=commit,parent='30086bae4d60abe70784a1176bbe418434833b2f',tracked_clean=True,
 files=[dict(path=p,sha256=hashlib.sha256((source/p).read_bytes()).hexdigest()) for p in paths],temporary_overlay_blob_not_in_source_or_patch=True,
 memory_backend_hardware_tested=True,firmware_not_started=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
# Clarify the precise build rollback scope; refreshed host tools are not Image.
report=json.loads((HERE/'intree-build-validation.json').read_text());report.pop('shared_build_outputs_restored',None)
report.update(shared_camera_outputs_and_config_restored=True,refreshed_host_tools_and_preparation_outputs_not_rolled_back=True)
(HERE/'intree-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(paths),patch_bytes=len(patch),tracked_clean=True),indent=2))
