from pathlib import Path
from hashlib import sha256
from collections import Counter
import gzip,json,re,runpy

base=Path(__file__).resolve().parent
listed={}
for line in (base/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert name not in listed and sha256((base/name).read_bytes()).hexdigest()==expected,name
    listed[name]=expected
assert set(listed)=={p.name for p in base.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
for row in json.loads((base/'exports.json').read_text()):
    assert sha256((base/row['name']).read_bytes()).hexdigest()==row['exported_sha256']
    if not row['name'].endswith('.asm.txt'):
        assert row['byte_identical'] and row['original_sha256']==row['exported_sha256']
for name,expected in json.loads((base/'dependencies.json').read_text()).items():
    assert sha256((base/name).read_bytes()).hexdigest()==expected,name
for name in ['prepared-hashes.json','prepared-hashes-02.json']:
    for dep,expected in json.loads((base/name).read_text()).items():
        path=base/dep if (base/dep).exists() else base.parent/'rx55'/dep
        assert sha256(path.read_bytes()).hexdigest()==expected,dep
functions={}
for name in ['logging-identity.json','creation-identity.json']:
    identity=json.loads((base/name).read_text())
    assert identity['identity_matches'] and identity['section_headers_match']
    assert identity['binary_sha256']=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
    assert identity['pdb_sha256']=='ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
    assert (identity['guid'],identity['age'])==('66581f50-52c9-4a32-9ac6-fe0c57b94a80',1)
    functions.update({f['name']:f for f in identity['functions']})
previous=json.loads((base.parent/'rx54/installed-driver-identity.json').read_text())
multi,=[f for f in previous['local_only_functions'] if f['name']=='QCMRD_L2MultiReadThread']
functions[multi['name']]=multi
instructions={}
for function in functions.values():
    code=bytearray();address=int(function['start_rva'],16)
    for line in (base/function['disassembly']).read_text().splitlines():
        match=re.match(r'^([0-9a-f]{8}) ((?:[0-9a-f]{2} )*[0-9a-f]{2})\s+([a-z].*)$',line)
        assert match and int(match[1],16)==address,line
        part=bytes.fromhex(match[2]);instructions[match[1]]=(part.hex(),match[3]);code.extend(part);address+=len(part)
    assert address==int(function['end_rva'],16) and len(code)==function['size']
    assert sha256(code).hexdigest()==function['code_sha256']
assert len(functions)==4
window=json.loads((base/'config-copy-window.json').read_text())
for row in window:
    assert instructions[row['instruction']][0]==row['bytes']
assert instructions['0001a847'][0]=='8a05e4fa0100' and instructions['0001a84d'][0]=='418885c2110000'
assert '0x2f708' in instructions['0000ef9e'][1]
refs=json.loads((base/'logging-code-refs.json').read_text())
assert any(c['caller']=='QCPNP_AddDevice' and c['call']=='00014c85' for c in refs['callers'])
assert any(c['caller']=='QCPTDO_CreateNewPTDO' and c['call']=='0001b768' for c in refs['callers'])
events=json.loads(gzip.decompress((base.parent/'rx56/old-etw-target-transfers.json.gz').read_bytes()))
pending={};peak=0;counts=Counter()
for event in events:
    fields=event['fields']
    if fields.get('fid_PipeHandle')!=['0xFFFFC00BB56C89F0']:continue
    key=(fields['fid_IRP_Ptr'][0],fields['fid_URB_Ptr'][0])
    if event['id']=='26':
        assert key not in pending;pending[key]=event['stamp'];counts[fields['fid_URB_TransferBufferLength'][0]]+=1
    elif event['id']=='27':assert key in pending;del pending[key]
    peak=max(peak,len(pending))
old=json.loads((base/'etw-outstanding.json').read_text())
assert peak==old['peak_concurrent_in']==6 and dict(counts)==old['in_dispatch_lengths']=={'0x8000':95} and not pending
for suffix in ['','-02']:
    tests=json.loads((base/('prepared-tests'+suffix+'.json')).read_text())
    assert tests['mock_registry_only'] and tests['no_native_pnp_calls'] and tests['no_port_opened'] and tests['parser_clean']
    assert tests['actual_helper_sha256']==sha256((base/('driver-log-admin'+suffix+'.ps1')).read_bytes()).hexdigest()
    assert len(tests['cases'])==4 and len(tests['reload_cases'])==3
    assert tests['cases'][-1]['phase']=='restore-failed' and tests['cases'][-1]['remaining_values']==1
first=json.loads((base/'control-01-status.json').read_text())
second=json.loads((base/'control-02-status.json').read_text())
assert first['phase']=='restore-failed' and 'Win32_PnPEntity' in first['failure']
assert second['phase']=='restored' and second['restore_request_seen'] and second['targeted_original_values_absent']
assert not second['failure'] and not second['restore_failure']
for name in ['state-after-attempt-01.json','final-state.json']:
    state=json.loads((base/name).read_text())
    assert state['snapshot_read_only'] and len(state['devices'])==3 and all(d['Status']=='OK' and d['ConfigManagerErrorCode']==0 for d in state['devices'])
    assert len(state['registry_values'])==2 and not any(r['present'] for r in state['registry_values'])
    assert not state['known_serial_owners'] and not any(h['process_alive'] for h in state['helper_states'])
    assert not any('Attached' in s for s in state['target_usbipd'])
    assert state['phone_flash_count']==state['phone_reboot_count']==state['driver_install_count']==0
    hashes={r['Path']:r['Hash'].lower() for r in state['hashes']}
    epoch=json.loads((base.parent/'rx53/source-epoch.json').read_text())
    assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c']==epoch['sha256']['driver']
    assert hashes['E:\\eud-host\\eud-terminal.ps1']=='9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
    assert hashes['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img']=='50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
    assert hashes['C:\\Windows\\System32\\drivers\\qcusbser.sys']=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
    assert any(s.startswith(epoch['sha256']['driver']+' ') for s in state['linux_hashes'])
    assert any(s.startswith(epoch['sha256']['Image']+' ') for s in state['linux_hashes'])
summary=json.loads((base/'capture-summary.json').read_text())
replayed=runpy.run_path(str(base/'analyze-capture.py'),init_globals={'RX57_VERIFY_ONLY':True})['result']
assert json.loads(json.dumps(replayed))==summary
assert summary['driver_rx_equals_raw'] and summary['received_delta']==summary['raw_bytes']==9550 and summary['direct_matches']==512
assert sha256((base/'windows-tx-journal.bin').read_bytes()).hexdigest()==summary['journal_sha256']
session=(base.parent.parent/'sessions/57-driver-raw-logging-boundary.md').read_text()
assert summary['journal_sha256'] in session and summary['journal_crc'] in session
assert '未取得稳定性修复' in session
print('RX57 verified: four exact functions, dual raw-log worker/config lifecycle; historical six-read concurrency; preserved setup failure and corrected bounded capture; 9550 driver/counter/raw bytes and 512 direct journal matches; restored state. Passing sample is not a repair.')
