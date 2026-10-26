from hashlib import sha256
import gzip
import json
from pathlib import Path
import re
import runpy

base=Path(__file__).resolve().parent
listed={}
for line in (base/'SHA256SUMS').read_text().splitlines():
    want,name=line.split('  ',1)
    assert name not in listed and sha256((base/name).read_bytes()).hexdigest()==want,name
    listed[name]=want
assert set(listed)=={p.name for p in base.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
rows=json.loads((base/'exports.json').read_text())
assert len(rows)==len({r['name'] for r in rows})
for row in rows:
    data=(base/row['name']).read_bytes()
    assert sha256(data).hexdigest()==row['exported_sha256']
    if row['name'].endswith('.gz'):
        assert sha256(gzip.decompress(data)).hexdigest()==row['original_sha256']
    elif Path(row['name']).suffix in ('.raw','.bin','.py','.ps1','.sh'):
        assert row['byte_identical'] and row['exported_sha256']==row['original_sha256']
    else:
        assert not data.startswith(b'\xef\xbb\xbf') and b'\r\n' not in data
repeated=runpy.run_path(str(base/'analyze-repeat.py'))
assert repeated['summary']==json.loads((base/'repeat-summary.json').read_text())
assert repeated['blob']==(base/'repeat-tx-journal.bin').read_bytes()
f1=runpy.run_path(str(base/'analyze-f1.py'))
assert f1['summary']==json.loads((base/'f1-summary.json').read_text())
assert repeated['summary']['partial_cancels']==[dict(status=-2,bytes=6,hex='90 04 5b 20 31 38')]
assert sha256((base/'eud-usb-repeated-console.py').read_bytes()).hexdigest()=='48bad103de1b41705d194ad332d88038807f3724753379af3d233d6fc6fa74ce'
assert sha256((base/'eud-usb-console-f1.py').read_bytes()).hexdigest()=='39d244978fdc6322bb0fbc3a1fdafc142ef31f5e3fe01c9c59b0bf08ed1bc3e5'

identity=json.loads((base/'installed-driver-identity.json').read_text())
assert identity['identity_matches'] and identity['section_headers_match']
assert (identity['guid'],identity['age'])==('66581f50-52c9-4a32-9ac6-fe0c57b94a80',1)
assert identity['binary_sha256']=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
assert identity['pdb_sha256']=='ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
assert {r['name'] for r in identity['functions']}=={'QCSER_Open','QCSER_StartDataThreads','QCRD_StartReadThread','QCSER_ReadThread','SerialGetStats'}
for row in identity['functions']:
    address=int(row['start_rva'],16); code=bytearray()
    for line in (base/row['disassembly']).read_text().splitlines():
        f=line.split(); assert int(f[0],16)==address+len(code)
        for token in f[1:]:
            if not re.fullmatch(r'[0-9a-f]{2}',token): break
            code.append(int(token,16))
    assert address+len(code)==int(row['end_rva'],16)
    assert len(code)==row['size'] and sha256(code).hexdigest()==row['code_sha256']
asm=(base/'SerialGetStats.asm.txt').read_text()
assert '0002b8e2' in asm and 'qword ptr [r9 + 0x2e0]' in asm and '0002b8f4' in asm
types=json.loads((base/'rx50-selected-types.json').read_text())
assert any(r['name']=='_SERIALPERF_STATS' and r['size']==24 for r in types)
received_type=json.loads((base/'perf-received-type.json').read_text())
assert received_type['name']=='_SERIALPERF_STATS' and received_type['size']==24
assert any(m['name']=='ReceivedCount' and m['offset']==0 for m in received_type['members'])
assert '00029795' in (base/'rx50-vPutToReadBuffer.asm.txt').read_text()

def decode_raw(name):
    raw=(base/(name+'.raw')).read_bytes(); body=bytearray(); p=0; frames=0
    while p<len(raw):
        assert raw[p]==0x90 and 1<=raw[p+1]<=4
        n=raw[p+1]; assert p+n+2<=len(raw)
        body.extend(raw[p+2:p+n+2]); p+=n+2; frames+=1
    text=body.decode('ascii',errors='replace').replace('\ufffd','?')
    norm=lambda s:re.sub(r'\r+\n','\n',s)
    assert norm(text)==norm((base/(name+'.txt')).read_bytes().decode('utf-8-sig'))
    return text,frames
boot,count=decode_raw('same-image-boot'); assert count==8956
assert 'sent=0 frames=8956 stray=0 pending=0' in (base/'same-image-boot.events.txt').read_text()
assert 'TOP_CFG=00000011 original=00000000' in boot and 'shell started on /dev/ttyEUD0' in boot
assert 'IRQ armed virq=19 active=1 mask=01' in boot
native,count=decode_raw('restored-native'); assert count==89 and '\nR54READY\r\n' in native
assert re.search(r'^\[\s*\d+\.\d+\] eud: tty byte=15 polls=',native)
assert 'fault=0 active=1' in native
events=(base/'restored-native.events.txt').read_text()
assert events.count('TX native')==events.count('ACK native')==2 and 'attempt=2' not in events
assert 'len=14 data=65 63 68 6f 20 52 35 34 52 45 41 44 59 0a' in events
state=json.loads((base/'final-state.json').read_text())
assert state['serial_closed'] and state['usb_owners_closed'] and state['usb_detached_or_removed_after_f1'] and not state['known_eud_helpers']
assert state['flash_count']==0 and not state['flashed_partitions'] and state['same_candidate_reboots']==1
assert not state['new_windows_admin_capture'] and not state['installed_terminal_modified']
assert state['ports']==['COM14'] and len(state['devices'])==3 and all(d['Status']=='OK' for d in state['devices'])
assert not any('Attached' in line for line in state['target_usbipd'])
hashes={r['Path']:r['Hash'].lower() for r in state['hashes']}
epoch=json.loads((base.parent/'rx53/source-epoch.json').read_text())
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c']==epoch['sha256']['driver']
assert hashes['E:\\eud-host\\eud-terminal.ps1']=='9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img']=='50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
assert any(s.startswith(epoch['sha256']['driver']+' ') for s in state['linux_hashes'])
assert any(s.startswith(epoch['sha256']['Image']+' ') for s in state['linux_hashes'])
assert sha256((base.parent.parent/'linux-port/eud.c').read_bytes()).hexdigest()==epoch['sha256']['driver']
print('RX54 verified: nine console inputs, six credited empties, console F1/fastboot, complete USB/raw and direct 512-frame journal, unchanged candidate/restored owner; TX remains open.')
