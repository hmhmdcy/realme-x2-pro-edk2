"""Read fixed Git objects and the existing host audit; write only this directory.

No make, configuration edit, SDK, device, image rebuild or archive rescan.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

R = Path(__file__).resolve().parent
K = Path('/mnt/samurai-full282/source354')
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
BLUEZ = '65d11edee469c24dcc8d075b8be9c040cebaaf98'
git = ['git', '-c', 'safe.directory=' + str(K), '-C', str(K)]
parent_audit = Path('/mnt/e/edk2-samurai-out/bluetooth-20261023/host-protocol-prerequisites-private.json')
baseline = json.loads(parent_audit.read_text())
assert baseline['stored_image_and_config_hash_verified'] and baseline['stored_module_archive_hash_verified']
assert baseline['kernel_release'] == '7.3.0-rc6-rmx1931-samurai-k363+'
specs = {
    'net/bluetooth/Makefile': [(1, 26)],
    'net/bluetooth/Kconfig': [(1, 82)],
    'net/bluetooth/mgmt.c': [(1523, 1531), (2555, 2582), (4703, 4708), (5071, 5075), (5133, 5138)],
    'include/net/bluetooth/hci_core.h': [(900, 917), (1958, 1960), (1998, 1999)],
    'include/net/bluetooth/bluetooth.h': [(655, 674)],
    'net/bluetooth/l2cap_sock.c': [(102, 110)],
    'net/bluetooth/l2cap_core.c': [(40, 44), (8040, 8044)],
    'net/bluetooth/smp.c': [(3370, 3392)],
    'net/bluetooth/hci_sync.c': [(4211, 4218)],
    'net/bluetooth/bnep/Kconfig': [(1, 32)],
    'net/bluetooth/bnep/Makefile': [(1, 10)],
    'net/bluetooth/hidp/Kconfig': [(1, 20)],
    'drivers/hid/Kconfig': [(1, 26), (63, 81)],
    'drivers/hid/Makefile': [(8, 14)],
    'drivers/hid/uhid.c': [(808, 819)],
}
evidence = {}
for path, spans in specs.items():
    raw = subprocess.check_output(git + ['show', COMMIT + ':' + path])
    lines = raw.decode().splitlines()
    evidence[path] = dict(git_blob=subprocess.check_output(git + ['rev-parse', COMMIT + ':' + path], text=True).strip(),
        sha256=hashlib.sha256(raw).hexdigest(),
        excerpts=[dict(first=lo, last=min(hi, len(lines)),
                       lines=[str(i + 1) + ':' + lines[i] for i in range(lo - 1, min(hi, len(lines)))])
                  for lo, hi in spans])
uses = subprocess.check_output(git + ['grep', '-n', '-e', 'CONFIG_BT_LE', '-e', 'CONFIG_UHID',
    '-e', 'CONFIG_BT_BNEP', COMMIT, '--', 'include', 'drivers', 'net'], text=True).splitlines()
uses = [line for line in uses if re.search(r'\bCONFIG_BT_LE\b|\bCONFIG_UHID\b|\bCONFIG_BT_BNEP(?:_\w+)?\b', line)]
(R / 'kernel-source-evidence.json').write_text(json.dumps(dict(commit=COMMIT, files=evidence, config_uses=uses), indent=2) + '\n')
bluez = []
for path in ['profiles/input/hog.c', 'profiles/input/hog-lib.c', 'src/shared/uhid.c']:
    p = R / 'bluez-reference' / path.replace('/', '__')
    bluez.append(dict(commit=BLUEZ, path=path, file=str(p.relative_to(R)), bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        url='https://raw.githubusercontent.com/bluez/bluez/' + BLUEZ + '/' + path))
(R / 'bluez-reference/manifest.json').write_text(json.dumps(bluez, indent=2) + '\n')
record = json.loads((R.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
result = dict(kernel_commit=COMMIT, bluez_commit=BLUEZ,
    reused_parent_audit=str(parent_audit), parent_audit_sha256=hashlib.sha256(parent_audit.read_bytes()).hexdigest(),
    kernel_release=baseline['kernel_release'], image_sha256=record['artifacts']['arch/arm64/boot/Image']['sha256'],
    image_config_sha256=record['artifacts']['.config']['sha256'],
    module_archive_sha256=record['module_archive']['sha256'], kernel_config=baseline['kernel_config'],
    matching_archive_modules=baseline['matching_archive_modules'],
    supplemental_read_only_image_config_values={'CONFIG_HID_SUPPORT': 'y', 'CONFIG_HID': 'y',
        'CONFIG_CRC32': 'y', 'CONFIG_MODVERSIONS': 'n'},
    ordinary_le_mgmt_att_smp_gatt_not_removed_by_bt_le_n=True,
    bt_le_switch_gates_iso_socket_objects_in_this_fixed_tree=True,
    mgmt_runtime_capability_and_bluez_interfaces_not_yet_read=True,
    uart_pm_module_is_not_a_host_protocol_enablement_patch=True,
    hog_requires_uhid_for_kernel_input=True, classic_hidp_does_not_replace_hog_uhid=True,
    bnep_needed_for_pan_networking=True,
    planned_config_delta={'CONFIG_BT_BNEP': ['n', 'm'], 'CONFIG_UHID': ['n', 'm']},
    unchanged_config=['CONFIG_BT', 'CONFIG_BT_BREDR', 'CONFIG_BT_LE', 'CONFIG_BT_HIDP',
                      'CONFIG_HID', 'CONFIG_HID_GENERIC', 'CONFIG_CRC32'],
    shared_header_abi_change_from_these_two_switches_found=False,
    abi_evidence='No CONFIG_UHID/CONFIG_BT_BNEP conditional shared headers; symbols occur only in module Kbuild/private BNEP filter paths',
    new_image_needed_for_two_module_additions=False,
    optional_iso_switch_would_require_new_builtin_bluetooth_image=True,
    ec_red_code_present_runtime_default_disabled=True,
    current_stage='source/configuration review and deferred -j1 build script only',
    kernel_build_started=False, shared_source_or_build_changed=False,
    sdk_or_device_accessed=False, installed_or_loaded=False,
    next_build_requires_main_session_camera456_resource_handoff=True)
(R / 'audit-summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(commit=COMMIT, reused_parent_audit=True, delta=result['planned_config_delta'],
                     kernel_build_started=False, shared_source_or_build_changed=False), indent=2))
