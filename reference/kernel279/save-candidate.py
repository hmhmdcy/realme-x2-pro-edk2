"""Save reviewed source candidate and provenance; no push or device deployment."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
PIN = '0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8'
build = json.loads((ROOT / 'candidate-build-validation.json').read_text())
assert build['exit'] == 0 and not build['diagnostics']
test = json.loads((ROOT / 'params-after-fix-validation.json').read_text())
assert test['exit'] == 0 and test['actual_mmio_helpers_and_flag_application']


def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args], text=True)


assert git('rev-parse', 'HEAD').strip() == PIN
assert not git('diff', '--cached', '--name-only')
paths = ['drivers/media/platform/qcom/camss', 'drivers/media/v4l2-core/v4l2-ioctl.c',
         'include/uapi/linux/qcom-camss-config.h', 'include/uapi/linux/videodev2.h',
         'Documentation/userspace-api/media/v4l/meta-formats.rst',
         'Documentation/userspace-api/media/v4l/metafmt-qcom-isp.rst', 'MAINTAINERS']
git('add', '--', *paths)
git('diff', '--cached', '--check')
changed = git('diff', '--cached', '--name-only').splitlines()
assert not any(path.startswith('arch/') for path in changed)
patch = git('diff', '--cached', '--binary')
(ROOT / 'camss-isp-candidate.patch').write_text(patch)
body = PRIVATE / 'candidate-commit-message.txt'
body.write_text('''media: camss: prepare an ISP outputs and metadata source candidate

Adapt the 5 October 2026 SM8650 IFE YUV/stats/params RFC onto the
maintained SM8150 camera tree. Existing core V4L2 ISP support stays intact.
Preserve regulator failure cleanup, SOF tagging, DMA checks and buffer
detachment. Use fixed VFE170 RDI mapping and three hardware bus IRQ banks;
do not advertise an unimplemented SM8150 PIX line.

Handle header-only BHIST DISABLE parameters before reading payload fields,
reject reserved flags and apply the enable/disable state explicitly.

The imported series is by Bryan O'Donoghue, with common ISP and OPE work
by Antoine Bouyer, Jacopo Mondi and Loic Poulain. Preserve their source
copyrights. Original message IDs and per-patch hashes are recorded in the
project's reference/kernel279 provenance manifest. This is an experimental
integration candidate, not a claim of upstream acceptance or VFE170 ISP
support. No deployment or new SM8150 pixel registers are enabled.

Validation: ARM64 W=1 KCFLAGS=-Werror, all 30 CAMSS component objects,
V4L2 ioctl/ISP objects and unchanged board DTB; actual core/callback and
mock-MMIO production helper tests under host ASan/UBSan. Full kernel
linking, boot/runtime and hardware-produced pixel validation remain.

Link: https://lore.kernel.org/all/20261005-linux-mainline-7-2-sm8650-hdk-rfc-0-v1-0-ed985aefd611@kernel.org/
''')
git('commit', '-F', str(body))
commit = git('rev-parse', 'HEAD').strip()
assert not git('status', '--porcelain')
maintained = Path('/home/cy122/x2pro-linux/camera270-kernel')
assert subprocess.check_output(['git', '-C', str(maintained), 'rev-parse', 'HEAD'], text=True).strip() == PIN
assert not subprocess.check_output(['git', '-C', str(maintained), 'status', '--porcelain'], text=True)
report = dict(stage=279, candidate=str(TREE), branch=git('branch', '--show-current').strip(),
              base_commit=PIN, commit=commit, changed_paths=changed,
              patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
              candidate_clean=True, maintained_source_unchanged_and_clean=True,
              no_board_dt_changes=True, not_pushed=True, phone_unchanged=True)
(ROOT / 'candidate-commit-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'changed_paths'}, indent=2))
