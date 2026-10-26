"""Commit only the tested CAMIF source candidate, keeping production unchanged."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel281')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '7f81d76ee7e05c1713ca87b59fc31df806ae0295'
git = lambda *args: subprocess.check_output(['git', '-C', str(TREE), *args], text=True)
build = json.loads((ROOT / 'camif-build-validation.json').read_text())
tests = json.loads((ROOT / 'camif-host-tests-validation.json').read_text())
style = json.loads((ROOT / 'camif-checkpatch-validation.json').read_text())
assert build['exit'] == tests['exit'] == 0 and not build['diagnostics'] and not tests['stderr']
assert style['new_files_covered_by_existing_maintainer_pattern'] and 'total: 0 errors, 1 warnings' in style['stdout']
assert git('rev-parse', 'HEAD').strip() == BASE
assert git('branch', '--show-current').strip() == 'samurai-vfe175-281'
assert not git('diff', '--name-only') and not git('ls-files', '--others', '--exclude-standard')
paths = git('diff', '--cached', '--name-only').splitlines()
assert len(paths) == 8 and all(p.startswith('drivers/media/platform/qcom/camss/') for p in paths)
git('diff', '--cached', '--check')
patch = git('diff', '--cached', '--binary')
assert patch == (ROOT / 'vfe175-camif-candidate.patch').read_text()
hashes = {p:hashlib.sha256((TREE / p).read_bytes()).hexdigest() for p in paths}
message = PRIVATE / 'candidate-message-private.txt'
message.write_text('''media: qcom: camss: prepare matched VFE175 CAMIF input

Select explicit VFE175 operations for the two SM8150 full IFEs, sharing
the existing RDI backend. Add decoded Bayer pattern selection, bounded
full-frame RAW crop, CAMIF output and skip/IRQ configuration, and the
175 epoch position. Validate inputs before any MMIO. Preserve unrelated
core bits and leave pixel reg update until processing/outputs are armed.

Distinguish PIX reg-update bit0/ACK bit4/SOF bit0 from the RDI ports,
including Lite RDI3. Let line preparation return errors through both
17x and common v2 enable paths before parameters or DMA, unwinding the
output reservation and stream count. Adapt the 780 callback contract.

The full resources still expose three RDI lines only. This is an ISP
source candidate: VFE175 processing, output completion and statistics,
libcamera pipeline/IPA and hardware verification remain required. It
does not expose NV12, change board DT, firmware or deployed code.

Source: pinned realme kernel 9668fcdc6ec15be7a10d66f7b93c347829e0fdb6,
cam_vfe175.h and cam_vfe_camif_ver2.c. Local factory HAL static analysis
corroborates CAMIF register ranges and command/config encodings; the
proprietary binary and disassembly stay private and were not executed.

Validation: 31 CAMSS ARM64 components W=1/-Werror; unchanged DTB.
Actual CAMIF/17x ISR/update/enable and common enable functions under
ASan/UBSan: 16 Bayer inputs, bounds, negative no-MMIO cases, PIX/Lite
IRQ distinction, accumulated reg updates and prepare error rollback.
''')
git('commit', '-F', str(message))
commit = git('rev-parse', 'HEAD').strip()
assert not git('status', '--porcelain')
assert git('rev-parse', 'samurai-ipp175-280').strip() == BASE
production = '/home/cy122/x2pro-linux/camera270-kernel'
assert subprocess.check_output(['git','-C',production,'rev-parse','HEAD'],text=True).strip() == '0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8'
assert not subprocess.check_output(['git','-C',production,'status','--porcelain'],text=True)
report = dict(stage=281, commit=commit, base_commit=BASE, branch='samurai-vfe175-281',
    changed_paths=paths, source_hashes=hashes, patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
    source_clean=True, production_tree_unchanged_and_clean=True, prior_candidate_branch_preserved=True,
    no_board_dt_or_firmware_changes=True, not_deployed=True, not_pushed=True,
    closed_oem_binary_and_disassembly_not_in_patch=True)
(ROOT / 'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['changed_paths','source_hashes']},indent=2))
