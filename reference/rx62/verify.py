"""Verify frozen RX62 build/package evidence; optional read-only external byte checks."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
entries = [line.split('  ', 1) for line in (root / 'SHA256SUMS').read_text().splitlines()]
assert len(entries) == len({name for _, name in entries})
for expected, name in entries:
    assert Path(name).name == name
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
assert {p.name for p in root.iterdir() if p.is_file()} == {name for _, name in entries} | {'SHA256SUMS'}
read = lambda name: json.loads((root / name).read_text(encoding='utf-8-sig'))
for attempt, exit_code in [(1, 1), (2, 1), (3, 0)]:
    assert read(f'build-attempt-{attempt:02}.json')['exit_code'] == exit_code
build = read('build-attempt-03.json')
assert build['qcpnp_sha256'] == '7cf3f3db7878d4a1a037da075e4dfda6985851b7805a42434cf3ae2202c014fd'
assert build['sign_mode'] == 'Off' and not build['installed'] and not build['hardware_validated']
assert hashlib.sha256((root / 'qceudexp.vcxproj').read_bytes()).hexdigest() == build['project_sha256']
assert hashlib.sha256((root / 'qceudexp.inf').read_bytes()).hexdigest() == build['input_inf_sha256']
ns = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}
project = ET.parse(root / 'qceudexp.vcxproj').getroot()
modules = [x.attrib['Include'] for x in project.findall('.//m:ClCompile[@Include]', ns)]
assert len(modules) == 9 and len(set(modules)) == 9
assert [x.attrib['Include'] for x in project.findall('.//m:Inf[@Include]', ns)] == ['qceudexp.inf']
assert '/utf-8' in (root / 'qceudexp.vcxproj').read_text()
authored = (root / 'qceudexp.inf').read_text()
stamped = (root / 'qceudexp-stamped.inf').read_text()
assert 'NTamd64.10.0...26100' in authored and '$KMDFVERSION$' in authored
assert authored.count('USB\\VID_05C6&PID_9505') == 1 and 'PID_9501' not in authored
assert 'KmdfLibraryVersion=1.15' in stamped and '5.47.2.26' in stamped
assert 'QCEudPreserveToggleOnOpen,0x00010001,1' in stamped
log = (root / 'build-attempt-03.log').read_text(encoding='utf-8-sig')
assert '0 个警告' in log and '0 个错误' in log and '已成功生成' in log
assert 'INF is VALID' in (root / 'infverif-w-verbose.log').read_text()
for name in ['inf2cat-win11-generation-retry.log', 'test-signed-inf2cat.log']:
    text = (root / name).read_text()
    assert 'Errors:\nNone' in text and 'Warnings:\nNone' in text and 'Catalog generation complete' in text
package = read('windows11-package.json')
assert all(package[k] == 0 for k in ['infverif_windows_driver_exit', 'infverif_info_exit', 'inf2cat_exit', 'dumpbin_exit'])
assert not package['signed'] and not package['installed'] and not package['hardware_validated']
binary = read('binary-audit.json')
assert binary['machine'] == 'AMD64' and binary['no_executable_writable_sections']
assert binary['new_opt_in_key_present_in_linked_binary'] and not binary['hardware_validated']
sign = read('offline-signing.json')
assert all(sign[k] == 0 for k in ['sys_sign_exit', 'inf2cat_exit', 'catalog_sign_exit'])
assert all(x['signature_only_valid'] for x in sign['cms_signature_checks'])
assert len(sign['certificate_store_checks']) == 6 and all(x['test_certificate_matches'] == 0 for x in sign['certificate_store_checks'])
assert not sign['certificate']['certificate_store_imported'] and not sign['installed'] and not sign['trusted_by_current_host']
cleanup = read('offline-signing-cleanup.json')
assert cleanup['temporary_pfx_absent'] and not cleanup['iso_attached'] and cleanup['private_directory_acl_protected']
image = read('signed-image-audit.json')
assert image['signed_digest_matches_image'] and image['all_original_bytes_unchanged_except_pe_checksum_and_security_directory']
assert not image['kernel_loading_trust_proved'] and not image['hardware_validated']
downloads = read('download-state-12.json')
assert downloads['total_bytes'] == downloads['expected_iso_bytes'] == 20002537472 and downloads['live_count'] == 0
assert len(downloads['parts']) == 8
assert all(x['range_ok'] and x['http206'] and x['etag_matches'] and 'exitcode=0' in x['result'] for x in downloads['parts'])
assembly = read('ewdk-assembly.json')
assert assembly['bytes'] == sum(x['bytes'] for x in assembly['parts']) == 20002537472
assert assembly['sha256'] == '9f48251dd24ad31aac206d8256e95bda5f90a9783982c45a8aafeb9054562379'
post = read('post-signing-state.json')
assert len(post['nodes']) == 3 and all(x['Status'] == 'OK' for x in post['nodes'])
assert not post['known_owners'] and not post['active_eud_trace'] and not post['ewdk_iso_attached']
assert post['temporary_values_absent'] and post['installed_inf'] == 'oem102.inf' and post['installed_signature'] == 'Valid'
assert post['hashes'] == read('baseline-state.json')['hashes']
assert post['secureboot_registry_enabled'] == 1 and post['device_guard']['SecurityServicesRunning'] == [2]

external_checked = False
if '--external' in sys.argv:
    out = Path('/mnt/e/edk2-samurai-out/rx62')
    for report, directory in [(package, 'package-windows11'), (sign, 'package-test-signed')]:
        for item in report['files']:
            data = (out / directory / item['name']).read_bytes()
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    source = Path('/mnt/e/edk2-samurai-out/rx61/source-pinned/qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a/src/windows/wdfserial')
    for name, expected in binary['source_module_sha256'].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected
    assert not (out / 'private-signing/one-use.pfx').exists()
    external_checked = True
print(json.dumps({'frozen_files_verified': len(entries), 'full_build_and_package_checks_passed': True, 'external_package_and_source_bytes_checked': external_checked, 'hardware_validated': False, 'goal_complete': False}))
