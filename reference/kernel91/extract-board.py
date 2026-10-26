from pathlib import Path
import hashlib,json,tarfile,struct
O=Path('/mnt/e/edk2-samurai-out/kernel91');W=Path('/mnt/e/RealmeX2Pro edk2')
archive=O.parent/'kernel81/wifi-firmware-stock.tar'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())=='ef6f8e4283a720a4d22916176e8e8d314577604987e1ca7626552f4cf091f190'
manifest=json.loads((W/'reference/kernel81/wifi-firmware-manifest.json').read_text())
entry=next(x for x in manifest['files'] if x['name']=='bdwlan.bin')
with tarfile.open(archive) as t:
    members=[m for m in t.getmembers() if Path(m.name).name=='bdwlan.bin' and m.isfile()]
    assert len(members)==1
    data=t.extractfile(members[0]).read()
assert len(data)==26328 and len(data)==entry['bytes'] and sha(data)==entry['sha256']
check=0
for word in struct.unpack('<'+'H'*(len(data)//2),data): check^=word
assert check==0xffff
assert struct.unpack_from('<H',data,8)[0]==len(data)
(O/'board.bin').write_bytes(data)
report=dict(source='same handset stock bdwlan.bin',qmi_chip_id='0x30224',qmi_board_id='0xff',
            selection='stock CNSS_BDF_BIN selects bdwlan.bin when board_id == 0xff',
            target='ath10k/WCN3990/hw1.0/board.bin',bytes=len(data),sha256=sha(data),xor16='0xffff',byte_unchanged=True)
(W/'reference/kernel91/board-selection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
