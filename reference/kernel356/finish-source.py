"""Save the implemented bootstrap candidate without claiming hardware success."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess
import host

HERE=Path(__file__).resolve().parent; P=host.PRIVATE
for name in ['memory-validation.json','boot-timeout-validation.json','board-region-selection-validation.json','intree-build-validation.json']:
    assert json.loads((HERE/name).read_text())['passed'],name
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';base='drivers/media/platform/qcom/camss/'
parent='0a23a25f34723a9d6fddb3a7c4e94080d0e92b7c'
assert subprocess.check_output(['git','-C',str(source),'branch','--show-current'],text=True).strip()=='samurai-icp-a5-bootstrap356'
for name in ['Kconfig','Makefile']:
    shutil.copyfile(source/base/name,HERE/'kernel'/name)
names=['Kconfig','Makefile','camss-icp-a5.h','camss-icp-a5-memory.c','camss-icp-a5-boot.h','camss-icp-a5-boot.c','camss-icp-a5-boot-test.c']
paths=[base+name for name in names]
for name in names:
    reference=HERE/('camss-icp-a5-boot-test.c' if name.endswith('boot-test.c') else 'kernel/'+name)
    assert reference.read_bytes()==(source/base/name).read_bytes(),name
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'diff','--cached','--check'],check=True)
pending=subprocess.check_output(['git','-C',str(source),'diff','--cached','--name-only'],text=True).splitlines()
if pending:
    assert set(pending)<=set(paths)
    q=subprocess.run(['git','-C',str(source),'commit','-m','media: camss: add SM8150 A5 firmware bootstrap transport'],capture_output=True)
    (P/'source-commit.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
patch=subprocess.check_output(['git','-C',str(source),'diff',parent,commit,'--',*paths])
(HERE/'a5-icp-bootstrap.patch').write_bytes(patch)
status=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True)
assert not status,status
state=dict(stage=356,source=str(source),branch='samurai-icp-a5-bootstrap356',parent=parent,commit=commit,
    tracked_clean=True,reuses_preceding_checkout=True,
    files=[dict(path=p,sha256=hashlib.sha256((source/p).read_bytes()).hexdigest()) for p in paths],
    temporary_overlay_blob_not_in_source_or_patch=True,installed=False,
    firmware_boot_verified=False,corrected_board_carveout_runtime_tested=False,
    r5_worker_status='unknown_ssh_handshake_unresponsive')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(paths),patch_bytes=len(patch),tracked_clean=True),indent=2))
