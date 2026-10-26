"""Commit the CSID175 source candidate, preserving production and prior RFC branches."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel280')
BASE = '30b0daa8cab27f64be4f058629b65f8af1a7cc6f'
git = lambda *args: subprocess.check_output(['git', '-C', str(TREE), *args], text=True)
build = json.loads((ROOT / 'ipp-final-build-validation.json').read_text())
tests = json.loads((ROOT / 'csid175-host-tests-validation.json').read_text())
assert build['exit'] == 0 and not build['diagnostics'] and tests['exit'] == 0 and not tests['diagnostics']
assert git('rev-parse', 'HEAD').strip() == BASE
assert git('branch', '--show-current').strip() == 'samurai-ipp175-280'
assert not git('diff', '--cached', '--name-only')
paths = git('diff', '--name-only').splitlines()
assert len(paths) == 9 and all(path.startswith('drivers/media/platform/qcom/camss/') for path in paths)
git('diff', '--check')
for path in paths:
    git('add', '--', path)
patch = git('diff', '--cached', '--binary')
(ROOT / 'csid175-ipp-candidate.patch').write_text(patch)
hashes = {path: hashlib.sha256((TREE / path).read_bytes()).hexdigest() for path in paths}
body = PRIVATE / 'candidate-message-private.txt'
body.write_text('''media: qcom: camss: prepare CSID175 pixel input transport

The SM8150 OEM description selects CSID175/VFE175. The vfe_ops_170
symbol names a shared RDI backend; it does not identify the actual IFE
silicon or make its PIX interface implemented.

Add the OEM175 IPP register contract, real RAW decode and pixel store,
CID zero, receiver setup, drop/subsample settings, independent IRQs,
frame-boundary halt acknowledgement and bounded timeout errors.
Return stream errors through the common CSID operations and adapt the
other backends to the return type. Arm paths before starting the TPG,
and halt paths before stopping the shared source.

Declare the capability only for the matched SM8150 full CSIDs. Require
a real PIX VFE consumer on that source pad, preserving RAW RDI and Lite
RDI3. A VFE175 processing/output backend and userspace IPA are still
needed: this source candidate is not deployed and does not claim
hardware-processed images. Board DT and firmware stay unchanged.

Validation: all CAMSS ARM64 objects W=1/-Werror and unchanged DTB.
Actual gen2 helpers/configure/ISR under host ASan/UBSan, checked against
15 pinned OEM175 register fields: real RAW decode, invalid formats,
VC limits, C-PHY, halt success/timeout, RDI/Lite, TPG order and IRQs.

Source: realme-kernel-opensource/realmeX2Pro-kernel-source
Commit: 9668fcdc6ec15be7a10d66f7b93c347829e0fdb6
''')
git('commit', '-F', str(body))
commit = git('rev-parse', 'HEAD').strip()
assert not git('status', '--porcelain')
assert git('rev-parse', 'samurai-isp279-candidate').strip() == BASE
production = '/home/cy122/x2pro-linux/camera270-kernel'
assert subprocess.check_output(['git', '-C', production, 'rev-parse', 'HEAD'], text=True).strip() == '0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8'
assert not subprocess.check_output(['git', '-C', production, 'status', '--porcelain'], text=True)
report = dict(stage=280, commit=commit, base_commit=BASE, branch='samurai-ipp175-280',
              changed_paths=paths, source_hashes=hashes,
              patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
              source_clean=True, production_tree_unchanged_and_clean=True,
              prior_candidate_branch_preserved=True, no_board_dt_or_firmware_changes=True,
              not_deployed=True, not_pushed=True)
(ROOT / 'candidate-commit-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key:value for key,value in report.items() if key not in ['source_hashes','changed_paths']}, indent=2))
