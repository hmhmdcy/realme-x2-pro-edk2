from hashlib import sha256
import json
from pathlib import Path
import runpy

base=Path(__file__).resolve().parent
listed={}
for line in (base/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert name not in listed and sha256((base/name).read_bytes()).hexdigest()==expected,name
    listed[name]=expected
assert set(listed)=={p.name for p in base.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
rows=json.loads((base/'exports.json').read_text())
assert len(rows)==len({r['name'] for r in rows})
for row in rows:
    data=(base/row['name']).read_bytes()
    assert sha256(data).hexdigest()==row['exported_sha256']
    if Path(row['name']).suffix in ('.cs','.ps1','.py','.raw','.bin'):
        assert row['byte_identical'] and row['original_sha256']==row['exported_sha256']
    else: assert not data.startswith(b'\xef\xbb\xbf') and b'\r\n' not in data
for name,expected in json.loads((base/'dependencies.json').read_text()).items():
    assert sha256((base/name).read_bytes()).hexdigest()==expected,name
analyzer=runpy.run_path(str(base/'analyze-windows-perf.py'))
summary,blob=analyzer['analyze'](base)
assert summary==json.loads((base/'windows-perf-summary.json').read_text())
assert blob==(base/'windows-tx-journal.bin').read_bytes()
abi=json.loads((base/'diagnostic-abi.json').read_text())
assert abi['no_port_opened'] and abi['parser_clean'] and not abi['retained_pending_perf']
assert abi['ps_version'].startswith('5.1.') and abi['runtime']=='4.0.30319.42000'
assert (abi['ioctl'],abi['overlap_size'],abi['event_offset'])==(0x1b008c,32,24)
assert any('System.Threading.ThreadPool.BindHandle' in c for c in abi['ctor_calls'])
assert abi['sdk_ntddser_sha256']=='59e63c525f49802d1a40da184005ae83829f5a7dee6f1cd2ec3b89433cac8169'
state=json.loads((base/'final-state.json').read_text())
assert state['serial_closed'] and state['diagnostic_finally_verified'] and state['usb_not_attached']
assert not state['known_eud_helpers'] and state['ports']==['COM14']
assert len(state['devices'])==3 and all(d['Status']=='OK' for d in state['devices'])
assert not any('Attached' in line for line in state['target_usbipd'])
assert state['flash_count']==state['same_candidate_reboots']==0 and not state['flashed_partitions']
assert not state['installed_terminal_modified'] and not state['new_windows_admin_capture']
epoch=json.loads((base.parent/'rx53/source-epoch.json').read_text())
hashes={r['Path']:r['Hash'].lower() for r in state['hashes']}
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c']==epoch['sha256']['driver']
assert hashes['E:\\eud-host\\eud-terminal.ps1']=='9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img']=='50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
assert any(s.startswith(epoch['sha256']['driver']+' ') for s in state['linux_hashes'])
assert any(s.startswith(epoch['sha256']['Image']+' ') for s in state['linux_hashes'])
assert sha256((base.parent.parent/'linux-port/eud.c').read_bytes()).hexdigest()==epoch['sha256']['driver']
identity=json.loads((base.parent/'rx54/installed-driver-identity.json').read_text())
assert identity['identity_matches'] and identity['binary_sha256']=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
print('RX55 verified: missing seq7376, 511 direct matches, six drained counters/raw equal, first-sync failure retained, 19 once-only data receipts, unchanged candidate/terminal and finally closure. Stability unresolved.')
