"""Prepare minimal FLOAT candidate from the frozen provider header, PC only."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parent
base = root.parent.parent / 'charging-management-20261023'
original = (base / 'samurai-usb-input-decode.h').read_text()
candidate = original.replace('SAMURAI_USB_DCP, SAMURAI_USB_TYPE_C,',
                            'SAMURAI_USB_DCP, SAMURAI_USB_TYPE_C, SAMURAI_USB_FLOAT,', 1)
anchor = '\tif (!(s->legacy & 2) && (cc == 4 || cc == 2)) {'
assert original.count(anchor) == 1
candidate = candidate.replace(anchor,
    '\t/* OEM SMB5 accepts USB-stack SDP current after a FLOAT detection.\n'
    '\t * Keep FLOAT unclassified until a valid native USB2 allowance exists;\n'
    '\t * never inherit a DCP/Rp high-current budget from this ambiguity.\n'
    '\t */\n'
    '\tif (result == 0x10) {\n'
    '\t\tif (!(s->apsd & 1) || s->result != 0x10 || (s->apsd & 0x8c))\n'
    '\t\t\treturn 0;\n'
    '\t\tb->kind = SAMURAI_USB_FLOAT;\n'
    '\t\treturn 0;\n'
    '\t}\n' + anchor, 1)
candidate = candidate.replace(
    '\tif (b->kind != SAMURAI_USB_SDP || !b->online) return 0;',
    '\tif ((b->kind != SAMURAI_USB_SDP && b->kind != SAMURAI_USB_FLOAT) ||\n'
    '\t    !b->online) return 0;', 1)
candidate = candidate.replace('\tb->current_ua = current_ua;\n\treturn 0;\n}',
    '\tif (b->kind == SAMURAI_USB_FLOAT)\n\t\tb->kind = SAMURAI_USB_SDP;\n'
    '\tb->current_ua = current_ua;\n\treturn 0;\n}', 1)
(root / 'samurai-usb-input-decode.h').write_text(candidate)
(root / 'original-samurai-usb-input-decode.h').write_text(original)
patch = ''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
    fromfile='a/samurai-usb-input-decode.h', tofile='b/samurai-usb-input-decode.h'))
(root / 'float-only.patch').write_text(patch)
source_path = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research/stock--drivers--power--supply--qcom--smb5-lib.c')
oem = source_path.read_text()
functions = []
records = []
for name in ('smblib_handle_usb_current', 'smblib_set_prop_sdp_current_max'):
    match = re.search(r'^(?:static )?int\s+' + name + r'\([^;]*?\)\n\{', oem, re.M)
    assert match
    stop = oem.index('\n}', match.start()) + 2
    function = oem[match.start():stop]
    functions.append(function)
    records.append({'function': name, 'line': oem.count('\n', 0, match.start()) + 1,
                    'sha256': hashlib.sha256(function.encode()).hexdigest()})
(root / 'oem-functions.inc').write_text('\n\n'.join(functions) + '\n')
# Verify the cached file against the pinned same-device OEM git object.
git_path = '/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
git_data = subprocess.check_output(['git', '--git-dir=' + git_path, 'show',
    '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6:drivers/power/supply/qcom/smb5-lib.c'])
assert hashlib.sha256(git_data).digest() == hashlib.sha256(source_path.read_bytes()).digest()
manifest = {
    'base_header_sha256': hashlib.sha256((base / 'samurai-usb-input-decode.h').read_bytes()).hexdigest(),
    'candidate_header_sha256': hashlib.sha256((root / 'samurai-usb-input-decode.h').read_bytes()).hexdigest(),
    'patch_sha256': hashlib.sha256((root / 'float-only.patch').read_bytes()).hexdigest(),
    'provider_c_sha256_unchanged': hashlib.sha256((base / 'samurai-usb-input.c').read_bytes()).hexdigest(),
    'oem_source': str(source_path), 'oem_sha256': hashlib.sha256(git_data).hexdigest(),
    'oem_commit': '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6',
    'oem_functions': records, 'shared_or_main_modified': False, 'phone_accessed': False,
    'udc_valid_lifecycle_changed': False,
}
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
