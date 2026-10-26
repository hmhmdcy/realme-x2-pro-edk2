"""Commit the validated FULL transport while preserving all prior candidates."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='2985ef200e4ae28d567f5919a4d8657ac0559b65'
git=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args],text=True)
assert git('rev-parse','HEAD').strip()==BASE
assert not git('diff','--name-only') and not git('ls-files','--others','--exclude-standard')
build=json.loads((ROOT/'output-final-build-validation.json').read_text())
tests=json.loads((ROOT/'full-output-host-tests-validation.json').read_text())
style=json.loads((ROOT/'output-checkpatch-validation.json').read_text())
assert build['exit']==tests['exit']==0 and not build['diagnostics'] and not tests['stderr']
assert style['new_files_covered_by_existing_camss_maintainers_pattern']
assert 'total: 0 errors, 1 warnings' in style['stdout']
assert 'F:\tdrivers/media/platform/qcom/camss/' in (TREE/'MAINTAINERS').read_text()
paths=git('diff','--cached','--name-only').splitlines()
assert len(paths)==7 and all(p.startswith('drivers/media/platform/qcom/camss/') for p in paths)
git('diff','--cached','--check')
patch=git('diff','--cached','--binary');assert patch==(ROOT/'vfe175-output-candidate.patch').read_text()
hashes={p:hashlib.sha256((TREE/p).read_bytes()).hexdigest() for p in paths}
message=host.PRIVATE/'output-commit-message-private.txt'
message.write_text('''media: qcom: camss: prepare VFE175 FULL NV12 transport

Add the matched single-IFE FULL Y/C clients3/4, packer0xe, per-plane
geometry and stride/frame increments, unshifted byte addresses, UBWC
disable and group0 completion mask. Preserve other bus client fields
when starting or stopping this output. Use all six 17x composite groups
and retire PIX buffers through the common grouped path, excluding PIX
planes from individual RDI DONE dispatch.

Validate the fixed descriptor and NV12 layout before CAMIF MMIO. Apply
the OEM single-FULL 4096x4096 limit and 16-byte stride. Add an optional
capture DMA preparation hook after SG/plane checks, rejecting malformed
contiguous planes, misalignment and any byte beyond the 32-bit aperture.
Metadata preparation keeps its separate callback. Adapt175 output ops
while preserving exact legacy RDI writes. Treat175 PIX height as separate
Y/C write masters, avoiding the aggregate line-based cap.

No board DT or firmware changes, private register UAPI or OEM runtime
dependency. Resources still expose only three RDI lines: pixel modules,
statistics, typed parameters/pipeline/IPA and hardware tests remain
required before exposing or deploying a complete hardware ISP.

Source: realme kernel9668fcdc6ec15be7a10d66f7b93c347829e0fdb6,
cam_vfe175.h and cam_vfe_bus_ver2.c. Validate26 client register addresses,
packer format and full output geometry against that pinned source.

Validation: 32 CAMSS ARM64 components W=1/-Werror; unchanged DTB.
Actual backend, capture prepare, common buffer retirement and17x ISR
under ASan/UBSan: descriptor/layout/32-bit bounds, paired completion,
refill/starvation, late/no-duplicate IRQs, Lite RDI3, exact RDI adapter
writes and height policy. Public multistream negative/control tests
also pass on the resulting code. Not deployed or hardware-verified.
''')
git('commit','-F',str(message))
assert not git('status','--porcelain')
assert git('rev-parse','samurai-vfe175-281').strip()=='21facb9a7941ecd0a624a9e4fccd9ae544dde7b5'
production='/home/cy122/x2pro-linux/camera270-kernel'
assert subprocess.check_output(['git','-C',production,'rev-parse','HEAD'],text=True).strip()=='0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8'
assert not subprocess.check_output(['git','-C',production,'status','--porcelain'],text=True)
report=dict(stage=282,commit=git('rev-parse','HEAD').strip(),base_commit=BASE,
    branch=git('branch','--show-current').strip(),changed_paths=paths,source_hashes=hashes,
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),source_clean=True,
    production_tree_unchanged_and_clean=True,prior_candidate_branches_preserved=True,
    no_board_dt_or_firmware_changes=True,pix_line_not_exposed=True,not_deployed=True,not_pushed=True)
(ROOT/'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['changed_paths','source_hashes']},indent=2))
