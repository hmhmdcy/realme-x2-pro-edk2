"""Verify frozen offline evidence only. Never opens a device or starts helpers."""
from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
entries = []
for line in (root / 'SHA256SUMS').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert '/' not in name and '\\' not in name and name not in ('.', '..')
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    entries.append(name)
assert len(entries) == len(set(entries))
assert set(entries) == {p.name for p in root.iterdir() if p.is_file()} - {'SHA256SUMS'}
get = lambda name: json.loads((root / name).read_text(encoding='utf-8-sig'))
inf = (root / 'qceudexp.inf').read_text()
package = get('package-inputs.json')
assert hashlib.sha256((root / 'qceudexp.inf').read_bytes()).hexdigest() == package['inf_sha256']
assert inf.count('USB\\VID_05C6&PID_9505') == 1 and '9501' not in inf and 'HKLM' not in inf
assert 'KmdfLibraryVersion=$KMDFVERSION$' in inf and 'KmdfService=qceudexp,EudKmdf' in inf
assert 'EudCopy=13' in inf and 'ServiceBinary=%13%\\qcwdfserial.sys' in inf
assert 'QCDeviceZLPEnabled' not in inf
ns = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}
tree = ET.parse(root / 'qceudexp.vcxproj')
assert [e.attrib['Include'] for e in tree.findall('.//m:Inf', ns)] == ['qceudexp.inf']
assert len([e for e in tree.findall('.//m:ClCompile', ns) if 'Include' in e.attrib]) == 9
source = get('source-audit.json')
assert len(source['module_hashes']) == 9
assert [name for name, data in source['module_hashes'].items() if data['changed']] == ['QCPNP.c']
assert source['all_functions_after_filecreate_unchanged'] and not source['upstream_inf_has_eud_match']
download = get('download-state-record.json')
assert download['live_count'] == 8
assert sum(p['bytes'] for p in download['parts']) == download['total_bytes'] == 11459821568
assert all(p['live'] and p['range_ok'] and p['http206'] and p['etag_matches'] for p in download['parts'])
assert round(download['total_bytes'] / download['expected_iso_bytes'] * 100, 2) == download['percent']
for name in ['baseline-state.json', 'post-state.json']:
    state = get(name)
    assert len(state['nodes']) == 3 and all(n['Status'] == 'OK' for n in state['nodes'])
    assert not state['known_owners'] and state['temporary_values_absent'] and not state['active_eud_trace']
    assert 'Attached' not in state['usbipd'] and 'Shared' in state['usbipd']
assert get('baseline-state.json')['hashes'] == get('post-state.json')['hashes']
host = get('host-binding.json')
assert host['driver']['InfPath'] == 'oem102.inf' and host['driver']['DriverVersion'] == '2.1.3.5'
assert host['signature_status'] == 'Valid' and host['secureboot_registry_enabled'] == 1
assert host['device_guard']['SecurityServicesRunning'] == [2]
rollback = get('rollback-package.json')
assert rollback['inf_sha256'] == host['installed_inf_sha256'] and len(rollback['files']) == 4
assert not package['full_wdk_build'] and not package['installed'] and not package['hardware_validated']
print(f'PASS: {len(entries)} frozen files; package/source/download/baseline evidence. Full WDK build and hardware still pending.')
