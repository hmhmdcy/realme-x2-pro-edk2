from pathlib import Path
from hashlib import sha256
import gzip,json,re
from collections import Counter

base=Path(__file__).resolve().parent
listed={}
for line in (base/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert name not in listed and sha256((base/name).read_bytes()).hexdigest()==expected,name
    listed[name]=expected
assert set(listed)=={p.name for p in base.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
for row in json.loads((base/'exports.json').read_text()):
    data=(base/row['name']).read_bytes()
    assert sha256(data).hexdigest()==row['exported_sha256']
    if row.get('lossless_gzip'):
        assert sha256(gzip.decompress(data)).hexdigest()==row['original_sha256']
    elif Path(row['name']).suffix in ('.py','.ps1'):
        assert row['byte_identical'] and row['original_sha256']==row['exported_sha256']
    else: assert not data.startswith(b'\xef\xbb\xbf') and b'\r\n' not in data
for name,expected in json.loads((base/'dependencies.json').read_text()).items():
    assert sha256((base/name).read_bytes()).hexdigest()==expected,name
functions={}
for name in ['front-identity.json','reset-identity.json','padding-identity.json']:
    ident=json.loads((base/name).read_text())
    assert ident['identity_matches'] and ident['section_headers_match']
    assert ident['binary_sha256']=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
    assert ident['pdb_sha256']=='ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
    assert (ident['guid'],ident['age'])==('66581f50-52c9-4a32-9ac6-fe0c57b94a80',1)
    for f in ident['functions']:
        data=bytearray(); address=int(f['start_rva'],16)
        for line in (base/f['disassembly']).read_text().splitlines():
            match=re.match(r'^([0-9a-f]{8}) ((?:[0-9a-f]{2} )*[0-9a-f]{2})\s+[a-z]',line)
            assert match and int(match[1],16)==address,line
            code=bytes.fromhex(match[2]); data.extend(code); address+=len(code)
        assert address==int(f['end_rva'],16) and len(data)==f['size']
        assert sha256(data).hexdigest()==f['code_sha256']
        functions[f['name']]=f
assert len(functions)==8
calls=json.loads((base/'exact-callers.json').read_text())
assert [c['caller'] for c in calls if c['target']=='vPutToReadBuffer']==['ReadIrpCompletion']
assert any(c['caller']=='QCSER_ReadThread' and c['call']=='00024e22' and c['target']=='QCSER_LogData' for c in calls)
summary=json.loads((base/'old-etw-in-summary.json').read_text())
events=json.loads(gzip.decompress((base/'old-etw-target-transfers.json.gz').read_bytes()))
incoming=[e for e in events if e['id']=='27' and e['fields'].get('fid_PipeHandle')==['0xFFFFC00BB56C89F0']]
lengths=dict(Counter(e['fields']['fid_URB_TransferBufferLength'][0] for e in incoming))
assert len(events)==summary['target_transfer_events']==196
assert len(incoming)==summary['in_completions']==95 and lengths==summary['in_length_histogram']
assert sum(int(k,0)*v for k,v in lengths.items())==summary['in_completed_bytes']==sum(summary['raw_bytes'].values())==489
assert not summary['payload_captured'] and not summary['physical_data_pid_captured']
reg=json.loads((base/'registry-readonly.json').read_text())
assert reg['read_only'] and reg['service']=='qcusbser'
assert len(reg['values'])==3 and all(v['QCDriverConfig'] is None and v['QCDriverLoggingDirectory'] is None for v in reg['values'])
state=json.loads((base/'final-state.json').read_text())
assert state['no_port_opened_this_session'] and state['no_usbip_attach_this_session']
assert state['flash_count']==state['same_candidate_reboots']==0
assert not state['registry_changed'] and not state['new_windows_admin_capture'] and not state['installed_terminal_modified']
assert len(state['devices'])==3 and all(d['Status']=='OK' for d in state['devices'])
assert not state['known_eud_helpers'] and state['ports']==['COM14']
assert not any('Attached' in s for s in state['target_usbipd'])
epoch=json.loads((base.parent/'rx53/source-epoch.json').read_text())
hashes={r['Path']:r['Hash'].lower() for r in state['hashes']}
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c']==epoch['sha256']['driver']
assert hashes['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img']=='50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
assert hashes['E:\\eud-host\\eud-terminal.ps1']=='9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert any(s.startswith(epoch['sha256']['driver']+' ') for s in state['linux_hashes'])
assert any(s.startswith(epoch['sha256']['Image']+' ') for s in state['linux_hashes'])
print('RX56 verified: eight exact functions; conditional pre-buffer logger/reset selection/padding bounds; old ETW 489-byte sum; read-only state; no repair claimed.')
